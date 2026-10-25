"""Metadata historis PyPI dari cermin publik ClickHouse (ClickPy).

Tabel `pypi.projects` di https://sql-clickhouse.clickhouse.com berisi satu
baris per berkas distribusi yang pernah diunggah ke PyPI, dibangun dari
tabel BigQuery `bigquery-public-data.pypi.distribution_metadata`. Seperti
tabel BigQuery-nya, baris tidak dihapus ketika PyPI menghapus proyek —
sehingga metadata paket berbahaya yang sudah dihapus tetap tersedia.
Berbeda dengan BigQuery, aksesnya tidak memerlukan akun (pengguna `demo`).

Batas pengguna `demo` (diamati 2026-10-19): 10.000 baris per kueri dan
60.000 baris hasil per jam. Klien di bawah memecah kueri dan menunggu
otomatis bila kuota jam berjalan habis.

Hanya pustaka standar. Tidak pernah mengunduh berkas paket.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

CLICKHOUSE_URL = "https://sql-clickhouse.clickhouse.com/?user=demo"

# Harus sama dengan internal/registry/pypi.go (repoURLKeys).
REPO_URL_KEYS = {"Source", "Repository", "Source Code", "Homepage", "Code", "GitHub"}

NORM_SQL = "lower(replaceRegexpAll(name, '[-_.]+', '-'))"

# Satu baris per (proyek, versi). Metadata diambil dari berkas pertama versi
# itu — yang dilihat PyPI JSON API — dan waktu berkas terbangun (wheel/egg)
# pertama dicatat terpisah agar "hanya sdist" dapat dinilai pada waktu as_of.
VERSION_COLUMNS = f"""
  {NORM_SQL} AS norm_name,
  version,
  toString(min(upload_time)) AS version_upload_time,
  argMin(summary, upload_time) AS summary,
  argMin(home_page, upload_time) AS home_page,
  argMin(project_urls, upload_time) AS project_urls,
  argMin(length(description), upload_time) AS description_len,
  argMin(length(classifiers), upload_time) AS classifier_count,
  argMin(length(requires_dist), upload_time) AS requires_dist_count,
  toString(minIf(upload_time, packagetype != 'sdist')) AS first_built_upload,
  countIf(packagetype != 'sdist') AS built_files
"""


def normalize(name):
    """PEP 503, sama dengan internal/parser.Normalize."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_time(s):
    s = s.replace(" UTC", "+00:00").replace("Z", "+00:00")
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    t = datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def fmt_time(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class QuotaExceeded(Exception):
    def __init__(self, until):
        self.until = until


def _post(sql):
    req = urllib.request.Request(CLICKHOUSE_URL, data=sql.encode())
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            body = r.read().decode()
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")
        m = re.search(r"Interval will end at (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", msg)
        if "QUOTA_EXCEEDED" in msg and m:
            raise QuotaExceeded(parse_time(m.group(1)))
        raise RuntimeError(f"ClickHouse HTTP {e.code}: {msg[:300]}") from None
    rows = [json.loads(line) for line in body.splitlines() if line.strip()]
    if rows and "exception" in rows[-1]:
        raise RuntimeError(f"ClickHouse: {rows[-1]['exception'][:300]}")
    return rows


# The demo user has max_rows_to_read = 1e9 with read_overflow_mode = 'break':
# a query that would read more rows silently returns PARTIAL results. The
# download tables are ordered by project, so only project-filtered queries are
# safe; query_complete() verifies completeness from the response summary.
MAX_ROWS_TO_READ = 1_000_000_000


def query_complete(sql):
    """Like query(), but raise unless the server read every row it had to read."""
    for attempt in range(8):
        req = urllib.request.Request(CLICKHOUSE_URL, data=sql.encode())
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                body = r.read().decode()
                summary = json.loads(r.headers.get("X-ClickHouse-Summary") or "{}")
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")
            m = re.search(r"Interval will end at (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", msg)
            if "QUOTA_EXCEEDED" in msg and m:
                wait = (parse_time(m.group(1)) - datetime.now(timezone.utc)).total_seconds() + 30
                print(f"  ClickHouse quota exhausted; waiting {wait / 60:.0f} min", file=sys.stderr)
                time.sleep(max(wait, 30))
                continue
            raise RuntimeError(f"ClickHouse HTTP {e.code}: {msg[:300]}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"  network: {e}; retrying", file=sys.stderr)
            time.sleep(2 ** attempt)
            continue
        rows = [json.loads(line) for line in body.splitlines() if line.strip()]
        if rows and "exception" in rows[-1]:
            raise RuntimeError(f"ClickHouse: {rows[-1]['exception'][:300]}")
        read, total = int(summary.get("read_rows", 0)), int(summary.get("total_rows_to_read", 0))
        if read >= MAX_ROWS_TO_READ or read < total:
            raise RuntimeError(f"ClickHouse returned a truncated result (read {read:,} of {total:,} rows)")
        return rows, summary
    raise RuntimeError("ClickHouse: failed after several attempts")


def estimate_rows(table, where):
    """Rows the server would read for `SELECT ... FROM table WHERE where` (EXPLAIN ESTIMATE)."""
    sql = f"EXPLAIN ESTIMATE SELECT sum(count) FROM {table} WHERE {where} FORMAT JSONEachRow"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(CLICKHOUSE_URL, data=sql.encode()), timeout=120) as r:
                return sum(int(json.loads(l)["rows"]) for l in r.read().decode().splitlines() if l.strip())
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            detail = e.read().decode(errors="replace")[:200] if isinstance(e, urllib.error.HTTPError) else e
            print(f"  estimate failed ({detail}); retrying", file=sys.stderr)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"EXPLAIN ESTIMATE failed for {where}")


def query(sql):
    """Jalankan kueri (harus diakhiri FORMAT JSONEachRow); tunggu bila kuota habis."""
    for attempt in range(8):
        try:
            return _post(sql)
        except QuotaExceeded as q:
            wait = (q.until - datetime.now(timezone.utc)).total_seconds() + 30
            print(f"  kuota ClickHouse habis; menunggu {wait/60:.0f} menit (sampai {fmt_time(q.until)})",
                  file=sys.stderr)
            time.sleep(max(wait, 30))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"  jaringan: {e}; mencoba lagi", file=sys.stderr)
            time.sleep(2 ** attempt)
    raise RuntimeError("ClickHouse: gagal setelah beberapa percobaan")


def _sql_list(names):
    for n in names:
        if not re.fullmatch(r"[a-z0-9-]+", n):
            raise ValueError(f"nama tidak dinormalkan: {n!r}")
    return ",".join(f"'{n}'" for n in names)


def fetch_versions(names, batch=200, progress=True, compact=False):
    """Baris per-versi untuk nama-nama (dinormalkan) yang diberikan.

    Batch yang melebihi batas 10.000 baris per kueri dibelah dua.

    compact=True hanya mengembalikan versi yang diunggah dalam menit pertama
    proyek ditambah versi terakhir, masing-masing dengan `n_versions`
    (jumlah seluruh versi). Itu cukup untuk skenario "first" dan "last"
    (lihat snapshot) dan menghemat kuota bersama pengguna `demo`.
    """
    names = sorted(set(names))
    out = []

    def run(chunk):
        sql = (f"SELECT {VERSION_COLUMNS} FROM pypi.projects "
               f"WHERE norm_name IN ({_sql_list(chunk)}) "
               f"GROUP BY norm_name, version")
        if compact:
            sql = (f"SELECT * EXCEPT (t, pkg_first, pkg_last) FROM ("
                   f"SELECT *, parseDateTime64BestEffort(version_upload_time, 3) AS t, "
                   f"min(t) OVER (PARTITION BY norm_name) AS pkg_first, "
                   f"max(t) OVER (PARTITION BY norm_name) AS pkg_last, "
                   f"count() OVER (PARTITION BY norm_name) AS n_versions FROM ({sql})) "
                   f"WHERE t <= pkg_first + INTERVAL 1 MINUTE OR t = pkg_last")
        sql += " FORMAT JSONEachRow"
        try:
            return query(sql)
        except RuntimeError as e:
            if len(chunk) > 1 and ("TOO_MANY_ROWS" in str(e) or "Limit for result" in str(e)):
                h = len(chunk) // 2
                return run(chunk[:h]) + run(chunk[h:])
            raise

    for i in range(0, len(names), batch):
        out += run(names[i:i + batch])
        if progress:
            print(f"  ... {min(i + batch, len(names))}/{len(names)} nama, {len(out)} versi", file=sys.stderr)
    for r in out:
        r["upload_time"] = r.pop("version_upload_time")
        for k in ("description_len", "classifier_count", "requires_dist_count", "built_files", "n_versions"):
            if k not in r:
                continue
            r[k] = int(r[k])
    return out


def has_repository(project_urls):
    # Elemen project_urls berbentuk "Label, https://...".
    for item in project_urls or []:
        label, _, url = item.partition(",")
        if label.strip() in REPO_URL_KEYS and url.strip():
            return True
    return False


def group_versions(rows):
    """{nama: [versi terurut menurut waktu unggah]} dengan upload_time ter-parse."""
    by = {}
    for r in rows:
        r = dict(r)
        r["upload_time"] = parse_time(r["upload_time"]) if isinstance(r["upload_time"], str) else r["upload_time"]
        fb = r.get("first_built_upload")
        r["first_built_upload"] = parse_time(fb) if fb and not fb.startswith("1970-01-01") else None
        by.setdefault(r["norm_name"], []).append(r)
    for vs in by.values():
        vs.sort(key=lambda v: (v["upload_time"], v["version"]))
    return by


def snapshot(versions, as_of):
    """Metadata yang akan dilihat PyPI JSON API (internal/registry) pada waktu as_of.

    "Versi terbaru" diambil sebagai versi yang terakhir diunggah sebelum
    as_of. PyPI sendiri memakai urutan versi (PEP 440), yang hampir selalu
    sama; kesesuaian keduanya diukur oleh build_sets.py `consistency`.
    """
    live = [v for v in versions if v["upload_time"] <= as_of]
    latest = live[-1]
    built = latest.get("first_built_upload")
    count = len(live)
    if "n_versions" in latest and latest["upload_time"] == versions[-1]["upload_time"]:
        # Hasil fetch compact: versi tengah tidak diambil, jumlahnya dari kueri.
        count = latest["n_versions"]
    rec = {
        "exists": True,
        "first_release": fmt_time(live[0]["upload_time"]),
        "release_count": count,
        "has_homepage": bool(latest.get("home_page")),
        # PyPI JSON API menyalin home_page ke project_urls["Homepage"], dan
        # internal/registry menganggap "Homepage" sebagai tautan repositori.
        "has_repository": has_repository(latest.get("project_urls")) or bool(latest.get("home_page")),
        "summary": latest.get("summary") or "",
        "description_len": latest.get("description_len", 0),
        "classifier_count": latest.get("classifier_count", 0),
        "requires_dist_count": latest.get("requires_dist_count", 0),
        "sdist_only": not (built is not None and built <= as_of),
    }
    # Release-level fields for I-10. Compact fetches lack the versions in the
    # middle, so callers with a full release timeline override these
    # (build_sets.py meta, legit_release_times).
    rec["latest_release"] = fmt_time(latest["upload_time"])
    rec["previous_release"] = fmt_time(live[-2]["upload_time"]) if len(live) > 1 else None
    return rec


def as_of_time(versions, scenario, first_malicious=None, reported=None):
    """Waktu penilaian untuk satu skenario (lihat scripts/malicious/README.md)."""
    start = first_malicious or versions[0]["upload_time"]
    if scenario == "first":
        return start + timedelta(minutes=1)
    if scenario == "last":
        return versions[-1]["upload_time"] + timedelta(minutes=1)
    if scenario == "reported":
        return max(reported, start + timedelta(minutes=1))
    raise ValueError(scenario)
