# Ringkasan Kelompok Positif (reproduksi Spracklen dkk.)

Model: `DeepSeek_1B` · diverifikasi ke PyPI: 2026-10-06T03:29:03Z

Hanya agregat — daftar nama ada di `positive_reproduced.txt` (sensitif, tidak di-commit).

| Tahap | Jumlah |
|---|---:|
| Kemunculan mentah `hallucinated_1` | 22 |
| Kemunculan mentah `hallucinated_2` | 30 |
| Kemunculan mentah `pip_hallucinated` | 7 |
| Nama unik terdeteksi halusinasi (gabungan) | 56 |
| Sekarang sudah terdaftar di PyPI (tingkat terpisah) | 2 |
| Gagal diverifikasi (dikeluarkan) | 0 |
| **Kelompok positif akhir (masih tidak terdaftar)** | **54** |

Sumber nama dalam kelompok akhir (satu nama bisa dari >1 sumber):

| Sumber | Nama |
|---|---:|
| `hallucinated_1` | 22 |
| `hallucinated_2` | 28 |
| `pip_hallucinated` | 6 |

## Kualitas kelompok positif

Dari 54 nama akhir, **7** jelas bukan nama paket menurut aturan sederhana (kata kunci/builtin Python, modul stdlib, fragmen berisi `=`, angka murni). Ini artefak parser upstream pada model kecil yang tidak patuh format, dan **tidak disaring** agar tetap setia pada metodologi. Aturan ini hanya batas bawah: nama variabel/kata sifat (mis. nama kolom data) tidak tertangkap.

Implikasi: aturan I-01 pipguard memberi BAHAYA pada string apa pun yang tidak terdaftar, sehingga recall pada kelompok ini mendekati 100% **menurut konstruksi**. Uji yang lebih bermakna adalah tingkat `registered` (nama halusinasi yang kini terdaftar), yang hanya dapat ditangkap heuristik umur/rilis/metadata.
