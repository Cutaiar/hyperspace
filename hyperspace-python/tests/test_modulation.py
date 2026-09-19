"""WP0 foundation: param flags, registry snapshot/restore/remove, modulation.

Modulation is the one control concept every source shares (params.py
docstring): a source calls modulate(u) each frame, Registry.apply() lands
base + offsets on the object, and the base — what the user set — is what
every surface reads and every preset saves.
"""

import math

import pytest
from test_params import make

from hyperspace.params import Kind


@pytest.fixture()
def rig(tmp_path):
    return make(tmp_path)


def _frame(reg, *mods):
    """One frame: every source calls modulate, then the registry applies."""
    for p, u in mods:
        p.modulate(u)
    reg.apply()


# ---------------------------------------------------------------- new params

def test_new_params_exist_and_default_to_the_undriven_look(rig):
    reg, view, *_ = rig
    for name in ("XY", "XZ", "YZ", "XW", "YW", "ZW"):
        assert reg[f"rot.rate.{name}"].value == 1.0
        assert reg[f"rot.phase.{name}"].value == 0.0
    for k in range(8):
        assert reg[f"pattern.mod.{k}"].value == 1.0
    assert reg["camera.pan.x"].value == 0.0 and reg["camera.pan.y"].value == 0.0
    assert reg["view.bmp_file"].kind is Kind.TEXT
    reg["camera.pan.x"].set_value(12.5)
    assert view.pan[0] == 12.5
    reg["rot.rate.XY"].set_value(-2.0)   # signed: a plane can run backwards
    assert view.rate[0] == -2.0


def test_rate_multiplies_the_integrator(rig):
    _reg, view, *_ = rig
    view.planes = [True] + [False] * 5
    view.ang = [0.0] * 6
    view.rate[0] = 2.0
    view.integrate(0.1)
    doubled = view.ang[0]
    view.ang = [0.0] * 6
    view.rate[0] = 1.0
    view.integrate(0.1)
    assert doubled == pytest.approx(2 * view.ang[0])
    view.rate[0] = -1.0
    view.ang = [0.0] * 6
    view.integrate(0.1)
    assert view.ang[0] < 0


# ---------------------------------------------------------------- flags

def test_flags_say_what_a_param_is_for(rig):
    reg = rig[0]
    a = reg["band.sel.atk"]
    assert a.alias and not a.persist and not a.modulatable
    for pid in ("band.select", "theme.select", "rot.phase.XY"):
        assert not reg[pid].persist, pid
    assert not reg["theme.select"].modulatable
    assert not reg["theme.save.0"].modulatable
    assert reg["theme.load.0"].modulatable      # a kick may load a theme
    assert not reg["camera.reset"].persist       # triggers never persist
    assert reg["view.bright"].persist and reg["view.bright"].modulatable
    assert not reg["view.bmp_file"].modulatable


def test_text_param_is_inert_on_every_numeric_surface(rig):
    reg, view, *_ = rig
    p = reg["view.bmp_file"]
    p.set("/tmp/x.png")
    assert view.bmp_file == "/tmp/x.png" and p.text() == "/tmp/x.png"
    assert p.norm == 0.0
    p.set_norm(1.0)
    p.step(3)
    p.toggle()
    p.modulate(0.5)
    reg.apply()
    assert view.bmp_file == "/tmp/x.png" and not p.modulated


# ---------------------------------------------------------------- persistence

def test_snapshot_and_restore_round_trip_through_the_registry(rig):
    reg, view, _control, _audio, _ = rig
    view.bright, view.shape, view.faces = 1.5, 7, True
    reg["camera.pan.y"].set_value(-40.0)
    reg["band.2.atk"].set_norm(0.3)
    reg["view.bmp_file"].set("a.png")
    snap = reg.snapshot()
    for absent in ("band.sel.atk", "theme.select", "camera.reset", "rot.phase.XY"):
        assert absent not in snap, absent
    assert snap["view.bright"] == 1.5 and snap["view.shape"] == 7
    assert snap["view.faces"] is True and snap["view.bmp_file"] == "a.png"
    assert set(reg.snapshot("camera")) == {p.id for p in reg.group("camera") if p.persist}
    # scramble, restore, compare
    view.bright, view.shape, view.faces, view.bmp_file = 0.4, 1, False, ""
    view.pan[1] = 0.0
    reg["band.2.atk"].set_norm(0.9)
    missing = reg.restore({**snap, "gone.param": 1})
    assert missing == ["gone.param"]
    assert (view.bright, view.shape, view.faces, view.pan[1]) == (1.5, 7, True, -40.0)
    assert view.bmp_file == "a.png"
    assert reg["band.2.atk"].norm == pytest.approx(0.3, abs=1.0 / reg["band.2.atk"].steps)
    assert reg.snapshot() == snap


def test_snapshot_saves_the_base_not_the_modulated_value(rig):
    reg, view, *_ = rig
    b = reg["view.bright"]
    b.set_value(1.0)
    _frame(reg, (b, 0.3))
    assert view.bright != 1.0
    assert reg.snapshot(ids={"view.bright"}) == {"view.bright": 1.0}


def test_remove_and_remove_prefix(rig):
    reg = rig[0]
    n = len(reg)
    assert reg.remove("band.5.atk").id == "band.5.atk"
    assert "band.5.atk" not in reg and reg.get("band.5.atk") is None
    gone = reg.remove_prefix("band.5.")
    assert gone and all(p.id.startswith("band.5.") for p in gone)
    assert len(reg) == n - 1 - len(gone)
    assert reg.remove("nope") is None


def test_removing_a_modulated_param_hands_back_its_base(rig):
    reg, view, *_ = rig
    b = reg["view.bright"]
    b.set_value(1.0)
    _frame(reg, (b, 0.3))
    assert view.bright != 1.0
    reg.remove("view.bright")
    assert view.bright == 1.0


# ---------------------------------------------------------------- modulation

def test_modulation_rides_on_the_base_and_lets_go_cleanly(rig):
    reg, view, *_ = rig
    b = reg["view.bright"]
    b.set_value(1.0)
    base_norm = b.norm
    _frame(reg, (b, 0.25))
    assert b.modulated
    assert b.base == 1.0 and b.norm == base_norm          # the setting is untouched
    assert view.bright == pytest.approx(b.taper.map((base_norm + 0.25) * b.taper.steps))
    assert b.value > 1.0 and b.eff_norm > b.norm
    # two sources sum; the result clamps at the top of the throw
    _frame(reg, (b, 0.5), (b, 0.5))
    assert view.bright == b.taper.map(b.taper.steps)
    # nothing calls this frame: the object gets the base back
    _frame(reg)
    assert not b.modulated and view.bright == 1.0


def test_modulation_is_float_mapped_not_detented(rig):
    reg, view, *_ = rig
    b = reg["view.bright"]
    b.set_value(1.0)
    seen = set()
    for i in range(20):
        _frame(reg, (b, 0.001 * i))
        seen.add(view.bright)
    assert len(seen) == 20                      # every tiny offset is a distinct value


def test_setting_a_modulated_param_moves_its_base(rig):
    reg, view, *_ = rig
    b = reg["view.bright"]
    b.set_value(1.0)
    _frame(reg, (b, 0.1))
    b.set_norm(0.2)                            # a fader / MIDI knob while modulated
    assert b.norm == pytest.approx(0.2)        # …lands on the base
    _frame(reg, (b, 0.1))
    assert b.eff_norm == pytest.approx(0.3, abs=1.5 / b.steps)
    b.step(10)
    assert b.position() == 30
    b.set(b.taper.map(50))                     # raw set() too
    assert b.position() == 50
    assert b.text() == b.fmt(b.taper.map(50))  # the readout shows the setting
    _frame(reg)
    assert view.bright == b.taper.map(50)


def test_a_direct_object_write_is_adopted_into_the_base(rig):
    """The rotation integrator adds to ang every frame; a lane adds a phase offset."""
    reg, view, *_ = rig
    ph = reg["rot.phase.XY"]
    view.ang[0] = 0.0
    _frame(reg, (ph, 0.25))                    # a quarter turn of offset
    assert view.ang[0] == pytest.approx(math.pi / 2)
    view.ang[0] += 0.1                         # the integrator's step, written raw
    _frame(reg, (ph, 0.25))
    assert view.ang[0] == pytest.approx(math.pi / 2 + 0.1)
    _frame(reg)                                # offset removed: only the spin remains
    assert view.ang[0] == pytest.approx(0.1)
    # any other raw write to a modulated object is taken as a delta too —
    # in the param's normalized (here: log) space, so the base moves by the
    # same ratio the object did. Absolute writes belong to set()/restore().
    b = reg["view.bright"]
    b.set_value(1.0)
    _frame(reg, (b, 0.1))
    before = b.eff_norm
    view.bright = 2.0
    _frame(reg, (b, 0.1))
    assert b.norm == pytest.approx(b._norm_of(1.0) + b._norm_of(2.0) - before, abs=1e-9)


def test_wrap_params_modulate_around_the_circle(rig):
    reg, view, *_ = rig
    yaw = reg["camera.yaw"]
    yaw.set_value(math.pi - 0.1)
    _frame(reg, (yaw, 0.1))                    # a tenth of a turn, across the seam
    expect = math.remainder(math.pi - 0.1 + 0.2 * math.pi, 2 * math.pi)
    assert view.yaw == pytest.approx(expect, abs=1e-6)
    assert yaw.base == pytest.approx(math.pi - 0.1)


def test_discrete_targets_move_with_hysteresis(rig):
    reg, view, *_ = rig
    f = reg["view.faces"]
    f.set(False)
    _frame(reg, (f, 0.5))
    assert view.faces is False                 # below ON
    _frame(reg, (f, 0.65))
    assert view.faces is True
    _frame(reg, (f, 0.5))
    assert view.faces is True                  # holds until below OFF
    _frame(reg, (f, 0.35))
    assert view.faces is False
    s = reg["view.shape"]
    s.set(0)
    n = s.steps
    _frame(reg, (s, 0.5 / n))                  # exactly half a choice: deadband holds
    assert view.shape == 0
    _frame(reg, (s, 0.7 / n))
    assert view.shape == 1
    _frame(reg, (s, 0.4 / n))                  # back inside the deadband: still 1
    assert view.shape == 1
    inst = reg["view.instances"]
    inst.set_value(1)
    _frame(reg, (inst, 2.0 / inst.steps))
    assert view.instances == 3 and isinstance(view.instances, int)
    _frame(reg)
    assert view.shape == 0 and view.instances == 1 and view.faces is False


def test_trigger_fires_once_per_rising_edge(rig):
    reg, view, *_ = rig
    t = reg["camera.reset"]
    view.yaw = 1.0
    _frame(reg, (t, 0.3))
    assert view.yaw == 1.0
    _frame(reg, (t, 0.8))
    assert view.yaw == 0.0                     # fired
    view.yaw = 1.0
    _frame(reg, (t, 0.9))
    assert view.yaw == 1.0                     # still high: no second fire
    _frame(reg, (t, 0.3))
    _frame(reg, (t, 0.9))
    assert view.yaw == 0.0                     # re-armed below OFF, fired again


def test_unmodulatable_params_ignore_sources(rig):
    reg, _view, control, *_ = rig
    sel = reg["band.select"]
    sel.set(2)
    _frame(reg, (sel, 1.0))
    assert control.selb == 2 and not sel.modulated
