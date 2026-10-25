# Kelompok positif kedua: paket berbahaya yang pernah terdaftar

## Mengapa diperlukan

Seluruh kelompok positif hasil reproduksi (`testdata/positive_reproduced.txt`)
**tidak terdaftar** di PyPI, dan seluruh kelompok negatif **terdaftar**.
Akibatnya baseline satu baris "tandai bila tidak terdaftar" (I-01 saja)
mengungguli pipguard pada data itu (lihat `testdata/ACCURACY_NOTES.md`,
bagian Baseline). Heuristik I-02..I-06 — inti kontribusi pipguard — belum
pernah diuji pada paket berbahaya yang benar-benar dapat dipasang.

Kelompok ini berisi paket PyPI yang dilaporkan berbahaya di
[OSV / ossf/malicious-packages](https://github.com/ossf/malicious-packages)
(rekaman `MAL-*`), dinilai dengan metadata **seperti saat paket itu masih
dapat dipasang**.

## Mengapa tidak diambil langsung dari PyPI

PyPI menghapus paket berbahaya; 150/150 sampel acak mengembalikan 404
(2026-10-14). Pengambilan langsung hanya akan menguji ulang I-01.
Metadata historis diambil dari tabel BigQuery publik
`bigquery-public-data.pypi.distribution_metadata`, yang menurut
[dokumentasi PyPI](https://docs.pypi.org/api/bigquery/) tidak menghapus baris
meskipun rilis atau proyeknya dihapus.

## Langkah

```bash
# 1. Nama dari OSV (sudah dijalankan; mengunduh PyPI/all.zip bila belum ada)
python3 scripts/malicious/build_malicious_set.py names
#    -> testdata/malicious_osv.csv   (11.800 nama, 544 berlabel typosquat)

# 2. Kueri BigQuery (sudah dijalankan)
python3 scripts/malicious/build_malicious_set.py sql
#    -> scripts/malicious/query.sql

# 3. Jalankan kueri di BigQuery — PERLU AKUN GOOGLE CLOUD (lihat di bawah)
#    Simpan hasil ke scripts/malicious/data/bq_results.json

# 4. Ubah ke JSONL untuk evalset, untuk ketiga skenario waktu
for m in first last reported; do
  python3 scripts/malicious/build_malicious_set.py meta --as-of $m
done
#    -> testdata/malicious_meta_{first,last,reported}.jsonl

# 5. Evaluasi (ulangi untuk tiap skenario)
make build && go build -o build/evalset ./cmd/evalset
./build/evalset \
  -positive testdata/positive_reproduced.txt \
  -positive-meta testdata/malicious_meta_last.jsonl \
  -negative testdata/negative_top1000.txt,testdata/negative_newest.txt \
  -out testdata/results_with_malicious_last.csv
```

### Menjalankan kueri (langkah 3)

Konsol: buka https://console.cloud.google.com/bigquery, tempel isi
`query.sql`. **Periksa perkiraan "This query will process X GB" sebelum
menjalankan** — kuota gratis 1 TB/bulan. Simpan hasil sebagai JSON.

CLI (`gcloud` + `bq`):

```bash
bq query --use_legacy_sql=false --dry_run "$(cat scripts/malicious/query.sql)"   # cek biaya dulu
bq query --use_legacy_sql=false --format=json --max_rows=10000000 \
  "$(cat scripts/malicious/query.sql)" > scripts/malicious/data/bq_results.json
```

Langkah `meta` melaporkan berapa nama yang tidak ditemukan di BigQuery;
laporkan angka cakupan ini di Bab IV.

## Skenario waktu (`--as-of`) — laporkan ketiganya

Kapan tepatnya korban memasang paket tidak diketahui, jadi hasil dilaporkan
sebagai analisis sensitivitas:

| Skenario | Saat penilaian | Sifat |
|---|---|---|
| `first` | 1 menit setelah versi pertama diunggah | Paling menguntungkan I-02/I-03 (batas atas) |
| `last` | 1 menit setelah versi terakhir diunggah | Keadaan terakhir yang diketahui |
| `reported` | Saat laporan OSV diterbitkan | Paling realistis untuk korban "terlambat"; sebagian laporan OSV adalah impor massal data lama (lonjakan 2023), sehingga umur bisa berlebih (batas bawah) |

Metadata yang dibangun meniru apa yang dilihat `internal/registry` dari PyPI
JSON API pada saat itu: `first_release` = unggahan paling awal, `release_count`
= jumlah versi yang sudah diunggah, ringkasan/homepage/URL dari versi terbaru.

## Kelompok di keluaran evalset

- `malicious-typosquat` — laporan OSV menyebut typosquatting (sasaran utama pipguard)
- `malicious-other` — berbahaya, tetapi bukan typosquat menurut laporan
  (mis. dependency confusion, nama acak). Recall rendah di sini bukan
  kegagalan desain, tetapi tetap dilaporkan.

## Pengecualian (laporkan di Bab III)

- 25 laporan berstatus `withdrawn` (ditarik karena salah lapor).
- 2 nama tumpang tindih dengan kelompok negatif: `litellm`, `mistralai` —
  paket sah yang salah satu rilisnya pernah dibobol. Dikeluarkan dari
  positif agar tidak berlabel ganda.

## Keamanan

Nama-nama ini sudah publik di OSV, jadi berbeda dengan nama halusinasi,
tidak ada risiko slopsquatting tambahan. Skrip ini **tidak pernah mengunduh
artefak paket** — hanya metadata. `data/` (zip OSV, hasil BigQuery) di-.gitignore
karena besar.
