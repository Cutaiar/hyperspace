# ruff: noqa: F811 — `rig` is test_midi's fixture, taken as each test's argument
"""Plan 24 C2 — the faders freed (decisions 17, 23 and 24).

Driven through `MidiIO` with the fake ports tests/test_midi.py injects (its
rig: a scratch library whose show is the factory party show):

- **S1–S8 are the preset's**: the track faders carry no factory row on the
  preset layer, so every factory preset leaves them dark; a preset whose
  desk binds them (the fixture under tests/fixtures/desk-faders/, loaded
  through the scratch library) lights all eight and drives its params, and
  the rows round-trip through save and load;
- **the audio strip is one latch away**: the bands' post-drive on S1–S6 and
  master.dyn / master.trim on S7–S8 are the SHIFT layer's; MASTER stays the
  audio drive and the crossfader the master dim, invariant;
- **soft pickup across the latch** (D7): a fader moved on one layer picks
  up its own param on the other instead of jumping it;
- **the migration**: an older `bindings.json` with the eight invariant
  fader rows gets them on the SHIFT layer, noted, backed up, written once;
- **lines and points opacity**: two performance params at 1, today's
  picture; at 0 the layer is gone.
"""

import json
import shutil
from pathlib import Path

import pytest
from test_midi import cc, push, rig, shift  # noqa: F401 — the fixture

from hyperspace import apc40, preset, routing, ui_desk
from hyperspace.routing import Binding, Bindings, bindings_path
from hyperspace.view import ViewState

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "desk-faders"
FADER = apc40.CC_FADER
GLYPHS = [f"S{k + 1}" for k in range(8)]
TARGETS = ("view.points_alpha", "view.lines_alpha", "view.pattern_mix", "view.bmp_alpha",
           "view.bright", "view.speed", "view.inst_amp", "dream.mix")
SHIFT_TARGETS = (*(f"band.{i}.post" for i in range(6)), "master.dyn", "master.trim")


def load_fixture(rig, name="faders.json"):
    lib = rig.presets.lib
    (lib.home / "presets").mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / name, lib.home / "presets" / name)
    lib.presets.load("FADERS")
    rig.midi.poll()
    return lib


def faders_lit(t) -> dict[str, str]:
    """{glyph: target} of the track faders the desk shows now."""
    lit = ui_desk.lit(t)
    return {g: lit[g].target for g in GLYPHS if g in lit}


def at(rig, pid) -> int:
    """The CC value that puts a fader on `pid`'s value."""
    return round(rig.reg[pid].norm * 127)


# ------------------------------------------------------------------ the map

def test_the_faders_are_the_presets_and_the_audio_strip_is_shifts():
    """Decision 17: no preset-layer fader row in the factory map (no
    inherited default); the audio strip is the SHIFT layer's; MASTER and the
    crossfader stay invariant."""
    rows = [Binding.from_json(d) for d in apc40.DEFAULT_MAP]
    on_faders = [b for b in rows if b.kind == "cc" and b.number == FADER]
    assert [(b.channel, b.target, b.layer) for b in on_faders] == [
        (k, t, "global") for k, t in enumerate(SHIFT_TARGETS)]
    assert apc40.SHIFT_FADERS == SHIFT_TARGETS
    assert all(b.feedback is None and b.pickup and b.op == "abs" for b in on_faders)
    (gain,) = [b for b in rows if b.target == "master.gain"]
    (dim,) = [b for b in rows if b.target == "output.dim"]
    assert (gain.number, gain.layer) == (apc40.CC_MASTER, None)
    assert (dim.number, dim.layer) == (apc40.CC_XFADE, None)
    assert not [b for b in preset.fresh_desk() if b.number == FADER and b.kind == "cc"]
    assert not [b for b in preset.file_desk() if b.number == FADER and b.kind == "cc"]


def test_every_factory_preset_leaves_the_faders_dark_and_shift_lights_the_audio(rig):
    """Decision 23: no preset gets fader rows in this run — every factory
    file's desk binds no track fader, and each loads with S1–S8 dark on the
    preset layer and the audio strip under SHIFT, with no desk note."""
    lib, t = rig.presets.lib, rig.midi.table
    for path in sorted(preset.FACTORY_DIR.glob("*.json")):
        desk = json.loads(path.read_text()).get("desk") or []
        assert not [d for d in desk if d["source"].endswith(f":{FADER}")
                    and d["source"].startswith("cc:")], path.name
    for name in lib.list("presets"):
        lib.presets.load(name)
        rig.midi.poll()
        assert lib.presets.desk_notes == [], name
        assert t.layer == "preset"
        assert faders_lit(t) == {}, name
    shift(rig)
    assert faders_lit(t) == dict(zip(GLYPHS, SHIFT_TARGETS))


def test_knob_desk_learns_fader_rows_without_changing_a_factory_desk():
    """`knob_desk(…, faders=…)` puts track fader k + 1 on faders[k] (the
    mechanism the owner's authoring pass uses); with no faders, the default,
    the desk is the one every factory spec writes today."""
    plain = preset.knob_desk(preset.TRIP_KNOBS)()
    assert not [b for b in plain if b.kind == "cc" and b.number == FADER]
    withf = preset.knob_desk(preset.TRIP_KNOBS, faders=("view.lines_alpha", None,
                                                        "view.points_alpha"))()
    rows = [(b.channel, b.target, b.layer, b.feedback) for b in withf
            if b.kind == "cc" and b.number == FADER]
    assert rows == [(0, "view.lines_alpha", "preset", None),
                    (2, "view.points_alpha", "preset", None)]
    assert [b.to_json() for b in withf if not (b.kind == "cc" and b.number == FADER)] == \
        [b.to_json() for b in plain]
    b = preset.track_fader(8, "dream.mix")
    assert (b.source, b.op, b.layer, b.feedback, b.pickup) == (
        f"cc:7:{FADER}", "abs", "preset", None, True)


# -------------------------------------------------- a preset with fader rows

def test_a_preset_with_fader_rows_lights_s1_s8_and_drives_them(rig):
    """The fixture binds S1–S8 on its desk: it loads with no note and no
    dirt, all eight light (the on-screen desk's rule) on the preset layer,
    and each fader drives its own param once picked up. Under SHIFT the same
    faders are the audio strip."""
    lib = load_fixture(rig)
    t = rig.midi.table
    assert lib.current("presets") == "FADERS"
    assert lib.presets.desk_notes == []
    assert not lib.is_dirty("presets")
    assert faders_lit(t) == dict(zip(GLYPHS, TARGETS))
    for k, pid in enumerate(TARGETS):
        push(rig, cc(FADER, at(rig, pid), channel=k))           # picked up where it is
        push(rig, cc(FADER, 100, channel=k))
        assert rig.reg[pid].norm == pytest.approx(100 / 127, abs=0.02), pid
    shift(rig)
    assert faders_lit(t) == dict(zip(GLYPHS, SHIFT_TARGETS))
    shift(rig)
    assert faders_lit(t) == dict(zip(GLYPHS, TARGETS))


def test_the_fader_rows_round_trip_through_save_and_load(rig):
    """Saved, the preset's file holds the eight fader rows as the fixture
    had them; loaded back, the desk is the same and nothing is noted."""
    lib = load_fixture(rig)
    t = rig.midi.table
    before = sorted(json.dumps(b.to_json(), sort_keys=True) for b in t.desk())
    path = lib.presets.save_as("FADERS 2")
    doc = json.loads(Path(path).read_text())
    want = json.loads((FIXTURES / "faders.json").read_text())["desk"]
    assert sorted(preset._norm_rows(doc["desk"])) == sorted(preset._norm_rows(want))
    lib.presets.load("FADERS 2")
    rig.midi.poll()
    assert lib.presets.desk_notes == []
    assert sorted(json.dumps(b.to_json(), sort_keys=True) for b in t.desk()) == before
    assert faders_lit(t) == dict(zip(GLYPHS, TARGETS))


def test_a_fader_picks_up_its_own_param_across_the_latch(rig):
    """D7 across SHIFT: S1 set on the preset layer, then SHIFT latched —
    the same fader, now band.0.post's, does not jump the band to where the
    fader stands; it moves the band once it reaches the band's value. Back
    on the preset layer, the opacity waits likewise."""
    load_fixture(rig)
    reg = rig.reg
    push(rig, cc(FADER, at(rig, "view.points_alpha")), cc(FADER, 120))
    assert reg["view.points_alpha"].norm == pytest.approx(120 / 127, abs=0.01)
    shift(rig)
    band = reg["band.0.post"].norm
    assert abs(band - 120 / 127) > 0.05                    # the band is somewhere else
    push(rig, cc(FADER, 118))                              # moved, not across the band
    assert reg["band.0.post"].norm == pytest.approx(band)
    here = at(rig, "band.0.post")
    push(rig, cc(FADER, here))                             # reaches it: caught
    push(rig, cc(FADER, here + 3))
    assert reg["band.0.post"].norm == pytest.approx((here + 3) / 127, abs=0.02)
    assert reg["view.points_alpha"].norm == pytest.approx(120 / 127, abs=0.01)
    here += 3
    shift(rig)                                             # back: the opacity waits
    push(rig, cc(FADER, here + 1 if here < 100 else here - 1))
    assert reg["view.points_alpha"].norm == pytest.approx(120 / 127, abs=0.01)


def test_a_fader_on_its_value_when_the_layer_switches_is_caught_at_once(rig):
    """A fader that already stands on the other layer's value catches on
    its first move: no dead travel."""
    load_fixture(rig)
    reg = rig.reg
    band = at(rig, "band.0.post")
    push(rig, cc(FADER, at(rig, "view.points_alpha")), cc(FADER, band))
    shift(rig)
    push(rig, cc(FADER, band + 2 if band < 120 else band - 2))
    assert reg["band.0.post"].norm == pytest.approx(
        (band + 2 if band < 120 else band - 2) / 127, abs=0.02)


def test_a_power_up_forgets_where_a_fader_was_on_every_layer(rig):
    """Review of PR #180: a fader moved while the cable was out must not
    read as a crossing. S1 caught under SHIFT at 110; the band set back to
    0.5 from the panel; a power-up; the fader pulled to ~10 while unplugged;
    SHIFT latched: the first move to 12 leaves the band alone (no position
    is known, so only an on-value catch counts). The same for MASTER, an
    invariant fader, through the power-up alone."""
    reg = rig.reg
    band, gain = reg["band.0.post"], reg["master.gain"]
    shift(rig)
    band.set_norm(0.5)
    gain.set_norm(0.5)
    rig.midi.poll()
    push(rig, cc(FADER, 64), cc(FADER, 110), cc(apc40.CC_MASTER, 64),
         cc(apc40.CC_MASTER, 110))
    assert band.norm == pytest.approx(110 / 127, abs=0.01)
    assert gain.norm == pytest.approx(110 / 127, abs=0.01)
    shift(rig)                                             # back to the preset layer
    band.set_norm(0.5)
    gain.set_norm(0.5)
    rig.midi.poll()
    rig.midi._enter()                                      # a power-up (a reconnect)
    shift(rig)
    push(rig, cc(FADER, 12), cc(apc40.CC_MASTER, 12))      # moved while unplugged
    assert band.norm == pytest.approx(0.5)
    assert gain.norm == pytest.approx(0.5)
    push(rig, cc(FADER, 64), cc(FADER, 70))                # brought to the value: caught
    assert band.norm == pytest.approx(70 / 127, abs=0.01)


def test_a_track_fader_is_learnable_on_the_preset_layer(rig):
    """Decision 17: S1 is the preset's, so the on-screen desk offers it and
    a desk learn on CC 7 lands a preset-layer pickup row with no ring."""
    t, m = rig.midi.table, rig.midi
    s1 = next(c for c in apc40.LAYOUT if c.glyph == "S1")
    assert t.layer == "preset" and ui_desk.mappable(t, s1) is None
    m.learner.arm("view.lines_alpha", "desk")
    push(rig, cc(FADER, 40))
    (b,) = [x for x in t.desk() if x.target == "view.lines_alpha"]
    assert (b.source, b.op, b.layer, b.pickup) == (f"cc:0:{FADER}", "abs", "preset", True)
    assert (b.feedback, b.ring) == (None, 0)               # no light: the map's fader row
    assert faders_lit(t)["S1"] is not None
    shift(rig)
    assert ui_desk.mappable(t, s1) is not None             # SHIFT up: the session's layer


# ------------------------------------------------------------- the migration

def test_an_older_session_file_moves_the_fader_rows_to_shift_once(tmp_path):
    """A `bindings.json` from before C2 holds the eight audio rows on the
    track faders with no layer (invariant): its next load gives each the
    SHIFT layer, notes it, keeps a backup and writes the file back once; the
    next load is quiet. A fader row the owner changed stays invariant."""
    old = []
    for b in Bindings.factory().bindings:
        if not routing.is_session_row(b):
            continue
        if b.kind == "cc" and b.number == FADER and b.is_midi:
            b = Binding.from_json({**b.to_json(), "layer": None})
        old.append(b)
    assert sum(1 for b in old if b.kind == "cc" and b.number == FADER
               and b.layer is None) == 8
    folder = tmp_path / "a"
    folder.mkdir()
    path = bindings_path(folder)
    Bindings(old, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    for k, pid in enumerate(SHIFT_TARGETS):
        (b,) = t.route("cc", k, FADER)
        assert (b.target, b.layer) == (pid, "global")
        assert any(n.startswith(f"moved cc:{k}:{FADER} → {pid} to the SHIFT layer")
                   for n in t.notes)
    assert (folder / "bindings.json.bak-v3").exists()
    assert t.said.startswith("bindings.json updated (8 rows changed)")
    rows = json.loads(path.read_text())["bindings"]
    assert all(r.get("layer") == "global" for r in rows
               if r["source"].endswith(f":{FADER}") and r["source"].startswith("cc:"))
    assert path.read_text() == Bindings.factory(path=path).dumps()
    again = Bindings.load(path, legacy_midi=None)
    assert again.notes == []
    # an owner's own row on S1 stays the session's on both layers
    mine = Binding(f"cc:0:{FADER}", "view.speed", "abs", ring=0)
    folder = tmp_path / "b"
    folder.mkdir()
    path = bindings_path(folder)
    Bindings([b for b in old if b.source != mine.source] + [mine], path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    (b,) = t.route("cc", 0, FADER)
    assert (b.target, b.layer) == ("view.speed", None)


def test_a_preset_row_on_an_owners_invariant_fader_drops_with_the_d6_note(rig):
    """Where the owner kept a fader invariant, a preset's row on it is
    dropped with D6's note, as on any invariant control."""
    t = rig.midi.table
    for b in [x for x in t.bindings if x.source == f"cc:0:{FADER}"]:
        t.bindings.remove(b)
    t.bindings.append(Binding(f"cc:0:{FADER}", "view.speed", "abs", ring=0))
    lib = load_fixture(rig)
    assert lib.presets.desk_notes == [
        (f"dropped cc:0:{FADER} → view.points_alpha: that control is invariant, the "
         "session's (plan 13 D6)")]


# ------------------------------------------------------- lines and points opacity

def test_lines_and_points_opacity_are_performance_params_at_one(rig):
    """Decision 24: each new opacity defaults to the picture as it was."""
    for pid in ("view.lines_alpha", "view.points_alpha"):
        p = rig.reg[pid]
        assert p.value == 1.0
        assert getattr(ViewState(), pid.partition(".")[2]) == 1.0
        assert (p.lo, p.hi) == (0.0, 1.0)
        assert p.modulatable and p.persist
        assert not routing.is_session_id(pid)
        assert routing.base_refusal(pid, rig.reg) is None


@pytest.fixture(scope="module")
def ctx():
    moderngl = pytest.importorskip("moderngl")
    try:
        c = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    yield c
    c.release()


def test_an_opacity_at_zero_takes_its_layer_away_and_one_changes_nothing(ctx):
    from hyperspace.render import render_offscreen

    def frame(**kw):
        s = ViewState(shape=3, ang=[0.3, 0.7, 1.1, 0.5, 0.9, 1.3], yaw=0.4, pitch=0.25, **kw)
        return render_offscreen(s, 320, 240, ctx=ctx, t_now=0.0)

    both = frame()
    assert (frame(lines_alpha=1.0, points_alpha=1.0) == both).all()
    lines_only = frame(points=False)
    points_only = frame(lines=False)
    assert (frame(points_alpha=0.0) == lines_only).all()
    assert (frame(lines_alpha=0.0) == points_only).all()
    half = frame(points=False, lines_alpha=0.5)
    assert 0 < int(half.sum()) < int(lines_only.sum())
