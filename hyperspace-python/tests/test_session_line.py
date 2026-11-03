"""Plan 44 D3 — the session / performance line made mechanical (schema `/10`).

What crosses the line, and how each half is held:

- the registry: `params.build_session` → the rig's `SessionRegistry`, one
  for every deck; `build_performance` → a deck's `Registry`, which holds the
  session's `Param` objects by reference (tests/test_params.py proves the
  registry half);
- the table: `routing.SessionTable` (the session rows, `bindings.json`, the
  latch, the slew, the pad's feel, the rig facts) and a deck's `Bindings`
  holding its rows by reference beside the deck's own;
- the media: `media.channels.MediaSources` (resolver, opener, closer, the
  mixer) shared, a deck's `Channels` (the eight channels) its own;
- the library: what is loaded and the dirty dot are the `Presets`' own;
- the look made whole: the hands' and clouds' looks and the bus cuts are
  the preset's — an old (`/2`) show's are handed to every old preset a
  load reads while it is open, and the migration writes them into every
  preset (REVIEW.md: an old preset and an old show opened end to end, not
  only the converter).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from test_presets import boot

from hyperspace import graph as G
from hyperspace import graphmigrate, preset
from hyperspace.library import LOOK_BACKUP, PROJECT_SUFFIX, PROJECT_V2, PROJECTS
from hyperspace.media.channels import Channels, MediaSources, MediaState, NoResolver
from hyperspace.routing import Binding, Bindings, SessionTable
from hyperspace.routing_sources import Sources

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "corpus" / "presets"
CUT = G.bus_wire(2, "image")
LOOK = {"ghost.alpha": 0.25, "ghost.style": 2, "cloud.size": 3.5}


# ---------------------------------------------------------------- the table


def test_two_decks_tables_hold_the_session_rows_by_reference():
    """A second deck's table over the first's session: the session rows are
    the same `Binding` objects, first in its list; a key row learned on one
    deck is the other's at once; the latch, the slew and the pad's feel are
    one value; each deck's routes and preset layer are its own; the file
    holds the session rows once, whichever deck writes it; the sources
    follow the session table once."""
    a = Bindings.factory()
    s = a.session
    assert isinstance(s, SessionTable) and s.tables == [a]
    b = Bindings([Binding("hand:7", "view.speed", "push", 0.3)], session=s)
    assert b.session is s and s.tables == [a, b]
    shared = [x for x in a.bindings if x.op not in ("push", "position") and x.layer != "preset"]
    assert all(any(y is x for y in b.bindings) for x in shared)
    assert b.routes() and not a.routes()
    assert not [x for x in b.bindings if x.is_midi and x.layer == "preset"]
    key = Binding("key:F9", "view.lines", "toggle")
    a.bind(key, write=False)
    assert any(x is key for x in b.bindings)
    a.set_layer("global")
    assert b.layer == "global" and b.layer_serial == a.layer_serial
    b.slew = 0.1
    assert a.slew == 0.1 and s.slew == 0.1
    assert a.to_json() == s.to_json() == {**b.to_json()}
    src = Sources()
    src.follow(a)
    src.follow(b)
    assert src.tables == [s]
    a.remove(key)
    assert not any(x is key for x in b.bindings)


def test_the_session_table_reads_and_writes_the_file(tmp_path):
    """`SessionTable.load` is the file's one door (the old migrations and the
    backup through it); `write` writes the session rows only."""
    path = tmp_path / "bindings.json"
    t = SessionTable.load(path, legacy_midi=None)
    assert isinstance(t, Bindings) and t.session.path == path
    t.add(Binding("hand:7", "view.speed", "push", 0.3))
    t.write()
    doc = json.loads(path.read_text())
    assert all(x.get("op") not in ("push", "position") for x in doc["bindings"])
    assert SessionTable.backup is not None and SessionTable.migrate_v1 is not None


# ---------------------------------------------------------------- the media


def test_two_decks_channels_read_through_one_set_of_sources():
    """`MediaSources` is the rig's (one resolver, opener, closer, mixer);
    each deck's `Channels` are its own eight; `MediaState` is the old name."""
    a = Channels(resolver=NoResolver())
    b = Channels(sources=a.sources)
    assert MediaState is Channels and isinstance(a.sources, MediaSources)
    assert b.resolver is a.resolver and b.live_mixer() is a.live_mixer()
    assert b.closer is a.closer and b.opener is a.opener
    assert b.channels["a"] is not a.channels["a"]
    a.channels["a"].slot = 3.0
    assert b.channels["a"].slot == 0.0


def test_a_media_state_from_before_the_split_finds_its_sources():
    """A hot reload re-classes an old `MediaState` (its resolver and mixer on
    itself): the first read moves them onto its sources, nothing lost."""
    old = Channels.__new__(Channels)
    res = NoResolver()
    old.__dict__.update(resolver=res, channels={}, _closed=False)
    assert old.resolver is res and isinstance(old.sources, MediaSources)
    assert "resolver" not in old.__dict__


# ---------------------------------------------------------------- an old show and an old preset


def _old_show(home: Path, **extra) -> Path:
    path = home / PROJECTS / f"rig{PROJECT_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"schema": PROJECT_V2, "name": "rig", "bank": [None] * 8,
           "session": {"tempo.bpm": 128.0, "ghost.mirror": True, **LOOK},
           "rig": {"cut": [CUT.to_json()]}, **extra}
    path.write_text(json.dumps(doc, indent=1) + "\n")
    return path


def _old_preset(home: Path, name: str = "OLD", folder: str = "") -> Path:
    """dial as a `/9` (before the look was the preset's): no hands' or
    clouds' values, a module label."""
    doc = json.loads((CORPUS / "dial.json").read_text())
    doc["schema"] = graphmigrate.EYE_SCHEMA
    doc["name"] = name
    doc["values"] = {k: v for k, v in doc["values"].items()
                     if not k.startswith(("ghost.", "cloud."))}
    doc["modules"] = {"dream": "wake"}
    path = home / "presets" / folder / f"{name.lower()}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(preset.dumps(doc))
    return path


def test_an_old_preset_opened_with_an_old_show_takes_its_look_and_cuts_end_to_end(tmp_path):
    home = tmp_path / "home"
    show = _old_show(home)
    before = show.read_bytes()
    _old_preset(home)
    rig = boot(home, show="rig")
    pr, reg, pre = rig.lib.project, rig.reg, rig.presets
    # the show: its look and cuts read out, its mirror the room's
    assert pr.old_look == LOOK and pr.old_cuts.cut == {CUT}
    assert reg["ghost.mirror"].value is True and reg["tempo.bpm"].value == 128.0
    assert not pr.is_dirty()
    # the old preset, loaded with the show open: the show's look and cuts
    assert pre.load("OLD") == []
    assert reg["ghost.alpha"].value == 0.25 and reg["cloud.size"].value == 3.5
    assert reg["ghost.style"].value == 2
    assert pre.bus.cut == {CUT} and G.rig_of(pre).cut == {CUT}
    assert rig.lib.current("dream") is None                   # no module label
    assert not rig.lib.is_dirty("presets")
    doc = pre.document("OLD")
    assert doc["schema"] == "hyperspace.preset/10" and "modules" not in doc
    assert doc[preset.BUS_KEY] == {"cut": [CUT.to_json()]}
    assert doc["values"]["ghost.alpha"] == 0.25 and "ghost.mirror" not in doc["values"]
    # the show saved: /3, the rig's session, kept as /2 beside it
    path = pr.save()
    saved = json.loads(path.read_text())
    assert saved["schema"] == "hyperspace.project/3" and "rig" not in saved
    assert saved["session"]["ghost.mirror"] is True and saved["session"]["tempo.bpm"] == 128.0
    assert not any(k in saved["session"] for k in LOOK)
    assert (path.parent / f"{path.name}.bak-v{LOOK_BACKUP}").read_bytes() == before
    # a /10 preset: its own look and no cut — a load moves the hands' look
    pre.load("DIAL")
    assert pre.bus == G.RigWires() and reg["ghost.alpha"].value == 0.6
    assert reg["ghost.mirror"].value is True                  # the room's stays
    # a fresh launch on the /3 show: the old look still from its backup
    again = boot(home, show="rig")
    assert again.lib.project.old_look == LOOK and again.lib.project.old_cuts.cut == {CUT}
    again.presets.load("OLD")
    assert again.reg["ghost.alpha"].value == 0.25 and again.presets.bus.cut == {CUT}


def test_a_cut_is_the_presets_undone_with_it_and_held_in_its_dot(tmp_path):
    """The cuts are in the preset's dirty dot and its load's undo step."""
    from test_undo import boot as undo_boot
    from test_undo import settle

    rig = undo_boot(tmp_path / "home")
    pre = rig.presets
    rig.lib.load("presets", "party-trip")
    settle(rig)
    assert not rig.lib.is_dirty("presets")
    pre.bus = pre.bus.cutting(CUT)
    assert rig.lib.is_dirty("presets")
    path = pre.save_as("cut trip")
    assert json.loads(path.read_text())["bus"] == {"cut": [CUT.to_json()]}
    settle(rig)
    rig.lib.load("presets", "party-trip")
    settle(rig)
    assert pre.bus == G.RigWires()
    assert rig.undo.undo()
    assert pre.bus.cut == {CUT} and pre.current == "cut trip"


def test_the_window_a_rig_lacks_is_asked_for():
    from hyperspace import graphview
    spec = G.read_graph({"frame": "wired", "wires": [{"from": "scene", "to": "output.4.image"}]})
    assert graphview.wanted_windows(spec, G.RigWires().cutting(G.bus_wire(6, "hands")), 2) == [
        4, 6]
    assert graphview.wanted_windows(spec, None, 4) == []
    assert "Output 4" in graphview.WINDOW_WANTED.format(n=4)


# ---------------------------------------------------------------- the migration, on a scratch copy


def _tool():
    sys.path.insert(0, str(ROOT / "tools"))
    import migrate_library
    return migrate_library


def same_picture(path, *, library=None, show=None):
    return ["x"] * 8, []


def test_the_tool_writes_the_shows_look_and_cuts_into_every_preset_every_folder_down(
        tmp_path, monkeypatch, capsys):
    """tools/migrate_library.py on a scratch library (never the owner's): a
    dry run writes nothing and says the cuts; --apply backs the library up,
    rewrites every preset — folders too — as /10 with the show's look and
    cuts, and the show as /3 beside its .bak-v2-look; a second run has
    nothing to do."""
    lib = tmp_path / "Drive" / "Hyperspace"
    show = _old_show(lib)
    _old_preset(lib, "OLD")
    _old_preset(lib, "DEEP", folder="party")
    shutil.copyfile(CORPUS / "legacy6.json", lib / "presets" / "legacy6.json")   # a /10
    home = tmp_path / "machine"
    home.mkdir()
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    tool = _tool()
    tree = {p: p.read_bytes() for p in lib.rglob("*") if p.is_file()}
    assert tool.main(["--library", str(lib)], picture=same_picture) == 0
    out = capsys.readouterr().out
    assert {p: p.read_bytes() for p in lib.rglob("*") if p.is_file()} == tree
    assert "1 bus cut(s) into every preset: output.all.image → output.2.image" in out
    assert "would rewrite 2 as /10, leave 1 untouched (already /10)" in out
    assert "shows to rewrite as /3: 1 — rig.hyp.json" in out
    assert tool.main(["--library", str(lib), "--apply"], picture=same_picture) == 0
    out = capsys.readouterr().out
    backups = list(home.glob("library-backup-*"))
    assert len(backups) == 1
    for rel in ("presets/old.json", "presets/party/deep.json"):
        doc = json.loads((lib / rel).read_text())
        assert doc["schema"] == "hyperspace.preset/10", rel
        assert doc["bus"] == {"cut": [CUT.to_json()]}, rel
        assert {k: doc["values"][k] for k in LOOK} == LOOK, rel
        assert "modules" not in doc and "ghost.mirror" not in doc["values"], rel
        assert json.loads((backups[0] / rel).read_text())["schema"] == graphmigrate.EYE_SCHEMA
    assert (lib / "presets" / "legacy6.json").read_bytes() == (CORPUS / "legacy6.json").read_bytes()
    doc = json.loads(show.read_text())
    assert doc["schema"] == "hyperspace.project/3" and "rig" not in doc
    assert doc["session"] == {"tempo.bpm": 128.0, "ghost.mirror": True}
    assert (show.parent / f"{show.name}.bak-v{LOOK_BACKUP}").is_file()
    assert "rewrote 2 as /10" in out and "rewrote 1 show(s) as /3" in out
    assert tool.main(["--library", str(lib), "--apply"], picture=same_picture) == 0
    assert "rewrote 0 as /10, left 3 untouched (already /10)" in capsys.readouterr().out


def test_a_newer_file_is_refused_as_an_older_build_refuses_a_ten(tmp_path):
    """The two-Macs rule, as this build sees it: a `/11` and a `/4` show are
    refused, as a build from before refuses a `/10` and a `/3`."""
    from hyperspace.library import Library, LibraryError, Project, migrate_doc
    assert preset.VERSIONS[-1] == 10
    with pytest.raises(LibraryError, match="newer than this build"):
        migrate_doc({"schema": "hyperspace.project/4"}, "hyperspace.project")
    lib = Library(tmp_path)
    with pytest.raises(LibraryError):
        Project(lib)._take({"schema": "hyperspace.project/4", "name": "x"}, None)
