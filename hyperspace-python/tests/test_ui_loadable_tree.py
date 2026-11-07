"""Plan 48 stage 2: the PRESETS list as a tree — headless imgui over the
controls rig (tests/test_ui_shell.py), on a home seeded with the corpus
(the party show open: ACID on F6), driven by the mouse and the keys.

The top-level loadable patches first, then a folding header per folder,
alphabetically, nested folders nested; a header folds by a click and the
fold is this Mac's (``presets.folded`` in ``<machine>/ui.json``, beside
the pane's); a row's right-click **move to ▸** and a drag onto a header
move the loadable patch (its bytes kept, the bank's slot following); a folder's
right-click makes a folder inside, renames it, removes it (empty only);
**new folder** at the list's foot makes one at the top."""

import json
import time

from imgui_bundle import imgui
from test_ui_shell import CONTROL_SIZE, _click, _mouse, frame, rig  # noqa: F401 — the fixture

from hyperspace import ui_loadable, ui_pane

TALL = (CONTROL_SIZE[0], 2400)      # every row in view: the folders sit after the top level


def _folders(lib, layout: dict[str, list[str]]) -> None:
    """Move corpus loadable patches into folders: {"party": ["DIAL", "FIELD"], …};
    an empty list makes an empty folder."""
    for folder, names in layout.items():
        d = lib.home / "loadable" / folder
        d.mkdir(parents=True, exist_ok=True)
        for n in names:
            src = lib.path_of("loadable", n)
            src.rename(d / src.name)
    lib._sync()


def _page(panel, n: int = 2):
    imgui.get_io().display_size = imgui.ImVec2(*TALL)
    frame(panel, "loadable")
    for _ in range(n - 1):
        frame(panel)
    return ui_loadable._state(panel)


def _type(panel, text: str) -> None:
    io = imgui.get_io()
    io.add_input_characters_utf8(text)
    frame(panel)
    io.add_key_event(imgui.Key.enter, True)
    frame(panel)
    io.add_key_event(imgui.Key.enter, False)
    frame(panel)
    frame(panel)


def _hover(panel, rect, frames: int = 3) -> None:
    x, y = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    for _ in range(frames):
        _mouse(panel, x, y)


def test_the_tree_is_the_top_level_then_each_folder_nested(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    _folders(lib, {"party": ["DIAL", "FIELD"], "party/deep": ["TUMBLE"], "ambient": []})
    st = _page(panel)
    page = st["page"]
    assert page["folders"] == [("ambient", True), ("party", True), ("party/deep", True)]
    names = [n for n, _ in page["rows"]]
    top = [n for n in lib.list("loadable") if "/" not in n]
    assert names == [*top, "party/DIAL", "party/FIELD", "party/deep/TUMBLE"]
    r = page["rects"]
    assert r["folder.party"][3] <= r["row.party/DIAL"][1]
    assert r["row.party/FIELD"][3] <= r["folder.party/deep"][1]
    assert r["folder.party"][0] < r["folder.party/deep"][0]          # nested: indented
    assert r["folder.party/deep"][0] < r["row.party/deep/TUMBLE"][0]
    assert r["row.ACID"][3] <= r["folder.ambient"][1]               # the top level first
    assert ("deep", "TUMBLE") not in page["text"]                   # the row's text: its leaf
    assert ("party/deep", "TUMBLE") in page["text"]


def test_a_header_folds_by_a_click_and_the_fold_is_this_macs(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    ui_json = lib._machine() / "ui.json"
    ui_json.write_text(json.dumps({"pane": {"open": {"loadable": False}}, "graph": {"side": 300}}))
    _folders(lib, {"party": ["DIAL"], "party/deep": ["TUMBLE"]})
    lib.load("loadable", "party/DIAL")
    st = _page(panel)
    _click(panel, st["page"]["rects"]["folder.party"])
    frame(panel)
    page = st["page"]
    assert page["folders"] == [("party", False)]                    # its folders go with it
    assert not [n for n, _ in page["rows"] if n.startswith("party/")]
    # written WRITE_AFTER_S after the click, as the pane's folds are (review of #349)
    assert "loadable" not in json.loads(ui_json.read_text())
    assert ui_loadable.flush_folds(panel, now=time.monotonic() + ui_pane.WRITE_AFTER_S + 0.1)
    assert not ui_loadable.flush_folds(panel, force=True)            # nothing left to write
    doc = json.loads(ui_json.read_text())
    assert doc["loadable"] == {"folded": ["party"]}
    assert doc["pane"] == {"open": {"loadable": False}} and doc["graph"] == {"side": 300}
    # a fresh panel state reads it back: still folded, the loaded patch said
    st.pop("folded")
    labels = []
    real = imgui.tree_node_ex
    imgui.tree_node_ex = lambda label, *a: (labels.append(label), real(label, *a))[1]
    try:
        frame(panel)
    finally:
        imgui.tree_node_ex = real
    assert st["page"]["folders"] == [("party", False)]
    assert labels == ["party  ·  2  ·  DIAL###folder.party"]
    _click(panel, st["page"]["rects"]["folder.party"])               # and open again
    frame(panel)
    assert ("party", True) in st["page"]["folders"]
    ui_loadable.flush_folds(panel, force=True)
    assert json.loads(ui_json.read_text())["loadable"] == {"folded": []}
    # a fold clicked just before quitting is written by the panel's close
    _click(panel, st["page"]["rects"]["folder.party"])
    assert json.loads(ui_json.read_text())["loadable"] == {"folded": []}   # not yet
    panel.close()
    assert json.loads(ui_json.read_text())["loadable"] == {"folded": ["party"]}
    assert not ui_loadable.flush_folds(panel, force=True)              # nothing left


def test_a_fold_read_before_the_machine_is_known_is_read_again(rig):  # noqa: F811
    """Review of #349: `folded` asked while no machine is known (no
    library yet) is not the file — once the machine is known it is read,
    a fold clicked meanwhile laid over it, and the write keeps both."""
    panel, lib = rig.panel, rig.lib
    (lib._machine() / "ui.json").write_text(json.dumps({"loadable": {"folded": ["party"]}}))
    panel.library = None
    assert ui_loadable.folded(panel) == set()
    ui_loadable.set_folded(panel, "ambient", True)
    panel.library = lib
    assert ui_loadable.folded(panel) == {"party", "ambient"}
    ui_loadable.flush_folds(panel, force=True)
    doc = json.loads((lib._machine() / "ui.json").read_text())
    assert doc["loadable"] == {"folded": ["ambient", "party"]}


def test_the_no_loadables_hint_shows_while_only_empty_folders_are_there(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    for p in list((lib.home / "loadable").glob("*.json")):
        p.unlink()
    _folders(lib, {"ambient": []})
    got = []
    real = imgui.text_disabled
    imgui.text_disabled = lambda text, *a: (got.append(text), real(text, *a))[1]
    try:
        _page(panel)
    finally:
        imgui.text_disabled = real
    assert "no patches — new, then save as… makes one" in got
    assert ("ambient", True) in ui_loadable._state(panel)["page"]["folders"]


def test_remove_is_off_for_a_folder_holding_a_hidden_file_and_says_what(rig):  # noqa: F811
    """Review of #349: the menu asks the library what is in the way
    (`Library.held`), hidden files too, so the item is never on and then
    refused."""
    panel, lib = rig.panel, rig.lib
    _folders(lib, {"keep": []})
    (lib.home / "loadable" / "keep" / ".notes").write_text("yours")
    st = _page(panel)
    _click(panel, st["page"]["rects"]["folder.keep"], button=1)
    assert st["menu_for"] == "keep" and st["menu_held"] == [".notes"]
    _click(panel, st["menu"]["remove"])
    assert "keep" in lib.folders() and (lib.home / "loadable" / "keep" / ".notes").is_file()


def test_move_to_on_a_rows_menu_moves_the_file_and_the_bank_follows(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    _folders(lib, {"party": []})
    pr = lib.install
    assert pr.bank[5] == "ACID"
    src = lib.path_of("loadable", "ACID")
    before = src.read_bytes()
    lib.load("loadable", "ACID")
    st = _page(panel)
    _click(panel, st["page"]["rects"]["row.ACID"], button=1)       # the right-click
    menu = st["menu"]
    assert st["menu_for"] == "ACID" and "move to" in menu
    _hover(panel, menu["move to"])                                   # the submenu opens
    assert {"to.party"} <= set(st["menu"]) and "to." not in st["menu"]   # not where it is
    _click(panel, st["menu"]["to.party"])
    dst = lib.home / "loadable" / "party" / src.name
    assert dst.read_bytes() == before and not src.exists()
    assert pr.bank[5] == "party/ACID" and lib.current("loadable") == "party/ACID"
    show = json.loads(pr.path.read_text())
    assert show["bank"][5] == "party/ACID"
    frame(panel)
    frame(panel)
    assert "party/ACID" in [n for n, _ in st["page"]["rows"]]
    assert lib.status.startswith("moved ACID → party/ACID")


def test_a_row_dragged_onto_a_header_moves_into_that_folder(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    _folders(lib, {"party": []})
    src = lib.path_of("loadable", "DIAL")
    before = src.read_bytes()
    st = _page(panel)
    row, head = st["page"]["rects"]["row.DIAL"], st["page"]["rects"]["folder.party"]
    x0, y0 = (row[0] + 40, (row[1] + row[3]) / 2)
    x1, y1 = ((head[0] + head[2]) / 2, (head[1] + head[3]) / 2)
    _mouse(panel, x0, y0)
    _mouse(panel, x0, y0, 0, True)
    for k in range(1, 9):
        _mouse(panel, x0 + (x1 - x0) * k / 8, y0 + (y1 - y0) * k / 8)
    _mouse(panel, x1, y1, 0, False)
    frame(panel)
    assert (lib.home / "loadable" / "party" / src.name).read_bytes() == before
    assert "party/DIAL" in lib.list("loadable") and lib.current("loadable") is None  # not loaded


def test_a_folder_renamed_from_its_menu_and_the_bank_follows(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    _folders(lib, {"party": ["ACID"]})
    pr = lib.install
    pr.bank[5] = "party/ACID"
    st = _page(panel)
    _click(panel, st["page"]["rects"]["folder.party"], button=1)
    assert st["menu_for"] == "party"
    _click(panel, st["menu"]["rename"])
    frame(panel)
    assert st["naming"] == "folder:party" and st["buf"] == "party"
    _type(panel, "crowd")
    assert st["naming"] is None
    assert (lib.home / "loadable" / "crowd").is_dir()
    assert not (lib.home / "loadable" / "party").exists()
    assert pr.bank[5] == "crowd/ACID"
    assert ("crowd", True) in st["page"]["folders"]


def test_new_folder_at_the_foot_and_inside_and_remove_only_when_empty(rig):  # noqa: F811
    panel, lib = rig.panel, rig.lib
    st = _page(panel)
    assert st["page"]["folders"] == []
    _click(panel, st["page"]["rects"]["new_folder"])
    frame(panel)
    assert st["naming"] == "newfolder:"
    _type(panel, "ambient")
    assert lib.folders() == ["ambient"] and ("ambient", True) in st["page"]["folders"]
    _click(panel, st["page"]["rects"]["folder.ambient"], button=1)
    _click(panel, st["menu"]["new"])
    frame(panel)
    assert st["naming"] == "newfolder:ambient"
    _type(panel, "slow")
    assert lib.folders() == ["ambient", "ambient/slow"]
    # a folder with a folder in it: remove is off, clicking it does nothing
    _click(panel, st["page"]["rects"]["folder.ambient"], button=1)
    _click(panel, st["menu"]["remove"])
    assert lib.folders() == ["ambient", "ambient/slow"]
    _click(panel, st["rects"]["strip.loadable.name"])              # a click away closes it
    _click(panel, st["page"]["rects"]["folder.ambient/slow"], button=1)
    assert st["menu_for"] == "ambient/slow"
    _click(panel, st["menu"]["remove"])
    assert lib.folders() == ["ambient"] and lib.status == "removed the folder ambient/slow"
