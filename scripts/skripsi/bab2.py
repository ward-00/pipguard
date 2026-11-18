"""BAB II LANDASAN TEORI."""
from ctx_id import FIG, kata


def tulis(m):
    m.bab(2, "Landasan Teori", key="teori")
    m.h2("Landasan Teori", key="landasan")
    m.p(
        "Bagian ini menyajikan konstruksi teori yang menjadi dasar penelitian. Uraian disusun secara deduktif, "
        "mulai dari konsep umum keamanan rantai pasok perangkat lunak menuju konsep khusus yang langsung "
        "berkaitan dengan rancangan dan evaluasi sistem, yaitu mekanisme instalasi paket Python, resolusi "
        "perintah pada shell, masa tunggu dependensi, serta metode evaluasi yang memperhitungkan waktu.")

    m.h3("Keamanan Rantai Pasok Perangkat Lunak", key="rantai")
    m.p(
        "Rantai pasok perangkat lunak adalah keseluruhan komponen, pustaka, perkakas, dan proses yang terlibat "
        "dalam pembuatan dan pendistribusian perangkat lunak. Serangan rantai pasok menyisipkan kode berbahaya "
        "ke salah satu mata rantai tersebut agar sistem hilir yang bergantung padanya ikut terkompromi. Gokkaya "
        "dkk. (2026) menyusun taksonomi serangan, mitigasi, dan strategi penilaian risiko rantai pasok, "
        "sedangkan Williams dkk. (2025) merangkum arah penelitian keamanan rantai pasok yang disepakati para "
        "peneliti dan praktisi. Cox (2025) menunjukkan bahwa risiko ini telah menyertai penggunaan ulang "
        "perangkat lunak sumber terbuka selama lima puluh tahun, sedangkan bentuknya terus berubah.")
    m.p(
        "Ciri yang membuat serangan ini berbahaya adalah efek pengganda: satu paket yang tersusupi dapat "
        "memengaruhi banyak proyek, baik secara langsung maupun melalui dependensi transitif. Praktisi dari 30 "
        "organisasi industri dan pemerintahan menempatkan pengambilalihan akun pengelola dan kompromi pipeline "
        "build di antara tantangan utama keamanan rantai pasok (Enck dan Williams, 2022). Bagi penelitian ini, "
        "dua kelas serangan perlu dibedakan sejak awal: *proyek baru* yang sejak awal dibuat untuk menyebarkan "
        "kode berbahaya, dan *proyek lama* yang disusupi, diambil alih, atau sengaja dibiarkan menua sebelum "
        "dipersenjatai (pre-aging). Kedua kelas ini menuntut aturan pertahanan yang berbeda, sebagaimana "
        "ditunjukkan pada {{bab:hasil}}.")

    m.h3("Serangan Kebingungan Nama Paket", key="kebingungan")
    m.p(
        "Serangan kebingungan nama paket (package confusion) membuat pengembang memasang paket yang berbeda "
        "dari yang dimaksudkannya. Typosquatting mendaftarkan nama yang berjarak sedikit operasi penyuntingan "
        "dari nama paket populer, combosquatting menambahkan kata yang masuk akal pada nama yang dikenal, dan "
        "dependency confusion mendaftarkan nama paket internal sebuah organisasi pada registry publik sehingga "
        "pengelola paket memilih salinan milik penyerang (Gokkaya dkk., 2026). Repositori privat yang berbagi "
        "ruang nama dengan PyPI tetap rentan terhadap bentuk terakhir tersebut (Lizzit dkk., 2026).")
    m.p(
        "Detektor typosquatting membandingkan nama yang diminta dengan daftar nama populer menggunakan ukuran "
        "jarak string, baik untuk paket (Neupane dkk., 2023) maupun untuk nama domain web (Blefari dkk., 2026). "
        "Ukuran yang paling umum adalah jarak Levenshtein, yaitu jumlah minimum operasi penyisipan, penghapusan, "
        "atau penggantian satu karakter untuk mengubah satu string menjadi string lain. Varian optimal string "
        "alignment juga menghitung pertukaran dua karakter yang bersebelahan sebagai satu operasi. Jarak "
        "Levenshtein antara string *a* dan *b* dihitung secara rekursif dengan Persamaan (2.1), dengan "
        "lev(*i*, 0) = *i* dan lev(0, *j*) = *j*.")
    m.persamaan("lev(i, j) = min{ lev(i−1, j) + 1;  lev(i, j−1) + 1;  lev(i−1, j−1) + [aᵢ ≠ bⱼ] }", key="lev")
    m.p(
        "Indikator berbasis kemiripan nama memiliki kelemahan bawaan: nama yang pendek mudah berjarak satu atau "
        "dua operasi dari nama populer secara kebetulan, sehingga indikator ini perlu dibatasi pada panjang nama "
        "minimum dan daftar rujukan yang cukup besar. Kelemahan ini teramati pada iterasi pertama penelitian "
        "dan diuraikan pada {{bab:analisa}}.")

    m.h3("Large Language Model dan Halusinasi Paket", key="halusinasi")
    m.p(
        "Large language model adalah model bahasa berskala besar yang dilatih pada korpus teks dan kode dalam "
        "jumlah sangat besar sehingga mampu menghasilkan keluaran yang menyerupai tulisan manusia. Model "
        "menghasilkan token berdasarkan probabilitas, bukan berdasarkan verifikasi terhadap sumber pengetahuan, "
        "sehingga dapat menghasilkan keluaran yang tampak meyakinkan tetapi bertentangan dengan fakta. Alansari "
        "dan Luqman (2026) menggolongkan kesalahan ini sebagai halusinasi yang bertentangan dengan fakta "
        "(fact-conflicting hallucination).")
    m.p(
        "Spracklen dkk. (2025) mendefinisikan halusinasi paket sebagai kesalahan ketika model menghasilkan kode "
        "atau rekomendasi yang merujuk pada paket yang tidak terdapat pada registry mana pun. Penelitian mereka "
        "menunjukkan bahwa fenomena ini terjadi pada seluruh model yang diuji, dengan tingkat yang lebih tinggi "
        "pada model sumber terbuka, dan bahwa sebagian besar nama halusinasi bersifat persisten: nama yang sama "
        "muncul kembali ketika prompt diulang. Halusinasi yang persisten berarti dapat diprediksi, dan nama yang "
        "dapat diprediksi dapat didaftarkan lebih dahulu oleh penyerang. Z. Huang dkk. (2026) menambahkan bahwa "
        "augmentasi pencarian web tidak selalu mengurangi persistensi tersebut.")

    m.h3("Slopsquatting", key="slopsquatting")
    m.p(
        "Slopsquatting adalah serangan yang memanfaatkan halusinasi paket. Alur serangannya ditunjukkan pada "
        "{{gbr:slop}}. Penyerang mengirimkan prompt berulang kepada LLM untuk menemukan nama paket tidak "
        "terdaftar yang muncul secara konsisten, mendaftarkan nama tersebut pada registry publik dengan muatan "
        "berbahaya, lalu menunggu pengembang atau agen AI yang menerima rekomendasi yang sama menjalankan "
        "perintah instalasi.")
    m.gambar(FIG / "gbr_slopsquatting.png", "Alur Serangan Slopsquatting pada PyPI", 14.0, key="slop")
    m.p(
        "Perbedaan mendasar slopsquatting dan typosquatting terletak pada sumber kekeliruannya. Typosquatting "
        "bergantung pada kesalahan ketik manusia yang acak dan bervariasi, sedangkan slopsquatting memanfaatkan "
        "perilaku sistematis model sehingga nama yang akan diketik calon korban dapat diperkirakan. Selama nama "
        "halusinasi belum didaftarkan, pip hanya akan gagal karena paket tidak ditemukan; bahaya baru muncul "
        "setelah seseorang mendaftarkannya. Karena itu, pertanyaan yang relevan bagi pertahanan bukan hanya "
        "apakah sebuah nama terdaftar, tetapi juga *sejak kapan* nama tersebut terdaftar.")

    m.h3("Python Package Index, pip, dan Eksekusi Kode saat Instalasi", key="pypi")
    m.p(
        "Python Package Index (PyPI) adalah registry paket resmi ekosistem Python. Siapa pun dapat mendaftarkan "
        "nama proyek yang belum digunakan, dan PyPI mendistribusikan dua jenis berkas: distribusi sumber "
        "(sdist) dan wheel yang sudah dibangun. Memasang sdist berarti membangunnya di mesin pengguna dan "
        "menjalankan skrip build milik paket, sehingga kode berjalan sebelum paket diimpor; `pip download` dan "
        "`pip wheel` juga membangun sdist. Paket berbahaya umumnya menjalankan muatannya pada titik ini (Ladisa "
        "dkk., 2023; Mehedi dkk., 2026; C. Huang dkk., 2024).")
    m.p(
        "PyPI menyediakan antarmuka pemrograman aplikasi (API) berbasis JavaScript Object Notation (JSON) pada "
        "rute `GET /pypi/<proyek>/json` yang mengembalikan metadata proyek, riwayat rilis beserta waktu "
        "unggahnya, dan berkas rilis terbaru. Rute ini menjawab HTTP 404 untuk nama yang tidak terdaftar. Karena "
        "pip sendiri gagal memasang nama yang tidak terdaftar, pemeriksaan keberadaan tidak mencegah kerugian "
        "secara langsung; pemeriksaan tersebut hanya dapat menjelaskan kegagalan dan memperingatkan risiko "
        "slopsquatting. Nama proyek dinormalisasi menurut Python Enhancement Proposal (PEP) 503, yaitu huruf "
        "kecil dengan rangkaian karakter `-`, `_`, dan `.` diganti satu tanda hubung.")
    m.p(
        "Paket berbahaya yang dilaporkan dicatat pada basis data Open Source Vulnerabilities (OSV) dengan "
        "pengenal berawalan MAL, lalu dihapus dari PyPI. Penghapusan ini membuat metadata paket berbahaya tidak "
        "lagi dapat diambil dari API PyPI; penelitian ini karena itu merekonstruksinya dari cermin publik tabel "
        "metadata dan log unduhan PyPI (ClickPy) yang tetap menyimpan baris proyek yang telah dihapus.")

    m.h3("Resolusi Perintah, Shim, Fungsi Shell, dan Virtual Environment", key="resolusi")
    m.p(
        "Shell keluarga Unix menentukan program yang dijalankan untuk sebuah nama perintah melalui urutan "
        "resolusi: alias, fungsi shell, perintah bawaan, kemudian pencarian berkas pada direktori-direktori PATH "
        "dari kiri ke kanan ({{gbr:resolusi}}). Teknik shim memanfaatkan urutan ini dengan menempatkan program "
        "pengganti bernama sama pada direktori yang lebih awal di PATH. Program pengganti melakukan pekerjaan "
        "tambahan lalu menyerahkan eksekusi kepada program aslinya.")
    m.gambar(FIG / "gbr_resolusi.png", "Urutan Resolusi Perintah pip pada Shell dan Posisi Kedua Lapisan "
                                       "Intersepsi", 14.0, key="resolusi")
    m.p(
        "Aktivasi virtual environment menambahkan direktori `bin` milik lingkungan tersebut di posisi terdepan "
        "PATH. Direktori itu berisi salinan pip yang berdiri sendiri, sehingga shim global tertimpa tepat ketika "
        "pengembang mengikuti praktik yang dianjurkan. Fungsi shell dievaluasi sebelum seluruh pencarian PATH "
        "sehingga tidak tertimpa, tetapi hanya ada pada shell interaktif yang membaca berkas konfigurasi "
        "pengguna seperti `~/.bashrc` atau `~/.zshrc`. Kedua teknik ini saling melengkapi, dan penggabungannya "
        "menjadi dasar rancangan intersepsi dua lapis pada penelitian ini. Pemanggilan dengan jalur absolut, "
        "misalnya `/usr/bin/pip`, tidak melalui resolusi tersebut sehingga tidak dapat ditangkap oleh teknik "
        "berbasis PATH mana pun.")
    m.p(
        "Setelah pemeriksaan selesai, program pengganti dapat menyerahkan eksekusi dengan pemanggilan sistem "
        "`exec`, yang mengganti citra proses yang sedang berjalan dengan program lain tanpa membuat proses baru. "
        "Dengan cara ini sinyal dan status keluar pip asli diteruskan tanpa perubahan kepada pemanggil, dan tidak "
        "ada proses pembungkus yang tersisa.")

    m.h3("Masa Tunggu Dependensi", key="cooldown")
    m.p(
        "Masa tunggu dependensi (dependency cooldown) menolak atau menunda pemasangan kode yang berumur kurang "
        "dari suatu ambang *T*, dengan premis bahwa unggahan berbahaya terdeteksi dan dihapus dengan cepat. "
        "Penelitian ini membedakan dua granularitas. Masa tunggu *tingkat rilis* menahan setiap versi yang "
        "diunggah kurang dari *T* hari yang lalu; pip dan uv kemudian memilih versi lama secara diam-diam bila "
        "tersedia, atau gagal bila tidak ada. Masa tunggu *tingkat proyek* hanya menahan proyek yang rilis "
        "pertamanya berumur kurang dari *T* hari, sehingga pembaruan proyek yang sudah mapan tidak terpengaruh.")
    m.p(
        "Masa tunggu tingkat rilis juga menunda pembaruan sah, termasuk perbaikan keamanan. Perbaikan keamanan "
        "sampai kepada pengguna sebagai rilis baru, makin sering melalui bot pembaruan: Dependabot membuka pull "
        "request keamanan dalam jumlah besar, tetapi banyak di antaranya terlambat digabungkan (Rebatchi dkk., "
        "2024; He dkk., 2023). Apakah sebuah proyek menerima rilis baru sama sekali bergantung pada strategi "
        "pembaruannya (Javan Jafari dkk., 2023) dan pada cara proyek mengunci dependensinya (Gamage dkk., 2026), "
        "sedangkan perbaikan sudah merambat lambat melalui rantai dependensi: pada npm, kerentanan yang akhirnya "
        "tersingkir dari pohon dependensi rata-rata bertahan 371 hari, dan sekitar 40% masih tertinggal pada "
        "pohon dependensi terbaru (Liu dkk., 2022). Masa tunggu "
        "tingkat rilis memperpanjang jeda tersebut di setiap simpul rantai. Di sisi lain, hanya aturan tingkat "
        "rilis yang dapat melihat proyek lama yang disusupi atau yang aktif kembali setelah lama dorman "
        "(Zerouali dkk., 2025).")

    m.h3("Evaluasi Temporal dan Pergeseran Konsep", key="temporal")
    m.p(
        "Sistem keamanan berbasis pembelajaran rentan terhadap jebakan evaluasi, antara lain temporal snooping, "
        "yaitu bocornya informasi dari masa depan ke dalam data pelatihan atau penyetelan (Arp dkk., 2024). "
        "Concept drift, yaitu berubahnya hubungan antara ciri dan label dari waktu ke waktu, menurunkan kinerja "
        "detektor malware (Guerra-Manzanares dkk., 2022; Patel dkk., 2026), dan protokol yang bebas kebocoran "
        "temporal makin menjadi tuntutan (Yang dkk., 2026). Konsekuensinya, data harus dibagi menurut waktu: "
        "model disusun pada data lama, divalidasi pada data yang lebih baru, dan diuji pada data paling baru "
        "yang tidak disentuh selama perancangan.")
    m.p(
        "Pada domain paket berbahaya, Moufid dkk. (2026) merekonstruksi atribut metadata setiap versi paket pada "
        "waktu publikasinya, menempatkan paket, pengelola, dan keluarga nama dalam satu lipatan, dan menunjukkan "
        "bahwa interval bootstrap per klaster 3,7 kali lebih lebar daripada interval per versi. Draz (2026) "
        "menunjukkan bahwa kinerja detektor pembaruan berbahaya bergantung pada cara data kontrol disusun dan "
        "runtuh pada pemisahan temporal yang ketat. Paket berbahaya juga datang dalam *kampanye* berisi banyak "
        "paket yang hampir identik; memperlakukan setiap paket sebagai pengamatan independen membuat interval "
        "kepercayaan terlalu sempit. Penelitian ini karena itu mengelompokkan paket ke dalam kampanye dan "
        "melaporkan interval yang melakukan pencuplikan ulang per kampanye.")

    m.h3("Ukuran Evaluasi", key="ukuran")
    m.p(
        "Keputusan sebuah detektor terhadap paket berbahaya (positif) dan paket sah (negatif) dirangkum dalam "
        "confusion matrix berisi true positive (TP), false negative (FN), false positive (FP), dan true negative "
        "(TN). Penelitian ini melaporkan recall per kelompok positif dan false positive rate (FPR) per kelompok "
        "negatif, bukan presisi, karena presisi bergantung pada perbandingan jumlah kelas dalam sampel.")
    m.persamaan("recall = TP / (TP + FN)", key="recall")
    m.persamaan("FPR = FP / (FP + TN)", key="fpr")
    m.p(
        "Interval kepercayaan 95% untuk sebuah proporsi *p̂* = *k*/*n* dihitung dengan interval Wilson pada "
        "Persamaan (2.4), dengan *z* = 1,96. Interval ini tetap berperilaku baik ketika proporsi mendekati 0 "
        "atau 1, berbeda dengan interval normal biasa.")
    m.persamaan("(p̂ + z²/2n ± z·√(p̂(1−p̂)/n + z²/4n²)) / (1 + z²/n)", key="wilson")
    m.p(
        "Untuk paket berbahaya yang berkelompok dalam kampanye, interval dihitung dengan bootstrap persentil: "
        "kampanye dicuplik ulang dengan pengembalian sebanyak 2.000 kali, statistik dihitung pada setiap sampel, "
        "lalu persentil ke-2,5 dan ke-97,5 dijadikan batas interval. Dua detektor yang dinilai pada paket yang "
        "sama dibandingkan dengan uji McNemar eksak, yang hanya memakai pasangan yang keputusannya berbeda "
        "(*b* dan *c*); di bawah hipotesis nol, *b* berdistribusi binomial dengan peluang 0,5 dari *b* + *c* "
        "percobaan.")
    m.p(
        "Kemampuan skor untuk memisahkan dua kelas dirangkum dengan kurva receiver operating characteristic "
        "(ROC), yaitu true positive rate terhadap FPR pada semua ambang, dan luas di bawah kurva (AUC), yang "
        "setara dengan peluang sebuah paket positif acak memperoleh skor lebih tinggi daripada paket negatif "
        "acak. Likelihood ratio positif (LR+) dan nilai prediktif positif (PPV) pada prevalensi π menghubungkan "
        "ukuran tersebut dengan prevalensi nyata melalui Persamaan (2.5) dan (2.6).")
    m.persamaan("LR+ = TPR / FPR", key="lr")
    m.persamaan("PPV = π·TPR / (π·TPR + (1 − π)·FPR)", key="ppv")
    m.p(
        "Bobot indikator ditaksir dengan regresi logistik, yang memodelkan peluang sebuah paket berbahaya "
        "sebagai fungsi logistik dari kombinasi linear indikatornya (Persamaan 2.7). Penalti ridge "
        "(λ‖β‖²) mencegah koefisien membesar ketika indikator saling berkorelasi, dan pembobotan kelas yang "
        "seimbang mencegah kelas yang lebih besar mendominasi. Ambang keputusan dipilih dengan indeks Youden, "
        "*J* = TPR − FPR, yang dimaksimalkan pada data validasi.")
    m.persamaan("P(berbahaya | x) = 1 / (1 + exp(−(β₀ + β₁x₁ + … + βₖxₖ)))", key="logit")

    m.h3("Bahasa Pemrograman Go", key="go")
    m.p(
        "Go adalah bahasa pemrograman bertipe statis yang dikompilasi langsung menjadi kode mesin. Tiga "
        "karakteristiknya sesuai dengan kebutuhan penelitian ini. Pertama, hasil kompilasi berupa satu berkas "
        "biner statis yang tidak memerlukan runtime atau pustaka tambahan di mesin sasaran. Kedua, program "
        "dimulai sangat cepat karena tidak ada inisialisasi interpreter atau mesin virtual; hal ini menentukan "
        "karena interceptor dijalankan secara sinkron pada setiap perintah instalasi. Ketiga, Go mendukung "
        "kompilasi silang dari satu basis kode untuk berbagai sistem operasi dan arsitektur. Pustaka standar Go "
        "telah menyediakan klien HTTP, pengurai JSON, dan pemanggilan sistem `syscall.Exec`, sehingga seluruh "
        "kebutuhan implementasi dapat dipenuhi tanpa dependensi eksternal. Selain memperkecil berkas biner, hal "
        "ini juga memperkecil permukaan serangan rantai pasok dari perangkat pertahanan itu sendiri.")

    m.h3("Agen Pemrograman AI dan Perancangan Peringatan Keamanan", key="agen")
    m.p(
        "Survei mengenai agen berbasis LLM mengidentifikasi penggunaan alat (tool use) dan interaksi dengan "
        "lingkungan sebagai permukaan serangan yang dapat diarahkan melalui prompt injection (Gan dkk., 2026; "
        "Hu dkk., 2026). Agen yang memasang paket tanpa terminal tidak dapat menjawab prompt konfirmasi, dan "
        "agen yang dapat mengatur variabel lingkungan dapat mematikan pertahanan yang dikonfigurasi melalui "
        "variabel tersebut. Kedua hal ini menentukan rancangan antarmuka pada penelitian ini: pemanggil tanpa "
        "terminal harus menerima keputusan yang dapat dibaca mesin, dan pengecualian tidak boleh dapat diaktifkan "
        "hanya dari lingkungan proses yang dilindungi.")
    m.p(
        "Bagi pengguna manusia, efektivitas peringatan keamanan menurun akibat habituasi. Vance dkk. (2025) "
        "menunjukkan bahwa habituasi terhadap notifikasi non-keamanan yang sering muncul ikut melemahkan "
        "peringatan keamanan yang belum pernah dilihat, dan bahwa efek ini berkurang bila peringatan dibuat "
        "berbeda secara visual dan interaktif. Kelelahan peringatan (alert fatigue) juga merupakan masalah sentral "
        "pada pusat operasi keamanan (Tariq dkk., 2025). Penelitian ini karena itu memperlakukan frekuensi "
        "gangguan terhadap pekerjaan sah sebagai biaya utama: peringatan hanya muncul bila terdapat bukti yang "
        "memadai, memuat alasan yang spesifik, dan memilih pembatalan sebagai jawaban bawaan.")

    m.h2("Penelitian Terdahulu", key="terdahulu")
    m.p(
        "Penelitian yang relevan dapat dikelompokkan menjadi tiga. Kelompok pertama adalah detektor paket "
        "berbahaya di sisi registry atau pemindai. Cerebro memodelkan perilaku berbahaya sebagai urutan dan "
        "mendeteksi paket npm dan PyPI dengan satu model (Zhang dkk., 2025); model dengan ciri yang tidak "
        "bergantung pada bahasa memindai 31.292 unggahan baru npm dan PyPI selama sepuluh hari dan menemukan 58 "
        "paket berbahaya yang belum dikenal (Ladisa dkk., 2023); DySec memantau instalasi dengan probe extended Berkeley Packet Filter (Mehedi dkk., 2026); "
        "detektor lain menggabungkan analisis statis dan dinamis (C. Huang dkk., 2024; Iqbal dkk., 2025), "
        "bekerja lintas bahasa (Iqbal dkk., 2026), menggabungkan kode dan metadata (Yan dan Zhao, 2026), atau "
        "memakai LLM untuk membangkitkan ciri dan mengoordinasikan agen analisis (Wang dkk., 2025; Umar Zeshan "
        "dkk., 2026). Detektor ini menganalisis kode setelah unggahan dan beroperasi di bawah batas positif palsu "
        "yang ketat (Vu dkk., 2023).")
    m.p(
        "Kelompok kedua adalah metodologi evaluasi. Moufid dkk. (2026) dan Draz (2026) adalah penelitian yang "
        "paling dekat dengan metodologi penelitian ini karena sama-sama merekonstruksi metadata pada waktu "
        "publikasi dan menuntut pemisahan temporal. Penelitian ini berbeda dalam skala (8.588 paket berbahaya "
        "PyPI yang telah dihapus dan 9.850 paket sah), dalam pemakaian skenario waktu instalasi dan log unduhan "
        "yang mengubah deteksi menjadi paparan, dan dalam pertanyaan yang diajukan: bukan klasifikasi mana yang "
        "terbaik, melainkan kebijakan waktu instalasi mana yang sepadan dengan biayanya.")
    m.p(
        "Kelompok ketiga adalah pertahanan sebelum dan saat instalasi. Neupane dkk. (2023) menunjukkan bahwa "
        "kebingungan nama paket tidak terbatas pada salah ketik, menyusun 13 kategori mekanisme kebingungan "
        "beserta detektornya pada npm, dan menyarankan agar detektor tersebut dipakai sebagai peringatan sebelum "
        "instalasi, bukan sebagai pemblokiran; Latch memediasi kemampuan paket npm pada waktu instalasi melalui "
        "kebijakan pengguna (Wyss dkk., 2022); terhadap halusinasi, Z. Huang dkk. (2026) mengusulkan agen yang "
        "mendaftarkan lebih dahulu nama halusinasi dan memelihara registry peringatan publik. Spracklen dkk. "
        "(2025) mengukur fenomena halusinasi paket dan mitigasinya di sisi model. {{tbl:terdahulu}} merangkum persamaan "
        "dan perbedaan penelitian-penelitian tersebut dengan penelitian ini.")
    m.tabel("Perbandingan Penelitian Terdahulu dengan Penelitian Ini",
            ["No", "Peneliti (Tahun)", "Fokus Penelitian", "Persamaan", "Perbedaan"], [
                ["1", "Spracklen dkk. (2025)", "Frekuensi dan persistensi halusinasi paket pada 16 model; mitigasi "
                 "di sisi model", "Halusinasi paket sebagai sumber risiko; probe rekomendasi dipakai ulang",
                 "Penelitian ini membangun pertahanan di sisi klien dan mengklasifikasikan nama menurut waktu "
                 "pendaftaran"],
                ["2", "Z. Huang dkk. (2026)", "Halusinasi paket pada npm; pendaftaran nama halusinasi; agen "
                 "pendaftaran preventif", "Slopsquatting sebagai ancaman nyata", "Penelitian ini pada PyPI dan "
                 "memutuskan di sisi klien, bukan dengan mendaftarkan nama"],
                ["3", "Zhang dkk. (2025); Ladisa dkk. (2023); Mehedi dkk. (2026)", "Deteksi paket berbahaya dari "
                 "kode atau perilaku di sisi registry", "Objek berupa paket berbahaya PyPI", "Penelitian ini "
                 "memutuskan dari metadata dalam milidetik sebelum kode diunduh"],
                ["4", "Moufid dkk. (2026)", "Bias evaluasi dan metadata titik-waktu pada npm dan PyPI",
                 "Metadata pada waktu publikasi; interval per klaster", "Penelitian ini mengukur paparan dan "
                 "biaya kebijakan dengan log unduhan"],
                ["5", "Draz (2026)", "Deteksi pembaruan berbahaya dengan konteks versi", "Pemisahan temporal "
                 "yang ketat", "Penelitian ini membandingkan kebijakan waktu instalasi, bukan pengklasifikasi"],
                ["6", "Neupane dkk. (2023)", "Kategori kebingungan nama paket dan detektornya pada npm",
                 "Kemiripan nama sebagai sinyal; peringatan sebelum instalasi", "Penelitian ini memakai umur proyek sebagai penentu dan "
                 "menunjukkan bahwa kemiripan nama hampir tidak menambah deteksi"],
                ["7", "Wyss dkk. (2022)", "Latch: kebijakan kemampuan waktu instalasi pada npm", "Pertahanan "
                 "waktu instalasi di sisi klien", "Penelitian ini tidak memerlukan manifest izin dan mendukung "
                 "agen AI"],
                ["8", "Vu dkk. (2023)", "Pemindaian malware PyPI dan toleransi positif palsu administrator",
                 "Ekosistem PyPI", "Penelitian ini memindahkan keputusan ke klien yang dapat menanggung "
                 "positif palsu pada proyek baru"],
                ["9", "pip ≥ 26.0, uv ≥ 0.1.15, pnpm ≥ 10.16", "Masa tunggu tingkat rilis", "Umur sebagai "
                 "sinyal", "Penelitian ini mengukur granularitas, ambang, dan biayanya, dan memakai tingkat "
                 "proyek"],
            ], lebar=[0.8, 2.6, 3.4, 3.4, 3.8], size=9, align=["c", "l", "l", "l", "l"], key="terdahulu")
    m.p(
        "Berdasarkan tabel tersebut, penelitian terdahulu telah memberikan landasan yang kuat dalam memahami "
        "halusinasi paket dan dalam mendeteksi paket berbahaya di sisi registry. Namun, belum ada penelitian "
        "yang mengukur berapa banyak paparan berbahaya yang dihilangkan sebuah masa tunggu dibandingkan dengan "
        "berapa banyak instalasi sah yang diubahnya, dan belum ada yang mengevaluasi kebijakan waktu instalasi "
        "pada paket berbahaya yang benar-benar pernah dapat dipasang. Kesenjangan inilah yang menjadi kebaruan "
        "penelitian ini.")

    m.h2("Rancangan Sistem", key="rancangan_teori")
    m.p(
        "Sistem yang dirancang adalah sebuah interceptor yang menyisipkan diri di antara pemanggil dan pip. "
        f"Secara konseptual, sistem bekerja melalui {kata(4)} tahap berurutan: menangkap perintah, mengekstraksi "
        "nama paket, menilai risiko, dan menyajikan keputusan.")
    m.p(
        "Tahap penangkapan menerapkan strategi dua lapis sesuai {{sub:resolusi}}. Lapisan pertama berupa fungsi "
        "shell bernama `pip`, `pip3`, `python`, dan `python3` pada berkas konfigurasi shell, yang menang atas "
        "virtual environment aktif dan menangkap `python -m pip`. Lapisan kedua berupa shim pada `~/.local/bin` "
        "yang menangkap skrip, subproses, job CI, dan agen AI yang memanggil `pip` melalui PATH. Kedua lapisan "
        "memanggil biner yang sama sehingga logika pemeriksaan hanya diimplementasikan satu kali.")
    m.p(
        "Tahap ekstraksi mengurai argumen pip, mengikuti berkas *requirements*, dan menormalisasi nama menurut "
        "PEP 503. Tahap penilaian mengambil metadata dari cache lokal atau API JSON PyPI dan memisahkan dua "
        "keputusan: *apakah* instalasi memerlukan konfirmasi ditentukan oleh sinyal yang stabil (tidak terdaftar "
        "atau proyek berumur kurang dari 30 hari), sedangkan *seberapa berat* peringatannya ditentukan oleh "
        "indikator metadata. Tahap terakhir menampilkan peringatan dan meminta konfirmasi pada terminal "
        "interaktif, atau membatalkan dengan rekaman JSON bila tidak ada terminal, lalu meneruskan perintah "
        "kepada pip asli dengan `exec`. Seluruh kegagalan jaringan atau internal meneruskan perintah "
        "(fail-open), sehingga perangkat keamanan tidak menjadi titik kegagalan tunggal.")
