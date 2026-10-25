#!/usr/bin/env python3
"""Bangun himpunan evaluasi beku (frozen) untuk studi akurasi pipguard.

Semua langkah yang memerlukan jaringan menulis hasil mentahnya ke
testdata/frozen/, sehingga evaluasi (scripts/eval/run_all.sh) dapat diulang
tanpa jaringan dan memberi angka yang identik, terlepas dari tanggal.

Langkah (jaringan):
  malicious-fetch   OSV (testdata/malicious_osv.csv) -> metadata per-versi dari ClickHouse
  benign-sample     sampel acak paket baru yang sah (bertahan di PyPI, tidak di OSV)
  benign-fetch      sampel itu -> riwayat dari PyPI JSON API (baku) atau ClickHouse
  established       daftar teratas hugovk -> negatif mapan (dev/test), atau daftar populer v2
  consistency-fetch riwayat ClickHouse untuk 500 paket sampel konsistensi
  consistency       bandingkan ClickHouse vs PyPI, dan rekonstruksi vs registry Go
  install-share     porsi unduhan PyPI ke proyek < 30 hari (biaya masa tunggu)

Langkah (luring):
  meta              metadata per-versi -> JSONL per skenario untuk `evalset -*-meta`

Hanya pustaka standar.
"""
import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pypi_history as ph  # noqa: E402

FROZEN = Path("testdata/frozen")
RAW = FROZEN / "raw"

# Pembagian temporal menurut waktu unggahan pertama (untuk paket berbahaya:
# waktu versi berbahaya pertama):
#   dev  (< 2025)  kalibrasi awal yang ditetapkan sebelumnya ("v2-initial"),
#                  dan analisis pergeseran (drift)
#   val  (2025)    kalibrasi v2 final (bobot metadata, ambang BAHAYA, I-05)
#   test (≥ 2026)  pelaporan saja; tidak dipakai untuk keputusan desain apa pun
# Lihat paper/RESULTS.md, "Protokol", untuk alasan pembagian tiga ini.
VAL_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
TEST_START = datetime(2026, 1, 1, tzinfo=timezone.utc)

# Jendela paket baru yang sah: cukup lama sebelum tanggal pengambilan agar
# paket berbahaya sempat dilaporkan/dihapus (median masa hidup paket
# berbahaya di PyPI dalam hitungan hari).
BENIGN_FROM, BENIGN_UNTIL = "2023-01-01", "2026-07-01"
BENIGN_SEED = "pipguard-benign-v1"

TOP_URL = "https://hugovk.github.io/top-pypi-packages/top-pypi-packages.min.json"
SIMPLE_URL = "https://pypi.org/simple/"


def write_jsonl_gz(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"{len(rows)} baris -> {path}")


def read_jsonl_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_names(path):
    return [ph.normalize(l.strip()) for l in Path(path).read_text().splitlines()
            if l.strip() and not l.startswith("#")]


def stable_order(names, seed):
    """Urutan pseudo-acak yang deterministik (sampel dapat diulang persis)."""
    return sorted(names, key=lambda n: hashlib.sha256(f"{seed}:{n}".encode()).hexdigest())


def now_utc():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- jaringan

def cmd_malicious_fetch(a):
    names = [r["name"] for r in csv.DictReader(open(a.osv_csv))]
    print(f"mengambil metadata per-versi untuk {len(names)} nama berbahaya dari ClickHouse...")
    rows = ph.fetch_versions(names)
    write_jsonl_gz(RAW / "malicious_versions.jsonl.gz", rows)
    found = len({r["norm_name"] for r in rows})
    (RAW / "malicious_fetch.json").write_text(json.dumps({
        "fetched_at": ph.fmt_time(now_utc()), "source": ph.CLICKHOUSE_URL,
        "osv_names": len(names), "names_with_history": found}, indent=2) + "\n")
    print(f"{found}/{len(names)} nama punya riwayat")


def fetch_alive_index():
    req = urllib.request.Request(SIMPLE_URL, headers={"Accept": "application/vnd.pypi.simple.v1+json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    return {ph.normalize(p["name"]) for p in d["projects"]}, d["meta"].get("_last-serial")


def cmd_benign_sample(a):
    print("mengambil kandidat paket baru dari ClickHouse...")
    cand = ph.query(
        f"SELECT {ph.NORM_SQL} AS n, toString(min(upload_time)) AS first FROM pypi.projects "
        f"GROUP BY n HAVING first >= '{BENIGN_FROM}' AND first < '{BENIGN_UNTIL}' "
        f"ORDER BY cityHash64(n, '{BENIGN_SEED}'), n LIMIT {a.candidates} FORMAT JSONEachRow")
    print("mengambil indeks PyPI (daftar proyek yang masih ada)...")
    alive, serial = fetch_alive_index()
    checked_at = now_utc()
    malicious = {r["name"] for r in csv.DictReader(open(a.osv_csv))}

    kept, removed, in_osv = [], 0, 0
    for c in cand:
        if c["n"] in malicious:
            in_osv += 1
        elif c["n"] not in alive:
            removed += 1
        else:
            kept.append(c)
    kept = kept[:a.n]
    print(f"kandidat {len(cand)}: {in_osv} ada di OSV, {removed} sudah dihapus dari PyPI, "
          f"{len(kept)} diambil")

    with open(RAW / "benign_new_sample.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "first_upload"])
        for c in kept:
            w.writerow([c["n"], c["first"]])
    (RAW / "benign_new_sample.json").write_text(json.dumps({
        "window": [BENIGN_FROM, BENIGN_UNTIL], "seed": BENIGN_SEED,
        "candidates": len(cand), "in_osv": in_osv, "removed_from_pypi": removed,
        "kept": len(kept), "alive_checked_at": ph.fmt_time(checked_at),
        "pypi_last_serial": serial}, indent=2) + "\n")


def pypi_json(path, tries=5):
    url = f"https://pypi.org/pypi/{path}/json"
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pipguard-eval/1.0 (thesis research)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            err = e
        time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: {err}")


def pypi_history_rows(name):
    """Baris compact (format sama dengan pypi_history.fetch_versions) dari PyPI JSON API.

    Paket baru yang sah masih ada di PyPI, sehingga riwayatnya dapat dibaca
    langsung: waktu dan jenis setiap berkas dari `releases`, metadata versi
    dari /pypi/<nama>/<versi>/json. Hanya versi menit pertama dan versi
    terakhir yang diambil metadatanya (cukup untuk skenario first/last).
    """
    d = pypi_json(name)
    if d is None:
        return []
    versions = []
    for ver, files in d["releases"].items():
        if not files:
            continue
        times = [ph.parse_time(f["upload_time_iso_8601"]) for f in files]
        built = [ph.parse_time(f["upload_time_iso_8601"]) for f in files if f["packagetype"] != "sdist"]
        versions.append((min(times), ver, min(built) if built else None))
    if not versions:
        return []
    versions.sort()
    first, last = versions[0][0], versions[-1][0]
    rows = []
    for t, ver, built in versions:
        if not (t <= first + timedelta(minutes=1) or t == last):
            continue
        info = (pypi_json(f"{name}/{ver}") or {}).get("info") or {}
        rows.append({
            "norm_name": name, "version": ver, "upload_time": ph.fmt_time(t),
            "summary": info.get("summary") or "", "home_page": info.get("home_page") or "",
            "project_urls": [f"{k}, {v}" for k, v in (info.get("project_urls") or {}).items()],
            "description_len": len(info.get("description") or ""),
            "classifier_count": len(info.get("classifiers") or []),
            "requires_dist_count": len(info.get("requires_dist") or []),
            "first_built_upload": ph.fmt_time(built) if built else "1970-01-01 00:00:00.000",
            "built_files": 0, "n_versions": len(versions),
        })
    return rows


def cmd_benign_fetch(a):
    names = [r["name"] for r in csv.DictReader(open(RAW / "benign_new_sample.csv"))]
    rows, missing = [], 0
    if a.source == "clickhouse":
        print(f"mengambil riwayat {len(names)} paket baru yang sah dari ClickHouse...")
        # Versi menit pertama + versi terakhir saja: cukup untuk skenario first/last.
        rows = ph.fetch_versions(names, batch=500, compact=True)
    else:
        print(f"mengambil riwayat {len(names)} paket baru yang sah dari PyPI JSON API...")
        with ThreadPoolExecutor(max_workers=8) as ex:
            for i, rs in enumerate(ex.map(pypi_history_rows, names), 1):
                rows += rs
                missing += not rs
                if i % 500 == 0:
                    print(f"  ... {i}/{len(names)}", file=sys.stderr)
    write_jsonl_gz(Path(a.out), rows)
    (Path(a.out).parent / (Path(a.out).name.split(".")[0] + "_fetch.json")).write_text(json.dumps({
        "fetched_at": ph.fmt_time(now_utc()), "source": a.source,
        "packages": len(names), "without_history": missing}, indent=2) + "\n")
    print(f"{len(names) - missing}/{len(names)} paket punya riwayat")


def cmd_established(a):
    raw_path = RAW / "top_pypi_packages.json"
    if not a.offline:
        with urllib.request.urlopen(TOP_URL, timeout=120) as r:
            raw_path.write_bytes(r.read())
    d = json.loads(raw_path.read_text())
    top = [ph.normalize(r["project"]) for r in d["rows"]]
    print(f"daftar teratas: {len(top)} paket (last_update {d['last_update']})")

    if a.popular_n:
        # Daftar populer v2 (rujukan I-05 yang ditanam di shim): N teratas.
        header = (f"# {a.popular_n} paket PyPI teratas menurut unduhan 30 hari\n"
                  f"# Sumber: {TOP_URL} (last_update: {d['last_update']})\n"
                  f"# Dibangun oleh: scripts/eval/build_sets.py established --offline --popular-n {a.popular_n}\n")
        Path(a.popular_out).write_text(header + "\n".join(top[:a.popular_n]) + "\n")
        print(f"daftar populer v2 ({a.popular_n}) -> {a.popular_out}")
        return

    # Negatif mapan di luar top-1000 (yang dipakai saat mengembangkan v1):
    # sampel peringkat 1001-15000, dibagi dua secara deterministik menjadi
    # dev (penyetelan) dan test (pelaporan).
    dev_v1 = set(read_names("testdata/negative_top1000.txt"))
    pool = [n for n in top[1000:] if n not in dev_v1]
    sample = stable_order(pool, "pipguard-established-v1")[:2 * a.holdout_n]
    rank = {n: i + 1 for i, n in enumerate(top)}
    for split, part in (("dev", sample[:a.holdout_n]), ("test", sample[a.holdout_n:])):
        part = sorted(part, key=rank.get)
        out = FROZEN / f"negative_established_{split}.txt"
        out.write_text(f"# Sampel {len(part)} paket mapan peringkat 1001-{len(top)} (split {split}),\n"
                       f"# di luar testdata/negative_top1000.txt\n"
                       f"# Sumber: {TOP_URL} (last_update: {d['last_update']})\n"
                       + "\n".join(part) + "\n")
        print(f"{len(part)} -> {out}")


CONSISTENCY_FIELDS = {
    "release_count": lambda m: m["release_count"],
    "first_release_day": lambda m: m["first_release"][:10],
    "I-03 single release": lambda m: m["release_count"] == 1,
    "I-04 no homepage/repository": lambda m: not m["has_homepage"] and not m["has_repository"],
    "I-06 summary < 10": lambda m: len(m["summary"]) < 10,
    "I-07 sdist only": lambda m: m["sdist_only"],
    "I-08 description < 100": lambda m: m["description_len"] < 100,
    "I-09 no classifiers": lambda m: m["classifier_count"] == 0,
}


def agreement(pairs):
    out = {}
    for f, get in CONSISTENCY_FIELDS.items():
        out[f] = round(sum(get(x) == get(y) for x, y in pairs) / len(pairs), 4)
    return {"n": len(pairs), "agreement": out}


def consistency_names():
    return read_names(FROZEN / "consistency_sample.txt")


def cmd_consistency_fetch(a):
    """Riwayat ClickHouse untuk sampel konsistensi (±650 baris kuota)."""
    rows = ph.fetch_versions(consistency_names(), batch=250, compact=True)
    write_jsonl_gz(RAW / "consistency_clickhouse.jsonl.gz", rows)


def cmd_consistency(a):
    """Ukur kesesuaian sumber metadata yang dipakai evaluasi.

    (a) ClickHouse (sumber paket berbahaya) vs PyPI JSON API (sumber paket
        baru yang sah), keduanya direkonstruksi dengan snapshot() pada
        skenario first dan last, untuk 500 paket yang sama.
    (b) Rekonstruksi PyPI skenario last vs metadata yang dibaca langsung oleh
        internal/registry (Go) pada hari yang sama — menguji bahwa snapshot()
        meniru apa yang dilihat shim.
    """
    names = consistency_names()
    pypi = ph.group_versions(read_jsonl_gz(RAW / "benign_new_versions.jsonl.gz"))
    out = {}
    ch_path = RAW / "consistency_clickhouse.jsonl.gz"
    if ch_path.exists():
        ch = ph.group_versions(read_jsonl_gz(ch_path))
        for scen in ("first", "last"):
            pairs = []
            for n in names:
                if n in ch and n in pypi:
                    pairs.append((ph.snapshot(ch[n], ph.as_of_time(ch[n], scen)),
                                  ph.snapshot(pypi[n], ph.as_of_time(pypi[n], scen))))
            out[f"clickhouse_vs_pypi_{scen}"] = agreement(pairs)
        out["clickhouse_vs_pypi_coverage"] = {"sample": len(names), "in_clickhouse": sum(n in ch for n in names)}

    live = {}
    for line in Path(a.live_meta).read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            live[r["name"]] = r
    pairs = []
    for n in names:
        if n in pypi and live.get(n, {}).get("exists"):
            vs = pypi[n]
            as_of = ph.parse_time(live[n]["as_of"])
            if vs[-1]["upload_time"] <= as_of:
                pairs.append((ph.snapshot(vs, as_of), live[n]))
    out["reconstruction_vs_live_registry"] = agreement(pairs)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


def cmd_install_share(a):
    """Biaya masa tunggu 30 hari dalam praktik: porsi unduhan PyPI ke proyek < 30 hari.

    Satu kueri agregat ke cermin ClickHouse (tabel unduhan harian per proyek,
    digabung dengan tanggal unggahan pertama proyek). Unduhan didominasi CI dan
    cermin, jadi angka ini proksi frekuensi pemasangan, bukan jumlah pengguna.
    """
    # Total unduhan di cermin tidak stabil antarkueri (tabel SummingMergeTree
    # yang sedang dimuat/digabung; diamati 2026-10-19), jadi kueri diulang dan
    # yang dilaporkan median porsinya beserta rentangnya.
    runs = []
    for _ in range(a.repeats):
        rows = ph.query(f"""
SELECT sum(d.count) AS total, sumIf(d.count, d.date < f.first + 30) AS young,
       uniqExactIf(d.project, d.date < f.first + 30) AS young_projects, uniqExact(d.project) AS projects
FROM pypi.pypi_downloads_per_day AS d
INNER JOIN (SELECT {ph.NORM_SQL} AS project, toDate(min(upload_time)) AS first
            FROM pypi.projects GROUP BY project) AS f
ON lower(replaceRegexpAll(d.project, '[-_.]+', '-')) = f.project
WHERE d.date BETWEEN '{a.start}' AND '{a.end}' FORMAT JSONEachRow""")
        r = {k: int(v) for k, v in rows[0].items()}
        r["share"] = r["young"] / r["total"]
        runs.append(r)
    runs.sort(key=lambda r: r["share"])
    med = runs[len(runs) // 2]
    out = {"window": f"{a.start} – {a.end}", "downloads_total": med["total"], "downloads_young": med["young"],
           "share_young": med["share"], "share_min": runs[0]["share"], "share_max": runs[-1]["share"],
           "runs": runs, "projects_downloaded": med["projects"],
           "projects_young_downloaded": med["young_projects"], "fetched_at": ph.fmt_time(now_utc()),
           "source": ph.CLICKHOUSE_URL + " (pypi.pypi_downloads_per_day × pypi.projects)",
           "note": "Median of repeated queries (the mirror's download totals vary between queries; the share is "
                   "far more stable, see share_min/share_max). Downloads are dominated by CI systems and mirrors, "
                   "so this is a proxy for how often an install would hit the cooldown prompt, not a count of users."}
    (FROZEN / "install_share.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


# ---------------------------------------------------------------- luring

def split_of(t):
    return "dev" if t < VAL_START else ("val" if t < TEST_START else "test")


def load_legit_release_times():
    path = RAW / "legit_release_times.json.gz"
    if not path.exists():
        return {}
    with gzip.open(path, "rt") as f:
        return json.load(f)["releases"]


def override_release_times(rec, times, as_of):
    """Set latest/previous release from a full {version: time} map, as of as_of.

    Returns False (and leaves the record unchanged) when no map is available
    or no version precedes as_of, e.g. a project deleted since the snapshot.
    """
    if not times:
        return False
    ts = sorted(t for t in (ph.parse_time(v) for v in times.values()) if t <= as_of)
    if not ts:
        return False
    rec["latest_release"] = ph.fmt_time(ts[-1])
    rec["previous_release"] = ph.fmt_time(ts[-2]) if len(ts) > 1 else None
    return True


def cmd_meta(a):
    FROZEN.mkdir(parents=True, exist_ok=True)
    osv = {r["name"]: r for r in csv.DictReader(open(a.osv_csv))}
    mal = ph.group_versions(read_jsonl_gz(RAW / "malicious_versions.jsonl.gz"))
    ben = ph.group_versions(read_jsonl_gz(RAW / "benign_new_versions.jsonl.gz"))

    stats = {"malicious_with_history": len(mal), "malicious_versions_not_found": 0}
    for scenario in ("first", "last", "reported"):
        lines = []
        for n in sorted(mal):
            vs, o = mal[n], osv[n]
            # Waktu serangan = unggahan pertama versi yang dinyatakan berbahaya.
            listed = set(o["mal_versions"].split())
            hit = [v for v in vs if v["version"] in listed]
            if listed and not hit and scenario == "first":
                stats["malicious_versions_not_found"] += 1
            first_mal = hit[0]["upload_time"] if hit else vs[0]["upload_time"]
            as_of = ph.as_of_time(vs, scenario, first_mal, ph.parse_time(o["published"]))
            if as_of < first_mal:  # "last" tidak boleh mendahului serangan
                as_of = ph.as_of_time(vs, "first", first_mal)
            group = "malicious-typosquat" if o["typosquat"] == "true" else "malicious-other"
            rec = {"name": n, "group": group, "split": split_of(first_mal),
                   "as_of": ph.fmt_time(as_of), **ph.snapshot(vs, as_of)}
            lines.append(json.dumps(rec, ensure_ascii=False))
        out = FROZEN / f"meta_malicious_{scenario}.jsonl"
        out.write_text("\n".join(lines) + "\n")
        print(f"{len(lines)} -> {out}")

    legit_times = load_legit_release_times()
    for scenario in ("first", "last"):
        lines = []
        for n in sorted(ben):
            vs = ben[n]
            as_of = ph.as_of_time(vs, scenario)
            rec = {"name": n, "group": "benign-new", "split": split_of(vs[0]["upload_time"]),
                   "as_of": ph.fmt_time(as_of), **ph.snapshot(vs, as_of)}
            override_release_times(rec, legit_times.get(n), as_of)
            lines.append(json.dumps(rec, ensure_ascii=False))
        out = FROZEN / f"meta_benign_new_{scenario}.jsonl"
        out.write_text("\n".join(lines) + "\n")
        print(f"{len(lines)} -> {out}")

    # Prospective hold-out: OSV reports published after the design freeze
    # (fetch_v3.py prospective), scored at their first malicious upload.
    pros_csv, pros_raw = FROZEN / "prospective_osv.csv", RAW / "prospective_versions.jsonl.gz"
    if pros_csv.exists() and pros_raw.exists():
        posv = {r["name"]: r for r in csv.DictReader(open(pros_csv))}
        pv = ph.group_versions(read_jsonl_gz(pros_raw))
        lines = []
        for n in sorted(pv):
            vs, o = pv[n], posv[n]
            listed = set(o["mal_versions"].split())
            hit = [v for v in vs if v["version"] in listed]
            first_mal = hit[0]["upload_time"] if hit else vs[0]["upload_time"]
            as_of = ph.as_of_time(vs, "first", first_mal)
            group = "malicious-typosquat" if o["typosquat"] == "true" else "malicious-other"
            lines.append(json.dumps({"name": n, "group": group, "split": "prospective",
                                     "as_of": ph.fmt_time(as_of), **ph.snapshot(vs, as_of)}, ensure_ascii=False))
        (FROZEN / "meta_prospective_first.jsonl").write_text("\n".join(lines) + "\n")
        print(f"{len(lines)} -> {FROZEN / 'meta_prospective_first.jsonl'}")

    # Established packages: the live snapshot (Go registry client, 2026-10-19)
    # plus release times as of the same instant.
    lines, missing = [], 0
    for line in (FROZEN / "meta_established_live.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("exists"):
            if not override_release_times(rec, legit_times.get(rec["name"]), ph.parse_time(rec["as_of"])):
                missing += 1
        lines.append(json.dumps(rec, ensure_ascii=False))
    (FROZEN / "meta_established.jsonl").write_text("\n".join(lines) + "\n")
    stats["established_without_release_times"] = missing
    print(f"{len(lines)} -> {FROZEN / 'meta_established.jsonl'} ({missing} without release times)")

    (FROZEN / "meta_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(stats)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    osv = {"default": "testdata/malicious_osv.csv"}

    p = sub.add_parser("malicious-fetch")
    p.add_argument("--osv-csv", **osv)
    p.set_defaults(func=cmd_malicious_fetch)

    p = sub.add_parser("benign-sample")
    p.add_argument("--osv-csv", **osv)
    p.add_argument("--candidates", type=int, default=7000)
    p.add_argument("--n", type=int, default=5000)
    p.set_defaults(func=cmd_benign_sample)

    p = sub.add_parser("benign-fetch")
    p.add_argument("--source", choices=["pypi", "clickhouse"], default="pypi",
                   help="paket ini masih ada di PyPI, sehingga JSON API-nya dapat dipakai (tanpa kuota)")
    p.add_argument("--out", default=str(RAW / "benign_new_versions.jsonl.gz"))
    p.set_defaults(func=cmd_benign_fetch)

    p = sub.add_parser("established")
    p.add_argument("--offline", action="store_true", help="pakai raw/top_pypi_packages.json yang sudah ada")
    p.add_argument("--popular-n", type=int, default=0, help="tulis daftar populer v2 (N teratas) saja")
    p.add_argument("--popular-out", default="assets/popular_v2.txt")
    p.add_argument("--holdout-n", type=int, default=2000)
    p.set_defaults(func=cmd_established)

    p = sub.add_parser("consistency-fetch")
    p.set_defaults(func=cmd_consistency_fetch)

    p = sub.add_parser("consistency")
    p.add_argument("--live-meta", default=str(FROZEN / "live_benign_new_check.jsonl"))
    p.add_argument("--out", default=str(FROZEN / "consistency.json"))
    p.set_defaults(func=cmd_consistency)

    p = sub.add_parser("install-share")
    p.add_argument("--start", default="2026-09-01")
    p.add_argument("--end", default="2026-09-30")
    p.add_argument("--repeats", type=int, default=5)
    p.set_defaults(func=cmd_install_share)

    p = sub.add_parser("meta")
    p.add_argument("--osv-csv", **osv)
    p.set_defaults(func=cmd_meta)

    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    a.func(a)


if __name__ == "__main__":
    main()
