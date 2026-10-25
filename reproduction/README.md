# Reproduksi Dataset Halusinasi Paket (Metodologi Spracklen et al., USENIX Security 2025)

Folder ini mereproduksi **kelompok positif** untuk studi akurasi pipguard
dengan mengikuti metodologi upstream:
https://github.com/Spracks/PackageHallucination

## Mengapa direproduksi, bukan diunduh

Upstream sengaja tidak merilis daftar nama paket halusinasi (alasan: dapat
dipakai untuk serangan package confusion/slopsquatting). Daftar itu hanya
dapat diminta peneliti terverifikasi. Maka kelompok positif dibangkitkan
ulang dengan kode upstream yang tersedia publik.

## Alur (sama dengan `run_test.py` upstream)

1. **generate_code** — LLM menulis kode Python untuk setiap prompt
   (`Data/Python/{LLM,SO}_{AT,LY}.json`)
2. **aggregate_results** — kode digabung dengan prompt
3. **generate_package_names** — LLM mendaftar paket dari (1) kode dan (2) prompt
4. **package_detection** — setiap nama dicocokkan dengan `pypi_package_names.csv`
   (≈500 ribu nama master) dan `false_positive_packages.csv`; nama yang tidak
   ada di master dan tidak di daftar false-positive = **halusinasi**

Semua skrip logika (`package_detection.py`, `custom_parse_python.py`,
`aggregate_results.py`) dipakai **tanpa perubahan**.

## Deviasi dari upstream (wajib dilaporkan di Bab III/IV)

| Aspek | Upstream | Reproduksi ini | Alasan |
|---|---|---|---|
| Model | 16 LLM, termasuk DeepSeek 1B | 1 model: DeepSeek-Coder 1.3B instruct (`deepseek-ai/deepseek-coder-1.3b-instruct`), dinamai `DeepSeek_1B` | Keterbatasan perangkat (CPU, 7 GB RAM, tanpa GPU). Nama `DeepSeek_1B` dipilih agar aturan pasca-proses upstream berlaku |
| Perangkat | CUDA | CPU, bfloat16 (`device_map="cpu"`) | Tidak ada GPU |
| Jumlah prompt | ±4.900 per dataset (≈19.600 total) | Sampel acak berbenih, N per dataset (lihat `make_subset`) | Waktu generasi CPU |
| Suhu, top-k, top-p | 0.7 / 0.01 / 20 / 0.9 | sama | — |
| Panjang kode maks | 2048 token | sama (lihat `generate_code.py`) | — |

Hasil **bukan** replikasi tingkat-paper; ini sampel kecil dari satu model.
Angka persentase halusinasi tidak dapat langsung dibandingkan dengan paper.

## Definisi kelompok positif

- **Sumber (sama dengan upstream):** gabungan tiga heuristik di
  `PACKAGE_NAMES.csv` — `hallucinated_1` (LLM mendaftar paket dari kode),
  `hallucinated_2` (LLM merekomendasikan paket dari prompt), dan
  `pip_hallucinated` (baris `pip install <nama>` di kode). Ringkasan mencatat
  jumlah per sumber.
- **Verifikasi langsung (tambahan, bukan upstream):** setiap nama diperiksa
  ulang ke PyPI **saat ini** oleh `build_positive_set.py`. Master list berasal
  dari snapshot lama; nama yang sekarang sudah terdaftar **dikeluarkan**.

Lokasi hasil:

- `../testdata/positive_reproduced.txt` — daftar nama (**sensitif**, di-.gitignore)
- `../testdata/positive_reproduced_summary.md` — agregat saja (aman dilampirkan)

## Keamanan data (penting)

Folder `Tests/` dan daftar positif berisi nama-nama yang **belum terdaftar**
di PyPI. Keduanya **tidak boleh** dipublikasikan atau di-commit. Lihat
`.gitignore`. Hanya agregat (jumlah, persentase, metrik) yang masuk ke Bab IV.

## Menjalankan

```bash
cd reproduction
.venv/bin/python run_experiment.py --n 25            # generate + query + detect
.venv/bin/python run_experiment.py --stage detect    # hanya deteksi (ulang)
.venv/bin/python build_positive_set.py               # verifikasi PyPI + tulis kelompok positif
```

Bila terhenti (mis. perangkat mati), cukup jalankan ulang perintah yang sama:
pekerjaan yang sudah lengkap dilewati, berkas parsial dihapus lalu dibangkitkan
ulang. Sampel berbenih menghasilkan prompt yang identik di setiap run.

## Deviasi teknis tambahan

- `device_map="cuda"` → `device_map="cpu", torch_dtype="bfloat16"`
- `apply_chat_template(..., return_dict=False)` — tidak mengubah perilaku pada
  transformers 4.46.1 (versi yang dipin upstream dan dipakai di sini)
- Versi pustaka mengikuti pin upstream: transformers 4.46.1, tokenizers 0.20.1,
  accelerate 0.29.3. Torch 2.14.1+cpu (upstream: 2.2.2 CUDA).

Keluaran: `Tests/DeepSeek_1B_Python/PACKAGE_NAMES.csv` dan `FINAL_RESULTS.csv`.

## Lisensi model

DeepSeek-Coder 1.3B instruct: lisensi "other" (DeepSeek Model License).
Salinan `LICENSE` ada di `Models/DeepSeek_1B/`. Penggunaan untuk penelitian.
