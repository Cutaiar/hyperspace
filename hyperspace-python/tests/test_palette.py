"""Plan 30 N8: the palette as a colour compression (the owner, 2026-10-20).

Mode 0 maps the whole HSV cylinder onto a closed slice of it — a hue arc
``hue_from → hue_to`` (up the wheel, through 360 when to < from), a
saturation range ``sat_from → sat_to`` and a brightness range
``val_from → val_to`` — a map, never a clamp: every input colour lands
inside the slice. The defaults are the whole cylinder, so an on palette
at mix 1 leaves the picture as it was. Here a synthetic rainbow (every hue
across, saturation and brightness down) is run through the real shader,
headless, and the output's colours are checked against the slice; then
the old ``centre``/``width`` (and ``sat_lo``/``_hi``, ``val_lo``/``_hi``)
documents are read in the new form, and the strip draws the mode as a
picker and the slice as from → to rows.
"""

import colorsys
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from test_presets import boot, put

from hyperspace import ui_fx
from hyperspace.fx import FX_DIR, FxChain, FxState, SpecError, palette_slice, parse
from hyperspace.library import PRESETS
from hyperspace.params import Kind

moderngl = pytest.importorskip("moderngl")
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "presets"
W, H = 180, 48          # every 2° of hue across; saturation and brightness down


@pytest.fixture(scope="module")
def ctx():
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def rainbow() -> np.ndarray:
    """(H, W, 3) floats: hue across (0 → 358°), saturation 0 → 1 over the
    top half's rows, brightness 0 → 1 over the bottom half's (the other at 1)."""
    img = np.zeros((H, W, 3))
    half = H // 2
    for y in range(H):
        s = y / (half - 1) if y < half else 1.0
        v = 1.0 if y < half else (y - half) / (H - half - 1)
        for x in range(W):
            img[y, x] = colorsys.hsv_to_rgb(x / W, s, v)
    return img


def run(ctx, **vals) -> tuple[np.ndarray, np.ndarray]:
    """The rainbow through the palette alone (on, mix 1, `vals`): (in, out), floats."""
    st = FxState()
    st.values["palette"].update(on=True, mix=1.0, **vals)
    chain = FxChain(ctx, st)
    src = rainbow()
    rgba = np.concatenate([src, np.ones((H, W, 1))], axis=2)
    tex = ctx.texture((W, H), 4, (rgba * 255 + 0.5).astype(np.uint8).tobytes())
    out = ctx.texture((W, H), 4)
    fbo = ctx.framebuffer(color_attachments=[out])
    ctx.viewport = (0, 0, W, H)
    chain.run_one("palette", tex, fbo, 0.0)
    assert ctx.error == "GL_NO_ERROR" and chain.error("palette") in ("", None)
    px = np.frombuffer(fbo.read(components=4), dtype=np.uint8).reshape(H, W, 4)
    got = px[..., :3].astype(float) / 255.0
    inp = np.frombuffer(tex.read(), dtype=np.uint8).reshape(H, W, 4)[..., :3] / 255.0
    for o in (fbo, out, tex):
        o.release()
    chain.release()
    return inp, got


def hsv(img: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hue (degrees), saturation, value of every pixel."""
    flat = img.reshape(-1, 3)
    h, s, v = np.array([colorsys.rgb_to_hsv(*p) for p in flat]).T
    return h * 360.0, s, v


def in_arc(h: np.ndarray, lo: float, hi: float, tol: float) -> np.ndarray:
    """Whether each hue sits on the arc lo → hi (up the wheel), within tol degrees."""
    arc = (hi - lo) % 360.0
    return ((h - lo + tol) % 360.0) <= arc + 2 * tol


# ---------------------------------------------------------------- the transform


def test_the_defaults_are_the_whole_cylinder_and_the_identity(ctx):
    v = FxState().values["palette"]
    assert v["on"] is False and v["mix"] == 0.0           # off, and mix 0, as before
    assert (v["mode"], v["hue_from"], v["hue_to"], v["sat_from"], v["sat_to"],
            v["val_from"], v["val_to"]) == (0, 0.0, 360.0, 0.0, 1.0, 0.0, 1.0)
    inp, got = run(ctx)                                   # on, mix 1, the defaults
    assert np.abs(got - inp).max() <= 1.5 / 255           # the picture as it was


def test_a_red_slice_gives_only_reds(ctx):
    """The owner's "the entire image all shades of a particular red"."""
    _, got = run(ctx, hue_from=350.0, hue_to=10.0, sat_from=0.6, sat_to=1.0,
                 val_from=0.3, val_to=1.0)
    h, s, v = hsv(got)
    assert in_arc(h, 350.0, 10.0, 1.5).all(), h[~in_arc(h, 350.0, 10.0, 1.5)][:5]
    assert s.min() >= 0.6 - 0.02 and v.min() >= 0.3 - 0.01 and v.max() <= 1.0
    # a map, not a clamp: the whole range is used, from end to end
    assert s.max() >= 0.98 and v.min() <= 0.31


def test_a_yellow_slice_spans_its_arc(ctx):
    """"Shades of yellow and derivations on yellow for a given angular
    slice": every hue on the arc, and the arc covered end to end — the
    fold lands red on `from` and cyan on `to`, every hue between them."""
    _, got = run(ctx, hue_from=45.0, hue_to=75.0, sat_from=0.4, sat_to=1.0,
                 val_from=0.5, val_to=1.0)
    h, s, v = hsv(got)
    lit = s > 0.45                                        # the saturated part of the rainbow
    assert in_arc(h, 45.0, 75.0, 1.5).all()
    assert h[lit].min() <= 47.0 and h[lit].max() >= 73.0
    assert s.min() >= 0.38 and v.min() >= 0.49


def test_a_slice_through_red_wraps(ctx):
    """from > to: the arc runs up from `from` through 360 to `to`."""
    _, got = run(ctx, hue_from=300.0, hue_to=60.0, sat_from=1.0, sat_to=1.0,
                 val_from=1.0, val_to=1.0)
    h, _, _ = hsv(got)
    assert in_arc(h, 300.0, 60.0, 1.5).all()
    assert (h > 180.0).any() and (h < 180.0).any()          # both sides of red
    assert not ((h > 62.0) & (h < 298.0)).any()             # nothing on the far side


def test_one_hue_and_a_wide_slice(ctx):
    _, got = run(ctx, hue_from=200.0, hue_to=200.0, sat_from=1.0, sat_to=1.0,
                 val_from=1.0, val_to=1.0)
    h, _, _ = hsv(got)
    assert np.abs(h - 200.0).max() < 1.5                   # from == to is one hue
    # wider than the old fold reached: still only the arc, red on `from`
    _, got = run(ctx, hue_from=0.0, hue_to=270.0, sat_from=1.0, sat_to=1.0,
                 val_from=1.0, val_to=1.0)
    h, _, _ = hsv(got)
    assert in_arc(h, 0.0, 270.0, 1.5).all() and h.max() >= 250.0


def test_an_inverted_val_range_turns_dark_to_bright(ctx):
    inp, got = run(ctx, val_from=1.0, val_to=0.2)
    _, _, vi = hsv(inp)
    _, _, vo = hsv(got)
    assert vo.min() >= 0.2 - 0.01 and vo.max() <= 1.0
    assert np.corrcoef(vi, vo)[0, 1] < -0.99               # the darkest is now the brightest
    black = vi < 0.01
    assert black.any() and vo[black].min() >= 0.99


def test_the_gradient_mode_is_still_there(ctx):
    inp, got = run(ctx, mode=1)                            # the grey ramp: a greyscale
    assert np.abs(got[..., 0] - got[..., 1]).max() <= 1.5 / 255
    assert np.abs(got - inp).sum() > 1.0


# ---------------------------------------------------------------- the picker


def test_mode_is_a_discrete_choice():
    spec = FxState().specs["palette"]
    mode = next(p for p in spec.params if p.key == "mode")
    assert mode.choices == ("compress", "gradient") and mode.integer and mode.default == 0
    from types import SimpleNamespace

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    from hyperspace.params import build_registry
    from hyperspace.view import ViewState
    chain = Analyzer(Analyser())
    reg = build_registry(ViewState(), Control(chain), SimpleNamespace(chain=chain), fx=FxState())
    p = reg["fx.palette.mode"]
    assert p.kind is Kind.ENUM and p.names == ["compress", "gradient"]
    assert p.text() == "compress"
    p.set(1)
    assert p.text() == "gradient" and reg.fx_state.values["palette"]["mode"] == 1
    # a continuous param stays a slider's
    assert reg["fx.palette.hue_to"].kind is Kind.CONTINUOUS


def test_the_choice_form_is_parsed_and_refused_when_bad():
    body = "vec4 effect(vec2 uv) { return src(uv); }\n"
    ok = parse("e", 'uniform int u_way; // @param choice [a|b c|d] 2 "Way" which way\n' + body)
    (p,) = ok.params
    assert (p.choices, p.default, p.lo, p.hi, p.label, p.tip) == (
        ("a", "b c", "d"), 2.0, 0.0, 2.0, "Way", "which way")
    for bad, why in [
        ('uniform float u_way; // @param choice [a|b] 0 "Way"\n', "int"),
        ('uniform int u_way; // @param choice [a] 0 "Way"\n', "two or more"),
        ('uniform int u_way; // @param choice [a|a] 0 "Way"\n', "two or more"),
        ('uniform int u_way; // @param choice a|b 0 "Way"\n', "choice wants"),
        ('uniform int u_on; // @param choice [a|b] 0 "On"\n', "taken"),
    ]:
        with pytest.raises(SpecError, match=why):
            parse("e", bad + body)
    # the signature carries the names: a renamed choice re-declares
    other = parse("e", 'uniform int u_way; // @param choice [a|x|d] 2 "Way" which way\n' + body)
    assert other.signature() != ok.signature()


# ---------------------------------------------------------------- the strip


def test_the_strip_rows_are_the_slice():
    keys = [p.key for p in FxState().specs["palette"].params]
    assert ui_fx.strip_rows("palette", keys, 0) == [
        ("mode", ["mode"]), ("hue", ["hue_from", "hue_to"]),
        ("sat", ["sat_from", "sat_to"]), ("val", ["val_from", "val_to"])]
    assert ui_fx.strip_rows("palette.2", keys, 1) == [
        ("mode", ["mode"]), ("anchors", ["anchors"]), ("a1", ["a1_hue", "a1_sat", "a1_val"]),
        ("a2", ["a2_hue", "a2_sat", "a2_val"]), ("a3", ["a3_hue", "a3_sat", "a3_val"]),
        ("a4", ["a4_hue", "a4_sat", "a4_val"])]
    v = dict(FxState().values["palette"], hue_from=170.0, hue_to=230.0, val_from=0.25)
    assert ui_fx.compress_line(v) == ("compress into: hue 170° → 230° · sat 0.00 → 1.00 · "
                                      "val 0.25 → 1.00")
    assert ui_fx.slice_arc(350.0, 10.0) == 20.0 and ui_fx.slice_arc(0.0, 360.0) == 360.0
    assert ui_fx.slice_arc(200.0, 200.0) == 0.0


# ---------------------------------------------------------------- the old documents


def test_centre_and_width_become_the_slice_s_ends():
    doc = {"values": {"fx.palette.centre": 200.0, "fx.palette.width": 60.0,
                      "fx.palette.sat_lo": 0.2, "fx.palette.val_hi": 0.9,
                      "fx.palette.2.centre": 10.0, "fx.palette.2.width": 40.0,
                      "fx.palette.3.width": 360.0, "fx.acid.mix": 1.0},
           "routes": [{"source": "lane:0", "target": "fx.palette.centre", "op": "push",
                       "value": 0.2},
                      {"source": "lane:1", "target": "fx.palette.width", "op": "push",
                       "value": 0.4, "scale": "master.gain"},
                      {"source": "lane:2", "target": "fx.palette.sat_hi", "op": "push",
                       "value": 0.3},
                      {"source": "lane:3", "target": "fx.acid.bend", "op": "push",
                       "value": 0.3}]}
    out, notes = palette_slice(doc)
    assert out is not doc and "fx.palette.centre" in doc["values"]     # a copy
    assert out["values"] == {
        "fx.palette.hue_from": 170.0, "fx.palette.hue_to": 230.0,
        "fx.palette.sat_from": 0.2, "fx.palette.val_to": 0.9,
        "fx.palette.2.hue_from": 350.0, "fx.palette.2.hue_to": 30.0,
        "fx.palette.3.hue_from": 0.0, "fx.palette.3.hue_to": 360.0, "fx.acid.mix": 1.0}
    assert [(r["target"], r["value"]) for r in out["routes"]] == [
        ("fx.palette.hue_from", 0.2), ("fx.palette.hue_to", 0.2),      # the slice turns
        ("fx.palette.hue_from", -0.2), ("fx.palette.hue_to", 0.2),     # it widens
        ("fx.palette.sat_to", 0.3), ("fx.acid.bend", 0.3)]
    assert out["routes"][3]["scale"] == "master.gain"
    # a fold wider than the slice reproduces is said; the rest is silent
    assert notes == [("fx.palette.3: a fold 360° wide reads as a wider slice now "
                      "(the old fold only to 180°)")]
    # a document already in the new form is the document itself
    new = {"values": {"fx.palette.hue_from": 1.0}, "routes": []}
    assert palette_slice(new) == (new, [])
    assert palette_slice(new)[0] is new
    # an id in the new form wins over the old one beside it
    both, _ = palette_slice({"values": {"fx.palette.centre": 100.0, "fx.palette.hue_to": 5.0}})
    assert both["values"] == {"fx.palette.hue_from": 0.0, "fx.palette.hue_to": 5.0}


def test_an_old_preset_loads_as_the_same_slice(tmp_path):
    """A preset saved with centre 200 / width 60 loads with no note, its
    palette at 170 → 230 and its route on the slice; the next save writes
    the new keys only."""
    rig = boot(tmp_path)
    put(rig.home, "old-fold", values={"fx.palette.on": True, "fx.palette.mix": 1.0,
                                      "fx.palette.centre": 200.0, "fx.palette.width": 60.0,
                                      "fx.palette.sat_lo": 0.25},
        routes=[{"source": "lane:0", "target": "fx.palette.centre", "op": "push",
                 "value": 0.1}])
    assert rig.lib.load(PRESETS, "old-fold") == [] and rig.presets.notes == []
    v = rig.reg.fx_state.values["palette"]
    assert (v["on"], v["hue_from"], v["hue_to"], v["sat_from"]) == (True, 170.0, 230.0, 0.25)
    assert sorted(b.target for b in rig.router.table.routes()
                  if b.target.startswith("fx.palette")) == ["fx.palette.hue_from",
                                                            "fx.palette.hue_to"]
    saved = rig.presets.document("old-fold")
    assert saved["values"]["fx.palette.hue_from"] == 170.0
    assert not any(k.endswith((".centre", ".width", "_lo", "_hi")) for k in saved["values"]
                   if k.startswith("fx.palette"))


def test_an_old_fx_module_preset_is_read_as_the_slice(tmp_path):
    rig = boot(tmp_path)
    (rig.home / "fx").mkdir(parents=True, exist_ok=True)
    (rig.home / "fx" / "teal.json").write_text(json.dumps({
        "schema": "hyperspace.preset/1", "group": "fx", "name": "teal",
        "values": {"fx.palette.on": True, "fx.palette.mix": 1.0,
                   "fx.palette.centre": 180.0, "fx.palette.width": 20.0}}))
    assert rig.lib.load("fx", "teal") == []
    v = rig.reg.fx_state.values["palette"]
    assert (v["hue_from"], v["hue_to"]) == (170.0, 190.0)


@pytest.mark.parametrize("slug", ["palette-hands", "palette-glass", "wired-outputs"])
def test_the_fixtures_carry_the_slice(slug):
    doc = json.loads((FIXTURES / f"{slug}.json").read_text())
    assert doc["values"]["fx.palette.hue_from"] == 170.0
    assert doc["values"]["fx.palette.hue_to"] == 230.0
    assert palette_slice(doc) == (doc, [])                 # nothing left to convert


def test_no_factory_file_names_the_palette():
    """The base goldens cannot move: no factory preset turns the palette on."""
    lib = FX_DIR.parent.parent / "library"
    hits = [p for p in lib.rglob("*.json") if "fx.palette" in p.read_text()]
    assert hits == []


def test_the_shader_file_is_the_one_parsed(tmp_path):
    """The live file parses with no error (the choice form included)."""
    d = tmp_path / "fx"
    shutil.copytree(FX_DIR, d)
    st = FxState(d)
    assert st.errors == {} and "palette" in st.specs
