"""GRAPH's off-air signs, hushed: the owner at the rig, 2026-11-24.

The canvas takes a red frame and an inset of what is on air whenever the panel is on
the deck off air (`ui_graph._monitor`, plan 44 D5d). A fade across — a hand's, the
playlist's, or the Edge's D-pad — moves `on_air` away from the deck someone is editing,
and the pair lands over their nodes. **quiet off air** on the deck row hushes that pair;
the deck chip still says it, in red, so what is live is never hidden.
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from imgui_bundle import imgui
from test_save_live import _graph
from test_ui_shell import build_rig
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import ui_graph


def _meta(on_air_is_panel: bool):
    """GRAPH's deck row, with the panel on deck 1 and the air where asked."""
    one, two = NS(name="deck 1"), NS(name="deck 2")
    air = one if on_air_is_panel else two
    return NS(decks=(one, two), panel=one, on_air=air, timed=None, playing=None,
              deck_name=lambda deck: deck.name,
              words=lambda deck: f"{deck.name} · {'on' if deck is air else 'off'} air")


def _mon():
    asked: list[bool] = []
    return NS(tex=NS(glo=7, size=(160, 90)), want=lambda: asked.append(True)), asked


# ------------------------------------------------- the pair, and what hushes it

@pytest.mark.empty_frame
def test_quiet_draws_no_frame_and_no_inset_while_the_panel_is_still_off_air(shell_rig):  # noqa: F811
    """The deck is off air either way: `panel_off_air` is what the chip reads, and it
    does not move. Only the canvas's pair goes."""
    mon, asked = _mon()
    panel = NS(meta=_meta(False), monitor=mon)
    imgui.new_frame()
    imgui.begin("probe")
    try:
        dl = imgui.get_window_draw_list()
        before = dl.vtx_buffer.size()
        ui_graph._monitor(panel, (0.0, 0.0), (800.0, 600.0))
        loud = dl.vtx_buffer.size()
        assert loud > before and asked == [True], "off air draws the pair"

        panel.__dict__[ui_graph.STATE] = {"quiet_off_air": True}
        ui_graph._monitor(panel, (0.0, 0.0), (800.0, 600.0))

        assert dl.vtx_buffer.size() == loud, "quiet: nothing drawn"
        assert asked == [True], "and no texture asked for"
        assert ui_graph.panel_off_air(panel), "the deck chip's own truth is untouched"
    finally:
        imgui.end()
        imgui.end_frame()


def test_reading_quiet_off_a_panel_with_no_page_drawn_yet_makes_no_state():
    """A stand-in (a test's, a desk's panel before its first graph frame) answers False
    without growing a page state dict, so `_monitor` stays free of side effects."""
    panel = NS(meta=_meta(False), monitor=_mon()[0])
    assert ui_graph.quiet_off_air(panel) is False
    assert ui_graph.STATE not in panel.__dict__


def test_a_page_state_from_before_this_edit_gains_the_key():
    """`_state` fills every key by `setdefault` (a hot reload re-classes the live panel
    without running `__init__`), so a dict an older build made is not missing it."""
    panel = NS()
    panel.__dict__[ui_graph.STATE] = {"editor": None}          # an older build's
    assert ui_graph._state(panel)["quiet_off_air"] is False
    assert ui_graph.quiet_off_air(panel) is False


# ------------------------------------------------------------- the chip, drawn

def test_the_chip_hushes_the_pair_and_a_second_press_brings_it_back(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.meta = _meta(False)
        d = _graph(r, monkeypatch)
        d.run(d.wait(2))
        assert "graph.quiet" in d.rects, "on the deck row, beside the deck chip"
        assert not ui_graph.quiet_off_air(r.panel), "loud until asked"

        d.run(d.click("graph.quiet", frames=2))
        assert ui_graph.quiet_off_air(r.panel)

        d.run(d.click("graph.quiet", frames=2))
        assert not ui_graph.quiet_off_air(r.panel)


def test_the_chip_is_drawn_on_air_too_so_a_fade_landing_moves_nothing_on_the_row(
        tmp_path, monkeypatch):
    """Why it is not drawn only while off air: a chip that came and went would shift
    **load…** and its neighbours under the hand at the moment the fade lands — the very
    disruption it is here to end. So the row is the same row, air or no air."""
    with build_rig(tmp_path) as r:
        r.panel.meta = _meta(True)
        d = _graph(r, monkeypatch)
        d.run(d.wait(2))
        assert "graph.quiet" in d.rects, "there while the panel's deck is on air"
        # the deck chip's own words go from "on air" to "off air" and so grow by a
        # letter: what must hold is that this chip stays where it is *in the row* —
        # the gap from the chip before it, and the one after it from this
        on_air = _gaps(d)

        r.panel.meta = _meta(False)             # the fade lands: this deck is off air
        d.run(d.wait(2))

        assert _gaps(d) == pytest.approx(on_air, abs=1.0)


def _gaps(d) -> tuple[float, float]:
    """The quiet chip's gap from the deck chip, and **load…**'s from the quiet chip."""
    deck, quiet, load = (d.rects[k] for k in ("graph.deck", "graph.quiet", "graph.load"))
    return quiet[0] - deck[2], load[0] - quiet[2]
