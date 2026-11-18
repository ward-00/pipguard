#!/usr/bin/env python3
"""Gambar skripsi berbahasa Indonesia (hitam putih).

Gambar data memakai data beku dan hasil yang sama dengan naskah jurnal (scripts/eval/analyze_v3.py, dibaca,
tidak dijalankan ulang); diagram (kerangka pikir, UML, arsitektur, protokol) digambar di sini.
Keluaran: skripsi-writing/figures/*.png; logo resmi ('Logo UPH.png') disediakan penulis.
Jalankan dari akar repositori setelah scripts/eval/run_all.sh:

    ~/.cache/pipguard-analysis-venv/bin/python scripts/skripsi/figures_skripsi.py
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
os.chdir(REPO)
sys.path.insert(0, str(REPO / "scripts/eval"))
import analyze_v3 as A  # noqa: E402  (gaya, pemuat data beku, fungsi bantu)

import matplotlib.ticker as mticker  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle  # noqa: E402

plt = A.plt
K, G1, G2, G3 = A.K, A.G1, A.G2, A.G3
OUT = REPO / "skripsi-writing/figures"
N = json.loads((REPO / "paper/numbers_v3.json").read_text())
T_LIST = [1, 2, 3, 7, 14, 21, 30, 60, 90]


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)


def koma(x, nd=1):
    return f"{x:,.{nd}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def fmt_koma(ax, axis="x"):
    def f(v, _):
        if v == 0:
            return "0"
        nd = max(0, -int(np.floor(np.log10(abs(v))))) if abs(v) < 1 else 0
        return koma(v, nd)
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(mticker.FuncFormatter(f))


# ======================================================================= gambar data

def g_paparan():
    """Gambar 4.x: waktu pelaporan dan penghapusan (a); paparan sisa terhadap biaya (b)."""
    edge = {b: b + 1 for b in range(15)}
    edge.update({15: 21, 21: 30, 30: 60, 60: 90, 90: 180, 180: 365, 365: np.inf})
    last = {}
    for r in A.jsonl(A.RAW / "malicious_downloads.jsonl.gz"):
        if r["bucket"] >= 0 and r["client"] > 0:
            last[r["project"]] = max(last.get(r["project"], 0), edge[r["bucket"]])
    rep, gone = [], []
    for n in A.META_FIRST:
        fm = A.first_malicious(n)
        rep.append((A.t(A.OSV[n]["published"]) - fm).total_seconds() / 86400)
        gone.append(last.get(n, np.nan))
    rep, gone = np.array(rep), np.array(gone)
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    ax = axes[0]
    xs = np.logspace(-2, 3, 300)
    for arr, lab, ls in ((rep, "Laporan OSV", "-"), (gone[~np.isnan(gone)], "Unduhan klien terakhir", "--")):
        arr = np.sort(arr)
        ax.plot(xs, [np.mean(arr <= x) * 100 for x in xs], ls=ls, color=K, label=lab)
    ax.set_xscale("log")
    fmt_koma(ax)
    ax.set_xlabel("Hari setelah unggahan berbahaya pertama")
    ax.set_ylabel("Paket berbahaya (%)")
    ax.set_title("(a) Waktu hingga dilaporkan dan dihapus")
    for d in (2, 7, 30):
        ax.axvline(d, color=G3, lw=0.7, zorder=0)
    ax.legend(loc="upper left")
    ax = axes[1]
    cost = N["cost"]
    est = N["exposure_estimators"]["by_shift"]["shift0"]
    for pol, ckey, lab, ls, mk in (("project", "project_client", "Tingkat proyek (pipguard)", "-", "o"),
                                   ("release", "release_client", "Tingkat rilis (pip, uv, pnpm)", "--", "s")):
        x = [100 * cost[ckey][str(T)]["median"] for T in T_LIST]
        y = [100 - 100 * est[pol][str(T)]["test"]["per_package"]["est"] for T in T_LIST]
        ax.plot(x, y, ls=ls, marker=mk, color=K, mfc="white", label=lab)
        for T, xx, yy in zip(T_LIST, x, y):
            if T in (1, 2, 7, 30, 90):
                ax.annotate(f"{T} hr", (xx, yy), textcoords="offset points", xytext=(3, 3), fontsize=6.5)
    ax.set_xscale("log")
    fmt_koma(ax)
    ax.set_xlabel("Unduhan klien instalasi yang terdampak (%)")
    ax.set_ylabel("Paparan sisa 2026,\nrata-rata per paket (%)")
    ax.set_title("(b) Paparan sisa terhadap biaya")
    ax.legend(loc="upper right")
    fig.tight_layout()
    save(fig, "gbr_paparan")


def _first():
    rows = A.results("first")
    A.add_i10_columns(rows)
    return rows


def g_pergeseran(first):
    rules = [("I-02", "I-02 umur < 30 hari", "-", "o"), ("I-07", "I-07 hanya sdist", "--", "s"),
             ("I-04", "I-04 tanpa tautan", ":", "^"), ("I-08", "I-08 README pendek", "-.", "D")]
    halves = sorted({A.half(A.first_malicious(r["name"])) for r in first if r["group"] in A.MAL})
    halves = [h for h in halves if h >= "2022 H2"]
    lab_h = [h.replace(" H1", "\nS1").replace(" H2", "\nS2") for h in halves]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1))

    def series(col):
        ys = []
        for h in halves:
            rs = [r for r in first if r["group"] in A.MAL and A.half(A.first_malicious(r["name"])) == h]
            ys.append(100 * np.mean([r[col] == "1" for r in rs]))
        return ys
    for code, lab, ls, mk in rules:
        axes[0].plot(range(len(halves)), series(f"sig_{code}"), ls=ls, marker=mk, color=K, mfc="white", label=lab)
    axes[0].set_ylabel("Paket berbahaya (%)")
    axes[0].set_title("(a) Prevalensi indikator")
    for code, lab, ls, mk in (("pipguard-v2", "pipguard (rancangan akhir)", "-", "o"),
                              ("v2-initial", "Kalibrasi awal", "--", "s"),
                              ("pipguard-v2-danger", "Tingkat DANGER", ":", "^")):
        axes[1].plot(range(len(halves)), series(f"flagged_{code}"), ls=ls, marker=mk, color=K, mfc="white",
                     label=lab)
    axes[1].set_ylabel("Recall (%)")
    axes[1].set_title("(b) Recall per semester")
    for ax in axes:
        ax.set_xticks(range(len(halves)))
        ax.set_xticklabels(lab_h)
        ax.set_ylim(0, 105)
        for b in ("2025 H1", "2026 H1"):
            if b in halves:
                ax.axvline(halves.index(b) - 0.5, color=G2, lw=0.8, ls="--")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    fig.tight_layout()
    save(fig, "gbr_pergeseran")


def g_tingkat(first):
    sel = {"mal": [r for r in first if r["group"] in A.MAL and r["split"] == "test"],
           "benign-new": [r for r in first if r["group"] == "benign-new" and r["split"] == "test"],
           "negative_established": [r for r in first if r["group"] == "negative_established" and r["split"] == "test"]}
    groups = [("mal", "Berbahaya"), ("benign-new", "Sah baru"), ("negative_established", "Mapan")]
    fig, ax = plt.subplots(figsize=(4.6, 2.0))
    fills = {"DANGER": K, "WARNING": G2, "SAFE": "white"}
    for i, (g, lab) in enumerate(groups):
        left = 0
        for lvl in ("DANGER", "WARNING", "SAFE"):
            w = 100 * np.mean([r["v2_level"] == lvl for r in sel[g]])
            ax.barh(i, w, left=left, color=fills[lvl], edgecolor=K, lw=0.6, label=lvl if i == 0 else None)
            if w >= 8:
                ax.text(left + w / 2, i, koma(w, 0), ha="center", va="center", fontsize=7,
                        color="white" if lvl == "DANGER" else K)
            left += w
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([f"{g[1]} (n = {len(sel[g[0]]):,})".replace(",", ".") for g in groups])
    ax.invert_yaxis()
    ax.set_xlabel("Paket (%)")
    ax.set_xlim(0, 100)
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.45, 1.0))
    fig.tight_layout()
    save(fig, "gbr_tingkat")


def g_keparahan(first):
    m = [r for r in first if r["group"] in A.MAL and r["split"] == "test" and r["sig_I-02"] == "1"]
    b = [r for r in first if r["group"] == "benign-new" and r["split"] == "test" and r["sig_I-02"] == "1"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    ax = axes[0]
    for col, lab, ls in (("v2_score", "Skor rancangan akhir", "-"), ("v1_score", "Skor rancangan awal", "--")):
        ms, bs = np.array([float(r[col]) for r in m]), np.array([float(r[col]) for r in b])
        th = sorted(set(ms) | set(bs), reverse=True)
        tpr = [0] + [np.mean(ms >= x) for x in th]
        fpr = [0] + [np.mean(bs >= x) for x in th]
        ax.plot(fpr, tpr, ls=ls, color=K, label=f"{lab} (AUC {koma(A.auc(ms, bs), 3)})", drawstyle="steps-post")
    op = (np.mean([r["flagged_pipguard-v2-danger"] == "1" for r in b]),
          np.mean([r["flagged_pipguard-v2-danger"] == "1" for r in m]))
    ax.plot(*op, marker="o", color=K, mfc=K)
    ax.annotate("Ambang DANGER", op, xytext=(0.35, 0.3), fontsize=7, arrowprops=dict(arrowstyle="-", color=K, lw=0.6))
    ax.plot([0, 1], [0, 1], color=G2, lw=0.7, ls=":")
    fmt_koma(ax, "x")
    fmt_koma(ax, "y")
    ax.set_xlabel("False positive rate (sah baru)")
    ax.set_ylabel("True positive rate (berbahaya baru)")
    ax.set_title("(a) Kurva ROC paket baru, data uji")
    ax.legend(loc="lower right")
    ax = axes[1]
    bands = [(50, 50), (51, 56), (57, 62), (63, 68), (69, 100)]
    xs, ys, ns = [], [], []
    for lo, hi in bands:
        mm = sum(lo <= float(r["v2_score"]) <= hi for r in m) / len(m)
        bb = sum(lo <= float(r["v2_score"]) <= hi for r in b) / len(b)
        if mm + bb > 0:
            xs.append(f"{lo}" if lo == hi else f"{lo}–{hi}")
            ys.append(100 * mm / (mm + bb))
            ns.append(sum(lo <= float(r["v2_score"]) <= hi for r in m + b))
    ax.bar(range(len(xs)), ys, color=[G2 if x.startswith("5") and not x.startswith("57") else K for x in xs],
           edgecolor=K, lw=0.6)
    for i, (y, n) in enumerate(zip(ys, ns)):
        ax.text(i, y + 2, f"n={n}", ha="center", fontsize=6.5)
    ax.axhline(50, color=G2, ls=":", lw=0.8)
    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels(xs)
    ax.set_xlabel("Rentang skor (≥ 57 = DANGER)")
    ax.set_ylabel("Berbahaya pada ukuran kelas\nyang sama (%)")
    ax.set_ylim(0, 105)
    ax.set_title("(b) Keandalan skor")
    fig.tight_layout()
    save(fig, "gbr_keparahan")


def g_adaptif():
    a = N["adaptive"]
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    xs = np.linspace(0, 1, 101)
    for k, lab, ls in (("release30", "Tingkat rilis, 30 hari", "--"),
                       ("project30_i10_observed", "Proyek + I-10 (90 hari), tidak dihindari", "-."),
                       ("project30", "Tingkat proyek, 30 hari", "-")):
        ax.plot(100 * xs, [100 * ((1 - p) * a[k]["young"] + p * a[k]["old"]) for p in xs], ls=ls, color=K, label=lab)
    ax.axvline(5.9, color=G2, lw=0.8, ls=":")
    ax.text(7.5, 40, "2026", fontsize=6.5, color=K)
    ax.set_xlabel("Porsi penyerang yang melakukan pre-aging (%)")
    ax.set_ylabel("Unduhan berbahaya yang dihentikan,\nrata-rata per paket (%)")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 100)
    ax.legend(loc="lower left", fontsize=6.5)
    fig.tight_layout()
    save(fig, "gbr_adaptif")


def g_latensi():
    sys.path.insert(0, str(REPO / "scripts/paper"))
    from ctx import latency
    lab = {"Set 2: stub pip, no pipguard": "Stub pip tanpa pipguard",
           "Set 2: pipguard, warm cache (1 entry)": r"pipguard, $\it{cache}$ terisi (1 entri)",
           "Set 2: pipguard, warm cache (1,000 entries)": r"pipguard, $\it{cache}$ terisi (1.000 entri)",
           "Set 2: pipguard, -r file with 20 cached packages": r"pipguard, berkas -r 20 paket (dalam $\it{cache}$)",
           "Reference: Python start-up + reading the cache": r"Rujukan: Python menyala + membaca $\it{cache}$",
           "Set 2: pipguard, empty cache (PyPI request)": r"pipguard, $\it{cache}$ kosong (permintaan PyPI)"}
    rows = [r for r in latency() if r[0] in lab]
    rows.sort(key=lambda r: float(r[1]))
    # p99 tidak digambar: nilainya ada pada tabel latensi tepat di atas gambar ini
    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    y = np.arange(len(rows))
    mean = [float(r[1]) for r in rows]
    ax.barh(y, mean, color=[K if "pipguard" in r[0] else "white" for r in rows], edgecolor=K, lw=0.6)
    for yy, v in zip(y, mean):
        ax.text(v + 1.5, yy, koma(v, 1), fontsize=6.5, va="center")
    ax.axvline(50, color=G2, ls="--", lw=0.8)
    ax.text(52, 1.0, "sasaran 50 ms\n(" + r"$\it{cache}$" + " terisi)", fontsize=6.3, va="center")
    ax.set_xlim(0, max(mean) * 1.12)
    ax.set_yticks(y)
    ax.set_yticklabels([lab[r[0]] for r in rows])
    ax.set_xlabel("Waktu per pemanggilan pip, rata-rata (ms)")
    fig.tight_layout()
    save(fig, "gbr_latensi")


# ======================================================================= alat bantu diagram

plt.rcParams.update({"font.family": "DejaVu Sans"})


def kanvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    ax.set_aspect("equal")
    return fig, ax


def kotak(ax, x, y, w, h, teks, fill="white", bold=False, dashed=False, size=7, rounded=True, align="center",
          lw=0.8):
    style = "round,pad=0.02,rounding_size=0.08" if rounded else "square,pad=0.0"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fill, ec=K, lw=lw, ls="--" if dashed else "-"))
    tx = x + w / 2 if align == "center" else x + 0.08
    ax.text(tx, y + h / 2, teks, ha=align, va="center", fontsize=size, fontweight="bold" if bold else "normal",
            linespacing=1.25)


def panah(ax, p, q, teks=None, dashed=False, size=6.5, off=(0, 0.1), style="-|>", ha="center", rot=0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9, lw=0.8, color=K,
                                 ls="--" if dashed else "-", shrinkA=0, shrinkB=0))
    if teks:
        ax.text((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1], teks, fontsize=size, ha=ha, va="center",
                style="italic", rotation=rot, bbox=dict(fc="white", ec="none", pad=0.4))


def garis(ax, pts, dashed=False):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=K, lw=0.8, ls="--" if dashed else "-")


def belah(ax, x, y, w, h, teks, size=6.5):
    ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y + h), (x + w, y + h / 2), (x + w / 2, y)], closed=True,
                         fc="white", ec=K, lw=0.8))
    ax.text(x + w / 2, y + h / 2, teks, ha="center", va="center", fontsize=size, linespacing=1.15)


def aktor(ax, x, y, nama, size=7):
    ax.add_patch(Ellipse((x, y + 0.62), 0.22, 0.22, fc="white", ec=K, lw=0.8))
    garis(ax, [(x, y + 0.51), (x, y + 0.2)])
    garis(ax, [(x - 0.2, y + 0.42), (x + 0.2, y + 0.42)])
    garis(ax, [(x - 0.16, y - 0.05), (x, y + 0.2), (x + 0.16, y - 0.05)])
    ax.text(x, y - 0.15, nama, ha="center", va="top", fontsize=size, linespacing=1.2)


# ======================================================================= diagram

def d_slopsquatting():
    fig, ax = kanvas(7.0, 1.6)
    ax.set_position([0, 0, 1, 1])     # sumbu memenuhi kanvas: 1 satuan = 1 inci, kotak keempat tidak terpotong
    langkah = [("1", "Penyerang mengirim\nprompt berulang\nke LLM dan mencatat\nnama paket yang\ntidak terdaftar"),
               ("2", "Penyerang\nmendaftarkan nama\nyang berulang di PyPI\ndengan muatan\nberbahaya"),
               ("3", "Pengembang atau\nagen AI menerima\nrekomendasi yang\nsama dan menjalankan\npip install"),
               ("4", "pip membangun sdist:\nskrip build\npenyerang berjalan\nsaat instalasi, sebelum\nkode diimpor")]
    w, gap, x0 = 1.5, 0.25, 0.1
    for i, (n, t) in enumerate(langkah):
        x = x0 + i * (w + gap)
        kotak(ax, x, 0.1, w, 1.4, t, size=7.6, fill="0.93" if i % 2 else "white")
        ax.text(x + 0.12, 1.36, n, fontsize=8.5, fontweight="bold", va="center")
        if i < 3:
            panah(ax, (x + w, 0.8), (x + w + gap, 0.8))
    save(fig, "gbr_slopsquatting")


def d_resolusi():
    fig, ax = kanvas(7.0, 2.8)
    ax.text(0.1, 2.62, "Urutan resolusi perintah pip pada bash/zsh", fontsize=7.5, fontweight="bold")
    urut = ["Alias", "Fungsi shell\npip()", "Perintah\nbawaan", "PATH: venv/bin\n(pip milik venv)",
            "PATH: ~/.local/bin\n(shim pipguard)", "PATH: /usr/bin\n(pip sistem)"]
    w, gap = 1.0, 0.16
    for i, t in enumerate(urut):
        x = 0.1 + i * (w + gap)
        fill = "0.8" if i == 1 else ("0.93" if i == 4 else "white")
        kotak(ax, x, 1.55, w, 0.75, t, size=6.2, fill=fill)
        if i < len(urut) - 1:
            panah(ax, (x + w, 1.92), (x + w + gap, 1.92))
    ax.text(0.1, 1.15, "Tanpa venv aktif: shim pada ~/.local/bin ditemukan lebih dahulu daripada pip sistem.",
            fontsize=6.6)
    ax.text(0.1, 0.85, "Dengan venv aktif: venv/bin berada di depan PATH sehingga shim terlewati;",
            fontsize=6.6)
    ax.text(0.1, 0.6, "fungsi shell tetap menang karena dievaluasi sebelum pencarian PATH.", fontsize=6.6)
    ax.text(0.1, 0.25, "Abu-abu tua = lapisan 1 (fungsi shell); abu-abu muda = lapisan 2 (shim).", fontsize=6.3,
            style="italic")
    save(fig, "gbr_resolusi")


def d_kerangka():
    fig, ax = kanvas(6.4, 7.6)
    blok = [
        ("MASALAH", "Paket berbahaya baru di PyPI menjalankan kode saat instalasi dan berumur pendek;\n"
                    "LLM merekomendasikan nama paket yang tidak terdaftar (slopsquatting);\n"
                    "detektor berada di sisi registry; manfaat dan biaya cooldown tingkat rilis\n"
                    "belum pernah diukur."),
        ("PERTANYAAN", "RM1 paparan dan waktu pelaporan; RM2 stabilitas indikator metadata;\n"
                       "RM3 perlindungan dan biaya kebijakan; RM4 halusinasi paket;\n"
                       "RM5 cakupan intersepsi dan overhead."),
        ("PENDEKATAN", "Rekonstruksi metadata titik-waktu 8.588 paket berbahaya + log unduhan;\n"
                       "pembagian temporal (pengembangan < 2025, validasi 2025, uji 2026), kampanye;\n"
                       "perancangan interceptor pipguard (Go) mengikuti DSRM."),
        ("PROSES", "Iterasi 1: bobot rancangan; iterasi 2: kalibrasi awal;\n"
                   "rancangan akhir: keputusan oleh I-01/I-02, tingkat oleh metadata;\n"
                   "evaluasi: paparan, biaya, kasus, intersepsi 43 skenario, latensi."),
        ("LUARAN", "pipguard: intersepsi fungsi shell + shim,\n"
                   "masa tunggu tingkat proyek 30 hari, rekaman JSON untuk CI dan agen AI;\n"
                   "pipeline evaluasi yang dapat direproduksi secara " + r"$\it{offline}$" + "."),
        ("CAPAIAN", "Rekomendasi kebijakan berlapis berbasis bukti: masa tunggu tingkat proyek\n"
                    "sebagai bawaan, aturan tingkat rilis untuk proyek yang disusupi atau pre-aged."),
    ]
    h, gap = 0.98, 0.26
    for i, (judul, isi) in enumerate(blok):
        y = 7.6 - 0.15 - (i + 1) * h - i * gap
        kotak(ax, 0.05, y, 1.25, h, judul, bold=True, fill="0.85", size=7)
        kotak(ax, 1.45, y, 4.9, h, isi, size=5.9, align="left")
        if i < len(blok) - 1:
            panah(ax, (3.9, y), (3.9, y - gap))
    save(fig, "gbr_kerangka")


def d_usecase():
    fig, ax = kanvas(7.0, 5.9)
    ax.add_patch(Rectangle((1.45, 0.55), 4.15, 5.2, fc="white", ec=K, lw=0.9))
    ax.text(1.55, 5.6, "pipguard", ha="left", fontsize=7.5, fontweight="bold")
    uc = {
        "UC-01": (2.45, 4.75, "UC-01 Menjalankan perintah\npip (install, download,\nwheel)"),
        "UC-02": (4.6, 5.05, "UC-02 Mengurai argumen\ndan berkas -r"),
        "UC-03": (4.6, 4.15, "UC-03 Mengambil metadata\n(" + r"$\it{cache}$" + " / PyPI)"),
        "UC-04": (2.45, 3.3, "UC-04 Menilai risiko\n(keputusan dan tingkat)"),
        "UC-07": (4.6, 3.2, "UC-07 Meneruskan perintah\nke pip asli (exec)"),
        "UC-05": (2.45, 2.2, "UC-05 Menampilkan\nperingatan dan\nkonfirmasi [y/N]"),
        "UC-06": (4.6, 2.2, "UC-06 Membatalkan dengan\nrekaman JSON (status 3)"),
        "UC-09": (2.45, 1.15, "UC-09 Memasang, melepas,\nmengatur konfigurasi"),
        "UC-08": (4.6, 1.15, "UC-08 Mengunci\nkonfigurasi sistem"),
    }
    W2, H2 = 0.9, 0.33
    for k, (x, y, t) in uc.items():
        ax.add_patch(Ellipse((x, y), 2 * W2, 2 * H2, fc="white", ec=K, lw=0.8))
        ax.text(x, y, t, ha="center", va="center", fontsize=5.6, linespacing=1.12)
    aktor(ax, 0.55, 4.45, "Skrip, CI,\nagen AI")
    aktor(ax, 0.55, 1.95, "Pengembang")
    aktor(ax, 6.5, 3.75, "Registry PyPI\n(JSON API)")
    aktor(ax, 6.5, 0.85, "Administrator\nsistem")
    garis(ax, [(0.78, 4.9), (1.55, 4.8)])
    garis(ax, [(0.78, 2.45), (1.7, 4.55)])
    garis(ax, [(0.78, 2.35), (1.55, 2.2)])
    garis(ax, [(0.78, 2.25), (1.6, 1.25)])
    garis(ax, [(6.27, 4.15), (5.5, 4.15)])
    garis(ax, [(6.27, 1.25), (5.5, 1.15)])

    def rel(p, q, teks, off):
        panah(ax, p, q, teks, dashed=True, size=5.4, off=off, style="->")
    rel((3.33, 4.85), (3.72, 4.98), "«include»", (0.0, 0.14))
    rel((3.25, 4.6), (3.78, 4.3), "«include»", (0.05, -0.14))
    rel((2.45, 4.42), (2.45, 3.63), "«include»", (0.38, 0.0))
    rel((3.7, 3.21), (3.35, 3.28), "«extend»", (0.0, 0.14))
    rel((2.45, 2.53), (2.45, 2.97), "«extend»", (0.35, 0.0))
    rel((3.95, 2.43), (3.15, 3.05), "«extend»", (0.3, -0.05))
    save(fig, "gbr_usecase")


def d_aktivitas():
    fig, ax = kanvas(7.0, 10.3)
    ax.add_patch(Ellipse((2.0, 10.05), 0.2, 0.2, fc=K, ec=K))

    def akt(y, t, x=0.7, w=2.6, h=0.42, fill="white"):
        kotak(ax, x, y, w, h, t, size=6.1, fill=fill)

    def lab(x, y, t):
        ax.text(x, y, t, fontsize=6, style="italic", va="center")
    akt(9.3, "Perintah pip dipanggil (shell, skrip,\nCI, atau agen AI)")
    panah(ax, (2.0, 9.95), (2.0, 9.72))
    akt(8.6, "Lapisan 1 (fungsi shell) atau lapisan 2\n(shim) menjalankan pipguard")
    panah(ax, (2.0, 9.3), (2.0, 9.02))
    akt(7.9, "Cari pip asli di PATH, lewati semua\nsalinan pipguard")
    panah(ax, (2.0, 8.6), (2.0, 8.32))
    belah(ax, 1.0, 6.95, 2.0, 0.62, "install / download\n/ wheel?")
    panah(ax, (2.0, 7.9), (2.0, 7.57))
    akt(6.1, "Urai nama paket, berkas -r dan\nopsi indeks")
    panah(ax, (2.0, 6.95), (2.0, 6.52))
    lab(2.1, 6.75, "ya")
    belah(ax, 1.0, 5.25, 2.0, 0.62, "Indeks utama\nkustom (-i)?")
    panah(ax, (2.0, 6.1), (2.0, 5.87))
    # eksekusi pip asli
    kotak(ax, 4.3, 7.0, 2.4, 0.52, "Simpan " + r"$\it{cache}$" + ";\nexec pip asli (proses diganti)", fill="0.9", size=6.1)
    ax.add_patch(Ellipse((5.5, 6.45), 0.22, 0.22, fc="white", ec=K, lw=0.8))
    ax.add_patch(Ellipse((5.5, 6.45), 0.13, 0.13, fc=K, ec=K))
    panah(ax, (5.5, 7.0), (5.5, 6.57))
    panah(ax, (3.0, 7.26), (4.3, 7.26))
    lab(3.05, 7.38, "tidak")
    garis(ax, [(3.0, 5.56), (3.75, 5.56)])
    lab(3.05, 5.68, "ya: tidak diperiksa")
    garis(ax, [(3.75, 4.95), (3.75, 7.26)])
    ax.text(3.85, 5.12, "semua paket selesai\ntanpa pembatalan", fontsize=5.6, style="italic", va="center")
    # wilayah per paket
    ax.add_patch(Rectangle((0.2, 0.95), 6.7, 4.0, fc="none", ec=K, lw=0.8, ls="--"))
    ax.text(0.3, 4.8, "untuk setiap paket di luar allowlist", fontsize=6, style="italic", va="center")
    akt(4.05, "Ambil metadata (" + r"$\it{cache}$" + " 24 jam / PyPI);\n" + r"$\it{error}$" + ": catat dan lewati (fail-open)")
    panah(ax, (2.0, 5.25), (2.0, 4.47))
    lab(2.1, 5.05, "tidak")
    akt(3.35, "Hitung sinyal I-01..I-10: keputusan\n(I-01, I-02), tingkat (metadata)")
    panah(ax, (2.0, 4.05), (2.0, 3.77))
    belah(ax, 1.0, 2.5, 2.0, 0.62, "Tingkat\nselain SAFE?")
    panah(ax, (2.0, 3.35), (2.0, 3.12))
    belah(ax, 1.0, 1.55, 2.0, 0.62, "Terminal\ninteraktif?")
    panah(ax, (2.0, 2.5), (2.0, 2.17))
    lab(2.1, 2.33, "ya")
    belah(ax, 3.82, 4.11, 0.36, 0.3, "")
    panah(ax, (3.82, 4.26), (3.3, 4.26))
    garis(ax, [(3.0, 2.81), (4.0, 2.81)])
    panah(ax, (4.0, 2.81), (4.0, 4.11))
    lab(3.05, 2.93, "tidak: paket berikutnya")
    kotak(ax, 4.6, 1.6, 2.0, 0.52, "Tampilkan peringatan dan\nalasan; prompt [y/N]", size=6)
    panah(ax, (3.0, 1.86), (4.6, 1.86))
    lab(3.05, 1.98, "ya")
    belah(ax, 5.0, 2.55, 1.2, 0.56, "y?")
    panah(ax, (5.6, 2.12), (5.6, 2.55))
    garis(ax, [(5.6, 3.11), (5.6, 4.26)])
    panah(ax, (5.6, 4.26), (4.18, 4.26))
    lab(5.68, 3.6, "y: paket berikutnya")
    garis(ax, [(6.2, 2.83), (6.75, 2.83), (6.75, 0.42)])
    panah(ax, (6.75, 0.42), (6.6, 0.42))
    lab(6.3, 2.95, "N")
    kotak(ax, 4.6, 0.18, 2.0, 0.5, "Batal: \"Installation\ncancelled.\", status 3", fill="0.8", size=6)
    kotak(ax, 0.7, 0.18, 2.6, 0.5, "Batal tanpa terminal: satu baris\nrekaman JSON di stderr, status 3",
          fill="0.8", size=6)
    panah(ax, (2.0, 1.55), (2.0, 0.68))
    lab(2.1, 1.1, "tidak")
    ax.add_patch(Ellipse((3.95, 0.43), 0.22, 0.22, fc="white", ec=K, lw=0.8))
    ax.add_patch(Ellipse((3.95, 0.43), 0.13, 0.13, fc=K, ec=K))
    panah(ax, (3.3, 0.43), (3.84, 0.43))
    panah(ax, (4.6, 0.43), (4.06, 0.43))
    save(fig, "gbr_aktivitas")


def d_sekuens():
    names = ["Pengguna /\nagen", "Shell (fungsi\natau shim)", "main", "parser", "cache", "PyPI\nJSON API",
             "scorer", "ui", "logger", "pip asli"]
    msgs = [(0, 1, "pip install X"), (1, 2, "jalankan pipguard (argv)"), (2, 2, "findRealPip()"),
            (2, 3, "Subcommand(), ExtractPackages(),\nReadRequirements()"), (2, 4, "GetOrFetch(X)"),
            (4, 5, "GET /pypi/X/json"), (5, 4, "200 + metadata / 404", True), (4, 2, "Metadata", True),
            (2, 6, "Evaluate(X, meta)"), (6, 2, "Result (skor, tingkat, alasan)", True), (2, 8, "Record(X, hasil)"),
            (2, 7, "Confirm(X, hasil)")]
    step = [0.5 if a == b else (0.55 if "\n" in t else 0.42) for a, b, t, *_ in msgs]
    W, Hh = 7.4, 0.95 + sum(step) + 2.9
    fig, ax = kanvas(W, Hh)
    xs = [0.4 + i * 0.73 for i in range(len(names))]
    for x, n in zip(xs, names):
        kotak(ax, x - 0.34, Hh - 0.62, 0.68, 0.45, n, size=5.3, rounded=False)
        garis(ax, [(x, Hh - 0.62), (x, 0.1)], dashed=True)
    lbl = dict(fc="white", ec="none", pad=0.3)
    y = Hh - 0.95
    for (a, b, t, *r), st in zip(msgs, step):
        ret = bool(r)
        if a == b:
            garis(ax, [(xs[a], y), (xs[a] + 0.3, y), (xs[a] + 0.3, y - 0.18)])
            panah(ax, (xs[a] + 0.3, y - 0.18), (xs[a], y - 0.18))
            ax.text(xs[a] + 0.35, y - 0.05, t, fontsize=5.5, va="center", bbox=lbl)
        else:
            panah(ax, (xs[a], y), (xs[b], y), dashed=ret, style="->" if ret else "-|>")
            ax.text((xs[a] + xs[b]) / 2, y + 0.11 + (0.08 if "\n" in t else 0), t, fontsize=5.5, ha="center",
                    va="center", linespacing=1.1, bbox=lbl)
        y -= st
    top = y + 0.1
    ax.add_patch(Rectangle((0.08, top - 2.0), 7.25, 2.0, fc="none", ec=K, lw=0.7))
    ax.text(0.13, top - 0.13, "alt", fontsize=6, fontweight="bold", va="center", bbox=lbl)
    ax.text(0.5, top - 0.13, "[terminal interaktif]", fontsize=5.6, va="center", style="italic", bbox=lbl)
    yy = top - 0.45
    panah(ax, (xs[7], yy), (xs[0], yy))
    ax.text((xs[0] + xs[7]) / 2, yy + 0.11, "peringatan + alasan, [y/N]", fontsize=5.5, ha="center", bbox=lbl)
    yy -= 0.4
    panah(ax, (xs[0], yy), (xs[7], yy), dashed=True, style="->")
    ax.text((xs[0] + xs[7]) / 2, yy + 0.11, "y / N", fontsize=5.5, ha="center", bbox=lbl)
    garis(ax, [(0.08, top - 1.1), (7.33, top - 1.1)], dashed=True)
    ax.text(0.5, top - 1.23, "[tanpa terminal: CI, agen AI]", fontsize=5.6, va="center", style="italic", bbox=lbl)
    yy = top - 1.6
    panah(ax, (xs[7], yy), (xs[1], yy))
    ax.text((xs[1] + xs[7]) / 2, yy + 0.11, "satu baris rekaman JSON pada stderr; batal, status keluar 3",
            fontsize=5.5, ha="center", bbox=lbl)
    yy = top - 2.35
    panah(ax, (xs[2], yy), (xs[9], yy))
    ax.text((xs[2] + xs[9]) / 2, yy + 0.11, "syscall.Exec(pip, argv)  [semua paket lolos atau dikonfirmasi y]",
            fontsize=5.5, ha="center", bbox=lbl)
    save(fig, "gbr_sekuens")


def d_kelas():
    fig, ax = kanvas(7.4, 6.6)

    def kelas(x, y, w, nama, atribut, metode, size=5.4):
        lh = 0.15
        h1, h2, h3 = 0.26, lh * max(1, len(atribut)) + 0.08, lh * max(1, len(metode)) + 0.08
        top = y
        ax.add_patch(Rectangle((x, top - h1), w, h1, fc="0.85", ec=K, lw=0.8))
        ax.text(x + w / 2, top - h1 / 2, nama, ha="center", va="center", fontsize=6, fontweight="bold")
        ax.add_patch(Rectangle((x, top - h1 - h2), w, h2, fc="white", ec=K, lw=0.8))
        for i, a in enumerate(atribut):
            ax.text(x + 0.05, top - h1 - 0.1 - i * lh, a, fontsize=size, va="center", family="DejaVu Sans Mono")
        ax.add_patch(Rectangle((x, top - h1 - h2 - h3), w, h3, fc="white", ec=K, lw=0.8))
        for i, mm in enumerate(metode):
            ax.text(x + 0.05, top - h1 - h2 - 0.1 - i * lh, mm, fontsize=size, va="center", family="DejaVu Sans Mono")
        return (x, top - h1 - h2 - h3, w, h1 + h2 + h3)
    m = kelas(2.7, 6.5, 2.0, "main", ["realPip string", "cfg config.Config"],
              ["main()", "findRealPip(cmd) string", "pipCommandName(argv0)", "forward(pip, args)"])
    p = kelas(0.05, 6.5, 2.35, "parser", ["IndexOptions {IndexURL,", "  ExtraIndexURL, NoIndex}"],
              ["Subcommand(args)", "ExtractPackages(args)", "ExtractIndexOptions(args)", "ExtractRequirementFiles()",
               "ReadRequirements(path)", "Normalize(name)"])
    c = kelas(5.0, 6.5, 2.35, "config.Config", ["Allow []string", "AllowEnvOverride bool", "AssumeYes, Disabled bool",
                                                 "ReleaseDormancyDays int", "CheckCustomIndex bool", "Locked bool"],
              ["Load() Config", "EnvOverrideIgnored() bool"])
    ca = kelas(0.05, 4.05, 2.35, "cache.Cache", ["path string", "entries map[string]entry", "(TTL 24 jam)"],
               ["Load(path) *Cache", "GetOrFetch(name, fetch)", "Save() error"])
    r = kelas(0.05, 2.35, 2.35, "registry.Metadata", ["Exists bool", "FirstRelease time.Time", "ReleaseCount int",
                                                       "HasHomepage, HasRepository", "Summary string",
                                                       "DescriptionLen int", "ClassifierCount int", "SdistOnly bool",
                                                       "LatestRelease, PreviousRelease"],
              ["Fetch(name) (Metadata, error)"])
    s = kelas(2.7, 4.2, 2.0, "scorer.Model", ["Points map[string]int", "Warn, Danger int", "Similarity *Similarity",
                                               "Dormancy time.Duration"],
              ["V1(), V2(), V3(popular, G)", "Signals(name, meta, now)", "Score(Signals) Result",
               "Evaluate(name, meta) Result"])
    res = kelas(2.7, 1.9, 2.0, "scorer.Result", ["Score int", "Level Level", "Reasons []string", "Hits []Hit"], [""])
    lv = kelas(5.0, 1.9, 2.35, "«enumeration» Level", ["Safe", "Warning", "Danger"], ["String() string"])
    u = kelas(5.0, 4.6, 2.35, "ui", ["Decision {decision, package,", "  level, score, reasons,", "  advice, exit_status}"],
              ["Confirm(name, Result, ...) bool", "isTerminal(f) bool", "adviceFor(Result)"])
    lg = kelas(5.0, 2.85, 2.35, "logger", ["(activity.log, JSONL)"], ["Record(name, Result)"])

    def hub(a, b, teks="", dashed=True):
        panah(ax, a, b, teks, dashed=dashed, style="->", size=5.3, off=(0, 0.08))
    hub((2.7, 6.2), (2.4, 6.2), "memakai")
    hub((4.7, 6.2), (5.0, 6.2), "memuat")
    hub((3.0, 5.18), (2.4, 3.8), "memakai")
    hub((3.7, 5.18), (3.7, 4.2), "Evaluate")
    hub((4.7, 5.35), (5.0, 4.1), "Confirm")
    hub((4.62, 5.18), (5.0, 2.6), "Record")
    hub((1.2, 2.73), (1.2, 2.35), "menyimpan")
    hub((3.7, 2.58), (3.7, 1.9), "menghasilkan")
    hub((4.7, 1.6), (5.0, 1.6), "memiliki", dashed=False)
    hub((2.7, 3.5), (2.4, 2.0), "membaca")
    save(fig, "gbr_kelas")


def d_arsitektur():
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(0.02, 0.98)
    ax.axis("off")

    def box(x, y, w, h, text, fill="white", dashed=False, size=6.2, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012", fc=fill, ec=K,
                                    lw=0.8, ls="--" if dashed else "-"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, linespacing=1.25,
                fontweight="bold" if bold else "normal")

    def arr(p, q):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, lw=0.8, color=K, shrinkA=1, shrinkB=1))
    callers = ["Shell interaktif\n(termasuk\nvenv aktif)", "Skrip dan\nsubproses", "Job CI dan\nkontainer",
               "Agen\npemrograman AI\n(tanpa terminal)"]
    for i, c in enumerate(callers):
        box(0.01, 0.80 - i * 0.2, 0.155, 0.13, c)
    box(0.2, 0.73, 0.235, 0.2, "Lapisan 1: fungsi shell\npip, pip3, python, python3\n(dievaluasi sebelum PATH;\n"
                                 "menang di dalam venv aktif)", fill="0.92", size=5.9)
    box(0.2, 0.30, 0.235, 0.2, "Lapisan 2: shim PATH\n~/.local/bin/pip, pip3\n(pemanggil non-interaktif)", fill="0.92")
    for i in range(4):
        arr((0.165, 0.865 - i * 0.2), (0.2, 0.83 if i == 0 else 0.40))
    ax.add_patch(FancyBboxPatch((0.47, 0.06), 0.33, 0.9, boxstyle="round,pad=0.004,rounding_size=0.012", fc="white",
                                ec=K, lw=1.0))
    ax.text(0.635, 0.915, "pipguard", ha="center", va="center", fontsize=6.4,
            fontweight="bold", linespacing=1.2)
    steps = ["1  Urai argumen pip; baca berkas -r;\nhanya install / download / wheel",
             "2  Kebijakan indeks dan allowlist\n(--index-url kustom: tidak diperiksa)",
             "3  Metadata: " + r"$\it{cache}$" + " lokal (24 jam)\natau PyPI JSON API (batas 3 detik)",
             "4  Keputusan: tidak terdaftar (I-01)\natau proyek < 30 hari (I-02)\n[+ I-10 opt-in]",
             "5  Tingkat: poin metadata (I-04..I-09)\nWARNING atau DANGER"]
    ys = [0.79, 0.635, 0.48, 0.325, 0.17]
    for y, st in zip(ys, steps):
        box(0.49, y - 0.06, 0.29, 0.12, st, size=5.4)
    for a, b in zip(ys, ys[1:]):
        arr((0.635, a - 0.055), (0.635, b + 0.055))
    arr((0.435, 0.83), (0.49, 0.80))
    arr((0.435, 0.40), (0.49, 0.78))
    box(0.835, 0.43, 0.165, 0.1, "PyPI JSON API\n(hanya nama\npaket)", dashed=True, size=5.9)
    arr((0.78, 0.48), (0.835, 0.48))
    box(0.835, 0.76, 0.165, 0.14, "SAFE atau " + r"$\it{error}$" + "\n(fail-open):\nexec pip asli", fill="0.92", size=5.9)
    box(0.835, 0.16, 0.165, 0.22, "WARNING /\nDANGER\nTTY: alasan +\nprompt [y/N]\nTanpa TTY: batal,\nbaris JSON,\nstatus 3",
        fill="0.75", size=5.9)
    arr((0.78, 0.325), (0.835, 0.29))
    arr((0.78, 0.325), (0.84, 0.80))
    ax.text(0.845, 0.64, "SAFE", fontsize=6.2, style="italic", ha="left")
    save(fig, "gbr_arsitektur")


def d_protokol():
    fig, ax = kanvas(7.0, 2.3)
    x0, x1 = 0.3, 6.8

    def xd(y):  # tahun pecahan -> x
        return x0 + (y - 2022.0) / (2027.0 - 2022.0) * (x1 - x0)
    garis(ax, [(x0, 1.0), (x1, 1.0)])
    for yr in range(2022, 2028):
        garis(ax, [(xd(yr), 0.93), (xd(yr), 1.07)])
        ax.text(xd(yr), 0.75, str(yr), ha="center", fontsize=6.5)
    ax.add_patch(Rectangle((xd(2022.0), 1.15), xd(2025.0) - xd(2022.0), 0.4, fc="white", ec=K, lw=0.8))
    ax.text((xd(2022) + xd(2025)) / 2, 1.35, "Pengembangan (< 2025): 7.431 berbahaya, 2.213 sah baru,\n"
                                                "struktur dan kalibrasi awal", ha="center", va="center", fontsize=6)
    ax.add_patch(Rectangle((xd(2025.0), 1.15), xd(2026.0) - xd(2025.0), 0.4, fc="0.88", ec=K, lw=0.8))
    ax.text((xd(2025) + xd(2026)) / 2, 1.35, "Validasi (2025)\n611 / 1.598; bobot", ha="center", va="center",
            fontsize=6)
    ax.add_patch(Rectangle((xd(2026.0), 1.15), xd(2026.8) - xd(2026.0), 0.4, fc="0.7", ec=K, lw=0.8))
    ax.text((xd(2026) + xd(2026.8)) / 2, 1.35, "Uji (2026)\n546 / 1.039", ha="center", va="center", fontsize=6)
    fz = xd(2026 + 292 / 365)
    garis(ax, [(fz, 0.55), (fz, 1.9)], dashed=True)
    ax.text(fz + 0.05, 1.82, "Pembekuan model\n19 Okt 2026", fontsize=5.8, va="top")
    ax.add_patch(Rectangle((fz, 0.35), 0.14, 0.3, fc=K, ec=K))
    ax.text(fz - 0.05, 0.45, "Hold-out prospektif:\n97 laporan OSV 19-24 Okt 2026", fontsize=5.8, ha="right",
            va="center")
    ax.text(x0, 2.1, "Paket dibagi menurut waktu unggahan berbahaya pertama; paket mapan dibagi acak ke data "
                     "pengembangan dan uji.", fontsize=6.3)
    save(fig, "gbr_protokol")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    first = _first()
    g_paparan()
    g_pergeseran(first)
    g_tingkat(first)
    g_keparahan(first)
    g_adaptif()
    g_latensi()
    d_slopsquatting()
    d_resolusi()
    d_kerangka()
    d_usecase()
    d_aktivitas()
    d_sekuens()
    d_kelas()
    d_arsitektur()
    d_protokol()
    print("ok:", OUT)


if __name__ == "__main__":
    main()
