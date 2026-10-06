"""Plan 22 B1: the face patterns' eight inputs mean one thing each, in every
mode — the convention in hyperspace/patterns.py, which the registry, the
shader's header and its named accessors are held to here, and which the
rendered faces are held to by pixels (Renderer.pattern_tile: one face's
pattern alone, offscreen).

The contact sheets a person judges are tools/pattern_sheet.py's, in
docs/plans/assets/22-face-patterns/.
"""

import re
import shutil
import subprocess
import sys
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from hyperspace import patterns
from hyperspace.patterns import INPUTS, MODES, N_INPUTS

ROOT = Path(__file__).resolve().parents[1]
SHADER = ROOT / "hyperspace" / "shaders" / "patterns.glsl"
T, FID = 4.0, 5.0          # a still's time, and a face other than 0 (SPREAD shows)


# ---- the table ----

def test_every_mode_says_what_each_of_the_eight_inputs_does():
    from hyperspace.params import PATTERNS
    from hyperspace.view import N_MOD

    assert N_INPUTS == N_MOD == 8
    assert PATTERNS == [m.name for m in MODES]
    for m in MODES:
        assert m.name.isupper() and m.about, m
        assert len(m.does) == N_INPUTS, m.name
        assert all(isinstance(d, str) for d in m.does), m.name


def test_the_inputs_have_short_distinct_capital_names_and_say_what_they_mean():
    names = [i.name for i in INPUTS]
    assert names == ["SCALE", "GLOW", "WARP", "SPEED", "COLOUR", "SHARP", "HUE", "SPREAD"]
    assert len(set(names)) == N_INPUTS
    for k, i in enumerate(INPUTS):
        assert i.name.isupper() and len(i.name) <= 8
        assert "1 as designed" in i.meaning, i.name       # 1.0 is the un-driven look
        assert i.why and patterns.INDEX[i.name] == k


def test_only_flat_ignores_an_input():
    """The holes are rare: FLAT runs no pattern at all; every other mode
    reads every input."""
    assert patterns.ignores(0) == list(range(N_INPUTS))
    for mode in range(1, len(MODES)):
        assert patterns.ignores(mode) == [], MODES[mode].name


def test_the_registry_labels_and_tips_come_from_the_table(tmp_path):
    from test_params import make

    r = make(tmp_path)[0]
    for k, i in enumerate(INPUTS):
        p = r[f"pattern.mod.{k}"]
        assert p.label == patterns.label(k) == f"Pattern {i.name.lower()}"
        assert p.tip == patterns.tip(k) and i.meaning in p.tip
        assert (p.lo, p.hi) == (0.0, 2.6)
    assert all(i.name in r["view.pattern"].tip for i in INPUTS)


def test_the_factory_routes_put_lane_i_on_input_i():
    """The order is designed for this: SUB → SCALE … AIR → SHARP."""
    from hyperspace.bands import BANDS
    from hyperspace.routing import legacy6_routes

    rows = {b.source: b.target for b in legacy6_routes() if b.target.startswith("pattern.")}
    assert rows == {f"lane:{i}": f"pattern.mod.{i}" for i in range(len(BANDS))}
    assert len(BANDS) == 6 and patterns.HUE == 6 and patterns.SPREAD == 7


# ---- the shader keeps the same convention ----

def test_the_shader_names_each_input_at_its_index():
    src = SHADER.read_text()
    for k, i in enumerate(INPUTS):
        assert re.search(rf"^//\s+{k} {i.name}\b", src, re.MULTILINE), f"header: {k} {i.name}"
        assert re.search(rf"float m_{i.name.lower()}\(\)\s*{{ return u_mod\[{k}\]; }}", src), (
            f"no m_{i.name.lower()}() reading u_mod[{k}]")


def test_the_modes_read_the_inputs_only_by_name():
    """u_mod[k] appears only in the accessors; the modes call m_*() and
    the helpers built on them."""
    code = "\n".join(ln for ln in SHADER.read_text().splitlines()
                     if not ln.lstrip().startswith("//"))
    raw = [ln for ln in code.splitlines() if "u_mod[" in ln]
    assert len(raw) == N_INPUTS and all(ln.startswith("float m_") for ln in raw), raw


def test_the_shader_has_a_case_for_every_mode_in_the_table():
    cases = {int(n) for n in re.findall(r"mode == (\d+)", SHADER.read_text())}
    assert cases == set(range(len(MODES)))


@pytest.mark.skipif(shutil.which("glslangValidator") is None,
                    reason="glslangValidator (the Khronos reference compiler) not installed")
def test_the_face_shaders_pass_the_reference_compiler():
    """Mesa is lenient where Apple's GL 4.1 compiler is not; glslang holds
    #version 330 to the letter (tools/check_glsl.py)."""
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "check_glsl.py")],
                         capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stdout + out.stderr


# ---- the pixels ----

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def tiles():
    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    r = Renderer(ctx)
    assert r.pattern_error == ""

    def tile(mode, k=0, v=1.0, fid=FID, t=T):
        mods = [1.0] * N_INPUTS
        mods[k] = v
        s = ViewState(pattern=mode, pattern_mod=mods)
        return r.pattern_tile(s, 64, t, fid).astype(float)

    yield tile
    ctx.release()


@pytest.mark.parametrize("mode", range(1, len(MODES)), ids=[m.name for m in MODES[1:]])
def test_every_input_moves_every_mode_from_1_to_2_6(tiles, mode):
    for k, i in enumerate(INPUTS):
        d = np.abs(tiles(mode, k, 2.6) - tiles(mode, k, 1.0)).mean()
        assert d > 5.0, f"{MODES[mode].name}: {i.name} 1.0 → 2.6 barely moves the face ({d:.2f})"


def test_flat_reads_no_input(tiles):
    base = tiles(0)
    for k in range(N_INPUTS):
        assert np.array_equal(tiles(0, k, 2.6), base)


@pytest.mark.parametrize("mode", range(1, len(MODES)), ids=[m.name for m in MODES[1:]])
def test_glow_brightens_every_mode_steadily(tiles, mode):
    means = [tiles(mode, patterns.GLOW, v).mean() for v in (0.0, 0.5, 1.0, 1.8, 2.6)]
    assert all(a < b for a, b in pairwise(means)), means


@pytest.mark.parametrize("mode", range(1, len(MODES)), ids=[m.name for m in MODES[1:]])
def test_colour_at_0_is_grey_on_every_mode(tiles, mode):
    img = tiles(mode, patterns.COLOUR, 0.0)
    assert (img.max(axis=2) - img.min(axis=2)).max() <= 2
    assert img.max() > 20                           # grey, not gone


@pytest.mark.parametrize("mode", range(1, len(MODES)), ids=[m.name for m in MODES[1:]])
def test_spread_at_0_plays_every_face_in_unison(tiles, mode):
    for fid in (1.0, 5.0, 719.0):                   # 719: the 120-cell's last face
        assert np.array_equal(tiles(mode, patterns.SPREAD, 0.0, fid=fid),
                              tiles(mode, patterns.SPREAD, 0.0, fid=0.0)), fid


@pytest.mark.parametrize("mode", range(1, len(MODES)), ids=[m.name for m in MODES[1:]])
def test_speed_at_0_is_frozen(tiles, mode):
    assert np.array_equal(tiles(mode, patterns.SPEED, 0.0, t=1.0),
                          tiles(mode, patterns.SPEED, 0.0, t=9.0))


@pytest.mark.parametrize("mode", range(1, len(MODES)), ids=[m.name for m in MODES[1:]])
def test_hue_turns_the_palette_and_keeps_the_shape(tiles, mode):
    """HUE moves colour, not structure: the light (the max channel's
    spread aside) stays put while the channels change."""
    a, b = tiles(mode, patterns.HUE, 1.0), tiles(mode, patterns.HUE, 1.5)
    assert np.abs(a - b).mean() > 3.0
    la, lb = a @ [0.299, 0.587, 0.114], b @ [0.299, 0.587, 0.114]
    assert np.corrcoef(la.ravel(), lb.ravel())[0, 1] > 0.8


# ---- SPEED is a rate: the patterns' clock is integrated ----

def test_moving_speed_changes_the_rate_and_never_jumps_the_clock():
    """t · SPEED would jump a pattern by t · ΔSPEED — minutes into a set,
    a band on SPEED would strobe. The renderer integrates instead."""
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    r = Renderer.__new__(Renderer)          # the clock needs no GL
    r._ptime, r._ptime_at = 0.0, None
    s = ViewState()
    assert r._pattern_clock(s, 600.0) == 600.0            # the first frame anchors
    assert r._pattern_clock(s, 600.0) == 600.0            # a second pass, same frame
    s.pattern_mod[patterns.SPEED] = 2.0
    assert r._pattern_clock(s, 600.0) == 600.0            # no jump where it changed
    assert r._pattern_clock(s, 601.0) == pytest.approx(602.0)
    s.pattern_mod[patterns.SPEED] = 0.0
    assert r._pattern_clock(s, 640.0) == pytest.approx(602.0)   # frozen where it was
    assert r._pattern_clock(s, 3.0) == 0.0                # a clock run back re-anchors
