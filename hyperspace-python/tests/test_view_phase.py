"""K3 (register row 578): `view.inst_rate` and `view.media_rate` are
integrated by the host (`ViewState.integrate`) into `inst_phase` and
`media_phase`; the draw reads the phase, never t × rate. A knob step on
either changes how fast the motion goes and never where it is — the same
rule as the turn, the pattern clock (row 99) and an effect's `@clock`
(row 560). Pure numpy: no GL.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pytest

from hyperspace import field as F
from hyperspace.view import INST_PERIOD, MEDIA_PERIOD, ViewState

PKG = Path(__file__).resolve().parents[1] / "hyperspace"
DT = 1 / 60


def _run(s: ViewState, frames: int) -> list[tuple[float, float]]:
    out = []
    for _ in range(frames):
        s.integrate(DT)
        out.append((s.inst_phase, s.media_phase))
    return out


# ---------------------------------------------------------------- the integrator

def test_a_rate_step_changes_the_slope_not_the_value():
    s = ViewState(inst_rate=1.0, media_rate=1.0)
    _run(s, 60)
    assert s.inst_phase == pytest.approx(1.0) and s.media_phase == pytest.approx(1.0)
    before = (s.inst_phase, s.media_phase)
    s.inst_rate, s.media_rate = 6.0, 0.0           # a knob step on each
    assert (s.inst_phase, s.media_phase) == before  # the step alone moves nothing
    s.integrate(DT)
    assert s.inst_phase - before[0] == pytest.approx(6.0 * DT)   # the new slope
    assert s.media_phase == pytest.approx(before[1])               # rate 0: it stands
    _run(s, 59)
    assert s.inst_phase == pytest.approx(1.0 + 6.0)


def test_from_rest_at_a_constant_rate_the_phase_is_rate_times_t():
    """What the draw read before K3 (t × rate from t = 0), so a picture at a
    constant rate is the picture it was."""
    s = ViewState(inst_rate=1.4, media_rate=0.7)
    _run(s, 90)
    assert s.inst_phase == pytest.approx(1.4 * 1.5) and s.media_phase == pytest.approx(0.7 * 1.5)


@pytest.mark.parametrize("t", (0.0, 2.0, 37.5))
def test_seeding_then_integrating_is_rate_times_t(t):
    """`seed_phases(t)` (a pinned clock's start: the golden harness, the
    shot tools) then k frames of `integrate` read (t + k·dt) · rate, the
    phase t × rate gave before K3, wrapped."""
    s = ViewState(inst_rate=1.4, media_rate=0.7)
    s.seed_phases(t)
    _run(s, 30)
    end = t + 30 * DT
    assert s.inst_phase == pytest.approx((end * 1.4) % INST_PERIOD, abs=1e-9)
    assert s.media_phase == pytest.approx((end * 0.7) % MEDIA_PERIOD, abs=1e-9)


def test_the_phases_run_while_the_turn_is_paused():
    """`playing` pauses the turn; the field and the path ran on the wall
    clock before K3 and still run."""
    s = ViewState(playing=False)
    _run(s, 30)
    assert s.inst_phase == pytest.approx(0.5) and s.media_phase == pytest.approx(0.5)


def test_the_wrap_is_a_whole_period_of_every_use():
    """The phases wrap so they never grow, at a period of every use: the
    path reads ph and 2·ph; the field reads ph, 0.7·ph and 0.9·ph."""
    for k in (1.0, 2.0):
        assert math.isclose(math.sin(k * MEDIA_PERIOD), 0.0, abs_tol=1e-12)
    for k in (1.0, 0.7, 0.9):
        assert math.isclose(math.sin(k * INST_PERIOD), 0.0, abs_tol=1e-12)
        assert math.isclose(math.cos(k * INST_PERIOD), 1.0, abs_tol=1e-12)
    s = ViewState(inst_rate=6.0, media_rate=6.0)
    for _ in range(60 * 20):                        # 20 s at the top of the knob
        s.integrate(DT)
        assert 0.0 <= s.inst_phase < INST_PERIOD and 0.0 <= s.media_phase < MEDIA_PERIOD
    assert s.inst_phase == pytest.approx((6.0 * 20) % INST_PERIOD, abs=1e-9)


@pytest.mark.parametrize("motion", (1, 2, 3))
@pytest.mark.parametrize("layout", (0, 3))
def test_the_wrap_moves_no_copy(motion, layout):
    """The field drawn at the phase just past the wrap is the field drawn
    at the unwrapped phase: the wrap is invisible."""
    def at(ph):
        return F.field(ViewState(instances=19, inst_layout=layout, inst_motion=motion,
                                 inst_amp=0.5, inst_phase=ph), 1600, 900)
    for ph in (0.3, 2.0):
        assert np.allclose(at(ph), at(ph + INST_PERIOD), atol=1e-2)


# ---------------------------------------------------------------- the harness

def _max_step(a: np.ndarray, b: np.ndarray) -> float:
    """The farthest any copy moved between two frames' rows, px."""
    return float(np.hypot(*(b[:, :2] - a[:, :2]).T).max())


@pytest.mark.parametrize("motion", (1, 2, 3))
def test_a_knob_step_on_the_field_rate_moves_no_copy_further_than_one_frame(motion):
    """Ten seconds in at rate 1, the field's rate nudged to 1.5 in one
    frame: the copies move no further across the step than one frame's
    motion at the new rate — where t × rate jumped the phase by t · Δrate
    (5 rad)."""
    s = ViewState(instances=19, inst_layout=0, inst_motion=motion, inst_amp=0.5,
                  inst_rate=1.0)
    _run(s, 600)
    w, h = 1600, 900
    before = F.field(s, w, h)
    s.inst_rate = 1.5
    s.integrate(DT)
    across = _max_step(before, F.field(s, w, h))
    # one frame's motion at the new rate, measured after the step
    steps = []
    for _ in range(30):
        a = F.field(s, w, h)
        s.integrate(DT)
        steps.append(_max_step(a, F.field(s, w, h)))
    assert across <= max(steps) * 1.05 + 1e-3, (across, max(steps))
    # and the harness can see a jump: the old t × rate would have moved them
    t = 600 * DT
    old = F.field(ViewState(instances=19, inst_layout=0, inst_motion=motion, inst_amp=0.5,
                            inst_phase=(t + DT) * 1.5), w, h)
    assert _max_step(before, old) > 3 * max(steps)


# ---------------------------------------------------------------- the pin

RATES = ("inst_rate", "media_rate")
# a string that reaches a rate: the attribute's name (getattr, vars) or
# its param id (reg[...]) — exactly; a uniform or a message that merely
# contains one is not a read
RATE_NAMES = {*RATES, *(f"view.{r}" for r in RATES)}


def _rate_reads(name: str) -> list[int]:
    """Lines in `name` that reach a rate: an attribute `.inst_rate` /
    `.media_rate`, or a string naming one — `getattr(s, "media_rate")`,
    `vars(s)["inst_rate"]`, the param ids `reg["view.inst_rate"]`. A
    docstring (a string standing alone as a statement) is prose, not a read."""
    return _reads(ast.parse((PKG / name).read_text()))


def _reads(tree: ast.AST) -> list[int]:
    prose = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)}
    return [n.lineno for n in ast.walk(tree)
            if (isinstance(n, ast.Attribute) and n.attr in RATES)
            or (isinstance(n, ast.Constant) and id(n) not in prose and n.value in RATE_NAMES)]


def test_the_pin_sees_every_road_to_a_rate():
    for src in ('ph = t * s.media_rate', 'ph = t * getattr(s, "inst_rate")',
                'ph = vars(s)["media_rate"]', 'r = reg["view.inst_rate"].value'):
        assert _reads(ast.parse(src)), src
    assert not _reads(ast.parse('def f(s):\n    """reads inst_rate"""\n    return s.inst_phase'))
    for src in ('u = p["u_media_rate"]', 'log("inst_rate moved")'):
        assert not _reads(ast.parse(src)), src


@pytest.mark.parametrize("name", ("render.py", "field.py"))
def test_the_draw_reads_the_phase_never_the_rate(name):
    """No `t * s.media_rate` / `t * s.inst_rate` (DECISIONS: "No shader
    multiplies time by a param"): the draw reads no rate at all — the host
    integrated it into the phase."""
    assert _rate_reads(name) == [], f"{name} reads a rate (lines {_rate_reads(name)})"


def test_the_phases_are_not_params():
    """Integrated state, like the turn's angles: nothing writes them but
    `integrate`, so no loadable patch saves them and no knob can jump them."""
    src = (PKG / "params.py").read_text()
    assert "inst_phase" not in src and "media_phase" not in src
