"""BAB I PENDAHULUAN."""
from ctx_id import N, kata, num, pct


def tulis(m):
    D, C = N["detection"], N["cost"]
    X = N["exposure_estimators"]["by_shift"]["shift0"]
    p30, r30 = X["project"]["30"]["test"], X["release"]["30"]["test"]
    m.bab(1, "Pendahuluan", key="pendahuluan")
    m.h2("Latar Belakang Masalah", key="latar")
    m.p(
        "Praktik pengembangan perangkat lunak modern telah mengalami pergeseran mendasar seiring masuknya "
        "large language model (LLM) sebagai asisten penulisan kode. Pengembang memakai asisten tersebut untuk "
        "menulis kode, menyusun struktur program, dan memilih pustaka pihak ketiga yang menjadi dependensi "
        "proyek. Semakin banyak pula perintah instalasi yang tidak lagi diketik oleh pengembang, melainkan "
        "dijalankan oleh agen pemrograman berbasis kecerdasan buatan (AI) yang mengeksekusi perintah shell atas "
        "nama penggunanya (Sergeyuk dkk., 2025; Gan dkk., 2026; Hu dkk., 2026). Adopsi yang cepat ini membawa "
        "peningkatan produktivitas, tetapi juga memperkenalkan permukaan serangan baru yang belum sepenuhnya "
        "dipahami.")
    m.p(
        "Keluaran asisten kode terbukti kurang aman daripada kesan yang ditimbulkannya. Sekitar 40% dari 1.689 "
        "program yang dihasilkan GitHub Copilot untuk skenario yang relevan dengan keamanan mengandung "
        "kerentanan (Pearce dkk., 2025), dan 29,5% potongan kode Python serta 24,2% potongan kode JavaScript "
        "hasil perangkat AI pada proyek GitHub publik mengandung kelemahan keamanan (Fu dkk., 2025). Pengembang "
        "pun menakar kepercayaannya terhadap perangkat tersebut terutama melalui sinyal komunitas, bukan melalui "
        "verifikasi (Cheng dkk., 2024). Kombinasi antara keluaran yang tidak terjamin dan kepercayaan yang tidak "
        "diverifikasi inilah yang menjadi titik awal permasalahan penelitian ini.")
    m.p(
        "Salah satu bentuk kegagalan LLM yang berdampak langsung pada rantai pasok perangkat lunak adalah "
        "*halusinasi paket* (package hallucination), yaitu rekomendasi nama paket yang tidak terdapat pada "
        "registry mana pun. Spracklen dkk. (2025) membangkitkan 576.000 sampel kode dengan enam belas model dan "
        "menemukan bahwa 19,7% paket yang direkomendasikan merupakan halusinasi; banyak di antaranya muncul "
        "berulang sehingga dapat diprediksi. Penyerang yang mendaftarkan nama halusinasi yang berulang pada "
        "registry publik akan menerima instalasi dari setiap pengembang, atau agen, yang mengikuti rekomendasi "
        "tersebut. Serangan ini disebut slopsquatting. Z. Huang dkk. (2026) membuktikan kelayakannya pada npm: "
        "dari 107 nama halusinasi yang mereka daftarkan selama enam bulan, sebagian besar instalasi berasal dari "
        "pengembang sungguhan dan terjadi dalam dua minggu pertama setelah pendaftaran.")
    m.p(
        "Slopsquatting merupakan jalan baru menuju hasil yang lama. Sebagian besar paket berbahaya pada PyPI dan "
        "npm adalah proyek baru yang menjalankan muatannya ketika dipasang dan hanya beredar singkat sebelum "
        "dilaporkan dan dihapus (Ladisa dkk., 2023; Williams dkk., 2025; Gokkaya dkk., 2026). Hal ini merupakan "
        "bentuk terbaru dari risiko rantai pasok yang telah menyertai penggunaan ulang perangkat lunak selama "
        "puluhan tahun (Cox, 2025). Pada ekosistem Python, pip membangun distribusi sumber (sdist) di mesin "
        "pengguna dan menjalankan skrip build milik paket, sehingga kode penyerang sudah berjalan sebelum paket "
        "diimpor oleh program. Pertahanan yang efektif karenanya harus mengambil keputusan *sebelum* perintah "
        "instalasi diteruskan kepada pip.")
    m.p(
        "Pengamatan bahwa paket berbahaya umumnya berumur pendek mendasari perubahan paling menonjol pada "
        "pertahanan waktu instalasi saat ini, yaitu *masa tunggu dependensi* (dependency cooldown). uv "
        "menyediakan opsi `--exclude-newer` sejak versi 0.1.15 (Maret 2024), pnpm menambahkan "
        "`minimumReleaseAge` pada versi 10.16 (September 2025) dan sejak versi 11 (April 2026) menahan rilis yang "
        "berumur kurang dari satu hari secara bawaan, pip menambahkan `--uploaded-prior-to` pada versi 26.0 "
        "(Januari 2026), dan pembungkus komersial menahan paket yang berumur kurang dari 48 jam. Seluruh "
        "mekanisme tersebut bekerja pada tingkat *rilis*, sehingga setiap versi baru dari setiap paket ikut "
        "tertunda, termasuk perbaikan keamanan. Apakah tingkat rilis merupakan granularitas yang tepat, ambang "
        "berapa yang dapat dibenarkan, dan berapa biaya penundaan tersebut dalam praktik belum pernah diukur.")
    m.p(
        "Pengukuran tersebut memerlukan data yang justru dihapus oleh registry. PyPI menghapus paket berbahaya "
        "setelah dilaporkan, sehingga metadata yang akan dilihat oleh sebuah pertahanan pada saat instalasi ikut "
        "hilang. Evaluasi yang mengabaikan urutan waktu data juga cenderung melebih-lebihkan kemampuan detektor "
        "(Arp dkk., 2024; Moufid dkk., 2026), karena indikator yang mencirikan paket berbahaya di masa lalu belum "
        "tentu bertahan di masa depan. Sementara itu, detektor paket berbahaya yang telah dikembangkan umumnya "
        "dirancang untuk registry atau peneliti yang memindai unggahan baru (Zhang dkk., 2025; Ladisa dkk., 2023; "
        "Mehedi dkk., 2026). Detektor tersebut menganalisis kode setelah diunggah, dengan biaya yang tidak "
        "memungkinkan pemakaian sinkron pada setiap instalasi, dan operatornya menghadapi batas positif palsu "
        "yang ketat: administrator PyPI menganggap tingkat positif palsu 0,1% pun tidak dapat diterima (Vu dkk., "
        "2023). Akibatnya, belum ada mekanisme di sisi klien yang terbukti efektif tepat pada titik keputusan "
        "instalasi.")
    m.p(
        "Perancangan pertahanan di sisi klien juga menghadapi tantangan teknis tersendiri. Mekanisme intersepsi "
        "yang paling lazim adalah shim, yaitu program pengganti yang diletakkan lebih awal pada PATH. Aktivasi "
        "virtual environment menempatkan salinan pip miliknya di posisi terdepan PATH, sehingga shim global "
        "terlewati tepat ketika pengembang mengikuti praktik yang dianjurkan. Pemanggil non-interaktif seperti "
        "skrip, job continuous integration (CI), dan agen AI tidak dapat menjawab prompt konfirmasi, dan agen "
        "yang dapat mengatur variabel lingkungan dapat mematikan pertahanan yang dikendalikan melalui variabel "
        "tersebut. Selain itu, pemeriksaan yang dijalankan pada setiap instalasi harus cukup cepat agar tidak "
        "mengganggu alur kerja, dan peringatan yang terlalu sering akan diabaikan oleh penggunanya (Vance dkk., "
        "2025; Tariq dkk., 2025).")
    m.p(
        "Berdasarkan uraian tersebut, terdapat kesenjangan antara kondisi yang seharusnya dan kondisi yang "
        "senyatanya. Idealnya, pengembang dan agen AI memperoleh keputusan yang dapat dijelaskan sebelum memasang "
        "paket yang tidak terdaftar atau proyek yang baru muncul, dengan kebijakan yang manfaat dan biayanya telah "
        "diukur pada paket berbahaya sebagaimana adanya ketika masih dapat dipasang. Kenyataannya, detektor "
        "berada di sisi registry, masa tunggu yang tersedia bekerja pada tingkat rilis tanpa bukti biaya, dan "
        "evaluasi yang ada belum memperhitungkan waktu. Penelitian ini menutup kesenjangan tersebut dengan dua "
        "langkah. Pertama, penelitian merekonstruksi metadata titik-waktu (point-in-time) 8.588 paket berbahaya "
        "PyPI yang telah dihapus, menautkannya dengan log unduhan PyPI dan laporan Open Source Vulnerabilities "
        "(OSV), lalu membandingkan kebijakan waktu instalasi dari sisi perlindungan dan biaya. Kedua, penelitian "
        "merancang dan membangun *pipguard*, sebuah interceptor sisi klien untuk pip yang ditulis dalam bahasa "
        "Go, yang menerapkan kebijakan hasil evaluasi sebelum pip dijalankan.")
    m.p(
        f"Hasil penelitian menunjukkan bahwa masa tunggu tingkat proyek selama 30 hari mencakup "
        f"{pct(D['pipguard-v2']['mal'])}% paket berbahaya tahun 2026 dan menghentikan "
        f"{pct(p30['per_package']['est'])}% unduhan rata-rata paket berbahaya, dibandingkan "
        f"{pct(r30['per_package']['est'])}% untuk masa tunggu tingkat rilis, tetapi dengan biaya berupa unduhan "
        f"sah yang terdampak sekitar {num(round(C['ratio']['30']['median']))} kali lebih kecil. Rincian temuan "
        "tersebut diuraikan pada {{bab:hasil}}.")

    m.h2("Rumusan Masalah", key="rumusan")
    m.p("Berdasarkan latar belakang yang telah diuraikan, rumusan masalah penelitian ini adalah sebagai berikut:")
    m.daftar([
        "Kapan paket berbahaya PyPI dilaporkan, dihapus, dan dipasang relatif terhadap waktu unggahannya (RM1)?",
        "Seberapa stabil indikator metadata paket berbahaya dari waktu ke waktu, dan apa implikasinya bagi "
        "rancangan algoritma penilaian risiko (RM2)?",
        "Bagaimana perbandingan perlindungan dan biaya antara pemeriksaan keberadaan paket, penilaian berbasis "
        "metadata, serta masa tunggu tingkat proyek dan tingkat rilis, dan risiko apa yang tetap tidak "
        "terdeteksi (RM3)?",
        "Seberapa sering model bahasa kecil sumber terbuka merekomendasikan nama paket yang tidak terdaftar, dan "
        "apakah nama tersebut kemudian didaftarkan setelah model dirilis (RM4)?",
        "Bagaimana merancang interceptor sisi klien yang mencakup shell interaktif, virtual environment aktif, "
        "skrip, job CI, dan agen AI, dan berapa tambahan waktu tunda yang ditimbulkannya (RM5)?",
    ])
    m.h2("Tujuan Penelitian", key="tujuan")
    m.p("Tujuan yang hendak dicapai melalui penelitian ini adalah sebagai berikut:")
    m.daftar([
        "Mengukur waktu pelaporan, penghapusan, dan instalasi paket berbahaya PyPI menggunakan metadata "
        "titik-waktu dan log unduhan, dengan memperhitungkan kampanye paket yang hampir identik.",
        "Mengukur pergeseran (drift) indikator metadata paket berbahaya antarperiode dan menurunkan prinsip "
        "rancangan algoritma penilaian risiko yang tahan terhadap pergeseran tersebut.",
        "Membandingkan perlindungan (paparan unduhan berbahaya yang dihentikan) dan biaya (unduhan sah yang "
        "terdampak) dari berbagai kebijakan waktu instalasi, serta mengidentifikasi kelas paket berbahaya yang "
        "tersisa.",
        "Mengklasifikasikan nama paket hasil halusinasi empat model bahasa kecil berdasarkan waktu pendaftarannya "
        "pada PyPI.",
        "Merancang, mengimplementasikan, dan menguji pipguard, yaitu interceptor pip berbahasa Go dengan "
        "intersepsi dua lapis, keputusan yang dapat dijelaskan, perilaku yang dapat diprediksi bagi pemanggil "
        "non-interaktif, dan tambahan waktu tunda yang rendah.",
    ])
    m.h2("Batasan Masalah", key="batasan")
    m.p("Agar pembahasan tetap terfokus dan sesuai dengan kemampuan penulis, ditetapkan batasan sebagai berikut:")
    m.daftar([
        "Penelitian dibatasi pada ekosistem Python dengan registry PyPI. Ekosistem lain seperti npm, RubyGems, "
        "dan Maven berada di luar cakupan.",
        "Perintah yang diintersepsi adalah `pip install`, `pip download`, dan `pip wheel` melalui pip, pip3, "
        "dan `python -m pip`. Pengelola paket lain seperti uv, poetry, conda, dan pipx tidak didukung.",
        "Sistem operasi sasaran adalah Linux dan macOS (amd64 dan arm64) dengan shell bash dan zsh; Windows tidak "
        "didukung.",
        "Keputusan diambil dari nama paket dan metadata registry, bukan dari analisis statis maupun dinamis "
        "terhadap kode paket.",
        "Pemeriksaan dilakukan terhadap paket yang disebutkan pada baris perintah dan pada berkas *requirements*; "
        "dependensi transitif yang diresolusi oleh pip tidak diperiksa.",
        "Pemanggilan yang tidak melalui resolusi PATH, misalnya jalur absolut menuju pip, serta `python -m pip` "
        "dari pemanggil yang tidak membaca konfigurasi shell, tidak tertangkap; batasan ini diuji dan dilaporkan.",
        "Evaluasi paket berbahaya memakai laporan OSV yang diekspor pada 14 Oktober 2026 dan data yang "
        "dibekukan pada 19 dan 24 Oktober 2026. Tidak ada berkas paket berbahaya yang diunduh atau dijalankan.",
        "Penelitian tidak mencakup studi pengguna maupun eksperimen terhadap agen AI; gangguan diukur sebagai "
        "frekuensi, bukan sebagai respons pengguna.",
    ])
    m.h2("Manfaat Penelitian", key="manfaat")
    m.p("Penelitian ini diharapkan memberikan manfaat sebagai berikut:")
    m.daftar([
        "Manfaat teoretis, yaitu sumber evaluasi berbasis waktu yang mengendalikan kebocoran data untuk "
        "pertahanan waktu instalasi, bukti empiris mengenai pergeseran indikator metadata paket berbahaya, serta "
        "pengukuran pertama atas granularitas dan ambang masa tunggu dependensi terhadap perlindungan dan biaya.",
        "Manfaat praktis bagi pengembang dan tim pengembangan, yaitu perangkat sumber terbuka yang dapat "
        "dipasang mandiri, menjelaskan keputusannya, berperilaku dapat diprediksi pada job CI dan agen AI, dan "
        "tidak dapat dimatikan hanya melalui variabel lingkungan.",
        "Manfaat bagi pengembang pengelola paket dan pengelola registry, yaitu rekomendasi kebijakan berlapis "
        "berbasis bukti mengenai kapan masa tunggu tingkat proyek dan tingkat rilis sebaiknya dipakai, serta "
        "pipeline analisis yang dapat direproduksi untuk penelitian lanjutan.",
    ])
    m.h2("Metodologi Penelitian", key="metodologi")
    m.p(
        "Penelitian ini menggunakan pendekatan Design Science Research Methodology (DSRM), yaitu proses "
        "penelitian desain yang bergerak dari identifikasi masalah sampai komunikasi hasil dan dapat dijalankan "
        "secara iteratif (Tuunanen dkk., 2024). Pendekatan ini dipilih karena luaran penelitian berupa artefak, yaitu perangkat "
        "lunak beserta kebijakan keputusan yang diterapkannya, sehingga metodologi yang berorientasi pada "
        "perancangan dan evaluasi artefak lebih sesuai daripada metodologi yang hanya menjelaskan fenomena. "
        f"DSRM terdiri atas {kata(6)} tahap yang pada penelitian ini dilaksanakan sebagai berikut:")
    m.daftar([
        "Identifikasi masalah dan motivasi, melalui studi literatur mengenai halusinasi paket, paket berbahaya, "
        "evaluasi temporal, dan pertahanan waktu instalasi.",
        "Penetapan tujuan solusi, berupa kebutuhan fungsional dan non-fungsional yang terukur serta model "
        "ancaman.",
        "Perancangan dan pengembangan, meliputi arsitektur intersepsi dua lapis, pemodelan Unified Modeling "
        "Language (UML), algoritma keputusan, dan implementasi dalam bahasa Go. Tahap ini dijalani dalam "
        f"{kata(3)} iterasi; rancangan akhir ditetapkan berdasarkan hasil evaluasi iterasi sebelumnya.",
        "Demonstrasi, dengan memasang artefak pada direktori home sementara dan menjalankannya pada 43 skenario "
        "pemanggilan secara otomatis.",
        "Evaluasi, berupa evaluasi temporal pada data paket berbahaya dan sah, pengukuran paparan dan biaya dari "
        "log unduhan, studi kasus insiden, probe halusinasi, pengujian intersepsi, dan pengukuran latensi.",
        "Komunikasi, berupa laporan skripsi ini, naskah artikel jurnal, serta kode sumber dan data beku yang "
        "diarsipkan secara terbuka.",
    ])
    m.h2("Sistematika Penulisan", key="sistematika")
    m.p(f"Laporan skripsi ini disusun dalam {kata(5)} bab dengan sistematika sebagai berikut:")
    m.daftar([
        "BAB I PENDAHULUAN, berisi latar belakang masalah, rumusan masalah, tujuan, batasan, manfaat, "
        "metodologi penelitian, dan sistematika penulisan.",
        "BAB II LANDASAN TEORI, berisi teori mengenai keamanan rantai pasok perangkat lunak, kebingungan nama "
        "paket, halusinasi paket dan slopsquatting, PyPI dan pip, resolusi perintah pada shell, masa tunggu "
        "dependensi, evaluasi temporal, ukuran evaluasi, bahasa Go, agen AI dan peringatan keamanan, penelitian "
        "terdahulu, serta gambaran teoretis rancangan sistem.",
        "BAB III ANALISA DAN PERANCANGAN SISTEM, berisi kerangka pikir, metode pengembangan sistem, analisa "
        "kebutuhan, pemodelan UML, perancangan arsitektur, algoritma penilaian risiko, antarmuka, dan "
        "perancangan evaluasi.",
        "BAB IV HASIL DAN PEMBAHASAN, berisi hasil implementasi dan pengujian sistem, hasil evaluasi untuk "
        "setiap rumusan masalah, serta pembahasan implikasi, keterbatasan, dan ancaman terhadap validitas.",
        "BAB V KESIMPULAN DAN SARAN, berisi jawaban atas rumusan masalah dan saran bagi penelitian serta "
        "pengembangan lanjutan.",
    ])
