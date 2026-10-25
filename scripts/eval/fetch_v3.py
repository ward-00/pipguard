#!/usr/bin/env python3
"""Online data pulls added in the third evaluation round (journal revision).

Every step writes its raw result to testdata/frozen/ so that the analysis
(scripts/eval/analyze_v3.py) runs offline and reproduces identical numbers.

Steps (network):
  exposure      daily downloads of every malicious release, split into install
                clients (pip, uv, poetry, pdm, pipenv) and everything else
                (mirrors, browsers, scripts), from the public ClickPy mirror
  campaign      uploader fields of the first malicious release of each package
                (author, e-mail, upload tool, description hash) for campaign
                clustering
  cost          share of PyPI downloads that a project-level or a release-level
                cooldown of T days would affect (one aggregate query per window)
  prospective   OSV reports published after the evaluation freeze (2026-10-19):
                names, versions and per-version history for a prospective hold-out
  firstseen     first upload time on PyPI of arbitrary names (hallucination study)

Standard library only. No package file is ever downloaded.
"""
import argparse
import csv
import gzip
import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pypi_history as ph  # noqa: E402

FROZEN = Path("testdata/frozen")
RAW = FROZEN / "raw"
CLIENTS = "('pip','uv','poetry','pdm','pipenv')"
FREEZE = datetime(2026, 10, 19, 13, 0, tzinfo=timezone.utc)


def write_jsonl_gz(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"{len(rows)} rows -> {path}")


def malicious_targets():
    """(name, listed malicious versions or [] for 'all versions') for every reconstructed package."""
    osv = {r["name"]: r for r in csv.DictReader(open("testdata/malicious_osv.csv"))}
    names = [json.loads(l)["name"] for l in open(FROZEN / "meta_malicious_first.jsonl")]
    return [(n, osv[n]["mal_versions"].split()) for n in names]


def sql_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


AGE_BUCKET = ("multiIf(age < 0, -1, age <= 14, age, age < 21, 15, age < 30, 21, age < 60, 30, "
              "age < 90, 60, age < 180, 90, age < 365, 180, 365)")


def first_malicious_dates():
    """Date of the first malicious upload of each package (scenario 'first' as_of minus 1 minute)."""
    out = {}
    for l in open(FROZEN / "meta_malicious_first.jsonl"):
        r = json.loads(l)
        out[r["name"]] = ph.parse_time(r["as_of"]).date().isoformat()
    return out


def cmd_exposure(a):
    """Downloads of the malicious releases by age bucket (days since the first malicious upload).

    Buckets: single days 0..14, then 15-20, 21-29, 30-59, 60-89, 90-179, 180-364, 365+
    (labelled by their lower bound; -1 = before the first malicious upload, which
    happens only for releases re-listed by later reports). One extra row per
    package (bucket = -2) carries the last date with any download, a proxy for
    the removal date.
    """
    targets = malicious_targets()
    fm = first_malicious_dates()
    rows = []
    for i in range(0, len(targets), a.batch):
        chunk = targets[i:i + a.batch]
        allv = [n for n, vs in chunk if not vs]
        keys = [f"{n}@{v}" for n, vs in chunk for v in vs]
        cond = []
        if allv:
            cond.append(f"project IN ({','.join(map(sql_str, allv))})")
        if keys:
            cond.append(f"concat(project,'@',version) IN ({','.join(map(sql_str, keys))})")
        names = ",".join(sql_str(n) for n, _ in chunk)
        dates = ",".join(f"toDate('{fm[n]}')" for n, _ in chunk)
        base = f"""
FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
WHERE project IN ({names}) AND ({' OR '.join(cond)})"""
        rows += ph.query(f"""
SELECT project, bucket, sum(client) AS client, sum(total) AS total FROM (
  SELECT project, dateDiff('day', transform(project, [{names}], [{dates}], toDate('1970-01-01')), date) AS age,
         {AGE_BUCKET} AS bucket, sumIf(count, installer IN {CLIENTS}) AS client, sum(count) AS total
  {base} GROUP BY project, date)
GROUP BY project, bucket FORMAT JSONEachRow""")
        rows += [dict(r, bucket=-2) for r in ph.query(f"""
SELECT project, toString(max(date)) AS last_date, toString(min(date)) AS first_date,
       sum(count) AS total {base} AND count > 0 GROUP BY project FORMAT JSONEachRow""")]
        print(f"  ... {min(i + a.batch, len(targets))}/{len(targets)} packages, {len(rows)} rows", file=sys.stderr)
    for r in rows:
        for k in ("client", "total", "bucket"):
            if k in r:
                r[k] = int(r[k])
    write_jsonl_gz(RAW / "malicious_downloads.jsonl.gz", rows)
    (RAW / "malicious_downloads_fetch.json").write_text(json.dumps({
        "fetched_at": ph.fmt_time(datetime.now(timezone.utc)), "source": ph.CLICKHOUSE_URL,
        "table": "pypi.pypi_downloads_per_day_by_version_by_installer_by_type",
        "client_installers": CLIENTS, "age_bucket": AGE_BUCKET}, indent=2) + "\n")


def cmd_campaign(a):
    targets = malicious_targets()
    rows = []
    for i in range(0, len(targets), a.batch):
        chunk = targets[i:i + a.batch]
        names = ",".join(sql_str(n) for n, _ in chunk)
        rows += ph.query(f"""
SELECT {ph.NORM_SQL} AS norm_name, version,
       toString(min(upload_time)) AS first_upload,
       argMin(author, upload_time) AS author, argMin(author_email, upload_time) AS author_email,
       argMin(maintainer_email, upload_time) AS maintainer_email,
       argMin(uploaded_via, upload_time) AS uploaded_via,
       toString(argMin(cityHash64(description), upload_time)) AS description_hash,
       toString(argMin(cityHash64(summary), upload_time)) AS summary_hash,
       argMin(sha256_digest, upload_time) AS first_file_sha256
FROM pypi.projects WHERE norm_name IN ({names})
GROUP BY norm_name, version FORMAT JSONEachRow""")
        print(f"  ... {min(i + a.batch, len(targets))}/{len(targets)}", file=sys.stderr)
    write_jsonl_gz(RAW / "malicious_uploaders.jsonl.gz", rows)


def cmd_cost(a):
    """Share of downloads affected by project-level and release-level cooldowns.

    Project level (pipguard): the downloaded project was first uploaded less than
    T days before the download date. Release level (pip --uploaded-prior-to,
    uv --exclude-newer, pnpm minimumReleaseAge): the downloaded *version* was
    uploaded less than T days before the download date, i.e. the installer
    would have had to pick an older version. Both are computed over all
    downloads and over install clients only (pip, uv, poetry, pdm, pipenv).
    The mirror's totals vary slightly between identical queries, so each
    query is repeated and the median share is kept.
    """
    ts = [1, 2, 3, 7, 14, 21, 30, 60, 90]
    proj = ", ".join(f"sumIf(c, d.date < f.first + {t}) AS p{t}, sumIf(cc, d.date < f.first + {t}) AS pc{t}" for t in ts)
    rel = ", ".join(f"sumIf(c, d.date < v.vt + {t}) AS r{t}, sumIf(cc, d.date < v.vt + {t}) AS rc{t}" for t in ts)
    out = {"window": [a.start, a.end], "thresholds_days": ts, "runs": []}
    for _ in range(a.repeats):
        q = f"""
WITH d AS (SELECT project, version, date, sum(count) AS c, sumIf(count, installer IN {CLIENTS}) AS cc
           FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
           WHERE date BETWEEN '{a.start}' AND '{a.end}' GROUP BY project, version, date)
SELECT sum(c) AS total, sum(cc) AS total_client, {proj}, {rel}
FROM d
LEFT JOIN (SELECT {ph.NORM_SQL} AS project, toDate(min(upload_time)) AS first
           FROM pypi.projects GROUP BY project) AS f ON d.project = f.project
LEFT JOIN (SELECT {ph.NORM_SQL} AS project, version, toDate(min(upload_time)) AS vt
           FROM pypi.projects GROUP BY project, version) AS v ON d.project = v.project AND d.version = v.version
FORMAT JSONEachRow"""
        r = {k: int(v) for k, v in ph.query(q)[0].items()}
        out["runs"].append(r)
        print(json.dumps(r)[:300], file=sys.stderr)
    out["fetched_at"] = ph.fmt_time(datetime.now(timezone.utc))
    out["source"] = ph.CLICKHOUSE_URL
    path = Path(a.out) if a.out else FROZEN / "cooldown_cost.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")


DL_TABLE = "pypi.pypi_downloads_per_day_by_version_by_installer_by_type"
ALPHABET = "-0123456789abcdefghijklmnopqrstuvwxyz"


def project_chunks(limit):
    """Contiguous project-name ranges [lo, hi) whose download rows stay below `limit`.

    The `cost` and `dormancy-cost` steps filter only by date, which the table's
    project-first ordering cannot prune, so the server read capped at 1e9
    rows and returned partial sums. Splitting by project name keeps every
    query complete. Row counts per name prefix come from the table's primary
    index (mergeTreeIndex), which reads no data.
    """
    def where(lo, hi):
        c = [f"project >= {sql_str(lo)}"] if lo else []
        if hi is not None:
            c.append(f"project < {sql_str(hi)}")
        return " AND ".join(c) or "1 = 1"

    def counts(prefix):
        rows = ph.query_complete(f"""
SELECT substring(project, 1, {len(prefix) + 1}) AS p, sum(rows_in_granule) AS r
FROM mergeTreeIndex('pypi', '{DL_TABLE.split('.')[1]}')
WHERE startsWith(project, {sql_str(prefix)}) GROUP BY p ORDER BY p FORMAT JSONEachRow""")[0]
        out = []
        for r in rows:
            n = int(r["r"])
            if n > limit and len(r["p"]) > len(prefix) and len(r["p"]) < 6:
                out += counts(r["p"])
            else:
                out.append((r["p"], n))
        return out

    prefixes = sorted(counts(""))
    merged = []                       # [lo, n]; hi = next lo
    for p, n in prefixes:
        if merged and merged[-1][1] + n <= limit:
            merged[-1][1] += n
        else:
            merged.append([p, n])
    chunks = [("" if i == 0 else lo, merged[i + 1][0] if i + 1 < len(merged) else None, n)
              for i, (lo, n) in enumerate(merged)]
    return chunks, where


def cmd_cost_complete(a):
    """Round 2: complete monthly cooldown and I-10 costs, [--first, --last], one pass per name range.

    Same definitions as `cost` and `dormancy-cost` (calendar-day ages), but
    every query is checked for completeness (pypi_history.query_complete), and
    a download counts as young only from the first known upload on (downloads
    dated before it, or of projects without metadata, are counted separately).
    Results per month and per chunk go to testdata/frozen/cost_complete.json;
    already finished chunks are kept when the step is re-run.
    """
    import calendar
    out_path = FROZEN / "cost_complete.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else {}
    if done.get("window") != [a.first, a.last]:
        done = {}
    start = f"{a.first}-01"
    ly, lm = map(int, a.last.split("-"))
    end = f"{a.last}-{calendar.monthrange(ly, lm)[1]}"
    ts, gs = [1, 2, 3, 7, 14, 21, 30, 60, 90], [30, 60, 90, 180, 365]
    chunks, where = project_chunks(a.limit)
    print(f"{len(chunks)} name ranges, at most {max(c[2] for c in chunks):,} rows each", file=sys.stderr)
    cols = ", ".join(
        [f"sumIf(c, d.date >= f.first AND d.date < f.first + {t}) AS p{t}, "
         f"sumIf(cc, d.date >= f.first AND d.date < f.first + {t}) AS pc{t}" for t in ts] +
        [f"sumIf(c, d.date >= v.vt AND d.date < v.vt + {t}) AS r{t}, "
         f"sumIf(cc, d.date >= v.vt AND d.date < v.vt + {t}) AS rc{t}" for t in ts] +
        ["sumIf(cc, d.date < f.first) AS pc_before_first, sumIf(cc, d.date < v.vt) AS rc_before_upload, "
         "sumIf(cc, f.first = toDate('1970-01-01')) AS cc_no_project_metadata, "
         "sumIf(cc, v.vt = toDate('1970-01-01')) AS cc_no_version_metadata"] +
        [f"sumIf(cc, d.date < v.vt + 30 AND d.date >= f.first + 30 AND v.pv > toDate('1971-01-01') "
         f"AND dateDiff('day', v.pv, v.vt) >= {g}) AS dc{g}" for g in gs])
    done.setdefault("chunks", {})
    for lo, hi, n in chunks:
        key = f"{lo}|{'' if hi is None else hi}"
        if key in done["chunks"]:
            continue
        w = where(lo, hi)
        wn = where(lo, hi).replace("project", ph.NORM_SQL)
        q = f"""
WITH d AS (SELECT project, version, date, sum(count) AS c, sumIf(count, installer IN {CLIENTS}) AS cc
           FROM {DL_TABLE} WHERE {w} AND date BETWEEN '{start}' AND '{end}' GROUP BY project, version, date),
     f AS (SELECT {ph.NORM_SQL} AS project, toDate(min(upload_time)) AS first FROM pypi.projects
           WHERE {wn} GROUP BY project),
     v AS (SELECT project, version, vt,
                  lagInFrame(vt, 1, toDate('1970-01-01')) OVER (PARTITION BY project ORDER BY vt
                      ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS pv
           FROM (SELECT {ph.NORM_SQL} AS project, version, toDate(min(upload_time)) AS vt
                 FROM pypi.projects WHERE {wn} GROUP BY project, version))
SELECT toString(toStartOfMonth(d.date)) AS month, sum(c) AS total, sum(cc) AS total_client, {cols}
FROM d LEFT JOIN f ON d.project = f.project
       LEFT JOIN v ON d.project = v.project AND d.version = v.version
GROUP BY month ORDER BY month FORMAT JSONEachRow"""
        t0 = time.time()
        rows, summ = ph.query_complete(q)
        done["chunks"][key] = {"rows_read": int(summ["read_rows"]), "months": {
            r.pop("month")[:7]: {k: int(v) for k, v in r.items()} for r in rows}}
        done.update({"window": [a.first, a.last], "thresholds_days": ts, "dormancy_days": gs,
                     "source": ph.CLICKHOUSE_URL, "table": DL_TABLE, "client_installers": CLIENTS,
                     "fetched_at": ph.fmt_time(datetime.now(timezone.utc))})
        out_path.write_text(json.dumps(done, indent=1) + "\n")
        print(f"  [{lo!r}, {hi!r}) {int(summ['read_rows']):,} rows in {time.time() - t0:.0f} s", file=sys.stderr)
    print(f"done: {len(done['chunks'])} chunks -> {out_path}", file=sys.stderr)


def cmd_background(a):
    """Round 2: downloads of new legitimate projects by age (days since the first upload).

    The control for automated traffic that every new upload receives (mirrors,
    scanners, sandboxes): same table, same installer split and same age
    buckets as `exposure`, but anchored at the project's first upload and over
    all versions. One row per project with the buckets as arrays.
    """
    firsts = {}
    for l in open(FROZEN / "meta_benign_new_first.jsonl"):
        r = json.loads(l)
        firsts[r["name"]] = ph.parse_time(r["as_of"]).date().isoformat()
    names = sorted(firsts)
    rows = []
    for i in range(0, len(names), a.batch):
        chunk = names[i:i + a.batch]
        ns = ",".join(sql_str(n) for n in chunk)
        ds = ",".join(f"toDate('{firsts[n]}')" for n in chunk)
        rows += ph.query_complete(f"""
SELECT project, groupArray(bucket) AS buckets, groupArray(client) AS client, groupArray(total) AS total FROM (
  SELECT project, bucket, sum(client) AS client, sum(total) AS total FROM (
    SELECT project, dateDiff('day', transform(project, [{ns}], [{ds}], toDate('1970-01-01')), date) AS age,
           {AGE_BUCKET} AS bucket, sumIf(count, installer IN {CLIENTS}) AS client, sum(count) AS total
    FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
    WHERE project IN ({ns}) GROUP BY project, date)
  GROUP BY project, bucket ORDER BY bucket)
GROUP BY project FORMAT JSONEachRow""")[0]
        print(f"  ... {min(i + a.batch, len(names))}/{len(names)}", file=sys.stderr)
    write_jsonl_gz(RAW / "benign_new_downloads.jsonl.gz", rows)


def cmd_filetype(a):
    """Round 2: downloaded file types of every OSV name (sdist vs built distributions).

    Independent of the metadata mirror, so it estimates source-only
    distribution (I-07) also for the names that could not be reconstructed.
    """
    names = sorted({r["name"] for r in csv.DictReader(open("testdata/malicious_osv.csv"))})
    rows = []
    for i in range(0, len(names), 1500):
        chunk = ",".join(sql_str(n) for n in names[i:i + 1500])
        rows += ph.query_complete(f"""
SELECT project, sumIf(count, type = 'sdist') AS sdist, sumIf(count, type != 'sdist') AS built,
       uniqExactIf(version, type != 'sdist') AS built_versions, uniqExact(version) AS versions
FROM pypi.pypi_downloads_per_day_by_version_by_file_type
WHERE project IN ({chunk}) AND count > 0 GROUP BY project FORMAT JSONEachRow""")[0]
        print(f"  ... {min(i + 1500, len(names))}/{len(names)}", file=sys.stderr)
    write_jsonl_gz(RAW / "osv_filetype.jsonl.gz", rows)


def cmd_dependents(a):
    """Round 2: releases of other projects whose requires_dist names a reconstructed malicious package."""
    mal = sorted(json.loads(l)["name"] for l in open(FROZEN / "meta_malicious_first.jsonl"))
    rows = []
    for i in range(0, len(mal), 3000):
        chunk = ",".join(sql_str(n) for n in mal[i:i + 3000])
        rows += ph.query_complete(f"""
SELECT dep, {ph.NORM_SQL} AS dependent, uniqExact(version) AS versions,
       toString(min(upload_time)) AS first_uploaded, toString(max(upload_time)) AS last_uploaded
FROM pypi.projects
ARRAY JOIN arrayMap(x -> lower(replaceRegexpAll(extract(x, '^\\\\s*([A-Za-z0-9][A-Za-z0-9._-]*)'), '[-_.]+', '-')),
                    requires_dist) AS dep
WHERE dep IN ({chunk}) AND dependent != dep
GROUP BY dep, dependent FORMAT JSONEachRow""")[0]
        print(f"  ... {min(i + 3000, len(mal))}/{len(mal)}, {len(rows)} rows", file=sys.stderr)
    write_jsonl_gz(RAW / "malicious_dependents.jsonl.gz", rows)


def cmd_dep_additions(a):
    """Round 2: dependency additions in PyPI releases and the age of the added project.

    For every release first uploaded in [--first, --last], the dependencies in
    its requires_dist that the project's previous release did not have (all of
    them for a first release), with the age of the dependency's project on the
    release day. A proxy for how often adding a dependency meets a project-level
    cooldown; one query over the metadata table (about 19 million rows).
    """
    import calendar
    ly, lm = map(int, a.last.split("-"))
    start, end = f"{a.first}-01", f"{a.last}-{calendar.monthrange(ly, lm)[1]}"
    dep = "lower(replaceRegexpAll(extract(x, '^\\\\s*([A-Za-z0-9][A-Za-z0-9._-]*)'), '[-_.]+', '-'))"
    q = f"""
WITH r AS (SELECT {ph.NORM_SQL} AS project, version, min(upload_time) AS vt,
                  arraySort(arrayDistinct(arrayMap(x -> {dep}, argMin(requires_dist, upload_time)))) AS deps
           FROM pypi.projects GROUP BY project, version),
     w AS (SELECT project, vt, deps,
                  lagInFrame(deps, 1, ['__none__']) OVER (PARTITION BY project ORDER BY vt
                      ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS prev
           FROM r),
     e AS (SELECT project, toDate(vt) AS day, prev = ['__none__'] AS first_release, d
           FROM w ARRAY JOIN arrayFilter(x -> x != '' AND x != project AND NOT has(prev, x), deps) AS d
           WHERE vt >= toDateTime('{start}') AND vt < toDateTime('{end}') + INTERVAL 1 DAY),
     f AS (SELECT {ph.NORM_SQL} AS project, toDate(min(upload_time)) AS first FROM pypi.projects GROUP BY project)
SELECT toString(toStartOfMonth(e.day)) AS month, e.first_release AS first_release, count() AS edges,
       countIf(f.first = toDate('1970-01-01')) AS target_unknown,
       countIf(f.first > e.day) AS target_registered_later,
       countIf(f.first > toDate('1970-01-01') AND e.day >= f.first AND e.day < f.first + 1) AS age_lt1,
       countIf(f.first > toDate('1970-01-01') AND e.day >= f.first AND e.day < f.first + 7) AS age_lt7,
       countIf(f.first > toDate('1970-01-01') AND e.day >= f.first AND e.day < f.first + 30) AS age_lt30,
       countIf(f.first > toDate('1970-01-01') AND e.day >= f.first AND e.day < f.first + 90) AS age_lt90,
       uniqExact(e.project) AS adding_projects
FROM e LEFT JOIN f ON e.d = f.project
GROUP BY month, first_release ORDER BY month, first_release FORMAT JSONEachRow"""
    rows, summ = ph.query_complete(q)
    (FROZEN / "dependency_additions.json").write_text(json.dumps({
        "window": [a.first, a.last], "rows": [{k: (v if k == "month" else int(v)) for k, v in r.items()} for r in rows],
        "rows_read": int(summ["read_rows"]), "source": ph.CLICKHOUSE_URL,
        "fetched_at": ph.fmt_time(datetime.now(timezone.utc))}, indent=1) + "\n")
    print(f"{len(rows)} rows -> {FROZEN / 'dependency_additions.json'}", file=sys.stderr)


# High-impact PyPI incidents for the case-study table: project -> malicious versions
# (from the public incident reports cited in the paper; [] = every version; for ctx every version
# uploaded after the account takeover of 14 May 2022).
CASES = {"ultralytics": ["8.3.41", "8.3.42", "8.3.45", "8.3.46"], "ctx": ["0.1.4", "0.2", "0.2.1", "0.2.2", "0.2.3", "0.2.2.1", "0.2.4", "0.2.5", "0.2.6"],
         "num2words": ["0.5.15", "0.5.16"], "lightning": ["2.6.2", "2.6.3"], "aiocpa": ["0.1.13", "0.1.14"],
         "torchtriton": []}


def cmd_cases(a):
    """Round 2: release timelines and daily downloads (first 60 days) of the malicious case-study versions."""
    ns = ",".join(sql_str(n) for n in CASES)
    versions = ph.query_complete(f"""
SELECT {ph.NORM_SQL} AS norm_name, version, toString(min(upload_time)) AS uploaded
FROM pypi.projects WHERE norm_name IN ({ns}) GROUP BY norm_name, version ORDER BY norm_name, uploaded
FORMAT JSONEachRow""")[0]
    up = {(r["norm_name"], r["version"]): r["uploaded"][:10] for r in versions}
    keys = [(n, v) for n, vs in CASES.items() for v in (vs or [v for (p, v) in up if p == n])]
    downloads = []
    for n, v in keys:
        if (n, v) not in up:
            # deleted before the metadata mirror captured it: the first download day stands in for the upload
            first = ph.query_complete(f"""
SELECT toString(min(date)) AS d FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
WHERE project = {sql_str(n)} AND version = {sql_str(v)} AND count > 0 FORMAT JSONEachRow""")[0]
            if not first or first[0]["d"].startswith("1970"):
                print(f"  (no metadata and no downloads for {n} {v})", file=sys.stderr)
                continue
            up[(n, v)] = first[0]["d"]
            versions.append({"norm_name": n, "version": v, "uploaded": first[0]["d"] + " 00:00:00",
                             "proxy": "first download day"})
        downloads += ph.query_complete(f"""
SELECT project, version, toString(date) AS day, sumIf(count, installer IN {CLIENTS}) AS client, sum(count) AS total
FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
WHERE project = {sql_str(n)} AND version = {sql_str(v)}
  AND date BETWEEN toDate('{up[(n, v)]}') AND toDate('{up[(n, v)]}') + 60
GROUP BY project, version, date ORDER BY date FORMAT JSONEachRow""")[0]
    write_jsonl_gz(RAW / "case_versions.jsonl.gz", versions)
    write_jsonl_gz(RAW / "case_downloads.jsonl.gz", downloads)


def cmd_dormancy_cost(a):
    """Share of install-client downloads that I-10 would prompt, for several dormancy periods.

    A download counts when its version is younger than 30 days at the download
    date, the project is at least 30 days old, and the version was uploaded at
    least G days after the project's previous version.
    """
    gs = [30, 60, 90, 180, 365]
    cols = ", ".join(f"sumIf(cc, d.date < v.vt + 30 AND d.date >= v.pfirst + 30 AND v.pv > toDate('1971-01-01') "
                     f"AND dateDiff('day', v.pv, v.vt) >= {g}) AS dc{g}" for g in gs)
    out = {"window": [a.start, a.end], "dormancy_days": gs, "runs": []}
    for _ in range(a.repeats):
        q = f"""
WITH d AS (SELECT project, version, date, sumIf(count, installer IN {CLIENTS}) AS cc
           FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
           WHERE date BETWEEN '{a.start}' AND '{a.end}' GROUP BY project, version, date),
     v AS (SELECT project, version, vt,
                  lagInFrame(vt, 1, toDate('1970-01-01')) OVER (PARTITION BY project ORDER BY vt
                      ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS pv,
                  min(vt) OVER (PARTITION BY project) AS pfirst
           FROM (SELECT {ph.NORM_SQL} AS project, version, toDate(min(upload_time)) AS vt
                 FROM pypi.projects GROUP BY project, version))
SELECT sum(cc) AS total_client, {cols}
FROM d LEFT JOIN v ON d.project = v.project AND d.version = v.version
FORMAT JSONEachRow"""
        r = {k: int(v) for k, v in ph.query(q)[0].items()}
        out["runs"].append(r)
        print(json.dumps(r), file=sys.stderr)
    out["fetched_at"] = ph.fmt_time(datetime.now(timezone.utc))
    (FROZEN / a.out).write_text(json.dumps(out, indent=2) + "\n")


OSV_ZIP = "https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip"


def cmd_prospective(a):
    """Malicious PyPI packages reported after the evaluation freeze."""
    known = {r["name"] for r in csv.DictReader(open("testdata/malicious_osv.csv"))}
    with urllib.request.urlopen(OSV_ZIP, timeout=600) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    recs = {}
    for f in z.namelist():
        if not f.startswith("MAL-"):
            continue
        d = json.loads(z.read(f))
        if d.get("withdrawn"):
            continue
        pub = ph.parse_time(d["published"])
        for aff in d.get("affected", []):
            pkg = aff.get("package", {})
            if pkg.get("ecosystem") != "PyPI":
                continue
            n = ph.normalize(pkg["name"])
            r0 = recs.setdefault(n, {"name": n, "published": pub, "ids": set(), "versions": set(),
                                     "typosquat": False})
            r0["published"] = min(r0["published"], pub)
            r0["ids"].add(d["id"])
            r0["versions"].update(aff.get("versions", []))
            text = (d.get("summary", "") + " " + d.get("details", "")).lower()
            r0["typosquat"] |= "typosquat" in text
    new = [r for n, r in recs.items() if n not in known and r["published"] >= FREEZE]
    print(f"OSV MAL PyPI names: {len(recs)}; published after freeze and not in the frozen set: {len(new)}")
    with open(FROZEN / "prospective_osv.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "typosquat", "published", "mal_ids", "mal_versions"])
        for r in sorted(new, key=lambda r: r["name"]):
            w.writerow([r["name"], str(r["typosquat"]).lower(), ph.fmt_time(r["published"]),
                        " ".join(sorted(r["ids"])), " ".join(sorted(r["versions"]))])
    rows = ph.fetch_versions([r["name"] for r in new], batch=200) if new else []
    write_jsonl_gz(RAW / "prospective_versions.jsonl.gz", rows)
    (RAW / "prospective_fetch.json").write_text(json.dumps({
        "fetched_at": ph.fmt_time(datetime.now(timezone.utc)), "freeze": ph.fmt_time(FREEZE),
        "osv_new_names": len(new), "with_history": len({r["norm_name"] for r in rows})}, indent=2) + "\n")


def cmd_presence(a):
    """Download-log footprint of every OSV name (frozen and prospective sets).

    The download table is independent of the metadata table used for the
    reconstruction, so it shows (i) whether a name without metadata was ever
    downloadable and (ii) whether the reconstructed first upload agrees with
    the first day on which the project was downloaded.
    """
    names = [r["name"] for r in csv.DictReader(open("testdata/malicious_osv.csv"))]
    if (FROZEN / "prospective_osv.csv").exists():
        names += [r["name"] for r in csv.DictReader(open(FROZEN / "prospective_osv.csv"))]
    names = sorted(set(names))
    rows = []
    for i in range(0, len(names), 1500):
        chunk = ",".join(sql_str(n) for n in names[i:i + 1500])
        rows += ph.query_complete(f"""
SELECT project, toString(min(date)) AS first_date, toString(max(date)) AS last_date,
       sum(count) AS total, sumIf(count, installer IN {CLIENTS}) AS client, uniqExact(version) AS versions
FROM pypi.pypi_downloads_per_day_by_version_by_installer_by_type
WHERE project IN ({chunk}) AND count > 0 GROUP BY project FORMAT JSONEachRow""")[0]
        print(f"  ... {min(i + 1500, len(names))}/{len(names)}", file=sys.stderr)
    write_jsonl_gz(RAW / "osv_presence.jsonl.gz", rows)


def release_times(name):
    """{version: first upload time} from the PyPI JSON API (None if the project is gone)."""
    url = f"https://pypi.org/pypi/{name}/json"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pipguard-eval/1.0 (research)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            out = {}
            for ver, files in d["releases"].items():
                ts = [f["upload_time_iso_8601"] for f in files]
                if ts:
                    out[ver] = min(ts)
            return out
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return None


def cmd_release_times(a):
    """Per-version upload times of the legitimate packages (benign new and established).

    Needed for the release-level indicators (latest and previous release at the
    assessment time). Versions uploaded after the frozen assessment time are
    ignored later, in build_sets.py meta, so the evaluation stays frozen.
    """
    from concurrent.futures import ThreadPoolExecutor
    names = [r["name"] for r in csv.DictReader(open(RAW / "benign_new_sample.csv"))]
    names += [json.loads(l)["name"] for l in open(FROZEN / "meta_established_live.jsonl")]
    names = sorted(set(names))
    out = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, (n, rt) in enumerate(zip(names, ex.map(release_times, names)), 1):
            out[n] = rt
            if i % 1000 == 0:
                print(f"  ... {i}/{len(names)}", file=sys.stderr)
    with gzip.open(RAW / "legit_release_times.json.gz", "wt") as f:
        json.dump({"fetched_at": ph.fmt_time(datetime.now(timezone.utc)), "releases": out}, f)
    print(f"{sum(v is not None for v in out.values())}/{len(names)} projects still on PyPI")


def cmd_firstseen(a):
    names = sorted({ph.normalize(l.strip()) for l in open(a.names) if l.strip()})
    names = [n for n in names if all(c.isalnum() or c == "-" for c in n)]
    rows = []
    for i in range(0, len(names), 2000):
        chunk = names[i:i + 2000]
        rows += ph.query_complete(f"""
SELECT {ph.NORM_SQL} AS n, toString(min(upload_time)) AS first, toString(max(upload_time)) AS last,
       uniqExact(version) AS versions
FROM pypi.projects WHERE n IN ({','.join(map(sql_str, chunk))}) GROUP BY n FORMAT JSONEachRow""")[0]
    Path(a.out).write_text(json.dumps({r["n"]: r for r in rows}, indent=1) + "\n")
    print(f"{len(rows)}/{len(names)} names have PyPI history -> {a.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("exposure"); p.add_argument("--batch", type=int, default=800); p.set_defaults(func=cmd_exposure)
    p = sub.add_parser("campaign"); p.add_argument("--batch", type=int, default=1500); p.set_defaults(func=cmd_campaign)
    p = sub.add_parser("cost")
    p.add_argument("--start", default="2026-09-01"); p.add_argument("--end", default="2026-09-30")
    p.add_argument("--repeats", type=int, default=3); p.add_argument("--out", default="")
    p.set_defaults(func=cmd_cost)
    p = sub.add_parser("cost-complete", help="round 2: complete monthly costs for [--first, --last]")
    p.add_argument("--first", default="2024-10"); p.add_argument("--last", default="2026-09")
    p.add_argument("--limit", type=int, default=600_000_000); p.set_defaults(func=cmd_cost_complete)
    p = sub.add_parser("background"); p.add_argument("--batch", type=int, default=400)
    p.set_defaults(func=cmd_background)
    p = sub.add_parser("filetype"); p.set_defaults(func=cmd_filetype)
    p = sub.add_parser("dependents"); p.set_defaults(func=cmd_dependents)
    p = sub.add_parser("cases"); p.set_defaults(func=cmd_cases)
    p = sub.add_parser("dep-additions")
    p.add_argument("--first", default="2024-10"); p.add_argument("--last", default="2026-09")
    p.set_defaults(func=cmd_dep_additions)
    p = sub.add_parser("dormancy-cost")
    p.add_argument("--start", default="2026-06-01"); p.add_argument("--end", default="2026-06-30")
    p.add_argument("--repeats", type=int, default=1); p.add_argument("--out", default="dormancy_cost.json")
    p.set_defaults(func=cmd_dormancy_cost)
    p = sub.add_parser("prospective"); p.set_defaults(func=cmd_prospective)
    p = sub.add_parser("release-times"); p.set_defaults(func=cmd_release_times)
    p = sub.add_parser("presence"); p.set_defaults(func=cmd_presence)
    p = sub.add_parser("firstseen"); p.add_argument("names"); p.add_argument("out"); p.set_defaults(func=cmd_firstseen)
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    a.func(a)


if __name__ == "__main__":
    main()
