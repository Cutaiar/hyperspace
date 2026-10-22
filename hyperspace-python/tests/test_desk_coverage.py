# ruff: noqa: F811 — `rig` is test_ui_shell's fixture, taken as each test's argument
"""Plan 24 C3 — every preset's desk interesting (decision 19).

- **The coverage report** (tools/desk_coverage.py): every preset × every
  control of the APC40's preset layer, each `mapped`, `dark` or `dead`
  (`learn.cannot_show`). Its output is committed at
  docs/plans/assets/24-party-fixes/desk-coverage.md; this test
  regenerates it — twice, byte for byte — and fails when the committed
  file is stale. The owner's bar (at most four dark or dead) is reported,
  not met: no preset is remapped in this run.
- **Click-to-map ranked**: a picked control on the on-screen desk is
  offered the params this preset uses first (`learn.ranked`, a pure
  function), then the rest by group; an item clicked goes through
  `Learn.map_picked`, the one road.
"""

import importlib.util
import re
import shutil
import sys
from pathlib import Path

import pytest
from imgui_bundle import imgui
from test_ui_desk import _control, _pushes
from test_ui_shell import _click, _learn_over, frame, rig  # noqa: F401 — the fixture

from hyperspace import apc40, learn, ui_desk
from hyperspace.app import CONTROL_SIZE
from hyperspace.learn import DESKED, MOVED, ON, ROUTED, cannot_show, ranked
from hyperspace.routing import Binding

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "desk-templates"


def _tool():
    spec = importlib.util.spec_from_file_location("desk_coverage",
                                                  ROOT / "tools" / "desk_coverage.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod             # its dataclasses look their module up
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _tool()


# ---------------------------------------------------------------- the report

def test_the_committed_report_is_fresh_and_regenerates_byte_identical(tool):
    """Two runs, one text; and the committed file is that text — else run
    `uv run python tools/desk_coverage.py` and commit the report."""
    first, second = tool.build(), tool.build()
    assert first == second
    assert tool.read_report() == first, \
        "desk-coverage.md is stale: run `uv run python tools/desk_coverage.py`"
    assert not re.search(r"\d{4}-\d{2}-\d{2}|\d{2}:\d{2}", first)   # no date, no time
    assert tool.main(["--check"]) == 0
    # --check checks the factory report only: with --library it is refused
    for extra in (["--library", str(FIXTURES)], ["--stdout"]):
        with pytest.raises(SystemExit) as e:
            tool.main(["--check", *extra])
        assert e.value.code == 2


def test_the_preset_layer_is_the_three_strips_and_the_maps_preset_controls(tool):
    glyphs = [c.glyph for c in tool.layer_controls()]
    strips = [f"{s}{k}" for s in "DKS" for k in range(1, 9)]
    assert glyphs[:24] == strips
    assert set(glyphs[24:]) == {"G3·5", "G3·6", "G3·7", "G3·8", *(f"G8·{k}" for k in range(1, 7)),
                                "G5·9", "C", "B16", "B17"}
    # none of the session's controls: MASTER, the crossfader, SHIFT, SAVE, the bank pads,
    # the render toggles (scene launch 1–4)
    assert not {"SM", "X", "⇧", "G6·8", "G1·1", "G4·1", "G1·9", "G4·9"} & set(glyphs)


def test_every_factory_presets_numbers_are_in_the_report(tool, tmp_path):
    """The numbers the PR body and the decisions file quote: every factory
    preset is a row; the faders are dark on every one (no preset has fader
    rows in this run); none meets the bar yet."""
    controls, rows = tool.coverage(tmp_path)
    names = [r.name for r in rows]
    assert len(rows) == 25 and "TRIP" in names and "hands-orbit" in names   # + DIAL (#212), seq-demo (plan 31)
    n = len(controls)
    for r in rows:
        assert r.count(tool.MAPPED) + r.count(tool.DARK) + r.count(tool.DEAD) == n
        faders = [c for c in r.cells if c.glyph.startswith("S")]
        assert [c.status for c in faders] == [tool.DARK] * 8, r.name
        assert r.count(tool.DARK) + r.count(tool.DEAD) > tool.BAR, r.name
    trip = rows[names.index("TRIP")]
    k7 = next(c for c in trip.cells if c.glyph == "K7")
    assert (k7.status, k7.target, k7.why) == (tool.DEAD, "view.bmp_alpha", "no bitmap file")


def test_a_library_template_preset_is_reported_with_its_expanded_desk(tool, tmp_path):
    """`--library` copies a library's presets and templates into the scratch
    home (the source is only read): the fixture preset's row is its
    template plus overrides — D2 the dream (on), K2 dark (a dark row), K3
    the pattern mix (faces on), S1 the lines opacity."""
    lib = tmp_path / "lib"
    shutil.copytree(FIXTURES, lib)
    before = sorted(p.read_bytes() for p in lib.rglob("*.json"))
    home = tmp_path / "home"
    home.mkdir()
    controls, rows = tool.coverage(home, lib)
    (row,) = [r for r in rows if r.name == "TEMPLATED"]
    cells = {c.glyph: (c.status, c.target) for c in row.cells}
    assert cells["D1"] == (tool.MAPPED, "view.depth4")
    assert cells["D2"] == (tool.MAPPED, "dream.mix")
    assert cells["K2"] == (tool.DARK, "")
    assert cells["K3"] == (tool.MAPPED, "view.pattern_mix")
    assert cells["S1"] == (tool.MAPPED, "view.lines_alpha")
    assert row.count(tool.MAPPED) == 7
    assert sorted(p.read_bytes() for p in lib.rglob("*.json")) == before
    text = tool.report(controls, rows)
    assert "| TEMPLATED | 7 | 31 | 0 | 31 | 27 over |" in text


# ---------------------------------------------------------------- the dead rule

def test_cannot_show_is_the_rule_by_group():
    v = {"view.faces": False, "view.points": True, "view.lines": False, "fx.on": True,
         "fx.kaleido.on": False, "fx.plasma.on": True, "dream.on": False,
         "view.rotate": False, "view.bmp_file": ""}
    assert cannot_show("view.pattern", v) == "faces off"
    assert cannot_show("view.pattern_mix", v) == "faces off"
    assert cannot_show("pattern.mod.3", v) == "faces off"
    assert cannot_show("view.bmp_alpha", v) == "faces off"
    assert cannot_show("view.bmp_alpha", {**v, "view.faces": True}) == "no bitmap file"
    assert cannot_show("view.bmp_alpha", {**v, "view.faces": True,
                                          "view.bmp_file": "a.png"}) is None
    assert cannot_show("view.points_alpha", v) is None
    assert cannot_show("view.lines_alpha", v) == "lines off"
    # the stroke space (plan 26 A2b): dead only with the points and the lines off
    assert cannot_show("view.screen_strokes", v) is None
    assert cannot_show("view.screen_strokes", {**v, "view.points": False}) == \
        "points and lines off"
    assert cannot_show("view.screen_strokes", {**v, "view.lines": True,
                                               "view.points": False}) is None
    assert cannot_show("fx.kaleido.segments", v) == "kaleido off"
    assert cannot_show("fx.kaleido.mix", v) == "kaleido off"
    assert cannot_show("fx.kaleido.on", v) is None          # the switch itself shows
    assert cannot_show("fx.plasma.level", v) is None
    assert cannot_show("fx.plasma.level", {**v, "fx.on": False}) == "effects off"
    assert cannot_show("fx.mix", {**v, "fx.on": False}) == "effects off"
    assert cannot_show("fx.on", {**v, "fx.on": False}) is None
    assert cannot_show("dream.mix", v) == "look-back off"
    assert cannot_show("dream.on", v) is None
    assert cannot_show("rot.rate.XW", v) == "rotation off"
    assert cannot_show("view.plane.XY", v) == "rotation off"
    for pid in ("view.bright", "camera.zoom", "view.depth4", "lfo.1.depth", "macro.1"):
        assert cannot_show(pid, v) is None, pid
    assert cannot_show("view.pattern", {}) is None          # a switch not named counts as on


# ---------------------------------------------------------------- the ranking

PARAMS = [("view.bright", "view"), ("view.speed", "view"), ("view.pattern", "view"),
          ("view.pattern_mix", "view"), ("camera.zoom", "camera"), ("fx.kaleido.mix", "fx"),
          ("fx.kaleido.segments", "fx"), ("fx.plasma.level", "fx"), ("dream.mix", "dream"),
          ("band.0.post", "band"), ("lfo.1.depth", "lfo"), ("tempo.bpm", "tempo")]
VALUES = {"view.bright": 2.0, "view.speed": 0.5, "view.pattern": 0, "view.pattern_mix": 1.0,
          "camera.zoom": 1.0, "view.faces": True, "fx.on": True, "fx.kaleido.on": True,
          "fx.kaleido.mix": 1.0, "fx.kaleido.segments": 6, "fx.plasma.on": False,
          "fx.plasma.level": 0.2, "dream.on": False, "dream.mix": 0.5, "band.0.post": 3.0,
          "lfo.1.depth": 0.0, "tempo.bpm": 120.0}
DEFAULTS = {"view.bright": 1.0, "view.speed": 0.5, "view.pattern": 0, "view.pattern_mix": 1.0,
            "camera.zoom": 1.0, "fx.kaleido.mix": 1.0, "fx.kaleido.segments": 6,
            "fx.plasma.level": 0.2, "dream.mix": 0.3, "lfo.1.depth": 0.0}


def test_ranked_puts_the_presets_own_params_first_in_tiers():
    used, rest = ranked(PARAMS, VALUES, DEFAULTS, routed={"camera.zoom"},
                        on_desk={"view.speed"})
    assert used == [("camera.zoom", ROUTED), ("view.bright", MOVED),
                    ("view.pattern", ON), ("view.pattern_mix", ON),
                    ("fx.kaleido.mix", ON), ("fx.kaleido.segments", ON),
                    ("view.speed", DESKED)]
    # the rest by group, the performance groups first, each in registry order:
    # the plasma is off and the look-back is off (dead), so not this preset's;
    # a session param off its value is not "moved" (the preset never sets it)
    assert rest == [("dream", ["dream.mix"]), ("fx", ["fx.plasma.level"]),
                    ("lfo", ["lfo.1.depth"]), ("band", ["band.0.post"]),
                    ("tempo", ["tempo.bpm"])]
    every = [p for p, _ in used] + [p for _, ids in rest for p in ids]
    assert sorted(every) == sorted(p for p, _ in PARAMS)


def test_ranked_is_pure_and_never_offers_a_dead_param_as_the_presets():
    args = (PARAMS, dict(VALUES), dict(DEFAULTS), {"dream.mix"}, set())
    a = ranked(*args)
    assert ranked(*args) == a and args[1] == VALUES          # the same answer, nothing moved
    assert "dream.mix" not in [p for p, _ in a[0]]           # routed, but the look-back is off
    used, _rest = ranked(PARAMS, {**VALUES, "dream.on": True}, DEFAULTS, {"dream.mix"}, set())
    assert used[0] == ("dream.mix", ROUTED)
    # a caller's own rule
    used, _ = ranked(PARAMS, VALUES, DEFAULTS, set(), set(), shows=lambda pid: "no")
    assert used == []


# ---------------------------------------------------------------- click-to-map on screen

def test_the_offer_covers_no_control():
    x, y, w, h = ui_desk.OFFER
    for c in apc40.LAYOUT:
        apart = (c.x + c.w <= x or x + w <= c.x or c.y + c.h <= y or y + h <= c.y)
        assert apart, c


def test_a_picked_control_is_offered_this_presets_params_and_a_click_maps_it(rig, monkeypatch):
    """TRIP loaded, D5 picked: the offer lists TRIP's own params first —
    its routed and moved ones, its effects that are on — and none of a
    module it has off; a click on the first item puts D5 there through
    `Learn.map_picked` (one undo step), and the pick is over. The page
    click road still works beside it."""
    panel, table = rig.panel, rig.router.table
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    rig.lib.load("presets", "TRIP")
    pushes = _pushes(monkeypatch)
    calls = []
    real = lrn.map_picked
    monkeypatch.setattr(lrn, "map_picked", lambda pid, prof=None: calls.append(pid)
                        or real(pid, prof))
    d5 = _control("D5")
    for _ in range(3):
        frame(panel, "view")
    _click(panel, ui_desk.rect(panel, d5))
    assert lrn.control == d5.source
    frame(panel)
    used, rest = ui_desk.offer(panel, table)
    assert used and ui_desk._state(panel)["offer_drawn"] == [p for p, _ in used]
    tiers = [why for _, why in used]
    assert tiers == sorted(tiers, key=[ROUTED, MOVED, ON, DESKED].index)
    ids = [p for p, _ in used]
    reg = rig.reg
    values = reg.snapshot()
    assert all(learn.cannot_show(p, values) is None for p in ids)
    assert "fx.kaleido.segments" in ids                  # an effect TRIP has on
    assert not [p for p in ids if p.startswith("dream.")]   # TRIP's look-back is off
    assert {g for g, _ in rest} >= {"view", "band"}
    # at the default control size (the small desk, ~107 × 79 px of ground)
    # the chip lies inside the offer and at least three items show whole
    st = ui_desk._state(panel)
    box, chip = st["offer_box"], st["offer_chip"]
    inside = lambda r: (box[0] <= r[0] and r[2] <= box[2] + 0.5
                        and box[1] <= r[1] and r[3] <= box[3] + 0.5)
    assert ui_desk._state(panel)["unit"][0] < ui_desk.LABEL_UNIT
    assert inside(chip), (chip, box)
    rects = st["offer_rects"]
    assert all(inside(rects[p]) for p in ids[:3]), ([rects[p] for p in ids[:3]], box)
    # the first item, clicked with the mouse
    first = used[0][0]
    _click(panel, rects[first])
    assert calls == [first]
    (row,) = [b for b in table.desk() if b.source == d5.source]
    assert row.target == first and row.layer == "preset"
    assert lrn.control is None and pushes == [f"learn {first}"]
    frame(panel)
    assert "offer_rects" not in ui_desk._state(panel)       # no pick, no offer


def test_no_offer_for_a_control_that_cannot_be_mapped(rig):
    """An invariant control, or any with the global layer up, is picked for
    the look only: nothing is offered."""
    panel, table = rig.panel, rig.router.table
    imgui.get_io().display_size = imgui.ImVec2(*CONTROL_SIZE)
    lrn = _learn_over(rig)
    for _ in range(3):
        frame(panel, "view")
    lrn.pick(_control("SM").source)
    frame(panel)
    frame(panel)
    assert "offer_rects" not in ui_desk._state(panel)
    lrn.pick(_control("D5").source)
    table.set_layer("global")
    frame(panel)
    frame(panel)
    assert "offer_rects" not in ui_desk._state(panel)
    table.set_layer("preset")
    frame(panel)
    frame(panel)
    assert "offer_rects" in ui_desk._state(panel)


def test_the_offer_reads_routes_and_macros_as_routed(rig):
    """A route's target and a macro's base subscriber are "routed"."""
    panel, table = rig.panel, rig.router.table
    lrn = _learn_over(rig)
    rig.lib.load("presets", "TRIP")
    lrn.pick(_control("D6").source)
    used, _ = ui_desk.offer(panel, table)
    assert ("camera.pan.x", ROUTED) not in used
    table.add(Binding("lfo:1", "camera.pan.x", "push", 0.3))
    table.set_macros({"macro.2": {"subs": [{"base": "camera.pan.y", "from": 0, "to": 1}]}},
                     rig.reg)
    used, _ = ui_desk.offer(panel, table)
    assert ("camera.pan.x", ROUTED) in used and ("camera.pan.y", ROUTED) in used
