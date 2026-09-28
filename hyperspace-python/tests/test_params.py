"""The parameter registry: one address space, one normalized contract."""

import math
from types import SimpleNamespace

import pytest

from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.bands import BANDS
from hyperspace.control import SCENES, Control
from hyperspace.geometry import SHAPES
from hyperspace.library import Library
from hyperspace.params import Kind, Registry, build_registry
from hyperspace.render import ViewState


def make(tmp_path):
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(tmp_path)
    presets = lib.bank
    reg = build_registry(view, control, audio, presets)
    lib.attach(reg)
    return reg, view, control, audio, presets


@pytest.fixture()
def rig(tmp_path):
    return make(tmp_path)


def test_ids_are_unique_and_stable(rig):
    reg = rig[0]
    ids = reg.ids()
    assert len(ids) == len(set(ids))
    for must in ("view.bright", "view.shape", "master.gain", "scene.select",
                 "band.0.atk", "band.5.thr", "band.sel.pre", "band.select",
                 "theme.load.0", "theme.save.7", "camera.zoom", "view.plane.ZW"):
        assert must in reg, must
    r = Registry()
    r.toggle("x", "x", lambda: True, lambda v: None)
    with pytest.raises(ValueError):
        r.toggle("x", "x", lambda: True, lambda v: None)


def test_every_continuous_param_round_trips_norm(rig):
    """norm → set_norm → norm is the identity on every detent."""
    reg = rig[0]
    for p in reg:
        if p.kind is not Kind.CONTINUOUS:
            continue
        for pos in range(0, p.steps + 1, max(p.steps // 25, 1)):
            p.set_position(pos)
            assert p.position() == pos, f"{p.id} walks sideways at {pos}"
            u = p.norm
            p.set_norm(u)
            assert p.norm == pytest.approx(u, abs=1e-12), p.id
        p.set_norm(0.0)
        assert p.position() == 0
        p.set_norm(1.0)
        assert p.position() == p.steps


def test_tapered_param_quantizes_to_the_taper(rig):
    reg, view, *_ = rig
    b = reg["view.bright"]
    b.set_norm(0.5)
    assert b.position() == 50 and view.bright == b.taper.map(50)
    b.set_value(1.0)  # unity sits on the detent exactly
    assert b.position() == b.taper.unity and view.bright == 1.0
    b.set_value(999.0)  # clamped to the top of the throw
    assert b.position() == b.steps
    assert b.text() == "4.00×"


def test_raw_ranges_clamp_int_and_log(rig):
    reg, view, *_ = rig
    inst = reg["view.instances"]
    inst.set_norm(1.0)
    assert view.instances == 100 and isinstance(view.instances, int)
    inst.set_value(-5)
    assert view.instances == 1
    inst.step(3)
    assert view.instances == 4
    z = reg["camera.zoom"]
    z.set_norm(0.5)  # log: halfway is the geometric middle
    assert view.zoom == pytest.approx(math.sqrt(0.05 * 40.0))
    z.set_value(1.0)
    assert z.norm == pytest.approx(math.log2(1.0 / 0.05) / math.log2(40.0 / 0.05))
    yaw = reg["camera.yaw"]
    yaw.set_value(math.pi + 0.5)  # wraps, never clamps
    assert view.yaw == pytest.approx(-math.pi + 0.5)


def test_nudge_and_scale_move_the_base_without_a_detent(rig):
    """Plan 09 WP2: the relative writers' two moves. In the param's own
    units, on the base, wrapped or clamped, returning what was applied —
    and never snapped to a detent, so a tapered param takes a fraction of
    a step per frame and adds it up."""
    reg, view, *_ = rig
    yaw, zoom, inst = reg["camera.yaw"], reg["camera.zoom"], reg["view.instances"]
    # wrap: the whole delta always lands
    yaw.set_value(math.pi - 0.1)
    assert yaw.nudge(0.3) == 0.3
    assert view.yaw == pytest.approx(-math.pi + 0.2)
    # clamp: what the stop let through
    zoom.set_value(39.0)
    assert zoom.nudge(5.0) == pytest.approx(1.0) and view.zoom == 40.0
    assert zoom.scale(2.0) == pytest.approx(1.0) and view.zoom == 40.0
    zoom.set_value(2.0)
    assert zoom.scale(1.5) == pytest.approx(1.5) and view.zoom == pytest.approx(3.0)
    assert zoom.nudge(-0.5) == pytest.approx(-0.5) and view.zoom == pytest.approx(2.5)
    # a ratio means nothing across zero: yaw's range does, a base of 0 does
    assert yaw.scale(2.0) == 1.0 and view.yaw == pytest.approx(-math.pi + 0.2)
    zoom.set_value(0.05)
    assert zoom.scale(2.0) == pytest.approx(2.0)          # lo is above zero: fine
    # an integer range stays integer
    inst.set_value(4)
    assert inst.nudge(0.4) == 0 and view.instances == 4
    assert inst.nudge(0.6) == 1 and view.instances == 5
    # a tapered param: 20 sub-detent nudges add up to one detent's move
    d = reg["view.depth4"]
    d.set_position(80)
    one = d.taper.map(81) - d.taper.map(80)
    for _ in range(20):
        d.nudge(one / 20)
    assert view.depth4 == pytest.approx(d.taper.map(81), rel=1e-9) and d.position() == 81
    d.nudge(one / 20)
    assert view.depth4 > d.taper.map(81)                    # raw: not parked on the detent
    with pytest.raises(TypeError):
        reg["view.shape"].nudge(1)


def test_nudge_and_scale_under_modulation_move_the_base(rig):
    """While a source holds the param, nudge and scale write the base — a
    tapered one at a continuous position, so sub-detent moves still add
    up — and the offset rides on top through apply()."""
    reg, view, *_ = rig
    zoom, d = reg["camera.zoom"], reg["view.depth4"]
    zoom.set_value(1.0)
    d.set_position(80)
    one = d.taper.map(81) - d.taper.map(80)                  # a detent, in depth units
    for _ in range(10):
        zoom.scale(1.1)
        d.nudge(one / 20)
        zoom.modulate(0.1)
        d.modulate(0.1)
        reg.apply()
    assert zoom.base == pytest.approx(1.1 ** 10, rel=1e-9)
    assert zoom.eff_norm == pytest.approx(zoom.norm + 0.1, abs=1e-9)
    want = d.taper.map(80) + one / 2                         # linear in value: half a detent
    assert d.base == pytest.approx(want, rel=1e-9)
    assert 80.0 < d.norm * d.steps < 81.0                    # a continuous position
    assert view.depth4 == pytest.approx(d.taper.map(d.norm * d.steps + 16), rel=1e-9)  # + 0.1 × 160
    reg.apply()                                              # the source lets go
    assert view.zoom == pytest.approx(1.1 ** 10, rel=1e-9)
    assert view.depth4 == pytest.approx(want, rel=1e-9)


def test_enum_norm_and_stepping(rig):
    reg, view, *_ = rig
    s = reg["view.shape"]
    assert s.names == [x.name for x in SHAPES]
    s.set_norm(1.0)
    assert view.shape == len(SHAPES) - 1
    s.step(1)  # clamps at the end
    assert view.shape == len(SHAPES) - 1
    s.cycle(1)  # cycle wraps
    assert view.shape == 0
    s.set_norm(0.0)
    s.step(-1)
    assert view.shape == 0
    assert s.text() == SHAPES[0].name


def test_toggles_and_triggers(rig):
    reg, view, _control, *_ = rig
    f = reg["view.faces"]
    assert not view.faces
    f.toggle()
    assert view.faces and f.norm == 1.0
    f.set_norm(0.0)
    assert not view.faces
    f.step(1)
    assert view.faces
    zw = reg["view.plane.ZW"]
    zw.set(True)
    assert view.planes[5] is True
    view.yaw = 1.0
    reg["camera.reset"].fire()
    assert view.yaw == 0.0
    view.yaw = 1.0
    reg["camera.reset"].set_norm(1.0)  # a note-on fires a trigger
    assert view.yaw == 0.0
    view.yaw = 1.0
    reg["camera.reset"].set_norm(0.0)  # a note-off does not
    assert view.yaw == 1.0


def test_scene_and_band_params_route_through_control(rig):
    reg, _view, control, audio, _ = rig
    reg["scene.select"].set(4)
    assert control.scene == 4
    assert audio.chain.params[3].trim == -10  # Bass Engine's MID trim
    audio.chain.st[2]["e"] = 0.7
    reg["band.2.fn"].set(9)
    assert audio.chain.params[2].fn == 9 and audio.chain.st[2] == {}
    reg["band.3.atk"].set_norm(0.25)
    assert reg["band.3.atk"].position() == 36


def test_selected_band_alias_follows_selection(rig):
    reg, _view, control, audio, _ = rig
    control.selb = 1
    reg["band.sel.pre"].set_norm(1.0)
    assert audio.chain.params[1].pre == reg["band.1.pre"].value
    assert audio.chain.params[0].pre == 1  # untouched
    reg["band.select"].set(4)
    assert control.selb == 4
    assert reg["band.sel.atk"].value == audio.chain.params[4].atk
    assert reg["band.select"].names == [b.id for b in BANDS]


def test_params_survive_a_chain_swap(rig):
    """Getters resolve audio.chain live — a source attach replaces it."""
    reg, _view, control, audio, _ = rig
    new = Analyzer(Analyser())
    new.gain = 3.3
    audio.chain = new
    control.chain = new
    assert reg["master.gain"].value == 3.3
    reg["band.0.post"].set_norm(0.0)
    assert new.params[0].post == 0.0


def test_theme_params(rig):
    reg, view, _control, _audio, presets = rig
    assert len(reg["theme.select"].names) == 8
    reg["theme.load.1"].fire()
    assert presets.active == 1 and view.shape == 10
    reg["theme.select"].set_norm(0.0)
    assert presets.active == 0
    reg["theme.next"].fire()
    assert presets.active == 1
    view.shape = 12
    reg["theme.save.5"].fire()
    assert presets.slots[5]["values"]["view.shape"] == 12


def test_scene_names_match_presets(rig):
    assert rig[0]["scene.select"].names == list(SCENES)


def test_macro_knobs_are_persisted_attenuators_with_no_object(rig):
    """macro.1–8 (plan 09, decision 7): continuous 0–1, saved and drivable,
    read as a percentage, base 1 (the "× 1" a route runs at unscaled). They
    hold no object, so a snapshot is all there is to them: restoring one
    brings every knob back."""
    reg = rig[0]
    ms = reg.group("macro")
    assert [p.id for p in ms] == [f"macro.{k}" for k in range(1, 9)]
    for k, p in enumerate(ms, 1):
        assert (p.label, p.kind, p.lo, p.hi) == (f"Macro {k}", Kind.CONTINUOUS, 0.0, 1.0)
        assert p.persist and p.modulatable and not p.alias and p.taper is None
        assert p.value == 1.0 and p.text() == "100 %"
        assert "scale" in p.tip
    m = reg["macro.2"]
    m.set_value(0.42)
    assert m.text() == "42 %" and reg["macro.1"].value == 1.0   # its own slot
    snap = reg.snapshot("macro")
    assert snap == {f"macro.{k}": (0.42 if k == 2 else 1.0) for k in range(1, 9)}
    m.set_value(0.0)
    reg["macro.7"].set_norm(0.5)
    assert reg.restore(snap) == []
    assert m.value == pytest.approx(0.42) and reg["macro.7"].value == 1.0
    # the slot bounds itself: a restore writes raw, and nothing else would clamp
    assert reg.restore({"macro.3": 5.0, "macro.4": -2.0}) == []
    assert reg["macro.3"].value == 1.0 and reg["macro.4"].value == 0.0
    # routing-layer state (ROUTING_GROUPS): in a snapshot by group, out of the whole one
    assert not any(k.startswith("macro.") for k in reg.snapshot())
    assert set(reg.snapshot("macro")) == {p.id for p in ms}


def test_core_does_not_import_the_midi_adapter():
    """BLUEPRINT §3.6: the bridge depends on the core, never the reverse."""
    import sys

    sys.modules.pop("hyperspace.midi", None)
    import importlib

    for m in ("hyperspace.params", "hyperspace.control", "hyperspace.presets",
              "hyperspace.bands", "hyperspace.render"):
        importlib.import_module(m)
    assert "hyperspace.midi" not in sys.modules
