"""Bagian akhir: Daftar Pustaka (APA, Panduan 6.2) dan Lampiran (Panduan 3.3.2, 4.14)."""
import json
import re
import sys

from ctx_id import REPO, id_angka, tabel_id
from skripsilib import SOROT_PUSTAKA

sys.path.insert(0, str(REPO / "scripts/paper"))
from part4 import REFS as REFS_JURNAL  # noqa: E402  (daftar yang sudah diaudit, reference_audit.md)

# Rujukan tambahan khusus skripsi. Seluruh rujukan skripsi terbit 2022-2026 dan terindeks Scopus:
# Tuunanen dkk. (2024) menggantikan Peffers dkk. (2007) untuk DSRM (Bab I dan III), Neupane dkk. (2023)
# menggantikan Taylor dkk. (2020) untuk deteksi kebingungan nama paket (Bab II). Tiga rujukan IEEE berbayar
# diganti dengan rujukan yang dapat diunduh gratis: Liu dkk. (2022) menggantikan Wang dkk. (2023, Plumber)
# untuk lambatnya perbaikan merambat di rantai dependensi; Ladisa dkk. (2023) menggantikan Liang dkk. (2026,
# EMPHunter) dan C. Huang dkk. (2024, DONAPI) menggantikan C. Huang dkk. (2026, Snake in the grass) untuk
# detektor paket berbahaya.
REFS_SKRIPSI = [
    "Huang, C., Wang, N., Wang, Z., Sun, S., Li, L., Chen, J., Zhao, Q., Han, J., Yang, Z., & Shi, L. (2024). "
    "DONAPI: Malicious NPM packages detector using behavior sequence knowledge mapping. In *Proceedings of the "
    "33rd USENIX Security Symposium* (pp. 3765–3782). USENIX Association. "
    "https://www.usenix.org/conference/usenixsecurity24/presentation/huang-cheng",
    "Ladisa, P., Ponta, S. E., Ronzoni, N., Martinez, M., & Barais, O. (2023). On the feasibility of "
    "cross-language detection of malicious packages in npm and PyPI. In *Proceedings of the 39th Annual Computer "
    "Security Applications Conference* (pp. 71–82). ACM. https://doi.org/10.1145/3627106.3627138",
    "Liu, C., Chen, S., Fan, L., Chen, B., Liu, Y., & Peng, X. (2022). Demystifying the vulnerability "
    "propagation and its evolution via dependency trees in the NPM ecosystem. In *Proceedings of the 44th "
    "International Conference on Software Engineering* (pp. 672–684). ACM. https://doi.org/10.1145/3510003.3510142",
    "Neupane, S., Holmes, G., Wyss, E., Davidson, D., & De Carli, L. (2023). Beyond typosquatting: An in-depth "
    "look at package confusion. In *Proceedings of the 32nd USENIX Security Symposium* (pp. 3439–3456). USENIX "
    "Association. https://www.usenix.org/conference/usenixsecurity23/presentation/neupane",
    "Tuunanen, T., Winter, R., & vom Brocke, J. (2024). Dealing with complexity in design science research: A "
    "methodology using design echelons. *MIS Quarterly*, *48*(2), 427–458. https://doi.org/10.25300/MISQ/2023/16700",
]
# Rujukan naskah jurnal yang tidak dipakai di skripsi (nama keluarga, inisial, tahun): Taylor terbit sebelum
# 2022; tiga lainnya artikel IEEE berbayar yang diganti (lihat REFS_SKRIPSI).
TIDAK_DIPAKAI = {("Taylor", "M", "2020"), ("Wang", "Y", "2023"), ("Liang", "W", "2026"), ("Huang", "C", "2026")}


def _kunci(ref):
    """(nama keluarga penulis pertama, inisial, tahun) dari entri APA."""
    fam = ref.split(",")[0].strip()
    ini = ref.split(",")[1].strip()[:1]
    year = re.search(r"\((\d{4})\)", ref).group(1)
    return fam, ini, year


def semua_rujukan():
    return [r for r in REFS_JURNAL if _kunci(r) not in TIDAK_DIPAKAI] + REFS_SKRIPSI


def nama_penulis():
    """Nama keluarga penulis pertama seluruh rujukan (untuk menyorot kutipan di teks)."""
    return [_kunci(r)[0] for r in semua_rujukan()]


def dikutip(ref, teks):
    """Apakah entri dikutip di teks, dengan pola 'Nama dkk. (2025)', '(Nama dkk., 2025)' atau 'Nama dan X (2025)'."""
    fam, ini, year = _kunci(ref)
    awal = f"{ini}. " if fam == "Huang" else ""
    return re.search(rf"{re.escape(awal + fam)}(?: dkk\.| dan [\w-]+)?,? \(?{year}", teks) is not None


def pustaka_terpakai(teks):
    refs = sorted(semua_rujukan(), key=lambda r: (_kunci(r)[0].lower(), _kunci(r)[1], _kunci(r)[2]))
    pakai = [r for r in refs if dikutip(r, teks)]
    return pakai, [r for r in refs if r not in pakai]


def cek_kutipan(teks, refs):
    """Setiap 'Nama dkk. (tahun)' di teks harus ada di Daftar Pustaka."""
    kunci = {(_kunci(r)[0], _kunci(r)[2]) for r in refs}
    hilang = set()
    for m in re.finditer(r"(?:[A-Z]\. )?([A-Z][\w-]+(?: [A-Z][\w-]+)?)(?: dkk\.| dan [A-Z][\w-]+)?,? \(?(\d{4})\b",
                         teks):
        fam, year = m.group(1), m.group(2)
        fam = fam.split()[-1] if fam not in {k[0] for k in kunci} and " " in fam else fam
        if fam in {"Januari", "Maret", "April", "September", "Oktober", "Juni", "November", "Desember", "Juli",
                   "Agustus", "Februari", "Mei", "Python", "PyPI", "Go", "OSV", "Gambar", "Tabel", "Lampiran"}:
            continue
        if any(k[0] == fam for k in kunci) and (fam, year) not in kunci:
            hilang.add(f"{fam} ({year})")
    return sorted(hilang)


def daftar_pustaka(m, teks):
    refs, tidak = pustaka_terpakai(teks)
    para = m.judul_bab_lain("Daftar Pustaka")
    for r in refs:
        m.p(r, style="Pustaka", auto_italic=False, kutipan=False, sorot=SOROT_PUSTAKA)
    m.penanda(m.doc.paragraphs[-1], "akhir_daftar_pustaka")
    tahun = sorted(int(_kunci(r)[2]) for r in refs)
    m.ref["jml:referensi"] = f"{len(refs)} ({tahun[0]}–{tahun[-1]})"
    return refs, tidak


# ====================================================================== lampiran

KODE = ["main.go", "internal/parser/parser.go", "internal/parser/requirements.go", "internal/registry/pypi.go",
        "internal/cache/cache.go", "internal/scorer/scorer.go", "internal/scorer/levenshtein.go",
        "internal/ui/prompt.go", "internal/ui/tty.go", "internal/ui/tty_linux.go", "internal/ui/tty_darwin.go",
        "internal/config/config.go", "internal/logger/logger.go", "internal/popular/popular.go",
        "scripts/install.sh", "scripts/uninstall.sh"]


def lampiran(m):
    # Lampiran A: kode program dua kolom, Courier New 10 pt, spasi tunggal (Panduan 4.14)
    m.bagian_baru("decimal", start=1, footer="A-")
    m.judul_lampiran("A", "Kode Program")
    m.p("Kode sumber pipguard di luar berkas pengujian. Repositori lengkap (termasuk pengujian, alat evaluasi, dan "
        "data beku): https://github.com/ward-00/pipguard, diarsipkan pada https://doi.org/10.5281/zenodo.23645430.",
        style="Tunggal", size=10, after=6, auto_italic=False)
    m.bagian_baru("decimal", footer="A-", cols=2, lanjut=True)
    for f in KODE:
        p = m.p(f"// {f}" if f.endswith(".go") else f"# {f}", style="Kode Program", bold=True, auto_italic=False,
                before=6)
        for line in (REPO / f).read_text().splitlines():
            para = m.doc.add_paragraph(style="Kode Program")
            para.add_run(line.replace("\t", "  ") or " ")
    # Lampiran B: probe halusinasi dan reproduksi
    m.bagian_baru("decimal", start=1, footer="B-")
    m.judul_lampiran("B", "Parameter Probe Halusinasi dan Reproduksi")
    meta = json.loads((REPO / "reproduction/Tests/multimodel/prompts_meta.json").read_text())
    s = meta["sampling"]
    m.p("**Probe halusinasi.** Pesan sistem (apa adanya dari kode asal Spracklen dkk., 2025): "
        f"\"{meta['system']}\" Pesan pengguna: \"{meta['prefix']}<prompt>\". Sampling: temperature "
        f"{id_angka(str(s['temperature']))}, top-k {s['top_k']}, top-p {id_angka(str(s['top_p']))}, paling banyak "
        f"{s['max_tokens']} token baru, seed tetap. Prompt: {meta['n_per_dataset']} per dataset asal (LLM_AT, LLM_LY, "
        "SO_AT, SO_LY), dipilih menurut urutan SHA-256 teks prompt dan sama untuk semua model. Runtime: llama.cpp "
        "pada CPU dengan berkas GGUF DeepSeek-Coder-1.3B-Instruct (Q8_0), Qwen2.5-Coder-1.5B-Instruct (Q8_0), "
        "Gemma-3-4B-it (Q4_K_M), dan Qwen3.5-4B (Q4_K_M, enable_thinking = false). Tanggal rilis yang dipakai "
        "sebagai batas klasifikasi: 1 November 2023, 19 September 2024, 12 Maret 2025, dan 2 Maret 2026. "
        "Penyimpangan dari penelitian asal: empat model kecil alih-alih 16, 500 prompt alih-alih sekitar 19.600 per "
        "model, hanya probe rekomendasi, inferensi CPU terkuantisasi, dan klasifikasi terhadap riwayat PyPI bertanda "
        "waktu alih-alih satu daftar induk. Nama diperiksa pada 24 Oktober 2026.", style="Tunggal", size=11, after=8)
    m.p("**Reproduksi.** `scripts/eval/run_all.sh` membangun ulang seluruh hasil dari `testdata/frozen/` tanpa akses "
        "jaringan; opsi `--live` menambahkan pengujian intersepsi dan pengukuran latensi, dan "
        "`scripts/eval/compare_tools.py` mengulang perbandingan alat secara langsung. Masukan daring diambil oleh "
        "`scripts/eval/build_sets.py` dan `scripts/eval/fetch_v3.py` (ekspor OSV 14 Oktober 2026; tabel metadata dan "
        "unduhan ClickPy serta API JSON PyPI, 19–24 Oktober 2026). Naskah skripsi ini dibangun oleh "
        "`scripts/skripsi/build_skripsi.py` dan gambarnya oleh `scripts/skripsi/figures_skripsi.py`.",
        style="Tunggal", size=11, after=8)
    go = (REPO / "paper/data/go_test.txt").read_text().splitlines() if (REPO / "paper/data/go_test.txt").exists() else []
    if go:
        m.p("**Keluaran pengujian unit** (`go test ./...` dan `python3 -m unittest test_pypi_history`):",
            style="Tunggal", size=11, after=4)
        for line in go:
            para = m.doc.add_paragraph(style="Kode Program")
            para.add_run(line.replace("\t", "  ") or " ")
    # Lampiran C: sensitivitas kampanye
    m.bagian_baru("decimal", start=1, footer="C-")
    m.judul_lampiran("C", "Sensitivitas Hasil Tingkat Kampanye")
    h, rows = tabel_id("t_campaign_sensitivity", ["Definisi (jendela, penghubung)", "Kampanye (semua)",
                                                  "Kampanye terbesar", "Kampanye (2026)",
                                                  "Recall 2026, bootstrap kampanye (%)",
                                                  "I-07 berbobot kampanye, < 2025 (%)",
                                                  "I-07 berbobot kampanye, 2026 (%)",
                                                  "Dihentikan, proyek 30 hr, berbobot kampanye 2026 (%)",
                                                  "Dihentikan, rilis 30 hr, berbobot kampanye 2026 (%)"],
                       {"3 d, all keys": "3 hari, semua kunci", "7 d, all keys (main)": "7 hari, semua kunci (utama)",
                        "14 d, all keys": "14 hari, semua kunci", "30 d, all keys": "30 hari, semua kunci",
                        "7 d, e-mail only": "7 hari, surel saja",
                        "7 d, e-mail or description": "7 hari, surel atau deskripsi"}, kolom_teks=(0,))
    m.tabel("Jumlah Kampanye dan Hasil Tingkat Kampanye pada Definisi Kampanye Alternatif", h, rows,
            lebar=[3.0, 1.4, 1.4, 1.4, 1.8, 1.6, 1.6, 1.9, 1.9], size=8, align=["l"] + ["r"] * 8,
            catatan="Utama = definisi yang dipakai di seluruh naskah (" + "{{sub:evaluasi}}" + "). Recall = "
                    "porsi paket berbahaya 2026 yang ditandai pipguard, interval bootstrap kampanye 95%.",
            key="lamp_kampanye")


# ====================================================================== BibTeX (Mendeley)

_APA = re.compile(
    r"^(?P<aut>.+?) \((?P<year>\d{4})\)\. (?P<title>.+?)\. "
    r"(?:In \*(?P<book>[^*]+)\* \(pp\. (?P<pp>[^)]+)\)\. (?P<pub>[^.]+)\."
    r"|\*(?P<jour>[^*]+)\*(?:, \*(?P<vol>\d+)\*(?:\((?P<iss>[^)]+)\))?)?(?:, (?P<pages>[^.]+?))?\."
    r"(?P<aop> Advance online publication\.)?) (?P<url>https?://\S+)$")
_PENULIS = re.compile(r"(?:^|, (?:& )?)([^,&]+?), ((?:[A-Z]\.(?:-[A-Z]\.)?\s?)+)")
_PENERBIT = {"10.1145": "ACM", "10.1109": "IEEE", "10.1016": "Elsevier", "10.1007": "Springer",
             "10.1002": "Wiley", "10.1038": "Springer Nature", "10.3390": "MDPI",
             "10.25300": "Management Information Systems Research Center, University of Minnesota"}


def _tex(s):
    s = s.replace("*", "")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")):
        s = s.replace(a, b)
    return s.replace("–", "--")


def bibtex(refs):
    """Entri BibTeX (UTF-8) dari entri APA; kunci NamaTahun (Huang dibedakan dengan inisial)."""
    out, kunci = [], set()
    for r in refs:
        m = _APA.match(r)
        if not m:
            raise SystemExit(f"entri APA tidak dapat diurai untuk BibTeX: {r[:80]}")
        g = m.groupdict()
        penulis = [(f.strip(), i.strip()) for f, i in _PENULIS.findall(g["aut"])]
        fam0 = penulis[0][0]
        key = re.sub(r"[^A-Za-z]", "", fam0) + (penulis[0][1][0] if fam0 == "Huang" else "") + g["year"]
        assert key not in kunci, key
        kunci.add(key)
        f = {"author": " and ".join(f"{fam}, {ini}" for fam, ini in penulis), "title": g["title"], "year": g["year"]}
        doi = re.match(r"https://doi\.org/(.+)", g["url"])
        if g["book"]:
            typ = "inproceedings"
            f.update(booktitle=g["book"], pages=g["pp"], publisher=g["pub"])
        else:
            typ = "article"
            f["journal"] = g["jour"]
            if g["vol"]:
                f["volume"] = g["vol"]
            if g["iss"]:
                f["number"] = g["iss"]
            if g["pages"]:
                f["pages"] = g["pages"]          # rentang halaman atau nomor artikel (Mendeley: pages)
            if g["aop"]:
                f["note"] = "Advance online publication"
        if doi:
            f["doi"] = doi.group(1)
            pfx = doi.group(1).split("/")[0]
            f.setdefault("publisher", _PENERBIT.get(pfx, ""))
        else:
            f["url"] = g["url"]
        badan = ",\n".join(f"  {k} = {{{_tex(v)}}}" for k, v in f.items() if v)
        out.append(f"@{typ}{{{key},\n{badan}\n}}")
    return "\n\n".join(out) + "\n"
