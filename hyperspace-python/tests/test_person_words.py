"""The owner, 2026-11-06: "Session and rig need to go away." (register rows 778-780.)

Neither word may return in a string a person reads. Every string literal in `hyperspace/`
is scanned, docstrings excluded: an f-string's pieces are read one by one, and comments
are not read at all. The README is read whole. `LEFT` is what stays and why: each is a
saved key or an attribute's name, so no person ever sees it. Add to it only for a string no
person reads; say a new panel string as what it means (rows 778 and 779 list how).

The rest holds the words to the truth, since a false new word is worse than a kept old one,
and to the pane's narrowest width.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace as NS

from imgui_bundle import imgui
from test_ui_shell import rig  # noqa: F401 — the headless panel fixture

import hyperspace
from hyperspace import graph as rgraph
from hyperspace import graphview, learn, ui, ui_graph, ui_loadable, ui_routing
from hyperspace.modbank import MAX_ID, Bank

ROOT = Path(hyperspace.__file__).parent
WORDS = re.compile(r"\b(sessions?|rigs?)\b", re.IGNORECASE)

SAVED_SHOW_KEY = "a key of a saved show file; goes with the one migration"
# (file, the whole string): how many times it stands in that file, and why it stays. A
# count and no line numbers: others move lines, and a new use has to come through here.
LEFT: dict[tuple[str, str], tuple[int, str]] = {
    ("headless.py", "session"): (1, SAVED_SHOW_KEY),
    ("library.py", "session"): (11, SAVED_SHOW_KEY),
    ("library.py", "rig"): (1, SAVED_SHOW_KEY),
}


def said_by(source: str) -> list[str]:
    """Every string in `source` a person could read: all but the docstrings."""
    tree = ast.parse(source)
    docs = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs
    ]


def _found() -> Counter:
    return Counter(
        (path.relative_to(ROOT).as_posix(), text)
        for path in sorted(ROOT.rglob("*.py"))
        for text in said_by(path.read_text(encoding="utf-8"))
        if WORDS.search(text)
    )


def test_session_and_rig_leave_every_string_a_person_reads():
    want = Counter({key: n for key, (n, _why) in LEFT.items()})
    back = sorted((_found() - want).items())
    assert not back, (
        "say these as what they mean (the meta controller's, the bus cable: register rows "
        f"778, 779), or, if no person reads them, count them in LEFT and say why: {back}"
    )


def test_what_is_left_is_still_there():
    """So the list shrinks as the migration and the cleanup take these keys away."""
    want = Counter({key: n for key, (n, _why) in LEFT.items()})
    gone = sorted((want - _found()).items())
    assert not gone, f"fewer in the code than LEFT counts, so lower LEFT: {gone}"


def test_the_readme_says_neither():
    lines = (ROOT.parent / "README.md").read_text(encoding="utf-8").splitlines()
    assert not [line for line in lines if WORDS.search(line)]


def test_the_scan_finds_the_word_in_every_shape_it_could_come_back_in():
    source = '''
"""A session's docstring is not read."""
# a rig's comment is not read
TIP = "the rig's cable"
LABEL = "Session"
MICRO = "session"
SPLIT = ("not in this "
         "rig")
def f(x):
    """A rig's docstring is not read."""
    return f"{x} is the session's"
'''
    said = [text for text in said_by(source) if WORDS.search(text)]
    assert sorted(said) == sorted(
        ["the rig's cable", "Session", "session", "not in this rig", " is the session's"]
    )


def test_a_bare_word_restored_beside_a_listed_key_is_caught():
    """Review of #407: `ui._micro("session")` back in a file that lists "session"."""
    key = ("library.py", "session")
    more = _found() + Counter({key: 1})
    want = Counter({k: n for k, (n, _why) in LEFT.items()})
    assert (more - want)[key] == 1


def test_right_rigid_and_origin_are_no_rig():
    assert not WORDS.search("the right rigid origin, a trigger's rigging")


# ---------------------------------------------------------------- the words are true

def test_a_show_is_not_said_to_hold_the_bus_cables():
    """They are the loaded patch's since plan 44 D3 (`LoadedPatch.bus`), as `BUS_SAID` says."""
    assert "bus" not in ui_loadable.SHOW_LINE
    assert "preset is the look, with the bus cables" in ui_loadable.SHOW_TIP
    assert "(a preset saves its cuts)" in graphview.BUS_SAID


def test_a_clouds_wire_is_no_bus_cable(monkeypatch):
    """It never touches All outputs; `_cut_bus` cuts both, and says which."""
    assert "bus" not in graphview.CLOUD_SAID
    cuts = NS(has=lambda w: True, cutting=lambda w: None)
    monkeypatch.setattr(graphview, "_bus_cuts", lambda edit: cuts)
    monkeypatch.setattr(graphview, "_doc", lambda edit: {})
    monkeypatch.setattr(graphview, "_land", lambda e, d, label, said, bus_cuts: said)
    cloud = rgraph.cloud_wire(0)
    assert rgraph.is_cloud_wire(cloud)
    assert graphview._cut_bus(None, cloud) == f"cut the cloud's wire {cloud}"
    bus = rgraph.Wire("output.all.image", "output.1.image")
    assert rgraph.is_fixture_wire(bus) and not rgraph.is_cloud_wire(bus)
    assert graphview._cut_bus(None, bus) == f"cut the bus cable {bus}"


def test_a_controller_with_no_config_entry_is_not_set_up_rather_than_absent():
    """`MISSING` means no `[[devices]]` entry lists the role: the pad may be plugged in."""
    assert graphview.PLACEHOLDER_STATUS.startswith("not set up on this Mac")
    assert "[[devices]] in config.toml" in graphview.PLACEHOLDER_STATUS


def test_the_banks_refusal_says_what_truly_frees_an_id():
    """A restart with the top id still in use refuses again; with it gone, it does not."""
    class Voices(Bank):
        SCHEME, LABEL, KEY, DEFAULT = "voice", "voice", "voices", (1,)

        def make(self):
            return object()

    bank = Voices([1, MAX_ID])
    said = bank.refusal()
    assert said is not None and "highest still in use" in said
    bank.remove(MAX_ID)
    assert bank.refusal() == said                  # removed, this run: still used up
    assert Voices([MAX_ID]).refusal() == said      # a restart with it in use
    assert Voices([1]).refusal() is None           # a restart with it gone


def test_every_door_says_a_blocked_control_in_one_set_of_words():
    assert learn.blocked_words("K1", "invariant") == "K1 is invariant (the meta controller's)"
    assert learn.blocked_words("K1", "global", verb="learn").endswith(
        "(the meta controller's) — latch SHIFT off to learn into the preset")
    assert learn._table_name(NS(path=None)) == "the meta controller"
    assert learn._table_name(NS(path=Path("bindings.json"))) == "bindings.json"


# ---------------------------------------------------------------- the pane's narrow widths

def _in_a_pane(width: float, draw):
    """`draw` in a window of `width`; (the right edge of what it drew, the window's right)."""
    imgui.new_frame()
    imgui.set_next_window_size(imgui.ImVec2(width, 400))
    imgui.begin("##narrow")
    edge = imgui.get_window_pos().x + width
    try:
        draw()
        return imgui.get_item_rect_max().x, edge
    finally:
        imgui.end()
        imgui.end_frame()


def test_the_show_line_is_whole_at_the_panes_first_width_and_cut_with_care_at_its_narrowest(
    rig,  # noqa: F811
):
    """REVIEW.md: widgets fit their narrowest width. Its hover has the whole sentence."""
    seen = {}

    def draw():
        seen["fit"] = ui.fit_micro(ui_loadable.SHOW_LINE, imgui.get_content_region_avail().x)
        ui._micro(seen["fit"])

    right, edge = _in_a_pane(ui_graph.SIDE_W, draw)
    assert seen["fit"] == ui_loadable.SHOW_LINE.upper() and right <= edge
    right, edge = _in_a_pane(ui_graph.SIDE_MIN, draw)
    assert seen["fit"].startswith("SHOW: PADS, META") and right <= edge


SINKS_NOTE = "the meta controller's — out to a sink · right-click a param: Learn sink"


def test_routings_headings_stay_inside_the_pane(rig):  # noqa: F811
    for width in (ui_graph.SIDE_MIN, ui_graph.SIDE_W):
        for title, note in (("meta controller", "its own rows — edit bindings.json"),
                            ("sinks", SINKS_NOTE)):
            right, edge = _in_a_pane(width, lambda t=title, n=note: ui_routing._heading(t, n))
            assert right <= edge, (title, width)
