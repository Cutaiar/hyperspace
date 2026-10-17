#!/usr/bin/env python3
"""Reference implementation: Dubois least-squares anaglyph matrices from spectra.

Source of the method: E. Dubois, "A projection method to generate anaglyph stereo
images", ICASSP 2001 (https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf)
and the March 2009 how-to note, as summarised in
research_notes/Custom anaglyph 3D projection plan/rendering_algorithms.md (Q2, Q3).
This file is a small numpy port of that formulation; it is NOT Dubois's own code.

Conventions (read before use)
-----------------------------
* Wavelength grid: one 1-D array ``wl`` in nm, shared by every spectrum. Use
  :func:`resample` to bring data onto a common grid. Integration = trapezoid rule.
* ``cmf``: (N, 3) CIE 1931 2-degree colour-matching functions x-bar, y-bar, z-bar.
  NOT bundled. Download the CIE 1931 2-deg XYZ CMFs (e.g. from http://www.cvrl.org/ ,
  "CIE 1931 2-deg, XYZ CMFs") and pass them in. The tests use synthetic CMFs only.
* ``primaries``: (N, 3) display primary SPDs d_j, columns ordered (R, G, B). Measure each
  with one channel at full drive, others at 0, and SUBTRACT the black-frame SPD.
  Units cancel in the final normalisation, but all three must share one scale.
* ``f_left``, ``f_right``: (N,) filter transmittances as FRACTIONS 0..1
  (gel_spectra.csv is in PERCENT: divide by 100, or use ``percent=True`` in the CLI).
* Matrices are ROW-MAJOR with OUTPUT rows: anaglyph = M_L @ L + M_R @ R where L, R are
  column vectors (r, g, b). Same convention as anaglyph_profile.schema.json
  (`layout: row_major_output_rows`). GLSL mat3 is column-major: upload the transpose.
* Matrices act on LINEAR-light RGB. Decode before (sRGB EOTF or measured projector EOTF),
  encode after. Dubois 2009: clip each eye term to [0, 1] separately, then add.
* Maths (rendering_algorithms.md Q2):
      C[k, j]   = integral cmf_k * d_j dl                     (3x3, display RGB -> XYZ)
      A_l[k, j] = integral cmf_k * d_j * f_left dl            (3x3)
      A_r[k, j] = integral cmf_k * d_j * f_right dl           (3x3)
      R  = [A_l; A_r]                                          (6x3)
      C2 = blockdiag(C, C)                                     (6x6)
      P0 = (R^T W R)^-1 R^T W C2                               (3x6), W 6x6 positive-definite
      N  = diag(1 / (P0 @ ones(6)))                            (white maps to white)
      P  = N P0 = [M_L | M_R]
  W = I gives Euclidean XYZ x XYZ error; a diagonal W that up-weights the two Y entries
  (indices 1 and 4) favours correct luminance over colour (Dubois 2001).
* Unit test from the notes: rowsum(M_L) + rowsum(M_R) ~= 1 for every output channel.
  All published Dubois presets satisfy this to about +/-0.001.

Run tests:   python compute_dubois_matrix.py --test     (numpy only; pytest also works)
Compute:     python compute_dubois_matrix.py --cmf cmf.csv --primaries spd.csv \\
                 --filters gel_spectra.csv --left-col LEE_106_primary_red \\
                 --right-col LEE_172_lagoon_blue --percent
"""
from __future__ import annotations

import argparse
import csv
import sys

import numpy as np

# --------------------------------------------------------------------------------------
# Published presets, copied exactly from rendering_algorithms.md Q3 (for tests/reference)
# --------------------------------------------------------------------------------------
DUBOIS_PRESETS = {
    # Dubois March 2009, "red/cyan glasses and CRT/plasma display"
    "red_cyan_2009": (
        [[0.437, 0.449, 0.164], [-0.062, -0.062, -0.024], [-0.048, -0.050, -0.017]],
        [[-0.011, -0.032, -0.007], [0.377, 0.761, 0.009], [-0.026, -0.093, 1.234]],
    ),
    # "Classic" red-cyan as shipped by ffmpeg arcd / three.js (older set)
    "red_cyan_classic": (
        [[0.456, 0.500, 0.176], [-0.040, -0.038, -0.016], [-0.015, -0.021, -0.005]],
        [[-0.043, -0.088, -0.002], [0.378, 0.734, -0.018], [-0.072, -0.113, 1.226]],
    ),
    # Dubois 2010 SPM screenshot, LCD + TrioScopics3D; left = green, right = magenta
    "green_magenta_2010_lcd": (
        [[-0.062, -0.158, -0.039], [0.284, 0.668, 0.143], [-0.015, -0.027, 0.021]],
        [[0.529, 0.705, 0.024], [-0.016, -0.015, -0.065], [0.009, 0.075, 0.937]],
    ),
    # Dubois 2010 SPM screenshot, LCD + ColorCode; left = amber, right = blue
    "amber_blue_2010_lcd": (
        [[1.062, -0.205, 0.299], [-0.026, 0.908, 0.068], [-0.038, -0.173, 0.022]],
        [[-0.016, -0.123, -0.017], [0.006, 0.062, -0.017], [0.094, 0.185, 0.911]],
    ),
}

# Channel masks (Wimmer "Color" anaglyph / Blender channel selection), row-major output rows.
_Z = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
CHANNEL_MASKS = {
    "red_cyan": ([[1, 0, 0], [0, 0, 0], [0, 0, 0]], [[0, 0, 0], [0, 1, 0], [0, 0, 1]]),
    "green_magenta": ([[0, 0, 0], [0, 1, 0], [0, 0, 0]], [[1, 0, 0], [0, 0, 0], [0, 0, 1]]),
    "amber_blue": ([[1, 0, 0], [0, 1, 0], [0, 0, 0]], [[0, 0, 0], [0, 0, 0], [0, 0, 1]]),
}


# --------------------------------------------------------------------------------------
# Transfer functions (sRGB, as quoted from Dubois 2009 in rendering_algorithms.md Q2)
# --------------------------------------------------------------------------------------
def srgb_eotf(v):
    """Encoded sRGB value (0..1) -> linear light."""
    v = np.asarray(v, dtype=float)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_oetf(v):
    """Linear light (0..1) -> encoded sRGB value."""
    v = np.clip(np.asarray(v, dtype=float), 0.0, None)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)


# --------------------------------------------------------------------------------------
# Core maths
# --------------------------------------------------------------------------------------
def resample(wl_src, values, wl_dst):
    """Linear interpolation onto wl_dst; zero outside the source range. values: (N,) or (N, k)."""
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        return np.interp(wl_dst, wl_src, values, left=0.0, right=0.0)
    return np.stack([np.interp(wl_dst, wl_src, values[:, i], left=0.0, right=0.0)
                     for i in range(values.shape[1])], axis=1)


def _integrate(y, wl):
    trapz = getattr(np, "trapezoid", None) or np.trapz  # numpy >= 2 renamed trapz
    return trapz(y, wl, axis=0)


def tristimulus_matrices(wl, cmf, primaries, f_left, f_right):
    """Return (C, A_l, A_r), each 3x3 with [k, j] = integral cmf_k * d_j (* f) dl."""
    wl = np.asarray(wl, float)
    cmf = np.asarray(cmf, float)
    d = np.asarray(primaries, float)
    fl = np.asarray(f_left, float)
    fr = np.asarray(f_right, float)
    n = wl.shape[0]
    if cmf.shape != (n, 3) or d.shape != (n, 3) or fl.shape != (n,) or fr.shape != (n,):
        raise ValueError("shapes must be wl (N,), cmf (N,3), primaries (N,3), filters (N,)")
    if fl.max() > 1.0 + 1e-9 or fr.max() > 1.0 + 1e-9:
        raise ValueError("filter transmittance must be a fraction 0..1 (divide percent by 100)")

    def mat(weight):
        return np.array([[_integrate(cmf[:, k] * d[:, j] * weight, wl) for j in range(3)]
                         for k in range(3)])

    ones = np.ones(n)
    return mat(ones), mat(fl), mat(fr)


def dubois_projection(C, A_l, A_r, W=None, normalize=True):
    """Return (M_L, M_R, P) from the 3x3 matrices. W: 6x6 SPD weighting (default identity)."""
    C, A_l, A_r = (np.asarray(x, float) for x in (C, A_l, A_r))
    R = np.vstack([A_l, A_r])                       # 6x3
    C2 = np.block([[C, np.zeros((3, 3))], [np.zeros((3, 3)), C]])  # 6x6
    W = np.eye(6) if W is None else np.asarray(W, float)
    if W.shape != (6, 6):
        raise ValueError("W must be 6x6")
    RtW = R.T @ W
    P = np.linalg.solve(RtW @ R, RtW @ C2)          # 3x6 = (R^T W R)^-1 R^T W C2
    if normalize:
        white = P @ np.ones(6)
        if np.any(np.abs(white) < 1e-12):
            raise ValueError("white projects to ~0 in a channel; cannot normalise")
        P = np.diag(1.0 / white) @ P
    return P[:, :3], P[:, 3:], P


def dubois_from_spectra(wl, cmf, primaries, f_left, f_right, W=None, normalize=True):
    """Convenience wrapper: spectra -> (M_L, M_R, info dict with C, A_l, A_r, P)."""
    C, A_l, A_r = tristimulus_matrices(wl, cmf, primaries, f_left, f_right)
    M_L, M_R, P = dubois_projection(C, A_l, A_r, W=W, normalize=normalize)
    return M_L, M_R, {"C": C, "A_l": A_l, "A_r": A_r, "P": P}


def row_sum_check(M_L, M_R):
    """rowsum(M_L) + rowsum(M_R) per output channel (~1.0 for white-normalised matrices)."""
    return np.asarray(M_L, float).sum(axis=1) + np.asarray(M_R, float).sum(axis=1)


def y_weighted_W(y_weight=4.0):
    """Example diagonal W up-weighting the Y entries (indices 1 and 4). y_weight is a free design
    choice (Dubois gives no value); 4.0 is an arbitrary illustration, not a recommendation."""
    w = np.ones(6)
    w[[1, 4]] = y_weight
    return np.diag(w)


def apply_anaglyph(L_enc, R_enc, M_L, M_R, clip_mode="clip_each_term_then_sum",
                   decode=srgb_eotf, encode=srgb_oetf, gains=(1.0, 1.0)):
    """Composite encoded RGB arrays (..., 3) the way the proposed shader would.

    decode -> per-eye gain -> M_L L, M_R R -> clip (per term, or after sum) -> encode.
    Pass decode=encode=None to work directly in linear values.
    """
    L = np.asarray(L_enc, float)
    R = np.asarray(R_enc, float)
    if decode is not None:
        L, R = decode(L), decode(R)
    L, R = gains[0] * L, gains[1] * R
    tL = L @ np.asarray(M_L, float).T
    tR = R @ np.asarray(M_R, float).T
    if clip_mode == "clip_each_term_then_sum":
        out = np.clip(tL, 0, 1) + np.clip(tR, 0, 1)
    elif clip_mode == "sum_then_clip":
        out = tL + tR
    else:
        raise ValueError(clip_mode)
    out = np.clip(out, 0, 1)
    return encode(out) if encode is not None else out


# --------------------------------------------------------------------------------------
# Tests (synthetic data only; run with --test or pytest)
# --------------------------------------------------------------------------------------
def _synthetic_gaussians(wl):
    g = lambda mu, s: np.exp(-0.5 * ((wl - mu) / s) ** 2)  # noqa: E731
    # SYNTHETIC shapes, not CIE data and not a real display
    cmf = np.stack([g(600, 40) + 0.35 * g(445, 20), g(555, 45), 1.7 * g(450, 22)], axis=1)
    prim = np.stack([g(615, 15), g(540, 25), g(460, 12)], axis=1)
    f_left = 1 / (1 + np.exp(-(wl - 590) / 8))      # synthetic long-pass "red"
    f_right = 1 - 1 / (1 + np.exp(-(wl - 585) / 8))  # synthetic short-pass "cyan"
    return cmf, prim, f_left, f_right


def test_published_preset_row_sums():
    """Notes' unit test: every published Dubois pair has row sums ~1 (white -> white)."""
    for name, (ml, mr) in DUBOIS_PRESETS.items():
        rs = row_sum_check(ml, mr)
        assert np.allclose(rs, 1.0, atol=0.002), (name, rs)


def test_recomputed_matrix_row_sums_synthetic():
    """Same unit test applied to matrices recomputed from (synthetic) spectra, W = I and Y-weighted."""
    wl = np.arange(380.0, 781.0, 1.0)
    cmf, prim, fl, fr = _synthetic_gaussians(wl)
    for W in (None, y_weighted_W()):
        M_L, M_R, info = dubois_from_spectra(wl, cmf, prim, fl, fr, W=W)
        assert M_L.shape == (3, 3) and M_R.shape == (3, 3) and info["P"].shape == (3, 6)
        assert np.allclose(row_sum_check(M_L, M_R), 1.0, atol=1e-9)
        # red-eye filter: the output red row should draw mainly on the left image
        assert M_L[0].sum() > abs(M_R[0].sum())


def test_ideal_separation_reduces_to_channel_mask():
    """Non-overlapping box primaries, box CMFs aligned to them, perfect red/cyan filters:
    the least-squares solution must equal the pure channel mask."""
    wl = np.arange(400.0, 701.0, 1.0)
    box = lambda lo, hi: ((wl >= lo) & (wl <= hi)).astype(float)  # noqa: E731
    prim = np.stack([box(600, 640), box(520, 560), box(440, 480)], axis=1)
    cmf = np.stack([box(600, 640), box(520, 560), box(440, 480)], axis=1)  # synthetic
    f_left, f_right = box(590, 700), box(400, 580)
    M_L, M_R, _ = dubois_from_spectra(wl, cmf, prim, f_left, f_right)
    ml, mr = CHANNEL_MASKS["red_cyan"]
    assert np.allclose(M_L, ml, atol=1e-12) and np.allclose(M_R, mr, atol=1e-12)


def test_channel_mask_reproduces_pure_channels():
    """A channel-mask profile must pass pure channels unchanged through the full
    decode -> matrix -> clip -> encode path (red/cyan, green/magenta, amber/blue)."""
    white, black = np.ones(3), np.zeros(3)
    cases = {
        "red_cyan": ([1, 0, 0], [0, 1, 1]),
        "green_magenta": ([0, 1, 0], [1, 0, 1]),
        "amber_blue": ([1, 1, 0], [0, 0, 1]),
    }
    for name, (left_only, right_only) in cases.items():
        ml, mr = CHANNEL_MASKS[name]
        assert np.allclose(apply_anaglyph(white, black, ml, mr), left_only, atol=1e-9), name
        assert np.allclose(apply_anaglyph(black, white, ml, mr), right_only, atol=1e-9), name
        # arbitrary colours: each output channel is copied from its assigned eye
        L, R = np.array([0.5, 0.2, 0.9]), np.array([0.1, 0.7, 0.3])
        sel = np.array(left_only, bool)
        expect = np.where(sel, L, R)
        assert np.allclose(apply_anaglyph(L, R, ml, mr), expect, atol=1e-9), name
    # the shipped YAML profile, if pyyaml is available
    try:
        import os
        import yaml
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles", "red_cyan_channel_mask.yaml")
        with open(p, encoding="utf-8") as fh:
            m = yaml.safe_load(fh)["matrices"]
        assert np.allclose(apply_anaglyph(white, black, m["M_left"], m["M_right"]), [1, 0, 0])
        assert np.allclose(apply_anaglyph(black, white, m["M_left"], m["M_right"]), [0, 1, 1])
    except ImportError:
        pass


def test_srgb_roundtrip_and_clip_modes():
    x = np.linspace(0, 1, 101)
    assert np.allclose(srgb_oetf(srgb_eotf(x)), x, atol=1e-9)
    ml, mr = DUBOIS_PRESETS["red_cyan_2009"]
    L, R = np.array([1.0, 1.0, 1.0]), np.array([1.0, 1.0, 1.0])
    a = apply_anaglyph(L, R, ml, mr, clip_mode="clip_each_term_then_sum")
    b = apply_anaglyph(L, R, ml, mr, clip_mode="sum_then_clip")
    assert a.shape == b.shape == (3,)
    assert np.all((a >= 0) & (a <= 1)) and np.all((b >= 0) & (b <= 1))


def run_tests():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {e!r}")
    print("ALL TESTS PASSED" if not failed else f"{failed} TEST(S) FAILED")
    return 1 if failed else 0


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------
def _read_table(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh) if r and not r[0].lstrip().startswith("#")]
    header = [h.strip() for h in rows[0]]
    data = np.array([[float(v) for v in r] for r in rows[1:]])
    return header, data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--test", action="store_true", help="run the built-in tests (synthetic data)")
    ap.add_argument("--cmf", help="CSV: wavelength, xbar, ybar, zbar (CIE 1931 2-deg, e.g. from cvrl.org)")
    ap.add_argument("--primaries", help="CSV: wavelength, R, G, B (measured, black-subtracted SPDs)")
    ap.add_argument("--filters", help="CSV with wavelength in column 0 (e.g. gel_spectra.csv)")
    ap.add_argument("--left-col"); ap.add_argument("--right-col")
    ap.add_argument("--percent", action="store_true", help="filter values are percent (gel_spectra.csv)")
    ap.add_argument("--y-weight", type=float, default=None, help="optional diagonal W weight on Y entries")
    ap.add_argument("--step", type=float, default=5.0, help="integration grid step, nm")
    a = ap.parse_args(argv)
    if a.test:
        return run_tests()
    if not all([a.cmf, a.primaries, a.filters, a.left_col, a.right_col]):
        ap.error("need --cmf --primaries --filters --left-col --right-col (or --test)")
    _, cmf_t = _read_table(a.cmf)
    _, prim_t = _read_table(a.primaries)
    fh, filt_t = _read_table(a.filters)
    lo = max(cmf_t[0, 0], prim_t[0, 0], filt_t[0, 0])
    hi = min(cmf_t[-1, 0], prim_t[-1, 0], filt_t[-1, 0])
    wl = np.arange(lo, hi + 1e-9, a.step)
    if lo > 380 or hi < 720:
        print(f"WARNING: common range only {lo:.0f}-{hi:.0f} nm (Dubois integrates ~370-730 nm).",
              file=sys.stderr)
    cmf = resample(cmf_t[:, 0], cmf_t[:, 1:4], wl)
    prim = resample(prim_t[:, 0], prim_t[:, 1:4], wl)
    scale = 0.01 if a.percent else 1.0
    fl = resample(filt_t[:, 0], filt_t[:, fh.index(a.left_col)] * scale, wl)
    fr = resample(filt_t[:, 0], filt_t[:, fh.index(a.right_col)] * scale, wl)
    W = y_weighted_W(a.y_weight) if a.y_weight else None
    M_L, M_R, _ = dubois_from_spectra(wl, cmf, prim, fl, fr, W=W)
    fmt = lambda m: "\n".join(f"    - [{', '.join(f'{v:.4f}' for v in row)}]" for row in m)  # noqa: E731
    print("# paste into a profile's matrices block (status: measured once inputs are measured)")
    print(f"  M_left:\n{fmt(M_L)}\n  M_right:\n{fmt(M_R)}")
    print(f"  row_sum_check: [{', '.join(f'{v:.4f}' for v in row_sum_check(M_L, M_R))}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
