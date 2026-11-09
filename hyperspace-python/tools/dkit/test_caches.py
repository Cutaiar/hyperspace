"""The per-frame caches from the CPU pass (RETRO row 71), and what each must
NOT go on returning once its inputs change.

Every cache here was added under one rule: a frame drawn from it is byte
for byte the frame drawn without it. The pixel captures prove that for the
inputs they cover; these tests cover the other direction - an input that
changed and a cache that did not notice, which is the bug a cache is for.

    xvfb-run -a uv run python -m pytest tools/dkit/test_caches.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import draw as D
import menu as M
import tokens as T


class Rec:
    """A draw list that records the calls the cached helpers make."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def rec(*a, **k):
            self.calls.append((name, tuple(_plain(v) for v in a),
                               {n: _plain(v) for n, v in k.items()}))
        return rec


def _plain(v):
    if hasattr(v, "x") and hasattr(v, "y"):
        return (v.x, v.y)
    if isinstance(v, list):
        return tuple(_plain(p) for p in v)
    return v


@pytest.fixture
def rec(monkeypatch):
    monkeypatch.setattr(D, "_u32", lambda col: tuple(col))
    return Rec()


# --------------------------------------------------------------------------
# tokens.rgba
# --------------------------------------------------------------------------

def test_rgba_follows_the_theme_it_is_handed():
    assert T.rgba("background", theme=T.LIGHT) != \
        T.rgba("background", theme=T.DARK)
    assert T.rgba("border", 0.5, theme=T.DARK)[3] == \
        pytest.approx(T.rgba("border", theme=T.DARK)[3] * 0.5)


def test_rgba_sees_an_edited_theme():
    """The memo is keyed on what a token RESOLVES to, not on the theme dict,
    so editing a theme cannot leave the old colour behind."""
    th = dict(T.LIGHT)
    before = T.rgba("primary", theme=th)
    th["primary"] = "#ff0000"
    assert T.rgba("primary", theme=th) == (1.0, 0.0, 0.0, 1.0)
    assert before != (1.0, 0.0, 0.0, 1.0)


def test_rgba_takes_a_list_it_cannot_hash():
    assert T.rgba([255, 0, 0]) == (1.0, 0.0, 0.0, 1.0)


# --------------------------------------------------------------------------
# draw.sparkline
# --------------------------------------------------------------------------

def _line(rec):
    return next(c for c in rec.calls if c[0] == "add_polyline")[1][0]


def test_a_sparkline_redraws_when_its_values_change(rec):
    D.sparkline(rec, 0.0, 0.0, 100.0, 40.0, [0.0, 0.5, 1.0], (1, 1, 1, 1))
    a = _line(rec)
    rec.calls.clear()
    D.sparkline(rec, 0.0, 0.0, 100.0, 40.0, [0.0, 0.5, 0.25], (1, 1, 1, 1))
    b = _line(rec)
    assert a[:2] == b[:2] and a[2] != b[2]
    assert b[2] == (100.0, 30.0)


def test_a_sparkline_follows_its_rect_when_the_page_scrolls(rec):
    vals = [0.2, 0.9, 0.4]
    D.sparkline(rec, 10.0, 50.0, 100.0, 40.0, vals, (1, 1, 1, 1))
    a = _line(rec)
    rec.calls.clear()
    D.sparkline(rec, 10.0, 37.0, 100.0, 40.0, vals, (1, 1, 1, 1))
    b = _line(rec)
    assert [p[1] - 13.0 for p in a] == pytest.approx([p[1] for p in b])
    quads = [c for c in rec.calls if c[0] == "add_quad_filled"]
    assert len(quads) == 2 and quads[0][1][2][1] == 77.0   # base = y + h


def test_a_sparkline_takes_its_colour_live(rec):
    vals = [0.2, 0.9]
    D.sparkline(rec, 0.0, 0.0, 10.0, 10.0, vals, (1, 0, 0, 1))
    D.sparkline(rec, 0.0, 0.0, 10.0, 10.0, vals, (0, 0, 1, 1))
    cols = [c[1][1] for c in rec.calls if c[0] == "add_polyline"]
    assert cols == [(1, 0, 0, 1), (0, 0, 1, 1)]


# --------------------------------------------------------------------------
# draw.icon
# --------------------------------------------------------------------------

def test_an_icon_moves_with_its_origin(rec):
    D.icon(rec, "check", 0.0, 0.0, 16.0, (1, 1, 1, 1))
    a = [c for c in rec.calls if c[0] == "path_line_to"]
    rec.calls.clear()
    D.icon(rec, "check", 5.0, 0.0, 16.0, (1, 1, 1, 1))
    b = [c for c in rec.calls if c[0] == "path_line_to"]
    assert a and [p[1][0][0] + 5.0 for p in a] == \
        pytest.approx([p[1][0][0] for p in b])


def test_an_icon_is_scaled_and_stroked_for_its_own_size(rec):
    D.icon(rec, "check", 0.0, 0.0, 24.0, (1, 1, 1, 1))
    D.icon(rec, "check", 0.0, 0.0, 12.0, (1, 1, 1, 1), width=3.0)
    w = [c[2]["thickness"] for c in rec.calls if c[0] == "path_stroke"]
    assert w == [D.ICON_STROKE, 1.5]


def test_an_unknown_or_invisible_icon_draws_nothing(rec):
    assert D.icon(rec, "no-such-icon", 0, 0, 16, (1, 1, 1, 1)) is False
    assert D.icon(rec, "check", 0, 0, 16, (1, 1, 1, 0)) is False
    assert rec.calls == []


# --------------------------------------------------------------------------
# menu.measure
# --------------------------------------------------------------------------

def _ui():
    return SimpleNamespace(faces={}, anim=SimpleNamespace(store={}))


def test_a_menu_is_remeasured_when_an_item_changes_in_place():
    """The memo is keyed on the fields `measure` reads, not on the list, so
    an item edited where it stands is not measured as it was."""
    ui = _ui()
    items = [M.Item("a", "Open"), M.Item("b", "Copy")]
    w0, h0 = M.measure(ui, items, min_w=0.0)
    items[1].label = "Copy the whole Schlafli symbol"
    w1, h1 = M.measure(ui, items, min_w=0.0)
    assert w1 > w0 and h1 == h0
    items.append(M.sep())
    assert M.measure(ui, items, min_w=0.0)[1] > h1
    assert M.measure(ui, items, min_w=400.0)[0] == 400.0 - 2 * M.PAD


# --------------------------------------------------------------------------
# dashboard._laid_out
# --------------------------------------------------------------------------

def test_paints_layout_memo_is_lay_out_and_follows_a_resize():
    import dashboard as DB
    for args in ((1440, 1100, 0.0), (1100, 800, 0.0), (1440, 1100, -120.0)):
        assert DB._laid_out(*args) == DB.lay_out(args[0], args[1],
                                                 body_dy=args[2])
    assert DB._laid_out(1440, 1100, 0.0).stats != \
        DB._laid_out(1100, 800, 0.0).stats


# --------------------------------------------------------------------------
# draw.label - needs the faces, so GL
# --------------------------------------------------------------------------

class Tap:
    """Forward to a real draw list, recording `add_text`."""

    def __init__(self, dl):
        self.dl, self.texts = dl, []

    def add_text(self, *a):
        self.texts.append((a[0].x, a[0].y, a[1], a[2]))
        self.dl.add_text(*a)

    def __getattr__(self, name):
        return getattr(self.dl, name)


def test_a_replayed_label_is_the_label_and_takes_its_colour_live():
    """The second of two identical calls replays the first's placement. It
    must put every run where the first did - and draw in the colour it is
    handed NOW, under the style alpha in force now: `begin_disabled` halves
    that alpha, and a colour baked into the memo would ignore it."""
    from test_interaction import _gl_or_skip, one_widget
    _gl_or_skip()
    from imgui_bundle import imgui
    got = {}

    def paint(ui):
        tap = Tap(ui.dl)
        args = (13.25, 40.0, "Each frequency band drives one rotation plane",
                ui.faces, "regular", 13)
        kw = {"baseline_box": 18, "max_w": 180.0}
        D._LABELS.clear()
        w0 = D.label(tap, *args, (1, 0, 0, 1), **kw)        # computed
        w1 = D.label(tap, *args, (0, 0, 1, 1), **kw)        # replayed
        imgui.begin_disabled()
        D.label(tap, *args, (0, 0, 1, 1), **kw)             # replayed, dimmed
        imgui.end_disabled()
        got.update(w=(w0, w1), texts=tap.texts,
                   red=D._u32((1, 0, 0, 1)), blue=D._u32((0, 0, 1, 1)))

    one_widget("light", paint, 1)
    t = got["texts"]
    assert got["w"][0] == got["w"][1]
    n = len(t) // 3
    assert n >= 2 and len(t) == 3 * n, t
    first, again, dim = t[:n], t[n:2 * n], t[2 * n:]
    assert [(x, y, s) for x, y, _c, s in first] == \
        [(x, y, s) for x, y, _c, s in again] == \
        [(x, y, s) for x, y, _c, s in dim]
    assert all(c == got["red"] for *_, c, _s in first)
    assert all(c == got["blue"] for *_, c, _s in again)
    assert all((c >> 24) < (got["blue"] >> 24) for *_, c, _s in dim)
    assert first[-1][3].endswith("…")      # max_w fitted it


def test_a_label_moves_when_its_box_does():
    """A scroll moves every label's y: the memo must not hand back the old
    baseline."""
    from test_interaction import _gl_or_skip, one_widget
    _gl_or_skip()
    got = {}

    def paint(ui):
        tap = Tap(ui.dl)
        for y in (40.0, 27.0, 40.0):
            D.label(tap, 10.0, y, "Cutoff", ui.faces, "medium", 13,
                    (0, 0, 0, 1), baseline_box=24)
        got["ys"] = [r[1] for r in tap.texts]

    one_widget("light", paint, 1)
    ys = got["ys"]
    n = len(ys) // 3
    assert ys[:n] == ys[2 * n:] and all(a - b == 13.0 for a, b in
                                        zip(ys[:n], ys[n:2 * n]))


def test_a_closed_menu_is_still_measured():
    """Not an accident to tidy away. Measuring "⌘C" bakes DejaVu's
    command key into the font atlas, and WHEN that first happens decides
    where later glyphs are packed: skipping the measure for closed menus
    moved 30 contact-sheet pixels by up to 107 levels (RETRO row 71). The
    memo makes the repeats free; the first measure has to stay."""
    from test_interaction import _gl_or_skip, one_widget
    _gl_or_skip()
    seen = {}

    def paint(ui):
        M.popup(ui, "##never.opened", [M.Item("c", "Copy", shortcut="⌘C")])
        seen["memo"] = dict(ui.anim.store.get("menu.measure", {}))

    one_widget("light", paint, 1)
    assert len(seen["memo"]) == 1
