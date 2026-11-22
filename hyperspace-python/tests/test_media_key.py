"""Plan 66 — black is clear: a luma key on the media channels, in the fit
pass (`media_tex.FIT_FS`, `Renderer._media_fit`), and `screen` on the
composite (`graph.BLENDS`, `Renderer.lay`).

The GL half draws through the real fit pass on a standalone context (skips
without one) and holds it to a numpy oracle; the off pass to the bytes of
the pass from before the plan; the params to their ids, defaults and
persistence; an old loadable patch to every key off."""

from __future__ import annotations

import json

import numpy as np
import pytest
from test_media_render import Still, _media

from hyperspace import graph as G
from hyperspace import masks, media_tex
from hyperspace.media import channels
from hyperspace.media.channels import CHANNELS
from hyperspace.params import Kind

KEY_IDS = ("key", "key_measure", "key_level", "key_soft", "key_keep", "key_feather",
           "key_invert")

# the fit pass as it was before plan 66, word for word: the key off must be
# its bytes (every saved look, every golden)
FIT_BEFORE = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform vec2 u_scale;      // frame uv → picture uv, about the centre (fit_scale)
uniform int u_flip;        // the texture's first row is the picture's top (an upload)
uniform float u_alpha;
out vec4 f_color;
void main() {
    vec2 uv = 0.5 + (v_uv - 0.5) * u_scale;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) {
        f_color = vec4(0.0);
        return;
    }
    if (u_flip != 0) uv.y = 1.0 - uv.y;
    vec4 c = texture(u_src, uv);
    f_color = vec4(c.rgb * c.a, c.a) * u_alpha;
}
"""


# ---------------------------------------------------------------- no GL

def test_the_constants_agree():
    assert media_tex.KEY_MEASURES == channels.KEY_MEASURES == ("peak", "luma")
    assert channels.KEY_FEATHER == masks.MAX_FEATHER


def test_key_of_is_none_while_off_and_for_a_channel_from_before():
    ch = channels.Channel("a")
    assert ch.key is False and media_tex.key_of(ch) is None
    assert media_tex.key_of(None) is None

    class Old:                     # a live channel from before the plan: no fields
        fit = 0
    assert media_tex.key_of(Old()) is None
    ch.key = True
    assert media_tex.key_of(ch) == media_tex.Key(0, 0.02, 0.1, True, 0.0, False)
    ch.key_level, ch.key_soft, ch.key_feather = -1.0, 7.0, -3.0      # held to their ranges
    k = media_tex.key_of(ch)
    assert k is not None and (k.level, k.soft, k.feather) == (0.0, 1.0, 0.0)


def test_screen_is_appended_to_the_blends():
    """Appended, never inserted; a composite saves it and reads it back."""
    assert G.BLENDS == ("over", "add", "depth", "screen")
    c = G.CompositeAt(2, "screen")
    assert c.to_json() == {"kind": "composite", "instance": 2, "blend": "screen"}
    assert G.NODE_KINDS["composite"](c.to_json()) == c


def test_screen_has_its_own_words():
    """`blend_words`, which the OUTPUT page's and the graph's words read."""
    assert G.blend_words("screen") == "screened"
    assert G.blend_words("add") == "added" and G.blend_words("depth") == "depth-aware"
    assert G.blend_words("over") == ""


# ---------------------------------------------------------------- the params

@pytest.fixture()
def rig(tmp_path):
    from test_loadable import boot
    return boot(tmp_path)


def test_the_key_params_per_channel(rig):
    """Seven a channel, group media, persisted and modulatable, off — writing
    the channel's fields."""
    reg, m = rig.reg, rig.reg.media
    for c in CHANNELS:
        ps = [reg[f"media.{c}.{k}"] for k in KEY_IDS]
        assert all(p.persist and p.modulatable and p.group == "media" for p in ps)
        key, measure, level, soft, keep, feather, invert = ps
        assert key.kind is Kind.TOGGLE and key.value is False
        assert measure.choices == ["peak", "luma"] and measure.value == 0
        assert (level.value, level.lo, level.hi) == (0.02, 0.0, 1.0)
        assert (soft.value, soft.lo, soft.hi) == (0.1, 0.0, 1.0)
        assert keep.kind is Kind.TOGGLE and keep.value is True
        assert (feather.value, feather.lo, feather.hi) == (0.0, 0.0, 32.0)
        assert invert.kind is Kind.TOGGLE and invert.value is False
        key.set(True)
        level.set(0.3)
        ch = m.channels[c]
        assert ch.key is True and ch.key_level == 0.3


def test_an_old_loadable_patch_lands_every_key_off(rig):
    """No schema move (row 907, as row 582's sound): a file from before names
    no key id and loads with no note, every key off — even after a patch that
    had one on; one that names them lands them; the save holds them."""
    from test_media_loadable import save_text

    doc = json.loads(save_text(rig, "x"))
    assert doc["values"]["media.a.key"] is False
    on = json.loads(json.dumps(doc))
    on["values"]["media.a.key"], on["values"]["media.a.key_level"] = True, 0.2
    assert rig.loaded_patch.load_doc(on) == [] and rig.loaded_patch.notes == []
    assert rig.reg["media.a.key"].value is True and rig.reg["media.a.key_level"].value == 0.2
    old = json.loads(json.dumps(doc))
    for c in CHANNELS:
        for k in KEY_IDS:
            del old["values"][f"media.{c}.{k}"]
    assert rig.loaded_patch.load_doc(old) == [] and rig.loaded_patch.notes == []
    assert all(rig.reg[f"media.{c}.key"].value is False for c in CHANNELS)
    assert rig.reg["media.a.key_level"].value == 0.02
    assert json.loads(save_text(rig, "y"))["schema"] == old["schema"]


# ---------------------------------------------------------------- the panel

@pytest.mark.parametrize("layout", ["band", "min", "default"])
def test_black_is_clear_on_the_media_page_by_the_mouse(tmp_path, monkeypatch, layout):
    """MEDIA, channel A, driven by control id (tests/ui_driver.py): the
    switch is drawn and its knobs are not; a click turns it on and the
    level, softness, measure, feather, keep colour and invert appear, none
    past the pane's right edge at any width; a typed level lands; a second
    click turns it off and the knobs go."""
    from test_ui_pane import _focus_rig, _spills, _st
    from test_ui_shell import build_rig

    from hyperspace.ui import PAGE_KEYS

    knobs = [f"media.a.{k}" for k in KEY_IDS[1:]]
    with build_rig(tmp_path) as r:
        d = _focus_rig(r, monkeypatch, layout)
        r.reg["ui.page"].set(PAGE_KEYS.index("media"))
        d.run(d.wait(4))
        assert "media.a.key" in d.rects and not any(k in d.rects for k in knobs)
        d.run(d.click("media.a.key"), d.park(), d.wait(2))
        assert r.reg["media.a.key"].value is True
        assert all(k in d.rects for k in knobs), sorted(k for k in knobs if k not in d.rects)
        assert not _spills(d, _st(r)), sorted(_spills(d, _st(r)))
        d.run(d.enter("media.a.key_level", 0.1))
        assert r.reg["media.a.key_level"].value == pytest.approx(0.1)
        d.run(d.click("media.a.key"), d.park(), d.wait(2))
        assert r.reg["media.a.key"].value is False
        assert not any(k in d.rects for k in knobs)


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")

W, H = 16, 8


def _still() -> np.ndarray:
    """A W×H still, top row first: a grey ramp across the top half (0 to
    255), a colour per column below it (pure blue, red, dark green …), and
    a PNG's own alpha falling across the bottom rows."""
    px = np.zeros((H, W, 4), np.uint8)
    px[..., 3] = 255
    ramp = np.array([0, 1, 3, 5, 8, 13, 20, 26, 31, 40, 64, 96, 128, 180, 230, 255], np.uint8)
    px[: H // 2, :, :3] = ramp[None, :, None]
    cols = np.array([(0, 0, 255), (255, 0, 0), (0, 20, 0), (10, 10, 40), (200, 180, 20),
                     (3, 2, 1), (0, 0, 0), (60, 0, 60)] * 2, np.uint8)
    px[H // 2:, :, :3] = cols[None, :, :]
    px[-2:, :, 3] = np.linspace(0, 255, W).astype(np.uint8)[None, :]
    return px


def _oracle(px: np.ndarray, *, measure=0, level=0.02, soft=0.1, keep=True, invert=False,
            alpha=1.0) -> np.ndarray:
    """What `FIT_FS` makes of `px` keyed, as floats 0–255 (rows top first)."""
    c = px.astype(np.float64) / 255.0
    rgb, a = c[..., :3], c[..., 3:]
    m = (rgb @ np.array([0.2126, 0.7152, 0.0722]) if measure == 1 else rgb.max(-1))[..., None]
    if soft > 0:
        t = np.clip((m - level) / soft, 0.0, 1.0)
        k = t * t * (3 - 2 * t)
    else:
        k = (m > level).astype(np.float64)
    if invert:
        k = 1.0 - k
    cover = a * k
    out_rgb = rgb * (a if keep and not invert else cover)
    return np.concatenate([out_rgb, cover], -1) * alpha * 255.0


def _renderer(ctx, media):
    from test_media_render import _renderer as make
    r = make(ctx, media, wires=[G.Wire("media.a", "output.1.image")])
    return r


def _fit(r, size=(W, H), alpha=1.0) -> np.ndarray:
    """Channel a fitted (stretch) at `size`, read back rows top first, as ints."""
    r._media_frame_now().clear()
    tex = r._media_fit("a", size, alpha)
    assert r.ctx.error == "GL_NO_ERROR"
    raw = np.frombuffer(tex.read(), np.uint8).reshape(size[1], size[0], 4)
    return raw[::-1].astype(int)


def _keyed(ctx, **kw):
    m = _media(a=Still(_still()))
    ch = m.channels["a"]
    ch.fit = 2                                      # stretch: 1:1 at W×H
    ch.key = True
    for k, v in kw.items():
        setattr(ch, f"key_{k}", v)
    return _renderer(ctx, m), m


@pytest.mark.parametrize("kw", [
    {},                                                   # the ask's defaults
    {"measure": 1},                                       # luma: pure blue goes
    {"level": 0.2, "soft": 0.0},                          # a hard edge
    {"level": 0.0, "soft": 1.0},                          # the widest ramp
    {"keep": False},                                      # colour goes with alpha
    {"invert": True},                                     # white is clear
    {"invert": True, "keep": False},
])
def test_the_key_matches_its_oracle(ctx, kw):
    """Through the real fit pass, within a step of 8-bit rounding — pure black
    always clear, the source's own alpha kept under the key."""
    r, _ = _keyed(ctx, **kw)
    got = _fit(r)
    want = _oracle(_still(), **{k: v for k, v in kw.items()})
    assert np.abs(got - want).max() <= 1.5
    if not kw.get("invert"):
        assert (got[: H // 2, 0] == 0).all()               # pure black is clear


def test_the_backdrops_fader_multiplies_the_keyed_picture(ctx):
    r, _ = _keyed(ctx)
    got = _fit(r, alpha=0.5)
    assert np.abs(got - _oracle(_still(), alpha=0.5)).max() <= 1.5


def test_luma_clears_a_dark_colour_that_peak_keeps(ctx):
    """Pure blue: peak 1 (solid), luma 0.07 (in the ramp: mostly clear)."""
    peak, _ = _keyed(ctx)
    luma, _ = _keyed(ctx, measure=1, level=0.1)
    assert _fit(peak)[H // 2, 0, 3] == 255
    assert _fit(luma)[H // 2, 0, 3] == 0


def test_off_is_the_pass_from_before_byte_for_byte(ctx):
    """The key off (the default) writes exactly what the pass before plan 66
    wrote, on a random still with its own alpha, at an opacity and in each
    fit — so no saved look and no golden moves."""
    from hyperspace.glsl import QUAD_VS
    from hyperspace.media_tex import fit_scale

    rng = np.random.default_rng(66)
    px = rng.integers(0, 256, (23, 37, 4), dtype=np.uint8)
    m = _media(a=Still(px))
    r = _renderer(ctx, m)
    prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=FIT_BEFORE)
    vao = ctx.vertex_array(prog, [])
    size = (48, 40)
    out = ctx.texture(size, 4)
    fbo = ctx.framebuffer(color_attachments=[out])
    for fit in range(3):
        for alpha in (1.0, 0.37):
            m.channels["a"].fit = fit
            got = _fit(r, size, alpha)
            src = r.media_texture("a")
            fbo.use()
            ctx.viewport = (0, 0, *size)
            ctx.disable(moderngl.BLEND)
            src.use(location=0)
            prog["u_src"].value = 0
            prog["u_scale"].value = fit_scale(fit, tuple(src.size), size)
            prog["u_flip"].value = 1
            prog["u_alpha"].value = alpha
            vao.render(moderngl.TRIANGLES, vertices=3)
            ctx.enable(moderngl.BLEND)
            before = np.frombuffer(out.read(), np.uint8).reshape(size[1], size[0], 4)[::-1]
            assert (got == before.astype(int)).all(), (fit, alpha)


def test_the_feather_blurs_the_alpha_alone_and_only_when_asked(ctx):
    """Feather 0 runs no blur; above 0 the ramp is blurred (`MaskPasses.
    feather`) and the clear edge is softer — the colour, kept, untouched."""
    px = np.zeros((32, 32, 4), np.uint8)
    px[..., 3] = 255
    px[:, 16:, :3] = 200                          # black left, grey right
    m = _media(a=Still(px))
    ch = m.channels["a"]
    ch.fit, ch.key = 2, True
    r = _renderer(ctx, m)
    calls = []
    passes = r.mask_passes()
    real = passes.feather
    passes.feather = lambda *a, **k: calls.append(a) or real(*a, **k)
    hard = _fit(r, (32, 32))
    assert calls == []
    assert hard[8, 15, 3] == 0 and hard[8, 16, 3] == 255
    ch.key_feather = 4.0
    soft = _fit(r, (32, 32))
    assert len(calls) == 1 and calls[0][2] == 4.0
    assert 0 < soft[8, 15, 3] < 255 and 0 < soft[8, 16, 3] < 255
    assert soft[8, 0, 3] == 0 and soft[8, 31, 3] == 255     # far from the edge: as it was
    assert (soft[:, 16:, :3] == 200).all()                    # keep colour: rgb untouched
    assert r.ctx.error == "GL_NO_ERROR"


def test_the_feather_does_not_eat_the_pictures_edge_at_the_letterbox(ctx):
    """Contain: the ramp is sampled clamped into the picture, so a grey still
    letterboxed keeps its edge rows solid with a feather."""
    px = np.full((8, 32, 4), 200, np.uint8)
    px[..., 3] = 255
    m = _media(a=Still(px))
    ch = m.channels["a"]
    ch.fit, ch.key, ch.key_feather = 1, True, 6.0
    r = _renderer(ctx, m)
    got = _fit(r, (32, 32))
    inside = got[got[..., 3] > 0]
    assert len(inside) and (inside[..., 3] == 255).all()


def _lay(ctx, blend: str, under, over, opaque: bool) -> np.ndarray:
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    size = (4, 1)
    tex = ctx.texture(size, 4, np.array(over, np.uint8).tobytes())
    dst = ctx.texture(size, 4, np.array(under, np.uint8).tobytes())
    fbo = ctx.framebuffer(color_attachments=[dst])
    assert r.lay(tex, fbo, (0, 0, *size), blend=blend, alpha=1.0, opaque=opaque)
    return np.frombuffer(dst.read(), np.uint8).reshape(4, 4).astype(int)


def test_a_screen_lay_is_premultiplied_screen(ctx):
    """`src + dst·(1 − src)` per colour channel; alpha as over on a see-through
    ground, left as it is on an opaque one. Black adds nothing; white stays
    white; nothing passes 255."""
    under = [(100, 150, 200, 255), (100, 150, 200, 255), (255, 255, 255, 255), (60, 0, 0, 128)]
    over = [(0, 0, 0, 0), (128, 64, 255, 255), (255, 255, 255, 255), (100, 100, 100, 128)]
    for opaque in (False, True):
        got = _lay(ctx, "screen", under, over, opaque)
        u, o = np.array(under, float) / 255, np.array(over, float) / 255
        rgb = o[:, :3] + u[:, :3] * (1 - o[:, :3])
        a = u[:, 3] if opaque else o[:, 3] + u[:, 3] * (1 - o[:, 3])
        want = np.concatenate([rgb, a[:, None]], -1) * 255
        assert np.abs(got - want).max() <= 1.5, opaque
    added = _lay(ctx, "add", under, over, True)
    assert added[1, 2] == 255 and _lay(ctx, "screen", under, over, True)[1, 2] == 255
    assert _lay(ctx, "screen", under, over, True)[1, 0] < added[1, 0]
