"""The SEQ page — the step sequencer and its envelopes (sequencer.py,
envelope.py; plan 31 U).

Top to bottom:

  seq   ◀ preset ▶ …     the transport: run · span · restart, the beat
                         light and the playhead's step on one line; length,
                         swing and gate as three half faders on the next
        the grid         five lanes × eight steps, the APC40's clip grid on
                         screen in its LED palette: a step on is green, on
                         in a muted lane red, a lit step under the playhead
                         yellow; the playhead's column is tinted and framed
                         in the one red. Columns past `length` are dimmed
                         and take no click. The step numbers over the grid
                         set the length (the APC's clip stop k). On the
                         left of each row: the lane's number (a click
                         selects the lane), its mute, and the envelope it
                         fires (`seq.<l>.env`, a picker over the bank)
  envs  ◀ preset ▶ …     a strip per envelope, by id — the five lane
                         envelopes, then any extras. Every strip but one is
                         folded to half a line, two to a row (a thumbnail of
                         the shape, the name, the live level, a chevron) —
                         so the default page fits without a scroll; the open one is
                         the selected lane's envelope unless another was
                         opened since. It holds the AHDSR shape drawn from
                         the current knobs with a dot at the live level,
                         mode · sync · retrig, and A/H, D/S, R/curve,
                         amount/velocity as half faders. `+ env` adds an
                         extra (cap 16) and `×`, on extras only, removes
                         one — each an undo step; envelopes 1–5 never go.

Every step, mute, binding and knob is a registry param, drawn with the
panel's own widgets or wired to its menu (`Panel._ctx`), so a click is an
ordinary param write — undo sees it — and right-click → Learn works on a
cell like on any fader. A function over the Panel, like ui_lfo: no state of
its own but the selected lane (`panel._seq_lane`) and an opened envelope
(`panel._seq_env`), kept for the session and never saved; a save of this
file lands live (hotreload.MODULES). Without a sequencer and envelopes
attached (a Panel built without app.py) the page says so and draws nothing
else.

Per frame the grid is 40 invisible buttons and as many filled rects; the
open envelope's shape is about 80 points and each folded one 17, so even
sixteen envelopes stay cheap.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui, ui_lfo, undo
from .envelope import (
    ATTACK,
    DECAY,
    HOLD,
    IDLE,
    LANE_ENVS,
    ONE_SHOT,
    RELEASE,
    STAGES,
    SUSTAIN,
    T_LO,
    shape,
)
from .envelope import GROUP as ENV_GROUP
from .sequencer import GROUP as SEQ_GROUP
from .view import RED as RED_RGB

CELL = 48.0           # a step cell's height, and its width where the page has room
GAP = 4.0             # between cells
HEAD_H = 18.0         # the step-number row over the grid
LANE_W = 72.0         # the row-label column: lane · mute over the env picker
SPAN_W = 96.0         # the span picker
SCOPE_W = 104.0       # the open envelope's shape
ROW_LABEL_W = 44.0    # a half fader's label column on an envelope strip
STAGE_SAMPLES = 24    # per curved stage of the open shape
THUMB_W = 48.0        # a folded strip's thumbnail (its height is the frame's)
THUMB_SAMPLES = 4     # per curved stage of a thumbnail
NAME_W = 52.0         # a folded strip's name cell; its level bar takes the rest
FOLD_COLS = 2         # folded strips to a line
SUS_SHARE = 0.25      # the sustain plateau's width in the drawing, of the other stages

# the APC40's LED colours (ui_desk._LED), so the screen and the pads agree
GREEN = imgui.ImVec4(0.30, 0.85, 0.40, 1.0)
YELLOW = imgui.ImVec4(0.95, 0.80, 0.25, 1.0)
OFF = imgui.ImVec4(0.13, 0.13, 0.145, 1.0)        # the frame ground
OFF_HOV = imgui.ImVec4(0.20, 0.20, 0.22, 1.0)
TINT = imgui.ImVec4(*RED_RGB, 0.20)   # the playhead's column
PAST_ALPHA = 0.30     # a column past `length`

# what a cell shows (cell_state)
OFF_S, ON_S, MUTED_S, PLAY_S = "off", "on", "muted", "play"


def page(panel, dt: float) -> None:
    seq, envs = getattr(panel, "seq", None), getattr(panel, "envs", None)
    have = seq is not None and envs is not None and f"{SEQ_GROUP}.run" in panel.reg
    panel._section("seq", SEQ_GROUP if have else None,
                   note="click a step · right-click Learn")
    if not have:
        imgui.text_disabled("no sequencer — app.py wires sequencer.py and envelope.py")
        return
    _transport(panel, seq)
    _grid(panel, seq, envs)
    panel._section("envelopes", ENV_GROUP, note="lanes 1–5 fire env 1–5")
    sel = open_env(panel, seq, envs)
    ids = envs.ids()
    k = ids.index(sel) if sel in ids else len(ids)
    _folds(panel, seq, envs, ids[:k], "before")
    if sel is not None:
        _strip(panel, seq, envs, sel)
    _folds(panel, seq, envs, ids[k + 1:], "after")


# ---- the selection: the Panel's, never the preset's ----

def selected_lane(panel, seq) -> int:
    """The selected lane, 0-based: the one picked this session, else lane 1."""
    li = getattr(panel, "_seq_lane", 0)
    if not isinstance(li, int) or not 0 <= li < len(seq.lanes):
        li = panel._seq_lane = 0
    return li


def select_lane(panel, li: int) -> None:
    """Lane `li` (0-based) is selected, and its envelope's strip opens."""
    panel._seq_lane = li
    panel._seq_env = None


def open_env(panel, seq, envs) -> int | None:
    """The open envelope strip's id: one opened by hand this session, else
    the selected lane's envelope, else the first."""
    ids = envs.ids()
    n = getattr(panel, "_seq_env", None)
    if n not in ids:
        n = seq.lanes[selected_lane(panel, seq)].env
    if n not in ids:
        n = ids[0] if ids else None
    return n


def open_strip(panel, n: int) -> None:
    panel._seq_env = n


# ---- the grid's actions ----

def toggle_step(panel, seq, li: int, si: int) -> bool:
    """A click on lane `li`'s step `si` (both 0-based): the step's toggle
    param flips, so undo and a performer's ownership see an ordinary
    write. A column past `length` is inert: False, nothing written."""
    if not 0 <= si < seq.length:
        return False
    panel.reg[f"{SEQ_GROUP}.{li + 1}.{si + 1}"].toggle()
    return True


def cell_state(seq, li: int, si: int) -> tuple[str, bool]:
    """What the cell shows: (off | on | muted | play, under the playhead).
    `play` is a lit step the playhead is on — the yellow pad."""
    lane = seq.lanes[li]
    head = seq.playhead is not None and si == seq.playhead and si < seq.length
    if lane.steps[si] <= 0.0:
        return OFF_S, head
    if lane.mute:
        return MUTED_S, head
    return (PLAY_S if head else ON_S), head


def fill(state: str) -> imgui.ImVec4 | None:
    """A cell's colour: the APC's LED for a lit state, None for off."""
    if state == ON_S:
        return GREEN
    if state == PLAY_S:
        return YELLOW
    if state == MUTED_S:
        return ui.RED
    return None


def add_env(panel, envs) -> int | None:
    """"+ env": an extra envelope at one past the highest id, its knobs
    declared; one undo step. None at the cap."""
    if not envs.can_add():
        return None
    undo.push("add envelope")
    n = envs.add()
    panel._seq_env = n                # the new one opens, where it can be seen
    return n


def remove_env(panel, envs, n: int) -> bool:
    """The ×: extra envelope `n` and its knobs go; a lane pointed at it
    fires nothing until it is pointed elsewhere. One undo step. A lane
    envelope, 1–5, is refused: False, and no step."""
    if n in LANE_ENVS or n not in envs:
        return False
    undo.push(f"delete envelope {n}")
    return envs.remove(n)


# ---- the transport ----

def _transport(panel, seq) -> None:
    g = SEQ_GROUP
    panel._lit_button(f"{g}.run", "run", bool(seq.run))
    imgui.same_line()
    panel._combo(f"{g}.span", SPAN_W)
    imgui.same_line()
    panel._button(f"{g}.trigger", "restart", small=True)
    clock = getattr(panel, "clock", None)
    step = "stopped" if seq.playhead is None else f"step {seq.playhead + 1}/{seq.length}"
    w = ui._micro_width(step) + (2 * ui_lfo.BEAT_R + 10 + 4 * 12 + 8 if clock else 0)
    imgui.same_line(imgui.get_content_region_avail().x + imgui.get_cursor_pos_x() - w - 4)
    h = imgui.get_frame_height()
    if clock is not None:
        ui_lfo._beats(clock, h)
        imgui.same_line()
    imgui.begin_group()
    imgui.dummy(imgui.ImVec2(0, max(0.0, (h - ui.FONT_MICRO) / 2 - 4)))
    ui._micro(step, ui.TEXT if seq.playhead is not None else ui.FAINT)
    imgui.end_group()
    if imgui.begin_table("##seqknobs", 3, imgui.TableFlags_.sizing_stretch_same):
        imgui.table_next_column()
        panel.half(f"{g}.length", "length", label_w=ui_lfo.ROW_LABEL_W)
        imgui.table_next_column()
        panel.half(f"{g}.swing", "swing", label_w=ui_lfo.ROW_LABEL_W)
        imgui.table_next_column()
        # how long a step holds a gate-mode envelope (P1), a fraction of a step
        panel.half(f"{g}.gate", "gate", label_w=ui_lfo.ROW_LABEL_W)
        imgui.end_table()


# ---- the grid ----

def _grid(panel, seq, envs) -> None:
    lanes, steps = len(seq.lanes), len(seq.lanes[0].steps)
    avail = imgui.get_content_region_avail().x
    cw = max(16.0, min(CELL, (avail - LANE_W - GAP * steps) / steps))
    ch = CELL
    o = imgui.get_cursor_screen_pos()
    x0 = o.x + LANE_W + GAP
    gy = o.y + HEAD_H + GAP
    dl = imgui.get_window_draw_list()
    head = seq.playhead if seq.playhead is not None and seq.playhead < seq.length else None
    # the playhead's column, under the cells: a red tint and a red frame
    if head is not None:
        cx = x0 + head * (cw + GAP)
        a = imgui.ImVec2(cx - 2, o.y)
        b = imgui.ImVec2(cx + cw + 2, gy + lanes * (ch + GAP) - GAP + 2)
        dl.add_rect_filled(a, b, ui.u32(TINT), 6.0)
        dl.add_rect(a, b, ui.u32(ui.RED), 6.0, 2.0)
    _heads(panel, seq, x0, o.y, cw)
    sel = selected_lane(panel, seq)
    for li in range(lanes):
        y = gy + li * (ch + GAP)
        _lane_label(panel, seq, envs, li, o.x, y, ch, li == sel)
        for si in range(steps):
            _cell(panel, seq, li, si, x0 + si * (cw + GAP), y, cw, ch)
    # the grid's extent as one item, so the page lays out below it
    imgui.set_cursor_screen_pos(o)
    imgui.dummy(imgui.ImVec2(LANE_W + GAP + steps * (cw + GAP) - GAP,
                             HEAD_H + GAP + lanes * (ch + GAP) - GAP))


def _heads(panel, seq, x0: float, y: float, cw: float) -> None:
    """The step numbers: a click on k sets the length to k (clip stop k)."""
    a = panel.reg[f"{SEQ_GROUP}.length"]
    dl = imgui.get_window_draw_list()
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    for si in range(len(seq.lanes[0].steps)):
        x = x0 + si * (cw + GAP)
        imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
        imgui.pop_font()
        hit = imgui.invisible_button(f"##seq.head.{si + 1}", imgui.ImVec2(cw, HEAD_H))
        hov = imgui.is_item_hovered()
        if hov:
            imgui.set_tooltip(f"length {si + 1}: the pattern wraps after step {si + 1}")
        panel._ctx(a, f".{si + 1}")
        imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
        if hit:
            a.set(si + 1)
        t = str(si + 1)
        col = ui.TEXT if hov else ui.DIM if si < seq.length else ui.LINE
        tw = imgui.calc_text_size(t).x
        dl.add_text(imgui.ImVec2(x + (cw - tw) / 2, y + (HEAD_H - ui.FONT_MICRO) / 2 - 1),
                    ui.u32(col), t)
    imgui.pop_font()


def _lane_label(panel, seq, envs, li: int, x: float, y: float, h: float,
                sel: bool) -> None:
    """Lane li's label: its number (select) and mute over its envelope picker."""
    lane = seq.lanes[li]
    p = f"{SEQ_GROUP}.{li + 1}"
    ch = ui.FONT_BASE + 2 * ui.CHIP_PAD.y
    top = y + (h - 2 * ch - 4) / 2
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, top))
    if ui.lit_chip(f"{li + 1}##{p}.sel", sel):
        select_lane(panel, li)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"Lane {li + 1} → env {lane.env}: click to select it and open "
                          "its envelope")
    imgui.same_line(0, 4)
    panel._lit_button(f"{p}.mute", "M", lane.mute)
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, top + ch + 4))
    _env_picker(panel, envs, f"{p}.env", lane.env)


def _env_picker(panel, envs, pid: str, cur: int) -> None:
    """`seq.<l>.env` as a picker over the bank's ids; a lane pointed at a
    removed extra says so."""
    a = panel.reg[pid]
    p = panel._real(a)
    gone = cur not in envs
    imgui.push_style_var(imgui.StyleVar_.frame_padding, ui.CHIP_PAD)
    imgui.set_next_item_width(LANE_W - 4)
    if gone:
        imgui.push_style_color(imgui.Col_.text, ui.WARN)
    opened = imgui.begin_combo(f"##{pid}", f"env {cur}",
                               imgui.ComboFlags_.no_arrow_button)
    if gone:
        imgui.pop_style_color()
    imgui.pop_style_var()
    if opened:
        for n in envs.ids():
            if imgui.selectable(f"env {n}##{pid}.{n}", n == cur)[0] and n != cur:
                p.set(n)
        imgui.end_combo()
    panel._tip(a, (f"env {cur} is gone: this lane fires nothing until it is pointed at "
                   "another") if gone else None)
    panel._ctx(a)
    panel._learn_frame(a)
    panel._mod_dot(p)


def _cell(panel, seq, li: int, si: int, x: float, y: float, w: float, h: float) -> None:
    pid = f"{SEQ_GROUP}.{li + 1}.{si + 1}"
    a = panel.reg[pid]
    past = si >= seq.length
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    if past:
        imgui.begin_disabled()
    hit = imgui.invisible_button(f"##{pid}", imgui.ImVec2(w, h))
    hov = imgui.is_item_hovered()
    if past:
        imgui.end_disabled()
    else:
        panel._tip(a, f"lane {li + 1} step {si + 1} — click to toggle")
        panel._ctx(a)
    state, _head = cell_state(seq, li, si)
    col = fill(state)
    if col is None:
        col = OFF_HOV if hov and not past else OFF
    if past:
        col = imgui.ImVec4(col.x, col.y, col.z, PAST_ALPHA)
    imgui.get_window_draw_list().add_rect_filled(
        imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h), ui.u32(col), 6.0)
    panel._learn_frame(a)
    panel._mod_dot(panel._real(a))
    if hit and not past:
        toggle_step(panel, seq, li, si)


# ---- one envelope ----

def _lanes_of(seq, n: int) -> str:
    on = [str(i + 1) for i, lane in enumerate(seq.lanes) if lane.env == n]
    if not on:
        return "no lane"
    return ("lane " if len(on) == 1 else "lanes ") + ",".join(on)


def _strip(panel, seq, envs, n: int) -> None:
    env = envs.voice(n)
    p = f"{ENV_GROUP}.{n}"
    extra = n not in LANE_ENVS
    imgui.push_id(p)
    ui._micro(f"env {n}")
    imgui.same_line(SCOPE_W + imgui.get_style().item_spacing.x)
    ui._micro(f"{_lanes_of(seq, n)} · {STAGES[env.stage]} · out {env.out:.2f}", ui.FAINT)
    # the head's chips, flush right on the label line: `+ env` lives here,
    # since there is always an open strip (the lane envelopes never go)
    chips = ["+ env", "gate"] + (["×"] if extra else [])
    imgui.same_line(imgui.get_content_region_avail().x + imgui.get_cursor_pos_x()
                    - ui.chip_w(*chips) - 4)
    _add_chip(panel, envs)
    imgui.same_line()
    panel._lit_button(f"{p}.gate", "gate", bool(env.held))
    if extra:
        imgui.same_line()
        if ui.chip(f"×##{p}.del"):
            remove_env(panel, envs, n)
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"Remove env {n} — the others keep their numbers; a lane "
                              "on it fires nothing")
    rows = 5
    fh = imgui.get_frame_height_with_spacing()
    _scope(env, rows * fh - imgui.get_style().item_spacing.y)
    imgui.same_line()
    imgui.begin_group()
    sp = imgui.get_style().item_spacing.x
    cw = (imgui.get_content_region_avail().x - 2 * sp) / 3
    panel._combo(f"{p}.mode", cw)
    imgui.same_line()
    panel._combo(f"{p}.sync", cw)
    imgui.same_line()
    panel._combo(f"{p}.retrig", cw)
    for k, (l_id, l_lab, r_id, r_lab) in enumerate((
            ("attack", "A", "hold", "H"), ("decay", "D", "sustain", "S"),
            ("release", "R", "curve", "crv"), ("amount", "amt", "velocity", "vel"))):
        if imgui.begin_table(f"##env{k}", 2, imgui.TableFlags_.sizing_stretch_same):
            imgui.table_next_column()
            panel.half(f"{p}.{l_id}", l_lab, label_w=ROW_LABEL_W)
            imgui.table_next_column()
            panel.half(f"{p}.{r_id}", r_lab, label_w=ROW_LABEL_W)
            imgui.end_table()
    imgui.end_group()
    imgui.pop_id()


def _add_chip(panel, envs) -> None:
    """`+ env`, greyed out at the cap with the reason on hover."""
    can = envs.can_add()
    imgui.begin_disabled(not can)
    if ui.chip("+ env##env.add") and can:
        add_env(panel, envs)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        imgui.set_tooltip(add_tip(envs))


def add_tip(envs) -> str:
    """`+ env`'s tooltip: the envelope it would add, or the bank's reason
    not (`modbank.Bank.refusal`)."""
    why = envs.refusal()
    if why is not None:
        return why + (" — remove an extra with its × to add another"
                      if len(envs) >= envs.MAX else "")
    return (f"Another envelope, env {envs.next_id()} (up to {envs.MAX}); "
            "point a lane at it with its picker")


def _folds(panel, seq, envs, ids, key: str) -> None:
    """The folded strips, two to a line: half the rows a strip each would take."""
    if not ids:
        return
    if imgui.begin_table(f"##envfold.{key}", FOLD_COLS, imgui.TableFlags_.sizing_stretch_same):
        for n in ids:
            imgui.table_next_column()
            _folded(panel, seq, envs, n)
        imgui.end_table()


def _folded(panel, seq, envs, n: int) -> None:
    """Half a line: thumbnail · name · level bar · chevron; a click opens it."""
    env = envs.voice(n)
    p = f"{ENV_GROUP}.{n}"
    imgui.push_id(p)
    h = imgui.get_frame_height()
    sp = imgui.get_style().item_spacing.x
    pos = imgui.get_cursor_screen_pos()
    w = max(THUMB_W + NAME_W + 2 * sp, imgui.get_content_region_avail().x - h - sp)
    hit = imgui.invisible_button(f"##{p}.row", imgui.ImVec2(w, h))
    hov = imgui.is_item_hovered()
    dl = imgui.get_window_draw_list()
    if hov:
        dl.add_rect_filled(pos, imgui.ImVec2(pos.x + w, pos.y + h),
                           imgui.get_color_u32(imgui.Col_.button_hovered), 4.0)
        imgui.set_tooltip(f"env {n} ({_lanes_of(seq, n)}): {STAGES[env.stage]}, "
                          f"out {env.out:.2f} — click to open it")
    dl.add_rect(pos, imgui.ImVec2(pos.x + THUMB_W, pos.y + h), ui.u32(ui.LINE))
    _shape(dl, env, pos.x, pos.y + 2, THUMB_W, h - 4, THUMB_SAMPLES, 1.0, 2.5)
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    dl.add_text(imgui.ImVec2(pos.x + THUMB_W + sp, pos.y + (h - ui.FONT_MICRO) / 2 - 1),
                ui.u32(ui.TEXT if hov else ui.DIM), f"env {n}")
    imgui.pop_font()
    bx = THUMB_W + sp + NAME_W
    _level_bar(dl, env.out, pos.x + bx, pos.y, max(w - bx, 0.0), h)
    imgui.same_line(0, sp)
    if imgui.arrow_button(f"##{p}.open", imgui.Dir.right) or hit:
        open_strip(panel, n)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"Open env {n} (the open one folds)")
    imgui.pop_id()


def _level_bar(dl, out: float, x0: float, y0: float, w: float, h: float) -> None:
    pad = h * 0.25
    a, b = imgui.ImVec2(x0, y0 + pad), imgui.ImVec2(x0 + w, y0 + h - pad)
    dl.add_rect_filled(a, b, ui.u32(ui.LINE), 3.0)
    v = min(max(out, 0.0), 1.0)
    if v > 0:
        dl.add_rect_filled(a, imgui.ImVec2(x0 + w * v, b.y), ui.u32(ui.RED), 3.0)


# ---- the shape: drawn from the knobs, the dot from the voice ----

def segments(env) -> tuple[float, float, float, float, float]:
    """The drawing's stage widths (A, H, D, S, R) in the voice's time
    units: the sustain is a plateau a quarter as wide as the rest, none in
    one-shot (decay's end releases from the sustain level)."""
    a = max(env.attack, 0.0)
    h = env.hold if env.hold > T_LO else 0.0
    d, r = max(env.decay, 0.0), max(env.rel, 0.0)
    s = 0.0 if env.mode == ONE_SHOT else SUS_SHARE * (a + h + d + r)
    return a, h, d, s, r


def now_at(env) -> float | None:
    """Where the voice is, in the drawing's time units; None at rest."""
    a, h, d, s, r = segments(env)
    st, p = env.stage, env.p
    if st == ATTACK:
        return a * p
    if st == HOLD:
        return a + h * p
    if st == DECAY:
        return a + h + d * p
    if st == SUSTAIN:
        return a + h + d + s / 2
    if st == RELEASE:
        return a + h + d + s + r * p
    return None


def _shape(dl, env, x0: float, y0: float, w: float, h: float, n: int,
           thick: float, dot: float) -> None:
    """The AHDSR polyline at the current knobs (peak = amount), and the
    live level as a red dot where the voice is."""
    a, hd, d, s, r = segments(env)
    total = a + hd + d + s + r
    if total <= 0.0:
        total = 1.0
    sx, c, sus, amt = w / total, env.curve, env.sustain, env.amount
    pts = [imgui.ImVec2(x0, y0 + h)]

    def y(level):
        return y0 + h * (1.0 - min(max(level * amt, 0.0), 1.0))
    for k in range(1, n + 1):
        f = k / n
        pts.append(imgui.ImVec2(x0 + sx * a * f, y(shape(f, c))))
    t = a + hd
    pts.append(imgui.ImVec2(x0 + sx * t, y(1.0)))
    for k in range(1, n + 1):
        f = k / n
        pts.append(imgui.ImVec2(x0 + sx * (t + d * f), y(1.0 + (sus - 1.0) * shape(f, c))))
    t += d + s
    pts.append(imgui.ImVec2(x0 + sx * t, y(sus)))
    for k in range(1, n + 1):
        f = k / n
        pts.append(imgui.ImVec2(x0 + sx * (t + r * f), y(sus * (1.0 - shape(f, c)))))
    dl.add_polyline(pts, ui.u32(ui_lfo.WAVE), thick, 0)   # read late: ui_lfo → ui → ui_seq is a cycle
    at = now_at(env)
    if at is not None and env.stage != IDLE:
        dl.add_circle_filled(
            imgui.ImVec2(x0 + sx * at, y0 + h * (1.0 - min(max(env.out, 0.0), 1.0))),
            dot, ui.u32(ui.RED))


def _scope(env, height: float) -> None:
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    x0, y0 = pos.x, pos.y
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x0 + SCOPE_W, y0 + height),
                ui.u32(ui.LINE))
    ym = y0 + 2 + (height - 4) * (1.0 - env.sustain * env.amount)
    dl.add_line(imgui.ImVec2(x0, ym), imgui.ImVec2(x0 + SCOPE_W, ym), ui.u32(ui.LINE))
    _shape(dl, env, x0 + 2, y0 + 2, SCOPE_W - 4, height - 4, STAGE_SAMPLES, 1.2, 3.0)
    imgui.dummy(imgui.ImVec2(SCOPE_W, height))
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"the shape at the knobs (peak {env.amount:.2f}, sustain "
                          f"{env.sustain:.2f}); the dot is the level now "
                          f"({env.out:.2f}, {STAGES[env.stage]})")
