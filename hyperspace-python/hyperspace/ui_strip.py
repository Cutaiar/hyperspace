"""A group's patch strip on dkit (`ui_kit`): what `ui_loadable.strip` draws
where the kit is there — ◀ name ▶ as one joined group of the kit's outline
Buttons, the dirty dot inside the name's button, and the strip's actions
(new · save · as… · reset) flush right as the kit's Buttons: save solid in
the one red while there is something to write (the stock strip's lit
chip), the rest quiet.

Everything a strip does is still `ui_loadable`'s: the list a module name
opens (`_list_popup`, in the same id scope, under ``push_id("strip.<group>")``),
the save-as field that stands in for the strip while a name is typed
(`_name_field`), the save's words and hover (`save_label`, `save_tip`),
the library calls (`_guard`), the devices-missing chip under a loadable
strip (`ui_graph._wants_chip`). Each control's rect goes into the strip's
state as the stock one's does (``strip.<group>.<name|next|save|as|reset|new|dot>``,
`ui_loadable._rect`), so what reads them reads the kit's.

Narrow (the 240 px pane), the actions take a row of their own under
◀ name ▶, as the stock strip's chips do.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import loadable, ui, ui_fields, ui_kit, ui_loadable

ARROW = "icon-sm"        # ◀ ▶: 28 px squares, the panel's frame height


def strip(panel, group: str) -> None:
    L = ui_loadable
    lib = panel.library
    meta = getattr(panel, "meta", None) if group == L.LOADABLE else None
    imgui.push_id(f"strip.{group}")
    try:
        if L._name_field(panel, group, lambda n: L._save_as(panel, group, n)):
            return
        _draw(panel, group, lib, meta)
    finally:
        imgui.pop_id()


def _draw(panel, group: str, lib, meta) -> None:
    L, C, T = ui_loadable, ui_kit.mod("comp_button"), ui_kit.mod("tokens")
    st = L._state(panel)
    cur = lib.current(group)
    listing = L.names(panel, group)
    is_dirty = L.dirty(panel, group)
    kind = group in lib.kinds
    loaded_patch = getattr(lib, "loaded_patch", None) if group == L.LOADABLE else None
    unsaved = loaded_patch is not None and cur == loadable.UNTITLED_PATCH and (
        bool(getattr(loaded_patch, "unsaved", False)) or lib.path_of(group, cur) is None)
    actions = (["new"] if loaded_patch is not None else []) + ["save", "as"] + \
        ([] if kind else ["reset"])
    words = {"new": "new", "save": L.save_label(lib, group), "as": "as…", "reset": "reset"}

    k = ui_kit.begin(panel)
    gap = T.SPACE[1]
    rh = ui_fields.ROW_H
    aw = [ui_fields.button_w(k, words[a]) for a in actions]
    actions_w = sum(aw) + gap * (len(aw) - 1)
    x, y, w, _ = ui_kit.block(0.0)
    roomy = w - actions_w - T.SPACE[2] - 2 * rh >= L.NAME_MIN
    nav_w = min(w - actions_w - T.SPACE[2] if roomy else w, 2 * rh + L.name_w())
    h = rh if roomy else 2 * rh + T.SPACE[2]
    with ui_kit.mod("uictx").chrome(k):
        _nav(panel, k, group, cur, listing, is_dirty, meta, x, y, nav_w, rh)
        ax = x + w - actions_w if roomy else x
        ay = y if roomy else y + rh + T.SPACE[2]
        for a, bw in zip(actions, aw):
            _action(panel, k, group, a, words[a], cur, is_dirty, unsaved, loaded_patch,
                    (ax, ay, bw, rh))
            ax += bw + gap
    ui_kit.end_block((x, y, w, h))
    if group == L.LOADABLE:
        from . import ui_graph  # (late: ui_graph imports ui_routing, which imports ui_loadable)
        ui_graph._wants_chip(panel, beside=False)
    else:
        L._list_popup(panel, group, listing, cur)
    del st


def _nav(panel, k, group, cur, listing, is_dirty, meta, x, y, w, h) -> None:
    """◀ name ● ▶, one joined group; the arrows step by name order, a module
    strip's name opens its list. The dirty dot (plan 19 WP5: a 12 px disc
    between the name and ▶) is a segment of its own, there only while the
    group has moved off its patch."""
    L, C, T = ui_loadable, ui_kit.mod("comp_button"), ui_kit.mod("tokens")
    st = L._state(panel)
    dot_w = 2 * ui.DOT_R + 2 * T.SPACE[1] if is_dirty else 0.0
    rects = [(x, y, h, h), (x + h, y, w - 2 * h - dot_w, h)]
    if is_dirty:
        rects.append((x + w - h - dot_w, y, dot_w, h))
    rects.append((x + w - h, y, h, h))
    joins = C.button_group(rects, "horizontal")
    off = not listing
    # ◀
    s = C.ui_button(k, f"strip.{group}:prev", *rects[0], "", variant="outline", size=ARROW,
                    icon="chevron_left", join=joins[0], in_group=True, disabled=off)
    if s.clicked:
        L._guard(panel, panel.library.prev, group)
    # the name: cut to its button; "—" while nothing is loaded
    nx, ny, nw, nh = rects[1]
    label = L._elide(cur) if cur else "—"
    imgui.push_font(ui._FONTS["ui"], ui.FONT_BASE)
    label = ui.fit_text(label, nw - 2 * T.SPACE[2])
    imgui.pop_font()
    s = C.ui_button(k, f"strip.{group}:name", nx, ny, nw, nh, label, variant="outline",
                    size="sm", join=joins[1], in_group=True, disabled=off)
    L._rect(panel, f"strip.{group}.name")
    st.setdefault("names", {})[group] = label       # what the name says (the tests)
    if s.hovered:
        if cur is None:
            ui.tooltip(f"no patch loaded{L._on_deck(meta)}")
        elif group == L.LOADABLE:
            ui.tooltip(f"{cur}{L._on_deck(meta)}  ·  the loaded patch — the list below "
                       "loads onto this deck")
        else:
            ui.tooltip(f"{cur}  ·  click for the list")
    if s.clicked and group != L.LOADABLE:
        imgui.open_popup("list")
    st["rects"].pop(f"strip.{group}.dot", None)
    if is_dirty:
        dx, dy, dw, dh = rects[2]
        d = C.ui_button(k, f"strip.{group}:dot", dx, dy, dw, dh, "", variant="outline",
                        size="sm", join=joins[2], in_group=True)
        cx, cy, r = dx + dw / 2, dy + dh / 2, ui.DOT_R
        k.dl.add_circle_filled(imgui.ImVec2(cx, cy), r, ui.u32(ui.RED))
        st["rects"][f"strip.{group}.dot"] = (cx - r, cy - r, cx + r, cy + r)
        if d.hovered:
            ui.tooltip("edited since the patch loaded — save writes it")
    # ▶
    s = C.ui_button(k, f"strip.{group}:next", *rects[-1], "", variant="outline", size=ARROW,
                    icon="chevron_right", join=joins[-1], in_group=True, disabled=off)
    L._rect(panel, f"strip.{group}.next")
    if s.clicked:
        L._guard(panel, panel.library.next, group)


def _action(panel, k, group, what, words, cur, is_dirty, unsaved, loaded_patch, rect) -> None:
    L, C = ui_loadable, ui_kit.mod("comp_button")
    lib = panel.library
    x, y, w, h = rect
    if what == "save":
        lit = bool(is_dirty and cur is not None)
        s = C.ui_button(k, f"strip.{group}:save", x, y, w, h, words,
                        variant="default" if lit else "secondary", size=ui_fields.BUTTON_SIZE,
                        disabled=cur is None)
        L._rect(panel, f"strip.{group}.save")
        st = L._state(panel)
        st["save"][f"strip.{group}"] = (words, lit)
        if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
            ui.tooltip(L.save_tip(lib, group))
        if s.clicked:
            if unsaved:
                L._begin_naming(panel, group, "")      # unnamed: save acts as as…
            else:
                L._guard(panel, lib.overwrite, group)
                L.invalidate(panel, group)
        return
    s = C.ui_button(k, f"strip.{group}:{what}", x, y, w, h, words, variant="ghost",
                    size=ui_fields.BUTTON_SIZE)
    L._rect(panel, f"strip.{group}.{what}")
    if what == "new":
        if s.hovered:
            ui.tooltip("A new patch: default values, shape → scene → All outputs — "
                       "a shape on every window")
        if s.clicked:
            from . import ui_graph  # (late, as ui_loadable's)
            L._guard(panel, loaded_patch.new, ui_graph.in_view(panel))
            L.invalidate(panel, group)
    elif what == "as":
        if s.hovered:
            ui.tooltip("Save the settings as a new patch")
        if s.clicked:
            L._begin_naming(panel, group, "" if unsaved else (cur or ""))
    elif what == "reset":
        if s.hovered:
            d = lib.default_name(group)
            ui.tooltip(f"Back to the default patch — {d}" if d
                       else "Back to the values the module started with")
        if s.clicked:
            L._guard(panel, lib.reset, group)
