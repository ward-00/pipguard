#!/usr/bin/env python3
"""Bangun kelompok positif kedua: paket PyPI berbahaya yang PERNAH terdaftar.

Kelompok positif hasil reproduksi Spracklen dkk. seluruhnya tidak terdaftar,
sehingga hanya menguji I-01. Kelompok ini menguji heuristik I-02..I-06 pada
paket yang benar-benar dapat dipasang korban. Lihat README.md di folder ini.

Tiga langkah:

  names  OSV (ossf/malicious-packages) -> daftar nama + label typosquat
  sql    daftar nama -> kueri BigQuery ke bigquery-public-data.pypi.distribution_metadata
  meta   hasil kueri -> JSONL metadata historis untuk `evalset -positive-meta`

Hanya pustaka standar. Tidak pernah mengunduh atau memasang paket berbahaya:
yang diambil hanya metadata (nama, versi, waktu unggah, ringkasan, URL).
"""
import argparse
import csv
import json
import re
import sys
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

OSV_URL = "https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip"
TYPOSQUAT_RE = re.compile(r"typo-?squat", re.I)

# Harus sama dengan internal/registry/pypi.go (repoURLKeys).
REPO_URL_KEYS = {"Source", "Repository", "Source Code", "Homepage", "Code", "GitHub"}


def normalize(name):
    """PEP 503, sama dengan internal/parser.Normalize."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_time(s):
    s = s.replace(" UTC", "+00:00").replace("Z", "+00:00")
    t = datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def fmt_time(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_name_list(paths):
    names = set()
    for p in paths:
        for line in Path(p).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                names.add(normalize(line))
    return names


# ---------------------------------------------------------------- names

def cmd_names(a):
    zpath = Path(a.osv_zip)
    if not zpath.exists():
        print(f"mengunduh {OSV_URL} -> {zpath}", file=sys.stderr)
        zpath.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(OSV_URL, zpath)

    pkgs = {}
    withdrawn = 0
    with zipfile.ZipFile(zpath) as z:
        for entry in z.namelist():
            if not entry.startswith("MAL-"):
                continue
            rec = json.loads(z.read(entry))
            if rec.get("withdrawn"):
                withdrawn += 1
                continue
            typo = bool(TYPOSQUAT_RE.search(rec.get("details", "") + rec.get("summary", "")))
            for aff in rec.get("affected", []):
                if aff.get("package", {}).get("ecosystem") != "PyPI":
                    continue
                n = normalize(aff["package"]["name"])
                p = pkgs.setdefault(n, {"ids": set(), "published": rec["published"], "typosquat": False,
                                        "versions": set(), "all_versions": False})
                p["ids"].add(rec["id"])
                p["published"] = min(p["published"], rec["published"])
                p["typosquat"] |= typo
                # Rentang "introduced: 0" = semua versi berbahaya; selain itu
                # OSV mendaftar versi berbahaya secara eksplisit (mis. proyek
                # sah yang satu rilisnya dibobol).
                intro0 = any(e.get("introduced") == "0"
                             for rg in aff.get("ranges", []) for e in rg.get("events", []))
                if intro0 or not aff.get("versions"):
                    p["all_versions"] = True
                p["versions"].update(aff.get("versions", []))

    # Paket sah yang pernah dibobol (mis. rilis berbahaya pada proyek mapan)
    # berlabel ganda; keluarkan agar positif dan negatif tidak tumpang tindih.
    negatives = read_name_list(a.exclude) if a.exclude else set()
    overlap = sorted(set(pkgs) & negatives)
    for n in overlap:
        del pkgs[n]

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "typosquat", "published", "mal_ids", "mal_versions"])
        for n in sorted(pkgs):
            p = pkgs[n]
            # mal_versions kosong = semua versi berbahaya.
            versions = "" if p["all_versions"] else " ".join(sorted(p["versions"]))
            w.writerow([n, str(p["typosquat"]).lower(), p["published"], " ".join(sorted(p["ids"])), versions])

    ntypo = sum(p["typosquat"] for p in pkgs.values())
    print(f"{len(pkgs)} nama ({ntypo} berlabel typosquat) -> {out}")
    print(f"dikeluarkan: {withdrawn} laporan withdrawn, {len(overlap)} tumpang tindih dengan negatif"
          + (f" ({', '.join(overlap)})" if overlap else ""))


def read_names_csv(path):
    with open(path, newline="") as f:
        return {r["name"]: r for r in csv.DictReader(f)}


# ---------------------------------------------------------------- sql

SQL_TEMPLATE = """\
-- Dihasilkan oleh scripts/malicious/build_malicious_set.py sql ({count} nama).
-- Satu baris per (paket, versi): waktu unggah pertama versi itu dan metadata
-- berkas pertamanya. Tabel ini tidak menghapus baris saat proyek dihapus dari
-- PyPI (docs.pypi.org/api/bigquery), sehingga paket berbahaya tetap ada.
WITH files AS (
  SELECT LOWER(REGEXP_REPLACE(name, r'[-_.]+', '-')) AS norm_name,
         version, upload_time, summary, home_page, project_urls
  FROM `bigquery-public-data.pypi.distribution_metadata`
), per_version AS (
  SELECT norm_name, version,
         ARRAY_AGG(STRUCT(upload_time, summary, home_page, project_urls)
                   ORDER BY upload_time LIMIT 1)[OFFSET(0)] AS f
  FROM files
  WHERE norm_name IN UNNEST([
{names}
  ])
  GROUP BY norm_name, version
)
SELECT norm_name, version, f.upload_time, f.summary, f.home_page, f.project_urls
FROM per_version
ORDER BY norm_name, upload_time
"""


def cmd_sql(a):
    names = sorted(read_names_csv(a.names))
    body = ",\n".join(f"  '{n}'" for n in names)
    Path(a.out).write_text(SQL_TEMPLATE.format(count=len(names), names=body))
    print(f"kueri untuk {len(names)} nama -> {a.out}")


# ---------------------------------------------------------------- meta

def load_bq_rows(path):
    """Ekspor BigQuery: larik JSON (bq --format=json) atau JSONL (konsol)."""
    text = Path(path).read_text()
    try:
        rows = json.loads(text)
        if isinstance(rows, list):
            return rows
    except json.JSONDecodeError:
        pass
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def has_repository(project_urls):
    # Elemen project_urls berbentuk "Label, https://...".
    for item in project_urls or []:
        label, _, url = item.partition(",")
        if label.strip() in REPO_URL_KEYS and url.strip():
            return True
    return False


def snapshot(versions, as_of):
    """Metadata yang akan dilihat PyPI JSON API pada waktu as_of."""
    live = [v for v in versions if v["upload_time"] <= as_of]
    latest = live[-1]
    return {
        "exists": True,
        "first_release": fmt_time(live[0]["upload_time"]),
        "release_count": len(live),
        "has_homepage": bool(latest.get("home_page")),
        "has_repository": has_repository(latest.get("project_urls")),
        "summary": latest.get("summary") or "",
    }


def cmd_meta(a):
    wanted = read_names_csv(a.names)
    by_name = {}
    for r in load_bq_rows(a.bq_results):
        r["upload_time"] = parse_time(r["upload_time"])
        by_name.setdefault(r["norm_name"], []).append(r)

    out_lines, missing = [], []
    groups = {}
    for n in sorted(wanted):
        versions = sorted(by_name.get(n, []), key=lambda v: v["upload_time"])
        if not versions:
            missing.append(n)
            continue
        if a.as_of == "first":
            # Korban memasang tepat setelah versi pertama diunggah.
            as_of = versions[0]["upload_time"] + timedelta(minutes=1)
        elif a.as_of == "last":
            # Keadaan terakhir yang diketahui sebelum dihapus.
            as_of = versions[-1]["upload_time"] + timedelta(minutes=1)
        else:
            # Saat dilaporkan ke OSV; bila laporan mendahului unggahan
            # (selisih jam), pakai keadaan terakhir.
            as_of = max(parse_time(wanted[n]["published"]), versions[0]["upload_time"] + timedelta(minutes=1))
        group = "malicious-typosquat" if wanted[n]["typosquat"] == "true" else "malicious-other"
        groups[group] = groups.get(group, 0) + 1
        rec = {"name": n, "group": group, "as_of": fmt_time(as_of), **snapshot(versions, as_of)}
        out_lines.append(json.dumps(rec, ensure_ascii=False))

    Path(a.out).write_text("\n".join(out_lines) + "\n")
    print(f"{len(out_lines)}/{len(wanted)} nama punya metadata historis -> {a.out} (as_of={a.as_of})")
    for g, c in sorted(groups.items()):
        print(f"  {g}: {c}")
    if missing:
        print(f"tidak ditemukan di BigQuery (dikeluarkan): {len(missing)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("names", help="ekstrak nama paket berbahaya dari OSV")
    p.add_argument("--osv-zip", default="scripts/malicious/data/PyPI_all.zip")
    p.add_argument("--exclude", nargs="*", default=["testdata/negative_top1000.txt", "testdata/negative_newest.txt"],
                   help="berkas nama negatif yang dikeluarkan dari positif")
    p.add_argument("--out", default="testdata/malicious_osv.csv")
    p.set_defaults(func=cmd_names)

    p = sub.add_parser("sql", help="tulis kueri BigQuery")
    p.add_argument("--names", default="testdata/malicious_osv.csv")
    p.add_argument("--out", default="scripts/malicious/query.sql")
    p.set_defaults(func=cmd_sql)

    p = sub.add_parser("meta", help="ubah hasil BigQuery menjadi JSONL untuk evalset")
    p.add_argument("--names", default="testdata/malicious_osv.csv")
    p.add_argument("--bq-results", default="scripts/malicious/data/bq_results.json")
    p.add_argument("--as-of", choices=["first", "last", "reported"], default="last")
    p.add_argument("--out")
    p.set_defaults(func=cmd_meta)

    a = ap.parse_args()
    if a.cmd == "meta" and not a.out:
        a.out = f"testdata/malicious_meta_{a.as_of}.jsonl"
    a.func(a)


if __name__ == "__main__":
    main()
