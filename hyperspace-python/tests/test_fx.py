"""The effects (fx.py): effect files → registry params → GL passes.

The spec parser and the registry side run anywhere; the GL half needs a
standalone context and skips without one. What an effect *looks* like is
judged by eye (tools/fx_shots.py writes the shots); here every factory
file must parse, compile and change the frame, the off path must stay a
copy, and a pass's own blend and alpha rules are checked against numpy.
Plan 33 T7: an effect runs where the graph wires it, so a rig that switches
effects on by hand gets its run as a load lands it
(`graphmigrate.wiring_of`); the FX page browses the graph's effects.
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
    for pid in ("fx.on", "fx.mix", "fx.face_map", "fx.warp.on", "fx.warp.mix",
                "fx.warp.speed", "fx.warp.blend", "fx.warp.amount", "fx.kaleido.segments"):
        assert pid in r, pid
    for pid in ("fx.select", "fx.warp.order", "fx.warp.target"):     # plan 33 T7: retired
        assert pid not in r, pid
    assert all(p.group == "fx" for p in r)
    assert r["fx.kaleido.segments"].integer
    assert r["fx.warp.scale"].log
    # a fader writes the state the chain reads, and back
    r["fx.warp.amount"].set_value(1.25)
    assert st.values["warp"]["amount"] == pytest.approx(1.25)
    st.values["warp"]["on"] = True
    assert r["fx.warp.on"].value is True


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

def test_live_follows_the_bypass_and_the_mixes():
    """`FxState.live` (plan 33 R): an effect draws where it is wired while it
    is on above mix 0 and the effects are on above FX mix 0 — no order, no
    target. (The run's order is its wires: test_graph_free.py.)"""
    st = FxState()
    for n in ("warp", "acid", "huecycle"):
        st.values[n]["on"] = True
    assert {n for n in st.names() if st.live(n)} == {"warp", "acid", "huecycle"}
    st.values["warp"]["mix"] = 0.0
    assert not st.live("warp") and st.live("acid")              # a dry effect reads through
    st.on = False
    assert not any(st.live(n) for n in st.names())
    st.on, st.mix = True, 0.0
    assert not any(st.live(n) for n in st.names())
    assert not st.live("no_such_effect")


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
    from hyperspace.graphmigrate import wiring_of
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, fx=fx)
    r.wiring = wiring_of(fx)        # plan 33 R23: the run the effects on make, as a load
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


# plan 32 T7: displace and blend bend the frame by the picture wired into
# their aux input; with none (here) they leave it as it is, by design —
# tests/test_media_faces_aux.py holds them with an aux
AUX_ONLY = {"displace", "blend"}


@pytest.mark.parametrize("name", sorted(set(FxState().specs) - AUX_ONLY))
def test_each_effect_changes_the_frame(ctx, name):
    base = render(ctx, FxState())
    st = FxState()
    st.values[name]["on"] = True
    if name == "glimmer":
        st.values[name]["density"] = 1.0
    if name == "palette":                  # it starts at mix 0 (today's picture): turn it up
        st.values[name].update(mix=1.0, hue_from=155.0, hue_to=245.0)
    img = render(ctx, st)
    assert ctx.error == "GL_NO_ERROR"
    diff = np.abs(img[..., :3].astype(int) - base[..., :3]).sum()
    assert diff > W * H * 0.05, f"{name} left the frame (almost) as it was"


def test_a_compile_error_is_reported_and_skipped(ctx, fxdir):
    """A file that does not compile says why (`error`), and its node reads
    through: `run_one` copies its source across, so the picture arrives."""
    write(fxdir, "good", EFFECT.replace("@blend add", "@blend mix"))
    write(fxdir, "bad", EFFECT.replace("src(uv) * u_amount", "src(uv) * nope"))
    st = FxState(fxdir)
    for n in ("good", "bad"):
        st.values[n]["on"] = True
    chain = FxChain(ctx, st)
    errs = chain.compile_all()
    assert set(errs) == {"bad"} and "line" in errs["bad"]
    assert chain.error("bad") == errs["bad"]
    assert chain.ready("good") and not chain.ready("bad")
    (src, src_fbo), (_, dst_fbo) = chain.pool((8, 8))
    src_fbo.use()
    ctx.clear(0.5, 0.25, 0.75, 1.0)
    chain.run_one("bad", src, dst_fbo, 0.0)
    px = np.frombuffer(dst_fbo.read(components=4, dtype="f2"), dtype=np.float16)
    assert np.allclose(px.reshape(8, 8, 4)[4, 4], [0.5, 0.25, 0.75, 1.0], atol=1e-3)


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
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((4, 4), 4)])
    a = np.array([0.4, 0.2, 0.1, 0.5])            # a premultiplied, half-covered pixel
    (src, src_fbo), _ = chain.pool((4, 4))
    src_fbo.use()
    ctx.clear(*a)
    chain.run_one("const", src, fbo, 0.0)
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
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((64, 40), 4)])
    (src, src_fbo), _ = chain.pool((64, 40))
    src_fbo.use()
    ctx.clear(0.0, 0.0, 0.0, 0.0)
    chain.run_one("plasma", src, fbo, 1.0)
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
    from hyperspace.graphmigrate import wiring_of
    lib.load("fx", "noita heavily tripping")
    assert wiring_of(st).run == ("warp", "fractals", "tripcolour")      # by their @order
    assert st.values["warp"]["amount"] == pytest.approx(0.9)
    lib.load("fx", "acid")                           # unnamed ids fall back: warp goes off
    run = wiring_of(st).run
    assert not st.live("warp") and st.live("acid") and "acid" in run and "warp" not in run


def shell(tmp_path):
    """The shell's rig (tests/test_ui_shell.py: the real Panel and its
    pages) at the control size, its renderer a stand-in holding a live
    FxState — the registry's `fx.*` its own. A context manager; yields
    (rig, the FxState, the stand-in)."""
    from contextlib import contextmanager

    from imgui_bundle import imgui
    from test_ui_shell import build_rig

    from hyperspace.app import CONTROL_SIZE
    from hyperspace.lookback import DreamState

    @contextmanager
    def made():
        st = FxState()
        stand_in = SimpleNamespace(fx=SimpleNamespace(state=st, error=lambda n: ""),
                                   lookback=SimpleNamespace(state=DreamState()))
        with build_rig(tmp_path, renderer=stand_in) as rig:
            imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
            yield rig, st, stand_in
    return made()


def test_the_page_draws_and_fits(tmp_path, monkeypatch):
    """The FX page at the control size over a party preset's graph (TRIP:
    its run), nothing open, then each of its effects' strips with an error
    line on it, then the longest strip of all: it never scrolls."""
    from imgui_bundle import imgui
    from test_ui_shell import frame

    from hyperspace import ui_fx
    from hyperspace.ui import Panel
    with shell(tmp_path) as (rig, st, stand_in):
        rig.lib.presets.load("TRIP")
        stand_in.fx.error = lambda n: "line 3: made up"
        listed = [n for _, ns in ui_fx.groups(rig.lib.presets.graph.spec) for n in ns]
        assert listed
        over = []
        draw = Panel._page_fx

        def measured(self, dt):
            draw(self, dt)
            over.append(imgui.get_scroll_max_y())
        monkeypatch.setattr(Panel, "_page_fx", measured)
        longest = max(st.specs, key=lambda n: len(st.specs[n].params))
        for sel in (None, *listed, longest):
            rig.panel.fx_selected = sel
            for _ in range(3):
                frame(rig.panel, "fx")
            assert over and over[-1] == 0, f"the fx page scrolls with {sel} open"


def test_the_page_has_no_conflicting_ids(tmp_path, monkeypatch):
    """Every widget on the FX page has its own imgui id — an effect listed
    in two groups is two rows, each under its group's id, and the open
    strip's own widgets are apart from its rows'. The ids are imgui's own
    (`get_id`, the id stack included), every effect's strip open in turn."""
    from imgui_bundle import imgui

    from hyperspace import ui_fx
    rig = browsing(tmp_path, monkeypatch)
    try:
        ids: list[int] = []
        names: dict[int, str] = {}
        for fn in ("button", "checkbox", "slider_float", "slider_int", "combo",
                   "invisible_button", "begin_popup_context_item"):
            real = getattr(imgui, fn)

            def rec(label, *a, _real=real, **k):
                i = imgui.get_id(label)
                ids.append(i)
                names[i] = label
                return _real(label, *a, **k)
            monkeypatch.setattr(imgui, fn, rec)
        listed = [n for _, ns in ui_fx.groups(rig.app.presets.graph.spec) for n in ns]
        assert listed.count("acid.3") == 2
        for name in [None, *dict.fromkeys(listed)]:
            rig.panel.fx_selected = name
            ids.clear()
            rig.frame()
            dup = sorted({names[i] for i in ids if ids.count(i) > 1})
            assert not dup, f"{name}: conflicting ids {dup}"
    finally:
        rig.close()


def test_the_selection_is_a_name_a_load_keeps(tmp_path, monkeypatch):
    """The open strip is a name (`Panel.fx_selected`, the one selection
    GRAPH shares): a preset load never moves it, nothing saves it, and a
    name the loaded graph lacks still opens its strip — or says there is
    no such effect."""
    rig = browsing(tmp_path, monkeypatch)
    try:
        rig.panel.fx_selected = "kaleido.2"
        rig.frame()
        assert "fx.kaleido.2.speed" in rig.rects
        rig.app.presets.load("TRIP")                 # kaleido.2 is no node of TRIP's
        rig.frame()
        assert rig.panel.fx_selected == "kaleido.2"
        assert "no effect kaleido.2" in rig.plain
        rig.panel.fx_selected = "warp"               # a file: its strip, in the graph or not
        rig.frame()
        assert "fx.warp.speed" in rig.rects
        assert not any("sel" in k for k in rig.app.presets.document("x")["values"])
    finally:
        rig.close()


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
        self.plain: list[str] = []       # every text_disabled line of the last frame
        real_plain = imgui.text_disabled

        def text_disabled(text):
            self.plain.append(text)
            return real_plain(text)
        monkeypatch.setattr(imgui, "text_disabled", text_disabled)

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
        self.plain.clear()
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


@pytest.fixture()
def fxpage(tmp_path, monkeypatch):
    rig = PageRig(tmp_path, monkeypatch)
    yield rig
    rig.close()


def test_a_rows_on_toggles_and_never_selects(tmp_path, monkeypatch):
    """A row is two click targets: its name picks the effect and never
    switches it (test_the_fx_page_lists_the_graphs_effects); its `on`
    switches it — a base through Param.set — and never picks it, nor any
    other effect's switch."""
    rig = browsing(tmp_path, monkeypatch)
    try:
        reg = rig.reg
        rig.panel.fx_selected = "acid.2"
        others = {p.id: p.base for p in reg if p.id.endswith(".on") and p.id != "fx.warp.on"}
        for want in (False, True, False):
            rig.click("on.Run.warp")
            assert reg["fx.warp.on"].base is want and rig.st.values["warp"]["on"] is want
            assert rig.panel.fx_selected == "acid.2"
            assert {p.id: p.base for p in reg if p.id in others} == others
    finally:
        rig.close()


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
    assert why_idle(st, "warp", faces_on=False) == "faces off"
    assert why_idle(st, "warp", faces_on=False, reached=False) == "reaches nothing"
    v["on"] = False
    assert why_idle(st, "warp", faces_on=False, reached=False) == "off"
    # every effect in every state: None exactly when `live` says it draws
    seen = set()
    for on, bypass, fxmix, mix in product((True, False), (True, False), (1.0, 0.3, 0.0),
                                          (1.0, 0.5, 0.0)):
        st.on, st.mix = bypass, fxmix
        for n in st.names():
            st.values[n].update(on=on, mix=mix)
        st.values["acid"].update(on=not on, mix=1.0)           # one effect out of step
        for n in st.names():
            why = why_idle(st, n)
            assert (why is None) == st.live(n), (n, on, bypass, fxmix, mix, why)
            seen.add(why)
    assert seen == {None, "off", "bypassed", "fx mix 0", "mix 0"}


def test_an_off_effects_strip_says_so_and_turn_on_switches_it_on(fxpage):
    from hyperspace.ui_fx import IDLE
    st, reg = fxpage.st, fxpage.reg
    line = IDLE["off"][0]
    assert line == "off — nothing below shows until it is on"
    fxpage.panel.fx_selected = "warp"
    fxpage.frame()
    assert line in fxpage.texts and "idle.fx.warp.on" in fxpage.rects
    # the line sits over the strip's "on" row, and the rows under it are veiled
    assert fxpage.rects["idle.fx.warp.on"][3] <= fxpage.rects["fx.warp.on"][1]
    assert len(fxpage.veils) == 2
    others = {n: reg[f"fx.{n}.on"].base for n in st.names() if n != "warp"}
    fxpage.click("idle.fx.warp.on")
    assert reg["fx.warp.on"].base is True and st.values["warp"]["on"] is True
    assert {n: reg[f"fx.{n}.on"].base for n in others} == others
    assert fxpage.panel.fx_selected == "warp" and st.live("warp")
    fxpage.frame()                                   # running: no line, no chip, no veil
    assert line not in fxpage.texts and "idle.fx.warp.on" not in fxpage.rects
    assert not fxpage.veils and not set(fxpage.texts) & {v[0] for v in IDLE.values()}


def test_a_bypassed_stack_says_so_on_the_strip(fxpage):
    from hyperspace.ui_fx import IDLE
    st, reg = fxpage.st, fxpage.reg
    fxpage.panel.fx_selected = "warp"
    reg["fx.warp.on"].set(True)
    reg["fx.on"].set(False)
    fxpage.frame()
    assert "every effect is bypassed" in fxpage.texts
    assert "idle.fx.on" in fxpage.rects and "idle.fx.warp.on" not in fxpage.rects
    fxpage.click("idle.fx.on")
    assert reg["fx.on"].base is True and st.live("warp")
    fxpage.frame()
    assert "every effect is bypassed" not in fxpage.texts and "idle.fx.on" not in fxpage.rects
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
    fxpage.panel.fx_selected = "warp"
    fxpage.frame()
    assert reg["fx.warp.on"].base is False and fxpage.veils
    # (plan 33 U: no order slider, no ONTO chips — an effect's place is its wires)
    rows = ["fx.warp.mix", "fx.warp.speed", "fx.warp.blend",
            *(f"fx.warp.{p.key}" for p in st.specs["warp"].params)]
    for pid in ("fx.warp.on", *rows):                # no begin_disabled wraps a row
        assert fxpage.disabled[pid] == 0, pid
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
    panel.fx_selected = "warp"
    seen = []
    real = ui_fx._relearn_frame
    monkeypatch.setattr(ui_fx, "_relearn_frame",
                        lambda p, rects: (seen.append(dict(rects)), real(p, rects))[1])
    panel.learn = SimpleNamespace(learning="fx.warp.speed", arm=lambda pid: None)
    fxpage.frame()
    assert len(seen) == 1 and fxpage.veils          # idle: after the veil, once
    rows = {"fx.warp.mix", "fx.warp.speed", "fx.warp.blend",      # (plan 33 U: no order)
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
    """No graph loaded (the empty-state line), every effect's strip open in
    turn with an error line, idle for each reason a chip mends: the page
    never scrolls at the control size."""
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
        panel.fx_selected = name
        for reason in ("off", "bypassed"):
            reg[f"fx.{name}.on"].set(reason != "off")
            reg["fx.on"].set(reason != "bypassed")
            assert why_idle(st, name) == reason
            for _ in range(3):
                fxpage.texts.clear()
                imgui.new_frame()
                panel.draw(1 / 60, 60.0)
                imgui.end_frame()
            assert any(t.startswith(("off —", "every effect")) for t in fxpage.texts)
            assert over[-1] == 0, f"the fx page scrolls with {name} open and {reason}"


def test_the_palette_strip_fits_in_both_modes(fxpage, monkeypatch):
    """Plan 24 C6: the palette has 21 params; the strip packs lo/hi and
    hue/sat/val onto one row and shows the open mode's rows only, so the
    page fits in fold and in gradient mode, error line and all."""
    from hyperspace.ui import PAGE_KEYS, Panel
    imgui, reg, panel = fxpage.imgui, fxpage.reg, fxpage.panel
    panel.renderer.fx.error = lambda n: "line 3: made up"
    over = []
    draw = Panel._page_fx

    def measured(self, dt):
        draw(self, dt)
        over.append(imgui.get_scroll_max_y())
    monkeypatch.setattr(Panel, "_page_fx", measured)
    drawn, picked = [], []
    real_slider, real_combo = Panel._slider, Panel._combo
    monkeypatch.setattr(Panel, "_slider", lambda self, pid, *a, **k: (drawn.append(pid),
                                                                       real_slider(self, pid, *a, **k))[1])
    monkeypatch.setattr(Panel, "_combo", lambda self, pid, *a, **k: (picked.append(pid),
                                                                      real_combo(self, pid, *a, **k))[1])
    reg["ui.page"].set(PAGE_KEYS.index("fx"))
    panel.fx_selected = "palette"
    for mode in (0, 1):
        drawn.clear()
        picked.clear()
        reg["fx.palette.mode"].set(mode)
        reg["fx.palette.on"].set(True)
        for _ in range(3):
            imgui.new_frame()
            panel.draw(1 / 60, 60.0)
            imgui.end_frame()
        assert over[-1] == 0, f"the fx page scrolls with the palette in mode {mode}"
        shown = set(drawn)
        assert ("fx.palette.a4_val" in shown) == (mode == 1)      # the last anchor's slider
        assert ("fx.palette.val_to" in shown) == (mode == 0)      # the last slice slider
        # plan 30 N8: the mode is a picker (a combo), never a slider
        assert "fx.palette.mode" in picked and "fx.palette.mode" not in shown


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
        rig.panel.fx_selected = "warp"
        r.reg["fx.on"].set(False)                    # the effects bypassed and warp off,
        r.reg["fx.warp.on"].set(False)               # whatever the startup preset left
        settle(r)
        start = labels(r)
        rig.click("idle.fx.warp.on")                 # "turn on": the first reason's chip
        settle(r)
        assert r.reg["fx.warp.on"].base is True and r.reg["fx.on"].base is False
        assert len(labels(r)) == len(start) + 1 and not pushes
        rig.click("idle.fx.on")                      # now it reads bypassed: "effects on"
        settle(r)
        assert r.reg["fx.on"].base is True and st.live("warp")
        assert len(labels(r)) == len(start) + 2 and not pushes
        for want_stack, want_warp in ((False, True), (False, False)):
            undo.undo()
            frames(r, 3)
            assert r.reg["fx.on"].base is want_stack and r.reg["fx.warp.on"].base is want_warp
        assert labels(r) == start
    finally:
        rig.close()


# ---------------------------------------------------------------- the faces' map (plan 20 WP1)

def test_face_map_is_one_switch_for_every_effect():
    """`fx.face_map`: how a picture wired into the faces sits on them —
    one enum for all of them (fork F4: the mapping is a move, modulatable),
    persisted and watched by undo. Plan 33 T7: no per-effect target with
    it — an effect is on the faces where a wire puts it."""
    from hyperspace import undo
    from hyperspace.fx import FACE_MAPS, PER_FACE, SCREEN
    from hyperspace.params import Kind
    assert FACE_MAPS == ["per face", "screen"] and (PER_FACE, SCREEN) == (0, 1)
    st = FxState()
    r = Registry()
    declare(r, st)
    m = r["fx.face_map"]
    assert m.kind is Kind.ENUM and m.names == FACE_MAPS and m.value == PER_FACE
    assert m.persist and m.modulatable and m.group == "fx" and undo.watched(m)
    assert not [p.id for p in r if p.id.endswith(".target")]
    r["fx.face_map"].set(SCREEN)
    assert st.face_map == SCREEN


def test_advance_to_moves_the_clocks_once_per_frame_time():
    st = FxState()
    st.values["warp"]["speed"] = 2.0
    assert st.advance_to(5.0) == 0.0                         # the first call: no dt yet
    assert st.advance_to(5.1) == pytest.approx(0.1)
    assert st.advance_to(5.1) == 0.0                         # a second node, same frame
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


def test_two_effect_nodes_advance_the_clocks_once(ctx):
    """Two effect nodes run at one frame time (the run's and a branch's,
    `run_one`): every phase is what one alone gives — not double speed."""
    def run(two: bool) -> dict:
        st = FxState()
        for n, speed in (("warp", 2.0), ("plasma", -1.0), ("acid", 0.5)):
            st.values[n].update(on=True, speed=speed)
        chain = FxChain(ctx, st)
        (src, _), (_, dst) = chain.pool((16, 16))
        for k in range(5):
            t = 3.0 + k * 0.1
            chain.run_one("warp", src, dst, t)
            if two:                                   # a second node, the same frame
                chain.run_one("plasma", src, dst, t)
        return dict(st.phase)

    one, two = run(False), run(True)
    assert one["warp"] == pytest.approx(0.8) and one["plasma"] == pytest.approx(-0.4)
    assert two == pytest.approx(one)


def test_a_pass_on_a_see_through_ground_never_forces_alpha(ctx, fxdir):
    """On the faces' picture alpha is a face's intensity: a pass told
    `opaque` 0 (a branch on the faces, a hands' layer) covers its own colour
    and no more, whatever the chain's `opaque`; on an opaque frame it
    writes alpha 1."""
    write(fxdir, "flat", CONST.format(blend="mix"))
    st = FxState(fxdir)
    st.values["flat"].update(on=True, level=0.1)
    chain = FxChain(ctx, st)
    chain.opaque = True
    out = ctx.framebuffer(color_attachments=[ctx.texture((8, 8), 4)])
    (src, src_fbo), _ = chain.pool((8, 8))
    for opaque, want in ((0, 102), (None, 255)):      # covers its 0.4; lifted to 1
        src_fbo.use()
        ctx.clear(0.0, 0.0, 0.0, 0.0)
        chain.run_one("flat", src, out, 0.0, opaque=opaque)
        px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(8, 8, 4)
        assert px[4, 4, 3] == want, opaque


def faces_run(*names):
    """The faces' run as the wiring holds it (plan 33 R): `pattern → names…
    → shape.faces`, the frame's run empty (none said, R23)."""
    from hyperspace import graph as G
    chain = ["pattern", *names]
    wires = [G.Wire(a, f"{b}.image") for a, b in zip(chain, names)]
    return G.Wiring(wires=(*wires, G.Wire(chain[-1], "shape.faces")) if names else ())


def face_frame(ctx, fx: FxState, frames: int = 3, pattern: int = 2, faces: tuple = ()):
    """`render` with the renderer handed back: the frame, the renderer.
    `faces`: the effects of the faces' run (`faces_run`)."""
    from hyperspace.render import Renderer
    from hyperspace.view import ViewState
    fbo = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H))])
    r = Renderer(ctx, fx=fx)
    r.wiring = faces_run(*faces)
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
    """On the faces alone (plan 33 R: wired `pattern → name → shape.faces`),
    every factory effect compiles, the frame draws with no GL error, the
    picture is not the seed, and the frame is not the frame without it. No
    effect is adapted and none is refused."""
    from hyperspace.render import FACE_PIC
    base, r0 = face_frame(ctx, FxState())
    assert r0.face_pic.tex is None
    st = FxState()
    st.values[name].update(on=True)
    if name == "glimmer":
        st.values[name]["density"] = 1.0
    if name == "palette":                  # it starts at mix 0, which reads through
        st.values[name].update(mix=1.0, hue_from=155.0, hue_to=245.0)
    img, r = face_frame(ctx, st, faces=(name,))
    assert ctx.error == "GL_NO_ERROR"
    assert r.face_error == "" and r.fx.errors == {} and r.stats["fx_on"] is False
    pool = r._pools[(FACE_PIC, FACE_PIC)]
    assert r.face_pic.tex.size == (FACE_PIC, FACE_PIC) and not hasattr(r, "face_fx")
    # the faces' first texture still holds the seed (one pass: read, never written)
    seed = np.frombuffer(pool[0][0].read(), dtype=np.float16).astype(np.float32)
    seed = np.clip(seed * 255.0, 0, 255).reshape(FACE_PIC, FACE_PIC, 4)
    pic = np.frombuffer(r.face_pic.tex.read(), dtype=np.uint8).reshape(FACE_PIC, FACE_PIC, 4)
    assert seed[..., 3].max() > 100                          # the pattern is in the seed
    change = np.abs(pic.astype(np.float32) - seed).mean()
    print(f"{name}: picture differs from the seed by {change:.2f} / 255 (mean)")
    assert change > 0.25, f"{name} left the picture as the seed was"
    assert np.abs(img.astype(int) - base).sum() > 200, f"{name} does not show on the faces"


# ---------------------------------------------------------------- the faces on the page

def test_the_map_chips_set_fx_face_map(tmp_path, monkeypatch):
    """The `→ faces` group's header carries `fx.face_map`'s two chips: a
    click writes the base (Param.set), each has a menu of its own, the lit
    one is what the faces show (the effective value), and while a source
    rides it either chip's hover names the source."""
    from hyperspace import ui
    from hyperspace.fx import FACE_MAPS, PER_FACE, SCREEN
    rig = browsing(tmp_path, monkeypatch)
    try:
        imgui, st, reg = rig.imgui, rig.st, rig.reg
        p = reg["fx.face_map"]
        assert p.names == FACE_MAPS == ["per face", "screen"] and p.modulatable and p.persist
        sets = []
        real_set = type(p).set
        monkeypatch.setattr(type(p), "set", lambda self, v: (sets.append((self.id, v)),
                                                             real_set(self, v))[1])
        popups = []
        real_popup = imgui.begin_popup_context_item
        monkeypatch.setattr(imgui, "begin_popup_context_item",
                            lambda label, *a, **k: (popups.append(label),
                                                    real_popup(label, *a, **k))[1])
        for want in (SCREEN, PER_FACE, SCREEN):
            sets.clear()
            rig.click(f"map.fx.face_map.{want}")
            assert sets == [("fx.face_map", want)]
            assert p.base == want and st.face_map == want
        assert {"##ctx.fx.face_map.map0", "##ctx.fx.face_map.map1"} <= set(popups)
        lit = []
        real_lit = ui.lit_chip
        monkeypatch.setattr(ui, "lit_chip", lambda label, on, *a, **k: (
            lit.append((label.split("##", 1)[-1], bool(on))), real_lit(label, on, *a, **k))[1])
        rig.frame()
        assert ("map.fx.face_map.1", True) in lit and ("map.fx.face_map.0", False) in lit
        p.modulate(-1.0)
        reg.apply()
        assert p.base == SCREEN and st.face_map == PER_FACE
        lit.clear()
        rig.frame()
        assert ("map.fx.face_map.0", True) in lit and ("map.fx.face_map.1", False) in lit
        tips = []
        monkeypatch.setattr(imgui, "set_tooltip", lambda t: tips.append(t))
        x0, y0, x1, y1 = rig.rects["map.fx.face_map.1"]
        imgui.get_io().add_mouse_pos_event((x0 + x1) / 2, (y0 + y1) / 2)
        for _ in range(3):
            tips.clear()
            reg.apply()
            p.modulate(-1.0)
            reg.apply()
            rig.frame()
        assert tips and tips[-1].startswith(p.tip + "\n") and "per face" in tips[-1]
    finally:
        rig.close()


def test_faces_on_switches_the_faces_on(tmp_path, monkeypatch):
    """An open effect that is on and ends on the faces while Faces is off
    says so, with the chip that mends it: Param.set on view.faces. One that
    ends elsewhere is not idle for it, and one that reaches nothing says
    that."""
    from hyperspace.ui_fx import IDLE
    rig = browsing(tmp_path, monkeypatch)
    try:
        reg, view = rig.reg, rig.panel.view
        line, chip, pid, _tip = IDLE["faces off"]
        assert (line, chip, pid) == ("it ends on the faces, and Faces is off", "faces on",
                                     "view.faces")
        assert list(IDLE)[:4] == ["off", "reaches nothing", "faces off", "bypassed"]
        reg["view.faces"].set(False)
        rig.panel.fx_selected = "acid.2"
        reg["fx.acid.2.on"].set(False)
        rig.frame()                                  # off: "off" comes first
        assert IDLE["off"][0] in rig.texts and line not in rig.texts
        reg["fx.acid.2.on"].set(True)
        rig.frame()
        assert line in rig.texts and "idle.view.faces" in rig.rects
        assert "idle.fx.acid.2.on" not in rig.rects and len(rig.veils) == 2
        switches = {p.id: p.base for p in reg if p.id.endswith(".on")}
        rig.click("idle.view.faces")
        assert reg["view.faces"].base is True and view.faces is True
        assert {p.id: p.base for p in reg if p.id.endswith(".on")} == switches
        assert rig.panel.fx_selected == "acid.2"
        rig.frame()                                  # running: no line, no chip, no veil
        assert line not in rig.texts and "idle.view.faces" not in rig.rects
        assert not rig.veils
        reg["view.faces"].set(False)                 # one under the scene: not the faces'
        rig.panel.fx_selected = "kaleido.2"
        rig.frame()
        assert line not in rig.texts and not rig.veils
        rig.panel.fx_selected = "wobble.2"           # unreached: said, no chip
        rig.frame()
        assert IDLE["reaches nothing"][0] in rig.texts and len(rig.veils) == 2
        assert not [k for k in rig.rects if k.startswith("idle.")]
    finally:
        rig.close()


def test_the_map_is_one_undo_step(tmp_path, monkeypatch):
    """A map chip writes a base and pushes nothing: undo's watcher makes the
    change one step ("Scene-setters write the base")."""
    from test_undo import frames, labels, settle

    from hyperspace import undo
    from hyperspace.fx import PER_FACE, SCREEN
    pushes = []
    real_push = undo.push
    monkeypatch.setattr(undo, "push", lambda *a, **k: (pushes.append(a), real_push(*a, **k))[1])
    rig = browsing(tmp_path, monkeypatch)
    try:
        r = rig.app
        r.reg["fx.face_map"].set(PER_FACE)
        settle(r)
        start = labels(r)
        pushes.clear()
        rig.click(f"map.fx.face_map.{SCREEN}")
        settle(r)
        assert r.reg["fx.face_map"].base == SCREEN
        assert len(labels(r)) == len(start) + 1 and not pushes
        undo.undo()
        frames(r, 3)
        assert r.reg["fx.face_map"].base == PER_FACE and labels(r) == start
    finally:
        rig.close()


def test_the_strip_says_where_its_effect_ends_wherever_it_is_drawn(tmp_path, monkeypatch):
    """`ui_fx.strip` — the FX page's open strip and the GRAPH page's side
    column for a selected effect node — reads the graph itself, so its title
    note says where the effect's paths end (`acid.glsl · → output 2 · →
    blend aux`) however the strip is reached; a D1 placement says its place
    (`→ after hands`)."""
    from hyperspace import graph as G
    from hyperspace import ui_fx
    rig = browsing(tmp_path, monkeypatch)
    try:
        imgui, panel = rig.imgui, rig.panel
        seen = []
        real = ui_fx._strip_header

        def header(panel_, fx, name, place=None):
            seen.append((name, place))
            return real(panel_, fx, name, place)
        monkeypatch.setattr(ui_fx, "_strip_header", header)

        def side(name):                     # what ui_graph's side column does
            imgui.new_frame()
            imgui.begin("side")
            ui_fx.strip(panel, name)
            imgui.end()
            imgui.end_frame()
        side("acid.3")
        side("zoomblur")                    # in no group of this graph
        assert seen[-2:] == [("acid.3", "→ output 2 · → blend aux"), ("zoomblur", None)]
        panel.fx_selected = "acid.3"
        rig.frame()
        assert seen[-1] == ("acid.3", "→ output 2 · → blend aux")
        panel.graph_now = lambda: (G.Wiring(), G.read_graph(
            {"nodes": [{"kind": "effect", "file": "warp", "after": "hands"}]}))
        side("warp")
        assert seen[-1] == ("warp", "→ after hands")
    finally:
        rig.close()


# ---------------------------------------------------------------- plan 33 T7: the FX page browses the graph

# a run of two, a branch onto the faces, one under the scene, one behind a
# switch into the pattern's layer, one unreached, and one read in two places
BROWSED = {
    "nodes": [{"kind": "effect", "file": f, "instance": n}
              for f, n in (("acid", 2), ("acid", 3), ("kaleido", 2), ("wobble", 2),
                           ("glimmer", 2))] + [{"kind": "switch"}],
    "wires": [{"from": a, "to": b} for a, b in (
        ("frame", "warp.image"), ("warp", "blend.image"), ("blend", "fx.image"),
        ("media.a", "acid.2.image"), ("acid.2", "shape.faces"),
        ("kaleido.2", "backdrop.image"),
        ("glimmer.2", "switch.in1"), ("switch", "pattern.media"),
        ("acid.3", "output.2.image"), ("acid.3", "blend.aux"))],
}
BROWSED_GROUPS = [
    ("Run", ["warp", "blend"]),
    ("→ faces", ["acid.2"]),
    ("→ pattern media", ["glimmer.2"]),
    ("→ backdrop", ["kaleido.2"]),
    ("→ output 2", ["acid.3"]),
    ("→ blend aux", ["acid.3"]),
    ("reaches nothing", ["wobble.2"]),
]
EMPTY_GRAPH = "no effects in the graph — add one on GRAPH (right-click the canvas)"


def test_groups_follow_the_wires():
    """`ui_fx.groups`: every effect of the loaded graph by where its path
    ends — the run in wire order, then the faces, the pattern's layer, the
    backdrop, each output, each effect's aux, and the unreached last; one
    behind a switch by the switch's destination; one read in two places in
    each; within a group from the head to the sink."""
    from hyperspace import graph as G
    from hyperspace.ui_fx import groups
    assert groups(G.read_graph(BROWSED)) == BROWSED_GROUPS
    # within a group, the path from its head: acid.2 before huecycle.2
    chain = G.read_graph({
        "nodes": [{"kind": "effect", "file": "acid", "instance": 2},
                  {"kind": "effect", "file": "huecycle", "instance": 2}],
        "wires": [{"from": a, "to": b} for a, b in (
            ("frame", "fx.image"), ("media.a", "acid.2.image"),
            ("acid.2", "huecycle.2.image"), ("huecycle.2", "shape.faces"))]})
    assert groups(chain) == [("→ faces", ["acid.2", "huecycle.2"])]
    assert groups(G.read_graph({"wires": [{"from": "frame", "to": "fx.image"}]})) == []


def browsing(tmp_path, monkeypatch, section=BROWSED):
    """The FX page over the app's construction (test_undo.boot) with
    `section` loaded as a `/5` preset — every effect of it on."""
    from test_undo import boot
    st = FxState()
    r = boot(tmp_path / "home", fx=st)
    r.fx = st
    rig = PageRig(tmp_path, monkeypatch, r)
    rig.app = r
    names = {n for _, ns in BROWSED_GROUPS for n in ns} if section is BROWSED else set()
    doc = {"schema": "hyperspace.preset/5", "name": "browse", "graph": section,
           "values": {f"fx.{n}.on": True for n in sorted(names)}}
    r.presets.load_doc(doc)
    assert not [n for n in r.presets.notes if "graph" in n or "unknown" in n], r.presets.notes
    return rig


def test_the_fx_page_lists_the_graphs_effects(tmp_path, monkeypatch):
    """The panel harness: every name `groups` gives is drawn once per group
    it is in (a row's name is a chip, `row.<group>.<name>`), and a click on
    acid.2's opens its strip — `Panel.fx_selected`, the one selection GRAPH
    shares — with nothing switched."""
    rig = browsing(tmp_path, monkeypatch)
    try:
        rig.frame()
        rows = [k for k in rig.rects if k.startswith("row.")]
        want = [f"row.{title}.{n}" for title, names in BROWSED_GROUPS for n in names]
        assert sorted(rows) == sorted(want) and len(rows) == len(set(rows))
        assert rig.panel.fx_selected is None and "fx.acid.2.speed" not in rig.rects
        before = {p.id: p.base for p in rig.reg if p.id.startswith("fx.")}
        rig.click("row.→ faces.acid.2")
        assert rig.panel.fx_selected == "acid.2"
        rig.frame()
        assert "fx.acid.2.speed" in rig.rects and "fx.acid.2.blend" in rig.rects
        assert {p.id: p.base for p in rig.reg if p.id.startswith("fx.")} == before
        # each row: its on, a small mix and its state in a word
        # (a row's mix is the panel's own slider, on the row's line)
        assert "on.→ faces.acid.2" in rig.rects and "on.→ blend aux.acid.3" in rig.rects
        on, mix = rig.rects["on.Run.warp"], rig.rects["fx.warp.mix"]
        assert mix[0] >= on[2] and mix[1] == pytest.approx(on[1])
        assert {"running", "reaches nothing"} <= set(rig.texts)
    finally:
        rig.close()


def test_show_on_graph_selects_the_node(tmp_path, monkeypatch):
    """**Show on GRAPH** at the strip's head: `ui_graph.select_effect` — the
    GRAPH page's selection, drawn next, is `render:acid.2`. On the shell's
    rig (tests/test_ui_shell.py: the real Panel, its pages and the node
    editor), its renderer a stand-in holding the live FxState."""
    from test_graphview import views
    from test_ui_shell import frame

    from hyperspace import graph as G
    from hyperspace import ui, ui_graph
    from hyperspace.outputs import Switches
    with shell(tmp_path) as (rig, st, stand_in):
        doc = {"schema": "hyperspace.preset/5", "name": "browse", "graph": BROWSED,
               "values": {"fx.acid.2.on": True}}
        rig.lib.presets.load_doc(doc)
        wiring = rig.lib.presets.graph.wiring
        stand_in.wiring = wiring
        stand_in._graph = G.build_graph(views(Switches(), Switches()), wiring,   # (plan 35)
                                          effects=tuple(sorted(st.specs)))
        rig.panel.fx_selected = "acid.2"
        real = ui.chip
        drawn = []

        def chip(label, size=None):                 # a click on the button alone
            drawn.append(label)
            return label.endswith("##fx.show") or real(label, size)
        monkeypatch.setattr(ui, "chip", chip)
        frame(rig.panel, "fx")
        assert f"{ui_fx_show()}##fx.show" in drawn
        assert ui_graph._state(rig.panel).get("select") == "acid.2"
        monkeypatch.setattr(ui, "chip", real)
        for _ in range(4):
            frame(rig.panel, "graph")
        gst = ui_graph._state(rig.panel)
        sel = ui_graph._selection(gst, gst["view"])
        assert sel is not None and sel[1].id == "render:acid.2"
        assert rig.panel.fx_selected == "acid.2"


def ui_fx_show() -> str:
    from hyperspace.ui_fx import SHOW
    assert SHOW == "Show on GRAPH"
    return SHOW


def test_an_empty_graph_says_where_to_add(tmp_path, monkeypatch):
    rig = browsing(tmp_path, monkeypatch, {"wires": [{"from": "frame", "to": "fx.image"}]})
    try:
        rig.frame()
        assert EMPTY_GRAPH in rig.plain
        assert not [k for k in rig.rects if k.startswith("row.")]
    finally:
        rig.close()


def test_the_retired_ids_are_gone():
    """Plan 33 row 341: no `order`, no `target`, no `fx.select`, no
    `view.media` and no `backdrop.channel` — unknown ids like any other."""
    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState
    chain = Analyzer(Analyser())
    st = FxState()
    r = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), fx=st)
    for pid in ("fx.acid.order", "fx.acid.target", "fx.select", "view.media",
                "backdrop.channel", "backdrop.history"):     # (plan 35 T3: the capture wire)
        assert r.get(pid) is None and pid not in r, pid
        with pytest.raises(KeyError):
            r[pid]
    for pid in ("fx.on", "fx.mix", "fx.face_map", "fx.acid.on", "fx.acid.mix",
                "fx.acid.speed", "fx.acid.blend", "view.media_alpha", "backdrop.alpha"):
        assert pid in r, pid
    assert set(st.values["acid"]) >= {"on", "mix", "speed", "blend"}
    assert not {"order", "target"} & set(st.values["acid"])
    assert st.names() == sorted(st.specs)                       # by name: no stack order


def test_an_effect_file_with_an_order_line_still_parses():
    """Every factory file keeps its `// @order` line (plan 33 T8 rewrites the
    header comment): `parse` accepts it, and it is what an old preset's
    absent order means (`graphmigrate`), nothing else."""
    s = parse("test", EFFECT)
    assert s.order == 12 and s.label == "Test"
    st = FxState()
    assert all("@order" in (FX_DIR / f"{st.file_of(n)}.glsl").read_text() for n in st.specs)
    assert st.errors == {}


def test_an_old_preset_loads_its_retired_ids_without_a_note(tmp_path):
    """A `/4` file with every `fx.<n>.order` / `.target`, `view.media` and
    `backdrop.channel` loads with no unknown-id note, and its wires are
    what the migration made of them before this task: the frame run by
    order, a faces-aimed effect onto `shape.faces`, the channels straight
    into `pattern.media` and `backdrop.image`."""
    from test_plan31_wiring import make_app

    from hyperspace import graph as G
    app = make_app(tmp_path)
    st = app.presets.graph.fx
    values = {"view.media": 2, "backdrop.channel": 1}
    for k, n in enumerate(sorted(st.specs)):
        values[f"fx.{n}.order"] = 90 - k
        values[f"fx.{n}.target"] = 0
    values.update({"fx.warp.on": True, "fx.acid.on": True, "fx.kaleido.on": True,
                   "fx.kaleido.target": 1})
    doc = {"schema": "hyperspace.preset/4", "name": "old", "values": values}
    assert app.presets.load_doc(doc) == []
    assert not [n for n in app.presets.notes if "unknown" in n], app.presets.notes
    spec = app.presets.graph.spec
    # (plan 35 T3: a wired frame — the run from the look-back into All
    # outputs, the channels in the new ids)
    assert G.run_of(spec, "lookback", "output.all.image") == ("warp", "acid")   # warp's lower
    assert G.run_of(spec, "pattern", "shape.faces") == ("kaleido",)
    assert G.Wire("channel.b", "pattern.media") in spec.wires
    assert G.Wire("channel.a", "backdrop.image") in spec.wires


def test_the_channel_choices_are_read_off_the_wires():
    """Plan 33 T7: what `view.media` and `backdrop.channel` said is the
    section's wire into `pattern.media` / `backdrop.image` — straight, or
    through a switch at its pick (`graph.channel_into`): the MEDIA page's
    words and tags, the FACES page's tiles, learn's "no media channel"."""
    from hyperspace import graph as G
    from hyperspace import learn, ui_media
    spec = G.read_graph({
        "nodes": [{"kind": "switch"}, {"kind": "effect", "file": "acid", "instance": 2}],
        "wires": [{"from": a, "to": b} for a, b in (
            ("frame", "fx.image"), ("media.b", "switch.in1"), ("media.c", "switch.in2"),
            ("switch", "pattern.media"), ("media.a", "acid.2.image"),
            ("acid.2", "backdrop.image"))]})
    wires = spec.all_wires()
    assert G.channel_into(wires, "pattern.media", {"switch": 2}) == "c"
    assert G.channel_into(wires, "pattern.media", {"switch": 1}) == "b"
    assert G.channel_into(wires, "pattern.media", {}) is None           # the switch off
    assert G.channel_into(wires, "backdrop.image") is None              # a branch, no channel
    assert G.source_into(wires, "backdrop.image") == "acid.2"
    # learn: the faces' media knobs are dead with nothing on the layer
    assert learn.faces_media(spec, {"switch": 2}) is True
    assert learn.faces_media(spec, {}) is False and learn.faces_media(None) is None
    assert learn.cannot_show("view.media_alpha", {"view.faces": True}, False) == (
        "no media channel")
    assert learn.cannot_show("view.media_alpha", {"view.faces": True}, True) is None
    assert learn.cannot_show("view.media_alpha", {"view.faces": True}) is None
    # the MEDIA page's words, from the loaded graph and the view's picks
    panel = SimpleNamespace(graph_now=lambda: (G.Wiring(), spec),
                            view=SimpleNamespace(switch={"switch": 2}))
    assert ui_media.feed_words(panel, "pattern.media") == "channel C (switch)"
    assert ui_media.feed_words(panel, "backdrop.image") == "acid.2"
    assert ui_media._channel_of(panel, "pattern.media") == "c"
    panel.view.switch = {}
    assert ui_media.feed_words(panel, "pattern.media") == "off (switch)"
    none = SimpleNamespace(graph_now=lambda: (G.Wiring(), None), view=None)
    assert ui_media.feed_words(none, "backdrop.image") == "nothing wired"


def test_the_media_page_reads_a_wired_frames_channels():
    """Plan 35 T5 review: on a wired frame (every load's) the MEDIA page
    reads `channel.<c>` — the strip's "the backdrop" / "on the faces" marks
    (`_channel_of`) and the pickers' words (`feed_words`) — straight and
    through a switch."""
    from hyperspace import graph as G
    from hyperspace import ui_media
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "switch"}], "wires": [
        {"from": "channel.a", "to": "backdrop.image"}, {"from": "scene", "to": "backdrop.scene"},
        {"from": "shape", "to": "scene.geometry"}, {"from": "backdrop", "to": "output.all.image"},
        {"from": "channel.c", "to": "switch.in2"}, {"from": "switch", "to": "pattern.media"}]})
    assert not spec.notes
    panel = SimpleNamespace(graph_now=lambda: (spec.wiring(), spec),
                            view=SimpleNamespace(switch={"switch": 2}))
    assert ui_media.feed_words(panel, "backdrop.image") == "channel A"
    assert ui_media._channel_of(panel, "backdrop.image") == "a"
    assert ui_media.feed_words(panel, "pattern.media") == "channel C (switch)"
    assert ui_media._channel_of(panel, "pattern.media") == "c"


def test_an_old_preset_saves_no_retired_id(tmp_path):
    """Row 394: a `/4` preset's retired ids (an effect's order and target,
    `view.media`) are read as wires on load and never written back — the
    save is `/6`, the run and the channel the wired frame's; a run
    reordered on GRAPH saves as the wires it now is."""
    from test_plan31_wiring import make_app

    from hyperspace import graph as G
    from hyperspace import graphmigrate as M
    app = make_app(tmp_path)
    values = {"fx.warp.on": True, "fx.acid.on": True, "fx.acid.order": 30,
              "view.media": 2, "media.a.slot": 0}
    doc = {"schema": "hyperspace.preset/4", "name": "old", "values": values,
           "media": {"channels": {"b": ["shared:x.png"]}}}
    assert app.presets.load_doc(doc) == []
    out = app.presets.document("old")
    assert out["schema"] == "hyperspace.preset/6"
    assert not [k for k in out["values"] if M.retired(k)]
    run = G.run_of(G.read_graph(out["graph"]), "lookback", "output.all.image")
    assert run == ("warp", "acid")                     # warp (@order 20) before acid (30)
    assert G.Wire("channel.b", "pattern.media") in G.read_graph(out["graph"]).all_wires()
    # reorder on GRAPH to acid first (the wired frame's run, rewired where it stands)
    sec = app.presets.graph.free_doc()
    rerun = [{"from": "lookback", "to": "acid.image"}, {"from": "acid", "to": "warp.image"},
             {"from": "warp", "to": "output.all.image"}]
    old = [w for w in sec["wires"] if w["from"] in ("lookback", "acid", "warp")
           and w["to"] != "pattern.media"]
    at = sec["wires"].index(old[0])
    keep = [w for w in sec["wires"] if w not in old]
    sec = {**sec, "wires": [*keep[:at], *rerun, *keep[at:]]}
    app.presets.graph.land(G.read_graph(sec), sec)
    out = app.presets.document("old")
    assert out["schema"] == "hyperspace.preset/6"
    assert G.run_of(G.read_graph(out["graph"]), "lookback", "output.all.image") == (
        "acid", "warp")
    assert not [k for k in out["values"] if M.retired(k)]
