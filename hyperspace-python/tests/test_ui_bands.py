"""The band editor (WP5b).

The geometry first — fit_box, drag_edge, pooled, band_under are pure
and are checked against the analyzer's own f/q ↔ edges — then the
registry writes, then the headless harness (test_ui_shell's rig, with
an implot context) drawing the ANALYZER page at 1, 6 and 16 bands and
around add / remove, and the ghost for a modulated centre. The ROUTING
page's tests are test_ui_routing.py (audit D5). A mouse can't be driven
here, so the drag handlers' *effects* are what the tests call.
"""

import math

import numpy as np
import pytest
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import ui_bands
from hyperspace.analysis import FFT_SIZE
from hyperspace.analyzer import (
    F_HI,
    F_LO,
    HIST_DT,
    HIST_F,
    HIST_FLOOR,
    HIST_T,
    N_MAX,
    Q_HI,
    Q_LO,
    centre_q,
    edges,
)


@pytest.fixture()
def rig(shell_rig):  # noqa: F811 — pytest hands the shell's rig through under its name
    return shell_rig


# ---------------------------------------------------------------- geometry

def test_fit_box_is_the_frequency_extent_either_way_up():
    f, q = ui_bands.fit_box(60.0, 20.0)
    lo, hi = edges(f, q)
    assert lo == pytest.approx(20.0) and hi == pytest.approx(60.0)
    assert ui_bands.fit_box(20.0, 60.0) == (f, q)
    assert (f, q) == pytest.approx(centre_q(20.0, 60.0))


def test_fit_box_clamps_to_the_params_ranges():
    # the whole axis: wider than Q_LO allows, so the band is narrower than the box
    f, q = ui_bands.fit_box(20.0, 24000.0)
    assert q == Q_LO and F_LO <= f <= F_HI
    # a sliver (a drag with no height) pins Q at the top
    f, q = ui_bands.fit_box(1000.0, 1000.5)
    assert q == Q_HI and f == pytest.approx(1000.25, rel=1e-3)
    # off the axis: the centre clamps
    assert ui_bands.fit_box(1.0, 5.0)[0] == F_LO
    assert ui_bands.fit_box(30000.0, 40000.0)[0] == F_HI


def test_drag_edge_moves_one_edge_and_keeps_the_other():
    lo, hi = 100.0, 400.0
    f, q = ui_bands.drag_edge(lo, hi, "lo", 50.0)
    assert edges(f, q) == pytest.approx((50.0, 400.0))
    f, q = ui_bands.drag_edge(lo, hi, "hi", 800.0)
    assert edges(f, q) == pytest.approx((100.0, 800.0))
    # dragged through the other edge: the band never flips — it narrows to
    # MIN_OCT about the fixed edge, which Q_HI then widens a little
    f, q = ui_bands.drag_edge(lo, hi, "lo", 1000.0)
    assert q == Q_HI and abs(math.log2(f / 400.0)) < 0.05
    f, q = ui_bands.drag_edge(lo, hi, "hi", 10.0)
    assert q == Q_HI and abs(math.log2(f / 100.0)) < 0.05
    # a narrow-enough range that Q_HI allows keeps the fixed edge exactly
    f, q = ui_bands.drag_edge(lo, hi, "lo", 380.0)
    assert edges(f, q) == pytest.approx((380.0, 400.0))


def test_band_under_picks_the_narrowest():
    specs = [(20.0, 20000.0), (100.0, 400.0), (150.0, 300.0)]
    assert ui_bands.band_under(specs, 200.0) == 2
    assert ui_bands.band_under(specs, 120.0) == 1
    assert ui_bands.band_under(specs, 5000.0) == 0
    assert ui_bands.band_under(specs, 5.0) is None


def test_pooled_keeps_peaks_and_turns_the_map():
    spec = np.full((HIST_T, HIST_F), HIST_FLOOR, dtype=np.float32)
    spec[3, 7] = -10.0        # early in time, low in frequency
    spec[-1, -1] = -5.0       # now, at the top
    m = ui_bands.pooled(spec)
    assert m.shape == (HIST_F // 2, HIST_T // 2) and m.dtype == np.float32
    assert m.flags["C_CONTIGUOUS"]
    assert m[0, -1] == -5.0                         # top row = highest bin, last column = now
    assert m[HIST_F // 2 - 1 - 3, 1] == -10.0       # row 3 from the bottom, column 1
    assert (m == HIST_FLOOR).sum() == m.size - 2


def test_history_fills_from_a_fed_analyser(rig):
    """A tone lands in the ring at its bin — what the heat map shows."""
    chain = rig.chain
    sr = chain.an.sample_rate
    t = np.arange(FFT_SIZE) / sr
    chain.an.feed(0.5 * np.sin(2 * np.pi * 1000.0 * t))
    for _ in range(6):
        chain.step(HIST_DT)
    spec, freqs = chain.history()
    assert spec.shape == (HIST_T, HIST_F) and len(freqs) == HIST_F
    col = spec[-1]
    assert col.max() > -40 and abs(freqs[int(col.argmax())] - 1000) < 60
    assert spec[0].max() == HIST_FLOOR             # the ring is mostly unwritten


# ------------------------------------------------------- registry writes

def test_apply_fq_writes_through_the_registry(rig):
    reg, chain = rig.reg, rig.chain
    ui_bands.apply_fq(reg, 1, *ui_bands.fit_box(200.0, 800.0))
    assert chain.edges(1) == pytest.approx((200.0, 800.0))
    assert reg["band.1.f"].value == pytest.approx(400.0)
    # only the centre: q keeps
    q = chain.spec[1].q
    ui_bands.apply_fq(reg, 1, f=1000.0)
    assert chain.spec[1].f == 1000.0 and chain.spec[1].q == q
    # the params clamp
    ui_bands.apply_fq(reg, 1, f=1.0, q=99.0)
    assert (chain.spec[1].f, chain.spec[1].q) == (F_LO, Q_HI)


def test_handle_writes_land_on_the_base_while_modulated(rig):
    """A lane on band.0.f: the handle moves the base, the ghost the effective."""
    reg, chain = rig.reg, rig.chain
    pf = reg["band.0.f"]
    base = pf.base
    pf.modulate(0.2)
    reg.apply()
    assert pf.modulated and pf.value > base and pf.base == pytest.approx(base)
    ui_bands.apply_fq(reg, 0, f=100.0)
    pf.modulate(0.2)
    reg.apply()
    assert pf.base == pytest.approx(100.0, rel=1e-6) and pf.value > 100.0
    assert ui_bands._base_fq(reg, 0)[0] == pytest.approx(100.0, rel=1e-6)
    reg.apply()                                     # the lane lets go
    assert not pf.modulated and chain.spec[0].f == pytest.approx(100.0, rel=1e-6)


# ------------------------------------------------------------- the page

def test_editor_draws_at_every_band_count(rig):
    panel, control, chain = rig.panel, rig.panel.control, rig.chain
    frame(panel, "analyzer")
    assert chain.n == 6
    while chain.n > 1:
        control.remove_band()
        frame(panel)
    assert chain.n == 1
    frame(panel)
    while chain.n < N_MAX:
        control.add_band()
        frame(panel)
    assert chain.n == N_MAX and control.selb < N_MAX
    frame(panel)
    # the state the editor keeps is only the gesture and the colormap id
    st = ui_bands._state(panel)
    assert st["box"] is None and st["cmap"] >= 0
    assert ui_bands.HINT and ui_bands.PLOT_H > 0


def test_editor_add_remove_follow_the_registry(rig):
    panel, reg, chain = rig.panel, rig.reg, rig.chain
    frame(panel, "analyzer")
    reg["band.add"].fire()
    assert chain.n == 7 and "band.6.f" in reg
    frame(panel)
    reg["band.select"].set(6)
    reg["band.remove"].fire()
    assert chain.n == 6 and "band.6.f" not in reg
    frame(panel)
    panel.control.move_band(0, 5)
    frame(panel)


def test_modulated_centre_draws_a_ghost_in_the_editor(rig):
    panel, reg = rig.panel, rig.reg
    frame(panel, "analyzer")
    assert panel.ghosts == 0
    reg["band.0.f"].modulate(0.15)
    reg.apply()
    frame(panel)
    # the editor's hairline, and band.sel.f's fader (band 0 is selected)
    assert panel.ghosts == 2
    reg["band.select"].set(2)
    reg["band.0.f"].modulate(0.15)
    reg.apply()
    frame(panel)
    assert panel.ghosts == 1
    reg.apply()
    frame(panel)
    assert panel.ghosts == 0
