// Command evalset adalah perkakas evaluasi akurasi untuk pipguard,
// sesuai metodologi build_guide.md §6.2.
//
// Diberi nama paket "positif" (seharusnya ditandai berisiko) dan "negatif"
// (paket sah, seharusnya AMAN), perkakas ini menjalankan scorer yang sama
// persis dengan yang dipakai pipguard, lalu menghitung matriks konfusi,
// presisi, recall, F1, dan FPR untuk setiap detektor:
//
//   - pipguard-v2      : model yang dipakai shim (scorer.V2)
//   - pipguard-v1      : rancangan awal Tabel 3.5/3.6 (scorer.V1)
//   - registry-only    : tandai bila tidak terdaftar di PyPI (I-01 saja)
//   - new-or-missing   : tandai bila tidak terdaftar atau berumur < 30 hari (I-01 ∨ I-02)
//   - similarity-v1/v2 : tandai bila nama mirip paket populer (I-05 saja)
//   - v2-without-I-0x    : pipguard-v2 dengan satu heuristik dimatikan (ablasi)
//
// Masukan berupa daftar nama (diambil langsung dari PyPI saat dijalankan)
// atau berkas JSONL metadata beku (-positive-meta/-negative-meta). Daftar
// nama sebaiknya dibekukan sekali dengan -dump-meta lalu dievaluasi dari
// berkas itu, agar hasil tidak bergantung pada tanggal evaluasi.
//
// Metadata paket berbahaya yang sudah dihapus dari PyPI berasal dari
// riwayat publik (scripts/eval/build_sets.py) dan dinilai pada saat paket
// itu masih dapat dipasang (as_of).
//
// Tidak untuk dipasang sebagai shim — ini alat bantu riset/pengujian.
package main

import (
	"bufio"
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/editorid0001/pipguard/internal/parser"
	"github.com/editorid0001/pipguard/internal/popular"
	"github.com/editorid0001/pipguard/internal/registry"
	"github.com/editorid0001/pipguard/internal/scorer"
)

// fetchWithRetry memanggil registry dengan backoff eksponensial.
// Timeout klien shim (3 detik) sengaja pendek agar fail-open cepat saat
// runtime. Untuk evaluasi, timeout diperpanjang agar paket dengan metadata
// besar tidak tercatat sebagai kegagalan palsu, dan kegagalan sementara
// dicoba ulang sebelum dianggap gagal.
func fetchWithRetry(name string) (registry.Metadata, error) {
	var lastErr error
	for attempt := 0; attempt < 4; attempt++ {
		m, err := registry.FetchWithTimeout(name, 60*time.Second)
		if err == nil {
			return m, nil
		}
		lastErr = err
		time.Sleep(time.Duration(1<<attempt) * 500 * time.Millisecond)
	}
	return registry.Metadata{}, lastErr
}

// metaRecord adalah satu baris berkas metadata JSONL (-positive-meta,
// -negative-meta, keluaran -dump-meta dan scripts/eval/build_sets.py).
type metaRecord struct {
	Name  string    `json:"name"`
	Group string    `json:"group"`
	Split string    `json:"split,omitempty"`
	AsOf  time.Time `json:"as_of"`
	registry.Metadata
}

type job struct {
	name, label, group, split string
	meta                      *registry.Metadata // nil → ambil langsung dari PyPI
	asOf                      time.Time
}

type labeledResult struct {
	Name            string
	Label           string // "positive" (seharusnya berisiko) atau "negative" (seharusnya aman)
	Group           string // asal nama (nama berkas, atau "group" pada berkas metadata)
	Split           string // "dev"/"test" bila berkas metadata menyertakannya
	AsOf            time.Time
	Meta            registry.Metadata
	Signals         scorer.Signals // signals of the v3 model (v2 ignores I-10, which it gives no points)
	V1, V2, V2I, V3 scorer.Result
	Err             error
}

// detector memutuskan apakah suatu hasil "ditandai" menurut satu varian.
type detector struct {
	name    string
	flagged func(r labeledResult) bool
}

// v2Initial adalah kalibrasi v2 pertama yang ditetapkan sebelum melihat data
// uji: bobot dipas pada split dev (paket < 2025) atas seluruh populasi.
// Model ini gagal pada data uji (pergeseran taktik penyerang; lihat
// paper/RESULTS.md) dan diganti scorer.V2. Dipertahankan di sini — bukan di
// shim — agar hasil kegagalannya tetap dapat direproduksi dan dilaporkan.
func v2Initial(popular []string) scorer.Model {
	return scorer.Model{
		Name: "v2-initial",
		Points: map[string]int{
			scorer.RuleNotRegistered: 100, scorer.RuleNew: 39, scorer.RuleNoLinks: 18,
			scorer.RuleSimilarName: 18, scorer.RuleSdistOnly: 35, scorer.RuleShortDesc: 2,
		},
		Warn: 76, Danger: 95,
		Similarity: scorer.NewSimilarity(popular, 4, 1, false),
	}
}

// without mengembalikan pipguard-v2 dengan satu heuristik dimatikan, dinilai
// pada tingkat "min" (Warning = ditandai, Danger = tingkat BAHAYA). Skor
// bersifat aditif, sehingga mengurangi poin heuristik itu lalu menerapkan
// ulang ambang identik dengan menjalankan scorer tanpa heuristik tersebut.
func without(m scorer.Model, rule string, min scorer.Level) detector {
	name := "v2-without-" + rule
	if min == scorer.Danger {
		name = "v2-danger-tanpa-" + rule
	}
	return detector{name, func(r labeledResult) bool {
		if r.Signals.Fired[scorer.RuleNotRegistered] {
			return true
		}
		score := r.V2.Score
		for _, h := range r.V2.Hits {
			if h.Rule == rule {
				score -= h.Points
			}
		}
		return m.LevelFor(score) >= min
	}}
}

// days returns the whole days from a to b (negative or zero when b is not after a).
func days(a, b time.Time) float64 {
	if a.IsZero() || b.IsZero() {
		return -1
	}
	return b.Sub(a).Hours() / 24
}

func buildDetectors(v2 scorer.Model) []detector {
	ds := []detector{
		{"v2+I10-90", func(r labeledResult) bool { return r.V3.Level != scorer.Safe }},
		{"v2+I10-90-danger", func(r labeledResult) bool { return r.V3.Level == scorer.Danger }},
		// Release-level cooldown as in pip --uploaded-prior-to P30D, uv --exclude-newer
		// and pnpm minimumReleaseAge: the newest release is withheld while younger
		// than 30 days (an unregistered name fails in pip anyway).
		{"release-cooldown-30", func(r labeledResult) bool {
			return !r.Meta.Exists || (!r.Meta.LatestRelease.IsZero() && days(r.Meta.LatestRelease, r.AsOf) < 30)
		}},
		{"dormancy-only", func(r labeledResult) bool { return r.Signals.Fired[scorer.RuleReactivated] }},
		{"pipguard-v2", func(r labeledResult) bool { return r.V2.Level != scorer.Safe }},
		{"pipguard-v2-danger", func(r labeledResult) bool { return r.V2.Level == scorer.Danger }},
		{"pipguard-v1", func(r labeledResult) bool { return r.V1.Level != scorer.Safe }},
		{"pipguard-v1-danger", func(r labeledResult) bool { return r.V1.Level == scorer.Danger }},
		{"v2-initial", func(r labeledResult) bool { return r.V2I.Level != scorer.Safe }},
		{"registry-only", func(r labeledResult) bool { return !r.Meta.Exists }},
		{"new-or-missing", func(r labeledResult) bool {
			return !r.Meta.Exists || r.Signals.Fired[scorer.RuleNew]
		}},
		{"similarity-v1", func(r labeledResult) bool { return hasHit(r.V1, scorer.RuleSimilarName) }},
		{"similarity-v2", func(r labeledResult) bool { return r.Signals.Fired[scorer.RuleSimilarName] }},
	}
	for _, rule := range scorer.AllRules[1:] {
		if v2.Points[rule] > 0 {
			ds = append(ds, without(v2, rule, scorer.Warning), without(v2, rule, scorer.Danger))
		}
	}
	return ds
}

func hasHit(r scorer.Result, rule string) bool {
	for _, h := range r.Hits {
		if h.Rule == rule {
			return true
		}
	}
	return false
}

func readLines(path string) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var lines []string
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		lines = append(lines, line)
	}
	return lines, sc.Err()
}

func readMeta(path string) ([]metaRecord, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var recs []metaRecord
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	for n := 1; sc.Scan(); n++ {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var r metaRecord
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			return nil, fmt.Errorf("%s:%d: %w", path, n, err)
		}
		if r.Name == "" || r.AsOf.IsZero() {
			return nil, fmt.Errorf("%s:%d: name dan as_of wajib diisi", path, n)
		}
		recs = append(recs, r)
	}
	return recs, sc.Err()
}

// splitPaths memecah daftar berkas dipisah koma.
func splitPaths(s string) []string {
	var out []string
	for _, p := range strings.Split(s, ",") {
		if p = strings.TrimSpace(p); p != "" {
			out = append(out, p)
		}
	}
	return out
}

func groupName(path string) string {
	return strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
}

func loadPopular(path string) []string {
	raw, err := os.ReadFile(path)
	if err != nil {
		log.Fatalf("evalset: gagal membaca daftar populer %q: %v", path, err)
	}
	return popular.Parse(string(raw))
}

func main() {
	var (
		positivePath  = flag.String("positive", "", "berkas nama paket positif, dipisah koma (satu nama per baris; seharusnya BERISIKO)")
		positiveMeta  = flag.String("positive-meta", "", "berkas JSONL metadata positif, dipisah koma")
		negativePath  = flag.String("negative", "", "berkas nama paket negatif, dipisah koma (satu nama per baris; seharusnya AMAN)")
		negativeMeta  = flag.String("negative-meta", "", "berkas JSONL metadata negatif, dipisah koma")
		popularV1     = flag.String("popular-v1", "assets/popular.txt", "daftar paket populer untuk model v1")
		popularV2     = flag.String("popular-v2", "assets/popular.txt", "daftar paket populer untuk model v2 (sama dengan yang ditanam di shim)")
		outCSV        = flag.String("out", "", "tulis hasil per-nama ke berkas CSV (opsional)")
		dumpMeta      = flag.String("dump-meta", "", "tulis metadata nama yang diambil langsung ke JSONL ini (membekukan input)")
		redact        = flag.String("redact", "", "kelompok yang namanya disamarkan di -out (mis. nama halusinasi), dipisah koma")
		simGrid       = flag.String("sim-grid", "", "tulis evaluasi kisi konfigurasi I-05 ke CSV ini (lihat -top-json)")
		topJSON       = flag.String("top-json", "testdata/frozen/raw/top_pypi_packages.json", "daftar teratas hugovk untuk -sim-grid")
		concurrency   = flag.Int("concurrency", 8, "jumlah goroutine pengambil PyPI paralel")
		limitPositive = flag.Int("limit-positive", 0, "batasi jumlah nama positif per berkas (0 = semua)")
		limitNegative = flag.Int("limit-negative", 0, "batasi jumlah nama negatif per berkas (0 = semua)")
		quiet         = flag.Bool("quiet", false, "jangan cetak tabel metrik")
		printModel    = flag.Bool("print-model", false, "cetak konfigurasi model v2 sebagai JSON lalu keluar")
	)
	flag.Parse()

	if *printModel {
		m := scorer.V2(loadPopular(*popularV2))
		out, _ := json.MarshalIndent(map[string]any{
			"points": m.Points, "warn": m.Warn, "danger": m.Danger,
			"similarity": map[string]any{"list_size": len(m.Similarity.Popular), "min_len": m.Similarity.MinLen,
				"max_dist": m.Similarity.MaxDist, "transpositions": m.Similarity.Transpositions},
		}, "", "  ")
		fmt.Println(string(out))
		return
	}

	if *positivePath == "" && *positiveMeta == "" && *negativePath == "" && *negativeMeta == "" {
		fmt.Fprintln(os.Stderr, "evalset: berikan setidaknya salah satu dari -positive, -positive-meta, -negative, -negative-meta")
		os.Exit(2)
	}

	v1 := scorer.V1(loadPopular(*popularV1))
	v2 := scorer.V2(loadPopular(*popularV2))
	// I-10 is evaluated at a fixed 90-day dormancy here so that its signal and
	// the columns prev_gap_days/release_age_days are always available; other
	// dormancy periods are simulated from those columns (analyze_v3.py).
	v3 := scorer.V3(loadPopular(*popularV2), 90)
	// v2-initial memakai 2.000 teratas; daftar v2 terurut menurut peringkat.
	v2iList := loadPopular(*popularV2)
	if len(v2iList) > 2000 {
		v2iList = v2iList[:2000]
	}
	v2i := v2Initial(v2iList)
	detectors := buildDetectors(v2)

	var jobs []job
	addNames := func(paths, label string, limit int) {
		for _, p := range splitPaths(paths) {
			names, err := readLines(p)
			if err != nil {
				log.Fatalf("evalset: gagal membaca %q: %v", p, err)
			}
			if limit > 0 && len(names) > limit {
				names = names[:limit]
			}
			// Konvensi nama berkas: akhiran _dev/_test menandai split.
			g, split := groupName(p), ""
			if i := strings.LastIndex(g, "_"); i > 0 && (g[i+1:] == "dev" || g[i+1:] == "test") {
				g, split = g[:i], g[i+1:]
			}
			for _, n := range names {
				jobs = append(jobs, job{name: n, label: label, group: g, split: split})
			}
		}
	}
	addMeta := func(paths, label string, limit int) {
		for _, p := range splitPaths(paths) {
			recs, err := readMeta(p)
			if err != nil {
				log.Fatalf("evalset: gagal membaca %q: %v", p, err)
			}
			if limit > 0 && len(recs) > limit {
				recs = recs[:limit]
			}
			for _, r := range recs {
				g := r.Group
				if g == "" {
					g = groupName(p)
				}
				m := r.Metadata
				jobs = append(jobs, job{name: r.Name, label: label, group: g, split: r.Split, meta: &m, asOf: r.AsOf})
			}
		}
	}
	addNames(*positivePath, "positive", *limitPositive)
	addMeta(*positiveMeta, "positive", *limitPositive)
	addNames(*negativePath, "negative", *limitNegative)
	addMeta(*negativeMeta, "negative", *limitNegative)

	fmt.Fprintf(os.Stderr, "evalset: mengevaluasi %d nama (concurrency=%d)...\n", len(jobs), *concurrency)

	results := make([]labeledResult, len(jobs))
	sem := make(chan struct{}, *concurrency)
	var wg sync.WaitGroup
	var done int
	var mu sync.Mutex
	start := time.Now()

	for i, j := range jobs {
		wg.Add(1)
		sem <- struct{}{}
		go func(i int, j job) {
			defer wg.Done()
			defer func() { <-sem }()

			norm := parser.Normalize(j.name)
			r := labeledResult{Name: j.name, Label: j.label, Group: j.group, Split: j.split, AsOf: j.asOf}
			if j.meta != nil {
				r.Meta = *j.meta
			} else {
				r.Meta, r.Err = fetchWithRetry(norm)
				r.AsOf = time.Now().UTC().Truncate(time.Second)
			}
			if r.Err == nil {
				r.Signals = v3.Signals(norm, r.Meta, r.AsOf)
				r.V2 = v2.Score(r.Signals)
				r.V3 = v3.Score(r.Signals)
				r.V1 = v1.EvaluateAt(norm, r.Meta, r.AsOf)
				r.V2I = v2i.EvaluateAt(norm, r.Meta, r.AsOf)
			}
			results[i] = r

			mu.Lock()
			done++
			if j.meta == nil && (done%100 == 0 || done == len(jobs)) {
				fmt.Fprintf(os.Stderr, "  ... %d/%d (%.0fs)\n", done, len(jobs), time.Since(start).Seconds())
			}
			mu.Unlock()
		}(i, j)
	}
	wg.Wait()

	var ok []labeledResult
	errs := 0
	for _, r := range results {
		if r.Err != nil {
			errs++
			fmt.Fprintf(os.Stderr, "evalset: gagal memeriksa satu nama (%s): %v\n", r.Group, r.Err)
			continue
		}
		ok = append(ok, r)
	}

	if *dumpMeta != "" {
		if err := writeMeta(*dumpMeta, ok); err != nil {
			log.Fatalf("evalset: gagal menulis %s: %v", *dumpMeta, err)
		}
		fmt.Fprintf(os.Stderr, "evalset: metadata beku ditulis ke %s\n", *dumpMeta)
	}
	if !*quiet {
		printMetrics(ok, detectors, errs)
		fmt.Printf("\nDurasi  : %.1fs\n", time.Since(start).Seconds())
	}
	if *outCSV != "" {
		if err := writeCSV(*outCSV, results, detectors, groupSet(*redact)); err != nil {
			log.Fatalf("evalset: gagal menulis CSV: %v", err)
		}
		fmt.Fprintf(os.Stderr, "evalset: hasil per-nama ditulis ke %s\n", *outCSV)
	}
	if *simGrid != "" {
		if err := writeSimGrid(*simGrid, *topJSON, v1.Similarity.Popular, ok); err != nil {
			log.Fatalf("evalset: gagal menulis kisi I-05: %v", err)
		}
		fmt.Fprintf(os.Stderr, "evalset: kisi I-05 ditulis ke %s\n", *simGrid)
	}
}

func printMetrics(ok []labeledResult, detectors []detector, errs int) {
	fmt.Println()
	fmt.Println("=== Metrik per detektor (semua positif vs semua negatif) ===")
	fmt.Println("Rentang = interval kepercayaan Wilson 95%.")
	if errs > 0 {
		fmt.Printf("Gagal diperiksa (dikecualikan dari metrik): %d\n", errs)
	}
	fmt.Println()
	fmt.Printf("%-16s %5s %5s %5s %5s  %-7s %-21s %-7s %-21s\n",
		"Detektor", "TP", "FN", "FP", "TN", "Presisi", "Recall", "F1", "FPR")
	for _, d := range detectors {
		c := confusion(ok, d, "")
		precision := safeDiv(float64(c.tp), float64(c.tp+c.fp))
		recall := safeDiv(float64(c.tp), float64(c.tp+c.fn))
		f1 := safeDiv(2*precision*recall, precision+recall)
		fmt.Printf("%-16s %5d %5d %5d %5d  %.4f  %-21s %.4f  %-21s\n",
			d.name, c.tp, c.fn, c.fp, c.tn, precision,
			withCI(c.tp, c.tp+c.fn), f1, withCI(c.fp, c.fp+c.tn))
	}

	// Rasio kelas berbeda antarkelompok, sehingga presisi gabungan sulit
	// dibandingkan. Recall per kelompok positif dan FPR per kelompok
	// negatif tidak bergantung pada rasio kelas.
	groups := map[string][]string{}
	for _, r := range ok {
		g := r.Group
		if r.Split != "" {
			g += "/" + r.Split
		}
		if !contains(groups[r.Label], g) {
			groups[r.Label] = append(groups[r.Label], g)
		}
	}
	for _, label := range []string{"positive", "negative"} {
		gs := groups[label]
		if len(gs) == 0 {
			continue
		}
		sort.Strings(gs)
		metric := "Recall"
		if label == "negative" {
			metric = "FPR"
		}
		fmt.Println()
		fmt.Printf("=== %s per kelompok %s ===\n", metric, label)
		for _, g := range gs {
			fmt.Printf("\n%s\n", g)
			for _, d := range detectors {
				c := confusion(ok, d, g)
				k, n := c.tp, c.tp+c.fn
				if label == "negative" {
					k, n = c.fp, c.fp+c.tn
				}
				fmt.Printf("  %-16s %6d/%-6d %s\n", d.name, k, n, withCI(k, n))
			}
		}
	}
}

type counts struct{ tp, fn, fp, tn int }

// confusion menghitung matriks konfusi detektor d; group kosong = semua,
// selain itu "kelompok" atau "kelompok/split".
func confusion(rs []labeledResult, d detector, group string) counts {
	var c counts
	for _, r := range rs {
		if group != "" && r.Group != group && r.Group+"/"+r.Split != group {
			continue
		}
		f := d.flagged(r)
		switch {
		case r.Label == "positive" && f:
			c.tp++
		case r.Label == "positive":
			c.fn++
		case f:
			c.fp++
		default:
			c.tn++
		}
	}
	return c
}

// wilson mengembalikan interval kepercayaan skor Wilson 95% untuk k/n.
func wilson(k, n int) (lo, hi float64) {
	if n == 0 {
		return 0, 0
	}
	const z = 1.959964
	p := float64(k) / float64(n)
	nn := float64(n)
	den := 1 + z*z/nn
	center := (p + z*z/(2*nn)) / den
	half := z * math.Sqrt(p*(1-p)/nn+z*z/(4*nn*nn)) / den
	return math.Max(0, center-half), math.Min(1, center+half)
}

func withCI(k, n int) string {
	if n == 0 {
		return "n/a"
	}
	lo, hi := wilson(k, n)
	return fmt.Sprintf("%.4f [%.3f–%.3f]", safeDiv(float64(k), float64(n)), lo, hi)
}

func contains(xs []string, s string) bool {
	for _, x := range xs {
		if x == s {
			return true
		}
	}
	return false
}

func safeDiv(a, b float64) float64 {
	if b == 0 {
		return 0
	}
	return a / b
}

func groupSet(s string) map[string]bool {
	m := map[string]bool{}
	for _, g := range splitPaths(s) {
		m[g] = true
	}
	return m
}

// redactName menyamarkan nama yang tidak boleh dipublikasikan (nama
// halusinasi yang belum terdaftar dapat didaftarkan penyerang).
func redactName(name string) string {
	h := sha256.Sum256([]byte("pipguard-redact:" + parser.Normalize(name)))
	return "redacted-" + hex.EncodeToString(h[:])[:12]
}

func writeMeta(path string, rs []labeledResult) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	w := bufio.NewWriter(f)
	for _, r := range rs {
		line, err := json.Marshal(metaRecord{Name: parser.Normalize(r.Name), Group: r.Group, Split: r.Split,
			AsOf: r.AsOf, Metadata: r.Meta})
		if err != nil {
			return err
		}
		w.Write(line)
		w.WriteByte('\n')
	}
	return w.Flush()
}

func rulesOf(r scorer.Result) string {
	var rules []string
	for _, h := range r.Hits {
		rules = append(rules, h.Rule)
	}
	return strings.Join(rules, "+")
}

func fmtDays(d float64, ok bool) string {
	if !ok || d < 0 {
		return ""
	}
	return fmt.Sprintf("%.3f", d)
}

func b01(b bool) string {
	if b {
		return "1"
	}
	return "0"
}

func writeCSV(path string, results []labeledResult, detectors []detector, redacted map[string]bool) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	w := csv.NewWriter(f)
	defer w.Flush()

	header := []string{"name", "label", "group", "split", "as_of", "exists", "error",
		"v1_score", "v1_level", "v1_rules", "v2_score", "v2_level", "v2_rules", "v3_score", "v3_level", "v3_rules",
		"similar_to", "distance", "project_age_days", "release_age_days", "prev_gap_days"}
	for _, rule := range scorer.AllRules {
		header = append(header, "sig_"+rule)
	}
	for _, d := range detectors {
		header = append(header, "flagged_"+d.name)
	}
	_ = w.Write(header)
	for _, r := range results {
		name := r.Name
		if redacted[r.Group] {
			name = redactName(name)
		}
		errStr := ""
		if r.Err != nil {
			errStr = r.Err.Error()
		}
		asOf := ""
		if !r.AsOf.IsZero() {
			asOf = r.AsOf.UTC().Format(time.RFC3339)
		}
		row := []string{name, r.Label, r.Group, r.Split, asOf, b01(r.Meta.Exists), errStr,
			fmt.Sprint(r.V1.Score), r.V1.Level.String(), rulesOf(r.V1),
			fmt.Sprint(r.V2.Score), r.V2.Level.String(), rulesOf(r.V2),
			fmt.Sprint(r.V3.Score), r.V3.Level.String(), rulesOf(r.V3),
			r.Signals.SimilarTo, fmt.Sprint(r.Signals.Distance),
			fmtDays(days(r.Meta.FirstRelease, r.AsOf), r.Meta.Exists),
			fmtDays(days(r.Meta.LatestRelease, r.AsOf), r.Meta.Exists),
			fmtDays(days(r.Meta.PreviousRelease, r.Meta.LatestRelease), r.Meta.Exists && !r.Meta.PreviousRelease.IsZero())}
		for _, rule := range scorer.AllRules {
			row = append(row, b01(r.Signals.Fired[rule]))
		}
		for _, d := range detectors {
			row = append(row, b01(r.Err == nil && d.flagged(r)))
		}
		_ = w.Write(row)
	}
	return w.Error()
}

// writeSimGrid menulis, untuk setiap nama, jarak ke nama populer terdekat
// (1 atau 2; 0 = tidak ada dalam jarak 2, atau nama itu sendiri populer)
// terhadap beberapa daftar rujukan (kurasi v1, atau N teratas hugovk), dengan
// dan tanpa transposisi. Dari sini setiap konfigurasi I-05 (daftar × panjang
// minimum × jarak maksimum × transposisi) dapat dievaluasi tanpa menjalankan
// ulang evalset (scripts/eval/fit_weights.py). Nama tidak ditulis.
func writeSimGrid(path, topPath string, curated []string, rs []labeledResult) error {
	raw, err := os.ReadFile(topPath)
	if err != nil {
		return err
	}
	var top struct {
		Rows []struct {
			Project string `json:"project"`
		} `json:"rows"`
	}
	if err := json.Unmarshal(raw, &top); err != nil {
		return err
	}
	var topNames []string
	for _, r := range top.Rows {
		topNames = append(topNames, parser.Normalize(r.Project))
	}

	type list struct {
		name  string
		names []string
	}
	lists := []list{{"curated-v1", curated}}
	for _, n := range []int{500, 1000, 2000, 5000} {
		if n <= len(topNames) {
			lists = append(lists, list{fmt.Sprintf("top-%d", n), topNames[:n]})
		}
	}
	var matchers []*scorer.Similarity
	header := []string{"label", "group", "split", "name_len"}
	for _, l := range lists {
		for _, tr := range []bool{false, true} {
			matchers = append(matchers, scorer.NewSimilarity(l.names, 0, 2, tr))
			header = append(header, fmt.Sprintf("d_%s_%s", l.name, map[bool]string{false: "lev", true: "osa"}[tr]))
		}
	}

	rows := make([][]string, len(rs))
	var wg sync.WaitGroup
	sem := make(chan struct{}, 16)
	for i, r := range rs {
		wg.Add(1)
		sem <- struct{}{}
		go func(i int, r labeledResult) {
			defer wg.Done()
			defer func() { <-sem }()
			name := parser.Normalize(r.Name)
			row := []string{r.Label, r.Group, r.Split, fmt.Sprint(len([]rune(name)))}
			for _, m := range matchers {
				_, d, _ := m.Match(name)
				row = append(row, fmt.Sprint(d))
			}
			rows[i] = row
		}(i, r)
	}
	wg.Wait()

	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	w := csv.NewWriter(f)
	defer w.Flush()
	_ = w.Write(header)
	for _, row := range rows {
		_ = w.Write(row)
	}
	return w.Error()
}
