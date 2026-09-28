"""The FX page — the effect stack (fx.py).

The chain's bypass and mix, then one chip per effect in stack order, lit
while it is on: clicking a chip switches the effect and opens its strip,
right-clicking it binds it (MIDI learn) like any widget. The open strip
is the effect's own five (on, mix, speed, blend, order) and a row per
annotated uniform, with the file's parse or compile error under it.

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

CHIPS_PER_ROW = 4
ORDER_W = 96        # the order slider beside the blend combo


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
    sp = imgui.get_style().item_spacing.x
    w = (imgui.get_content_region_avail().x - sp * (CHIPS_PER_ROW - 1)) / CHIPS_PER_ROW
    for k, name in enumerate(names):
        if k % CHIPS_PER_ROW:
            imgui.same_line()
        label = fx.specs[name].label + (" !" if _error(chain, fx, name) else "")
        color = ui.TEXT if name == sel else None
        if panel._lit_button(f"fx.{name}.on", label, bool(fx.values[name]["on"]),
                             color=color, width=w):
            r["fx.select"].set(k)
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


def _state(panel):
    """The live FxState — the renderer's; None headless."""
    chain = getattr(panel.renderer, "fx", None)
    return None if chain is None else chain.state


def _error(chain, fx, name: str) -> str:
    if chain is not None:
        return chain.error(name)
    return fx.errors.get(name, "")
