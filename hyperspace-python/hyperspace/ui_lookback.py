"""The LOOKBACK page — the frame history and its composite (lookback.py).

Four sections on the dream group: the composite (on, the two mixes, the
age fade and the grade), the chroma (the dream buffer's hue, saturation and
tint — lookback.py's chroma()), the history (depth, cadence, size, and a row of
live thumbnails — the echoes newest first, straight from the atlas
texture, with the dream buffer at the end when a worker has filled it),
and the dream worker's settings (dream.py) with its status line —
device and copy path, ms per submit, frames behind, drops, NaN resets,
the stability clamp — or why there is none. One preset strip for the
group, under the first title.

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
from .lookback import RES, tint_colour

RES_W = 84          # the res and octaves combos
THUMB_H = 48        # thumbnail height, px; width follows the echo's aspect


def page(panel, dt: float) -> None:
    r = panel.reg
    st = r["dream.on"]
    lb = getattr(panel.renderer, "lookback", None)

    panel._section("look-back", "dream", note=_worker_note(lb))
    panel._check("dream.on")
    status = _status(lb, bool(st.base))
    imgui.same_line(imgui.get_content_region_avail().x - imgui.calc_text_size(status).x)
    imgui.align_text_to_frame_padding()
    imgui.text_disabled(status)
    panel._row("dream.mix")
    panel._row("dream.echo_mix")
    panel._row("dream.decay")
    panel._row("dream.darken")
    panel._row("dream.contrast")
    imgui.spacing()

    panel._section("chroma", note="the dream buffer's colour")
    panel._row("dream.hue")
    panel._row("dream.sat")
    panel._row("dream.tint")
    ui._micro("from")
    panel._tip(r["dream.tint_from"])
    imgui.same_line(ui.LABEL_W)
    panel._combo("dream.tint_from", 72)
    imgui.same_line()
    _tint_swatch(r, lb)
    panel._row("dream.tint_hue")
    panel._row("dream.tint_sat")
    imgui.spacing()

    panel._section("history", note="rebuilds the ring")
    panel._row("dream.echoes")
    panel._label_cell("every")
    panel._tip(r["dream.every"])
    panel._slider("dream.every", -(RES_W + imgui.get_style().item_spacing.x))
    imgui.same_line()
    panel._combo("dream.res", RES_W)
    imgui.text_disabled(f"echo size  {_echo_text(lb)}")
    _thumbnails(panel, lb)
    imgui.spacing()

    panel._section("dream worker", note="[dream] in config.toml")
    imgui.push_style_color(imgui.Col_.text, ui.FAINT)
    imgui.text_wrapped(_worker_status(lb))
    imgui.pop_style_color()
    panel._label_cell("net")
    panel._tip(r["dream.layer"])
    panel._combo("dream.layer", -(RES_W + imgui.get_style().item_spacing.x))
    imgui.same_line()
    panel._combo("dream.octaves", RES_W)
    panel._row("dream.steps")
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


def _tint_swatch(r, lb) -> None:
    """The tint colour the composite uses this frame, as a swatch: the
    chosen one, or — from the scene — whatever hue the newest echo had."""
    scene = int(r["dream.tint_from"].value) == 1
    live = getattr(lb, "tint_rgb", None)         # None without a renderer
    if live is not None:
        rgb = live()
    elif scene:
        rgb = (1.0, 1.0, 1.0)
    else:
        rgb = tint_colour(r["dream.tint_hue"].value, r["dream.tint_sat"].value)
    imgui.color_button("##tint", imgui.ImVec4(*rgb, 1.0),
                       imgui.ColorEditFlags_.no_tooltip | imgui.ColorEditFlags_.no_alpha,
                       imgui.ImVec2(36, imgui.get_frame_height()))
    if scene:
        imgui.same_line()
        imgui.text_disabled("the scene's mean hue" if getattr(lb, "scene_mean", None)
                            else "the scene's mean hue — nothing captured yet")


def _worker(lb):
    """The attached source if it is a worker with a status line."""
    src = getattr(lb, "source", None)
    return src if src is not None and hasattr(src, "status") else None


def _worker_note(lb) -> str:
    return "dream worker on" if _worker(lb) is not None else "echoes only: no worker"


def _worker_status(lb) -> str:
    w = _worker(lb)
    if w is None:
        return "no worker — [dream] enabled = true needs torch (uv sync --extra dream)"
    try:
        return w.status()
    except Exception as e:  # noqa: BLE001 — a status line must not take the page down
        return f"worker: {type(e).__name__}: {e}"[:120]


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
                ui.u32(ui.LINE))
