"""The Combobox's measured table: `COMBOBOX`, its dark overrides, and the resolver.

Pure data, read off the real `combobox.tsx` on `?probe`. Moved out of
`comp_combobox.py` by `HANDOFF.md` item 3c; `comp_combobox` re-exports all
three names, so `C.COMBOBOX` and `C.combobox_table(...)` are unchanged.
"""

from __future__ import annotations

from . import tokens as T

# --------------------------------------------------------------------------
# the measured table
# --------------------------------------------------------------------------
#
# (token, alpha) pairs multiply, exactly as tokens.rgba() does, so
# ("input", 0.3) is Tailwind's `bg-input/30` over a dark `input` that is
# itself #ffffff26. Lengths are CSS px at dpr 1.

COMBOBOX = {
    # ---- trigger: an INPUT. You type INTO it. ---------------------------
    # Re-measured against the real `combobox.tsx`, which is Base UI and
    # whose `ComboboxInput` IS the trigger - an InputGroup wrapping a real
    # <input> with a ghost chevron in an inline-end addon. The kit first
    # shipped the OLD Popover+Command recipe, a Button that opens a panel
    # with a search box inside it, because I told the agent that building it
    # that `shadcn has no combobox component`. It does.
    #
    # Measured: 320x32, radius 10, border 1px `input`, bg transparent in
    # light and `input/30` in dark - which is exactly tokens.INPUT - with
    # padding-left 10 and padding-RIGHT 6 (the chevron's addon takes the
    # rest). Font 14/20.
    "input_pad_l": T.SPACE[2.5],          # pl-2.5 = 10
    "input_pad_r": T.SPACE[1.5],          # pr-1.5 = 6, then the addon
    "side_offset": T.SPACE[1.5],          # sideOffset 6, not the Select's 4
    # the panel's rows are MENU rows: h 28, rounded-md, px 6, gap 8 - all
    # three measured equal to menu.py's, so they are not restated here
    # Measured on `[data-slot="combobox-item"]`, which is NOT menu.py's row
    # and NOT the old Command recipe's: h 28, `rounded-md` 8, and padding
    # `4px 32px 4px 6px` — six on the left and THIRTY-TWO on the right. The
    # right pad is what keeps the label clear of the ItemIndicator, which is
    # a 16px span whose right edge sits 8px from the row's (`absolute
    # right-2`, `size-4`). The kit drew both sides at 8, so the check
    # crowded the row's edge and long labels ran under it.
    "row_h": 28.0,
    "row_radius": "md",                   # 8, not the Command recipe's 6
    "row_pad_x": T.SPACE[1.5],            # pl-1.5 = 6
    "row_pad_r": T.SPACE[8],              # pr-8 = 32
    "row_gap": T.SPACE[2],
    "check_gap": T.SPACE[2],              # the indicator's `right-2` = 8
    "list_pad": T.SPACE[1],               # p-1
    # `max-h-[min(calc(--spacing(72)---spacing(9)), ...)]` = 288 - 36 = 252,
    # and MEASURED on the LIST, whose box includes its own `p-1`: the
    # 16-row `combobox.tight` block reports the list AND the content at
    # 319x252, with `scrollHeight` 456. So 252 is the padded list's height
    # - the PANEL's - not the rows' box. The kit clamped the rows at 252
    # and then added the 4px rails, which made a clamped panel 260.
    "list_max_h": 252.0,                  # the PANEL's clamp, rails included
    # ---- the old recipe's trigger, kept for reference --------------------
    # Its (height, radius key) is T.SELECT_SIZES, NOT a second table: the
    # Button and the SelectTrigger measured identical there (32, rounded-lg
    # = 10). Only `default` is measured; `sm` is the Select's, borrowed.
    "trigger_pad_x": T.SPACE[2.5],        # px-2.5 = 10, BOTH sides
    "trigger_font": 14.0,                 # text-sm
    "trigger_weight": "medium",           # font-medium = 500  (Select: 400)
    "trigger_gap": T.SPACE[1.5],          # gap-1.5 = 6
    "trigger_bg": ("background", 1.0),    # light bg-background, opaque white
    "trigger_hover": ("muted", 1.0),      # light DOES tint; a Select's does not
    # `aria-expanded:bg-muted`: in LIGHT the trigger is tinted the whole
    # time its panel is open, hovered or not. In dark it is not — measured,
    # `dark:bg-input/30` wins and the open trigger is byte-identical to the
    # closed one. An asymmetry no reading of the class list produces.
    "trigger_open": ("muted", 1.0),
    # `border-border` in light and `dark:border-input` in dark. The two
    # tokens are the SAME #e5e5e5 in light, so the measurement cannot tell
    # them apart there; in dark it can, and says input: measured
    # `oklch(1 0 0 / 0.15)` is #ffffff26 (input), not #ffffff1a (border).
    "trigger_border": ("border", 1.0),
    # MEASURED, under a real keyboard focus on the probe's PopoverTrigger:
    # `box-shadow: ring/50 0 0 0 3px`, the same band every other control in
    # the kit gives. What a mouse-opened trigger has is still nothing - that
    # measurement stands, it is `:focus-visible` and a pointer does not match
    # it - so the open state is the FILL above and the ring is the keyboard's.
    "trigger_ring": ("ring", 0.5),
    # The second half of the answer, and here it is THEMED. This trigger is a
    # Button variant="outline", so it inherits that variant's one dark
    # anomaly: measured focused, light swaps the border to `ring`
    # (oklch(0.708 0 0)) and dark keeps `input` (oklch(1 0 0 / 0.15)),
    # because `dark:border-input` sorts after `focus-visible:border-ring` in
    # Tailwind's output. comp_button.BUTTON_DARK["outline"] records the same
    # finding on the same component; this is it measured again on this one.
    "trigger_focus_border": ("ring", 1.0),
    # DERIVED, not measured — the probe's trigger carries no icon. The
    # recipe's is `<ChevronsUpDownIcon className="opacity-50"/>`, 16px by
    # `[&_svg:not([class*='size-'])]:size-4`, and `justify-between` puts its
    # right edge on the content box's, i.e. border 1 + pr 10 in. The glyph
    # `chevrons-up-down` is not in the generated table (icons.py has 38 and
    # that is not one), so `chevron-down` stands in — what select_trigger
    # draws.
    "chevron": 16.0,
    "chevron_icon": "chevron-down",
    "chevron_ink": ("foreground", 0.5),   # opacity-50 over currentColor

    # ---- panel: PopoverContent (p-0) + Command (p-1) --------------------
    "pad": T.SPACE[1],                    # 4 — the Command's p-1
    "radius": "lg",                       # 10, the same as menu.py's panel
    "bg": ("popover", 1.0),               # as menu.py
    "ring": ("foreground", 0.10),         # ring-1 ring-foreground/10, as menu.py
    # superseded: the real component declares sideOffset 6. Kept only as a
    # record of what the OLD Popover+Command recipe used.
    "_old_recipe_side_offset": T.SPACE[1],
    # `combobox.tsx` declares `align="start"`, not `popover.tsx`'s
    # `center` - which is what this used to say, from the old recipe.
    # Measured, the two are indistinguishable here: the panel and the
    # trigger are the same width. Base UI anchors the positioner to the
    # inner `<input>`, not to the InputGroup, so the real panel is
    # `--anchor-width` (291 of a 320 trigger) plus `--spacing(7)` = 319,
    # at the input's x - i.e. one pixel right of the trigger's left edge
    # with its right edge exactly on the trigger's. The kit draws the
    # panel at the trigger's own (x, w); that is a 1px difference on the
    # left and none on the right, and it is left alone deliberately,
    # because the panel's edge lining up with the field's is what the
    # arrangement looks like it means.
    "align": "center",                    # == "start" at equal widths
    "fade": 0.10,                         # animation: enter 0.1s, as menu.py

    # ---- CommandInput ---------------------------------------------------
    "field_h": 32.0,                      # h-8!
    "field_radius": "lg",                 # rounded-lg! = 10
    "field_pad": T.SPACE[1],              # the wrapper's p-1 pb-0
    "field_bg": ("input", 0.3),           # bg-input/30 in BOTH themes
    "field_border": ("input", 0.3),       # border-input/30 in BOTH themes
    "field_icon": 16.0,                   # size-4
    # The chevron's RIGHT edge, in from the trigger's right. MEASURED on the
    # real component at two widths (200 and 320) and constant at both, which
    # is why it is a number here and not an arithmetic model: the addon it
    # lives in is 32x36 overhanging the 32px field by 2 top and bottom and
    # 3.797 to the right, and reproducing that box to get at its content is
    # modelling the browser's layout rather than its paint.
    #
    # It replaces `field_icon_x` (9.0 = "border 1 + the addon's pl-2"), which
    # described a LEADING magnifier in a search field this component has not
    # had since the Popover+Command recipe was replaced - residue of the same
    # shape as the 36px `combobox_size` used to reserve for it. Nothing read
    # it but a test asserting it equalled its own derivation.
    "field_chevron_right": 8.203,
    # ENABLED, the chevron is muted-foreground at FULL strength: measured
    # oklch(0.556 0 0) on the svg at `opacity: 1` (#737373, level 115). The
    # kit drew it at 0.5 and came out at 185 - 70 levels, the biggest miss
    # the Combobox cell found on its first run.
    "field_icon_ink": ("muted-foreground", 1.0),
    # DISABLED, it is dimmed TWICE, and that is why the old code looked
    # right. `has-disabled:opacity-50` on the input GROUP dims the box, the
    # placeholder and the chevron alike - but the chevron also sits in a
    # BUTTON inside the trailing addon which carries a disabled:opacity-50 of
    # its own. Measured: group 0.5, addon 1, that button 0.5, svg 1, and the
    # chevron bottoms out at 217 against a 249 fill, which is 0.25 of full
    # ink and not the 0.5 one factor gives.
    #
    # The previous code wrote `0.5 * dim` with dim itself 0.5 when disabled:
    # 0.25 disabled, which is right, and 0.5 enabled, which is the bug. One
    # folded constant cannot be both, so the two facts are named separately.
    "field_icon_disabled_opacity": 0.5,
    "field_text_r": 1.0,                  # the input's right edge: the border
    "field_font": 14.0,                   # text-sm
    "field_line": 20.0,                   # line-height; centred in h-8 -> +6
    "field_ink": ("popover-foreground", 1.0),
    "field_placeholder": ("foreground", 0.5),   # Chromium's own, measured

    # ---- CommandList ----------------------------------------------------
    "_old_recipe_list_max_h": 288.0,      # max-h-72

    # ---- CommandGroup ---------------------------------------------------
    # The Base UI `ComboboxGroup` carries NO padding of its own — measured,
    # the first row's x is the content's x + 4, which is the LIST's `p-1`
    # and nothing else. The old Command recipe nested a p-1 group inside a
    # p-1 list, so every row was inset 8 and two rows' worth of width went
    # missing.
    "group_pad": 0.0,
    "head_h": 28.0,                       # py-1.5 on a 16px line box
    "head_pad_x": T.SPACE[2],             # px-2
    "head_font": 12.0,                    # text-xs
    # RE-MEASURED on `[data-slot="combobox-label"]`: `font-weight: 400`.
    # `ComboboxLabel` is `px-2 py-1.5 text-xs text-muted-foreground` and
    # carries no `font-medium` at all - that was `command.tsx`'s
    # CommandGroup heading, i.e. the old recipe's, and it survived the
    # rewrite the way the empty block's 68px did.
    "head_weight": "regular",             # measured 400, NOT medium
    "head_ink": ("muted-foreground", 1.0),

    # ---- CommandItem ----------------------------------------------------
    # The real component's rows are MENU rows: 28, not 32. `item_h` stays
    # the name the rest of this module and its tests use.
    "item_h": 28.0,                       # measured on combobox-item
    "item_pad_x": T.SPACE[2],             # px-2
    "item_radius": "sm",                  # rounded-sm = 6
    "item_gap": T.SPACE[2],               # gap-2
    "item_font": 14.0,                    # text-sm
    "item_ink": ("popover-foreground", 1.0),
    "item_sel_bg": ("muted", 1.0),        # data-selected:bg-muted
    "item_sel_ink": ("foreground", 1.0),  # the same value as popover-foreground
    # DERIVED from `data-[disabled=true]:opacity-50`; no disabled row exists
    # on the probe route.
    "item_disabled_opacity": 0.5,
    # Measured at 16x16, right-aligned inside the padding and vertically
    # centred, with `opacity: 0` — no probe row is checked, so the OPAQUE
    # colour is DERIVED: `<CheckIcon/>` at currentColor.
    "check": 16.0,
    "check_ink": ("popover-foreground", 1.0),
    # MEASURED on `[data-slot="combobox-separator"]` in the `combobox.grp`
    # probe block: `margin: 4px -4px`, height 1, and it spans the panel's
    # full 319 width - so it DOES carry `my-1`, four above and four below,
    # and the block it occupies is 9 tall. `combobox.tsx`'s separator is
    # `-mx-1 my-1 h-px bg-border`; `command.tsx`'s is `-mx-1 h-px bg-border`
    # with no margin, and the kit had recorded the Command one. Checked
    # against the layout: label 28 ends at 2782, row 28 ends at 2810,
    # separator at 2814, next row at 2819.
    "sep_h": 1.0,
    "sep_my": T.SPACE[1],                 # my-1 = 4, above AND below
    "sep_col": ("border", 1.0),

    # ---- ComboboxEmpty --------------------------------------------------
    # Re-measured on the real component with a query that matches nothing:
    # the whole panel is 319x36, the LIST collapses to zero height and zero
    # padding (`data-empty:p-0`), and the empty block is the panel - 36 tall
    # from `py-2` on a 20px line box, full width, centred, in
    # `muted-foreground` (oklch(0.556 0 0)).
    #
    # The old numbers - 68 tall from `py-6`, in popover-foreground, inside
    # the list's padding - were the Popover+Command recipe's, and they
    # survived the rewrite because nothing asked the empty panel its height.
    "empty_h": 36.0,                      # py-2 on a 20px line box
    "empty_font": 14.0,                   # text-sm
    "empty_ink": ("muted-foreground", 1.0),
}

# The only values that move with the theme, and all five are the trigger's.
# The first two are tokens.SELECT_DARK's two exactly, because a dark
# Button-outline and a dark SelectTrigger measure the same. Everything else
# in the table above is a token that swaps itself.
COMBOBOX_DARK = {
    "trigger_bg": ("input", 0.3),         # dark:bg-input/30
    "trigger_hover": ("input", 0.5),      # dark:hover:bg-input/50
    # measured: an OPEN dark trigger is byte-identical to a closed one
    "trigger_open": ("input", 0.3),
    "trigger_border": ("input", 1.0),     # dark:border-input
    # measured focused: the border does NOT move to `ring` in dark - see
    # `trigger_focus_border` above. The 3px band is unthemed and stays.
    "trigger_focus_border": ("input", 1.0),
}


def combobox_table(theme_name: str) -> dict:
    """COMBOBOX resolved for a theme, the shape tokens.select_table has."""
    t = dict(COMBOBOX)
    if theme_name == "dark":
        t.update(COMBOBOX_DARK)
    return t
