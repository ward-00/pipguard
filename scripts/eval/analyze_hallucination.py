#!/usr/bin/env python3
"""Hallucination study across models (aggregates only; names are never written to paper/).

Input : reproduction/Tests/multimodel/<model>.jsonl (git-ignored, sensitive)
Steps :
  1. parse every response into candidate package names (PEP 503 normalized),
     dropping standard-library modules and the upstream false-positive list;
  2. look every distinct name up on PyPI (JSON API) and in the time-stamped
     ClickPy history (first upload), once, and freeze the result in
     reproduction/Tests/multimodel/lookup.json (sensitive);
  3. classify each recommendation relative to the model's release date:
       existing      registered before the model was released
       unregistered  never registered on PyPI
       late          first registered after the model's release, i.e. a name the
                     model could not have learned from a real package: a
                     hallucination that someone has since registered
       removed       registered before the release but deleted since
  4. assess the late-registered names with pipguard's decision rule at two
     instants: when they were registered and today.

Outputs (aggregates): paper/tables/t_hallucination.{csv,md}, paper/numbers_hallucination.json.
Usage: python3 scripts/eval/analyze_hallucination.py [--refresh]
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pypi_history as ph  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "reproduction/Tests/multimodel"
OSV = {r["name"] for r in csv.DictReader(open(REPO / "testdata/malicious_osv.csv"))}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
STOP = {"python", "pip", "and", "or", "the", "for", "with", "none", "package", "packages", "library", "libraries",
        "module", "modules", "sure", "here", "are", "is", "a", "an", "to", "of", "in", "use", "you", "can",
        "following", "some", "these", "this", "that", "also", "etc", "e-g", "i-e", "builtin", "built-in"}


def stdlib():
    names = set(getattr(sys, "stdlib_module_names", ()))
    fp = REPO / "reproduction/Data/Python/false_positive_packages.csv"
    if fp.exists():
        for row in csv.reader(open(fp)):
            if row:
                names.add(row[0].strip())
    return {ph.normalize(n) for n in names if n}


TOP = {}   # dotted name -> its top-level component


def _norm(tok):
    tok = re.split(r"[=<>!~\[;]", tok.strip())[0].strip().strip(".,:")
    if not tok or not NAME_RE.match(tok):
        return None
    n = ph.normalize(tok)
    if "." in tok:  # "scipy.sparse" may name a module of scipy; resolved in main()
        TOP[n] = ph.normalize(tok.split(".")[0])
    return None if (n in STOP or n.isdigit() or len(n) < 2) else n


def parse(resp):
    """Candidate names from one response.

    Counted: backticked identifiers, the leading token of numbered or bulleted
    lines, `pip install x` arguments, and comma-separated lists whose items are
    at most three words (the format the prompt asks for). Free prose is ignored.
    """
    out = re.findall(r"`([^`\s]+)`\s+(?:library|package|module)", resp)
    out += re.findall(r"pip3? install\s+([A-Za-z0-9][A-Za-z0-9._-]*)", resp, flags=re.I)
    for line in resp.replace("*", " ").splitlines():
        line = line.strip()
        m = re.match(r"^(\d+[.)]|[-•])\s*(.+)$", line)
        if m:
            item = re.split(r"\s[-–(]|:", m.group(2).replace("`", ""))[0].strip()
            words = item.split()
            if 1 <= len(words) <= 3:
                out.append("-".join(words))   # "Keras Tuner" -> keras-tuner
            continue
        items = [x.strip() for x in line.replace("`", "").split(",")]
        if len(items) >= 2 and all(0 < len(x.split()) <= 3 for x in items if x):
            out += [x.split()[0] for x in items if x]
        elif len(items) == 1 and len(line.split()) == 1:
            out.append(line.replace("`", ""))
    seen, uniq = set(), []
    for tok in out:
        n = _norm(tok)
        if n and n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


def pypi_status(name):
    url = f"https://pypi.org/pypi/{name}/json"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pipguard-eval/1.0"}),
                                        timeout=60) as r:
                d = json.load(r)
            times = [f["upload_time_iso_8601"] for fs in d["releases"].values() for f in fs]
            return {"exists": True, "first": min(times) if times else None, "releases": len(d["releases"])}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"exists": False}
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return {"exists": None}


def lookup(names, refresh):
    path = SRC / "lookup.json"
    cache = json.loads(path.read_text()) if path.exists() and not refresh else {"names": {}}
    todo = [n for n in names if n not in cache["names"]]
    if todo:
        with ThreadPoolExecutor(max_workers=8) as ex:
            for n, st in zip(todo, ex.map(pypi_status, todo)):
                cache["names"][n] = st
        hist = {}
        for i in range(0, len(todo), 1500):
            chunk = ",".join(f"'{n}'" for n in todo[i:i + 1500] if re.fullmatch(r"[a-z0-9-]+", n))
            if chunk:
                for r in ph.query(f"SELECT {ph.NORM_SQL} AS n, toString(min(upload_time)) AS first FROM pypi.projects "
                                  f"WHERE n IN ({chunk}) GROUP BY n FORMAT JSONEachRow"):
                    hist[r["n"]] = r["first"]
        for n in todo:
            cache["names"][n]["history_first"] = hist.get(n)
        cache["looked_up_at"] = ph.fmt_time(datetime.now(timezone.utc))
        path.write_text(json.dumps(cache, indent=0))
    return cache


DEFENSIVE = re.compile(r"hallucinat|slopsquat|placeholder|reserved|security research|typo-?squat|do not (use|install)|"
                       r"prevent(ing)? (malicious|squat)|name ?squat|this package (is|has been) (claimed|registered)")


def owner_record(name):
    """What a late-registered name holds today (PyPI JSON API), for the ownership classification."""
    url = f"https://pypi.org/pypi/{name}/json"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pipguard-eval/1.0"}),
                                        timeout=60) as r:
                d = json.load(r)
            info = d["info"]
            files = [f for fs in d["releases"].values() for f in fs]
            return {"exists": True, "releases": len(d["releases"]), "files": len(files),
                    "summary": info.get("summary") or "", "description_len": len(info.get("description") or ""),
                    "description_head": (info.get("description") or "")[:2000],
                    "has_repository": bool(ph.has_repository([f"{k}, {v}" for k, v in
                                                              (info.get("project_urls") or {}).items()]))}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"exists": False}
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return {"exists": None}


def owners(names):
    """Classify who holds each late-registered hallucinated name (frozen in late_owners.json, sensitive).

    removed: deleted since; defensive or research: the text says it is a placeholder,
    a reservation or a security study; substantive: at least three releases, or a
    repository link with a description of at least 1,000 characters; minimal: the rest.
    """
    path = SRC / "late_owners.json"
    cache = json.loads(path.read_text()) if path.exists() else {}
    todo = [n for n in names if n not in cache]
    for n in todo:
        cache[n] = owner_record(n)
        cache[n]["looked_up_at"] = ph.fmt_time(datetime.now(timezone.utc))
    if todo:
        path.write_text(json.dumps(cache, indent=1))
    for n in names:
        r = cache[n]
        text = (r.get("summary", "") + " " + r.get("description_head", "")).lower()
        if not r.get("exists"):
            r["class"] = "removed"
        elif DEFENSIVE.search(text):
            r["class"] = "defensive or research"
        elif r["releases"] >= 3 or (r["has_repository"] and r["description_len"] >= 1000):
            r["class"] = "substantive"
        else:
            r["class"] = "minimal"
    return {n: cache[n] for n in names}


def first_seen(st):
    ts = [x for x in (st.get("first"), st.get("history_first")) if x]
    return min(ph.parse_time(x) for x in ts) if ts else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--n", type=int, default=125, help="prompts per dataset used (must match multimodel.py --n)")
    a = ap.parse_args()
    meta = json.loads((SRC / "prompts_meta.json").read_text())
    release = {m["name"]: ph.parse_time(m["release"] + "T00:00:00Z") for m in meta["models"]}
    std = stdlib()
    recs = defaultdict(list)          # model -> list of (prompt key, [names])
    for m in release:
        f = SRC / f"{m}.jsonl"
        if not f.exists():
            continue
        for r in map(json.loads, f.read_text().splitlines()):
            if r["i"] < a.n and r.get("response") is not None:
                recs[m].append(((r["dataset"], r["i"]), [n for n in parse(r["response"]) if n not in std]))
    allnames = sorted({n for v in recs.values() for _, ns in v for n in ns} | {TOP[n] for v in recs.values()
                                                                               for _, ns in v for n in ns if n in TOP})
    cache = lookup(allnames, a.refresh)["names"]
    now = datetime.now(timezone.utc)

    def cls(m, n):
        st = cache[n]
        if n in TOP and st.get("exists") is False and first_seen(st) is None and cache[TOP[n]].get("exists"):
            return "existing"   # a module of an existing package
        fs = first_seen(st)
        if fs is None and st.get("exists") is False:
            return "unregistered"
        if fs is None:
            return "unknown"
        if fs >= release[m]:
            return "late"
        return "existing" if st.get("exists") else "removed"

    rows, per_model = [], {}
    late_names, late_release = {}, {}
    occurrences = defaultdict(set)       # name -> prompts (any model)
    by_models = defaultdict(set)
    for m, items in recs.items():
        c = Counter()
        prompts_with_halluc = 0
        for key, ns in items:
            kinds = [cls(m, n) for n in ns]
            c.update(kinds)
            prompts_with_halluc += any(k in ("unregistered", "late") for k in kinds)
            for n, k in zip(ns, kinds):
                if k in ("unregistered", "late"):
                    occurrences[n].add(key)
                    by_models[n].add(m)
                if k == "late":
                    late_names[n] = cache[n]
                    late_release[n] = min(late_release.get(n, release[m]), release[m])
        tot = sum(c.values())
        per_model[m] = {"prompts": len(items), "recommendations": tot, **{k: c[k] for k in
                        ("existing", "unregistered", "late", "removed", "unknown")},
                        "prompts_with_hallucination": prompts_with_halluc}
        rows.append([m, release[m].date().isoformat(), len(items), tot,
                     f"{100 * c['unregistered'] / tot:.1f}", f"{100 * c['late'] / tot:.2f}",
                     f"{100 * prompts_with_halluc / len(items):.1f}"])
    # late-registered names: what pipguard and OSV say
    late = {}
    for n, st in late_names.items():
        fs = first_seen(st)
        late[n] = {"age_now_days": (now - fs).total_seconds() / 86400, "on_pypi_now": bool(st.get("exists")),
                   "in_osv": n in OSV, "recurring": len(occurrences[n]) >= 2 or len(by_models[n]) >= 2}
    own = owners(sorted(late_names))
    delays = sorted((first_seen(late_names[n]) - late_release[n]).total_seconds() / 86400 for n in late_names)
    unreg = {n for n in occurrences if all(cls(m, n) == "unregistered" for m in by_models[n])}
    out = {
        "models": per_model,
        "distinct_hallucinated": len(occurrences),
        "distinct_unregistered": len(unreg),
        "distinct_late": len(late),
        "recurring_hallucinated": sum(1 for n in occurrences if len(occurrences[n]) >= 2 or len(by_models[n]) >= 2),
        "late": {
            "on_pypi_now": sum(v["on_pypi_now"] for v in late.values()),
            "removed_since": sum(not v["on_pypi_now"] for v in late.values()),
            "in_osv": sum(v["in_osv"] for v in late.values()),
            "recurring": sum(v["recurring"] for v in late.values()),
            "younger_than_30d_now": sum(v["age_now_days"] < 30 for v in late.values()),
            "age_now_days_quartiles": sorted(v["age_now_days"] for v in late.values())[::max(1, len(late) // 4)]
            if late else [],
            "days_after_model_release": {"min": delays[0], "median": delays[len(delays) // 2], "max": delays[-1]}
            if delays else {},
            "owner_class": dict(Counter(v["class"] for v in own.values())),
        },
        "lookup_at": json.loads((SRC / "lookup.json").read_text()).get("looked_up_at"),
    }
    (REPO / "paper/numbers_hallucination.json").write_text(json.dumps(out, indent=1) + "\n")
    tab = REPO / "paper/tables"
    header = ["Model", "Released", "Prompts", "Recommended names", "Never registered (%)",
              "Registered only after the model's release (%)", "Prompts with ≥ 1 hallucinated name (%)"]
    with open(tab / "t_hallucination.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    md = ["### Package hallucination by model (500 prompts per model)", "", "| " + " | ".join(header) + " |",
          "|" + "---|" * len(header)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    (tab / "t_hallucination.md").write_text("\n".join(md) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
