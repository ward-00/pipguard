package scorer

import (
	"testing"
	"time"

	"github.com/editorid0001/pipguard/internal/registry"
)

var testPopular = []string{"requests", "numpy", "flask", "django", "pandas", "psycopg", "psycopg2"}

func established() registry.Metadata {
	return registry.Metadata{
		Exists:          true,
		FirstRelease:    time.Now().AddDate(-5, 0, 0),
		ReleaseCount:    40,
		HasHomepage:     true,
		HasRepository:   true,
		Summary:         "A well established HTTP library for Python.",
		DescriptionLen:  5000,
		ClassifierCount: 12,
	}
}

func brandNewSparse() registry.Metadata {
	return registry.Metadata{Exists: true, FirstRelease: time.Now().AddDate(0, 0, -2), ReleaseCount: 1, SdistOnly: true}
}

func models() []Model { return []Model{V1(testPopular), V2(testPopular), V3(testPopular, 90)} }

func TestNotFoundIsAlwaysDanger(t *testing.T) {
	for _, m := range models() {
		r := m.Evaluate("zzz-not-registered", registry.Metadata{Exists: false})
		if r.Level != Danger || r.Score < m.Danger {
			t.Errorf("%s: expected Danger with score ≥ %d, got %v (%d)", m.Name, m.Danger, r.Level, r.Score)
		}
	}
}

func TestEstablishedIsSafe(t *testing.T) {
	for _, m := range models() {
		r := m.Evaluate("requests", established())
		if r.Level != Safe {
			t.Errorf("%s: expected Safe, got %v (score %d, reasons %v)", m.Name, r.Level, r.Score, r.Reasons)
		}
	}
}

func TestNewAndSparseFlagged(t *testing.T) {
	for _, m := range models() {
		r := m.Evaluate("some-brand-new-pkg", brandNewSparse())
		if r.Level == Safe {
			t.Errorf("%s: expected new+sparse package to be flagged, got Safe (score %d)", m.Name, r.Score)
		}
	}
}

// The initial design must stay intact in V1 so that comparisons remain valid.
func TestV1MatchesOriginalTable(t *testing.T) {
	m := V1(testPopular)
	r := m.Evaluate("some-brand-new-pkg", registry.Metadata{Exists: true, FirstRelease: time.Now(), ReleaseCount: 1})
	// I-02 40 + I-03 20 + I-04 15 + I-06 10 = 85; I-07..I-10 carry no points in V1.
	if r.Score != 85 || r.Level != Danger {
		t.Fatalf("V1 score = %d (%v), want 85 DANGER; hits %v", r.Score, r.Level, r.Hits)
	}
	if m.LevelFor(19) != Safe || m.LevelFor(20) != Warning || m.LevelFor(60) != Danger {
		t.Fatal("V1 thresholds must be 20/60")
	}
}

func TestLevenshteinAndOSA(t *testing.T) {
	cases := []struct {
		a, b     string
		lev, osa int
	}{
		{"requests", "requests", 0, 0},
		{"requests", "reqeusts", 2, 1},
		{"flask", "flsak", 2, 1},
		{"numpy", "nunpy", 1, 1},
		{"ca", "abc", 3, 3},
		{"", "abc", 3, 3},
	}
	for _, c := range cases {
		if got := levenshtein(c.a, c.b); got != c.lev {
			t.Errorf("levenshtein(%q,%q) = %d, want %d", c.a, c.b, got, c.lev)
		}
		if got := osa(c.a, c.b); got != c.osa {
			t.Errorf("osa(%q,%q) = %d, want %d", c.a, c.b, got, c.osa)
		}
	}
}

func TestSimilarityLengthFilter(t *testing.T) {
	if _, _, ok := NewSimilarity(testPopular, 6, 2, false).Match("a-very-long-name-indeed"); ok {
		t.Fatal("expected no match for a name far longer than every popular name")
	}
}

// Short names must not count as similar merely because they are within two
// edits (see testdata/ACCURACY_NOTES.md, finding 2).
func TestSimilarityShortNamesExempt(t *testing.T) {
	s := NewSimilarity(testPopular, 6, 2, false)
	for _, name := range []string{"mcp", "h2", "jedi", "py4j", "pyotp"} {
		if _, _, ok := s.Match(name); ok {
			t.Errorf("Match(%q) matched; short names must be exempt", name)
		}
	}
}

// A name on the popular list is not a typosquat of its neighbours.
func TestSimilarityPopularNamesExempt(t *testing.T) {
	if m, _, ok := NewSimilarity(testPopular, 6, 2, false).Match("psycopg"); ok {
		t.Fatalf("Match(psycopg) = %q; popular names must be exempt", m)
	}
}

func TestSimilarityTyposquatDetected(t *testing.T) {
	for _, tr := range []bool{false, true} {
		match, d, ok := NewSimilarity(testPopular, 6, 2, tr).Match("reqeusts")
		if !ok || match != "requests" {
			t.Fatalf("transpositions=%v: Match(reqeusts) = (%q,%d,%v), want requests", tr, match, d, ok)
		}
	}
	if _, _, ok := NewSimilarity(testPopular, 6, 1, false).Match("reqeusts"); ok {
		t.Error("swap is 2 Levenshtein edits; must not match with MaxDist 1")
	}
	if _, d, ok := NewSimilarity(testPopular, 6, 1, true).Match("reqeusts"); !ok || d != 1 {
		t.Error("swap is 1 OSA edit; must match with MaxDist 1 when transpositions are on")
	}
}

// Historical evaluation: ages are relative to the given "now", not the clock.
func TestEvaluateAtHistorical(t *testing.T) {
	upload := time.Date(2023, 3, 1, 0, 0, 0, 0, time.UTC)
	meta := registry.Metadata{Exists: true, FirstRelease: upload, ReleaseCount: 3, HasRepository: true,
		Summary: "Plausible looking summary"}
	m := V1(testPopular)
	if s := m.Signals("x-pkg", meta, upload.Add(24*time.Hour)); !s.Fired[RuleNew] {
		t.Fatalf("expected I-02 one day after upload, got %v", s.Fired)
	}
	if s := m.Signals("x-pkg", meta, time.Now()); s.Fired[RuleNew] {
		t.Fatalf("expected no I-02 years later, got %v", s.Fired)
	}
}

// The score must equal the sum of the recorded hits; cmd/evalset relies on
// this for the ablation.
func TestHitsSumToScore(t *testing.T) {
	meta := registry.Metadata{Exists: true, FirstRelease: time.Now(), ReleaseCount: 1, SdistOnly: true}
	for _, m := range models() {
		r := m.Evaluate("reqeusts", meta)
		sum := 0
		for _, h := range r.Hits {
			sum += h.Points
			if h.Points != m.Points[h.Rule] {
				t.Errorf("%s: hit %v has wrong points", m.Name, h)
			}
		}
		if sum != r.Score || len(r.Hits) != len(r.Reasons) {
			t.Fatalf("%s: hits %v do not match score %d / reasons %v", m.Name, r.Hits, r.Score, r.Reasons)
		}
	}
	if r := V1(testPopular).Evaluate("reqeusts", meta); len(r.Hits) != 5 {
		t.Fatalf("V1: expected I-02,I-03,I-04,I-05,I-06 to fire, got %v", r.Hits)
	}
}

func TestSignalsExtractEveryRule(t *testing.T) {
	meta := registry.Metadata{Exists: true, FirstRelease: time.Now(), ReleaseCount: 1, SdistOnly: true}
	s := V3(testPopular, 90).Signals("requets", meta, time.Now()) // one deletion from "requests"
	for _, rule := range AllRules[1:] {
		if rule == RuleReactivated {
			continue // I-10 applies only to projects older than 30 days (see TestV3Reactivated)
		}
		if !s.Fired[rule] {
			t.Errorf("expected %s to fire on an empty, new, sdist-only typosquat", rule)
		}
	}
	if s.Fired[RuleNotRegistered] {
		t.Error("I-01 must not fire for a registered package")
	}
}

// V2 behaviour: every new package requires confirmation (WARNING), a
// malicious-looking profile raises a new package to DANGER, and metadata
// alone never flags an established package.
func TestV2NewPackageIsWarnedNotDanger(t *testing.T) {
	meta := registry.Metadata{Exists: true, FirstRelease: time.Now().AddDate(0, 0, -1), ReleaseCount: 1,
		HasRepository: true, Summary: "A new but ordinary library", DescriptionLen: 1500, ClassifierCount: 5}
	if r := V2(testPopular).Evaluate("brand-new-lib", meta); r.Level != Warning {
		t.Fatalf("new, well-formed package: got %v (score %d, %v), want WARNING", r.Level, r.Score, r.Hits)
	}
}

func TestV2MaliciousProfileIsDanger(t *testing.T) {
	meta := registry.Metadata{Exists: true, FirstRelease: time.Now(), ReleaseCount: 1, SdistOnly: true,
		Summary: "Totally legit utilities", DescriptionLen: 0}
	if r := V2(testPopular).Evaluate("some-util-pkg", meta); r.Level != Danger {
		t.Fatalf("new + sdist-only + no README: got %v (score %d), want DANGER", r.Level, r.Score)
	}
}

func TestV2MetadataAloneNeverFlagsEstablished(t *testing.T) {
	for _, m := range []Model{V2(testPopular), V3(testPopular, 90)} {
		metadataAloneNeverFlags(t, m)
	}
}

func metadataAloneNeverFlags(t *testing.T, m Model) {
	sum := 0
	for _, rule := range AllRules {
		if rule != RuleNotRegistered && rule != RuleNew && rule != RuleReactivated {
			sum += m.Points[rule]
		}
	}
	if sum >= m.Warn {
		t.Fatalf("metadata points sum to %d ≥ WARNING threshold %d", sum, m.Warn)
	}
	if m.Points[RuleNew] < m.Warn || m.Points[RuleNotRegistered] < m.Danger {
		t.Fatal("I-02 alone must reach WARNING and I-01 alone must reach DANGER")
	}
	worst := registry.Metadata{Exists: true, FirstRelease: time.Now().AddDate(-3, 0, 0), ReleaseCount: 1,
		SdistOnly: true}
	if r := m.Evaluate("requets", worst); r.Level != Safe {
		t.Fatalf("established package with every metadata signal: got %v (score %d)", r.Level, r.Score)
	}
}

// I-10: a fresh release after a long silence in an older project requires
// confirmation; regular releases of active projects do not.
func TestV3Reactivated(t *testing.T) {
	now := time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC)
	base := registry.Metadata{Exists: true, FirstRelease: now.AddDate(-3, 0, 0), ReleaseCount: 12,
		HasRepository: true, Summary: "An older library", DescriptionLen: 2000, ClassifierCount: 8}
	m := V3(testPopular, 90)

	dormant := base
	dormant.LatestRelease = now.AddDate(0, 0, -2)
	dormant.PreviousRelease = dormant.LatestRelease.Add(-m.Dormancy)
	if r := m.EvaluateAt("older-lib", dormant, now); r.Level != Warning || !hasRule(r, RuleReactivated) {
		t.Fatalf("reactivated release: got %v %v, want WARNING with I-10", r.Level, r.Hits)
	}

	active := base
	active.LatestRelease = now.AddDate(0, 0, -2)
	active.PreviousRelease = active.LatestRelease.Add(-m.Dormancy + 24*time.Hour)
	if r := m.EvaluateAt("older-lib", active, now); r.Level != Safe {
		t.Fatalf("regular release: got %v %v, want SAFE", r.Level, r.Hits)
	}

	settled := dormant
	settled.LatestRelease = now.AddDate(0, 0, -31)
	settled.PreviousRelease = settled.LatestRelease.Add(-m.Dormancy)
	if r := m.EvaluateAt("older-lib", settled, now); r.Level != Safe {
		t.Fatalf("reactivation older than 30 days: got %v %v, want SAFE", r.Level, r.Hits)
	}

	if r := V2(testPopular).EvaluateAt("older-lib", dormant, now); r.Level != Safe {
		t.Fatalf("V2 has no I-10: got %v", r.Level)
	}
	if r := V3(testPopular, 0).EvaluateAt("older-lib", dormant, now); r.Level != Safe {
		t.Fatalf("V3 with dormancy 0 must not use I-10: got %v", r.Level)
	}
}

func hasRule(r Result, rule string) bool {
	for _, h := range r.Hits {
		if h.Rule == rule {
			return true
		}
	}
	return false
}
