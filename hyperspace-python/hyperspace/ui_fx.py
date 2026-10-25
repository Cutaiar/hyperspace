"""The FX page — a browser of the effect nodes in the loaded graph (plan 33 U).

The owner's "file explorer" over the graph (row 348): the page lists every
effect instance the loaded preset's graph holds — in the run, on a branch,
unreached — grouped by where its path ends (`groups`): **Run** (in wire
order), **→ faces**, **→ pattern media**, **→ backdrop**, **→ output N**,
**→ <effect> aux**, and **reaches nothing** last. An effect behind a switch
is grouped by the switch's destination; one that ends in two places is
listed under each. The page adds, removes, wires and reorders nothing:
that is GRAPH's.

The head is `fx.on` and `fx.mix`, every effect's bypass and fade; the
**→ faces** group's header carries the two chips of `fx.face_map` (how a
picture wired into the faces sits on them). Each row is the effect's name
(a chip: a click picks it), an `on` check, a small `mix`, and its state in
a word — running, off, why it idles (`why_idle`) or its compile error. The
picked effect is one panel state shared with GRAPH's side pane
(`Panel.fx_selected`): picking a node on either page picks it on both.
Its **strip** is drawn under the list — the effect's own four (on, mix,
speed, blend) and a row per annotated uniform, with the file's parse or
compile error under its title — and **Show on GRAPH** selects and centres
its node there (`ui_graph.select_effect`). The strip is the GRAPH page's
side pane for a selected effect node too.

An effect that is not running says why on its strip (plan 16 WP3,
`why_idle`): one line over its rows — off, reaching nothing, on the faces
with Faces off, every effect bypassed, FX mix at 0, its own mix at 0 — with
a chip that mends the ones a click can ("turn on", "faces on", "effects
on"). The rows under the line are dimmed but live.

Gone with the stack (plan 33 T7, row 341): the chip grid and its
drag-to-reorder, the placed grid, the order slider, the ONTO chips, the
faces lines and `fx.select`.

A function over the Panel, like ui_lookback: no state of its own, and a
save of this file lands live (hotreload.MODULES). The effects are whatever
the loaded graph holds of the files in shaders/fx/, so the page draws from
the graph and the live FxState rather than a fixed id list.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui
from .fx import FACE_MAPS, FX_DIR, PER_FACE
from .graph import _PICTURE_PORTS, run_of, wire_node_kind

# the groups `groups` makes, as their headers say them
RUN = "Run"
FACES = "→ faces"
PATTERN = "→ pattern media"
BACKDROP = "→ backdrop"
UNREACHED = "reaches nothing"
# a picture port's sink → the group it ends in (an output, an aux: by name)
_ENDS = {"shape.faces": FACES, "pattern.media": PATTERN, "backdrop.image": BACKDROP,
         "fx.image": RUN}
EMPTY = "no effects in the graph — add one on GRAPH (right-click the canvas)"
SHOW = "Show on GRAPH"
NAME_W = 0.42       # of the page's width: a row's name chip
MIX_W = 0.30        # …and its mix
IDLE_ALPHA = 0.45   # how much of an idle strip's rows shows through the veil
# why_idle's reason → the strip's line, then the chip beside it, the param
# the chip sets and the chip's hover (None: a fader or GRAPH mends it, not a click)
IDLE = {
    "off": ("off — nothing below shows until it is on", "turn on", "fx.{name}.on",
            "Switch this effect on."),
    UNREACHED: ("it reaches nothing — wire it on GRAPH to see it", None, None, None),
    "faces off": ("it ends on the faces, and Faces is off", "faces on", "view.faces",
                  "Switch the faces on (the Faces check on the VIEW and FACES pages)."),
    "bypassed": ("every effect is bypassed", "effects on", "fx.on",
                 "Switch the effects on (the Effects check at the top)."),
    "fx mix 0": ("FX mix is at 0", None, None, None),     # its fader is at the top of the page
    "mix 0": ("its mix is at 0", None, None, None),       # its fader is the next row
}
# one line at the page's width (plan 20 WP2: it wrapped to two by 2 px)
RESET_NOTE = "a preset load resets these: save a preset to keep them"


def groups(spec) -> list[tuple[str, list[str]]]:
    """The effect instances of graph `spec` (a `graph.GraphSpec`; None for
    none) grouped by where their path ends, in the page's order: `Run` (the
    run's wire order, `graph.run_of`), `→ faces`, `→ pattern media`, `→
    backdrop`, `→ output <n>` by n, `→ <effect> aux` by effect, any other
    end (`→ history`), and `reaches nothing` last. A path is followed
    through effects' `image` inputs and through switches (to their
    destination, whatever their pick: the page shows what is wired);
    an effect ending in two places is in each group; within a group the
    effects are in path order, the head first. Empty groups are left out.
    Pure: it reads the spec alone (D1's placements as the wires they are)."""
    if spec is None:
        return []
    # (the picture ports `graph.reaches` follows: a value port carries none)
    wires = [w for w in spec.all_wires() if w.port in _PICTURE_PORTS]
    names = {e.name for e in spec.effects}
    for w in wires:
        names.update(n for n in (w.src, w.node) if wire_node_kind(n) == "effect")
    out_of: dict[str, list] = {}
    for w in wires:
        out_of.setdefault(w.src, []).append(w)
    run = run_of(spec)
    ends: dict[str, dict[str, int]] = {}      # effect → its ends → its distance from each

    def follow(node: str, seen: frozenset[str]) -> dict[str, int]:
        got: dict[str, int] = {}
        for w in out_of.get(node, ()):
            kind, port = wire_node_kind(w.node), w.port
            if w.node in seen:
                continue
            if kind in ("effect", "switch", "composite") and port != "aux":
                for end, d in follow(w.node, seen | {w.node}).items():
                    got[end] = min(got.get(end, d + 1), d + 1)
                continue
            end = _end_of(w.dst, kind, w.node, port)
            got[end] = min(got.get(end, 1), 1)
        return got

    for name in names:
        ends[name] = follow(name, frozenset({name}))
    # D1's `after` a node (plan 30): the effect is laid on that node's
    # picture wherever it goes — no wire of its own says where, so the
    # group is the place (`→ after hands`)
    for e in spec.effects:
        if e.placed and e.where[0] == "after" and not ends.get(e.name):
            ends[e.name] = {f"→ after {e.where[1]}": 1}
    by: dict[str, list[str]] = {}
    for name in sorted(names):
        for end in ends[name] or {UNREACHED: 0}:
            by.setdefault(end, []).append(name)
    for end, members in by.items():
        if end == RUN:
            members.sort(key=lambda n: (run.index(n) if n in run else len(run), n))
        else:                                  # the head first: the farthest from the sink
            members.sort(key=lambda n: (-ends[n].get(end, 0), n))
    return [(end, by[end]) for end in sorted(by, key=_group_key)]


def _end_of(dst: str, kind: str | None, node: str, port: str) -> str:
    """The group a wire into `dst` ends a path in."""
    if dst in _ENDS:
        return _ENDS[dst]
    if kind == "output":
        return f"→ output {node.partition('.')[2]}"
    if port == "aux":
        return f"→ {node} aux"
    return f"→ {node}"


def _group_key(end: str) -> tuple:
    fixed = {RUN: 0, FACES: 1, PATTERN: 2, BACKDROP: 3}
    if end in fixed:
        return (fixed[end], 0, "")
    if end == UNREACHED:
        return (9, 0, "")
    if end.startswith("→ output "):
        n = end[len("→ output "):]
        return (4, int(n) if n.isdecimal() else 0, n)
    if end.endswith(" aux"):
        return (5, 0, end)
    return (6, 0, end)


def _spec(panel):
    """The loaded preset's graph spec (`Panel.graph_now`), or None: a
    stand-in Panel, no presets, no graph."""
    now = getattr(panel, "graph_now", None)
    try:
        return now()[1] if now is not None else None
    except (AttributeError, TypeError):     # a stand-in renderer or library: no graph
        return None


def page(panel, dt: float) -> None:
    chain = getattr(panel.renderer, "fx", None)
    fx = _state(panel)
    panel._section("effects", "fx", note=f"shaders/{FX_DIR.name}/*.glsl · live")
    panel._check("fx.on")
    imgui.same_line()
    panel._slider("fx.mix")
    # plan 14 WP5: a preset load replaces every effect value (plan 13 D2),
    # so what is tried here is gone on the next F-key unless it is saved
    _faint(RESET_NOTE)
    if fx is None:
        imgui.text_disabled("no renderer")
        return
    found = groups(_spec(panel))
    if not found:
        imgui.text_disabled(EMPTY)
    sel = getattr(panel, "fx_selected", None)
    for title, names in found:
        _group(panel, chain, fx, title, names, sel)
    sel = getattr(panel, "fx_selected", None)
    if sel is None:
        return
    imgui.dummy(imgui.ImVec2(0, 2))
    # the button first, at the strip's head: a long strip never pushes it
    # off the page
    if sel in fx.specs:
        if ui.chip(f"{SHOW}##fx.show"):
            from . import ui_graph  # (late: ui_graph imports this page for its strip)
            ui_graph.select_effect(panel, sel)
        if imgui.is_item_hovered():
            imgui.set_tooltip("select this effect's node on the GRAPH page and bring it "
                              "on screen")
    strip(panel, sel)


def _group(panel, chain, fx, title: str, names: list[str], sel: str | None) -> None:
    """One group: its header (the faces' with `fx.face_map`'s chips), then
    a row per effect. Its widgets under an id of the group's, so an effect
    listed in two groups is two rows with ids of their own."""
    imgui.push_id(title)
    try:
        if title == FACES:
            _faces_header(panel)
        else:
            ui._micro(title, ui.DIM)
        for name in names:
            _effect_row(panel, chain, fx, title, name, name == sel)
    finally:
        imgui.pop_id()


def _effect_row(panel, chain, fx, title: str, name: str, open_: bool) -> None:
    """One effect's row: its name (a chip: a click picks it, never switches
    it), its `on`, a small `mix` and its state in a word. An instance whose
    file is gone has its name and the word alone."""
    avail = imgui.get_content_region_avail().x
    spec = fx.specs.get(name)
    label = spec.label if spec is not None else name
    if ui.lit_chip(f"{ui.fit_text(label, avail * NAME_W - 2 * ui.CHIP_PAD.x)}"
                   f"##row.{title}.{name}", open_, ui.TEXT if open_ else None,
                   imgui.ImVec2(avail * NAME_W, 0)):
        panel.fx_selected = name
    if imgui.is_item_hovered():
        imgui.set_tooltip(f"{name} — click to play its params below")
    if spec is None:
        imgui.same_line()
        imgui.text_colored(ui.WARN, f"no {fx.file_of(name)} effect in this build")
        return
    p = panel.reg.get(f"fx.{name}.on")
    if p is not None:
        imgui.same_line()
        real = panel._real(p)
        changed, on = imgui.checkbox(f"##on.{title}.{name}", bool(real.base))
        panel._tip(p)
        panel._ctx(p, key=".row")
        panel._learn_frame(p)
        panel._mod_dot(real)
        if changed:
            real.set(on)
    if f"fx.{name}.mix" in panel.reg:
        imgui.same_line()
        panel._slider(f"fx.{name}.mix", avail * MIX_W)
    imgui.same_line()
    word = state_word(chain, fx, name, title, bool(getattr(panel.view, "faces", True)))
    imgui.text_colored(ui.FAINT if word == "running" else ui.WARN,
                       ui.fit_text(word, imgui.get_content_region_avail().x))


def state_word(chain, fx, name: str, where: str = RUN, faces_on: bool = True) -> str:
    """A row's state in a word: `error: <first line>` for a file that does
    not compile, else why it idles (`why_idle`, with `where` its group —
    `reaches nothing`, the faces with Faces off), else `running`."""
    err = _error(chain, fx, name)
    if err:
        return f"error: {err.splitlines()[0]}"
    why = why_idle(fx, name, faces_on or where != FACES, reached=where != UNREACHED)
    return why if why is not None else "running"


def _faces_header(panel) -> None:
    """The `→ faces` group's header, one chip tall: its title and, at the
    right end, the two chips of `fx.face_map`, the lit one how the faces
    show a picture wired into them. A chip click is Param.set; its
    right-click is the param's menu, so it can be learned."""
    p = panel.reg.get("fx.face_map")
    _chip_baseline()
    ui._micro(FACES, ui.DIM)
    if p is None:
        return
    fx = _state(panel)
    now = getattr(fx, "face_map", PER_FACE)     # what the faces show: the effective value
    avail = imgui.get_content_region_avail().x
    x = imgui.get_cursor_pos_x() + avail - ui.chip_w(*FACE_MAPS)
    for i, label in enumerate(FACE_MAPS):
        imgui.same_line(x) if i == 0 else imgui.same_line()
        if ui.lit_chip(f"{label}##map.{p.id}.{i}", i == now):
            p.set(i)                            # a scene-setter's write to the base
        panel._tip(p, lambda: f"{p.tip}\n{panel._mod_line(p)}" if p.modulated else p.tip)
        panel._ctx(p, key=f".map{i}")           # a key each: one popup id per item
        panel._learn_frame(p)
        if i == now:
            panel._mod_dot(p)


def _where(panel, name: str) -> list[str]:
    """The groups effect `name` is listed in on the loaded graph."""
    return [title for title, names in groups(_spec(panel)) if name in names]


def strip(panel, sel: str) -> None:
    """One effect's strip — its title (its file and where its paths end in
    the hover), its tip, why it is idle, on and mix, speed and blend, then
    its own params: the FX page's open strip, and the GRAPH page's side
    column for a selected effect node (plan 28 N2)."""
    r = panel.reg
    chain = getattr(panel.renderer, "fx", None)
    fx = _state(panel)
    if fx is None or sel not in fx.specs:
        imgui.text_disabled(f"no effect {sel}" if fx is not None else "no renderer")
        return
    spec = fx.specs[sel]
    pre = f"fx.{sel}"
    where = _where(panel, sel)
    _strip_header(panel, fx, sel, " · ".join(where) if where else None)
    if spec.tip:
        imgui.push_style_color(imgui.Col_.text, ui.FAINT)
        imgui.text_wrapped(spec.tip)
        imgui.pop_style_color()
    err = _error(chain, fx, sel)
    if err:
        imgui.text_colored(ui.WARN, err)
    # plan 16 WP3: an effect that is not running says why, and the rows
    # under the line are dimmed but live — set it up dark, then switch it on.
    # Plan 33 T7: "faces off" and "reaches nothing" read its paths
    faces_on = bool(getattr(panel.view, "faces", True)) or not where or where != [FACES]
    idle = why_idle(fx, sel, faces_on, reached=where != [UNREACHED] if where else True)
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
    # plan 33 U: no order slider — an effect's place is its wires (GRAPH)
    panel._combo(f"{pre}.blend")
    drawn(f"{pre}.blend")
    mode = fx.values[sel].get("mode", 0)
    labels = {p.key: p.label.lower() for p in spec.params}
    choices = {p.key for p in spec.params if p.choices}
    for label, keys in strip_rows(sel, [p.key for p in spec.params if f"{pre}.{p.key}" in r],
                                  mode):
        if len(keys) == 1 and keys[0] in choices:
            # a discrete choice (plan 30 N8, `@param choice`): a picker
            panel._label_cell(labels[keys[0]])
            panel._ctx_label(r[f"{pre}.{keys[0]}"])   # its label opens the menu, as a row's
            panel._combo(f"{pre}.{keys[0]}")
            drawn(f"{pre}.{keys[0]}")
            line = compress_line(fx.values[sel]) if _is_palette(sel) and not mode else None
            if line is not None:
                imgui.push_style_color(imgui.Col_.text, ui.FAINT)
                imgui.text(line)
                imgui.pop_style_color()
            continue
        if len(keys) == 1:
            panel._row(f"{pre}.{keys[0]}", label=labels[keys[0]])
            drawn(f"{pre}.{keys[0]}")
            continue
        panel._label_cell(label)
        pair = keys[0].endswith("_from")
        turn = pair and keys[-1].endswith("_turn")      # the slice's turn, small, at the end
        ends = 2 if pair else len(keys)
        gap = imgui.calc_text_size(ARROW).x + 2 * sp if pair else sp
        room = imgui.get_content_region_avail().x - (TURN_W + sp if turn else 0.0)
        w = (room - gap * (ends - 1)) / ends
        for i, k in enumerate(keys):
            if i and pair and i < 2:
                # a slice's two ends: from → to (plan 30 N8)
                imgui.same_line()
                imgui.text_disabled(ARROW)
                imgui.same_line()
            elif i:
                imgui.same_line()
            panel._slider(f"{pre}.{k}", TURN_W if turn and i == 2 else w)
            drawn(f"{pre}.{k}")
        if pair and _is_palette(sel) and keys[0] == "hue_from":
            _hue_bar(fx.values[sel])
    if idle is not None:
        _dim(top, imgui.ImVec2(right, imgui.get_cursor_screen_pos().y))
        _relearn_frame(panel, rects)


# plan 24 C6: an effect with many params would scroll the page, so the rows
# are packed by a convention in the uniform names: consecutive params that
# share a stem and end _lo/_hi, or _hue/_sat/_val, share one row (sat_lo +
# sat_hi -> "sat"; a1_hue + a1_sat + a1_val -> "a1"). Every param is still
# declared and routable; this only decides what the strip draws
# plan 30 N8: and _from/_to — a slice's two ends, drawn `from → to`
# (and a slice's `_turn` after them on the same row)
ROW_SUFFIXES = (("_lo", "_hi"), ("_from", "_to", "_turn"), ("_from", "_to"),
                ("_hue", "_sat", "_val"))
ARROW = "→"
TURN_W = 64         # px: the hue row's turn slider, after from → to
# and the palette shows one mode's rows at a time: effect -> mode -> key prefixes hidden
HIDDEN_BY_MODE = {
    "palette": {0: ("anchors", "a1_", "a2_", "a3_", "a4_"),
                1: ("hue_", "sat_", "val_")},
}
HUE_BAR_H = 4.0     # px: the hue row's bar of the slice's colours, under its sliders
HUE_BAR_STEPS = 32  # the bar's segments


def _is_palette(name: str) -> bool:
    return name.partition(".")[0] == "palette"


def compress_line(v: dict) -> str:
    """The palette's compress mode in the owner's words (plan 30 N8):
    `compress into: hue 170° → 230° · sat 0.00 → 1.00 · val 0.00 → 1.00`."""
    turn = float(v.get("hue_turn", 0.0))
    return (f"compress into: hue {v.get('hue_from', 0.0):.0f}° → {v.get('hue_to', 360.0):.0f}°"
            + (f" turned {turn:.0f}°" if turn else "")
            + f" · sat {v.get('sat_from', 0.0):.2f} → {v.get('sat_to', 1.0):.2f}"
            f" · val {v.get('val_from', 0.0):.2f} → {v.get('val_to', 1.0):.2f}")


def slice_arc(hue_from: float, hue_to: float) -> float:
    """The hue slice's arc, degrees, as palette.glsl reads it: from up the
    wheel to to, through 360 when to < from."""
    return hue_to - hue_from if hue_to >= hue_from else hue_to + 360.0 - hue_from


def _hue_bar(v: dict) -> None:
    """A thin bar under the hue row: the colours of the slice, from → to."""
    import colorsys
    lo = float(v.get("hue_from", 0.0))
    arc = slice_arc(lo, float(v.get("hue_to", 360.0)))
    lo += float(v.get("hue_turn", 0.0))       # the slice as turned
    pos = imgui.get_cursor_screen_pos()
    x0 = pos.x + ui.LABEL_W
    width = max(imgui.get_content_region_avail().x - ui.LABEL_W, 1.0)
    dl = imgui.get_window_draw_list()
    seg = width / HUE_BAR_STEPS
    for i in range(HUE_BAR_STEPS):
        h = ((lo + arc * (i + 0.5) / HUE_BAR_STEPS) % 360.0) / 360.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        dl.add_rect_filled(imgui.ImVec2(x0 + i * seg, pos.y),
                           imgui.ImVec2(x0 + (i + 1) * seg, pos.y + HUE_BAR_H),
                           imgui.get_color_u32(imgui.ImVec4(r, g, b, 1.0)))
    imgui.dummy(imgui.ImVec2(1.0, HUE_BAR_H))


def strip_rows(name: str, keys: list[str], mode: int = 0) -> list[tuple[str, list[str]]]:
    """The open strip's param rows: (label, [param keys on the row])."""
    # an instance (`palette.2`, plan 26 A4) hides as its file does
    hide = HIDDEN_BY_MODE.get(name.partition(".")[0], {}).get(1 if mode else 0, ())
    keys = [k for k in keys if not k.startswith(hide)]
    rows: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(keys):
        for group in ROW_SUFFIXES:
            stem = keys[i][: -len(group[0])] if keys[i].endswith(group[0]) else None
            if stem is not None and keys[i:i + len(group)] == [stem + g for g in group]:
                rows.append((stem.replace("_", " "), keys[i:i + len(group)]))
                i += len(group)
                break
        else:
            rows.append((keys[i].replace("_", " "), [keys[i]]))
            i += 1
    return rows


def _strip_header(panel, fx, name: str, place: str | None = None) -> None:
    """The open strip's title; its note the file name and where the
    effect's paths end (`place`, the page's groups). Plan 33 U: no ONTO
    chips and no order — where an effect runs is its wires, edited on GRAPH."""
    spec = fx.specs[name]
    note = f"{spec.name}.glsl" + (f" · {place}" if place else "")
    panel._section(spec.label.lower(), note=note)


def _faint(text: str) -> None:
    """A wrapped line in the quietest text colour."""
    imgui.push_style_color(imgui.Col_.text, ui.FAINT)
    imgui.text_wrapped(text)
    imgui.pop_style_color()


def _chip_baseline() -> None:
    """Put the next text on the baseline of a chip beside it: a chip is a
    frame with CHIP_PAD."""
    imgui.push_style_var(imgui.StyleVar_.frame_padding, ui.CHIP_PAD)
    imgui.align_text_to_frame_padding()
    imgui.pop_style_var()


def why_idle(fx, name: str, faces_on: bool = True, reached: bool = True) -> str | None:
    """Why `name` is not running, first reason only; None while it runs.
    "off" | "reaches nothing" | "faces off" | "bypassed" | "fx mix 0" | "mix 0".

    With the two flags left True it is None exactly when `FxState.live`
    says the effect draws. Plan 33 T7: where it is wired is the caller's to
    say — `reached` False for an effect whose paths reach nothing (it never
    runs), `faces_on` False for one that ends only on the faces while
    `view.faces` is off (the faces draw nothing)."""
    v = fx.values[name]
    if not v["on"]:
        return "off"
    if not reached:
        return UNREACHED
    if not faces_on:
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


def _state(panel):
    """The live FxState — the renderer's; None headless."""
    chain = getattr(panel.renderer, "fx", None)
    return None if chain is None else chain.state


def _error(chain, fx, name: str) -> str:
    if chain is not None:
        return chain.error(name)
    return fx.errors.get(name, "")
