"""The LOOKBACK page — the look-back and the dream, as the two picture
nodes they are (plan 36 T4; redrawn by plan 49 stage 2).

The owner, 2026-11-02, on the page's old split into look-back / dream /
"both": "a horrid representation of what's going on there". Since plan 36
they are two nodes on GRAPH, each picture in → picture out, and the page
draws them so, top to bottom under one preset strip for the dream group:

  LOOK-BACK   picture in → trail out. Its head says how far back the
              trail reaches; then what it records (a combo of the graph's
              pictures, `lookback.image`) and what its trail is laid over,
              in words; its knobs (`params.is_lookback_knob`: brightness,
              fade time, count, time apart, shape hides, darken, contrast,
              detail); the echoes it holds as thumbnails, newest first.
  DREAM       picture in → dreamed picture out. Its head is `dream.on`
              (off: the picture passes through untouched, the worker
              idle) and its state; the worker's status line, the net
              layer as one menu of every layer of both nets, its knobs,
              the tint swatch, and the dream buffer's thumbnail.

What the old page called "both" is named for what it is: darken,
contrast and detail are the look-back's knobs (`LOOKBACK_KEYS`), and the
dream reads them too — one state, `Renderer.dreamer` is made on the
look-back's — so the dream says so in a line (`GRADE_LINE`), not a third
section. A node not on the canvas says so on its head. `SECTIONS` is the
layout: which param is drawn under which node, in order, two to a row
(one where the room is narrower than `TWO_UP`, the side pane).

One function, `page`, for the LOOKBACK page and GRAPH's side pane's
lookback section (ui_pane.py). A function over the Panel, like
ui_presets: it draws with the panel's widget helpers and keeps no state,
so a hot reload of this module lands on the next frame. Without a
renderer (headless tests) or before the first capture, the thumbnail row
says so instead of drawing textures; the control window shares the
render window's GL context, so the atlas is a plain texture id to imgui
there.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import graphview, learn, ui
from .graph import lookback_words
from .lookback import LAYER_INFO, LAYERS, RES, tint_colour
from .params import Kind

# what is drawn under each node, in order (plan 49 stage 2): the look-back's
# own knobs (`params.LOOKBACK_KEYS`), then the dream's — `dream.on` on its
# head, `dream.layer` its layer menu, the rest half-width cells
SECTIONS = {
    "look-back": ("dream.echo_mix", "dream.fade", "dream.echoes", "dream.gap",
                  "dream.occlude", "dream.darken", "dream.contrast", "dream.res"),
    "dream": ("dream.on", "dream.layer", "dream.mix", "dream.k", "dream.step", "dream.steps",
              "dream.mask_decay", "dream.jitter", "dream.octaves", "dream.hue",
              "dream.sat", "dream.tint", "dream.tint_from", "dream.tint_hue",
              "dream.tint_sat"),
}
# each node's head: what goes in and what comes out (plan 36's two picture nodes)
PORTS = {"look-back": "picture in → trail out",
         "dream": "picture in → dreamed picture out"}
GRADE = ("dream.darken", "dream.contrast", "dream.res")     # the look-back's, read by the dream
GRADE_LINE = "graded by the look-back's darken and contrast, sent at its detail"
OFF_CANVAS = "not on the canvas"
TWO_UP = 360.0      # px: narrower than this (the side pane), the cells go one to a row
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
LABEL_W = 94        # a cell's label column: "SHAPE HIDES", the longest, is 88 px
LAYER_POPUP_H = 520  # the layer menu's most height before it scrolls, px
THUMB_H = 48        # thumbnail height, px; width follows the echo's aspect
STATUS_LINES = 3   # the worker's status is at most this tall; the rest is on its hover


def page_label(pid: str) -> str:
    """What the page calls `pid`: its cell's label, the switch's own, or —
    for the layer, a menu with no label — the layer's own name."""
    if pid == "dream.layer":
        return "(the layer's name)"
    return SHORT.get(pid, "dream")


def page(panel, dt: float) -> None:
    """The look-back and the dream, as two picture nodes (the module's
    doc): the LOOKBACK page and the pane's lookback section."""
    r = panel.reg
    lb = getattr(panel.renderer, "lookback", None)
    dr = getattr(panel.renderer, "dreamer", None)       # plan 36 T4: the dream node's
    spec = _spec(panel)
    drawn = learn.drawn_of(spec) if spec is not None else None

    panel._section("look-back · dream", "dream", note=_worker_note(dr))
    if getattr(lb, "error", ""):
        imgui.text_colored(ui.WARN, f"GLSL: {lb.error} — on the shipped helpers")

    # LOOK-BACK: picture in → trail out
    _node_head(panel, "look-back", _held(lb) + _trail_note(r),
               drawn is None or "lookback" in drawn)
    # plan 35 U: what the look-back records — a combo of the graph's
    # pictures setting the wire into `lookback.image` (plan 36 T4), one GRAPH edit
    # (`graphview.set_picture`) — and what it draws over, in words, beside it
    _records_row(panel, spec)
    _cells(panel, lb, "##look-back", SECTIONS["look-back"])
    _thumbnails(panel, lb)
    imgui.spacing()

    # DREAM: picture in → dreamed picture out; off passes it through
    _node_head(panel, "dream", _dream_word(dr, bool(r["dream.on"].base)),
               drawn is None or "dream" in drawn, switch="dream.on")
    _worker_line(panel, dr)
    _layer_menu(panel)
    _cells(panel, dr, "##dream", [pid for pid in SECTIONS["dream"]
                                  if pid not in ("dream.on", "dream.layer")])
    ui._micro(ui.fit_text(GRADE_LINE.upper(), imgui.get_content_region_avail().x), ui.FAINT)


def _spec(panel):
    """The loaded preset's graph (`Panel.graph_now`), or None: a stand-in
    renderer or library, no graph."""
    now = getattr(panel, "graph_now", None)
    try:
        return now()[1] if now is not None else None
    except (AttributeError, TypeError):
        return None


NODE_BG = imgui.ImVec4(0.16, 0.16, 0.18, 1.0)    # a node head's band (GRAPH's node face)


def _node_head(panel, title: str, word: str, on_canvas: bool,
               switch: str | None = None) -> None:
    """A node's head, one control tall, drawn as GRAPH draws a node: a band
    with its title, what it takes and gives (`PORTS`), and `word` at its
    right — or, for a node the graph does not hold, that it is not on the
    canvas. `switch`: the node's on/off (`dream.on`), a tick at its start."""
    dl = imgui.get_window_draw_list()
    p0 = imgui.get_cursor_screen_pos()
    w, h = imgui.get_content_region_avail().x, imgui.get_frame_height()
    dl.add_rect_filled(p0, imgui.ImVec2(p0.x + w, p0.y + h), ui.u32(NODE_BG), 5.0)
    dl.add_rect(p0, imgui.ImVec2(p0.x + w, p0.y + h), ui.u32(ui.LINE), 5.0)
    if switch is not None:
        panel._check(switch, "")
        imgui.same_line(0, 6)
    else:
        imgui.dummy(imgui.ImVec2(2, h))
        imgui.same_line(0, 6)
    imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + (h - ui.FONT_MICRO) / 2 - 1)
    ui._micro(title, ui.TEXT)
    imgui.same_line(0, 10)
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    try:
        right = word if on_canvas else OFF_CANVAS
        rw = min(imgui.calc_text_size(right.upper()).x, w * 0.5)
        right = ui.fit_text(right.upper(), rw)
        room = p0.x + w - 8 - rw - 10 - imgui.get_cursor_screen_pos().x
        ports = ui.fit_text(PORTS[title].upper(), room) if room > 24 else ""
        if ports:
            imgui.text_colored(ui.FAINT, ports)
            imgui.same_line(0, 10)
        imgui.set_cursor_screen_pos(imgui.ImVec2(p0.x + w - 8 - imgui.calc_text_size(right).x,
                                                 imgui.get_cursor_screen_pos().y))
        imgui.text_colored(ui.FAINT if on_canvas else ui.WARN, right)
    finally:
        imgui.pop_font()
    if imgui.is_item_hovered():
        ui.tooltip(f"{title}: {PORTS[title]}" + ("" if on_canvas else
                   f" — {OFF_CANVAS}: its knobs act once GRAPH has one (right-click the "
                   "canvas, look-back ▸)"))
    imgui.set_cursor_screen_pos(imgui.ImVec2(p0.x, p0.y + h + imgui.get_style().item_spacing.y))


def _held(lb) -> str:
    """How many echoes the ring holds, for the look-back's head."""
    if lb is None:
        return ""
    if lb.atlas is None:
        return f"{getattr(lb, 'ring_error', '') or 'no echoes'} · "
    return f"{len(lb.thumbnails())} held · "


def _dream_word(dr, on: bool) -> str:
    """The dream's state on its head (plan 36 T4: `dream.on` is the
    dream's — off, it passes its picture through)."""
    if not on:
        return "off: passes the picture through"
    return "dreaming" if getattr(dr, "dream_frame", -1) >= 0 else "no dream yet"


CAPTURE = "lookback.image"            # plan 36 T4: what it records is its image
RECORDS_NOTHING = "nothing — the echoes fade"
RECORDS_TIP = ("what the look-back records: the picture wired into lookback.image — "
               "the echoes are made of it (a GRAPH edit, one undo step)")


def capture_line(spec) -> str:
    """The LOOKBACK page's "records:" (plan 35 U): the source wired into
    `lookback.image` by its title (`graphview.picture_label`: "Scene"),
    or "nothing — the echoes fade" with no wire there. `spec` is the
    loaded preset's graph (`graphview.page_spec`: None is the empty
    frame, plan 36 T3)."""
    spec = graphview.page_spec(spec)
    now = graphview.picture_now(spec, CAPTURE)
    return "records: " + (RECORDS_NOTHING if now == graphview.NOTHING
                          else graphview.picture_label(spec, now))


def draws_over_line(spec) -> str:
    """"draws over: <the picture under it>" — words alone (plan 35 U; plan
    36 T4: the `under` of the composite its trail, or a dream of it, is
    laid into — D3: the look-back lays itself over nothing)."""
    spec = graphview.page_spec(spec)
    wires = list(spec.wires) if spec is not None else []
    trail = {"lookback"} | {w.node for w in wires if w.src == "lookback" and w.port == "image"
                            and w.node == "dream"}
    comp = next((w.node for w in wires if w.src in trail and w.port == "over"), None)
    now = graphview.picture_now(spec, f"{comp}.under") if comp else graphview.NOTHING
    return "draws over: " + (graphview.NOTHING if now == graphview.NOTHING
                             else graphview.picture_label(spec, now))


def _records_row(panel, spec) -> None:
    """The records combo, half the row, and "draws over:" beside it; the
    last edit's words under them while there are any. `spec` is the
    loaded preset's graph (`_spec`)."""
    frame = graphview.page_spec(spec)
    width = imgui.get_content_region_avail().x * 0.55
    # (the hover: the longer words — "with the hands", a placed effect)
    tip = RECORDS_TIP if frame is None else f"{lookback_words(frame.wiring())}\n\n{RECORDS_TIP}"
    panel._picture_combo(frame, CAPTURE, capture_line(frame), width, False, tip,
                         key="lookback_said")
    imgui.same_line()
    imgui.align_text_to_frame_padding()
    over = draws_over_line(frame)
    imgui.text_disabled(ui.fit_text(over, imgui.get_content_region_avail().x))
    panel._edit_said("lookback_said")




def _cells(panel, lb, table: str, ids) -> None:
    """`ids` two to a row (one in a room narrower than `TWO_UP`: the side
    pane): a slider, or a combo for an enum, behind its label."""
    cols = 2 if imgui.get_content_region_avail().x >= TWO_UP else 1
    if not imgui.begin_table(table, cols, imgui.TableFlags_.sizing_stretch_same):
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


def layer_menu() -> list[tuple[str, list[str]]]:
    """The layer menu's groups in order: (net, its layer names shallow →
    deep), from lookback.LAYER_INFO."""
    out: list[tuple[str, list[str]]] = []
    for name, (net, _, _) in LAYER_INFO.items():
        if not out or out[-1][0] != net:
            out.append((net, []))
        out[-1][1].append(name)
    return out


def layer_preview(name: str, width: float) -> str:
    """The closed menu's text: the layer's name and its short description,
    cut to `width` in the current font."""
    short = LAYER_INFO.get(name, ("", "", ""))[1]
    return ui.fit_text(f"{name} · {short}" if short else name, width)


def _layer_menu(panel) -> None:
    """`dream.layer` as one combo the row wide: closed, the layer's name and
    short description; open, every layer of both nets under a heading for
    each, shallow → deep, the name and its short description on a line,
    the longer description on hover. The popup scrolls past LAYER_POPUP_H.
    A pick is a scene-setter's write (the layer is not modulatable: a change
    loads another trunk); a right-click is the param's menu."""
    a = panel.reg["dream.layer"]
    p = panel._real(a)
    k_now = int(p.base)
    now = LAYERS[k_now] if 0 <= k_now < len(LAYERS) else "—"
    imgui.set_next_item_width(-1)
    pad = imgui.get_style().frame_padding.x
    room = imgui.get_content_region_avail().x - imgui.get_frame_height() - 2 * pad
    imgui.set_next_window_size_constraints(
        imgui.ImVec2(0, 0), imgui.ImVec2(1e6, min(LAYER_POPUP_H,
                                                  imgui.get_io().display_size.y * 0.7)))
    if not imgui.begin_combo(f"##{a.id}", layer_preview(now, room)):
        # closed: the frame is the last item, for the hover, the param's
        # menu and the learn outline (open, the popup is the last window)
        if imgui.is_item_hovered() and now in LAYER_INFO:
            net, _, long = LAYER_INFO[now]
            ui.tooltip(f"{now} · {net}\n\n{long}\n\n{a.tip}")
        panel._ctx(a)
        panel._learn_frame(a)
        panel._mod_dot(p)
        return
    name_w = max(imgui.calc_text_size(n).x for n in LAYERS) + 3 * pad
    for net, names in layer_menu():
        imgui.spacing()
        ui._micro(net, ui.FAINT)              # a heading, not a choice
        for name in names:
            k = LAYERS.index(name)
            _, short, long = LAYER_INFO[name]
            chosen = k == k_now
            x = imgui.get_cursor_pos_x()
            if imgui.selectable(f"{name}##layer.{name}", chosen)[0] and not chosen:
                p.set(k)
            if imgui.is_item_hovered():
                ui.tooltip(f"{name} · {net}\n\n{long}")
            if chosen and imgui.is_window_appearing():
                imgui.set_item_default_focus()
                imgui.set_scroll_here_y()
            imgui.same_line(x + name_w)
            imgui.text_colored(ui.TEXT if chosen else ui.DIM, short)
    imgui.end_combo()


def _trail_note(r) -> str:
    """How far back the trail reaches — in seconds, the same on any screen
    (plan 14 WP6). What an echo is, is the brightness cell's hover."""
    n, gap = int(r["dream.echoes"].value), float(r["dream.gap"].value)
    if n <= 0:
        return "no echoes: the dream alone"
    if gap <= 0:
        return f"{n}, one a frame"
    return f"{n} × {gap * 1000:.0f} ms · the trail reaches {n * gap:.2f} s"


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
        elif getattr(lb, "input_mean", None):
            says = "the scene's mean hue"
        else:
            says = "the scene's mean hue — nothing captured yet"
        ui.tooltip(f"The colour the dream is tinted towards: {says}.")


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
    # the dream buffer, while a worker has filled it, left of the words:
    # the dream's picture beside what its worker says (as tall as the words' room)
    thumb = _dream_thumb(lb)
    if thumb:
        imgui.same_line()
    shown = fit_lines(full, imgui.get_content_region_avail().x, STATUS_LINES)
    # torch missing: said plainly, in the warning colour
    imgui.push_style_color(imgui.Col_.text, ui.WARN if err else ui.FAINT)
    imgui.text_wrapped(shown)
    imgui.pop_style_color()
    if shown != full and imgui.is_item_hovered():
        ui.tooltip(full)


def _echo_text(lb) -> str:
    if lb is None or lb.atlas is None:
        return f"{RES[0]}–{RES[-1]} px short side"
    w, h = lb.echo
    return f"{w}×{h} px"


def _thumbnails(panel, lb) -> None:
    """The look-back's echoes newest first: what its trail is made of this
    frame, with each one's age and weight on hover."""
    if lb is None or lb.atlas is None:
        imgui.text_disabled("no history yet — wire a look-back on GRAPH")
        return
    thumbs = lb.thumbnails()
    if not thumbs:
        imgui.text_disabled("nothing captured yet")
        return
    ew, eh = lb.echo
    size = imgui.ImVec2(THUMB_H * ew / max(eh, 1), THUMB_H)
    tex = imgui.ImTextureRef(lb.atlas.glo)
    origin = imgui.get_cursor_screen_pos()
    # as many as fit on one line, room kept for a "+n"
    avail = imgui.get_content_region_avail().x - 30
    fit = max(1, int(avail // (size.x + 3)))
    shown = thumbs[:fit]
    for k, t in enumerate(shown):
        if k:
            imgui.same_line(0, 3)
        imgui.image(tex, size, imgui.ImVec2(*t["uv0"]), imgui.ImVec2(*t["uv1"]))
        if imgui.is_item_hovered():
            ui.tooltip(f"echo {k + 1} · {t['age'] * 1000:.0f} ms old · weight "
                              f"{t['weight']:.3f}")
    if len(thumbs) > fit:
        imgui.same_line(0, 3)
        imgui.text_disabled(f"+{len(thumbs) - fit}")
    # a hairline under the row: newest at the left
    r1 = imgui.get_item_rect_max()
    dl = imgui.get_window_draw_list()
    dl.add_line(imgui.ImVec2(origin.x, r1.y + 2), imgui.ImVec2(r1.x, r1.y + 2),
                ui.u32(ui.LINE))


def _dream_thumb(dr) -> bool:
    """The dream buffer — what the dream lays over its picture — as one
    thumbnail, while a worker has filled it (True); nothing before."""
    if dr is None or getattr(dr, "dream", None) is None or getattr(dr, "dream_frame", -1) < 0:
        return False
    w, h = getattr(dr.dream, "size", (16, 9))
    imgui.image(imgui.ImTextureRef(dr.dream.glo), imgui.ImVec2(THUMB_H * w / max(h, 1), THUMB_H),
                imgui.ImVec2(0, 1), imgui.ImVec2(1, 0))
    if imgui.is_item_hovered():
        ui.tooltip(f"dream buffer · answers frame {dr.dream_frame}")
    return True
