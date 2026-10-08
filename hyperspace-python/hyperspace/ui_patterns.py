"""The FACES page — the faces, the pattern on them and its eight inputs
(plan 22 B2).

Top to bottom:

- **faces**: the Faces and Cut-through checks and the pattern's mix.
  While Faces is off a line says the pattern shows on nothing, with a
  chip that switches them on.
- **patterns**: every mode as a chip with a small live swatch, the one
  on show lit, four to a row; ‹ and › step through them, at the end of
  the line under the chips that names the mode on show. A swatch is the renderer's
  (`Renderer.want_swatches`): what face 0 shows of that mode on the
  inputs as they are now, one mode redrawn a frame, so the strip is also
  a preview of the current inputs on every pattern. A chip's hover is its
  mode's one line (`patterns.MODES[k].about`); a click is `view.pattern`'s
  Param.set — one undo step, like any choice; a right-click is the
  param's menu (learn a knob to step the patterns). Under the chips: the
  mode on show, its line, and the GLSL error while patterns.glsl does not
  compile (the last good version keeps drawing).
- **inputs**: the eight pattern inputs (`pattern.mod.0–7`), two lines
  each. The first is the convention's name, what the input does *in this
  mode* (`patterns.effect`) and, at its right end, what drives it. The
  second is the slider — `base → effective` while a source rides it, the
  white bar at the effective value — and a "1" chip that puts the base
  back to neutral, the pattern as designed. What drives it is the route
  in its adapter's words with any macro scaling it, a desk or session control, a
  macro that sets its base (`drivers`) — a click opens ROUTING filtered
  to the input. An input nothing drives offers "+ <source>" there: a
  push route at the factory depth (routing.PATTERN_DEPTH) from the source
  the convention puts on it
  (`suggest`: lane k for SCALE … SHARP, the factory's layout; LFO 1 and
  LFO 2 for HUE and SPREAD), into the loaded preset, staying on this
  page. "all neutral" puts every base back at 1.0 as one undo step. On
  FLAT, which runs no pattern, the rows are dimmed but live.
- a last faint line: what a right-click on an input offers.

A function over the Panel, like ui_fx: no state of its own, and a save of
this file lands live (hotreload.MODULES). Every write is a base through
the param (Param.set / set_value) or a row into the live table — the
undo watcher makes each its step — except "all neutral", which pushes its
own named step first.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import learn, patterns, ui, ui_presets, ui_routing, undo
from .patterns import INPUTS, MODES, N_INPUTS
from .routing import PATTERN_DEPTH

COLS = 4                # mode chips to a row
CELL_H = 24.0           # a mode chip's height, px; its swatch is a disc inset in it
GRID_GAP = 4.0          # px between rows of mode chips (17 modes: five rows)
SWATCH_INSET = 3.0
NEUTRAL = 1.0
NEUTRAL_CHIP = "1"
NEUTRAL_TIP = "Back to 1.0 — the pattern as designed."
ALL_NEUTRAL = "all neutral"
ALL_NEUTRAL_TIP = "Every input back to 1.0 — the pattern as designed. One undo step."
NEUTRAL_STEP = "neutral pattern inputs"     # the undo step "all neutral" pushes
PREV, NEXT = "‹", "›"
FACES_OFF = "Faces is off"
FLAT_NOTE = "a plain fill: no pattern runs, so the inputs do nothing"
FLAT_ROW = "FLAT reads no input"
HINT = "right-click an input: learn a knob or a hand"
ROUTE_DEPTH = PATTERN_DEPTH   # a "+ source" route's push depth: the factory's
SUGGEST = {patterns.HUE: "lfo:0", patterns.SPREAD: "lfo:1"}   # the rest: lane k
ROUTING_TIP = "Open ROUTING on this input."
LINK_MAX = 0.62        # of the row's width, at most, for what drives it
ROW_GAP = 2.0           # px between an input's two lines
ROWS_GAP = 5.0          # px between one input and the next
IDLE_ALPHA = 0.45       # how much of FLAT's rows shows through the veil (ui_fx's)


def page(panel, dt: float) -> None:
    r = panel.reg
    rend = panel.renderer
    if rend is not None and hasattr(rend, "want_swatches"):
        rend.want_swatches()            # the strip's pictures: drawn only while asked
    p = r["view.pattern"]
    mode = int(p.value)                 # what shows: the effective choice
    mode = mode if 0 <= mode < len(MODES) else 0

    panel._section("faces", note="saved with view")
    panel._check("view.faces")
    imgui.same_line()
    panel._check("view.cut_through")
    imgui.same_line()
    panel._slider("view.pattern_mix")

    _browser(panel, p, mode)
    _about(panel, p, mode)
    _inputs(panel, mode)
    _faint(HINT)


# ---- the patterns ----

def _browser(panel, p, mode: int) -> None:
    """A chip per mode, COLS to a row, the rows close together."""
    sp = imgui.get_style().item_spacing.x
    n = len(MODES)
    imgui.spacing()
    w = (imgui.get_content_region_avail().x - sp * (COLS - 1)) / COLS
    imgui.push_style_var(imgui.StyleVar_.item_spacing, imgui.ImVec2(sp, GRID_GAP))
    for k in range(n):
        if k % COLS:
            imgui.same_line()
        if _mode_chip(panel, p, k, k == mode, w) and k != int(p.base):
            p.set(k)
    imgui.pop_style_var()


def _steps(panel, p) -> None:
    """‹ and ›: the previous and the next pattern, round the ends."""
    n = len(MODES)
    for step, label in zip((-1, 1), _step_labels(p), strict=True):
        if step > 0:
            imgui.same_line()
        if ui.chip(label):
            p.set((int(p.base) + step) % n)     # a scene-setter's write to the base
        panel._tip(p, "previous pattern" if step < 0 else "next pattern")
        panel._ctx(p, key=f".step{step}")


def _step_labels(p) -> tuple[str, str]:
    return f"{PREV}##prev.{p.id}", f"{NEXT}##next.{p.id}"


def _mode_chip(panel, p, k: int, lit: bool, w: float) -> bool:
    """One mode: its swatch, a disc at the left end, and its name; solid
    red while it is the one on show. Returns the click."""
    pos = imgui.get_cursor_screen_pos()
    hit = imgui.invisible_button(f"##mode.{k}", imgui.ImVec2(w, CELL_H))
    hov = imgui.is_item_hovered()
    dl = imgui.get_window_draw_list()
    end = imgui.ImVec2(pos.x + w, pos.y + CELL_H)
    ground = (ui.u32(ui.RED) if lit else imgui.get_color_u32(
        imgui.Col_.button_hovered if hov else imgui.Col_.button))
    dl.add_rect_filled(pos, end, ground, CELL_H / 2)
    d = CELL_H - 2 * SWATCH_INSET
    a = imgui.ImVec2(pos.x + SWATCH_INSET, pos.y + SWATCH_INSET)
    b = imgui.ImVec2(a.x + d, a.y + d)
    tex = _swatch(panel, k)
    if tex is not None:
        # GL's way up: the picture's first row is its bottom
        dl.add_image_rounded(imgui.ImTextureRef(tex.glo), a, b, imgui.ImVec2(0, 1),
                             imgui.ImVec2(1, 0), ui.u32(imgui.ImVec4(1, 1, 1, 1)), d / 2)
    else:
        dl.add_circle_filled(imgui.ImVec2(a.x + d / 2, a.y + d / 2), d / 2, ui.u32(ui.LINE))
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    # the name after the swatch, nearer it when it is long, and never past
    # the chip's rounded end (TRUCHET, at four to a row)
    tw = imgui.calc_text_size(MODES[k].name).x
    x = min(b.x + 6, end.x - CELL_H / 2 - tw + 4)
    dl.add_text(imgui.ImVec2(max(x, b.x + 2), pos.y + (CELL_H - ui.FONT_MICRO) / 2 - 1),
                ui.u32(imgui.ImVec4(1, 1, 1, 1) if lit else ui.TEXT if hov else ui.DIM),
                MODES[k].name)
    imgui.pop_font()
    panel._tip(p, f"{MODES[k].name} — {MODES[k].about}")
    panel._ctx(p, key=f".mode{k}")      # a key each: one popup id per chip
    if lit:
        panel._learn_frame(p)
        panel._mod_dot(p)
    return hit


def _swatch(panel, k: int):
    """Mode `k`'s swatch texture from the renderer, or None (no renderer,
    a headless test, not drawn yet)."""
    rend = panel.renderer
    get = getattr(rend, "swatch", None)
    return get(k) if get is not None else None


def _about(panel, p, mode: int) -> None:
    """The mode on show: its name and its line, wrapped short of ‹ ›,
    which sit at the right end of its first line. In the line's place, so
    the page is no taller for them: the GLSL error while patterns.glsl
    does not compile, else while Faces is off a line saying so and a chip
    that switches them on."""
    m = MODES[mode]
    err = " ".join((getattr(panel.renderer, "pattern_error", "") or "").split())
    off = not getattr(panel.view, "faces", True)
    sp = imgui.get_style().item_spacing.x
    avail = imgui.get_content_region_avail().x
    left, y0 = imgui.get_cursor_pos_x(), imgui.get_cursor_pos_y()
    chips_w = ui.chip_w(*_step_labels(p))
    stop = left + avail - chips_w - sp          # where the line's text must end
    _baseline()
    ui._micro(m.name, ui.TEXT)
    imgui.same_line()
    if err:                 # one line: the whole of it on hover
        text = f"GLSL: {err}"
        shown = ui.fit_text(text, stop - imgui.get_cursor_pos_x())
        imgui.text_colored(ui.WARN, shown)
        if shown != text and imgui.is_item_hovered():
            imgui.set_tooltip(text)
    elif off:
        imgui.text_colored(ui.WARN, FACES_OFF)
        imgui.same_line()
        f = panel.reg["view.faces"]
        if ui.chip(f"faces on##idle.{f.id}"):
            f.set(True)
        panel._tip(f, "Switch the faces on.")
    else:
        imgui.push_text_wrap_pos(stop)
        imgui.text_colored(ui.FAINT, FLAT_NOTE if mode == 0 else m.about)
        imgui.pop_text_wrap_pos()
    y1 = imgui.get_cursor_pos_y()
    imgui.set_cursor_pos(imgui.ImVec2(left + avail - chips_w, y0))
    _steps(panel, p)
    imgui.set_cursor_pos(imgui.ImVec2(left, max(y1, imgui.get_cursor_pos_y())))


# ---- the inputs ----

def _inputs(panel, mode: int) -> None:
    """The section header ("all neutral" at its right end, the group's
    preset strip under it) and a row per input."""
    sp = imgui.get_style().item_spacing.x
    avail = imgui.get_content_region_avail().x
    left = imgui.get_cursor_pos_x()
    label = f"{ALL_NEUTRAL}##neutral.all"
    _baseline()
    ui._micro(f"inputs · {MODES[mode].name}", ui.TEXT)
    imgui.same_line(left + avail - ui.chip_w(label))
    if ui.chip(label):
        neutral_all(panel)
    if imgui.is_item_hovered():
        imgui.set_tooltip(ALL_NEUTRAL_TIP)
    ui_presets.strip(panel, "pattern")
    imgui.separator()
    imgui.dummy(imgui.ImVec2(0, 1))
    top = imgui.get_cursor_screen_pos()
    right = top.x + avail
    gap = imgui.get_style().item_spacing
    imgui.push_style_var(imgui.StyleVar_.item_spacing, imgui.ImVec2(gap.x, ROWS_GAP))
    for k in range(N_INPUTS):
        _input_row(panel, k, mode, sp)
    imgui.pop_style_var()
    if mode == 0:
        _dim(top, imgui.ImVec2(right, imgui.get_cursor_screen_pos().y))


def _input_row(panel, k: int, mode: int, sp: float) -> None:
    """Two lines: the name, what it does in this mode and what drives it;
    then the slider and the neutral chip."""
    pid = f"pattern.mod.{k}"
    p = panel.reg[pid]
    name = INPUTS[k].name
    x0 = imgui.get_cursor_pos_x()
    avail = imgui.get_content_region_avail().x
    # the first line
    said = drivers(panel, pid)
    offer = None if said or mode == 0 else suggest(panel, k)
    # the driver's link takes up to LINK_MAX of the line, cut short beyond
    link = ui.fit_text(said, avail * LINK_MAX - 2 * LINK_PAD.x) if said else (
        f"+ {offer[1]}" if offer else "")
    link_w = _link_w(link) if link else 0.0
    _baseline_link()
    ui._micro(name, ui.TEXT)
    panel._tip(p, lambda: f"{name} — {INPUTS[k].meaning}")
    panel._ctx_label(p)
    imgui.same_line(0, 8)
    what = patterns.effect(mode, k) or FLAT_ROW
    room = x0 + avail - imgui.get_cursor_pos_x() - (link_w + sp if link else 0.0)
    shown = ui.fit_text(what, room)
    imgui.text_colored(ui.FAINT, shown)
    if shown != what and imgui.is_item_hovered():
        imgui.set_tooltip(what)
    if link:
        imgui.same_line(x0 + avail - link_w)
        if said:
            if _link(f"{link}##drv.{pid}", ui.TEXT):
                open_routing(panel, pid)
            if imgui.is_item_hovered():
                imgui.set_tooltip(f"{said}\n{ROUTING_TIP}")
        elif _link(f"+ {offer[1]}##route.{pid}", ui.DIM):
            ui_routing.add_route(panel, pid, source=offer[0], depth=ROUTE_DEPTH)
        elif imgui.is_item_hovered():
            imgui.set_tooltip(f"Route {offer[1]} here: a push at depth {ROUTE_DEPTH}, into "
                              "the loaded preset. ROUTING shows and edits it.")
    imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() - (ROWS_GAP - ROW_GAP))
    # the second line: the slider, then neutral
    chip = f"{NEUTRAL_CHIP}##neutral.{pid}"
    panel._slider(pid, -(ui.chip_w(chip) + sp))
    imgui.same_line()
    at = abs(p.base - NEUTRAL) < 1e-9
    imgui.push_style_color(imgui.Col_.text, ui.FAINT if at else ui.TEXT)
    if ui.chip(chip) and not at:
        p.set_value(NEUTRAL)
    imgui.pop_style_color()
    if imgui.is_item_hovered():
        imgui.set_tooltip(NEUTRAL_TIP)


def drivers(panel, pid: str) -> str:
    """What drives `pid`, one line: each route in its adapter's words
    ("SUB pushes +0.5", "(off)" while disabled) with the macros scaling it
    ("× macro.2"), each desk control on it ("K3 sets it"), each macro that
    sets its base ("macro.4 sets its base"). A desk control is the loaded
    preset's or the session's (bindings.json's): either sets the base, so
    a row it drives offers no "+ <source>". "" when nothing does, or with
    no table."""
    table = panel._table()
    if table is None:
        return ""
    router = ui_routing.router_of(panel)
    desk, routes, session = learn.bound(table, (pid,))
    macros = getattr(table, "macros", {}) or {}
    said = []
    for b in routes:
        line = router.describe(b) if router is not None else b.describe()
        for mid, _sub in table.depth_subs(b):
            line += f" × {macros[mid].label or mid}"
        said.append(line if b.enabled else f"{line} (off)")
    said += [f"{ui_routing.control_glyph(table, b)} sets it" for b in desk + session]
    said += [f"{m.label or mid} sets its base" for mid, m in macros.items()
             if any(s.base == pid for s in m.subs)]
    return " · ".join(said)


def suggest(panel, k: int) -> tuple[str, str] | None:
    """(source, its name) the convention puts on input `k`: the analyzer's
    lane k for SCALE … SHARP (the factory routes' layout — SUB on SCALE …
    AIR on SHARP), LFO 1 and 2 for HUE and SPREAD. None with no table."""
    router = ui_routing.router_of(panel)
    if router is None:
        return None
    source = SUGGEST.get(k, f"lane:{k}")
    scheme, i = router.lane(source)
    labels = getattr(router, "labels", {}).get(scheme) or []
    if scheme == "lane" and not labels:
        labels = panel.audio.chain.band_names
    if scheme == "lfo" and not labels:
        labels = [f"LFO {j + 1}" for j in range(i + 1)]
    if not 0 <= i < len(labels):
        return None
    return source, str(labels[i])


def neutral_all(panel) -> None:
    """Every input's base back to 1.0, as one named undo step — pushed
    before the first write and only when something moves."""
    ps = [panel.reg[f"pattern.mod.{k}"] for k in range(N_INPUTS)]
    moved = [p for p in ps if abs(p.base - NEUTRAL) > 1e-9]
    if not moved:
        return
    undo.push(NEUTRAL_STEP)
    for p in moved:
        p.set_value(NEUTRAL)


def open_routing(panel, pid: str) -> None:
    """ROUTING, its rows filtered to `pid`'s."""
    ui_routing._state(panel)["find"] = pid
    panel.reg["ui.page"].set(ui.PAGE_KEYS.index("routing"))


# ---- small drawing helpers ----

LINK_PAD = imgui.ImVec2(6, 0)   # a link is a chip one text line tall


def _link(label: str, color: imgui.ImVec4) -> bool:
    imgui.push_style_var(imgui.StyleVar_.frame_padding, LINK_PAD)
    imgui.push_style_var(imgui.StyleVar_.frame_rounding, 999.0)
    imgui.push_style_color(imgui.Col_.text, color)
    hit = imgui.button(label)
    imgui.pop_style_color()
    imgui.pop_style_var(2)
    return hit


def _link_w(text: str) -> float:
    return imgui.calc_text_size(text).x + 2 * LINK_PAD.x


def _baseline() -> None:
    """The next text on the baseline of a chip beside it (ui_fx's)."""
    imgui.push_style_var(imgui.StyleVar_.frame_padding, ui.CHIP_PAD)
    imgui.align_text_to_frame_padding()
    imgui.pop_style_var()


def _baseline_link() -> None:
    imgui.push_style_var(imgui.StyleVar_.frame_padding, LINK_PAD)
    imgui.align_text_to_frame_padding()
    imgui.pop_style_var()


def _faint(text: str) -> None:
    imgui.push_style_color(imgui.Col_.text, ui.FAINT)
    imgui.text_wrapped(text)
    imgui.pop_style_color()


def _dim(lo: imgui.ImVec2, hi: imgui.ImVec2) -> None:
    """A veil of the window's ground over what is drawn in the rect; the
    controls under it stay live (ui_fx._dim)."""
    c = imgui.get_style_color_vec4(imgui.Col_.window_bg)
    imgui.get_window_draw_list().add_rect_filled(
        lo, hi, ui.u32(imgui.ImVec4(c.x, c.y, c.z, 1.0 - IDLE_ALPHA)))
