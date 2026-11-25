"""The Gallery: every component in the kit, on one scrolling page.

Why this exists, when `gallery.py` already does:

* `gallery.py` is the **pixel diff**. It draws a fixed set of cells pinned to
  `spec.json` so the ImGui side and the React side can be subtracted. It is a
  measuring instrument, it is not interactive, and it only holds the cells
  somebody has written a spec rect for.
* this is the **contact sheet**. It is a tab of the live dashboard, it draws
  the real interactive widgets, and the rule for it is simply: if the kit has
  it, it is on this page in every state it can be in.

The two find different things, which is the whole argument for having both.
The diff proves chrome to a pixel and cannot see that a control is
unclickable; the contact sheet shows how a disabled Select feels under the
pointer and cannot tell you its border is a level off. Three real bugs — a
slider drawing its format string across its own track, per-widget state
thrown away before it could be read, input text invisible on the light theme
— were invisible to the diff by construction and obvious here.

Layout is `box.Node`, measured then placed, exactly as `dashboard.lay_out`
does it: nothing on this page carries a typed height, so adding a specimen
to a section makes the section grow rather than making the specimen land
outside it.
"""

from __future__ import annotations

from imgui_bundle import imgui

from hyperspace.dkit import box as B
from hyperspace.dkit import comp_button as CB
from hyperspace.dkit import comp_combobox as CC
from hyperspace.dkit import comp_context_menu as CX
from hyperspace.dkit import draw as D
from hyperspace.dkit import icons as IC
from hyperspace.dkit import interact as I
from hyperspace.dkit import menu as M
from hyperspace.dkit import tokens as T

# ---- the page's own rhythm, on the spacing scale -------------------------
PAD = T.CARD_PAD            # 16, a Card's own padding
GAP = T.SPACE[4]            # 16 between sections
COL_GAP = T.SPACE[3]        # 12 between specimens in a row
ROW_GAP = T.SPACE[5]        # 20 between rows of specimens
CAP_H = 16.0                # a specimen's caption line box
CAP_GAP = T.SPACE[1.5]      # caption baseline box -> the specimen
CAP_FONT = 12.0

# A specimen is (caption, size, draw), where `size` is (w, h) and `draw` is
# `fn(ui, key, x, y, w, h, state)`. Nothing here draws at layout time and
# nothing measures at paint time.


def _cap(ui, x, y, text):
    D.label(ui.dl, x, y, text, ui.faces, "regular", CAP_FONT,
            T.rgba("muted-foreground", theme=ui.theme), baseline_box=CAP_H)


# --------------------------------------------------------------------------
# the sections
# --------------------------------------------------------------------------
# Each one is `fn(faces, theme_name) -> (title, blurb, [[specimen, ...], ...])`
# — a list of ROWS of specimens, so a section decides its own grouping and
# the flow only has to wrap what does not fit.


def _s_button(faces, tn):
    rows = []
    variants = ("default", "secondary", "outline", "ghost", "destructive",
                "link")
    row = []
    for v in variants:
        w, h = CB.button_size("default", v.title(), faces)
        row.append((v, (w, h),
                    lambda ui, k, x, y, w, h, st, v=v:
                    CB.ui_button(ui, k, x, y, w, h, v.title(), variant=v)))
    rows.append(row)

    row = []
    for z in ("xs", "sm", "default", "lg"):
        w, h = CB.button_size(z, z.title(), faces)
        row.append((z, (w, h),
                    lambda ui, k, x, y, w, h, st, z=z:
                    CB.ui_button(ui, k, x, y, w, h, z.title(),
                                 variant="outline", size=z)))
    for z in ("icon-xs", "icon-sm", "icon", "icon-lg"):
        w, h = CB.button_size(z, "", faces, icon=True)
        row.append((z, (w, h),
                    lambda ui, k, x, y, w, h, st, z=z:
                    CB.ui_button(ui, k, x, y, w, h, "", variant="outline",
                                 size=z, icon="check")))
    rows.append(row)

    row = []
    for cap, kw in (("disabled", {"disabled": True}),
                    ("icon start", {"icon": "plus"}),
                    ("icon end", {"icon": "plus", "icon_side": "inline-end"}),
                    ("popup trigger", {"haspopup": True})):
        lab = cap.title()
        w, h = CB.button_size("default", lab, faces,
                              icon=bool(kw.get("icon")))
        row.append((cap, (w, h),
                    lambda ui, k, x, y, w, h, st, lab=lab, kw=kw:
                    CB.ui_button(ui, k, x, y, w, h, lab, variant="outline",
                                 **kw)))
    rows.append(row)
    return ("Button",
            ("Six variants, eight sizes. The ring is keyboard-only: click one "
            "and nothing rings, Tab to it and it does."), rows)


def _s_button_group(faces, tn):
    h_items = ["One", "Two", "Three"]
    v_items = ["Top", "Bottom"]
    hw, hh = CB.group_size(h_items, faces)
    vw, vh = CB.group_size(v_items, faces, orientation="vertical")
    rows = [[
        ("horizontal", (hw, hh),
         lambda ui, k, x, y, w, h, st:
         CB.ui_button_group(ui, k, x, y, h_items)),
        ("vertical", (vw, vh),
         lambda ui, k, x, y, w, h, st:
         CB.ui_button_group(ui, k, x, y, v_items, orientation="vertical")),
        ("one disabled", (hw, hh),
         lambda ui, k, x, y, w, h, st:
         CB.ui_button_group(ui, k, x, y, h_items, disabled=(1,))),
    ]]
    return ("ButtonGroup",
            ("The seam is a single border, not two: inner corners square, "
            "outer ones rounded."), rows)


def _s_input(faces, tn):
    def mk(cap, key, init="", **kw):
        def draw(ui, k, x, y, w, h, st, key=key, init=init, kw=kw):
            _ch, out = I.text_input(ui, k, x, y, w,
                                    st.setdefault(key, init), h=h, **kw)
            st[key] = out
        return (cap, (200.0, 32.0), draw)
    rows = [[
        mk("placeholder", "g.in1", placeholder="Placeholder"),
        mk("value", "g.in2", init="600-cell"),
        mk("invalid", "g.in4", init="bad", invalid=True),
        mk("disabled", "g.in3", init="off", disabled=True),
    ]]
    return ("Input",
            ("A real imgui.input_text under the measured chrome, so the caret, "
            "selection and clipboard are ImGui's and the box is shadcn's."),
            rows)


def _s_select(faces, tn):
    OPTS = ["Alpha", "Beta", "Gamma", "Delta"]

    def mk(cap, key, size="default", **kw):
        hh = T.SELECT_SIZES[size][0]

        def draw(ui, k, x, y, w, h, st, key=key, size=size, kw=kw):
            # `interact.select` takes menu.Item, not bare strings - the row
            # needs its own id and its checked state. Handing it a list of
            # str raised `'str' object has no attribute 'kind'` the first
            # time anybody CLICKED one, which no test here did.
            cur = st.setdefault(key, OPTS[0])
            got, _o = I.select(
                ui, k, x, y, w, cur,
                [M.Item(id=o, label=o, checked=(o == cur)) for o in OPTS],
                size=size, **kw)
            if got:
                st[key] = got
        return (cap, (170.0, hh), draw)
    rows = [[mk("default", "g.sel1"), mk("sm", "g.sel2", size="sm"),
             mk("disabled", "g.sel3", disabled=True)]]
    return ("Select",
            ("73 of the registry's params are enums. The trigger has no hover "
            "tint in light and does have one in dark — measured, not guessed."),
            rows)


# A list long enough that the panel clamps and scrolls, which is the state
# worth showing: `max-height: 252px`, and no scrollbar at all.
COMBO_ITEMS = ["Tetrahedron", "Cube", "Octahedron", "Dodecahedron",
               "Icosahedron", "5-cell", "8-cell", "16-cell", "24-cell",
               "120-cell", "600-cell", "Grand antiprism",
               "Great dodecahedron", "Small stellated dodecahedron",
               "Great icosahedron", "Rhombicuboctahedron"]


def _s_combobox(faces, tn):
    def draw(ui, k, x, y, w, h, st):
        got, _o = CC.combobox(
            ui, k, x, y, w, st.setdefault("g.cb", COMBO_ITEMS[0]),
            [CC.Item(id=s, label=s) for s in COMBO_ITEMS],
            empty="No such shape.")
        if got is not None:
            st["g.cb"] = got

    def draw_off(ui, k, x, y, w, h, st):
        CC.combobox(ui, k, x, y, w, "Disabled",
                    [CC.Item(id=s, label=s) for s in COMBO_ITEMS],
                    disabled=True)
    rows = [[("sixteen items", (220.0, 32.0), draw),
             ("disabled", (220.0, 32.0), draw_off)]]
    return ("Combobox",
            ("The trigger IS the input — Base UI's shape, not Popover + "
            "Command. Sixteen rows clamp to 252px and scroll with no bar."),
            rows)


def _s_switch(faces, tn):
    def mk(cap, key, init=False, size="default", **kw):
        sw, sh = T.SWITCH_SIZES[size][0], T.SWITCH_SIZES[size][1]

        def draw(ui, k, x, y, w, h, st, key=key, init=init, size=size, kw=kw):
            _c, on = I.switch(ui, k, x, y, st.setdefault(key, init),
                              size=size, **kw)
            st[key] = on
        return (cap, (sw, sh), draw)
    rows = [[mk("off", "g.sw1"), mk("on", "g.sw2", init=True),
             mk("sm off", "g.sw3", size="sm"),
             mk("sm on", "g.sw5", init=True, size="sm"),
             mk("disabled", "g.sw4", init=True, disabled=True)]]
    return ("Switch",
            ("18.390625 px tall, because the class says h-[18.4px] and "
            "Chromium lays out on a 1/64 px grid."), rows)


def _s_checkbox(faces, tn):
    def mk(cap, key, init=False, label=None, **kw):
        size = I.checkbox_size(label, faces)

        def draw(ui, k, x, y, w, h, st, key=key, init=init, label=label,
                 kw=kw):
            _c, on = I.checkbox(ui, k, x, y, st.setdefault(key, init),
                                label=label, **kw)
            st[key] = on
        return (cap, size, draw)
    rows = [[mk("off", "g.cb1"), mk("on", "g.cb2", init=True),
             mk("disabled", "g.cb3", disabled=True),
             mk("disabled on", "g.cb4", init=True, disabled=True),
             mk("with label", "g.cb5", init=True, label="Bypass when idle"),
             mk("label, disabled", "g.cb6", label="Locked", disabled=True)]]
    return ("Checkbox",
            ("Space toggles and Enter does not; the click target reaches 11px "
            "past each side, and a click on the label toggles the box."),
            rows)


def _s_kbd(faces, tn):
    tbl = T.kbd_table(tn)

    def key(cap, s):
        def draw(ui, k, x, y, w, h, st, s=s):
            D.kbd(ui.dl, x, y, s, ui.faces, ui.theme, tbl)
        return (cap, D.kbd_size(s, faces, tbl), draw)

    def group(cap, keys, sep=None):
        def draw(ui, k, x, y, w, h, st, keys=keys, sep=sep):
            D.kbd_group(ui.dl, x, y, keys, ui.faces, ui.theme, tbl, sep=sep)
        return (cap, D.kbd_group_size(keys, faces, tbl, sep=sep), draw)

    def in_tip(ui, k, x, y, w, h, st):
        # on the tooltip's own ground, which is what the restyle is for
        D.fill(ui.dl, x, y, w, h, T.rgba("foreground", theme=ui.theme),
               T.RADII["md"])
        D.kbd(ui.dl, x + T.SPACE[1.5], y + T.SPACE[1.5], "S", ui.faces,
              ui.theme, tbl, in_tooltip=True)
    tip_w = D.kbd_size("S", faces, tbl)[0] + 2 * T.SPACE[1.5]
    rows = [[key("letter", "K"), key("word", "Ctrl"), key("symbol", "\u2318"),
             group("group", ["Ctrl", "B"], sep="+"),
             group("chord", ["\u2318", "\u21e7", "P"]),
             ("in a tooltip", (tip_w, tbl["h"] + 2 * T.SPACE[1.5]), in_tip)]]
    return ("Kbd",
            ("min-w-5 or text + 8, whichever is wider. A KbdGroup's \"+\" is "
            "MONOSPACE in the browser: the group is a <kbd> and never resets "
            "the UA font."), rows)


def _s_slider(faces, tn):
    def mk(cap, key, init, **kw):
        def draw(ui, k, x, y, w, h, st, key=key, init=init, kw=kw):
            _c, v = I.slider(ui, k, x, y, w, h, st.setdefault(key, init),
                             0.0, 1.0, **kw)
            st[key] = v
        return (cap, (200.0, 20.0), draw)

    def rng(ui, k, x, y, w, h, st):
        _c, lo, hi = I.range_slider(ui, k, x, y, w, h,
                                    st.setdefault("g.rlo", 0.3),
                                    st.setdefault("g.rhi", 0.7), 0.0, 1.0)
        st["g.rlo"], st["g.rhi"] = lo, hi
    rows = [[mk("continuous", "g.sl1", 0.25),
             mk("detents", "g.sl2", 0.5, detents=(0.25, 0.5, 0.75)),
             ("range", (200.0, 20.0), rng),
             mk("disabled", "g.sl3", 0.4, disabled=True)]]
    return ("Slider",
            ("292 of the registry's 427 params are continuous. The range and "
            "the thumb use different mappings and agree only at 50%."), rows)


def _s_tooltip(faces, tn):
    def draw(ui, k, x, y, w, h, st):
        hit = CB.ui_button(ui, k, x, y, w, h, "Hover me", variant="outline")
        I.tooltip(ui, k, (x, y, w, h), "Cutoff frequency",
                  hovered=hit.hot > 0.0)
    w, h = CB.button_size("default", "Hover me", faces)
    return ("Tooltip",
            ("700ms to open, measured; the panel reserves the arrow's full "
            "10px while the arrow only paints 5.071 of it."),
            [[("after 700ms", (w, h), draw)]])


def _s_menu(faces, tn):
    ITEMS = [M.heading("Shape"),
             M.Item(id="open", label="Open", icon="eye", shortcut="\u2318O"),
             M.Item(id="dup", label="Duplicate", icon="copy"),
             M.sep(),
             M.Item(id="lock", label="Lock", icon="lock", checked=False),
             M.sep(),
             M.Item(id="del", label="Delete", icon="x",
                    variant="destructive")]

    def kebab(ui, k, x, y, w, h, st):
        if I.icon_button(ui, k, x, y, w, "ellipsis").clicked:
            imgui.open_popup(f"##{k}.menu")
        M.popup(ui, f"##{k}.menu", ITEMS, anchor=B.Rect(x, y, w, h))

    def ctx(ui, k, x, y, w, h, st):
        D.box(ui.dl, x, y, w, h, border_col=T.rgba("border", theme=ui.theme),
              radius=T.RADII["lg"])
        D.label(ui.dl, x, y, "right-click here", ui.faces, "regular", 12,
                T.rgba("muted-foreground", theme=ui.theme),
                align="center", box_w=w, baseline_box=h)
        CX.context_menu(ui, f"{k}.ctx", B.Rect(x, y, w, h), ITEMS)

    rows = [[("dropdown", (28.0, 28.0), kebab),
             ("context menu", (200.0, 56.0), ctx)]]
    return ("Menu, ContextMenu",
            ("One panel, two ways in. Hover changes the INK as well as the "
            "ground, and a destructive row tints at 10% in light / 20% in "
            "dark."), rows)


def _s_scroll(faces, tn):
    def draw(ui, k, x, y, w, h, st):
        n, rh = 14, 24.0
        # this specimen draws a 1px border, so the scrollbar is inset by it
        # the way the browser's is - the bar belongs to the VIEWPORT
        with I.scroll_area(ui, k, x, y, w, h, n * rh, radius=T.RADII["lg"],
                           backdrop=T.rgba("card", theme=ui.theme),
                           pad=T.SPACE[2], border=1.0) as view:
            for i in range(n):
                D.label(ui.dl, view.x, view.y + i * rh, f"Row {i + 1}",
                        ui.faces, "regular", 13,
                        T.rgba("foreground", theme=ui.theme),
                        baseline_box=rh)
        D.box(ui.dl, x, y, w, h,
              border_col=T.rgba("border", theme=ui.theme),
              radius=T.RADII["lg"])
    return ("ScrollArea",
            ("The bar floats over the content rather than taking a column of "
            "it, and the corners are painted back because ImGui clips to "
            "rectangles."), [[("overlay bar", (200.0, 120.0), draw)]])


def _s_icons(faces, tn):
    names = sorted(IC.ICONS)
    rows, row = [], []
    for n in names:
        row.append((n, (28.0, 28.0),
                    lambda ui, k, x, y, w, h, st, n=n:
                    D.icon(ui.dl, n, x + 6, y + 6, 16.0,
                           T.rgba("foreground", theme=ui.theme))))
    rows.append(row)
    return ("Icons",
            (f"{len(names)} Lucide glyphs as vector paths — crisp at any size, "
            "coloured by token, no atlas."), rows)


def _s_type(faces, tn):
    SAMPLES = [("regular 14", "regular", 14.0), ("medium 14", "medium", 14.0),
               ("semibold 14", "semibold", 14.0),
               ("regular 12", "regular", 12.0),
               ("semibold 30", "semibold", 30.0),
               ("tabular 14", "regular", 14.0)]
    rows, row = [], []
    for cap, var, size in SAMPLES:
        txt = "1.36 0.50 2.08" if "tabular" in cap else "Polytope 1.36"
        w = D.text_w(txt, faces, var, size) + 4.0
        row.append((cap, (w, max(size + 8.0, 22.0)),
                    lambda ui, k, x, y, w, h, st, txt=txt, var=var,
                    size=size, cap=cap:
                    D.label(ui.dl, x, y, txt, ui.faces, var, size,
                            T.rgba("foreground", theme=ui.theme),
                            baseline_box=h, tabular=("tabular" in cap))))
    rows.append(row)
    return ("Type",
            ("Six Inter faces cut from the variable woff2 — three weights, "
            "each with and without tabular figures."),
            rows)


SWATCHES = ["background", "foreground", "card", "popover", "primary",
            "secondary", "muted", "muted-foreground", "accent", "destructive",
            "border", "input", "ring", "sidebar"]


def _s_tokens(faces, tn):
    row = []
    for name in SWATCHES:
        row.append((name, (64.0, 40.0),
                    lambda ui, k, x, y, w, h, st, name=name:
                    (D.fill(ui.dl, x, y, w, h,
                            T.rgba(name, theme=ui.theme), T.RADII["md"]),
                     D.box(ui.dl, x, y, w, h,
                           border_col=T.rgba("border", theme=ui.theme),
                           radius=T.RADII["md"]))))
    return ("Colour tokens",
            ("One swap between light and dark; every component reads these "
            "and nothing holds a literal."), [row])


SECTIONS = (_s_button, _s_button_group, _s_input, _s_select, _s_combobox,
            _s_switch, _s_checkbox, _s_kbd, _s_slider, _s_tooltip, _s_menu, _s_scroll,
            _s_icons, _s_type, _s_tokens)


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------
def plan(w: float, faces, theme_name: str, *, measure=None) -> tuple:
    """Where everything goes, at a content width of `w`.

    Returns `(height, [(title, blurb, card_h, [(caption, x, y, w, h, draw)])])`
    with every position relative to (0, 0), so the caller adds its own
    origin. Measured bottom-up the way `box.wants` does it — a section's
    card is as tall as the rows that wrapped into it, and nothing here is a
    typed height.

    `measure(text, variant, size) -> width` is injectable, exactly as
    `comp_combobox.combobox_size` takes one, so the layout can be tested
    with no GL and no display. Everything in here that needs a renderer
    needs it only for a text width.
    """
    mw = measure or (lambda t, v, size: D.text_w(t, faces, v, size))
    out, y = [], 0.0
    inner = w - 2 * PAD
    for build in SECTIONS:
        title, blurb, rows = build(faces, theme_name)
        placed, cy = [], 0.0
        for row in rows:
            # wrap: a row is a flow, and a specimen that does not fit starts
            # the next line. This is `flex-wrap`, which the layout tree does
            # not model, so it is done here rather than pretended elsewhere.
            cx, line_h = 0.0, 0.0
            for cap, (sw, sh), draw in row:
                # a specimen's CELL is as wide as the wider of the specimen
                # and its caption. Without this the captions of narrow
                # specimens overlap each other - "icon-xs icon-sm icon" ran
                # together under three 24px buttons, and the icon sheet was
                # unreadable.
                cw_ = max(sw, mw(cap, "regular", CAP_FONT))
                if cx > 0.0 and cx + cw_ > inner:
                    cx, cy, line_h = 0.0, cy + line_h + ROW_GAP, 0.0
                placed.append((cap, cx, cy, sw, sh, draw))
                cx += cw_ + COL_GAP
                line_h = max(line_h, CAP_H + CAP_GAP + sh)
            cy += line_h + ROW_GAP
        body_h = max(cy - ROW_GAP, 0.0)
        head = (T.CARD_TITLE_H + T.CARD_TITLE_GAP + T.CARD_DESC_H
                + T.CARD_HEAD_GAP)
        card_h = PAD + head + body_h + PAD
        out.append((title, blurb, card_h, placed))
        y += card_h + GAP
    return max(y - GAP, 0.0), out


def paint(ui, x: float, y: float, w: float, state: dict, pre=None) -> float:
    """Draw the contact sheet at (x, y) with content width `w`.

    Returns the height drawn, which is the same number `plan` gave — they
    are the same call, so the page's scroll range and what is on screen can
    never disagree.
    """
    # `pre` is the plan the CALLER already made. The page's scroll range
    # has to be known before the scroll area opens, and the height comes out
    # of the same call that places the specimens - so the caller plans once
    # and hands it back rather than the two halves planning separately and
    # being allowed to disagree.
    total, sections = pre if pre is not None else plan(w, ui.faces,
                                                       ui.theme_name)
    theme = ui.theme
    for i, (title, blurb, card_h, placed) in enumerate(sections):
        D.card(ui.dl, {"x": x, "y": y, "w": w, "h": card_h,
                       "variant": "plain"}, theme,
               ui.grad_tex)
        D.label(ui.dl, x + PAD, y + PAD, title, ui.faces, "semibold", 16,
                T.rgba("foreground", theme=theme),
                baseline_box=T.CARD_TITLE_H)
        D.label(ui.dl, x + PAD, y + PAD + T.CARD_TITLE_H + T.CARD_TITLE_GAP,
                blurb, ui.faces, "regular", 13,
                T.rgba("muted-foreground", theme=theme),
                baseline_box=T.CARD_DESC_H, max_w=w - 2 * PAD)
        by = (y + PAD + T.CARD_TITLE_H + T.CARD_TITLE_GAP + T.CARD_DESC_H
              + T.CARD_HEAD_GAP)
        for j, (cap, sx, sy, sw, sh, draw) in enumerate(placed):
            _cap(ui, x + PAD + sx, by + sy, cap)
            draw(ui, f"gal.{i}.{j}", x + PAD + sx,
                 by + sy + CAP_H + CAP_GAP, sw, sh, state)
        y += card_h + GAP
    return total
