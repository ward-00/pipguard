"""Penulis dokumen skripsi di atas python-docx, mengikuti format Skripsi-example.docx dan Panduan UPH Medan.

Gaya diambil dari templat (Heading 1-4, Paragraph, List Paragraph, Caption Style); isi templat dibuang.
Markah dalam teks:  *miring*  **tebal**  `kode`  {{gbr:kunci}} {{tbl:kunci}} {{sub:kunci}} (rujukan silang,
diisi saat disimpan). Istilah asing pada daftar ISTILAH_ASING dimiringkan otomatis (Panduan 4.12 butir 4).

Keterangan gambar dan tabel memakai field SEQ (label "Gambar"/"Tabel") sehingga Daftar Gambar dan Daftar Tabel
adalah Table of Figures Word (TOC \\c) yang tertaut; rujukan {{gbr:..}} dan {{tbl:..}} menjadi field REF ke
penanda pada label keterangan. Kutipan pustaka (nama penulis dari set_penulis) disorot kuning untuk diganti
dengan sitasi Mendeley; entri Daftar Pustaka disorot hijau (diganti Insert Bibliography Mendeley).

Penomoran halaman (Panduan 4.3): bagian awal angka Romawi kecil (halaman judul dan pernyataan dihitung tetapi
tidak dicetak), isi dan Daftar Pustaka angka Arab mulai 1, lampiran huruf-angka (A-1, B-1, ...). Daftar Isi,
Daftar Gambar, Daftar Tabel, Daftar Lampiran dan jumlah halaman pada Abstrak adalah field Word yang
diperbarui otomatis ketika berkas dibuka (settings: updateFields).
"""
import copy
import re
import zlib
from pathlib import Path

import docx
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

FONT = "Times New Roman"
MONO = "Courier New"
LEBAR_TEKS_CM = 14.0          # A4 21 cm - kiri 4 cm - kanan 3 cm
TWIP_PER_CM = 567
ROMAWI = ["", "I", "II", "III", "IV", "V", "VI", "VII"]
TOKEN = re.compile(r"(\{\{[^}]+\}\}|\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`)")
SOROT_KUTIPAN = WD_COLOR_INDEX.YELLOW
SOROT_PUSTAKA = WD_COLOR_INDEX.BRIGHT_GREEN
LABEL_SEQ = {"gbr": "Gambar", "tbl": "Tabel"}

# Istilah asing yang dimiringkan otomatis di luar `kode`. Urutan: frasa panjang lebih dahulu.
ISTILAH_ASING = sorted({
    "large language model", "large language models", "package hallucination", "hallucination",
    "slopsquatting", "typosquatting", "combosquatting", "dependency confusion", "package confusion",
    "cooldown", "interceptor", "shim", "shell function", "shell", "virtual environment",
    "prompt", "recall", "false positive rate", "false positive", "true positive rate", "true positive",
    "registry", "fail-open", "wheel", "wheels", "sdist", "bootstrap", "baseline", "pre-aging", "pre-aged",
    "continuous integration", "allowlist", "proxy", "sandbox", "lockfile", "dry run", "mirror",
    "user agent", "homepage", "classifier", "ridge", "active-set", "likelihood ratio", "hold-out",
    "in-sample", "temporal snooping", "concept drift", "drift", "use case", "use case diagram",
    "activity diagram", "sequence diagram", "class diagram", "lifeline", "struct", "interface", "include",
    "extend", "black box", "overhead", "round trip", "top-k", "top-p", "temperature", "receiver operating characteristic",
    "Design Science Research Methodology", "Unified Modeling Language", "problem-centered initiation",
    "field", "requirements", "constraints", "extra index", "index proxy", "pipeline",
    "release", "update bot", "dormancy", "account takeover", "maintainer", "provenance", "scanner",
    "infostealer", "payload", "build script", "build", "runtime", "supply chain",
    "coding agent", "agent", "framework", "tool use", "prompt injection", "alert fatigue", "habituation",
    "pull request", "pull requests", "update", "updates", "cross-compile", "cache", "timeout", "log",
    "trade-off", "ablation", "benchmark", "stub", "passthrough", "self-test", "smoke test",
    "quantization", "reasoning mode", "chat template", "fine-tuning", "retrieval augmented generation",
    "dataset", "ground truth", "outlier", "online", "offline", "default", "opt-in", "opt-out",
    "secure path", "home directory", "dependency", "dependencies", "transitive", "resolver", "resolution",
    "snapshot", "feed", "error", "standard error",
}, key=len, reverse=True)
_ISTILAH_RE = re.compile(r"(?<![\w/.`*-])(" + "|".join(re.escape(t) for t in ISTILAH_ASING) +
                         r")(?![\w/`*-]|\.\w)", re.IGNORECASE)


def _set_rfonts(rpr, name):
    f = rpr.find(qn("w:rFonts"))
    if f is None:
        f = OxmlElement("w:rFonts")
        rpr.insert(0, f)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        f.set(qn(a), name)


class Skripsi:
    def __init__(self, template):
        self.doc = docx.Document(str(template))
        body = self.doc.element.body
        for el in list(body):
            if el.tag != qn("w:sectPr"):
                body.remove(el)
        for rid, rel in list(self.doc.part.rels.items()):
            if not rel.is_external and rel.reltype.endswith("/image"):
                self.doc.part.drop_rel(rid)
        sect = body.find(qn("w:sectPr"))
        for ref in sect.findall(qn("w:headerReference")) + sect.findall(qn("w:footerReference")):
            sect.remove(ref)
        settings = self.doc.settings.element
        for tag in ("w:evenAndOddHeaders", "w:updateFields"):
            for e in settings.findall(qn(tag)):
                settings.remove(e)
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        # urutan skema CT_Settings: updateFields tepat sebelum hdrShapeDefaults/footnotePr/.../compat/rsids
        settings.insert_element_before(uf, "w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr", "w:compat",
                                       "w:docVars", "w:rsids", "m:mathPr", "w:attachedSchema", "w:themeFontLang",
                                       "w:clrSchemeMapping", "w:doNotIncludeSubdocsInStats",
                                       "w:doNotAutoCompressPictures", "w:forceUpgrade", "w:captions",
                                       "w:readModeInkLockDown", "w:smartTagType", "sl:schemaLibrary",
                                       "w:shapeDefaults", "w:doNotEmbedSmartTags", "w:decimalSymbol",
                                       "w:listSeparator")
        self._styles()
        self.bab_ke = 0
        self.prefix = ""                  # "3" untuk Bab III, "B" untuk Lampiran B
        self.n_gbr = self.n_tbl = 0
        self.n_h2 = self.n_h3 = self.n_h4 = 0
        self.list_gambar, self.list_tabel = [], []  # (label, judul) untuk isi awal daftar
        self.isi = []                     # (level, teks) untuk isi awal Daftar Isi
        self.list_lampiran = []
        self.ref = {}
        self.bookmark_id = 100
        self._kutipan_re = None
        self._seq_mulai = set()           # (label, prefix) yang sudah punya keterangan pertama
        self._first_in_section = True
        self.n_section = 1

    # ------------------------------------------------------------------ gaya
    def _styles(self):
        st = self.doc.styles

        def para_style(name, base, size=None, bold=None, italic=None, align=None, line=None, before=0, after=0,
                       first=None, left=None, keep_next=None, caps=None, font=None):
            s = st[name] if name in [x.name for x in st] else st.add_style(name, 1)
            if base:
                s.base_style = st[base]
            s.quick_style = True
            f = s.font
            if size:
                f.size = Pt(size)
            if bold is not None:
                f.bold = bold
            if italic is not None:
                f.italic = italic
            if caps is not None:
                f.all_caps = caps
            if font:
                f.name = font
                _set_rfonts(s.element.get_or_add_rPr(), font)
            pf = s.paragraph_format
            if align is not None:
                pf.alignment = align
            if line is not None:
                pf.line_spacing = line
            pf.space_before = Pt(before)
            pf.space_after = Pt(after)
            if first is not None:
                pf.first_line_indent = Cm(first)
            if left is not None:
                pf.left_indent = Cm(left)
            if keep_next is not None:
                pf.keep_with_next = keep_next
            return s

        J, C, L = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
        # Keterangan gambar/tabel: TNR 10, spasi tunggal, rata kiri kanan (Panduan 4.13 butir 5)
        para_style("Keterangan Gambar", "Caption Style", size=10, align=J, line=1.0, before=6, after=12,
                   keep_next=False)
        para_style("Keterangan Tabel", "Caption Style", size=10, align=J, line=1.0, before=12, after=6,
                   keep_next=True)
        para_style("Catatan Tabel", "Normal", size=10, align=J, line=1.0, before=3, after=12)
        para_style("Isi Tabel", "Normal", size=10, align=L, line=1.0, before=1, after=1)
        para_style("Gambar", "Normal", align=C, line=1.0, before=12, after=0, keep_next=True)
        para_style("Judul Awal", "Normal", size=14, bold=True, caps=True, align=C, line=1.0, after=24)
        para_style("Judul Lampiran", "Normal", size=12, bold=True, caps=True, align=L, line=1.5, after=12)
        para_style("Kode Program", "Normal", size=10, align=L, line=1.0, font=MONO)
        para_style("Pustaka", "Normal", size=12, align=J, line=1.0, after=12, first=-1.27, left=1.27)
        para_style("Tunggal", "Normal", align=J, line=1.0)
        # Daftar isi dan daftar gambar: TNR 12 spasi tunggal, tab kanan bertitik (Panduan 4.10-4.11)
        for name, left in (("toc 1", 0), ("toc 2", 0.9), ("toc 3", 1.8), ("table of figures", 0)):
            s = st[name]
            s.font.size = Pt(12)
            s.font.bold = False
            pf = s.paragraph_format
            pf.line_spacing = 1.0
            pf.space_after = Pt(6)
            pf.left_indent = Cm(left)
            pf.tab_stops.add_tab_stop(Cm(LEBAR_TEKS_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        ls = st["List Paragraph"].paragraph_format
        ls.left_indent, ls.first_line_indent = Cm(0.95), Cm(-0.63)

    # ------------------------------------------------------------------ kutipan
    def set_penulis(self, nama_keluarga):
        """Nama keluarga penulis pertama dari Daftar Pustaka; kutipan dengan nama ini disorot."""
        nama = "|".join(re.escape(n) for n in sorted(set(nama_keluarga), key=len, reverse=True))
        aut = rf"(?:[A-Z]\. )?(?:{nama})(?: dkk\.| dan [A-Z][\w-]+)?"
        cit = rf"{aut},? \d{{4}}"
        self._kutipan_re = re.compile(rf"\({cit}(?:; {cit})*\)|{aut} \(\d{{4}}\)|{cit}")

    def _pisah_kutipan(self, text):
        """[(potongan, kutipan?)]"""
        if not self._kutipan_re:
            return [(text, False)]
        out, pos = [], 0
        for m in self._kutipan_re.finditer(text):
            if m.start() > pos:
                out.append((text[pos:m.start()], False))
            out.append((m.group(0), True))
            pos = m.end()
        if pos < len(text):
            out.append((text[pos:], False))
        return out

    # ------------------------------------------------------------------ teks
    def _italic_terms(self, text):
        """Memecah teks biasa menjadi [(potongan, miring?)] menurut ISTILAH_ASING."""
        out, pos = [], 0
        for m in _ISTILAH_RE.finditer(text):
            if m.start() > pos:
                out.append((text[pos:m.start()], False))
            out.append((m.group(0), True))
            pos = m.end()
        if pos < len(text):
            out.append((text[pos:], False))
        return out

    def runs(self, p, text, size=None, bold=False, italic=False, auto_italic=True, mono=False, kutipan=True,
             sorot=None):
        for part in TOKEN.split(text):
            if not part:
                continue
            b, i, code = bold, italic, mono
            plain = part.startswith("{{")
            mref = re.fullmatch(r"\{\{(gbr|tbl):([^}]+)\}\}", part)
            if mref:
                self._field_ref(p, mref.group(1), mref.group(2), part, size=size, bold=b)
                continue
            if plain:
                pass
            elif part.startswith("**") and part.endswith("**") and len(part) > 4:
                part, b = part[2:-2], True
            elif part.startswith("`") and part.endswith("`"):
                part, code = part[1:-1], True
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                part, i = part[1:-1], True
            pieces = []
            for t, cit in ([(part, False)] if (plain or code or not kutipan) else self._pisah_kutipan(part)):
                if cit:
                    pieces.append((t, False, True))
                elif plain or code or i or not auto_italic:
                    pieces.append((t, False, False))
                else:
                    pieces.extend((tt, ti, False) for tt, ti in self._italic_terms(t))
            for t, ti, cit in pieces:
                segs = t.split("\n")
                for k, seg in enumerate(segs):
                    r = p.add_run(seg)
                    r.bold = b or None
                    r.italic = (i or ti) or None
                    if cit or sorot:
                        r.font.highlight_color = SOROT_KUTIPAN if cit else sorot
                    if code:
                        r.font.name = MONO
                        _set_rfonts(r._r.get_or_add_rPr(), MONO)
                        r.font.size = Pt((size or 12) - 1)
                    elif size:
                        r.font.size = Pt(size)
                    if k < len(segs) - 1:
                        r.add_break()
        return p

    def p(self, text, style="Paragraph", align=None, size=None, bold=False, italic=False, after=None, before=None,
          first=None, line=None, keep_next=None, auto_italic=True, kutipan=True, sorot=None):
        para = self.doc.add_paragraph(style=style)
        self.runs(para, text, size=size, bold=bold, italic=italic, auto_italic=auto_italic, kutipan=kutipan,
                  sorot=sorot)
        pf = para.paragraph_format
        if align:
            pf.alignment = {"c": WD_ALIGN_PARAGRAPH.CENTER, "l": WD_ALIGN_PARAGRAPH.LEFT,
                            "r": WD_ALIGN_PARAGRAPH.RIGHT, "j": WD_ALIGN_PARAGRAPH.JUSTIFY}[align]
        if after is not None:
            pf.space_after = Pt(after)
        if before is not None:
            pf.space_before = Pt(before)
        if first is not None:
            pf.first_line_indent = Cm(first)
        if line is not None:
            pf.line_spacing = line
        if keep_next is not None:
            pf.keep_with_next = keep_next
        self._first_in_section = False
        return para

    def daftar(self, items, gaya="1)", level=0, intro=None):
        """Daftar bernomor (Panduan 4.12 butir 7): 1) ... a) ... 1)) ..., tanpa butir (bullet)."""
        if intro:
            self.p(intro)
        for k, it in enumerate(items, 1):
            if gaya == "1)":
                lab = f"{k})"
            elif gaya == "a)":
                lab = f"{chr(96 + k)})"
            elif gaya == "1))":
                lab = f"{k}))"
            elif gaya == "1.":
                lab = f"{k}."
            else:
                lab = gaya
            para = self.doc.add_paragraph(style="List Paragraph")
            pf = para.paragraph_format
            pf.left_indent = Cm(0.95 + 0.75 * level)
            pf.first_line_indent = Cm(-0.75 if gaya == "1))" else -0.63)
            pf.tab_stops.add_tab_stop(pf.left_indent)
            pf.contextual_spacing = False
            if isinstance(it, tuple):           # (teks, sub-daftar)
                self.runs(para, f"{lab}\t{it[0]}")
                self.daftar(it[1], gaya="a)" if gaya in ("1)", "1.") else "1))", level=level + 1)
            else:
                self.runs(para, f"{lab}\t{it}")
        self._first_in_section = False

    # ------------------------------------------------------------------ judul
    def _tc(self, para, text, level=1):
        """Field TC: entri Daftar Isi tanpa teks yang tampak (dipakai untuk judul bab satu baris)."""
        self._field(para, f'TC "{text}" \\f C \\l {level}', "")

    def bab(self, nomor, judul, key=None):
        self.bab_ke = nomor
        self.prefix = str(nomor)
        self.n_gbr = self.n_tbl = self.n_h2 = 0
        para = self.doc.add_paragraph(style="Heading 1")
        para.add_run(f"BAB {ROMAWI[nomor]}").add_break()
        para.add_run(judul.upper())
        if self._first_in_section:
            para.paragraph_format.page_break_before = False
        self._tc(para, f"BAB {ROMAWI[nomor]} {judul.upper()}")
        self.isi.append((1, f"BAB {ROMAWI[nomor]} {judul.upper()}"))
        self._first_in_section = False
        if key:
            self.ref["bab:" + key] = f"Bab {ROMAWI[nomor]}"

    def judul_bab_lain(self, judul):
        """Judul setingkat bab tanpa nomor (DAFTAR PUSTAKA)."""
        para = self.doc.add_paragraph(style="Heading 1")
        para.add_run(judul.upper())
        if self._first_in_section:
            para.paragraph_format.page_break_before = False
        self._tc(para, judul.upper())
        self.isi.append((1, judul.upper()))
        self._first_in_section = False
        return para

    def h2(self, judul, key=None):
        self.n_h2 += 1
        self.n_h3 = 0
        num = f"{self.prefix}.{self.n_h2}"
        para = self.doc.add_paragraph(style="Heading 2")
        self.runs(para, f"{num}\t{judul}")
        self.isi.append((2, f"{num} {judul}"))
        if key:
            self.ref["sub:" + key] = f"Subbab {num}"
        self._first_in_section = False
        return num

    def h3(self, judul, key=None):
        self.n_h3 += 1
        self.n_h4 = 0
        num = f"{self.prefix}.{self.n_h2}.{self.n_h3}"
        para = self.doc.add_paragraph(style="Heading 3")
        self.runs(para, f"{num}\t{judul}")
        self.isi.append((3, f"{num} {judul}"))
        if key:
            self.ref["sub:" + key] = f"Subbab {num}"
        self._first_in_section = False
        return num

    def h4(self, judul):
        self.n_h4 += 1
        para = self.doc.add_paragraph(style="Heading 4")
        self.runs(para, f"{chr(64 + self.n_h4)}.\t{judul}")
        pf = para.paragraph_format
        pf.left_indent, pf.first_line_indent = Cm(0.63), Cm(-0.63)
        self._first_in_section = False

    def judul_awal(self, teks, size=14, toc=True):
        para = self.doc.add_paragraph(style="Judul Awal")
        r = para.add_run(teks.upper())
        r.font.size = Pt(size)
        if toc:
            self._tc(para, teks.upper())
            self.isi.append((1, teks.upper()))
        self._first_in_section = False
        return para

    def judul_lampiran(self, huruf, judul):
        """Judul lampiran: huruf = field SEQ Lampiran (\\* ALPHABETIC), entri TC berjenis L.

        Entri L dipakai Daftar Lampiran dan bagian lampiran pada Daftar Isi (TOC \\f L \\s Lampiran), sehingga
        entrinya tertaut dan bernomor halaman A-1, B-1, ... seperti kaki halaman lampiran.
        """
        self.prefix = huruf
        self.n_gbr = self.n_tbl = 0
        teks = f"LAMPIRAN {huruf}: {judul.upper()}"
        para = self.doc.add_paragraph(style="Judul Lampiran")
        para.add_run("LAMPIRAN ")
        awal = not self.list_lampiran
        self._field(para, "SEQ Lampiran \\* ALPHABETIC" + (" \\r 1" if awal else ""), huruf)
        para.add_run(f": {judul.upper()}")
        self._field(para, f'TC "{teks}" \\f L \\l 1', "")
        self.list_lampiran.append(teks)
        self._first_in_section = False
        return para

    def persamaan(self, rumus, key=None):
        """Persamaan di tengah dengan nomor (bab.urutan) rata kanan."""
        self.n_pers = getattr(self, "n_pers", 0) + 1
        if getattr(self, "_pers_bab", None) != self.prefix:
            self._pers_bab, self.n_pers = self.prefix, 1
        label = f"{self.prefix}.{self.n_pers}"
        para = self.doc.add_paragraph(style="Tunggal")
        pf = para.paragraph_format
        pf.space_before = Pt(6)
        pf.space_after = Pt(6)
        pf.tab_stops.add_tab_stop(Cm(LEBAR_TEKS_CM / 2), WD_TAB_ALIGNMENT.CENTER)
        pf.tab_stops.add_tab_stop(Cm(LEBAR_TEKS_CM), WD_TAB_ALIGNMENT.RIGHT)
        self.runs(para, f"\t{rumus}\t({label})", auto_italic=False)
        if key:
            self.ref["pers:" + key] = f"Persamaan ({label})"
        return label

    # ------------------------------------------------------------------ gambar dan tabel
    @staticmethod
    def _nama_penanda(jenis, key):
        """Nama penanda bergaya Word (_Ref + angka) untuk label keterangan yang dirujuk."""
        return f"_Ref{zlib.crc32(f'{jenis}:{key}'.encode()) % 900000000 + 100000000}"

    def _keterangan(self, style, jenis, judul, key=None):
        """Paragraf keterangan 'Gambar 3.1 Judul': label + field SEQ di dalam penanda, lalu judul."""
        label_seq = LABEL_SEQ[jenis]
        n = self.n_gbr if jenis == "gbr" else self.n_tbl
        label = f"{label_seq} {self.prefix}.{n}"
        cap = self.doc.add_paragraph(style=style)
        if key:
            self.bookmark_id += 1
            bs = OxmlElement("w:bookmarkStart")
            bs.set(qn("w:id"), str(self.bookmark_id))
            bs.set(qn("w:name"), self._nama_penanda(jenis, key))
            cap._p.append(bs)
        cap.add_run(f"{label_seq} {self.prefix}.")
        awal = (label_seq, self.prefix) not in self._seq_mulai
        self._seq_mulai.add((label_seq, self.prefix))
        self._field(cap, f"SEQ {label_seq} \\* ARABIC" + (" \\r 1" if awal else ""), str(n))
        if key:
            be = OxmlElement("w:bookmarkEnd")
            be.set(qn("w:id"), str(self.bookmark_id))
            cap._p.append(be)
        self.runs(cap, f" {judul}")
        return cap, label

    def _field_ref(self, para, jenis, key, placeholder, size=None, bold=False):
        """Field REF bertaut (\\h) ke label keterangan; hasil awal diisi _resolve_refs saat disimpan."""
        def fc(kind):
            r = OxmlElement("w:r")
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), kind)
            r.append(f)
            return r
        p = para._p
        p.append(fc("begin"))
        r = OxmlElement("w:r")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = f" REF {self._nama_penanda(jenis, key)} \\h "
        r.append(it)
        p.append(r)
        p.append(fc("separate"))
        run = para.add_run(placeholder)
        run.bold = bold or None
        if size:
            run.font.size = Pt(size)
        p.append(fc("end"))

    def gambar(self, path, judul, lebar_cm=14.0, key=None, sumber=None):
        self.n_gbr += 1
        label = f"Gambar {self.prefix}.{self.n_gbr}"
        para = self.doc.add_paragraph(style="Gambar")
        para.add_run().add_picture(str(path), width=Cm(min(lebar_cm, LEBAR_TEKS_CM)))
        cap, _ = self._keterangan("Keterangan Gambar", "gbr", judul, key)
        if sumber:
            cap.paragraph_format.space_after = Pt(0)
            s = self.p(f"Sumber: {sumber}", style="Catatan Tabel")
            s.paragraph_format.space_before = Pt(0)
        self.list_gambar.append(f"{label} {judul}")
        if key:
            self.ref["gbr:" + key] = label
        self._first_in_section = False
        return label

    def tabel(self, judul, header, rows, lebar=None, size=10, align=None, catatan=None, key=None, bold_first=False):
        """Tabel bergaris penuh seperti contoh; judul di atas tabel, catatan di bawah."""
        self.n_tbl += 1
        label = f"Tabel {self.prefix}.{self.n_tbl}"
        self._keterangan("Keterangan Tabel", "tbl", judul, key)
        ncol = len(header)
        if lebar is None:
            lebar = [LEBAR_TEKS_CM / ncol] * ncol
        skala = min(1.0, LEBAR_TEKS_CM / sum(lebar))
        lebar = [w * skala for w in lebar]
        align = align or ["l"] * ncol
        t = self.doc.add_table(rows=len(rows) + 1, cols=ncol)
        t.style = self.doc.styles["Table Grid"]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tblpr = t._tbl.tblPr
        mar = OxmlElement("w:tblCellMar")
        for side, w in (("left", 70), ("right", 70)):
            e = OxmlElement(f"w:{side}")
            e.set(qn("w:w"), str(w))
            e.set(qn("w:type"), "dxa")
            mar.append(e)
        tblpr.insert_element_before(mar, "w:tblLook", "w:tblCaption", "w:tblDescription")
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), lebar):
            gc.set(qn("w:w"), str(int(w * TWIP_PER_CM)))
        for i, row in enumerate([header] + [list(r) for r in rows]):
            tr = t.rows[i]
            trpr = tr._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
            if i == 0:
                trpr.append(OxmlElement("w:tblHeader"))
            for j in range(ncol):
                cell = tr.cells[j]
                cell.width = Cm(lebar[j])
                v = str(row[j]) if j < len(row) else ""
                para = cell.paragraphs[0]
                para.style = self.doc.styles["Isi Tabel"]
                para.alignment = {"l": WD_ALIGN_PARAGRAPH.LEFT, "r": WD_ALIGN_PARAGRAPH.RIGHT,
                                  "c": WD_ALIGN_PARAGRAPH.CENTER}["c" if i == 0 else align[j]]
                self.runs(para, v, size=size, bold=(i == 0) or (bold_first and j == 0))
                if i == 0:
                    tcpr = cell._tc.get_or_add_tcPr()
                    va = OxmlElement("w:vAlign")
                    va.set(qn("w:val"), "center")
                    tcpr.append(va)
        if catatan:
            self.p(catatan, style="Catatan Tabel")
        else:
            sp = self.doc.add_paragraph(style="Tunggal")
            sp.paragraph_format.space_after = Pt(6)
        self.list_tabel.append(f"{label} {judul}")
        if key:
            self.ref["tbl:" + key] = label
        self._first_in_section = False
        return label

    def kotak_kode(self, judul, baris, key=None, size=10):
        """Pseudokode atau keluaran teks dalam kotak bergaris, diperlakukan sebagai Gambar."""
        t = self.doc.add_table(rows=1, cols=1)
        t.style = self.doc.styles["Table Grid"]
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.cell(0, 0)
        cell.width = Cm(LEBAR_TEKS_CM - 0.5)
        para = cell.paragraphs[0]
        para.style = self.doc.styles["Kode Program"]
        for k, b in enumerate(baris):
            r = para.add_run(b)
            r.font.size = Pt(size)
            if k < len(baris) - 1:
                r.add_break()
        self.n_gbr += 1
        label = f"Gambar {self.prefix}.{self.n_gbr}"
        self._keterangan("Keterangan Gambar", "gbr", judul, key)
        self.list_gambar.append(f"{label} {judul}")
        if key:
            self.ref["gbr:" + key] = label
        return label

    # ------------------------------------------------------------------ field dan penanda
    def _field(self, para, instr, hasil):
        def fc(kind):
            r = OxmlElement("w:r")
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), kind)
            r.append(f)
            return r
        p = para._p
        p.append(fc("begin"))
        r = OxmlElement("w:r")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = f" {instr} "
        r.append(it)
        p.append(r)
        p.append(fc("separate"))
        if hasil:
            para.add_run(hasil)
        p.append(fc("end"))

    def field_inline(self, para, instr, hasil="?"):
        self._field(para, instr, hasil)

    def penanda(self, para, nama):
        """Bookmark pada paragraf (dipakai PAGEREF jumlah halaman di Abstrak)."""
        self.bookmark_id += 1
        s = OxmlElement("w:bookmarkStart")
        s.set(qn("w:id"), str(self.bookmark_id))
        s.set(qn("w:name"), nama)
        e = OxmlElement("w:bookmarkEnd")
        e.set(qn("w:id"), str(self.bookmark_id))
        para._p.append(s)
        para._p.append(e)

    def daftar_field(self, instr, entri, gaya_entri, label_halaman=True):
        """Field TOC; isi awal (tanpa nomor halaman) diganti Word saat field diperbarui."""
        if label_halaman:
            label = self.doc.add_paragraph(style="Tunggal")
            label.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            label.add_run("Halaman")
            label.paragraph_format.space_after = Pt(6)
        entri = entri or [(1, " ")]
        paras = []
        for lvl, teks in entri:
            st = gaya_entri if isinstance(gaya_entri, str) else gaya_entri[lvl]
            paras.append(self.doc.add_paragraph(style=st))
        def fc(kind):
            r = OxmlElement("w:r")
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), kind)
            r.append(f)
            return r
        first = paras[0]._p
        first.append(fc("begin"))
        r = OxmlElement("w:r")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = f" {instr} "
        r.append(it)
        first.append(r)
        first.append(fc("separate"))
        for para, (lvl, teks) in zip(paras, entri):
            para.add_run(teks + "\t")
        paras[-1]._p.append(fc("end"))
        self._first_in_section = False
        return paras

    # ------------------------------------------------------------------ halaman dan bagian
    def page_break(self):
        para = self.doc.add_paragraph(style="Tunggal")
        para.add_run().add_break(WD_BREAK.PAGE)

    def _sect_props(self, section, fmt, start, footer, cols=1):
        sp = section._sectPr
        for e in sp.findall(qn("w:pgNumType")):
            sp.remove(e)
        pg = OxmlElement("w:pgNumType")
        pg.set(qn("w:fmt"), fmt)
        if start is not None:
            pg.set(qn("w:start"), str(start))
        sp.append(pg)
        for e in sp.findall(qn("w:cols")):
            sp.remove(e)
        c = OxmlElement("w:cols")
        c.set(qn("w:space"), "567")
        if cols > 1:
            c.set(qn("w:num"), str(cols))
        sp.append(c)
        # urutan anak sectPr menurut skema: ... pgSz, pgMar, ..., pgNumType, cols, ...
        order = ["headerReference", "footerReference", "footnotePr", "endnotePr", "type", "pgSz", "pgMar",
                 "paperSrc", "pgBorders", "lnNumType", "pgNumType", "cols", "formProt", "vAlign", "noEndnote",
                 "titlePg", "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange"]
        kids = sorted(list(sp), key=lambda e: order.index(e.tag.split("}")[1]) if e.tag.split("}")[1] in order else 99)
        for k in kids:
            sp.remove(k)
            sp.append(k)
        section.footer.is_linked_to_previous = False
        section.header.is_linked_to_previous = False
        ft = section.footer.paragraphs[0]
        for r in list(ft.runs):
            r._r.getparent().remove(r._r)
        ft.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if footer is not None:
            if footer:
                ft.add_run(footer)
            self._field(ft, "PAGE", "1")

    def bagian_pertama(self, fmt="lowerRoman", start=1, footer=None):
        """Mengatur bagian (section) pertama: halaman judul dan pernyataan, nomor dihitung tetapi tidak dicetak."""
        self._sect_props(self.doc.sections[0], fmt, start, footer)

    def bagian_baru(self, fmt, start=None, footer="", cols=1, lanjut=False):
        """Section baru pada halaman baru (lanjut=True: pada halaman yang sama, mis. untuk dua kolom).

        footer=None: nomor tidak dicetak; "": nomor saja; "A-": nomor dengan awalan lampiran.
        """
        sec = self.doc.add_section(WD_SECTION.CONTINUOUS if lanjut else WD_SECTION.NEW_PAGE)
        self.n_section += 1
        self._sect_props(sec, fmt, start, footer, cols)
        self._first_in_section = not lanjut
        return sec

    # ------------------------------------------------------------------ simpan
    def _resolve_refs(self):
        pat = re.compile(r"\{\{(gbr|tbl|sub|bab|pers|jml):([^}]+)\}\}")
        missing = set()

        def rep(m):
            k = f"{m.group(1)}:{m.group(2)}"
            if k not in self.ref:
                missing.add(k)
                return "??"
            return self.ref[k]
        for t in self.doc.element.body.iter(qn("w:t")):
            if t.text and "{{" in t.text:
                t.text = pat.sub(rep, t.text)
        if missing:
            raise SystemExit(f"rujukan silang tidak ditemukan: {sorted(missing)}")

    def save(self, path):
        self._resolve_refs()
        self.doc.core_properties.language = "id-ID"
        self.doc.save(str(path))
