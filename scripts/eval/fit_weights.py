#!/usr/bin/env python3
"""Kalibrasi model pipguard v2: konfigurasi I-05, poin, dan ambang.

Masukan  : CSV keluaran `evalset -out` (skenario "first") dan `evalset -sim-grid`
           (jarak nama per paket, sejajar dengan CSV pertama).
Keluaran : JSON berisi konfigurasi terpilih beserta seluruh angka antara.
           run_all.sh memeriksa bahwa scorer.V2 sama dengan hasil ini.

Dua metode, keduanya hanya membaca split yang disebut:

--method initial  (ditetapkan sebelum melihat data uji; DITOLAK)
    Split dev (< 2025), seluruh populasi (berbahaya vs paket baru yang sah
    vs paket mapan). Regresi logistik berbobot atas I-02..I-09, poin =
    round(10·β), PERINGATAN = ambang Youden J tertinggi, BAHAYA = FPR ≤ 1%.
    Pada data uji model ini hanya menangkap 12% paket berbahaya: 82% positif
    dev berasal dari satu kampanye massal 2023 yang hampir semuanya hanya-
    sdist tanpa tautan, dan taktik itu tidak bertahan pada 2025–2026.

--method final  (v2 yang dipakai shim)
    Struktur ditetapkan oleh temuan di atas: umur adalah satu-satunya sinyal
    yang stabil (93–100% paket berbahaya < 30 hari di setiap periode),
    sehingga
      * I-01 (tidak terdaftar) = 100 poin → BAHAYA;
      * I-02 (< 30 hari) = 50 poin = ambang PERINGATAN (masa tunggu/cooldown);
      * heuristik metadata I-03..I-09 hanya menentukan BAHAYA di antara paket
        baru; jumlah poinnya dibatasi ≤ 49 sehingga paket mapan tidak pernah
        ditandai oleh metadata saja.
    Bobot metadata, ambang BAHAYA, dan konfigurasi I-05 dipas pada split val
    (paket 2025) di antara paket baru: berbahaya vs paket baru yang sah,
    bobot kelas seimbang, regresi logistik ridge (λ=1) dengan β ≥ 0,
    poin = round(10·β) (diskalakan bila jumlahnya > 49). Ambang BAHAYA =
    50 + τ, τ = skor metadata dengan Youden J tertinggi pada val (seri →
    τ lebih kecil). I-05: dari 100 konfigurasi kisi dipilih yang model
    lengkapnya memberi J val tertinggi (seri → daftar lebih kecil, jarak lebih
    kecil, panjang minimum lebih besar, tanpa transposisi). Interval β:
    bootstrap berstrata 1.000×. Split test (≥ 2026) tidak dibaca.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict

import numpy as np

FEATURES = ["I-02", "I-03", "I-04", "I-05", "I-06", "I-07", "I-08", "I-09"]
NEW_NEG = {"benign-new"}
EST_NEG = {"negative_top1000", "negative_established"}
POS = {"malicious-typosquat", "malicious-other"}
SEED = 20261019


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ I-05

LISTS = ["curated-v1", "top-500", "top-1000", "top-2000", "top-5000"]


def list_size(name):
    return 331 if name == "curated-v1" else int(name.split("-")[1])


def similarity_configs():
    for lst in LISTS:
        for tr in (False, True):
            for max_dist in (1, 2):
                for min_len in (4, 5, 6, 7, 8):
                    yield {"list": lst, "min_len": min_len, "max_dist": max_dist, "transpositions": tr}


def similarity_column(grid_rows, cfg):
    col = f"d_{cfg['list']}_{'osa' if cfg['transpositions'] else 'lev'}"
    return np.array([1.0 if int(g["name_len"]) >= cfg["min_len"] and 1 <= int(g[col]) <= cfg["max_dist"] else 0.0
                     for g in grid_rows])


# ------------------------------------------------------------------ poin

def weighted_logreg(X, y, w, lam=1.0, iters=50):
    """Regresi logistik berbobot dengan ridge (intersep tidak dipenalti)."""
    Xb = np.hstack([np.ones((X.shape[0], 1)), X])
    beta = np.zeros(Xb.shape[1])
    pen = np.full(Xb.shape[1], lam)
    pen[0] = 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ beta))
        g = Xb.T @ (w * (p - y)) + pen * beta
        H = (Xb * (w * p * (1 - p))[:, None]).T @ Xb + np.diag(pen)
        step = np.linalg.solve(H, g)
        beta -= step
        if np.max(np.abs(step)) < 1e-10:
            break
    return beta


def fit_nonneg(X, y, w):
    """Pas ulang dengan koefisien negatif ditetapkan nol sampai semua ≥ 0."""
    active = list(range(X.shape[1]))
    raw = None
    while True:
        b = weighted_logreg(X[:, active], y, w)
        if raw is None:
            raw = b.copy()
        neg = [active[i] for i, c in enumerate(b[1:]) if c < 0]
        if not neg:
            full = np.zeros(X.shape[1])
            for i, a in enumerate(active):
                full[a] = b[1 + i]
            return b[0], full, raw
        active = [a for a in active if a not in neg]


def sample_weights(groups, y):
    w = np.zeros(len(y))
    pos = y == 1
    new = np.array([g in NEW_NEG for g in groups])
    est = np.array([g in EST_NEG for g in groups])
    n = len(y)
    w[pos] = (n / 2) / pos.sum()
    w[new] = (n / 4) / new.sum()
    w[est] = (n / 4) / est.sum()
    return w


def balanced_rates(score, y, groups, t):
    flagged = score >= t
    tpr = flagged[y == 1].mean()
    new = np.array([g in NEW_NEG for g in groups])
    est = np.array([g in EST_NEG for g in groups])
    fpr_new = flagged[new].mean()
    fpr_est = flagged[est].mean()
    return tpr, fpr_new, fpr_est, (fpr_new + fpr_est) / 2


def dev_arrays(results_path, grid_path):
    results, grid = load_rows(results_path), load_rows(grid_path)
    ok = [r for r in results if not r["error"]]
    if len(ok) != len(grid) or any((r["label"], r["group"], r["split"]) != (g["label"], g["group"], g["split"])
                                   for r, g in zip(ok, grid)):
        raise SystemExit("hasil evalset dan kisi I-05 tidak sejajar; jalankan keduanya dari satu evalset")
    keep = [i for i, r in enumerate(ok) if r["split"] == "dev" and r["group"] in POS | NEW_NEG | EST_NEG]
    rows = [ok[i] for i in keep]
    grid = [grid[i] for i in keep]
    groups = [r["group"] for r in rows]
    X = np.array([[0.0 if f == "I-05" else float(r["sig_" + f]) for f in FEATURES] for r in rows])
    y = np.array([1.0 if r["label"] == "positive" else 0.0 for r in rows])
    return X, y, groups, grid


def fit_model(X, y, groups):
    w = sample_weights(groups, y)
    intercept, beta, raw = fit_nonneg(X, y, w)
    points = {f: int(round(10 * b)) for f, b in zip(FEATURES, beta)}
    score = X @ np.array([points[f] for f in FEATURES])
    best, sweep = None, []
    for t in range(1, int(score.max()) + 2):
        tpr, fn, fe, fb = balanced_rates(score, y, groups, t)
        sweep.append({"threshold": t, "tpr": tpr, "fpr_new": fn, "fpr_established": fe, "youden_j": tpr - fb})
        if best is None or tpr - fb > best["youden_j"] + 1e-12:
            best = sweep[-1]
    danger = next((s for s in sweep if (s["fpr_new"] + s["fpr_established"]) / 2 <= 0.01), sweep[-1])
    return {"intercept": float(intercept), "beta": beta, "beta_raw": raw[1:], "points": points,
            "warn": best["threshold"], "warn_dev": best, "danger": danger["threshold"], "danger_dev": danger,
            "threshold_sweep_dev": sweep}


def choose_and_fit(results_path, grid_path):
    X0, y, groups, grid = dev_arrays(results_path, grid_path)
    i05 = FEATURES.index("I-05")
    new = np.array([g in NEW_NEG for g in groups])
    est = np.array([g in EST_NEG for g in groups])
    typo = np.array([g == "malicious-typosquat" for g in groups])

    table = []
    for cfg in similarity_configs():
        X = X0.copy()
        X[:, i05] = similarity_column(grid, cfg)
        m = fit_model(X, y, groups)
        table.append({**cfg,
                      "signal_tpr_typosquat": float(X[typo, i05].mean()),
                      "signal_tpr_malicious": float(X[y == 1, i05].mean()),
                      "signal_fpr_new": float(X[new, i05].mean()),
                      "signal_fpr_established": float(X[est, i05].mean()),
                      "points_i05": m["points"]["I-05"],
                      "model_youden_j": m["warn_dev"]["youden_j"], "model_tpr": m["warn_dev"]["tpr"],
                      "model_fpr_new": m["warn_dev"]["fpr_new"],
                      "model_fpr_established": m["warn_dev"]["fpr_established"]})
    table.sort(key=lambda t: (-round(t["model_youden_j"], 6), list_size(t["list"]), t["max_dist"],
                              -t["min_len"], t["transpositions"]))
    sim = {k: table[0][k] for k in ("list", "min_len", "max_dist", "transpositions")}

    X = X0.copy()
    X[:, i05] = similarity_column(grid, sim)
    m = fit_model(X, y, groups)

    rng = np.random.default_rng(SEED)
    idx_by = defaultdict(list)
    for i, g in enumerate(groups):
        idx_by[g].append(i)
    boots = []
    for _ in range(1000):
        # Bootstrap berstrata per kelompok agar komposisi kelas tetap.
        idx = np.concatenate([rng.choice(v, size=len(v), replace=True) for v in idx_by.values()])
        _, bb, _ = fit_nonneg(X[idx], y[idx], sample_weights([groups[i] for i in idx], y[idx]))
        boots.append(bb)
    boots = np.array(boots)

    prevalence = {}
    for g in sorted(set(groups)):
        mask = np.array([gg == g for gg in groups])
        prevalence[g] = {"n": int(mask.sum()), **{f: float(X[mask, i].mean()) for i, f in enumerate(FEATURES)}}

    return {
        "similarity": sim,
        "similarity_grid_dev": table,
        "n_dev": len(y),
        "n_dev_by_group": {g: len(v) for g, v in idx_by.items()},
        "intercept": m["intercept"],
        "beta_raw_unconstrained": {f: float(b) for f, b in zip(FEATURES, m["beta_raw"])},
        "beta": {f: float(b) for f, b in zip(FEATURES, m["beta"])},
        "beta_ci95_bootstrap": {f: [float(np.percentile(boots[:, i], 2.5)), float(np.percentile(boots[:, i], 97.5))]
                                for i, f in enumerate(FEATURES)},
        "points": m["points"],
        "warn": m["warn"], "warn_dev": m["warn_dev"],
        "danger": m["danger"], "danger_dev": m["danger_dev"],
        "threshold_sweep_dev": m["threshold_sweep_dev"],
        "prevalence_dev": prevalence,
    }


# ------------------------------------------------------------------ final

META = ["I-03", "I-04", "I-05", "I-06", "I-07", "I-08", "I-09"]
WARN = 50  # = poin I-02: paket baru selalu PERINGATAN


def val_arrays(results_path, grid_path):
    results, grid = load_rows(results_path), load_rows(grid_path)
    ok = [r for r in results if not r["error"]]
    if len(ok) != len(grid) or any((r["label"], r["group"], r["split"]) != (g["label"], g["group"], g["split"])
                                   for r, g in zip(ok, grid)):
        raise SystemExit("hasil evalset dan kisi I-05 tidak sejajar; jalankan keduanya dari satu evalset")
    keep = [i for i, r in enumerate(ok)
            if r["split"] == "val" and r["group"] in POS | NEW_NEG and r["sig_I-02"] == "1"]
    est = [i for i, r in enumerate(ok) if r["group"] in EST_NEG and r["split"] == "dev"]
    rows = [ok[i] for i in keep]
    X = np.array([[0.0 if f == "I-05" else float(r["sig_" + f]) for f in META] for r in rows])
    y = np.array([1.0 if r["label"] == "positive" else 0.0 for r in rows])
    return X, y, [r["group"] for r in rows], [grid[i] for i in keep], [grid[i] for i in est]


def balanced_weights(y):
    n = len(y)
    return np.where(y == 1, (n / 2) / y.sum(), (n / 2) / (1 - y).sum())


def capped_points(beta, cap=WARN - 1):
    k = 10.0
    while True:
        pts = np.round(k * beta).astype(int)
        if pts.sum() <= cap:
            return pts, k
        k *= 0.99


def fit_severity(X, y):
    intercept, beta, raw = fit_nonneg(X, y, balanced_weights(y))
    pts, k = capped_points(beta)
    score = X @ pts
    sweep, best = [], None
    for t in range(1, int(pts.sum()) + 2):
        tpr, fpr = float((score[y == 1] >= t).mean()), float((score[y == 0] >= t).mean())
        sweep.append({"tau": t, "tpr": tpr, "fpr_new": fpr, "youden_j": tpr - fpr})
        if best is None or tpr - fpr > best["youden_j"] + 1e-12:
            best = sweep[-1]
    return {"intercept": float(intercept), "beta": beta, "beta_raw": raw[1:], "points": pts, "scale": k,
            "tau": best["tau"], "tau_val": best, "tau_sweep_val": sweep}


def fit_final(results_path, grid_path):
    X0, y, groups, grid, est_grid = val_arrays(results_path, grid_path)
    i05 = META.index("I-05")
    typo = np.array([g == "malicious-typosquat" for g in groups])

    table = []
    for cfg in similarity_configs():
        X = X0.copy()
        X[:, i05] = similarity_column(grid, cfg)
        m = fit_severity(X, y)
        est_sig = similarity_column(est_grid, cfg)
        table.append({**cfg,
                      "signal_tpr_typosquat": float(X[typo, i05].mean()),
                      "signal_tpr_malicious": float(X[y == 1, i05].mean()),
                      "signal_fpr_new": float(X[y == 0, i05].mean()),
                      "signal_fpr_established": float(est_sig.mean()),
                      "points_i05": int(m["points"][i05]),
                      "model_youden_j": m["tau_val"]["youden_j"], "model_tpr": m["tau_val"]["tpr"],
                      "model_fpr_new": m["tau_val"]["fpr_new"]})
    table.sort(key=lambda t: (-round(t["model_youden_j"], 6), list_size(t["list"]), t["max_dist"],
                              -t["min_len"], t["transpositions"]))
    sim = {k: table[0][k] for k in ("list", "min_len", "max_dist", "transpositions")}

    X = X0.copy()
    X[:, i05] = similarity_column(grid, sim)
    m = fit_severity(X, y)

    rng = np.random.default_rng(SEED)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    boots = []
    for _ in range(1000):
        idx = np.concatenate([rng.choice(pos, len(pos)), rng.choice(neg, len(neg))])
        _, bb, _ = fit_nonneg(X[idx], y[idx], balanced_weights(y[idx]))
        boots.append(bb)
    boots = np.array(boots)

    points = {"I-01": 100, "I-02": WARN, **{f: int(p) for f, p in zip(META, m["points"])}}
    return {
        "method": "final",
        "similarity": sim,
        "similarity_grid_val": table,
        "n_val_new": {"malicious": int(y.sum()), "benign_new": int((1 - y).sum()),
                      "malicious_typosquat": int(typo.sum())},
        "intercept": m["intercept"],
        "beta_raw_unconstrained": {f: float(b) for f, b in zip(META, m["beta_raw"])},
        "beta": {f: float(b) for f, b in zip(META, m["beta"])},
        "beta_ci95_bootstrap": {f: [float(np.percentile(boots[:, i], 2.5)), float(np.percentile(boots[:, i], 97.5))]
                                for i, f in enumerate(META)},
        "points_scale": m["scale"],
        "points": points,
        "warn": WARN,
        "tau": m["tau"],
        "danger": WARN + m["tau"],
        "tau_val": m["tau_val"],
        "tau_sweep_val": m["tau_sweep_val"],
        "prevalence_val_new": {lab: {f: float(X[y == v, i].mean()) for i, f in enumerate(META)}
                               for lab, v in (("malicious", 1), ("benign_new", 0))},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True, help="CSV evalset (skenario first)")
    ap.add_argument("--grid", required=True, help="CSV evalset -sim-grid (jarak per nama, sejajar dengan --results)")
    ap.add_argument("--method", choices=["final", "initial"], default="final")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    fit = fit_final(a.results, a.grid) if a.method == "final" else {"method": "initial",
                                                                    **choose_and_fit(a.results, a.grid)}
    with open(a.out, "w") as f:
        json.dump(fit, f, indent=2)

    print(f"metode {fit['method']}; I-05 terpilih:", json.dumps(fit["similarity"]))
    print("β (tanpa batasan):", {k: round(v, 3) for k, v in fit["beta_raw_unconstrained"].items()})
    print("β (≥0)          :", {k: round(v, 3) for k, v in fit["beta"].items()})
    print("poin            :", fit["points"])
    if fit["method"] == "final":
        t = fit["tau_val"]
        print(f"ambang PERINGATAN {fit['warn']} (I-02), BAHAYA {fit['danger']} (τ={fit['tau']}: val TPR "
              f"{t['tpr']:.3f}, FPR baru {t['fpr_new']:.3f})")
    else:
        print(f"ambang PERINGATAN {fit['warn']}, BAHAYA {fit['danger']}")
    print("->", a.out, file=sys.stderr)


if __name__ == "__main__":
    main()
