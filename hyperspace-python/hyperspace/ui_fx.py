"""The FX page — the effect stack (fx.py).

The chain's bypass and mix, then one chip per effect in stack order, lit
while it is on. A chip is two click targets (plan 16 WP2): the name opens
the effect's strip and never switches it; the LED at its left end — a
dot while on, a ring while off — switches it and never opens it. The
open effect's chip carries an outline, so "open" and "on" read apart.
Right-clicking either part binds the effect's switch (MIDI learn) like
any widget. The open strip is the effect's own five (on, mix, speed,
blend, order) and a row per annotated uniform, with the file's parse or
compile error under it.

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
from .fx import FX_DIR

# three to a row since plan 16 WP2: the LED takes a chip-height square of
# each chip, and at four the names of seven of the twelve factory effects
# were cut short ("Kaleidosc", "Trip colou"); at three the longest loses 3 px
CHIPS_PER_ROW = 3
ORDER_W = 96        # the order slider beside the blend combo
LED_GAP = 2.0       # px between a chip's LED and its name
LED_ON_TIP = "on — click to switch off"
LED_OFF_TIP = "off — click to switch on"
RESET_NOTE = "a preset load resets the effect stack; save it as a preset to keep it"


def page(panel, dt: float) -> None:
    r = panel.reg
    chain = getattr(panel.renderer, "fx", None)
    st = r["fx.on"]
    fx = _state(panel)
    running = fx.chain() if fx is not None else []

    panel._section("effects", "fx", note=f"shaders/{FX_DIR.name}/*.glsl · live")
    panel._check("fx.on")
    imgui.same_line()
    panel._slider("fx.mix")
    status = ("bypassed" if not st.base else
              " → ".join(fx.specs[n].label for n in running) if running else "nothing on")
    imgui.push_style_color(imgui.Col_.text, ui.FAINT)
    imgui.text_wrapped(status)
    # plan 14 WP5: a preset load replaces every effect value (plan 13 D2),
    # so what is tried here is gone on the next F-key unless it is saved
    imgui.text_wrapped(RESET_NOTE)
    imgui.pop_style_color()
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
    panel._check(f"{pre}.on")
    imgui.same_line()
    panel._slider(f"{pre}.mix")
    panel._row(f"{pre}.speed", label="speed")
    panel._label_cell("blend")
    panel._tip(r[f"{pre}.blend"])
    panel._combo(f"{pre}.blend", -(ORDER_W + imgui.get_style().item_spacing.x))
    imgui.same_line()
    panel._slider(f"{pre}.order", ORDER_W)
    imgui.spacing()
    for p in spec.params:
        if f"{pre}.{p.key}" in r:
            panel._row(f"{pre}.{p.key}", label=p.label.lower())


def _chip(panel, fx, name: str, label: str, width: float, open_: bool) -> None:
    """One effect's chip, `width` px in all: the LED, then the name.

    Two adjacent items rather than one over another (which needs imgui's
    overlap flags), each with its own id: ``##led.fx.<name>.on`` toggles
    `fx.<name>.on` and nothing else; ``##chip.fx.<name>.on`` opens the
    strip and nothing else. Both are solid red while the effect is on."""
    p = panel.reg[f"fx.{name}.on"]
    on = bool(fx.values[name]["on"])
    h = imgui.get_font_size() + 2 * ui.CHIP_PAD.y        # a chip's height (ui.chip)
    dl = imgui.get_window_draw_list()

    # the LED: a chip-height square (a disc, at the chip's rounding)
    if ui.lit_chip(f"##led.{p.id}", on, size=imgui.ImVec2(h, h)):
        p.toggle()                  # Param.set on the base: a scene-setter's write
    r0, r1 = imgui.get_item_rect_min(), imgui.get_item_rect_max()
    c = imgui.ImVec2((r0.x + r1.x) / 2, (r0.y + r1.y) / 2)
    if on:
        dl.add_circle_filled(c, h * 0.2, ui.u32(ui.TEXT))
    else:
        dl.add_circle(c, h * 0.2, ui.u32(ui.DIM), 0, 1.5)
    panel._tip(p, lambda: _led_tip(panel, p))
    # the same param's menu on the LED, the name and the strip's check: a
    # key each, or the three would share one popup id and draw it thrice
    panel._ctx(p, key=".led")
    panel._learn_frame(p)

    # the name: opens the strip, and carries the modulation dot
    imgui.same_line(0, LED_GAP)
    if ui.lit_chip(f"{label}##chip.{p.id}", on, ui.TEXT if open_ else None,
                   imgui.ImVec2(max(1.0, width - h - LED_GAP), 0)):
        fx.select(name)
    panel._tip(p)
    panel._ctx(p, key=".chip")
    panel._learn_frame(p)
    panel._mod_dot(p)
    armed = panel.learn is not None and panel.learn.learning == p.id
    if open_ and not armed:         # "open", apart from "on": an outline round both parts
        r1 = imgui.get_item_rect_max()
        dl.add_rect(imgui.ImVec2(r0.x - 1, r0.y - 1), imgui.ImVec2(r1.x + 1, r1.y + 1),
                    ui.u32(ui.TEXT), h / 2 + 1, 2.0)


def _led_tip(panel, p) -> str:
    """The LED's hover: what a click does. A click writes the base, so the
    base is what it reads; while a source rides the switch the effective
    state (the dot) can differ, and the modulation line says so."""
    tip = LED_ON_TIP if p.base else LED_OFF_TIP
    return f"{tip}\n{panel._mod_line(p)}" if p.modulated else tip


def _state(panel):
    """The live FxState — the renderer's; None headless."""
    chain = getattr(panel.renderer, "fx", None)
    return None if chain is None else chain.state


def _error(chain, fx, name: str) -> str:
    if chain is not None:
        return chain.error(name)
    return fx.errors.get(name, "")
