"""The Gallery tab: that it plans, that it paints, and that the two agree.

The thing worth testing about a contact sheet is not any one specimen - every
component has its own tests - but that the page is HONEST: the height it
tells the scroll area is the height it draws, every specimen lands inside its
card, and nothing silently drops off the end. Those are exactly the failures
that made the old hand-sized dashboard put rows outside the card that was
supposed to hold them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tests"))

import comp_gallery as CG      # noqa: E402
import tokens as T             # noqa: E402

W, H = 1440, 1100


def _gl_or_skip():
    try:
        import gl_probe
    except ImportError:
        pytest.skip("gl_probe not importable")
    gl_probe.require()


@pytest.fixture(scope="module")
def DB():
    _gl_or_skip()
    import dashboard
    return dashboard


def _faces(DB):
    """Real faces, which `plan` needs because a caption reserves its own
    width and a width needs a font."""
    import draw as D
    from imgui_bundle import imgui
    win, impl, io, faces, grad = DB._boot("dark", 320, 240, visible=False,
                                          retina=False)
    return faces


# --------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------
def test_every_section_is_built_and_named(DB):
    faces = _faces(DB)
    total, secs = CG.plan(1000.0, faces, "dark")
    assert len(secs) == len(CG.SECTIONS)
    titles = [t for t, _b, _h, _p in secs]
    assert len(set(titles)) == len(titles), f"duplicate titles: {titles}"
    for t, b, _h, _p in secs:
        assert t and b, f"{t!r} has no title or no blurb"


def test_the_height_is_the_sum_of_the_cards_and_the_gaps(DB):
    """The number handed to the scroll area IS the number drawn. They come
    out of one call for exactly this reason."""
    faces = _faces(DB)
    total, secs = CG.plan(1000.0, faces, "dark")
    want = sum(h for _t, _b, h, _p in secs) + CG.GAP * (len(secs) - 1)
    assert total == pytest.approx(want)


def test_no_specimen_escapes_its_card(DB):
    """A card is as tall as what wrapped into it. If a specimen's bottom is
    below the card's content box, the card was sized from something other
    than its content - which is the bug intrinsic sizing exists to stop."""
    faces = _faces(DB)
    _total, secs = CG.plan(1000.0, faces, "dark")
    head = (T.CARD_TITLE_H + T.CARD_TITLE_GAP + T.CARD_DESC_H
            + T.CARD_HEAD_GAP)
    for title, _b, card_h, placed in secs:
        body = card_h - 2 * CG.PAD - head
        for cap, sx, sy, sw, sh, _draw in placed:
            bottom = sy + CG.CAP_H + CG.CAP_GAP + sh
            assert bottom <= body + 0.01, (
                f"{title}/{cap} reaches {bottom} in a {body} body")
            assert sx >= 0.0


def test_specimens_wrap_rather_than_running_off_the_right(DB):
    faces = _faces(DB)
    inner = 420.0                      # deliberately narrow
    _total, secs = CG.plan(inner + 2 * CG.PAD, faces, "dark")
    for title, _b, _h, placed in secs:
        for cap, sx, _sy, sw, _sh, _d in placed:
            # a single specimen wider than the row is allowed to overhang -
            # nothing can be done about that - but one that STARTED past the
            # edge means the wrap did not fire
            assert sx < inner, f"{title}/{cap} starts at {sx} in {inner}"


def test_a_narrower_page_is_a_taller_page(DB):
    """Wrapping is real: the same specimens in less width take more rows."""
    faces = _faces(DB)
    wide, _ = CG.plan(1200.0, faces, "dark")
    narrow, _ = CG.plan(500.0, faces, "dark")
    assert narrow > wide


# --------------------------------------------------------------------------
# driven
# --------------------------------------------------------------------------
def test_the_sidebar_switches_to_the_gallery_and_the_header_follows(DB):
    import numpy as np
    r = DB.lay_out(W, H)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    cx, cy = nx + nw / 2, ny + nh / 2
    script = [(10, 10, False)] * 6 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * 40
    frames = DB.render("dark", W, H, script=script)
    assert DB.render.last_state["nav"] == DB.NAV_GALLERY
    # the page is now taller than the window, which is what a contact sheet
    # of thirteen sections should be
    assert DB.render.last_state["page_max"] > H
    # and something was actually drawn in the body
    f = np.asarray(frames[-1])[:, :, :3].astype(int)
    body = f[DB.HEADER_H + 20:H - 20, DB.SIDEBAR_W + 20:W - 20]
    assert int(body.max() - body.min()) > 60, "the gallery body is blank"


def test_the_gallery_scrolls_to_its_end(DB):
    """It is longer than any window, so the page scroll has to reach the
    bottom - the thing that was broken when only the table scrolled."""
    script = []
    r = DB.lay_out(W, H)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    cx, cy = nx + nw / 2, ny + nh / 2
    script = [(10, 10, False)] * 6 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * 10
    script += [(W / 2, H / 2, False, -4.0)] * 80 + [(W / 2, H / 2, False)] * 10
    DB.render("dark", W, H, script=script)
    st = DB.render.last_state
    assert st["page_max"] > 0
    assert st["page_scroll"] == pytest.approx(st["page_max"], abs=1.0)


def test_both_themes_draw_it(DB):
    import numpy as np
    r = DB.lay_out(W, H)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    cx, cy = nx + nw / 2, ny + nh / 2
    script = [(10, 10, False)] * 6 + [(cx, cy, False)] * 4 \
        + [(cx, cy, True)] * 3 + [(cx, cy, False)] * 40
    for theme in ("light", "dark"):
        f = np.asarray(DB.render(theme, W, H, script=script)[-1])
        body = f[DB.HEADER_H + 20:H - 20, DB.SIDEBAR_W + 20:W - 20, :3]
        assert int(body.max()) - int(body.min()) > 60, f"{theme} is blank"
