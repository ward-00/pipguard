"""Bangun kelompok positif untuk cmd/evalset dari hasil package_detection.

Masukan : Tests/<model>_Python/PACKAGE_NAMES.csv (keluaran upstream)
Keluaran:
  ../testdata/positive_reproduced.txt  — nama halusinasi (SENSITIF, di-.gitignore)
  ../testdata/positive_reproduced_registered.txt — nama yang tidak ada di master
      tetapi SEKARANG terdaftar (calon slopsquat; tingkat terpisah, di-.gitignore)
  ../testdata/positive_reproduced_summary.md — hanya agregat (aman dilampirkan)

Definisi halusinasi mengikuti upstream: nama yang tidak ada di master
pypi_package_names.csv dan tidak di false_positive_packages.csv, dari salah satu
tiga sumber: hallucinated_1 (query dari kode), hallucinated_2 (query dari
prompt), pip_hallucinated (baris `pip install` di kode).

Tambahan (bukan bagian upstream): setiap nama diverifikasi ulang ke PyPI saat
ini. Master list adalah snapshot lama. Nama yang SEKARANG sudah terdaftar
dipisah ke tingkat tersendiri: bisa paket sah yang baru dibuat, atau
pendaftaran oportunistik atas nama halusinasi (slopsquat) — justru kasus yang
menguji heuristik umur/metadata pipguard.
"""
import argparse
import ast
import builtins
import csv
import keyword
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ("hallucinated_1", "hallucinated_2", "pip_hallucinated")


# Nama yang jelas bukan nama paket: artefak parser upstream pada keluaran
# model kecil yang tidak patuh format. Hanya untuk PELAPORAN — tidak dipakai
# menyaring kelompok positif (agar tetap setia pada metodologi upstream).
_PY_NAMES = {k.lower() for k in keyword.kwlist} | {
    b.lower() for b in dir(builtins)} | set(sys.stdlib_module_names)


def looks_like_junk(name):
    flat = name.replace("-", "")
    return (
        name.replace("-", "_") in _PY_NAMES
        or flat in _PY_NAMES
        or "=" in name
        or flat.isdigit()
    )


def parse_list(cell):
    if not cell:
        return []
    try:
        v = ast.literal_eval(cell)
        return [str(x) for x in v] if isinstance(v, (list, tuple)) else []
    except (ValueError, SyntaxError):
        return []


def pypi_status(name, retries=4):
    """'missing' (404), 'exists' (200), atau 'error'."""
    url = f"https://pypi.org/pypi/{urllib.request.quote(name)}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "pipguard/1.0 (thesis research tool)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return "exists" if r.status == 200 else "error"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "missing"
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2 ** attempt)
    return "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-name", default="DeepSeek_1B")
    ap.add_argument("--delay", type=float, default=0.3, help="jeda antar-permintaan PyPI (detik)")
    args = ap.parse_args()

    src = os.path.join(HERE, "Tests", f"{args.model_name}_Python", "PACKAGE_NAMES.csv")
    out_dir = os.path.join(HERE, "..", "testdata")
    out_names = os.path.join(out_dir, "positive_reproduced.txt")
    out_summary = os.path.join(out_dir, "positive_reproduced_summary.md")
    out_registered = os.path.join(out_dir, "positive_reproduced_registered.txt")

    names = {}  # nama -> himpunan sumber
    raw_counts = {s: 0 for s in SOURCES}
    with open(src, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for s in SOURCES:
                for n in parse_list(row.get(s, "")):
                    n = n.strip()
                    if not n:
                        continue
                    raw_counts[s] += 1
                    names.setdefault(n, set()).add(s)

    status = {}
    for i, n in enumerate(sorted(names)):
        status[n] = pypi_status(n)
        time.sleep(args.delay)

    kept = sorted(n for n, st in status.items() if st == "missing")
    now_exists = sorted(n for n, st in status.items() if st == "exists")
    errors = sorted(n for n, st in status.items() if st == "error")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(out_names, "w", encoding="utf-8") as f:
        f.write("# SENSITIF — nama paket halusinasi yang BELUM terdaftar di PyPI.\n")
        f.write("# Jangan publikasikan / commit / bakar ke CD. Lihat remind.md #5.\n")
        f.write(f"# Model: {args.model_name}; diverifikasi ke PyPI: {stamp}\n")
        for n in kept:
            f.write(n + "\n")

    with open(out_registered, "w", encoding="utf-8") as f:
        f.write("# Nama halusinasi (tidak ada di master upstream) yang SEKARANG terdaftar di PyPI.\n")
        f.write("# Bisa paket sah baru ATAU slopsquat. Evaluasi terpisah; jangan dipublikasikan.\n")
        f.write(f"# Model: {args.model_name}; diverifikasi ke PyPI: {stamp}\n")
        for n in now_exists:
            f.write(n + "\n")

    by_source = {s: sum(1 for n in kept if s in names[n]) for s in SOURCES}
    junk = sum(1 for n in kept if looks_like_junk(n))
    with open(out_summary, "w", encoding="utf-8") as f:
        f.write("# Ringkasan Kelompok Positif (reproduksi Spracklen dkk.)\n\n")
        f.write(f"Model: `{args.model_name}` · diverifikasi ke PyPI: {stamp}\n\n")
        f.write("Hanya agregat — daftar nama ada di `positive_reproduced.txt` (sensitif, tidak di-commit).\n\n")
        f.write("| Tahap | Jumlah |\n|---|---:|\n")
        for s in SOURCES:
            f.write(f"| Kemunculan mentah `{s}` | {raw_counts[s]} |\n")
        f.write(f"| Nama unik terdeteksi halusinasi (gabungan) | {len(names)} |\n")
        f.write(f"| Sekarang sudah terdaftar di PyPI (tingkat terpisah) | {len(now_exists)} |\n")
        f.write(f"| Gagal diverifikasi (dikeluarkan) | {len(errors)} |\n")
        f.write(f"| **Kelompok positif akhir (masih tidak terdaftar)** | **{len(kept)}** |\n\n")
        f.write("Sumber nama dalam kelompok akhir (satu nama bisa dari >1 sumber):\n\n")
        f.write("| Sumber | Nama |\n|---|---:|\n")
        for s in SOURCES:
            f.write(f"| `{s}` | {by_source[s]} |\n")
        f.write("\n## Kualitas kelompok positif\n\n")
        f.write(f"Dari {len(kept)} nama akhir, **{junk}** jelas bukan nama paket menurut aturan "
                "sederhana (kata kunci/builtin Python, modul stdlib, fragmen berisi `=`, angka murni). "
                "Ini artefak parser upstream pada model kecil yang tidak patuh format, dan "
                "**tidak disaring** agar tetap setia pada metodologi. Aturan ini hanya batas bawah: "
                "nama variabel/kata sifat (mis. nama kolom data) tidak tertangkap.\n\n")
        f.write("Implikasi: aturan I-01 pipguard memberi BAHAYA pada string apa pun yang tidak "
                "terdaftar, sehingga recall pada kelompok ini mendekati 100% **menurut konstruksi**. "
                "Uji yang lebih bermakna adalah tingkat `registered` (nama halusinasi yang kini "
                "terdaftar), yang hanya dapat ditangkap heuristik umur/rilis/metadata.\n")

    print(f"unik={len(names)} sekarang_terdaftar={len(now_exists)} error={len(errors)} positif_akhir={len(kept)}")
    print(f"daftar  : {os.path.normpath(out_names)}")
    print(f"ringkas : {os.path.normpath(out_summary)}")


if __name__ == "__main__":
    main()
