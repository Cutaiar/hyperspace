"""Plan 82, control widgets: the faders' shapes (unipolar, bipolar, unity,
stepped ticks) and the XY pad / XYZ volume an effect file declares with
`@pair` / `@volume` — parsed, drawn on the fx strip, and driven by the
mouse through tests/ui_driver.py."""

from __future__ import annotations

from contextlib import contextmanager
from itertools import pairwise
from types import SimpleNamespace

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import fx, ui, ui_fields
from hyperspace.fx import FxState, SpecError, parse
from hyperspace.lookback import DreamState
from hyperspace.ui_fields import BIPOLAR, UNIPOLAR, UNITY, polarity, shape_of, ticks

HEAD = "vec4 effect(vec2 uv) { return src(uv); }\n"


@contextmanager
def strip(tmp_path, monkeypatch, sel: str, fx_dir=None):
    """The real panel over a live FxState (the shipped effects, or
    `fx_dir`'s), effect `sel`'s strip open in the fx section, a Driver
    recording every control."""
    st = FxState() if fx_dir is None else FxState(fx_dir)
    stand_in = SimpleNamespace(fx=SimpleNamespace(state=st, error=lambda n: ""),
                               lookback=SimpleNamespace(state=DreamState()))
    with build_rig(tmp_path, renderer=stand_in) as r:
        r.panel.desk = False
        st.set_instances({})                # every file, once: the effect's params declared
        fx.declare(r.reg, st)
        imgui.get_io().display_size = imgui.ImVec2(1600, 2400)
        r.panel.fx_selected = sel
        d = Driver(step=lambda: frame(r.panel, "fx"))
        d.record(monkeypatch.setattr)
        d.run(d.wait(3))
        yield r, d, st


# ---- the parse ----

def test_pair_and_volume_lines_name_the_files_own_params():
    spec = parse("t", '// @pair u_a u_b "Centre"\n// @volume u_c u_d u_e "Burst"\n'
                 'uniform float u_a; // @param -1 1 0 "A"\n'
                 'uniform float u_b; // @param -1 1 0 "B"\n'
                 'uniform float u_c; // @param 0 1 0 "C"\n'
                 'uniform float u_d; // @param 0 1 0 "D"\n'
                 'uniform float u_e; // @param 0 1 0 amount "E"\n' + HEAD)
    assert [(p.keys, p.label) for p in spec.pads] == [(("a", "b"), "Centre"),
                                                     (("c", "d", "e"), "Burst")]
    assert fx.pad_of(spec, "e").label == "Burst" and fx.pad_of(spec, "x") is None
    # drawing only: a pad declares nothing, so it re-declares nothing
    bare = parse("t", "\n".join(ln for ln in spec.source.splitlines() if "@pair" not in ln
                                and "@volume" not in ln) + "\n")
    assert bare.signature() == spec.signature()


@pytest.mark.parametrize("line,why", [
    ('// @pair u_a "X"', "wants 2 uniforms"),
    ('// @volume u_a u_b "X"', "wants 3 uniforms"),
    ('// @pair u_a u_a "X"', "twice"),
    ('// @pair u_a u_zz "X"', "no continuous @param"),
    ('// @pair u_a u_m "X"', "no continuous @param"),            # a choice is no axis
    ('// @pair u_a u_b "X"\n// @pair u_b u_a "Y"', "on another pad"),
    ('// @pair u_a u_b', "wants 2 uniforms"),
])
def test_a_bad_pad_line_says_why(line, why):
    body = (line + "\nuniform float u_a; // @param 0 1 0 \"A\"\n"
            "uniform float u_b; // @param 0 1 0 \"B\"\n"
            "uniform int u_m; // @param choice [p|q] 0 \"M\"\n" + HEAD)
    with pytest.raises(SpecError, match=why):
        parse("t", body)


def test_a_param_line_may_say_its_polarity():
    spec = parse("t", 'uniform float u_a; // @param -1 1 0.5 bipolar "A"\n'
                 'uniform float u_b; // @param -1 1 0 unipolar "B"\n'
                 'uniform float u_c; // @param 0 1 0 "C"\n' + HEAD)
    assert [p.polarity for p in spec.params] == ["bipolar", "unipolar", ""]
    with pytest.raises(SpecError, match="not both"):
        parse("t", 'uniform float u_a; // @param -1 1 0 bipolar unipolar "A"\n' + HEAD)


def test_the_four_files_carry_their_pads_and_no_param_moved():
    """D3: Prism, Wave and Wave Table a pair, Zoom burst a volume; every
    param they had is still declared under its own id."""
    st = FxState()
    got = {n: [(p.keys, p.label) for p in st.files[n].pads]
           for n in ("prism", "wave", "wavetable", "zoomblur")}
    assert got == {"prism": [(("cx", "cy"), "Centre")], "wave": [(("cx", "cy"), "Centre")],
                   "wavetable": [(("offset_x", "offset_y"), "Offset")],
                   "zoomblur": [(("cx", "cy", "amount"), "Burst")]}
    assert not st.errors


# ---- the shapes ----

@pytest.mark.parametrize("lo,hi,log,default,said,want", [
    (-2, 2, False, 0, "", BIPOLAR),           # Kaleidoscope's swirl
    (-1, 1, False, 0, "", BIPOLAR),           # a centre
    (-1, 1, False, None, "", BIPOLAR),        # no default to read (no effect's): as before
    (-2, 2, False, -0.8, "", UNIPOLAR),       # across 0, resting elsewhere
    (-2, 2, False, -0.8, "bipolar", BIPOLAR), # …unless the line says so
    (-1, 1, False, 0, "unipolar", UNIPOLAR),
    (0.25, 4, True, 1, "", UNITY),            # Kaleidoscope's zoom
    (0.0625, 16, True, 1, "", UNITY),         # Blocks' aspect
    (0, 2, False, 1, "", UNITY),              # Hue cycle's saturation
    (0, 3, False, 1, "", UNIPOLAR),           # Prism's rim: 1 is no neutral
    (0, 16, False, 1, "", UNIPOLAR),
    (0.5, 8, True, 1, "", UNIPOLAR),
    (0, 1, False, 0, "", UNIPOLAR),
])
def test_polarity_is_inferred_from_the_range_and_the_default(lo, hi, log, default, said, want):
    assert polarity(lo, hi, log, default, said) == want


def test_ticks_one_a_step_while_they_fit():
    assert len(ticks(2, 16, 300)) == 15                  # Kaleidoscope's segments: all 15
    assert ticks(2, 16, 300)[0] == 0.0 and ticks(2, 16, 300)[-1] == 1.0


@pytest.mark.parametrize("lo,hi,span", [(4, 32, 100), (8, 96, 200), (3, 32, 60), (0, 1000, 300),
                                        (1, 4, 10), (0, 16, 400)])
def test_ticks_thin_and_never_crowd(lo, hi, span):
    t = ticks(lo, hi, span)
    assert t[0] == 0.0 and t[-1] == 1.0
    gaps = [(b - a) * span for a, b in pairwise(t)]
    assert min(gaps) >= 6.0 - 1e-9
    # thinned ticks sit on whole values a stride apart
    vals = [lo + x * (hi - lo) for x in t[1:-1]]
    assert all(abs(v - round(v)) < 1e-9 for v in vals)


def test_ticks_thinned_count():
    # Zoom burst's taps over 100 px: 3.6 px a step, every 2nd from 6 to 30, and both ends
    assert len(ticks(4, 32, 100)) == 15
    assert ticks(4, 32, 0) == [] and ticks(5, 5, 100) == []


def test_shapes_of_the_effects_params(tmp_path, monkeypatch):
    with strip(tmp_path, monkeypatch, "kaleido") as (r, _d, _st):
        reg, p = r.reg, r.panel
        swirl = shape_of(p, reg["fx.kaleido.swirl"])
        assert (swirl.polarity, swirl.origin, swirl.detent, swirl.neutral) == (BIPOLAR, 0.5, 0.5, 0.0)
        zoom = shape_of(p, reg["fx.kaleido.zoom"])
        assert zoom.polarity == UNITY and zoom.detent == pytest.approx(0.5)
        seg = shape_of(p, reg["fx.kaleido.segments"])
        assert (seg.polarity, seg.lo, seg.hi, seg.detent) == (UNIPOLAR, 2, 16, None)
        speed = shape_of(p, reg["fx.kaleido.speed"])       # the stop, and the 1× notch
        assert speed.polarity == BIPOLAR and speed.detent == 0.5 and len(speed.notches) == 2
        assert p._origin(reg["fx.kaleido.swirl"]) == 0.5     # the stock path's fill too
        assert shape_of(p, reg["fx.huecycle.sat"]).polarity == UNITY
        assert shape_of(p, reg["fx.blocks.aspect"]).polarity == UNITY


# ---- the panel, driven ----

def test_a_bipolar_fader_rests_centred_and_a_drag_near_centre_lands_on_zero(tmp_path, monkeypatch):
    with strip(tmp_path, monkeypatch, "kaleido") as (r, d, _st):
        swirl = r.reg["fx.kaleido.swirl"]
        assert swirl.value == 0 and swirl.norm == 0.5          # at rest, the thumb is the detent
        d.run(d.slide("fx.kaleido.swirl", 0.9), d.park())
        assert swirl.value > 1.0
        d.run(d.slide("fx.kaleido.swirl", 0.505), d.park())    # within the detent: on it
        assert swirl.value == 0.0
        d.run(d.enter("fx.kaleido.swirl", 0.01))               # a typed value is not snapped
        assert swirl.value == pytest.approx(0.01)


def test_a_stepped_fader_draws_its_ticks(tmp_path, monkeypatch):
    seen = []
    real = ui_fields.ticks

    def rec(lo, hi, span, gap=None):
        out = real(lo, hi, span, gap)
        seen.append((lo, hi, span, len(out)))
        return out
    monkeypatch.setattr(ui_fields, "ticks", rec)
    with strip(tmp_path, monkeypatch, "kaleido") as (_r, _d, _st):
        segs = [s for s in seen if (s[0], s[1]) == (2, 16)]
        assert segs, seen
        _lo, _hi, span, n = segs[-1]
        assert span > 15 * 6 and n == 15                        # room for all 15


def test_a_drag_on_the_pad_sets_both_params(tmp_path, monkeypatch):
    with strip(tmp_path, monkeypatch, "prism") as (r, d, _st):
        cx, cy = r.reg["fx.prism.cx"], r.reg["fx.prism.cy"]
        for pid in ("fx.prism.cx", "fx.prism.cy"):
            d.rect(pid)                                          # each axis keeps its own knob
        x0, y0, x1, y1 = d.rect("pad.fx.prism.cx")
        assert x1 - x0 >= 120 and abs((x1 - x0) - (y1 - y0)) < 1   # a square, stage-sized
        d.run(d.move("pad.fx.prism.cx"), d.press(True),
              d.move((x0 + 0.75 * (x1 - x0), y0 + 0.25 * (y1 - y0)), 6), d.press(False), d.park())
        assert cx.value == pytest.approx(0.5, abs=0.02)        # right of centre
        assert cy.value == pytest.approx(0.5, abs=0.02)        # up is +
        d.run(d.click((x0 + 1, y1 - 1)), d.park())               # the bottom-left corner
        assert cx.value == pytest.approx(-1, abs=0.02) and cy.value == pytest.approx(-1, abs=0.02)


def test_a_knob_turns_one_axis_and_a_double_click_centres_it(tmp_path, monkeypatch):
    with strip(tmp_path, monkeypatch, "zoomblur") as (r, d, _st):
        cx, cy, amt = (r.reg[f"fx.zoomblur.{k}"] for k in ("cx", "cy", "amount"))
        before = (cy.value, amt.value)
        x, y = d.centre("fx.zoomblur.cx")
        d.run(d.move((x, y)), d.press(True), d.move((x, y - 100), 5), d.press(False), d.park())
        assert cx.value == pytest.approx(0.0 + 2 * 0.5, abs=0.05)    # half the throw up: +1
        assert (cy.value, amt.value) == before
        d.run(d.click("fx.zoomblur.cx"), d.click("fx.zoomblur.cx"), d.park())
        assert cx.value == 0.0
        # the volume's third knob: the tapered amount, turned up
        x, y = d.centre("fx.zoomblur.amount")
        d.run(d.move((x, y)), d.press(True), d.move((x, y - 40), 4), d.press(False), d.park())
        assert amt.value > before[1]


def test_the_pad_shows_a_lane_riding_it(tmp_path, monkeypatch):
    """A lane on one axis: the pad draws where it has it now (a ghost)
    beside the bases, and the readout goes red."""
    with strip(tmp_path, monkeypatch, "wave") as (r, d, _st):
        p = r.reg["fx.wave.cx"]
        r.panel.ghosts = 0
        p.modulate(0.5)            # a lane's offset this frame, as the Router writes it
        d.run(d.wait(1))
        assert p.modulated and r.panel.ghosts >= 2              # the pad's ghost and the knob's
        assert p.base == 0.0                                    # the base is where it was


def test_the_strip_draws_no_slider_for_a_padded_param(tmp_path, monkeypatch):
    with strip(tmp_path, monkeypatch, "wavetable") as (_r, d, _st):
        assert "pad.fx.wavetable.offset_x" in d.rects
        # the knob is an invisible button, not a slider row of its own
        kx0, _ky0, kx1, _ky1 = d.rect("fx.wavetable.offset_x")
        assert kx1 - kx0 == pytest.approx(2 * ui.KNOB_R)


# ---- the review's four (Devin, 2026-11-23) ----

def test_a_slow_fine_drag_on_a_tapered_knob_adds_up(tmp_path, monkeypatch):
    """A ⇧-drag a few px a frame on Zoom burst's Amount (a 200-detent taper):
    each frame's move is under half a detent, and together they cross several."""
    with strip(tmp_path, monkeypatch, "zoomblur") as (r, d, _st):
        amt = r.reg["fx.zoomblur.amount"]
        pos = amt.position()
        x, y = d.centre("fx.zoomblur.amount")
        io = imgui.get_io()
        d.run(d.move((x, y)), d.press(True))
        io.add_key_event(imgui.Key.mod_shift, True)
        for i in range(1, 21):                       # 2 px a frame: 0.1 of a detent each
            d.run(d.move((x, y - 2 * i)))
        io.add_key_event(imgui.Key.mod_shift, False)
        d.run(d.press(False), d.park())
        assert amt.position() - pos == pytest.approx(4, abs=1)


def test_letting_go_of_shift_mid_drag_does_not_jump_the_pad(tmp_path, monkeypatch):
    with strip(tmp_path, monkeypatch, "prism") as (r, d, _st):
        cx = r.reg["fx.prism.cx"]
        x0, y0, x1, y1 = d.rect("pad.fx.prism.cx")
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        io = imgui.get_io()
        d.run(d.move((mx, my)), d.press(True))
        assert cx.value == pytest.approx(0.0, abs=0.02)
        io.add_key_event(imgui.Key.mod_shift, True)
        d.run(d.move((mx + (x1 - x0) / 4, my), 4))   # a quarter across, fine: a tenth of it
        fine = cx.value
        assert fine == pytest.approx(0.05, abs=0.01)
        io.add_key_event(imgui.Key.mod_shift, False)
        d.run(d.wait(3))                             # ⇧ up, the pointer still
        assert cx.value == pytest.approx(fine)
        d.run(d.press(False), d.park())
        assert cx.value == pytest.approx(fine)


def test_a_pad_over_keys_the_strip_packs_is_still_a_pad():
    from hyperspace import ui_fx
    spec = parse("t", '// @pair u_sat_lo u_sat_hi "Saturation"\n'
                 'uniform float u_amount; // @param 0 1 0 "Amount"\n'
                 'uniform float u_sat_lo; // @param 0 1 0 "Sat lo"\n'
                 'uniform float u_sat_hi; // @param 0 1 1 "Sat hi"\n'
                 'uniform float u_val_lo; // @param 0 1 0 "Val lo"\n'
                 'uniform float u_val_hi; // @param 0 1 1 "Val hi"\n' + HEAD)
    keys = [p.key for p in spec.params]
    assert ui_fx.pad_rows(spec, "t", keys) == [
        ("amount", ["amount"]), ("saturation", ["sat_lo", "sat_hi"]), ("val", ["val_lo", "val_hi"])]
    # without the kit the strip's rows are as before: the pair packed
    assert ui_fx.pad_rows(spec, "t", keys, pads=False) == ui_fx.strip_rows("t", keys)


def test_a_ridden_knobs_readout_stays_in_its_column(tmp_path, monkeypatch):
    """`base → effective` at its widest (−0.50 → −0.25) is two lines, each
    inside the knob's column, never past the pane."""
    drawn = []
    real = ui_fields.text

    def rec(dl, x, y, h, s, font, size, col):
        w = real(dl, x, y, h, s, font, size, col)
        drawn.append((s, x, x + w))
        return w
    monkeypatch.setattr(ui_fields, "text", rec)
    with strip(tmp_path, monkeypatch, "prism") as (r, d, _st):
        p = r.reg["fx.prism.cx"]
        p.set_value(-0.5)
        p.modulate(0.125)                            # a lane's offset: −0.50 → −0.25
        drawn.clear()
        d.run(d.wait(1))
        kx0, _ky0, kx1, _ky1 = d.rect("fx.prism.cx")
        cx = (kx0 + kx1) / 2
        lines = [t for t in drawn if "→" in t[0] or t[0] == "-0.50"]
        assert any(t[0].startswith("→") for t in lines), drawn
        for _s, a, b in lines:
            assert cx - ui.KNOB_COL / 2 - 1 <= a and b <= cx + ui.KNOB_COL / 2 + 1


def test_a_double_click_held_into_a_drag_moves_from_the_detent(tmp_path, monkeypatch):
    with strip(tmp_path, monkeypatch, "prism") as (r, d, _st):
        cx = r.reg["fx.prism.cx"]
        cx.set_value(0.6)
        d.run(d.wait(1))
        x, y = d.centre("fx.prism.cx")
        d.run(d.click((x, y)), d.press(True))       # the second press, held
        assert cx.value == 0.0
        d.run(d.move((x, y - 2)), d.press(False), d.park())
        assert cx.value == pytest.approx(0.02, abs=0.005)    # 2 px of a 200 px throw over −1…1


def test_without_the_kit_a_packed_pad_is_its_sliders(tmp_path, monkeypatch):
    """No kit: a pad over keys the strip packs (`sat_lo`, `sat_hi`) is the
    packed row of sliders it always was — never a pad."""
    import shutil

    from hyperspace import ui_kit
    src = fx.FX_DIR
    dst = tmp_path / "fx"
    dst.mkdir()
    for f in ("_lib.glsl", "prism.glsl"):
        shutil.copy(src / f, dst / f)
    (dst / "packed.glsl").write_text(
        '// @label Packed\n// @pair u_sat_lo u_sat_hi "Saturation"\n'
        'uniform float u_sat_lo; // @param 0 1 0 "Sat lo"\n'
        'uniform float u_sat_hi; // @param 0 1 1 "Sat hi"\n' + HEAD)
    pads = []
    monkeypatch.setattr(ui_fields, "inline_pad", lambda *a, **k: pads.append(a) or {})
    monkeypatch.setattr(ui_kit, "ready", lambda: False)
    with strip(tmp_path / "home", monkeypatch, "packed", fx_dir=dst) as (_r, d, st):
        assert not st.errors
        assert not pads
        assert "fx.packed.sat_lo" in d.rects and "fx.packed.sat_hi" in d.rects
