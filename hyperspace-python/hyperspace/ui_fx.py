"""The FX page — the effect stack (fx.py).

The chain's bypass and mix, then one chip per effect in stack order, lit
while it is on. A chip is two click targets (plan 16 WP2): the name opens
the effect's strip and never switches it; the LED at its left end — a
dot while on, a ring while off — switches it and never opens it. The
open effect's chip carries an outline, so "open" and "on" read apart.
Right-clicking either part binds the effect's switch (MIDI learn) like
any widget. The open strip is the effect's own six (on, mix, speed,
blend, target, order) and a row per annotated uniform, with the file's
parse or compile error under it.

An effect runs on the frame or on the picture in the faces (plan 20:
`fx.<name>.target`, the combo between the strip's blend and order). A
chip aimed at the faces has a diamond for its LED — filled while on,
outlined while off. While any effect is aimed at the faces the status
under the bypass is two rows, the running chain per target, and the
faces' row ends in the two chips of `fx.face_map` (per face / screen);
it is also where "Faces is off" and the renderer's `face_error` are
said. With nothing aimed at the faces there is one line, as before.

An open effect that is not running says why (plan 16 WP3, `why_idle`):
one line over its rows — off, aimed at the faces with Faces off, the
stack bypassed, the stack's mix at 0, its own mix at 0 — with a chip
that mends the first three ("turn on", "faces on", "effects on"). The
rows under the line are dimmed but live.

Which strip is open is a name (`FxState.sel_name`), not a place in the
stack: moving an effect's order or loading a preset never changes it.

A function over the Panel, like ui_lookback: no state of its own, and a
save of this file lands live (hotreload.MODULES). The effects are
whatever files sit in shaders/fx/, so the page draws from the live
FxState rather than a fixed id list — a new file shows up here on the
next poll.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui
from .fx import FACE_MAPS, FACES, FRAME, FX_DIR, PER_FACE

# three to a row since plan 16 WP2: the LED takes a chip-height square of
# each chip, and at four the names of seven of the twelve factory effects
# were cut short ("Kaleidosc", "Trip colou"); at three the longest loses 3 px
CHIPS_PER_ROW = 3
ORDER_W = 96        # the order slider at the end of the blend row
TARGET_W = 84       # the target combo between them: "frame" / "faces" and the arrow
LED_GAP = 2.0       # px between a chip's LED and its name
DIAMOND = 0.27      # a face-aimed chip's diamond: centre to point, in chip heights
LED_ON_TIP = "on — click to switch off"
LED_OFF_TIP = "off — click to switch on"
IDLE_ALPHA = 0.45   # how much of an idle strip's rows shows through the veil
# why_idle's reason → the strip's line, then the chip beside it, the param
# the chip sets and the chip's hover (None: a fader mends it, not a click)
IDLE = {
    "off": ("off — nothing below shows until it is on", "turn on", "fx.{name}.on",
            "Switch this effect on."),
    "faces off": ("aimed at the faces, and Faces is off", "faces on", "view.faces",
                  "Switch the faces on (the Faces check on the VIEW and FACES pages)."),
    "bypassed": ("the whole stack is bypassed", "effects on", "fx.on",
                 "Switch the effect stack on (the Effects check at the top)."),
    "fx mix 0": ("FX mix is at 0", None, None, None),     # its fader is at the top of the page
    "mix 0": ("its mix is at 0", None, None, None),       # its fader is the next row
}
# one line at the page's width (plan 20 WP2: it wrapped to two by 2 px)
RESET_NOTE = "a preset load resets this stack: save a preset to keep it"
FACES_TIP = "on the faces"      # added to the hovers of a chip aimed at the faces
FACES_OFF = "(Faces is off)"    # the faces' status row while view.faces is off
NO_COPIES = "(no copies to show them)"      # …and while view.instances is 0


def page(panel, dt: float) -> None:
    r = panel.reg
    chain = getattr(panel.renderer, "fx", None)
    fx = _state(panel)
    # plan 20 WP2: the status is per target while any effect — on or off —
    # is aimed at the faces; with none, it is the one line it always was
    aimed = fx is not None and any(_faces(fx, n) for n in fx.specs)

    panel._section("effects", "fx", note=f"shaders/{FX_DIR.name}/*.glsl · live")
    panel._check("fx.on")
    imgui.same_line()
    panel._slider("fx.mix")
    if fx is None:
        status = "nothing on" if r["fx.on"].base else "bypassed"
    else:
        status = f"frame  {_status(fx, FRAME)}" if aimed else _status(fx)
    _faint(status)
    if aimed:
        _faces_row(panel, fx)
    # plan 14 WP5: a preset load replaces every effect value (plan 13 D2),
    # so what is tried here is gone on the next F-key unless it is saved
    _faint(RESET_NOTE)
    if fx is None:
        imgui.text_disabled("no renderer")
        return
    if not fx.specs:
        imgui.text_disabled("no effects — put a .glsl file in hyperspace/shaders/fx/")
        return
    imgui.spacing()

    # the stack, in order: a chip per effect, lit while on
    names = fx.names()
    sel = fx.selected()
    # nothing chosen yet (every launch): the first effect is open. Now that
    # it is on show it is held by name like any other, or dragging its own
    # order slider would hand the strip to whichever effect became first
    if sel is not None and getattr(fx, "sel_name", None) is None:
        fx.select(sel)
    sp = imgui.get_style().item_spacing.x
    w = (imgui.get_content_region_avail().x - sp * (CHIPS_PER_ROW - 1)) / CHIPS_PER_ROW
    for k, name in enumerate(names):
        if k % CHIPS_PER_ROW:
            imgui.same_line()
        label = fx.specs[name].label + (" !" if _error(chain, fx, name) else "")
        _chip(panel, fx, name, label, w, name == sel)
    imgui.spacing()

    if sel is None:
        return
    spec = fx.specs[sel]
    pre = f"fx.{sel}"
    panel._section(spec.label.lower(), note=f"{sel}.glsl · #{fx.values[sel]['order']}")
    if spec.tip:
        imgui.push_style_color(imgui.Col_.text, ui.FAINT)
        imgui.text_wrapped(spec.tip)
        imgui.pop_style_color()
    err = _error(chain, fx, sel)
    if err:
        imgui.text_colored(ui.WARN, err)
    # plan 16 WP3: an effect that is not running says why, and the rows
    # under the line are dimmed but live — set it up dark, then switch it on
    idle = why_idle(fx, sel, bool(getattr(panel.view, "faces", True)))
    if idle is not None:
        _idle_line(panel, sel, idle)
    panel._check(f"{pre}.on")
    imgui.same_line()
    panel._slider(f"{pre}.mix")
    if idle not in (None, "mix 0"):     # at "mix 0" this fader is the one the line names
        _dim(imgui.get_item_rect_min(), imgui.get_item_rect_max())
    top = imgui.get_cursor_screen_pos()
    right = top.x + imgui.get_content_region_avail().x
    rects = {f"{pre}.mix": (imgui.get_item_rect_min(), imgui.get_item_rect_max())}

    def drawn(pid: str) -> None:        # the control just drawn, for _relearn_frame
        rects[pid] = (imgui.get_item_rect_min(), imgui.get_item_rect_max())
    panel._row(f"{pre}.speed", label="speed")
    drawn(f"{pre}.speed")
    panel._label_cell("blend")
    panel._tip(r[f"{pre}.blend"])
    sp = imgui.get_style().item_spacing.x
    target = f"{pre}.target" in r       # a registry from before plan 20 has none
    panel._combo(f"{pre}.blend", -(ORDER_W + sp + ((TARGET_W + sp) if target else 0)))
    drawn(f"{pre}.blend")
    imgui.same_line()
    if target:
        # where it runs. Not modulatable, like order (its menu says so):
        # Param.set on the base, and one undo step by itself
        panel._combo(f"{pre}.target", TARGET_W)
        drawn(f"{pre}.target")
        imgui.same_line()
    panel._slider(f"{pre}.order", ORDER_W)
    drawn(f"{pre}.order")
    imgui.spacing()
    for p in spec.params:
        if f"{pre}.{p.key}" in r:
            panel._row(f"{pre}.{p.key}", label=p.label.lower())
            drawn(f"{pre}.{p.key}")
    if idle is not None:
        _dim(top, imgui.ImVec2(right, imgui.get_cursor_screen_pos().y))
        _relearn_frame(panel, rects)


def _faint(text: str) -> None:
    """A wrapped line in the quietest text colour."""
    imgui.push_style_color(imgui.Col_.text, ui.FAINT)
    imgui.text_wrapped(text)
    imgui.pop_style_color()


def _status(fx, target: int | None = None) -> str:
    """What runs, as a status line says it: the chain's labels in order —
    all of it, or one target's — or why there is none. It reads what runs
    (the effective `fx.on`), as `why_idle` does."""
    if not fx.on:
        return "bypassed"
    running = fx.chain(target)
    return " → ".join(fx.specs[n].label for n in running) if running else "nothing on"


def _chip_baseline() -> None:
    """Put the next text on the baseline of a chip beside it: a chip is a
    frame with CHIP_PAD."""
    imgui.push_style_var(imgui.StyleVar_.frame_padding, ui.CHIP_PAD)
    imgui.align_text_to_frame_padding()
    imgui.pop_style_var()


def _faces(fx, name: str) -> bool:
    """Is `name` aimed at the faces? `.get`: a values dict from before a
    hot reload has no "target"."""
    return fx.values[name].get("target", FRAME) == FACES


def _faces_row(panel, fx) -> None:
    """The faces' status row, one chip tall: what runs on the faces — or
    why nothing does — and at its right end the two chips of `fx.face_map`,
    the lit one being how the faces show their picture. A chip click is
    Param.set; its right-click is the param's menu, so it can be learned."""
    p = panel.reg.get("fx.face_map")    # None: a registry declared before plan 20
    chips = FACE_MAPS if p is not None else []
    # "faces: <Type>: <msg>" (render.py); a GL message can be several lines,
    # and this row is one
    err = " ".join((getattr(panel.renderer, "face_error", "") or "").split())
    warn = True
    if err:
        text = err
    elif not getattr(panel.view, "faces", True):
        text = f"faces  {FACES_OFF}"
    elif int(getattr(panel.view, "instances", 1)) <= 0:
        text = f"faces  {NO_COPIES}"            # the face pass does not run with no copies
    else:
        warn = False
        text = f"faces  {_status(fx, FACES)}"
    sp = imgui.get_style().item_spacing.x
    avail = imgui.get_content_region_avail().x
    left = imgui.get_cursor_pos_x()             # same_line's offset is from the window's edge
    chips_w = ui.chip_w(*chips) if chips else 0.0
    # the text on the chips' baseline, and cut to the room the chips leave:
    # this row is never two lines
    _chip_baseline()
    shown = ui.fit_text(text, avail - chips_w - sp)
    imgui.text_colored(ui.WARN if warn else ui.FAINT, shown)
    if shown != text and imgui.is_item_hovered():
        imgui.set_tooltip(text)
    if p is None:
        return
    now = getattr(fx, "face_map", PER_FACE)     # what the faces show: the effective value
    x = left + avail - chips_w
    for i, label in enumerate(chips):
        imgui.same_line(x) if i == 0 else imgui.same_line()
        if ui.lit_chip(f"{label}##map.{p.id}.{i}", i == now):
            p.set(i)                            # a scene-setter's write to the base
        # the lit chip is what the faces show, a click writes the base: while
        # a source rides the switch the hover names it, as the LED's does
        panel._tip(p, lambda: f"{p.tip}\n{panel._mod_line(p)}" if p.modulated else p.tip)
        panel._ctx(p, key=f".map{i}")           # a key each: one popup id per item
        panel._learn_frame(p)
        if i == now:
            panel._mod_dot(p)


def why_idle(fx, name: str, faces_on: bool = True) -> str | None:
    """Why `name` is not running, first reason only; None while it runs.
    "off" | "faces off" | "bypassed" | "fx mix 0" | "mix 0".

    With `faces_on` left True it is None exactly when fx.chain() lists the
    effect. An effect aimed at the faces runs nothing while `view.faces`
    is off although chain() still lists it (plan 20 WP1), so the page
    passes the view's switch and gets "faces off"."""
    v = fx.values[name]
    if not v["on"]:
        return "off"
    if not faces_on and _faces(fx, name):
        return "faces off"
    if not fx.on:
        return "bypassed"
    if fx.mix <= 0.0:
        return "fx mix 0"
    if v["mix"] <= 0.0:
        return "mix 0"
    return None


def _idle_line(panel, name: str, reason: str) -> None:
    """The open strip's one line saying why its effect is not running, and
    for the three reasons a click mends, the chip that mends it. The chip
    writes a base through Param.set, as the checks do."""
    text, chip, pid, tip = IDLE[reason]
    if chip is None:
        imgui.text_colored(ui.WARN, text)
        return
    p = panel.reg[pid.format(name=name)]
    _chip_baseline()
    imgui.text_colored(ui.WARN, text)
    imgui.same_line()
    if ui.chip(f"{chip}##idle.{p.id}"):
        p.set(True)
    # the line reads what runs (the effective value), the chip writes the
    # base: while a source holds the switch off the hover names it
    panel._tip(p, lambda: f"{tip}\n{panel._mod_line(p)}" if p.modulated else tip)


def _relearn_frame(panel, rects: dict) -> None:
    """The learn frame of an armed row, drawn again over the veil: the cue
    that a row is waiting for a control must not be dimmed with it."""
    pid = panel.learn.learning if panel.learn is not None else None
    if pid in rects:
        r0, r1 = rects[pid]
        imgui.get_window_draw_list().add_rect(
            imgui.ImVec2(r0.x - 2, r0.y - 2), imgui.ImVec2(r1.x + 2, r1.y + 2),
            ui.u32(ui.RED), ui.ROUND + 2, 2.0)


def _dim(lo: imgui.ImVec2, hi: imgui.ImVec2) -> None:
    """Dim what is already drawn in the rect: a veil of the window's ground
    over it. The controls under it stay live (they are not disabled, fork
    F2), and their menus, tooltips and combo lists — windows of their own —
    stay at full strength, which a pushed style alpha would not leave them."""
    c = imgui.get_style_color_vec4(imgui.Col_.window_bg)
    imgui.get_window_draw_list().add_rect_filled(
        lo, hi, ui.u32(imgui.ImVec4(c.x, c.y, c.z, 1.0 - IDLE_ALPHA)))


def _chip(panel, fx, name: str, label: str, width: float, open_: bool) -> None:
    """One effect's chip, `width` px in all: the LED, then the name.

    Two adjacent items rather than one over another (which needs imgui's
    overlap flags), each with its own id: ``##led.fx.<name>.on`` toggles
    `fx.<name>.on` and nothing else; ``##chip.fx.<name>.on`` opens the
    strip and nothing else. Both are solid red while the effect is on."""
    p = panel.reg[f"fx.{name}.on"]
    on = bool(fx.values[name]["on"])
    faces = _faces(fx, name)
    h = imgui.get_font_size() + 2 * ui.CHIP_PAD.y        # a chip's height (ui.chip)
    dl = imgui.get_window_draw_list()

    # the LED: a chip-height square (a disc, at the chip's rounding)
    if ui.lit_chip(f"##led.{p.id}", on, size=imgui.ImVec2(h, h)):
        p.toggle()                  # Param.set on the base: a scene-setter's write
    r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    c = imgui.ImVec2((r0.x + r1.x) / 2, (r0.y + r1.y) / 2)
    if faces:
        # aimed at the faces: a diamond, filled while on and outlined while
        # off, where an effect on the frame has a dot or a ring
        d = h * DIAMOND
        quad = (imgui.ImVec2(c.x, c.y - d), imgui.ImVec2(c.x + d, c.y),
                imgui.ImVec2(c.x, c.y + d), imgui.ImVec2(c.x - d, c.y))
        if on:
            dl.add_quad_filled(*quad, ui.u32(ui.TEXT))
        else:
            dl.add_quad(*quad, ui.u32(ui.DIM), 1.5)
    elif on:
        dl.add_circle_filled(c, h * 0.2, ui.u32(ui.TEXT))
    else:
        dl.add_circle(c, h * 0.2, ui.u32(ui.DIM), 0, 1.5)
    panel._tip(p, lambda: _led_tip(panel, p, faces))
    # the same param's menu on the LED, the name and the strip's check: a
    # key each, or the three would share one popup id and draw it thrice
    panel._ctx(p, key=".led")
    panel._learn_frame(p)

    # the name: opens the strip, and carries the modulation dot
    imgui.same_line(0, LED_GAP)
    if ui.lit_chip(f"{label}##chip.{p.id}", on, ui.TEXT if open_ else None,
                   imgui.ImVec2(max(1.0, width - h - LED_GAP), 0)):
        fx.select(name)
    panel._tip(p, (lambda: f"{p.tip}\n{FACES_TIP}" if p.tip else FACES_TIP) if faces else None)
    panel._ctx(p, key=".chip")
    panel._learn_frame(p)
    panel._mod_dot(p)
    armed = panel.learn is not None and panel.learn.learning == p.id
    if open_ and not armed:         # "open", apart from "on": an outline round both parts
        r1 = imgui.get_item_rect_max()
        dl.add_rect(imgui.ImVec2(r0.x - 1, r0.y - 1), imgui.ImVec2(r1.x + 1, r1.y + 1),
                    ui.u32(ui.TEXT), h / 2 + 1, 2.0)


def _led_tip(panel, p, faces: bool = False) -> str:
    """The LED's hover: what a click does, and "on the faces" for an effect
    aimed at them. A click writes the base, so the base is what it reads;
    while a source rides the switch the effective state (the dot) can
    differ, and the modulation line says so."""
    tip = LED_ON_TIP if p.base else LED_OFF_TIP
    if faces:
        tip = f"{tip}\n{FACES_TIP}"
    return f"{tip}\n{panel._mod_line(p)}" if p.modulated else tip


def _state(panel):
    """The live FxState — the renderer's; None headless."""
    chain = getattr(panel.renderer, "fx", None)
    return None if chain is None else chain.state


def _error(chain, fx, name: str) -> str:
    if chain is not None:
        return chain.error(name)
    return fx.errors.get(name, "")
