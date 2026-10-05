"""The effect stack (fx.py): effect files → registry params → GL passes.

The spec parser and the registry side run anywhere; the GL half needs a
standalone context and skips without one. What an effect *looks* like is
judged by eye (tools/fx_shots.py writes the shots); here every factory
file must parse, compile and change the frame, the off path must stay a
copy, and the chain's own blend and alpha rules are checked against numpy.
"""

import os
import shutil
import time
from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace.fx import (
    BLENDS,
    FX_DIR,
    FxChain,
    FxState,
    SpecError,
    declare,
    parse,
)
from hyperspace.params import Registry

EFFECT = """// @label Test
// @order 12
// @blend add
// @speed 0.5
// @tip first line
// @tip second line
uniform float u_amount;  // @param 0 2 0.5 "Amount" how much
uniform float u_scale;   // @param 0.5 16 3 log "Scale" cells
uniform float u_turn;    // @param -3.14 3.14 0 wrap "Turn"
uniform int u_count;     // @param 1 8 9 "Count" clamped default
vec4 effect(vec2 uv) { return src(uv) * u_amount; }
"""


def write(d, name, text):
    (d / f"{name}.glsl").write_text(text)
    # the folder is watched by mtime; make each write a distinct one
    t = time.time() + len(list(d.iterdir()))
    os.utime(d / f"{name}.glsl", (t, t))


@pytest.fixture()
def fxdir(tmp_path):
    d = tmp_path / "fx"
    d.mkdir()
    shutil.copy(FX_DIR / "_lib.glsl", d / "_lib.glsl")
    return d


# ---------------------------------------------------------------- the file format

def test_parse_reads_the_header_and_params():
    s = parse("test", EFFECT)
    assert (s.label, s.order, s.blend, s.speed) == ("Test", 12, BLENDS.index("add"), 0.5)
    assert s.tip == "first line second line"
    by = {p.key: p for p in s.params}
    assert list(by) == ["amount", "scale", "turn", "count"]
    assert (by["amount"].lo, by["amount"].hi, by["amount"].default) == (0.0, 2.0, 0.5)
    assert by["amount"].label == "Amount" and by["amount"].tip == "how much"
    assert by["scale"].log and not by["scale"].wrap
    assert by["turn"].wrap and by["turn"].tip == ""
    assert by["count"].integer and by["count"].default == 8    # held in range


@pytest.mark.parametrize("bad, why", [
    (EFFECT.replace("vec4 effect(", "vec4 fx("), "no 'vec4 effect"),
    (EFFECT.replace("u_amount", "u_mix"), "taken"),
    (EFFECT.replace("0 2 0.5", "2 0 0.5"), "lo < hi"),
    (EFFECT.replace("0.5 16 3 log", "0 16 3 log"), "lo must be > 0"),
    (EFFECT.replace('"Amount"', "Amount"), "@param wants"),
    (EFFECT + "// @param 0 1 0 \"Loose\"\n", "needs 'uniform"),
    (EFFECT.replace("@order 12", "@order soon"), "bad @order"),
    (EFFECT.replace("@blend add", "@blend dodge"), "bad @blend"),
])
def test_parse_rejects_a_bad_header(bad, why):
    with pytest.raises(SpecError, match=why):
        parse("test", bad)


def test_parse_wants_snake_case_names():
    with pytest.raises(SpecError):
        parse("Trip-Warp", EFFECT)


def test_every_factory_effect_parses():
    st = FxState()
    assert st.errors == {}
    assert len(st.specs) >= 10
    for name, spec in st.specs.items():
        assert spec.params, f"{name} has nothing to automate"
        assert all(p.tip for p in spec.params), f"{name}: a fader without a tooltip"
        assert spec.tip


# ---------------------------------------------------------------- the registry

def test_declare_makes_ordinary_params():
    st = FxState()
    r = Registry()
    declare(r, st)
    for pid in ("fx.on", "fx.mix", "fx.select", "fx.warp.on", "fx.warp.mix", "fx.warp.speed",
                "fx.warp.blend", "fx.warp.order", "fx.warp.amount", "fx.kaleido.segments"):
        assert pid in r, pid
    assert all(p.group == "fx" for p in r)
    assert not r["fx.select"].persist and not r["fx.select"].modulatable
    assert not r["fx.warp.order"].modulatable
    assert r["fx.kaleido.segments"].integer
    assert r["fx.warp.scale"].log
    # a fader writes the state the chain reads, and back
    r["fx.warp.amount"].set_value(1.25)
    assert st.values["warp"]["amount"] == pytest.approx(1.25)
    st.values["warp"]["on"] = True
    assert r["fx.warp.on"].value is True
    assert r["fx.select"].names[0] == st.specs[st.names()[0]].label


def test_a_lane_rides_an_effect_param():
    st = FxState()
    r = Registry()
    declare(r, st)
    p = r["fx.warp.amount"]
    p.set_value(0.5)
    p.modulate(0.25)                # a quarter of the 0–2 throw
    r.apply()
    assert st.values["warp"]["amount"] == pytest.approx(1.0)
    assert p.base == pytest.approx(0.5)
    r.apply()                        # nobody held it this frame: base comes back
    assert st.values["warp"]["amount"] == pytest.approx(0.5)


def test_build_registry_declares_the_group():
    from hyperspace.params import build_registry
    audio = SimpleNamespace(chain=SimpleNamespace())
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.view import ViewState
    chain = Analyzer(Analyser())
    audio.chain = chain
    st = FxState()
    r = build_registry(ViewState(), Control(chain), audio, fx=st)
    assert "fx.acid.bend" in r and st.on_specs is not None


# ---------------------------------------------------------------- live files

def test_a_new_uniform_shows_up_and_values_survive(fxdir):
    write(fxdir, "test", EFFECT)
    st = FxState(fxdir)
    r = Registry()
    declare(r, st)
    st.on_specs = lambda names: declare(r, st, names)
    r["fx.test.amount"].set_value(1.5)
    r["fx.test.on"].set(True)
    assert st.poll() == set()        # nothing moved
    write(fxdir, "test", EFFECT.replace(
        "vec4 effect", 'uniform float u_extra; // @param 0 1 0.25 "Extra" new\nvec4 effect'))
    assert st.poll() == {"test"}
    assert r["fx.test.extra"].value == pytest.approx(0.25)
    assert r["fx.test.amount"].value == pytest.approx(1.5)     # kept across the edit
    assert r["fx.test.on"].value is True
    # dropping the uniform drops its id
    write(fxdir, "test", EFFECT.replace("* u_amount", "* u_amount * 0.5"))
    assert st.poll() == {"test"}
    assert "fx.test.extra" not in r
    # a body-only edit changes no params: nothing re-declared, new source kept
    write(fxdir, "test", EFFECT.replace("* u_amount", "* u_amount * 0.25"))
    assert st.poll() == set()
    assert "0.25" in st.specs["test"].source


def test_new_and_deleted_files(fxdir):
    st = FxState(fxdir)
    r = Registry()
    declare(r, st)
    st.on_specs = lambda names: declare(r, st, names)
    assert st.specs == {}
    write(fxdir, "test", EFFECT)
    st.poll()
    assert "fx.test.amount" in r
    (fxdir / "test.glsl").unlink()
    st.poll()
    assert "fx.test.amount" not in r and "test" not in st.values


def test_a_broken_edit_keeps_the_last_good_spec(fxdir):
    write(fxdir, "test", EFFECT)
    st = FxState(fxdir)
    write(fxdir, "test", EFFECT.replace("vec4 effect(", "vec4 oops("))
    st.poll()
    assert "no 'vec4 effect" in st.errors["test"]
    assert "test" in st.specs and st.specs["test"].params


# ---------------------------------------------------------------- the chain's order

def test_chain_order_and_bypass():
    st = FxState()
    for n in ("warp", "acid", "huecycle"):
        st.values[n]["on"] = True
    assert st.chain() == ["acid", "warp", "huecycle"]           # by order
    st.values["acid"]["order"] = 90
    assert st.chain() == ["warp", "huecycle", "acid"]
    st.values["warp"]["mix"] = 0.0
    assert st.chain() == ["huecycle", "acid"]                   # a dry effect is skipped
    st.on = False
    assert st.chain() == []
    st.on, st.mix = True, 0.0
    assert st.chain() == []


def test_clocks_integrate_the_speed():
    st = FxState()
    st.values["warp"]["speed"] = 2.0
    st.values["acid"]["speed"] = -1.0
    st.advance(0.5)
    st.values["warp"]["speed"] = 0.0    # freezing keeps the phase where it was
    st.advance(0.5)
    assert st.phase["warp"] == pytest.approx(1.0)
    assert st.phase["acid"] == pytest.approx(-1.0)


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


W, H = 320, 200


def render(ctx, fx: FxState, frames: int = 3) -> np.ndarray:
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, fx=fx)
    s = ViewState(shape=10, faces=True, pattern=2, bright=1.3)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    for k in range(frames):
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 30)
    out = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()
    fbo.release()
    return out


def test_every_factory_effect_compiles(ctx):
    assert FxChain(ctx).compile_all() == {}


def test_the_shared_helpers_are_written_once(ctx):
    """audit V2: TAU, LUMA, hsv, pal and the hue rotation live in
    shaders/_common.glsl and nowhere else; it compiles on its own (it reads
    no uniform); an edit to it counts as a change to every effect."""
    import re

    from hyperspace import glsl, lookback
    from hyperspace.render import PATTERNS_GLSL

    shared = glsl.common()
    ctx.program(vertex_shader=glsl.QUAD_VS,
                fragment_shader="#version 330\n" + shared
                + "\nout vec4 f; void main() { f = vec4(hsv(0.1, 1.0, 1.0), luma(pal(0.0, "
                  "vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.0)))); }")
    defs = re.compile(r"(?m)^(?:const\s+\w+\s+(TAU|LUMA)\b|vec3\s+(hsv|hsv2rgb|pal|hue_rotate|rotate_hue)\s*\()")
    for text in (PATTERNS_GLSL.read_text(), (FX_DIR / "_lib.glsl").read_text(), lookback.post_fs("")):
        assert not defs.search(text), defs.search(text).group(0)
    assert lookback.QUAD_VS is glsl.QUAD_VS
    assert "_common" in FxState()._scan()
    assert glsl.FALLBACK == shared, "glsl.FALLBACK must be the shipped _common.glsl"




def test_off_is_the_old_frame_exactly(ctx):
    base = render(ctx, FxState())
    bypassed = FxState()
    bypassed.values["warp"]["on"] = True
    bypassed.on = False
    assert np.array_equal(render(ctx, bypassed), base)
    dry = FxState()
    dry.values["warp"]["on"] = True
    dry.mix = 0.0
    assert np.array_equal(render(ctx, dry), base)


@pytest.mark.parametrize("name", sorted(FxState().specs))
def test_each_effect_changes_the_frame(ctx, name):
    base = render(ctx, FxState())
    st = FxState()
    st.values[name]["on"] = True
    if name == "glimmer":
        st.values[name]["density"] = 1.0
    img = render(ctx, st)
    assert ctx.error == "GL_NO_ERROR"
    diff = np.abs(img[..., :3].astype(int) - base[..., :3]).sum()
    assert diff > W * H * 0.05, f"{name} left the frame (almost) as it was"


def test_a_compile_error_is_reported_and_skipped(ctx, fxdir):
    write(fxdir, "good", EFFECT.replace("@blend add", "@blend mix"))
    write(fxdir, "bad", EFFECT.replace("src(uv) * u_amount", "src(uv) * nope"))
    st = FxState(fxdir)
    for n in ("good", "bad"):
        st.values[n]["on"] = True
    chain = FxChain(ctx, st)
    errs = chain.compile_all()
    assert set(errs) == {"bad"} and "line" in errs["bad"]
    assert chain.error("bad") == errs["bad"]
    tex = ctx.texture((8, 8), 4)
    fbo = ctx.framebuffer(color_attachments=[tex])
    chain.begin((8, 8)).use()
    ctx.clear(0.5, 0.5, 0.5, 1.0)
    assert chain.run(fbo, 0.0) == ["good"]      # the broken one is passed over
    # and with only the broken one on, the frame still arrives: a copy
    st.values["good"]["on"] = False
    chain.begin((8, 8)).use()
    ctx.clear(0.5, 0.25, 0.75, 1.0)
    assert chain.run(fbo, 0.0) == []
    px = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(8, 8, 4)
    assert np.allclose(px[4, 4], [128, 64, 191, 255], atol=1)


CONST = """// @blend {blend}
uniform float u_level; // @param 0 1 0.25 "Level" the constant
vec4 effect(vec2 uv) {{ return vec4(u_level, u_level * 2.0, u_level * 4.0, u_level); }}
"""


@pytest.mark.parametrize("blend", BLENDS)
@pytest.mark.parametrize("mix", [1.0, 0.5])
def test_blend_and_mix_match_numpy(ctx, fxdir, blend, mix):
    write(fxdir, "const", CONST.format(blend=blend))
    st = FxState(fxdir)
    st.values["const"].update(on=True, mix=mix)
    chain = FxChain(ctx, st)
    tex = ctx.texture((4, 4), 4)
    fbo = ctx.framebuffer(color_attachments=[tex])
    a = np.array([0.4, 0.2, 0.1, 0.5])            # a premultiplied, half-covered pixel
    chain.begin((4, 4)).use()
    ctx.clear(*a)
    chain.run(fbo, 0.0)
    got = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(4, 4, 4)[1, 1] / 255
    b = np.array([0.25, 0.5, 1.0, 0.25])
    c = {"mix": b, "add": a + b, "screen": a + b - a * b, "multiply": a * b}[blend]
    c = np.clip(a + (c - a) * mix, 0, 1)
    c[3] = max(c[3], c[:3].max())                  # a pass covers what it lights
    assert np.allclose(got, c, atol=2 / 255), (got, c)


def test_a_generator_lights_a_transparent_ground(ctx):
    st = FxState()
    st.values["plasma"]["on"] = True
    chain = FxChain(ctx, st)
    tex = ctx.texture((64, 40), 4)
    fbo = ctx.framebuffer(color_attachments=[tex])
    chain.begin((64, 40)).use()
    ctx.clear(0.0, 0.0, 0.0, 0.0)
    chain.run(fbo, 1.0)
    px = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(40, 64, 4)
    assert px[..., 3].mean() > 20
    assert (px[..., :3].max(axis=2) <= px[..., 3].astype(int) + 1).all()   # premultiplied


# ---------------------------------------------------------------- presets and the page

def test_factory_presets_name_only_real_params(tmp_path):
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState
    chain = Analyzer(Analyser())
    st = FxState()
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), lib.project,
                         fx=st)
    lib.attach(reg)
    names = lib.list("fx")
    assert {"noita tripping", "noita heavily tripping", "noita tripping balls", "acid",
            "mandala"} <= set(names)
    for name in names:
        assert lib.load("fx", name) == [], name
    lib.load("fx", "noita heavily tripping")
    assert st.chain() == ["warp", "fractals", "tripcolour"]
    assert st.values["warp"]["amount"] == pytest.approx(0.9)
    lib.load("fx", "acid")                           # unnamed ids fall back: warp goes off
    assert "warp" not in st.chain() and "acid" in st.chain()


def test_the_page_draws_and_fits(tmp_path, monkeypatch):
    from imgui_bundle import imgui, implot

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.app import CONTROL_SIZE
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts
    from hyperspace.view import ViewState

    ictx = imgui.create_context()
    pctx = implot.create_context()
    try:
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(*CONTROL_SIZE)
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        chain = Analyzer(Analyser())
        audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        st = FxState()
        lib = Library(tmp_path, period=0.0)
        view = ViewState()
        reg = build_registry(view, Control(chain), audio, lib.project, fx=st)
        lib.attach(reg)
        panel = Panel(Control(chain), audio, view, bank=lib.project, registry=reg, library=lib)
        # just enough renderer for the page: the live state and its errors
        panel.renderer = SimpleNamespace(fx=SimpleNamespace(
            state=st, error=lambda n: "line 3: made up" if n == "warp" else ""))
        lib.load("fx", "noita tripping balls")
        reg["fx.select"].set(st.names().index("fractals"))    # the longest strip
        over = []
        draw = Panel._page_fx

        def measured(self, dt):
            draw(self, dt)
            over.append(imgui.get_scroll_max_y())
        monkeypatch.setattr(Panel, "_page_fx", measured)
        reg["ui.page"].set(PAGE_KEYS.index("fx"))
        for _ in range(3):
            imgui.new_frame()
            panel.draw(1 / 60, 60.0)
            imgui.end_frame()
        assert over and over[-1] == 0, "the fx page scrolls"
    finally:
        implot.destroy_context(pctx)
        imgui.destroy_context(ictx)


def test_the_page_has_no_conflicting_ids(tmp_path, monkeypatch):
    """Every widget on the FX page has its own imgui id — the open effect's
    chip and its strip's "on" check once shared one ("Fractals##fx.fractals.on"),
    which imgui flags as two visible items with a conflicting id."""
    from imgui_bundle import imgui, implot

    from hyperspace import ui_fx
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.ui import Panel, apply_style, load_fonts
    from hyperspace.view import ViewState

    ictx = imgui.create_context()
    pctx = implot.create_context()
    try:
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(960, 900)
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        chain = Analyzer(Analyser())
        audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        st = FxState()
        lib = Library(tmp_path, period=0.0)
        view = ViewState()
        reg = build_registry(view, Control(chain), audio, lib.project, fx=st)
        lib.attach(reg)
        panel = Panel(Control(chain), audio, view, bank=lib.project, registry=reg, library=lib)
        panel.renderer = SimpleNamespace(fx=SimpleNamespace(state=st, error=lambda n: ""))
        ids: list[str] = []
        # …and its own popup: a param's menu hangs off its chip's LED, its
        # chip's name and its strip's check (plan 16 WP2: a key apiece)
        for fn in ("button", "checkbox", "slider_float", "slider_int", "combo",
                   "invisible_button", "begin_popup_context_item"):
            real = getattr(imgui, fn)

            def rec(label, *a, _real=real, **k):
                ids.append(label.split("##", 1)[-1] if "##" in label else label)
                return _real(label, *a, **k)
            monkeypatch.setattr(imgui, fn, rec)
        for k, name in enumerate(st.names()):     # every effect's strip open in turn
            reg["fx.select"].set(k)
            ids.clear()
            imgui.new_frame()
            imgui.begin("page")
            ui_fx.page(panel, 1 / 60)
            imgui.end()
            imgui.end_frame()
            dup = {i for i in ids if ids.count(i) > 1}
            assert not dup, f"{name}: conflicting ids {sorted(dup)}"
            # plan 16 WP2: every chip is two items, the LED and the name
            for n in st.names():
                assert f"led.fx.{n}.on" in ids and f"chip.fx.{n}.on" in ids, n
    finally:
        implot.destroy_context(pctx)
        imgui.destroy_context(ictx)


# ---------------------------------------------------------------- which strip is open (plan 16 WP2)

def test_selection_is_by_name_and_survives_a_reorder():
    st = FxState()
    r = Registry()
    declare(r, st)
    assert st.selected() == st.names()[0] and st.sel_name is None    # nothing chosen: the first
    st.select("warp")
    was = st.names().index("warp")
    assert st.selected() == "warp" and r["fx.select"].value == was
    r["fx.warp.order"].set_value(99)                 # the open effect to the end of the stack…
    assert st.names()[-1] == "warp" and st.selected() == "warp"
    assert r["fx.select"].value == len(st.names()) - 1 != was
    r["fx.huecycle.order"].set_value(0)              # …and another one past it to the front
    assert st.names()[0] == "huecycle" and st.selected() == "warp"
    assert r["fx.select"].value == st.names().index("warp")
    # every step of a drag across the whole range: never another effect
    for k in range(100):
        r["fx.warp.order"].set_value(k)
        assert st.selected() == "warp"
    st.select("no_such_effect")                      # a name with no spec is ignored
    assert st.selected() == "warp"
    st.select(None)                                  # None: whatever is first
    assert st.sel_name is None and st.selected() == st.names()[0]


def test_selection_survives_a_preset_load(tmp_path):
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.library import Library
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState
    chain = Analyzer(Analyser())
    st = FxState()
    lib = Library(tmp_path, period=0.0)
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), lib.project,
                         fx=st)
    lib.attach(reg)
    st.select("acid")
    orders = []
    for name in ("mandala", "acid", "mandala", "noita tripping balls"):
        assert lib.load("fx", name) == []
        orders.append(tuple(st.names()))
        assert st.selected() == "acid", name
        assert reg["fx.select"].value == st.names().index("acid")
    assert orders[0] != orders[1], "the two presets must differ in order for this to mean anything"
    assert orders[0].index("acid") != orders[1].index("acid")
    # and the selection is in no file: nothing a preset saves names it
    assert "fx.select" not in reg.snapshot(part="performance")
    assert not any("sel" in k for k in lib.read("fx", "mandala")["values"])


def test_a_removed_effect_falls_back_and_comes_back(fxdir):
    write(fxdir, "alpha", EFFECT.replace("@order 12", "@order 1"))
    write(fxdir, "beta", EFFECT.replace("@order 12", "@order 2"))
    write(fxdir, "gamma", EFFECT.replace("@order 12", "@order 3"))
    st = FxState(fxdir)
    r = Registry()
    declare(r, st)
    st.on_specs = lambda names: declare(r, st, names)
    st.select("gamma")
    (fxdir / "alpha.glsl").unlink()                  # another effect's file goes: no change
    st.poll()
    assert st.selected() == "gamma" and r["fx.select"].value == 1
    write(fxdir, "aardvark", EFFECT.replace("@order 12", "@order 0"))   # one is added: no change
    st.poll()
    assert st.selected() == "gamma" and st.names()[0] == "aardvark"
    (fxdir / "gamma.glsl").unlink()                  # the open one goes: the first is open
    st.poll()
    assert st.selected() == "aardvark" and r["fx.select"].value == 0
    assert st.sel_name == "gamma"                    # selected() never writes
    write(fxdir, "gamma", EFFECT)                    # …and it is open again when it returns
    st.poll()
    assert st.selected() == "gamma"
    for name in list(st.specs):                      # no effects at all
        (fxdir / f"{name}.glsl").unlink()
    st.poll()
    assert st.selected() is None and r["fx.select"].value == 0
    r["fx.select"].set(3)                            # nothing to open: no raise, no write
    assert st.sel_name == "gamma"


def test_fx_select_is_a_view_onto_the_name():
    st = FxState()
    r = Registry()
    declare(r, st)
    p = r["fx.select"]
    names = st.names()
    assert p.value == 0                              # nothing chosen: the first
    p.set(names.index("fractals"))
    assert st.sel_name == "fractals" and st.selected() == "fractals"
    assert p.value == names.index("fractals")
    p.set(10_000)                                    # out of range clamps
    assert st.sel_name == names[-1]
    p.set(-3)
    assert st.sel_name == names[0]
    assert (p.id, p.label) == ("fx.select", "Edit")
    assert not p.persist and not p.modulatable
    assert p.names == [st.specs[n].label for n in st.names()]
    assert not hasattr(st, "sel")                    # the index is no longer what is stored
    # a live FxState re-classed by a hot reload never ran this __init__
    old = FxState.__new__(FxState)
    old.specs, old.values = st.specs, st.values
    assert old.selected() == names[0]
    old.select("warp")
    assert old.selected() == "warp"


class PageRig:
    """The FX page over a real Panel in a headless imgui context, with the
    mouse: `rects` holds every button's screen rect from the last frame."""

    def __init__(self, tmp_path, monkeypatch):
        from imgui_bundle import imgui, implot

        from hyperspace import ui_fx
        from hyperspace.analysis import Analyser
        from hyperspace.analyzer import Analyzer
        from hyperspace.app import CONTROL_SIZE
        from hyperspace.control import Control
        from hyperspace.library import Library
        from hyperspace.params import build_registry
        from hyperspace.ui import Panel, apply_style, load_fonts
        from hyperspace.view import ViewState

        self.imgui, self.ui_fx, self.size = imgui, ui_fx, CONTROL_SIZE
        self.ictx = imgui.create_context()
        self.pctx = implot.create_context()
        self._implot = implot
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(*CONTROL_SIZE)
        io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        chain = Analyzer(Analyser())
        control = Control(chain)
        audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        self.st = FxState()
        lib = Library(tmp_path, period=0.0)
        view = ViewState()
        self.reg = build_registry(view, control, audio, lib.project, fx=self.st)
        lib.attach(self.reg)
        self.panel = Panel(control, audio, view, bank=lib.project, registry=self.reg,
                           library=lib)
        self.panel.renderer = SimpleNamespace(fx=SimpleNamespace(state=self.st,
                                                                 error=lambda n: ""))
        self.rects: dict[str, tuple[float, float, float, float]] = {}
        real = imgui.button

        def button(label, *a, **k):
            hit = real(label, *a, **k)
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            self.rects[label.split("##", 1)[-1]] = (lo.x, lo.y, hi.x, hi.y)
            return hit
        monkeypatch.setattr(imgui, "button", button)

    def frame(self) -> None:
        imgui = self.imgui
        self.rects.clear()
        imgui.new_frame()
        imgui.set_next_window_pos(imgui.ImVec2(0, 0))
        imgui.set_next_window_size(imgui.ImVec2(*self.size))
        imgui.begin("page", None, imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.no_move)
        self.ui_fx.page(self.panel, 1 / 60)
        imgui.end()
        imgui.end_frame()

    def click(self, item: str, at: float = 0.5) -> None:
        """A left click on the button whose id is `item`, `at` of the way
        along it: the mouse moves there, presses, releases, and leaves."""
        io = self.imgui.get_io()
        self.frame()
        x0, y0, x1, y1 = self.rects[item]
        io.add_mouse_pos_event(x0 + (x1 - x0) * at, (y0 + y1) / 2)
        self.frame()
        io.add_mouse_button_event(0, True)
        self.frame()
        io.add_mouse_button_event(0, False)
        self.frame()
        io.add_mouse_pos_event(-1.0, -1.0)
        self.frame()

    def close(self) -> None:
        self._implot.destroy_context(self.pctx)
        self.imgui.destroy_context(self.ictx)


@pytest.fixture()
def fxpage(tmp_path, monkeypatch):
    rig = PageRig(tmp_path, monkeypatch)
    yield rig
    rig.close()


def test_a_chip_click_selects_and_never_toggles(fxpage):
    st, reg = fxpage.st, fxpage.reg
    reg["fx.warp.on"].set(True)
    fxpage.frame()
    assert st.selected() == st.names()[0] != "fractals"

    def switches():
        return {n: reg[f"fx.{n}.on"].base for n in st.names()}
    before = switches()
    # the whole width of the name, end to end: an off effect, then one that is on
    for name in ("fractals", "warp", "fractals"):
        for at in (0.02, 0.5, 0.98):
            fxpage.click(f"chip.fx.{name}.on", at)
            assert st.selected() == name, (name, at)
            assert switches() == before, (name, at)
    assert reg["fx.select"].value == st.names().index("fractals")


def test_the_first_effect_is_held_by_name_once_it_is_shown(fxpage):
    """Nothing chosen (every launch) means the first effect is open; once
    the page has drawn it, it is held by name, so dragging its own order
    slider — or a preset load — does not hand the strip to the new first."""
    st, reg = fxpage.st, fxpage.reg
    first = st.names()[0]
    assert st.sel_name is None
    fxpage.frame()
    assert st.sel_name == first
    for k in range(100):                             # its own order, end to end
        reg[f"fx.{first}.order"].set_value(k)
        fxpage.frame()
        assert st.selected() == first, k
    assert st.names()[-1] == first


def test_the_leds_hover_says_what_a_click_does(fxpage):
    """The LED shows what runs (the effective value); a click writes the
    base. Its hover reads the base, and names the source riding it."""
    from hyperspace.ui_fx import LED_OFF_TIP, LED_ON_TIP, _led_tip
    st, reg, panel = fxpage.st, fxpage.reg, fxpage.panel
    p = reg["fx.warp.on"]
    assert _led_tip(panel, p) == LED_OFF_TIP == "off — click to switch on"
    p.set(True)
    assert _led_tip(panel, p) == LED_ON_TIP == "on — click to switch off"
    p.set(False)
    p.modulate(1.0)                                  # a source holds it on over an off base
    reg.apply()
    assert st.values["warp"]["on"] and not p.base
    tip = _led_tip(panel, p)
    assert tip.startswith(LED_OFF_TIP + "\n") and "→ on" in tip
    fxpage.click("led.fx.warp.on")                   # the click does what the hover said
    assert p.base is True


def test_the_chips_led_toggles_and_never_selects(fxpage):
    st, reg = fxpage.st, fxpage.reg
    st.select("acid")
    fxpage.frame()
    led, body = fxpage.rects["led.fx.warp.on"], fxpage.rects["chip.fx.warp.on"]
    assert led[3] - led[1] == pytest.approx(led[2] - led[0])        # a square…
    assert led[3] - led[1] == pytest.approx(body[3] - body[1])      # …the chip's height…
    assert led[2] <= body[0] and led[1] == pytest.approx(body[1])   # …at its left end
    others = {n: reg[f"fx.{n}.on"].base for n in st.names() if n != "warp"}
    for want in (True, False, True):
        fxpage.click("led.fx.warp.on")
        assert reg["fx.warp.on"].base is want
        assert st.values["warp"]["on"] is want
        assert st.selected() == "acid" and st.sel_name == "acid"
        assert {n: reg[f"fx.{n}.on"].base for n in others} == others


def test_selecting_an_effect_is_not_an_undo_step(tmp_path):
    """Plan 15's undo watches persisted params only (`undo.watched`), and
    fx.select is persist=False: opening a strip — through the param, or by
    name as the page does — makes no step. Reordering does (it is an edit),
    and undoing it leaves the open strip where it was."""
    from test_undo import boot, frames, labels, settle

    from hyperspace import undo
    st = FxState()
    r = boot(tmp_path / "home", fx=st)
    settle(r)
    start = labels(r)
    assert not undo.watched(r.reg["fx.select"])
    for name in ("warp", "fractals", "acid"):
        st.select(name)
        settle(r)
        r.reg["fx.select"].set(st.names().index(name) + 1)
        settle(r)
    assert labels(r) == start
    st.select("warp")
    r.reg["fx.warp.order"].set_value(99)
    settle(r)
    assert len(labels(r)) == len(start) + 1
    undo.undo()
    frames(r, 3)
    assert r.reg["fx.warp.order"].base != 99 and st.selected() == "warp"
