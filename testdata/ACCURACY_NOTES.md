> **Catatan 2026-10-19 — dokumen ini riwayat, bukan hasil akhir.** Evaluasi v1 di bawah hanya memakai positif yang tidak terdaftar. Evaluasi v2 menambahkan 8.588 paket berbahaya yang pernah dapat dipasang dan memakai pembagian temporal.
> Hasil terkini dan cara mereproduksinya: `paper/RESULTS.md`; perubahan dan
> alasannya: `CHANGES.md`.

# Catatan Studi Akurasi (§6.2)

## Hasil akhir (setelah perbaikan I-05, 2026-10-06)

`results_full.csv` — `build/evalset` dengan kelompok positif hasil reproduksi
dan kelompok negatif di bawah. Semua 1.092 nama berhasil diperiksa (0 error).

|  | Ditandai | Tidak ditandai |
|---|---:|---:|
| **Positif** (54 nama halusinasi) | TP = 54 | FN = 0 |
| **Negatif** (1.038 paket sah) | FP = 63 | TN = 975 |

| Metrik | Nilai |
|---|---:|
| Presisi | 0.4615 |
| Recall | 1.0000 |
| F1 | 0.6316 |
| FPR | 0.0607 |

Rincian FP: 38/38 paket baru (heuristik umur, Temuan 1) + 25/1000 paket mapan
(23 di antaranya karena kemiripan nama — sisa Temuan 2 setelah perbaikan).

**Cara membaca angka ini (wajib dibahas di Bab IV):**

- **Recall 1.0 hampir pasti menurut konstruksi.** Aturan I-01 memberi BAHAYA
  pada string apa pun yang tidak terdaftar di PyPI, dan seluruh kelompok
  positif memang tidak terdaftar. Selain itu, sebagian nama positif adalah
  artefak parser upstream (kata kunci, nama exception, nama variabel), bukan
  nama paket yang masuk akal — lihat `positive_reproduced_summary.md`.
- **Presisi bergantung pada rasio kelas.** 54 positif vs 1.038 negatif;
  presisi akan naik/turun bila rasio ini berubah tanpa perubahan alat. FPR
  adalah angka yang lebih dapat dibandingkan.
- **Tingkat `registered`** (nama halusinasi yang tidak ada di master upstream
  tetapi kini terdaftar): 2 nama, keduanya AMAN skor 0 — mapan, banyak rilis,
  metadata lengkap. Kemungkinan besar paket sah yang terlewat dari snapshot
  master upstream, bukan slopsquat. Terlalu sedikit untuk menyimpulkan apa pun
  tentang kemampuan pipguard menangkap slopsquat yang sudah terdaftar.
- **Hasil bergantung tanggal evaluasi.** 38 paket "baru" diambil 2026-09-21;
  setelah ±2026-10-21 umurnya melewati 30 hari dan tidak lagi memicu I-02.
  Ambil ulang RSS PyPI bila evaluasi diulang.

## Baseline dan ablasi (2026-10-14)

Dijalankan ulang dengan `build/evalset` versi baru pada data yang sama.
Angka pipguard identik dengan tabel di atas. Rentang = Wilson 95%.

| Detektor | Recall | FPR gabungan | FPR top-1000 | FPR newest |
|---|---|---|---|---|
| pipguard | 1.000 [0.934–1.000] | 0.061 [0.048–0.077] | 25/1000 | 38/38 |
| registry-only (I-01 saja) | 1.000 [0.934–1.000] | 0.003 [0.001–0.008] | 0/1000 | 3/38 |
| similarity-only (I-05 saja) | 0.019 [0.003–0.098] | 0.022 [0.015–0.033] | 23/1000 | 0/38 |
| tanpa I-02 | 1.000 | 0.041 | 25/1000 | 17/38 |
| tanpa I-05 | 1.000 | 0.039 | 2/1000 | 38/38 |
| tanpa I-03 / I-04 / I-06 | 1.000 | 0.060 | 24/1000 | 38/38 |

**Implikasi (wajib dibahas):**

- Pada data ini, baseline registry-only **mengungguli** pipguard (FPR 0.3%
  vs 6.1%, recall sama). Penyebabnya desain data, bukan alat: positif
  semuanya tidak terdaftar, negatif semuanya terdaftar. Data ini tidak bisa
  menunjukkan nilai I-02..I-06. Kelompok positif kedua (paket berbahaya yang
  pernah terdaftar) disiapkan di `scripts/malicious/` untuk mengujinya.
- I-05 menyumbang 23 dari 25 FP pada paket mapan dan hanya menangkap 1/54
  nama halusinasi. I-02 menyumbang 21 dari 38 FP pada paket baru.
- 3 paket `negative_newest` kini 404 (`swipeflow-api`, `lythosfea`,
  `basechekersz`) — dihapus setelah 2026-09-21, tidak ada di OSV; alasan
  penghapusan tidak diketahui. Kemungkinan derau label; sebutkan.
- Ambang `minSimilarityNameLen = 6` dipilih setelah melihat FP pada
  `negative_top1000.txt`, lalu FPR dilaporkan pada berkas yang sama —
  angka ini *in-sample*. Validasi pada himpunan terpisah (mis. peringkat
  1001–5000) sebelum diklaim sebagai hasil generalisasi.

## Perbaikan I-05 yang diterapkan (opsi 1)

Heuristik kemiripan nama kini hanya berlaku untuk nama ≥6 karakter
(`minSimilarityNameLen` di `internal/scorer/scorer.go`). Dampak pada kelompok
negatif yang sama: FP paket mapan 63 → 25, FPR gabungan 9.74% → 6.07%.
Sisa 23 FP kemiripan adalah pasangan nama ≥6 karakter yang memang mirip
secara tekstual tetapi sah (mis. `psycopg`↔`psycopg2`, `httpx2`↔`httpx`,
`authlib`↔`oauthlib`) — batasan yang tidak dapat diselesaikan dengan ambang
panjang saja.

---

*Bagian di bawah adalah catatan awal (sebelum perbaikan), dipertahankan
sebagai riwayat untuk Bab IV.*

## Kelompok negatif — SELESAI

- `negative_top1000.txt`: 1000 paket PyPI teratas berdasarkan unduhan
  30 hari terakhir. Sumber: snapshot publik hugovk
  (https://hugovk.github.io/top-pypi-packages/), diambil 2026-09-21.
- `negative_newest.txt`: 38 paket yang baru saja terdaftar di PyPI
  (kasus sulit, <30 hari). Sumber: RSS resmi PyPI
  (https://pypi.org/rss/packages.xml), diambil 2026-09-21 — daftar ini
  akan berbeda setiap kali diambil ulang karena selalu berisi rilis
  terbaru saat itu.

Hasil (`results_negative_only.csv`, dijalankan via `build/evalset`):

| | Ditandai (flagged) | Total | FPR |
|---|---:|---:|---:|
| Top-1000 established | 63 | 1000 | 6.3% |
| Newest (<30 hari, sengaja sulit) | 38 | 38 | 100% |
| **Gabungan** | **101** | **1038** | **9.74%** |

## Temuan 1 (diharapkan): heuristik umur paket

Seluruh 38 paket yang baru terdaftar ditandai — ini **persis** yang
diperkirakan oleh build_guide.md §6.2 ("paket sah yang baru rilis sebagai
kasus sulit — ini yang akan memunculkan false positive dan harus
dilaporkan jujur"). Bukan bug; heuristik I-02 (umur < 30 hari → +40 skor)
memang dirancang agresif terhadap paket baru, dan trade-off ini perlu
dibahas eksplisit di Bab IV.

## Temuan 2 (tidak diharapkan): heuristik kemiripan nama terlalu sensitif untuk nama pendek

63 dari 1000 paket **mapan** (established, bukan baru) ikut ditandai —
seluruhnya karena heuristik I-05 (jarak Levenshtein ≤2 dari nama populer),
BUKAN karena umur/metadata. Contoh:

| Paket asli | Dianggap mirip dengan | Jarak | Catatan |
|---|---|---|---|
| `mcp` | `pip` | 2 | Tidak terkait sama sekali secara semantik |
| `gitpython` | `ipython` | 2 | Tidak terkait |
| `h2` | `h11` | 2 | Tidak terkait |
| `jedi` | `redis` | 2 | Tidak terkait |
| `py4j` | `pytz` | 2 | Tidak terkait |

**Akar masalah:** untuk nama pendek (≤6 karakter), jarak Levenshtein ≤2
sangat mudah tercapai secara kebetulan — ruang kombinatorial string pendek
kecil, sehingga "mirip menurut edit distance" tidak berarti "mirip menurut
manusia/berisiko typosquat". Filter panjang yang ada
(`abs(len(a)-len(b))>2 → lewati`) mengurangi biaya komputasi tapi TIDAK
mengurangi angka false-positive ini, karena filter itu soal performa,
bukan soal ambang kemiripan.

**Bukan cacat implementasi** — ini kelemahan desain algoritmik pada
Tabel 3.5/3.6 yang diikuti apa adanya. Perlu didiskusikan di Bab IV/V
sebagai batasan, dan berikut opsi perbaikan yang dipertimbangkan (**opsi 1
diterapkan** — lihat "Perbaikan I-05 yang diterapkan" di atas; perubahan ini
juga perlu dicerminkan di Tabel 3.5/3.6 Bab III):

1. Naikkan ambang panjang minimum sebelum heuristik I-05 berlaku (mis.
   hanya berlaku bila `len(name) >= 5` atau `>= 6`)
2. Gunakan rasio jarak-terhadap-panjang (mis. jarak/panjang ≤ 0.3) alih-alih
   jarak absolut ≤2
3. Kombinasikan dengan bobot lebih rendah untuk I-05 sendirian tanpa sinyal
   lain (skor +30 saat ini otomatis melewati ambang PERINGATAN 20 hanya
   dari satu heuristik ini)

## Kelompok positif — direproduksi

Dataset resmi Spracklen dkk. sengaja tidak mempublikasikan daftar nama
halusinasinya (risiko slopsquatting; hanya untuk peneliti terverifikasi).
Kelompok positif karena itu **direproduksi** dengan kode upstream — lihat
`../reproduction/README.md` untuk metode dan deviasi (1 model DeepSeek-Coder
1.3B, 100 prompt berbenih, CPU).

- Ringkasan agregat (aman dilampirkan): `positive_reproduced_summary.md`
- Daftar nama (**sensitif**, di-.gitignore): `positive_reproduced.txt`
- Tingkat `registered` (**sensitif**, di-.gitignore): `positive_reproduced_registered.txt`
