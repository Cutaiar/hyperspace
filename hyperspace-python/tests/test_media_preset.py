"""Plan 32 T5 — the media channels in the preset: the `media` section (the
bins), the channel params, `hyperspace.preset/4` only when a preset uses
them, and the old `view.bmp_*` dropped with a note.

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
    assert sorted(p.id for p in reg if p.id.startswith("backdrop.")) == [
        "backdrop.alpha", "backdrop.channel", "backdrop.history"]
    assert reg["backdrop.history"].kind is Kind.TOGGLE
    views = sorted(p.id for p in reg if p.id.startswith("view.media"))
    assert views == ["view.media", "view.media_alpha", "view.media_amp", "view.media_mode",
                     "view.media_rate", "view.media_scale"]
    off = ["off", *CHANNELS]
    assert reg["view.media"].choices == off and reg["backdrop.channel"].choices == off
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
def test_preset_without_media_is_unchanged(tmp_path, name):
    """A preset that uses no media is written byte for byte as the base
    wrote it (fixtures/media-preset-base/, saved by the writer before T5)
    but for the six `view.bmp_*` values this build no longer has — and the
    values of the effect files added since (plan 32 T7's displace and blend:
    a preset holds every effect's params, as it did each file before them)."""
    r = boot(tmp_path)
    assert r.presets.load(name) == []
    want = "".join(line for line in (BASE / f"{name}.json").read_text().splitlines(True)
                   if not line.startswith('  "view.bmp_'))
    got = save_text(r, name).splitlines(True)
    assert any(line.startswith(LATER_EFFECTS) for line in got)
    assert "".join(line for line in got if not line.startswith(LATER_EFFECTS)) == want
    assert preset.uses_media(r.presets.document(name)) is False


def test_media_preset_is_v4(rig):
    doc = rig.presets.document("x")
    assert doc["schema"] == preset.SCHEMA and preset.MEDIA_KEY not in doc
    rig.reg.media.assign("a", 0, "shared:loops/tunnel.mp4")
    doc = rig.presets.document("x")
    assert doc["schema"] == preset.MEDIA_SCHEMA == "hyperspace.preset/4"
    assert doc[preset.MEDIA_KEY] == {"channels": {"a": ["shared:loops/tunnel.mp4"]}}
    assert doc["values"]["media.a.slot"] == 0          # a /4 file holds every value
    rig.reg.media.assign("a", 0, None)
    assert rig.presets.document("x")["schema"] == preset.SCHEMA
    # a value away from its default is enough, of each family
    for pid, v in (("media.b.rate", 2.0), ("backdrop.channel", 3),
                   ("view.media_alpha", 0.5), ("backdrop.history", True)):
        was = rig.reg[pid].value
        rig.reg[pid].set(v)
        assert rig.presets.document("x")["schema"] == preset.MEDIA_SCHEMA, pid
        rig.reg[pid].set(was)
    assert rig.presets.document("x")["schema"] == preset.SCHEMA


def test_uses_media_rule():
    assert not preset.uses_media({"values": {"view.bright": 2.0}})
    assert not preset.uses_media({"values": {"media.a.slot": 0, "view.media_scale": 0.9},
                                  "media": {"channels": {"a": [None, None]}}})
    assert preset.uses_media({"media": {"channels": {"a": [None, "local:x.png"]}}})
    assert preset.uses_media({"values": {"view.media": 2}})
    assert preset.uses_media({"values": {"media.h.loop": 1}})


def test_uses_media_counts_names_in_rows():
    """A preset whose only media is a row naming a media-family id or a
    channel node — a route, a modifier's input, a macro's subscriber, a
    graph wire — is /4: an older build would drop that row silently."""
    assert preset.uses_media({"routes": [{"source": "lfo:0", "target": "media.a.pos",
                                          "op": "push", "value": 0.2}]})
    assert preset.uses_media({"routes": [{"source": "param:backdrop.alpha",
                                          "target": "bridge:3", "op": "send"}]})
    assert preset.uses_media({"macros": {"macro.1": {"subs": [{"base": "backdrop.alpha",
                                                               "from": 0, "to": 1}]}}})
    assert preset.uses_media({"macros": {"macro.2": {"subs": [
        {"depth": {"source": "hand:right.y", "target": "view.media_alpha"},
         "from": 0, "to": 1}]}}})
    assert preset.uses_media({"modifiers": [{"id": "mod.1", "kind": "smooth",
                                             "in": ["param:media.b.rate"]}]})
    assert preset.uses_media({"graph": {"nodes": [], "wires": [{"from": "media.a",
                                                                "to": "acid.aux"}]}})
    # rows that name no media id leave the preset /2
    assert not preset.uses_media({
        "routes": [{"source": "lfo:0", "target": "camera.zoom", "op": "push"}],
        "modifiers": [{"id": "mod.1", "kind": "smooth", "in": ["hand:right.energy", None]}],
        "macros": {"macro.1": {"subs": [{"base": "dream.decay", "from": 0, "to": 1}]}},
        "graph": {"nodes": [], "wires": [{"from": "hands.2", "to": "output.2.hands"}]}})
    # a malformed section is not media, and never raises
    assert not preset.uses_media({"routes": "x", "macros": [], "graph": {"wires": 3},
                                  "modifiers": [7, {"in": "media.a.pos"}]})


def test_preset_whose_only_media_is_a_route_or_macro_is_v4(rig):
    from test_presets import put
    put(rig.home, "LFOPOS", routes=[{"source": "lfo:0", "target": "media.a.pos",
                                     "op": "push", "value": 0.2}])
    assert rig.presets.load("LFOPOS") == []
    doc = rig.presets.document("LFOPOS")
    assert doc["schema"] == preset.MEDIA_SCHEMA
    assert any(r["target"] == "media.a.pos" for r in doc["routes"])
    put(rig.home, "MACROALPHA", macros={"macro.1": {"subs": [
        {"base": "backdrop.alpha", "from": 0, "to": 1}]}})
    assert rig.presets.load("MACROALPHA") == []
    assert rig.presets.document("MACROALPHA")["schema"] == preset.MEDIA_SCHEMA
    put(rig.home, "PLAIN", routes=[{"source": "lfo:0", "target": "camera.zoom",
                                    "op": "push", "value": 0.1}])
    assert rig.presets.load("PLAIN") == []
    assert rig.presets.document("PLAIN")["schema"] == preset.SCHEMA


def test_bins_round_trip(rig, tmp_path):
    m = rig.reg.media
    m.assign("a", 0, "shared:loops/tunnel.mp4")
    m.assign("a", 1, "camera:FaceTime HD Camera")
    m.assign("d", 7, "file:/Users/x/pic.heic")
    rig.reg["media.a.slot"].set(1)
    rig.reg["view.media"].set(1)
    path = rig.presets.save_as("MEDIA")
    text = path.read_text()
    assert '"schema": "hyperspace.preset/4"' in text
    assert '  "a": ["shared:loops/tunnel.mp4", "camera:FaceTime HD Camera"]' in text
    want = m.to_json()
    m.from_json({})
    rig.reg["media.a.slot"].set(0)
    assert rig.presets.load("MEDIA") == [] and rig.presets.notes == []
    assert m.to_json() == want and rig.reg["media.a.slot"].value == 1
    assert rig.view.media == 1
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
    assert rig.reg["backdrop.channel"].value == 2
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
    assert doc["values"]["view.media_alpha"] == 0.3 and doc["schema"] == preset.MEDIA_SCHEMA
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
