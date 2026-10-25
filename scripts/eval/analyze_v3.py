#!/usr/bin/env python3
"""All tables, figures and numbers of the journal version of the pipguard paper.

Reads only frozen inputs (testdata/frozen/) and the per-package results written
by `evalset` (paper/data/results_*.csv); never touches the network. Run through
scripts/eval/run_all.sh.

Outputs
  paper/tables/*.csv, *.md   one file per table, plus tables.md (all of them)
  paper/figures/*.pdf, *.png black-and-white figures, English labels
  paper/numbers.json         every number quoted in the text

Statistical conventions
  * Proportions: 95% Wilson intervals (package level) and 95% cluster-bootstrap
    percentile intervals that resample malicious-package campaigns (2,000
    replicates), because packages of one campaign are near-duplicates.
  * Paired detector comparisons: exact McNemar test.
  * AUC: Mann-Whitney estimate; intervals by stratified (or campaign) bootstrap.
"""
import csv
import gzip
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pypi_history as ph  # noqa: E402

FROZEN = Path("testdata/frozen")
RAW = FROZEN / "raw"
DATA = Path("paper/data")
TABLES = Path("paper/tables")
FIGS = Path("paper/figures")
SEED = 20261024
B = 2000                      # bootstrap replicates
MAL = ("malicious-typosquat", "malicious-other")
THRESHOLDS = [1, 2, 3, 7, 14, 21, 30, 60, 90]
NUMBERS = {}

# ----------------------------------------------------------------- style (B/W)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.2, "legend.frameon": False,
    "axes.edgecolor": "black", "axes.linewidth": 0.7, "xtick.color": "black", "ytick.color": "black",
    "axes.labelcolor": "black", "text.color": "black", "lines.linewidth": 1.2, "lines.markersize": 4,
    "hatch.linewidth": 0.6, "savefig.dpi": 600, "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
    "axes.prop_cycle": matplotlib.cycler(color=["black"]),
})
K, G1, G2, G3 = "black", "0.35", "0.6", "0.85"       # black and three greys
LS = ["-", "--", ":", "-."]
MK = ["o", "s", "^", "D", "v", "x"]


def save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)


# ----------------------------------------------------------------- statistics

def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def pct(x, nd=1):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.{nd}f}"


def rate_ci(k, n, nd=1):
    lo, hi = wilson(k, n)
    return f"{pct(k / n if n else float('nan'), nd)} [{pct(lo, nd)}–{pct(hi, nd)}]"


def cluster_boot(values, clusters, reps=B, seed=SEED, stat=np.mean):
    """Percentile interval of stat(values) resampling whole clusters."""
    values = np.asarray(values, float)
    ids = np.asarray(clusters)
    uniq, inv = np.unique(ids, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=len(uniq))
    cnts = np.bincount(inv, minlength=len(uniq)).astype(float)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(reps):
        pick = rng.integers(0, len(uniq), len(uniq))
        n = cnts[pick].sum()
        out.append(sums[pick].sum() / n if n else np.nan)
    return np.nanpercentile(out, 2.5), np.nanpercentile(out, 97.5)


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    rp = ranks[:len(pos)].sum()
    return (rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


# ----------------------------------------------------------------- tables

ALL_TABLES = []


def table(name, title, header, rows, note=""):
    TABLES.mkdir(parents=True, exist_ok=True)
    with open(TABLES / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    md = [f"### {title}", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    if note:
        md += ["", note]
    (TABLES / f"{name}.md").write_text("\n".join(md) + "\n")
    ALL_TABLES.append("\n".join(md))


# ----------------------------------------------------------------- loading

def jsonl(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def results(scenario):
    with open(DATA / f"results_{scenario}.csv", newline="") as f:
        return list(csv.DictReader(f))


def t(s):
    return ph.parse_time(s)


def half(dt):
    return f"{dt.year} H{1 if dt.month <= 6 else 2}"


OSV = {r["name"]: r for r in csv.DictReader(open("testdata/malicious_osv.csv"))}
META_FIRST = {r["name"]: r for r in jsonl(FROZEN / "meta_malicious_first.jsonl")}
VERS = ph.group_versions(jsonl(RAW / "malicious_versions.jsonl.gz"))
PRESENCE = {r["project"]: r for r in jsonl(RAW / "osv_presence.jsonl.gz")}


def first_malicious(n):
    return t(META_FIRST[n]["as_of"]) - timedelta(minutes=1)


def project_age_at_attack(n):
    return (first_malicious(n) - VERS[n][0]["upload_time"]).total_seconds() / 86400


def prev_gap(n):
    fm = first_malicious(n)
    prev = [v for v in VERS[n] if v["upload_time"] < fm]
    return (fm - prev[-1]["upload_time"]).total_seconds() / 86400 if prev else None


# ----------------------------------------------------------------- campaigns

def campaigns(window=7, keys_used=("email", "desc", "sum")):
    """Union-find clustering of malicious packages into campaigns.

    Two packages are linked when their first malicious uploads are at most
    `window` (7) days apart and they share the uploader e-mail, the description
    (>= 100 characters, same hash), or the summary together with the upload tool.
    """
    up = defaultdict(list)
    for r in jsonl(RAW / "malicious_uploaders.jsonl.gz"):
        up[r["norm_name"]].append(r)
    names = sorted(META_FIRST)
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    keys = defaultdict(list)
    for n in names:
        fm = first_malicious(n)
        rows = up.get(n, [])
        # the uploader record of the first malicious version
        best = min(rows, key=lambda r: abs((t(r["first_upload"]) - fm).total_seconds()), default=None)
        if best is None:
            continue
        email = (best["author_email"] or best["maintainer_email"] or "").strip().lower()
        if email and "email" in keys_used:
            keys[("email", email)].append((fm, n))
        if META_FIRST[n]["description_len"] >= 100 and "desc" in keys_used:
            keys[("desc", best["description_hash"])].append((fm, n))
        if META_FIRST[n]["summary"] and "sum" in keys_used:
            keys[("sum", best["summary_hash"], best["uploaded_via"])].append((fm, n))
    for members in keys.values():
        members.sort()
        for (t1, a), (t2, b) in zip(members, members[1:]):
            if (t2 - t1) <= timedelta(days=window):
                union(a, b)
    return {n: find(n) for n in names}


CAMP = campaigns()


# ================================================================= analyses

def a_dataset_and_missingness():
    """R4: which OSV names could be reconstructed, by report period, and validation."""
    by = defaultdict(lambda: [0, 0, 0])   # half-year -> [osv names, downloadable, reconstructed]
    life_found, life_missing = [], []
    early_missing = 0
    n_missing_present = 0
    for n, o in OSV.items():
        h = half(t(o["published"]))
        pres = PRESENCE.get(n)
        by[h][0] += 1
        by[h][1] += pres is not None
        by[h][2] += n in META_FIRST
        if pres:
            life = (datetime.fromisoformat(pres["last_date"]) - datetime.fromisoformat(pres["first_date"])).days + 1
            (life_found if n in META_FIRST else life_missing).append(life)
            if n not in META_FIRST:
                n_missing_present += 1
                rep = t(o["published"]).date()
                if (rep - datetime.fromisoformat(pres["first_date"]).date()).days < 30:
                    early_missing += 1
    rows = []
    for h in sorted(by):
        tot, pres, rec = by[h]
        rows.append([h, tot, f"{pct(pres / tot)}", rec, f"{pct(rec / tot)}"])
    tot = [sum(v[i] for v in by.values()) for i in range(3)]
    rows.append(["All", tot[0], pct(tot[1] / tot[0]), tot[2], pct(tot[2] / tot[0])])
    table("t_missingness", "Coverage of OSV malicious PyPI names by period of the OSV report",
          ["OSV report period", "Names", "Downloadable (%)", "Reconstructed", "Reconstructed (%)"], rows,
          "Downloadable = at least one download in the ClickPy download log (independent of the metadata table). "
          "Reconstructed = per-version metadata available, which the evaluation requires.")
    # validation of the reconstruction on deleted projects: first upload vs first download
    diffs = []
    for n in META_FIRST:
        pres = PRESENCE.get(n)
        if pres:
            fu = VERS[n][0]["upload_time"].date()
            diffs.append((datetime.fromisoformat(pres["first_date"]).date() - fu).days)
    diffs = np.array(diffs)
    listed_found = listed_total = 0
    for n in META_FIRST:
        listed = set(OSV[n]["mal_versions"].split())
        if listed:
            have = {v["version"] for v in VERS[n]}
            listed_total += len(listed)
            listed_found += len(listed & have)
    NUMBERS["missingness"] = {
        "osv_names": tot[0], "downloadable": tot[1], "reconstructed": tot[2],
        "missing_but_downloadable": n_missing_present,
        "missing_first_download_within_30d_of_report": early_missing,
        "lifetime_days_median_reconstructed": float(np.median(life_found)),
        "lifetime_days_median_missing": float(np.median(life_missing)),
        "lifetime_days_iqr_reconstructed": [float(np.percentile(life_found, 25)), float(np.percentile(life_found, 75))],
        "lifetime_days_iqr_missing": [float(np.percentile(life_missing, 25)), float(np.percentile(life_missing, 75))],
        "first_download_minus_first_upload_days": {
            "n": int(len(diffs)), "same_day": float(np.mean(diffs == 0)), "within_1_day": float(np.mean(np.abs(diffs) <= 1)),
            "download_before_upload": int(np.sum(diffs < 0))},
        "osv_listed_versions_found": [listed_found, listed_total],
    }
    return by


def a_missing_sensitivity(first):
    """R4: bounds on 2026 recall if the packages that could not be reconstructed were included.

    A package whose first download (download log, independent of the metadata
    table) falls in 2026 is assigned to the 2026 cohort. A missing package
    first downloaded less than 30 days before its OSV report was certainly a
    project younger than 30 days when the malicious upload happened, so the
    existence-plus-age rule would have prompted for it; for the others the
    outcome is unknown (lower bound: missed; upper bound: prompted).
    """
    flagged = {r["name"]: r["flagged_pipguard-v2"] == "1" for r in first if r["group"] in MAL}
    out = {}
    for year in (2025, 2026):
        tot = rec = rec_flag = miss_young = miss_other = 0
        for n, o in OSV.items():
            pres = PRESENCE.get(n)
            if not pres or datetime.fromisoformat(pres["first_date"]).year != year:
                continue
            tot += 1
            if n in META_FIRST:
                rec += 1
                rec_flag += flagged.get(n, False)
            else:
                age = (t(o["published"]).date() - datetime.fromisoformat(pres["first_date"]).date()).days
                if age < 30:
                    miss_young += 1
                else:
                    miss_other += 1
        out[year] = {"cohort": tot, "reconstructed": rec, "reconstructed_flagged": rec_flag,
                     "missing_young": miss_young, "missing_other": miss_other,
                     "recall_reconstructed": rec_flag / rec if rec else None,
                     "recall_lower": (rec_flag + miss_young) / tot, "recall_upper": (rec_flag + miss_young + miss_other) / tot}
    NUMBERS["missing_sensitivity"] = out


def a_timing():
    """R3: time from the first malicious upload to the OSV report and to the last download."""
    # Removal proxy: the end of the last age bucket with any install-client
    # download (mirrors and crawlers keep fetching sporadically for years).
    edge = {b: b + 1 for b in range(15)}
    edge.update({15: 21, 21: 30, 30: 60, 60: 90, 90: 180, 180: 365, 365: np.inf})
    last = {}
    for r in jsonl(RAW / "malicious_downloads.jsonl.gz"):
        if r["bucket"] >= 0 and r["client"] > 0:
            last[r["project"]] = max(last.get(r["project"], 0), edge[r["bucket"]])
    rep, gone, split = [], [], []
    for n, m in META_FIRST.items():
        fm = first_malicious(n)
        rep.append((t(OSV[n]["published"]) - fm).total_seconds() / 86400)
        gone.append(last.get(n, np.nan))
        split.append(m["split"])
    rep, gone, split = np.array(rep), np.array(gone), np.array(split)
    out = {}
    for s in ("all", "dev", "val", "test"):
        sel = np.ones(len(rep), bool) if s == "all" else split == s
        r_, g_ = rep[sel], gone[sel]
        g_ = g_[~np.isnan(g_)]
        out[s] = {"n": int(sel.sum()),
                  "report_median_days": float(np.median(r_)),
                  "report_q": [float(np.percentile(r_, q)) for q in (25, 75, 90)],
                  "report_within": {str(d): float(np.mean(r_ <= d)) for d in (1, 2, 7, 30, 90)},
                  "lastdl_median_days": float(np.median(g_)), "lastdl_n": int(len(g_)),
                  "lastdl_within": {str(d): float(np.mean(g_ <= d)) for d in (1, 2, 7, 30, 90)},
                  "report_negative": int(np.sum(r_ < 0))}
    NUMBERS["timing"] = out
    rows = []
    for s, lab in (("dev", "< 2025"), ("val", "2025"), ("test", "2026"), ("all", "All")):
        o = out[s]
        rows.append([lab, o["n"], f"{o['report_median_days']:.1f}",
                     pct(o["report_within"]["1"]), pct(o["report_within"]["7"]), pct(o["report_within"]["30"]),
                     f"{o['lastdl_median_days']:.0f}", pct(o["lastdl_within"]["7"]), pct(o["lastdl_within"]["30"])])
    table("t_timing", "Time from the first malicious upload to the OSV report and to the last recorded download",
          ["Period", "n", "Report: median (days)", "Reported ≤ 1 d (%)", "≤ 7 d (%)", "≤ 30 d (%)",
           "Last client download: median (days)", "≤ 7 d (%)", "≤ 30 d (%)"], rows,
          "Last client download = end of the last day (age bucket) with a download by pip, uv, poetry, pdm or pipenv; "
          "it approximates removal from PyPI. Packages without any client download are excluded from that column.")
    return rep, gone, split


def load_exposure():
    """Client downloads of malicious releases by age bucket, per package."""
    per = defaultdict(dict)
    for r in jsonl(RAW / "malicious_downloads.jsonl.gz"):
        if r["bucket"] >= 0:
            per[r["project"]][r["bucket"]] = (r["client"], r["total"])
    return per


BUCKETS = list(range(15)) + [15, 21, 30, 60, 90, 180, 365]


def protected_share(per, policy, which=0):
    """Pooled and per-package protected shares of malicious downloads.

    policy(n, bucket) -> True when an installation at that age would be stopped.
    which: 0 = install clients only, 1 = all downloads.
    """
    pooled_num = pooled_den = 0
    pkg_shares, pkg_names = [], []
    for n, bk in per.items():
        if n not in META_FIRST:
            continue
        num = den = 0
        for b, v in bk.items():
            den += v[which]
            if policy(n, b):
                num += v[which]
        if den > 0:
            pooled_num += num
            pooled_den += den
            pkg_shares.append(num / den)
            pkg_names.append(n)
    return pooled_num / pooled_den, np.array(pkg_shares), pkg_names


def project_age_days_cal(n):
    """Project age at the attack in calendar days, the resolution of the download log.

    Age buckets count calendar days since the first malicious upload (fetch_v3
    exposure), so the project's age on a download day is this value plus the
    bucket. (Round 1 added the age in fractional days; it came out about -0.4 s
    for brand-new projects because as_of is truncated to seconds, so b + age0 < T
    also stopped bucket b = T and inflated every project-level figure.)
    """
    return (t(META_FIRST[n]["as_of"]).date() - VERS[n][0]["upload_time"].date()).days


def policies(G=None, shift=0):
    """Install-time policies as functions (package, age bucket in days since the attack) -> stopped.

    shift moves the day alignment: +1 treats a download on calendar day b as one
    day older (conservative for every policy), -1 as one day younger.
    """
    age0 = {n: project_age_days_cal(n) for n in META_FIRST}
    gap = {n: prev_gap(n) for n in META_FIRST}
    rep = {n: (t(OSV[n]["published"]) - first_malicious(n)).total_seconds() / 86400 for n in META_FIRST}
    G = G or 90
    return {
        "project": lambda T: (lambda n, b: b + shift + age0[n] < T),
        "release": lambda T: (lambda n, b: b + shift < T),
        "hybrid": lambda T: (lambda n, b: (b + shift + age0[n] < T) or
                             (age0[n] >= 30 and gap[n] is not None and gap[n] >= G and b + shift < T)),
        "feed": lambda T: (lambda n, b: b >= math.ceil(rep[n])),
        "release+feed": lambda T: (lambda n, b: b < T or b >= math.ceil(rep[n])),
    }


def a_exposure(per):
    P = policies()
    out = {}
    for pol in ("project", "release"):
        out[pol] = {}
        for T in THRESHOLDS:
            pooled, shares, names = protected_share(per, P[pol](T))
            out[pol][T] = {"pooled": pooled, "median_pkg": float(np.median(shares)), "mean_pkg": float(np.mean(shares))}
    pooled_all, _, _ = protected_share(per, P["project"](30), which=1)
    feed_pooled, feed_sh, _ = protected_share(per, P["feed"](0))
    NUMBERS["exposure"] = {"by_policy": out, "project30_all_downloads": pooled_all,
                           "feed_pooled": feed_pooled, "feed_mean_pkg": float(np.mean(feed_sh)),
                           "packages_with_client_downloads": len(feed_sh)}
    return out


# ----------------------------------------------------------------- round 2: exposure estimators

def pkg_stopped(per, policy, names, which=0, counts=None):
    """Per package: downloads stopped by the policy and all downloads (client downloads by default)."""
    num, den = np.zeros(len(names)), np.zeros(len(names))
    for i, n in enumerate(names):
        for b, v in (counts or per)[n].items():
            x = v[which] if isinstance(v, tuple) else v
            den[i] += x
            if policy(n, b):
                num[i] += x
    return num, den


def estimators(num, den, camps, reps=B, seed=SEED):
    """Per-package mean, download-weighted (pooled) and campaign-weighted protected share, with
    95% intervals from resampling campaigns."""
    keep = den > 0
    num, den, camps = num[keep], den[keep], np.asarray(camps)[keep]
    share = num / den
    uniq, inv = np.unique(camps, return_inverse=True)
    k = len(uniq)
    s_sum = np.bincount(inv, weights=share, minlength=k)
    cnt = np.bincount(inv, minlength=k).astype(float)
    n_sum = np.bincount(inv, weights=num, minlength=k)
    d_sum = np.bincount(inv, weights=den, minlength=k)
    c_mean = s_sum / cnt

    def stats(w):
        return (w @ s_sum / (w @ cnt), w @ n_sum / (w @ d_sum), w @ c_mean / w.sum())

    point = stats(np.ones(k))
    rng = np.random.default_rng(seed)
    boots = np.array([stats(np.bincount(rng.integers(0, k, k), minlength=k).astype(float)) for _ in range(reps)])
    lo, hi = np.percentile(boots, 2.5, axis=0), np.percentile(boots, 97.5, axis=0)
    out = {}
    for i, key in enumerate(("per_package", "download_weighted", "campaign_weighted")):
        out[key] = {"est": float(point[i]), "ci": [float(lo[i]), float(hi[i])]}
    out["n_packages"], out["n_campaigns"] = int(len(share)), int(k)
    return out


def leave_top_out(num, den, ks=(1, 5, 10)):
    order = np.argsort(-den, kind="stable")
    return {str(k): float(num[order[k:]].sum() / den[order[k:]].sum()) for k in ks}


def a_exposure_estimators(per, counts=None, tag=""):
    """R1 (round 2): exposure under every estimator, by period, with campaign intervals."""
    names = sorted(n for n in per if n in META_FIRST)
    split = {n: META_FIRST[n]["split"] for n in names}
    subsets = {"all": names, "dev": [n for n in names if split[n] == "dev"],
               "val": [n for n in names if split[n] == "val"], "test": [n for n in names if split[n] == "test"]}
    res = {}
    for shift in (0, -1, 1):
        P = policies(shift=shift)
        for pol in ("project", "release"):
            for T in (THRESHOLDS if shift == 0 else [1, 2, 7, 30]):
                for sub, ns in subsets.items():
                    num, den = pkg_stopped(per, P[pol](T), ns, counts=counts)
                    if den.sum() == 0:
                        continue
                    e = estimators(num, den, [CAMP[n] for n in ns], reps=B if shift == 0 else 200)
                    e["leave_top_out"] = leave_top_out(num, den)
                    e["client_downloads"] = float(den.sum())
                    res.setdefault(f"shift{shift}", {}).setdefault(pol, {}).setdefault(str(T), {})[sub] = e
    # who carries the download weight
    _, den = pkg_stopped(per, lambda n, b: False, names, counts=counts)
    order = np.argsort(-den)
    top = [{"name": names[i], "split": split[names[i]], "client": float(den[i]),
            "share": float(den[i] / den.sum()), "project_age_days": project_age_days_cal(names[i])}
           for i in order[:10]]
    NUMBERS["exposure_estimators" + tag] = {"by_shift": res, "top_packages": top,
                                            "top1_share": top[0]["share"],
                                            "top10_share": float(den[order[:10]].sum() / den.sum())}
    return res


def t_exposure_tables():
    """Tables for R1/R3: exposure estimators by period, and protection against cost by threshold."""
    ex = NUMBERS["exposure_estimators"]["by_shift"]["shift0"]

    def ci(e, nd=1):
        return f"{pct(e['est'], nd)} [{pct(e['ci'][0], nd)}–{pct(e['ci'][1], nd)}]"
    rows = []
    for sub, lab in (("test", "2026 (test)"), ("val", "2025"), ("dev", "< 2025"), ("all", "All periods")):
        p, r = ex["project"]["30"][sub], ex["release"]["30"][sub]
        for key, kl in (("per_package", "Mean per package"), ("campaign_weighted", "Mean per campaign"),
                        ("download_weighted", "Download-weighted")):
            rows.append([lab, kl, ci(p[key]), ci(r[key])])
        for k in ("1", "10"):
            rows.append([lab, f"Download-weighted, top {k} excluded", pct(p["leave_top_out"][k]), pct(r["leave_top_out"][k])])
    table("t_exposure_estimators", "Malicious install-client downloads stopped by 30-day cooldowns, by estimator and period",
          ["Period", "Estimator", "Project-level 30 d (%)", "Release-level 30 d (%)"], rows,
          "95% intervals resample campaigns. Download-weighted = all stopped client downloads / all client downloads.")
    bg = NUMBERS.get("background")
    cost = NUMBERS["cost"]
    rows = []
    for T in ("1", "2", "7", "14", "30", "60", "90"):
        p, r = ex["project"][T]["test"], ex["release"][T]["test"]
        cp, cr = cost["project_client"][int(T)], cost["release_client"][int(T)]
        rows.append([T, pct(p["per_package"]["est"]), pct(p["download_weighted"]["est"]),
                     f"{pct(cp['median'], 4)} [{pct(cp['q1'], 4)}–{pct(cp['q3'], 4)}]",
                     pct(r["per_package"]["est"]), pct(r["download_weighted"]["est"]),
                     f"{pct(cr['median'], 2)} [{pct(cr['q1'], 2)}–{pct(cr['q3'], 2)}]",
                     f"{cost['ratio'][int(T)]['median']:,.0f}"])
    table("t_tradeoff", "Protection (2026 malicious packages) and cost (monthly share of client downloads) by threshold",
          ["T (days)", "Project: stopped per package (%)", "Project: stopped, download-weighted (%)",
           "Project: downloads affected, median [IQR] (%)", "Release: stopped per package (%)",
           "Release: stopped, download-weighted (%)", "Release: downloads affected, median [IQR] (%)",
           "Cost ratio release / project (median)"], rows)


def a_adaptive(per):
    """R7 (round 2): protection when a share p of attackers pre-ages its projects.

    New-project packages keep their observed exposure profile; a pre-aged
    package is modelled by the observed malicious releases in projects at least
    30 days old (all periods, n small in 2026). I-10 is evaluated twice: as
    observed (attackers have not adapted to it) and fully adapted (pre-agers
    keep a release cadence shorter than G, so I-10 never fires).
    """
    names = sorted(n for n in per if n in META_FIRST)
    age = {n: project_age_days_cal(n) for n in names}
    young_test = [n for n in names if age[n] < 30 and META_FIRST[n]["split"] == "test"]
    old_all = [n for n in names if age[n] >= 30]
    P = policies(G=90)
    pols = {"project30": P["project"](30), "project30_i10_observed": P["hybrid"](30),
            "project30_i10_adapted": P["project"](30), "release30": P["release"](30),
            "release1": P["release"](1), "release7": P["release"](7)}
    out = {"n_young_test": len(young_test), "n_old_all": len(old_all),
           "n_old_test": sum(1 for n in old_all if META_FIRST[n]["split"] == "test")}
    for k, pol in pols.items():
        for grp, ns in (("young", young_test), ("old", old_all)):
            num, den = pkg_stopped(per, pol, ns)
            sh = num[den > 0] / den[den > 0]
            out.setdefault(k, {})[grp] = float(sh.mean())
            out[k][grp + "_pooled"] = float(num.sum() / den.sum())
    ps = [0, 0.059, 0.1, 0.25, 0.5, 0.75, 1.0]
    for k in pols:
        out[k]["by_p"] = {str(p): (1 - p) * out[k]["young"] + p * out[k]["old"] for p in ps}
    # how long malicious releases in old projects stay installable (2026): what waiting buys
    rep_old, last_old = [], []
    edge = {b: b + 1 for b in range(15)}
    edge.update({15: 21, 21: 30, 30: 60, 60: 90, 90: 180, 180: 365, 365: np.inf})
    for n in old_all:
        if META_FIRST[n]["split"] != "test":
            continue
        rep_old.append((t(OSV[n]["published"]) - first_malicious(n)).total_seconds() / 86400)
        bs = [b for b, v in per[n].items() if v[0] > 0]
        if bs:
            last_old.append(edge[max(bs)])
    out["old_test_report_median_days"] = float(np.median(rep_old))
    out["old_test_lastdl_median_days"] = float(np.median(last_old))
    out["old_test_lastdl_within30"] = float(np.mean(np.array(last_old) <= 30))
    NUMBERS["adaptive"] = out
    return out


def f_adaptive():
    a = NUMBERS["adaptive"]
    fig, ax = plt.subplots(figsize=(3.6, 2.5))
    xs = np.linspace(0, 1, 101)
    for k, lab, ls in (("release30", "Release-level, 30 d", "--"),
                       ("project30_i10_observed", "Project + I-10 (90 d), not evaded", "-."),
                       ("project30", "Project-level, 30 d", "-")):
        ax.plot(100 * xs, [100 * ((1 - p) * a[k]["young"] + p * a[k]["old"]) for p in xs], ls=ls, color=K, label=lab)
    ax.axvline(5.9, color=G2, lw=0.8, ls=":")
    ax.text(7.5, 40, "2026", fontsize=6.5, color=K)
    ax.set_xlabel("Share of attackers who pre-age (%)")
    ax.set_ylabel("Malicious downloads stopped,\nmean per package (%)")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 100)
    ax.legend(loc="lower left", fontsize=6.3)
    fig.tight_layout()
    save(fig, "fig_adaptive")


def a_campaign_sensitivity(first, per):
    """S2 (round 2): how the campaign definition changes campaign counts and campaign-level results."""
    global CAMP
    keep = CAMP
    mal_test = [r for r in first if r["group"] in MAL and r["split"] == "test"]
    names = sorted(n for n in per if n in META_FIRST and META_FIRST[n]["split"] == "test")
    P = policies()
    out = {}
    for label, w, keys in (("3 d, all keys", 3, ("email", "desc", "sum")), ("7 d, all keys (main)", 7, ("email", "desc", "sum")),
                           ("14 d, all keys", 14, ("email", "desc", "sum")), ("30 d, all keys", 30, ("email", "desc", "sum")),
                           ("7 d, e-mail only", 7, ("email",)), ("7 d, e-mail or description", 7, ("email", "desc"))):
        CAMP = campaigns(w, keys)
        vals = [float(r["flagged_pipguard-v2"] == "1") for r in mal_test]
        lo, hi = cluster_boot(vals, [CAMP[r["name"]] for r in mal_test])
        per_c = defaultdict(list)
        for r in first:
            if r["group"] in MAL and r["split"] in ("dev", "test"):
                per_c[(r["split"], CAMP[r["name"]])].append(r["sig_I-07"] == "1")
        cw = {s: float(np.mean([np.mean(v) for (sp, _), v in per_c.items() if sp == s])) for s in ("dev", "test")}
        ex = {}
        for pol in ("project", "release"):
            num, den = pkg_stopped(per, P[pol](30), names)
            ex[pol] = estimators(num, den, [CAMP[n] for n in names], reps=500)["campaign_weighted"]["est"]
        sizes = Counter(CAMP[n] for n in META_FIRST)
        out[label] = {"campaigns_all": len(sizes), "largest": max(sizes.values()),
                      "campaigns_test": len({CAMP[r["name"]] for r in mal_test}),
                      "recall_ci": [lo, hi], "i07_cw_dev": cw["dev"], "i07_cw_test": cw["test"],
                      "exposure_cw_project30_test": ex["project"], "exposure_cw_release30_test": ex["release"]}
    CAMP = keep
    NUMBERS["campaign_sensitivity"] = out
    rows = [[k, v["campaigns_all"], v["largest"], v["campaigns_test"], f"{pct(v['recall_ci'][0])}–{pct(v['recall_ci'][1])}",
             pct(v["i07_cw_dev"]), pct(v["i07_cw_test"]), pct(v["exposure_cw_project30_test"]),
             pct(v["exposure_cw_release30_test"])] for k, v in out.items()]
    table("t_campaign_sensitivity", "Sensitivity of campaign-level results to the campaign definition",
          ["Definition (window, linkage)", "Campaigns (all)", "Largest campaign", "Campaigns (2026)",
           "Recall 2026, campaign bootstrap (%)", "I-07 campaign-weighted, < 2025 (%)", "I-07 campaign-weighted, 2026 (%)",
           "Stopped, project 30 d, campaign-weighted 2026 (%)", "Stopped, release 30 d, campaign-weighted 2026 (%)"], rows)


def period_of(year):
    return "dev" if year < 2025 else ("val" if year == 2025 else "test")


def a_filetype(first):
    """R4 (round 2): source-only distribution from the download log, also for unreconstructed names.

    Proxy: no built distribution (wheel, egg, ...) of the project was ever
    downloaded. Validated against I-07 on the reconstructed packages, then
    compared between reconstructed and missing names by the year of the first
    download, and stratified by lifetime for the reconstructed ones.
    """
    path = RAW / "osv_filetype.jsonl.gz"
    if not path.exists():
        return None
    ft = {r["project"]: r for r in jsonl(path)}
    i07 = {r["name"]: r["sig_I-07"] == "1" for r in first if r["group"] in MAL}
    agree = [(i07[n], int(ft[n]["built"]) == 0) for n in i07 if n in ft]
    tp = sum(a and b for a, b in agree)
    out = {"validated_n": len(agree), "agreement": float(np.mean([a == b for a, b in agree])),
           "sensitivity": tp / max(1, sum(a for a, _ in agree)),
           "specificity": sum((not a) and (not b) for a, b in agree) / max(1, sum(not a for a, _ in agree))}
    rows = []
    for s, lab in (("dev", "< 2025"), ("val", "2025"), ("test", "2026")):
        cell = {}
        for grp in ("reconstructed", "missing"):
            v = []
            for n, pres in PRESENCE.items():
                if n not in OSV or n not in ft:
                    continue
                if period_of(datetime.fromisoformat(pres["first_date"]).year) != s:
                    continue
                if (n in META_FIRST) != (grp == "reconstructed"):
                    continue
                v.append(int(ft[n]["built"]) == 0)
            cell[grp] = (sum(v), len(v))
        # lifetime strata of the reconstructed packages (days between first and last download)
        life = []
        for n in META_FIRST:
            pres = PRESENCE.get(n)
            if pres and META_FIRST[n]["split"] == s:
                lt = (datetime.fromisoformat(pres["last_date"]) - datetime.fromisoformat(pres["first_date"])).days
                life.append((lt, i07[n]))
        life.sort()
        k = len(life) // 3
        terc = [life[:k], life[k:2 * k], life[2 * k:]]
        out[s] = {"proxy_reconstructed": cell["reconstructed"], "proxy_missing": cell["missing"],
                  "i07_by_lifetime_tercile": [float(np.mean([b for _, b in g])) for g in terc],
                  "lifetime_tercile_bounds_days": [terc[0][-1][0], terc[1][-1][0]]}
        rows.append([lab, f"{pct(cell['reconstructed'][0] / cell['reconstructed'][1])} ({cell['reconstructed'][1]:,})",
                     f"{pct(cell['missing'][0] / cell['missing'][1])} ({cell['missing'][1]:,})" if cell["missing"][1] else "–"]
                    + [pct(x) for x in out[s]["i07_by_lifetime_tercile"]])
    NUMBERS["filetype"] = out
    table("t_filetype", "Source-only distribution of malicious packages from the download log, by year of the first download",
          ["Period", "No built distribution downloaded: reconstructed, % (n)", "Not reconstructed, % (n)",
           "I-07, shortest-lived third (%)", "I-07, middle third (%)", "I-07, longest-lived third (%)"], rows)
    return out


def a_dependents(per):
    """R5 (round 2): malicious packages that other projects declare as a dependency.

    A malicious package that is a dependency of an established, unreported
    project can be pulled in transitively, which pipguard does not check. We
    bound pipguard-as-implemented by counting such packages' downloads as not
    stopped (worst case); the policy figure is the best case.
    """
    path = RAW / "malicious_dependents.jsonl.gz"
    if not path.exists():
        return None
    osv = set(OSV)
    deps = defaultdict(list)
    for r in jsonl(path):
        deps[r["dep"]].append(r)
    risky = set()
    any_dep, mal_only = set(), set()
    for n, rs in deps.items():
        if n not in META_FIRST:
            continue
        any_dep.add(n)
        fm = first_malicious(n)
        benign = [r for r in rs if r["dependent"] not in osv]
        if not benign:
            mal_only.add(n)
        for r in benign:
            if (fm - t(r["first_uploaded"])).days >= 30:
                risky.add(n)
    names = sorted(n for n in per if n in META_FIRST)
    P = policies()
    out = {"with_dependents": len(any_dep), "only_malicious_dependents": len(mal_only),
           "established_unreported_dependent": len(risky)}
    for sub in ("all", "test"):
        ns = [n for n in names if sub == "all" or META_FIRST[n]["split"] == "test"]
        num, den = pkg_stopped(per, P["project"](30), ns)
        num_w = np.array([0.0 if n in risky else x for n, x in zip(ns, num)])
        keep = den > 0
        out[sub] = {"risky_packages": sum(1 for n in ns if n in risky),
                    "risky_download_share": float(den[[n in risky for n in ns]].sum() / den.sum()),
                    "policy_per_package": float((num[keep] / den[keep]).mean()),
                    "implemented_worst_per_package": float((num_w[keep] / den[keep]).mean()),
                    "policy_pooled": float(num.sum() / den.sum()), "implemented_worst_pooled": float(num_w.sum() / den.sum())}
    NUMBERS["dependents"] = out
    return out


def a_cases():
    """R7 (round 2): high-impact incidents, how each policy would have treated the malicious versions."""
    vp, dp = RAW / "case_versions.jsonl.gz", RAW / "case_downloads.jsonl.gz"
    if not (vp.exists() and dp.exists()):
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_v3 import CASES
    vers = defaultdict(list)
    proxy = set()
    for r in jsonl(vp):
        vers[r["norm_name"]].append((t(r["uploaded"]), r["version"]))
        if r.get("proxy"):
            proxy.add(r["norm_name"])
    dl = defaultdict(list)
    for r in jsonl(dp):
        dl[(r["project"], r["version"])].append((datetime.fromisoformat(r["day"]).date(), int(r["client"])))
    rows, out = [], {}
    for n, mv in CASES.items():
        if n not in vers:
            continue
        vs = sorted(vers[n])
        mal = [(u, v) for u, v in vs if v in mv] if mv else vs
        if not mal:
            continue
        m0 = min(u for u, _ in mal)
        prev = [u for u, v in vs if u < m0 and (v not in mv if mv else False)]
        start = vs[0][0].date()
        if n in proxy and not prev and n in PRESENCE:
            # no metadata at all: the project's first download day stands in for its first upload
            start = datetime.fromisoformat(PRESENCE[n]["first_date"]).date()
        age = (m0.date() - start).days
        gap = (m0 - prev[-1]).total_seconds() / 86400 if prev else None
        tot = s_rel1 = s_rel30 = s_proj = 0
        last = 0
        for u, v in mal:
            for day, c in dl.get((n, v), []):
                a_ = (day - u.date()).days
                tot += c
                s_rel1 += c if a_ < 1 else 0
                s_rel30 += c if a_ < 30 else 0
                s_proj += c if (day - start).days < 30 else 0
                if c > 0:
                    last = max(last, a_)
        i10 = age >= 30 and gap is not None and gap >= 90
        o = {"malicious_versions": len(mal), "first_malicious": fmt_date(m0), "project_age_days": age,
             "gap_days": gap, "client_downloads": tot, "last_client_download_day": last,
             "stopped_project30": s_proj / tot if tot else None, "stopped_release1": s_rel1 / tot if tot else None,
             "stopped_release30": s_rel30 / tot if tot else None, "i10_90_fires": i10}
        out[n] = o
        def sh(x):
            return "–" if x is None else f"{pct(x)}"
        o["upload_proxy"] = n in proxy
        rows.append([n, ("≈ " if n in proxy else "") + o["first_malicious"], o["malicious_versions"], f"{age:,}",
                     "–" if gap is None else f"{gap:.0f}", f"{tot:,}", last,
                     sh(o["stopped_project30"]), sh(o["stopped_release1"]), sh(o["stopped_release30"]),
                     "yes" if i10 else "no"])
    NUMBERS["cases"] = out
    table("t_cases", "High-impact PyPI incidents and the cooldown policies",
          ["Project", "First malicious upload", "Malicious versions", "Project age (days)",
           "Days since previous release", "Client downloads of malicious versions", "Last day with a client download",
           "Stopped: project 30 d (%)", "Stopped: release 1 d (%)", "Stopped: release 30 d (%)", "I-10 (G = 90 d) fires"],
          rows)
    return out


def fmt_date(dt):
    return dt.date().isoformat()


def load_background():
    """Client downloads of new legitimate projects by age bucket (days since the first upload)."""
    path = RAW / "benign_new_downloads.jsonl.gz"
    if not path.exists():
        return None
    split = {r["name"]: r["split"] for r in jsonl(FROZEN / "meta_benign_new_first.jsonl")}
    first = {r["name"]: t(r["as_of"]).date() for r in jsonl(FROZEN / "meta_benign_new_first.jsonl")}
    rows = {r["project"]: r for r in jsonl(path)}
    end = datetime(2026, 10, 19).date()
    edge = {b: b + 1 for b in range(15)}
    edge.update({15: 21, 21: 30, 30: 60, 60: 90, 90: 180, 180: 365, 365: 10 ** 6})
    per = {}
    for n, s in split.items():
        r = rows.get(n)
        d = {int(b): (int(c), int(tt)) for b, c, tt in zip(r["buckets"], r["client"], r["total"])} if r else {}
        age = (end - first[n]).days
        # only buckets that the project has completely lived through
        per[n] = {b: d.get(b, (0, 0)) for b in BUCKETS if edge[b] <= age}
    return per, split


def a_background(per):
    """R2 (round 2): automated download background of new uploads, and malicious downloads in excess of it."""
    bg = load_background()
    if bg is None:
        return None
    legit, lsplit = bg
    out = {"legit_packages": len(legit)}
    prof = {}
    for s in ("dev", "val", "test"):
        ns = [n for n in legit if lsplit[n] == s]
        prof[s] = {}
        for b in BUCKETS:
            v = [legit[n][b][0] for n in ns if b in legit[n]]
            if len(v) >= 30:
                prof[s][b] = {"median": float(np.median(v)), "p25": float(np.percentile(v, 25)),
                              "p75": float(np.percentile(v, 75)), "n": len(v)}
        # how concentrated are LEGITIMATE downloads on day 0 (first 30 days)?
        d0 = []
        for n in ns:
            first30 = sum(legit[n][b][0] for b in BUCKETS if b < 30 and b in legit[n])
            if first30 > 0 and 21 in legit[n]:
                d0.append(legit[n][0][0] / first30)
        out[f"legit_day0_share_first30_{s}"] = {"mean": float(np.mean(d0)), "median": float(np.median(d0)),
                                                 "n": len(d0)}
    out["profile"] = {s: {str(b): v for b, v in p.items()} for s, p in prof.items()}
    # malicious downloads in excess of the background of their period
    names = sorted(n for n in per if n in META_FIRST)
    for stat in ("median", "p25"):
        excess = {}
        for n in names:
            p = prof[META_FIRST[n]["split"]]
            excess[n] = {b: max(0.0, v[0] - p[b][stat]) if b in p else float(v[0]) for b, v in per[n].items()}
        tag = f"_excess_{stat}"
        NUMBERS.setdefault("background", {})
        res = a_exposure_estimators(per, counts=excess, tag=tag)
        tot = {n: sum(excess[n].values()) for n in names}
        raw = {n: sum(v[0] for v in per[n].values()) for n in names}
        with_ex = [n for n in names if tot[n] > 0]
        day0 = [excess[n].get(0, 0.0) / tot[n] for n in with_ex]
        raw_pos = [n for n in names if raw[n] > 0]
        out[stat] = {"packages_with_excess": len(with_ex), "packages_with_client_downloads": len(raw_pos),
                     "excess_share_of_client_downloads": float(sum(tot.values()) / sum(raw.values())),
                     "day0_share_mean_pkg": float(np.mean(day0)),
                     "by_split_with_excess": {s: [sum(1 for n in with_ex if META_FIRST[n]["split"] == s),
                                                  sum(1 for n in raw_pos if META_FIRST[n]["split"] == s)]
                                              for s in ("dev", "val", "test")}}
    raw_day0 = [per[n].get(0, (0, 0))[0] / sum(v[0] for v in per[n].values()) for n in names
                if sum(v[0] for v in per[n].values()) > 0]
    out["malicious_day0_share_mean_pkg"] = float(np.mean(raw_day0))
    NUMBERS["background"] = out
    return out


def _shares(runs, num, den):
    v = sorted(r[num] / r[den] for r in runs)
    return {"median": v[len(v) // 2], "min": v[0], "max": v[-1]}


def a_cost():
    """Share of downloads whose outcome a cooldown changes (test window and validation window)."""
    out = {}
    for tag, fn, dfn in (("", "cooldown_cost.json", "dormancy_cost.json"),
                         ("_val", "cooldown_cost_val.json", "dormancy_cost_val.json")):
        d = json.load(open(FROZEN / fn))
        out["window" + tag] = d["window"]
        for key, num, den in (("project", "p", "total"), ("release", "r", "total"),
                              ("project_client", "pc", "total_client"), ("release_client", "rc", "total_client")):
            out[key + tag] = {T: _shares(d["runs"], f"{num}{T}", den) for T in d["thresholds_days"]}
        if (FROZEN / dfn).exists():
            dc = json.load(open(FROZEN / dfn))
            out["dormancy_client" + tag] = {G: _shares(dc["runs"], f"dc{G}", "total_client") for G in dc["dormancy_days"]}
    NUMBERS["cost"] = out
    return out


def _summary(v):
    v = np.asarray(v, float)
    return {"median": float(np.median(v)), "q1": float(np.percentile(v, 25)), "q3": float(np.percentile(v, 75)),
            "min": float(v.min()), "max": float(v.max()), "n": int(len(v))}


def a_cost_complete():
    """R3 (round 2): complete monthly costs (every query verified complete; fetch_v3 cost-complete).

    Replaces the round-1 cost, whose date-filtered queries were silently
    truncated by the mirror's read limit (kept as cost_round1_truncated).
    Design decisions keep using June 2025, the month fixed in advance.
    """
    path = FROZEN / "cost_complete.json"
    if not path.exists():
        return None
    d = json.load(open(path))
    months = defaultdict(Counter)
    for ch in d["chunks"].values():
        for mo, r in ch["months"].items():
            months[mo].update(r)
    ms = sorted(months)
    ts, gs = d["thresholds_days"], d["dormancy_days"]
    per_month = {}
    for mo in ms:
        r = months[mo]
        per_month[mo] = {"total": r["total"], "total_client": r["total_client"],
                         "project_client": {T: r[f"pc{T}"] / r["total_client"] for T in ts},
                         "release_client": {T: r[f"rc{T}"] / r["total_client"] for T in ts},
                         "project": {T: r[f"p{T}"] / r["total"] for T in ts},
                         "release": {T: r[f"r{T}"] / r["total"] for T in ts},
                         "dormancy_client": {G: r[f"dc{G}"] / r["total_client"] for G in gs},
                         "ratio": {T: r[f"rc{T}"] / r[f"pc{T}"] if r[f"pc{T}"] else None for T in ts},
                         "before_first_upload": r.get("pc_before_first", 0) / r["total_client"],
                         "no_project_metadata": r.get("cc_no_project_metadata", 0) / r["total_client"],
                         "project30_upper": (r["pc30"] + r.get("pc_before_first", 0)) / r["total_client"]}
    NUMBERS["cost_round1_truncated"] = NUMBERS.get("cost")
    cost = {"window": [ms[0], ms[-1]], "months": len(ms)}
    for key in ("project_client", "release_client", "project", "release"):
        cost[key] = {T: _summary([per_month[m][key][T] for m in ms]) for T in ts}
    cost["ratio"] = {T: _summary([per_month[m]["ratio"][T] for m in ms if per_month[m]["ratio"][T]]) for T in ts}
    cost["dormancy_client"] = {G: _summary([per_month[m]["dormancy_client"][G] for m in ms]) for G in gs}
    cost["dormancy_ratio"] = {G: _summary([per_month[m]["dormancy_client"][G] / per_month[m]["project_client"][30]
                                           for m in ms]) for G in gs}
    val, test = "2025-06", "2026-06"
    for tag, mo in (("_val", val), ("_june2026", test)):
        if mo in per_month:
            for key in ("project_client", "release_client", "dormancy_client"):
                cost[key + tag] = {k: {"median": v} for k, v in per_month[mo][key].items()}
    cost["per_month"] = per_month
    for key in ("before_first_upload", "no_project_metadata", "project30_upper"):
        cost[key] = _summary([per_month[m][key] for m in ms])
    cost["client_share_of_downloads"] = _summary([per_month[m]["total_client"] / per_month[m]["total"] for m in ms])
    cost["rows_read_max"] = max(ch["rows_read"] for ch in d["chunks"].values())
    cost["chunks"] = len(d["chunks"])
    NUMBERS["cost"] = cost
    return cost


def a_dependency_additions():
    """R3 (round 2): share of dependency additions whose target project is younger than T days."""
    path = FROZEN / "dependency_additions.json"
    if not path.exists():
        return None
    d = json.load(open(path))
    tot = Counter()
    by_month = defaultdict(Counter)
    for r in d["rows"]:
        for k in ("edges", "target_unknown", "target_registered_later", "age_lt1", "age_lt7", "age_lt30", "age_lt90"):
            tot[(r["first_release"], k)] += r[k]
            tot[("all", k)] += r[k]
            by_month[r["month"]][k] += r[k]
    out = {"window": d["window"]}
    for grp in ("all", 0, 1):
        e = tot[(grp, "edges")]
        known = e - tot[(grp, "target_unknown")] - tot[(grp, "target_registered_later")]
        out[{"all": "all", 0: "later_releases", 1: "first_releases"}[grp]] = {
            "edges": e, "unknown_target": tot[(grp, "target_unknown")],
            "target_registered_later": tot[(grp, "target_registered_later")],
            **{f"lt{T}": tot[(grp, f"age_lt{T}")] / known for T in (1, 7, 30, 90)}}
    out["lt30_by_month"] = _summary([v["age_lt30"] / (v["edges"] - v["target_unknown"] - v["target_registered_later"])
                                     for v in by_month.values()])
    NUMBERS["dependency_additions"] = out
    return out


def i10(r, G):
    """I-10 at dormancy G, simulated from the per-package columns written by evalset."""
    try:
        return (float(r["project_age_days"]) >= 30 and float(r["release_age_days"]) < 30
                and r["prev_gap_days"] != "" and float(r["prev_gap_days"]) >= G)
    except ValueError:
        return False


def add_i10_columns(rows):
    for r in rows:
        for G in (30, 60, 90, 180, 365):
            r[f"flagged_i10only-{G}"] = "1" if i10(r, G) else "0"
            r[f"flagged_i10-{G}"] = "1" if (r["flagged_pipguard-v2"] == "1" or i10(r, G)) else "0"


def a_detection(first, last, reported):
    """Main results on the 2026 test data, with Wilson and campaign-bootstrap intervals."""
    dets = [("pipguard-v2", "pipguard (final design)"), ("pipguard-v2-danger", "  DANGER level only"),
            ("i10-90", "  with I-10, G = 90 d (opt-in)"), ("i10-365", "  with I-10, G = 365 d (opt-in)"),
            ("pipguard-v1", "Initial design (iteration 1)"), ("v2-initial", "Early calibration (rejected)"),
            ("new-or-missing", "Project-level cooldown, 30 d"), ("release-cooldown-30", "Release-level cooldown, 30 d"),
            ("registry-only", "Existence check only"), ("similarity-v2", "Name similarity only")]
    groups = [("mal", "Malicious (n = {n})"), ("benign-new", "New legitimate (n = {n})"),
              ("negative_established", "Established (n = {n})")]
    rows, nums = [], {}
    sel = {"mal": [r for r in first if r["group"] in MAL and r["split"] == "test"],
           "benign-new": [r for r in first if r["group"] == "benign-new" and r["split"] == "test"],
           "negative_established": [r for r in first if r["group"] == "negative_established" and r["split"] == "test"]}
    header = ["Detector"] + [g[1].format(n=len(sel[g[0]])) for g in groups] + ["Malicious, campaign bootstrap"]
    for d, lab in dets:
        row = [lab]
        nums[d] = {}
        for g, _ in groups:
            rs = sel[g]
            k = sum(r[f"flagged_{d}"] == "1" for r in rs)
            row.append(rate_ci(k, len(rs)) if g == "mal" or k else rate_ci(k, len(rs), 2))
            nums[d][g] = [k, len(rs)]
        vals = [float(r[f"flagged_{d}"] == "1") for r in sel["mal"]]
        lo, hi = cluster_boot(vals, [CAMP[r["name"]] for r in sel["mal"]])
        row.append(f"[{pct(lo)}–{pct(hi)}]")
        nums[d]["mal_cluster_ci"] = [lo, hi]
        rows.append(row)
    table("t_detection", "Detection results on the 2026 test data, % [95% interval]", header, rows,
          "Flagged = installation requires confirmation (or, for the release-level cooldown, the newest release is "
          "withheld). Wilson intervals treat packages as independent; the last column resamples campaigns.")
    # campaign-level recall: share of test campaigns with every / at least one package flagged
    camp = defaultdict(list)
    for r in sel["mal"]:
        camp[CAMP[r["name"]]].append(r["flagged_pipguard-v2"] == "1")
    nums["campaigns_test"] = {"n": len(camp), "all_flagged": sum(all(v) for v in camp.values()),
                              "any_flagged": sum(any(v) for v in camp.values()),
                              "mean_within": float(np.mean([np.mean(v) for v in camp.values()])),
                              "largest": max(len(v) for v in camp.values())}
    camp2 = defaultdict(list)
    for r in sel["mal"]:
        camp2[CAMP[r["name"]]].append(r["flagged_pipguard-v2"] == "1")
    nums["campaigns_test_v2_mean_within"] = float(np.mean([np.mean(v) for v in camp2.values()]))
    # McNemar v3 vs v2 on malicious and established
    for g in ("mal", "negative_established", "benign-new"):
        b = sum(r["flagged_pipguard-v2"] == "1" and r["flagged_pipguard-v2"] != "1" for r in sel[g])
        c = sum(r["flagged_pipguard-v2"] != "1" and r["flagged_pipguard-v2"] == "1" for r in sel[g])
        nums[f"mcnemar_v3_v2_{g}"] = {"v3_only": b, "v2_only": c, "p": mcnemar_exact(b, c)}
    b = sum(r["flagged_pipguard-v1"] == "1" and r["flagged_pipguard-v2"] != "1" for r in sel["negative_established"])
    c = sum(r["flagged_pipguard-v1"] != "1" and r["flagged_pipguard-v2"] == "1" for r in sel["negative_established"])
    nums["mcnemar_v1_v3_established"] = {"v1_only": b, "v3_only": c, "p": mcnemar_exact(b, c)}
    # top-1000 (development) for completeness
    top = [r for r in first if r["group"] == "negative_top1000"]
    nums["top1000"] = {d: [sum(r[f"flagged_{d}"] == "1" for r in top), len(top)] for d, _ in dets}
    # scenarios
    srows = []
    for scen, rs in (("First malicious release (primary)", first), ("Last release", last), ("At OSV report", reported)):
        m = [r for r in rs if r["group"] in MAL and r["split"] == "test"]
        bn = [r for r in rs if r["group"] == "benign-new" and r["split"] == "test"]
        k = sum(r["flagged_pipguard-v2"] == "1" for r in m)
        kd = sum(r["flagged_pipguard-v2-danger"] == "1" for r in m)
        row = [scen, f"{pct(k / len(m))} ({k}/{len(m)})", f"{pct(kd / len(m))} ({kd}/{len(m)})"]
        if bn:
            kb = sum(r["flagged_pipguard-v2"] == "1" for r in bn)
            kbd = sum(r["flagged_pipguard-v2-danger"] == "1" for r in bn)
            row += [f"{pct(kb / len(bn))} ({kb}/{len(bn)})", f"{pct(kbd / len(bn))} ({kbd}/{len(bn)})"]
        else:
            row += ["–", "–"]
        srows.append(row)
    table("t_scenarios", "pipguard under each installation-time scenario (test data)",
          ["Scenario", "Malicious flagged", "Malicious at DANGER", "New legitimate flagged", "New legitimate at DANGER"],
          srows)
    NUMBERS["detection"] = nums
    return sel


def a_misses(first):
    """Malicious releases in projects already >= 30 days old: what project-level age cannot see."""
    by = defaultdict(lambda: [0, 0, 0, 0, 0])
    for r in first:
        if r["group"] not in MAL:
            continue
        n = r["name"]
        y = first_malicious(n).year
        key = str(y) if y >= 2021 else "≤ 2020"
        a0 = project_age_at_attack(n)
        by[key][0] += 1
        if a0 >= 30:
            by[key][1] += 1
            by[key][2] += r["flagged_i10only-90"] == "1"
            by[key][3] += r["flagged_i10only-365"] == "1"
            by[key][4] += r["flagged_release-cooldown-30"] == "1"
    rows = []
    for k in sorted(by, key=lambda x: (x != "≤ 2020", x)):
        tot, old, g90, g365, rel = by[k]
        rows.append([k, tot, old, pct(old / tot), g90, g365, rel])
    table("t_preaged", "Malicious releases in projects that were already at least 30 days old",
          ["Year of the first malicious upload", "Malicious packages", "In projects ≥ 30 d old", "Share (%)",
           "Caught by I-10, G = 90 d", "Caught by I-10, G = 365 d", "Withheld by a 30-day release-level cooldown"], rows)
    NUMBERS["preaged_by_year"] = {k: v for k, v in by.items()}
    gaps = defaultdict(list)
    for r in first:
        if r["group"] in MAL and project_age_at_attack(r["name"]) >= 30:
            g = prev_gap(r["name"])
            gaps[r["split"]].append(g if g is not None else -1)
    NUMBERS["preaged_gaps"] = {s_: sorted(v) for s_, v in gaps.items()}
    test_old = [r for r in first if r["group"] in MAL and r["split"] == "test" and project_age_at_attack(r["name"]) >= 30]
    NUMBERS["test_misses"] = {"n": len(test_old),
                              "project_age_days_min": min(project_age_at_attack(r["name"]) for r in test_old),
                              "project_age_days_max": max(project_age_at_attack(r["name"]) for r in test_old),
                              "gap_ge_30": sum(1 for r in test_old if (prev_gap(r["name"]) or 0) >= 30),
                              "gap_lt_7": sum(1 for r in test_old if (prev_gap(r["name"]) or 0) < 7)}


def a_dormancy_choice(first, last):
    """Choose the I-10 dormancy period on development + validation data only.

    Benefit: share of old-project malicious releases (dev + val) that I-10 catches.
    Cost: share of established development packages (live snapshot) and of
    install-client downloads (validation-period window) that I-10 would prompt.
    Rule fixed in advance: the smallest dormancy period whose download cost does
    not exceed the cost of the 30-day project-level cooldown.
    """
    cands = [30, 60, 90, 180, 365]
    old = [r for r in first if r["group"] in MAL and r["split"] in ("dev", "val")
           and project_age_at_attack(r["name"]) >= 30]
    est_dev = [r for r in first if r["group"] in ("negative_established", "negative_top1000") and r["split"] == "dev"]
    cost = NUMBERS["cost"]
    dc = cost.get("dormancy_client_val", {})
    proj = cost["project_client_val"][30]["median"]
    rows, choice = [], None
    for G in cands:
        caught = sum(1 for r in old if prev_gap(r["name"]) is not None and prev_gap(r["name"]) >= G)
        est = sum(1 for r in est_dev if r["prev_gap_days"] and r["release_age_days"]
                  and float(r["release_age_days"]) < 30 and float(r["prev_gap_days"]) >= G
                  and float(r["project_age_days"]) >= 30)
        c = dc[G]["median"] if G in dc else None
        rows.append([G, f"{caught}/{len(old)} ({pct(caught / len(old))})", f"{est}/{len(est_dev)} ({pct(est / len(est_dev), 2)})",
                     pct(c, 3) if c is not None else "–"])
        if choice is None and c is not None and proj is not None and c <= proj:
            choice = G
    table("t_dormancy", "Choice of the I-10 dormancy period on development and validation data",
          ["Dormancy period G (days)", "Old-project malicious releases caught (dev + val)",
           "Established dev packages prompted (snapshot)", "Install-client downloads prompted (%)"], rows,
          "Decision rule fixed before the test data were scored: the smallest G whose download share does not "
          "exceed that of the 30-day project-level cooldown.")
    NUMBERS["dormancy_choice"] = {"candidates": cands, "chosen": choice or 0, "project30_cost_val": proj,
                                  "dormancy_cost_val": {G: dc[G]["median"] for G in dc}}
    (DATA / "dormancy_choice.json").write_text(json.dumps(NUMBERS["dormancy_choice"], indent=2) + "\n")
    return choice


def a_drift(first):
    rules = ["I-02", "I-04", "I-05", "I-07", "I-08", "I-09"]
    rows = []
    for grp, lab in ((MAL, "Malicious"), (("benign-new",), "New legitimate")):
        for s, sl in (("dev", "< 2025"), ("val", "2025"), ("test", "2026")):
            rs = [r for r in first if r["group"] in grp and r["split"] == s]
            rows.append([lab, sl, len(rs)] + [pct(np.mean([r[f"sig_{x}"] == "1" for r in rs])) for x in rules])
    table("t_drift", "Percentage of packages for which each indicator fired, by period",
          ["Group", "Period", "n"] + rules, rows)
    # campaign-weighted prevalence (each campaign counts once)
    cw = {}
    for s in ("dev", "val", "test"):
        rs = [r for r in first if r["group"] in MAL and r["split"] == s]
        per = defaultdict(list)
        for r in rs:
            per[CAMP[r["name"]]].append(r)
        cw[s] = {x: float(np.mean([np.mean([r[f"sig_{x}"] == "1" for r in v]) for v in per.values()])) for x in rules}
        cw[s]["campaigns"] = len(per)
    NUMBERS["drift_campaign_weighted"] = cw


def a_campaign_summary(first):
    per = defaultdict(lambda: defaultdict(int))
    for r in first:
        if r["group"] in MAL:
            per[r["split"]][CAMP[r["name"]]] += 1
    out = {}
    for s, c in per.items():
        sizes = sorted(c.values(), reverse=True)
        out[s] = {"packages": sum(sizes), "campaigns": len(sizes), "largest": sizes[0],
                  "singletons": sum(1 for x in sizes if x == 1), "top3": sizes[:3]}
    NUMBERS["campaigns"] = out
    rows = [[s, o["packages"], o["campaigns"], o["singletons"], o["largest"], pct(o["largest"] / o["packages"])]
            for s, o in sorted(out.items(), key=lambda kv: ["dev", "val", "test"].index(kv[0]))]
    table("t_campaigns", "Malicious packages grouped into campaigns",
          ["Split", "Packages", "Campaigns", "Single-package campaigns", "Largest campaign", "Largest share (%)"], rows)


def a_early_model_validation(first):
    """R2: the rejected model's validation-period numbers, which alone justify rejecting it."""
    out = {}
    for s in ("dev", "val", "test"):
        m = [r for r in first if r["group"] in MAL and r["split"] == s]
        b = [r for r in first if r["group"] == "benign-new" and r["split"] == s]
        out[s] = {}
        for d in ("v2-initial", "new-or-missing"):
            out[s][d] = {"recall": [sum(r[f"flagged_{d}"] == "1" for r in m), len(m)],
                         "fpr_new": [sum(r[f"flagged_{d}"] == "1" for r in b), len(b)]}
    NUMBERS["early_model"] = out


def a_recalibration(first):
    """R5: re-fit the rejected early model with the 2023 mass campaign removed or down-weighted.

    Same procedure as fit_weights.py --method initial (dev data, logistic
    regression, points = round(10 beta), WARNING = Youden-optimal threshold), with
    the early model's I-05 configuration. Shows whether the early model's
    collapse is an artefact of one campaign or of drift in general.
    """
    import fit_weights as fw
    grid = list(csv.DictReader(open(DATA / "sim_grid.csv")))
    ok = [r for r in first if not r["error"]]
    assert len(ok) == len(grid)
    cfg = {"list": "top-2000", "min_len": 4, "max_dist": 1, "transpositions": False}
    i05 = fw.similarity_column(grid, cfg)
    feats = fw.FEATURES
    sizes = Counter(CAMP[r["name"]] for r in ok if r["group"] in MAL and r["split"] == "dev")
    biggest = sizes.most_common(1)[0][0]

    def arrays(rows, idx):
        X = np.array([[i05[i] if f == "I-05" else float(r["sig_" + f]) for f in feats] for i, r in zip(idx, rows)])
        y = np.array([1.0 if r["group"] in MAL else 0.0 for r in rows])
        g = [r["group"] if r["group"] != "negative_top1000" else "negative_established" for r in rows]
        return X, y, [x if x in fw.NEW_NEG | fw.EST_NEG else "malicious-other" for x in g]

    out = {}
    for variant in ("all", "without_largest", "campaign_weighted"):
        idx = [i for i, r in enumerate(ok) if r["split"] == "dev" and r["group"] in MAL + ("benign-new", "negative_established", "negative_top1000")
               and not (variant == "without_largest" and r["group"] in MAL and CAMP[r["name"]] == biggest)]
        rows = [ok[i] for i in idx]
        X, y, groups = arrays(rows, idx)
        w = fw.sample_weights(groups, y)
        if variant == "campaign_weighted":
            pos = np.where(y == 1)[0]
            cw = np.array([1.0 / sizes[CAMP[rows[i]["name"]]] for i in pos])
            w[pos] = w[pos].sum() * cw / cw.sum()
        _, beta, _ = fw.fit_nonneg(X, y, w)
        pts = np.array([int(round(10 * b)) for b in beta])
        score = X @ pts
        best = max(range(1, int(score.max()) + 2),
                   key=lambda t: fw.balanced_rates(score, y, groups, t)[0] - fw.balanced_rates(score, y, groups, t)[3])
        res = {"points": dict(zip(feats, map(int, pts))), "warn": best}
        for split in ("val", "test"):
            sidx = [i for i, r in enumerate(ok) if r["split"] == split and r["group"] in MAL + ("benign-new",)]
            Xs, ys, _ = arrays([ok[i] for i in sidx], sidx)
            sc = Xs @ pts
            res[split] = {"recall": float(np.mean(sc[ys == 1] >= best)), "fpr_new": float(np.mean(sc[ys == 0] >= best))}
        out[variant] = res
    out["largest_campaign_size"] = sizes[biggest]
    NUMBERS["recalibration"] = out
    rows = [[{"all": "All development data (as rejected)", "without_largest": "Without the largest campaign",
              "campaign_weighted": "Each campaign weighted equally"}[v],
             ", ".join(f"{k} {p}" for k, p in out[v]["points"].items() if p), out[v]["warn"],
             pct(out[v]["val"]["recall"]), pct(out[v]["test"]["recall"]), pct(out[v]["test"]["fpr_new"])]
            for v in ("all", "without_largest", "campaign_weighted")]
    table("t_recalibration", "Re-fitting the early model on development data without the 2023 mass campaign",
          ["Development data", "Points", "WARNING threshold", "Recall 2025 (%)", "Recall 2026 (%)",
           "FPR new legitimate 2026 (%)"], rows)


def a_severity(first):
    """DANGER level: AUC, reliability by score, and positive predictive value at realistic base rates."""
    out = {}
    for s in ("val", "test"):
        m = [r for r in first if r["group"] in MAL and r["split"] == s and r["sig_I-02"] == "1"]
        b = [r for r in first if r["group"] == "benign-new" and r["split"] == s and r["sig_I-02"] == "1"]
        a = auc([float(r["v2_score"]) for r in m], [float(r["v2_score"]) for r in b])
        a1 = auc([float(r["v1_score"]) for r in m], [float(r["v1_score"]) for r in b])
        rng = np.random.default_rng(SEED)
        ms, bs = np.array([float(r["v2_score"]) for r in m]), np.array([float(r["v2_score"]) for r in b])
        boots = [auc(rng.choice(ms, len(ms)), rng.choice(bs, len(bs))) for _ in range(500)]
        tpr = np.mean([r["flagged_pipguard-v2-danger"] == "1" for r in m])
        fpr = np.mean([r["flagged_pipguard-v2-danger"] == "1" for r in b])
        out[s] = {"auc_final": a, "auc_final_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                  "auc_v1": a1, "danger_tpr": float(tpr), "danger_fpr": float(fpr), "lr_plus": float(tpr / fpr)}
        out[s]["ppv_at_prior"] = {str(p): float(tpr * p / (tpr * p + fpr * (1 - p))) for p in (0.01, 0.05, 0.1)}
    NUMBERS["severity"] = out


def a_prospective():
    """R2: packages reported after the design was frozen, scored once with the frozen model."""
    path = FROZEN / "prospective_osv.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(open(path)))
    res = {}
    if (DATA / "results_prospective.csv").exists():
        for r in csv.DictReader(open(DATA / "results_prospective.csv")):
            res[r["name"]] = r
    n_young = n_old = 0
    for r in rows:
        pres = PRESENCE.get(r["name"])
        if not pres:
            continue
        age = (t(r["published"]).date() - datetime.fromisoformat(pres["first_date"]).date()).days
        n_young += age < 30
        n_old += age >= 30
    flagged = sum(v["flagged_pipguard-v2"] == "1" for v in res.values())
    NUMBERS["prospective"] = {"osv_names": len(rows), "with_download_log": n_young + n_old,
                              "first_download_lt30d_before_report": n_young, "older": n_old,
                              "with_metadata": len(res), "v3_flagged_with_metadata": flagged}


# ================================================================= figures

def f_drift(first):
    rules = [("I-02", "I-02 age < 30 d", "-", "o"), ("I-07", "I-07 sdist only", "--", "s"),
             ("I-04", "I-04 no links", ":", "^"), ("I-08", "I-08 short README", "-.", "D")]
    halves = sorted({half(first_malicious(r["name"])) for r in first if r["group"] in MAL})
    halves = [h for h in halves if h >= "2022 H2"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
    for code, lab, ls, mk in rules:
        ys = []
        for h in halves:
            rs = [r for r in first if r["group"] in MAL and half(first_malicious(r["name"])) == h]
            ys.append(100 * np.mean([r[f"sig_{code}"] == "1" for r in rs]))
        axes[0].plot(range(len(halves)), ys, ls=ls, marker=mk, color=K, mfc="white", label=lab)
    axes[0].set_ylabel("Malicious packages (%)")
    axes[0].set_title("(a) Indicator prevalence")
    for code, lab, ls, mk in (("pipguard-v2", "pipguard (final design)", "-", "o"), ("v2-initial", "Early calibration (rejected)", "--", "s"),
                              ("pipguard-v2-danger", "DANGER level", ":", "^")):
        ys = []
        for h in halves:
            rs = [r for r in first if r["group"] in MAL and half(first_malicious(r["name"])) == h]
            ys.append(100 * np.mean([r[f"flagged_{code}"] == "1" for r in rs]))
        axes[1].plot(range(len(halves)), ys, ls=ls, marker=mk, color=K, mfc="white", label=lab)
    axes[1].set_ylabel("Recall (%)")
    axes[1].set_title("(b) Recall by half-year")
    for ax in axes:
        ax.set_xticks(range(len(halves)))
        ax.set_xticklabels([h.replace(" ", "\n") for h in halves])
        ax.set_ylim(0, 105)
        for b in ("2025 H1", "2026 H1"):
            if b in halves:
                ax.axvline(halves.index(b) - 0.5, color=G2, lw=0.8, ls="--")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    fig.tight_layout()
    save(fig, "fig_drift")


def f_timing(rep, gone, split, per):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6))
    ax = axes[0]
    xs = np.logspace(-2, 3, 300)
    for arr, lab, ls in ((rep, "OSV report", "-"), (gone[~np.isnan(gone)], "Last install-client download", "--")):
        arr = np.sort(arr)
        ax.plot(xs, [np.mean(arr <= x) * 100 for x in xs], ls=ls, color=K, label=lab)
    ax.set_xscale("log")
    ax.set_xlabel("Days after the first malicious upload")
    ax.set_ylabel("Malicious packages (%)")
    ax.set_title("(a) Time to report and to removal")
    for d in (2, 7, 30):
        ax.axvline(d, color=G3, lw=0.7, zorder=0)
    ax.legend(loc="upper left")
    tradeoff_axes(axes[1])
    axes[1].set_title("(b) Residual exposure versus cost")
    fig.tight_layout()
    save(fig, "fig_exposure")


def tradeoff_axes(ax):
    cost = NUMBERS["cost"]
    ex = NUMBERS["exposure"]["by_policy"]
    for pol, ckey, lab, ls, mk in (("project", "project_client", "Project-level (pipguard)", "-", "o"),
                                   ("release", "release_client", "Release-level (pip, uv, pnpm)", "--", "s")):
        xs = [100 * cost[ckey][T]["median"] for T in THRESHOLDS]
        est = NUMBERS["exposure_estimators"]["by_shift"]["shift0"][pol]
        ys = [100 - 100 * est[str(T)]["test"]["per_package"]["est"] for T in THRESHOLDS]
        ax.plot(xs, ys, ls=ls, marker=mk, color=K, mfc="white", label=lab)
        for T, x, y in zip(THRESHOLDS, xs, ys):
            if T in (1, 2, 7, 30, 90):
                ax.annotate(f"{T} d", (x, y), textcoords="offset points", xytext=(3, 3), fontsize=6.5)
    ax.set_xscale("log")
    ax.set_xlabel("Install-client downloads affected (%)")
    ax.set_ylabel("Residual exposure, 2026,\nmean per package (%)")
    ax.legend(loc="upper right")


def f_levels(sel):
    groups = [("mal", "Malicious"), ("benign-new", "New legitimate"), ("negative_established", "Established")]
    fig, ax = plt.subplots(figsize=(3.6, 2.2))
    fills = {"DANGER": (K, ""), "WARNING": (G2, ""), "SAFE": ("white", "")}
    for i, (g, lab) in enumerate(groups):
        rs = sel[g]
        left = 0
        for lvl in ("DANGER", "WARNING", "SAFE"):
            w = 100 * np.mean([r["v2_level"] == lvl for r in rs])
            fc, h = fills[lvl]
            ax.barh(i, w, left=left, color=fc, edgecolor=K, lw=0.6, hatch=h, label=lvl if i == 0 else None)
            if w >= 8:
                ax.text(left + w / 2, i, f"{w:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if lvl == "DANGER" else K)
            left += w
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([g[1] for g in groups])
    ax.invert_yaxis()
    ax.set_xlabel("Packages (%)")
    ax.set_xlim(0, 100)
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.45, 1.0))
    fig.tight_layout()
    save(fig, "fig_levels")


def f_roc_reliability(first):
    m = [r for r in first if r["group"] in MAL and r["split"] == "test" and r["sig_I-02"] == "1"]
    b = [r for r in first if r["group"] == "benign-new" and r["split"] == "test" and r["sig_I-02"] == "1"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7))
    ax = axes[0]
    for col, lab, ls in (("v2_score", "Final design score", "-"), ("v1_score", "Initial design score", "--")):
        ms, bs = np.array([float(r[col]) for r in m]), np.array([float(r[col]) for r in b])
        th = sorted(set(ms) | set(bs), reverse=True)
        tpr = [0] + [np.mean(ms >= x) for x in th]
        fpr = [0] + [np.mean(bs >= x) for x in th]
        ax.plot(fpr, tpr, ls=ls, color=K, label=f"{lab} (AUC {auc(ms, bs):.3f})", drawstyle="steps-post")
    op = (np.mean([r["flagged_pipguard-v2-danger"] == "1" for r in b]), np.mean([r["flagged_pipguard-v2-danger"] == "1" for r in m]))
    ax.plot(*op, marker="o", color=K, mfc=K)
    ax.annotate("DANGER threshold", op, xytext=(0.35, 0.3), fontsize=7, arrowprops=dict(arrowstyle="-", color=K, lw=0.6))
    ax.plot([0, 1], [0, 1], color=G2, lw=0.7, ls=":")
    ax.set_xlabel("False positive rate (new legitimate)")
    ax.set_ylabel("True positive rate (new malicious)")
    ax.set_title("(a) ROC among new packages, test data")
    ax.legend(loc="lower right")
    ax = axes[1]
    # observed share malicious by score band (balanced prior 50 %) on test
    scores = sorted({int(float(r["v2_score"])) for r in m + b})
    bands = [(50, 50), (51, 56), (57, 62), (63, 68), (69, 100)]
    xs, ys, ns = [], [], []
    for lo, hi in bands:
        mm = sum(lo <= float(r["v2_score"]) <= hi for r in m) / len(m)
        bb = sum(lo <= float(r["v2_score"]) <= hi for r in b) / len(b)
        if mm + bb > 0:
            xs.append(f"{lo}" if lo == hi else f"{lo}–{hi}")
            ys.append(100 * mm / (mm + bb))
            ns.append(sum(lo <= float(r["v2_score"]) <= hi for r in m + b))
    bars = ax.bar(range(len(xs)), ys, color=[G2 if x.startswith("5") and not x.startswith("57") else K for x in xs],
                  edgecolor=K, lw=0.6)
    for i, (y, n) in enumerate(zip(ys, ns)):
        ax.text(i, y + 2, f"n={n}", ha="center", fontsize=6.5)
    ax.axhline(50, color=G2, ls=":", lw=0.8)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels(xs)
    ax.set_xlabel("Score band (≥ 57 = DANGER)")
    ax.set_ylabel("Malicious at equal class sizes (%)")
    ax.set_ylim(0, 105)
    ax.set_title("(b) Reliability of the score")
    fig.tight_layout()
    save(fig, "fig_severity")


def main():
    first, last, reported = results("first"), results("last"), results("reported")
    for rows in (first, last, reported):
        add_i10_columns(rows)
    a_dataset_and_missingness()
    a_missing_sensitivity(first)
    rep, gone, split = a_timing()
    per = load_exposure()
    a_exposure(per)
    a_exposure_estimators(per)
    a_background(per)
    a_cost()
    a_cost_complete()
    a_dependency_additions()
    a_campaign_summary(first)
    a_drift(first)
    a_early_model_validation(first)
    a_dormancy_choice(first, last)  # needs a_cost
    sel = a_detection(first, last, reported)
    a_misses(first)
    a_severity(first)
    a_recalibration(first)
    a_prospective()
    a_adaptive(per)
    a_campaign_sensitivity(first, per)
    a_filetype(first)
    a_dependents(per)
    a_cases()
    if "per_month" in NUMBERS["cost"]:
        t_exposure_tables()
    f_adaptive()
    f_drift(first)
    f_timing(rep, gone, split, per)
    f_levels(sel)
    f_roc_reliability(first)
    (TABLES / "tables_v3.md").write_text("\n\n".join(ALL_TABLES) + "\n")
    Path("paper/numbers_v3.json").write_text(json.dumps(NUMBERS, indent=1, default=str) + "\n")
    print("ok: paper/tables, paper/figures, paper/numbers_v3.json")


if __name__ == "__main__":
    main()
