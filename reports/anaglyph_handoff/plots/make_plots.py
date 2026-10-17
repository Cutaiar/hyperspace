#!/usr/bin/env python3
"""Diagram C: spectral transmission plots for the Hyperspace anaglyph candidate gel pairs.

Data source
-----------
All curves come from ``gel_spectra.csv`` in
``research_notes/Custom anaglyph 3D projection plan/``. The LEE_* columns there are
manufacturer-published per-wavelength transmittance values (percent, 400-700 nm,
5 nm step) scraped on 2026-10-17 from the inline SVG graph on each LEE colour page,
URL pattern ``https://leefilters.com/colour/<code>-<name>/`` (for example
https://leefilters.com/colour/106-primary-red/). They are manufacturer-published,
NOT measured by us. LEE reports 0.01 as its floor value (treat as <= 0.01 %).

The shaded bands (blue 445-465 nm, green 530-560 nm, red 610-640 nm) are the
narrow-band proxies used in theatrical_gels.md (B455/G545/R625). They are
illustrative band markers only, not measured projector primaries.

The crosstalk figure (C5) uses synthetic shapes and is labelled CONCEPTUAL; it
contains no data.

Outputs (written next to this script)
-------------------------------------
C1_red_cyan.{svg,png}, C2_magenta_green.{svg,png}, C3_amber_blue.{svg,png},
C4_pale_pink_leakage.{svg,png}, C5_crosstalk_conceptual.{svg,png}, band_summary.csv

Usage
-----
    python make_plots.py            # needs matplotlib + numpy
"""
from __future__ import annotations

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.normpath(
    os.path.join(HERE, "..", "..", "..", "research_notes",
                 "Custom anaglyph 3D projection plan", "gel_spectra.csv"))

# Illustrative band markers (nm), as used for B455/G545/R625 in theatrical_gels.md.
BANDS = [("blue", 445, 465), ("green", 530, 560), ("red", 610, 640)]

SOURCE_FOOTER = (
    "Data: gel_spectra.csv, LEE_* columns = values published on each LEE colour page, "
    "URL pattern https://leefilters.com/colour/<code>-<name>/ (e.g. .../colour/106-primary-red/), "
    "scraped 2026-10-17.\n"
    "Manufacturer-published (LEE Filters website), not measured by us. LEE floor value 0.01 % "
    "(read as <= 0.01 %). Single sheet; includes the sheet's own surface-reflection losses.\n"
    "Shaded bands are ILLUSTRATIVE BAND MARKERS ONLY (blue 445-465, green 530-560, red 610-640 nm), "
    "not measured projector primaries."
)

# Design tokens (light surface). Series colours: validated with the dataviz
# validator (--pairs all, light mode) per figure; every series also has a unique
# line style and a legend entry, so colour is never the only identity channel.
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
BAND_FILL = "#000000"

# column, short label, eye role, colour, linestyle
FIGURES = [
    {
        "stem": "C1_red_cyan",
        "title": "C1  Red / cyan candidates: LEE 106 (left, red) vs LEE 172 / 183 / 115 (right, cyan)",
        "series": [
            ("LEE_106_primary_red", "LEE 106 Primary Red", "left eye (red)", "#e34948", "-"),
            ("LEE_172_lagoon_blue", "LEE 172 Lagoon Blue", "right eye (cyan)", "#2a78d6", "--"),
            ("LEE_183_moonlight_blue", "LEE 183 Moonlight Blue", "right eye (cyan)", "#1baf7a", "-."),
            ("LEE_115_peacock_blue", "LEE 115 Peacock Blue", "right eye (cyan)", "#008300", ":"),
        ],
    },
    {
        "stem": "C2_magenta_green",
        "title": "C2  Magenta / green candidates: LEE 139 / 124 (left, green) vs LEE 795 / 128 (right, magenta)",
        "series": [
            ("LEE_139_primary_green", "LEE 139 Primary Green", "left eye (green)", "#008300", "-"),
            ("LEE_124_dark_green", "LEE 124 Dark Green", "left eye (green)", "#1baf7a", "-."),
            ("LEE_795_magical_magenta", "LEE 795 Magical Magenta", "right eye (magenta)", "#e87ba4", "--"),
            ("LEE_128_bright_pink", "LEE 128 Bright Pink", "right eye (magenta)", "#6250d6", ":"),
        ],
        "label_at": {"LEE_795_magical_magenta": 450, "LEE_128_bright_pink": 665},
    },
    {
        "stem": "C3_amber_blue",
        "title": "C3  Amber / blue candidates (DIY only): LEE 010 / 101 (left, amber) vs LEE 363 / 119 (right, blue)",
        "series": [
            ("LEE_010_medium_yellow", "LEE 010 Medium Yellow", "left eye (amber)", "#eda100", "-"),
            ("LEE_101_yellow", "LEE 101 Yellow", "left eye (amber)", "#e34948", "-."),
            ("LEE_363_special_medium_blue", "LEE 363 Special Medium Blue", "right eye (blue)", "#2a78d6", "--"),
            ("LEE_119_dark_blue", "LEE 119 Dark Blue", "right eye (blue)", "#1baf7a", ":"),
        ],
        "label_at": {"LEE_010_medium_yellow": 560, "LEE_101_yellow": 520,
                     "LEE_363_special_medium_blue": 430, "LEE_119_dark_blue": 470},
    },
    {
        "stem": "C4_pale_pink_leakage",
        "title": "C4  Why pale pinks fail: LEE 035 / 036 / 002 pass the green band that LEE 139 (green eye) uses",
        "series": [
            ("LEE_035_light_pink", "LEE 035 Light Pink", "pale pink (would-be magenta eye)", "#e87ba4", "--"),
            ("LEE_036_medium_pink", "LEE 036 Medium Pink", "pale pink (would-be magenta eye)", "#eda100", "-."),
            ("LEE_002_rose_pink", "LEE 002 Rose Pink", "pale pink (would-be magenta eye)", "#6250d6", ":"),
            ("LEE_139_primary_green", "LEE 139 Primary Green", "green eye reference", "#008300", "-"),
        ],
        "label_at": {"LEE_035_light_pink": 540, "LEE_036_medium_pink": 425,
                     "LEE_002_rose_pink": 595},
    },
]


def load_spectra(path: str = CSV_PATH) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Read gel_spectra.csv (first line is a '#' comment). Returns (wavelengths, {column: %T})."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh) if r and not r[0].startswith("#")]
    header, body = rows[0], rows[1:]
    data = np.array([[float(v) for v in r] for r in body])
    wl = data[:, 0]
    cols = {name: data[:, i] for i, name in enumerate(header) if i > 0}
    return wl, cols


def band_mean(wl: np.ndarray, t: np.ndarray, lo: float, hi: float) -> float:
    """Arithmetic mean of the 5 nm samples with lo <= wavelength <= hi (inclusive)."""
    m = (wl >= lo) & (wl <= hi)
    return float(np.mean(t[m]))


def _style_axes(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.6, linestyle="-")
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#b9b8b2")
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    ax.set_xlim(400, 700)
    ax.set_xticks(range(400, 701, 25))


def _draw_bands(ax, label: bool):
    for name, lo, hi in BANDS:
        ax.axvspan(lo, hi, color=BAND_FILL, alpha=0.06, linewidth=0, zorder=0)
        if label:
            ax.text((lo + hi) / 2, 1.0, f"illustrative\n{name} band\n{lo}-{hi} nm",
                    transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                    fontsize=7.5, color=TEXT_SECONDARY)


def plot_pair(wl, cols, fig_spec, outdir):
    fig = plt.figure(figsize=(11, 9.6), facecolor=SURFACE)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.0], hspace=0.12,
                          left=0.08, right=0.93, top=0.87, bottom=0.31)
    ax_lin = fig.add_subplot(gs[0])
    ax_log = fig.add_subplot(gs[1], sharex=ax_lin)
    for ax in (ax_lin, ax_log):
        _style_axes(ax)
    _draw_bands(ax_lin, label=True)
    _draw_bands(ax_log, label=False)

    for col, label, role, color, ls in fig_spec["series"]:
        t = cols[col]
        for ax in (ax_lin, ax_log):
            ax.plot(wl, t, color=color, linestyle=ls, linewidth=2.0,
                    label=f"{label}  -  {role}" if ax is ax_lin else None)
        # selective direct label: at the curve's peak in the linear panel, or at a
        # per-figure override wavelength where peaks would collide
        lx = fig_spec.get("label_at", {}).get(col)
        i = int(np.argmax(t)) if lx is None else int(np.argmin(np.abs(wl - lx)))
        code = label.split()[1]
        ax_lin.annotate(code, (wl[i], t[i]), xytext=(0, 5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8.5, color=TEXT_PRIMARY,
                        fontweight="bold")

    ax_lin.set_ylim(0, 100)
    ax_lin.set_ylabel("Transmittance  %T  (linear)", color=TEXT_PRIMARY, fontsize=10)
    plt.setp(ax_lin.get_xticklabels(), visible=False)
    ax_log.set_yscale("log")
    ax_log.set_ylim(0.005, 100)
    ax_log.set_yticks([0.01, 0.1, 1, 10, 100])
    ax_log.set_yticklabels(["0.01", "0.1", "1", "10", "100"])
    ax_log.axhline(0.01, color=TEXT_SECONDARY, linewidth=0.8)
    ax_log.text(702, 0.01, " LEE floor\n 0.01 %", va="center", ha="left", fontsize=7.5,
                color=TEXT_SECONDARY, clip_on=False)
    ax_log.set_ylabel("Transmittance  %T  (log; same data)", color=TEXT_PRIMARY, fontsize=10)
    ax_log.set_xlabel("Wavelength (nm)", color=TEXT_PRIMARY, fontsize=10)

    fig.text(0.08, 0.962, fig_spec["title"], fontsize=12.5, fontweight="bold",
             color=TEXT_PRIMARY, ha="left")
    fig.text(0.08, 0.94, "Top: linear %T. Bottom: the same curves on a log axis, "
             "so stop-band leakage (crosstalk source) is visible.",
             fontsize=9, color=TEXT_SECONDARY, ha="left")
    fig.legend(loc="upper center", bbox_to_anchor=(0.505, 0.255), ncol=2, frameon=False,
               fontsize=9, labelcolor=TEXT_PRIMARY, handlelength=3.2)

    # band-mean table (computed from the CSV) as footer text
    lines = ["Mean %T in illustrative bands (computed from gel_spectra.csv, 5 nm samples, inclusive):"]
    for col, label, _, _, _ in fig_spec["series"]:
        b, g, r = (band_mean(wl, cols[col], lo, hi) for _, lo, hi in BANDS)
        lines.append(f"   {label:<28s}  blue 445-465: {b:7.3f}   green 530-560: {g:7.3f}   red 610-640: {r:7.3f}")
    fig.text(0.08, 0.175, "\n".join(lines), fontsize=8, family="monospace",
             color=TEXT_PRIMARY, ha="left", va="top")
    fig.text(0.08, 0.012, SOURCE_FOOTER, fontsize=7.2, color=TEXT_SECONDARY, ha="left", va="bottom")

    for ext in ("svg", "png"):
        fig.savefig(os.path.join(outdir, f"{fig_spec['stem']}.{ext}"), dpi=150,
                    facecolor=SURFACE, metadata={"Date": None} if ext == "svg" else None)
    plt.close(fig)


def plot_conceptual(outdir):
    """C5: conceptual crosstalk illustration. Synthetic Gaussians/logistics; NO data."""
    wl = np.linspace(400, 700, 301)

    def g(mu, sig):
        return np.exp(-0.5 * ((wl - mu) / sig) ** 2)

    # synthetic, arbitrary shapes chosen only to illustrate overlap
    prim_b, prim_g, prim_r = g(460, 14), g(545, 24), g(615, 18)
    filt_red = 1.0 / (1.0 + np.exp(-(wl - 590) / 9.0))          # synthetic long-pass "red" filter

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), facecolor=SURFACE)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.80, bottom=0.25, wspace=0.18)
    for ax in axes:
        _style_axes(ax)
        ax.set_ylim(0, 1.55)
        ax.set_yticks([])
        ax.set_xlabel("Wavelength (nm)", color=TEXT_PRIMARY, fontsize=10)

    ax = axes[0]
    ax.plot(wl, prim_b, color="#2a78d6", lw=2, ls="--", label="synthetic 'blue primary' SPD")
    ax.plot(wl, prim_g, color="#008300", lw=2, ls="-.", label="synthetic 'green primary' SPD")
    ax.plot(wl, prim_r, color="#e34948", lw=2, ls=":", label="synthetic 'red primary' SPD")
    ax.plot(wl, filt_red, color=TEXT_PRIMARY, lw=1.6, ls="-", label="synthetic red-eye filter T(λ)")
    ax.set_title("(a) Display primaries and one eye's filter (shapes are invented)",
                 fontsize=10, color=TEXT_PRIMARY, loc="left")
    ax.set_ylabel("arbitrary units", color=TEXT_SECONDARY, fontsize=9)
    ax.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=TEXT_PRIMARY)

    ax = axes[1]
    signal = prim_r * filt_red
    ghost = (prim_g + prim_b) * filt_red
    ax.fill_between(wl, 0, signal, color="#e34948", alpha=0.35, lw=0)
    ax.plot(wl, signal, color="#e34948", lw=2, ls=":", label="intended: red SPD × T_red  (signal area)")
    ax.fill_between(wl, 0, ghost, color="#008300", alpha=0.45, lw=0, hatch="////", edgecolor="#008300")
    ax.plot(wl, ghost, color="#008300", lw=2, ls="-.", label="leak: (green+blue) SPD × T_red  (ghost area)")
    ax.annotate("ghost area = overlap of the\nother eye's primaries with\nthis filter's pass band",
                xy=(585, float(ghost[185])), xytext=(470, 0.62), fontsize=8.5, color=TEXT_PRIMARY,
                arrowprops=dict(arrowstyle="->", color=TEXT_SECONDARY, lw=0.9))
    ax.set_title("(b) Through the red-eye filter: signal vs ghost", fontsize=10,
                 color=TEXT_PRIMARY, loc="left")
    ax.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=TEXT_PRIMARY)

    fig.text(0.06, 0.93, "C5  CONCEPTUAL crosstalk illustration  -  synthetic curves, NOT data",
             fontsize=13, fontweight="bold", color=TEXT_PRIMARY)
    fig.text(0.06, 0.885, "Shapes are invented Gaussians/logistic edges chosen only to show the mechanism; "
             "no wavelength, height or area here is a measurement or a prediction.",
             fontsize=9, color=TEXT_SECONDARY)
    fig.text(0.06, 0.03,
             "Spectral prediction (Woods & Rourke 2004): crosstalk_eye % = 100 × ∫ SPD_other(λ)·T_eye(λ)·V(λ) dλ "
             "/ ∫ SPD_own(λ)·T_eye(λ)·V(λ) dλ   (V = CIE photopic; V omitted from this sketch).\n"
             "Measured, black-level corrected (Weissman & Woods 2011): crosstalk = (ghost − black) / (white − black), "
             "per eye, through that eye's filter.\n"
             "Sources: research_notes/Custom anaglyph 3D projection plan/rendering_algorithms.md Q1/Q4, "
             "calibration_equipment.md Q3.",
             fontsize=8, color=TEXT_SECONDARY, va="bottom")
    for ext in ("svg", "png"):
        fig.savefig(os.path.join(outdir, f"C5_crosstalk_conceptual.{ext}"), dpi=150,
                    facecolor=SURFACE, metadata={"Date": None} if ext == "svg" else None)
    plt.close(fig)


def write_band_summary(wl, cols, outdir):
    seen, rows = set(), []
    for spec in FIGURES:
        for col, label, role, _, _ in spec["series"]:
            if col in seen:
                continue
            seen.add(col)
            b, g, r = (band_mean(wl, cols[col], lo, hi) for _, lo, hi in BANDS)
            rows.append([label.split()[1], col, label, role, spec["stem"],
                         f"{b:.3f}", f"{g:.3f}", f"{r:.3f}"])
    path = os.path.join(outdir, "band_summary.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write("# Mean %T of each plotted LEE gel over illustrative bands, computed by make_plots.py from "
                 "gel_spectra.csv (arithmetic mean of 5 nm samples, band edges inclusive). Source data: "
                 "manufacturer-published (LEE Filters website, https://leefilters.com/colour/<code>-<name>/, "
                 "scraped 2026-10-17), not measured by us. Bands are illustrative markers, not measured "
                 "projector primaries. LEE floor 0.01 = <=0.01.\n")
        w = csv.writer(fh)
        w.writerow(["lee_code", "csv_column", "name", "role_in_plot", "first_plot",
                    "mean_T_pct_blue_445_465", "mean_T_pct_green_530_560", "mean_T_pct_red_610_640"])
        w.writerows(rows)
    return rows


def main():
    plt.rcParams["svg.hashsalt"] = "hyperspace-anaglyph"
    plt.rcParams["font.family"] = "DejaVu Sans"
    wl, cols = load_spectra()
    assert wl[0] == 400 and wl[-1] == 700, "expected 400-700 nm grid"
    for spec in FIGURES:
        plot_pair(wl, cols, spec, HERE)
    plot_conceptual(HERE)
    rows = write_band_summary(wl, cols, HERE)
    for r in rows:
        print(",".join(r))


if __name__ == "__main__":
    main()
