#!/usr/bin/env python3
"""Membangun skripsi-writing/skripsi.docx dari keluaran evaluasi, dengan format Skripsi-example.docx dan Panduan.

Memerlukan python-docx. Jalankan figures_skripsi.py lebih dahulu bila gambar belum ada.
Pemakaian: python3 scripts/skripsi/build_skripsi.py [keluaran.docx]
Juga menulis <keluaran>.bib: seluruh entri Daftar Pustaka sebagai BibTeX untuk diimpor ke Mendeley.

Dokumen dibangun dua kali: bangunan pertama mengumpulkan judul, gambar, tabel, dan lampiran untuk isi awal
Daftar Isi dan daftar lainnya; nomor halaman diisi Word ketika field diperbarui saat berkas dibuka.
"""
import sys
from pathlib import Path

from docx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import akhir  # noqa: E402
import awal  # noqa: E402
import bab1  # noqa: E402
import bab2  # noqa: E402
import bab3  # noqa: E402
import bab4  # noqa: E402
import bab5  # noqa: E402
from ctx_id import REPO  # noqa: E402
from skripsilib import Skripsi  # noqa: E402

TEMPLATE = REPO / "skripsi-writing/Skripsi-example.docx"


def teks_isi(m):
    return " ".join(t.text or "" for t in m.doc.element.body.iter(qn("w:t")))


def bangun(pra=None):
    m = Skripsi(TEMPLATE)
    m.set_penulis(akhir.nama_penulis())
    m.bagian_pertama("lowerRoman", start=1, footer=None)
    awal.tulis(m, pra)
    m.bagian_baru("decimal", start=1, footer="")
    for bab in (bab1, bab2, bab3, bab4, bab5):
        bab.tulis(m)
    refs, tidak = akhir.daftar_pustaka(m, teks_isi(m))
    akhir.lampiran(m)
    m.ref["jml:gambar"] = str(len(m.list_gambar))
    m.ref["jml:tabel"] = str(len(m.list_tabel))
    m.ref["jml:lampiran"] = str(len(m.list_lampiran))
    return m, refs, tidak


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "skripsi-writing/skripsi.docx"
    pra, _, _ = bangun()
    m, refs, tidak = bangun(pra)
    hilang = akhir.cek_kutipan(teks_isi(m), refs)
    if hilang:
        raise SystemExit(f"kutipan tanpa entri Daftar Pustaka: {hilang}")
    m.save(out)
    out.with_suffix(".bib").write_text(akhir.bibtex(refs), encoding="utf-8")
    print(f"{out}: {len(m.isi)} judul, {len(m.list_gambar)} gambar, {len(m.list_tabel)} tabel, {len(m.list_lampiran)} lampiran, "
          f"{len(refs)} rujukan")
    if tidak:
        print("   rujukan jurnal yang tidak dikutip di skripsi (tidak dimasukkan):",
              "; ".join(r.split(".")[0] for r in tidak))


if __name__ == "__main__":
    main()
