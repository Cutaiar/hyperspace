"""The LFO page — the tap-tempo clock and the four LFOs (tempo.py, lfo.py).

Top to bottom:

  tempo  ◀ preset ▶ …    the clock strip: the BPM readout, a beat light
                         that flashes on every beat (the same predicate
                         as the APC's METRONOME LED), the bar's four
                         beats, then tap · trigger · nudge −/+ — the
                         trigger params as buttons — and the bpm and
                         nudge faders on one row
  lfos   ◀ preset ▶ …    four strips. Each: a small scope of two cycles
                         of the shape at the current depth, a hairline
                         where the wave is now and a dot at the live
                         output; beside it shape · sync · reset on one
                         line, rate on the next, depth · phase on the
                         third — three rows, so four strips fit.

The scope samples the shape function rather than keeping a history: the
wave is a closed form in the phase, so two cycles cost nothing and the
picture is exact. Random draws its held value as a flat line, which is
what the output is.

Every control is a registry param, drawn with the panel's own widgets,
so right-click → Learn and a performer's ownership work on them like on
anything else. A function over the Panel, like ui_lookback: no state of
its own; a save of this file lands live (hotreload.MODULES). Without a
clock and LFOs attached (headless tests, a Panel built without app.py)
the page says so and draws nothing else.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui
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
DIM_LINE = imgui.ImVec4(0.25, 0.25, 0.25, 1.0)
WAVE = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)


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
    for i in range(len(lfos)):
        _strip(panel, lfos, clock, i)


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
        _half(panel, f"{TEMPO_GROUP}.bpm", "bpm")
        imgui.table_next_column()
        _half(panel, f"{TEMPO_GROUP}.nudge", "nudge")
        imgui.end_table()


def _half(panel, pid: str, label: str) -> None:
    """A labelled slider in a half-width table cell: short label, narrow column."""
    panel._row(pid, label=label, label_w=ROW_LABEL_W)


def _beats(clock, h: float) -> None:
    """The beat light, then one dot per beat of the bar with the current one lit."""
    dl = imgui.get_window_draw_list()
    pos = imgui.get_cursor_screen_pos()
    cy = pos.y + h / 2
    on = clock.on_beat()
    dl.add_circle_filled(imgui.ImVec2(pos.x + BEAT_R, cy), BEAT_R,
                         ui.u32(ui.RED if on else DIM_LINE))
    bar = int(clock.bar())
    x = pos.x + 2 * BEAT_R + 10
    for k in range(BEATS_PER_BAR):
        col = ui.TEXT if k == bar else DIM_LINE
        dl.add_circle_filled(imgui.ImVec2(x + k * 12, cy), 3.0, ui.u32(col))
    imgui.dummy(imgui.ImVec2(2 * BEAT_R + 10 + BEATS_PER_BAR * 12, h))
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"beat {bar + 1} of {BEATS_PER_BAR} — the light is the "
                          "METRONOME LED; the trigger puts beat 1 here")


# ---- one LFO ----

def _strip(panel, lfos, clock, i: int) -> None:
    lf = lfos[i]
    p = f"{LFO_GROUP}.{i + 1}"
    imgui.push_id(p)
    ui._micro(f"lfo {i + 1}")
    imgui.same_line(SCOPE_W + imgui.get_style().item_spacing.x)
    ui._micro(_where(lf, clock), ui.FAINT)
    _scope(lf)
    imgui.same_line()
    imgui.begin_group()
    panel._combo(f"{p}.shape", COMBO_W)
    imgui.same_line()
    panel._combo(f"{p}.sync", COMBO_W)
    imgui.same_line()
    panel._button(f"{p}.reset", "reset", small=True)
    _half(panel, f"{p}.rate", "rate")
    # depth and phase share the third row: three rows beside a scope, four
    # strips on the page without a scrollbar
    if imgui.begin_table("##knobs", 2, imgui.TableFlags_.sizing_stretch_same):
        imgui.table_next_column()
        _half(panel, f"{p}.depth", "depth")
        imgui.table_next_column()
        _half(panel, f"{p}.phase", "phase")
        imgui.end_table()
    imgui.end_group()
    imgui.pop_id()


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
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1), ui.u32(DIM_LINE))
    # the rest line, and one per cycle boundary
    ym = y0 + SCOPE_H * (1 - REST)
    dl.add_line(imgui.ImVec2(x0, ym), imgui.ImVec2(x1, ym), ui.u32(DIM_LINE))
    for c in range(1, CYCLES):
        xc = x0 + SCOPE_W * c / CYCLES
        dl.add_line(imgui.ImVec2(xc, y0), imgui.ImVec2(xc, y1), ui.u32(DIM_LINE))
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
