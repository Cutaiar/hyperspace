"""Plan 24 C6: the palette fold is an effect file (shaders/fx/palette.glsl).

Everything here is the FX mechanism's own: ``fx.palette.*`` params, hot
reload, module presets, routes. What a palette *looks* like is judged by
eye; here the defaults must leave every frame byte-identical (stream A's
goldens), a turned-up mix must change it, a route must move the mix, and
a saved palette is an ``fx`` module preset in the library.
"""

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace.fx import FX_DIR, FxChain, FxState
from hyperspace.routing import Binding, Bindings, Router

FIXTURES = Path(__file__).parent / "fixtures" / "palettes"
LIBRARY_FX = Path(__file__).parent.parent / "hyperspace" / "library" / "fx"
W, H = 320, 200

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def state(tmp_path, *, palette: bool = True) -> FxState:
    """The factory effects, with or without the palette file."""
    d = tmp_path / f"fx{len(list(tmp_path.iterdir()))}"
    shutil.copytree(FX_DIR, d, ignore=None if palette else shutil.ignore_patterns("palette.glsl"))
    return FxState(d)


def frame(ctx, fx: FxState, frames: int = 3) -> np.ndarray:
    from hyperspace.graphmigrate import wiring_of
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, fx=fx)
    r.wiring = wiring_of(fx)        # plan 33 R23: its run, as a load lands it
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    for k in range(frames):
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 30)
    out = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()
    fbo.release()
    return out


def test_the_file_declares_the_params_and_defaults_to_nothing(tmp_path):
    st = state(tmp_path)
    spec = st.specs["palette"]
    assert st.errors == {} and spec.order == max(s.order for s in st.specs.values())
    keys = {p.key for p in spec.params}
    # plan 30 N8: the fold's centre/width and sat/val lo/hi became the slice's ends
    assert {"mode", "hue_from", "hue_to", "sat_from", "sat_to", "val_from", "val_to",
            "anchors", "a1_hue", "a4_val"} <= keys
    assert not keys & {"centre", "width", "sat_lo", "sat_hi", "val_lo", "val_hi"}
    v = st.values["palette"]
    assert v["on"] is False and v["mix"] == 0.0          # off, and mix 0 if switched on
    # the neutral ramp: grey, dark to light
    vals = [v[f"a{i}_val"] for i in (1, 2, 3, 4)]
    assert vals == sorted(vals) and vals[0] == 0.0 and vals[-1] == 1.0
    assert all(v[f"a{i}_sat"] == 0.0 for i in (1, 2, 3, 4))
    assert (v["mode"], v["hue_from"], v["hue_to"], v["sat_from"], v["sat_to"], v["val_from"],
            v["val_to"]) == (0, 0, 360, 0, 1, 0, 1)            # the whole cylinder


def test_the_defaults_leave_every_frame_byte_identical(ctx, tmp_path):
    absent = frame(ctx, state(tmp_path, palette=False))
    off = frame(ctx, state(tmp_path))
    assert np.array_equal(off, absent)
    on = state(tmp_path)
    on.values["palette"]["on"] = True                     # switched on at its defaults: mix 0
    assert np.array_equal(frame(ctx, on), absent)
    # and on top of another effect, the picture is that effect's, untouched
    a, b = state(tmp_path, palette=False), state(tmp_path)
    for st in (a, b):
        st.values["acid"]["on"] = True
    b.values["palette"]["on"] = True
    assert np.array_equal(frame(ctx, b), frame(ctx, a))


def test_a_turned_up_mix_changes_the_picture(ctx, tmp_path):
    base = frame(ctx, state(tmp_path, palette=False))
    st = state(tmp_path)
    st.values["palette"].update(on=True, mix=1.0, hue_from=155.0, hue_to=245.0)
    img = frame(ctx, st)
    assert ctx.error == "GL_NO_ERROR"
    assert np.abs(img[..., :3].astype(int) - base[..., :3]).sum() > W * H * 0.05
    # one hue only: everything lit sits at the centre
    st.values["palette"].update(hue_from=200.0, hue_to=200.0, sat_from=1.0)
    narrow = frame(ctx, st).astype(float)[..., :3] / 255.0
    lit = narrow[narrow.max(axis=2) > 0.3]
    mx, mn = lit.max(axis=1), lit.min(axis=1)
    d = mx - mn + 1e-9
    hue = np.where(mx == lit[:, 2], 4 + (lit[:, 0] - lit[:, 1]) / d,
                   np.where(mx == lit[:, 1], 2 + (lit[:, 2] - lit[:, 0]) / d,
                            (lit[:, 1] - lit[:, 2]) / d)) * 60 % 360
    assert lit.shape[0] > 100 and np.abs(hue - 200.0).max() < 6.0


def test_the_grey_ramp_is_a_greyscale_and_a_coloured_one_is_not(ctx, tmp_path):
    st = state(tmp_path)
    st.values["palette"].update(on=True, mix=1.0, mode=1)
    grey = frame(ctx, st)[..., :3].astype(int)
    assert np.abs(grey[..., 0] - grey[..., 1]).max() <= 1
    assert np.abs(grey[..., 1] - grey[..., 2]).max() <= 1
    st.values["palette"].update(a2_sat=1.0, a2_hue=0.0, a3_sat=1.0, a3_hue=240.0)
    assert np.abs(frame(ctx, st)[..., :3].astype(int) - grey).sum() > W * H


def test_the_file_hot_reloads(ctx, tmp_path):
    st = state(tmp_path)
    chain = FxChain(ctx, st)
    assert chain.compile_all() == {}
    path = st.dir / "palette.glsl"
    path.write_text(path.read_text().replace('@param 0 360 360 "Hue to"',
                                             '@param 0 360 180 "Hue to"'))
    later = path.stat().st_mtime + 5
    os.utime(path, (later, later))
    assert "palette" in st.poll()
    assert {p.key: p.default for p in st.specs["palette"].params}["hue_to"] == 180.0
    assert chain.compile_all() == {}


def _registry(home):
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState
    chain = Analyzer(Analyser())
    st = FxState()
    lib = Library(home, period=0.0)
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), lib.project,
                         fx=st)
    lib.attach(reg)
    return reg, st, lib


def test_every_palette_param_takes_a_route(tmp_path):
    reg, st, _ = _registry(tmp_path)
    ids = [p for p in reg.ids() if p.startswith("fx.palette.")]
    assert "fx.palette.mix" in ids and "fx.palette.a4_val" in ids
    for p in ids:
        if not p.endswith(("order", "target")):
            assert reg[p].modulatable, p
    router = Router(reg, Bindings([Binding("ext:0", "fx.palette.mix", "push", 0.8),
                                   Binding("ext:1", "fx.palette.hue_from", "push", 0.5)]))
    router.feed("ext", [0.0, 0.0])
    router.modulate(None)
    reg.apply()
    assert st.values["palette"]["mix"] == 0.0
    router.feed("ext", [1.0, 1.0])
    router.modulate(None)
    reg.apply()
    assert st.values["palette"]["mix"] == pytest.approx(0.8)      # the route moved the mix
    assert st.values["palette"]["hue_from"] > 0.0
    assert reg["fx.palette.mix"].base == 0.0                      # non-destructive


def test_a_saved_palette_is_an_fx_module_preset(ctx, tmp_path):
    """The library already keeps `fx` presets; a palette is one (a fixture,
    force-added: nothing ships in hyperspace/library/fx)."""
    assert not list(LIBRARY_FX.glob("*palette*")) and not list(LIBRARY_FX.glob("sunset*"))
    home = tmp_path / "home"
    (home / "fx").mkdir(parents=True)
    shutil.copy(FIXTURES / "fx" / "sunset.json", home / "fx" / "sunset.json")
    reg, st, lib = _registry(home)
    assert "sunset" in lib.list("fx")
    base = frame(ctx, st)
    assert lib.load("fx", "sunset") == []
    v = st.values["palette"]
    assert v["on"] and v["mix"] == 1.0 and v["mode"] == 1 and v["a1_hue"] == 270.0
    assert np.abs(frame(ctx, st)[..., :3].astype(int) - base[..., :3]).sum() > W * H
    # and a palette saved from the live state comes back through the same road
    reg["fx.palette.a3_hue"].set(100.0)
    lib.save_as("fx", "mine")
    reg["fx.palette.a3_hue"].set(10.0)
    assert lib.load("fx", "mine") == [] and st.values["palette"]["a3_hue"] == 100.0


def test_a_raised_floor_does_not_light_a_see_through_ground(ctx, tmp_path):
    """On the overlay ground (u_opaque 0) a clear pixel stays clear when
    val_from / a ramp colour is above black; on an opaque ground it lifts."""
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState

    def alpha(opaque: bool, **vals) -> int:
        st = state(tmp_path)
        st.values["palette"].update(on=True, mix=1.0, **vals)
        fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
        r = Renderer(ctx, fx=st)
        r.bg_alpha = 1.0 if opaque else 0.0
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(ViewState(shape=10, faces=False, points=False, lines=False), W, H, t_now=4.0)
        px = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4)
        fbo.release()
        return int(px[..., 3].max())
    assert alpha(True, val_from=0.5) == 255
    assert alpha(False, val_from=0.5) == 0
