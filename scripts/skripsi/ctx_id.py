"""Angka skripsi dari keluaran evaluasi (sama dengan naskah jurnal), dalam format bilangan Indonesia.

Desimal memakai koma dan ribuan memakai titik (8.588; 93,6%). Bilangan 0-9 yang menyatakan jumlah ditulis
dengan kata (Panduan 4.12 butir 6) melalui kata().
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "paper"))
from ctx import CMP, H, N, REPO, env, interception, latency, table_csv, wilson  # noqa: E402,F401

FIG_EN = REPO / "paper/figures"
FIG = REPO / "skripsi-writing/figures"
KATA = ["nol", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan"]


def _id(s):
    """Format bilangan bergaya Inggris ('8,588.5') menjadi gaya Indonesia ('8.588,5')."""
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def num(n):
    return _id(f"{n:,}")


def dec(x, nd=1):
    return _id(f"{x:,.{nd}f}")


def pct(x, nd=1):
    """Persentase tanpa tanda %: pct(0.936) -> '93,6'; pct((514, 546)) -> '94,1'."""
    if isinstance(x, (list, tuple)):
        x = x[0] / x[1]
    return dec(100 * x, nd)


def frac(kn):
    return f"{num(kn[0])}/{num(kn[1])}"


def kata(n):
    """Jumlah 0-9 dengan kata, selebihnya angka."""
    return KATA[n] if 0 <= n <= 9 else num(n)


_NUM = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\w]|\.\d)")


def id_angka(s):
    """Mengubah semua bilangan bergaya Inggris dalam teks sel tabel menjadi gaya Indonesia.

    Tanggal (2026-10-24), versi (26.2.2) dan kode (I-07) tidak diubah.
    """
    s = str(s)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s.strip("≈ ")):
        return s
    return _NUM.sub(lambda m: _id(m.group(0)), s)


def tabel_id(nama, header_id, terjemah=None, kolom_teks=()):
    """Membaca paper/tables/<nama>.csv, mengganti judul kolom dan menerjemahkan sel teks."""
    _, rows = table_csv(nama)
    terjemah = terjemah or {}
    out = []
    for r in rows:
        rr = []
        for j, v in enumerate(r):
            v = terjemah.get(v.strip(), v) if j in kolom_teks or not re.search(r"\d", v) else v
            rr.append(id_angka(v))
        out.append(rr)
    return header_id, out
