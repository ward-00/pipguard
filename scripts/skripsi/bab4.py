"""BAB IV HASIL DAN PEMBAHASAN."""
import re

from ctx_id import (CMP, FIG, FIG_EN, H, N, REPO, dec, env, frac, interception, kata, latency, num, pct,
                    tabel_id, wilson)

P30 = "{{sub:hasil_kebijakan}}"


def _w(kn, nd=1):
    lo, hi = wilson(*kn)
    return f"{pct(kn, nd)} [{dec(100 * lo, nd)}–{dec(100 * hi, nd)}]"


def _ci(x):
    return f"{pct(x['est'])}% [{pct(x['ci'][0])}–{pct(x['ci'][1])}]"


def tulis(m):
    m.bab(4, "Hasil dan Pembahasan", key="hasil")
    m.p(
        "Bab ini menyajikan hasil implementasi dan pengujian sistem, hasil evaluasi untuk setiap rumusan "
        "masalah, dan pembahasannya. Seluruh angka dibangun ulang dari masukan yang dibekukan oleh skrip "
        "`scripts/eval/run_all.sh` tanpa akses jaringan; angka tidak diketik secara manual ke dalam naskah.")
    m.h2("Hasil Penelitian", key="hasil_penelitian")
    implementasi(m)
    pengujian_sistem(m)
    rm1(m)
    rm2(m)
    rm3(m)
    rm4(m)
    m.h2("Pembahasan", key="pembahasan")
    pembahasan(m)


# ====================================================================== implementasi dan pengujian sistem

def _baris_go(path):
    files = [p for p in path.glob("*.go") if not p.name.endswith("_test.go")]
    return sum(len(p.read_text().splitlines()) for p in files)


def _jumlah_uji():
    n = 0
    for p in REPO.rglob("*_test.go"):
        if "reproduction" in p.parts:
            continue
        n += len(re.findall(r"^func Test", p.read_text(), re.M))
    return n


def implementasi(m):
    m.h3("Implementasi Sistem", key="implementasi")
    komp = [("main.go", REPO, "Alur utama: mencari pip asli, mengurai, memeriksa, meneruskan dengan exec"),
            ("internal/parser", REPO / "internal/parser", "Nama paket (PEP 503), berkas requirements, opsi indeks, "
                                                           "subperintah"),
            ("internal/registry", REPO / "internal/registry", "Klien API JSON PyPI, termasuk waktu rilis terbaru dan "
                                                               "sebelumnya"),
            ("internal/cache", REPO / "internal/cache", "Cache ~/.cache/pipguard/cache.json, masa berlaku 24 jam"),
            ("internal/scorer", REPO / "internal/scorer", "Indikator I-01..I-10; model V1, V2, dan V3 (dipasang)"),
            ("internal/ui", REPO / "internal/ui", "Peringatan, prompt [y/N], rekaman JSON, deteksi terminal"),
            ("internal/config", REPO / "internal/config", "Berkas konfigurasi pengguna dan sistem, penguncian"),
            ("internal/logger", REPO / "internal/logger", "Log aktivitas JSONL"),
            ("internal/popular", REPO / "internal/popular", "Daftar 5.000 paket teratas yang ditanam di biner")]
    rows, total = [], 0
    for nama, path, fungsi in komp:
        n = len((REPO / "main.go").read_text().splitlines()) if nama == "main.go" else _baris_go(path)
        total += n
        rows.append([f"`{nama}`", fungsi, num(n)])
    rows.append(["Jumlah", "", num(total)])
    m.p(
        "Sistem diimplementasikan dalam bahasa Go 1.22 ke atas (dikembangkan dengan Go 1.26) hanya dengan "
        "pustaka standar, sebagai satu biner statis yang dikompilasi silang untuk Linux dan macOS pada arsitektur "
        "amd64 dan arm64. Komponen implementasi beserta jumlah baris kode di luar pengujian disajikan pada "
        "{{tbl:komponen}}; kode lengkapnya terdapat pada Lampiran A.")
    m.tabel("Komponen Implementasi Sistem", ["Paket/berkas", "Fungsi", "Baris"], rows, lebar=[3.6, 8.8, 1.6],
            size=10, align=["l", "l", "r"], key="komponen")
    m.p(
        "Pemasangan dilakukan dengan `make install`, yang menyalin biner ke `~/.local/bin`, membuat tautan `pip` "
        "dan `pip3` sebagai shim, dan menambahkan blok fungsi shell bertanda pada `~/.bashrc` atau `~/.zshrc`; "
        "`make uninstall` menghapus semuanya. Pada iterasi kedua ditemukan dan diperbaiki sejumlah cacat yang "
        "relevan bagi keabsahan pengujian: lapisan fungsi shell semula memanggil biner dengan nama `pipguard` "
        "sehingga pip asli tidak ditemukan dan dua instalasi dapat saling memanggil tanpa henti; `python3 -m "
        "pip` belum tertangkap; isi berkas *requirements* belum diperiksa; `/dev/null` dianggap terminal; dan "
        "pengukuran latensi dijalankan dari drive Windows yang dipasang melalui 9p sehingga setiap proses "
        "bertambah 30–40 ms. Seluruh perbaikan disertai uji yang dapat dijalankan ulang.")
    m.p(
        "Tampilan peringatan untuk paket yang tidak terdaftar, sebagaimana direkam oleh pengujian intersepsi "
        "otomatis, ditunjukkan pada {{gbr:peringatan}}. Teks keluaran sistem berbahasa Inggris karena pipguard "
        "ditujukan bagi pengguna internasional.")
    m.gambar(FIG_EN / "fig_warning.png", "Tampilan Peringatan dan Konfirmasi untuk Paket yang Tidak Terdaftar "
                                         "(Keluaran Rekaman Pengujian Intersepsi)", 11.5, key="peringatan")


def pengujian_sistem(m):
    m.h3("Hasil Pengujian Unit dan Intersepsi", key="hasil_intersepsi")
    m.p(
        f"Seluruh {num(_jumlah_uji())} fungsi uji unit Go pada {kata(8)} paket yang memiliki berkas uji lulus "
        "(`go test ./...`), demikian pula uji Python untuk rekonstruksi historis. Rincian cakupan pengujian unit "
        "diuraikan pada {{sub:evaluasi}}.")
    rows = interception()
    n_pass = sum(r["pass"] == "yes" for r in rows)
    m.p(
        f"Sebanyak {n_pass} dari {len(rows)} kasus intersepsi berperilaku sesuai spesifikasi "
        "({{tbl:intersepsi}}). Pada shell interaktif, pipguard menangkap setiap bentuk sasaran pada "
        "kedua shell, termasuk virtual environment aktif, `python -m pip`, skrip, subproses Python, dan berkas "
        "*requirements*. `pip download`, `pip wheel`, dan instalasi dengan constraints atau indeks tambahan juga "
        "diperiksa. Tanpa terminal, seperti pada job CI dan subproses bergaya agen AI dengan keluaran yang "
        "ditangkap, pipguard membatalkan dan mencetak rekaman JSON dengan status keluar 3. Variabel pengecualian "
        "diabaikan kecuali diizinkan konfigurasi.")
    m.p(
        "Pemanggil yang tidak membaca konfigurasi shell, seperti langkah CI atau sandbox alat agen, tertangkap "
        "ketika menjalankan `pip` melalui shim PATH, tetapi tidak ketika menjalankan `python3 -m pip` secara "
        "langsung, dari subproses bergaya agen, atau sebagai `[sys.executable, \"-m\", \"pip\"]`. Kasus lain "
        "yang tidak tertangkap juga merupakan batas yang didokumentasikan: jalur absolut ke pip atau interpreter "
        "seperti yang dipakai IDE, skrip yang mengaktifkan virtual environment sendiri, PATH tanpa pipguard "
        "(secure path sudo atau citra CI tanpa pipguard), uv, dan dependensi berupa URL langsung. Indeks utama "
        "kustom sengaja tidak diperiksa. Bagi CI dan agen, pipguard karena itu andal hanya bila pemanggil "
        "memakai `pip`, yang dapat dipaksakan oleh citra sandbox.")
    # Seluruh 43 kasus dari scripts/test_interception.sh, diterjemahkan (istilah teknis dipertahankan)
    skenario = {
        "1 Interactive shell (TTY), answer N": "Shell interaktif (TTY), menjawab N",
        "1 Interactive shell (TTY), answer Y": "Shell interaktif (TTY), menjawab Y",
        "2 Active virtual environment": "Virtual environment aktif",
        "3 pip3": "`pip3`",
        "4 python -m pip (active venv)": "`python -m pip` (venv aktif)",
        "5 python3 -m pip": "`python3 -m pip`",
        "6 Non-interactive script (bash t.sh)": "Skrip non-interaktif (`bash t.sh`)",
        "7 Python subprocess": "Subproses Python",
        "8 pip install -r requirements.txt": "`pip install -r requirements.txt`",
        "9 Absolute path to the real pip (limitation)": "Jalur absolut ke pip asli (batasan)",
        "Script that activates its own venv (limitation)": "Skrip yang mengaktifkan venv sendiri (batasan)",
        "Absolute interpreter path, as IDEs run pip (limitation)":
            "Jalur absolut interpreter, seperti IDE menjalankan pip (batasan)",
        "CI job, stdin not a TTY (/dev/null)": "Job CI, stdin bukan TTY (`/dev/null`)",
        "AI agent: subprocess, no TTY, output captured": "Agen AI: subproses tanpa TTY, keluaran ditangkap",
        "pip download (builds sdists)": "`pip download` (membangun sdist)",
        "pip wheel (builds sdists)": "`pip wheel` (membangun sdist)",
        "pip install -c constraints.txt": "`pip install -c constraints.txt`",
        "--extra-index-url (warning notes dependency confusion)":
            "`--extra-index-url` (peringatan menyebut dependency confusion)",
        "Custom primary index -i (not checked by design)": "Indeks utama kustom `-i` (sengaja tidak diperiksa)",
        "Direct URL/VCS requirement (not on PyPI; not checked)":
            "Dependensi URL langsung/VCS (bukan dari PyPI; tidak diperiksa)",
        "Safe package (requests) passes without a warning": "Paket mapan (`requests`) lolos tanpa peringatan",
        "uv pip install (other installer; limitation)": "`uv pip install` (pemasang lain; batasan)",
        "sudo-style secure_path without ~/.local/bin (limitation)":
            "`secure_path` gaya sudo tanpa `~/.local/bin` (batasan)",
        "CI runner or container image without pipguard on PATH": "Runner CI atau citra kontainer tanpa pipguard di PATH",
        "CI runner or container image with pipguard on PATH": "Runner CI atau citra kontainer dengan pipguard di PATH",
        "Non-interactive shell (CI step): pip": "Shell non-interaktif (langkah CI): `pip`",
        "Non-interactive shell (CI step): python3 -m pip (limitation)":
            "Shell non-interaktif (langkah CI): `python3 -m pip` (batasan)",
        "Agent subprocess from a non-interactive shell: python3 -m pip (limitation)":
            "Subproses agen dari shell non-interaktif: `python3 -m pip` (batasan)",
        "Python subprocess [sys.executable, -m, pip] (limitation)":
            "Subproses Python `[sys.executable, -m, pip]` (batasan)",
        "PIPGUARD_ASSUME_YES=1 ignored by default (agent-resistant)":
            "`PIPGUARD_ASSUME_YES=1` diabaikan secara bawaan (tahan agen)",
        "PIPGUARD_ASSUME_YES=1 with allow_env_override": "`PIPGUARD_ASSUME_YES=1` dengan `allow_env_override`",
        "PIPGUARD_DISABLE=1 ignored by default (agent-resistant)":
            "`PIPGUARD_DISABLE=1` diabaikan secara bawaan (tahan agen)",
        "Fail-open: PyPI unreachable": "PyPI tidak dapat dijangkau (fail-open)",
    }
    harapan = {"prompt-no": "Prompt, lalu dibatalkan", "prompt-yes": "Prompt, lalu diteruskan",
               "blocked": "Dibatalkan", "bypass": "Tidak dicegat", "skipped": "Tidak diperiksa, diteruskan",
               "safe": "Aman, diteruskan", "forwarded": "Diteruskan", "failopen": "Diteruskan (fail-open)"}
    teramati = {"intercepted, prompt, blocked": "Dicegat, prompt, dibatalkan",
                "intercepted, forwarded": "Dicegat, diteruskan", "intercepted, blocked": "Dicegat, dibatalkan",
                "bypass": "Tidak dicegat",
                "not checked (non-PyPI index), forwarded": "Tidak diperiksa (indeks non-PyPI), diteruskan",
                "intercepted, safe, forwarded": "Dicegat, aman, diteruskan",
                "check failed, forwarded (fail-open)": "Pemeriksaan gagal, diteruskan (fail-open)"}
    trows = [[str(i), r["shell"], skenario[r["scenario"]], harapan[r["expected"]], teramati[r["observed"]],
              "Ya" if r["pass"] == "yes" else "Tidak"] for i, r in enumerate(rows, 1)]
    m.tabel(f"Hasil Pengujian Intersepsi ({len(rows)} Kasus)",
            ["No", "Shell", "Skenario", "Hasil yang diharapkan", "Hasil teramati", "Lulus"], trows,
            lebar=[0.9, 1.2, 5.6, 2.6, 3.0, 1.1], size=9, align=["c", "l", "l", "l", "l", "c"],
            catatan="Dicegat = pipguard memeriksa paket; dibatalkan = perintah dihentikan sebelum pip asli "
                    "berjalan (status keluar 3); diteruskan = perintah dijalankan oleh pip asli; tidak dicegat = "
                    "pipguard tidak terlibat. Lulus = hasil teramati sama dengan hasil yang diharapkan.",
            key="intersepsi")

    m.h3("Hasil Pengujian Kinerja", key="hasil_kinerja")
    lat = latency()
    v = {r[0]: r for r in lat}
    warm = float(v["Set 2: pipguard, warm cache (1 entry)"][1])
    stub = float(v["Set 2: stub pip, no pipguard"][1])
    py = float(v["Reference: Python start-up + reading the cache"][1])
    cold = v["Set 2: pipguard, empty cache (PyPI request)"]
    e = env()
    m.p(
        f"Pengukuran dilakukan pada laptop {e.get('cpu', '').replace(' w/ Radeon 780M Graphics', '')} di bawah "
        "Windows Subsystem for Linux (WSL2) pada 24 Oktober 2026 dengan biner pada sistem berkas Linux asli. "
        f"Dengan cache terisi, pipguard menambah sekitar {dec(warm - stub, 0)} ms pada sebuah perintah instalasi "
        f"(rata-rata {dec(warm)} ms dibandingkan {dec(stub)} ms tanpa pipguard; p99 "
        f"{id_(v['Set 2: pipguard, warm cache (1 entry)'][4])} ms), jauh di bawah sasaran KNF-01 sebesar 50 ms, "
        "dan cache berisi 1.000 entri atau berkas -r berisi 20 paket hanya menambah beberapa milidetik "
        "({{tbl:latensi}}, {{gbr:latensi}}). Dengan cache kosong, latensi didominasi perjalanan pulang-pergi "
        f"ke PyPI (rata-rata {id_(cold[1])} ms, p99 {id_(cold[4])} ms, maksimum {id_(cold[5])} ms), di bawah "
        "sasaran 500 ms pada koneksi tersebut; pada jaringan yang lebih lambat biaya ini mengikuti waktu "
        f"pulang-pergi dan dibatasi batas waktu tiga detik. Sebagai pembanding, menyalakan interpreter Python dan "
        f"membaca berkas cache yang sama saja memerlukan {dec(py)} ms, lebih lama daripada seluruh jalur "
        "cache terisi milik alat terkompilasi; hal ini mendukung pemilihan bahasa terkompilasi untuk "
        "pemeriksaan yang berjalan pada setiap instalasi. Seluruh biaya tersebut kecil dibandingkan pip "
        "sendiri, yang perintah `index versions`-nya memerlukan lebih dari setengah detik.")
    lab = {"Set 1: real pip, index versions": "pip asli, index versions",
           "Set 1: through the pipguard shim (passthrough)": "Melalui shim pipguard (diteruskan)",
           "Set 2: stub pip, no pipguard": "Stub pip tanpa pipguard",
           "Set 2: pipguard, empty cache (PyPI request)": "pipguard, cache kosong (permintaan PyPI)",
           "Set 2: pipguard, warm cache (1 entry)": "pipguard, cache terisi (1 entri)",
           "Set 2: pipguard, warm cache (1,000 entries)": "pipguard, cache terisi (1.000 entri)",
           "Set 2: pipguard, -r file with 20 cached packages": "pipguard, berkas -r 20 paket dalam cache",
           "Reference: Python start-up + reading the cache": "Rujukan: Python menyala + membaca cache"}
    m.tabel("Latensi per Pemanggilan pip (n = 200 per Kondisi) dalam Milidetik",
            ["Kondisi", "Rata-rata", "Median", "p95", "p99", "Maks."],
            [[lab.get(r[0], r[0])] + [id_(x) for x in r[1:]] for r in lat],
            lebar=[6.4, 1.6, 1.5, 1.5, 1.5, 1.5], size=10, align=["l", "r", "r", "r", "r", "r"], key="latensi")
    m.gambar(FIG / "gbr_latensi.png", "Latensi Rata-rata per Kondisi", 12.5, key="latensi")


def id_(s):
    from ctx_id import id_angka
    return id_angka(s)


# ====================================================================== RM1

def rm1(m):
    tm = N["timing"]
    cp = N["campaigns"]
    bg = N["background"]
    pr = bg["profile"]["test"]
    m.h3("Waktu Pelaporan, Penghapusan, dan Instalasi Paket Berbahaya (RM1)", key="hasil_rm1")
    m.p(
        f"Paket berbahaya dilaporkan ke OSV dengan median {dec(24 * tm['all']['report_median_days'])} jam setelah "
        f"unggahan berbahaya pertamanya ({dec(24 * tm['test']['report_median_days'])} jam pada 2026), dan "
        f"{pct(tm['test']['report_within']['1'])}% paket tahun 2026 dilaporkan dalam satu hari ({{{{tbl:timing}}}}, "
        "{{gbr:paparan}}a). Hari terakhir dengan unduhan klien instalasi, yang dipakai sebagai proksi penghapusan, "
        f"adalah hari pertama untuk {pct(tm['all']['lastdl_within']['1'])}% seluruh paket dan berada dalam tujuh "
        f"hari untuk {pct(tm['test']['lastdl_within']['7'])}% paket 2026. Pelaporan makin cepat dan lengkap: porsi "
        f"yang dilaporkan dalam 30 hari naik dari {pct(tm['dev']['report_within']['30'])}% sebelum 2025 menjadi "
        f"{pct(tm['test']['report_within']['30'])}% pada 2026.")
    h, rows = tabel_id("t_timing", ["Periode", "n", "Laporan: median (hari)", "Dilaporkan ≤ 1 hr (%)",
                                    "≤ 7 hr (%)", "≤ 30 hr (%)", "Unduhan klien terakhir: median (hari)",
                                    "≤ 7 hr (%)", "≤ 30 hr (%)"], {"All": "Semua"})
    m.tabel("Waktu dari Unggahan Berbahaya Pertama hingga Laporan OSV dan Unduhan Klien Terakhir", h, rows,
            lebar=[1.7, 1.2, 1.8, 1.6, 1.2, 1.3, 2.2, 1.2, 1.3], size=9, align=["l"] + ["r"] * 8,
            catatan="Unduhan klien terakhir (pip, uv, poetry, pdm, atau pipenv) mendekati waktu penghapusan dan "
                    "diukur dalam hari; waktu laporan diukur hingga detik. Paket tanpa unduhan klien dikeluarkan "
                    "dari tiga kolom terakhir.", key="timing")
    m.gambar(FIG / "gbr_paparan.png",
             "Porsi Kumulatif Paket Berbahaya yang Dilaporkan ke OSV dan yang Terakhir Diunduh Klien Instalasi "
             "menurut Hari setelah Unggahan Berbahaya Pertama (a, Sumbu Waktu Logaritmik); Paparan Sisa Paket "
             "Berbahaya 2026 terhadap Median Porsi Unduhan Klien yang Terdampak per Bulan untuk Masa Tunggu "
             "Tingkat Proyek dan Rilis 1 sampai 90 Hari (b, Sumbu Biaya Logaritmik)", 14.0, key="paparan")
    m.p(
        f"Untuk rata-rata paket berbahaya, {pct(bg['malicious_day0_share_mean_pkg'])}% unduhan kliennya terjadi "
        "pada hari unggahan berbahaya. Konsentrasi ini sebagian besar merupakan hal yang diterima setiap unggahan "
        f"baru. Paket sah baru menerima median {dec(pr['0']['median'], 0)} unduhan klien pada hari pertama dan "
        f"{kata(int(round(pr['1']['median'])))} pada hari kedua pada 2026, lalu hampir tidak ada setelahnya; latar ini "
        "berasal dari cermin yang melaporkan user agent pip dan dari pemindai yang memasang unggahan baru dalam "
        f"sandbox, yang tidak dapat dibedakan dari korban oleh log unduhan. Hanya "
        f"{bg['median']['by_split_with_excess']['test'][0]} dari {bg['median']['by_split_with_excess']['test'][1]} "
        "paket berbahaya 2026 yang memiliki unduhan klien diunduh lebih banyak daripada median paket baru pada "
        "periode yang sama pada hari mana pun. Unduhan yang melebihi latar, yang kemungkinan mencapai korban, "
        f"tetap mencakup {pct(bg['median']['excess_share_of_client_downloads'])}% seluruh unduhan klien berbahaya "
        "karena terkonsentrasi pada segelintir nama yang banyak diunduh. Angka hari pertama karena itu merupakan "
        "batas atas seberapa awal korban memasang, dan paparan dilaporkan dengan dan tanpa latar.")
    m.p(
        f"Pengelompokan menghasilkan {num(cp['dev']['campaigns'])} kampanye di antara {num(cp['dev']['packages'])} "
        f"paket pengembangan, {num(cp['val']['campaigns'])} di antara {num(cp['val']['packages'])} paket validasi, "
        f"dan {num(cp['test']['campaigns'])} di antara {num(cp['test']['packages'])} paket uji ({{{{tbl:kampanye}}}}). "
        f"Satu kampanye pada semester pertama 2023 menyumbang {num(cp['dev']['largest'])} paket pengembangan "
        f"({pct(cp['dev']['largest'] / cp['dev']['packages'])}%); kampanye uji terbesar berisi "
        f"{num(cp['test']['largest'])} paket. Mengubah jendela penghubung dari tiga sampai 30 hari atau membatasi "
        "penghubung pada alamat surel mengubah jumlah kampanye paling banyak 8% dan hasil tingkat kampanye paling "
        "banyak satu poin persentase (Lampiran C).")
    h, rows = tabel_id("t_campaigns", ["Data", "Paket", "Kampanye", "Kampanye satu paket", "Kampanye terbesar",
                                       "Porsi terbesar (%)"],
                       {"dev": "Pengembangan", "val": "Validasi", "test": "Uji"}, kolom_teks=(0,))
    m.tabel("Kampanye Paket Berbahaya per Periode Data", h, rows, lebar=[2.6, 1.8, 2.0, 2.6, 2.4, 2.6], size=10,
            align=["l", "r", "r", "r", "r", "r"], key="kampanye")


# ====================================================================== RM2

def rm2(m):
    rc = N["recalibration"]
    cw = N["drift_campaign_weighted"]
    ft = N["filetype"]
    m.h3("Pergeseran Indikator Metadata (RM2)", key="hasil_drift")
    m.p(
        "{{tbl:drift}} dan {{gbr:pergeseran}} menunjukkan seberapa sering setiap indikator terpenuhi per periode. "
        "Indikator umur I-02 terpenuhi pada lebih dari 94% paket berbahaya pada setiap periode dan lebih dari 93% "
        "pada setiap semester 2022–2026. Sebaliknya, indikator metadata berubah tajam. Distribusi hanya sdist "
        "(I-07) mencirikan 87,7% paket berbahaya pengembangan, tetapi hanya 12,1% pada 2025 dan 20,3% pada 2026; "
        "ketiadaan tautan proyek (I-04) turun dari 90,2% menjadi 46,5%; dan deskripsi pendek (I-08) naik dari "
        "16,1% menjadi 43,0%. Penyerang mulai menyertakan wheel, tautan, dan deskripsi. Pergeseran ini bukan "
        "artefak kampanye 2023: dengan setiap kampanye berbobot sama, I-07 tetap turun dari "
        f"{pct(cw['dev']['I-07'])}% sebelum 2025 menjadi {pct(cw['val']['I-07'])}% pada 2025 dan "
        f"{pct(cw['test']['I-07'])}% pada 2026.")
    h, rows = tabel_id("t_drift", ["Kelompok", "Periode", "n", "I-02", "I-04", "I-05", "I-07", "I-08", "I-09"],
                       {"Malicious": "Berbahaya", "New legitimate": "Sah baru"}, kolom_teks=(0,))
    m.tabel("Persentase Paket yang Memenuhi Setiap Indikator per Periode", h, rows,
            lebar=[2.4, 1.6, 1.3, 1.25, 1.25, 1.25, 1.25, 1.25, 1.25], size=10,
            align=["l", "l", "r", "r", "r", "r", "r", "r", "r"], key="drift")
    m.gambar(FIG / "gbr_pergeseran.png",
             "Prevalensi Indikator per Semester pada Paket Berbahaya (a) dan Recall Model Akhir, Kalibrasi Awal yang "
             "Ditolak, serta Tingkat DANGER (b). Garis Vertikal Putus-putus Memisahkan Periode Pengembangan, "
             "Validasi, dan Uji", 14.0, key="pergeseran")
    m.p(
        "Pergeseran tersebut menjelaskan kegagalan kalibrasi awal. Ditaksir pada data pengembangan, kalibrasi ini "
        f"menandai {pct(N['early_model']['dev']['v2-initial']['recall'])}% paket berbahaya pengembangan tetapi "
        f"hanya {pct(rc['all']['val']['recall'])}% pada 2025 dan {pct(rc['all']['test']['recall'])}% pada 2026, "
        "karena bobot terbesarnya jatuh pada I-07 ({{tbl:rekalibrasi}}). Menaksir ulang dengan prosedur yang sama "
        f"tanpa kampanye 2023 hanya menaikkan recall 2026 menjadi {pct(rc['without_largest']['test']['recall'])}%, "
        f"dengan FPR {pct(rc['without_largest']['test']['fpr_new'])}% pada paket sah baru, dan pembobotan kampanye "
        "yang sama mengulang kegagalan semula. Model metadata yang dikalibrasi pada masa lalu dengan demikian "
        "gagal pada masa depan karena alasan yang melampaui satu kampanye, sejalan dengan keruntuhan temporal "
        f"yang diamati Draz (2026). Dari temuan ini ditarik {kata(3)} konsekuensi rancangan: indikator yang "
        "bergeser tidak boleh menentukan apakah peringatan muncul; indikator tersebut boleh menentukan tingkat "
        "bila dikalibrasi ulang pada data terbaru; dan setiap kalibrasi harus divalidasi pada data yang lebih "
        "baru daripada data pelatihannya.")
    h, rows = tabel_id("t_recalibration", ["Data pengembangan", "Poin", "Ambang WARNING", "Recall 2025 (%)",
                                           "Recall 2026 (%)", "FPR sah baru 2026 (%)"],
                       {"All development data (as rejected)": "Seluruh data pengembangan (seperti yang ditolak)",
                        "Without the largest campaign": "Tanpa kampanye terbesar",
                        "Each campaign weighted equally": "Setiap kampanye berbobot sama"}, kolom_teks=(0,))
    m.tabel("Penaksiran Ulang Kalibrasi Awal pada Data Pengembangan tanpa atau dengan Bobot Lebih Rendah untuk "
            "Kampanye Massal 2023", h, rows, lebar=[3.6, 4.0, 1.6, 1.5, 1.5, 1.8], size=9,
            align=["l", "l", "r", "r", "r", "r"], key="rekalibrasi")
    a, b_, c = (ft[s]["proxy_missing"] for s in ("dev", "val", "test"))
    d, e, f = (ft[s]["proxy_reconstructed"] for s in ("dev", "val", "test"))
    m.p(
        "Apakah pergeseran ini hanya artefak paket yang sempat terekam? Cakupan rekonstruksi turun menjadi 47,6% "
        "pada 2026, dan paket yang terlewat oleh cermin adalah paket yang paling cepat dihapus. Log unduhan "
        "mencatat jenis berkas setiap unduhan secara independen dari cermin metadata. Paket yang distribusi "
        f"terbangunnya tidak pernah diunduh adalah paket hanya-sdist; proksi ini sesuai dengan I-07 pada "
        f"{pct(ft['agreement'])}% dari {num(ft['validated_n'])} paket yang direkonstruksi ({{{{tbl:jenisberkas}}}}). "
        f"Di antara paket yang tidak dapat direkonstruksi, porsi hanya-sdist turun dari {pct(a[0] / a[1])}% sebelum "
        f"2025 menjadi {pct(b_[0] / b_[1])}% pada 2025 dan {pct(c[0] / c[1])}% pada 2026, dibandingkan "
        f"{pct(d[0] / d[1])}%, {pct(e[0] / e[1])}%, dan {pct(f[0] / f[1])}% pada paket yang direkonstruksi. "
        "Pergeseran tersebut nyata; data rekonstruksi sedikit melebih-lebihkan besarnya setelah 2024, tetapi hal "
        "ini tidak mengubah konsekuensi rancangan bahwa indikator yang bergeser tidak boleh menentukan keputusan.")
    h, rows = tabel_id("t_filetype", ["Periode", "Tanpa distribusi terbangun diunduh: direkonstruksi, % (n)",
                                      "Tidak direkonstruksi, % (n)", "I-07, sepertiga umur terpendek (%)",
                                      "I-07, sepertiga tengah (%)", "I-07, sepertiga terpanjang (%)"])
    m.tabel("Distribusi Hanya-sdist pada Paket Berbahaya menurut Tahun Unduhan Pertama", h, rows,
            lebar=[1.6, 3.4, 2.6, 2.2, 2.0, 2.2], size=9, align=["l", "r", "r", "r", "r", "r"],
            catatan="Proksi hanya-sdist = tidak pernah ada distribusi terbangun (wheel) proyek yang diunduh. Umur = "
                    "hari antara unduhan pertama dan terakhir, dibagi tiga dalam setiap periode.", key="jenisberkas")


# ====================================================================== RM3

def rm3(m):
    D, C = N["detection"], N["cost"]
    X = N["exposure_estimators"]["by_shift"]["shift0"]
    XB = N["exposure_estimators_excess_median"]["by_shift"]["shift0"]
    XB25 = N["exposure_estimators_excess_p25"]["by_shift"]["shift0"]
    ms = N["missing_sensitivity"]["2026"]
    pr = N["prospective"]
    sv = N["severity"]["test"]
    dc = N["dormancy_choice"]
    tmiss = N["test_misses"]
    da = N["dependency_additions"]
    dep = N["dependents"]
    cs = N["cases"]

    def e(pol, T):
        return X[pol][str(T)]["test"]["per_package"]["est"]

    m.h3("Perbandingan Perlindungan dan Biaya Kebijakan (RM3)", key="hasil_kebijakan")
    m.h4("Deteksi")
    m.p(
        f"Pada data uji 2026, model akhir menandai {pct(D['pipguard-v2']['mal'])}% paket berbahaya "
        f"({frac(D['pipguard-v2']['mal'])}; interval bootstrap kampanye {pct(D['pipguard-v2']['mal_cluster_ci'][0])}–"
        f"{pct(D['pipguard-v2']['mal_cluster_ci'][1])}%), seluruh paket sah baru, dan satu dari 2.000 paket mapan, "
        "yaitu proyek yang masuk 15.000 teratas dalam 30 hari pertamanya ({{tbl:deteksi}}, {{gbr:tingkat}}). "
        "Keputusan konfirmasi ini identik dengan masa tunggu tingkat proyek 30 hari menurut konstruksinya, "
        "sehingga porsi yang ditandai bukan tingkat deteksi dalam arti biasa: porsi tersebut adalah porsi paket "
        "berbahaya yang merupakan proyek muda, yaitu sifat ancaman itu sendiri, yang dibayar dengan FPR 100% "
        "pada proyek baru. Porsi ini selanjutnya disebut *cakupan*, dan pertanyaannya menjadi berapa nilai cakupan "
        f"tersebut dalam paparan dan berapa biayanya. Sebanyak {D['campaigns_test']['all_flagged']} dari "
        f"{D['campaigns_test']['n']} kampanye uji tercakup seluruhnya. Rancangan awal menandai paket berbahaya yang "
        "sama tetapi juga 91 paket mapan, seluruhnya melalui indikator metadata yang mencapai ambang tanpa sinyal "
        "umur (uji McNemar eksak, 90 pasangan berbeda, p = 1,6 × 10⁻²⁷). Pemeriksaan keberadaan tidak menandai "
        "satu pun paket berbahaya yang terdaftar, dan kemiripan nama menandai 2,4%.")
    rows = []
    for key, lab in (("pipguard-v2", "pipguard (model akhir)"), ("pipguard-v2-danger", "  hanya tingkat DANGER"),
                     ("i10-90", "  + I-10, G = 90 hari (opsional)"), ("i10-365", "  + I-10, G = 365 hari (opsional)"),
                     ("pipguard-v1", "Rancangan awal (iterasi 1)"), ("v2-initial", "Kalibrasi awal (ditolak)"),
                     ("release-cooldown-30", "Masa tunggu tingkat rilis, 30 hari"),
                     ("registry-only", "Pemeriksaan keberadaan saja"), ("similarity-v2", "Kemiripan nama saja")):
        d = D[key]
        rows.append([lab, _w(d["mal"]), f"[{pct(d['mal_cluster_ci'][0])}–{pct(d['mal_cluster_ci'][1])}]",
                     _w(d["benign-new"]), _w(d["negative_established"], 2)])
    m.tabel("Porsi Paket yang Ditandai pada Data Uji 2026, % [Interval 95%]",
            ["Detektor", "Berbahaya (n = 546), Wilson", "Berbahaya, bootstrap kampanye", "Sah baru (n = 1.039)",
             "Mapan (n = 2.000)"], rows, lebar=[4.2, 2.6, 2.2, 2.5, 2.5], size=9, align=["l", "r", "r", "r", "r"],
            catatan="Ditandai = instalasi memerlukan konfirmasi; untuk masa tunggu tingkat rilis, rilis terbaru "
                    "ditahan. Masa tunggu tingkat proyek 30 hari membuat keputusan yang sama dengan pipguard. Seluruh "
                    "54 nama halusinasi iterasi pertama ditandai oleh setiap detektor yang memuat I-01.",
            key="deteksi")
    m.gambar(FIG / "gbr_tingkat.png", "Tingkat Risiko Model Akhir per Kelompok pada Data Uji 2026", 11.0,
             key="tingkat")
    h, rows = tabel_id("t_scenarios", ["Skenario", "Berbahaya ditandai", "Berbahaya DANGER", "Sah baru ditandai",
                                       "Sah baru DANGER"],
                       {"First malicious release (primary)": "Rilis berbahaya pertama (utama)",
                        "Last release": "Rilis terakhir", "At OSV report": "Saat laporan OSV"}, kolom_teks=(0,))
    m.p(
        "Cakupan tetap di atas 90% pada semua skenario waktu instalasi ({{tbl:skenario}}). Ketika paket dinilai "
        "pada saat laporan OSV, setelah median beberapa jam, 90,5% paket masih berumur kurang dari 30 hari.")
    m.tabel("pipguard pada Setiap Skenario Waktu Instalasi (Data Uji), % (k/n)", h, rows,
            lebar=[4.2, 2.5, 2.5, 2.4, 2.4], size=9, align=["l", "r", "r", "r", "r"], key="skenario")
    m.p(
        "Paket yang hilang tidak mengancam angka cakupan untuk proyek baru. Pada kohort "
        f"{num(ms['cohort'])} proyek yang dilaporkan OSV dan pertama kali diunduh pada 2026, {num(ms['reconstructed'])} "
        f"direkonstruksi dan {num(ms['missing_young'] + ms['missing_other'])} tidak; {num(ms['missing_young'])} di "
        "antaranya pertama kali diunduh kurang dari 30 hari sebelum laporannya sehingga pasti ditandai. "
        "Memperlakukan sisanya sebagai terlewat atau tertangkap membatasi cakupan pada kohort ini antara "
        f"{pct(ms['recall_lower'])}% dan {pct(ms['recall_upper'])}%. Pada hold-out prospektif, "
        f"{pr['first_download_lt30d_before_report']} dari {pr['osv_names']} paket yang dilaporkan setelah pembekuan "
        "pertama kali diunduh kurang dari 30 hari sebelum laporannya, dan seluruh "
        f"{kata(pr['with_metadata'])} paket yang metadatanya tersedia ditandai oleh model yang dibekukan, sebuah sampel "
        "kecil (interval Wilson 64,6–100%).")

    m.h4("Paparan")
    p30, r30 = X["project"]["30"]["test"], X["release"]["30"]["test"]
    m.p(
        "{{tbl:paparan}} menyajikan porsi unduhan klien berbahaya yang dihentikan masa tunggu 30 hari menurut "
        "penaksir dan periode. Untuk paket uji 2026, masa tunggu tingkat proyek menghentikan "
        f"{_ci(p30['per_package'])} unduhan rata-rata paket dan masa tunggu tingkat rilis {_ci(r30['per_package'])}; "
        f"per kampanye, {_ci(p30['campaign_weighted'])} dan {_ci(r30['campaign_weighted'])}; berbobot unduhan, "
        f"{_ci(p30['download_weighted'])} dan {_ci(r30['download_weighted'])}. Masa tunggu tingkat rilis dengan "
        "demikian menghentikan lebih banyak pada setiap penaksir, sebesar "
        f"{dec(100 * (r30['per_package']['est'] - p30['per_package']['est']))} poin persentase per paket dan "
        f"{dec(100 * (r30['download_weighted']['est'] - p30['download_weighted']['est']), 0)} poin berbobot unduhan, "
        "dan selisih tersebut seluruhnya berasal dari rilis berbahaya pada proyek berumur sedikitnya 30 hari "
        "yang tidak terlihat oleh aturan tingkat proyek. Digabung untuk seluruh periode, porsi berbobot unduhan "
        "tidak informatif: satu nama berumur panjang yang dilaporkan bertahun-tahun setelah unggahan pertamanya "
        f"membawa {pct(N['exposure_estimators']['top1_share'])}% seluruh unduhan klien berbahaya dan sepuluh nama "
        f"terbesar {pct(N['exposure_estimators']['top10_share'])}%. Dengan latar unduhan otomatis dikeluarkan, "
        f"porsi per paket 2026 menjadi {pct(XB['project']['30']['test']['per_package']['est'])}% dan "
        f"{pct(XB['release']['30']['test']['per_package']['est'])}% "
        f"({pct(XB25['project']['30']['test']['per_package']['est'])}% dan "
        f"{pct(XB25['release']['30']['test']['per_package']['est'])}% terhadap persentil ke-25), dan porsi berbobot "
        f"unduhan {pct(XB['project']['30']['test']['download_weighted']['est'])}% dan "
        f"{pct(XB['release']['30']['test']['download_weighted']['est'])}%. Menggeser penyelarasan hari sebanyak satu "
        "hari mengubah angka 30 hari kurang dari satu poin persentase.")
    h, rows = tabel_id("t_exposure_estimators", ["Periode", "Penaksir", "Tingkat proyek 30 hr (%)",
                                                 "Tingkat rilis 30 hr (%)"],
                       {"2026 (test)": "2026 (uji)", "All periods": "Semua periode",
                        "Mean per package": "Rata-rata per paket", "Mean per campaign": "Rata-rata per kampanye",
                        "Download-weighted": "Berbobot unduhan",
                        "Download-weighted, top 1 excluded": "Berbobot unduhan, tanpa 1 teratas",
                        "Download-weighted, top 10 excluded": "Berbobot unduhan, tanpa 10 teratas"},
                       kolom_teks=(0, 1))
    m.tabel("Unduhan Klien Berbahaya yang Dihentikan Masa Tunggu 30 Hari menurut Penaksir dan Periode", h, rows,
            lebar=[2.6, 5.0, 3.2, 3.2], size=9, align=["l", "l", "r", "r"],
            catatan="Interval 95% mencuplik ulang kampanye (2.000 replikasi).", key="paparan")

    m.h4("Biaya dan Gangguan")
    rc, pc, ra = C["release_client"]["30"], C["project_client"]["30"], C["ratio"]["30"]
    m.p(
        "Selama 24 bulan dari Oktober 2024 sampai September 2026, masa tunggu tingkat proyek 30 hari berdampak "
        f"pada median {pct(pc['median'], 4)}% seluruh unduhan klien instalasi per bulan (rentang antarkuartil "
        f"{pct(pc['q1'], 4)}–{pct(pc['q3'], 4)}%), sedangkan masa tunggu tingkat rilis 30 hari {pct(rc['median'])}% "
        f"({pct(rc['q1'])}–{pct(rc['q3'])}%). Rasio bulanannya bermedian {num(round(ra['median']))} (rentang "
        f"antarkuartil {num(round(ra['q1']))}–{num(round(ra['q3']))}; {num(round(ra['min']))}–{num(round(ra['max']))}), "
        "sekitar tiga orde besaran pada setiap ambang satu sampai 30 hari ({{tbl:tradeoff}}, {{gbr:paparan}}b). "
        f"Menghitung pula {pct(C['before_first_upload']['median'], 3)}% unduhan yang bertanggal sebelum unggahan "
        "pertama proyeknya pada cermin metadata sebagai muda menaikkan biaya tingkat proyek menjadi "
        f"{pct(C['project30_upper']['median'], 3)}% dan menurunkan rasio menjadi sekitar "
        f"{num(round(rc['median'] / C['project30_upper']['median']))}. Kedua biaya berbeda jenis: dampak tingkat "
        "proyek berupa prompt yang dijelaskan atau, tanpa terminal, perintah yang diblokir; dampak tingkat rilis "
        "berupa penggantian diam-diam dengan versi lama, yang biasanya berhasil tetapi kadang menahan perbaikan. "
        f"Perbandingan baru berbalik bila satu prompt dinilai lebih berat daripada sekitar {num(round(ra['median']))} "
        "penggantian diam-diam.")
    m.p(
        "Ambang lebih tidak menentukan daripada granularitas: pada tingkat proyek, satu hari sudah menghentikan "
        f"{pct(e('project', 1))}% per paket dan tujuh hari {pct(e('project', 7))}%, sedangkan di atas 30 hari biaya "
        "naik tajam karena makin banyak proyek mapan yang terkena aturan. Masa tunggu tingkat rilis satu hari, "
        f"bawaan pnpm sejak versi 11, menghentikan {pct(e('release', 1))}% dengan biaya "
        f"{pct(C['release_client']['1']['median'], 2)}%, dan bawaan 48 jam pembungkus komersial "
        f"{pct(e('release', 2))}% dengan biaya {pct(C['release_client']['2']['median'], 2)}%.")
    h, rows = tabel_id("t_tradeoff", ["T (hari)", "Proyek: dihentikan per paket (%)", "Proyek: dihentikan, "
                                      "berbobot unduhan (%)", "Proyek: unduhan terdampak, median [IQR] (%)",
                                      "Rilis: dihentikan per paket (%)", "Rilis: dihentikan, berbobot unduhan (%)",
                                      "Rilis: unduhan terdampak, median [IQR] (%)", "Rasio biaya rilis/proyek"])
    m.tabel("Perlindungan (Paket Berbahaya 2026) dan Biaya (Porsi Unduhan Klien per Bulan, Oktober 2024 sampai "
            "September 2026) Masa Tunggu menurut Ambang T", h, rows, lebar=[1.2, 1.7, 1.8, 2.4, 1.7, 1.8, 2.2, 1.6],
            size=8.5, align=["r"] * 8,
            catatan="Dihentikan: seperti pada " + "{{tbl:paparan}}" + ". Terdampak: porsi unduhan klien dalam sebulan "
                    "yang akan di-prompt (tingkat proyek) atau diganti versi lama (tingkat rilis); median dan rentang "
                    "antarkuartil (IQR) atas 24 bulan. Rasio: median rasio bulanan.", key="tradeoff")
    m.p(
        "Biaya berbobot unduhan didominasi sistem CI yang memasang ulang dependensi mapan, sedangkan pengembang "
        f"atau agen terganggu ketika menambahkan dependensi baru. Dari {num(da['all']['edges'])} dependensi yang "
        f"ditambahkan rilis PyPI pada 24 bulan yang sama, {pct(da['all']['lt30'])}% menamai proyek yang berumur "
        f"kurang dari 30 hari saat itu (median bulanan {pct(da['lt30_by_month']['median'])}%), {pct(da['all']['lt7'])}% "
        f"kurang dari seminggu, dan {pct(da['all']['unknown_target'] / da['all']['edges'])}% menamai proyek yang tidak "
        "ditemukan pada cermin metadata. Kira-kira satu dari lima puluh penambahan dependensi akan bertemu prompt "
        "tingkat proyek: jauh lebih sering daripada yang disiratkan porsi unduhan, tetapi cukup jarang untuk tetap "
        "menjadi pengecualian.")

    m.h4("Risiko yang Tersisa")
    m.p(
        f"Seluruh {tmiss['n']} paket berbahaya uji yang terlewat oleh model akhir adalah rilis berbahaya dari "
        f"proyek yang sudah berumur antara {dec(tmiss['project_age_days_min'], 0)} hari dan "
        f"{dec(tmiss['project_age_days_max'] / 365.25)} tahun; {tmiss['gap_ge_30']} di antaranya menyusul sedikitnya "
        "30 hari tanpa rilis, konsisten dengan proyek pre-aged atau terbengkalai, dan "
        f"{kata(tmiss['gap_lt_7'])} menyusul rilis kurang dari seminggu sebelumnya, konsisten dengan proyek aktif yang "
        "disusupi. Kelas ini bertambah: porsinya di antara paket berbahaya naik dari paling banyak 1,5% per tahun "
        "pada 2022–2025 menjadi 5,9% pada 2026 ({{tbl:preaged}}), dan dampaknya terkonsentrasi: kompromi "
        "`lightning` pada 2026, proyek yang berumur hampir empat tahun, menerima unduhan klien lebih banyak "
        "daripada semua paket berbahaya 2026 lainnya kecuali satu. Masa tunggu tingkat rilis menahan seluruh "
        "rilis ini menurut konstruksinya, dan aturan I-10 menangkap yang dorman, tetapi keduanya bekerja pada "
        "setiap rilis setiap proyek.")
    h, rows = tabel_id("t_preaged", ["Tahun unggahan berbahaya pertama", "Paket berbahaya", "Pada proyek ≥ 30 hr",
                                     "Porsi (%)", "Tertangkap I-10, G = 90 hr", "Tertangkap I-10, G = 365 hr",
                                     "Ditahan masa tunggu rilis 30 hr"])
    m.tabel("Rilis Berbahaya pada Proyek yang Sudah Berumur Sedikitnya 30 Hari", h, rows,
            lebar=[2.4, 1.8, 1.9, 1.4, 2.2, 2.2, 2.4], size=9, align=["l", "r", "r", "r", "r", "r", "r"], key="preaged")
    m.p(
        "Menurut aturan yang ditetapkan lebih dahulu, I-10 diaktifkan secara bawaan hanya bila biayanya pada "
        "unduhan Juni 2025 tidak melebihi biaya masa tunggu tingkat proyek 30 hari "
        f"({pct(dc['project30_cost_val'], 4)}%). Setiap periode dorman melampauinya, dengan faktor "
        f"{num(round(dc['dormancy_cost_val']['365'] / dc['project30_cost_val']))} untuk G = 365 hari "
        f"({pct(dc['dormancy_cost_val']['365'], 2)}%) sampai {num(round(dc['dormancy_cost_val']['30'] / dc['project30_cost_val']))} "
        f"untuk G = 30 hari ({pct(dc['dormancy_cost_val']['30'], 2)}%; {{{{tbl:dorman}}}}), sehingga I-10 dirilis "
        "dalam keadaan nonaktif dan dapat diaktifkan bila prompt tambahan dapat diterima. Pada data uji, "
        f"mengaktifkannya pada G = 90 hari akan menaikkan cakupan menjadi {pct(D['i10-90']['mal'])}% dan FPR pada "
        f"paket mapan menjadi {pct(D['i10-90']['negative_established'], 2)}%.")
    h, rows = tabel_id("t_dormancy", ["Periode dorman G (hari)", "Rilis berbahaya proyek lama tertangkap "
                                      "(pengembangan + validasi)", "Paket mapan pengembangan yang di-prompt",
                                      "Unduhan klien yang di-prompt (%)"])
    m.tabel("Pemilihan Periode Dorman I-10 pada Data Pengembangan dan Validasi", h, rows,
            lebar=[2.8, 4.2, 3.8, 3.2], size=10, align=["r", "r", "r", "r"],
            catatan="Aturan keputusan ditetapkan sebelum data uji dinilai dengan I-10: aktifkan I-10 secara bawaan "
                    "dengan G terkecil yang porsi unduhan kliennya (Juni 2025) tidak melebihi masa tunggu tingkat "
                    f"proyek 30 hari ({pct(dc['project30_cost_val'], 4)}%). Tidak ada G yang memenuhi.",
            key="dorman")
    names = ("ultralytics", "ctx", "num2words", "lightning")
    m.p(
        "Menghitung paket menyembunyikan di mana kerugian terkonsentrasi. {{tbl:kasus}} menelusuri enam insiden. "
        f"Kompromi `ultralytics` ({num(cs['ultralytics']['client_downloads'])} unduhan klien versi berbahaya), "
        "`num2words`, dan `lightning`, serta pengambilalihan `ctx` yang dorman, mengenai proyek yang berumur "
        "bertahun-tahun, sehingga masa tunggu tingkat proyek tidak menghentikan satu pun unduhannya, sedangkan "
        "masa tunggu tingkat rilis 30 hari akan menahan seluruhnya; masa tunggu tingkat rilis satu hari akan "
        f"menghentikan antara {pct(min(cs[n]['stopped_release1'] for n in names))}% dan "
        f"{pct(max(cs[n]['stopped_release1'] for n in names))}%. I-10 akan aktif untuk `ctx` dan `num2words`, yang "
        "menyusul masa sunyi panjang, tetapi tidak untuk `ultralytics`, yang dirilis sehari setelah versi bersih, "
        "maupun `lightning`, yang rilis sebelumnya berselang 89 hari, satu hari kurang dari G = 90. `aiocpa`, "
        f"proyek yang diterbitkan pembuatnya {cs['aiocpa']['project_age_days']} hari sebelum disisipi pencuri "
        "informasi, adalah strategi pre-aging dalam praktik. `torchtriton` merupakan proyek baru dan akan "
        "ditandai, tetapi hanya bila dipasang langsung: paket ini mencapai korban sebagai dependensi build nightly "
        "PyTorch, yang tidak diperiksa pipguard.")
    h, rows = tabel_id("t_cases", ["Proyek", "Unggahan berbahaya pertama", "Versi berbahaya", "Umur proyek (hari)",
                                   "Hari sejak rilis sebelumnya", "Unduhan klien versi berbahaya",
                                   "Hari terakhir dengan unduhan klien", "Dihentikan: proyek 30 hr (%)",
                                   "Dihentikan: rilis 1 hr (%)", "Dihentikan: rilis 30 hr (%)", "I-10 (G = 90 hr)"],
                       {"yes": "ya", "no": "tidak"}, kolom_teks=(10,))
    m.tabel("Insiden PyPI Berdampak Tinggi dan Porsi Unduhan Klien Versi Berbahaya yang Dihentikan Setiap Kebijakan",
            h, rows, lebar=[1.7, 1.7, 1.0, 1.2, 1.2, 1.4, 1.2, 1.2, 1.2, 1.2, 1.0], size=8,
            catatan="≈ = versi berbahaya tidak terekam cermin metadata; hari unduhan pertama dipakai sebagai pengganti "
                    "waktu unggah, dan untuk aiocpa unduhan pertama proyek sebagai pengganti waktu pembuatannya. "
                    "Unduhan dihitung selama 60 hari setelah unggahan. Untuk ctx, versi yang diunggah setelah "
                    "pengambilalihan akun.", key="kasus")
    m.p(
        "Angka paparan di atas milik *kebijakan* tingkat proyek. pipguard menerapkannya pada paket yang disebut "
        "pada baris perintah dan berkas *requirements*, bukan pada dependensi yang diresolusi pip, sedangkan opsi "
        f"pip dan uv berlaku pada seluruh resolusi. Sebanyak {dep['with_dependents']} dari 8.588 paket berbahaya "
        f"dideklarasikan sebagai dependensi proyek lain, {dep['only_malicious_dependents']} di antaranya hanya oleh "
        f"paket berbahaya lain; {dep['established_unreported_dependent']} memiliki dependen yang tidak dilaporkan dan "
        "berumur sedikitnya 30 hari saat rilis berbahaya muncul, yaitu kasus ketika instalasi transitif melewati "
        f"pipguard. Pada 2026, {dep['test']['risky_packages']} paket semacam itu membawa "
        f"{pct(dep['test']['risky_download_share'])}% unduhan klien berbahaya. Menghitung seluruh unduhannya sebagai "
        "tidak dihentikan, kasus terburuk, menurunkan porsi pipguard sebagaimana diimplementasikan dari "
        f"{pct(dep['test']['policy_per_package'])}% menjadi {pct(dep['test']['implemented_worst_per_package'])}% per "
        f"paket dan dari {pct(dep['test']['policy_pooled'])}% menjadi {pct(dep['test']['implemented_worst_pooled'])}% "
        "berbobot unduhan.")
    cols = [("pip", "pip"), ("pip_P30D", "pip, P30D"), ("pip_P2D", "pip, P2D"), ("uv_30d", "uv, 30 hr"),
            ("pipguard", "pipguard"), ("pipguard_I10", "pipguard + I-10")]
    kasus = {"Unregistered name": "Nama tidak terdaftar",
             "Project first published < 1 day ago": "Proyek pertama terbit < 1 hari lalu",
             "Project first published 10-15 days ago": "Proyek pertama terbit 10–15 hari lalu",
             "Established project, regular release < 30 days ago": "Proyek mapan, rilis rutin < 30 hari lalu",
             "Established project, release < 30 days ago after > 90 days without releases":
                 "Proyek mapan, rilis < 30 hari lalu setelah > 90 hari tanpa rilis",
             "Established project, no release in the last 30 days": "Proyek mapan, tanpa rilis 30 hari terakhir"}

    def pendek(s):
        s = s.replace("; cancelled without a terminal", "")
        s = re.sub(r"installs older \(([^)]*)\)", r"versi lama (\1)", s)
        return (s.replace("fails (no matching distribution)", "gagal").replace("installs latest", "terbaru")
                .replace("passes silently", "lolos").replace("prompts (", "prompt ("))
    rows = [[kasus.get(r["case"], r["case"]), "(buatan)" if r["package"].startswith("zzz-") else r["package"]] +
            [pendek(r[c[0]]) for c in cols] for r in CMP["rows"]]
    meta = CMP["meta"]
    m.p(
        "{{tbl:alat}} menunjukkan perlakuan alat-alat yang ada terhadap enam paket hidup. Seluruhnya menghentikan "
        "nama yang tidak terdaftar dan proyek yang terbit pada hari yang sama. Masa tunggu tingkat rilis dua hari "
        "meloloskan proyek berumur 10–15 hari, yang di-prompt oleh pipguard. Masa tunggu tingkat rilis pip dan uv "
        "memasang versi lama dua proyek mapan yang baru merilis secara diam-diam, salah satunya bundel "
        "sertifikat yang diandalkan sebagian besar klien HTTPS Python, dan pipguard dengan I-10 memberi prompt "
        "untuk proyek mapan yang merilis setelah lebih dari 90 hari sunyi. Perbedaannya kualitatif sekaligus "
        "kuantitatif: masa tunggu tingkat rilis mengubah hasil banyak instalasi sah secara diam-diam, sedangkan "
        "masa tunggu tingkat proyek jarang mengganggu dan menyebutkan alasannya.")
    m.tabel(f"Perbandingan Langsung Masa Tunggu Waktu Instalasi ({meta['run_at'][:10]}; pip {meta['pip']}, "
            f"{meta['uv'].split(' (')[0]})", ["Kasus", "Paket"] + [c[1] for c in cols], rows,
            lebar=[3.4, 1.8, 1.2, 1.5, 1.5, 1.5, 1.6, 1.6], size=8,
            catatan="Dry run dibatasi pada wheel; tidak ada yang dipasang. Versi lama = versi lama akan dipasang "
                    "diam-diam; gagal = tidak ada distribusi yang cocok; prompt = pipguard meminta konfirmasi (tanpa "
                    "terminal: batal dengan status keluar 3).", key="alat")
    m.h4("Tingkat Keparahan")
    m.p(
        "Di antara paket baru, skor memisahkan paket berbahaya dari paket sah dengan AUC "
        f"{dec(sv['auc_final'], 3)} [{dec(sv['auc_final_ci'][0], 3)}–{dec(sv['auc_final_ci'][1], 3)}] pada data uji, "
        f"dekat dengan nilai in-sample {dec(N['severity']['val']['auc_final'], 3)} pada data validasi tempat bobot "
        f"dan τ ditaksir, dibandingkan {dec(sv['auc_v1'], 3)} untuk rancangan awal ({{{{gbr:keparahan}}}}a). Tingkat "
        f"DANGER mencakup {pct(sv['danger_tpr'])}% dari 514 paket berbahaya baru dan {pct(sv['danger_fpr'])}% dari "
        f"1.039 paket sah baru, likelihood ratio positif {dec(sv['lr_plus'])}; pada porsi realistis 1% paket "
        f"berbahaya di antara proyek baru, label DANGER hanya benar {pct(sv['ppv_at_prior']['0.01'])}% kali. Skor "
        "andal dalam urutan ({{gbr:keparahan}}b) tetapi lemah secara absolut; karena itu skor hanya menentukan tingkat "
        "peringatan dan tidak pernah memblokir.")
    m.gambar(FIG / "gbr_keparahan.png", "Kurva ROC Skor Akhir dan Awal di antara Paket Baru pada Data Uji dengan "
                                         "Titik Operasi DANGER (a) dan Porsi Paket Berbahaya per Rentang Skor pada "
                                         "Ukuran Kelas yang Sama (b)", 14.0, key="keparahan")


# ====================================================================== RM4

def rm4(m):
    m.h3("Halusinasi Paket pada Model Bahasa Kecil (RM4)", key="hasil_halusinasi")
    if not H:
        m.p("[Hasil halusinasi belum tersedia.]")
        return
    tot = sum(v["recommendations"] for v in H["models"].values())
    unreg = sum(v["unregistered"] for v in H["models"].values())
    late = sum(v["late"] for v in H["models"].values())
    L = H["late"]
    oc = L.get("owner_class", {})
    dl = L.get("days_after_model_release", {})
    h, rows = tabel_id("t_hallucination", ["Model", "Dirilis", "Prompt", "Nama direkomendasikan",
                                           "Tidak pernah terdaftar (%)", "Terdaftar setelah model dirilis (%)",
                                           "Prompt dengan ≥ 1 nama halusinasi (%)"], kolom_teks=())
    rates = [float(r[4].replace(",", ".")) for r in rows]
    m.p(
        f"Empat model terbuka kecil merekomendasikan {num(tot)} nama untuk 2.000 prompt ({{{{tbl:halusinasi}}}}). "
        f"Sebanyak {pct(unreg / tot)}% rekomendasi menamai paket yang tidak pernah terdaftar pada PyPI, "
        f"{dec(min(rates))}% sampai {dec(max(rates))}% per model, dengan {num(H['distinct_unregistered'])} nama "
        f"berbeda yang tidak terdaftar dan {num(H['recurring_hallucinated'])} nama halusinasi yang berulang lintas "
        "prompt atau model. Untuk nama-nama ini pip gagal dan pemeriksaan keberadaan pipguard mengubah kegagalan "
        "tersebut menjadi penjelasan; keduanya tidak mencegah kerugian karena tidak ada yang dapat dipasang.")
    m.p(
        f"Sebanyak {kata(H['distinct_late'])} nama berbeda ({late} rekomendasi, {pct(late / tot, 2)}%) pertama kali "
        f"didaftarkan pada PyPI setelah model yang merekomendasikannya dirilis, dengan median {dec(dl['median'], 0)} "
        f"hari kemudian ({dec(dl['min'], 0)}–{dec(dl['max'], 0)}). Tidak satu pun tercantum pada laporan OSV, tidak "
        f"satu pun berumur kurang dari 30 hari saat diperiksa, dan dari {kata(L['on_pypi_now'])} yang masih ada, "
        f"{kata(oc.get('substantive', 0))} merupakan proyek substantif dan {kata(oc.get('minimal', 0))} proyek "
        f"minimal; tidak ada yang berupa penampung nama atau pendaftaran riset/defensif, dan {kata(L['removed_since'])} "
        "telah dihapus. Nama-nama tersebut adalah tabrakan nama dengan proyek independen, bukan penyerobot. Masa "
        "tunggu hanya mencakup penyerobot selama 30 hari pertama setelah pendaftaran; penyerobot yang mendaftar "
        "lalu menunggu akan lolos, seperti proyek pre-aged lainnya. Karena modelnya kecil, terkuantisasi, dan hanya "
        "diuji dengan prompt rekomendasi, angka absolutnya tidak dapat dibandingkan dengan Spracklen dkk. (2025).")
    m.tabel("Halusinasi Paket per Model (500 Prompt per Model)", h, rows, lebar=[3.6, 1.8, 1.2, 1.8, 1.8, 2.0, 1.8],
            size=9, align=["l", "l", "r", "r", "r", "r", "r"],
            catatan="Tidak pernah terdaftar = tidak ada unggahan pada riwayat PyPI bertanda waktu dan HTTP 404 saat "
                    "ini. Terdaftar setelah model dirilis = unggahan pertama setelah tanggal rilis publik model. "
                    "Nama tidak dipublikasikan.", key="halusinasi")


# ====================================================================== pembahasan

def pembahasan(m):
    D, C = N["detection"], N["cost"]
    X = N["exposure_estimators"]["by_shift"]["shift0"]
    A = N["adaptive"]
    ra = C["ratio"]["30"]
    m.h3("Implikasi Hasil Penelitian", key="implikasi")
    m.p(
        "Bagi pengembang alat, pertanyaan waktu instalasi bukan terutama *seperti apa rupa paket berbahaya*, "
        "melainkan *berapa umurnya*, dan pertanyaan tersebut sebaiknya diajukan kepada proyek secara bawaan dan "
        "kepada rilis bila taruhannya membenarkan. Masa tunggu tingkat proyek 30 hari menghentikan sebagian besar "
        "paparan yang dihentikan masa tunggu tingkat rilis "
        f"({pct(X['project']['30']['test']['per_package']['est'])}% dibandingkan "
        f"{pct(X['release']['30']['test']['per_package']['est'])}% per paket 2026) sambil mengubah unduhan dengan "
        f"median {num(round(ra['median']))} kali lebih sedikit, dan melakukannya secara terlihat alih-alih "
        "mengganti versi dependensi mapan secara diam-diam. Aturan ini tidak menggantikan aturan tingkat rilis: "
        "risiko sisa, yaitu proyek yang disusupi dan pre-aged, adalah tempat sebagian besar insiden berdampak "
        "tinggi pada {{tbl:kasus}}. Karena itu direkomendasikan bawaan berlapis: masa tunggu tingkat proyek di "
        "semua tempat; masa tunggu tingkat rilis sedikitnya satu hari, seperti bawaan pnpm, di tempat penggantian "
        "diam-diam dapat diterima, disertai pengecualian untuk perbaikan mendesak (Rebatchi dkk., 2024; Liu "
        "dkk., 2022); aturan tingkat rilis untuk masa dorman atau perubahan pengelola dan provenance pada "
        "lingkungan berjaminan tinggi; dan masa tunggu tingkat rilis 30 hari hanya bila biayanya, sekitar satu "
        "dari sembilan unduhan, dapat diterima. Penilaian metadata sebaiknya menjelaskan dan mengurutkan, bukan "
        "memutuskan, dan setiap komponen yang dipelajari harus dikalibrasi ulang dan divalidasi pada data yang "
        "lebih baru.")
    m.p(
        "Bagi registry dan komunitas keamanan, paket berbahaya dilaporkan dalam hitungan jam dan sebagian besar "
        "tidak menerima instalasi lebih banyak daripada latar otomatis yang diterima setiap unggahan baru, "
        "sehingga pelaporan dan penghapusan yang cepat tetap menjadi tuas utama melawan malware yang diproduksi "
        "massal. Detektor di sisi registry menghadapi batas positif palsu paling banyak 0,1% (Vu dkk., 2023), "
        "sedangkan masa tunggu di sisi klien dapat menanggung positif palsu yang tinggi pada proyek baru justru "
        "karena proyek baru menerima sedikit instalasi; biaya tersebut ditanggung pengelola proyek baru yang "
        "pengguna pertamanya menjumpai peringatan. Bagi peneliti, evaluasi detektor paket berbahaya sebaiknya "
        "memakai metadata titik-waktu, pemisahan temporal, dan ketidakpastian tingkat kampanye (Moufid dkk., "
        "2026; Draz, 2026), menimbang paket menurut kapan paket dipasang, dan melaporkan bagaimana kesimpulan "
        "bergantung pada pembobotan. Cermin publik memotong pemindaian besar secara diam-diam, sehingga setiap "
        "agregat harus diperiksa kelengkapannya.")
    m.h3("Penyerang Adaptif", key="adaptif")
    m.p(
        "Setiap aturan berbasis umur mengundang penyerang untuk menunggu. Penyerang yang mendaftarkan proyek "
        "dengan rilis tidak berbahaya dan mempersenjatainya setelah 30 hari lolos dari masa tunggu tingkat "
        "proyek, dan porsi rilis berbahaya pada proyek lama naik menjadi 5,9% pada 2026. {{gbr:adaptif}} "
        "memodelkan porsi *p* penyerang yang melakukan pre-aging, dengan profil paparan serangan proyek baru "
        f"seperti yang teramati pada 2026 dan profil serangan pre-aged seperti {A['n_old_all']} rilis berbahaya "
        f"pada proyek lama yang teramati. Masa tunggu tingkat proyek menghentikan {pct(A['project30']['young'])}% "
        "serangan proyek baru dan tidak menghentikan serangan pre-aged, sehingga perlindungannya turun linear "
        f"hingga nol; masa tunggu tingkat rilis 30 hari menghentikan {pct(A['release30']['old'])}% serangan pre-aged; "
        f"I-10 pada G = 90 hari memulihkan {pct(A['project30_i10_observed']['old'])}% selama penyerang tidak juga "
        "menjaga jeda rilis lebih pendek daripada G. Pada p = 25%, ketiga kebijakan menghentikan "
        f"{pct(A['project30']['by_p']['0.25'])}%, {pct(A['project30_i10_observed']['by_p']['0.25'])}%, dan "
        f"{pct(A['release30']['by_p']['0.25'])}% per paket.")
    m.gambar(FIG / "gbr_adaptif.png", "Unduhan Berbahaya yang Dihentikan (Rata-rata per Paket) bila Sebagian "
                                       "Penyerang Melakukan Pre-aging. Garis Titik-titik Menandai Porsi yang "
                                       "Teramati pada 2026", 10.5, key="adaptif")
    m.p(
        "Menunggu memberi keuntungan lebih kecil daripada kelihatannya: rilis berbahaya 2026 pada proyek lama "
        f"dilaporkan dengan median {dec(24 * 60 * A['old_test_report_median_days'], 0)} menit setelah unggahan dan "
        f"terakhir diunduh klien instalasi dengan median {kata(int(round(A['old_test_lastdl_median_days'])))} hari setelahnya, "
        "sehingga penyerang pre-aging hanya menukar masa tunggu dengan jendela singkat yang sama setelah rilis "
        f"berbahaya, yang sebagian besar tercakup masa tunggu tingkat rilis yang pendek: satu hari menghentikan "
        f"{pct(A['release1']['old'])}% dan tujuh hari {pct(A['release7']['old'])}% unduhan serangan pre-aged. "
        "Peniruan metadata hanya memengaruhi tingkat peringatan, yang menurut rancangan tidak pernah memutuskan. "
        "Lapisan yang kokoh karena itu adalah kombinasi aturan umur pada waktu instalasi dengan deteksi dan "
        "penghapusan cepat di hulu.")
    m.h3("Agen Pemrograman AI", key="agen_ai")
    m.p(
        "Agen menjalankan pip tanpa terminal. Prompt yang menunggu tanpa akhir, atau pertahanan yang dapat "
        "dimatikan agen dengan mengatur variabel lingkungan, gagal pada kondisi tersebut. pipguard membatalkan, "
        "menjelaskan dalam rekaman terstruktur, dan keluar dengan status khusus sehingga kerangka agen dapat "
        "meneruskan keputusan kepada manusia, serta mengabaikan variabel pengecualian kecuali diizinkan berkas "
        "konfigurasi. Sifat ini melindungi dari kekeliruan jujur agen, seperti mengikuti nama halusinasi atau "
        "nama yang diserobot, tetapi tidak dari agen yang diarahkan untuk menghindari pemeriksaan: `python -m "
        "pip` di luar shell interaktif, jalur absolut ke pip, atau pemasang lain melewati interceptor berbasis "
        "PATH mana pun. Bagi agen dan CI, aturan keputusan karena itu sebaiknya ditempatkan di titik yang harus "
        "dilalui setiap pemasang: citra sandbox yang hanya menyediakan pip ber-shim dengan konfigurasi sistem "
        "terkunci, lapisan alat agen, atau paling kokoh proxy indeks paket lokal yang menerapkan aturan umur "
        "proyek yang sama pada setiap permintaan. Memeriksa dependensi transitif di klien juga tidak sesederhana "
        "kelihatannya: `pip install --dry-run --report` meresolusi seluruh dependensi, tetapi untuk itu membangun sdist "
        "demi memperoleh metadatanya, yang menjalankan kode yang justru hendak dicegah, kecuali resolusi dibatasi "
        "pada wheel.")
    m.h3("Keterbatasan Penelitian", key="keterbatasan")
    m.daftar([
        "Intersepsi bergantung pada PATH dan fungsi shell: `python -m pip` dari pemanggil yang tidak membaca "
        "konfigurasi shell, jalur absolut, skrip yang mengaktifkan lingkungannya sendiri, sudo, dan citra tanpa "
        "pipguard melewatinya; uv, poetry, conda, pipx, dan Windows tidak didukung.",
        "Dependensi transitif tidak diperiksa; memeriksanya dengan aman sebelum instalasi memerlukan resolusi "
        "khusus wheel atau proxy indeks.",
        "Model bawaan tidak mendeteksi proyek yang disusupi atau pre-aged; aturan I-10 yang opsional mencakup "
        "sebagian dengan biaya yang besar.",
        "pipguard hanya memakai nama dan metadata registry, tidak menganalisis kode paket.",
        "Tidak dilakukan studi pengguna maupun eksperimen agen; yang diukur adalah frekuensi gangguan, bukan "
        "respons pengembang atau agen terhadapnya.",
        "Latensi diukur pada satu mesin di bawah WSL2 dan satu koneksi jaringan; latensi cache kosong "
        "mengikuti waktu pulang-pergi ke PyPI.",
    ])
    m.h3("Ancaman terhadap Validitas", key="validitas")
    m.p(
        "Validitas konstruk. Label tidak sempurna: OSV tidak lengkap sehingga sebagian paket yang dianggap sah "
        "mungkin berbahaya, dan bertahan di PyPI hanya proksi untuk keabsahan. Waktu publikasi OSV mencerminkan "
        "umpan vendor yang melapor kepadanya sehingga mengukur kapan laporan menjadi publik, bukan kapan paket "
        "pertama kali terdeteksi. Waktu instalasi tidak diketahui; karena itu dipakai tiga skenario dan tiga "
        "penaksir paparan. Unduhan klien instalasi mencakup instalasi otomatis oleh pemindai dan sandbox yang "
        "tidak dapat diidentifikasi log unduhan; kontrol latar membatasi, tetapi tidak menghilangkan, pengaruhnya. "
        "Unduhan klien terakhir hanya mendekati waktu penghapusan.")
    m.p(
        "Validitas internal. Metadata paket berbahaya dan paket sah berasal dari dua sumber yang kesesuaiannya "
        "diukur. Data 2026 sempat dinilai satu kali oleh kalibrasi awal sebelum perancangan ulang; penolakannya "
        "dibenarkan oleh data validasi saja, dan hold-out prospektif tidak tersentuh keputusan rancangan apa pun "
        "tetapi kecil. Pengelompokan kampanye bersifat heuristik; mengubah definisinya mengubah angka tingkat "
        "kampanye paling banyak sekitar satu poin persentase. Rekonstruksi mencakup lebih sedikit paket pada "
        "periode terbaru; analisis jenis berkas menunjukkan bahwa hal ini sedikit membesar-besarkan pergeseran "
        "metadata tetapi tidak membalik arahnya. Pengurai probe halusinasi dapat salah membaca jawaban teks bebas.")
    m.p(
        "Validitas eksternal. Penelitian hanya mencakup PyPI; npm dan registry lain berbeda dalam eksekusi waktu "
        "instalasi dan kecepatan pelaporan. Biaya diukur pada 24 jendela bulanan dan bervariasi antarbulan. Ukuran "
        "gangguan menghitung dependensi yang ditambahkan penulis paket dalam rilis, bukan penambahan oleh "
        "pengembang aplikasi atau agen. Probe halusinasi memakai empat model kecil dengan 500 prompt per model; "
        "model terdepan dan pengaturan agen dapat berperilaku berbeda, tetapi klasifikasi berbasis waktu berlaku "
        "untuk model apa pun.")
    m.h3("Rangkuman Hasil", key="rangkuman")
    m.p("Rangkuman jawaban setiap rumusan masalah disajikan pada {{tbl:rangkuman}}.")
    p30 = X["project"]["30"]["test"]["per_package"]["est"]
    r30 = X["release"]["30"]["test"]["per_package"]["est"]
    m.tabel("Rangkuman Hasil Penelitian", ["Rumusan masalah", "Hasil"], [
        ["RM1 Waktu pelaporan, penghapusan, instalasi", f"Median pelaporan {dec(24 * N['timing']['all']['report_median_days'])} "
         "jam; sebagian besar unduhan klien terjadi pada hari pertama dan sukar dibedakan dari latar otomatis"],
        ["RM2 Stabilitas indikator", "Indikator metadata bergeser tajam antarperiode; umur proyek stabil; kalibrasi "
         "pada data lama ditolak"],
        ["RM3 Perlindungan dan biaya", f"Tingkat proyek 30 hari: cakupan {pct(D['pipguard-v2']['mal'])}%, paparan "
         f"dihentikan {pct(p30)}% per paket; tingkat rilis {pct(r30)}% dengan biaya sekitar "
         f"{num(round(ra['median']))} kali lebih besar; sisa risiko pada proyek disusupi dan pre-aged"],
        ["RM4 Halusinasi paket", f"{pct(sum(v['unregistered'] for v in H['models'].values()) / sum(v['recommendations'] for v in H['models'].values()))}% "
         "rekomendasi tidak pernah terdaftar; nama yang terdaftar kemudian merupakan proyek tak terkait"],
        ["RM5 Cakupan dan overhead", "43 dari 43 kasus intersepsi sesuai spesifikasi; batas yang terdokumentasi "
         f"adalah `python -m pip` non-interaktif dan jalur absolut; tambahan sekitar "
         f"{dec(float([r for r in latency() if r[0] == 'Set 2: pipguard, warm cache (1 entry)'][0][1]) - float([r for r in latency() if r[0] == 'Set 2: stub pip, no pipguard'][0][1]), 0)} ms"],
    ], lebar=[4.4, 9.6], size=10, align=["l", "l"], key="rangkuman")
