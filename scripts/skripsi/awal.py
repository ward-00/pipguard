"""Bagian awal laporan (Panduan 3.1 dan 4.4-4.11, Lampiran F-M).

Data pribadi yang belum diketahui ditulis sebagai [..] di IDENTITAS; isi sekali di sini, lalu bangun ulang.
"""
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from ctx_id import FIG, N, kata, num, pct

IDENTITAS = {
    "nama": "Edward Alexandra",
    "npm": "03082230017",
    "peminatan": "Software Engineering",
    "program_studi": "Informatika",
    "fakultas": "Akal Imitasi dan Robotika",
    "kota": "Medan",
    "tahun": "2026",
    "pembimbing": "[Nama Dosen Pembimbing, gelar]",
    "kaprodi": "[Nama Ketua Program Studi Informatika (Kampus Kota Medan), gelar]",
    "associate_dean": "[Nama Associate Dean Fakultas Akal Imitasi dan Robotika, gelar]",
    "rektor": "[Nama Rektor Universitas Pelita Harapan, gelar]",
    "dekan": "[Nama Dekan Fakultas Akal Imitasi dan Robotika, gelar]",
    "executive_director": "[Nama Executive Director UPH Kampus Medan, gelar]",
    "penasehat_akademik": "[Nama Penasehat Akademik, gelar]",
    "penguji_2": "[Nama Penguji Kedua, gelar]",
    "penguji_3": "[Nama Penguji Ketiga, gelar]",
    "tanggal_persetujuan": "[tanggal bulan tahun]",
    "tanggal_sidang": "[hari, tanggal sidang]",
}
# Daftar Lampiran dari entri TC jenis L; \s Lampiran menambahkan huruf lampiran (field SEQ) di depan nomor halaman
TOC_LAMPIRAN = 'TOC \\f L \\h \\z \\s Lampiran'
JUDUL = ("Perancangan Interceptor pip dengan Masa Tunggu Tingkat Proyek dan Evaluasi Berbasis Waktu terhadap "
         "Paket Berbahaya Baru pada PyPI")
JUDUL_EN = ("Design of a pip Interceptor with a Project-Level Cooldown and a Time-Aware Evaluation against New "
            "Malicious PyPI Packages")


def _judul_kapital(t):
    return t.upper().replace("PIP ", "pip ").replace(" PIP", " pip").replace("PYPI", "PyPI")


def _tengah(m, teks, size=12, bold=False, line=1.0, after=0, before=0, italic=False):
    return m.p(teks, style="Tunggal", align="c", size=size, bold=bold, line=line, after=after, before=before,
               italic=italic)


def halaman_judul(m):
    I = IDENTITAS
    p = _tengah(m, "SKRIPSI", bold=True, after=48)
    m._tc(p, "HALAMAN JUDUL")
    m.isi.append((1, "HALAMAN JUDUL"))
    _tengah(m, _judul_kapital(JUDUL), size=14, bold=True, line=2.0, after=24)
    _tengah(m, "Ditulis untuk memenuhi sebagian persyaratan akademik\nguna memperoleh gelar Sarjana Komputer Strata "
               "Satu", size=10, after=48)
    _tengah(m, "Oleh:", bold=True, line=1.5)
    for lab, v in (("NAMA", I["nama"].upper()), ("NPM", I["npm"])):
        para = m.p(f"{lab}\t: {v}", style="Tunggal", bold=True, line=1.5, auto_italic=False)
        para.paragraph_format.left_indent = Cm(3.2)
        para.paragraph_format.tab_stops.add_tab_stop(Cm(5.4))
    para = m.doc.add_paragraph(style="Gambar")
    para.paragraph_format.space_before = Pt(36)
    para.paragraph_format.space_after = Pt(36)
    # logo resmi; lebar 4 cm = diameter lingkaran logo (Panduan: diameter empat cm), rasio aspek dipertahankan
    para.add_run().add_picture(str(FIG / "Logo UPH.png"), width=Cm(4))
    for t in (f"PROGRAM STUDI {I['program_studi'].upper()}", f"FAKULTAS {I['fakultas'].upper()}",
              "UNIVERSITAS PELITA HARAPAN", I["kota"].upper(), I["tahun"]):
        _tengah(m, t, bold=True)


def pernyataan(m):
    I = IDENTITAS
    m.page_break()
    p = _tengah(m, "UNIVERSITAS PELITA HARAPAN", size=14, bold=True, after=6)
    m._tc(p, "PERNYATAAN DAN PERSETUJUAN UNGGAH TUGAS AKHIR")
    m.isi.append((1, "PERNYATAAN DAN PERSETUJUAN UNGGAH TUGAS AKHIR"))
    _tengah(m, "Pernyataan dan Persetujuan Unggah Tugas Akhir", bold=True, after=12)
    m.p("Saya yang bertanda tangan di bawah ini:", style="Tunggal", size=10, after=6)
    for lab, v in (("Nama - NPM", f"{I['nama']} - {I['npm']}"), ("Fakultas", f"Fakultas {I['fakultas']}"),
                   ("Program Studi", I["program_studi"]), ("Lokasi Kampus", I["kota"]), ("Jenis Tugas Akhir",
                                                                                         "Skripsi"),
                   ("Judul", JUDUL)):
        para = m.p(f"{lab}\t:\t{v}", style="Tunggal", size=10, after=2)
        pf = para.paragraph_format
        pf.tab_stops.add_tab_stop(Cm(3.2))
        pf.tab_stops.add_tab_stop(Cm(3.6))
        pf.left_indent, pf.first_line_indent = Cm(3.6), Cm(-3.6)
    m.p("Menyatakan bahwa:", style="Tunggal", size=10, before=8, after=4)
    for k, t in enumerate([
        "Tugas akhir tersebut adalah benar karya saya dengan arahan dari dosen pembimbing dan bukan merupakan "
        "duplikasi karya tulis yang sudah dipublikasikan atau yang pernah dipakai untuk mendapatkan gelar akademik "
        "di perguruan tinggi manapun;",
        "Tugas akhir tersebut bukan merupakan plagiat dari hasil karya pihak lain, dan apabila saya mengutip dari "
        "karya orang lain maka akan dicantumkan sebagai referensi sesuai dengan ketentuan yang berlaku.",
        "Saya memberikan Hak Noneksklusif Tanpa Royalti kepada Universitas Pelita Harapan atas Tugas Akhir tersebut "
        "untuk diunggah ke dalam Repositori UPH."], 1):
        para = m.p(f"{k}.\t{t}", style="Tunggal", size=10, after=3)
        pf = para.paragraph_format
        pf.left_indent, pf.first_line_indent = Cm(0.9), Cm(-0.6)
        pf.tab_stops.add_tab_stop(Cm(0.9))
    m.p("Apabila di kemudian hari ditemukan pelanggaran Hak Cipta dan Kekayaan Intelektual atau Peraturan "
        "Perundang-undangan Republik Indonesia lainnya dan integritas akademik dalam karya saya tersebut, maka saya "
        "bersedia menanggung secara pribadi segala bentuk tuntutan hukum dan sanksi akademis yang timbul serta "
        "membebaskan Universitas Pelita Harapan dari segala tuntutan hukum yang berlaku.", style="Tunggal", size=10,
        before=6, after=8)
    for lab, v in (("Dibuat di", I["kota"]), ("Pada Tanggal", I["tanggal_persetujuan"])):
        para = m.p(f"{lab}\t: {v}", style="Tunggal", size=10)
        para.paragraph_format.tab_stops.add_tab_stop(Cm(2.6))
    m.p("Yang menyatakan,", style="Tunggal", size=10, after=6)
    t = m.doc.add_table(rows=2, cols=2)
    t.style = m.doc.styles["Table Grid"]
    for i, (a, b) in enumerate((("Tanda Tangan", "\n\nMeterai 10000\n\n"), ("Nama", f"( {I['nama']} )"))):
        for j, v in enumerate((a, b)):
            c = t.cell(i, j)
            c.width = Cm(3.0 if j == 0 else 7.0)
            c.paragraphs[0].style = m.doc.styles["Isi Tabel"]
            m.runs(c.paragraphs[0], v, size=10, italic=(v.strip() == "Meterai 10000"))
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER


def _kop(m, judul):
    _tengah(m, "UNIVERSITAS PELITA HARAPAN", size=14, bold=True)
    p = _tengah(m, f"FAKULTAS {IDENTITAS['fakultas'].upper()}", bold=True, after=4)
    pr = p._p.get_or_add_pPr()
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    bdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    for k, v in (("w:val", "thickThinSmallGap"), ("w:sz", "18"), ("w:space", "4"), ("w:color", "000000")):
        b.set(qn(k), v)
    bdr.append(b)
    pr.insert_element_before(bdr, "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
                             "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi",
                             "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
                             "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection", "w:textAlignment",
                             "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
                             "w:pPrChange")
    p = _tengah(m, judul, bold=True, before=18, after=18)
    m._tc(p, judul)
    m.isi.append((1, judul))


def _identitas(m, items, indent=2.5):
    for lab, v in items:
        para = m.p(f"{lab}\t: {v}", style="Tunggal", line=1.5, auto_italic=False)
        pf = para.paragraph_format
        pf.left_indent = Cm(indent)
        pf.tab_stops.add_tab_stop(Cm(indent + 3.3))


def _ttd(m, kiri, kanan, jarak=4):
    t = m.doc.add_table(rows=1, cols=2)
    for j, (jab, nama) in enumerate((kiri, kanan)):
        c = t.cell(0, j)
        c.width = Cm(7)
        if not jab:
            continue
        para = c.paragraphs[0]
        para.style = m.doc.styles["Tunggal"]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        m.runs(para, jab + "\n" * jarak + f"({nama})", bold=False)


def persetujuan_pembimbing(m):
    I = IDENTITAS
    _kop(m, "PERSETUJUAN DOSEN PEMBIMBING TUGAS AKHIR")
    _tengah(m, _judul_kapital(JUDUL), bold=True, line=1.5, after=6)
    _tengah(m, "Oleh:", after=6)
    _identitas(m, (("Nama", I["nama"]), ("NPM", I["npm"]), ("Program Studi", I["program_studi"]),
                   ("Peminatan", I["peminatan"])))
    m.p("Telah diperiksa dan disetujui untuk diajukan dan dipertahankan dalam Sidang Tugas Akhir guna memperoleh "
        f"gelar Sarjana Komputer Strata Satu pada Program Studi Informatika, Fakultas {I['fakultas']}, Universitas "
        f"Pelita Harapan, {I['kota']}, Sumatera Utara.", style="Tunggal", line=1.5, before=12, after=12)
    _tengah(m, f"{I['kota']}, {I['tanggal_persetujuan']}", after=4)
    _tengah(m, "Menyetujui:", after=12)
    _ttd(m, ("Dosen Pembimbing", I["pembimbing"]), ("Ketua Program Studi Informatika", I["kaprodi"]))
    m.p("", style="Tunggal", after=6)
    _ttd(m, (f"Associate Dean Fakultas {I['fakultas']}", I["associate_dean"]), ("", ""))


def persetujuan_penguji(m):
    I = IDENTITAS
    m.page_break()
    _kop(m, "PERSETUJUAN TIM PENGUJI TUGAS AKHIR")
    m.p(f"Pada {I['tanggal_sidang']} telah diselenggarakan Sidang Tugas Akhir untuk memenuhi sebagian persyaratan "
        "akademik guna memperoleh gelar Sarjana Komputer Strata Satu pada Program Studi Informatika, Fakultas "
        f"{I['fakultas']}, Universitas Pelita Harapan, atas nama:", style="Tunggal", line=1.5, after=8)
    _identitas(m, (("Nama", I["nama"]), ("NPM", I["npm"]), ("Program Studi", I["program_studi"]),
                   ("Fakultas", I["fakultas"])), indent=3.0)
    m.p(f"termasuk ujian Tugas Akhir yang berjudul \"{_judul_kapital(JUDUL)}\" oleh tim penguji yang terdiri dari:",
        style="Tunggal", line=1.5, before=8, after=12)
    t = m.doc.add_table(rows=4, cols=3)
    for j, h in enumerate(("Nama Penguji", "Jabatan dalam Tim Penguji", "Tanda Tangan")):
        c = t.cell(0, j)
        c.paragraphs[0].style = m.doc.styles["Tunggal"]
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        m.runs(c.paragraphs[0], h, bold=True)
    for i, (n, jab) in enumerate(((I["pembimbing"], "sebagai Ketua"), (I["penguji_2"], "sebagai Anggota"),
                                  (I["penguji_3"], "sebagai Anggota")), 1):
        for j, v in enumerate((f"{i}. {n}", jab, "\n\n______________")):
            c = t.cell(i, j)
            c.paragraphs[0].style = m.doc.styles["Tunggal"]
            m.runs(c.paragraphs[0], v, size=11)
    for row in t.rows:
        for j, w in enumerate((6.0, 4.0, 4.0)):
            row.cells[j].width = Cm(w)
    m.p(f"{I['kota']}, {I['tanggal_sidang']}", style="Tunggal", before=18)


def _jumlah_halaman(m, para):
    m.runs(para, "(")
    m.field_inline(para, "PAGEREF akhir_bagian_awal \\h", "…")
    m.runs(para, " + ")
    m.field_inline(para, "PAGEREF akhir_daftar_pustaka \\h", "…")
    m.runs(para, " halaman: {{jml:gambar}} gambar; {{jml:tabel}} tabel; {{jml:lampiran}} lampiran)")


def _hitung_kata(t):
    import re
    return len(re.findall(r"\w[\w,.%/–-]*", t.replace("*", "").replace("`", "")))


def abstrak(m):
    I = IDENTITAS
    D, C = N["detection"], N["cost"]
    X = N["exposure_estimators"]["by_shift"]["shift0"]
    p30, r30 = X["project"]["30"]["test"]["per_package"]["est"], X["release"]["30"]["test"]["per_package"]["est"]
    ratio = num(round(C["ratio"]["30"]["median"]))
    teks_id = (
        "Paket berbahaya pada Python Package Index (PyPI) umumnya merupakan proyek baru yang menjalankan kode saat "
        "dipasang dan cepat dihapus, sementara large language model merekomendasikan nama paket yang tidak terdaftar "
        "(slopsquatting). Penelitian ini merancang pipguard, interceptor pip berbahasa Go dengan intersepsi fungsi "
        "shell dan shim, serta mengevaluasi kebijakan waktu instalasi secara berbasis waktu menggunakan metode "
        "Design Science Research Methodology. Metadata 8.588 paket berbahaya yang telah dihapus direkonstruksi "
        "pada saat masih dapat dipasang, ditautkan dengan log unduhan dan laporan OSV, lalu dibagi menurut waktu. "
        f"Indikator metadata bergeser antarperiode, sedangkan umur proyek stabil. Masa tunggu tingkat proyek 30 "
        f"hari mencakup {pct(D['pipguard-v2']['mal'])}% paket berbahaya 2026 dan menghentikan {pct(p30)}% unduhan "
        f"rata-rata paket berbahaya, dibandingkan {pct(r30)}% untuk masa tunggu tingkat rilis, dengan biaya "
        f"unduhan sah terdampak sekitar {ratio} kali lebih kecil. Selisihnya berasal dari proyek yang disusupi dan "
        "pre-aged. pipguard lulus 43 skenario intersepsi, termasuk job CI dan agen AI, dengan tambahan sekitar "
        "11 ms. Disimpulkan bahwa masa tunggu tingkat proyek layak menjadi bawaan, dilengkapi aturan tingkat rilis.")
    teks_en = (
        "Malicious packages on the Python Package Index (PyPI) are mostly new projects that run code at install "
        "time and are removed quickly, while large language models recommend unregistered package names "
        "(slopsquatting). This study designs pipguard, a pip interceptor written in Go that combines shell "
        "functions with a PATH shim, and evaluates install-time policies with a time-aware method following the "
        "Design Science Research Methodology. The metadata of 8,588 removed malicious packages were reconstructed "
        "as they were while installable, linked to download logs and OSV reports, and split by time. Metadata "
        "indicators drifted between periods, whereas project age remained stable. A 30-day project-level cooldown "
        f"covered {pct(D['pipguard-v2']['mal']).replace(',', '.')}% of 2026 malicious packages and stopped "
        f"{pct(p30).replace(',', '.')}% of the downloads of the average malicious package, against "
        f"{pct(r30).replace(',', '.')}% for a release-level cooldown, at roughly {ratio.replace('.', ',')} times "
        "lower cost in affected legitimate downloads. The gap lies in compromised and pre-aged projects. pipguard "
        "passed 43 interception scenarios, including CI jobs and AI agents, at about 11 ms of overhead. A "
        "project-level cooldown is a sound default when complemented by release-level rules.")
    for judul_hal, nama_judul, teks, kunci, ref_lab in (
            ("ABSTRAK", _judul_kapital(JUDUL), teks_id,
             "Kata kunci: keamanan rantai pasok perangkat lunak; paket berbahaya; PyPI; masa tunggu dependensi; "
             "*concept drift*; halusinasi paket; Go", "Referensi"),
            ("ABSTRACT", JUDUL_EN.upper().replace("PIP ", "pip ").replace("PYPI", "PyPI"), teks_en,
             "Keywords: software supply chain security; malicious packages; PyPI; dependency cooldown; concept "
             "drift; package hallucination; Go", "References")):
        m.page_break()
        m.judul_awal(judul_hal, size=14)
        m.p(f"{I['nama']} ({I['npm']})", style="Tunggal", after=12)
        m.p(nama_judul, style="Tunggal", bold=True, align="l", after=0, auto_italic=judul_hal == "ABSTRAK")
        para = m.p("", style="Tunggal", after=12)
        _jumlah_halaman(m, para)
        if judul_hal == "ABSTRACT":
            for r in para.runs:
                r.text = r.text.replace(" halaman:", " pages:").replace(" gambar;", " figures;") \
                    .replace(" tabel;", " tables;").replace(" lampiran)", " appendices)")
        m.p(teks, style="Tunggal", after=12, auto_italic=judul_hal == "ABSTRAK")
        n = _hitung_kata(teks)
        assert n <= 200, f"{judul_hal}: {n} kata (> 200, Panduan 4.8)"
        m.p(f"{ref_lab}: {{{{jml:referensi}}}}", style="Tunggal", after=6)
        m.p(kunci, style="Tunggal", auto_italic=False)


def kata_pengantar(m):
    I = IDENTITAS
    m.page_break()
    m.judul_awal("KATA PENGANTAR", size=12)
    m.p("Puji syukur penulis panjatkan kepada Tuhan Yang Maha Esa atas segala berkat yang telah diberikan-Nya, "
        "sehingga Tugas Akhir ini dapat diselesaikan.")
    m.p(f"Tugas Akhir dengan judul \"{_judul_kapital(JUDUL)}\" ini ditujukan untuk memenuhi sebagian persyaratan "
        "akademik guna memperoleh gelar Sarjana Komputer Strata Satu pada Program Studi Informatika, Fakultas "
        f"{I['fakultas']}, Universitas Pelita Harapan, {I['kota']}.")
    m.p("Penulis menyadari bahwa tanpa bimbingan, bantuan, dan doa dari berbagai pihak, Tugas Akhir ini tidak akan "
        "dapat diselesaikan tepat pada waktunya. Oleh karena itu, penulis mengucapkan terima kasih yang "
        "sebesar-besarnya kepada semua pihak yang telah membantu dalam proses pengerjaan Tugas Akhir ini, yaitu "
        "kepada:")
    m.daftar([
        f"{I['rektor']}, selaku Rektor Universitas Pelita Harapan.",
        f"{I['dekan']}, selaku Dekan Fakultas {I['fakultas']}.",
        f"{I['executive_director']}, selaku Executive Director UPH Kampus Medan, dan {I['associate_dean']}, selaku "
        f"Associate Dean Fakultas {I['fakultas']}.",
        f"{I['kaprodi']}, selaku Ketua Program Studi Informatika (Kampus Kota Medan).",
        f"{I['pembimbing']}, selaku Dosen Pembimbing yang telah memberikan bimbingan dan banyak masukan kepada "
        "penulis.",
        f"{I['penasehat_akademik']}, selaku Penasehat Akademik penulis.",
        "Seluruh dosen yang telah mengajar penulis selama berkuliah di Universitas Pelita Harapan.",
        f"Staf karyawan Fakultas {I['fakultas']} dan perpustakaan yang telah membantu penulis dalam kegiatan "
        "administratif.",
        "Keluarga dan sahabat yang telah memberikan dukungan moril, doa, dan kasih sayang.",
    ])
    m.p("Penulis menyadari bahwa Tugas Akhir ini masih memiliki kekurangan. Oleh karena itu, kritik dan saran yang "
        "membangun sangat penulis harapkan. Semoga Tugas Akhir ini bermanfaat bagi pembaca dan bagi pengembangan "
        "keamanan rantai pasok perangkat lunak.")
    para = m.p(f"{I['kota']}, [bulan] {I['tahun']}\n\n\nPenulis", style="Tunggal", align="r", before=12)


def daftar_daftar(m, pra):
    """Daftar Isi, Daftar Gambar, Daftar Tabel, Daftar Lampiran (field TOC, diisi awal dari build pertama)."""
    m.page_break()
    m.judul_awal("DAFTAR ISI", size=14)
    gaya = {1: "toc 1", 2: "toc 2", 3: "toc 3"}
    m.daftar_field('TOC \\o "2-3" \\f C \\h \\z', pra.isi if pra else [], gaya)
    # lampiran: field kedua tepat di bawahnya (entri TC jenis L, nomor halaman A-1, B-1, ...)
    m.daftar_field(TOC_LAMPIRAN, [(1, g) for g in (pra.list_lampiran if pra else [])], "toc 1",
                   label_halaman=False)
    m.page_break()
    m.judul_awal("DAFTAR GAMBAR", size=12)
    m.daftar_field('TOC \\h \\z \\c "Gambar"', [(1, g) for g in (pra.list_gambar if pra else [])],
                   "table of figures")
    m.page_break()
    m.judul_awal("DAFTAR TABEL", size=12)
    m.daftar_field('TOC \\h \\z \\c "Tabel"', [(1, g) for g in (pra.list_tabel if pra else [])],
                   "table of figures")
    m.page_break()
    m.judul_awal("DAFTAR LAMPIRAN", size=12)
    paras = m.daftar_field(TOC_LAMPIRAN, [(1, g) for g in (pra.list_lampiran if pra else [])], "toc 1")
    # penanda di luar hasil field: hasil TOC dibuat ulang (dan penanda di dalamnya hilang) saat diperbarui
    m.penanda(m.p("", style="Tunggal"), "akhir_bagian_awal")


def tulis(m, pra):
    halaman_judul(m)
    pernyataan(m)
    # halaman iii dst.: angka Romawi kecil tercetak (Panduan 4.3.1)
    m.bagian_baru("lowerRoman", footer="")
    persetujuan_pembimbing(m)
    persetujuan_penguji(m)
    abstrak(m)
    kata_pengantar(m)
    daftar_daftar(m, pra)
