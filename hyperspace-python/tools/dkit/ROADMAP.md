# dkit roadmap

What to build next, and why — ordered by how much of Hyperspace's actual
surface each one unblocks, not by how interesting it is.

## Is any of this already out there?

Asked properly, because building what exists is the worst outcome.

**A shadcn-equivalent for Dear ImGui: no.** The whole field is
`shyalice/imgui_shadcn` (1 star), `lukaasm/ImFluent` (12 stars, Fluent
Design), and two Yoga+ImGui experiments at 0–1 stars. Nothing established,
nothing in Python.

**A layout engine: yes, and it does not fit.** Taffy has Python bindings
(`stretchable`, abi3 wheels, works on 3.14 — verified, flexbox *and* grid),
as does Yoga (`yogalayout`). Measured here:

```
build a 211-node tree from scratch   198 ms      <- per frame, impossible
reuse the tree, restyle + recompute  2.3 ms/frame
recompute + read 180 boxes back      1.4 ms/frame
901-node tree, layout only           6.0 ms
```

The Python↔Rust boundary dominates. 1.4 ms is ~9% of a 16.7 ms frame for
*180 boxes*, and the panel is far richer than that. An immediate-mode UI
wants to describe its layout every frame; this engine can only be used by
building once and mutating, which is the opposite shape — and the project's
own pattern (`ui_players.lay_out`: a pure width→rects function, cached on
resize) is both faster and dependency-free.

**So: write the flex subset, do not adopt the engine.** But take the user's
suggestion and validate it against a browser — a flex page in the existing
gallery harness, diffed the same way the chrome is. That turns "did I
implement flex right" from taste into a measurement, which is the trick
that has worked all the way through this.

## The layer stack

| layer | state |
|---|---|
| tokens (colour, radius, type scale) | done |
| draw primitives (fill, border, shadow, gradient, icon, text) | done |
| box model (`Rect`, padding, cuts, align) | done |
| layout (flex: direction, grow/shrink, justify, align, gap) | done — 27 cases vs Chromium |
| interaction (hit, eased state, the `_track` sandwich) | done |
| popover placement (side/align/offset, flip, shift) | done |
| components | in progress |

## Still missing, after flex

Primitives the browser gives free that ImGui does not, which components
will keep running into:

| missing | why it matters | hit yet? |
|---|---|---|
| **rounded clipping** (`overflow-hidden`) | ImGui clips to rectangles only; a card with an image or a scroll area has square corners | yes — the popup shadow needed a widened clip rect |
| **text wrapping / multi-line measure** | descriptions, tooltips, node summaries. `push_text_wrap_pos` exists but `label()` is single-line | not yet |
| **intrinsic sizing** (`fit-content`, `min-content`) | `Flow` measures one row; there is no "how big is this subtree" | yes — every container is hand-sized |
| **scroll container** | REVIEW.md: "a section may scroll down". ImGui child windows scroll but the bars need restyling | not yet |
| **focus ring + tab order** | `focus-visible:ring-[3px]`; nav is enabled now but nothing is styled or ordered | not yet |
| **variant resolver** (cva) | variants are ad-hoc dicts (`tokens.BADGE`); components will each invent their own | yes, mildly |
| **transform transitions** | shadcn menus `zoom-in-95`; the ease store does colour only | no — faded instead |
| **density / scale** | `Ui.scale` exists and is unused; the side pane is 240–320px | not yet |

Rounded clipping and intrinsic sizing are the two that will bite hardest,
in that order.

## Components, against Hyperspace's real control inventory

The counts are measured from `params.build_registry`, not guessed: **427
params in a bare registry, realistically 600–900 live** once bands, LFOs,
modifiers and graph instances declare theirs.

| Hyperspace need | how much | component |
|---|---|---|
| continuous param | **292** | **Slider** — taper-aware, detents, shift-fine |
| enum param | **73** | **Select**; Combobox for long lists; ToggleGroup for short |
| toggle param | **47** | **Switch**, Checkbox |
| text param / node rename / numeric entry | — | **Input** |
| trigger param | 15 | Button ✓ |
| every param has a tip | all | **Tooltip** |
| 17 folding sections (`ui_pane.SECTIONS`) | 17 | **Collapsible / Accordion** |
| "a section may scroll down" (REVIEW.md) | — | **ScrollArea** |
| canvas ↔ side-pane split (`ui_graph.band_height`) | 1 | **Resizable** |
| right-click a node | — | **ContextMenu** (reuses `menu.py`) |
| finding one of 600–900 params | — | **Command** palette |
| MIDI-learn, key bindings | — | **Kbd** |
| footer message slot (`_footer`, `MESSAGE_S`) | — | **Toast** |
| destructive confirms (delete node/preset) | — | **AlertDialog** |
| node summary without opening it | — | **HoverCard** |
| band/level meters | 6+ | Progress ✓ (as `meter`) |
| graph location | — | Breadcrumb |

### Order

**Tier 1 — unblocks the most surface.** Slider, Input, Select, Switch,
Tooltip. Those five cover 412 of the 427 measured params plus every tooltip.

**Tier 2 — what the node editor needs.** ScrollArea, ContextMenu,
Collapsible, Resizable, Command.

**Tier 3 — polish.** AlertDialog/Dialog, Toast, Kbd, HoverCard,
Sheet/Drawer, Breadcrumb, ButtonGroup, RadioGroup, Pagination.

### Two the requested list left out, which are the biggest wins

**Slider** and **Select** were not on the list of interest, but 292
continuous and 73 enum params are 85% of the registry. Nothing else comes
close. A Hyperspace panel is mostly sliders.

### One that is cheap and underrated

**Command** palette. With 600–900 addressable params and a stated rule that
"everything settable has a stable id", a fuzzy finder over the registry is
nearly free to build and changes how the app is used.

## Constraints every component has to respect

- **Keep an `invisible_button` with the same `##id`** — `tests/ui_driver.py`
  finds controls that way and 22 `test_ui_*.py` files depend on it.
- **Fit the narrowest width.** GRAPH's side pane is 240–320px
  (`REVIEW.md`), and `Ui.scale` exists but is still unused.
- **No per-frame cache rebuilds** (`REVIEW.md`). Layout is cached on size.
- **Popups never reach the canvas tap** — `replay.keep` drops every popup,
  menu and tooltip from `panel:graph`.
- **A persisted param id is a file format** (`REVIEW.md`), so a component
  that renames anything needs the migration rules.
