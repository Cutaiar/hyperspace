"""The GRAPH page (plan 28 N2, N3): both graphs on one canvas; the
modulation edited on it.

`page(panel, dt)` draws `graphview`'s model on one `imgui_node_editor`
canvas: the controllers, the analyzer, the LFOs, the modifiers and the
macros on the left, the params grouped under the render node that owns
them, the render graph's own image / geometry / mask cables, the
outputs last. Cables are coloured by what they carry (`COLOURS`); a value
cable's thickness follows its reading; a dormant one is faint.

**Legible by default** (plan 28 N7, the owner's decisions of 2026-10-20):
every node starts **collapsed** — its title and at most five short lines
(`graphview.summary`: what it holds, how much is patched, its live
reading), no row per port, one ``in`` and one ``out`` stub on its title
line. While either end of a pair is collapsed, every value / trigger
cable between the two nodes is **one wire** (`graphview.VBundle`, drawn
from stub to stub, as thick as it is many, capped; hover lists its
cables; selected, the side pane lists its rows, each route as ROUTING's
`_row`; Delete is refused in words). A render cable stays one wire each,
drawn to a collapsed node's stub. A node's **+** (or the head's **expand
all**) expands it: its ports as N2 drew them — the page's **patched
only** chip and the node's own **all ports / patched only** chip within
— and, both ends expanded, the real cables. A drag onto a collapsed
node's stub opens a picker of its ports (`open_land`, `land`) and lands
through `Edit.connect`; right-click a node for Learn on any of its params.
The collapse state is the page's UI state (`st["open"]`), saved nowhere.
**Tidy** collapses every node, forgets every position and says what it
did; the details chip shows only with a selection on a narrow page.

An expanded node folds its port groups (the hands' axes, the desk's
knobs) one by one. (Plan 28 N5's desk-template subgraph went with the
templates, plan 44 D3; `is_open` and `drawn_cable` stay for any cable
inside a subgraph.) A desk
layer that is down (SHIFT not latched, or latched) draws its node and its
ports faint. Hovering a cable says its reading and its depth; a
port, its reading; a device, its status. Selecting a route shows its
ROUTING row (`ui_routing._row`, the same widgets, the same table) beside
the canvas — below it while the page is narrow — selecting an effect's
node shows its strip (`ui_fx.strip`), and a modifier's node the
MODIFIERS strip's editor for it (`ui_routing.modifier_block`, plan 28
N7: GRAPH edits the routes and the modifiers; ROUTING points here).
Any other node shows its params as the panel's own rows (the owner,
2026-10-24: "I can see the ports … but I can't actually edit those
things"): `_param_rows`, `Panel._row` per param port — patched first in
each group, an alias left out — so an edit is the param's (undo, dirt,
modulation as on every page); past `FOLD_AT` rows each group folds, a
group holding a patched port open at first. A node with a page has an
**open on <PAGE>** chip at the top (`home_page`, `open_on`: a media
channel's MEDIA with it selected, an effect's FX, an LFO's LFO …); a
switch has none — its side panel is its control: a chip per input named
by what feeds it, the pick lit, a click its pick (`_switch_block`).

**Editing the modulation** (plan 28 N3): a cable dragged between two
pins (`_create`) and a cable or node deleted (`_delete`) go through
`graphview.Edit` and the table's own calls — the same table ROUTING
edits, so either page shows the other's change next frame, and undo, the
loadable patch's dirt and the referee are theirs. A taken param asks Replace /
Keep (ROUTING's prompt, `ui_routing.ask`); a refusal says why on the
page's head (`st["note"]`) and on the drag. Right-click: a param's `mod`
pin offers the param menu's Learn items (`Panel._ctx_learn_block`, the same
function), a cable offers "insert" (a modifier onto it) and delete, the
canvas the node picker (a modifier of each kind, a macro, and since plan
31 an LFO or an envelope, up to its bank's cap: `add_voice`), a modifier,
macro, LFO or extra envelope node delete (an LFO or envelope through its
bank, one undo step; a lane envelope 1–5 refused). A sequencer lane's
envelope binding is a ``lane`` cable: it is never deleted, only rebound
(a lane's pin dragged onto an envelope's ``fire`` base stub). A free modifier node dropped onto a lit cable is
inserted into it (`dropped`). **The seam with N4** (render edits): `_create` and
`_delete` dispatch by the pins' type through `CREATE` / `DELETE`; value and
trigger cables are this file's handlers, image / geometry / mask N4's.

**Edits** (plan 28 N4, the render graph): a cable dragged between two
image ports is a wire in the loadable patch's graph (`graphview.Edit.wire`),
type-checked while it is dragged — a port of another type, a port that
does not exist, a loop: the cable goes red and the tooltip says the
words a loadable patch file would get; a geometry cable from a hands node into
the scene or the layer is where that node is drawn. Right-click the
canvas for the picker (an effect instance, a hands node, a composite);
right-click a render node to delete it, draw its hands as lines or set
a composite's blend;
Delete — or ⌫, a Mac's delete key — takes a selected render cable or
node out of the graph, with the canvas focused (`_delete_key`). A box
dragged on the background selects the nodes in it; with ⌥ (Option) held,
the cables it touches instead (the widget's own link select: nodes and
cables are never selected together), so Delete takes many cables at once. Each
edit is one undo step and dirties the loadable patch; the renderer builds the
graph again from it. Render edits do not go through N3's `_act`:
their handlers (`_create_render`, `_delete_render_cable`,
`_delete_render_node`) land through `render_edit`, whose undo step is
pushed only once the edit is read back and accepted.

**The free graph** (plan 33 U): the pattern, the backdrop, the switches
and the shape's `faces` port are drawn like the other render nodes
(`graphview.build`). The picker adds a node on no wire, where the menu
opened (`add_render`): faint, "reaches nothing", until it is wired in. A
render cable's menu offers "insert ▸" (`insert_node`: effects ▸ and
every other picture node kind, `graphview.INSERT_MENU`); **any picture
node let go on a picture cable is spliced into it** (2026-11-01, the
owner: "there's nothing special about effects"; `dropped`,
`Edit.place_node`, `graphview.INSERT_PORTS`): the cable's picture into
its inlet, its picture on into whichever port the cable fed. A node with
several inlets (a composite's under and over, a switch's in1 … in8) asks
which on release (`st["onto"]` with `inlets`, `put_onto`); a source (a
channel) takes the cable over: it feeds the port instead, and what did
keeps its other consumers. **The drag shows
what the drop will do** (2026-10-29, `onto_plan`, `_drag_preview`): the
cable it will go onto — of those through the node's box, the one nearest
its centre — is drawn thick in the drop colour, and every other cable
that could take the node dims (a spotlight: a picture cable is already
red, a trigger already orange); a cable that could never take it (a
value cable under a picture node, a bus cable, a through wire over an
off effect, a mask or depth cable: the plan's `cold`) keeps its colour,
so "won't take it" reads differently from "not near enough", and near
one the reason is beside the pointer, which otherwise says what letting
go does; nothing lit, nothing happens. The release acts on the plan the
last drag frame lit (`st["press_plan"]`), never on a plan re-asked at the
editor's grid-snapped position. Two cables as near: a chooser names each
("Look-back → Acid") and the pick takes it (`st["onto"]`, `put_onto`). A
node already wired only moves on the canvas — unless ⌘ is held: then
it lights a cable as a free one does, and let go on it moves there (out
of its place, its chain closed over it: reordering the run; a source's
old consumers lose their feed, and the line says so). Without ⌘
the pointer says to hold it from the drag's start. A node that never
splices (a geometry, a hands layer, a matte, a window) is refused in
words over a picture cable, as a modifier is. A free modifier goes
onto a route or a modifier's input the same way; several nodes dragged
together only move. A member dropped out of its open group onto a cable
leaves the group and is spliced, two steps. A group node dropped on a
cable only moves (later). A compile error colours an effect
node's title and is its hover (`effect_errors`). The selected effect is
the panel's one selection, shared with the FX page (`Panel.fx_selected`,
`share`, `select_effect`). The selected node itself is published on the
panel (2026-10-31, `publish`: `Panel.graph_selected`, the one selected
node's id, and `graph_selected_at`) for whoever is not this view — a
controller's node mode, the side pane — as of the
last frame this page drew; a loadable patch landing without that node lets it go
on any page (`settle`); `select_id` / `Panel.select_graph_node` select
one from outside, and `node_params` / `Panel.graph_selected_params` are
its registry ids.

**The wired frame** (plan 35 G): the canvas is the loadable patch's wired frame,
in the owner's ids and words — every node of it titled for what it is
(`graphview.label_of`: "Look-back", "Hands layer", "Channel A", a window
by its config name), its hover what it does with its id and its params'
prefix (`graphview.hover_of`), the side panel's header the same
(`graphview.side_head`). Every node and wire of it deletes; only a type
error and a loop refuse, and a window keeps itself (its wires go). The
picker is grouped by primitive — starters ▸ (plan 36 T5: the scene chain
`shape → scene → All outputs`, tracers, tracers + dream, dream on a
picture, feedback (wave 0 E1, 2026-11-02: a delay loop with a blend, the
trails mechanism from here — many allowed), channel to backdrop, each a
pre-wired group in one gesture, laid left to right where the menu opened;
a picture cable's menu has the tracers, dream and feedback ones, on its
picture, and a picture node's menu has **add feedback after**, the loop on
the cable out of it, laid under the node's box: `render_node_menu`,
`add_feedback_after`, `node_below`), scene ▸, look-back ▸, pictures ▸, effects ▸,
copy of ▸ — a frame node the section has drawn disabled
(`render_picker`).

A node can be moved: where it is dropped is saved, in the
loadable patch's ``layout`` for the look's nodes and the show's for the meta controller's
(`graphview.home`), and the loadable patch (or the show) is dirty. An unplaced
node takes its place in its **area** (plan 28 N9, `graphview.layout`):
controllers → audio (the small *other* under it) → modulation → media →
scene → look-back → effects → outputs (plan 35 G: by primitive), left to
right, each titled faintly on the canvas behind its
nodes (`_titles`). A node with nothing in and nothing out — an unused
macro, an unpatched LFO, a group no cable reaches, a lost device — is
not drawn (`drawn_node`): its area shows one line in its place ("8 idle
macros · 3 idle LFOs", `_idle_line`) whose **+** shows them under it so
one can be patched; patched, it is drawn as any node. The picker still
offers every idle macro. **Tidy** (`tidy`) collapses every node, closes
the idle lines, forgets every position on the canvas and lays them all
out again in their areas — one undo step for the positions (`forget`) —
frames the canvas on them in what the side pane leaves of it (`ask_fit`, as the
canvas's open and every load do) and says so on the head ("laid out 36 nodes in
6 areas, every one collapsed · 12 idle off the canvas", or "already
tidy"). **The side pane is always on** (plan 49: `ui_pane.py`), one
view at a time at its full height (2026-11-07): the selection's details
(`_side`; with nothing selected, a line saying so), or the body of one
of the other pages, which this page's pane is the only home of (plan 49,
stage 3: no rail; this page is always drawn, and `ui.page` is the view).
A left click on the canvas that leaves something selected brings the
selection view up (`_note_pick`). It lies under the canvas on the panel's narrow
page; the **details beside / below** chip moves it (a page 720 px wide
puts it in a side column by itself, no chip). **The side column is resizable** (the
owner, 2026-10-27: "for some UI, the little sidebar … is just not wide
enough"): a grip on its left edge drags it between `SIDE_MIN` and what
leaves `CANVAS_MIN` of canvas (`side_width`), and the width is this Mac's,
kept in ``<machine>/ui.json`` (`read_side` / `write_side`, written when
the drag lets go), so it holds across loadable patches, shows and relaunches.

**The editor context** is the widget's own C++ object: made on the first
draw of the page, held in the panel's state (``panel._graph``) — not in
this module — so a hot reload of this file keeps drawing on the same
context and makes no second one; destroyed by `close` (`Panel.close`,
which app.py calls on quit and on ⌘R before imgui shuts down). Its
settings file is off (`Config.settings_file = ""`): the positions are
the loadable patch's and the show's, never a NodeEditor.json beside the app.

**The start zoom** (plan 58 SM2) is that settings file's one use: the binding
has no zoom setter, and only the editor's first load reads a zoom. `_canvas`
makes a temporary file holding just a view (`start_view`) for the editor it
creates, and `_start_view_read` turns the file off again right after the first
`ed.begin`, before that frame can save anything. So a zoom is set once per
editor, and `graphview.SCALE` and every saved position stay as they were.
Nothing else sets one, and a canvas's change of size keeps both the zoom
(`CanvasSizeMode.center_only`) and the corner (`keep_corner`).
"""

from __future__ import annotations

import colorsys
import dataclasses
import json
import math
import os
import tempfile
import time
from contextlib import contextmanager, suppress

from imgui_bundle import imgui
from imgui_bundle import imgui_node_editor as ed

from . import graph as rgraph
from . import (
    graphview,
    modifiers,
    params,
    patches,
    pinch,
    ui,
    ui_browse,
    ui_fx,
    ui_kit,
    ui_pad,
    ui_pane,
    ui_players,
    ui_routing,
    undo,
)
from .bands import CEIL
from .graph import Effect
from .groupwords import group_title
from .learn import META_UNDO, PairAsk
from .library import LibraryError
from .params import Kind
from .routing import PAIR_SCHEME, Binding, base_refusal, is_macro, row_words
from .view import RED as RED_RGB

STATE = "_graph"         # the panel's attribute: survives a reload of this module
COLOURS = {
    graphview.VALUE: imgui.ImVec4(0.86, 0.86, 0.88, 1.0),
    graphview.TRIGGER: imgui.ImVec4(1.0, 0.74, 0.28, 1.0),
    graphview.IMAGE: imgui.ImVec4(*RED_RGB, 1.0),     # ui.RED: the one red
    graphview.GEOMETRY: imgui.ImVec4(0.38, 0.72, 1.0, 1.0),
    graphview.MASK: imgui.ImVec4(0.72, 0.52, 1.0, 1.0),
}
# a cable of a kind with a colour of its own, whatever it carries (plan 57: the
# owner's "a special type of cable", not white, as the value cables nearly are)
KIND_COLOURS = {graphview.NODE_MODE: imgui.ImVec4(*graphview.NODE_MODE_RGB, 1.0)}
DORMANT_ALPHA = 0.22
THIN, THICK = 1.5, 5.5   # a value cable at rest and at full reading
WIRE = 3.0               # a render cable, a trigger
NODE_W = 190.0 * graphview.SCALE    # a node's inner width
DENSITY_STEP = 0.1                  # `canvas_density`: 1.3 lands exactly
DENSITY_MAX = 4.0
DENSITY_SETTLE_S = 0.3              # `held_density`
PIN = 12.0               # a pin's square: a bigger target for a trackpad (2026-10-26)
# 2026-10-31 (the show of 2026-10-30: cable targets "way too small" zoomed
# out): a pin's hit target is never under MIN_PX screen px, however far out
# the canvas is zoomed — the drawn pin stays PIN; the hit rect grows
# (`pin_hit_size`), held to its row and to the pins beside it
MIN_PX = 22.0            # a pin's hit target, at least, in screen px at any zoom
STUB_REACH = (graphview.COL_W - NODE_W) / 2 + PIN   # a stub's hit, outward past the node's edge:
#                          at most half the gap between two columns, so two columns' stubs never meet
GROW_LEFT, CENTRED, GROW_RIGHT = -1, 0, 1   # where a pin's hit rect grows from its drawn square
SIDE_W = 320.0           # the side column's width at first, when the page is wide enough for it
SIDE_MIN = 240.0         # …the narrowest a drag may make it
FIT_WAIT = 1             # frames a fit waits: a new loadable patch's nodes are measured on its second
FIT_TRIES = 30           # …and frames it goes on asking while none is measured yet
FIT_TOGETHER = 3         # frames apart a load's new name and new graph may land
FIT_A, FIT_B = "n:@fit.a", "n:@fit.b"   # the fit's two invisible corners (`_fit_when_asked`)
CANVAS_MIN = 240.0       # …and the canvas it must leave beside it
GRIP_W = 8.0             # the drag grip on the column's left edge
WIDE = 720.0             # …which is this wide; narrower, the selection goes below
BELOW_H = 240.0          # the selection's height below the canvas
TIMES = 120              # draws the SYSTEM line's median is over
PATCHED_TIP = ("Patched only: an expanded node shows just its patched ports — "
               "its own all / patched chip flips it")
TIDY_TIP = ("Collapse every node, forget every position on the canvas and lay them all "
            "out again in their areas — controllers, audio, modulation, geometry, shaders "
            "(⌘Z puts the positions back)")
# plan 28 N9: the areas' titles on the canvas, and the idle lines
TITLE_SIZE = 30.0        # canvas units: an area's title at full zoom
TITLE_SCREEN = 18.0      # px: what it stays on screen while the canvas is zoomed out
TITLE_FLOOR = 12.0       # px: never smaller on screen (review round 1); a short word if need be
TITLE_GAP = 16.0         # canvas units kept clear before the next title on its row
THROUGH_ALPHA = 0.5      # a through wire over off effects: drawn, but plainly not a cable
THROUGH_NO_DELETE = ("a through wire stands for off effects: turn one on (FX) or open the "
                     "off effects line to edit its cables")
AREA_TIP = "Frame the canvas on this area's boxes (a click on its title does the same)" 
TITLE_ALPHA = 0.30       # faint: behind the nodes, never one of them
IDLE_TIP = ("Nothing in, nothing out: not drawn so the canvas stays readable. + shows "
            "them here to patch one; patched, it is drawn like any node. The picker "
            "(right-click the canvas) still offers every idle macro.")
BESIDE_TIP = ("Where the selection's details go: beside the canvas or under it — widen "
              "the window to give both room (in a window this wide they sit beside by themselves)")
# plan 28 N7: a bundle's thickness follows how many cables it holds, capped
FAINT_TIP = (f"{graphview.REACHES_NOTHING}: no path from it ends at an output, the faces, "
             "the pattern, the backdrop or the run — it never runs. Wire it in, or drop "
             "it on a picture cable")
BUNDLE_STEP = 0.5        # px a cable, past the first
BUNDLE_MAX = 7.5         # the cap: a bundle of ten cables or more (3 + 9 × 0.5)
EXPAND_TIP = "Expand this node: a row per port, its real cables"
COLLAPSE_TIP = "Collapse this node: its title and a few lines, one wire per neighbour"
ALL_TIP = ("Expand every node (a row per port, every cable) — or collapse them all back "
           "to a handful of boxes and wires")
# plan 36 T6 (D4): the **preset only** chip starts lit, for every loadable patch
# (a constant so the tests' autouse fixture can start them on the full canvas)
PATCH_ONLY = True
PATCH_ONLY_TIP = ("Lit: only the patch's own nodes, what is wired to them and the windows "
                   "they reach. Controllers, modulation and macros are left off the canvas "
                   "(nothing is changed, only not drawn). Click to show everything.")
# 2026-10-26: output 1's picture behind the canvas, fixed to the canvas (not
# the canvas: it neither pans nor zooms), the editor's own ground laid
# over it at 1 − `backdrop_alpha`
BACKDROP_TIP = ("Output 1's picture behind the nodes, fixed to the canvas — the slider "
                "beside it sets how strongly it shows")
BACKDROP_ALPHA = 0.35    # how strongly it shows by default
# 2026-10-26 (the trackpad; ported from Dan's graph-quick-wins): two
# fingers moving pan the canvas — the editor itself only zooms on a wheel
# — and ⌘ with them zooms. GLFW gives a trackpad's scroll as a tenth of
# its pixels, so 10 px a unit follows the fingers; a mouse's notch is one unit
PAN_PX = 10.0
# while the panel is on the deck off air, what is on air in the canvas's
# top-right corner, this share of the canvas's width, framed red
MONITOR_W = 0.22
MONITOR_TIP = "What is on air: output 1, as the room sees it. Behind the nodes is the deck off air."
# plan 44 D5d: the head's deck row
DECK_TIP = ("Which deck this panel shows and edits. Click for the other. Red: it is off air, "
            "so nothing here reaches the room until the crossfader brings it up. Controllers "
            "go where their players' duties say, whichever you look at, and a pad or an F-key "
            "loads the deck off air. A load from this panel lands on the deck it shows.")
COPY_LABEL = "copy on air to off air"
COPY_TIP = ("Replace the deck off air with the look on air, running from where it is now, so "
            "the two are one until someone touches either. The deck on air does not move. "
            "One undo step on the deck off air.")
FADE_TIP = ("Run the crossfader to the far end over the seconds beside this. A hand on the "
            "desk's crossfader ends it there. Fading into an empty deck is black.")
OFF_AIR_FRAME = 3.0     # the red canvas frame's thickness, in points, while the panel is off air
XFADE_MIN_W, SECONDS_W = 120.0, 56.0     # the head's crossfade slider and its seconds
# plan 37 C1 (P1): a picture node's body is the picture it makes — its
# thumbnail (`outputs.PreviewTextures`) in a box at the node's width
# (`graphview.THUMB_H` tall), fitted whole; a geometry's scene picture is
# drawn at `FAINT_PIC` of its brightness (`graphview.THUMB_FAINT`)
FAINT_PIC = 0.4
THUMB_GROUND = (0.0, 0.0, 0.0, 1.0)    # the box before (or without) a picture
# the shape node's side panel: the polytope alone, as white lines on black
# (`_wireframe`, drawn by the renderer: `Renderer.want_wire`) — the shape as
# it turns now, without the scene's faces, points, pattern or effects; a
# square this wide (capped) at the top
WIRE_MAX = 260.0         # px: the square's side at most
WIRE_TIP = ("The shape alone, live: its edges at the angles it is drawn at — no faces, "
            "points, pattern or effects")
# plan 37 C2 (D3): the head's **pictures · tint cables** switch, off by
# default (plain red), page state only — never the loadable patch's or the show's.
# Lit, a picture cable's red leans by its maker's dominant hue
# (`PreviewTextures.hue`), at most `TINT_SPAN` turns either side of red
# (`tint`): red stays the colour of a picture cable, its lean says what
# flows; a picture with hue strength `TINT_FULL` or more leans all the way,
# a grey one not at all
TINT_LABEL = "pictures · tint cables##graph"
TINT_TIP = ("Lit: each picture cable's red leans by the colour of the picture it "
            "carries — toward orange for yellow-green pictures, toward rose for "
            "blue-violet ones; red, cyan and grey pictures leave it red — read from its "
            "maker's thumbnail once a second. Off: plain red. A view setting: not saved "
            "with the patch or the install")
TINT_SPAN = 20.0 / 360.0
TINT_FULL = 0.25


# ---------------------------------------------------------------- state and context

def _state(panel) -> dict:
    """The page's state on the panel. Every key by `setdefault`, so a key
    added by a later edit (N3, N4) lands on a dict an older build of this
    file made, across a hot reload."""
    st = panel.__dict__.setdefault(STATE, {})
    for k, v in (("editor", None), ("ids", {}), ("names", {}), ("applied", {}),
                 ("flip", set()), ("folds", set()), ("patched_only", True), ("view", None),
                 ("key", None), ("tidy", False), ("times", []), ("created", 0),
                 ("beside", False)):
        if k not in st:
            st[k] = v
    for k, make in EDIT_STATE:                     # plan 28 N3's keys
        st.setdefault(k, make())
    st.setdefault("said", "")               # plan 28 N4: the last render edit
    # plan 28 N7: the expanded nodes (every other one is collapsed: the
    # default), the bundles drawn last frame by id, how many wires were
    # drawn, a drag let go on a collapsed node's stub (its port picker)
    for k, make in (("open", set), ("bundles", dict), ("wires", int), ("land", lambda: None),
                    ("onto", lambda: None)):
        st.setdefault(k, make())
    st.setdefault("idle_open", set())       # plan 28 N9: the areas whose idle line is open
    st.setdefault("backdrop", True)         # 2026-10-26: output 1 behind the canvas
    st.setdefault("backdrop_alpha", BACKDROP_ALPHA)
    st.setdefault("pan", (0.0, 0.0))        # canvas units every position is moved by
    st.setdefault("patch_only", PATCH_ONLY)     # plan 36 T6 (D4): on for every loadable patch, kept across loads
    st.setdefault("hide", frozenset())      # the node ids that view leaves off this frame
    # 2026-10-31: the nodes the picker added this session (canvas ids), drawn
    # whatever the chip and the idle lines say until deleted (`reveal_node`):
    # never saved, not an undo step
    st.setdefault("revealed", set())
    st.setdefault("tint", False)            # plan 37 C2 (D3): plain red until lit
    st.setdefault("thumb_hover", None)      # the node whose thumbnail the pointer is on
    st.setdefault("tints", {})              # cable id → its tinted colour, this frame
    # 2026-10-27: the side column's width (None until this Mac's file has been
    # asked), whether its grip is held, and the machine folder the width is kept in
    st.setdefault("side_w", None)
    st.setdefault("side_drag", False)
    st.setdefault("machine", None)
    # plan 40 T3: the patch a browser line is dragging (its slug), the cable
    # it would splice into this frame and why not, the side pane's save-as-
    # patch form (``[group id, name, note]``), the browser's listing
    st.setdefault("patch_drag", None)
    st.setdefault("drop_cable", None)
    st.setdefault("onto_lit", None)         # 2026-10-29: a dragged node's `onto_plan`
    st.setdefault("press", None)            # … and the node the mouse went down on
    st.setdefault("press_plan", None)       # 2026-11-01: the last plan the drag lit (the drop's)
    st.setdefault("onto_cold", None)        # … and the cables that could never take it, cached
    st.setdefault("drop_why", "")
    st.setdefault("patch_form", None)
    st.setdefault("patch_list", None)
    return st


# plan 28 N3: the last refusal's words (shown on the head until the next
# edit), each drawn pin's canvas position (a drop onto a cable is found by
# it), the right-click menu's subject, the canvas point the picker opened at
EDIT_STATE = (("note", str), ("pin_xy", dict), ("menu", lambda: None), ("menu_at", tuple))


def start_view(zoom: float) -> str:
    """A temporary settings file saying only "start at `zoom`" (screen points
    per canvas unit), for `Config.settings_file`. "" for 1:1 or if no file can
    be written: the editor's own start, since no zoom is worth a launch."""
    if zoom == 1.0:
        return ""
    view = {"scroll": {"x": 0, "y": 0}, "zoom": zoom,   # (an empty rect: the zoom is taken as given)
            "visible_rect": {"min": {"x": 0, "y": 0}, "max": {"x": 0, "y": 0}}}
    try:
        fd, path = tempfile.mkstemp(prefix="hyperspace-graph-view-", suffix=".json")
    except OSError:
        return ""
    try:
        f = os.fdopen(fd, "w")
    except OSError:
        os.close(fd)
        with suppress(OSError):
            os.unlink(path)
        return ""
    try:
        with f:
            json.dump({"nodes": {}, "selection": None, "view": view}, f)
    except OSError:
        with suppress(OSError):
            os.unlink(path)
        return ""
    return path


def _start_view_read(ctx, path: str) -> None:
    """After the first `ed.begin`, which read the start view: the settings file
    off before the editor can save into it, and gone."""
    ed.get_config(ctx).settings_file = ""
    with suppress(OSError):
        os.unlink(path)


def canvas_density(base: float, units: float) -> float:
    """The density to bake the canvas's glyphs at, with `units` canvas units a
    point: the editor scales vertices, so a word zoomed 1.3× at 1x is a 20 px
    glyph stretched to 26, and soft. Baked at the size it lands, it's sharp. Up in
    `DENSITY_STEP`s, so a zoom's sweep bakes a few sizes, not one a frame; never
    under `base` (zoomed out, as before), never over `DENSITY_MAX`."""
    wanted = base / max(units, 1e-3)
    return max(base, min(math.ceil(wanted / DENSITY_STEP - 1e-3) * DENSITY_STEP, DENSITY_MAX))


def held_density(st: dict, wanted: float, now: float | None = None) -> float:
    """The density to draw at: `wanted` at the start, then only once it has held
    `DENSITY_SETTLE_S`. A new density is a bake and can be a new atlas, up to
    230 ms measured, on the one thread the render shares: a person's zoom makes
    one at its end, soft while it moves, not one a step."""
    now = time.monotonic() if now is None else now
    held = st.get("density_held")
    if held is None or held == wanted:
        st["density_held"], st["density_since"] = wanted, None
        return wanted
    since = st.get("density_since")
    if since is None or since[0] != wanted:
        st["density_since"] = (wanted, now)
    elif now - since[1] >= DENSITY_SETTLE_S:
        st["density_held"], st["density_since"] = wanted, None
        return wanted
    return held


def keep_corner(st: dict, size: tuple[float, float]) -> None:
    """Before `ed.begin`: a canvas that changed size stays at its top-left. The
    editor re-centres on any change of size, moving every node by half of it;
    the pan moves them back in the same frame (`st["pan"]`, as a scroll does)."""
    last, st["canvas_size"] = st.get("canvas_size"), size
    if last is None or last == size:
        return
    k = st.get("zoom", 1.0) / 2.0       # canvas units a point
    px, py = st["pan"]
    st["pan"] = (px + (last[0] - size[0]) * k, py + (last[1] - size[1]) * k)


def editor(panel, settings_file: str = ""):
    """The panel's editor context, made on first use (settings file off, but
    for the start view `_canvas` hands the one it makes)."""
    st = _state(panel)
    if st["editor"] is None:
        cfg = ed.Config()
        cfg.settings_file = settings_file
        cfg.enable_smooth_zoom = True       # a trackpad's small steps zoom a little each
        # a canvas that changes size keeps its zoom. The editor's default rescales
        # with the height: a head's extra line would change a person's zoom.
        cfg.canvas_size_mode = ed.CanvasSizeMode.center_only
        st["editor"] = ed.create_editor(cfg)
        st["created"] += 1
        st["applied"] = {}      # a new context knows no position yet
    return st["editor"]


def close(panel) -> None:
    """Destroy the editor context, if the page ever made one — before
    imgui's own context goes (quit, ⌘R). Safe to call twice."""
    st = panel.__dict__.get(STATE)
    if not st or st.get("editor") is None:
        return
    st.pop("canvas_size", None)
    ctx, st["editor"] = st["editor"], None
    st["applied"] = {}
    ed.destroy_editor(ctx)


def _id(st: dict, name: str) -> int:
    """A stable widget id for a pin, node or cable name (never 0)."""
    ids = st["ids"]
    k = ids.get(name)
    if k is None:
        k = ids[name] = len(ids) + 1
        st["names"][k] = name
    return k


# ---------------------------------------------------------------- the model, per frame

def _layouts(panel) -> tuple[dict | None, dict | None]:
    """(the loaded patch's layout map, the open show's), the live dicts —
    None where the panel has no library."""
    lib = getattr(panel, "library", None)
    loaded_patch = getattr(lib, "loaded_patch", None)
    project = getattr(lib, "install", None)
    pre = getattr(loaded_patch, "layout", None) if loaded_patch is not None else None
    if loaded_patch is not None and pre is None:
        pre = loaded_patch.layout = {}
    show = getattr(project, "layout", None) if project is not None else None
    if project is not None and show is None:
        show = project.layout = {}
    return pre, show


def _lanes(panel):
    a = getattr(panel, "audio", None)
    chain = getattr(a, "chain", None)
    if chain is None or not getattr(a, "on", False):
        return None
    return [float(v) / CEIL for v in chain.lanes[: chain.n]]


def view_of(panel) -> graphview.View | None:
    """The page's view: rebuilt when what it is made of moves
    (`graphview.key`), its readings refreshed every frame."""
    router = ui_routing.router_of(panel)
    if router is None:
        return None
    st = _state(panel)
    reg, table = panel.reg, router.table
    devices = getattr(panel, "devices", None)
    rgraph = getattr(getattr(panel, "renderer", None), "_graph", None)
    gs = getattr(getattr(getattr(panel, "library", None), "loaded_patch", None), "graph", None)
    # (plan 35 G: the wired frame itself, in the new ids)
    spec = getattr(gs, "spec", None)
    lanes = _lanes(panel)
    # plan 40 T2: the loadable patch's groups (made, opened, renamed: a new view)
    groups = getattr(getattr(getattr(panel, "library", None), "loaded_patch", None), "groups", None)
    k = (graphview.key(table, reg, router, devices, rgraph, spec), groups_key(groups))
    if st["view"] is None or st["key"] != k:
        chain = getattr(getattr(panel, "audio", None), "chain", None)
        bands = (getattr(router, "labels", {}).get("lane")
                 or (getattr(chain, "band_names", None) if chain is not None else None))
        st["view"] = graphview.build(table, reg, router, devices, rgraph, spec,
                                     lanes=lanes, bands=bands,
                                     slots=getattr(panel, "outputs", None) or (),
                                     groups=groups)
        st["key"] = k
    else:
        graphview.refresh(st["view"], reg, router, lanes, lambda nid: collapsed(st, nid))
    return st["view"]


def groups_key(groups) -> tuple:
    """Plan 40 T2: what the view's groups are made of, cheaply compared
    each frame (`view_of`)."""
    return tuple((g.get("id"), g.get("name"), tuple(g.get("nodes") or ()), bool(g.get("open")),
                  g.get("patch"), len(g.get("kept_by_host") or ()))
                 for g in groups or () if isinstance(g, dict))


def full(st: dict, nid: str) -> bool:
    """Does expanded node `nid` show every port, not just its patched ones?
    The page's **patched only** chip, flipped by the node's own."""
    return (not st["patched_only"]) != (nid in st["flip"])


def is_open(st: dict, nid: str) -> bool:
    """Is node `nid` expanded (plan 28 N7: every node starts collapsed — its
    title and a few lines, one wire per neighbour)? For a desk template's
    node (plan 28 N5) open is also when its rows are drawn as cables."""
    return nid in st.setdefault("open", set())


def collapsed(st: dict, nid: str) -> bool:
    """Is node `nid` collapsed (the default)?"""
    return not is_open(st, nid)


def toggle_open(st: dict, nid: str) -> None:
    """Expand a collapsed node, or collapse an expanded one."""
    st.setdefault("open", set())
    st["open"] ^= {nid}


def expand_all(st: dict, view: graphview.View, on: bool) -> None:
    """The head's **expand all** (`on`) / **collapse all**."""
    st["open"] = {n.id for n in view.nodes if drawn_node(st, n)} if on else set()


def drawn_node(st: dict, n: graphview.VNode) -> bool:
    """Is node `n` drawn (plan 28 N9)? Every node but an idle one
    (`graphview.VNode.idle`: nothing in, nothing out), which is drawn only
    while its area's idle line is open — unless the picker added it this
    meta controller (`reveal_node`, 2026-10-31): a fresh node has no cable yet, and a
    node that is not drawn cannot be cabled. A folded group's member stays
    folded whatever else says."""
    if n.id in st.get("hide", ()):         # plan 36 T6: left off by the preset-only view
        return False
    if n.id in st.get("revealed", ()):
        return True
    return not n.idle or n.area in st.setdefault("idle_open", set())


def hidden_ids(st: dict, view: graphview.View) -> frozenset[str]:
    """Plan 36 T6: the node ids the **preset only** chip leaves off the
    canvas (`graphview.patch_only` draws the rest, and so does what the
    picker added this session, `reveal_node`); none while it is off.
    Drawing only: no wire, table or position changes, and the layout
    (`areas_of`) still lays every node out, so hiding moves nothing.
    Plan 40 T2 (D4): and a folded group's members, whatever the chip —
    their group's node stands for them until +."""
    fold = frozenset(graphview.folded(view))
    if not st.get("patch_only", PATCH_ONLY):
        return fold
    keep = graphview.patch_only(view) | st.get("revealed", set())
    return frozenset(n.id for n in view.nodes if n.id not in keep) | fold


def reveal_node(st: dict, nid: str) -> None:
    """Node `nid` (a canvas id) drawn from now on whatever the preset-only
    chip and its area's idle line say (`drawn_node`; 2026-10-31, the owner
    after the show of 2026-10-30: in preset only a fresh node landed
    hidden, "it just doesn't exist"). Page state for this session only:
    never saved, not an undo step, forgotten when the node is deleted
    (`remove_node`). Once the node is cabled into the section, preset only
    draws it on its own."""
    st.setdefault("revealed", set()).add(nid)


def _drawn_id(st: dict, view: graphview.View, nid: str) -> bool:
    n = view.node(nid)
    return n is None or drawn_node(st, n)


def toggle_idle(st: dict, area: str) -> None:
    """Open an area's idle line (its idle nodes drawn under it), or close it."""
    st.setdefault("idle_open", set())
    st["idle_open"] ^= {area}


def drawn_cable(st: dict, c: graphview.VCable) -> bool:
    """Is cable `c` drawn this frame as far as subgraphs go: one inside a
    collapsed subgraph node is not."""
    return not c.inside or is_open(st, c.inside)


def hidden_by(st: dict, view: graphview.View, pin: str) -> str:
    """The hover's extra line for a pin whose cables are inside a collapsed
    subgraph (a param's `base` stub a desk template sets): which node holds
    them; "" when none is hidden."""
    held = sorted({c.inside for c in view.cables
                   if c.dst_port == pin and c.inside and not is_open(st, c.inside)})
    names = [view.node(nid).label if view.node(nid) is not None else nid for nid in held]
    return "".join(f"\nset by desk {n} (collapsed: + shows it)" for n in names)


def shown(st: dict, n: graphview.VNode) -> list[graphview.VPort]:
    """The ports node `n` draws: none while it is collapsed (plan 28 N7);
    expanded, `graphview.visible` with this page's state."""
    if collapsed(st, n.id):
        return []
    return graphview.visible(n, full(st, n.id), st["folds"])


def forget(panel, view: graphview.View) -> None:
    """The tidy: every position of `view`'s nodes forgotten, in the loadable patch's
    map and the show's — one undo step (the library's marks carry both
    maps, plan 28 N2), so ⌘Z puts them back."""
    pre, show = _layouts(panel)
    ids = {n.id for n in view.nodes}
    if not any(k in ids for m in (pre, show) if m for k in m):
        return
    undo.push("tidy the graph", load=True)
    for m in (pre, show):
        if m:
            for nid in [k for k in m if k in ids]:
                del m[nid]


TIDIED = "laid out {n} nodes in {k} areas, every one collapsed"
TIDIED_IDLE = " · {i} idle off the canvas"
ALREADY_TIDY = "already tidy"


def areas_of(st: dict, view: graphview.View, stored=None) -> graphview.Layout:
    """`graphview.layout` with this page's state: a collapsed node its
    title and lines, an expanded one its ports, the open idle lines'
    nodes under them."""
    return graphview.layout(
        view, stored, lambda nid: full(st, nid),
        st["folds"], collapsed=lambda nid: collapsed(st, nid),
        idle_open=st.setdefault("idle_open", set()))


def layout_of(st: dict, view: graphview.View, stored=None) -> dict:
    """`areas_of`'s node positions."""
    return areas_of(st, view, stored).nodes


def tidied(view: graphview.View) -> str:
    """What a tidy that did something says: the nodes it laid out (the
    drawn ones), in how many areas, and how many idle ones it left off."""
    shown = [n for n in view.nodes if not n.idle]
    said = TIDIED.format(n=len(shown), k=len({n.area for n in shown}))
    idle = len(view.nodes) - len(shown)
    return said + (TIDIED_IDLE.format(i=idle) if idle else "")


def tidy(panel, st: dict, view: graphview.View) -> str:
    """The head's **tidy** (plan 28 N7: it always does something you can
    see, or says why not): every node collapsed, every position on the
    canvas forgotten (`forget`, one undo step), every node laid out again
    in its area (plan 28 N9), the idle lines closed — and the head says
    what it did (`tidied`: "laid out 36 nodes in 6 areas, every one
    collapsed · 12 idle off the canvas"), or "already tidy" when nothing
    moved or folded. The canvas is framed on the nodes after it, in what
    the pane leaves of it (`ask_fit`)."""
    was_open = bool(st["open"]) or bool(st.setdefault("idle_open", set()))
    st["open"] = set()
    st["idle_open"] = set()
    st["flip"].clear()
    before = dict(st["applied"])
    forget(panel, view)
    st["sat"] = {}                          # the layout's own places go too
    auto = layout_of(st, view)
    moved = sum(1 for n in view.nodes if drawn_node(st, n) and (
                before.get(n.id) is None or tuple(round(v) for v in before[n.id])
                != tuple(round(v) for v in auto.get(n.id, (0.0, 0.0)))))
    said = tidied(view) if (moved or was_open) else ALREADY_TIDY
    st["note"], st["said"] = "", said
    ask_fit(st)
    return said


# ---------------------------------------------------------------- the page

@contextmanager
def _dimmed(panel):
    """Disabled while a desk control is picked (`Panel._draw`): GRAPH's own
    head and canvas. The pane dims its bodies itself (`ui_pane._body`), and
    its headers stay live."""
    on = getattr(panel, "_picking", False)
    if on:
        imgui.begin_disabled()
    try:
        yield
    finally:
        if on:
            imgui.end_disabled()


def band_height(avail_h: float, section: bool) -> float:
    """The narrow page's band: `BELOW_H` for the selection, or with a
    section shown all but `CANVAS_MIN` of the page, so the section reads as
    its page did (plan 49 stage 3: with no rail, the desk's narrow panel
    has only this)."""
    return max(BELOW_H, avail_h - CANVAS_MIN) if section else BELOW_H


def page(panel, dt: float) -> None:
    t0 = time.perf_counter()
    ui._micro("graph")
    view = view_of(panel)
    st = _state(panel)
    if view is None:            # no canvas without a router; the sections all the same
        imgui.separator()
        imgui.text_disabled("no router attached")
        if st["machine"] is None:
            st["machine"] = getattr(getattr(panel, "library", None), "machine", None)
        if imgui.begin_child("##graph.side", imgui.ImVec2(0, 0)):
            ui_pane.draw(panel, st, dt, None)
        imgui.end_child()
        return
    st["hide"] = hidden_ids(st, view)       # plan 36 T6: before anything asks `drawn_node`
    _fit_on_a_load(panel, st)
    sel = _selection(st, view)
    if sel is not None and escaped():           # Esc closes the details: nothing selected
        st["deselect"], sel = True, None
    if st.pop("canvas_pick", False) and sel is not None:
        ui_pane.show(panel, ui_pane.SELECTION)  # a click on the canvas: what it picked, shown
    publish(panel, st, sel)
    share(panel, st, sel)
    # plan 49: the pane is always on, so its chip is too (on a narrow page)
    with _dimmed(panel):
        _head(panel, st, view, True)
    imgui.separator()
    avail = imgui.get_content_region_avail()
    wide = st["beside"] or avail.x >= WIDE
    # the canvas is always the page's whole size: the node editor re-centres
    # its view whenever its canvas changes size (no `CanvasSizeMode` keeps the
    # top-left), so a selection that narrowed it panned every node (the
    # owner, 2026-10-24). The details are laid over its edge instead, and what
    # else changes the size (a window, a head's line) is `keep_corner`'s.
    origin = imgui.get_cursor_screen_pos()
    if st["machine"] is None:                   # asked until a library is attached
        st["machine"] = getattr(getattr(panel, "library", None), "machine", None)
    if st["side_w"] is None or (st["machine"] is not None and not st.get("side_read")
                                and not st.get("side_drag")):
        # this Mac's width, asked once the machine is known (the default until then)
        st["side_read"] = st["machine"] is not None
        st["side_w"] = (read_side(st["machine"]) if st["machine"] is not None else None) or SIDE_W
    # (the frame's width is clamped to this page; the remembered one is not,
    # so a narrow window never shrinks what a wide one was set to)
    side = side_width(st["side_w"], avail.x)
    pos, size = details_rect((origin.x, origin.y), (avail.x, avail.y), wide, side,
                             band_height(avail.y, ui_pane.showing(panel) != ui_pane.SELECTION))
    # the node editor still sees a right-click over the details (they lie on
    # its canvas): noted here, before it draws, so `_menus` opens no graph
    # menu there and the control's own Learn menu opens (the owner, 2026-10-24)
    mouse = imgui.get_mouse_pos()
    st["details_rect"] = (pos, size)          # plan 49: the pane is always on
    st["over_details"] = (pos[0] <= mouse.x < pos[0] + size[0]
                          and pos[1] <= mouse.y < pos[1] + size[1])
    canvas = imgui.ImVec2(max(avail.x, 80.0), max(avail.y, 80.0))
    # 2026-11-02: where the canvas is and whose draw list it lands on, for
    # `replay.grab` (`panel:graph`): the page window's own list carries the
    # backdrop, the editor and its nodes; the side pane below is a child
    # (its decorations' indices on this list are added at the page's end)
    fbs = imgui.get_io().display_framebuffer_scale
    panel.canvas_px = ((float(origin.x), float(origin.y)), (float(canvas.x), float(canvas.y)),
                       (float(fbs.x), float(fbs.y)), imgui.internal.get_current_window().name)
    shown = _backdrop(panel, st, (origin.x, origin.y), (canvas.x, canvas.y))
    _scroll(st, (origin.x, origin.y), (canvas.x, canvas.y))
    with _dimmed(panel):
        _canvas(panel, st, view, canvas, st["backdrop_alpha"] if shown else 0.0)
    _note_pick(panel, st, (origin.x, origin.y), (canvas.x, canvas.y))
    # off air: the red frame and what is on air's inset, in the canvas's corner, left
    # of the pane beside it, above the band under it (a narrow page)
    page_list = imgui.get_window_draw_list()
    i0 = page_list.idx_buffer.size()         # (`replay` cuts these out, with the pane's ground)
    _monitor(panel, (origin.x, origin.y), (canvas.x - size[0], canvas.y) if wide
             else (canvas.x, canvas.y - size[1]))
    # the pane, always on (plan 49): its bottom is the canvas's, so the page ends where it did
    imgui.set_cursor_screen_pos(imgui.ImVec2(*pos))
    imgui.push_style_color(imgui.Col_.child_bg, imgui.get_style_color_vec4(imgui.Col_.window_bg))
    # imgui draws a child's decorations — its ground, border and
    # scrollbar — on the parent's list inside `begin_child` (one draw
    # call fewer); on the page's list they would be in the canvas's
    # picture, so the indices they take are noted for `replay` to cut out
    opened = imgui.begin_child("##graph.side", imgui.ImVec2(*size), imgui.ChildFlags_.borders)
    omit = (i0, page_list.idx_buffer.size())
    st["pane_window"] = imgui.internal.get_current_window().name   # (the tests find it by it)
    if opened:
        if wide:                        # the grip on the column's left edge, then the details
            _grip(st, pos, size, avail.x, side)
            imgui.indent(GRIP_W)
        # the one view: the selection's details, or a section
        home = home_page(sel[1]) if sel is not None and sel[0] == "node" else None
        ui_pane.draw(panel, st, dt,
                     (lambda: _side(panel, st, view, sel)) if sel else None,
                     sel_words(sel), home[0] if home else None)
    imgui.end_child()
    _settle_take_over(st)
    imgui.pop_style_color()
    panel.canvas_px = (*panel.canvas_px[:4], omit)
    times = st["times"]
    times.append(time.perf_counter() - t0)
    del times[:-TIMES]
    _arrive(panel, st)


def _note_pick(panel, st: dict, origin, size) -> None:
    """A left click on the canvas — pressed there and let go, not over the
    pane, no menu open, no desk control picked — asks the next frame to
    show the selection, once the editor holds what the click picked
    (`page`; a click that leaves nothing selected leaves the view as it
    is). A selection by code (`select_id`, `select_effect`) is no click:
    the section being worked in stays."""
    m = imgui.get_mouse_pos()
    if imgui.is_mouse_clicked(0):
        st["canvas_press"] = (
            origin[0] <= m.x < origin[0] + size[0] and origin[1] <= m.y < origin[1] + size[1]
            and not st.get("over_details") and not getattr(panel, "_picking", False)
            and not imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id))
    if imgui.is_mouse_released(0) and st.pop("canvas_press", False):
        st["canvas_pick"] = True


def pinch_wheel(magnification: float) -> float:
    """A pinch's magnification as the editor's smooth-zoom wheel: the
    editor zooms by `smooth_zoom_power` (1.1) per unit of wheel, so the
    picture grows by just what the fingers spread."""
    return math.log(max(1.0 + magnification, 0.05)) / math.log(1.1)


def scroll_pan(st: dict, wheel: float, wheel_h: float, zoom: float, cmd: bool) -> bool:
    """Two fingers on the trackpad (or a mouse's wheel) over the canvas:
    the canvas panned by them — `st["pan"]`, in canvas units (`zoom` of
    them a screen pixel), the picture following the fingers as a page
    scrolls — unless ⌘ is held, when the wheel is the editor's zoom. True
    when it panned (the wheel is then the page's, not the editor's)."""
    if cmd or not (wheel or wheel_h):
        return False
    k = PAN_PX * max(zoom, 1e-3)
    px, py = st["pan"]
    st["pan"] = (px + wheel_h * k, py + wheel * k)
    return True


def panned(st: dict) -> tuple[float, float]:
    """The pan every position is moved by: `st["pan"]` in whole canvas
    units. The editor floors a position it is given, so a fractional pan
    would read back as a drag and be saved — every node creeping a unit a
    frame (the owner, 2026-10-26)."""
    px, py = st["pan"]
    return float(round(px)), float(round(py))


def _scroll(st: dict, origin, size) -> None:
    """The wheel this frame over the canvas (not its details, no popup
    open) → `scroll_pan`; a panning wheel is taken from imgui before the
    editor opens, so the editor does not zoom on it too."""
    io = imgui.get_io()
    m = imgui.get_mouse_pos()
    over = (origin[0] <= m.x < origin[0] + size[0] and origin[1] <= m.y < origin[1] + size[1])
    spread = pinch.take()
    if (not over or st.get("over_details")
            or imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id)):
        return
    if spread:                                  # a pinch: the editor's zoom, at the cursor
        io.mouse_wheel, io.mouse_wheel_h = pinch_wheel(spread), 0.0
        return
    zoom = 1.0
    if st.get("editor") is not None:            # (last frame's zoom: the editor is not open yet)
        ed.set_current_editor(st["editor"])
        zoom = ed.get_current_zoom() or 1.0
    if scroll_pan(st, io.mouse_wheel, io.mouse_wheel_h, zoom, io.key_ctrl or io.key_super):
        io.mouse_wheel = io.mouse_wheel_h = 0.0
    else:
        io.mouse_wheel_h = 0.0                  # ⌘: the editor zooms, never sideways


def details_rect(origin: tuple[float, float], avail: tuple[float, float],
                 wide: bool, side_w: float = SIDE_W, band_h: float = BELOW_H,
                 ) -> tuple[tuple[float, float], tuple[float, float]]:
    """Where the pane is laid over the canvas (screen position, size): a
    `side_w` column on its right edge when `wide`, else a `band_h` band
    along its bottom. The canvas keeps its size underneath."""
    (x, y), (w, h) = origin, avail
    if wide:
        return (x + w - side_w, y), (side_w, h)
    return (x, y + h - band_h), (w, band_h)


def side_width(wanted: float, avail_w: float) -> float:
    """The side column's width on a page `avail_w` wide: `wanted`, held
    between `SIDE_MIN` and what leaves `CANVAS_MIN` of canvas — and never
    under `SIDE_MIN`, whatever the page (a page too narrow for both is one
    the details go below on anyway)."""
    return max(SIDE_MIN, min(float(wanted), avail_w - CANVAS_MIN))


def read_side(machine) -> float | None:
    """This Mac's remembered side width (``<machine>/ui.json``, key
    ``graph.side_w``), or None: no file, an unreadable one, or a value that
    is not a number. Never raises; a bad file costs only the memory."""
    try:
        w = ui_pane.read_doc(machine)["graph"]["side_w"]
    except (KeyError, TypeError):
        return None
    return float(w) if isinstance(w, (int, float)) and not isinstance(w, bool) else None


def write_side(machine, side_w: float) -> None:
    """Remember `side_w` in ``<machine>/ui.json``, keeping whatever else
    the file holds; a write that fails says so on stderr and costs only
    the memory."""
    doc = ui_pane.read_doc(machine)
    graph = doc.get("graph")
    if not isinstance(graph, dict):
        graph = doc["graph"] = {}
    graph["side_w"] = round(float(side_w), 1)
    ui_pane.write_doc(machine, doc, "graph")


def _grip(st: dict, pos: tuple[float, float], size: tuple[float, float], avail_w: float,
          side: float) -> None:
    """The side column's drag grip: its left edge, `GRIP_W` wide, the
    column's height. Called inside the column's child but submits no item
    — a hit test of its own on the mouse (plan 49 review: an item pinned
    to the column's top grew the child's content by its scroll every
    frame, once the sections made the column scroll, and its hit box left
    the drawn edge). Pressed on, the column follows the mouse
    (`side_width` keeps it in range) until let go, when the width is
    written for this Mac. A faint line while hovered or held, and the
    east-west cursor."""
    m = imgui.get_mouse_pos()
    over = (pos[0] <= m.x < pos[0] + GRIP_W and pos[1] <= m.y < pos[1] + size[1]
            and imgui.is_window_hovered(imgui.HoveredFlags_.child_windows)
            and not imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id))
    if over and imgui.is_mouse_clicked(0):
        st["side_drag"] = True
    held = bool(st.get("side_drag"))
    if held and imgui.is_mouse_down(0):
        st["side_w"] = side_width(side - imgui.get_io().mouse_delta.x, avail_w)
    elif held:
        st["side_drag"] = held = False
        machine = st.get("machine")
        if machine is not None:
            write_side(machine, st["side_w"])
    if over or held:
        imgui.set_mouse_cursor(imgui.MouseCursor_.resize_ew)
        x = pos[0] + GRIP_W / 2
        imgui.get_window_draw_list().add_line(
            imgui.ImVec2(x, pos[1]), imgui.ImVec2(x, pos[1] + size[1]),
            imgui.get_color_u32(imgui.Col_.separator_active if held
                                else imgui.Col_.separator_hovered), 2.0)


def wants_chip_w(panel) -> float:
    """The width `_wants_chip` takes on its line, the spacing before it
    included; 0 when it draws nothing (the PRESET strip budgets it)."""
    from . import devices  # (late, as `_wants_chip`)
    text = devices.missing_chip(panel_wants(panel))
    return 0.0 if text is None else ui.chip_w(text) + imgui.get_style().item_spacing.x


def share(panel, st: dict, sel) -> None:
    """Plan 33 U: the one effect selection (`Panel.fx_selected`) both ways.
    Moved elsewhere since this page last looked (the FX page's row, its
    "show on GRAPH": `select_effect`), the canvas selects that effect's node
    (next frame, `_select`); an effect node selected on the canvas is the
    panel's selection."""
    shared = getattr(panel, "fx_selected", None)
    if shared != st.get("fx_seen"):
        st["fx_seen"] = shared
        if shared:
            st["select"] = shared
        return
    if st.get("select"):                    # the canvas has yet to move to it
        return
    n = sel[1] if sel is not None and sel[0] == "node" else None
    if n is not None and isinstance(n.ref, Effect) and n.ref.effect != shared:
        panel.fx_selected = st["fx_seen"] = n.ref.effect


def select_effect(panel, name: str) -> None:
    """Select effect instance `name` (plan 33 U, the FX page's "show on
    GRAPH"): the panel's selection, and its node selected and centred on the
    canvas next frame — its area's idle line opened if it sits there."""
    st = _state(panel)
    panel.fx_selected = st["fx_seen"] = name
    st["select"] = name


def select_node(panel, name: str) -> None:
    """Select frame node `name` (plan 35 U, OUTPUT's "open on GRAPH":
    `output.2`, `output.all`) and centre it on the canvas next frame."""
    select_id(panel, f"render:{name}")


def select_id(panel, nid: str) -> None:
    """Select canvas node `nid` — `Panel.graph_selected`'s form: a frame
    node's `render:acid.2`, a modifier's own id — and centre it on the
    canvas next frame (`_select`): the one request path, `select_node`'s
    and `Panel.select_graph_node`'s. The canvas is always drawn, so the
    pane's view stays where it is: a section being worked in is not thrown away."""
    _state(panel)["select_node"] = nid


# ---------------------------------------------------------------- the selection, published

def publish(panel, st: dict, sel) -> None:
    """The canvas's selection on the panel (2026-10-31: `Panel.
    graph_selected`, `graph_selected_at`), for whoever is not this view —
    a controller's node mode, the side pane. The one
    selected node's id when `sel` is a node and it is the only node
    selected; None for nothing, a cable, a bundle, a group or several
    nodes. Written each frame the panel draws (plan 49 stage 3: GRAPH is
    always drawn; a deleted node is gone from the view, so the next frame
    publishes None), so it is live but while the panel is hidden, when it
    is as of the last frame drawn — until `settle` sees a loadable patch land
    without the node. `graph_selected_at` is imgui's frame count when
    the value last changed. An effect node's instance is `Panel.
    fx_selected` as well (`share`); that stays as it is."""
    nid = None
    if sel is not None and sel[0] == "node" and len(selected_ids(st)) == 1:
        nid = sel[1].id
    if nid != getattr(panel, "graph_selected", None):
        panel.graph_selected = nid
        panel.graph_selected_at = imgui.get_frame_count()


def settle(panel) -> None:
    """Every frame, panel hidden or not (`Panel._draw`): the loaded patch's graph
    spec is a new object after a load or a new (and after a graph edit) —
    seen to have changed, a published node the loadable patch no longer holds
    (`still_held`) is let go of, so a load on the PRESETS page does not
    leave a controller on a node that is gone. One identity test a frame;
    the names are read only when the spec moved."""
    st = panel.__dict__.get(STATE)
    nid = getattr(panel, "graph_selected", None)
    loaded_patch = getattr(getattr(panel, "library", None), "loaded_patch", None)
    spec = getattr(getattr(loaded_patch, "graph", None), "spec", None)
    if st is None or spec is st.get("spec_seen"):
        return
    st["spec_seen"] = spec
    if nid is not None and not still_held(panel, nid, spec):
        panel.graph_selected = None
        panel.graph_selected_at = imgui.get_frame_count()


def still_held(panel, nid: str, spec) -> bool:
    """Does the loadable patch as it now stands hold canvas node `nid`: a frame
    node (`render:…`) the spec names, a modifier (`mod.N`, `modifiers.
    next_id`) the table holds; any other node — a device's, a lane's, a
    group's — is not the loadable patch's and stays."""
    if nid.startswith("render:"):
        return nid.partition(":")[2] in graphview.frame_names(spec)
    if nid.startswith("mod."):
        table = getattr(ui_routing.router_of(panel), "table", None)
        return table is None or table.modifier(nid) is not None
    return True


def node_params(panel, nid: str) -> list[str]:
    """The registry ids under canvas node `nid` (`Panel.graph_selected_params`):
    `graphview.param_ids`, a copy's being its original's, as its side-panel
    header says."""
    view = _state(panel).get("view")
    n = view.node(nid) if view is not None else None
    name = nid.partition(":")[2] if nid.startswith("render:") else nid
    of = getattr(n.ref, "effect", "") if n is not None and graphview.kind_of(name) == "copy" else ""
    return graphview.param_ids(panel.reg, nid, of)


def effect_node(view: graphview.View, name: str) -> graphview.VNode | None:
    """The node effect instance `name` is drawn as: its scene pipeline's
    (named by the instance), else its first."""
    hits = [n for n in view.nodes if isinstance(n.ref, Effect) and n.ref.effect == name]
    # (plan 35 G: the instance's own node, before a copy of it)
    return next((n for n in hits if n.id == f"render:{name}"),
                next((n for n in hits if n.ref.name == name), hits[0] if hits else None))


def escaped() -> bool:
    """Esc pressed this frame, and nothing else wants it: no text field
    being typed in, no popup open (imgui closes that on Esc itself), and the
    player screen, drawn first, did not take it."""
    return (imgui.is_key_pressed(imgui.Key.escape, False)
            and not imgui.get_io().want_text_input
            and not imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id)
            and not ui_players.took_escape())


DELETE_KEYS = (imgui.Key.delete, imgui.Key.backspace)     # ⌫ is a Mac's "delete"


def delete_pressed() -> bool:
    """Delete or ⌫ pressed this frame, and nothing else wants it: no text
    field being typed in, no control held, no popup open."""
    return (any(imgui.is_key_pressed(k, False) for k in DELETE_KEYS)
            and not imgui.get_io().want_text_input
            and not imgui.is_any_item_active()
            and not imgui.is_popup_open("", imgui.PopupFlags_.any_popup_id))


def _select(st: dict, view: graphview.View) -> None:
    """Inside the editor, the nodes drawn: the selection `select_effect` (or
    the FX page) asked for, selected and brought on screen; a frame node
    `select_node` asked for (OUTPUT's "open on GRAPH") the same."""
    if st.pop("deselect", False):
        ed.clear_selection()
    gid = st.pop("select_group", None)          # plan 40 T2: Rename… (its side pane's name)
    g = view.group(gid) if gid else None
    if g is not None:
        ed.clear_selection()
        ed.select_node(ed.NodeId(_id(st, "n:" + (region_id(g.id) if g.open else g.id))))
        return
    nid = st.pop("select_node", None)
    got = view.node(nid) if nid else None
    if got is not None and drawn_node(st, got):
        ed.clear_selection()
        ed.select_node(ed.NodeId(_id(st, "n:" + got.id)))
        ed.navigate_to_selection(False)
        return
    name = st.get("select")
    if not name:
        return
    n = effect_node(view, name)
    if n is None:
        st.pop("select", None)
        return
    if not drawn_node(st, n):               # on its area's idle line: opened, then next frame
        st.setdefault("idle_open", set()).add(n.area)
        return
    st.pop("select", None)
    ed.clear_selection()
    ed.select_node(ed.NodeId(_id(st, "n:" + n.id)))
    ed.navigate_to_selection(False)


def beside_chip(selected: bool, width: float, beside: bool) -> str | None:
    """The head's details chip (plan 28 N7): shown only while something is
    selected and the page is narrower than `WIDE` (that wide, the details
    sit beside the canvas by themselves), labelled by what a click does."""
    if not selected or width >= WIDE:
        return None
    return "details below" if beside else "details beside"


def head_line(st: dict, view: graphview.View) -> str:
    """The head's counts: the nodes drawn (and how many sit idle, plan 28
    N9), the wires drawn last frame (a bundle is one), the cables they
    stand for, how many are live."""
    live = sum(1 for c in view.cables if not c.dormant)
    drawn = sum(1 for n in view.nodes if drawn_node(st, n))
    hide = st.get("hide", ())
    idle = sum(1 for n in view.nodes if n.idle and n.id not in hide)
    off = sum(1 for n in view.nodes if n.id in hide)
    nodes = (f"{drawn} nodes" + (f" ({idle} idle)" if idle else "")
             + (f" · {off} hidden" if off else ""))
    return (f"{nodes}  ·  {st['wires']} wires  ·  {len(view.cables)} cables"
            f"  ·  {live} live")


def _head(panel, st: dict, view: graphview.View, selected: bool = False) -> None:
    width = imgui.get_content_region_avail().x
    _deck_row(panel, st)
    if _patches_chip(panel):                # plan 40 T3: the browser
        imgui.same_line()
    any_open = bool(st["open"])
    # the canvas's two verbs, quiet (on the kit a ghost Button: no box until
    # the pointer is on it), then its two filters as one joined pair
    if ui.chip("collapse all##graph" if any_open else "expand all##graph", variant="ghost"):
        expand_all(st, view, not any_open)
    if imgui.is_item_hovered():
        ui.tooltip(ALL_TIP)
    imgui.same_line()
    if ui.chip("tidy##graph", variant="ghost"):
        st["tidy"] = True
    if imgui.is_item_hovered():
        ui.tooltip(TIDY_TIP)
    imgui.same_line()
    hit = ui.chip_group(["patched only##graph", "patch only##graph"],
                        [st["patched_only"], st["patch_only"]], [PATCHED_TIP, PATCH_ONLY_TIP])
    if hit == 0:
        st["patched_only"] = not st["patched_only"]
        st["flip"].clear()
    elif hit == 1:
        st["patch_only"] = not st["patch_only"]
    imgui.same_line()
    _backdrop_chips(panel, st)
    label = beside_chip(selected, width, st["beside"])
    if label is not None:
        imgui.same_line()
        if ui.chip(f"{label}##graph"):
            st["beside"] = not st["beside"]
        if imgui.is_item_hovered():
            ui.tooltip(BESIDE_TIP)
    _wants_chip(panel)                      # plan 40 T4: N devices missing
    _tint_chip(st)                          # plan 37 C2 (D3): last among the chips
    # the counts after the chips, cut to what is left of the line
    imgui.same_line()
    line = head_line(st, view)
    imgui.text_disabled(ui.fit_text(line, imgui.get_content_region_avail().x))
    if imgui.is_item_hovered():
        ui.tooltip(line)
    _area_chips(st)
    for want in window_wants(panel):       # plan 44 D3: a window the meta controller lacks
        imgui.text_colored(ui.WARN, want)
    if st["note"]:
        imgui.text_colored(ui.WARN, st["note"])
    elif st["said"]:                        # plan 28 N4: the last render edit
        imgui.text_disabled(st["said"])
    else:
        imgui.text_disabled(EDIT_HINT)


def panel_wants(panel) -> list:
    """Plan 40 T4: `devices.wants` of the panel's table and registry, once a
    frame — the GRAPH head, the PRESET strip and the SYSTEM lines share it
    (cached on the panel by imgui's frame count); [] with no registry or
    no router (a panel from a test)."""
    from . import devices  # (late: the GRAPH page's imports stay as they are)
    device_reg, router = getattr(panel, "devices", None), getattr(panel, "router", None)
    if device_reg is None or router is None:
        return []
    key = (imgui.get_frame_count(), id(device_reg), id(router.table))
    got = panel.__dict__.get("_wants_cache")
    if got is None or got[0] != key:
        got = panel.__dict__["_wants_cache"] = (key, devices.wants(router.table, device_reg))
    return got[1]


def window_wants(panel) -> list[str]:
    """Plan 44 D3 (row 623): the windows the loaded patch wires or cuts
    that this rig has not open (`graphview.wanted_windows` over the
    loadable patches' graph and bus cuts, less the panel's outputs), one line each —
    what OUTPUT and the GRAPH head say; [] with no loadable patches (a test's panel)."""
    loaded_patch = getattr(getattr(panel, "library", None), "loaded_patch", None)
    if loaded_patch is None:
        return []
    spec = getattr(getattr(loaded_patch, "graph", None), "spec", None)
    # (one that has a slot and nothing to show it, as an empty slot has no `missing`, wants one)
    slots = getattr(panel, "outputs", None) or ()
    have = {sl.n for sl in slots if getattr(sl, "drawn", sl.opened) or sl.missing}
    bus = getattr(loaded_patch, "bus", None)
    return [graphview.WINDOW_WANTED.format(n=n) for n in graphview.wanted_windows(spec, bus)
            if n not in have]


def _wants_chip(panel, beside: bool = True) -> None:
    """Plan 40 T4: **N devices missing** on the line after the chips before
    it, its hover one line per device the loaded patch wants and the meta controller
    lacks ("apc40 (lost): K1, K2", `devices.want_lines`); nothing when
    every wanted device is there, or with no registry (a panel from a
    test). The PRESET strip draws the same chip (ui_loadable.strip)."""
    from . import devices  # (late: the GRAPH page's imports stay as they are)
    ws = panel_wants(panel)
    text = devices.missing_chip(ws)
    if text is None:
        return
    if beside:                              # (else on a row of its own: a narrow strip)
        imgui.same_line()
    ui.chip(f"{text}##wants")
    if imgui.is_item_hovered():
        ui.tooltip("\n".join(["the patch's rows that wait for a device:",
                              *devices.want_lines(ws)]))


def panel_off_air(panel) -> bool:
    """Is the panel on the deck off air (plan 44 D5d)? False with no meta controller
    (a panel from a test)."""
    meta = getattr(panel, "meta", None)
    return meta is not None and meta.panel is not meta.on_air


def _wrap_for(width: float) -> None:
    """Beside the last item when `width` fits on the line, else on the next."""
    imgui.same_line()
    if imgui.get_content_region_avail().x < width:
        imgui.new_line()


def _deck_row(panel, st: dict) -> None:
    """The head's first line (plan 44 D5d): which `Deck` the panel is on, the same
    words as the window's title, red off air, a click for the other; then **load…**
    (a patch from the library onto the deck off air, ui_browse) and the two verbs,
    "copy on air to off air" and the crossfade, by hand and timed. Nothing with
    no meta controller (a panel from a test). A click moves the panel at the page's end
    (`_arrive`): this frame's view and selection are of the deck it is on."""
    meta = getattr(panel, "meta", None)
    if meta is None:
        return
    words = meta.words(meta.panel)
    if ui.lit_chip(f"{words}##graph.deck", panel_off_air(panel)):
        st["panel_to"] = meta.decks[1] if meta.panel is meta.decks[0] else meta.decks[0]
    if imgui.is_item_hovered():
        ui.tooltip(DECK_TIP)
    # choosing a patch to load is the meta controller's: onto the deck off air
    _wrap_for(ui.chip_w(ui_browse.LABEL))
    ui_browse.chip(panel)
    _wrap_for(ui.chip_w(COPY_LABEL))
    if ui.chip(f"{COPY_LABEL}##graph.copy"):
        copy_on_air(panel)
    if imgui.is_item_hovered():
        ui.tooltip(COPY_TIP)
    reg = panel.reg
    if "output.xfade" not in reg:           # (a test rig with no outputs hook)
        return
    _wrap_for(XFADE_MIN_W + ui.chip_w("fade") + SECONDS_W)
    room = imgui.get_content_region_avail().x - ui.chip_w("fade") - SECONDS_W
    panel._slider("output.xfade", max(XFADE_MIN_W, room - 2 * imgui.get_style().item_spacing.x))
    imgui.same_line()
    if ui.lit_chip("fade##graph.fade", meta.timed is not None):
        meta.crossfade()
    if imgui.is_item_hovered():
        ui.tooltip(FADE_TIP)
    imgui.same_line()
    panel._slider("output.xfade_s", SECONDS_W)


def _arrive(panel, st: dict) -> None:
    """The page is drawn: the panel goes to the deck its chip was clicked for."""
    to = st.pop("panel_to", None)
    if to is not None:
        panel.meta.point_panel(to)


def copy_on_air(panel) -> None:
    """The head's second verb: said in the footer, with what the deck lacked. Refused
    while the deck off air is in the picture (`bars_copy`). A look that will not land
    is said, and the panel goes on: a refused load leaves that deck as it was, and its
    step, with nothing to put back, closes empty."""
    meta, say = panel.meta, panel.library.say
    why = meta.bars_copy()
    if why is not None:
        say(warning=why)
        return
    src, dst = meta.on_air, meta.off_air
    try:
        missing = meta.copy_on_air()
    except Exception as e:  # noqa: BLE001 — a panel click must not take the frame down
        say(warning=f"not copied: {type(e).__name__}: {e}"[:160])
        return
    words = (f"copied {src.loaded_patch.current or 'the look'} from {meta.words(src)} "
             f"to {meta.words(dst)}")
    if missing:
        say(warning=f"{words}; {len(missing)} id(s) it lacks: " + ", ".join(missing[:4]))
    else:
        say(status=words)


def _tint_chip(st: dict) -> None:
    """The head's **pictures · tint cables** chip (plan 37 C2, D3): off by
    default; lit, the picture cables are tinted (`tint`)."""
    imgui.same_line()
    if ui.lit_chip(TINT_LABEL, st["tint"]):
        st["tint"] = not st["tint"]
    if imgui.is_item_hovered():
        ui.tooltip(TINT_TIP)


def tint(hue: float, strength: float) -> tuple[float, float, float]:
    """A picture cable's colour with its picture's dominant `hue` (turns)
    bled into its red (plan 37 C2, D3): red's hue moved by `TINT_SPAN` ×
    sin(2π (hue − red)) — a lean that is continuous all the way round: the
    yellow-green half leans toward orange (most at chartreuse, 90°), the
    blue-violet half toward rose (most at violet, 270°), and red and cyan,
    on the axis, not at all (so a cyan-ish moving picture never flips from
    one end to the other) — times how strongly the picture has a hue
    (`strength` over `TINT_FULL`, at most 1). Red's saturation and value
    are kept, so the cable is always a red."""
    h0, s0, v0 = colorsys.rgb_to_hsv(*RED_RGB)
    k = max(0.0, min(1.0, strength / TINT_FULL))
    lean = TINT_SPAN * math.sin(2.0 * math.pi * (hue - h0)) * k
    return colorsys.hsv_to_rgb((h0 + lean) % 1.0, s0, v0)


def cable_tints(st: dict, view: graphview.View) -> dict[str, imgui.ImVec4]:
    """This frame's tinted picture cables (cable id → colour) while the
    switch is lit: each picture cable whose maker has a hue read
    (`PreviewTextures.hue` of its source node's thumbnail). Empty while it
    is off, or with no thumbnails: every cable plain red."""
    th = st.get("thumbs")
    if not st.get("tint") or th is None or not hasattr(th, "hue"):
        return {}
    out: dict[str, imgui.ImVec4] = {}
    cables = list(view.cables) + list(st.get("throughs", {}).values())
    for c in cables:
        if c.type != graphview.IMAGE:
            continue
        hit = view.owner(c.src_port)
        pin = graphview.pin_picture(view, c.src_port)
        got = th.hue(pin or thumb_name(hit[0])) if hit is not None else None
        if got is not None:
            out[c.id] = imgui.ImVec4(*tint(*got), 1.0)
    return out


def _backdrop_chips(panel, st: dict) -> None:
    """The head's **output behind** chip and, while it is lit, its alpha."""
    if ui.lit_chip("output behind##graph", st["backdrop"]):
        st["backdrop"] = not st["backdrop"]
    if imgui.is_item_hovered():
        ui.tooltip(BACKDROP_TIP)
    if st["backdrop"]:
        imgui.same_line()
        changed, v = panel._raw_slider("graph.backdrop", st["backdrop_alpha"], 0.0, 1.0, "%.2f",
                                       BACKDROP_TIP, imgui.get_font_size() * 6)
        if changed:
            st["backdrop_alpha"] = v


def backdrop_rect(origin: tuple[float, float], avail: tuple[float, float],
                  pic: tuple[int, int]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Where output 1's picture `pic` (w, h) lies on the page's canvas at
    `origin`, `avail` big: fitted whole and centred (letterboxed) —
    (top-left, bottom-right), screen pixels."""
    aw, ah = max(avail[0], 1.0), max(avail[1], 1.0)
    pw, ph = max(pic[0], 1), max(pic[1], 1)
    k = min(aw / pw, ah / ph)
    w, h = pw * k, ph * k
    x, y = origin[0] + (aw - w) / 2, origin[1] + (ah - h) / 2
    return (x, y), (x + w, y + h)


def _backdrop(panel, st: dict, origin, avail) -> bool:
    """Output 1 behind the canvas this frame (and asked for again next
    frame): drawn on the page's own draw list before the editor opens, so
    the editor's ground — faded by `_canvas` — and every node lie over it.
    True when it was drawn."""
    pv = getattr(panel, "preview", None)
    # off air it is always behind the canvas: nothing else draws that deck
    if not (st["backdrop"] or panel_off_air(panel)) or pv is None:
        return False
    pv.want()
    tex = pv.tex
    if tex is None or getattr(tex, "glo", 0) == 0:
        return False
    a, b = backdrop_rect(origin, avail, tuple(tex.size))
    # GL's rows: bottom first, so the picture is drawn upside down in v
    imgui.get_window_draw_list().add_image(imgui.ImTextureRef(tex.glo), imgui.ImVec2(*a),
                                           imgui.ImVec2(*b), imgui.ImVec2(0, 1), imgui.ImVec2(1, 0))
    return True


def monitor_rect(origin: tuple[float, float], avail: tuple[float, float],
                 pic: tuple[int, int]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Where the on-air inset lies: `MONITOR_W` of the
    canvas's width at its top-right corner, a margin in, the picture's
    aspect kept — and no taller than `avail`'s height leaves, a margin in
    (plan 49: on a narrow page `avail` stops above the side pane's band),
    narrowed to keep the aspect — (top-left, bottom-right), screen pixels."""
    pad = 8.0
    aspect = max(pic[1], 1) / max(pic[0], 1)
    w = max(avail[0] * MONITOR_W, 32.0)
    w = max(min(w, (avail[1] - 2 * pad) / aspect), 1.0)
    h = w * aspect
    x, y = origin[0] + avail[0] - w - pad, origin[1] + pad
    return (x, y), (x + w, y + h)


def _monitor(panel, origin, avail) -> None:
    """While the panel is on the deck off air (plan 44 D5d, DQ7): a red frame round
    the canvas, and what is on air in its corner — over the nodes, framed red — and
    asked for again next frame. On the page's list, clipped to the canvas, so a popup
    or a tooltip lies over them; `replay` cuts them out (`panel:graph` is no place
    for either)."""
    mon = getattr(panel, "monitor", None)
    if not panel_off_air(panel):
        return
    dl = imgui.get_window_draw_list()
    edge = OFF_AIR_FRAME / 2
    dl.push_clip_rect(imgui.ImVec2(*origin),
                      imgui.ImVec2(origin[0] + avail[0], origin[1] + avail[1]), True)
    try:
        dl.add_rect(imgui.ImVec2(origin[0] + edge, origin[1] + edge),
                    imgui.ImVec2(origin[0] + avail[0] - edge, origin[1] + avail[1] - edge),
                    imgui.get_color_u32(ui.RED), 0.0, OFF_AIR_FRAME)
        if mon is not None:
            _inset(mon, dl, origin, avail, panel.meta.deck_name(panel.meta.on_air))
    finally:
        dl.pop_clip_rect()


def _inset(mon, dl, origin, avail, deck: str) -> None:
    """What is on air, in the canvas's corner, and which `Deck` that is."""
    mon.want()
    tex = mon.tex
    if tex is None or getattr(tex, "glo", 0) == 0:
        return
    a, b = monitor_rect(origin, avail, tuple(tex.size))
    dl.add_image(imgui.ImTextureRef(tex.glo), imgui.ImVec2(*a), imgui.ImVec2(*b),
                 imgui.ImVec2(0, 1), imgui.ImVec2(1, 0))
    dl.add_rect(imgui.ImVec2(*a), imgui.ImVec2(*b), imgui.get_color_u32(ui.RED), 0.0, 2.0)
    dl.add_text(imgui.ImVec2(a[0] + 4, a[1] + 2), imgui.get_color_u32(ui.RED), f"ON AIR · {deck}")
    m = imgui.get_mouse_pos()
    if a[0] <= m.x < b[0] and a[1] <= m.y < b[1]:
        ui.tooltip(MONITOR_TIP)


def _area_chips(st: dict) -> None:
    """The head's area chips (review round 1): CONTROLLERS · AUDIO ·
    MODULATION · MEDIA · SCENE · LOOK-BACK · EFFECTS · OUTPUTS (plan 35 G),
    wrapped to the page; a click frames
    the canvas on that area (`frame_area`, next frame)."""
    if ui_kit.ready():
        # on the kit one segmented bar — the areas joined, a line of them at a
        # time where the page wraps them — rather than eight loose buttons
        areas, labels = list(graphview.AREAS), [f"{graphview.TITLES[a]}##area" for a in graphview.AREAS]
        while areas:
            room, n = imgui.get_content_region_avail().x, 0
            while n < len(areas) and ui.chip_w(*labels[:n + 1]) - imgui.get_style().item_spacing.x * n <= room:
                n += 1
            n = max(n, 1)
            hit = ui.chip_group(labels[:n], None, [AREA_TIP] * n)
            if hit is not None:
                st["frame_area"] = areas[hit]
            areas, labels = areas[n:], labels[n:]
        return
    for i, a in enumerate(graphview.AREAS):
        label = f"{graphview.TITLES[a]}##area"
        if i:
            imgui.same_line()
            if imgui.get_content_region_avail().x < ui.chip_w(label):
                imgui.new_line()
        if ui.chip(label):
            st["frame_area"] = a
        if imgui.is_item_hovered():
            ui.tooltip(AREA_TIP)


def _place(panel, st: dict, view: graphview.View) -> None:
    """Every node where it belongs this frame: the loadable patch's or the show's
    position, else where it already sits on the canvas, else its place in
    its area (`areas_of`) — and each area's idle line; set on the canvas
    only when that differs from what was last set, so a node being dragged
    is left alone. The layout never moves a node that is on the canvas: a
    node dragged away leaves its spot empty (2026-10-26: no layout runs on
    its own) — only a new loadable patch, or the head's **tidy** (`tidy`, which
    collapses every node and forgets the positions in both maps), lays
    them out."""
    if st["tidy"]:
        st["tidy"] = False
        tidy(panel, st, view)
    pre, show = _layouts(panel)
    if st.get("layout_of") != id(pre):        # another preset: its own layout
        st["layout_of"] = id(pre)
        st["sat"] = {}
    sat = st.setdefault("sat", {})
    px, py = panned(st)                        # the canvas as the fingers moved it (whole units)
    stored = {**(show or {}), **(pre or {})}
    k = (id(view), frozenset(st["open"]), frozenset(st["flip"]), st["patched_only"],
         frozenset(st["folds"]), frozenset(st["idle_open"]),
         tuple(sorted((n, tuple(xy)) for n, xy in stored.items())))
    held = st.get("auto")
    if held is None or held[0] != k:          # the areas, kept while nothing moves them
        held = st["auto"] = (k, areas_of(st, view, stored))
    lay = held[1]
    auto = lay.nodes
    applied = st["applied"]
    px, py = panned(st)                        # the canvas as the fingers moved it
    for n in view.nodes:
        if not drawn_node(st, n):              # N9: an idle node is not on the canvas
            continue
        xy = stored.get(n.id) or sat.get(n.id) or auto.get(n.id) or (0.0, 0.0)
        sat.setdefault(n.id, (float(xy[0]), float(xy[1])))
        target = (float(xy[0]) + px, float(xy[1]) + py)
        if applied.get(n.id) != target:
            ed.set_node_position(ed.NodeId(_id(st, "n:" + n.id)), imgui.ImVec2(*target))
            applied[n.id] = target
    _place_groups(panel, st, view, applied, px, py)     # plan 40 T2
    for area, xy in lay.lines.items():        # plan 28 N9: each area's idle line
        lid = graphview.idle_id(area)
        target = (float(xy[0]) + px, float(xy[1]) + py)
        if applied.get(lid) != target:
            ed.set_node_position(ed.NodeId(_id(st, "n:" + lid)), imgui.ImVec2(*target))
            applied[lid] = target


def _moved(panel, st: dict, view: graphview.View) -> None:
    """A node dropped somewhere new is saved where it lives (the loadable patch's
    map or the show's, `graphview.home`) — once the mouse lets go."""
    if imgui.is_mouse_down(imgui.MouseButton_.left):
        return
    pre, show = _layouts(panel)
    applied = st["applied"]
    carried = _moved_groups(panel, st, view, applied)    # plan 40 T2: a group's drop first
    moves = []
    for n in view.nodes:
        if not drawn_node(st, n) or n.id in carried:   # plan 28 N9: an idle node is not drawn
            continue
        p = ed.get_node_position(ed.NodeId(_id(st, "n:" + n.id)))
        now = (float(round(p.x)), float(round(p.y)))
        was = applied.get(n.id)
        if was is None or (round(was[0]), round(was[1])) == now:
            continue
        moves.append((n, now))
    # plan 40 T2: ungroup one — every member dropped outside its region (the
    # regions as they were before this drop) leaves in one undo step
    left = {n.id: out for n, now in moves
            if (out := _left_group(st, view, n, now, applied)) is not None}
    if left:
        leave_groups(panel, list(left.values()))
    for n, now in moves:
        applied[n.id] = now
        # (plan 36 T5: a node the loadable patch's map already places — a new
        # loadable patch's All outputs — moves there, or that entry would hold it;
        # a leaver was placed by `leave_groups`)
        m = pre if graphview.home(n) == graphview.PATCH_SECTION or (pre and n.id in pre) else show
        if m is not None and n.id not in left:
            px, py = panned(st)                 # saved in layout units, not panned ones
            m[n.id] = [round(now[0] - px), round(now[1] - py)]
        # (plan 33 U: an effect too; 2026-11-01: any picture node; 2026-10-29:
        # the node the mouse went down on, let go alone, as the drag lit it
        # — several selected nodes moved together only move; a member that
        # left its group by this drop is spliced too, a second step)
        press = st.get("press")
        if (press is not None and press[0] == n.id and not _with_others(st, n.id)
                and (n.kind == "modifier" or n.kind in graphview.FRAME_VKINDS)):
            plan = st.get("press_plan")
            if plan is not None and plan.get("node") == n.id:
                drop_plan(panel, view, plan)    # what the glow showed, exactly
            else:
                size = ed.get_node_size(ed.NodeId(_id(st, "n:" + n.id)))
                dropped(panel, view, n.id, (now[0] + size.x / 2, now[1] + size.y / 2),
                        (size.x, size.y), lift_held(), zoom=st.get("zoom", 1.0))
    st["press"] = None
    st["press_plan"] = None


def _canvas(panel, st: dict, view: graphview.View, size: imgui.ImVec2,
            through: float = 0.0) -> None:
    """The editor, its ground faded to 1 − `through` over the backdrop."""
    view_file = start_view(panel.graph_start_zoom) if st["editor"] is None else ""
    if st["editor"] is None and getattr(panel, "graph_fit", True):
        ask_fit(st, instant=True)       # the canvas opens with every node in view
    ed.set_current_editor(editor(panel, view_file))
    keep_corner(st, (size.x, size.y))
    try:
        if through > 0.0:
            bg = ed.get_style().color_(ed.StyleColor.bg)
            ed.push_style_color(ed.StyleColor.bg, imgui.ImVec4(bg.x, bg.y, bg.z, bg.w * (1.0 - through)))
        corner = imgui.get_cursor_screen_pos()
        ed.begin("##graph", size)
    finally:        # whatever happens, the editor never holds a file a later frame could save into
        if view_file:
            _start_view_read(st["editor"], view_file)
    # plan 36 T5: the canvas point at the view's top-left corner, kept for
    # what a new loadable patch lays out where you are looking (`in_view`)
    seen = ed.screen_to_canvas(corner)
    st["seen"] = (float(seen.x), float(seen.y))
    st["zoom"] = ed.get_current_zoom() or 1.0   # canvas units a screen px, for the pins' hit rects
    # plan 37 C1: the canvas rect on screen this frame (what a thumbnail
    # is wanted for), and where the thumbnails come from
    far = ed.screen_to_canvas(imgui.ImVec2(corner.x + size.x, corner.y + size.y))
    st["seen_rect"] = (st["seen"], (float(far.x), float(far.y)))
    # (plan 37 C2: the SYSTEM page's GPU medians, for a thumbnail's hover;
    # all three from the renderer the canvas reads: `picture_sources`)
    st["thumbs"], st["preview"], st["gpu_ms"] = picture_sources(panel)
    st["thumb_hover"] = None
    imgui.push_font(None, ui.FONT_BASE * graphview.SCALE)    # the canvas's own text size
    density = imgui.internal.get_font_rasterizer_density()
    imgui.internal.set_font_rasterizer_density(held_density(st, canvas_density(density, st["zoom"])))
    _place(panel, st, view)
    lay = st["auto"][1]
    _titles(st, lay)                    # plan 28 N9: behind the nodes
    st["regions"] = {}
    for g in view.groups:               # plan 40 T2: an open group's region, under its nodes
        if g.open:
            _region(st, g)
    st["errors"] = effect_errors(panel, view)
    drawn: set[str] = set()
    # 2026-11-01: a pin's place is this frame's or nothing — a pin not drawn
    # (a collapsed node's port) is never a drop target 300 units off the wire
    st["pin_xy"] = {}
    for n in view.nodes:
        if drawn_node(st, n):
            _node(st, n, drawn)
    for g in view.groups:               # plan 40 T2: a folded group's node, an open one's title
        if g.open:
            _region_title(panel, st, g)
        else:
            _group_node(panel, st, view, g, drawn)
    _want_thumbs(st, view)              # plan 37 C1: after the nodes, their sizes known
    if st["thumbs"] is not None and hasattr(st["thumbs"], "want_hues"):
        # plan 37 C2: the hues while the switch is lit, none from the frame it goes off
        if st["tint"]:
            st["thumbs"].want_hues()
        else:
            st["thumbs"].stop_hues()
    _select(st, view)                   # plan 33 U: the FX page's selection, here too
    for area in lay.lines:
        ids = lay.idle.get(area, [])
        if ids and all(i in st["hide"] for i in ids):    # plan 36 T6: nothing there to say
            continue
        _idle_line(st, view, area, ids)
    _drop_target(panel, st, view)       # plan 40 T3: a dragged patch's cable, lit below
    _drag_preview(panel, st, view)      # 2026-10-29: a dragged node's cable, lit below
    # plan 28 N7: one wire per node pair while either end is collapsed
    singles, bundles = _wiring(st, view)
    st["tints"] = cable_tints(st, view)     # plan 37 C2: the through wires known
    wires = 0
    for c, a, b in singles:
        if a in drawn and b in drawn:
            _cable(st, c, a, b)
            wires += 1
    st["bundles"] = {}
    for b in bundles:
        if b.src_port in drawn and b.dst_port in drawn:
            _bundle(st, b)
            st["bundles"][b.id] = b
            wires += 1
    st["wires"] = wires
    held = ui_routing._state(panel).pop("reveal", None)     # "Route a lane here…"
    if held is not None:
        reveal(st, view, held)
    _fit_when_asked(panel, st, view, lay, size)    # open, a load, a tidy: every node in view
    area = st.pop("frame_area", None)   # N9: an area chip or a title clicked
    if area is not None:
        frame_area(st, view, area)
    _title_click(st)
    _create(panel, st, view)
    _delete_key()
    _delete(panel, st, view)
    _menus(panel, st, view)
    _hover(st, view, panel)
    _moved(panel, st, view)
    _patch_drop(panel, st, view)        # plan 40 T3: let go on a lit cable: splice
    imgui.internal.set_font_rasterizer_density(density)
    imgui.pop_font()
    ed.end()
    if through > 0.0:
        ed.pop_style_color()


def effect_errors(panel, view: graphview.View) -> dict[str, str]:
    """Plan 33 U: each effect node whose file did not compile, by node id →
    the error (`ui_fx`'s words): its title is drawn in the error colour and
    its hover says it."""
    chain = getattr(getattr(panel, "renderer", None), "fx", None)
    fx = getattr(chain, "state", None)
    if fx is None:
        return {}
    out = {}
    for n in view.nodes:
        if isinstance(n.ref, Effect) and n.ref.effect in fx.specs:
            try:
                err = ui_fx._error(chain, fx, n.ref.effect)
            except Exception:  # noqa: BLE001 — a chain that cannot say draws no error
                err = ""
            if err:
                out[n.id] = err
    return out


def titles(lay: graphview.Layout) -> list[tuple[str, float, float]]:
    """The areas' titles to draw (plan 28 N9): (words, x, y) in canvas units,
    over each area's first column, in `graphview.ORDER`."""
    return [(graphview.TITLES.get(a, a.upper()), *lay.titles[a])
            for a in graphview.ORDER if a in lay.titles]


def title_room(lay: graphview.Layout, area: str) -> float:
    """How wide area `area`'s title may be, in canvas units: to the next
    title on its row (less `TITLE_GAP`), else its own columns."""
    x, y = lay.titles[area]
    nxt = [tx for a, (tx, ty) in lay.titles.items() if a != area and ty == y and tx > x]
    if nxt:
        return min(nxt) - x - TITLE_GAP
    return lay.spans.get(area, 1) * graphview.COL_W - (graphview.COL_W - NODE_W)


def title_fit(words: str, short: str, room: float, zoom: float, em: float,
              per_em: float, per_em_short: float) -> tuple[str, float]:
    """An area title's words and size in canvas units (review round 1):
    `TITLE_SIZE`, larger while the canvas is zoomed out so it stays
    `TITLE_SCREEN` px on screen, held to its `room` — and never under
    `TITLE_FLOOR` px on screen: when the word will not fit at that, its
    short form (CTRL, MOD …), at the floor if even that will not.
    `zoom` is the editor's (canvas units a screen pixel: 4 is zoomed out
    four times); `per_em` / `per_em_short` the words' widths at the font's
    size `em`."""
    want = max(TITLE_SIZE, TITLE_SCREEN * zoom)
    floor = TITLE_FLOOR * zoom
    for text, w in ((words, per_em), (short, per_em_short)):
        fits = room * em / w if w > 0 else want
        if fits >= floor:
            return text, min(want, fits)
    return short, floor


def _titles(st: dict, lay: graphview.Layout) -> None:
    """Each area's title, faint and large, on the canvas's own draw list
    (canvas units inside the editor), its foot on the title row's — drawn
    before the nodes, so behind them, and no node of its own (nothing to
    select or drag; a click on it frames its area: `_title_click`)."""
    dl = imgui.get_window_draw_list()
    k = ui.TEXT
    col = ui.u32(imgui.ImVec4(k.x, k.y, k.z, TITLE_ALPHA))
    font, em = imgui.get_font(), imgui.get_font_size()
    zoom = ed.get_current_zoom() or 1.0
    foot = graphview.TITLE_H - 12.0
    rects = st["title_rects"] = {}
    px, py = panned(st)
    for (words, x, y), area in zip(titles(lay), (a for a in graphview.ORDER
                                                 if a in lay.titles), strict=True):
        x, y = x + px, y + py
        short = graphview.SHORT_TITLES.get(area, words)
        text, size = title_fit(words, short, title_room(lay, area), zoom, em,
                               imgui.calc_text_size(words).x, imgui.calc_text_size(short).x)
        wide = imgui.calc_text_size(text).x * size / em
        dl.add_text(font, size, imgui.ImVec2(x, y + foot - size), col, text)
        dl.add_line(imgui.ImVec2(x, y + foot + 2.0), imgui.ImVec2(x + NODE_W, y + foot + 2.0),
                    col, 1.0)
        rects[area] = (x, y + foot - size, x + max(wide, NODE_W), y + foot + 2.0)


def _title_click(st: dict) -> None:
    """A click on the canvas's background inside an area's title frames
    that area (next frame, `frame_area`)."""
    if not ed.is_background_clicked():
        return
    m = imgui.get_mouse_pos()                  # canvas units, inside the editor
    for area, (x0, y0, x1, y1) in st.get("title_rects", {}).items():
        if x0 <= m.x <= x1 and y0 <= m.y <= y1:
            st["frame_area"] = area


def area_nodes(st: dict, view: graphview.View, area: str) -> list[str]:
    """The canvas ids an area's framing selects: its drawn nodes and its
    idle line (the head's area chips, a click on its title)."""
    ids = [n.id for n in view.nodes if n.area == area and drawn_node(st, n)]
    lay = st.get("auto")
    if lay and area in lay[1].lines:
        ids.append(graphview.idle_id(area))
    return ids


def frame_area(st: dict, view: graphview.View, area: str) -> list[str]:
    """Frame the canvas on area `area` (review round 1: how "at a glance"
    holds on a page 390 px wide): its nodes selected, the view brought to
    them, the selection cleared again. Inside the editor. Returns the ids."""
    ids = area_nodes(st, view, area)
    if not ids:
        return ids
    ed.clear_selection()
    for nid in ids:
        ed.select_node(ed.NodeId(_id(st, "n:" + nid)), True)
    ed.navigate_to_selection(True)
    ed.clear_selection()
    return ids


def idle_line(view: graphview.View, ids) -> str:
    """An area's idle line's words: its idle nodes by kind."""
    held = set(ids)
    return graphview.idle_words(n for n in view.nodes if n.id in held)


def _idle_line(st: dict, view: graphview.View, area: str, ids) -> None:
    """An area's idle line (plan 28 N9): one small node standing for the
    nodes with nothing in and nothing out, its **+** drawing them under it
    (its **-** taking them off again)."""
    lid = graphview.idle_id(area)
    ed.begin_node(ed.NodeId(_id(st, "n:" + lid)))
    imgui.push_id(lid)
    opened = area in st["idle_open"]
    imgui.text_disabled(ui.fit_text(idle_line(view, ids), NODE_W - 30))
    imgui.same_line(NODE_W - 30 - PIN)
    if ui.small_button("-" if opened else "+"):
        toggle_idle(st, area)
    if imgui.is_item_hovered():
        ed.suspend()
        ui.tooltip(IDLE_TIP)
        ed.resume()
    imgui.dummy(imgui.ImVec2(NODE_W, 0))
    imgui.pop_id()
    ed.end_node()


def _fit_on_a_load(panel, st: dict) -> None:
    """Another loadable patch on the canvas — its name and its graph both
    new within `FIT_TOGETHER` frames (a load, a new, the other deck's), not
    a save as (the name alone) nor an edit (the graph alone) — asks for
    every node in view."""
    lp = getattr(getattr(panel, "library", None), "loaded_patch", None)
    name = (id(lp), (getattr(lp, "landing", None) or (None,))[0])
    spec = getattr(getattr(lp, "graph", None), "spec", None)
    now = imgui.get_frame_count()
    seen = st.get("fit_seen")
    st["fit_seen"] = (name, spec)
    if seen is None:
        return
    moved = st.setdefault("fit_moved", {})
    if seen[0] != name:
        moved["name"] = now
    if seen[1] is not spec:
        moved["spec"] = now
    if len(moved) == 2:
        if abs(moved["name"] - moved["spec"]) <= FIT_TOGETHER and getattr(panel, "graph_fit", True):
            ask_fit(st)
        moved.clear()
    elif moved and now - next(iter(moved.values())) > FIT_TOGETHER:
        moved.clear()


def ask_fit(st: dict, instant: bool = False) -> None:
    """Ask the canvas to bring every node into view, centred in what the
    pane leaves of it (`_fit_when_asked`), `FIT_WAIT` frames on: a new
    loadable patch's nodes are placed on its first frame and measured on
    the next. `instant`: no glide (the launch)."""
    st["fit"] = {"wait": FIT_WAIT, "tries": FIT_TRIES, "instant": instant}


def fit_box(content: tuple[float, float, float, float], canvas: tuple[float, float],
            pane: tuple[str, float], most_zoom: float) -> tuple[float, float, float, float]:
    """The canvas box (x0, y0, x1, y1, canvas units) the editor is to frame
    so `content` sits centred in the part of the canvas the pane leaves —
    `pane` is ("beside", its width) or ("below", its height), in screen px —
    never larger on screen than `most_zoom` px a unit. The box has the
    canvas's own aspect, so the editor's fit maps it onto the canvas
    whole: the content's box grown to the visible part's aspect (and to
    that part's size at `most_zoom`), then out under the pane. Pure."""
    x0, y0, x1, y1 = content
    cw, ch = max(canvas[0], 1.0), max(canvas[1], 1.0)
    side, cut = pane
    vw, vh = (max(cw - cut, 1.0), ch) if side == "beside" else (cw, max(ch - cut, 1.0))
    w, h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    z = max(most_zoom, 1e-3)
    w, h = max(w, vw / z), max(h, vh / z)
    if w / h > vw / vh:                 # wider than the visible part: taller
        h = w * vh / vw
    else:
        w = h * vw / vh
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    bx0, by0 = mx - w / 2, my - h / 2
    if side == "beside":
        return (bx0, by0, bx0 + w * cw / vw, by0 + h)
    return (bx0, by0, bx0 + w, by0 + h * ch / vh)


def _content_ids(st: dict, view: graphview.View, lay) -> list[str]:
    """The editor names of what the canvas draws: its nodes, its groups
    (folded, or an open one's title) and the idle lines it shows."""
    names = ["n:" + n.id for n in view.nodes if drawn_node(st, n)]
    names += ["n:" + (region_id(g.id) if g.open else g.id) for g in view.groups]
    names += ["n:" + graphview.idle_id(a) for a in lay.lines
              if not all(i in st["hide"] for i in lay.idle.get(a, []))]
    return names


def _fit_when_asked(panel, st: dict, view: graphview.View, lay, size: imgui.ImVec2) -> None:
    """Inside the editor, after the nodes: what `ask_fit` asked, once its
    wait is out and every node is measured (else again next frame, up to
    `FIT_TRIES`, then on those measured). The binding has no zoom setter, so the box `fit_box` says
    is marked by two invisible corner nodes, selected with the content and
    framed (`navigate_to_selection`, zooming in as well as out); the
    selection — nodes and cables — is then put back as it was."""
    ask = st.get("fit")
    if not ask:
        return
    if ask["wait"] > 0:
        ask["wait"] -= 1
        return
    ids = [ed.NodeId(_id(st, k)) for k in _content_ids(st, view, lay)]
    every = [(ed.get_node_position(k), ed.get_node_size(k)) for k in ids]
    boxes = [(p, z) for p, z in every if z.x > 0 and z.y > 0]
    if len(boxes) < len(every) or not boxes:    # a node not measured yet: next frame
        ask["tries"] -= 1
        if ask["tries"] > 0 or not boxes:
            if ask["tries"] <= 0:
                st.pop("fit", None)
            return
    st.pop("fit", None)
    content = (min(p.x for p, _ in boxes), min(p.y for p, _ in boxes),
               max(p.x + z.x for p, z in boxes), max(p.y + z.y for p, z in boxes))
    (_x, _y), (pw, ph) = st.get("details_rect") or ((0.0, 0.0), (0.0, 0.0))
    pane = ("beside", pw) if ph >= size.y - 1 else ("below", ph)
    box = fit_box(content, (size.x, size.y), pane,
                  float(getattr(panel, "graph_start_zoom", 1.0) or 1.0))
    held = list(ed.get_selected_nodes())           # (clear_selection takes the cables too)
    held_links = list(ed.get_selected_links())
    clear = imgui.ImVec4(0, 0, 0, 0)
    ed.push_style_color(ed.StyleColor.node_bg, clear)
    ed.push_style_color(ed.StyleColor.node_border, clear)
    ed.push_style_var(ed.StyleVar.node_padding, imgui.ImVec4(0, 0, 0, 0))
    corners = []
    for key, (x, y) in ((FIT_A, (box[0], box[1])), (FIT_B, (box[2] - 1.0, box[3] - 1.0))):
        k = ed.NodeId(_id(st, key))
        ed.set_node_position(k, imgui.ImVec2(x, y))
        ed.begin_node(k)
        imgui.dummy(imgui.ImVec2(1, 1))
        ed.end_node()
        corners.append(k)
    ed.pop_style_var()
    ed.pop_style_color(2)
    ed.clear_selection()
    for k in ids + corners:
        ed.select_node(k, True)
    ed.navigate_to_selection(True, 0.0 if ask["instant"] else -1.0)
    ed.clear_selection()
    for k in held:
        ed.select_node(k, True)
    for k in held_links:
        ed.select_link(k, True)


def pin_hit_size(zoom: float, row_h: float, pitch: float, min_px: float = MIN_PX,
                 pin: float = PIN) -> tuple[float, float]:
    """A pin's hit rect (width, height) in canvas units: its drawn square
    `pin`, grown so it is never under `min_px` on screen while the canvas
    is zoomed out (`zoom`: canvas units a screen pixel, as `title_fit`
    takes it), and held to `pitch` across (the pins beside it, or a
    stub's reach) and `row_h` down (its row) — never under `pin` even
    when those are."""
    want = max(pin, min_px * zoom)
    return max(pin, min(want, pitch)), max(pin, min(want, row_h))


def _pin(st: dict, pin: str, kind, port: graphview.VPort, stub: str, drawn: set[str],
         room: tuple[float, float] = (PIN, graphview.ROW_H), grow: int = CENTRED) -> None:
    """One pin: a `PIN` square drawn, its hit rect `pin_hit_size` within
    `room` (across, down) — centred on the square, or (`grow`) out from
    its left or right edge, a stub's way past the node's edge where
    nothing competes; cables attach to the square as they did."""
    ed.begin_pin(ed.PinId(_id(st, pin)), kind)
    p0 = imgui.get_cursor_screen_pos()
    imgui.dummy(imgui.ImVec2(PIN, PIN))
    w, h = pin_hit_size(st.get("zoom", 1.0), room[1], room[0])
    hx = p0.x + PIN - w if grow == GROW_LEFT else p0.x if grow == GROW_RIGHT else p0.x - (w - PIN) / 2
    hy = p0.y - (h - PIN) / 2
    ed.pin_rect(imgui.ImVec2(hx, hy), imgui.ImVec2(hx + w, hy + h))
    ed.pin_pivot_rect(p0, imgui.ImVec2(p0.x + PIN, p0.y + PIN))
    dl = imgui.get_window_draw_list()
    col = ui.u32(COLOURS.get(port.type, ui.DIM) if port.patched else ui.DIM)
    p1 = imgui.ImVec2(p0.x + PIN, p0.y + PIN)
    if stub == graphview.BASE:           # base: a square (many setters, last touch wins)
        dl.add_rect(p0, p1, col, 0.0, 1.5)
    elif stub == graphview.DEPTH:        # depth: a diamond
        cx, cy = p0.x + PIN / 2, p0.y + PIN / 2
        dl.add_quad(imgui.ImVec2(cx, p0.y), imgui.ImVec2(p1.x, cy), imgui.ImVec2(cx, p1.y),
                    imgui.ImVec2(p0.x, cy), col, 1.5)
    else:                                # mod, a source, a render port: a disc
        c = imgui.ImVec2(p0.x + PIN / 2, p0.y + PIN / 2)
        if port.patched:
            dl.add_circle_filled(c, PIN / 2, col)
        else:
            dl.add_circle(c, PIN / 2, col, 0, 1.5)
    ed.end_pin()
    drawn.add(pin)
    st["pin_xy"][pin] = (p0.x + PIN / 2, p0.y + PIN / 2)     # canvas units, inside the editor


def _wiring(st: dict, view: graphview.View):
    """`graphview.wiring` for this frame, kept while the view and the
    expanded nodes hold (only the bundles' readings move each frame)."""
    lay = st["auto"][1] if st.get("auto") else areas_of(st, view)
    k = (id(view), frozenset(st["open"]), frozenset(st["idle_open"]), id(lay))
    held = st.get("wiring")
    if held is None or held[0] != k:
        st["throughs"] = {c.id: c for c in lay.throughs}
        held = st["wiring"] = (k, graphview.wiring(
            view, lambda nid: collapsed(st, nid), lambda c: drawn_cable(st, c),
            lambda nid: _drawn_id(st, view, nid), lay.throughs,
            folded=graphview.folded(view)))     # plan 40 T2 (D4)
    else:
        graphview.readings(held[1][1])
    return held[1]


def wire_of(st: dict, view: graphview.View, b) -> str | None:
    """The drawn wire a row's cable is this frame: its bundle's id, or its
    own cable's id; None while it is not drawn."""
    c = next((x for x in view.cables if x.ref is b), None)
    if c is None:
        return None
    bundle = next((x for x in st["bundles"].values() if any(y is c for y in x.cables)), None)
    return bundle.id if bundle is not None else c.id


def reveal(st: dict, view: graphview.View, b) -> str | None:
    """A route just made elsewhere ("Route a lane here…", plan 28 N7):
    select the wire it is drawn in — its bundle, or its own cable — and
    bring it on screen; the side pane lists its row first (`st["focus"]`).
    Returns the wire's id, or None (not drawn)."""
    wid = wire_of(st, view, b)
    if wid is None:
        return None
    ed.clear_selection()
    ed.select_link(ed.LinkId(_id(st, "c:" + wid)))
    ed.navigate_to_selection(False)
    st["focus"] = b
    return wid


def _stub(st: dict, pin: str, kind, lit: bool, drawn: set[str]) -> None:
    """A node's single in or out stub (plan 28 N7): where its bundles and
    its collapsed render cables end, and where a drag lands to pick a port.
    Its hit grows outward, past the node's edge (an in stub left, an out
    stub right: the label and the + button keep their room), and down to
    the title line."""
    _pin(st, pin, kind, graphview.VPort(pin, "", "", patched=lit), "", drawn,
         room=(STUB_REACH, graphview.HEAD_H),
         grow=GROW_LEFT if kind == ed.PinKind.input else GROW_RIGHT)


def _node(st: dict, n: graphview.VNode, drawn: set[str]) -> None:
    ed.begin_node(ed.NodeId(_id(st, "n:" + n.id)))
    imgui.push_id(n.id)
    shut = collapsed(st, n.id)
    has_in = any(p.direction == graphview.IN for p in n.ports)
    has_out = any(p.direction == graphview.OUT for p in n.ports)
    # the title line: [in stub] label [+ / -] [out stub]
    if has_in:
        _stub(st, graphview.stub_in(n.id), ed.PinKind.input, n.wires > 0, drawn)
        imgui.same_line()
    # a desk layer that is down (plan 28 N5) reads like a lost device: faint;
    # (plan 33 U) so does a node that reaches nothing; a compile error is red
    err = st.get("errors", {}).get(n.id)
    imgui.push_style_color(imgui.Col_.text, ui.WARN if err else ui.FAINT if (
        n.grey or not n.up or n.faint) else ui.TEXT)
    imgui.text(ui.fit_text(n.label, NODE_W - 40 - 2 * PIN))
    imgui.pop_style_color()
    imgui.same_line(NODE_W - 30 - PIN)          # the + clear of the out stub
    if ui.small_button("+" if shut else "-"):
        toggle_open(st, n.id)
    if imgui.is_item_hovered():
        ed.suspend()
        ui.tooltip(EXPAND_TIP if shut else COLLAPSE_TIP)
        ed.resume()
    if has_out:
        imgui.same_line(NODE_W - PIN)
        _stub(st, graphview.stub_out(n.id), ed.PinKind.output, n.wires > 0, drawn)
    if n.thumb is not None:                     # plan 37 C1 (D2): collapsed or not
        _thumb(st, n)
    if shut:                                    # its title and at most five lines
        # (a picture node's lines are its hover's: plan 37 P1)
        for line in (graphview.summary(n) if n.thumb is None else ()):
            imgui.text_disabled(ui.fit_text(line, NODE_W))
        imgui.dummy(imgui.ImVec2(NODE_W, 0))
        imgui.pop_id()
        ed.end_node()
        return
    every = full(st, n.id)
    if ui.small_button("patched only" if every else "all ports"):
        st["flip"] ^= {n.id}
    ports = shown(st, n)
    group = None
    many = graphview.grouped(n, every)
    for port in (n.ports if many else ports):
        if many and port.group != group:
            group = port.group
            folded = (n.id, group) in st["folds"]
            count = sum(1 for p in n.ports if p.group == group)
            sign = "+" if folded else "-"
            if ui.small_button(f"{sign} {group_title(group) or 'misc'} ({count})"
                                  f"##{group}"):
                st["folds"] ^= {(n.id, group)}
        if port not in ports:
            continue
        _port(st, port, drawn)
    imgui.dummy(imgui.ImVec2(NODE_W, 0))
    imgui.pop_id()
    ed.end_node()


# ---------------------------------------------------------------- plan 40 T2: groups (P2, D4)
#
# A group of the loaded patch (`graphview.VGroup`, the loadable patch's `groups`)
# is drawn as one node while it is folded (`_group_node`: its name and +,
# its picture pins, a row per boundary param with its cable, its status —
# what it waits for, P4 — and its last picture outlet's thumbnail); its
# members are left off the canvas (`hidden_ids`) and so is every cable with
# both ends inside — the one place a cable is folded away, the owner's
# (D4). Open, its members are drawn where they sit inside a tinted region
# (`_region`) whose title (`_region_title`: its name and -) drags every
# member by the same delta (one undo step); a member dragged out of the
# region leaves the group. Right-click with nodes selected → Group; a
# group's menu → Open / Fold, Rename…, Ungroup; each one undo step
# (`group_edit`: the page's `Edit` with `undo.push(label, load=True)`).

GROUP_TINT = imgui.ImVec4(0.38, 0.72, 1.0, 0.07)     # an open group's region, under its nodes
GROUP_EDGE = imgui.ImVec4(0.38, 0.72, 1.0, 0.40)
GROUP_TITLE = imgui.ImVec4(0.38, 0.72, 1.0, 0.22)    # its title bar
GROUP_BAR = graphview.ROW_H                          # the title bar's height, canvas units
REGION = "region:"                                   # an open group's title node: region:group.1
OPEN_GROUP_TIP = "Open this group in place: its nodes where they sit, every cable drawn"
FOLD_GROUP_TIP = ("Fold this group: one node, its inside cables folded away until + "
                  "(the owner's one exception to no hidden cables, D4)")
REGION_TIP = "Drag the title to move every node of the group; drag a node out to take it out"


def region_id(gid: str) -> str:
    """An open group's title node on the canvas."""
    return f"{REGION}{gid}"


def group_at(view: graphview.View, name: str):
    """The group a canvas node name stands for — a folded group's node
    (``group.1``) or an open one's title (``region:group.1``) — or None."""
    return view.group(name.removeprefix(REGION))


def group_edit(panel) -> graphview.Edit | None:
    """The page's `Edit` for the group verbs: the router's table and the
    loadable patch's graph section (`patches.select` reads both), the loaded
    `LoadedPatch` (its `groups` and `layout`), one undo step per verb pushed
    with the library's marks (`load=True`: they carry both)."""
    e = edit_of(panel)
    if e is None:
        return None
    e.push = lambda label: undo.push(label, load=True)
    e.loaded_patch = getattr(getattr(panel, "library", None), "loaded_patch", None)
    e.slots = getattr(panel, "outputs", None) or ()     # (a window's name, in the chip's words)
    return e


def _group_said(panel, e: graphview.Edit, why: str | None) -> str | None:
    st = _state(panel)
    _note(st, why)
    if why is None and e.said:
        st["said"] = e.said
    return why


def group_nodes(panel, ids) -> dict | None:
    """Group (plan 40 T2): canvas ids `ids` made one group, folded — what
    group's rule leaves out said on the head ("output.all is the rig's
    window; left out"). Returns the entry, or None."""
    e = group_edit(panel)
    if e is None:
        return None
    entry, said = e.group(ids)
    _group_said(panel, e, "; ".join(said) if said else None)
    if entry is not None:
        _state(panel)["said"] = e.said
    return entry


def ungroup(panel, gid: str) -> str | None:
    """Ungroup: the group's entry gone, every node and cable where it was."""
    e = group_edit(panel)
    return None if e is None else _group_said(panel, e, e.ungroup(gid))


def rename_group(panel, gid: str, name: str) -> str | None:
    e = group_edit(panel)
    return None if e is None else _group_said(panel, e, e.rename_group(gid, name))


def set_open(panel, gid: str, on: bool) -> str | None:
    """Open (`+`) or Fold (`-`) a group: the loadable patch's, one undo step."""
    e = group_edit(panel)
    return None if e is None else _group_said(panel, e, e.set_open(gid, on))


def move_group(panel, gid: str, delta, positions) -> str | None:
    e = group_edit(panel)
    return None if e is None else _group_said(panel, e, e.move_group(gid, delta, positions))


def leave_group(panel, gid: str, nid: str, at=None) -> str | None:
    e = group_edit(panel)
    return None if e is None else _group_said(panel, e, e.leave_group(gid, nid, at))


def leave_groups(panel, moves) -> str | None:
    """Members dropped out of their regions together — ``(group id, node
    id, at)`` each — one undo step (`Edit.leave_groups`)."""
    e = group_edit(panel)
    return None if e is None else _group_said(panel, e, e.leave_groups(moves))


def selected_ids(st: dict) -> list[str]:
    """The canvas ids of the selected nodes (a folded group's node as its
    id), in selection order — what **Group** groups. An open group's title
    is left out (plan 40 review fix): a box-select across an open region
    takes its title with its members, and the group is not what was meant
    ("group.1 is a group: … left out" was noise)."""
    if st.get("editor") is None:
        return []
    out = []
    for nk in ed.get_selected_nodes():
        name = st["names"].get(nk.id(), "")[2:]
        if name and not name.startswith(("idle:", REGION)):
            out.append(name)
    return list(dict.fromkeys(out))


def group_status(panel, view: graphview.View, g) -> str:
    """A group node's status line (plan 40 P4, T4's words): what its
    members' rows wait for — "waits for apc40 (lost): K1" — "" when every
    device is there, or with no device registry (a panel from a test).
    Once a frame per group."""
    from . import devices  # (late, as `panel_wants`)
    device_reg, router = getattr(panel, "devices", None), getattr(panel, "router", None)
    if device_reg is None or router is None:
        return ""
    key = (imgui.get_frame_count(), id(device_reg), id(router.table), id(view))
    cache = panel.__dict__.get("_group_wants")
    if cache is None or cache[0] != key:
        cache = panel.__dict__["_group_wants"] = (key, {})
    got = cache[1].get(g.id)
    if got is None:
        got = cache[1][g.id] = devices.want_words(
            devices.wants_for(router.table, device_reg, graphview.group_params(g)))
    return got


def group_tip(panel, view: graphview.View, g) -> str:
    """Hovering a group's node: its name, its nodes, its provenance, its
    boundary in words, what it waits for, and how to open it."""
    names = [m.label for m in g.members]
    more = len(names) - 6
    lines = [g.name, f"{len(names)} node{'s' if len(names) != 1 else ''}: "
             + ", ".join(names[:6]) + (f", + {more} more" if more > 0 else "")]
    if g.patch:
        lines.append(f"from patch {g.patch}")
    renames = (group_entry_of(panel, g.id) or {}).get("renames") or {}
    if renames:                             # plan 40 T3: fresh ids are said (this session)
        lines.append("spawned as " + ", ".join(f"{a} → {b}" for a, b in renames.items()))
    lines += graphview.group_words(view, g)[:graphview.TIP_ROWS]
    status = group_status(panel, view, g)
    if status:
        lines.append(status)
    lines.append("- folds it" if g.open else "+ opens it in place")
    return "\n".join(lines)


def _laid(panel, st: dict, nid: str):
    """Where node `nid` sits in layout units: the loadable patch's or the show's
    position, else where the canvas put it, else its place in its area."""
    pre, show = _layouts(panel)
    for m in (pre, show, st.get("sat"), st["auto"][1].nodes if st.get("auto") else None):
        if m and m.get(nid) is not None:
            return m[nid]
    return None


def _size(st: dict, nid: str) -> tuple[float, float]:
    sz = ed.get_node_size(ed.NodeId(_id(st, "n:" + nid)))
    return ((float(sz.x) if sz.x > 0 else NODE_W),
            (float(sz.y) if sz.y > 0 else graphview.HEAD_H))


def group_area(st: dict, g, positions) -> tuple[float, float, float, float] | None:
    """An open group's region on the canvas from its members' `positions`
    (canvas units): their rect, `graphview.GAP` round it and the title bar
    above."""
    area = graphview.region(g.rect(positions, lambda nid: _size(st, nid)))
    if area is None:
        return None
    return (area[0], area[1] - GROUP_BAR, area[2], area[3])


def _place_groups(panel, st: dict, view: graphview.View, applied: dict,
                  px: float, py: float) -> None:
    """Each group's node where it belongs this frame (`_place`): a folded
    one at its members' top-left (D4: it has no position of its own), an
    open one's title over its members' region — and, while that title is
    dragged, its members follow it on the canvas (written on the drop:
    `_moved_groups`)."""
    for g in view.groups:
        laid = {m.id: _laid(panel, st, m.id) for m in g.members}
        laid = {k: v for k, v in laid.items() if v is not None}
        if not laid:
            continue
        if g.open:
            area = group_area(st, g, laid)
            if area is None:
                continue
            nid, target = region_id(g.id), (area[0] + px, area[1] + py)
        else:
            nid = g.id
            target = (min(float(v[0]) for v in laid.values()) + px,
                      min(float(v[1]) for v in laid.values()) + py)
        k = ed.NodeId(_id(st, "n:" + nid))
        if applied.get(nid) != target:
            ed.set_node_position(k, imgui.ImVec2(*target))
            applied[nid] = target
        elif g.open and imgui.is_mouse_down(imgui.MouseButton_.left):
            p = ed.get_node_position(k)
            dx, dy = float(round(p.x)) - target[0], float(round(p.y)) - target[1]
            if dx or dy:                       # the title held and moved: the members follow
                for m in g.members:
                    a = applied.get(m.id)
                    if a is not None:
                        ed.set_node_position(ed.NodeId(_id(st, "n:" + m.id)),
                                             imgui.ImVec2(a[0] + dx, a[1] + dy))


def _moved_groups(panel, st: dict, view: graphview.View, applied: dict) -> set[str]:
    """A group's node (folded) or title (open) dropped somewhere new: every
    member moved by the same delta, in the loadable patch's layout — one undo step
    (`Edit.move_group`). Returns the members it moved (their drop is this
    one, not theirs)."""
    moved: set[str] = set()
    for g in view.groups:
        nid = region_id(g.id) if g.open else g.id
        p = ed.get_node_position(ed.NodeId(_id(st, "n:" + nid)))
        now = (float(round(p.x)), float(round(p.y)))
        was = applied.get(nid)
        if was is None or (round(was[0]), round(was[1])) == now:
            continue
        applied[nid] = now
        dx, dy = now[0] - was[0], now[1] - was[1]
        laid = {m.id: _laid(panel, st, m.id) for m in g.members}
        move_group(panel, g.id, (dx, dy), {k: v for k, v in laid.items() if v is not None})
        for m in g.members:
            a = applied.get(m.id)
            if a is not None:
                applied[m.id] = (a[0] + dx, a[1] + dy)
                moved.add(m.id)
    return moved


def _left_group(st: dict, view: graphview.View, n: graphview.VNode,
                now: tuple[float, float], applied: dict
                ) -> tuple[str, str, tuple[float, float]] | None:
    """Node `n`, an open group's member, dropped at `now` (canvas units):
    when its rect lies wholly outside the region its group had before the
    drag (`graphview.leaves`, over `applied`: where each member was), it
    leaves the group — (the group's id, its id, its new position in layout
    units) for `Edit.leave_groups`, which `_moved` calls once for every
    leaver of the drop. None when it stays."""
    g = graphview.group_of(view, n.id)
    if g is None or not g.open:
        return None
    before = {m.id: applied[m.id] for m in g.members if m.id in applied}
    w, h = _size(st, n.id)
    if not graphview.leaves(group_area(st, g, before), (now[0], now[1], now[0] + w, now[1] + h)):
        return None
    px, py = panned(st)
    return g.id, n.id, (now[0] - px, now[1] - py)


def _region(st: dict, g) -> None:
    """An open group's region (plan 40 T2): a tinted, edged rectangle round
    its members as they sit this frame, its title bar's band on top — on
    the canvas's own draw list before the nodes, so under them."""
    pos = {}
    for m in g.members:
        p = ed.get_node_position(ed.NodeId(_id(st, "n:" + m.id)))
        pos[m.id] = (float(p.x), float(p.y))
    area = group_area(st, g, pos)
    if area is None:
        return
    dl = imgui.get_window_draw_list()
    a, b = imgui.ImVec2(area[0], area[1]), imgui.ImVec2(area[2], area[3])
    dl.add_rect_filled(a, b, ui.u32(GROUP_TINT), 6.0)
    dl.add_rect_filled(a, imgui.ImVec2(area[2], area[1] + GROUP_BAR), ui.u32(GROUP_TITLE), 6.0)
    dl.add_rect(a, b, ui.u32(GROUP_EDGE), 6.0, 1.5)
    st.setdefault("regions", {})[g.id] = area


def _region_title(panel, st: dict, g) -> None:
    """An open group's title: its name and -, a node of its own with no
    ground (the region is drawn under it), as wide as the region — dragged,
    it moves every member (`_moved_groups`)."""
    area = st.get("regions", {}).get(g.id)
    width = max((area[2] - area[0]) if area else NODE_W, NODE_W) - 2 * 8.0
    clear = imgui.ImVec4(0, 0, 0, 0)
    ed.push_style_color(ed.StyleColor.node_bg, clear)
    ed.push_style_color(ed.StyleColor.node_border, clear)
    ed.begin_node(ed.NodeId(_id(st, "n:" + region_id(g.id))))
    imgui.push_id(region_id(g.id))
    imgui.text(ui.fit_text(g.name, width - 40))
    if imgui.is_item_hovered():
        ed.suspend()
        ui.tooltip(REGION_TIP)
        ed.resume()
    imgui.same_line(max(width - 24, 40))
    if ui.small_button("-"):
        set_open(panel, g.id, False)
    if imgui.is_item_hovered():
        ed.suspend()
        ui.tooltip(FOLD_GROUP_TIP)
        ed.resume()
    imgui.dummy(imgui.ImVec2(width, 0))
    imgui.pop_id()
    ed.end_node()
    ed.pop_style_color(2)


def _group_node(panel, st: dict, view: graphview.View, g, drawn: set[str]) -> None:
    """A folded group (plan 40 T2): a node like a collapsed render node —
    its stubs, its name and +, its last picture outlet's picture (plan 37),
    its status (what it waits for), then a row per boundary pin: each
    picture cable in and out, each member lane going out, each member param
    a control row or a crossing route lands on — its cable drawn into it — and
    the rows a spawn's sheet kept for the loadable patch."""
    ed.begin_node(ed.NodeId(_id(st, "n:" + g.id)))
    imgui.push_id(g.id)
    # (its stubs: where a cable no boundary pin names would end — none, by
    # `attach_groups`; kept so no cable can lose an end)
    _stub(st, graphview.stub_in(g.id), ed.PinKind.input, False, drawn)
    imgui.same_line()
    imgui.text(ui.fit_text(g.name, NODE_W - 40 - 2 * PIN))
    imgui.same_line(NODE_W - 30 - PIN)
    if ui.small_button("+"):
        set_open(panel, g.id, True)
    if imgui.is_item_hovered():
        ed.suspend()
        ui.tooltip(OPEN_GROUP_TIP)
        ed.resume()
    imgui.same_line(NODE_W - PIN)
    _stub(st, graphview.stub_out(g.id), ed.PinKind.output, False, drawn)
    n = graphview.group_picture(view, g)
    if n is not None and n.thumb is not None:   # plan 37: its last picture outlet's
        _thumb(st, n)
    k = len(g.members)
    imgui.text_disabled(ui.fit_text(f"group · {k} node{'s' if k != 1 else ''}"
                                    + (f" · from {g.patch}" if g.patch else ""), NODE_W))
    status = group_status(panel, view, g)
    if status:
        imgui.text_colored(ui.WARN, ui.fit_text(status, NODE_W))
    for port in g.ports:
        _port(st, port, drawn)
    for row in g.kept_by_host:
        imgui.text_disabled(ui.fit_text(graphview.kept_words(row), NODE_W))
    imgui.dummy(imgui.ImVec2(NODE_W, 0))
    imgui.pop_id()
    ed.end_node()


def _group_side(panel, st: dict, view: graphview.View, g) -> None:
    """A selected group's side pane (plan 40 T2): its name (Enter renames,
    one undo step), its provenance, what it waits for, its nodes as chips
    (a click opens the group and selects that node), its boundary in words,
    the rows kept for the loadable patch, and T3's chips (`_group_chips`)."""
    ui._micro("group")
    names = st.setdefault("group_names", {})
    if names.get(g.id, (None, None))[0] != g.name:
        names[g.id] = (g.name, g.name)
    imgui.set_next_item_width(imgui.get_content_region_avail().x)
    entered, text = ui.input_text("##graph.group.name", names[g.id][1],
                                     imgui.InputTextFlags_.enter_returns_true)
    names[g.id] = (g.name, text)
    if entered:
        undo.by_hand(True)              # the field's own report: row 757
        rename_group(panel, g.id, text)
    if g.patch:
        imgui.text_disabled(f"from patch {g.patch}")
    status = group_status(panel, view, g)
    if status:
        imgui.text_colored(ui.WARN, status)
    imgui.text_disabled(("open" if g.open else "folded") + " · right-click it: "
                        + ("Fold" if g.open else "Open") + ", Rename…, Ungroup")
    ui._micro("nodes")
    for i, m in enumerate(g.members):
        if i:
            imgui.same_line()
            if imgui.get_content_region_avail().x < ui.chip_w(m.label):
                imgui.new_line()
        if ui.chip(f"{m.label}##graph.group.{m.id}"):
            if not g.open:
                set_open(panel, g.id, True)
            st["select_node"] = m.id
    words = graphview.group_words(view, g)
    if words:
        ui._micro("boundary")
        for line in words:
            imgui.text_wrapped(line)
    for row in g.kept_by_host:
        imgui.text_disabled(graphview.kept_words(row))
    _group_chips(panel, g)


def _group_chips(panel, g) -> None:
    """Plan 40 T3: the group's chips on its side pane — **wire as saved**
    while a spawn's pin is open (D2: "scene → in, out → output.all", one
    press, its result drawn), **save as patch…** and, for a group spawned
    from or saved as one, **update patch** — each opening the name / note
    form (`_patch_form`)."""
    st = _state(panel)
    view = st.get("view")
    entry = group_entry_of(panel, g.id) or {}
    ports = graphview.open_ports(getattr(view, "spec", None), entry)
    if ports:
        ui._micro("open pins")
        if ui.chip("wire as saved##graph.group"):
            wire_as_saved(panel, g.id)
        if imgui.is_item_hovered():
            ui.tooltip(WIRE_AS_SAVED_TIP + "\n" + saved_words(ports))
        _take_over_chip(panel, st, g.id)
    form = st.get("patch_form")
    if form is not None and form[0] == g.id:
        _patch_form(panel, g, form)
        return
    ui._micro("patch")
    if ui.chip("save as patch…##graph.group"):
        open_patch_form(panel, g)
    if imgui.is_item_hovered():
        ui.tooltip(SAVE_PATCH_TIP)
    if g.patch:
        ui.beside(ui.chip_w("update patch##graph.group"))
        if ui.chip("update patch##graph.group"):
            open_patch_form(panel, g, update=True)
        if imgui.is_item_hovered():
            ui.tooltip(f"Write this group over patch {g.patch} (its old text to the trash)")


def take_over_plan(panel, gid: str) -> graphview.TakeOver | None:
    """The take-over chip's plan for group `gid`, or None for no chip. Read
    afresh only when the section moved: a press re-reads it and refuses a plan
    that no longer holds, so a frame need not pay for a trial read."""
    st = _state(panel)
    e = group_edit(panel)
    if e is None:
        return None
    spec = getattr(e.graph, "spec", None)
    held = st.get("take_over_plan")
    if held is not None and held[0] is spec and held[1] == gid:
        return held[2]
    plan = e.take_over_of(gid)
    st["take_over_plan"] = (spec, gid, plan)
    return plan


def take_over_lines(plan: graphview.TakeOver, width: float) -> list[str]:
    """The chip's lines at `width` pixels of text: a cut too wide breaks after
    its arrow, and what is still too wide ends in an ellipsis (the hover has
    all of it)."""
    out: list[str] = []
    for line in plan.lines:
        src, arrow, dst = line.partition(" → ")
        parts = ([f"{src} →", dst]
                 if arrow and imgui.calc_text_size(line).x > width else [line])
        out += [ui.fit_text(part, width) for part in parts]
    return out


def _take_over_chip(panel, st: dict, gid: str) -> None:
    """Wave 3 P3 (row 524): under **wire as saved**, only while its press would
    refuse a taken port this one could take: the label names what is cut. What
    the press is judged against is what the chip said as the mouse went down."""
    plan = take_over_plan(panel, gid)
    if plan is None:
        return
    width = imgui.get_content_region_avail().x - 2 * ui.CHIP_PAD.x
    # (### : the same control whatever the label says, so a press under a label
    # that moved reaches the refusal instead of doing nothing)
    hit = ui.chip("\n".join(take_over_lines(plan, width)) + "###graph.group.take_over")
    if imgui.is_item_activated():
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        st["take_over_asked"] = (plan, (lo.x, lo.y, hi.x, hi.y))
    if imgui.is_item_hovered():
        ui.tooltip(plan.tip)
    if hit:
        asked = st.pop("take_over_asked", None)
        take_over(panel, asked[0] if asked is not None else plan)


def _settle_take_over(st: dict) -> None:
    """After the pane each frame: a held take-over chip whose mouse came up with
    no press of it. Over where it was, the chip is no longer there to press (a
    load took its group, or the port came free): refused in words, as any press
    that no longer holds. Anywhere else the person let go of it: nothing."""
    held = st.get("take_over_asked")
    if held is None or imgui.is_mouse_down(0):
        return
    del st["take_over_asked"]
    plan, (x0, y0, x1, y1) = held
    m = imgui.get_mouse_pos()
    if x0 <= m.x <= x1 and y0 <= m.y <= y1:
        st["note"] = graphview.TAKE_OVER_STALE.format(name=plan.name)
        st["said"] = ""


# ---------------------------------------------------------------- plan 40 T3: patches
#
# A group becomes a file (save as patch: `patches.lift` over the loaded
# parts, `Library.save_patch` — that file and nothing else) and a file
# becomes a group in any loadable patch (spawn: `patches.spawn` over a `Host` of
# the live parts, then — when its control rows collide with the loadable patch's —
# the conflict sheet, `ui_routing`'s modal, else straight on — landed by
# `graphview.Edit.spawn` through today's doors as one undo step). Nothing
# is attached by itself (D2): every host port is an open pin on the group
# node, unless the patch was dropped on a cable (splice) or **wire as
# saved** is pressed. The browser is the head's **patches** chip and the
# canvas's **spawn ▸**; the PRESETS page lists the same, for × and rename
# only (ui_loadable). The control window's only (D8): nothing on the desk.

PATCH_DRAG = "PATCH"                 # a browser line's drag payload: the patch's slug
PATCHES_POPUP = "##graph.patches"
DROP_COLOUR = imgui.ImVec4(1.0, 0.86, 0.35, 1.0)    # the cable a dragged patch would splice into
DROP_WIRE = 6.0
SPOT_ALPHA = 0.15       # every other cable while a hot node is dragged (refused, its own)
PATCHES_TIP = ("The patches: a click spawns one at the canvas's centre, its pins open — "
               "nothing wired to this loadable patch. Drag one onto a picture cable to splice it in")
NO_PATCHES = "no patches yet — a group's menu: save as patch…"
WIRE_AS_SAVED_TIP = ("Wire each open pin as the patch was saved, where this loadable patch has that "
                     "node and the port is free — the rest said, nothing else touched")
SAVE_PATCH_TIP = ("Save this group as a patch: its nodes, values, wires, rows and the cables "
                  "across its edge — the patch's file, nothing else written")
SHEET_UP = "{n} control{s} the loadable patch already uses: the sheet asks which keeps each"
SHEET_REPLACES = "this loadable patch already has {nodes}: the sheet asks to replace it"
SPAWN_CANCELLED = "spawn of {name} cancelled: nothing landed"
NO_LIBRARY = "no library: nothing to spawn"
WAITS_FOR = "waits for "    # plan 40 P4: a spawn's rows the meta controller lacks (`devices.want_words`')


def group_entry_of(panel, gid: str) -> dict | None:
    """The loaded patch's entry of group `gid` (its shared meta keys too: a
    spawn's open `ports` and its `renames`), or None."""
    pre = getattr(getattr(panel, "library", None), "loaded_patch", None)
    return next((g for g in getattr(pre, "groups", None) or () if g.get("id") == gid), None)


def saved_words(ports) -> str:
    """The open pins as **wire as saved** would wire them: "scene → in,
    out → output.all.image"."""
    return ", ".join(f"{p.get('was')} → {p.get('id')}" if "to" in p
                     else f"{p.get('id')} → {p.get('was')}" for p in ports)


def patch_list(panel) -> list[dict]:
    """The browser's lines (plan 40 T3): each patch of `Library.list(PATCHES)`
    — factory then the user's shadowing them, hidden ones out, as the
    PRESETS list is (`ui_loadable.names`, on its poll) — as ``{"name",
    "slug", "note", "words", "ports"}`` (`graphview.patch_words`: "in:
    picture · out: picture · wants: K1, right hand y, analyzer 1"). A patch
    the library refuses is left out (its words on the footer once).
    Asked every frame the canvas's menu is open or a line is dragged, it
    looks at the disk only on `ui_loadable`' poll (plan 40 review fix): the
    same listing as last time is the same list, with no file stat'ed; a new
    listing re-reads only when the listing or a file moved."""
    from . import library as libmod
    from . import ui_loadable
    lib = getattr(panel, "library", None)
    if lib is None:
        return []
    st = _state(panel)
    listed = ui_loadable.names(panel, libmod.PATCHES)
    held = st.get("patch_list")
    if held is not None and held[0] is listed:
        return held[2]
    paths = [lib.path_of(libmod.PATCHES, n) for n in listed]
    key = tuple((n, str(p), p.stat().st_mtime if p is not None and p.exists() else 0.0)
                for n, p in zip(listed, paths))
    if held is not None and held[1] == key:
        st["patch_list"] = (listed, key, held[2])
        return held[2]
    out = []
    for name, path in zip(listed, paths):
        if path is None:
            continue
        try:
            doc = lib.read_patch(path.name[:-5])
        except LibraryError as e:
            lib.say(warning=f"library: {e}")
            continue
        out.append({"name": name, "slug": path.name[:-5], "note": str(doc.get("note") or ""),
                    "words": graphview.patch_words(doc, _glyph(panel)),
                    "ports": tuple(patches.read(doc).ports),
                    "replaces": patches.replaceable(patches.read(doc).members.render)})
    st["patch_list"] = (listed, key, out)
    return out


def _glyph(panel):
    """The desk's names for a MIDI row ("K1"), when the table is the APC40's."""
    router = ui_routing.router_of(panel)
    if router is None or getattr(router.table, "profile", None) != "apc40":
        return None
    return lambda src: ui.apc40.glyph(src) if src.partition(":")[0] in ("cc", "note",
                                                                         "pitch") else None


def view_centre(panel) -> tuple[float, float]:
    """The canvas's centre last drawn, in layout units (a click in the
    browser spawns there): `st["seen_rect"]`'s middle, less the pan."""
    st = _state(panel)
    (x0, y0), (x1, y1) = st.get("seen_rect") or ((0.0, 0.0), (0.0, 0.0))
    px, py = panned(st)
    return (round((x0 + x1) / 2 - px), round((y0 + y1) / 2 - py))


def spawn(panel, slug: str, at=None, splice=None) -> str | None:
    """Spawn patch `slug` (plan 40 P3): `Library.read_patch`, then
    `patches.spawn` over a `Host` of the live parts, its layout placed at
    `at` (layout units; None: the canvas's centre) — and, when its control rows
    collide with the loadable patch's, the conflict sheet first
    (`panel.spawn_question`, drawn by `ui_routing.modal`: every row the
    patch's, D9) — as when it holds a dream and the loadable patch has one (wave 3
    P2: its row says what the host's loses, `Landing.loses`) — else landed
    at once (`land_spawn`: one undo step).
    `splice`: a picture cable it was dropped on. Returns the refusal (said
    on the head), or None."""
    st = _state(panel)
    lib = getattr(panel, "library", None)
    pre = getattr(lib, "loaded_patch", None)
    e = group_edit(panel)
    if lib is None or pre is None or e is None:
        _note(st, NO_LIBRARY)
        return NO_LIBRARY
    try:
        doc = lib.read_patch(slug)
    except LibraryError as err:
        _note(st, str(err))
        return str(err)
    from . import library as libmod
    path = lib.path_of(libmod.PATCHES, slug)
    stem = path.name[:-5] if path is not None else patches.slug(str(doc.get("name") or slug))
    at = view_centre(panel) if at is None else (float(at[0]), float(at[1]))
    gs = pre.graph
    host = patches.Host.of(gs.spec, e.table, pre.banks())
    landing = patches.spawn(doc, host, at, patch=stem)
    if landing.refusal is not None:      # (wave 3 P1) before any sheet could ask
        _note(st, landing.refusal)
        return landing.refusal
    replacing = landing.replacing        # (wave 3 P2) the host's dream: the sheet's to ask
    if splice is not None:
        why = graphview.splice_target(e, splice, landing.group.get("name") or stem,
                                      landing.ports, replacing)
        if why is not None:
            _note(st, why)
            return why
    if not landing.conflicts and not replacing:
        return land_spawn(panel, landing, {}, splice)
    name = landing.group.get("name") or stem
    if replacing:
        loses, keeps = e.replace_said(landing)
        landing = dataclasses.replace(landing, loses=tuple(loses), keeps=tuple(keeps),
                                      asked=e._asked(replacing))

    def cancelled() -> None:
        _note(st, None)
        st["said"] = SPAWN_CANCELLED.format(name=name)
    panel.spawn_question = (landing, {**{k: graphview.PATCH_SIDE
                                         for k in range(len(landing.conflicts))},
                                      **{patches.replace_key(n): graphview.PATCH_SIDE
                                         for n in replacing}},
                            lambda choices: land_spawn(panel, landing, choices, splice),
                            cancelled)
    lrn = getattr(panel, "learn", None)
    if lrn is not None and hasattr(lrn, "hold"):
        lrn.hold(True)                      # the hands learn nothing while it asks
    k = len(landing.conflicts)
    _note(st, None)
    st["said"] = " · ".join(
        [*([SHEET_REPLACES.format(nodes=", ".join(replacing))] if replacing else []),
         *([SHEET_UP.format(n=k, s="" if k == 1 else "s")] if k else [])])
    return None


def land_spawn(panel, landing, choices, splice=None) -> str | None:
    """Land `landing` with the sheet's `choices` (`Edit.spawn` / `Edit.splice`:
    one undo step through the doors); its words on the head. Returns the
    refusal, or None. What its rows wait for is said after the landing
    (plan 40 P4: "…; waits for leap (not set up on this Mac): right hand y") —
    with no conflict there was no sheet to say it before the press."""
    e = group_edit(panel)
    if e is None:
        return NO_LIBRARY
    why = e.splice(landing, splice, choices) if splice is not None else e.spawn(landing, choices)
    if why is None and e.said:
        waits = ui_routing.sheet_wants(panel, landing, choices)
        if waits:
            e.said = f"{e.said}; {WAITS_FOR}" + " · ".join(waits)
    return _group_said(panel, e, why)


def wire_as_saved(panel, gid: str) -> str | None:
    """**wire as saved** on group `gid` (`Edit.wire_as_saved`): what landed on
    the head's line, what was refused as its note."""
    e = group_edit(panel)
    if e is None:
        return None
    why = e.wire_as_saved(gid)
    st = _state(panel)
    st["note"] = why or ""
    st["said"] = e.said if e.said else ""
    return why


def take_over(panel, asked: graphview.TakeOver) -> str | None:
    """The take-over chip pressed (`Edit.wire_taking_over`): what landed and what
    was cut on the head's line, what stays refused as its note. `asked` is the
    plan the chip showed."""
    e = group_edit(panel)
    if e is None:
        return None
    e.said = ""
    why = e.wire_taking_over(asked)
    st = _state(panel)
    st["take_over_plan"] = None     # (a refused plan is read again, not drawn again)
    st["note"] = why or ""
    st["said"] = e.said if e.said else ""
    return why


def save_patch(panel, gid: str, name: str, note: str = "") -> str | None:
    """**Save** on the side pane's form (`Edit.save_patch`): the patch's file
    written and nothing else; a refusal on the head, nothing written."""
    from . import library as libmod
    from . import ui_loadable
    e = group_edit(panel)
    if e is None:
        return None
    why = _group_said(panel, e, e.save_patch(gid, name, note))
    if why is None:
        st = _state(panel)
        st["patch_form"], st["patch_list"] = None, None
        ui_loadable.invalidate(panel, libmod.PATCHES)
    return why


def open_patch_form(panel, g, update: bool = False) -> None:
    """The side pane's name / note form for group `g`: its name (or, to
    update, the patch's own name and note) filled in."""
    name, note = g.name, ""
    if update and g.patch:
        try:
            doc = panel.library.read_patch(g.patch)
            name, note = str(doc.get("name") or g.name), str(doc.get("note") or "")
        except (LibraryError, AttributeError):
            pass
    _state(panel)["patch_form"] = [g.id, name, note]


def _patch_form(panel, g, form: list) -> None:
    """The save-as-patch form: a name, a note, **Save** / **cancel**."""
    ui._micro("save as patch")
    w = imgui.get_content_region_avail().x
    imgui.set_next_item_width(w)
    _, form[1] = ui.input_text_with_hint("##graph.patch.name", "name", form[1])
    imgui.set_next_item_width(w)
    _, form[2] = ui.input_text_with_hint("##graph.patch.note", "note", form[2])
    if ui.chip("Save##graph.patch"):
        save_patch(panel, g.id, form[1], form[2])
    if imgui.is_item_hovered():
        ui.tooltip(SAVE_PATCH_TIP)
    imgui.same_line()
    if ui.chip("cancel##graph.patch"):
        _state(panel)["patch_form"] = None


def _patches_chip(panel) -> bool:
    """**patches** on the head (plan 40 T3): the browser's popup — False
    with no library (a panel from a test without one)."""
    if getattr(panel, "library", None) is None:
        return False
    if ui.chip("patches##graph"):
        imgui.open_popup(PATCHES_POPUP)
    if imgui.is_item_hovered():
        ui.tooltip(PATCHES_TIP)
    if imgui.begin_popup(PATCHES_POPUP):
        _patch_rows(panel)
        imgui.end_popup()
    return True


def _patch_rows(panel) -> None:
    """The browser's lines: each patch's name (a click spawns it at the
    canvas's centre; a drag carries it to a cable), its note and its
    boundary in words."""
    st = _state(panel)
    rows = patch_list(panel)
    ui._micro("patches")
    if not rows:
        imgui.text_disabled(NO_PATCHES)
        return
    for k, row in enumerate(rows):
        picked, _ = imgui.selectable(f"{row['name']}##patch.{row['slug']}", False)
        if imgui.begin_drag_drop_source():
            st["patch_drag"] = row["slug"]
            imgui.set_drag_drop_payload_py_id(PATCH_DRAG, k)
            imgui.text(row["name"])
            imgui.end_drag_drop_source()
        elif picked:
            spawn(panel, row["slug"])
        if row["note"]:
            imgui.text_disabled(row["note"])
        if row["words"]:
            imgui.text_disabled(row["words"])


def _spawn_menu(panel, at=None) -> None:
    """The canvas's **spawn ▸** (plan 40 T3): the browser's list, each item
    spawning at the point the menu opened (`at`, canvas units)."""
    rows = patch_list(panel)
    if not rows or not imgui.begin_menu("spawn"):
        return
    st = _state(panel)
    for row in rows:
        if imgui.menu_item_simple(f"{row['name']}##spawn.{row['slug']}"):
            px, py = panned(st)
            spawn(panel, row["slug"], None if not at else (at[0] - px, at[1] - py))
        if imgui.is_item_hovered() and (row["note"] or row["words"]):
            ui.tooltip("\n".join(x for x in (row["note"], row["words"]) if x))
    imgui.end_menu()


def _drop_target(panel, st: dict, view: graphview.View) -> None:
    """While a browser line is dragged (`st["patch_drag"]`): the picture
    cable under the pointer that the patch may splice into lights
    (`st["drop_cable"]`: one inlet and one outlet of its type) — or the
    words why not (`st["drop_why"]`, the hover's)."""
    st["drop_cable"], st["drop_why"] = None, ""
    slug = st.get("patch_drag")
    if not slug:
        return
    m = imgui.get_mouse_pos()                  # canvas units, inside the editor
    c = graphview.cable_near(view, st["pin_xy"], (m.x, m.y), kinds=("render",))
    if c is None:
        return
    row = next((r for r in patch_list(panel) if r["slug"] == slug), None)
    if row is None:
        return
    e = render_edit(panel)
    # (wave 3 P2) as the drop will judge it: a cable of the dream it would replace
    have = patches.spec_names(getattr(e.graph, "spec", None))
    why = graphview.splice_target(e, c, row["name"], row["ports"],
                                  [n for n in row.get("replaces", ()) if n in have])
    if why is None:
        st["drop_cable"] = c.id
    else:
        st["drop_why"] = why
        ed.suspend()
        ui.tooltip(why)
        ed.resume()


def _patch_drop(panel, st: dict, view: graphview.View) -> None:
    """A dragged patch let go: on a lit cable, spliced in (`spawn` with the
    cable) — anywhere else, nothing (a click on its line spawns it)."""
    slug = st.get("patch_drag")
    if not slug:
        return
    if imgui.is_mouse_down(imgui.MouseButton_.left):
        return
    st["patch_drag"] = None
    cid = st.get("drop_cable")
    st["drop_cable"] = None
    c = next((x for x in view.cables if x.id == cid), None) if cid else None
    if c is not None:
        m = imgui.get_mouse_pos()
        px, py = panned(st)
        spawn(panel, slug, (m.x - px, m.y - py), splice=c)


def _group_menu(panel, st: dict, view: graphview.View, g) -> None:
    """A group's right-click menu: Open / Fold, Rename… (the side pane's
    name, the group selected), Ungroup."""
    imgui.text_disabled(g.name)
    if imgui.menu_item_simple("fold" if g.open else "open"):
        set_open(panel, g.id, not g.open)
    if imgui.menu_item_simple("rename…"):
        st["select_group"] = g.id
    if imgui.menu_item_simple("save as patch…"):          # plan 40 T3: the side pane's form
        st["select_group"] = g.id
        open_patch_form(panel, g)
    if g.patch and imgui.menu_item_simple("update patch"):
        st["select_group"] = g.id
        open_patch_form(panel, g, update=True)
    if imgui.menu_item_simple("ungroup"):
        ungroup(panel, g.id)


def _group_item(panel, st: dict) -> None:
    """The menus' **Group** item, while two nodes or more are selected."""
    sel = st.get("menu_sel") or []
    if len(sel) >= 2 and imgui.menu_item_simple(f"group {len(sel)} nodes"):
        group_nodes(panel, sel)


# ---------------------------------------------------------------- plan 37 C1: the thumbnails

def thumb_name(n: graphview.VNode) -> str:
    """The render node a canvas node's thumbnail is kept under: its render
    node's name (a channel's or a copy's own), else the canvas id's."""
    return getattr(n.ref, "name", None) or n.id.partition(":")[2]


def by_preview(n: graphview.VNode) -> bool:
    """Is node `n`'s picture output 1's — the page's `outputs.Preview`, the
    backdrop's own tap, not a thumbnail?"""
    return n.thumb == graphview.WINDOW_PIC and thumb_name(n) == "output.1"


def on_screen(rect, pos, size) -> bool:
    """Does a node at `pos`, `size` big (canvas units) meet `rect`
    ((left, top), (right, bottom)) — any part of it?"""
    (x0, y0), (x1, y1) = rect
    return (pos[0] < x1 and pos[0] + max(size[0], 1.0) > x0
            and pos[1] < y1 and pos[1] + max(size[1], 1.0) > y0)


def thumb_wants(st: dict, view: graphview.View, where) -> dict[str, str]:
    """The thumbnails this frame wants (name → how, `graphview.THUMBS`): every
    picture node drawn (`drawn_node`: not hidden by **preset only**, not
    idle off the canvas) and on screen (`on_screen`, `where(node id)` its
    (position, size)) — output 1 is the page's `Preview`, never one. A node
    off screen, hidden or collapsed off the canvas is never wanted, so it
    costs nothing."""
    rect = st.get("seen_rect")
    out: dict[str, str] = {}
    for n in view.nodes:
        if n.thumb is None or by_preview(n) or not drawn_node(st, n):
            continue
        if rect is not None and not on_screen(rect, *where(n.id)):
            continue
        out[thumb_name(n)] = n.thumb
    for g in view.groups:               # plan 40 T2: a folded group's last picture outlet
        n = graphview.group_picture(view, g) if not g.open else None
        if n is None or n.thumb is None or by_preview(n):
            continue
        if rect is None or on_screen(rect, *where(g.id)):
            out[thumb_name(n)] = n.thumb
    return out


def tint_wants(st: dict, view: graphview.View, want: dict[str, str]) -> dict[str, str]:
    """While **tint cables** is lit, the segment pins a cable leaves whose
    node is wanted (SM3): a hue is read from a thumbnail, and a pin's picture
    has none otherwise. One copy each, only while the switch is lit."""
    if not st.get("tint"):
        return {}
    out: dict[str, str] = {}
    for c in view.cables:
        pin = graphview.pin_picture(view, c.src_port)
        hit = view.owner(c.src_port) if pin else None
        if hit is not None and thumb_name(hit[0]) in want:
            out[pin] = graphview.PICTURE
    return out


def _where(st: dict, nid: str):
    k = ed.NodeId(_id(st, "n:" + nid))
    p, sz = ed.get_node_position(k), ed.get_node_size(k)
    h = sz.y if sz.y > 0 else graphview.HEAD_H + graphview.THUMB_H
    return (float(p.x), float(p.y)), (float(sz.x) if sz.x > 0 else NODE_W, float(h))


def _want_thumbs(st: dict, view: graphview.View) -> None:
    """Ask the renderer for this frame's thumbnails (`thumb_wants`), and
    output 1's picture when its node is on screen; each picture node's
    `picture` the size its thumbnail was copied from."""
    th = st.get("thumbs")
    if th is None:
        return
    want = thumb_wants(st, view, lambda nid: _where(st, nid))
    want.update(tint_wants(st, view, want))
    if want:
        th.want(want)
    pv = st.get("preview")
    for n in view.nodes:
        if n.thumb is not None:
            n.picture = th.size_of(thumb_name(n))
            if by_preview(n) and getattr(pv, "tex", None) is not None:
                n.picture = tuple(int(v) for v in pv.tex.size)    # plan 37 C2: its size
    rect = st.get("seen_rect")
    if pv is not None and any(by_preview(n) and drawn_node(st, n)
                              and (rect is None or on_screen(rect, *_where(st, n.id)))
                              for n in view.nodes):
        pv.want()


def _body_of(st: dict, n: graphview.VNode):
    """(the texture, the shade it is drawn at) for node `n`'s body this
    frame: its thumbnail and `PreviewTextures.shade` (1 fresh, dimmed,
    0 black) — a geometry's at `FAINT_PIC` of that; output 1's the
    `Preview`'s picture, always at 1 (it has no age: a frame that fails
    leaves its last picture lit). (None, 0) with none yet: a black box."""
    if by_preview(n):
        pv = st.get("preview")
        tex = getattr(pv, "tex", None)
        return (tex, 1.0) if tex is not None else (None, 0.0)
    th = st.get("thumbs")
    if th is None:
        return None, 0.0
    name = thumb_name(n)
    k = th.shade(name)
    if n.thumb in graphview.THUMB_FAINT:
        k *= FAINT_PIC
    return th.get(name), k


def _thumb(st: dict, n: graphview.VNode) -> None:
    """Node `n`'s picture as its body: a box at the node's width,
    `graphview.THUMB_H` tall, black, the thumbnail fitted whole in it
    (`backdrop_rect`) at its shade; GL's rows, so drawn upside down in v
    as the backdrop is."""
    p0 = imgui.get_cursor_screen_pos()
    imgui.dummy(imgui.ImVec2(NODE_W, graphview.THUMB_H))
    if imgui.is_item_hovered():                 # plan 37 C2: the hover gives details
        st["thumb_hover"] = n.id
    p1 = imgui.ImVec2(p0.x + NODE_W, p0.y + graphview.THUMB_H)
    dl = imgui.get_window_draw_list()
    dl.add_rect_filled(p0, p1, ui.u32(imgui.ImVec4(*THUMB_GROUND)))
    tex, k = _body_of(st, n)
    if tex is not None and k > 0.0 and getattr(tex, "glo", 0) != 0:
        a, b = backdrop_rect((p0.x, p0.y), (NODE_W, graphview.THUMB_H), tuple(tex.size))
        dl.add_image(imgui.ImTextureRef(tex.glo), imgui.ImVec2(*a), imgui.ImVec2(*b),
                     imgui.ImVec2(0, 1), imgui.ImVec2(1, 0), ui.u32(imgui.ImVec4(k, k, k, 1.0)))
    words = graphview.mask_words(n) if k < 1.0 else ""
    if words:                                   # SM3: no mask, and it says why, on the node
        step = imgui.get_text_line_height_with_spacing()
        for i, line in enumerate(box_lines(words, imgui.calc_text_size, NODE_W - 12.0)):
            dl.add_text(imgui.ImVec2(p0.x + 6.0, p0.y + 6.0 + i * step), ui.u32(ui.WARN), line)


# as many lines of a mask node's refusal as sit in the picture's box
BOX_LINES = 4


def box_lines(words: str, measure, width: float) -> list[str]:
    """`words` broken at spaces to fit `width` (`measure(text).x`), at most
    `BOX_LINES` of them, the last ending "…" when some are left over."""
    lines: list[str] = []
    line = ""
    parts = words.split()
    for word in parts:
        wider = f"{line} {word}".strip()
        if line and measure(wider).x > width:
            if len(lines) == BOX_LINES - 1:
                while line and measure(f"{line}…").x > width:
                    line = line[:-1]
                return [*lines, f"{line}…"]
            lines.append(line)
            line = word
        else:
            line = wider
    return [*lines, line] if line else lines


def thumb_tip(st: dict, n: graphview.VNode) -> str:
    """Hovering node `n`'s thumbnail (plan 37 C2, P1): `graphview.picture_hover`
    with its GPU time from the SYSTEM page's medians (`st["gpu_ms"]`, by its
    render node's name), and its status when it has one."""
    tip = graphview.picture_hover(n, st.get("gpu_ms", {}).get(thumb_name(n)))
    return tip + (f"\n{n.status}" if n.status else "")


def picture_sources(panel):
    """(the thumbnails, the picture of this deck's output 1, the GPU medians) the
    canvas reads this frame: all of the renderer of the deck the panel is on, whose
    graph the canvas draws. Each deck's `PreviewTextures` are its own; on the deck
    off air its output's thumbnail is what that deck would put on the output, the
    backdrop's picture, and what is on air is the inset's (`panel.monitor`)."""
    r = getattr(panel, "renderer", None)
    stats = getattr(r, "stats", None) or {}
    return getattr(r, "thumbs", None), getattr(panel, "preview", None), stats.get("gpu_ms") or {}


def thumbnail_line(panel) -> str:
    """The SYSTEM page's line for the thumbnails (plan 37 C1): "thumbnails ·
    N copied · K repainted · M kept" — the copies the last frame made, how
    many of those painted a node again at the frame's size (one that paints
    into its consumer: the cost AH.2 reads), and the thumbnails held; ""
    with no renderer that keeps any. The panel's deck's (`picture_sources`)."""
    th = getattr(getattr(panel, "renderer", None), "thumbs", None)
    if th is None or not hasattr(th, "count"):
        return ""
    return (f"thumbnails · {th.count} copied · {getattr(th, 'repainted', 0)} repainted · "
            f"{th.kept} kept")


def _port(st: dict, port: graphview.VPort, drawn: set[str]) -> None:
    text = ui.fit_text(port.name, NODE_W - 4 * PIN - 40)
    if port.direction == graphview.OUT:
        # a desk layer's port (plan 28 N5): lit while its layer is up, faint while down
        imgui.text_colored(ui.FAINT if not port.up else ui.TEXT if port.layer else ui.DIM, text)
        imgui.same_line(NODE_W - PIN)
        _pin(st, port.pins[0], ed.PinKind.output, port, "", drawn,   # out past the node's edge
             room=(STUB_REACH, graphview.ROW_H), grow=GROW_RIGHT)
        return
    pitch = PIN + imgui.get_style().item_spacing.x    # base / mod / depth, side by side
    for pin in port.pins:
        stub = pin.partition(":")[0] if port.param is not None else ""
        _pin(st, pin, ed.PinKind.input, port, stub, drawn, room=(pitch, graphview.ROW_H))
        imgui.same_line()
    imgui.text_colored(ui.TEXT if port.patched else ui.DIM, text)


def _cable(st: dict, c: graphview.VCable, a: str | None = None, b: str | None = None) -> None:
    """One cable, from pin `a` to pin `b` (its own ends, or a collapsed
    node's stub for a render cable: plan 28 N7)."""
    k = st.get("tints", {}).get(c.id)          # plan 37 C2: tinted while the switch is lit
    if k is None:
        k = KIND_COLOURS.get(c.kind) or COLOURS.get(c.type, ui.DIM)
    col = imgui.ImVec4(k.x, k.y, k.z, DORMANT_ALPHA if c.dormant else
                       THROUGH_ALPHA if c.kind == graphview.THROUGH else k.w)
    if c.type == graphview.VALUE:
        u = c.live if c.live is not None else 0.0
        thick = THIN + (THICK - THIN) * max(0.0, min(1.0, abs(u)))
    else:
        thick = WIRE
    if st.get("drop_cable") == c.id:        # plan 40 T3: a dragged patch would splice here
        col, thick = DROP_COLOUR, DROP_WIRE
    lit = st.get("onto_lit")                # 2026-10-29: a hot node dragged — the spotlight
    if lit is not None and lit.get("hot"):
        if c.id == lit["best"] or c.id in lit["tie"]:
            col, thick = DROP_COLOUR, DROP_WIRE
        elif c.id not in lit.get("cold", ()):
            # every other cable that could take the node dims; one that never
            # could (2026-11-01, `cold`) keeps its colour
            col = imgui.ImVec4(col.x, col.y, col.z, min(col.w, SPOT_ALPHA))
    ed.link(ed.LinkId(_id(st, "c:" + c.id)), ed.PinId(_id(st, a or c.src_port)),
            ed.PinId(_id(st, b or c.dst_port)), col, thick)


def bundle_thickness(count: int) -> float:
    """A bundle's line (plan 28 N7): a single cable's resting width, a
    little more for each cable past the first, capped at `BUNDLE_MAX`."""
    return min(BUNDLE_MAX, WIRE + BUNDLE_STEP * max(0, count - 1))


def _bundle_colour(b: graphview.VBundle) -> imgui.ImVec4:
    """What a bundle carries: its kind's colour when every cable is of one kind
    that has its own (`KIND_COLOURS`), else its type's."""
    kinds = {c.kind for c in b.cables}
    k = KIND_COLOURS.get(kinds.pop()) if len(kinds) == 1 else None
    return k or COLOURS.get(b.type, ui.DIM)


def _bundle(st: dict, b: graphview.VBundle) -> None:
    """The one wire between two nodes while either is collapsed: coloured
    by what it carries, as thick as it is many, faint while dormant."""
    k = _bundle_colour(b)
    col = imgui.ImVec4(k.x, k.y, k.z, DORMANT_ALPHA if b.dormant else k.w)
    lit = st.get("onto_lit")
    thick = bundle_thickness(b.count)
    if lit is not None and lit.get("hot"):  # 2026-10-29: a dragged node's spotlight —
        if any(c.id == lit["best"] or c.id in lit["tie"] for c in b.cables):
            col, thick = DROP_COLOUR, max(thick, DROP_WIRE)     # the cable it lands in is here
        elif not all(c.id in lit.get("cold", ()) for c in b.cables):
            col = imgui.ImVec4(col.x, col.y, col.z, min(col.w, SPOT_ALPHA))
    ed.link(ed.LinkId(_id(st, "c:" + b.id)), ed.PinId(_id(st, b.src_port)),
            ed.PinId(_id(st, b.dst_port)), col, thick)


def _said(v: float | None) -> str:
    return "not live" if v is None else f"{v:.2f}"


def cable_tip(view: graphview.View, c: graphview.VCable) -> str:
    """What hovering a cable says: from and to, the reading, the depth."""
    src = view.owner(c.src_port)
    dst = view.owner(c.dst_port)
    a = f"{src[0].label} {src[1].name}" if src and src[1] else c.src_port
    b = f"{dst[0].label} {dst[1].name}" if dst and dst[1] else c.dst_port
    lines = [f"{a}  →  {b}  ({c.dst_port.partition(':')[0]})"]
    if c.kind != "render":
        lines.append(f"reading {_said(c.live)}")
    if c.depth is not None:
        lines.append(f"depth {c.depth:+.2f}")
    if c.label:
        lines.append(c.label)
    if c.dormant:
        lines.append("dormant")
    return "\n".join(lines)


def _hover(st: dict, view: graphview.View, panel=None) -> None:
    if st.get("onto_lit") is not None:
        return          # 2026-10-29: a node drag's own words (`_drag_preview`) are not covered
    tip = None
    names = st["names"]
    link = ed.get_hovered_link().id()
    pin = ed.get_hovered_pin().id()
    node = ed.get_hovered_node().id()
    if link:
        cid = names.get(link, "")[2:]
        bundle = st["bundles"].get(cid)
        c = next((x for x in view.cables if x.id == cid), None) if bundle is None else None
        through = st.get("throughs", {}).get(cid)
        tip = (graphview.bundle_tip(view, bundle) if bundle is not None
               else cable_tip(view, c) if c is not None
               else f"{through.label}\n{THROUGH_NO_DELETE}" if through is not None else None)
    elif pin and graphview.is_group_pin(names.get(pin, "")):      # plan 40 T2
        g = graphview.view_group_of_pin(view, names[pin])
        port = g.port(names[pin]) if g is not None else None
        if port is not None:
            rows = [graphview.cable_words(view, c) for c in g.rows.get(port.id, ())]
            tip = "\n".join([f"{g.name} · {port.name}", *rows[:graphview.TIP_ROWS]])
    elif pin and graphview.is_stub(names.get(pin, "")):
        n = view.node(graphview.stub_node(names[pin]))
        if n is not None:
            side = "in" if graphview.pin_kind(names[pin]) == graphview.STUB_IN else "out"
            tip = (f"{n.label} {side}: {n.wires} cable{'s' if n.wires != 1 else ''}\n"
                   f"drag a cable here to pick one of its ports")
    elif pin:
        hit = view.owner(names.get(pin, ""))
        if hit is not None and hit[1] is not None:
            port = hit[1]
            stub = names.get(pin, "").partition(":")[0] if port.param else ""
            tip = (f"{port.param or port.addr or port.id}{'  ' + stub if stub else ''}\n"
                   f"{port.name}: {_said(port.live)}")
            tip += hidden_by(st, view, names.get(pin, ""))
    elif node:
        n = view.node(names.get(node, "")[2:])
        err = st.get("errors", {}).get(n.id) if n is not None else None
        g = group_at(view, names.get(node, "")[2:]) if n is None else None
        if g is not None:                   # plan 40 T2
            tip = group_tip(panel, view, g) if panel is not None else g.name
        elif err:                             # plan 33 U: a compile error is its hover
            tip = f"{n.label}\n{err}"
        elif n is not None and n.thumb is not None and st.get("thumb_hover") == n.id:
            tip = thumb_tip(st, n)          # plan 37 C2: on its picture
        elif n is not None and n.faint:
            tip = f"{n.label}\n{FAINT_TIP}" + (f"\n{n.status}" if n.status else "")
        elif n is not None and n.status:
            tip = f"{n.label}\n{n.status}"
    if tip:
        ed.suspend()
        ui.tooltip(tip)
        ed.resume()


# ---------------------------------------------------------------- render edits (plan 28 N4)
#
# The render graph's edits, beside N3's below and on its contract: a drag's
# handler is `CREATE[type]` (image / geometry / mask → `_create_render`), a
# deleted cable's `DELETE["render"]`, a deleted node's
# `DELETE_NODE["render" / "output"]`; each handler accepts or rejects the
# widget's item itself. They do not go through N3's `_act` (an undo step
# pushed before the edit, even one refused): `render_edit` reads each edit
# back and pushes its undo step (`load=True`: the library's marks carry the
# graph) only when it lands. A refusal is the head's note; a landing's
# words are `st["said"]`.

def render_edit(panel) -> graphview.Edit:
    """The render edits on this panel's loaded patch (its `GraphSection`),
    pins named through the renderer's last graph, one undo step each."""
    lib = getattr(panel, "library", None)
    gs = getattr(getattr(lib, "loaded_patch", None), "graph", None)
    rg = getattr(getattr(panel, "renderer", None), "_graph", None)
    e = graphview.Edit(graph=gs, render=rg, push=lambda label: undo.push(label, load=True))
    e.slots = getattr(panel, "outputs", None) or ()     # (plan 35 G: a window's name)
    e.show = getattr(lib, "install", None)
    e.loaded_patch = getattr(lib, "loaded_patch", None)           # (plan 44 D3: the bus cuts are the loadable patch's)
    return e


def _render_said(panel, e: graphview.Edit, fn, st: dict | None = None) -> str | None:
    """Run render edit `fn(e)`: a refusal is the head's note, a landing's
    words the head's line (`st`: the page's state). Returns the refusal,
    or None."""
    st = st if st is not None else _state(panel)
    why = fn(e)
    _note(st, why)
    if why is None:
        st["said"] = e.said
    return why


def _note(st: dict, why: str | None) -> None:
    """The head after an edit: a refusal's words (`why`), or none for an
    edit that landed — and either way the last render edit's line goes
    (a render landing puts its own back after this). Inside one delete of
    a selection (`st["held"]` present) the first refusal's words stay for
    the frame: a later landing or refusal there does not wipe them."""
    st["said"] = ""
    if st.get("held"):
        return
    st["note"] = why or ""
    if why and "held" in st:
        st["held"] = True


def new_link() -> tuple[int, int] | None:
    """The two pins' widget ids of a cable being dragged this frame, in drag
    order, or None."""
    a, b = ed.PinId(), ed.PinId()
    if ed.query_new_link(a, b) and a.id() and b.id():
        return a.id(), b.id()
    return None


def _create_render(panel, st: dict, view: graphview.View, a: str, b: str) -> None:
    """An image / geometry / mask cable dragged (either end first): checked
    while it is held — red, and the words a loadable patch file would get — and a
    wire when it is let go."""
    src, dst = graphview.Edit.ordered(a, b)
    e = render_edit(panel)
    why = e.wire(src, dst, dry=True)
    if why:
        _drag_tip(why)
        ed.reject_new_item(imgui.ImVec4(*REFUSED_RGB), WIRE)
    elif ed.accept_new_item(COLOURS[graphview.IMAGE], WIRE):
        _render_said(panel, e, lambda e: e.wire(src, dst), st)


def _delete_render_cable(panel, st: dict, view: graphview.View, c) -> None:
    """Delete pressed on a render cable: its wire out of the section (plan
    35 G: any wire — the run's, the look-back's, the scene's geometry; only
    one the section does not have is refused, in words). A cable of a
    render node this delete just took out goes with it, saying nothing over
    the node's words."""
    gone = st.get("dropped") or set()
    if view is not None and gone and any(
            view.pins.get(p, ("",))[0] in gone for p in (c.src_port, c.dst_port)):
        ed.accept_deleted_item()
        return
    if _render_said(panel, render_edit(panel), lambda e: e.unwire(c), st) is None:
        ed.accept_deleted_item()
    else:
        ed.reject_deleted_item()


def _delete_render_node(panel, st: dict, view: graphview.View, n) -> None:
    """Delete pressed on a render node: any node of the section out of the
    graph with its wires (plan 35 G); a window keeps itself, its wires
    gone (said, accepted as an edit: the node stays drawn); the camera and
    a cloud are the meta controller's, refused in words."""
    if _render_said(panel, render_edit(panel), lambda e: e.drop_node(n.id), st) is None:
        st.setdefault("dropped", set()).add(n.id)
        ed.accept_deleted_item(False)
    else:
        ed.reject_deleted_item()


LOOKBACK_MENU = "look-back frame"     # plan 34's echo items, under look-back ▸


def render_picker(panel, at=None) -> None:
    """The picker's render items (`graphview.picker`), grouped by primitive
    (plan 35 G, `graphview.PICKER_GROUP`): starters ▸ at the top (plan 36
    T5, `graphview.STARTERS`), then scene ▸, look-back ▸ (its look-back frames under `LOOKBACK_MENU`),
    pictures ▸ (R28's switch over the channels under the switch), media ▸
    (2026-10-31: channel a–h, each selecting a channel that always exists,
    `pick_channel`; the segment), masks ▸, effects ▸ and copy of ▸. A
    frame node the section has already — the scene, the
    shape, the look-back, the backdrop, the pattern, an echo, the dream —
    is drawn disabled (`graphview.picked`): there is one of each. A node
    lands unwired (faint, "reaches nothing") where the menu opened (`at`,
    canvas units); the starter and the channels' switch land wired."""
    e = render_edit(panel)
    items = graphview.picker(e)
    have = graphview.picked(e)
    for group in graphview.PICKER_GROUPS:
        mine = [it for it in items if graphview.PICKER_GROUP.get(it[0]) == group]
        if not mine:
            continue
        if not imgui.begin_menu(f"{group}##graph.pick"):
            continue
        for kind, f, label in mine:
            if kind in ("echo", "channels"):        # (their own submenus)
                continue
            if kind == "channel":                   # 2026-10-31: selects, makes nothing
                if imgui.menu_item_simple(label):
                    pick_channel(panel, f, at)
                continue
            if imgui.menu_item_simple(label, enabled=graphview.picked_name(kind, f) not in have):
                add_render(panel, e, kind, f, at)
            if kind == "lookback":
                _echo_menu(panel, e, [it for it in mine if it[0] == "echo"], have, at)
            if kind == "switch":
                _channels_menu(panel, e, items, at)
        imgui.end_menu()


def _echo_menu(panel, e: graphview.Edit, echoes, have: set[str], at=None) -> None:
    """Plan 34's look-back frames, echo.1 (newest) … echo.32 (oldest), in
    their own submenu under look-back ▸; one already in the section drawn
    disabled."""
    if imgui.begin_menu(LOOKBACK_MENU):
        for kind, f, label in echoes:
            if imgui.menu_item_simple(label, enabled=f"echo.{f}" not in have):
                add_render(panel, e, kind, f, at)
        imgui.end_menu()


def _channels_menu(panel, e: graphview.Edit, items, at=None) -> None:
    """R28: "switch over the channels ▸ faces media / backdrop", under the
    picker's switch: one undo step (`Edit.switch_channels`), the new switch
    put where the menu opened."""
    ports = [(port, label) for kind, port, label in items if kind == "channels"]
    if ports and imgui.begin_menu("switch over the channels"):
        for port, label in ports:
            if imgui.menu_item_simple(label):
                switch_channels(panel, e, port, at)
        imgui.end_menu()


def switch_channels(panel, e: graphview.Edit, port: str, at=None) -> str | None:
    """R28: a switch over the eight channels into `port`, one undo step,
    put where the menu opened. Returns the refusal, or None."""
    why = _render_said(panel, e, lambda e: e.switch_channels(port))
    if why is None and e.added:
        _place_new(panel, f"render:{e.added}", at)
    return why


def pick_channel(panel, c: str, at=None) -> None:
    """The picker's media ▸ channel a–h (2026-10-31). Nothing is made — the
    eight channels always exist (`graphview.build`) — and nothing is wired:
    the channel's node is revealed (`reveal_node`), put where the menu opened
    unless the loadable patch's layout already places it, and selected and centred
    next frame (`select_node`). The owner, after the show of 2026-10-30:
    in preset only, with no channel wired to the faces, "you can't actually
    spawn one, it just doesn't exist"."""
    name = rgraph.channel_name(c)
    nid = f"render:{name}"
    pre, _ = _layouts(panel)
    _place_new(panel, nid, None if pre is not None and pre.get(nid) is not None else at)
    select_node(panel, name)


def add_render(panel, e: graphview.Edit, kind: str, file: str | None = None, at=None):
    """A render node the picker adds (`Edit.add_node`), one undo step, put
    where the menu opened — a starter's group (plan 36 T5) laid left to
    right from there. Returns the refusal, or None."""
    why = _render_said(panel, e, lambda e: e.add_node(kind, file))
    if why is None:
        _place_group(panel, e, at)
    return why


def add_starter(panel, which: str, cable=None, at=None) -> str | None:
    """A starter (plan 36 T5, `Edit.starter`) — on picture cable `cable`,
    from its menu, or (None) from the picker — one undo step, its new nodes
    laid left to right from where the menu opened. Returns the refusal, or
    None."""
    e = render_edit(panel)
    why = _render_said(panel, e, lambda e: e.starter(which, cable))
    if why is None:
        _place_group(panel, e, at)
    return why


def insert_node(panel, cable: graphview.VCable, kind: str, file: str | None = None,
                inlet: str | None = None, at=None) -> str | None:
    """A render cable's "insert ▸" (2026-11-01; plan 33 U's "insert effect
    ▸ <file>" the first): a new node of `kind` (`graphview.INSERT_PORTS`;
    an effect `file`) made and spliced into the cable in one undo step
    (`Edit.insert_node`), put where the menu opened (on the cable), never
    left to the layout. A kind with several inlets and no `inlet` chosen
    opens the chooser instead (`st["onto"]` with `insert`: the pick calls
    this again with the inlet). Returns the refusal, or None."""
    ins = graphview.INSERT_PORTS.get(kind, ((), ""))[0]
    if len(ins) > 1 and inlet is None:
        _state(panel)["onto"] = {"node": None, "insert": (kind, file), "cables": [cable.id],
                                 "inlets": ins, "at": at, "open": True}
        return None
    e = render_edit(panel)
    why = _render_said(panel, e, lambda e: e.insert_node(cable, kind, file, inlet))
    if why is None and e.added:
        _place_new(panel, f"render:{e.added}", at)
    return why


def insert_effect(panel, cable: graphview.VCable, file: str, at=None) -> str | None:
    """A render cable's "insert ▸ effects ▸ <file>" (plan 33 U): the next
    instance of `file` onto it — `insert_node` for an effect."""
    return insert_node(panel, cable, "effect", file, None, at)


def render_node_menu(panel, n) -> None:
    """A render node's menu items: a hands node drawn solid or as lines, a
    composite's blend, a picture node's "add feedback after" (wave 0 E1:
    `_feedback_after_menu`, `add_feedback_after`), delete."""
    e = render_edit(panel)
    name, _ = graphview.spec_name(n.id, e.render)
    kind = graphview.kind_of(name) if name else None
    if kind in ("hands", "layer", "guide"):              # (plan 35 V2: the new ids)
        for how in rgraph.DRAWS:
            if imgui.menu_item_simple(f"draw {how}"):
                _render_said(panel, e, lambda e, how=how: e.set_node(name, draw=how))
    if kind == "composite":
        for how in rgraph.BLENDS:
            if imgui.menu_item_simple(f"laid {how}"):
                _render_said(panel, e, lambda e, how=how: e.set_node(name, blend=how))
    feeds = graphview.picture_feeds(e, name) if name else None   # (the spec's wires, no copy)
    if feeds is not None:
        _feedback_after_menu(panel, name, feeds)
    if imgui.menu_item_simple("delete"):
        _render_said(panel, e, lambda e: e.drop_node(n.id))


FEEDBACK_AFTER = "add feedback after"


def _feedback_after_menu(panel, name: str, feeds: list[tuple[str, str]]) -> None:
    """A picture node's "add feedback after" (wave 0 E1, 2026-11-02): the
    feedback starter on the cable out of it — one cable, the item itself;
    several, a submenu naming each port it feeds; none, the item disabled
    with why (`graphview.FEEDBACK_FEEDS_NOTHING`). The loop lands under the
    node's box (`add_feedback_after`, `node_below`)."""
    if not feeds:
        imgui.menu_item_simple(f"{FEEDBACK_AFTER}: {graphview.FEEDBACK_FEEDS_NOTHING}",
                               enabled=False)
    elif len(feeds) == 1:
        if imgui.menu_item_simple(FEEDBACK_AFTER):
            add_feedback_after(panel, name, feeds[0][1])
    elif imgui.begin_menu(FEEDBACK_AFTER):
        for _, d in feeds:
            if imgui.menu_item_simple(f"→ {d}"):
                add_feedback_after(panel, name, d)
        imgui.end_menu()


def node_below(st: dict, nid: str) -> tuple[float, float] | None:
    """The canvas point just under node `nid`'s box as the editor last drew
    it (its real position and size, expanded or collapsed: `GAP` below its
    bottom-left), or None when the editor has no box for it — the node
    menu's feedback lands there, never on the node's own rows."""
    if st.get("editor") is None or st["ids"].get("n:" + nid) is None:
        return None
    ed.set_current_editor(st["editor"])
    k = ed.NodeId(_id(st, "n:" + nid))
    size = ed.get_node_size(k)
    if size.y <= 0:
        return None
    p = ed.get_node_position(k)
    return (p.x, p.y + size.y + graphview.GAP)


def add_feedback_after(panel, name: str, port: str, at=None) -> str | None:
    """The feedback starter (`add_starter("feedback")`) on the cable from
    picture node `name` into `port` — the node menu's "add feedback after"
    (wave 0 E1), one undo step, its three nodes laid left to right from
    `at`, else from under the node's box as the editor last drew it
    (`node_below`), else from where the menu opened. Returns the refusal,
    or None."""
    if at is None:
        st = _state(panel)
        at = node_below(st, f"render:{name}") or st.get("menu_at")
    return add_starter(panel, "feedback", (name, port), at)


# ---------------------------------------------------------------- the selection

def _selection(st: dict, view: graphview.View):
    """The selected cable or node (the first), as ("cable", VCable) or
    ("node", VNode); None. Asked of last frame's canvas."""
    if st["editor"] is None:
        return None
    ed.set_current_editor(st["editor"])
    names = st["names"]
    for lk in ed.get_selected_links():
        cid = names.get(lk.id(), "")[2:]
        b = st["bundles"].get(cid)
        if b is not None:                       # plan 28 N7: a bundle's rows
            return ("bundle", b)
        c = next((x for x in view.cables if x.id == cid), None)
        if c is not None:
            return ("cable", c)
    for nk in ed.get_selected_nodes():
        n = view.node(names.get(nk.id(), "")[2:])
        if n is not None:
            return ("node", n)
        g = group_at(view, names.get(nk.id(), "")[2:])     # plan 40 T2
        if g is not None:
            return ("group", g)
    return None


def sel_words(sel) -> str:
    """The selection chip's words (plan 49): a node's label, a
    group's name, else the kind ("cable", "bundle"); "" with nothing."""
    if sel is None:
        return ""
    what, obj = sel
    if what == "node":
        return str(getattr(obj, "label", "") or what)
    if what == "group":
        return str(getattr(obj, "name", "") or what)
    return what


def _side(panel, st: dict, view: graphview.View, sel) -> None:
    what, obj = sel
    router = ui_routing.router_of(panel)
    if what != "bundle" or not any(c.ref is st.get("focus") for c in obj.cables):
        st["focus"] = None                      # another selection: no row first
    if what == "bundle":                        # plan 28 N7: each of its rows
        b = obj
        ui._micro("bundle")
        imgui.text_wrapped(graphview.bundle_tip(view, b).split("\n")[0])
        roles = _node_mode_roles(b)
        if roles:
            imgui.text_disabled(f"{b.count} cable{'s' if b.count != 1 else ''}")
            imgui.text_wrapped(graphview.LEAVE_WORDS)
            for role in roles:
                _leave_chip(panel, role)
        else:
            imgui.text_disabled(f"{b.count} cable{'s' if b.count != 1 else ''} · "
                                f"{graphview.EXPAND_TO_EDIT} on the canvas")
        imgui.separator()
        rows = [c.ref for c in b.cables if c.kind == "route"]
        focus = st.get("focus")
        if any(r is focus for r in rows):       # the route just made: first
            rows = [focus] + [r for r in rows if r is not focus]
        route_rows(panel, rows)
        for c in b.cables:                      # the rest: a desk row, a subscriber …
            if c.kind != "route":
                imgui.text_disabled(ui.fit_text(
                    f"{graphview.cable_words(view, c)}  {c.label}".rstrip(),
                    imgui.get_content_region_avail().x))
        return
    if what == "cable":
        c = obj
        if c.kind == graphview.NODE_MODE:
            ui._micro(NODE_CHIP)
            _route_row(panel, router, view, c)
            imgui.text_wrapped(graphview.LEAVE_WORDS)
            if c.ref is not None:
                _leave_chip(panel, c.ref[0])
            return
        ui._micro(c.kind)
        _route_row(panel, router, view, c)
        return
    if what == "group":                         # plan 40 T2
        imgui.push_id(f"graph.side.{obj.id}")
        try:
            _group_side(panel, st, view, obj)
        finally:
            imgui.pop_id()
        return
    n = obj
    imgui.push_id(f"graph.side.{n.id}")
    try:
        _node_side(panel, st, view, router, n)
    finally:
        imgui.pop_id()


def _node_side(panel, st: dict, view: graphview.View, router, n: graphview.VNode) -> None:
    """A selected node's side panel (the owner, 2026-10-24): its page's
    chip (`home_page`), then an effect's strip, a modifier's editor, or its
    label and status, a switch's chips (`_switch_block`) and a row per
    param (`_param_rows`); a node with no param keeps its patched ports'
    readings in words."""
    _open_chip(panel, n)
    node_mode_block(panel, n)
    if isinstance(n.ref, Effect):
        ui_fx.strip(panel, n.ref.effect)
        return
    m = router.table.modifier(n.id) if router is not None and n.kind == "modifier" else None
    if m is not None:                           # plan 28 N7: the MODIFIERS strip's editor
        ui._micro("modifier")
        if ui_routing.modifier_block(panel, router, m, stacked=True):
            ui_routing.remove_modifier(panel, m.id)
        return
    ui._micro(n.kind)
    if isinstance(n.ref, rgraph.Shape):
        _wireframe(panel)
    # plan 35 G (V2): a frame node's header says its id and its params' prefix
    imgui.text(graphview.side_head(n) if n.kind in graphview.FRAME_VKINDS else n.label)
    if n.status:
        imgui.push_text_wrap_pos(0.0)               # (a placeholder's says what to do: long)
        imgui.text_disabled(n.status.partition(" · id ")[0]
                            if n.kind in graphview.FRAME_VKINDS else n.status)
        imgui.pop_text_wrap_pos()
    if isinstance(n.ref, rgraph.SwitchNode):
        _switch_block(panel, view, n)
    if is_pad_node(panel, n):                   # the pad, drawn: what each control does
        if "ui.pad_view" in panel.reg:          # its readout (map, faithful, lanes, cockpit),
            panel._combo("ui.pad_view", width=-1)   # as on SYSTEM; the header steps them too
        ui_pad.inline(panel)
        if "pad.dial.left" in panel.reg:        # …and its sticks as dials, this deck's
            imgui.spacing()
            ui._micro("dials")
            panel._dials()
        return                                  # — the picture says what the port lines would
    if _param_rows(panel, st, n):
        return
    for port in n.ports:
        if port.patched:
            imgui.text_disabled(f"{port.name}: {_said(port.live)}")


def _node_desk(panel):
    """The panel's deck's `node_desk.NodeDesk`; None in a rig with none."""
    router = ui_routing.router_of(panel)
    return getattr(router.table, "node_desk", None) if router is not None else None


NODE_CHIP = "node mode"
OTHER_DECK_TIP = "It is on the other Deck: this brings it here. Its player stays where it is, and moving the player brings it back."
ASLEEP = "dormant: {role} is on the other Deck"
FILLS = {"gamepad": "sticks, triggers and free button pairs"}   # what a chip fills, by kind
RESTING = "{n} modulator route{s} at rest on these, back on leave"


def node_mode_words(nd, h, nid: str) -> list[str]:
    """What the side pane says of desk `h` on node `nid`: its map, in control order,
    then what stayed and what did not fit (`Fit.too_many`). Nothing is paged."""
    if h.node != nid:
        return []
    fit = h.fit
    out = [f"{nd.control_word(h.role, b)} → {b.words}" for b in h.rows]
    if fit.kept:
        out.append("mapped already: " + ", ".join(fit.kept))
    said = fit.too_many(nid)
    if said:
        out.append(said)
    deck = getattr(nd, "deck", None)
    if deck is not None:
        back = graphview.routes_held(deck.table, deck.reg, deck.router)     # (once a frame)
        mine = {r.target for r in h.rows}
        rest = sum(1 for b in deck.table.routes() if b.target in mine
                   and back.get(id(b)) == graphview.NODE_MODE_HOLDS)
    else:
        rest = 0
    if rest:
        out.append(RESTING.format(n=rest, s="" if rest == 1 else "s"))
    if not h.on_here:
        out.append(ASLEEP.format(role=h.role))
    return out


def _node_chip(panel, nd, h, nid: str, label: str, cid: str, tip: str) -> None:
    """A chip that enters: grey with the reason when it may not, and a refusal said."""
    why = nd.refusal(h.role, nid)
    imgui.begin_disabled(why is not None)
    hit = ui.chip(f"{label}##{cid}")
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        ui.tooltip(why or tip)
    if hit and why is None:
        said = nd.enter(h.role, nid)
        if said:
            panel.library.say(warning=said)


def node_mode_block(panel, n: graphview.VNode) -> None:
    """Entering node mode (plan 53 N1b, N2): a chip per controller a patch can point, on a
    selected node it can point at. An edit of the patch on the deck the panel looks
    at, one undo step; the controller comes here. The map below it, in the cable's colour,
    wrapped: what did not fit is listed whole, however narrow the pane."""
    nd = _node_desk(panel)
    if nd is None or not nd.pointable(n.id):
        return
    ink = KIND_COLOURS[graphview.NODE_MODE]
    for h in nd.held():
        cid = f"graph.side.node_mode.{h.role}"
        if h.node != n.id:
            tip = OTHER_DECK_TIP if not h.on_here else (
                f"Fill {h.role}'s {FILLS.get(h.kind, 'knobs and faders')} with this node's "
                "params, saved in this patch. One undo step.")
            _node_chip(panel, nd, h, n.id,
                       f"move {h.role} here" if h.node else f"point {h.role} here", cid, tip)
            continue
        if ui.lit_chip(f"{h.role} on this node · leave##{cid}", False, ink):
            nd.leave(h.role)
            continue
        # saved here, its player elsewhere: the operator's "you're on this for a while"
        if not h.on_here:
            _node_chip(panel, nd, h, n.id, f"bring {h.role} here", f"{cid}.bring", OTHER_DECK_TIP)
        imgui.push_style_color(imgui.Col_.text, ink)
        for line in node_mode_words(nd, h, n.id):
            imgui.text_wrapped(line)
        imgui.pop_style_color()


def is_pad_node(panel, n: graphview.VNode) -> bool:
    """Is `n` the node of the pad the panel's picture reads (`panel.pad`:
    the first gamepad entry with a controller now), whatever its role is called — plan 42
    lets it be "edge" or "xbox", not only "pad"? A second pad's node is
    not: the picture and its mappings are the primary pad's."""
    if n.kind != "device" or getattr(n.ref, "kind", "") != "gamepad":
        return False
    io = getattr(n.ref, "io", None)
    return io is not None and io is getattr(panel, "pad", None)


def wire_px(side: float, fb_scale: float) -> int:
    """The wireframe's square in framebuffer px: the box's logical `side`
    × the window's framebuffer scale (2 on a Retina screen), so it is drawn
    1:1 and stays sharp."""
    return max(16, round(side * max(fb_scale, 1.0)))


def _wireframe(panel) -> None:
    """The shape node's side panel: a black square as wide as the column
    (at most `WIRE_MAX`) holding the renderer's wireframe of the shape
    (`Renderer.want_wire`: the edges alone, drawn on the GPU at the end of
    each frame while this asks) — the renderer of the deck the panel is on.
    Black until its first picture, or with no renderer."""
    side = min(imgui.get_content_region_avail().x, WIRE_MAX)
    if side < 16.0:
        return
    p0 = imgui.get_cursor_screen_pos()
    imgui.dummy(imgui.ImVec2(side, side))
    if imgui.is_item_hovered():
        ui.tooltip(WIRE_TIP)
    p1 = imgui.ImVec2(p0.x + side, p0.y + side)
    dl = imgui.get_window_draw_list()
    dl.add_rect_filled(p0, p1, ui.u32(imgui.ImVec4(*THUMB_GROUND)))
    r = getattr(panel, "renderer", None)
    if r is None or not hasattr(r, "want_wire"):
        return
    r.want_wire(wire_px(side, imgui.get_io().display_framebuffer_scale.x))
    tex = r.wire_texture()
    if tex is None or getattr(tex, "glo", 0) == 0:
        return
    dl.add_image(imgui.ImTextureRef(tex.glo), p0, p1,
                 imgui.ImVec2(0, 1), imgui.ImVec2(1, 0))      # GL's rows: upside down in v


# ---------------------------------------------------------------- a node's controls (2026-10-24)

FOLD_AT = 12             # more param rows than this: each group under its own header
UNWIRED = imgui.ImVec4(0.58, 0.58, 0.61, 0.55)   # an input chip nothing feeds: faint
OPEN_TIP = ("Show this node's section in the side pane, with it selected there "
            "(its ← chip comes back here)")


def side_groups(panel, n: graphview.VNode) -> list[tuple[str, list[str]]]:
    """The node's param rows for the side panel, as (group, [param id]) in
    the order its ports are drawn: within a group the patched ports first,
    then the rest in port order. A param is drawn once (a macro's knob is
    two ports); an alias is left out (the param behind it is the row), and
    so is one the registry does not hold."""
    reg = panel.reg
    groups: dict[str, list[graphview.VPort]] = {}
    seen: set[str] = set()
    for port in n.ports:
        pid = port.param
        if pid is None or pid in seen or pid not in reg or reg[pid].alias:
            continue
        seen.add(pid)
        groups.setdefault(port.group, []).append(port)
    return [(g, [p.param for p in sorted(ports, key=lambda p: not p.patched)])
            for g, ports in groups.items()]


def _param_rows(panel, st: dict, n: graphview.VNode) -> bool:
    """Every param of node `n` as the panel's own row (the owner,
    2026-10-24: "I can see the ports … but I can't actually edit those
    things"): the same widgets, so an edit is the param's — undo, the
    loadable patch's dirt and the modulation as on every page. Several groups get a
    small header each; more than `FOLD_AT` rows fold each group under a
    collapsing header, the node's primary group (the first, the one that
    names it: the faces pattern's "pattern" run, 2026-10-27) and a group
    holding a patched port open at first, the open state kept per node
    (``st["side_open"]``). False: no param."""
    groups = side_groups(panel, n)
    if not groups:
        return False
    imgui.separator()
    fold = sum(len(pids) for _, pids in groups) > FOLD_AT
    opened = st.setdefault("side_open", {}).setdefault(n.id, {})
    patched = {p.group for p in n.ports if p.param is not None and p.patched}
    for g, pids in groups:
        name = group_title(g) or "params"
        if fold:
            if g not in opened:
                opened[g] = g in patched or g == groups[0][0]
            imgui.set_next_item_open(opened[g], imgui.Cond_.always)
            opened[g] = imgui.collapsing_header(f"{name} · {len(pids)}##fold.{g}")
            if not opened[g]:
                continue
        elif len(groups) > 1:
            ui._micro(name)
        for pid in pids:
            _param_row(panel, pid)
    return True


def _param_row(panel, pid: str) -> None:
    """One param in the side panel: `Panel._row` (a slider, or a combo for
    an enum) — a toggle its checkbox, a trigger its fire chip, a path its
    name, each beside the same label (whose menu is Learn / Unbind)."""
    p = panel.reg[pid]
    kind = panel._real(p).kind
    if kind in (Kind.CONTINUOUS, Kind.ENUM):
        panel._row(pid)
        return
    panel._label_cell(p.label)
    panel._ctx_label(p)
    if kind is Kind.TOGGLE:
        panel._check(pid, label="")
    elif kind is Kind.TRIGGER:
        panel._button(pid, label="fire", small=True)
    else:
        panel._path(pid)


def _page_of_group(group: str) -> str | None:
    """The section whose params are group `group` (`ui_pane.SECTIONS`)."""
    for key, _, groups, _ in ui_pane.SECTIONS:
        if group in groups:
            return key
    return None


def _media_sel(c: str):
    def sel(panel) -> None:
        from . import ui_media
        ui_media._state(panel)["sel"] = c
    return sel


def _fx_sel(name: str):
    def sel(panel) -> None:
        select_effect(panel, name)
    return sel


def _lfo_sel(k: int):
    def sel(panel) -> None:
        from . import ui_lfo
        ui_lfo.select(panel, k)
    return sel


def _env_sel(k: int):
    def sel(panel) -> None:
        from . import ui_seq
        ui_seq.open_strip(panel, k)
    return sel


def home_page(n: graphview.VNode):
    """The page node `n`'s controls live on, as (page key, selector): the
    selector, called with the panel, selects the node's item there (None:
    nothing to select) — the side panel's "open on <PAGE>" chip (the
    owner, 2026-10-24). None for a node with no page: a switch (the side
    panel is its control), a modifier (GRAPH is its editor), a macro, a
    controller. Pure: no imgui."""
    r = n.ref
    voice = graphview.voice_of(n.id)
    if voice is not None:
        scheme, k = voice
        return ("lfo", _lfo_sel(k)) if scheme == "lfo" else ("seq", _env_sel(k))
    if n.kind == graphview.SEQ:
        return ("seq", None)
    if n.kind == "analyzer":
        return ("analyzer", None)
    if n.kind == "device" and (n.role == "leap" or n.id == "device:leap"):
        return ("hands", None)
    if n.kind == "group":
        key = _page_of_group(n.id.partition(":")[2])    # the group's key; the label is words
        return (key, None) if key is not None else None
    # plan 35 G: by the wired frame's ids — `render:camera` (was `render:eye`),
    # a channel `render:channel.<c>`, All outputs the OUTPUT page with no
    # window picked, a copy FX with its original selected (`Copy.effect`)
    if n.id == f"render:{graphview.CAMERA}":
        return ("camera", None)
    if n.id == f"render:{rgraph.ALL_OUTPUTS}":
        return ("output", None)
    if isinstance(r, rgraph.MediaNode):
        return ("media", _media_sel(r.channel))
    if isinstance(r, Effect):
        return ("fx", _fx_sel(r.effect))
    if isinstance(r, rgraph.PatternNode):
        return ("faces", None)
    if isinstance(r, rgraph.BackdropNode):
        return ("media", None)
    if isinstance(r, rgraph.Shape):
        return ("view", None)
    if isinstance(r, (rgraph.History, rgraph.EchoNode, rgraph.DreamNode)):
        return ("lookback", None)
    if isinstance(r, (rgraph.Hands, rgraph.HandsLayer, rgraph.Readout)):
        return ("hands", None)
    if isinstance(r, rgraph.Output) or n.kind == "output":
        return ("output", None)
    return None


def open_on(panel, home) -> None:
    """Show `home`'s section in the pane (through ``ui.page``) with its item
    selected there."""
    key, sel = home
    if sel is not None:
        sel(panel)
    ui_pane.show(panel, key)


def _open_chip(panel, n: graphview.VNode) -> None:
    home = home_page(n)
    if home is None:
        return
    if ui.chip(f"open on {home[0].upper()}##graph.side.open"):
        open_on(panel, home)
    if imgui.is_item_hovered():
        ui.tooltip(OPEN_TIP)


def switch_feeds(view: graphview.View, n: graphview.VNode) -> list[str | None]:
    """What feeds each of switch node `n`'s inputs, in1 … in8: the label
    of the node its render cable comes from (`media.c`, `acid.2`), None
    for an input nothing is wired to."""
    name = getattr(n.ref, "name", n.label)
    ports = {f"rin:{name}/{p}": k for k, p in enumerate(rgraph.SWITCH_PORTS)}
    out: list[str | None] = [None] * len(rgraph.SWITCH_PORTS)
    for c in view.cables:
        k = ports.get(c.dst_port) if c.kind == "render" else None
        if k is None:
            continue
        hit = view.owner(c.src_port)
        out[k] = hit[0].label if hit is not None else c.src_port.partition(":")[2]
    return out


def switch_chips(feeds: list[str | None]) -> list[tuple[int, str, str]]:
    """The switch block's chips as (pick, label, hover): off, then
    ``k · <what feeds in<k>>`` (``—`` for nothing)."""
    chips = [(0, "off", "off: the faces show the pattern, the backdrop nothing")]
    for k, feed in enumerate(feeds, 1):
        tip = (f"in{k}: {feed}" if feed else
               f"in{k}: nothing wired — picked, the faces show the pattern, "
               "the backdrop nothing")
        chips.append((k, f"{k} · {feed or '—'}", tip))
    return chips


def _switch_block(panel, view: graphview.View, n: graphview.VNode) -> None:
    """A switch's control by mouse (the owner, 2026-10-24: "the switch
    node actually doesn't seem to have any controls anywhere"): `off` on
    its own line, then the eight inputs two to a line, each named by what
    feeds it and fitted to its chip, the pick lit; an unwired input faint
    but still a pick. A click is the param's write (`Param.set`, as its
    combo does), so it is one undo step. Its `select` row follows with the
    other rows."""
    pid = params.switch_id(n.ref.name)
    if pid not in panel.reg:
        return
    p = panel._real(panel.reg[pid])
    try:
        cur = int(p.value)
    except (TypeError, ValueError):
        cur = 0
    feeds = switch_feeds(view, n)
    gap = imgui.get_style().item_spacing.x
    w = max((imgui.get_content_region_avail().x - gap) / 2, 40.0)
    pad = 2 * ui.CHIP_PAD.x
    imgui.separator()
    for k, label, tip in switch_chips(feeds):
        if k == 0:
            size = imgui.ImVec2(2 * w + gap, 0)
        else:
            size = imgui.ImVec2(w, 0)
            if k % 2 == 0:
                imgui.same_line()
        unwired = k > 0 and feeds[k - 1] is None
        text = ui.fit_text(label, size.x - pad)
        if ui.lit_chip(f"{text}##graph.side.{n.ref.name}.{k}", cur == k,
                       UNWIRED if unwired else None, size):
            p.set(k)
        if imgui.is_item_hovered():
            ui.tooltip(tip)


def _route_row(panel, router, view: graphview.View, c: graphview.VCable) -> None:
    """A cable in the side pane: a route as its ROUTING row (`ui_routing._row`,
    the one table — its × deletes it, one undo step); anything else in words."""
    if c.kind == "route" and router is not None:
        rows = router.table.routes()
        k = next((i for i, b in enumerate(rows) if b is c.ref), None)
        if k is not None:
            if ui_routing._row(panel, router, c.ref, k):
                undo.push(f"delete route {c.ref.source} → {c.ref.target}")
                router.table.remove(c.ref)
            return
    imgui.text_wrapped(cable_tip(view, c))


def route_rows(panel, rows) -> None:
    """Routes `rows` as the side pane lists a bundle's (plan 28 N7): each
    its ROUTING row (`ui_routing._row`), under its own id, the source
    combo's list built once for the lot (as ROUTING's page did)."""
    router = ui_routing.router_of(panel)
    if router is None:
        return
    rst = ui_routing._state(panel)
    rst["sources"] = ui_routing._sources(panel, router) if rows else None
    view = _state(panel)["view"]
    try:
        for i, b in enumerate(rows):
            imgui.push_id(f"rows{i}")
            if i:
                imgui.separator()
            _route_row(panel, router, view, graphview.VCable("", "", "", ref=b, kind="route"))
            imgui.pop_id()
    finally:
        rst["sources"] = None                   # this draw's only


def timing_line(panel) -> str:
    """The SYSTEM page's line for this page: its draw's median over the
    last draws, in ms — "" until it has been drawn."""
    st = panel.__dict__.get(STATE)
    times = sorted(st["times"]) if st else []
    if not times:
        return ""
    v = st["view"]
    size = f"  ({len(v.nodes)} nodes, {len(v.cables)} cables)" if v is not None else ""
    return f"graph draw: {times[len(times) // 2] * 1000:.2f} ms median{size}"


# ---------------------------------------------------------------- editing (plan 28 N3)
#
# The page's edits, as plain functions over the panel (the tests drive
# these, as test_ui_routing drives ROUTING's): each builds a
# `graphview.Edit` on the page's view and the router's table, names one
# undo step before it changes anything, and settles what came back — a
# `graphview.Ask` becomes ROUTING's Replace / Keep prompt (`ui_routing.ask`),
# a `graphview.Refusal` the head's note. The canvas's gestures below call
# them; `CREATE` / `DELETE` are the dispatch by type N4 extends.

EDIT_HINT = ("drag pin to pin: a cable  ·  drop a node on a lit cable: into it "
             "(⌘-drag one already wired)  ·  Option-drag: select cables  ·  "
             "right-click: Learn, insert, add  ·  Delete: the selection")
MENU = "##graph.menu"
REFUSED_RGB = (1.0, 0.45, 0.35, 1.0)       # ui.WARN: a drag the table would refuse


def edit_of(panel, view: graphview.View | None = None) -> graphview.Edit | None:
    """The page's `Edit` on the router's table (None: no router)."""
    router = ui_routing.router_of(panel)
    if router is None:
        return None
    if view is None:
        view = view_of(panel)
    table = router.table
    profile = ui.apc40 if getattr(table, "profile", None) == "apc40" else None
    # plan 28 N4: render requests reach the loadable patch's graph too (no undo push
    # of their own here: `_act` pushed one; the canvas's render gestures use
    # `render_edit` instead)
    lib = getattr(panel, "library", None)
    e = graphview.Edit(table, panel.reg, router, view, profile,
                       graph=getattr(getattr(lib, "loaded_patch", None), "graph", None),
                       render=getattr(getattr(panel, "renderer", None), "_graph", None))
    e.show = getattr(lib, "install", None)              # (plan 36 T1: the meta controller's wires)
    # row 563: a modifier or a voice deleted leaves its group at once
    e.loaded_patch = getattr(lib, "loaded_patch", None)
    return e


def _settle(panel, res):
    """Settle what an edit returned: an Ask puts up the prompt, a Refusal
    is the head's note; anything else clears the note. Returns `res`."""
    st = _state(panel)
    if isinstance(res, graphview.Ask):
        ui_routing.ask(panel, res.old, res.new, res.commit)
        _note(st, None)
    elif isinstance(res, PairAsk):
        ui_routing.ask_pair(panel, res)
        _note(st, None)
    elif isinstance(res, Binding) and res.scheme == PAIR_SCHEME and res.op == "step":
        _note(st, None)                      # a stepped param's row: not this deck's stack
        ui_routing.say_pair(panel, f"{row_words(res)} → {res.target}; {META_UNDO}")
    elif isinstance(res, graphview.Refusal):
        _note(st, str(res))
    else:
        _note(st, None)
    return res


def _act(panel, label: str, why: str | None, fn, *, load: bool = False):
    """One edit: refused before anything moves (`why`), else one undo step
    named `label`, then `fn()` settled by `_settle`. `load`: the step also
    carries the library's marks (the groups and the layout; row 563: every
    node's deletion, so undoing it puts a member back in its group)."""
    if why is not None:
        return _settle(panel, graphview.Refusal(why))
    undo.push(label, load=load)
    return _settle(panel, fn())


def _name(view: graphview.View | None, pin: str) -> str:
    hit = view.owner(pin) if view is not None else None
    if hit is None or hit[1] is None:
        return pin.partition(":")[2] or pin
    return hit[1].param or hit[1].addr or f"{hit[0].label} {hit[1].name}"


def connect(panel, a: str, b: str):
    """A cable dragged from pin `a` to pin `b` (either order): a route, a
    setter row, a macro's subscriber, a modifier's input, or a cable's end
    moved (`graphview.Edit.connect`)."""
    e = edit_of(panel)
    if e is None:
        return None
    return _act(panel, f"connect {_name(e.view, a)} → {_name(e.view, b)}",
                e.refusal(a, b), lambda: e.connect(a, b))


def disconnect(panel, cable: graphview.VCable):
    """Delete a cable (`graphview.Edit.disconnect`): a route and its depth
    subscribers, a loadable patch desk row, a subscriber, a modifier's input."""
    e = edit_of(panel)
    if e is None:
        return None
    return _act(panel, f"delete cable {cable.id}", None, lambda: e.disconnect(cable))


def insert_modifier(panel, cable: graphview.VCable, kind: str):
    """A modifier (`kind`, or an existing one's id) into `cable`."""
    e = edit_of(panel)
    if e is None:
        return None
    return _act(panel, f"insert {kind} into {cable.id}", None,
                lambda: e.insert_modifier(cable, kind))


def _place_new(panel, nid: str, at) -> None:
    """A node the picker made: revealed (`reveal_node`, 2026-10-31) and, when
    the picker opened at a point, put there (the loadable patch's layout:
    modifiers and macros are the loadable patch's)."""
    reveal_node(_state(panel), nid)
    pre, _ = _layouts(panel)
    if at and pre is not None:
        px, py = panned(_state(panel))          # the menu's point is the panned canvas's
        pre[nid] = [round(at[0] - px), round(at[1] - py)]


def _place_group(panel, e: graphview.Edit, at) -> None:
    """A starter's new nodes (plan 36 T5, `Edit.placed`) laid left to right
    from where the menu opened (`graphview.chain_layout`), in the step the
    starter pushed; with no point, the last add's node alone, as before."""
    if e.placed:
        if at:
            for nid, xy in graphview.chain_layout(e.placed, at).items():
                _place_new(panel, nid, xy)
    elif e.added:
        _place_new(panel, f"render:{e.added}", at)


# a new loadable patch's chain sits this far in from the view's top-left corner
IN_VIEW_MARGIN = (graphview.GAP, graphview.TITLE_H)


def in_view(panel) -> tuple[float, float]:
    """Where a new loadable patch's chain goes (plan 36 T5, W5: "laid out where you
    are looking"), in layout units: the canvas point at the GRAPH page's
    view's top-left corner, last drawn (`st["seen"]`; the canvas origin
    before the page has drawn), in by `IN_VIEW_MARGIN`, less the page's
    pan (`st["pan"]`: a stored position is drawn moved by it)."""
    st = _state(panel)
    sx, sy = st.get("seen") or (0.0, 0.0)
    px, py = panned(st)
    return (round(sx + IN_VIEW_MARGIN[0] - px), round(sy + IN_VIEW_MARGIN[1] - py))


def add_modifier(panel, kind: str, at=None):
    """The picker's "+ modifier ▸ <kind>": a new node, placed at `at`."""
    e = edit_of(panel)
    if e is None:
        return None
    res = _act(panel, f"add modifier {kind}", None, lambda: e.add_modifier(kind))
    if isinstance(res, modifiers.Modifier):
        _place_new(panel, res.id, at)
    return res


def show_macro(panel, mid: str, at=None):
    """The picker's "+ macro ▸ <n>": the macro onto the canvas (its label set)."""
    e = edit_of(panel)
    if e is None:
        return None
    res = _act(panel, f"show {mid}", None, lambda: e.show_macro(mid))
    if not isinstance(res, graphview.Refusal):
        _place_new(panel, mid, at)
    return res


def remove_node(panel, nid: str):
    """Delete a node (`graphview.Edit.remove_node`): a modifier, a macro, a
    render node, an LFO or an extra envelope (plan 31 G1: through its bank,
    one undo step — the bank's membership is in the undo state). A lane
    envelope (1–5) is refused before any undo step is pushed."""
    e = edit_of(panel)
    if e is None:
        return None
    hit = graphview.voice_of(nid)
    why = voice_refusal(e.view.node(nid) if e.view is not None else None, nid) if hit else None
    # row 563: a delete's step carries the marks, as render_edit's and the
    # group verbs' do — the node may be a group member, and its undo puts
    # it back in its group
    res = _act(panel, f"delete node {nid}", why, lambda: e.remove_node(nid), load=True)
    if not isinstance(res, (graphview.Refusal, graphview.Ask)):   # 2026-10-31: its reveal goes
        _state(panel).setdefault("revealed", set()).discard(nid)
    return res


def voice_refusal(n, nid: str | None = None) -> str | None:
    """Why a bank voice's node may not be deleted (a lane envelope), or None."""
    nid = n.id if n is not None else nid or ""
    hit = graphview.voice_of(nid)
    if hit is not None and hit[0] == "env" and hit[1] in graphview.LANE_ENVS:
        return graphview.LANE_ENV_KEPT.format(label=n.label if n is not None else nid)
    return None


def add_refusal(panel, scheme: str) -> str | None:
    """Why the picker's "+ LFO" / "+ envelope" is greyed: no such bank, or
    the bank at its cap; None when one can be added."""
    bank = graphview.bank_of(ui_routing.router_of(panel), scheme)
    if bank is None:
        return graphview.NO_BANK.format(what=graphview.BANK_WORDS[scheme][0])
    return graphview.bank_refusal(bank, scheme)


def add_voice(panel, scheme: str, at=None):
    """The picker's "LFO" / "envelope" (plan 31 G1): a new voice in its
    bank (`graphview.Edit.add_voice`), one undo step, placed at `at` in the
    loadable patch's layout (a bank's membership is the loadable patch's). Its node id, or
    the Refusal at the cap."""
    e = edit_of(panel)
    if e is None:
        return None
    res = _act(panel, f"add {graphview.BANK_WORDS[scheme][0]}", add_refusal(panel, scheme),
               lambda: e.add_voice(scheme))
    if isinstance(res, str) and not isinstance(res, graphview.Refusal):
        _place_new(panel, res, at)
    return res


# ---- the param menu's "Route from ▸" (the owner, 2026-10-24, 2026-10-28) ----
#
# "There is no Learn option for routing one of the LFOs there or any of the
# envelopes there, and I do want to have that ability." Not a Learn — a
# Learn arms and waits for a gesture, and an LFO makes none — but a
# submenu of its own in the one param menu (`Panel._ctx_learn`), so every
# page has it. One submenu per kind of source (the owner, 2026-10-28:
# "instead of listing all the LFOs and envelopes together, it should have
# an LFO thing you can mouse over, a macro thing you can mouse over, and
# an envelope thing … because you can have up to six … we might add more
# things to route from"): **LFO ▸** and **envelope ▸** hold the bank's
# voices then a new one; **macro ▸** holds the meta controller's eight knobs by their
# labels. A voice pick is exactly the cable a drag on this page makes:
# the voice's ``out:`` pin into the param's ``mod`` stub through
# `Edit.connect_value`, its refusal, its Ask (ROUTING's Replace / Keep)
# and its undo step named as `connect` names it. A macro pick is the
# macro's ``bus:`` pin into the param's ``base`` stub — a base subscriber
# (`Edit.subscribe`, from where the param sits to its fader's end,
# `routing.base_sub`) — on a param a base subscriber may name
# (`routing.base_refusal`: a persisted patch param, never a macro),
# whether or not a lane may drive it; an idle macro picked gets its label
# first (`Edit.show_macro`, as the canvas's picker gives it), in the same
# undo step.

ROUTE_FROM = "Route from"
NEW_VOICE = "new {what}"
MACRO = "macro"
# the submenus, in order, and their titles
SECTIONS = (*graphview.BANK_SCHEMES, MACRO)
SECTION_WORDS = {**{s: graphview.BANK_WORDS[s][0] for s in graphview.BANK_SCHEMES},
                 MACRO: "macro"}


def voice_label(router, scheme: str, k: int) -> str:
    """Voice `k` (1-based) of bank `scheme` as its node is titled: the
    router's published label, else "LFO 3" / "env 3" (`graphview.build`)."""
    names = list((getattr(router, "labels", {}) or {}).get(scheme) or [])
    if k - 1 < len(names) and names[k - 1]:
        return names[k - 1]
    return f"{'LFO' if scheme == 'lfo' else scheme} {k}"


def voice_pin(router, scheme: str, k: int) -> str:
    """The ``out:`` pin voice `k` of `scheme` leaves from: ``out:lfo:0``
    for LFO 1 — the address the router names lane k − 1 by
    (`Router.address`), as `graphview.build` gives the node's port."""
    addr = router.address(scheme, k - 1) if router is not None else f"{scheme}:{k - 1}"
    return f"out:{addr}"


def macro_label(router, mid: str) -> str:
    """Macro `mid` as ROUTING's strip and the canvas name it: its label,
    else "macro 3" (what `Edit.show_macro` would give it)."""
    m = (router.table.macros if router is not None else {}).get(mid)
    return m.label if m is not None and m.label else f"macro {mid.rpartition('.')[2]}"


def _bank_items(panel, router, p, scheme: str) -> list[tuple]:
    on = {router.lane(b.source) for b in router.table.routes_to(p.id)}
    items = [(voice_label(router, scheme, k), voice_pin(router, scheme, k),
              (scheme, k - 1) in on, None)
             for k in graphview.bank_ids(router, panel.reg, scheme)]
    why = add_refusal(panel, scheme)
    items.append((why or NEW_VOICE.format(what=graphview.BANK_WORDS[scheme][0]),
                  scheme, False, why))
    return items


def _macro_items(router, p, macros) -> list[tuple]:
    subs = router.table.macros
    return [(macro_label(router, q.id), f"bus:{q.id}",
             q.id in subs and any(s.base == p.id for s in subs[q.id].subs), None)
            for q in macros]


def route_from_items(panel, p) -> dict[str, list[tuple]] | None:
    """The submenus for the real param `p`, ``{section: items}`` in
    `SECTIONS`' order with only the sections offered, or None when none
    is (no router; a trigger). "lfo" and "env" come on a param a lane
    may drive (`ui_routing.route_target`: modulatable, no meta param); "macro" on one a base subscriber may name
    (`base_refusal` None, not a macro, no text) where the meta controller has macros.
    Each item is ``(label, pin, checked, why)``: a voice or a macro by its
    label and its ``out:`` / ``bus:`` pin, checked when it already lands
    on `p` (a route from the voice; a base subscriber of the macro); then,
    in a bank's section, one ``(label, scheme, False, why)`` for its "new"
    item, `why` the refusal words that grey it (the bank full, no bank),
    else None."""
    router = ui_routing.router_of(panel)
    if router is None or p is None or p.kind in (Kind.TRIGGER, Kind.TEXT):
        return None
    out: dict[str, list[tuple]] = {}
    if ui_routing.route_target(p):
        for scheme in graphview.BANK_SCHEMES:
            out[scheme] = _bank_items(panel, router, p, scheme)
    macros = list(panel.reg.group(MACRO))
    if macros and not is_macro(p.id) and base_refusal(p.id, panel.reg) is None:
        out[MACRO] = _macro_items(router, p, macros)
    return out or None


def _footer_refusal(panel, res):
    """A refusal said where any page shows it: GRAPH's head (`_settle`
    put it there) and the footer's slot (`Library.say`) — the menu is
    open on every page, and only GRAPH draws its head."""
    if isinstance(res, graphview.Refusal):
        lib = getattr(panel, "library", None)
        if lib is not None and hasattr(lib, "say"):
            lib.say(warning=str(res))
    return res


def route_from(panel, src: str, pid: str):
    """The cable `src` → `pid`, as a drag on the page makes it (`connect`'s
    label, refusal and settling) through `Edit.connect_value`: a voice's
    ``out:`` pin into the ``mod`` stub (a route), a macro's ``bus:`` pin
    into the ``base`` stub (a base subscriber; an idle macro labelled
    first, `Edit.show_macro`, in the one step) — the route, an Ask (the
    prompt held), or a Refusal said (`_footer_refusal`)."""
    e = edit_of(panel)
    if e is None:
        return None
    is_bus = graphview.pin_kind(src) == "bus"
    dst = f"{graphview.BASE if is_bus else graphview.MOD}:{pid}"

    def make():
        if is_bus:
            mid = src.partition(":")[2]
            m = e.table.macros.get(mid)
            if m is None or m.empty:
                e.show_macro(mid)
        return e.connect_value(src, dst)

    res = _act(panel, f"connect {_name(e.view, src)} → {_name(e.view, dst)}",
               e.refusal(src, dst), make)
    return _footer_refusal(panel, res)


def route_from_new(panel, scheme: str, pid: str):
    """"new LFO" / "new envelope": GRAPH's picker (`add_voice`), then the
    new voice's cable into `pid` (`route_from`). In one frame, so the two
    are one undo step (`undo.Undo.push`: a second push before a tick is
    the same action) under the picker's label, "add LFO"."""
    nid = add_voice(panel, scheme)
    if not isinstance(nid, str) or isinstance(nid, graphview.Refusal):
        return _footer_refusal(panel, nid)
    hit = graphview.voice_of(nid)
    return route_from(panel, voice_pin(ui_routing.router_of(panel), *hit), pid)


def route_from_menu(panel, p) -> None:
    """Draw "Route from ▸" for the real param `p` inside the open param
    menu (`Panel._ctx_learn`): one submenu per section offered
    (`route_from_items`) — LFO ▸, envelope ▸, macro ▸ — nothing where none
    is. A checked item already lands on `p`: a click on it does nothing.
    Every `begin_menu` here is closed here."""
    sections = route_from_items(panel, p)
    if not sections or not imgui.begin_menu(ROUTE_FROM):
        return
    for section, items in sections.items():
        if not imgui.begin_menu(SECTION_WORDS[section]):
            continue
        picks = [it for it in items if it[1] not in graphview.BANK_SCHEMES]
        for i, (label, pin, checked, _) in enumerate(picks):
            clicked, _ = imgui.menu_item(f"{label}##route_from.{section}.{i}", "", checked)
            if clicked and not checked:
                route_from(panel, pin, p.id)
        news = items[len(picks):]
        if news:
            imgui.separator()
        for label, scheme, _, why in news:
            if imgui.menu_item_simple(f"{label}##route_from.new.{scheme}", enabled=why is None) \
                    and why is None:
                route_from_new(panel, scheme, p.id)
        imgui.end_menu()
    imgui.end_menu()


def dropped(panel, view: graphview.View, nid: str, centre, size=None,
            lift: bool = False, zoom: float = 1.0) -> graphview.VCable | None:
    """A node let go at `centre` (canvas units; `size` its box): what
    `onto_plan` lights while it is dragged happens (`drop_plan`). A free
    picture node goes onto the brightest picture cable under it — the one
    through its box nearest its centre (`Edit.place_node`, one undo step)
    — the cable's picture into its inlet, its picture on into the port
    the cable fed; one with several inlets asks which first; a source
    takes the cable over; a free modifier goes onto the brightest route or
    input (`insert_modifier`). A node already wired is only moved when
    `lift` (⌘ held as it is let go: 2026-10-29): out of its place, the
    wires either side of it closed over it, onto the cable — reordering
    the run; without ⌘ a drag only moves it on the canvas. Two cables as
    near as each other: a chooser opens (`st["onto"]`, `put_onto`) and
    nothing changes until one is picked. Returns the cable it went into,
    or None. `zoom` (canvas units a screen px) grows how near is near:
    `graphview.drop_reach`."""
    plan = onto_plan(panel, view, nid, centre, size, lift, zoom)
    return None if plan is None else drop_plan(panel, view, plan)


def drop_plan(panel, view: graphview.View, plan: dict) -> graphview.VCable | None:
    """What `plan` (`onto_plan`'s) said letting go does, done: the chooser
    for a tie, else the node onto its best cable (`put_onto`); nothing
    with nothing lit. Returns the cable it went into, or None."""
    nid = plan["node"]
    if plan["best"] is None:
        return None
    if plan["tie"]:
        _state(panel)["onto"] = {"node": nid, "cables": plan["tie"], "open": True}
        return None
    c = next((x for x in view.cables if x.id == plan["best"]), None)
    return None if c is None else put_onto(panel, view, nid, c)


ONTO_TIE = 1.0          # canvas units: two cables this near each other's distance are a tie
PICTURE_ON_VALUE = "{node} goes onto a picture cable, not a route"
MOD_ON_PICTURE = "a modifier goes onto a route or a modifier's input, not a picture cable"
THROUGH_DROP = "{through} — turn {it} on to splice here"


def _cold(panel, st: dict, view: graphview.View, n: graphview.VNode,
          never: str | None) -> set[str]:
    """The cables dragged node `n` could never go onto, wherever it is let
    go (2026-11-01: drawn undimmed while it is dragged, `_cable`): for a
    picture node every value cable, every through wire and every render
    cable `onto_refusal` refuses (the meta controller's bus, a mask, a depth, a pin's);
    for a node that never splices (`never`) or a modifier, every render
    cable and through wire, and for a modifier every cable with no source
    to take. Kept across the drag's frames while the view and the node
    hold (`st["onto_cold"]`): the refusals are asked once, not a frame."""
    key = (id(view), n.id, len(view.cables), len(st.get("throughs", {})))
    held = st.get("onto_cold")
    if held is not None and held[0] == key:
        return held[1]
    cold: set[str] = set(st.get("throughs", {}))
    e = render_edit(panel) if n.kind in graphview.FRAME_VKINDS and never is None else None
    for c in view.cables:
        if n.kind == "modifier":
            if c.kind in ("render", graphview.NODE_MODE) or not c.addr:
                cold.add(c.id)
        elif c.kind != "render" or never is not None or graphview.onto_refusal(e, c) is not None:
            cold.add(c.id)
    st["onto_cold"] = (key, cold)
    return cold


def onto_plan(panel, view: graphview.View, nid: str, centre, size=None,
              lift: bool = False, zoom: float = 1.0) -> dict | None:
    """What letting node `nid` (its box `size`) go at `centre` would do — what the drag
    lights (`_drag_preview`) and what the drop does (`drop_plan`), so the two
    never disagree. None: a node no drop moves (not a picture node or a
    modifier, a wired modifier). Else ``{"node", "hot", "lift", "lit",
    "best", "tie", "refused", "hint", "cold", "ask", "source"}``: `hot`,
    whether a drop can do anything (a free node, or a wired one with ⌘:
    the cables that could take it dim around it while it is dragged); the
    cables it may go onto through its box, nearest its centre first
    (`lit`), the one it will (`best`), the cables as near as that one when
    there are two or more (`tie`: the chooser's), the cables under it it
    may not go onto with why (`refused`: a value cable, a bus cable, a
    through wire over an off effect, a mask; or every cable, for a node
    that never splices — a geometry, a matte, a window), the cables it
    could never go onto wherever it is (`cold`: drawn undimmed); `lift`, a
    wired node lifted with ⌘; `ask`, the inlets the drop will ask between
    (a composite's, a switch's); `source`, a node that takes the cable
    over (a channel). `hint`: a wired node dragged without ⌘ — ``"over"``
    a cable it could go onto, else ``"away"`` (the drag says to hold ⌘
    either way)."""
    n = view.node(nid)
    if n is None:
        return None
    st = _state(panel)
    pins = st["pin_xy"]
    mine = view.cables_of(nid)
    near = graphview.drop_reach(zoom)           # never under NEAR screen px zoomed out
    plan = {"node": nid, "hot": not mine or lift, "lift": False, "lit": [], "best": None,
            "tie": [], "refused": {}, "hint": "", "cold": set(), "ask": (), "source": False}
    kinds = graphview.CABLE_KINDS               # every cable: the wrong ones refused in words
    if n.kind in graphview.FRAME_VKINDS:
        name = n.id.partition(":")[2]
        never = graphview.drop_refusal(name, n.label)
        cold = _cold(panel, st, view, n, never)
        e = render_edit(panel) if never is None else None
        ok, refused = [], {}
        for d, c in graphview.cables_near(view, pins, centre, near, kinds=kinds,
                                          skip={nid}, size=size):
            if c.kind != "render":
                refused[c.id] = never or PICTURE_ON_VALUE.format(node=n.label)
            elif c.id in cold:
                refused[c.id] = never or graphview.onto_refusal(e, c) or ""
            else:
                ok.append((d, c))
        plan["ask"] = graphview.inlet_choices(name)
        plan["source"] = graphview.is_source(name)
    elif n.kind == "modifier" and not mine:     # (a wired modifier is not lifted)
        never = None
        cold = _cold(panel, st, view, n, None)
        ok, refused = [], {}
        # (only a cable with a source to take: `insert_modifier`'s rule)
        for d, c in graphview.cables_near(view, pins, centre, near, kinds=kinds,
                                          skip=(nid,), size=size):
            if c.kind == "render":
                refused[c.id] = MOD_ON_PICTURE
            elif c.kind in ("route", "input") and c.addr:
                ok.append((d, c))
    else:
        return None
    # a through wire over an off effect is drawn, not a cable: under the
    # node it says what to turn on (`st["throughs"]`, `graphview.throughs`)
    thr = st.get("throughs", {})
    if thr:
        tv = graphview.View(nodes=view.nodes, cables=list(thr.values()), pins=view.pins)
        for d, c in graphview.cables_near(tv, pins, centre, near, kinds=(graphview.THROUGH,),
                                          skip={nid}, size=size):
            plural = "effects:" in c.label
            refused.setdefault(c.id, never or THROUGH_DROP.format(
                through=c.label, it="them" if plural else "it"))
    plan["cold"] = cold
    plan["refused"] = refused
    if never is not None:                       # a node that never splices: said, never hot
        plan["hot"] = False
        return plan
    if mine and not lift:
        plan["hint"] = "over" if ok else "away"
        return plan
    plan["lit"] = [c.id for _, c in ok]
    if ok:
        plan["best"] = ok[0][1].id
        tie = [c.id for d, c in ok if d - ok[0][0] < ONTO_TIE]
        plan["tie"] = tie if len(tie) > 1 else []
    plan["lift"] = bool(mine)
    return plan


def lift_held() -> bool:
    """⌘ (or Ctrl) held: a wired node's drag lifts it out of its chain."""
    io = imgui.get_io()
    return bool(io.key_ctrl or io.key_super)


ONTO_TIP = "let go: {node} onto {cable}"
LIFT_ONTO_TIP = "let go: {node} out of its chain, onto {cable}"
ASK_TIP = ", then pick {choices}"
TAKE_TIP = "let go: {node} feeds {dst} instead of {src}"
LIFT_TAKE_TIP = "let go: {node} out of its place, feeds {dst} instead of {src}"
ONTO_TIE_TIP = "let go: pick which cable {node} goes onto"
LIFT_HINT = "hold ⌘ to move {node} out of its chain and onto this cable"
LIFT_AWAY = "hold ⌘ to lift {node} out of its chain, then let go on a cable"


def drag_words(view: graphview.View, plan: dict) -> str:
    """What the drag's tooltip says for `plan` (`onto_plan`): what letting
    go does — onto which cable, then which inlet it will ask (a
    composite: "then pick under or over"), or which port a source takes
    over — or, with nothing lit, the nearest refusal's words."""
    n = view.node(plan["node"])
    node = n.label if n is not None else plan["node"]
    if plan["hint"]:
        return (LIFT_HINT if plan["hint"] == "over" else LIFT_AWAY).format(node=node)
    if plan["tie"]:
        return ONTO_TIE_TIP.format(node=node)
    if plan["best"] is not None:
        c = next((x for x in view.cables if x.id == plan["best"]), None)
        src, dst = graphview.onto_sides(view, c) if c is not None else (plan["best"], "")
        if plan.get("source"):
            return (LIFT_TAKE_TIP if plan["lift"] else TAKE_TIP).format(node=node, src=src,
                                                                        dst=dst)
        words = (LIFT_ONTO_TIP if plan["lift"] else ONTO_TIP).format(node=node,
                                                                     cable=f"{src} → {dst}")
        if plan.get("ask"):
            words += ASK_TIP.format(choices=graphview.choices_words(plan["ask"]))
        return words
    return next(iter(plan["refused"].values()), "")


def _drag_preview(panel, st: dict, view: graphview.View) -> None:
    """While one picture or modifier node is dragged: what letting it go
    would do (`onto_plan`), kept in `st["onto_lit"]` for the cables drawn
    this frame and in `st["press_plan"]` for the release (`_moved` acts on
    the last plan lit, so the glow and the drop never disagree: the
    editor's node position snaps to its grid, the pointer's does not),
    and its words said beside the pointer.
    The node is the one the mouse went down on (`st["press"]`), where it
    is now its place then plus how far the pointer has come — never a
    guess from which positions changed. Nothing while several selected
    nodes move together."""
    st["onto_lit"] = None
    left = imgui.MouseButton_.left
    if imgui.is_mouse_clicked(left):
        st["press"] = _pressed(st, view)
        st["press_plan"] = None
    press = st.get("press")
    if (press is None or not imgui.is_mouse_down(left) or st.get("patch_drag")
            or not imgui.is_mouse_dragging(left) or _with_others(st, press[0])):
        return
    nid, (mx, my), (x0, y0) = press
    m = imgui.get_mouse_pos()                  # canvas units, inside the editor
    x, y = x0 + m.x - mx, y0 + m.y - my
    size = ed.get_node_size(ed.NodeId(_id(st, "n:" + nid)))
    plan = onto_plan(panel, view, nid, (x + size.x / 2, y + size.y / 2),
                     (size.x, size.y), lift_held(), st.get("zoom", 1.0))
    if plan is None:
        return
    st["onto_lit"] = plan
    st["press_plan"] = plan
    words = drag_words(view, plan)
    if words:
        _drag_tip(words)


def _pressed(st: dict, view: graphview.View):
    """The mouse just went down: on a picture node (any render-side node:
    `graphview.FRAME_VKINDS` — one that never splices is refused in words
    as it is dragged) or a modifier node (not on one of its pins — that is
    a cable's drag), ``(node id, the pointer, the node's place)``, both
    in canvas units; else None."""
    if ed.get_hovered_pin().id():
        return None
    name = st["names"].get(ed.get_hovered_node().id(), "")[2:]
    n = view.node(name) if name else None
    if n is None or not (n.kind == "modifier" or n.kind in graphview.FRAME_VKINDS):
        return None
    m = imgui.get_mouse_pos()
    p = ed.get_node_position(ed.NodeId(_id(st, "n:" + n.id)))
    return n.id, (m.x, m.y), (p.x, p.y)


def _with_others(st: dict, nid: str) -> bool:
    """Is node `nid` dragged with other selected nodes (a group move)?"""
    sel = ed.get_selected_nodes()
    k = _id(st, "n:" + nid)
    return len(sel) > 1 and any(x.id() == k for x in sel)


def put_onto(panel, view: graphview.View, nid: str, c: graphview.VCable,
             inlet: str | None = None) -> graphview.VCable | None:
    """Node `nid` onto cable `c` (`dropped`'s, or the chooser's pick): a
    picture node through `Edit.place_node` — one with several inlets and
    no `inlet` picked yet opens the chooser for them (`st["onto"]` with
    `inlets`: "under", "over"; a switch's in1 … in8) and changes nothing
    until one is picked — a modifier `insert_modifier`. Returns the
    cable, or None (asked, or refused: said on the head)."""
    st = _state(panel)
    st["onto"] = None
    n = view.node(nid)
    if n is None:
        return None
    if n.kind in graphview.FRAME_VKINDS:
        # (plan 35 G: the node's own name — an instance, or a copy of one)
        name = n.id.partition(":")[2]
        ask = graphview.inlet_choices(name)
        if ask and inlet is None:
            st["onto"] = {"node": nid, "cables": [c.id], "inlets": ask, "open": True}
            return None
        why = _render_said(panel, render_edit(panel), lambda e: e.place_node(c, name, inlet))
        return None if why is not None else c
    res = insert_modifier(panel, c, nid)
    return None if isinstance(res, graphview.Refusal) else c


def _onto_menu(panel, st: dict, view: graphview.View) -> None:
    """The chooser a node let go over several cables opens: one item per
    cable (`graphview.onto_words`), nearest first; picked, the node goes
    onto it (`put_onto`). Or (2026-11-01) the inlets of a node with
    several (`inlets`): one item per inlet, headed by which picture it
    takes; picked, the node goes onto the one cable with that inlet —
    or, from the cable menu's insert ▸ (`insert`), a new node of that
    kind is made and spliced there (`insert_node`)."""
    held = st["onto"]
    n = view.node(held["node"]) if held.get("node") else None
    inlets = held.get("inlets")
    if inlets:
        c = next((x for x in view.cables if x.id == held["cables"][0]), None)
        if c is None:
            st["onto"] = None
            return
        src, _ = graphview.onto_sides(view, c)
        what = n.label if n is not None else held.get("insert", ("node",))[0]
        ui._micro(f"{what} onto {graphview.onto_words(view, c)}: which takes {src}?")
        for port in inlets:
            if imgui.menu_item_simple(f"{port}##onto.{port}"):
                if held.get("insert"):
                    st["onto"] = None
                    kind, file = held["insert"]
                    insert_node(panel, c, kind, file, port, held.get("at"))
                else:
                    put_onto(panel, view, held["node"], c, port)
        return
    ui._micro(f"put {n.label if n is not None else held['node']} onto")
    for cid in held["cables"]:
        c = next((x for x in view.cables if x.id == cid), None)
        if c is not None and imgui.menu_item_simple(f"{graphview.onto_words(view, c)}##{cid}"):
            put_onto(panel, view, held["node"], c)


def macros_free(panel, view: graphview.View) -> list[str]:
    """The macros the picker offers: the meta controller's knobs doing nothing yet (no
    label, no subscriber). Every macro is a node (its knob is modulatable),
    so picking one names it and brings it to where the picker opened."""
    router = ui_routing.router_of(panel)
    macros = router.table.macros if router is not None else {}
    return [p.id for p in panel.reg.group("macro")
            if (macros.get(p.id) is None or macros[p.id].empty)]


# ---- the canvas's gestures ----

def _value_drag(panel, st: dict, view: graphview.View, a: str, b: str) -> None:
    """A drag between two value / trigger pins, held: the refusal's words
    in red while it would be refused; let go, `connect`."""
    e = edit_of(panel, view)
    why = e.refusal(a, b) if e is not None else "no router"
    if why is not None:
        _drag_tip(why)
        ed.reject_new_item(imgui.ImVec4(*REFUSED_RGB), 2.0)
    elif ed.accept_new_item(COLOURS[graphview.VALUE], 2.0):
        connect(panel, a, b)


def _drag_tip(text: str) -> None:
    ed.suspend()
    ui.tooltip(text)
    ed.resume()


# a drag's handler by the signal type it carries (the seam: N4 maps
# graphview.IMAGE / GEOMETRY / MASK to its own)
CREATE = {graphview.VALUE: _value_drag, graphview.TRIGGER: _value_drag,
          graphview.IMAGE: _create_render, graphview.GEOMETRY: _create_render,
          graphview.MASK: _create_render}


def _drag_type(view: graphview.View, a: str, b: str) -> str:
    """The type a drag is dispatched by: a render type if either end has one."""
    e = graphview.Edit(None, None, None, view)
    types = [e.type_of(a), e.type_of(b)]
    return next((t for t in types if t in graphview.RENDER_TYPES), types[0])


def _create(panel, st: dict, view: graphview.View) -> None:
    """The widget's create query: a pin dragged onto another pin."""
    if ed.begin_create(COLOURS[graphview.VALUE], 2.0):
        got = new_link()
        if got is not None:
            pa, pb = st["names"].get(got[0]), st["names"].get(got[1])
            if pa and pb:                   # plan 28 N7: a one-output node's out stub
                pa, pb = graphview.stub_pin(view, pa), graphview.stub_pin(view, pb)
                # (plan 40 T2: a folded group's pin is its member's)
                pa, pb = graphview.real_pin(view, pa), graphview.real_pin(view, pb)
            if pa and pb and pa != pb:
                if graphview.is_stub(pa) or graphview.is_stub(pb):   # plan 28 N7
                    _stub_drag(panel, st, view, pa, pb)
                else:
                    CREATE.get(_drag_type(view, pa, pb), _create_render)(panel, st, view,
                                                                         pa, pb)
        ed.end_create()                 # only after a begin that opened (the widget asserts)


# ---- plan 28 N7: a drag onto a collapsed node's stub, and landing it ----

BOTH_STUBS = "drag from a port: expand one of the two nodes first"
GROUP_STUB = "{name} is folded: drop it on one of its pins, or open it (+)"
LAND_HINT = "let go: pick one of {label}'s ports"
LAND = "##graph.land"
ONTO = "##graph.onto"                   # a node let go over several cables: which one


def stub_refusal(view: graphview.View, a: str, b: str) -> str | None:
    """Why a drag between pins `a` and `b`, one of them a node's stub, can
    open no port picker: both are stubs (once a one-output node's out stub
    stands for its output, `graphview.stub_pin`), the stub is a folded
    group's (its picker would be empty: the group's pins are the drop),
    or both are outputs (inputs)."""
    if graphview.is_stub(a) and graphview.is_stub(b):
        return BOTH_STUBS
    stub, fixed = (a, b) if graphview.is_stub(a) else (b, a)
    g = view.group(graphview.stub_node(stub))
    if g is not None:           # plan 40 review fix: a folded group has no ports to pick
        return GROUP_STUB.format(name=g.name)
    into = graphview.pin_kind(stub) == graphview.STUB_IN
    if into == (not graphview.is_output(fixed)):
        return graphview.SAME_SIDE
    return None


def _stub_drag(panel, st: dict, view: graphview.View, a: str, b: str) -> None:
    """A cable dragged onto (or from) a collapsed node's stub: held, it says
    which node's ports it will offer; let go, the picker opens (`st["land"]`,
    drawn by `_menus`) — what it lands on goes through `land`."""
    why = stub_refusal(view, a, b)
    if why is not None:
        _drag_tip(why)
        ed.reject_new_item(imgui.ImVec4(*REFUSED_RGB), 2.0)
        return
    stub, fixed = (a, b) if graphview.is_stub(a) else (b, a)
    nid = graphview.stub_node(stub)
    n = view.node(nid)
    _drag_tip(LAND_HINT.format(label=n.label if n is not None else nid))
    if ed.accept_new_item(COLOURS[graphview.VALUE], 2.0):
        open_land(panel, st, view, fixed, nid)


def open_land(panel, st: dict, view: graphview.View, fixed: str, nid: str) -> list:
    """The port picker for a drag from pin `fixed` let go on node `nid`'s
    stub: its choices (`graphview.land_choices`, each with the refusal
    `Edit.connect` would give) held in `st["land"]` until one is picked or
    the menu closes; the next `_menus` opens it. Returns the choices."""
    e = edit_of(panel, view) if not _is_render_pin(view, fixed) else render_edit(panel)
    choices = graphview.land_choices(view, e, fixed, nid)
    st["land"] = {"fixed": fixed, "node": nid, "choices": choices, "open": True}
    return choices


def _is_render_pin(view: graphview.View, pin: str) -> bool:
    return graphview.Edit(None, None, None, view).is_render(pin)


def land(panel, fixed: str, pin: str):
    """A port picked from a stub's picker: the cable from `fixed` to `pin`
    (either order) as if it had been dragged there — a value cable through
    `connect` (`Edit.connect`, one undo step), a render cable through the
    render edits (`Edit.wire`). The picker closes."""
    st = _state(panel)
    st["land"] = None
    view = st["view"]
    if view is not None and _is_render_pin(view, fixed):
        src, dst = graphview.Edit.ordered(fixed, pin)
        return _render_said(panel, render_edit(panel), lambda e: e.wire(src, dst), st)
    return connect(panel, fixed, pin)


def _land_menu(panel, st: dict, view: graphview.View) -> None:
    """The stub's picker: the node's ports a drag may land on, by port
    group when there are more than twelve; a refused one is left out (and
    when every one is, the first refusal is said)."""
    held = st["land"]
    n = view.node(held["node"])
    label = n.label if n is not None else held["node"]
    ui._micro(f"onto {label}")
    ok = [c for c in held["choices"] if c[3] is None]
    if not ok:
        first = next((c[3] for c in held["choices"] if c[3]), None)
        imgui.text_disabled(graphview.NOTHING_TAKES.format(label=label)
                            + (f": {first}" if first else ""))
        return
    groups: dict[str, list] = {}
    for c in ok:
        groups.setdefault(c[2] or "", []).append(c)
    nested = len(ok) > 12 and len(groups) > 1
    for g, items in groups.items():
        if nested and not imgui.begin_menu(f"{g or 'misc'} ({len(items)})"):
            continue
        for pin, text, _, _ in items:
            if imgui.menu_item_simple(f"{text}##{pin}"):
                land(panel, held["fixed"], pin)
        if nested:
            imgui.end_menu()


def _value_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    """Delete pressed on a value / trigger cable: the meta controller's rows are
    kept (and say so); anything else goes (`disconnect`)."""
    b = c.ref if c.kind == "setter" else None
    if b is not None and graphview.is_meta_row(b):
        ed.reject_deleted_item()
        _note(st, graphview.META_ROW.format(what=b.source))
    elif ed.accept_deleted_item():
        disconnect(panel, c)


def _unknown_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    ed.reject_deleted_item()


def _node_mode_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    """Delete pressed on a node mode cable: kept, and the head says how to end it."""
    ed.reject_deleted_item()
    _note(st, graphview.LEAVE_WORDS)


# a delete's handler by the cable's kind ("render" is N4's)
DELETE = {"route": _value_cut, "setter": _value_cut, "sub": _value_cut,
          "input": _value_cut, "render": _delete_render_cable,
          graphview.NODE_MODE: _node_mode_cut}


def _value_node_cut(panel, st: dict, view: graphview.View, n: graphview.VNode) -> None:
    """Delete pressed on a modifier or a macro node: it goes, without its
    cables (`accept_deleted_item(False)`): a removed modifier's chain is
    closed over it — what fed it now feeds what it fed — as on ROUTING."""
    if ed.accept_deleted_item(False):
        remove_node(panel, n.id)


def _fixture_node_cut(panel, st: dict, view: graphview.View, n: graphview.VNode) -> None:
    """Delete pressed on the meta controller's node (a device, the analyzer, an LFO, a
    group): kept, said."""
    ed.reject_deleted_item()
    _note(st, graphview.NOT_REMOVABLE.format(label=n.label))


def _voice_node_cut(panel, st: dict, view: graphview.View, n: graphview.VNode) -> None:
    """Delete pressed on an LFO or an envelope node (plan 31 G1): it goes
    through its bank, without its cables (a route on its lane stays,
    dormant); a lane envelope is kept, said."""
    why = voice_refusal(n)
    if why is not None:
        ed.reject_deleted_item()
        _note(st, why)
    elif ed.accept_deleted_item(False):
        remove_node(panel, n.id)


def _lane_cut(panel, st: dict, view: graphview.View, c: graphview.VCable) -> None:
    """Delete pressed on a sequencer lane's binding: kept — a lane always
    fires an envelope — and the head says how to rebind it."""
    ed.reject_deleted_item()
    _note(st, graphview.LANE_NO_DELETE)


DELETE["lane"] = _lane_cut


# a node delete's handler by the node's kind (the seam: N4 maps "render"
# and "output", plan 35 G a channel too); a kind not listed is the meta controller's
DELETE_NODE = {"modifier": _value_node_cut, "macro": _value_node_cut,
               "lfo": _voice_node_cut, "env": _voice_node_cut,
               "render": _delete_render_node, "output": _delete_render_node,
               "channel": _delete_render_node}


def _leave(panel, role: str) -> None:
    nd = _node_desk(panel)
    if nd is not None:
        nd.leave(role)


def _leave_chip(panel, role: str) -> None:
    """The side pane's leave, for a selected node mode cable or bundle."""
    nd = _node_desk(panel)
    if nd is not None and ui.lit_chip(f"{role}: leave node mode##graph.side.leave.{role}", False,
                                      KIND_COLOURS[graphview.NODE_MODE]):
        nd.leave(role)


def _node_mode_roles(b: graphview.VBundle) -> list[str]:
    """The desks a bundle's node mode cables are from: an expanded one has no delete either."""
    return list(dict.fromkeys(c.ref[0] for c in b.cables
                              if c.kind == graphview.NODE_MODE and c.ref is not None))


def delete_bundle(st: dict, b: graphview.VBundle) -> str:
    """Delete pressed on a bundle (plan 28 N7): kept, and the head says how
    to edit its cables ("expand a node to edit its cables"). Returns the words."""
    ed.reject_deleted_item()
    said = graphview.LEAVE_WORDS if _node_mode_roles(b) else graphview.EXPAND_TO_EDIT
    _note(st, said)
    return said


def delete_through(st: dict) -> str:
    """Delete pressed on a through wire (plan 28 N9): kept — it is no render
    edge — and the head says what it stands for. Returns the words."""
    ed.reject_deleted_item()
    _note(st, THROUGH_NO_DELETE)
    return THROUGH_NO_DELETE


def _delete_key() -> None:
    """Inside the editor: Delete or ⌫ with the canvas focused queues the
    selection for `_delete` (next frame's query). The editor answers only
    Delete — fn+⌫ on a Mac — and only with the pointer over the canvas."""
    if not (delete_pressed() and imgui.is_window_focused()):
        return
    for nk in ed.get_selected_nodes():
        ed.delete_node(nk)
    for lk in ed.get_selected_links():
        ed.delete_link(lk)


def _delete(panel, st: dict, view: graphview.View) -> None:
    """The widget's delete query: the selection's nodes first, by kind
    (`DELETE_NODE`), then its cables, by kind (`DELETE`). The first
    refusal's words stay on the head for the frame (`st["held"]`, `_note`)."""
    if ed.begin_delete():
        names = st["names"]
        st["dropped"] = set()           # N4: render nodes this delete took out
        st["held"] = False
        try:
            nk = ed.NodeId()
            while ed.query_deleted_node(nk):
                n = view.node(names.get(nk.id(), "")[2:])
                if n is None:
                    ed.reject_deleted_item()
                    g = group_at(view, names.get(nk.id(), "")[2:])     # plan 40 T2
                    if g is not None:
                        _note(st, graphview.GROUP_NO_DELETE.format(name=g.name))
                    continue
                DELETE_NODE.get(n.kind, _fixture_node_cut)(panel, st, view, n)
            lk = ed.LinkId()
            while ed.query_deleted_link(lk):
                cid = names.get(lk.id(), "")[2:]
                if cid in st["bundles"]:                # plan 28 N7: refused in words
                    delete_bundle(st, st["bundles"][cid])
                    continue
                if cid in st.get("throughs", {}):       # N9: a through wire, refused
                    delete_through(st)
                    continue
                c = next((x for x in view.cables if x.id == cid), None)
                if c is None:
                    ed.reject_deleted_item()
                    continue
                DELETE.get(c.kind, _unknown_cut)(panel, st, view, c)
        finally:
            st.pop("held", None)
        ed.end_delete()


def _menus(panel, st: dict, view: graphview.View) -> None:
    """Right-click on the canvas: a pin's menu, a cable's, a node's, the
    picker on the background. Opened and drawn with the editor suspended."""
    at = imgui.get_mouse_pos()                 # canvas units, inside the editor
    names = st["names"]
    ed.suspend()
    pin, link, node = ed.PinId(), ed.LinkId(), ed.NodeId()
    subject = None
    if ed.show_pin_context_menu(pin):
        subject = ("pin", names.get(pin.id(), ""))
    elif ed.show_link_context_menu(link):
        subject = ("cable", names.get(link.id(), "")[2:])
    elif ed.show_node_context_menu(node):
        subject = ("node", names.get(node.id(), "")[2:])
    elif ed.show_background_context_menu():
        subject = ("picker", "")
    if st.get("over_details"):              # a right-click on the details: theirs, not the canvas's
        subject = None
    if subject is not None:
        st["menu"], st["menu_at"] = subject, (at.x, at.y)
        st["menu_sel"] = selected_ids(st)       # plan 40 T2: what Group would group
        imgui.open_popup(MENU)
    if imgui.begin_popup(MENU):
        menu(panel, st, view)
        imgui.end_popup()
    held = st["land"]                       # plan 28 N7: a drag let go on a stub
    if held is not None:
        if held.pop("open", False):
            imgui.open_popup(LAND)
        if imgui.begin_popup(LAND):
            _land_menu(panel, st, view)
            imgui.end_popup()
        else:
            st["land"] = None               # closed without a pick
    held = st["onto"]                       # 2026-10-29: a node let go over several cables
    if held is not None:
        if held.pop("open", False):
            imgui.open_popup(ONTO)
        if imgui.begin_popup(ONTO):
            _onto_menu(panel, st, view)
            imgui.end_popup()
        else:
            st["onto"] = None               # closed without a pick
    ed.resume()


def menu(panel, st: dict, view: graphview.View) -> None:
    """The open right-click menu's items, for `st["menu"]`."""
    what, name = st["menu"] or ("", "")
    if what == "pin":
        _pin_menu(panel, view, name)
    elif what == "cable":
        b = st["bundles"].get(name)
        c = next((x for x in view.cables if x.id == name), None) if b is None else None
        if b is not None:
            _bundle_menu(panel, st, view, b)
        elif c is not None:
            _cable_menu(panel, view, c, st["menu_at"])
    elif what == "node":
        n = view.node(name)
        g = group_at(view, name) if n is None else None
        if n is not None:
            _group_item(panel, st)              # plan 40 T2: with nodes selected
            _node_menu(panel, view, n)
        elif g is not None:
            _group_menu(panel, st, view, g)
    elif what == "picker":
        _group_item(panel, st)                  # plan 40 T2: with nodes selected
        picker(panel, view, st["menu_at"])


def port_param(pin: str) -> str | None:
    """The param a ``mod:`` pin is the performer stub of; None for any other pin."""
    kind, _, pid = pin.partition(":")
    return pid if kind == graphview.MOD and pid else None


def _pin_menu(panel, view: graphview.View, pin: str) -> None:
    """A pin's menu: on a param's `mod` stub, the param menu's Learn items
    — the same function the panel's widgets' menu calls (`Panel._ctx_learn_block`:
    desk, hand ▸ left / right, pad, a role, sink), or Cancel while armed —
    so a learn from here lands as a cable next frame (the view is rebuilt
    from the table); any other pin says what it is."""
    pid = port_param(pin)
    a = panel.reg.get(pid) if pid else None
    ui._micro(pid or pin)
    if a is None:
        hit = view.owner(pin)
        if hit is not None and hit[1] is not None:
            imgui.text_disabled(f"{hit[0].label} · {hit[1].name}")
        return
    panel._ctx_learn_block(a, panel._real(a))


def _cable_menu(panel, view: graphview.View, c: graphview.VCable, at=None) -> None:
    """A cable's menu: insert ▸ — a modifier of a kind on a route or a
    modifier's input; on a picture cable (2026-11-01) effects ▸ and every
    other picture node kind (`graphview.insert_items`), made and spliced
    in one undo step, a composite or a switch asked its inlet — the
    starters, delete."""
    imgui.text_disabled(cable_tip(view, c).splitlines()[0])
    if c.kind == graphview.NODE_MODE:           # not a row: leaving the node is what ends it
        role = c.ref[0] if c.ref is not None else None
        if role is not None and imgui.menu_item_simple(f"{role}: leave node mode"):
            _leave(panel, role)
        return
    if c.kind in ("route", "input") and imgui.begin_menu("insert"):
        for kind in modifiers.KINDS:
            if imgui.menu_item_simple(kind):
                insert_modifier(panel, c, kind)
        imgui.end_menu()
    if c.kind == "render" and c.type == graphview.IMAGE:
        e = render_edit(panel)
        files = [f for kind, f, _ in graphview.picker(e) if kind == "effect"]
        if imgui.begin_menu("insert"):          # plan 33 U; 2026-11-01: every picture node
            if files and imgui.begin_menu("effects"):
                for f in files:
                    if imgui.menu_item_simple(f):
                        insert_effect(panel, c, f, at)
                imgui.end_menu()
            for kind, label, why in graphview.insert_items(e):
                if imgui.menu_item_simple(label if why is None else f"{label}: {why}",
                                          enabled=why is None):
                    insert_node(panel, c, kind, None, None, at)
            imgui.end_menu()
        if imgui.begin_menu("starters"):        # plan 36 T5: laid on this cable's picture
            for which, label in graphview.STARTERS:
                if which in graphview.CABLE_STARTERS and imgui.menu_item_simple(label):
                    add_starter(panel, which, c, at)
            imgui.end_menu()
    if imgui.menu_item_simple("delete"):
        if c.kind == "render":                  # N4: unwire, its own undo step
            _render_said(panel, render_edit(panel), lambda e: e.unwire(c))
        else:
            disconnect(panel, c)


def _bundle_menu(panel, st: dict, view: graphview.View, b: graphview.VBundle) -> None:
    """A bundle's menu (plan 28 N7): what it holds, expand its ends (its
    cables appear), and no delete — "expand a node to edit its cables"."""
    imgui.text_disabled(graphview.bundle_tip(view, b).split("\n")[0])
    imgui.text_disabled(f"{b.count} cable{'s' if b.count != 1 else ''}")
    if imgui.menu_item_simple("expand both ends"):
        st["open"] |= {b.src, b.dst}
    roles = _node_mode_roles(b)
    for role in roles:
        if imgui.menu_item_simple(f"{role}: leave node mode"):
            _leave(panel, role)
    if not roles:
        imgui.menu_item_simple(f"delete: {graphview.EXPAND_TO_EDIT}", enabled=False)


def learn_params(n: graphview.VNode) -> dict[str, list[str]]:
    """The params a node's right-click offers Learn on (plan 28 N7, so a
    collapsed render node can be learned without expanding): each param
    port's id, by its port group."""
    out: dict[str, list[str]] = {}
    for p in n.ports:
        if p.param is not None and p.direction == graphview.IN:
            out.setdefault(p.group or "", []).append(p.param)
    return out


def _node_menu(panel, view: graphview.View, n: graphview.VNode) -> None:
    imgui.text_disabled(n.label)
    st = _state(panel)
    if imgui.menu_item_simple("collapse" if is_open(st, n.id) else "expand"):
        toggle_open(st, n.id)
    params = learn_params(n)
    if params and imgui.begin_menu("learn"):            # N3's param Learn, per param
        nested = len(params) > 1
        for g, pids in params.items():
            if nested and not imgui.begin_menu(f"{g or 'misc'} ({len(pids)})"):
                continue
            for pid in pids:
                p = panel.reg.get(pid)
                if imgui.begin_menu(f"{p.label if p is not None and p.label else pid}##{pid}"):
                    _pin_menu(panel, view, f"{graphview.MOD}:{pid}")
                    imgui.end_menu()
            if nested:
                imgui.end_menu()
        imgui.end_menu()
    if n.kind in ("modifier", "macro") and imgui.menu_item_simple("delete"):
        remove_node(panel, n.id)
    if n.kind in graphview.BANK_SCHEMES:          # plan 31 G1: an LFO, an envelope
        why = voice_refusal(n)
        if imgui.menu_item_simple("delete", enabled=why is None):
            remove_node(panel, n.id)
        if why is not None and imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
            ui.tooltip(why)
    if n.kind in graphview.FRAME_VKINDS:
        render_node_menu(panel, n)


def picker(panel, view: graphview.View, at=None) -> None:
    """The node picker (right-click on the canvas): a modifier of each
    kind, a macro not on the canvas yet; the node lands where the menu
    opened."""
    ui._micro("add")
    if imgui.begin_menu("modifier"):
        for kind in modifiers.KINDS:
            if imgui.menu_item_simple(kind):
                add_modifier(panel, kind, at)
        imgui.end_menu()
    for scheme in graphview.BANK_SCHEMES:       # plan 31 G1: another LFO, envelope
        why = add_refusal(panel, scheme)
        one = graphview.BANK_WORDS[scheme][0]
        if imgui.menu_item_simple(one if why is None else f"{one}: {why}",
                                  enabled=why is None):
            add_voice(panel, scheme, at)
    render_picker(panel, at)                    # N4 (and plan 33 U): an effect, a switch …
    _spawn_menu(panel, at)                      # plan 40 T3: a patch, spawned here
    free = macros_free(panel, view)
    if free and imgui.begin_menu("macro"):
        for mid in free:
            if imgui.menu_item_simple(mid):
                show_macro(panel, mid, at)
        imgui.end_menu()
