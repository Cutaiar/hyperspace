"""Plan 65: GRAPH's effect picker (`ui_effect_picker`), in place of the
nested effects ▸ submenu.

Driven like a person drives it (`tests/ui_driver.py`: the mouse and the
keys through imgui's queue, each control found by its id) on the headless
GRAPH page: the right-click picker's **effects…** opens it; a click on a
tile lands the very graph the menu's row landed — the same section, the
same place, unwired — and a cable's **insert ▸ effects…** splices it in as
the menu did; the search keeps the tiles whose label or tip answer; the
canvas under it is swallowed (`ui_graph._menu_up`); and nothing about it is
saved."""

from __future__ import annotations

import copy
from types import SimpleNamespace as NS

import pytest
from conftest import seed
from imgui_bundle import imgui
from test_graph_legible import party
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture
from ui_driver import Driver

from hyperspace import graphview, ui_graph, ui_menu
from hyperspace import ui_effect_picker as fxpick

AT = (140.0, 60.0)


@pytest.fixture()
def rig(shell_rig):  # noqa: F811
    seed(shell_rig.lib.home)
    return shell_rig


def _driver(rig, monkeypatch) -> Driver:
    d = Driver(step=lambda: frame(rig.panel, "graph"))
    d.record(monkeypatch.setattr)
    return d


def _landed(rig) -> tuple[dict, dict]:
    """(the loaded patch's graph section, its layout map), copied."""
    lp = rig.lib.loaded_patch
    return copy.deepcopy(lp.graph.spec.to_json()), copy.deepcopy(dict(lp.layout or {}))


def _tiles(d: Driver) -> set[str]:
    pre = fxpick.TILE.format("")
    return {k[len(pre):] for k in d.rects if k.startswith(pre)}


def _open(rig, d: Driver, mode="add", at=AT, cable=None) -> dict:
    st = ui_graph._state(rig.panel)
    fxpick.open_picker(st, mode, at, cable)
    d.run(d.wait(2))
    assert fxpick.state(st)["up"]
    return st


# ---------------------------------------------------------------- the menus

def test_the_menus_have_one_effects_row_in_place_of_the_submenu(rig):
    st = party(rig)
    st["menu"], st["menu_at"] = ("picker", ""), AT
    m = ui_menu.Menu("t.picker")
    ui_graph.menu(rig.panel, st, st["view"], m)
    subs = [r.label for r in m.walk() if r.kind == ui_menu.SUB]
    assert "effects" not in subs
    row = m.row(fxpick.MENU_LABEL)
    assert row is not None and row.id == "graph.pick.effects"
    assert "copy of" in subs                   # the rest of the picker as it was
    m.pick(row.id)
    s = fxpick.state(st)
    assert s["mode"] == "add" and s["at"] == AT and s["open"]
    # a picture cable's insert ▸ effects… opens it on that cable
    c = next(c for c in st["view"].cables if c.kind == "render" and c.type == graphview.IMAGE)
    st["menu"] = ("cable", c.id)
    m = ui_menu.Menu("t.cable")
    ui_graph.menu(rig.panel, st, st["view"], m)
    row = m.row("insert", fxpick.MENU_LABEL)
    assert row is not None and m.row("insert", "effects") is None
    m.pick(row.id)
    assert fxpick.state(st)["mode"] == "insert" and fxpick.state(st)["cable"] == c.id


# ---------------------------------------------------------------- the same graph as the menu

def test_a_tile_adds_what_the_menus_row_added(rig, monkeypatch):
    st = party(rig)
    d = _driver(rig, monkeypatch)
    before = _landed(rig)
    _open(rig, d)
    assert {"wave", "acid", "testcard"} <= _tiles(d)
    d.run(d.click(fxpick.TILE.format("wave")))
    assert fxpick.state(st) is None
    picked = _landed(rig)
    revealed = set(st.get("revealed", ()))
    assert picked != before
    # the same patch, the same click, through the old menu row's action
    party(rig)
    assert _landed(rig) == before
    e = ui_graph.render_edit(rig.panel)
    assert ui_graph.add_render(rig.panel, e, "effect", "wave", AT) is None
    assert _landed(rig) == picked
    assert "render:wave" in revealed
    frame(rig.panel, "graph")
    assert st["view"].node("render:wave").faint            # unwired, as the menu left it


def test_insert_on_a_cable_splices_what_the_menus_row_spliced(rig, monkeypatch):
    st = party(rig)
    d = _driver(rig, monkeypatch)
    before = _landed(rig)
    c = next(c for c in st["view"].cables if c.kind == "render" and c.type == graphview.IMAGE)
    _open(rig, d, "insert", AT, c.id)
    d.run(d.click(fxpick.TILE.format("wave")))
    picked = _landed(rig)
    assert picked != before
    party(rig)
    st = ui_graph._state(rig.panel)
    c = next(x for x in st["view"].cables if x.id == c.id)
    assert ui_graph.insert_effect(rig.panel, c, "wave", AT) is None
    assert _landed(rig) == picked
    frame(rig.panel, "graph")
    assert not st["view"].node("render:wave").faint        # wired in: it reaches


# ---------------------------------------------------------------- search, hover, keys

def test_the_search_keeps_the_tiles_whose_label_or_tip_answer(rig, monkeypatch):
    party(rig)
    d = _driver(rig, monkeypatch)
    _open(rig, d)
    every = _tiles(d)
    assert len(every) >= 26
    d.run(d.type("wave"))                       # the search has the keys from the start
    got = _tiles(d)
    assert {"wave", "wavetable"} <= got < every
    files = ui_graph.render_edit(rig.panel).graph.fx.files
    for name in got - {"wave", "wavetable"}:    # the rest say waves in their tips
        assert "wave" in files[name].tip.lower(), name
    d.run(d.click(fxpick.SEARCH), d.key(imgui.Key.a, d.ctrl), d.type("dither"))
    assert _tiles(d) == {"grain"}               # a word of its tip only
    d.run(d.key(imgui.Key.a, d.ctrl), d.type("zzqx"))
    assert _tiles(d) == set()
    d.run(d.key(imgui.Key.a, d.ctrl), d.key(imgui.Key.backspace))
    assert _tiles(d) == every


def test_enter_takes_the_first_tile_the_search_leaves(rig, monkeypatch):
    st = party(rig)
    d = _driver(rig, monkeypatch)
    _open(rig, d)
    d.run(d.type("kaleid"), d.key(imgui.Key.enter))
    assert fxpick.state(st) is None
    assert any(n.get("file") == "kaleido" for n in _landed(rig)[0].get("nodes", ()))


def test_hovering_a_tile_says_its_tip_and_asks_for_its_loop(rig, monkeypatch):
    st = party(rig)
    asked = []
    rig.panel.renderer.effect_previews = lambda: type(
        "C", (), {"want": lambda self, names, loop=None: asked.append((set(names), loop)),
                  "picture": lambda self, name, t=None: None})()
    d = _driver(rig, monkeypatch)
    _open(rig, d)
    d.run(d.move(fxpick.TILE.format("wave")), d.wait(1))
    assert fxpick.state(st)["hover"] == "wave"
    assert asked[-1][1] == "wave" and "wave" in asked[-1][0]
    d.run(d.key(imgui.Key.escape))
    assert fxpick.state(st) is None


def test_the_canvas_under_it_is_swallowed(rig, monkeypatch):
    """While it is open GRAPH's guard (`_menu_up`, #452) says a popup is up
    on the frames the canvas reads the pointer: no hover words, no click."""
    party(rig)
    seen = []
    real = ui_graph._hover
    monkeypatch.setattr(ui_graph, "_hover",
                        lambda *a, **k: (seen.append(ui_graph._menu_up()), real(*a, **k))[1])
    d = _driver(rig, monkeypatch)
    d.run(d.wait(1))
    assert seen and not any(seen)
    seen.clear()
    _open(rig, d)
    d.run(d.move(fxpick.TILE.format("wave")), d.wait(1))
    assert seen[-3:] == [True, True, True]


def test_the_picker_is_never_saved(rig, monkeypatch):
    st = party(rig)
    d = _driver(rig, monkeypatch)
    before = rig.lib.loaded_patch.document("party-trip")
    _open(rig, d)
    d.run(d.type("wave"))
    assert rig.lib.loaded_patch.document("party-trip") == before
    assert fxpick.KEY in st


# ---------------------------------------------------------------- the pieces

def test_the_tiles_are_big_and_fit_the_window():
    assert fxpick.TILE_W >= 160 and fxpick.TILE_H >= 120      # a trackpad on stage
    assert fxpick.columns(10.0) == 1
    assert fxpick.columns(6 * fxpick.TILE_W + 5 * fxpick.GAP) == 6
    assert fxpick.columns(1e6) == fxpick.MAX_COLS


def test_enter_prefers_a_label_to_a_tip():
    S = lambda n, label, tip, order: NS(name=n, label=label, tip=tip, order=order, family="")
    specs = [S("prism", "Prism", "Light waves split", 41), S("wave", "Wave", "", 27),
             S("acid", "Acid", "", 10)]
    assert fxpick.first_match(specs, "wave") == "wave"
    assert fxpick.first_match(specs, "light") == "prism"
    assert fxpick.first_match(specs, "") == "acid"
    assert fxpick.first_match(specs, "zzz") is None


def test_a_file_with_no_spec_still_gets_a_tile():
    got = fxpick.specs_of(["wave", "mystery"], {"wave": type("S", (), {"name": "wave"})()})
    assert [s.name for s in got] == ["wave", "mystery"] and got[1].label == "mystery"
