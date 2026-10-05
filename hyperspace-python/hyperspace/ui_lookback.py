"""The LOOKBACK page — the frame history and its composite (lookback.py).

Three sections on the dream group, named for what a knob acts on (plan 20
WP4): ECHOES (how bright, how long, how many, how far apart, and a row of
live thumbnails — the echoes newest first, straight from the atlas
texture, with the dream buffer at the end when a worker has filled it),
DREAM (the worker's status line — device and copy path, ms per submit,
frames behind, drops, NaN resets, the stability clamp — or why there is
none; the net layer as a row of chips; the worker's settings; the dream
buffer's hue, saturation and tint — lookback.py's chroma()), and BOTH
(the grade, the occlusion and the size, which every layer of the wake
shares). `SECTIONS` is the layout: which param is drawn under which
title, in order, two to a row. One preset strip for the group, under the
page's title.

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
from .lookback import LAYERS, RES, tint_colour
from .params import Kind

# what is drawn under each title, in order. `dream.on` is the page's own
# switch, above them; `dream.layer` is the DREAM section's chip row and the
# rest are half-width cells, two to a row.
SECTIONS = {
    "echoes": ("dream.echo_mix", "dream.fade", "dream.echoes", "dream.gap"),
    "dream": ("dream.layer", "dream.mix", "dream.k", "dream.step", "dream.steps",
              "dream.mask_decay", "dream.jitter", "dream.octaves", "dream.hue",
              "dream.sat", "dream.tint", "dream.tint_from", "dream.tint_hue",
              "dream.tint_sat"),
    "both": ("dream.darken", "dream.contrast", "dream.occlude", "dream.res"),
}
NOTES = {"dream": "[dream] in config.toml", "both": "echoes and dream alike"}
# a cell's label: the section says whose knob it is, so the registry's
# "Echo …" / "Dream …" is dropped here (the ROUTING page, a Learn message
# and the desk diagram say the registry's)
SHORT = {"dream.echo_mix": "brightness", "dream.fade": "fade time", "dream.echoes": "count",
         "dream.gap": "time apart", "dream.mix": "brightness", "dream.k": "speed",
         "dream.step": "strength", "dream.steps": "passes", "dream.mask_decay": "linger",
         "dream.jitter": "jitter", "dream.octaves": "scales", "dream.hue": "hue",
         "dream.sat": "saturation", "dream.tint": "tint", "dream.tint_from": "tint from",
         "dream.tint_hue": "tint hue", "dream.tint_sat": "tint sat", "dream.darken": "darken",
         "dream.contrast": "contrast", "dream.occlude": "shape hides", "dream.res": "detail"}
# dream.layer's chips, one per lookback.LAYERS entry. The first three are
# the words the param's tip uses; the inception layers share one description
# there, so they keep the end of their names until someone has looked at
# them side by side (plan 20 hand check P5). Renaming is one line each.
LAYER_CHIPS = {"conv2_2": "grain", "conv3_3": "swirl", "conv4_3": "blot",
               "inception3b": "3b", "inception4c": "4c", "inception4e": "4e"}
LAYER_SAYS = {"conv2_2": "fine grain", "conv3_3": "the classic swirl", "conv4_3": "blotchier",
              "inception3b": "the eyes-and-dogs curls, finest",
              "inception4c": "the eyes-and-dogs curls", "inception4e": "the eyes-and-dogs curls, "
              "largest"}
LABEL_W = 94        # a cell's label column: "SHAPE HIDES", the longest, is 88 px
THUMB_H = 48        # thumbnail height, px; width follows the echo's aspect
TIP_W = 380         # this page's own hovers wrap at this width (a set_tooltip line does not)
STATUS_LINES = 3   # the worker's status is at most this tall; the rest is on its hover


def page_label(pid: str) -> str:
    """What the page calls `pid`: its cell's label, the switch's own, or —
    for the layer — its chips'."""
    if pid == "dream.layer":
        return " / ".join(LAYER_CHIPS.get(name, name) for name in LAYERS)
    return SHORT.get(pid, "Look-back")


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
    if getattr(lb, "error", ""):
        imgui.text_colored(ui.WARN, f"GLSL: {lb.error} — on the shipped helpers")
    imgui.spacing()

    panel._section("echoes", note=_trail_note(r))
    _cells(panel, lb, "##echoes", SECTIONS["echoes"])
    _thumbnails(panel, lb)
    imgui.spacing()

    panel._section("dream", note=NOTES["dream"])
    _worker_line(panel, lb)
    _layer_chips(panel)
    _cells(panel, lb, "##dream", [pid for pid in SECTIONS["dream"] if pid != "dream.layer"])
    imgui.spacing()

    panel._section("both", note=NOTES["both"])
    _cells(panel, lb, "##both", SECTIONS["both"])


def _say(text: str) -> None:
    """A hover that wraps: a chip's, the swatch's and the worker's whole
    status are longer than a tooltip's one line can be wide."""
    if imgui.begin_tooltip():
        imgui.push_text_wrap_pos(TIP_W)
        imgui.text_unformatted(text)
        imgui.pop_text_wrap_pos()
        imgui.end_tooltip()


def _cells(panel, lb, table: str, ids) -> None:
    """`ids` two to a row: a slider, or a combo for an enum, behind its label."""
    if not imgui.begin_table(table, 2, imgui.TableFlags_.sizing_stretch_same):
        return
    for pid in ids:
        imgui.table_next_column()
        p = panel.reg[pid]
        if p.kind is not Kind.ENUM:
            panel.half(pid, SHORT[pid], label_w=LABEL_W)
            continue
        panel._label_cell(SHORT[pid], width=LABEL_W)
        panel._tip(p)
        if pid == "dream.res":          # the size it comes to, where the page had a line for it
            panel._combo(pid, -1, tip=f"{p.tip}\n\nNow: {_echo_text(lb)}.")
        else:
            panel._combo(pid, -1)
    if "dream.tint_sat" in ids:         # the colour those three make, in the cell left over
        imgui.table_next_column()
        _tint_swatch(panel, lb)
    imgui.end_table()


def _layer_chips(panel) -> None:
    """`dream.layer` as six chips tiling the row, the lit one its base. A
    click is a scene-setter's write (the layer is not modulatable: a change
    loads another trunk); a right-click on any of them is the param's menu."""
    a = panel.reg["dream.layer"]
    p = panel._real(a)
    gap = imgui.get_style().item_spacing.x
    w = max((imgui.get_content_region_avail().x - gap * (len(LAYERS) - 1)) / len(LAYERS), 1.0)
    row = None
    for k, name in enumerate(LAYERS):
        if k:
            imgui.same_line()
        hit = ui.lit_chip(f"{LAYER_CHIPS.get(name, name)}##chip.{a.id}.{k}", k == p.base,
                          size=imgui.ImVec2(w, 0))
        if imgui.is_item_hovered():
            _say(f"{name}: {LAYER_SAYS.get(name, name)}\n\n{a.tip}")
        panel._ctx(a, key=f".{k}")
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        row = (lo, hi) if row is None else (row[0], hi)
        if hit:
            p.set(k)
    # armed to learn: one outline round the row, as a combo would have had
    # one (panel._learn_frame per chip would draw six)
    lrn = panel.learn
    if row is not None and lrn is not None and lrn.learning == a.id:
        imgui.get_window_draw_list().add_rect(
            imgui.ImVec2(row[0].x - 2, row[0].y - 2), imgui.ImVec2(row[1].x + 2, row[1].y + 2),
            ui.u32(ui.RED), 999.0, 2.0)


def _trail_note(r) -> str:
    """How far back the trail reaches — in seconds, the same on any screen
    (plan 14 WP6). What an echo is, is the brightness cell's hover."""
    n, gap = int(r["dream.echoes"].value), float(r["dream.gap"].value)
    if n <= 0:
        return "no echoes: the dream alone"
    if gap <= 0:
        return f"{n}, one a frame"
    return f"{n} × {gap * 1000:.0f} ms · the trail reaches {n * gap:.2f} s"


def _status(lb, on: bool) -> str:
    if lb is None:
        return "no renderer"
    if not on:
        return "off"
    if lb.atlas is None:
        return getattr(lb, "ring_error", "") or "starting"
    n = len(lb.thumbnails())
    dream = "dream" if lb.dream_frame >= 0 else "no dream"
    return f"{n} echo(es) · {dream}"


def _tint_swatch(panel, lb) -> None:
    """The tint colour the composite uses this frame, as a swatch: the
    chosen one, or — from the scene — whatever hue the newest echo had."""
    r = panel.reg
    scene = int(r["dream.tint_from"].value) == 1
    live = getattr(lb, "tint_rgb", None)         # None without a renderer
    if live is not None:
        rgb = live()
    elif scene:
        rgb = (1.0, 1.0, 1.0)
    else:
        rgb = tint_colour(r["dream.tint_hue"].value, r["dream.tint_sat"].value)
    panel._label_cell("the tint", width=LABEL_W)
    imgui.color_button("##tint", imgui.ImVec4(*rgb, 1.0),
                       imgui.ColorEditFlags_.no_tooltip | imgui.ColorEditFlags_.no_alpha,
                       imgui.ImVec2(max(imgui.get_content_region_avail().x, 1.0),
                                    imgui.get_frame_height()))
    if imgui.is_item_hovered():
        if not scene:
            says = "the colour chosen (tint hue, tint sat)"
        elif getattr(lb, "scene_mean", None):
            says = "the scene's mean hue"
        else:
            says = "the scene's mean hue — nothing captured yet"
        _say(f"The colour the dream is tinted towards: {says}.")


def _worker(lb):
    """The attached source if it is a worker with a status line."""
    src = getattr(lb, "source", None)
    return src if src is not None and hasattr(src, "status") else None


def _worker_note(lb) -> str:
    return "dream worker on" if _worker(lb) is not None else "echoes only: no worker"


def _worker_status(lb, error: str = "") -> str:
    """The worker's line: its own status, else why it is off — `error` is
    app._open_dream's reason (torch missing, with the setup commands)."""
    w = _worker(lb)
    if w is None:
        if error:
            return error
        return ("no worker — [dream] enabled in config.toml opens it (on by default); "
                "torch comes with `uv sync`")
    try:
        return w.status()
    except Exception as e:  # noqa: BLE001 — a status line must not take the page down
        return f"worker: {type(e).__name__}: {e}"[:120]


def fit_lines(text: str, width: float, lines: int) -> str:
    """`text`, or its start and an ellipsis when it would wrap to more than
    `lines` lines of `width` pixels in the current font (ui.fit_text for a
    wrapped paragraph)."""
    room = lines * imgui.get_text_line_height() + 0.5

    def fits(s: str) -> bool:
        return imgui.calc_text_size(s, wrap_width=width).y <= room
    if fits(text):
        return text
    lo, hi = 0, len(text)
    while lo < hi:                      # the longest start that fits with its "…"
        mid = (lo + hi + 1) // 2
        if fits(text[:mid] + "…"):
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + "…"


def _worker_line(panel, lb) -> None:
    """The worker's status, at most STATUS_LINES tall so the page's height
    does not depend on what the worker has to say: a longer one (drops, NaN
    resets, the clamp and an error at once) ends in an ellipsis and is whole
    on its hover."""
    err = getattr(panel, "dream_error", "")
    full = _worker_status(lb, err)
    shown = fit_lines(full, imgui.get_content_region_avail().x, STATUS_LINES)
    # torch missing: said plainly, in the warning colour
    imgui.push_style_color(imgui.Col_.text, ui.WARN if err else ui.FAINT)
    imgui.text_wrapped(shown)
    imgui.pop_style_color()
    if shown != full and imgui.is_item_hovered():
        _say(full)


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
            imgui.set_tooltip(f"echo {k + 1} · {t['age'] * 1000:.0f} ms old · weight "
                              f"{t['weight']:.3f}")
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
