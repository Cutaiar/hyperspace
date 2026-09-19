"""The LOOKBACK page — the frame history and its composite (lookback.py).

Three sections on the dream group: the composite (on, the two mixes, the
age fade and the grade), the history (depth, cadence, size, and a row of
live thumbnails — the echoes newest first, straight from the atlas
texture, with the dream buffer at the end when a worker has filled it),
and the dream worker's own settings, which are presettable now and take
effect once WP6b's worker is attached. One preset strip for the group,
under the first title.

A function over the Panel, like ui_presets: it draws with the panel's
widget helpers and keeps no state, so a hot reload of this module lands
on the next frame. Without a renderer (headless tests) or before the
first capture, the thumbnail row says so instead of drawing textures;
the control window shares the render window's GL context, so the atlas
is a plain texture id to imgui there.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui
from .lookback import RES

THUMB_H = 40        # thumbnail height, px; width follows the echo's aspect


def page(panel, dt: float) -> None:
    r = panel.reg
    st = r["dream.on"]
    lb = getattr(panel.renderer, "lookback", None)

    panel._section("look-back", "dream", note="echoes only until WP6b")
    panel._check("dream.on")
    imgui.same_line(imgui.get_content_region_avail().x - 150)
    imgui.text_disabled(_status(lb, bool(st.base)))
    panel._row("dream.mix")
    panel._row("dream.echo_mix")
    panel._row("dream.decay")
    panel._row("dream.darken")
    panel._row("dream.contrast")
    imgui.spacing()

    panel._section("history", note="rebuilds the ring")
    panel._row("dream.echoes")
    ui._micro("every")
    panel._tip(r["dream.every"])
    imgui.same_line(ui.LABEL_W)
    panel._slider("dream.every", 92)
    imgui.same_line()
    panel._combo("dream.res", 62)
    imgui.same_line()
    imgui.text_disabled(_echo_text(lb))
    _thumbnails(panel, lb)
    imgui.spacing()

    panel._section("dream worker", note="WP6b")
    ui._micro("net")
    panel._tip(r["dream.layer"])
    imgui.same_line(ui.LABEL_W)
    panel._combo("dream.layer", 100)
    imgui.same_line()
    panel._combo("dream.octaves", 62)
    imgui.same_line()
    panel._slider("dream.steps")
    panel._row("dream.step")
    panel._row("dream.k")
    panel._row("dream.mask_decay")
    panel._row("dream.jitter")


def _status(lb, on: bool) -> str:
    if lb is None:
        return "no renderer"
    if not on:
        return "off"
    if lb.atlas is None:
        return "starting"
    n = len(lb.thumbnails())
    dream = "dream" if lb.dream_frame >= 0 else "no dream"
    return f"{n} echo(es) · {dream}"


def _echo_text(lb) -> str:
    if lb is None or lb.atlas is None:
        return f"{RES[0]}–{RES[-1]} px short side"
    w, h = lb.echo
    return f"{w}×{h} px"


def _thumbnails(panel, lb) -> None:
    """The echoes newest first, then the dream buffer: what the composite
    sees this frame, with each one's age and weight on hover."""
    if lb is None or lb.atlas is None:
        imgui.text_disabled("no history yet — turn look-back on")
        return
    thumbs = lb.thumbnails()
    if not thumbs and lb.dream_frame < 0:
        imgui.text_disabled("nothing captured yet")
        return
    ew, eh = lb.echo
    size = imgui.ImVec2(THUMB_H * ew / max(eh, 1), THUMB_H)
    tex = imgui.ImTextureRef(lb.atlas.glo)
    origin = imgui.get_cursor_screen_pos()
    # as many as fit on one line, room kept for the dream and a "+n"
    avail = imgui.get_content_region_avail().x - 30 - (size.x + 8 if lb.dream_frame >= 0 else 0)
    fit = max(1, int(avail // (size.x + 3)))
    shown = thumbs[:fit]
    for k, t in enumerate(shown):
        if k:
            imgui.same_line(0, 3)
        imgui.image(tex, size, imgui.ImVec2(*t["uv0"]), imgui.ImVec2(*t["uv1"]))
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"echo {k + 1} · age {t['age']} · weight {t['weight']:.3f}")
    if len(thumbs) > fit:
        imgui.same_line(0, 3)
        imgui.text_disabled(f"+{len(thumbs) - fit}")
    if lb.dream_frame >= 0:
        if shown:
            imgui.same_line(0, 8)
        imgui.image(imgui.ImTextureRef(lb.dream.glo), size, imgui.ImVec2(0, 1),
                    imgui.ImVec2(1, 0))
        if imgui.is_item_hovered():
            imgui.set_tooltip(f"dream buffer · answers frame {lb.dream_frame}")
    # a hairline under the row: newest at the left, the dream at the end
    r1 = imgui.get_item_rect_max()
    dl = imgui.get_window_draw_list()
    dl.add_line(imgui.ImVec2(origin.x, r1.y + 2), imgui.ImVec2(r1.x, r1.y + 2),
                imgui.color_convert_float4_to_u32(imgui.ImVec4(0.22, 0.22, 0.22, 1)))
