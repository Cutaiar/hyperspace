"""The panel says "analyzer"; the files keep `band` (wave 4 AZ, rows 737-738).

Words only: the first half pins what a person reads, the second what stayed.
"""

import json

import pytest
from test_ui_shell import page_frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graphview, patches, routing, ui, ui_desk, ui_graph, ui_pane, ui_presets
from hyperspace.groupwords import group_part, group_title, group_word
from hyperspace.library import PATCHES, Library, LibraryError
from hyperspace.params import Registry
from hyperspace.routing import Binding


def test_a_group_has_one_record_and_any_other_says_its_key(shell_rig):  # noqa: F811
    assert (group_word("band"), group_title("band"), group_part("band")) == (
        "analyzer", "analyzer tuning", "band")
    assert (group_word("view"), group_title("view"), group_part("view")) == ("view",) * 3
    assert group_word("") == ""
    assert shell_rig.reg.group_word("band") == "analyzer"       # undo.py's road: a leaf


def test_a_group_of_any_value_has_words_and_no_type_error():
    for bad in ([], {}, 3, None):
        assert group_word(bad) == group_title(bad) == group_part(bad) == str(bad)


def test_a_patch_whose_group_is_not_text_is_refused_in_words(tmp_path):
    lib = Library(tmp_path)
    for i, bad in enumerate(([], {}, 3)):
        doc = {"schema": patches.SCHEMA, "name": f"odd{i}", "group": bad}
        assert patches.check(doc) == [patches.GROUP_EMPTY_WORDS.format(value=bad)]
        (tmp_path / PATCHES).mkdir(exist_ok=True)
        (tmp_path / PATCHES / f"odd{i}.json").write_text(json.dumps(doc))
        with pytest.raises(LibraryError):
            lib.read_patch(f"odd{i}")


def test_the_registry_keeps_its_docstring():
    assert Registry.__doc__ == "An ordered map of Param by id."


def test_a_refusal_says_the_word_not_the_key(tmp_path):
    assert "(analyzer)" in patches.check({"schema": patches.SCHEMA, "group": "band",
                                          "routes": []})[0]


def test_the_section_head_is_the_analyzer_and_the_strip_still_the_band_group(shell_rig, monkeypatch):  # noqa: F811
    panel, seen = shell_rig.panel, []
    drawn = panel._section
    monkeypatch.setattr(panel, "_section", lambda *a, **k: (seen.append(a), drawn(*a, **k)))
    page_frame(panel, "analyzer")
    assert ("analyzer tuning", "band") in seen


def test_the_tuning_node_still_opens_its_section():
    n = graphview.VNode("group:band", "group", group_title("band"))
    assert ui_graph.home_page(n) == ("analyzer", None)


def test_the_tuning_node_keeps_its_layout_key_and_says_its_title():
    added = []
    n = graphview._group_node({}, "band", lambda v: added.append(v) or v)
    assert (n.id, n.kind, n.label) == ("group:band", "group", "analyzer tuning")
    other = graphview._group_node({}, "tempo", lambda v: v)
    assert other.label == "tempo"


def test_the_analyzer_node_counts_its_bands():
    n = graphview.VNode(graphview.ANALYZER, "analyzer", "analyzer")
    assert graphview.summary(n)[0] == "0 bands · 0 patched"


def test_a_route_and_a_refusal_say_analyzer():
    assert routing.row_words("lane:0") == "analyzer 1"
    assert graphview.NOUNS["lane"] == "the analyzer"


def test_the_desk_says_analyzer_and_a_step_fits_a_small_button(shell_rig):  # noqa: F811
    reg = shell_rig.reg
    name = reg["band.select"].names[0]
    assert ui_desk.text(reg, Binding("note:0:51", "band.select", "set", 0.0)) == f"analyzer {name}"
    assert ui_desk.text(reg, Binding("note:0:97", "band.select", "step", 1.0)) == "Band +1"
    assert ui_desk.text(reg, Binding("note:0:81", "scene.reset_all", "toggle")) == (
        "Reset analyzer (again: undo)")


def test_no_param_of_the_analyzer_is_called_band_alone(shell_rig):  # noqa: F811
    for p in shell_rig.reg.group("band"):
        assert p.label != "Band", p.id


def test_a_trash_row_says_the_word():
    class Item:
        group, old = "band", True
    assert ui_presets.trash_tag(Item) == "analyzer · library"


# ---- what stayed: a saved name, which only the format lane may move ----

def test_the_saved_names_stayed(shell_rig):  # noqa: F811
    reg = shell_rig.reg
    assert reg["band.select"].group == "band"
    assert "band.0.atk" in reg and "band.0.post" in reg
    assert "band" in shell_rig.lib.groups()
    assert "analyzer" in ui.PAGE_KEYS and "analyzer" in ui_pane.KEYS
    assert ("analyzer", "analyzer", ("band",)) == next(s[:3] for s in ui_pane.SECTIONS
                                                       if s[0] == "analyzer")
