"""BAB III ANALISA DAN PERANCANGAN SISTEM."""
import json

from ctx_id import FIG, N, REPO, dec, kata, num, pct, tabel_id


def tulis(m):
    m.bab(3, "Analisa dan Perancangan Sistem", key="analisa")
    kerangka(m)
    metode(m)
    analisa(m)
    perancangan(m)


def kerangka(m):
    m.h2("Kerangka Pikir", key="kerangka")
    m.p(
        "Kerangka pikir menggambarkan pola pikir penelitian secara keseluruhan, mulai dari permasalahan, "
        "pertanyaan penelitian, pendekatan dan proses penyelesaiannya, hingga luaran dan capaian yang "
        "diharapkan. Kerangka pikir penelitian ini disajikan pada {{gbr:kerangka}}.")
    m.gambar(FIG / "gbr_kerangka.png", "Kerangka Pikir Penelitian", 13.0, key="kerangka")
    m.p(
        "Alur berpikir dimulai dari dua kondisi: paket berbahaya baru di PyPI menjalankan kode saat instalasi "
        "dan hanya beredar singkat, sedangkan LLM merekomendasikan nama paket yang belum terdaftar. Pertahanan "
        "yang ada berada di sisi registry atau berupa masa tunggu tingkat rilis yang biayanya belum diukur. "
        "Permasalahan ini dirumuskan menjadi lima pertanyaan penelitian (RM1 sampai RM5) yang dijawab dengan "
        "dua kegiatan yang saling bergantung: evaluasi berbasis waktu yang menentukan kebijakan, dan perancangan "
        "interceptor yang menerapkan kebijakan tersebut pada titik keputusan instalasi.")
    m.p(
        "Kedua kegiatan dijalankan secara iteratif. Hasil evaluasi iterasi pertama dan kedua mengubah rancangan "
        "algoritma, dan rancangan akhir diuji pada data yang tidak dipakai selama perancangan. Luaran penelitian "
        "berupa perangkat pipguard dan pipeline evaluasi yang dapat direproduksi secara offline, sedangkan "
        "capaiannya berupa rekomendasi kebijakan berlapis yang didukung bukti.")


def metode(m):
    m.h2("Metode Pengembangan Sistem", key="dsrm")
    m.p(
        "Pengembangan sistem menerapkan Design Science Research Methodology (DSRM) dengan titik masuk yang "
        "berpusat pada masalah (problem-centered initiation). Tahap perancangan, demonstrasi, dan evaluasi "
        f"dijalankan dalam {kata(3)} iterasi. Tuunanen dkk. (2024) mencatat bahwa evaluasi yang hanya ditempatkan "
        "sebagai tahap akhir sulit mengikuti masalah yang berubah, dan menyarankan agar proyek penelitian desain "
        "dipecah menjadi bagian-bagian yang masing-masing dievaluasi. Karena itu, setiap iterasi pada penelitian "
        "ini diakhiri dengan evaluasi yang menentukan perubahan pada iterasi berikutnya. Penerapan tahapan DSRM "
        "disajikan pada {{tbl:dsrm}}.")
    m.tabel("Penerapan Tahapan DSRM pada Penelitian", ["No", "Tahapan DSRM", "Kegiatan", "Keluaran"], [
        ["1", "Identifikasi masalah dan motivasi", "Studi literatur halusinasi paket, paket berbahaya, evaluasi "
         "temporal, dan masa tunggu dependensi", "Rumusan masalah RM1–RM5"],
        ["2", "Penetapan tujuan solusi", "Model ancaman; kebutuhan fungsional dan non-fungsional; sasaran "
         "latensi", "Tabel kebutuhan (KF, KNF)"],
        ["3", "Perancangan dan pengembangan", "Iterasi 1: enam indikator dengan bobot rancangan. Iterasi 2: "
         "kalibrasi bobot pada data pengembangan (ditolak pada data validasi). Iterasi 3 (akhir): dua keputusan, "
         "bobot metadata pada data validasi, aturan I-10 opsional", "Biner pipguard, skrip pemasangan"],
        ["4", "Demonstrasi", "Pemasangan pada direktori home sementara; 43 skenario pemanggilan otomatis pada "
         "bash dan zsh", "Log keluaran setiap skenario"],
        ["5", "Evaluasi", "Evaluasi temporal, paparan dan biaya, studi kasus, probe halusinasi, uji intersepsi, "
         "latensi, uji unit", "Tabel dan gambar Bab IV"],
        ["6", "Komunikasi", "Laporan skripsi, naskah jurnal, arsip kode dan data", "Skripsi, artikel, arsip "
         "Zenodo"],
    ], lebar=[0.8, 3.0, 6.6, 3.6], size=10, align=["c", "l", "l", "l"], key="dsrm")


def analisa(m):
    m.h2("Analisa Sistem", key="analisa_sistem")
    m.p(
        "Analisa sistem menetapkan ancaman yang dihadapi, kebutuhan yang harus dipenuhi artefak, dan perilaku "
        "fungsionalnya dalam bentuk model UML.")
    m.h3("Analisa Kebutuhan Sistem", key="kebutuhan")
    m.h4("Model Ancaman")
    m.p(
        "Penyerang dapat mendaftarkan nama apa pun yang belum dipakai pada PyPI dan mengunggah paket yang "
        "muatannya berjalan saat instalasi. Penyerang dapat memilih nama yang dihalusinasikan LLM, nama yang "
        "meniru paket sah, atau nama biasa yang dipromosikan dengan cara lain; penyerang juga dapat menyiapkan "
        "proyek lebih dahulu, misalnya menerbitkan rilis yang tidak berbahaya lalu mempersenjatainya kemudian "
        "(pre-aging), atau mengambil alih proyek yang sudah ada. Korban adalah pengembang, skrip, job CI, atau "
        "agen AI yang menjalankan `pip install`, `pip download`, atau `pip wheel` dengan nama yang berasal dari "
        "sumber yang tidak tepercaya. Mesin korban diasumsikan belum terkompromi sebelum instalasi.")
    m.p(
        "Agen AI diperlakukan sebagai pihak yang mungkin dimanipulasi: prompt injection, misalnya dalam sebuah "
        "README, dapat memerintahkannya mencoba ulang, mengatur variabel lingkungan, atau memanggil pemasang "
        "dengan cara lain. pipguard melindungi dari kekeliruan yang jujur, bukan dari proses yang sengaja "
        "diarahkan untuk menghindari pemeriksaan, kecuali bila dipasang pada citra sandbox yang dikunci. Di luar "
        "cakupan adalah dependensi transitif yang diresolusi pip, pemasang selain pip, Windows, `python -m pip` "
        "dari pemanggil yang tidak membaca konfigurasi shell, dan pemanggilan yang melewati resolusi PATH.")
    m.h4("Kebutuhan Fungsional")
    m.p("Kebutuhan fungsional menyatakan layanan yang harus disediakan sistem, sebagaimana disajikan pada "
        "{{tbl:kf}}.")
    m.tabel("Daftar Kebutuhan Fungsional Sistem", ["Kode", "Kebutuhan", "Deskripsi"], [
        ["KF-01", "Intersepsi perintah", "Menangkap `pip`, `pip3`, `python -m pip`, dan `python3 -m pip` pada "
         "shell interaktif, termasuk di dalam virtual environment aktif"],
        ["KF-02", "Intersepsi non-interaktif", "Menangkap `pip` dan `pip3` yang dipanggil skrip, subproses, job "
         "CI, dan agen AI melalui PATH"],
        ["KF-03", "Subperintah yang diperiksa", "Memeriksa `install`, `download`, dan `wheel`; meneruskan "
         "subperintah lain tanpa pemeriksaan"],
        ["KF-04", "Ekstraksi nama paket", "Memisahkan nama paket dari opsi pip, mengikuti berkas -r (termasuk "
         "bersarang), dan menormalisasi nama menurut PEP 503"],
        ["KF-05", "Kebijakan indeks", "Melewati pemeriksaan bila indeks utama bukan PyPI (dengan catatan); "
         "memperingatkan dependency confusion bila ada indeks tambahan"],
        ["KF-06", "Pengambilan metadata", "Mengambil metadata dari cache lokal (24 jam) atau API JSON PyPI "
         "dengan batas waktu tiga detik"],
        ["KF-07", "Penilaian risiko", "Menghitung indikator I-01 sampai I-10, keputusan konfirmasi, skor, dan "
         "tingkat SAFE, WARNING, atau DANGER"],
        ["KF-08", "Peringatan dan konfirmasi", "Menampilkan nama paket, tingkat, dan alasan pada stderr, lalu "
         "meminta konfirmasi [y/N] dengan bawaan batal"],
        ["KF-09", "Keputusan tanpa terminal", "Tanpa terminal interaktif: membatalkan, mencetak satu baris "
         "rekaman JSON, dan keluar dengan status 3"],
        ["KF-10", "Penerusan perintah", "Meneruskan perintah dengan seluruh argumen aslinya kepada pip asli "
         "melalui `exec`"],
        ["KF-11", "Konfigurasi", "Allowlist, aturan I-10 opsional, dan konfigurasi sistem yang dapat dikunci; "
         "variabel pengecualian hanya berlaku bila diizinkan konfigurasi"],
        ["KF-12", "Pencatatan", "Mencatat setiap penilaian pada log aktivitas berformat JSONL"],
        ["KF-13", "Pemasangan dan pelepasan", "Memasang dan melepas shim serta blok fungsi shell bertanda "
         "dengan satu perintah"],
    ], lebar=[1.5, 3.6, 8.9], size=10, align=["c", "l", "l"], key="kf")
    m.h4("Kebutuhan Non-Fungsional")
    m.p("Kebutuhan non-fungsional menyatakan batasan kualitas atas layanan tersebut ({{tbl:knf}}).")
    m.tabel("Daftar Kebutuhan Non-Fungsional Sistem", ["Kode", "Aspek", "Kriteria"], [
        ["KNF-01", "Kinerja", "Tambahan waktu tunda paling banyak 50 ms dengan cache terisi dan 500 ms "
         "dengan cache kosong"],
        ["KNF-02", "Keputusan sebelum eksekusi", "Keputusan diambil sebelum perintah sampai ke pip, hanya dari "
         "metadata registry"],
        ["KNF-03", "Ketersediaan", "Fail-open: kegagalan jaringan atau internal tidak pernah memblokir "
         "instalasi"],
        ["KNF-04", "Portabilitas", "Satu biner statis untuk Linux dan macOS (amd64, arm64) tanpa dependensi "
         "runtime"],
        ["KNF-05", "Keamanan dan privasi", "Dipasang di ruang pengguna; hanya nama paket yang dikirim, dan hanya "
         "kepada PyPI; tidak dapat dimatikan oleh proses yang hanya mengendalikan variabel lingkungan"],
        ["KNF-06", "Kegunaan", "Peringatan hanya bila ada bukti, memuat alasan, dapat dibedakan dari keluaran "
         "pip, dan dapat dibaca mesin bila tanpa terminal"],
    ], lebar=[1.6, 3.4, 9.0], size=10, align=["c", "l", "l"], key="knf")

    m.h3("Pemodelan Fungsional Sistem", key="uml")
    m.p(
        "Pemodelan fungsional disajikan dengan Unified Modeling Language yang meliputi use case diagram, "
        "activity diagram, sequence diagram, dan class diagram.")
    m.h4("Use Case Diagram")
    m.p(
        f"Use case diagram pada {{{{gbr:usecase}}}} menggambarkan interaksi antara {kata(4)} aktor dan sistem. "
        "Pengembang adalah aktor utama yang menjalankan perintah, menjawab konfirmasi, dan memasang sistem. "
        "Skrip, job CI, dan agen AI adalah pemanggil non-interaktif yang tidak dapat menjawab prompt. Registry "
        "PyPI adalah sistem eksternal penyedia metadata, sedangkan administrator sistem dapat mengunci "
        "konfigurasi melalui berkas milik root.")
    m.gambar(FIG / "gbr_usecase.png", "Use Case Diagram Sistem pipguard", 13.5, key="usecase")
    m.tabel("Deskripsi Use Case", ["Kode", "Nama Use Case", "Aktor", "Deskripsi Singkat"], [
        ["UC-01", "Menjalankan perintah pip", "Pengembang; skrip, CI, agen AI", "Perintah install, download, atau "
         "wheel ditangkap oleh salah satu lapisan intersepsi"],
        ["UC-02", "Mengurai argumen dan berkas -r", "Sistem", "Nama paket, berkas requirements, dan opsi indeks "
         "diekstraksi lalu dinormalisasi"],
        ["UC-03", "Mengambil metadata", "Registry PyPI", "Metadata diambil dari cache atau API JSON; error "
         "membuat paket dilewati (fail-open)"],
        ["UC-04", "Menilai risiko", "Sistem", "Indikator, keputusan konfirmasi, skor, dan tingkat dihitung"],
        ["UC-05", "Menampilkan peringatan dan konfirmasi", "Pengembang", "Bila tingkat bukan SAFE dan terminal "
         "interaktif tersedia; jawaban bawaan batal"],
        ["UC-06", "Membatalkan dengan rekaman JSON", "Skrip, CI, agen AI", "Bila tingkat bukan SAFE dan tidak "
         "ada terminal; status keluar 3"],
        ["UC-07", "Meneruskan perintah", "Sistem", "Bila semua paket SAFE atau dikonfirmasi; pip asli "
         "dijalankan melalui exec"],
        ["UC-08", "Mengunci konfigurasi sistem", "Administrator sistem", "Berkas /etc/pipguard/config.json "
         "dengan locked mengabaikan berkas pengguna dan variabel lingkungan"],
        ["UC-09", "Memasang, melepas, mengatur konfigurasi", "Pengembang", "make install / make uninstall; "
         "allowlist dan opsi I-10 di berkas pengguna"],
    ], lebar=[1.4, 3.4, 3.0, 6.2], size=10, align=["c", "l", "l", "l"], key="uc")
    m.h4("Activity Diagram")
    m.p(
        "Activity diagram pada {{gbr:aktivitas}} menggambarkan alur kerja sejak perintah dipanggil hingga "
        "diteruskan atau dibatalkan. Bagian bertanda garis putus-putus diulang untuk setiap paket di luar "
        "allowlist. Perintah diteruskan ke pip asli hanya setelah seluruh paket lolos atau dikonfirmasi; satu "
        "pembatalan menghentikan seluruh perintah.")
    m.gambar(FIG / "gbr_aktivitas.png", "Activity Diagram Proses Intersepsi dan Penilaian", 13.0, key="aktivitas")
    m.h4("Sequence Diagram")
    m.p(
        "Sequence diagram pada {{gbr:sekuens}} menggambarkan pertukaran pesan antarkomponen untuk satu paket. "
        "Fragmen alt memisahkan perilaku pada terminal interaktif dan tanpa terminal.")
    m.gambar(FIG / "gbr_sekuens.png", "Sequence Diagram Pemeriksaan Satu Paket", 14.0, key="sekuens")
    m.h4("Class Diagram")
    m.p(
        "Go tidak mengenal pewarisan kelas, sehingga class diagram pada {{gbr:kelas}} memetakan paket, struct, "
        "dan fungsi Go ke notasi kelas UML. Paket `main` mengoordinasikan `parser`, `config`, `cache`, "
        "`registry`, `scorer`, `ui`, dan `logger`; tidak ada paket yang bergantung pada pustaka di luar pustaka "
        "standar Go.")
    m.gambar(FIG / "gbr_kelas.png", "Class Diagram Sistem (Pemetaan Paket dan Struct Go)", 14.0, key="kelas")


def perancangan(m):
    m.h2("Perancangan Sistem", key="perancangan")
    m.h3("Perancangan Arsitektur Sistem", key="arsitektur")
    m.p(
        "Arsitektur sistem terdiri atas dua lapisan intersepsi dan satu inti pemeriksa berupa biner Go statis "
        "({{gbr:arsitektur}}). Lapisan pertama adalah fungsi shell `pip`, `pip3`, `python`, dan `python3` yang "
        "dipasang ke berkas konfigurasi bash atau zsh dalam blok bertanda yang dapat dihapus. Fungsi ini "
        "mengungguli pencarian PATH sehingga juga bekerja di dalam virtual environment aktif, dan fungsi "
        "`python` menangkap `python -m pip`. Lapisan kedua adalah shim berupa tautan bernama `pip` dan `pip3` di "
        "`~/.local/bin` yang mencakup pemanggil non-interaktif, tetapi hanya bila pemanggil tersebut menjalankan "
        "`pip` atau `pip3`. Menjadikan `python` sendiri sebagai shim akan menyisipkan pipguard pada setiap "
        "penyalaan interpreter, sehingga `python -m pip` dari pemanggil non-interaktif sengaja dibiarkan di luar "
        "cakupan.")
    m.gambar(FIG / "gbr_arsitektur.png", "Arsitektur Sistem pipguard", 14.0, key="arsitektur")
    m.p(
        "Biner mencari pip asli pada PATH sambil melewati dirinya sendiri dan salinan pipguard lain, memeriksa "
        "paket yang diminta, lalu mengganti prosesnya sendiri dengan pip melalui pemanggilan sistem `exec`, "
        "sehingga sinyal dan status keluar diteruskan apa adanya. Bila indeks utama bukan PyPI (`-i`, "
        "`--index-url`, atau `PIP_INDEX_URL`), metadata PyPI tidak menggambarkan paket yang akan dipasang "
        "sehingga pemeriksaan dilewati dengan catatan; dengan `--extra-index-url`, pemeriksaan tetap berjalan dan "
        "peringatan menyebutkan risiko dependency confusion. Metadata berasal dari cache lokal "
        "`~/.cache/pipguard/cache.json` dengan masa berlaku 24 jam atau dari API JSON PyPI dengan batas waktu "
        "tiga detik; setiap error meneruskan perintah dengan catatan (fail-open).")

    m.h3("Perancangan Algoritma Penilaian Risiko", key="algoritma")
    c = json.loads((REPO / "paper/data/calibration.json").read_text())
    ci, b = c["beta_ci95_bootstrap"], c["beta"]

    def bci(k):
        return f"{dec(b[k], 2)} [{dec(ci[k][0], 2)}–{dec(ci[k][1], 2)}]"
    m.p(
        "Algoritma penilaian risiko dikembangkan dalam tiga iterasi. Iterasi pertama memakai enam indikator "
        "(I-01 sampai I-06) dengan bobot yang ditetapkan perancang dan ambang WARNING 20 serta DANGER 60. "
        "Iterasi kedua mengkalibrasi seluruh bobot dan ambang pada data pengembangan, tetapi gagal pada data "
        "validasi dan karena itu ditolak ({{sub:hasil_drift}}). Rancangan akhir mengikuti temuan analisis "
        "pergeseran dan memisahkan dua keputusan. *Apakah* instalasi memerlukan konfirmasi hanya ditentukan "
        "oleh sinyal yang stabil: nama yang tidak terdaftar (I-01) dinilai DANGER, dan proyek yang rilis "
        "pertamanya berumur kurang dari 30 hari (I-02) menerima tepat 50 poin, yaitu ambang WARNING. "
        "*Seberapa berat* peringatannya ditentukan oleh metadata: indikator I-03 sampai I-09 bersama-sama "
        "bernilai paling banyak 49 poin, sehingga metadata saja tidak pernah dapat menandai proyek mapan, dan "
        "proyek baru mencapai DANGER pada 50 + τ poin dengan τ = 7. Rincian indikator disajikan pada "
        "{{tbl:indikator}}.")
    m.tabel("Indikator dan Bobot Penilaian Risiko", ["Kode", "Indikator", "Awal", "Akhir", "β [IK 95%]",
                                                    "Peran"], [
        ["I-01", "Tidak terdaftar pada PyPI (HTTP 404)", "100", "100", "keputusan", "pip tetap gagal; peringatan "
         "menjelaskan slopsquatting"],
        ["I-02", "Rilis pertama proyek < 30 hari sebelum pemeriksaan", "40", "50", "keputusan", "Stabil "
         "sepanjang waktu; masa tunggu tingkat proyek"],
        ["I-03", "Tepat satu rilis", "20", "0", f"0,00 [0,00–{dec(ci['I-03'][1], 2)}]", "Tidak informatif "
         "setelah indikator lain"],
        ["I-04", "Tanpa tautan homepage atau repositori", "15", "5", bci("I-04"), "Tingkat"],
        ["I-05", "Nama berjarak satu operasi dari 5.000 paket teratas (nama ≥ 5 karakter)", "30", "15",
         bci("I-05"), "Typosquatting"],
        ["I-06", "Ringkasan < 10 karakter", "10", "0", f"{dec(b['I-06'], 2)} [0,00–{dec(ci['I-06'][1], 2)}]",
         "Tidak dipakai"],
        ["I-07", "Rilis terbaru hanya sdist (skrip build berjalan saat instalasi)", "–", "10", bci("I-07"),
         "Tingkat"],
        ["I-08", "Deskripsi panjang (README) < 100 karakter", "–", "12", bci("I-08"), "Tingkat"],
        ["I-09", "Tanpa Trove classifier", "–", "1", f"{dec(b['I-09'], 2)} [0,00–{dec(ci['I-09'][1], 2)}]",
         "Tingkat"],
        ["I-10", "Rilis < 30 hari setelah ≥ G hari tanpa rilis, pada proyek ≥ 30 hari", "–", "0 (opsional: 50)",
         "keputusan", "Proyek disusupi atau pre-aged; nonaktif bawaan"],
        ["", "Ambang WARNING / DANGER", "20 / 60", "50 / 57", "τ = 7", ""],
    ], lebar=[1.1, 4.6, 1.2, 1.5, 2.6, 3.0], size=9, align=["c", "l", "c", "c", "c", "l"],
        catatan="Awal = bobot rancangan iterasi pertama; Akhir = model yang dipasang; β = koefisien pada data "
                "validasi 2025 dengan interval bootstrap 95% (poin akhir = 10β, dibulatkan).", key="indikator")
    m.p(
        "Poin metadata adalah sepuluh kali koefisien regresi logistik dengan penalti ridge (λ = 1, intersep "
        "tidak dipenalti) dan pembobotan kelas seimbang yang ditaksir dengan metode Newton-Raphson pada data "
        "validasi 2025, yaitu 602 paket berbahaya baru dan 1.598 paket sah baru. Koefisien dibatasi tidak negatif "
        "melalui penaksiran ulang active-set yang menetapkan koefisien negatif pada nol; karena itu beberapa "
        "interval bootstrap dimulai dari 0,00. Poin dibulatkan ke bilangan bulat; penskalaan hanya mengubah "
        "log-odds menjadi poin bulat dan mempertahankan urutannya. τ memaksimalkan indeks Youden pada data "
        "validasi yang sama. Indikator I-05 memakai jarak optimal string alignment terhadap 5.000 paket teratas "
        "yang ditanam di dalam biner, dengan panjang nama minimum lima karakter. Aturan tingkat rilis I-10 "
        "diimplementasikan tetapi nonaktif secara bawaan; alasannya diuraikan pada {{sub:hasil_kebijakan}}. "
        "Aturan klasifikasi tingkat risiko disajikan pada {{tbl:tingkat}}.")
    m.tabel("Aturan Klasifikasi Tingkat Risiko Rancangan Akhir", ["Tingkat", "Aturan", "Perlakuan Sistem"], [
        ["DANGER", "Tidak terdaftar (I-01), atau proyek < 30 hari dengan poin metadata ≥ 7 (skor ≥ 57)",
         "Peringatan dan konfirmasi [y/N]; tanpa terminal: batal, status 3"],
        ["WARNING", "Proyek < 30 hari (skor 50–56); atau I-10 bila diaktifkan", "Sama dengan DANGER, dengan "
         "label dan saran yang berbeda"],
        ["SAFE", "Selain itu (poin metadata ≤ 49 < ambang WARNING)", "Diteruskan tanpa keluaran tambahan"],
    ], lebar=[2.0, 6.6, 5.4], size=10, align=["c", "l", "l"], key="tingkat")
    m.p("Rancangan algoritma secara ringkas disajikan dalam bentuk pseudokode pada {{gbr:pseudo}}.")
    m.kotak_kode("Pseudokode Algoritma Keputusan dan Penilaian Risiko", [
        "FUNGSI nilai(nama, meta, sekarang, G):",
        "  jika meta.ada = salah: KEMBALIKAN (100, DANGER, [\"tidak terdaftar\"])",
        "  skor := 0; alasan := []",
        "  jika sekarang - meta.rilisPertama < 30 hari:          # I-02",
        "      skor := skor + 50; tambah alasan",
        "  jika G > 0 dan umur proyek >= 30 hari dan",
        "     sekarang - meta.rilisTerbaru < 30 hari dan",
        "     meta.rilisTerbaru - meta.rilisSebelumnya >= G:    # I-10",
        "      skor := skor + 50; tambah alasan",
        "  untuk I dalam {I-04, I-05, I-07, I-08, I-09}:",
        "      jika I terpenuhi: skor := skor + poin[I]; tambah alasan",
        "  tingkat := DANGER jika skor >= 57,",
        "             WARNING jika skor >= 50, selain itu SAFE",
        "  KEMBALIKAN (skor, tingkat, alasan)",
        "",
        "UNTUK setiap paket p (bukan allowlist):",
        "  meta, err := cache.ambilAtauUnduh(p)",
        "  jika err: cetak catatan; LANJUT                    # fail-open",
        "  hasil := nilai(p, meta, sekarang, G); catat(hasil)",
        "  jika hasil.tingkat <> SAFE dan tidak konfirmasi(p, hasil):",
        "      KELUAR dengan status 3",
        "exec(pip asli, argumen asli)",
    ], key="pseudo", size=9)
    m.p(
        "Pemeriksaan keberadaan diletakkan pertama dan menghentikan evaluasi karena bersifat definitif: nama "
        "yang tidak terdaftar tidak memiliki metadata untuk dinilai. Karena poin metadata maksimum (49) lebih "
        "kecil daripada ambang WARNING (50), keputusan konfirmasi rancangan akhir identik dengan masa tunggu "
        "tingkat proyek 30 hari ditambah pemeriksaan keberadaan; indikator metadata hanya menentukan label "
        "WARNING atau DANGER.")

    m.h3("Perancangan Antarmuka Pengguna", key="antarmuka")
    m.p(
        "Antarmuka berupa keluaran baris perintah pada standard error agar tidak tercampur dengan keluaran pip. "
        "Susunan peringatan dirancang dari informasi yang paling menentukan menuju penjelas: nama paket lebih "
        "dahulu agar pengguna dapat membandingkannya dengan nama yang dimaksud, lalu tingkat, alasan, dan "
        "kalimat penutup yang bergantung pada alasan ({{gbr:mock}}). Prompt `[y/N]` menuliskan N dengan huruf "
        "kapital untuk menandai bahwa menekan Enter berarti membatalkan.")
    m.kotak_kode("Rancangan Tampilan Peringatan dan Konfirmasi", [
        "──────────────────────────────────────────────────────",
        "pipguard: <nama paket>",
        "Level   : <WARNING | DANGER> (score <skor>)",
        "Reasons :",
        "  - <alasan indikator pertama>",
        "  - <alasan indikator berikutnya>",
        "<saran: penjelasan slopsquatting atau masa tunggu 30 hari>",
        "──────────────────────────────────────────────────────",
        "Continue installation? [y/N]:",
    ], key="mock", size=9)
    m.p(
        "Tanpa terminal interaktif, yang dideteksi dengan ioctl terminal agar `/dev/null` tidak dianggap "
        "terminal, pipguard tidak pernah menunggu masukan. Sistem membatalkan, mencetak satu baris "
        "`pipguard: {\"decision\":\"blocked\", \"package\":..., \"level\":..., \"score\":..., \"reasons\":[...], "
        "\"advice\":..., \"exit_status\":3}`, dan keluar dengan status 3, yang berbeda dari status keluar pip "
        "sendiri. Dengan demikian sistem CI dan agen AI dapat meneruskan keputusan tersebut kepada manusia, "
        "alih-alih memperlakukannya sebagai instalasi yang gagal. Variabel `PIPGUARD_ASSUME_YES` dan "
        "`PIPGUARD_DISABLE` hanya berlaku bila berkas konfigurasi mengizinkannya (`allow_env_override`), dan "
        "konfigurasi sistem milik root dapat mengunci pengaturan (`locked`).")

    m.h3("Perancangan Evaluasi", key="evaluasi")
    m.p(
        "Evaluasi dirancang untuk menjawab RM1 sampai RM5 dan untuk menguji pemenuhan kebutuhan pada "
        "{{sub:kebutuhan}}. Rancangannya meliputi data, protokol temporal, skenario waktu instalasi, ukuran "
        "dan inferensi statistik, kebijakan yang dibandingkan, probe halusinasi, serta pengujian sistem.")
    nm = N["missingness"]
    m.h4("Data Evaluasi")
    m.p(
        "Paket berbahaya diambil dari seluruh laporan OSV berpengenal MAL untuk PyPI yang diekspor pada "
        "14 Oktober 2026, yaitu 11.800 nama setelah laporan yang ditarik dan dua nama paket sah populer "
        "dikeluarkan. Karena PyPI menghapus paket yang dilaporkan, metadatanya direkonstruksi dari ClickPy, "
        "cermin publik tabel metadata distribusi PyPI yang tetap menyimpan baris proyek yang dihapus dan dapat "
        f"diakses tanpa akun. Riwayat per versi tersedia untuk {num(nm['reconstructed'])} nama (72,8%). Untuk "
        "setiap paket ditentukan versi berbahaya pertama, lalu metadata disusun persis seperti yang akan dibaca "
        "klien registry pipguard pada saat tertentu; untuk proyek sah yang salah satu rilisnya disusupi, rilis "
        "sebelumnya tetap terlihat, sebagaimana dilihat korban.")
    m.p(
        "Sebagai negatif sulit, 7.000 proyek yang pertama kali diunggah antara Januari 2023 dan Juni 2026 diambil "
        "dalam urutan pseudo-acak yang deterministik; 166 proyek yang dilaporkan OSV dan 782 proyek yang telah "
        "dihapus dari PyPI dikeluarkan, lalu 4.850 proyek pertama yang memiliki berkas yang dapat dipasang "
        "dipertahankan. Paket mapan terdiri atas 4.000 proyek peringkat 1.001 sampai 15.000 menurut unduhan "
        "30 hari, dibagi deterministik menjadi separuh pengembangan dan separuh uji, ditambah 1.000 proyek "
        "teratas yang menjadi data pengembangan iterasi pertama. ClickPy juga mencerminkan log unduhan PyPI per "
        "hari, proyek, versi, dan pemasang. Unduhan oleh pip, uv, poetry, pdm, dan pipenv disebut *unduhan klien "
        "instalasi*; cermin, peramban, dan skrip dikeluarkan karena mengambil berkas baru tanpa niat pengguna. "
        "Ringkasan data evaluasi disajikan pada {{tbl:data}}.")
    m.tabel("Data Evaluasi", ["Kelompok", "Total", "Pengembangan (< 2025)", "Validasi (2025)", "Uji (2026)",
                              "Sumber"], [
        ["Paket berbahaya", "8.588", "7.431", "611", "546", "Laporan OSV MAL; metadata direkonstruksi dari "
         "ClickPy"],
        ["  di antaranya berlabel typosquatting", "382", "239", "57", "86", "Teks laporan OSV"],
        ["Paket sah baru", "4.850", "2.213", "1.598", "1.039", "Proyek PyPI acak 2023–2026, masih ada, bukan "
         "OSV"],
        ["Paket mapan, peringkat 1.001–15.000", "4.000", "2.000", "–", "2.000", "Top PyPI packages, 1 Oktober "
         "2026"],
        ["Paket mapan, 1.000 teratas", "1.000", "1.000", "–", "–", "Seperti iterasi pertama"],
        ["Hold-out prospektif (berbahaya)", "97", "–", "–", "–", "Laporan OSV 19–24 Oktober 2026"],
        ["Probe halusinasi", "2.000 prompt", "–", "–", "–", "Empat model terbuka, 500 prompt per model"],
    ], lebar=[3.8, 1.5, 2.1, 1.7, 1.5, 3.4], size=9, align=["l", "r", "r", "r", "r", "l"], key="data")
    m.p(
        "Cakupan rekonstruksi menurun dari 85,8% untuk laporan semester pertama 2023 menjadi 47,6% untuk "
        f"semester pertama 2026 ({{{{tbl:cakupan}}}}), padahal {num(nm['downloadable'])} dari "
        f"{num(nm['osv_names'])} nama tercatat pada log unduhan yang independen dari tabel metadata. Paket yang "
        "hilang dengan demikian adalah paket nyata yang dapat diunduh tetapi metadatanya tidak sempat tercermin, "
        "kemungkinan besar karena cepat dihapus. Rekonstruksi sesuai dengan log unduhan independen pada hari "
        f"pembuatan untuk {pct(nm['first_download_minus_first_upload_days']['same_day'])}% dari 8.588 proyek, "
        f"dan {pct(nm['osv_listed_versions_found'])}% versi yang tercantum pada laporan OSV ditemukan. Pada 487 "
        "paket sah acak yang ada pada kedua sumber, setiap indikator sama antara ClickPy dan API JSON PyPI pada "
        "sedikitnya 97,1% paket.")
    h, rows = tabel_id("t_missingness", ["Periode laporan OSV", "Nama", "Dapat diunduh (%)", "Direkonstruksi",
                                         "Direkonstruksi (%)"], {"All": "Semua"})
    rows = [[r[0].replace(" H1", " S1").replace(" H2", " S2")] + r[1:] for r in rows]
    m.tabel("Cakupan Rekonstruksi Nama Paket Berbahaya OSV per Periode Laporan", h, rows,
            lebar=[3.2, 2.0, 3.0, 2.6, 3.0], size=10, align=["l", "r", "r", "r", "r"],
            catatan="Dapat diunduh = memiliki sedikitnya satu unduhan pada log unduhan. Direkonstruksi = metadata "
                    "per versi tersedia, yang diperlukan evaluasi. S1/S2 = semester pertama/kedua.", key="cakupan")
    m.h4("Protokol Temporal")
    em = N["early_model"]
    m.p(
        "Paket berbahaya dan paket sah baru dibagi menurut waktu unggahan (berbahaya) pertamanya menjadi data "
        "pengembangan (sebelum 2025), validasi (2025), dan uji (2026) sebagaimana {{gbr:protokol}}. Iterasi "
        "pertama dievaluasi pada 54 nama halusinasi dan 1.000 paket teratas; karena seluruh positif tidak "
        "terdaftar dan seluruh negatif terdaftar, status registry saja sudah memisahkan kelas sehingga data "
        "tersebut tidak dapat menguji indikator lain. Pada iterasi kedua, kalibrasi yang telah ditetapkan "
        "sebelumnya menaksir seluruh bobot dan ambang pada data pengembangan (kalibrasi awal). Pada data "
        f"validasi, kalibrasi ini hanya menandai {pct(em['val']['v2-initial']['recall'])}% paket berbahaya, "
        f"sedangkan aturan keberadaan-dan-umur menandai {pct(em['val']['new-or-missing']['recall'])}%; hasil "
        "validasi ini saja sudah menolak model menurut aturan bahwa kandidat tidak boleh memiliki recall "
        "validasi di bawah aturan dasar tersebut. Perlu diungkapkan bahwa data 2026 sempat dinilai satu kali "
        "oleh kalibrasi awal sebelum perancangan ulang.")
    m.gambar(FIG / "gbr_protokol.png", "Protokol Evaluasi Temporal", 14.0, key="protokol")
    m.p(
        "Rancangan akhir menetapkan struktur berdasarkan analisis pergeseran pada data pengembangan dan "
        "validasi, menaksir bobot metadata hanya pada data validasi, dan dibekukan pada 19 Oktober 2026. Untuk "
        "memperoleh bukti yang tidak tersentuh langkah perancangan apa pun, 97 paket berbahaya PyPI yang pertama "
        "kali dilaporkan OSV setelah pembekuan (19–24 Oktober 2026) dinilai satu kali dengan model yang "
        "dibekukan (hold-out prospektif). Status bawaan aturan I-10 diputuskan dengan aturan yang ditetapkan "
        "sebelum data uji dinilai dengannya, hanya memakai data pengembangan, validasi, dan biaya unduhan Juni "
        "2025.")
    m.h4("Skenario Waktu Instalasi")
    m.p(
        f"Waktu korban memasang paket berbahaya tidak diketahui. Setiap paket karena itu dinilai pada {kata(3)} "
        "saat: satu menit setelah versi berbahaya pertama diunggah (skenario utama), satu menit setelah versi "
        "terakhir yang diketahui, dan pada saat laporan OSV diterbitkan. Paket sah baru dinilai pada saat yang "
        "setara. Skenario utama menguntungkan aturan berbasis umur, sehingga analisis paparan menimbang setiap "
        "paket menurut kapan paket tersebut benar-benar dipasang.")
    m.h4("Ukuran dan Inferensi Statistik")
    m.p(
        "Sebuah paket dinyatakan *ditandai* bila instalasinya memerlukan konfirmasi (untuk masa tunggu tingkat "
        "rilis: bila rilis terbarunya ditahan). Recall dilaporkan per kelompok positif dan FPR per kelompok "
        "negatif dengan interval Wilson. Paket berbahaya dikelompokkan ke dalam kampanye: dua paket dihubungkan "
        "bila unggahan berbahaya pertamanya berselisih paling lama tujuh hari dan keduanya berbagi alamat "
        "surel pengunggah, deskripsi sepanjang sedikitnya 100 karakter, atau ringkasan bersama alat pengunggah; "
        "kampanye adalah komponen terhubung. Interval untuk paket berbahaya dihitung dengan bootstrap per "
        "kampanye (2.000 replikasi), perbandingan berpasangan dengan uji McNemar eksak, dan pemisahan paket "
        "berbahaya baru dari paket sah baru oleh skor dengan AUC.")
    m.p(
        "*Paparan* mengukur perlindungan dalam satuan unduhan. Untuk setiap rilis berbahaya, unduhan klien "
        "instalasi dihitung per hari kalender sejak unggahan berbahaya pertama; sebuah kebijakan *menghentikan* "
        "unduhan bila kebijakan tersebut aktif pada hari itu (untuk aturan tingkat proyek: bila umur proyek "
        "dalam hari kalender pada hari unduhan kurang dari *T*). Karena penaksir menentukan makna hasil, "
        f"dilaporkan {kata(3)} penaksir per periode dengan interval 95% per kampanye: rata-rata per paket dari "
        "porsi unduhan setiap paket yang dihentikan, rata-rata per kampanye, dan porsi berbobot unduhan, yaitu "
        "seluruh unduhan yang dihentikan dibagi seluruh unduhan. Penaksir terakhir didominasi oleh segelintir "
        "nama berumur panjang sehingga juga dilaporkan dengan satu dan sepuluh paket teratas dikeluarkan. Setiap "
        "unggahan baru menerima unduhan otomatis, misalnya dari pemindai yang memasang paket baru dalam "
        "sandbox; sebagai kontrol, unduhan klien 4.850 paket sah baru diukur per hari umur, dan paparan dihitung "
        "ulang dari unduhan berbahaya yang melebihi median latar tersebut.")
    m.p(
        "*Biaya* adalah porsi seluruh unduhan klien instalasi dalam satu bulan kalender yang akan diubah sebuah "
        "kebijakan, diukur pada 24 bulan dari Oktober 2024 sampai September 2026: untuk masa tunggu tingkat "
        "proyek, unduhan proyek yang diunggah pertama kali kurang dari *T* hari sebelumnya; untuk tingkat rilis, "
        "unduhan versi yang diunggah kurang dari *T* hari sebelumnya, yang akan diganti versi lama atau gagal. "
        "Titik akhir anonim ClickPy berhenti membaca setelah 10⁹ baris lalu mengembalikan jumlah parsial tanpa "
        "error, sehingga setiap kueri difilter per proyek, kueri biaya bulanan dibagi menjadi rentang nama "
        "proyek, dan ringkasan respons server diperiksa untuk memastikan seluruh baris terbaca. Sebagai ukuran "
        "gangguan, dihitung pula dependensi yang ditambahkan setiap rilis PyPI pada 24 bulan yang sama "
        "dibandingkan rilis sebelumnya, beserta umur proyek dependensi tersebut pada hari itu.")
    m.h4("Kebijakan yang Dibandingkan")
    m.p(
        "Kebijakan yang dibandingkan adalah pemeriksaan keberadaan (I-01), kemiripan nama saja (I-05), "
        "rancangan awal, kalibrasi awal yang ditolak, model akhir pipguard, model akhir dengan I-10 pada G = 90 "
        "dan 365 hari, masa tunggu tingkat proyek *T* hari, serta masa tunggu tingkat rilis *T* hari yang "
        "memodelkan `--uploaded-prior-to` milik pip, `--exclude-newer` milik uv, dan `minimumReleaseAge` milik "
        "pnpm, dengan *T* dari satu sampai 90 hari. Untuk memisahkan kebijakan dari alat, diidentifikasi pula paket "
        "berbahaya yang dideklarasikan sebagai dependensi proyek lain. Enam insiden berdampak tinggi ditelusuri "
        "dengan data yang sama: kompromi `ultralytics` (2024), `num2words` (2025), dan `lightning` (2026), "
        "pengambilalihan `ctx` yang dorman (2022), `aiocpa` yang pre-aged (2024), dan paket dependency confusion "
        "`torchtriton` (2022). Selain itu, pip 26.2.2 dengan dan tanpa `--uploaded-prior-to`, uv dengan "
        f"`--exclude-newer`, dan pipguard dijalankan terhadap {kata(6)} paket hidup dalam mode dry run yang "
        "dibatasi pada wheel sehingga tidak ada kode yang dijalankan.")
    m.h4("Probe Halusinasi")
    m.p(
        "Spracklen dkk. (2025) tidak merilis nama halusinasinya karena dapat dipakai untuk slopsquatting. Probe "
        "rekomendasi paket mereka dipakai ulang apa adanya (pesan sistem, awalan pengguna, parameter sampling, "
        "dan batas 64 token) pada empat model terbuka yang dirilis 2023–2026: DeepSeek-Coder-1.3B-Instruct, "
        "Qwen2.5-Coder-1.5B-Instruct, Gemma-3-4B-it, dan Qwen3.5-4B. Setiap model menerima 500 prompt yang "
        "sama, 125 dari setiap dataset Python asal, dan dijalankan dengan llama.cpp pada CPU dengan kuantisasi "
        "8-bit atau 4-bit. Setiap nama diklasifikasikan menurut unggahan pertamanya pada riwayat PyPI yang "
        "bertanda waktu relatif terhadap tanggal rilis model: *sudah ada*, *tidak pernah terdaftar*, *terdaftar "
        "kemudian*, atau *dihapus*. Hanya angka agregat yang dilaporkan; nama halusinasi tidak dipublikasikan.")
    m.h4("Pengujian Sistem")
    m.p(
        "Pengujian unit Go mencakup pengurai argumen dan berkas *requirements*, opsi indeks, klien registry "
        "terhadap respons 404, 5xx, 429, rusak, dan lambat yang disimulasikan, cache, seluruh model "
        "penilaian termasuk I-10, penguncian konfigurasi, deteksi terminal, rekaman keputusan non-interaktif, "
        "dan pencegahan rekursi antara dua salinan terpasang. Pengujian intersepsi berupa skrip otomatis yang "
        "memasang pipguard ke direktori home sementara dan menjalankan 43 kasus pada bash dan zsh dengan nama "
        "paket buatan yang terverifikasi tidak terdaftar; setiap perintah memakai `--no-index`, kasus interaktif "
        "dijalankan pada pseudo-terminal, dan setiap kasus merekam status keluar, keluaran, dan entri log. "
        "Latensi diukur dengan pip diganti stub yang langsung keluar, 200 pengulangan per kondisi, dan biner "
        "pada sistem berkas Linux asli. Sebagai rujukan, diukur pula interpreter Python yang hanya menyala dan "
        "membaca berkas cache yang sama, yaitu biaya minimum alat setara yang ditulis dalam Python. Seluruh "
        "masukan daring dibekukan, dan satu skrip membangun ulang setiap angka, tabel, dan gambar tanpa akses "
        "jaringan serta menolak selesai bila bobot yang tertanam di biner berbeda dengan keluaran kalibrasi.")
