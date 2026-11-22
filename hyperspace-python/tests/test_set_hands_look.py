"""Plan 85 (row 1051): tools/set_hands_look.py — every loadable patch's ghost
hands set to the show look (`ghost.SHOW_LOOK`), an unwired hands layer given
the standard wires, the library walked every folder down, a dry run by
default and a backup before ``--apply`` writes.

Every test runs on tmp copies of tests/corpus patches; the machine home
(`HYPERSPACE_HOME`, the backup's place) is the conftest's tmp one."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "corpus" / "loadable"


def _tool():
    if "set_hands_look" in sys.modules:
        return sys.modules["set_hands_look"]
    spec = importlib.util.spec_from_file_location("set_hands_look",
                                                  ROOT / "tools" / "set_hands_look.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["set_hands_look"] = mod
    spec.loader.exec_module(mod)
    return mod


def _doc(name: str) -> dict:
    return json.loads((CORPUS / f"{name}.json").read_text())


def _library(tmp_path: Path) -> Path:
    """A library in era folders: dial with its hands wires gone, seq-demo with
    its layer drawn but into no output, big-blue-wave at #459's GLASS look
    with a second hands node, plasma-heart already at the show look, and a
    file that is no loadable patch."""
    lib = tmp_path / "lib"
    old, new = lib / "loadable" / "2025", lib / "loadable" / "2026"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    dial = _doc("dial")
    dial["graph"]["wires"] = [w for w in dial["graph"]["wires"]
                              if not w["from"].startswith("hands")]
    (old / "dial.json").write_text(json.dumps(dial, indent=1))
    seq = _doc("seq-demo")
    seq["graph"]["wires"] = [w for w in seq["graph"]["wires"]
                             if w["to"] not in ("output.all.hands", "output.all.guide")]
    (new / "seq-demo.json").write_text(json.dumps(seq, indent=1))
    wave = _doc("big-blue-wave")
    wave["values"].update({"ghost.on": True, "ghost.alpha": 0.35, "ghost.style": 8,
                           "ghost.material": 2})
    wave["graph"]["nodes"].append({"kind": "hands", "instance": 2})
    (new / "big-blue-wave.json").write_text(json.dumps(wave, indent=1))
    t = _tool()
    heart, _ = t.look(_doc("plasma-heart"))
    from hyperspace.loadable import dumps
    (lib / "loadable" / "plasma-heart.json").write_text(dumps(heart))
    (new / "notes.json").write_text('{"just": "notes"}')
    return lib


def _bytes(lib: Path) -> dict[str, bytes]:
    return {p.relative_to(lib).as_posix(): p.read_bytes()
            for p in sorted(lib.rglob("*")) if p.is_file()}


def test_the_look_sets_every_hands_node_and_leaves_the_rest():
    t = _tool()
    doc = _doc("hands-fx")
    doc["graph"]["nodes"].append({"kind": "hands", "instance": 3})
    doc["values"]["ghost.guide"] = 2
    out, moved = t.look(doc)
    for pre in ("ghost", "ghost.3"):
        assert out["values"][f"{pre}.on"] is True
        assert out["values"][f"{pre}.alpha"] == 0.5
        assert out["values"][f"{pre}.style"] == 8      # BONES
        assert out["values"][f"{pre}.material"] == 0   # PLAIN
    assert out["values"]["ghost.guide"] == 2 and "ghost.2.on" not in out["values"]
    assert doc["values"]["ghost.on"] is False          # (a copy: the input untouched)
    assert len(moved) == 3 + 4
    assert t.look(out)[1] == []


def test_a_dry_run_writes_nothing_and_says_what_it_would_do(tmp_path, capsys, monkeypatch):
    t = _tool()
    lib = _library(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    before = _bytes(lib)
    assert t.main(["--library", str(lib)]) == 0
    out = capsys.readouterr().out
    assert _bytes(lib) == before
    assert not list(home.glob("library-backup-*"))
    assert "2025/dial.json" in out and "wired: hands → hands.layer.hands" in out
    assert "2026/seq-demo.json" in out
    assert "plasma-heart.json" in out and "already the show look" in out
    assert "2026/notes.json" in out and "not a loadable patch" in out
    assert "3 would be written (2 wired)" in out and "dry run" in out


def test_apply_backs_up_then_writes_the_look_and_the_wires(tmp_path, capsys, monkeypatch):
    t = _tool()
    lib = _library(tmp_path)
    home = tmp_path / "home"
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    ml = t._migrate_library()
    monkeypatch.setattr(ml, "app_running", lambda: (False, "not open"))
    before = _bytes(lib)
    assert t.main(["--library", str(lib), "--apply"]) == 0
    out = capsys.readouterr().out
    (backup,) = home.glob("library-backup-*")
    assert _bytes(backup) == before                   # the backup is the library as it was
    assert "backup:" in out and "written: 3" in out
    for rel in ("loadable/2025/dial.json", "loadable/2026/seq-demo.json",
                "loadable/2026/big-blue-wave.json"):
        doc = json.loads((lib / rel).read_text())
        for pre in ("ghost",) + (("ghost.2",) if "wave" in rel else ()):
            assert [doc["values"][f"{pre}.{k}"] for k in ("on", "alpha", "style", "material")] \
                == [True, 0.5, 8, 0], rel
        wires = {(w["from"], w["to"]) for w in doc["graph"]["wires"]}
        assert set(t.STANDARD_WIRES) <= wires, rel
    # untouched: the one already at the look, and the file that is no patch
    for rel in ("loadable/plasma-heart.json", "loadable/2026/notes.json"):
        assert (lib / rel).read_bytes() == before[rel]
    # a second run finds nothing to do and makes no second backup
    assert t.main(["--library", str(lib), "--apply"]) == 0
    assert "0 to write" in capsys.readouterr().out
    assert len(list(home.glob("library-backup-*"))) == 1


def test_a_written_patch_loads_with_the_notes_it_had(tmp_path):
    """The written file loads in the app as it did, and lands the show look."""
    t = _tool()
    lib = _library(tmp_path)
    path = lib / "loadable" / "2025" / "dial.json"
    from hyperspace.fx import FxState
    c = t.plan(path, lib, set(FxState().files), tmp_path / "scratch")
    assert c.changed and not c.skipped and c.wires
    out = tmp_path / "out" / "dial.json"
    out.parent.mkdir()
    out.write_text(c.text)
    assert t.loads(out, tmp_path / "a", lib) == t.loads(path, tmp_path / "b", lib)


def test_apply_refuses_while_the_app_is_open(tmp_path, capsys, monkeypatch):
    t = _tool()
    lib = _library(tmp_path)
    monkeypatch.setattr(t._migrate_library(), "app_running",
                        lambda: (True, "Hyperspace is open on this Mac"))
    before = _bytes(lib)
    assert t.main(["--library", str(lib), "--apply"]) == 1
    assert "quit it first" in capsys.readouterr().out
    assert _bytes(lib) == before


def test_a_layer_that_reaches_an_output_is_left_as_it_is():
    t = _tool()
    from hyperspace.fx import FxState
    doc = _doc("big-blue-wave")
    wires = list(doc["graph"]["wires"])
    out, added = t.wire_layer(doc, set(FxState().files))
    assert added == [] and out["graph"]["wires"] == wires


def test_the_loadable_folder_itself_names_the_library(tmp_path, capsys, monkeypatch):
    """The launch sheet's shape: `set_hands_look.py "<library>/loadable"`."""
    t = _tool()
    lib = _library(tmp_path)
    monkeypatch.setenv("HYPERSPACE_HOME", str(tmp_path / "home"))
    assert t.main([str(lib / "loadable")]) == 0
    out = capsys.readouterr().out
    assert "2025/dial.json" in out and "3 would be written (2 wired)" in out
