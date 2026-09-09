"""The parameter registry: one address space, one normalized contract."""

import math
from types import SimpleNamespace

import pytest

from hyperspace.analysis import Analyser
from hyperspace.bands import BANDS, PRESETS, Chain
from hyperspace.control import Control
from hyperspace.geometry import SHAPES
from hyperspace.params import Kind, Registry, build_registry
from hyperspace.presets import Presets
from hyperspace.render import ViewState


def make(tmp_path):
    chain = Chain(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    presets = Presets(view, control, audio, path=tmp_path / "presets.json")
    reg = build_registry(view, control, audio, presets)
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
    new = Chain(Analyser())
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
    assert presets.slots[5]["view"]["shape"] == 12


def test_scene_names_match_presets(rig):
    assert rig[0]["scene.select"].names == [p["name"] for p in PRESETS]


def test_core_does_not_import_the_midi_adapter():
    """BLUEPRINT §3.6: the bridge depends on the core, never the reverse."""
    import sys

    sys.modules.pop("hyperspace.midi", None)
    import importlib

    for m in ("hyperspace.params", "hyperspace.control", "hyperspace.presets",
              "hyperspace.bands", "hyperspace.render"):
        importlib.import_module(m)
    assert "hyperspace.midi" not in sys.modules
