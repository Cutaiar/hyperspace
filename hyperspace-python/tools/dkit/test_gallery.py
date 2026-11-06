"""The Gallery tab: that it plans, that it paints, and that the two agree.

The thing worth testing about a contact sheet is not any one specimen - every
component has its own tests - but that the page is HONEST: the height it
tells the scroll area is the height it draws, every specimen lands inside its
card, and nothing silently drops off the end. Those are exactly the failures
that made the old hand-sized dashboard put rows outside the card that was
supposed to hold them.
"""

from __future__ import annotations

from contextlib import contextmanager

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


@contextmanager
def _booted(DB):
    """A window, its context and the real faces — torn down before anything
    else runs.

    `plan` needs text widths and a width needs a font, so a layout question
    cannot be answered without a renderer. What it must not do is LEAVE one:
    the first version of this file called `DB._boot(...)` in every test and
    never shut any of them down, which left the current GL context pointing
    at a dead window. Later `render()` calls in the same xdist worker
    stopped receiving clicks and keys, and tests with nothing to do with the
    Gallery failed depending on how pytest happened to distribute them.

    It cannot be a module fixture either, because `render()` ends with
    `glfw.terminate()` and that destroys this context's font atlas — a
    `faces` held across a render asserts inside `calc_text_size`. So: boot,
    measure, tear down, and only then render.
    """
    from imgui_bundle import imgui
    import glfw
    win, impl, _io, fc, _grad = DB._boot("dark", 320, 240, visible=False,
                                         retina=False)
    try:
        yield fc
    finally:
        impl.shutdown()
        imgui.destroy_context()
        glfw.terminate()


def _plan(DB, w, theme="dark"):
    """The plan at content width `w`, with the renderer already gone."""
    with _booted(DB) as fc:
        return CG.plan(w, fc, theme)


# --------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------
def test_every_section_is_built_and_named(DB):
    total, secs = _plan(DB, 1000.0)
    assert len(secs) == len(CG.SECTIONS)
    titles = [t for t, _b, _h, _p in secs]
    assert len(set(titles)) == len(titles), f"duplicate titles: {titles}"
    for t, b, _h, _p in secs:
        assert t and b, f"{t!r} has no title or no blurb"


def test_the_height_is_the_sum_of_the_cards_and_the_gaps(DB):
    """The number handed to the scroll area IS the number drawn. They come
    out of one call for exactly this reason."""
    total, secs = _plan(DB, 1000.0)
    want = sum(h for _t, _b, h, _p in secs) + CG.GAP * (len(secs) - 1)
    assert total == pytest.approx(want)


def test_no_specimen_escapes_its_card(DB):
    """A card is as tall as what wrapped into it. If a specimen's bottom is
    below the card's content box, the card was sized from something other
    than its content - which is the bug intrinsic sizing exists to stop."""
    _total, secs = _plan(DB, 1000.0)
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
    inner = 420.0                      # deliberately narrow
    _total, secs = _plan(DB, inner + 2 * CG.PAD)
    for title, _b, _h, placed in secs:
        for cap, sx, _sy, sw, _sh, _d in placed:
            # a single specimen wider than the row is allowed to overhang -
            # nothing can be done about that - but one that STARTED past the
            # edge means the wrap did not fire
            assert sx < inner, f"{title}/{cap} starts at {sx} in {inner}"


def test_a_narrower_page_is_a_taller_page(DB):
    """Wrapping is real: the same specimens in less width take more rows."""
    wide, _ = _plan(DB, 1200.0)
    narrow, _ = _plan(DB, 500.0)
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


# --------------------------------------------------------------------------
# the one that matters
# --------------------------------------------------------------------------
def _specimen_centres(DB, w, theme="dark"):
    """Where every specimen's hit target is, in screen coordinates, on a
    window tall enough to show the whole sheet with no scrolling."""
    gw = (w - DB.SIDEBAR_W) - 2 * DB.GUT
    _total, secs = _plan(DB, gw, theme)
    ox, oy = DB.SIDEBAR_W + DB.GUT, DB.HEADER_H + DB.GUT
    head = (T.CARD_TITLE_H + T.CARD_TITLE_GAP + T.CARD_DESC_H
            + T.CARD_HEAD_GAP)
    y, out = oy, []
    for title, _blurb, card_h, placed in secs:
        by = y + CG.PAD + head
        for cap, sx, sy, sw, sh, _draw in placed:
            out.append((title, cap,
                        ox + CG.PAD + sx + sw / 2,
                        by + sy + CG.CAP_H + CG.CAP_GAP + sh / 2))
        y += card_h + CG.GAP
    return out


def test_every_specimen_can_be_clicked(DB):
    """Click all of them. This is the test that was missing.

    The Gallery exists because the pixel diff "cannot see that a control is
    unclickable" - that sentence is in the module docstring - and the first
    version of this file tested the page by rendering it and asserting it was
    not blank, which is exactly how the pixel diff would have tested it. The
    Select specimens were handing `interact.select` a list of `str` where it
    wants `menu.Item`, and every one of them raised
    `'str' object has no attribute 'kind'` the moment anybody clicked. Nothing
    here caught it; the person looking at it did.

    So: a window tall enough to need no scrolling, then one long script that
    presses each specimen in turn and clicks away to dismiss whatever opened.
    A crash anywhere in it fails the test, and the frame at the end proves
    the page survived.
    """
    import numpy as np
    TALL = 2600
    spots = _specimen_centres(DB, W)
    assert len(spots) > 60, f"only {len(spots)} specimens - did a section die?"

    r = DB.lay_out(W, TALL)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    gx, gy = nx + nw / 2, ny + nh / 2
    script = [(10, 10, False)] * 6 + [(gx, gy, False)] * 4 \
        + [(gx, gy, True)] * 3 + [(gx, gy, False)] * 10
    clicked = 0
    for _title, _cap, sx, sy in spots:
        if sy > TALL - 30:
            continue
        clicked += 1
        script += [(sx, sy, False)] * 3 + [(sx, sy, True)] * 2 \
            + [(sx, sy, False)] * 6
        # away, to dismiss anything that opened, so the next press is not
        # swallowed by a popup's click-outside
        script += [(6, TALL - 6, False)] * 3 + [(6, TALL - 6, True)] * 2 \
            + [(6, TALL - 6, False)] * 3
    assert clicked > 60, f"only {clicked} specimens were on screen"

    # keep="last": a 1440x2600 frame is 15 MB and this script drives well
    # over a thousand of them. The first version kept them all and the
    # kernel killed the worker.
    frames = DB.render("dark", W, TALL, script=script, keep="last")
    f = np.asarray(frames[-1])[:, :, :3].astype(int)
    body = f[DB.HEADER_H + 20:TALL - 20, DB.SIDEBAR_W + 20:W - 20]
    assert int(body.max() - body.min()) > 60, "the page died during the run"


def test_every_specimen_survives_a_right_click(DB):
    """The same sweep with the other button. A ContextMenu target is a whole
    region with smaller controls drawn on top of it, so a right-click can
    reach a widget that never expected one."""
    import numpy as np
    TALL = 2600
    spots = _specimen_centres(DB, W)
    r = DB.lay_out(W, TALL)
    nx, ny, nw, nh = r.nav[DB.NAV_GALLERY]
    gx, gy = nx + nw / 2, ny + nh / 2
    script = [(10, 10, False)] * 6 + [(gx, gy, False)] * 4 \
        + [(gx, gy, True)] * 3 + [(gx, gy, False)] * 10
    for _title, _cap, sx, sy in spots:
        if sy > TALL - 30:
            continue
        # (x, y, down, wheel, right)
        script += [(sx, sy, False, 0.0, False)] * 3
        script += [(sx, sy, False, 0.0, True)] * 2
        script += [(sx, sy, False, 0.0, False)] * 5
        script += [(6, TALL - 6, False)] * 2 + [(6, TALL - 6, True)] * 2 \
            + [(6, TALL - 6, False)] * 3
    frames = DB.render("dark", W, TALL, script=script, keep="last")
    f = np.asarray(frames[-1])[:, :, :3].astype(int)
    body = f[DB.HEADER_H + 20:TALL - 20, DB.SIDEBAR_W + 20:W - 20]
    assert int(body.max() - body.min()) > 60, "the page died during the run"
