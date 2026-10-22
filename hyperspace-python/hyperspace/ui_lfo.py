"""The LFO page — the tap-tempo clock and the LFOs (tempo.py, lfo.py).

Top to bottom:

  tempo  ◀ preset ▶ …    the clock strip: the BPM readout, a beat light
                         that flashes on every beat (the same predicate
                         as the APC's METRONOME LED), the bar's four
                         beats, then tap · trigger · nudge −/+ — the
                         trigger params as buttons — and the bpm and
                         nudge faders on one row
  lfos   ◀ preset ▶ …    a strip per LFO, by id (four by default, plan 31
                         B; `+ lfo` on the first strip's head adds one, a
                         strip's `×` removes it — each one undo step). Each:
                         a small scope of two cycles
                         of the shape at the current depth, a hairline
                         where the wave is now and a dot at the live
                         output; beside it shape · sync · reset on one
                         line, rate on the next, depth · phase on the
                         third — three rows, so four strips fit.

Above four LFOs (plan 31 U) every strip but one folds to a single line: a
thumbnail of one cycle, the name, the live output as a bar, and a chevron
that opens it. Exactly one strip is open at a time — the selected one,
kept on the Panel for the session and never saved; a new LFO is selected
as it is added. The full 129-point scope is drawn only on the open strip,
the folded ones cost a 17-point thumbnail each, so sixteen LFOs stay
cheap. The page child scrolls when the strips overflow it. At four or
fewer nothing folds and the page is what it always was.

The scope samples the shape function rather than keeping a history: the
wave is a closed form in the phase, so two cycles cost nothing and the
picture is exact. Random draws its held value as a flat line, which is
what the output is.

Every control is a registry param, drawn with the panel's own widgets,
so right-click → Learn and a performer's ownership work on them like on
anything else. A function over the Panel, like ui_lookback: no state of
its own but the open strip's id (`panel._lfo_open`); a save of this file lands live (hotreload.MODULES). Without a
clock and LFOs attached (headless tests, a Panel built without app.py)
the page says so and draws nothing else.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui, undo
from .lfo import GROUP as LFO_GROUP
from .lfo import REST, SYNCS
from .tempo import BEATS_PER_BAR
from .tempo import GROUP as TEMPO_GROUP

SCOPE_W = 104.0       # the scope, px: three control rows tall
SCOPE_H = 98.0
COMBO_W = 86.0        # shape and sync
ROW_LABEL_W = 54.0    # the label column in a half-width cell: short labels
CYCLES = 2            # the scope shows this many
SAMPLES = 64          # per cycle
BEAT_R = 7.0          # the beat light's radius
WAVE = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)
FOLD_AT = 4           # more LFOs than this and the strips fold to one line
THUMB_W = 48.0        # a folded strip's thumbnail, px (its height is the frame's)
THUMB_SAMPLES = 16    # one cycle
NAME_W = 64.0         # a folded strip's name cell
OUT_W = 150.0         # a folded strip's output bar


def page(panel, dt: float) -> None:
    clock, lfos = getattr(panel, "clock", None), getattr(panel, "lfos", None)
    have = clock is not None and lfos is not None and f"{TEMPO_GROUP}.bpm" in panel.reg
    panel._section("tempo", TEMPO_GROUP if have else None, note="B tap · ⇧B trigger")
    if not have:
        imgui.text_disabled("no clock — app.py wires tempo.py and lfo.py")
        return
    _clock_strip(panel, clock)
    imgui.spacing()
    panel._section("lfos", LFO_GROUP, note="rest 0.5 · every knob ownable")
    ids = lfos.ids()
    if not ids:                       # every LFO removed: only the way back
        _add_chip(panel, lfos)
    if len(ids) <= FOLD_AT:
        for k, n in enumerate(ids):
            _strip(panel, lfos, clock, n, first=k == 0)
        return
    sel = selected(panel, lfos)
    for k, n in enumerate(ids):
        if n == sel:
            _strip(panel, lfos, clock, n, first=k == 0)
        else:
            _folded(panel, lfos, n, first=k == 0)


def selected(panel, lfos) -> int | None:
    """The open strip's id: the one picked this session, else the first.
    Kept on the Panel only — a selection is no preset content."""
    ids = lfos.ids()
    sel = getattr(panel, "_lfo_open", None)
    if sel not in ids:
        sel = ids[0] if ids else None
        panel._lfo_open = sel
    return sel


def select(panel, n: int) -> None:
    panel._lfo_open = n


def add_lfo(panel, lfos) -> int | None:
    """"+ lfo": a fresh LFO at one past the highest id, its knobs declared
    (modbank.Bank.add); one undo step. None at the cap."""
    if not lfos.can_add():
        return None
    undo.push("add LFO")
    n = lfos.add()
    panel._lfo_open = n               # the new one opens, where it can be seen
    return n


def remove_lfo(panel, lfos, n: int) -> None:
    """The ×: LFO `n` and its knobs go; the others keep their ids and a
    route on its lane goes dormant. One undo step."""
    if n not in lfos:
        return
    undo.push(f"delete LFO {n}")
    lfos.remove(n)


def _add_chip(panel, lfos) -> None:
    """`+ lfo`, greyed out at the cap with the reason on hover."""
    can = lfos.can_add()
    imgui.begin_disabled(not can)
    if ui.chip("+ lfo##lfo.add") and can:
        add_lfo(panel, lfos)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        if can:
            imgui.set_tooltip(f"Another LFO, LFO {lfos.next_id()} (up to {lfos.MAX})")
        else:
            imgui.set_tooltip(f"{len(lfos)} LFOs, the most there can be — remove one "
                              "with its × to add another")


# ---- the clock ----

def _clock_strip(panel, clock) -> None:
    r = panel.reg
    # the readout, big, with the beat light and the bar's four beats beside it
    imgui.push_font(ui._FONTS["num"], ui.FONT_BIG * 0.6)
    imgui.text(f"{clock.bpm:.1f}")
    imgui.pop_font()
    h = imgui.get_item_rect_size().y
    imgui.same_line(0, 8)
    imgui.begin_group()
    ui._micro("bpm", ui.FAINT)
    _beats(clock, h - ui.FONT_MICRO - 6)
    imgui.end_group()
    imgui.same_line(imgui.get_content_region_avail().x
                    - ui.chip_w("tap", "trigger", "−", "+") - 8)
    imgui.begin_group()
    imgui.dummy(imgui.ImVec2(0, max(0.0, (h - imgui.get_frame_height()) / 2 - 4)))
    panel._button(f"{TEMPO_GROUP}.tap", "tap", small=True)
    imgui.same_line()
    panel._button(f"{LFO_GROUP}.trigger", "trigger", small=True)
    imgui.same_line()
    nudge = r[f"{TEMPO_GROUP}.nudge"]
    for sign, tag, tip in ((-1, "−", "back"), (1, "+", "on")):
        if sign > 0:
            imgui.same_line()
        # a step chip on the nudge param: the menu and the learn frame are
        # the param's, like every other control that stands for one
        if ui.chip(f"{tag}##{nudge.id}.{tag}"):
            nudge.step(sign)
        panel._tip(nudge, f"Nudge the downbeat {tip} a hundredth of a beat (APC NUDGE {tag})")
        panel._ctx(nudge)
        panel._learn_frame(nudge)
    imgui.end_group()
    # the two faders side by side, so the clock costs the page one row
    if imgui.begin_table("##clock", 2, imgui.TableFlags_.sizing_stretch_same):
        imgui.table_next_column()
        panel.half(f"{TEMPO_GROUP}.bpm", "bpm", label_w=ROW_LABEL_W)
        imgui.table_next_column()
        panel.half(f"{TEMPO_GROUP}.nudge", "nudge", label_w=ROW_LABEL_W)
        imgui.end_table()


def _beats(clock, h: float) -> None:
    """The beat light, then one dot per beat of the bar with the current one lit."""
    dl = imgui.get_window_draw_list()
    pos = imgui.get_cursor_screen_pos()
    cy = pos.y + h / 2
    on = clock.on_beat()
    dl.add_circle_filled(imgui.ImVec2(pos.x + BEAT_R, cy), BEAT_R,
                         ui.u32(ui.RED if on else ui.LINE))
    bar = int(clock.bar())
    x = pos.x + 2 * BEAT_R + 10
    for k in range(BEATS_PER_BAR):
        col = ui.TEXT if k == bar else ui.LINE
        dl.add_circle_filled(imgui.ImVec2(x + k * 12, cy), 3.0, ui.u32(col))
    imgui.dummy(imgui.ImVec2(2 * BEAT_R + 10 + BEATS_PER_BAR * 12, h))
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"beat {bar + 1} of {BEATS_PER_BAR} — the light is the "
                          "METRONOME LED; the trigger puts beat 1 here")


# ---- one LFO ----

def _strip(panel, lfos, clock, n: int, first: bool = False) -> None:
    lf = lfos.voice(n)
    p = f"{LFO_GROUP}.{n}"
    imgui.push_id(p)
    ui._micro(f"lfo {n}")
    imgui.same_line(SCOPE_W + imgui.get_style().item_spacing.x)
    ui._micro(_where(lf, clock), ui.FAINT)
    # the head's chips, flush right on the label line: no row of their own
    chips = (["+ lfo"] if first else []) + ["×"]
    imgui.same_line(imgui.get_content_region_avail().x + imgui.get_cursor_pos_x()
                    - ui.chip_w(*chips) - 4)
    if first:
        _add_chip(panel, lfos)
        imgui.same_line()
    if ui.chip(f"×##{p}.del"):
        remove_lfo(panel, lfos, n)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"Remove LFO {n} — the others keep their numbers; a route "
                          "from it waits, dormant")
    _scope(lf)
    imgui.same_line()
    imgui.begin_group()
    panel._combo(f"{p}.shape", COMBO_W)
    imgui.same_line()
    panel._combo(f"{p}.sync", COMBO_W)
    imgui.same_line()
    panel._button(f"{p}.reset", "reset", small=True)
    panel.half(f"{p}.rate", "rate", label_w=ROW_LABEL_W)
    # depth and phase share the third row: three rows beside a scope, four
    # strips on the page without a scrollbar
    if imgui.begin_table("##knobs", 2, imgui.TableFlags_.sizing_stretch_same):
        imgui.table_next_column()
        panel.half(f"{p}.depth", "depth", label_w=ROW_LABEL_W)
        imgui.table_next_column()
        panel.half(f"{p}.phase", "phase", label_w=ROW_LABEL_W)
        imgui.end_table()
    imgui.end_group()
    imgui.pop_id()


def _folded(panel, lfos, n: int, first: bool = False) -> None:
    """One line: thumbnail · name · output bar · chevron. A click anywhere
    on it, or on the chevron, opens it (and so folds the open one)."""
    lf = lfos.voice(n)
    p = f"{LFO_GROUP}.{n}"
    imgui.push_id(p)
    h = imgui.get_frame_height()
    sp = imgui.get_style().item_spacing.x
    pos = imgui.get_cursor_screen_pos()
    w = THUMB_W + sp + NAME_W + sp + OUT_W
    hit = imgui.invisible_button(f"##{p}.row", imgui.ImVec2(w, h))
    hov = imgui.is_item_hovered()
    dl = imgui.get_window_draw_list()
    if hov:
        dl.add_rect_filled(pos, imgui.ImVec2(pos.x + w, pos.y + h),
                           imgui.get_color_u32(imgui.Col_.button_hovered), 4.0)
        imgui.set_tooltip(f"LFO {n}: out {lf.out:.2f} — click to open it")
    _thumb(dl, lf, pos.x, pos.y, h)
    # the name, in the label face, centred on the line
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    dl.add_text(imgui.ImVec2(pos.x + THUMB_W + sp, pos.y + (h - ui.FONT_MICRO) / 2 - 1),
                ui.u32(ui.TEXT if hov else ui.DIM), f"LFO {n}")
    imgui.pop_font()
    _out_bar(dl, lf.out, pos.x + THUMB_W + sp + NAME_W + sp, pos.y, OUT_W, h)
    # the chips flush right: `+ lfo` on the first line, then the chevron
    imgui.same_line(imgui.get_content_region_avail().x + imgui.get_cursor_pos_x()
                    - h - (ui.chip_w("+ lfo") + sp if first else 0) - 4)
    if first:
        _add_chip(panel, lfos)
        imgui.same_line()
    if imgui.arrow_button(f"##{p}.open", imgui.Dir.right) or hit:
        select(panel, n)
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"Open LFO {n} (the open one folds)")
    imgui.pop_id()


def _thumb(dl, lf, x0: float, y0: float, h: float) -> None:
    """One cycle of the shape at the current depth, small: THUMB_SAMPLES + 1
    points, and the output as a dot where the wave is now."""
    x1, y1 = x0 + THUMB_W, y0 + h
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1), ui.u32(ui.LINE))
    pts = []
    for j in range(THUMB_SAMPLES + 1):
        x = j / THUMB_SAMPLES if j < THUMB_SAMPLES else 1.0 - 1e-9
        u = REST + 0.5 * lf.depth * lf.wave_at(x)
        pts.append(imgui.ImVec2(x0 + THUMB_W * j / THUMB_SAMPLES, y0 + 2 + (h - 4) * (1 - u)))
    dl.add_polyline(pts, ui.u32(WAVE), 1.0, 0)
    dl.add_circle_filled(imgui.ImVec2(x0 + THUMB_W * lf.x, y0 + 2 + (h - 4) * (1 - lf.out)),
                         2.5, ui.u32(ui.RED))


def _out_bar(dl, out: float, x0: float, y0: float, w: float, h: float) -> None:
    """The live output, 0–1, as a fill from the left, with a tick at rest."""
    pad = h * 0.25
    a, b = imgui.ImVec2(x0, y0 + pad), imgui.ImVec2(x0 + w, y0 + h - pad)
    dl.add_rect_filled(a, b, ui.u32(ui.LINE), 3.0)
    v = min(max(out, 0.0), 1.0)
    if v > 0:
        dl.add_rect_filled(a, imgui.ImVec2(x0 + w * v, b.y), ui.u32(ui.RED), 3.0)
    xr = x0 + w * REST
    dl.add_line(imgui.ImVec2(xr, y0 + 2), imgui.ImVec2(xr, y0 + h - 2), ui.u32(ui.TEXT))


def _where(lf, clock) -> str:
    """What the LFO is locked to, and its output now."""
    if lf.synced:
        lock = f"{SYNCS[lf.sync]} · {clock.bpm:.0f} bpm"
    else:
        lock = f"{lf.rate:.2f} Hz"
    return f"{lock} · out {lf.out:.2f}"


def _scope(lf) -> None:
    """Two cycles of the shape at the current depth, the phase as a
    hairline, the live output as a dot on it."""
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    x0, y0, x1, y1 = pos.x, pos.y, pos.x + SCOPE_W, pos.y + SCOPE_H
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1), ui.u32(ui.LINE))
    # the rest line, and one per cycle boundary
    ym = y0 + SCOPE_H * (1 - REST)
    dl.add_line(imgui.ImVec2(x0, ym), imgui.ImVec2(x1, ym), ui.u32(ui.LINE))
    for c in range(1, CYCLES):
        xc = x0 + SCOPE_W * c / CYCLES
        dl.add_line(imgui.ImVec2(xc, y0), imgui.ImVec2(xc, y1), ui.u32(ui.LINE))
    n = SAMPLES * CYCLES
    pts = []
    for j in range(n + 1):
        x = j / SAMPLES                      # in cycles
        u = REST + 0.5 * lf.depth * lf.wave_at(x % 1.0 if j < n else 1.0 - 1e-9)
        pts.append(imgui.ImVec2(x0 + SCOPE_W * j / n, y0 + 2 + (SCOPE_H - 4) * (1 - u)))
    dl.add_polyline(pts, ui.u32(WAVE), 1.2, 0)   # one call for the whole wave
    # the wave is at `x` in every cycle; the hairline sits in the last one
    hx = x0 + SCOPE_W * (CYCLES - 1 + lf.x) / CYCLES
    dl.add_line(imgui.ImVec2(hx, y0), imgui.ImVec2(hx, y1), ui.u32(ui.RED))
    dl.add_circle_filled(imgui.ImVec2(hx, y0 + 2 + (SCOPE_H - 4) * (1 - lf.out)), 3.0,
                         ui.u32(ui.RED))
    imgui.dummy(imgui.ImVec2(SCOPE_W, SCOPE_H))
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"two cycles of the shape at depth {lf.depth:.2f}; the red "
                          f"line is the phase now ({lf.x:.2f}), the dot the output "
                          f"({lf.out:.2f}). Rest is 0.5.")
