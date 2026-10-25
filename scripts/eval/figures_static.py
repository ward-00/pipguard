#!/usr/bin/env python3
"""Black-and-white figures that do not depend on evaluation data.

  fig_architecture  interception layers and checking pipeline
  fig_warning       the warning printed for an unregistered package, taken
                    verbatim from test-results/interception/logs/b1.txt
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

FIGS = Path("paper/figures")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "pdf.fonttype": 42, "savefig.dpi": 600})


def save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", bbox_inches="tight", dpi=300)
    plt.close(fig)


def box(ax, x, y, w, h, text, fill="white", bold=False, dashed=False, size=6.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.012", fc=fill, ec="black",
                                lw=0.8, ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, p, q, text=None, offset=(0, 0), dashed=False):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, lw=0.8, color="black",
                                 ls="--" if dashed else "-", shrinkA=1, shrinkB=1))
    if text:
        ax.text((p[0] + q[0]) / 2 + offset[0], (p[1] + q[1]) / 2 + offset[1], text, fontsize=6.4,
                ha="center", va="center", style="italic")


def architecture():
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(0.02, 0.98)
    ax.axis("off")
    # callers
    callers = ["Interactive shell\n(incl. active venv)", "Scripts and\nsubprocesses", "CI jobs and\ncontainers",
               "AI coding agents\n(no terminal)"]
    for i, c in enumerate(callers):
        box(ax, 0.01, 0.80 - i * 0.2, 0.15, 0.13, c)
    # interception layers
    box(ax, 0.205, 0.73, 0.225, 0.2, "Layer 1: shell functions\npip, pip3, python, python3\n(evaluated before PATH;\nwin inside an active venv)",
        fill="0.92")
    box(ax, 0.205, 0.30, 0.225, 0.2, "Layer 2: PATH shim\n~/.local/bin/pip, pip3\n(non-interactive callers)", fill="0.92")
    for i in range(4):
        y = 0.865 - i * 0.2
        arrow(ax, (0.16, y), (0.205, 0.83 if i == 0 else 0.40))
    # core
    ax.add_patch(FancyBboxPatch((0.47, 0.06), 0.33, 0.9, boxstyle="round,pad=0.004,rounding_size=0.012", fc="white",
                                ec="black", lw=1.0))
    ax.text(0.635, 0.92, "pipguard (single static Go binary)", ha="center", va="center", fontsize=7.0, fontweight="bold")
    steps = ["1  Parse pip arguments; read -r files;\n    install / download / wheel only",
             "2  Index and allowlist policy\n    (custom --index-url: not checked)",
             "3  Metadata: local cache (24 h)\n    or PyPI JSON API (3 s timeout)",
             "4  Decision: unregistered (I-01) or\n    project < 30 days (I-02) [+ I-10 opt-in]",
             "5  Severity: metadata points (I-04..I-09)\n    WARNING vs DANGER"]
    ys = [0.80, 0.645, 0.49, 0.335, 0.18]
    for y, st in zip(ys, steps):
        box(ax, 0.49, y - 0.055, 0.29, 0.11, st, size=6.0)
    for a, b in zip(ys, ys[1:]):
        arrow(ax, (0.635, a - 0.055), (0.635, b + 0.055))
    arrow(ax, (0.43, 0.83), (0.49, 0.80))
    arrow(ax, (0.43, 0.40), (0.49, 0.78))
    # registry
    box(ax, 0.835, 0.44, 0.165, 0.1, "PyPI JSON API\n(name only)", dashed=True)
    arrow(ax, (0.78, 0.49), (0.835, 0.49))
    # outcomes
    box(ax, 0.835, 0.76, 0.165, 0.14, "SAFE or error\n(fail-open):\nexec real pip", fill="0.92")
    box(ax, 0.835, 0.20, 0.165, 0.19, "WARNING / DANGER\nTTY: reasons +\n[y/N] prompt\nNo TTY: cancel,\nJSON line, exit 3",
        fill="0.75")
    arrow(ax, (0.78, 0.335), (0.835, 0.30))
    arrow(ax, (0.78, 0.335), (0.84, 0.80))
    ax.text(0.845, 0.64, "SAFE", fontsize=6.2, style="italic", ha="left")
    save(fig, "fig_architecture")


def warning():
    log = Path("test-results/interception/logs/b1.txt").read_text().replace("\r", "")
    lines = [l for l in log.splitlines() if not l.startswith("bash:")]
    start = next(i for i, l in enumerate(lines) if l.startswith("─"))
    body = [l.replace("─" * 60, "─" * 56) for l in lines[start:] if l.strip() or True]
    body = [l.replace("Continue installation? [y/N]: Installation cancelled.",
                      "Continue installation? [y/N]: n\nInstallation cancelled.") for l in body]
    text = "\n".join(["$ pip install zzz-pipguard-selftest-unregistered"] + body).rstrip()
    n = text.count("\n") + 1
    fig = plt.figure(figsize=(4.9, 0.122 * n + 0.2))
    fig.patches.append(FancyBboxPatch((0.005, 0.01), 0.99, 0.98, boxstyle="round,pad=0,rounding_size=0.02",
                                      fc="white", ec="black", lw=0.8, transform=fig.transFigure))
    fig.text(0.03, 0.96, text, family="DejaVu Sans Mono", fontsize=6.6, va="top", ha="left", linespacing=1.3)
    save(fig, "fig_warning")


if __name__ == "__main__":
    architecture()
    warning()
    print("ok")
