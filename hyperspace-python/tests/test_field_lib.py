"""The shared field pieces in `shaders/fx/_lib.glsl`: `point_at`,
`from_point`, the measures (`measure_line`, `measure_rings`,
`measure_spokes`, `measure_cells`), `read_signed`, and the ops (`quantise`,
`threshold_soft`, `remap`, `combine`).

They are written once so every effect file that still computes a field inline
and every field node to come compute it the same way, to the bit. What is held
here:

- each piece against a numpy oracle, run in the real library on the GPU into a
  float32 target (so a rounding is the GPU's, not the readback's);
- no effect file carries its own copy of the pieces that were moved onto the
  library (a centre read from Centre X/Y, the soft key, a cell rule): no private copy of another primitive. Hue cycle is outside it.

Wave, Blocks, Displace, Blend, Prism, Zoom burst, Time Displace and Oil
slick render the same bytes through the pieces as with their own inline code."""

from __future__ import annotations

import math
import re

import numpy as np
import pytest

from hyperspace.fx import FS_HEAD, FX_DIR, FxState
from hyperspace.glsl import QUAD_VS, common

moderngl = pytest.importorskip("moderngl")

W, H = 48, 32
TAU = 2.0 * math.pi


def _run(ctx, body: str, **uniforms) -> np.ndarray:
    """`body` (a GLSL expression of `v_uv` giving a vec4) evaluated at every
    pixel through the real library, read back as float32 (H, W, 4)."""
    lib = FxState().lib
    src = f"{FS_HEAD}{common()}\n{lib}\nuniform float u_a; uniform float u_b; uniform int u_k;\n" \
          f"void main() {{ vec2 uv = v_uv; f_color = {body}; }}\n"
    prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=src)
    for k, v in {"u_res": (float(W), float(H)), **uniforms}.items():
        if k in prog:
            prog[k].value = v
    tex = ctx.texture((W, H), 4, dtype="f4")
    fbo = ctx.framebuffer(color_attachments=[tex])
    fbo.use()
    ctx.disable(moderngl.BLEND)
    ctx.vertex_array(prog, []).render(moderngl.TRIANGLES, vertices=3)
    out = np.frombuffer(fbo.read(components=4, dtype="f4"), np.float32).reshape(H, W, 4).copy()
    for o in (fbo, tex, prog):
        o.release()
    return out


def _uv():
    x = (np.arange(W) + 0.5) / W
    y = (np.arange(H) + 0.5) / H
    return np.meshgrid(x, y)


def _centred():
    u, v = _uv()
    return (u - 0.5) * (W / H), v - 0.5


def _close(a, b, tol=2e-5):
    assert np.allclose(a, b, atol=tol, rtol=tol), float(np.abs(a - b).max())


# ---------------------------------------------------------------- point

def test_a_point_is_centre_x_and_y_in_frame_heights(ctx):
    got = _run(ctx, "vec4(point_at(u_a, u_b), from_point(uv, u_a, u_b))", u_a=-0.6, u_b=0.8)
    cx, cy = -0.6 * 0.5 * W / H, 0.8 * 0.5
    _close(got[..., 0], cx)
    _close(got[..., 1], cy)
    px, py = _centred()
    _close(got[..., 2], px - cx)
    _close(got[..., 3], py - cy)


def test_the_edges_are_minus_one_and_one():
    """A point at Centre X 1 sits on the right edge, Y −1 on the bottom: half
    the width and half the height from the middle, in frame heights."""
    assert 1 * 0.5 * W / H == pytest.approx((W / H) / 2)


# ---------------------------------------------------------------- measures

@pytest.mark.parametrize("angle", [0.0, 0.7, math.pi / 2, 4.0])
def test_a_line_is_the_distance_along_its_angle(ctx, angle):
    got = _run(ctx, "vec4(measure_line(centred(uv), u_a).x, measure_line(centred(uv), u_a).g, 0.0)",
               u_a=angle)
    px, py = _centred()
    g = (math.cos(angle), math.sin(angle))
    _close(got[..., 0], px * g[0] + py * g[1])
    _close(got[..., 1], g[0])
    _close(got[..., 2], g[1])


def test_rings_are_the_distance_from_the_point_and_grow_outward(ctx):
    got = _run(ctx, "vec4(measure_rings(from_point(uv, u_a, u_b)).x, "
                    "measure_rings(from_point(uv, u_a, u_b)).g, 0.0)", u_a=0.3, u_b=-0.2)
    px, py = _centred()
    qx, qy = px - 0.3 * 0.5 * W / H, py + 0.2 * 0.5
    r = np.hypot(qx, qy)
    _close(got[..., 0], r)
    _close(got[..., 1], qx / r, 1e-4)
    _close(got[..., 2], qy / r, 1e-4)
    assert np.allclose(np.hypot(got[..., 1], got[..., 2]), 1.0, atol=1e-4)


def test_spokes_are_turns_round_the_point_and_grow_anticlockwise(ctx):
    got = _run(ctx, "vec4(measure_spokes(centred(uv)).x, measure_spokes(centred(uv)).g, 0.0)")
    px, py = _centred()
    _close(got[..., 0], np.arctan2(py, px) / TAU, 1e-4)
    assert got[..., 0].min() >= -0.5 and got[..., 0].max() <= 0.5
    r = np.hypot(px, py)
    _close(got[..., 1], -py / r, 1e-4)
    _close(got[..., 2], px / r, 1e-4)


def test_the_centre_of_rings_has_no_direction(ctx):
    got = _run(ctx, "vec4(measure_rings(vec2(0.0)).g, measure_spokes(vec2(0.0)).g)")
    assert np.all(got == 0.0)


@pytest.mark.parametrize("rule", range(5))
def test_cells_follow_their_rule(ctx, rule):
    """The cell `id` is the pixel's column − 24 and row − 16, so every rule
    meets negative and positive cells."""
    got = _run(ctx, "vec4(measure_cells(floor(uv * u_res) - vec2(24.0, 16.0), u_k, u_a))",
               u_k=rule, u_a=0.5)[..., 0]
    ix = np.arange(W)[None, :] - 24.0
    iy = np.arange(H)[:, None] - 16.0
    ix, iy = np.broadcast_to(ix, (H, W)), np.broadcast_to(iy, (H, W))
    want = {0: iy * 0.5, 1: ix * 0.5, 2: (ix + iy) * 0.5,
            3: np.maximum(np.abs(ix), np.abs(iy)) * 0.5}.get(rule)
    if want is None:      # random: a hash, the same in every cell of one id; in 0 … 32
        assert got.min() >= 0.0 and got.max() <= 32.0 and len(np.unique(got)) > W
        again = _run(ctx, "vec4(measure_cells(floor(uv * u_res) - vec2(24.0, 16.0), u_k, u_a))",
                     u_k=rule, u_a=0.0)[..., 0]
        assert np.all(again == 0.0)        # Spread 0: every cell in step
        return
    _close(got, want)


# ---------------------------------------------------------------- picture reads

def test_read_signed_is_zero_at_mid_grey_and_on_a_see_through_pixel(ctx):
    got = _run(ctx, "vec4(read_signed(uv.x, 1.0), read_signed(0.0, 0.0), read_signed(vec2(uv.x, 0.25), 0.5))")
    u, _ = _uv()
    _close(got[..., 0], (u - 0.5) * 2.0)
    assert np.all(got[..., 1] == 0.0)
    _close(got[..., 2], (u - 0.25) * 2.0)
    _close(got[..., 3], 0.0)


# ---------------------------------------------------------------- ops

@pytest.mark.parametrize("steps", [0, 1, 3, 8])
def test_quantise_rounds_to_steps_each_side_of_zero(ctx, steps):
    """The oracle reads x back from the GPU and rounds in float32: a pixel whose
    x · steps + ½ lands on a whole number is decided by the last bit."""
    out = _run(ctx, "vec4(quantise(uv.x * 2.0 - 1.0, u_k), uv.x * 2.0 - 1.0, 0.0, 0.0)", u_k=steps)
    got, x = out[..., 0], out[..., 1]
    s = np.float32(steps)
    want = x if steps == 0 else np.floor(x * s + np.float32(0.5)) / s
    _close(got, want)
    if steps:
        assert len(np.unique(got)) <= 2 * steps + 1


def test_a_soft_key_ramps_across_key_and_softness(ctx):
    got = _run(ctx, "vec4(threshold_soft(uv.x, u_a, u_b), threshold_soft(uv.x, u_a, 0.0), 0.0, 0.0)",
               u_a=0.5, u_b=0.1)
    u, _ = _uv()
    _close(got[..., 0], np.clip((u - 0.5 + 0.1) / 0.2, 0.0, 1.0), 1e-4)
    assert set(np.unique(got[..., 1])) <= {0.0, 1.0}            # soft 0: a hard step
    assert np.all(got[..., 1][u > 0.5 + 1e-3] == 1.0) and np.all(got[..., 1][u < 0.5 - 1e-3] == 0.0)


def test_remap_and_combine(ctx):
    got = _run(ctx, "vec4(remap(uv.x, 0.0, 1.0, -2.0, 2.0), combine(uv.x, uv.y, u_k), "
                    "combine(uv.x, uv.y, 0), combine(uv.x, uv.y, 3))", u_k=1)
    u, v = _uv()
    _close(got[..., 0], u * 4.0 - 2.0)
    _close(got[..., 1], u * v)
    _close(got[..., 2], u + v)
    _close(got[..., 3], np.maximum(u, v))
    mn = _run(ctx, "vec4(combine(uv.x, uv.y, 2))")[..., 0]
    _close(mn, np.minimum(u, v))


# ---------------------------------------------------------------- one copy

def _code(name: str) -> str:
    """A file's code with its comments and `@param` lines' tips taken out."""
    text = (FX_DIR / f"{name}.glsl").read_text()
    return "\n".join(re.sub(r"//.*$", "", line) for line in text.splitlines())


def _effects() -> list[str]:
    return sorted(p.stem for p in FX_DIR.glob("*.glsl") if not p.stem.startswith("_"))


def test_a_centre_is_read_only_through_point_at():
    """Centre X / Centre Y become a place in one function: no file spells out
    `u_cx * 0.5 …` for itself."""
    spelled = [n for n in _effects() if re.search(r"u_cx\s*\*\s*0\.5", _code(n))]
    assert spelled == []
    readers = [n for n in _effects() if "u_cx" in _code(n)]
    assert readers and all("point_at" in _code(n) or "from_point" in _code(n) for n in readers)


def test_the_soft_key_and_the_cell_rule_are_written_once():
    for n in _effects():
        code = _code(n)
        assert "max(2.0 * u_soft" not in code, n            # threshold_soft
        assert "hash21(id + 64.5) * 64.0" not in code, n     # measure_cells


def test_the_moved_files_call_the_pieces():
    want = {"wave": ("measure_", "from_point", "quantise"), "blocks": ("measure_cells",),
            "displace": ("read_signed", "pushed"), "blend": ("threshold_soft",),
            "prism": ("measure_rings", "from_point"), "zoomblur": ("point_at",),
            "oilslick": ("measure_rings",)}
    for name, calls in want.items():
        for c in calls:
            assert c in _code(name), (name, c)
