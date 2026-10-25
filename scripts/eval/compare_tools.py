#!/usr/bin/env python3
"""Live, functional comparison of install-time cooldowns (network; nothing is installed).

For five kinds of package the script records what each tool does with a
plain `install <name>`:
  pip (default), pip --uploaded-prior-to P30D and P2D (pip >= 26.1),
  uv pip install --exclude-newer <now - 30 days>,
  pipguard (default) and pipguard with the opt-in I-10 rule (90 days).
pip and uv run with --dry-run and wheels only, so no package code is
executed and nothing is installed; pipguard runs non-interactively in front
of `pip --dry-run`.

Output: test-results/compare_tools/results.json and results.md.
Usage: python3 scripts/eval/compare_tools.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "test-results/compare_tools"
BAD = "zzz-pipguard-selftest-unregistered"
PIP_VERSION = "26.2.2"


def pypi(name):
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=60) as r:
            return json.load(r)
    except Exception:
        return None


def release_times(d):
    out = {}
    for v, files in d["releases"].items():
        if files:
            out[v] = min(datetime.fromisoformat(f["upload_time_iso_8601"].replace("Z", "+00:00")) for f in files)
    return out


def describe(name, now):
    d = pypi(name)
    if d is None:
        return {"name": name, "registered": False}
    rt = sorted(release_times(d).items(), key=lambda kv: kv[1])
    latest_v, latest_t = rt[-1]
    prev_t = rt[-2][1] if len(rt) > 1 else None
    return {"name": name, "registered": True, "latest": d["info"]["version"],
            "project_age_days": round((now - rt[0][1]).total_seconds() / 86400, 1),
            "latest_release_age_days": round((now - latest_t).total_seconds() / 86400, 1),
            "gap_before_latest_days": round((latest_t - prev_t).total_seconds() / 86400, 1) if prev_t else None,
            "has_wheel": any(f["packagetype"] == "bdist_wheel" for f in d["urls"])}


def newest_project(now):
    """A project first published within the last 30 days that ships a wheel (from the PyPI RSS feed)."""
    with urllib.request.urlopen("https://pypi.org/rss/packages.xml", timeout=60) as r:
        root = ET.fromstring(r.read())
    for item in root.iter("item"):
        name = item.find("title").text.replace(" added to PyPI", "").strip().lower()
        info = describe(name, now)
        if info.get("registered") and info["has_wheel"] and info["project_age_days"] < 30:
            return name
    raise SystemExit("no suitable new project in the RSS feed")


def project_aged(now, lo, hi):
    """A project first published lo..hi days ago with a single release that ships a wheel (ClickPy, then PyPI)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import pypi_history as ph
    rows = ph.query(f"""SELECT {ph.NORM_SQL} AS n FROM pypi.projects GROUP BY n
HAVING min(upload_time) BETWEEN now() - INTERVAL {hi} DAY AND now() - INTERVAL {lo} DAY
   AND countIf(packagetype = 'bdist_wheel') > 0 AND uniqExact(version) = 1
ORDER BY cityHash64(n) LIMIT 30 FORMAT JSONEachRow""")
    for r in rows:
        info = describe(r["n"], now)
        if info.get("registered") and info["has_wheel"] and lo <= info["project_age_days"] <= hi \
                and info["latest_release_age_days"] >= lo:
            return r["n"]
    raise SystemExit("no suitable project aged %d-%d days" % (lo, hi))


def run(cmd, env=None):
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=600)
    return p.returncode, p.stdout + p.stderr


def pip_outcome(pip, name, extra, latest):
    with tempfile.TemporaryDirectory() as tmp:
        rep = Path(tmp) / "report.json"
        code, out = run([pip, "install", "--dry-run", "--no-deps", "--only-binary=:all:", "--ignore-installed",
                         "--report", str(rep), "--quiet", *extra, name])
        if code != 0 or not rep.exists():
            return "fails (no matching distribution)" if "No matching distribution" in out or "Could not find" in out \
                else f"fails (exit {code})"
        v = json.loads(rep.read_text())["install"][0]["metadata"]["version"]
        return "installs latest" if v == latest else f"installs older ({v})"


def uv_outcome(uv, py, name, cutoff, latest):
    code, out = run([uv, "pip", "install", "--dry-run", "--no-deps", "--only-binary", ":all:", "--python", py,
                     "--exclude-newer", cutoff, name])
    if code != 0:
        return "fails (no matching distribution)" if "not found" in out or "No solution" in out or "unsatisfiable" in out \
            else f"fails (exit {code})"
    m = re.search(rf"\+ {re.escape(name)}==(\S+)", out, re.I)
    if not m:
        return "resolved (version not reported)"
    return "installs latest" if m.group(1) == latest else f"installs older ({m.group(1)})"


def pipguard_outcome(shimdir, venv_bin, home, name, dormancy):
    env = {"PATH": f"{shimdir}:{venv_bin}:/usr/bin:/bin", "HOME": home, "XDG_CACHE_HOME": f"{home}/cache",
           "XDG_CONFIG_HOME": f"{home}/config", "LANG": "C.UTF-8"}
    cfg = Path(home) / "config/pipguard"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.json").write_text(json.dumps({"release_dormancy_days": dormancy} if dormancy else {}))
    code, out = run(["pip", "install", "--dry-run", "--no-deps", "--only-binary=:all:", "--ignore-installed",
                     "--quiet", name], env)
    if code == 3:
        lvl = re.search(r'"level":"(\w+)"', out)
        return f"prompts ({lvl.group(1) if lvl else '?'}); cancelled without a terminal"
    return "passes silently" if code == 0 else f"forwarded; pip exit {code}"


def main():
    now = datetime.now(timezone.utc)
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp())
    subprocess.run([sys.executable, "-m", "venv", str(work / "venv")], check=True)
    vpip = str(work / "venv/bin/pip")
    subprocess.run([vpip, "install", "-q", f"pip=={PIP_VERSION}", "uv"], check=True)
    uv = str(work / "venv/bin/uv")
    subprocess.run(["go", "build", "-ldflags=-s -w", "-o", str(work / "pipguard"), "."], cwd=REPO, check=True)
    shim = work / "shim"
    shim.mkdir()
    os.symlink(work / "pipguard", shim / "pip")

    cases = [("Unregistered name", BAD), ("Project first published < 1 day ago", newest_project(now)),
             ("Project first published 10-15 days ago", project_aged(now, 10, 15)),
             ("Established project, regular release < 30 days ago", "certifi"),
             ("Established project, release < 30 days ago after > 90 days without releases", "pluggy"),
             ("Established project, no release in the last 30 days", "requests")]
    cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for label, name in cases:
        info = describe(name, now)
        latest = info.get("latest")
        r = {"case": label, "package": name, **info,
             "pip": pip_outcome(vpip, name, [], latest),
             "pip_P30D": pip_outcome(vpip, name, ["--uploaded-prior-to", "P30D"], latest),
             "pip_P2D": pip_outcome(vpip, name, ["--uploaded-prior-to", "P2D"], latest),
             "uv_30d": uv_outcome(uv, str(work / "venv/bin/python"), name, cutoff, latest),
             "pipguard": pipguard_outcome(shim, work / "venv/bin", str(work / "home1"), name, 0),
             "pipguard_I10": pipguard_outcome(shim, work / "venv/bin", str(work / "home2"), name, 90)}
        rows.append(r)
        print(json.dumps(r))
    _, uvv = run([uv, "--version"])
    meta = {"run_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "pip": PIP_VERSION, "uv": uvv.strip()}
    (OUT / "results.json").write_text(json.dumps({"meta": meta, "rows": rows}, indent=2) + "\n")
    cols = [("pip", "pip (default)"), ("pip_P30D", "pip --uploaded-prior-to P30D"), ("pip_P2D", "pip --uploaded-prior-to P2D"),
            ("uv_30d", "uv --exclude-newer (30 d)"), ("pipguard", "pipguard"), ("pipguard_I10", "pipguard + I-10 (90 d)")]
    md = [f"# Install-time cooldowns compared ({meta['run_at']}; pip {PIP_VERSION}; {meta['uv']})", "",
          "| Case | Package | " + " | ".join(c[1] for c in cols) + " |", "|---|---|" + "---|" * len(cols)]
    for r in rows:
        md.append(f"| {r['case']} | {r['package'] if r['package'] != BAD else '(made-up name)'} | "
                  + " | ".join(r[c[0]] for c in cols) + " |")
    (OUT / "results.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
