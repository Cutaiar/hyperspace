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
    if name == "palette":                  # it starts at mix 0 (today's picture): turn it up
        st.values[name].update(mix=1.0, width=90.0, centre=200.0)
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
        # plan 20 WP2: and with the faces' status row showing (an effect
        # aimed at the faces), the open strip the longest one still
        from hyperspace import ui_fx
        rows = []
        real_row = ui_fx._faces_row
        monkeypatch.setattr(ui_fx, "_faces_row",
                            lambda *a: (rows.append(1), real_row(*a))[1])
        reg["fx.fractals.target"].set(1)
        for _ in range(3):
            imgui.new_frame()
            panel.draw(1 / 60, 60.0)
            imgui.end_frame()
        assert rows and over[-1] == 0, "the fx page scrolls with the faces row"
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
            for aimed in (False, True):           # …on the frame, then aimed at the faces
                reg["fx.select"].set(k)
                reg[f"fx.{name}.target"].set(int(aimed))
                reg[f"fx.{name}.on"].set(aimed)   # on and Faces off: the "faces on" chip too
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
                # the strip header's ONTO chips and a menu each, always;
                # the two map chips, a menu each, and "faces on" while aimed
                for i in (0, 1):
                    assert f"onto.fx.{name}.target.{i}" in ids
                    assert f"ctx.fx.{name}.target.onto{i}" in ids
                faces_ids = {"map.fx.face_map.0", "map.fx.face_map.1", "ctx.fx.face_map.map0",
                             "ctx.fx.face_map.map1", "idle.view.faces"}
                assert (faces_ids <= set(ids)) if aimed else not (faces_ids & set(ids)), name
            reg[f"fx.{name}.target"].set(0)
            reg[f"fx.{name}.on"].set(False)
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

    def __init__(self, tmp_path, monkeypatch, r=None):
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
        if r is None:                    # a bare rig; `r` is test_undo.boot's, with an Undo
            chain = Analyzer(Analyser())
            control = Control(chain)
            audio = SimpleNamespace(chain=chain, on=False, mode="", error="", label="",
                                    sr=48000.0)
            self.st = FxState()
            lib = Library(tmp_path, period=0.0)
            view = ViewState()
            self.reg = build_registry(view, control, audio, lib.project, fx=self.st)
            lib.attach(self.reg)
            self.panel = Panel(control, audio, view, bank=lib.project, registry=self.reg,
                               library=lib)
        else:
            self.st, self.reg = r.fx, r.reg
            r.audio.__dict__.update(mode="", error="", label="", sr=48000.0)
            self.panel = Panel(r.control, r.audio, r.view, bank=r.lib.project, registry=r.reg,
                               library=r.lib)
        self.panel.renderer = SimpleNamespace(fx=SimpleNamespace(state=self.st,
                                                                 error=lambda n: ""))
        self.rects: dict[str, tuple[float, float, float, float]] = {}
        self.texts: list[str] = []       # every text_colored line of the last frame
        self.colors: dict[str, tuple] = {}   # …and the colour each was drawn in
        self.wrapped: list[str] = []     # every text_wrapped line of the last frame
        self.disabled: dict[str, int] = {}   # item id → begin_disabled depth it was drawn at
        self.veils: list[tuple[float, float, float, float]] = []   # ui_fx._dim's rects
        depth = [0]

        def item(fn):
            real = getattr(imgui, fn)

            def rec(label, *a, **k):
                out = real(label, *a, **k)
                lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
                key = label.split("##", 1)[-1]
                self.rects[key] = (lo.x, lo.y, hi.x, hi.y)
                self.disabled[key] = depth[0]
                return out
            monkeypatch.setattr(imgui, fn, rec)
        for fn in ("button", "checkbox", "slider_float", "slider_int", "combo"):
            item(fn)
        real_text, real_begin, real_end = (imgui.text_colored, imgui.begin_disabled,
                                           imgui.end_disabled)

        def text_colored(col, text):
            self.texts.append(text)
            self.colors[text] = (col.x, col.y, col.z, col.w)
            return real_text(col, text)

        real_wrapped = imgui.text_wrapped

        def text_wrapped(text):
            self.wrapped.append(text)
            return real_wrapped(text)
        monkeypatch.setattr(imgui, "text_wrapped", text_wrapped)

        def begin_disabled(*a, **k):
            self._stack.append(bool(a[0] if a else k.get("disabled", True)))
            depth[0] = sum(self._stack)
            return real_begin(*a, **k)

        def end_disabled():
            self._stack.pop()
            depth[0] = sum(self._stack)
            return real_end()
        self._stack: list[bool] = []
        monkeypatch.setattr(imgui, "text_colored", text_colored)
        monkeypatch.setattr(imgui, "begin_disabled", begin_disabled)
        monkeypatch.setattr(imgui, "end_disabled", end_disabled)
        real_dim = getattr(ui_fx, "_dim", None)
        if real_dim is not None:

            def dim(lo, hi):
                self.veils.append((lo.x, lo.y, hi.x, hi.y))
                return real_dim(lo, hi)
            monkeypatch.setattr(ui_fx, "_dim", dim)

    def frame(self) -> None:
        imgui = self.imgui
        self.rects.clear()
        self.texts.clear()
        self.colors.clear()
        self.wrapped.clear()
        self.disabled.clear()
        self.veils.clear()
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

    def drag(self, src: str, dst: str, dst_at: float = 0.5, release: bool = True) -> None:
        """Press on the item `src`, drag it — past imgui's drag threshold,
        a few frames of travel — to `dst_at` of the way along the item
        `dst`, and (with `release`) let go there."""
        io = self.imgui.get_io()
        self.frame()
        x0, y0, x1, y1 = self.rects[src]
        x, y = (x0 + x1) / 2, (y0 + y1) / 2
        io.add_mouse_pos_event(x, y)
        self.frame()
        io.add_mouse_button_event(0, True)
        self.frame()
        for k in range(1, 6):
            io.add_mouse_pos_event(x + 4 * k, y - 2 * k)
            self.frame()
        x0, y0, x1, y1 = self.rects[dst]
        io.add_mouse_pos_event(x0 + (x1 - x0) * dst_at, (y0 + y1) / 2)
        self.frame()
        self.frame()
        if release:
            self.release()

    def release(self) -> None:
        """Let go of the mouse button where it is, and take the mouse away."""
        io = self.imgui.get_io()
        io.add_mouse_button_event(0, False)
        self.frame()
        self.frame()
        io.add_mouse_pos_event(-1.0, -1.0)
        self.frame()

    def pick(self, item: str, index: int) -> None:
        """Choose entry `index` of the combo whose id is `item`, with the
        mouse: a click opens its list (under it, with the popup's padding),
        a second click lands on the entry."""
        imgui = self.imgui
        io, style = imgui.get_io(), imgui.get_style()
        self.click(item)
        x0, _, x1, y1 = self.rects[item]
        line = imgui.get_text_line_height_with_spacing()
        io.add_mouse_pos_event((x0 + x1) / 2, y1 + style.window_padding.y + (index + 0.5) * line)
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


def without_palette(st, reg) -> None:
    """The twelve effects the page was sized for. The palette (plan 24 C6)
    is the thirteenth chip, which wraps onto a fifth row, and a strip of
    twenty-one faders: the page scrolls for it, which
    test_the_page_scrolls_for_the_palette_and_still_draws pins. These
    tests are about the stack's chips, drags and orders, so they run with
    the file's effect taken out of the state and the registry."""
    st.specs.pop("palette", None)
    st.values.pop("palette", None)
    st.phase.pop("palette", None)
    declare(reg, st, {"palette"})


@pytest.fixture()
def fxpage(tmp_path, monkeypatch):
    rig = PageRig(tmp_path, monkeypatch)
    without_palette(rig.st, rig.reg)
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


# ---------------------------------------------------------------- an idle effect says why (plan 16 WP3)

def test_why_idle_names_the_first_reason():
    from itertools import product

    from hyperspace.ui_fx import why_idle
    st = FxState()
    v = st.values["warp"]
    v["on"] = True
    assert why_idle(st, "warp") is None                       # running
    # each reason alone, then the order they are named in when several hold
    v["mix"] = 0.0
    assert why_idle(st, "warp") == "mix 0"
    st.mix = 0.0
    assert why_idle(st, "warp") == "fx mix 0"
    st.on = False
    assert why_idle(st, "warp") == "bypassed"
    v["on"] = False
    assert why_idle(st, "warp") == "off"
    # every effect in every state: None exactly when chain() runs it
    seen = set()
    for on, bypass, fxmix, mix in product((True, False), (True, False), (1.0, 0.3, 0.0),
                                          (1.0, 0.5, 0.0)):
        st.on, st.mix = bypass, fxmix
        for n in st.names():
            st.values[n].update(on=on, mix=mix)
        st.values["acid"].update(on=not on, mix=1.0)           # one effect out of step
        running = st.chain()
        for n in st.names():
            why = why_idle(st, n)
            assert (why is None) == (n in running), (n, on, bypass, fxmix, mix, why)
            seen.add(why)
    assert seen == {None, "off", "bypassed", "fx mix 0", "mix 0"}


def test_an_off_effects_strip_says_so_and_turn_on_switches_it_on(fxpage):
    from hyperspace.ui_fx import IDLE
    st, reg = fxpage.st, fxpage.reg
    line = IDLE["off"][0]
    assert line == "off — nothing below shows until it is on"
    st.select("warp")
    fxpage.frame()
    assert line in fxpage.texts and "idle.fx.warp.on" in fxpage.rects
    # the line sits over the strip's "on" row, and the rows under it are veiled
    assert fxpage.rects["idle.fx.warp.on"][3] <= fxpage.rects["fx.warp.on"][1]
    assert len(fxpage.veils) == 2
    others = {n: reg[f"fx.{n}.on"].base for n in st.names() if n != "warp"}
    fxpage.click("idle.fx.warp.on")
    assert reg["fx.warp.on"].base is True and st.values["warp"]["on"] is True
    assert {n: reg[f"fx.{n}.on"].base for n in others} == others
    assert st.selected() == "warp" and st.chain() == ["warp"]
    fxpage.frame()                                   # running: no line, no chip, no veil
    assert line not in fxpage.texts and "idle.fx.warp.on" not in fxpage.rects
    assert not fxpage.veils and not set(fxpage.texts) & {v[0] for v in IDLE.values()}


def test_a_bypassed_stack_says_so_on_the_strip(fxpage):
    from hyperspace.ui_fx import IDLE
    st, reg = fxpage.st, fxpage.reg
    st.select("warp")
    reg["fx.warp.on"].set(True)
    reg["fx.on"].set(False)
    fxpage.frame()
    assert "the whole stack is bypassed" in fxpage.texts
    assert "idle.fx.on" in fxpage.rects and "idle.fx.warp.on" not in fxpage.rects
    fxpage.click("idle.fx.on")
    assert reg["fx.on"].base is True and st.chain() == ["warp"]
    fxpage.frame()
    assert "the whole stack is bypassed" not in fxpage.texts and "idle.fx.on" not in fxpage.rects
    # the two reasons a fader mends: the line, and no chip beside it
    reg["fx.mix"].set_value(0.0)
    fxpage.frame()
    assert "FX mix is at 0" in fxpage.texts
    assert not [k for k in fxpage.rects if k.startswith("idle.")]
    reg["fx.mix"].set_value(1.0)
    reg["fx.warp.mix"].set_value(0.0)
    fxpage.frame()
    assert "its mix is at 0" in fxpage.texts
    assert not [k for k in fxpage.rects if k.startswith("idle.")]
    assert {v[0] for v in IDLE.values()} & set(fxpage.texts) == {"its mix is at 0"}
    # the fader that line names is the one row left undimmed
    assert len(fxpage.veils) == 1
    assert fxpage.veils[0][1] >= fxpage.rects["fx.warp.mix"][3]


def test_the_idle_strips_controls_stay_live(fxpage):
    st, reg = fxpage.st, fxpage.reg
    st.select("warp")
    fxpage.frame()
    assert reg["fx.warp.on"].base is False and fxpage.veils
    rows = ["fx.warp.mix", "fx.warp.speed", "fx.warp.blend", "fx.warp.order",
            *(f"fx.warp.{p.key}" for p in st.specs["warp"].params)]
    for pid in ("fx.warp.on", *rows):                # no begin_disabled wraps a row
        assert fxpage.disabled[pid] == 0, pid
    # the ONTO chips are in the header, over the veil: an idle effect can be re-aimed
    veil_top = fxpage.veils[1][1]
    for i in (0, 1):
        assert fxpage.rects[f"onto.fx.warp.target.{i}"][3] <= veil_top
        assert fxpage.disabled[f"onto.fx.warp.target.{i}"] == 0
    lo, hi = fxpage.veils[0], fxpage.veils[1]
    assert lo == pytest.approx(fxpage.rects["fx.warp.mix"])      # the mix beside the check
    on = fxpage.rects["fx.warp.on"]
    assert on[2] <= lo[0], "the 'on' check is not dimmed"
    for pid in rows[1:]:                             # every other row is under the veil
        x0, y0, x1, y1 = fxpage.rects[pid]
        assert hi[0] <= x0 and x1 <= hi[2] and hi[1] <= y0 and y1 <= hi[3], pid
    # a slider under the veil still takes the mouse: press at 9/10 of its throw
    amount, speed = reg["fx.warp.amount"], reg["fx.warp.speed"]
    was = amount.base
    fxpage.click("fx.warp.amount", 0.9)
    assert amount.base > was and amount.base == pytest.approx(amount.lo + 0.9 * (
        amount.hi - amount.lo), abs=0.1 * (amount.hi - amount.lo))
    fxpage.click("fx.warp.speed", 0.25)
    assert speed.base < 0
    fxpage.click("fx.warp.mix", 0.5)
    assert reg["fx.warp.mix"].base == pytest.approx(0.5, abs=0.1)
    assert reg["fx.warp.on"].base is False           # and none of that switched it on
    assert st.values["warp"]["amount"] == pytest.approx(amount.base)


def test_an_armed_rows_learn_frame_is_drawn_over_the_veil(fxpage, monkeypatch):
    """The veil is painted after the rows, so it would dim the red frame of
    a row armed to learn; the frame is drawn again on top, on that row."""
    from hyperspace import ui_fx
    st, panel = fxpage.st, fxpage.panel
    st.select("warp")
    seen = []
    real = ui_fx._relearn_frame
    monkeypatch.setattr(ui_fx, "_relearn_frame",
                        lambda p, rects: (seen.append(dict(rects)), real(p, rects))[1])
    panel.learn = SimpleNamespace(learning="fx.warp.speed", arm=lambda pid: None)
    fxpage.frame()
    assert len(seen) == 1 and fxpage.veils          # idle: after the veil, once
    rows = {"fx.warp.mix", "fx.warp.speed", "fx.warp.blend", "fx.warp.order",
            *(f"fx.warp.{p.key}" for p in st.specs["warp"].params)}
    assert set(seen[0]) == rows
    r0, r1 = seen[0]["fx.warp.speed"]
    assert (r0.x, r0.y, r1.x, r1.y) == pytest.approx(fxpage.rects["fx.warp.speed"])
    fxpage.reg["fx.warp.on"].set(True)               # running: no veil, nothing to redraw
    fxpage.reg["fx.on"].set(True)
    seen.clear()
    fxpage.frame()
    assert not seen and not fxpage.veils


def test_the_page_fits_with_the_tightest_strip_idle(fxpage, monkeypatch):
    from hyperspace.ui import PAGE_KEYS, Panel
    from hyperspace.ui_fx import why_idle
    imgui, st, reg, panel = fxpage.imgui, fxpage.st, fxpage.reg, fxpage.panel
    # the worst case for height: an error line showing on every strip as well
    panel.renderer.fx.error = lambda n: "line 3: made up"
    over = []
    draw = Panel._page_fx

    def measured(self, dt):
        draw(self, dt)
        over.append(imgui.get_scroll_max_y())
    monkeypatch.setattr(Panel, "_page_fx", measured)
    reg["ui.page"].set(PAGE_KEYS.index("fx"))
    for name in st.names():
        st.select(name)
        # the three lines that carry a chip; the third (plan 20 WP2) with the
        # effect aimed at the faces, so the faces' status row is drawn as well
        for reason in ("off", "bypassed", "faces off"):
            reg[f"fx.{name}.on"].set(reason != "off")
            reg["fx.on"].set(reason != "bypassed")
            reg[f"fx.{name}.target"].set(int(reason == "faces off"))
            assert why_idle(st, name, panel.view.faces) == reason
            for _ in range(3):
                fxpage.texts.clear()
                imgui.new_frame()
                panel.draw(1 / 60, 60.0)
                imgui.end_frame()
            assert any(t.startswith(("off —", "the whole stack", "aimed at the faces"))
                       for t in fxpage.texts)
            assert ("faces  (Faces is off)" in fxpage.texts) == (reason == "faces off")
            assert over[-1] == 0, f"the fx page scrolls with {name} open and {reason}"
        reg[f"fx.{name}.target"].set(0)


def test_the_page_scrolls_for_the_palette_and_still_draws(fxpage):
    """Plan 24 C6: the palette is the thirteenth chip and has twenty-one
    faders, more than the page was sized for (the tests above run without
    it). It scrolls; nothing is cut off, and it draws without error."""
    from hyperspace.ui import PAGE_KEYS
    st, reg, imgui, panel = fxpage.st, fxpage.reg, fxpage.imgui, fxpage.panel
    spec = FxState().specs["palette"]
    st.specs["palette"] = spec
    st._adopt(spec)
    declare(reg, st, {"palette"})
    st.select("palette")
    reg["ui.page"].set(PAGE_KEYS.index("fx"))
    for _ in range(3):
        imgui.new_frame()
        panel.draw(1 / 60, 60.0)
        imgui.end_frame()
    assert st.selected() == "palette"


def test_turn_on_is_one_undo_step(tmp_path, monkeypatch):
    """ "turn on" and "effects on" write a base through Param.set and push
    nothing: plan 15's watcher makes each one step, and undo takes it back."""
    from test_undo import boot, frames, labels, settle

    from hyperspace import undo
    st = FxState()
    r = boot(tmp_path / "home", fx=st)
    r.fx = st
    pushes = []
    real_push = undo.push
    monkeypatch.setattr(undo, "push", lambda *a, **k: (pushes.append(a), real_push(*a, **k))[1])
    rig = PageRig(tmp_path, monkeypatch, r)
    try:
        st.select("warp")
        r.reg["fx.on"].set(False)                    # the stack bypassed and warp off,
        r.reg["fx.warp.on"].set(False)               # whatever the startup preset left
        settle(r)
        start = labels(r)
        rig.click("idle.fx.warp.on")                 # "turn on": the first reason's chip
        settle(r)
        assert r.reg["fx.warp.on"].base is True and r.reg["fx.on"].base is False
        assert len(labels(r)) == len(start) + 1 and not pushes
        rig.click("idle.fx.on")                      # now it reads bypassed: "effects on"
        settle(r)
        assert r.reg["fx.on"].base is True and st.chain() == ["warp"]
        assert len(labels(r)) == len(start) + 2 and not pushes
        for want_stack, want_warp in ((False, True), (False, False)):
            undo.undo()
            frames(r, 3)
            assert r.reg["fx.on"].base is want_stack and r.reg["fx.warp.on"].base is want_warp
        assert labels(r) == start
    finally:
        rig.close()


# ---------------------------------------------------------------- the face target (plan 20 WP1)

def test_target_is_declared_per_effect_and_is_not_modulatable():
    """One generated enum per effect, declared by the loop that declares
    `order`, and one mapping switch for the whole target (fork F4: the
    target is structure, the mapping is a move)."""
    from hyperspace import undo
    from hyperspace.fx import FACE_MAPS, FACES, FRAME, PER_FACE, SCREEN, TARGETS
    from hyperspace.params import Kind
    assert TARGETS == ["frame", "faces"] and (FRAME, FACES) == (0, 1)
    assert FACE_MAPS == ["per face", "screen"] and (PER_FACE, SCREEN) == (0, 1)
    st = FxState()
    r = Registry()
    declare(r, st)
    assert len(st.specs) >= 12
    for name in st.specs:
        p = r[f"fx.{name}.target"]
        assert p.kind is Kind.ENUM and p.names == TARGETS and p.group == "fx"
        assert p.value == FRAME and st.values[name]["target"] == FRAME
        assert p.persist and not p.modulatable and undo.watched(p)
    m = r["fx.face_map"]
    assert m.kind is Kind.ENUM and m.names == FACE_MAPS and m.value == PER_FACE
    assert m.persist and m.modulatable and m.group == "fx" and undo.watched(m)
    # nothing else came with them: one id per effect and one for the stack
    new = [p.id for p in r if p.id.endswith(".target") or p.id == "fx.face_map"]
    assert len(new) == len(st.specs) + 1
    # the params write the state the renderer reads, and back
    r["fx.warp.target"].set(FACES)
    r["fx.face_map"].set(SCREEN)
    assert st.values["warp"]["target"] == FACES and st.face_map == SCREEN
    # a re-declare of one effect (its file changed shape) keeps its target
    declare(r, st, {"warp"})
    assert r["fx.warp.target"].value == FACES


def test_a_retargeted_effect_survives_a_reshape_of_its_file(fxdir):
    write(fxdir, "test", EFFECT)
    st = FxState(fxdir)
    st.values["test"]["target"] = 1
    write(fxdir, "test", EFFECT + "uniform float u_extra; // @param 0 1 0.5 \"Extra\"\n")
    assert st.poll() == {"test"}
    assert st.values["test"]["target"] == 1 and "extra" in st.values["test"]


def test_a_preset_without_targets_loads_all_frame(tmp_path):
    """D2: a load lands every fx.* value, and a file that names neither new
    id — every file saved before this plan, the whole factory layer — gets
    the group's defaults. No migration."""
    from test_undo import boot

    from hyperspace.fx import FACES, FRAME, PER_FACE, SCREEN
    from hyperspace.library import FACTORY
    st = FxState()
    r = boot(tmp_path / "home", fx=st)

    def aim():
        r.reg["fx.warp.target"].set(FACES)
        r.reg["fx.plasma.target"].set(FACES)
        r.reg["fx.face_map"].set(SCREEN)
        assert st.values["warp"]["target"] == FACES and st.face_map == SCREEN

    def all_frame(what):
        assert [st.values[n]["target"] for n in st.specs] == [FRAME] * len(st.specs), what
        assert st.face_map == PER_FACE, what

    names = r.lib.list("fx")
    assert len(names) >= 5
    for name in names:
        aim()
        assert r.lib.load("fx", name) == [], name
        all_frame(name)
    aim()
    assert r.presets.load("TRIP") == []
    all_frame("TRIP")
    # and no factory file names either id: the files are sparse, none was regenerated
    for f in FACTORY.rglob("*.json"):
        text = f.read_text()
        assert ".target" not in text and "fx.face_map" not in text, f.name


def test_chain_splits_by_target_and_keeps_order():
    from hyperspace.fx import FACES, FRAME
    st = FxState()
    on = ("warp", "acid", "huecycle", "plasma", "kaleido")
    for n in on:
        st.values[n]["on"] = True
    whole = st.chain()
    assert st.chain(None) == whole and st.chain(FRAME) == whole and st.chain(FACES) == []
    st.values["acid"]["target"] = FACES
    st.values["huecycle"]["target"] = FACES
    frame, faces = st.chain(FRAME), st.chain(FACES)
    assert st.chain() == whole                               # chain(None) is unchanged
    assert faces == [n for n in whole if n in ("acid", "huecycle")]
    assert frame == [n for n in whole if n not in ("acid", "huecycle")]
    st.values["acid"]["order"] = 99                          # each in order, still
    assert st.chain(FACES) == ["huecycle", "acid"]
    st.values["huecycle"]["mix"] = 0.0
    assert st.chain(FACES) == ["acid"]
    st.on = False                                            # the bypass is both chains'
    assert st.chain(FACES) == [] and st.chain(FRAME) == []
    st.on, st.mix = True, 0.0
    assert st.chain(FACES) == [] and st.chain(FRAME) == []
    # a values dict from before a hot reload has no target: the frame's
    st.mix = 1.0
    del st.values["warp"]["target"]
    assert "warp" in st.chain(FRAME) and "warp" not in st.chain(FACES)


def test_advance_to_moves_the_clocks_once_per_frame_time():
    st = FxState()
    st.values["warp"]["speed"] = 2.0
    assert st.advance_to(5.0) == 0.0                         # the first call: no dt yet
    assert st.advance_to(5.1) == pytest.approx(0.1)
    assert st.advance_to(5.1) == 0.0                         # the second chain, same frame
    assert st.phase["warp"] == pytest.approx(0.2)
    assert st.advance_to(9.0) == 0.25                        # a stall is clamped
    assert st.advance_to(8.0) == 0.0                         # and time never runs back
    assert st.phase["warp"] == pytest.approx(0.7)
    old = FxState()                                          # one from before a hot reload
    del old._t_last, old.face_map
    assert old.advance_to(1.0) == 0.0 and old.advance_to(1.5) == 0.25


def test_u_target_is_a_reserved_uniform_name():
    from hyperspace.fx import RESERVED
    assert RESERVED == {"on", "mix", "speed", "blend", "order", "target"}
    with pytest.raises(SpecError, match="'target' is taken"):
        parse("x", 'uniform float u_target; // @param 0 1 0 "Target"\n'
                   "vec4 effect(vec2 uv) { return src(uv); }")
    for f in FX_DIR.glob("*.glsl"):                          # and no factory file wants it
        assert "u_target" not in f.read_text(), f.name


def _two_chains(ctx, st):
    from hyperspace.fx import FACES
    frame = FxChain(ctx, st)
    return frame, FxChain(ctx, st, target=FACES, programs=frame)


def test_two_chains_advance_the_clocks_once(ctx):
    """A frame chain and a face chain over one state, both run at the same
    `t`: every phase is what one chain alone gives — not double speed."""
    from hyperspace.fx import FACES

    def run(split: bool) -> dict:
        st = FxState()
        for n, speed in (("warp", 2.0), ("plasma", -1.0), ("acid", 0.5)):
            st.values[n].update(on=True, speed=speed)
        if split:
            st.values["plasma"]["target"] = FACES
        frame, faces = _two_chains(ctx, st)
        out = ctx.framebuffer(color_attachments=[ctx.texture((16, 16), 4)])
        for k in range(5):
            t = 3.0 + k * 0.1
            if split:                                        # the faces' chain runs first
                faces.begin((32, 32))
                assert faces.run(out, t) == ["plasma"]
            frame.begin((16, 16))
            assert frame.run(out, t) == st.chain(0)
        return dict(st.phase)

    one, two = run(False), run(True)
    assert one["warp"] == pytest.approx(0.8) and one["plasma"] == pytest.approx(-0.4)
    assert two == pytest.approx(one)


def test_the_face_chain_borrows_the_frame_chains_programs(ctx, fxdir):
    """One program per effect across both chains, and one error line: the
    frame chain's `error(name)` speaks for an effect aimed at the faces."""
    from hyperspace.fx import FACES
    write(fxdir, "good", EFFECT.replace("@blend add", "@blend mix"))
    write(fxdir, "bad", EFFECT.replace("src(uv) * u_amount", "src(uv) * nope"))
    st = FxState(fxdir)
    for n in ("good", "bad"):
        st.values[n].update(on=True, target=FACES)
    frame, faces = _two_chains(ctx, st)
    assert faces.active() and not frame.active()
    out = ctx.framebuffer(color_attachments=[ctx.texture((8, 8), 4)])
    faces.begin((8, 8)).use()
    ctx.clear(0.5, 0.5, 0.5, 0.5)
    assert faces.run(out, 0.0) == ["good"]                   # the broken one is passed over
    assert faces._progs == {} and set(frame._progs) == {"good"}
    assert faces._program("good")[0] is frame._program("good")[0]
    assert "line" in frame.error("bad") and faces.error("bad") == frame.error("bad")
    assert faces.errors is frame.errors and faces.compile_all() == frame.compile_all()
    prog = frame._program("good")[0]
    faces.on_reload()                                        # a borrower releases no program
    assert frame._program("good")[0] is prog and prog.glo
    st.values["good"]["target"] = 0                          # and aimed back, the same program
    frame.begin((8, 8))
    assert frame.run(out, 0.1) == ["good"] and frame._program("good")[0] is prog
    # only the broken one aimed at the faces: the seed is copied through
    st.values["good"]["on"] = False
    faces.begin((8, 8)).use()
    ctx.clear(0.5, 0.25, 0.75, 1.0)
    assert faces.run(out, 0.2) == []
    px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(8, 8, 4)
    assert np.allclose(px[4, 4], [128, 64, 191, 255], atol=1)


def test_the_face_chain_never_forces_alpha(ctx, fxdir):
    """In the faces' picture alpha is a face's intensity: the chain aimed at
    the faces writes u_opaque 0 whatever its `opaque` says."""
    from hyperspace.fx import FACES
    write(fxdir, "flat", CONST.format(blend="mix"))
    st = FxState(fxdir)
    st.values["flat"].update(on=True, target=FACES, level=0.1)
    frame, faces = _two_chains(ctx, st)
    faces.opaque = True
    out = ctx.framebuffer(color_attachments=[ctx.texture((8, 8), 4)])
    faces.begin((8, 8)).use()
    ctx.clear(0.0, 0.0, 0.0, 0.0)
    assert faces.run(out, 0.0) == ["flat"]
    px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(8, 8, 4)
    assert px[4, 4, 3] == 102                    # covers its own colour (0.4), never lifted to 1
    st.values["flat"]["target"] = 0              # the same pass on an opaque frame: alpha 1
    frame.opaque = True
    frame.begin((8, 8)).use()
    ctx.clear(0.0, 0.0, 0.0, 0.0)
    assert frame.run(out, 0.0) == ["flat"]
    px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(8, 8, 4)
    assert px[4, 4, 3] == 255


def face_frame(ctx, fx: FxState, frames: int = 3, pattern: int = 2):
    """`render` with the renderer handed back: the frame, the renderer."""
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, fx=fx)
    s = ViewState(shape=10, faces=True, pattern=pattern, bright=1.3)
    s.ang = [0.3, 0.7, 1.1, 0.5, 0.9, 1.3]
    for k in range(frames):
        fbo.use()
        ctx.viewport = (0, 0, W, H)
        r.draw(s, W, H, t_now=4.0 + k / 30)
    out = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()
    fbo.release()
    return out, r


@pytest.mark.parametrize("name", sorted(FxState().specs))
def test_every_effect_runs_on_the_face_target(ctx, name):
    """Aimed at the faces alone, every factory effect compiles, the frame
    draws with no GL error, the picture is not the seed, and the frame is
    not the frame without it. No effect is adapted and none is refused."""
    from hyperspace.fx import FACES
    from hyperspace.render import FACE_PIC
    base, r0 = face_frame(ctx, FxState())
    assert r0.face_pic.tex is None
    st = FxState()
    st.values[name].update(on=True, target=FACES)
    if name == "glimmer":
        st.values[name]["density"] = 1.0
    if name == "palette":                  # it starts at mix 0, which the chain skips
        st.values[name].update(mix=1.0, width=90.0, centre=200.0)
    img, r = face_frame(ctx, st)
    assert ctx.error == "GL_NO_ERROR"
    assert r.face_error == "" and r.fx.errors == {} and not r.fx.active()
    assert r.face_fx.size == (FACE_PIC, FACE_PIC) and r.face_pic.tex.size == (FACE_PIC, FACE_PIC)
    # the chain's first texture still holds the seed (one pass: read, never written)
    seed = np.frombuffer(r.face_fx._tex[0].read(), dtype=np.float16).astype(np.float32)
    seed = np.clip(seed * 255.0, 0, 255).reshape(FACE_PIC, FACE_PIC, 4)
    pic = np.frombuffer(r.face_pic.tex.read(), dtype=np.uint8).reshape(FACE_PIC, FACE_PIC, 4)
    assert seed[..., 3].max() > 100                          # the pattern is in the seed
    change = np.abs(pic.astype(np.float32) - seed).mean()
    print(f"{name}: picture differs from the seed by {change:.2f} / 255 (mean)")
    assert change > 0.25, f"{name} left the picture as the seed was"
    assert np.abs(img.astype(int) - base).sum() > 200, f"{name} does not show on the faces"


# ---------------------------------------------------------------- the face target on the page (plan 20 WP2)

def test_the_status_reads_per_target(fxpage):
    """One line with nothing aimed at the faces — the page as it was — and
    two rows when something is: the running chain per target, the faces'
    row one chip tall with the two map chips at its right end."""
    from hyperspace import ui
    from hyperspace.fx import FACES
    from hyperspace.ui_fx import FACES_OFF, RESET_NOTE
    imgui, st, reg, panel = fxpage.imgui, fxpage.st, fxpage.reg, fxpage.panel
    panel.view.faces = True
    faint = (ui.FAINT.x, ui.FAINT.y, ui.FAINT.z, ui.FAINT.w)
    warn = (ui.WARN.x, ui.WARN.y, ui.WARN.z, ui.WARN.w)

    def label(names):
        return " → ".join(st.specs[n].label for n in names)

    def faces_rows():
        return [t for t in fxpage.texts if t.startswith("faces")]
    for name in ("plasma", "warp", "huecycle"):
        reg[f"fx.{name}.on"].set(True)
    fxpage.frame()
    # nothing aimed at the faces: the one line it always was, no second row
    assert fxpage.wrapped[:2] == [label(st.chain()), RESET_NOTE]
    assert not faces_rows() and not [k for k in fxpage.rects if k.startswith("map.")]
    # the note is one line now: it fits the page's width with room over
    assert RESET_NOTE == "a preset load resets this stack: save a preset to keep it"
    width = fxpage.rects["fx.mix"][2] - fxpage.rects["fx.on"][0]
    imgui.new_frame()
    assert imgui.calc_text_size(RESET_NOTE).x < width
    imgui.end_frame()

    # an effect aimed at the faces, even switched off: the second row
    reg["fx.glimmer.target"].set(FACES)
    assert not st.values["glimmer"]["on"]
    fxpage.frame()
    assert fxpage.wrapped[:2] == ["frame  " + label(st.chain()), RESET_NOTE]
    assert faces_rows() == ["faces  nothing on"] and fxpage.colors[faces_rows()[0]] == faint
    a, b = fxpage.rects["map.fx.face_map.0"], fxpage.rects["map.fx.face_map.1"]
    led = fxpage.rects["led.fx.warp.on"]
    assert a[1] == b[1] and a[3] - a[1] == pytest.approx(led[3] - led[1])   # one chip tall
    assert a[2] <= b[0] and b[2] == pytest.approx(fxpage.rects["fx.mix"][2], abs=1.5)  # the right end
    assert b[3] <= fxpage.rects["led.fx.warp.on"][1]                        # over the chip grid

    # one on the faces, the rest on the frame: each row its own chain, in order
    reg["fx.warp.target"].set(FACES)
    reg["fx.glimmer.on"].set(True)
    fxpage.frame()
    assert st.chain(FACES) == ["warp", "glimmer"]
    assert fxpage.wrapped[0] == "frame  " + label(["plasma", "huecycle"])
    assert faces_rows() == ["faces  " + label(["warp", "glimmer"])]
    # everything that is on aimed at the faces: the frame's row says so
    reg["fx.plasma.target"].set(FACES)
    reg["fx.huecycle.target"].set(FACES)
    fxpage.frame()
    assert fxpage.wrapped[0] == "frame  nothing on"

    # bypassed: both rows
    reg["fx.on"].set(False)
    fxpage.frame()
    assert fxpage.wrapped[0] == "frame  bypassed" and faces_rows() == ["faces  bypassed"]
    reg["fx.on"].set(True)
    # …and they read what runs, as why_idle does: a source holding the
    # bypass off over a base that is on (review of PR #106)
    reg["fx.on"].modulate(-1.0)
    reg.apply()
    assert reg["fx.on"].base is True and st.on is False and st.chain() == []
    fxpage.frame()
    assert fxpage.wrapped[0] == "frame  bypassed" and faces_rows() == ["faces  bypassed"]
    reg.apply()                                      # the source lets go
    assert st.on is True

    # Faces off: the row says so, in the warning colour, and keeps its chips
    panel.view.faces = False
    fxpage.frame()
    assert faces_rows() == [f"faces  {FACES_OFF}"] == ["faces  (Faces is off)"]
    assert fxpage.colors[faces_rows()[0]] == warn and "map.fx.face_map.1" in fxpage.rects
    panel.view.faces = True
    # no copies: the face pass does not run either, and the row says so
    panel.view.instances = 0
    fxpage.frame()
    assert faces_rows() == ["faces  (no copies to show them)"]
    assert fxpage.colors[faces_rows()[0]] == warn
    panel.view.instances = 1

    # the renderer's face_error is the row, cut to the room beside the chips
    panel.renderer.face_error = "faces: RuntimeError: seed pass failed"
    fxpage.frame()
    assert faces_rows() == ["faces: RuntimeError: seed pass failed"]
    assert fxpage.colors[faces_rows()[0]] == warn
    panel.renderer.face_error = "faces: RuntimeError: " + "long " * 30
    fxpage.frame()
    row, = faces_rows()
    assert row.endswith("…") and row.startswith("faces: RuntimeError: long")
    assert fxpage.rects["map.fx.face_map.0"][1] == a[1]                     # still one row
    # a GL message of several lines is still one row (review of PR #106)
    panel.renderer.face_error = "faces: Error: GLSL\n\n  0:12: bad\n"
    fxpage.frame()
    assert faces_rows() == ["faces: Error: GLSL 0:12: bad"]
    assert fxpage.rects["map.fx.face_map.0"] == pytest.approx(a)
    panel.renderer.face_error = ""

    # the last effect aimed back at the frame: one line again
    for name in ("plasma", "warp", "huecycle", "glimmer"):
        reg[f"fx.{name}.target"].set(0)
    fxpage.frame()
    assert fxpage.wrapped[0] == label(st.chain()) and not faces_rows()
    assert not [k for k in fxpage.rects if k.startswith("map.")]


def test_the_map_chips_set_fx_face_map(fxpage, monkeypatch):
    """per face / screen: a click on each is Param.set on fx.face_map; the
    param is an ordinary modulatable enum and each chip opens its menu."""
    from hyperspace.fx import FACE_MAPS, FACES, PER_FACE, SCREEN
    imgui, st, reg = fxpage.imgui, fxpage.st, fxpage.reg
    p = reg["fx.face_map"]
    assert p.names == FACE_MAPS == ["per face", "screen"] and p.modulatable and p.persist
    reg["fx.kaleido.target"].set(FACES)
    sets = []
    real_set = type(p).set
    monkeypatch.setattr(type(p), "set", lambda self, v: (sets.append((self.id, v)),
                                                         real_set(self, v))[1])
    popups = []
    real_popup = imgui.begin_popup_context_item
    monkeypatch.setattr(imgui, "begin_popup_context_item",
                        lambda label, *a, **k: (popups.append(label), real_popup(label, *a, **k))[1])
    targets = {n: st.values[n]["target"] for n in st.names()}
    for want in (SCREEN, PER_FACE, SCREEN):
        sets.clear()
        fxpage.click(f"map.fx.face_map.{want}")
        assert sets == [("fx.face_map", want)]
        assert p.base == want and st.face_map == want
    assert {n: st.values[n]["target"] for n in st.names()} == targets
    assert {"##ctx.fx.face_map.map0", "##ctx.fx.face_map.map1"} <= set(popups)
    # the lit chip is what the faces show (the effective value): a source
    # holding the switch at "per face" over a base of "screen"
    lit = []
    from hyperspace import ui
    real_lit = ui.lit_chip
    monkeypatch.setattr(ui, "lit_chip", lambda label, on, *a, **k: (
        lit.append((label.split("##", 1)[-1], bool(on))), real_lit(label, on, *a, **k))[1])
    fxpage.frame()
    assert ("map.fx.face_map.1", True) in lit and ("map.fx.face_map.0", False) in lit
    p.modulate(-1.0)
    reg.apply()
    assert p.base == SCREEN and st.face_map == PER_FACE
    lit.clear()
    fxpage.frame()
    assert ("map.fx.face_map.0", True) in lit and ("map.fx.face_map.1", False) in lit
    # …and then either chip's hover names the source, as the LED's does: a
    # click on the unlit one writes a base that is already there
    tips = []
    monkeypatch.setattr(imgui, "set_tooltip", lambda t: tips.append(t))
    x0, y0, x1, y1 = fxpage.rects["map.fx.face_map.1"]
    imgui.get_io().add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
    for _ in range(3):
        tips.clear()
        reg.apply()
        p.modulate(-1.0)
        reg.apply()
        fxpage.frame()
    assert tips and tips[-1].startswith(p.tip + "\n") and "per face" in tips[-1]


def test_the_strips_onto_chips_move_an_effect_between_chains(fxpage, monkeypatch):
    """The owner's report of 2026-10-05: "I'm not seeing how to route the FX
    shader output into the faces" — the target was an unlabelled combo
    under BLEND. Now every open strip's header carries ONTO and two chips,
    frame and faces, on the title's line at its right end, whatever the
    effect's state and whether Faces is on; the lit one is where it runs.
    A click is Param.set on fx.<name>.target, which is structure (not
    modulatable); each chip has the param's menu."""
    from hyperspace import ui
    from hyperspace.fx import FACES, FRAME, TARGETS
    from hyperspace.ui_fx import FAINT_FACES, ONTO
    imgui, st, reg, panel = fxpage.imgui, fxpage.st, fxpage.reg, fxpage.panel
    p = reg["fx.warp.target"]
    assert p.names == TARGETS == ["frame", "faces"] and not p.modulatable and p.persist
    popups, lit = [], []
    real_popup = imgui.begin_popup_context_item
    monkeypatch.setattr(imgui, "begin_popup_context_item",
                        lambda label, *a, **k: (popups.append(label), real_popup(label, *a, **k))[1])
    real_lit = ui.lit_chip
    monkeypatch.setattr(ui, "lit_chip", lambda label, on, *a, **k: (
        lit.append((label.split("##", 1)[-1], bool(on))), real_lit(label, on, *a, **k))[1])
    st.select("warp")
    # drawn in every state a newcomer meets: the effect off or on, Faces off or on
    for on, faces_on in ((False, False), (True, False), (False, True), (True, True)):
        reg["fx.warp.on"].set(on)
        panel.view.faces = faces_on
        lit.clear()
        fxpage.frame()
        a, b = fxpage.rects["onto.fx.warp.target.0"], fxpage.rects["onto.fx.warp.target.1"]
        assert a[1] == b[1] and a[2] <= b[0]                        # one row: frame, then faces
        assert b[2] == pytest.approx(fxpage.rects["fx.warp.mix"][2], abs=1.5)   # the right end
        assert b[3] <= fxpage.rects["fx.warp.on"][1]                # over the strip's rows
        assert b[1] >= fxpage.rects["chip.fx.huecycle.on"][3]        # under the chip grid
        assert ONTO.upper() in fxpage.texts and "WARP" in " ".join(fxpage.texts).upper()
        assert ("onto.fx.warp.target.0", True) in lit and ("onto.fx.warp.target.1", False) in lit
    assert "fx.warp.target" not in fxpage.rects                     # no combo any more
    assert {"##ctx.fx.warp.target.onto0", "##ctx.fx.warp.target.onto1"} <= set(popups)
    blend, order = fxpage.rects["fx.warp.blend"], fxpage.rects["fx.warp.order"]
    assert blend[1] == order[1] and blend[2] <= order[0]            # the blend row: blend, order
    reg["fx.plasma.on"].set(True)
    order_was = st.names()
    assert st.chain(FRAME) == st.chain() and st.chain(FACES) == []
    fxpage.click("onto.fx.warp.target.1")                           # the mouse: "faces"
    assert p.base == FACES and st.values["warp"]["target"] == FACES
    assert st.chain(FACES) == ["warp"] and st.chain(FRAME) == ["plasma"]
    lit.clear()
    fxpage.frame()
    assert ("onto.fx.warp.target.1", True) in lit and ("onto.fx.warp.target.0", False) in lit
    assert "faces  Trip warp" in fxpage.texts and fxpage.wrapped[0] == "frame  Plasma"
    # running on the faces: the faint line where the idle line would be, one line wide
    assert FAINT_FACES in fxpage.texts and fxpage.colors[FAINT_FACES] == (
        ui.FAINT.x, ui.FAINT.y, ui.FAINT.z, ui.FAINT.w)
    imgui.new_frame()
    assert imgui.calc_text_size(FAINT_FACES).x < 392    # the page's width in the panel
    imgui.end_frame()
    # nothing else moved: the stack order, the open strip, every other target
    assert st.names() == order_was and st.selected() == "warp"
    assert [n for n in st.names() if st.values[n]["target"] == FACES] == ["warp"]
    fxpage.click("onto.fx.warp.target.1")                           # the lit one again: no change
    assert p.base == FACES
    fxpage.click("onto.fx.warp.target.0")                           # …and back
    assert p.base == FRAME and st.chain(FACES) == [] and st.chain(FRAME) == st.chain()
    fxpage.frame()
    assert not [t for t in fxpage.texts if t.startswith("faces")]
    assert FAINT_FACES not in fxpage.texts


def test_a_chip_aimed_at_the_faces_is_marked(fxpage, monkeypatch):
    """A diamond for the LED of a chip aimed at the faces — filled while on,
    outlined while off — where a chip on the frame has a dot or a ring; and
    both of its hovers say "on the faces"."""
    from hyperspace.fx import FACES
    from hyperspace.ui_fx import FACES_TIP, LED_OFF_TIP, LED_ON_TIP, _led_tip
    imgui, st, reg, panel = fxpage.imgui, fxpage.st, fxpage.reg, fxpage.panel
    marks: list[tuple[str, float, float]] = []
    dl_type = imgui.ImDrawList
    for fn in ("add_quad_filled", "add_quad", "add_circle_filled", "add_circle"):
        real = getattr(dl_type, fn)

        def rec(self, *a, _fn=fn, _real=real, **k):
            pts = a[:4] if _fn.startswith("add_quad") else a[:1]
            marks.append((_fn, sum(q.x for q in pts) / len(pts), sum(q.y for q in pts) / len(pts)))
            return _real(self, *a, **k)
        monkeypatch.setattr(dl_type, fn, rec)

    def mark(name):
        """What is drawn at the centre of `name`'s LED."""
        x0, y0, x1, y1 = fxpage.rects[f"led.fx.{name}.on"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return [fn for fn, x, y in marks if abs(x - cx) < 0.5 and abs(y - cy) < 0.5]
    reg["fx.warp.on"].set(True)
    reg["fx.plasma.on"].set(True)
    reg["fx.plasma.target"].set(FACES)
    reg["fx.glimmer.target"].set(FACES)
    st.select("acid")
    fxpage.frame()
    assert mark("warp") == ["add_circle_filled"]         # on the frame: the dot…
    assert mark("acid") == ["add_circle"]                # …and the ring
    assert mark("plasma") == ["add_quad_filled"]         # on the faces: the diamond, filled…
    assert mark("glimmer") == ["add_quad"]               # …and outlined while off
    # nothing else on the chip changes: the same two items, the same rects
    faces_rects = {k: fxpage.rects[k] for k in ("led.fx.plasma.on", "chip.fx.plasma.on")}
    reg["fx.plasma.target"].set(0)
    reg["fx.glimmer.target"].set(0)
    marks.clear()
    fxpage.frame()
    assert mark("plasma") == ["add_circle_filled"] and mark("glimmer") == ["add_circle"]
    reg["fx.plasma.target"].set(FACES)
    marks.clear()
    fxpage.frame()
    assert {k: fxpage.rects[k] for k in faces_rects} == faces_rects
    # the hovers: the LED's says what a click does, then where the effect is aimed
    p = reg["fx.plasma.on"]
    assert FACES_TIP == "on the faces"
    assert _led_tip(panel, p, True) == f"{LED_ON_TIP}\n{FACES_TIP}"
    assert _led_tip(panel, reg["fx.glimmer.on"], True) == f"{LED_OFF_TIP}\n{FACES_TIP}"
    assert _led_tip(panel, p) == LED_ON_TIP
    tips = []
    monkeypatch.setattr(imgui, "set_tooltip", lambda t: tips.append(t))
    io = imgui.get_io()
    for item, want in (("led.fx.plasma.on", f"{LED_ON_TIP}\n{FACES_TIP}"),
                       ("chip.fx.plasma.on", f"{p.tip}\n{FACES_TIP}"),
                       ("chip.fx.warp.on", reg["fx.warp.on"].tip)):
        x0, y0, x1, y1 = fxpage.rects[item]
        io.add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
        for _ in range(3):
            tips.clear()
            fxpage.frame()
        assert tips == [want], item


def test_why_idle_names_faces_off():
    """ "faces off" after "off" and before "bypassed"; and with the default
    argument why_idle still agrees with FxState.chain() for an effect aimed
    at the faces (chain() lists it whatever view.faces is)."""
    from itertools import product

    from hyperspace.fx import FACES, FRAME
    from hyperspace.ui_fx import why_idle
    st = FxState()
    v = st.values["warp"]
    v.update(on=True, target=FACES)
    assert why_idle(st, "warp") is None and why_idle(st, "warp", True) is None
    assert why_idle(st, "warp", False) == "faces off"
    # its place in the order: every later reason holding as well
    v["mix"] = 0.0
    st.mix = 0.0
    st.on = False
    assert why_idle(st, "warp", False) == "faces off"
    assert why_idle(st, "warp", True) == "bypassed"
    v["on"] = False
    assert why_idle(st, "warp", False) == "off"
    # an effect on the frame never reads "faces off"
    v.update(on=True, target=FRAME)
    assert why_idle(st, "warp", False) == "bypassed"
    v.pop("target")                                   # a values dict from before a hot reload
    assert why_idle(st, "warp", False) == "bypassed"
    # every effect in every state, half of them aimed at the faces
    seen = set()
    for on, bypass, fxmix, mix, faces_on in product(
            (True, False), (True, False), (1.0, 0.0), (1.0, 0.0), (True, False)):
        st.on, st.mix = bypass, fxmix
        for k, n in enumerate(st.names()):
            st.values[n].update(on=on, mix=mix, target=k % 2)
        running = st.chain()
        assert running == sorted(st.chain(FRAME) + st.chain(FACES), key=st.names().index)
        for n in st.names():
            assert (why_idle(st, n) is None) == (n in running), (n, on, bypass, fxmix, mix)
            why = why_idle(st, n, faces_on)
            seen.add(why)
            aimed = st.values[n]["target"] == FACES
            assert (why == "faces off") == (on and aimed and not faces_on)
            if why != "faces off":
                assert why == why_idle(st, n)
    assert seen == {None, "off", "faces off", "bypassed", "fx mix 0", "mix 0"}


def test_faces_on_switches_the_faces_on(fxpage):
    """An open effect that is on and aimed at the faces while Faces is off
    says so, with the chip that mends it: Param.set on view.faces."""
    from hyperspace.fx import FACES
    from hyperspace.ui_fx import IDLE
    st, reg, view = fxpage.st, fxpage.reg, fxpage.panel.view
    line, chip, pid, _tip = IDLE["faces off"]
    assert (line, chip, pid) == ("aimed at the faces, and Faces is off", "faces on", "view.faces")
    assert list(IDLE)[:3] == ["off", "faces off", "bypassed"]
    assert view.faces is False
    st.select("warp")
    reg["fx.warp.target"].set(FACES)
    fxpage.frame()                                   # off: "off" comes first
    assert IDLE["off"][0] in fxpage.texts and line not in fxpage.texts
    reg["fx.warp.on"].set(True)
    fxpage.frame()
    assert line in fxpage.texts and "idle.view.faces" in fxpage.rects
    assert "idle.fx.warp.on" not in fxpage.rects and len(fxpage.veils) == 2
    # the line and its chip are one row inside the page's width
    assert fxpage.rects["idle.view.faces"][2] <= fxpage.rects["fx.mix"][2] + 1.5
    assert fxpage.rects["idle.view.faces"][3] <= fxpage.rects["fx.warp.on"][1]
    assert "faces  (Faces is off)" in fxpage.texts
    switches = {n: reg[f"fx.{n}.on"].base for n in st.names()}
    fxpage.click("idle.view.faces")
    assert reg["view.faces"].base is True and view.faces is True
    assert {n: reg[f"fx.{n}.on"].base for n in st.names()} == switches
    assert reg["fx.warp.target"].base == FACES and st.selected() == "warp"
    fxpage.frame()                                   # running: no line, no chip, no veil
    assert line not in fxpage.texts and "idle.view.faces" not in fxpage.rects
    assert not fxpage.veils and "faces  Trip warp" in fxpage.texts
    # an effect on the frame is not idle because Faces is off
    reg["view.faces"].set(False)
    reg["fx.warp.target"].set(0)
    fxpage.frame()
    assert line not in fxpage.texts and not fxpage.veils


def test_the_page_fits_with_the_faces_row_showing(fxpage, monkeypatch):
    """No page scrolls at the control size: every effect's strip in turn,
    aimed at the faces so the second status row shows, an error line on the
    strip — off, running, idle because Faces is off (the line with its
    chip), and with the renderer's face_error for the row."""
    from hyperspace.app import CONTROL_SIZE
    from hyperspace.fx import FACES
    from hyperspace.ui import PAGE_KEYS, Panel
    imgui, st, reg, panel = fxpage.imgui, fxpage.st, fxpage.reg, fxpage.panel
    assert tuple(imgui.get_io().display_size) == tuple(CONTROL_SIZE)
    panel.renderer.fx.error = lambda n: "line 3: made up"
    over, spare = [], []
    draw = Panel._page_fx

    def measured(self, dt):
        draw(self, dt)
        over.append(imgui.get_scroll_max_y())
        spare.append(imgui.get_content_region_avail().y)
    monkeypatch.setattr(Panel, "_page_fx", measured)
    reg["ui.page"].set(PAGE_KEYS.index("fx"))
    worst = (1e9, "")
    for name in st.names():
        st.select(name)
        reg[f"fx.{name}.target"].set(FACES)
        for state, on, faces_on, err in (
                ("off", False, True, ""),
                ("running", True, True, ""),
                ("faces off", True, False, ""),
                ("face error", False, True, "faces: RuntimeError: made up")):
            reg[f"fx.{name}.on"].set(on)
            reg["view.faces"].set(faces_on)
            panel.renderer.face_error = err
            for _ in range(3):
                fxpage.texts.clear()
                imgui.new_frame()
                panel.draw(1 / 60, 60.0)
                imgui.end_frame()
            assert any(t.startswith("faces") for t in fxpage.texts), (name, state)
            assert "line 3: made up" in fxpage.texts
            assert ("aimed at the faces, and Faces is off" in fxpage.texts) == (state == "faces off")
            assert over[-1] == 0, f"the fx page scrolls with {name} open, aimed at the faces, {state}"
            worst = min(worst, (spare[-1], f"{name}, {state}"))
        reg[f"fx.{name}.target"].set(0)
        reg[f"fx.{name}.on"].set(False)
    print(f"fx page with the faces row: {worst[0]:.0f} px to spare at worst ({worst[1]})")
    assert worst[0] >= 0


def test_the_target_and_the_map_are_one_undo_step_each(tmp_path, monkeypatch):
    """The ONTO chips and the map chips write a base through Param.set and
    push nothing: undo's watcher makes each change one step ("Scene-setters
    write the base")."""
    from test_undo import boot, frames, labels, settle

    from hyperspace import undo
    from hyperspace.fx import FACES, FRAME, PER_FACE, SCREEN
    st = FxState()
    r = boot(tmp_path / "home", fx=st)
    r.fx = st
    pushes = []
    real_push = undo.push
    monkeypatch.setattr(undo, "push", lambda *a, **k: (pushes.append(a), real_push(*a, **k))[1])
    rig = PageRig(tmp_path, monkeypatch, r)
    try:
        st.select("warp")
        r.reg["fx.warp.target"].set(FRAME)
        r.reg["fx.face_map"].set(PER_FACE)
        settle(r)
        start = labels(r)
        rig.click(f"onto.fx.warp.target.{FACES}")
        settle(r)
        assert r.reg["fx.warp.target"].base == FACES
        assert len(labels(r)) == len(start) + 1 and not pushes
        rig.click(f"map.fx.face_map.{SCREEN}")
        settle(r)
        assert r.reg["fx.face_map"].base == SCREEN
        assert len(labels(r)) == len(start) + 2 and not pushes
        undo.undo()
        frames(r, 3)
        assert r.reg["fx.face_map"].base == PER_FACE and r.reg["fx.warp.target"].base == FACES
        undo.undo()
        frames(r, 3)
        assert r.reg["fx.warp.target"].base == FRAME and labels(r) == start
    finally:
        rig.close()


# ---------------------------------------------------------------- drag a chip to reorder (plan 20 WP3)

FACTORY_ORDERS = {"plasma": 5, "acid": 10, "kaleido": 15, "zoomblur": 17, "warp": 20,
                  "wobble": 25, "doublevision": 30, "deconverge": 40, "fractals": 60,
                  "glimmer": 70, "tripcolour": 80, "huecycle": 85, "palette": 95}


def _moved_to(names: list[str], moved: str, place: int) -> list[str]:
    """`names` with `moved` taken out and put back at `place`."""
    seq = [n for n in names if n != moved]
    seq.insert(place, moved)
    return seq


def _sorted_by(orders: dict[str, int]) -> list[str]:
    return sorted(orders, key=lambda n: (orders[n], n))      # FxState.names()'s rule


def _fewest(seq: list[str], orders: dict[str, int]) -> int:
    """The fewest orders any rewrite must change for `seq` to sort that
    way, by trying every set of effects to leave alone (small lists only)."""
    from itertools import combinations

    from hyperspace.fx import MAX_ORDER
    for k in range(len(seq) + 1):
        for changed in combinations(seq, k):
            prev, prev_name, ok = -1, None, True     # prev_name: None after a rewritten one
            for n in seq:
                if n in changed:
                    prev, prev_name = prev + 1, None  # the smallest integer still free
                else:
                    o = orders[n]
                    if not (o > prev or (o == prev and prev_name is not None and prev_name < n)):
                        ok = False
                        break
                    prev, prev_name = o, n
                if prev > MAX_ORDER:
                    ok = False
                    break
            if ok:
                return k
    raise AssertionError("no rewrite at all")


def test_reordered_moves_one_effect_when_there_is_room():
    from hyperspace.fx import reordered
    st = FxState()
    orders = {n: st.values[n]["order"] for n in st.names()}
    assert orders == FACTORY_ORDERS
    names = st.names()
    for moved in names:
        for place in range(len(names)):
            seq = _moved_to(names, moved, place)
            new = reordered(seq, orders, moved)
            if seq == names:
                assert new == {}, (moved, place)             # dropped where it was
                continue
            # every single move changes exactly one order: the moved effect's
            assert list(new) == [moved], (moved, place, new)
            a = orders[seq[place - 1]] if place else -1
            b = orders[seq[place + 1]] if place + 1 < len(seq) else 100
            assert new[moved] == (a + b) // 2 and a < new[moved] < b
            assert _sorted_by({**orders, **new}) == seq
    # the one gap of one integer: between 15 and 17, twice running
    seq = _moved_to(names, "huecycle", names.index("zoomblur"))
    once = {**orders, **reordered(seq, orders, "huecycle")}
    assert once["huecycle"] == 16
    again = _moved_to(_sorted_by(once), "plasma", 3)         # between 15 and 16: no room
    new = reordered(again, once, "plasma")
    assert len(new) == 2 and "plasma" in new and _sorted_by({**once, **new}) == again
    # the inputs are read, never written
    assert orders == FACTORY_ORDERS


def test_reordered_renumbers_the_smallest_window():
    from itertools import permutations

    from hyperspace.fx import reordered
    orders = {"a": 10, "b": 11, "c": 12, "d": 40, "e": 41}
    names = _sorted_by(orders)
    # d between a and b: no integer between 10 and 11. One neighbour moves
    # with it (a: 10 → lower), not the whole packed run
    seq = ["a", "d", "b", "c", "e"]
    new = reordered(seq, orders, "d")
    assert set(new) == {"a", "d"} and _sorted_by({**orders, **new}) == seq
    assert new["a"] < new["d"] < 11 and orders["b"] == 11
    # a to the end: 41 < a < 100, alone
    assert reordered(["b", "c", "d", "e", "a"], orders, "a") == {"a": 70}
    # e to the front: alone again
    assert reordered(["e", "a", "b", "c", "d"], orders, "e") == {"e": 4}
    # stable: the same drop gives the same orders, whatever the dict's order
    for perm in permutations(orders.items()):
        assert reordered(seq, dict(perm), "d") == new
    # every move over lists packed tight in different places: the result
    # sorts to what was asked, and no rewrite of fewer orders would
    for packed in ({"a": 10, "b": 11, "c": 12, "d": 13, "e": 14},
                   {"a": 0, "b": 1, "c": 2, "d": 3, "e": 50},
                   {"a": 50, "b": 96, "c": 97, "d": 98, "e": 99},
                   {"a": 0, "b": 1, "c": 2, "d": 98, "e": 99},
                   orders):
        names = _sorted_by(packed)
        for moved in names:
            for place in range(len(names)):
                seq = _moved_to(names, moved, place)
                new = reordered(seq, packed, moved)
                after = {**packed, **new}
                assert _sorted_by(after) == seq, (packed, moved, place, new)
                assert len(set(after.values())) == len(after)            # no tie made
                assert all(o != packed[n] for n, o in new.items())       # only real changes
                assert len(new) == _fewest(seq, packed), (packed, moved, place, new)
    # ties that are already there (two effects at one order, told apart by
    # name) are left alone unless the move lands between them
    tied = {"a": 10, "b": 10, "c": 10, "d": 30}
    assert reordered(["a", "b", "c", "d"], tied, "b") == {}
    new = reordered(["d", "a", "b", "c"], tied, "d")
    assert list(new) == ["d"] and new["d"] < 10
    seq = ["a", "d", "b", "c"]                                           # between two of the tie
    new = reordered(seq, tied, "d")
    assert _sorted_by({**tied, **new}) == seq and "c" not in new
    seq = ["b", "a", "c", "d"]                                           # the tie itself reordered
    new = reordered(seq, tied, "b")
    assert _sorted_by({**tied, **new}) == seq and "d" not in new


def test_reordered_always_sorts_to_the_sequence_asked_for():
    from hyperspace.fx import MAX_ORDER, reordered
    hundred = {f"e{k:03d}": k for k in range(MAX_ORDER + 1)}     # every order taken
    for orders in (FACTORY_ORDERS, hundred):
        names = _sorted_by(orders)
        for moved in names:
            for place in range(len(names)):
                seq = _moved_to(names, moved, place)
                new = reordered(seq, orders, moved)
                after = {**orders, **new}
                assert _sorted_by(after) == seq, (moved, place)
                assert all(isinstance(o, int) and 0 <= o <= MAX_ORDER for o in new.values())
                assert len(set(after.values())) == len(after)    # never a tie to break by name
    # and a run of drops, each from the state the last one left
    import random
    rnd = random.Random(20)
    orders = dict(FACTORY_ORDERS)
    for _ in range(400):
        names = _sorted_by(orders)
        moved = rnd.choice(names)
        seq = _moved_to(names, moved, rnd.randrange(len(names)))
        orders.update(reordered(seq, orders, moved))
        assert _sorted_by(orders) == seq and all(0 <= o <= MAX_ORDER for o in orders.values())


def _bars(fxpage, monkeypatch) -> list[tuple[float, float, float, float]]:
    """Every DRAG_BAR-wide filled rect drawn from here on: the drop bars."""
    from hyperspace.ui_fx import DRAG_BAR
    bars: list[tuple[float, float, float, float]] = []
    dl_type = fxpage.imgui.ImDrawList
    real = dl_type.add_rect_filled

    def rec(self, lo, hi, *a, **k):
        if hi.x - lo.x == pytest.approx(DRAG_BAR):
            bars.append((lo.x, lo.y, hi.x, hi.y))
        return real(self, lo, hi, *a, **k)
    monkeypatch.setattr(dl_type, "add_rect_filled", rec)
    return bars


def test_a_drop_reorders_selects_and_is_one_undo_step(tmp_path, monkeypatch):
    """A simulated mouse drags one chip by its name onto another, over the
    real Panel with a real Undo: the dragged effect goes before the one it
    was dropped on, its strip opens, and the whole reorder — one order
    rewritten or several — is one step, "reorder effects"."""
    from test_undo import boot, frames, labels, settle

    from hyperspace import undo
    from hyperspace.ui_fx import REORDER
    st = FxState()
    r = boot(tmp_path / "home", fx=st)
    r.fx = st
    pushes = []
    real_push = undo.push
    monkeypatch.setattr(undo, "push", lambda *a, **k: (pushes.append(a), real_push(*a, **k))[1])
    rig = PageRig(tmp_path, monkeypatch, r)
    without_palette(st, r.reg)
    bars = _bars(rig, monkeypatch)
    try:
        for n, o in FACTORY_ORDERS.items():          # whatever the startup preset left
            if n in st.specs:
                r.reg[f"fx.{n}.order"].set_value(o)
        st.select("acid")
        settle(r)
        start, names = labels(r), st.names()
        assert names[0] == "plasma" and names[-1] == "huecycle"

        def orders():
            return {n: r.reg[f"fx.{n}.order"].base for n in st.names()}
        before = orders()
        # in flight over Plasma: a bar at the left edge of the chip under the mouse
        rig.drag("chip.fx.huecycle.on", "chip.fx.plasma.on", release=False)
        assert rig.imgui.get_drag_drop_payload_py_id().data_id == names.index("huecycle")
        led = rig.rects["led.fx.plasma.on"]
        assert bars and bars[-1][0] + 1 == pytest.approx(led[0])     # on the chip's own edge
        assert bars[-1][1] <= led[1] and bars[-1][3] >= led[3]
        assert orders() == before and not pushes and st.selected() == "acid"   # nothing yet
        rig.release()
        settle(r)
        assert st.names() == ["huecycle", *names[:-1]]
        assert st.selected() == "huecycle" and st.sel_name == "huecycle"   # the strip opens on it
        after = orders()
        assert {n for n in after if after[n] != before[n]} == {"huecycle"} and after["huecycle"] == 2
        assert pushes == [(REORDER,)] and labels(r) == [*start, "reorder effects"]
        undo.undo()                                  # what edit.undo (⌘Z / Ctrl+Z) fires
        frames(r, 3)
        assert orders() == before and st.names() == names and labels(r) == start
        assert st.selected() == "huecycle"           # the open strip is no undo step
        undo.redo()
        frames(r, 3)
        assert orders() == after

        # a drop that has to rewrite several orders is still one push, one step
        undo.undo()
        frames(r, 3)
        for k, n in enumerate(names):                # packed: no gap anywhere near the front
            r.reg[f"fx.{n}.order"].set_value(k)
        settle(r)
        start, before = labels(r), orders()
        pushes.clear()
        rig.drag("chip.fx.huecycle.on", "led.fx.acid.on")      # the LED takes a drop too
        settle(r)
        assert st.names() == ["plasma", "huecycle", *names[1:-1]]
        after = orders()
        assert len({n for n in after if after[n] != before[n]}) > 1
        assert pushes == [(REORDER,)] and labels(r) == [*start, "reorder effects"]
        undo.undo()
        frames(r, 3)
        assert orders() == before and labels(r) == start

        # a drop that changes nothing — onto the chip already after it — is no step
        pushes.clear()
        rig.drag("chip.fx.plasma.on", "chip.fx.acid.on")
        settle(r)
        assert orders() == before and not pushes and labels(r) == start
        assert st.selected() == "plasma"
    finally:
        rig.close()


def test_a_click_without_a_drag_still_only_opens(fxpage, monkeypatch):
    """imgui starts a drag only past its drag threshold: a press and a
    release on a name — the mouse still, or shaking a pixel or two — opens
    the strip and moves nothing; the LED still only switches."""
    from hyperspace import undo
    imgui, st, reg = fxpage.imgui, fxpage.st, fxpage.reg
    pushes = []
    monkeypatch.setattr(undo, "push", lambda *a, **k: pushes.append(a))
    io = imgui.get_io()
    names = st.names()
    orders = {n: reg[f"fx.{n}.order"].base for n in names}
    switches = {n: reg[f"fx.{n}.on"].base for n in names}
    fxpage.frame()
    assert st.selected() == "plasma"
    fxpage.click("chip.fx.warp.on")
    assert st.selected() == "warp"
    # a shaky click: under the threshold, and released on the same chip
    x0, y0, x1, y1 = fxpage.rects["chip.fx.fractals.on"]
    x, y = (x0 + x1) / 2, (y0 + y1) / 2
    assert io.mouse_drag_threshold >= 4
    io.add_mouse_pos_event(x, y)
    fxpage.frame()
    io.add_mouse_button_event(0, True)
    fxpage.frame()
    for dx, dy in ((1, 0), (2, 1), (1, -1), (0, 0)):
        io.add_mouse_pos_event(x + dx, y + dy)
        fxpage.frame()
        assert imgui.get_drag_drop_payload_py_id() is None
    io.add_mouse_button_event(0, False)
    fxpage.frame()
    io.add_mouse_pos_event(-1.0, -1.0)
    fxpage.frame()
    assert st.selected() == "fractals"
    fxpage.click("led.fx.fractals.on")               # the LED: switches, never opens or drags
    switches["fractals"] = True
    fxpage.click("chip.fx.warp.on")
    # a press on an LED dragged away is not a drag: the LED is no source
    fxpage.drag("led.fx.acid.on", "chip.fx.plasma.on")
    assert st.names() == names and st.selected() == "warp"
    assert {n: reg[f"fx.{n}.order"].base for n in names} == orders and not pushes
    assert {n: reg[f"fx.{n}.on"].base for n in names} == switches


def test_a_drag_never_changes_a_target_or_a_switch(fxpage, monkeypatch):
    """A drag changes order and nothing else (fork F6: an effect is re-aimed
    by its strip's ONTO chips): every drop — onto a name, an LED, the
    last chip's far half, its own chip — leaves every switch, target and
    mix, and the map, as they were."""
    from hyperspace.fx import FACES, SCREEN
    st, reg = fxpage.st, fxpage.reg
    bars = _bars(fxpage, monkeypatch)
    reg["fx.warp.on"].set(True)
    reg["fx.plasma.on"].set(True)
    reg["fx.plasma.target"].set(FACES)
    reg["fx.glimmer.target"].set(FACES)
    reg["fx.face_map"].set(SCREEN)
    fxpage.panel.view.faces = True

    def rest():
        return {n: {k: v for k, v in st.values[n].items() if k != "order"} for n in st.specs}
    was, names = rest(), st.names()
    # a face-aimed chip dragged among frame ones, and a frame one among face ones
    fxpage.drag("chip.fx.plasma.on", "chip.fx.warp.on")
    assert st.names().index("plasma") == st.names().index("warp") - 1 and st.selected() == "plasma"
    fxpage.drag("chip.fx.warp.on", "led.fx.glimmer.on")
    assert st.names().index("warp") == st.names().index("glimmer") - 1 and st.selected() == "warp"
    assert st.chain(FACES) == ["plasma"] and st.chain() == ["plasma", "warp"]
    # the last chip's right half is "to the end": the bar is at its right edge
    last = st.names()[-1]
    assert last == "huecycle"
    fxpage.drag("chip.fx.acid.on", f"chip.fx.{last}.on", dst_at=0.9, release=False)
    assert bars[-1][0] + 1 == pytest.approx(fxpage.rects[f"chip.fx.{last}.on"][2])
    fxpage.release()
    assert st.names()[-1] == "acid" and reg["fx.acid.order"].base > reg["fx.huecycle.order"].base
    # …and its left half is "before it", like any other chip
    fxpage.drag("chip.fx.kaleido.on", "chip.fx.acid.on", dst_at=0.1)
    assert st.names()[-2:] == ["kaleido", "acid"]
    # onto its own LED: where it is
    now = st.names()
    fxpage.drag("chip.fx.wobble.on", "led.fx.wobble.on")
    assert st.names() == now and st.selected() == "wobble"
    assert rest() == was and st.face_map == SCREEN and sorted(now) == sorted(names)
    assert reg["fx.plasma.target"].base == FACES and reg["fx.warp.target"].base == 0
    # no bar once nothing is in the hand
    bars.clear()
    fxpage.frame()
    assert not bars


def test_the_order_slider_still_reorders(fxpage):
    """Fork F7's fallback: the strip's order slider is still there and still
    moves its effect through the stack, the strip staying open on it."""
    st, reg = fxpage.st, fxpage.reg
    st.select("plasma")
    fxpage.frame()
    assert "fx.plasma.order" in fxpage.rects and st.names()[0] == "plasma"
    fxpage.click("fx.plasma.order", 0.95)
    assert reg["fx.plasma.order"].base > 85 and st.names()[-1] == "plasma"
    assert st.selected() == "plasma"
    fxpage.click("fx.plasma.order", 0.05)
    assert reg["fx.plasma.order"].base < 10 and st.names()[0] == "plasma"
    # and after a drag the slider reads what the drop wrote
    fxpage.drag("chip.fx.plasma.on", "chip.fx.warp.on")
    assert st.values["plasma"]["order"] == reg["fx.plasma.order"].base == 18


def test_a_drop_moves_the_effect_the_drag_began_on(fxpage, monkeypatch):
    """Review of PR #108. What a drop moves is a name, not the payload's
    index: the stack reordered under the hand (a preset on a desk button,
    an undo) still moves the chip that was picked up. A press that slips
    past the drag threshold and is let go on the same name opens it. An
    order the registry does not hold, or a result that would not sort as
    asked, makes the drop do nothing."""
    from hyperspace import fx as fx_mod
    from hyperspace import ui_fx, undo
    imgui, st, reg, panel = fxpage.imgui, fxpage.st, fxpage.reg, fxpage.panel
    pushes = []
    monkeypatch.setattr(undo, "push", lambda *a, **k: pushes.append(a))
    io = imgui.get_io()
    fxpage.drag("chip.fx.huecycle.on", "chip.fx.warp.on", release=False)
    assert panel._fx_drag == "huecycle"
    assert imgui.get_drag_drop_payload_py_id().data_id == 11       # huecycle's place
    # the stack moves under the hand just before the release frame (the
    # source re-sets the payload only while the button is down, so on the
    # drop it is the last held frame's index): index 11 is now tripcolour,
    # and warp's chip, under the mouse, stays put
    held = st.names()
    reg["fx.tripcolour.order"].set_value(99)
    assert st.names() == [*held[:10], "huecycle", "tripcolour"] and held[11] == "huecycle"
    fxpage.release()
    names = st.names()
    assert names.index("huecycle") == names.index("warp") - 1 and st.selected() == "huecycle"
    assert reg["fx.tripcolour.order"].base == 99 and pushes == [("reorder effects",)]
    fxpage.frame()
    assert panel._fx_drag is None                    # nothing in the hand: nothing noted

    # a slipped click: past the threshold, let go on the name it began on
    pushes.clear()
    fxpage.frame()
    x0, y0, _, y1 = fxpage.rects["chip.fx.fractals.on"]
    x, y = x0 + 12, (y0 + y1) / 2
    io.add_mouse_pos_event(x, y)
    fxpage.frame()
    io.add_mouse_button_event(0, True)
    fxpage.frame()
    for k in range(1, 5):
        io.add_mouse_pos_event(x + 4 * k, y)
        fxpage.frame()
    assert ui_fx._in_flight() and st.selected() == "huecycle"
    fxpage.release()
    assert st.selected() == "fractals" and st.names() == names and not pushes

    # an order the registry does not hold: nothing is written, nothing pushed
    orders = {n: st.values[n]["order"] for n in names}
    real_get = type(reg).get
    monkeypatch.setattr(type(reg), "get", lambda self, pid: None if pid == "fx.acid.order"
                        else real_get(self, pid))
    ui_fx._drop(panel, st, "acid", None)
    assert {n: st.values[n]["order"] for n in names} == orders and not pushes
    monkeypatch.setattr(type(reg), "get", real_get)
    # a rewrite that would not sort as asked (what a hundred-odd effects give)
    monkeypatch.setattr(ui_fx, "reordered", lambda seq, o, moved: {moved: o[seq[-1]]})
    ui_fx._drop(panel, st, "acid", "kaleido")
    assert {n: st.values[n]["order"] for n in names} == orders and not pushes
    monkeypatch.setattr(ui_fx, "reordered", fx_mod.reordered)
    ui_fx._drop(panel, st, "acid", None)
    assert st.names()[-1] == "acid" and pushes == [("reorder effects",)]
    # an effect whose file went away mid-drag: no raise
    ui_fx._drop(panel, st, "no_such_effect", "acid")
