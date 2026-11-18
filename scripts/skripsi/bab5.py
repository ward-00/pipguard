"""BAB V KESIMPULAN DAN SARAN.

Panduan 5.3.5: kesimpulan berupa ringkasan jawaban rumusan masalah, bukan pengulangan angka hasil analisis.
"""


def tulis(m):
    m.bab(5, "Kesimpulan dan Saran", key="kesimpulan")
    m.h2("Kesimpulan", key="simpulan")
    m.p(
        "Berdasarkan hasil implementasi dan evaluasi pada {{bab:hasil}}, kesimpulan penelitian ini sebagai "
        "berikut:")
    m.daftar([
        "Paket berbahaya PyPI dilaporkan dalam hitungan jam setelah diunggah dan umumnya berhenti diunduh dalam "
        "beberapa hari. Sebagian besar unduhannya terjadi pada hari pertama, tetapi sebagian besar unduhan itu tidak "
        "dapat dibedakan dari lalu lintas otomatis yang diterima setiap unggahan baru, sehingga paparan nyata "
        "terkonsentrasi pada segelintir paket yang banyak diunduh (RM1).",
        "Indikator metadata yang dahulu mencirikan paket berbahaya, seperti distribusi hanya-sdist dan ketiadaan "
        "tautan proyek, bergeser tajam dalam satu tahun, sedangkan umur proyek tetap stabil. Model yang dikalibrasi "
        "pada data lama gagal pada data baru meskipun kampanye terbesar dikeluarkan. Karena itu, keputusan "
        "konfirmasi harus didasarkan pada sinyal yang stabil, sedangkan metadata hanya layak menentukan tingkat "
        "peringatan dan harus selalu divalidasi pada data yang lebih baru (RM2).",
        "Masa tunggu tingkat proyek 30 hari mencakup sebagian besar paket berbahaya baru dan menghentikan sebagian "
        "besar paparan yang dihentikan masa tunggu tingkat rilis, dengan biaya berupa unduhan sah yang terdampak "
        "sekitar tiga orde besaran lebih kecil dan dengan peringatan yang terlihat, bukan penggantian versi secara "
        "diam-diam. Pemeriksaan keberadaan dan kemiripan nama hampir tidak menambah perlindungan terhadap paket "
        "berbahaya yang terdaftar. Selisih perlindungan berasal dari kelas proyek yang disusupi dan pre-aged yang "
        "terus bertambah dan hanya dapat dicakup aturan tingkat rilis, sehingga kebijakan bawaan yang dapat "
        "dipertanggungjawabkan adalah kebijakan berlapis (RM3).",
        "Model bahasa kecil sumber terbuka masih merekomendasikan nama paket yang tidak pernah terdaftar, dan "
        "sebagian nama tersebut berulang. Untuk nama ini, pemeriksaan keberadaan hanya menjelaskan kegagalan pip. "
        "Nama halusinasi yang kemudian didaftarkan ternyata merupakan proyek independen, bukan penyerobot, "
        "sehingga waktu pendaftaran merupakan pembeda yang lebih tepat daripada status terdaftar saja (RM4).",
        "Intersepsi dua lapis yang menggabungkan fungsi shell dan shim PATH, diimplementasikan sebagai biner Go "
        "statis, menangkap perintah pip pada shell interaktif, virtual environment aktif, skrip, subproses, job "
        "CI, dan agen AI yang memanggil pip, memberikan keputusan yang dapat dibaca mesin tanpa terminal, dan "
        "tidak dapat dimatikan hanya melalui variabel lingkungan. Tambahan waktu tundanya jauh di bawah sasaran. "
        "Batas cakupannya, yaitu `python -m pip` dari pemanggil non-interaktif, jalur absolut, dan pemasang lain, "
        "telah diuji dan didokumentasikan (RM5).",
    ])
    m.h2("Saran", key="saran")
    m.p("Berdasarkan hasil dan keterbatasan penelitian ini, saran yang dapat diberikan adalah sebagai berikut:")
    m.daftar([
        "Bagi pengembang pengelola paket seperti pip, uv, dan pnpm, disarankan menyediakan masa tunggu tingkat "
        "proyek sebagai bawaan dan mempertahankan masa tunggu tingkat rilis yang pendek sebagai lapisan tambahan, "
        "disertai mekanisme pengecualian untuk perbaikan keamanan yang mendesak.",
        "Bagi organisasi yang memakai CI dan agen pemrograman AI, disarankan memasang aturan yang sama pada titik "
        "yang harus dilalui setiap pemasang, misalnya citra sandbox dengan konfigurasi pipguard terkunci atau proxy "
        "indeks paket lokal, karena interceptor berbasis PATH dapat dilewati `python -m pip` dan jalur absolut.",
        "Bagi penelitian lanjutan, disarankan merancang aturan tingkat rilis yang menyasar proyek yang disusupi "
        "dengan biaya lebih rendah, misalnya menggabungkan umur rilis dengan perubahan pengelola dan provenance.",
        "Mengembangkan penerapan berupa proxy indeks yang juga mencakup dependensi transitif dan setiap pemasang, "
        "serta resolusi dependensi khusus wheel agar pemeriksaan tidak menjalankan kode paket.",
        "Melakukan studi lapangan mengenai respons pengembang dan agen AI terhadap prompt masa tunggu, termasuk "
        "apakah agen meneruskan keputusan berstatus keluar 3 kepada manusia atau terus mencoba ulang.",
        "Mereplikasi evaluasi berbasis waktu pada npm dan registry lain, dan memperluas probe halusinasi ke model "
        "yang lebih besar serta pengaturan agen.",
        "Bagi pengembang yang memakai asisten pemrograman berbasis LLM, disarankan selalu memverifikasi nama dan "
        "umur paket yang direkomendasikan sebelum memasangnya.",
    ])
