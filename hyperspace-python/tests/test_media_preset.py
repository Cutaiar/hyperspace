"""Plan 32 T5 — the media channels in the preset: the `media` section (the
bins), the channel params, and the old `view.bmp_*` dropped with a note.
Row 394: every save is `hyperspace.preset/6` with the section and every
media value (plan 32's "/4 only when a preset uses them" is gone with the
ladder).

Rigs are test_presets.boot / test_undo.boot (app.main's order on a tmp
home); the registry's own `MediaState` (`reg.media`) is handed a fake
resolver and opener from test_media_channels, so nothing is decoded."""

import json
from pathlib import Path

import pytest
from test_media_channels import FakeOpener, Here
from test_presets import boot

from hyperspace import preset
from hyperspace.media.channels import CHANNELS, MediaState
from hyperspace.params import Kind, build_registry

BASE = Path(__file__).parent / "fixtures" / "media-preset-base"


@pytest.fixture()
def rig(tmp_path):
    return boot(tmp_path)


def save_text(r, name):
    return preset.dumps(r.presets.document(name))


def test_channel_params_registered(rig):
    reg = rig.reg
    media = [p.id for p in reg if p.id.startswith("media.")]
    assert len(media) == 48
    for c in CHANNELS:
        slot = reg[f"media.{c}.slot"]
        assert slot.kind is Kind.CONTINUOUS and slot.integer and (slot.lo, slot.hi) == (0, 15)
        assert reg[f"media.{c}.fit"].choices == ["cover", "contain", "stretch"]
        assert (reg[f"media.{c}.rate"].lo, reg[f"media.{c}.rate"].hi) == (-4.0, 4.0)
        assert (reg[f"media.{c}.pos"].lo, reg[f"media.{c}.pos"].hi) == (0.0, 1.0)
        assert (reg[f"media.{c}.jog"].lo, reg[f"media.{c}.jog"].hi) == (-1.0, 1.0)
        assert reg[f"media.{c}.loop"].choices == ["loop", "pingpong", "once"]
        assert all(reg[f"media.{c}.{k}"].modulatable
                   for k in ("slot", "fit", "rate", "pos", "jog", "loop"))
    # (plan 33 T7: `backdrop.channel` and `view.media` retired — which
    # channel each draws is the graph's wire into `backdrop.image` /
    # `pattern.media`; plan 35 T3: and `backdrop.history`, the wire into
    # `lookback.capture`)
    assert sorted(p.id for p in reg if p.id.startswith("backdrop.")) == ["backdrop.alpha"]
    assert reg["backdrop.alpha"].kind is Kind.CONTINUOUS
    views = sorted(p.id for p in reg if p.id.startswith("view.media"))
    assert views == ["view.media_alpha", "view.media_amp", "view.media_mode",
                     "view.media_rate", "view.media_scale"]
    assert reg["view.media_alpha"].label == "Media alpha"
    # of the bitmap's ids only the factory knob 7's is left, an alias
    assert [p.id for p in reg if p.id.startswith("view.bmp")] == ["view.bmp_alpha"]
    assert reg["view.bmp_alpha"].alias
    # the params write the registry's own MediaState
    reg["media.c.slot"].set(4)
    reg["media.c.fit"].set(2)
    assert reg.media.channels["c"].slot == 4 and reg.media.channels["c"].fit == 2
    assert rig.presets.media is reg.media


def test_build_registry_takes_a_media_state(rig):
    from types import SimpleNamespace

    from hyperspace.view import ViewState
    m = MediaState(Here())
    reg = build_registry(ViewState(), rig.control, SimpleNamespace(chain=rig.chain), media=m)
    assert reg.media is m
    reg["media.a.rate"].set(-2.0)
    assert m.channels["a"].rate == -2.0


# the effect files added after the base was written (plan 32 T7)
LATER_EFFECTS = ('  "fx.displace.', '  "fx.blend.')


@pytest.mark.parametrize("name", ["party-faces", "lfo-breathe"])
def test_preset_without_media_keeps_every_value_in_six(tmp_path, name):
    """A preset that uses no media saves `/6` (row 394) holding every value
    the base wrote (fixtures/media-preset-base/, saved by the writer before
    T5) as it wrote it — but the six `view.bmp_*` this build no longer has
    and the retired ids (an effect's order and target, `backdrop.history`:
    the wires say them) — beside the media family at its defaults and an
    empty `media` section."""
    from hyperspace import graphmigrate as M

    r = boot(tmp_path)
    assert r.presets.load(name) == []
    base = json.loads((BASE / f"{name}.json").read_text())
    doc = json.loads(save_text(r, name))
    assert doc["schema"] == preset.WIRED_SCHEMA
    kept = {k: v for k, v in base["values"].items()
            if not k.startswith("view.bmp_") and not M.retired(k)}
    assert {k: doc["values"][k] for k in kept} == kept
    assert any(k.startswith(LATER_EFFECTS[0].strip(' "')) for k in doc["values"])
    assert doc[preset.MEDIA_KEY] == {"channels": {}}
    assert "media.a.slot" in doc["values"] and "view.media_alpha" in doc["values"]


def test_a_media_preset_and_one_without_are_both_six(rig):
    """Row 394: with media or without, the save is `/6`, with the bins (an
    empty section when none is assigned) and every media-family value."""
    doc = rig.presets.document("x")
    assert doc["schema"] == preset.WIRED_SCHEMA == "hyperspace.preset/6"
    assert doc[preset.MEDIA_KEY] == {"channels": {}}
    rig.reg.media.assign("a", 0, "shared:loops/tunnel.mp4")
    doc = rig.presets.document("x")
    assert doc["schema"] == preset.WIRED_SCHEMA
    assert doc[preset.MEDIA_KEY] == {"channels": {"a": ["shared:loops/tunnel.mp4"]}}
    assert doc["values"]["media.a.slot"] == 0
    for pid, v in (("media.b.rate", 2.0), ("view.media_alpha", 0.5),
                   ("backdrop.alpha", 0.5)):
        rig.reg[pid].set(v)
        assert rig.presets.document("x")["values"][pid] == v, pid


def test_a_row_on_a_media_param_survives_the_save(rig):
    """A route, a macro subscriber or a desk row on a media-family param is
    saved with the preset (`/6`, as every save)."""
    from test_presets import put
    put(rig.home, "LFOPOS", routes=[{"source": "lfo:0", "target": "media.a.pos",
                                     "op": "push", "value": 0.2}])
    assert rig.presets.load("LFOPOS") == []
    doc = rig.presets.document("LFOPOS")
    assert doc["schema"] == preset.WIRED_SCHEMA
    assert any(r["target"] == "media.a.pos" for r in doc["routes"])
    put(rig.home, "MACROALPHA", macros={"macro.1": {"subs": [
        {"base": "backdrop.alpha", "from": 0, "to": 1}]}})
    assert rig.presets.load("MACROALPHA") == []
    doc = rig.presets.document("MACROALPHA")
    assert doc["schema"] == preset.WIRED_SCHEMA
    assert doc["macros"]["macro.1"]["subs"][0]["base"] == "backdrop.alpha"
    put(rig.home, "DESKALPHA", desk=[{"source": "cc:0:48", "target": "backdrop.alpha",
                                      "op": "set"}])
    assert rig.presets.load("DESKALPHA") == []
    doc = rig.presets.document("DESKALPHA")
    assert doc["schema"] == preset.WIRED_SCHEMA
    assert any(r.get("target") == "backdrop.alpha" for r in doc["desk"])
    put(rig.home, "PLAIN", routes=[{"source": "lfo:0", "target": "camera.zoom",
                                    "op": "push", "value": 0.1}])
    assert rig.presets.load("PLAIN") == []
    assert rig.presets.document("PLAIN")["schema"] == preset.WIRED_SCHEMA


def test_bins_round_trip(rig, tmp_path):
    m = rig.reg.media
    m.assign("a", 0, "shared:loops/tunnel.mp4")
    m.assign("a", 1, "camera:FaceTime HD Camera")
    m.assign("d", 7, "file:/Users/x/pic.heic")
    rig.reg["media.a.slot"].set(1)
    path = rig.presets.save_as("MEDIA")
    text = path.read_text()
    assert '"schema": "hyperspace.preset/6"' in text
    assert '  "a": ["shared:loops/tunnel.mp4", "camera:FaceTime HD Camera"]' in text
    want = m.to_json()
    m.from_json({})
    rig.reg["media.a.slot"].set(0)
    assert rig.presets.load("MEDIA") == [] and rig.presets.notes == []
    assert m.to_json() == want and rig.reg["media.a.slot"].value == 1
    # a preset without the section empties every bin
    rig.presets.load("party-faces")
    assert m.to_json() == {"channels": {}}


def test_v2_and_v4_both_load(rig):
    from test_presets import put
    put(rig.home, "OLD", values={"view.bright": 2.0})
    put(rig.home, "NEW", schema=preset.MEDIA_SCHEMA, values={"backdrop.channel": 2},
        media={"channels": {"b": ["shared:x.png"]}})
    assert rig.presets.load("OLD") == []
    assert rig.reg["view.bright"].value == 2.0
    assert rig.presets.load("NEW") == [] and rig.presets.notes == []
    # (plan 33 T7: the retired choice is read as its wire, never an unknown
    # id — plan 35 V2: in the new ids)
    from hyperspace import graph as G
    assert G.Wire("channel.b", "backdrop.image") in rig.presets.graph.spec.wires
    assert "backdrop.channel" not in rig.reg
    assert rig.reg.media.channels["b"].bin[0] == "shared:x.png"


def test_bmp_file_dropped_with_note(rig):
    from test_presets import put
    put(rig.home, "BMP", values={"view.bmp_file": "/x.png", "view.bmp_alpha": 0.4,
                                 "view.bright": 1.5})
    assert rig.presets.load("BMP") == []
    assert rig.presets.notes == [
        "bitmap file /x.png is no longer read: put it on a media channel"]
    assert rig.reg["view.bright"].value == 1.5
    put(rig.home, "BMP0", values={"view.bmp_file": "", "view.bmp_scale": 0.3})
    assert rig.presets.load("BMP0") == [] and rig.presets.notes == []


def test_bmp_alpha_is_an_alias_of_media_alpha(rig):
    """The factory desk's knob 7 (`cc:0:54 → view.bmp_alpha`) keeps its
    meaning: the alias reads and writes view.media_alpha, is never saved
    as its own value, and an old preset's value lands on the real one."""
    from test_presets import put
    reg = rig.reg
    alias, real = reg["view.bmp_alpha"], reg["view.media_alpha"]
    assert reg.real(alias) is real and not alias.persist and not alias.modulatable
    alias.set(0.3)
    assert real.value == 0.3 and rig.view.media_alpha == 0.3
    assert "view.bmp_alpha" not in reg.snapshot()
    assert reg.snapshot()["view.media_alpha"] == 0.3
    doc = rig.presets.document("x")
    assert "view.bmp_alpha" not in doc["values"]
    assert doc["values"]["view.media_alpha"] == 0.3 and doc["schema"] == preset.WIRED_SCHEMA
    put(rig.home, "OLDALPHA", values={"view.bmp_alpha": 0.25})
    assert rig.presets.load("OLDALPHA") == [] and rig.presets.notes == []
    assert real.value == 0.25
    put(rig.home, "BOTH", values={"view.bmp_alpha": 0.25, "view.media_alpha": 0.6})
    assert rig.presets.load("BOTH") == []
    assert real.value == 0.6                       # the file's own new id wins
    # a factory preset's knob 7 row lands on the real param
    rig.presets.load("party-faces")
    knob =[b for b in rig.router.table.desk() if b.target == "view.bmp_alpha"]
    assert knob and all(reg.real(reg[b.target]) is real for b in knob)


def test_bad_id_in_bin_is_a_note(rig):
    from test_presets import put
    put(rig.home, "BAD", schema=preset.MEDIA_SCHEMA,
        media={"channels": {"a": ["shared:ok.png", "nonsense", None, "local:y.png"]}})
    assert rig.presets.load("BAD") == []
    assert rig.reg.media.channels["a"].bin[:4] == ["shared:ok.png", None, None, "local:y.png"]
    assert len(rig.presets.notes) == 1 and "'nonsense'" in rig.presets.notes[0]


def test_bins_change_lights_the_dirty_dot(rig):
    rig.presets.save_as("CLEAN")
    rig.presets.load("CLEAN")
    assert not rig.lib.is_dirty("presets")
    rig.reg.media.assign("e", 2, "local:a.png")
    assert rig.lib.is_dirty("presets")


def test_undo_of_a_slot_change_restores_the_source(tmp_path):
    from test_undo import boot as undo_boot
    from test_undo import frames, settle
    r = undo_boot(tmp_path / "home")
    m = r.reg.media
    op = FakeOpener()
    m.resolver, m.opener = Here("shared:x.png", "shared:y.png"), op
    m.assign("a", 0, "shared:x.png")
    m.assign("a", 1, "shared:y.png")
    m.poll(1 / 60, 0.0)
    assert m.channels["a"].source.sid == "shared:x.png"
    settle(r)
    r.reg["media.a.slot"].set(1)
    settle(r)
    m.poll(1 / 60, 1.0)
    assert m.channels["a"].source.sid == "shared:y.png"
    assert r.undo.undo()
    frames(r)
    m.poll(1 / 60, 2.0)
    assert r.reg["media.a.slot"].value == 0
    assert m.channels["a"].source.sid == "shared:x.png"


def test_undo_of_a_load_puts_the_bins_back(tmp_path):
    from test_presets import put
    from test_undo import boot as undo_boot
    from test_undo import frames, settle
    r = undo_boot(tmp_path / "home")
    m = r.reg.media
    m.assign("a", 0, "shared:before.png")
    settle(r)
    put(r.home, "NEW", schema=preset.MEDIA_SCHEMA,
        media={"channels": {"a": ["shared:after.png"]}})
    r.presets.load("NEW")
    frames(r)
    assert m.channels["a"].bin[0] == "shared:after.png"
    assert r.undo.undo()
    frames(r)
    assert m.channels["a"].bin[0] == "shared:before.png"
    json.dumps(m.to_json())
