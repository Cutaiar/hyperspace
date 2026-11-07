# What went wrong in this session, and what would have caught it

Every row is a real defect. Most were found by a person looking at the
running app, which is the part worth fixing: the kit has a pixel diff, a
browser oracle and 710 tests, and none of them saw these.

The right-hand column is the point of the table. "Be more careful" is not a
mechanism; each entry is a thing that can be done or checked.

## Reported by eye, after I had said the work was done

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 1 | The dashboard didn't scroll — only the table did | A page-level scroll area; the table is its natural height | A claim about the demo ("it scrolls") is a **driven assertion**, not a sentence. `test_the_gallery_scrolls_to_its_end` is what that looks like. |
| 2 | Clicking a Button left a focus ring behind, and it walked to the next one clicked | `:focus-visible`, not `:focus` — `Ui.focus_visible` tracks keyboard-vs-pointer | Model the **CSS pseudo-class**, not the word. If the registry says `focus-visible:`, the kit needs the distinction, and the test must drive the keyboard. |
| 3 | The Combobox was the wrong component — I briefed Popover + Command; shadcn ships `combobox.tsx` on Base UI | Rewrote it: the trigger IS the input | **Read the registry file.** Never recall a component's recipe. An agent verified the cmdk port against the shipped JS over 382 pairs and it was still wrong, because verification cannot see a wrong premise. |
| 4 | After that, the drawn trigger was *still* the old shape — I had fixed the table and the filter and called it done | Finished the visible half | "Done" means **looked at in `--live`**. A component is not finished while the thing on screen is the old one. |
| 5 | The vendored shadcn components had never been refreshed | `refresh_shadcn.sh`, and it is now rule zero | Run it before every component. It takes thirty seconds and a clean run ("no component changed") is itself a measurement. |
| 6 | Blue rectangles around focused controls | ImGui's `nav_cursor`, cleared once in `interact.chrome()` for the whole frame | **Audit ImGui's stock chrome** for things shadcn has no counterpart for, in one place, rather than per component. Same pass caught the text-selection colour. |
| 7 | The 1px press nudge was on plain Buttons after being taken off ButtonGroup | One `NUDGE` constant through one code path | A behaviour gets **exactly one switch**. If two call sites can disagree, they eventually will. |
| 8 | Combobox: square right corners, the check crowding the edge, the panel hopping top↔bottom while typing, a scrollbar flashing | Re-measured the real row (`4px 32px 4px 6px`, `rounded-md`, indicator `right-2`); pinned the side at open and clamped to the room available; `no-scrollbar` | All four came from drawing the Base UI component with the **old recipe's numbers**. When the premise changes, re-measure *everything*, not the parts that look wrong. |
| 9 | Clicking a Select in the Gallery crashed the app | It was handed `list[str]` where `menu.Item` was wanted | The Gallery exists because the diff "cannot see that a control is unclickable" — and I tested it by rendering it and checking it wasn't blank. **Drive every specimen**: `test_every_specimen_can_be_clicked`. |
| 10 | Stray lines between the Combobox field and its list | ImGui's `PopupBorderSize` (1.0, and `WindowBorderSize` does not cover it) | I had **seen this and written "Minor"** in my own notes without measuring it. Never file a visual anomaly as minor; measuring took eight minutes. |
| 11 | Ctrl+C printed a traceback instead of quitting | Catch it; teardown into `finally` in both loops | **An exception path is a code path.** The same `finally` stops one crash from reading as a dozen later ones. |
| 12 | Input text sat high; then, after my "fix", still high | Two causes: ImGui adds `FramePadding` (4,3) inside the frame, *and* the stock widget drew in imgui's current font, not Geist at `font × FONT_SPAN_EM` | My test asserted the **selection band** — imgui's line box — which was centred while the glyphs were not. **Assert the observable**: the value's ink against the placeholder's ink, two visible things that must agree. |
| 13 | Clicking the range slider's track did nothing | A track target, `nav=False`, driven off the press | **Enumerate a component's interactions from the real one**, not just its chrome. The pixel diff cannot tell you a region is dead. |
| 14 | The scroll thumb sat flush to the edge and crossed the rounded corner | The bar belongs to the **viewport**, inset by the border: thumb at (311,2) in a 320×200 root | Measure the **slot the browser uses**, not the box you happen to have. |
| 15 | Scrolling was wildly too sensitive | ImGui moves `5 × font_size` per wheel unit; macOS GLFW sends `scrollingDeltaY × 0.1` of *finger travel*, so a 100pt swipe moved 900px | **Input mapping is a measurement too.** A default is not a decision. |
| 16 | A Buttons enumeration card on the dashboard page | Removed; the Gallery enumerates | Two pages, two jobs: gallery enumerates, dashboard uses realistically, **nothing in both**. |

| 17 | The combobox opened on focus, trapped Tab, highlighted the first row always, and clipped its own focus ring | Measured the real keyboard model key by key and implemented it; inflated the popup window by `RING_PAD` | **Measure the component in the state the question is about.** My first keyboard probe used a block with `open` hard-set, so `aria-expanded` was true whatever I pressed. `?probe` now carries `combobox.kb`, the one block without it. |
| 18 | The combobox's focus ring was clipped when you CLICKED the field and correct when you TABBED to it | The field is drawn twice — the copy in the parent window owns the chrome, the copy in the popup owns the caret. The window is not inflated; `RING_PAD` stays 0 | **When a defect appears on one route in and not another, the difference between the routes IS the diagnosis.** Tab and click differ in exactly one thing — a click opens the list — so the fault has to live in code that only runs while it is open, which is one window and one call. Ask "what is different about the path that fails" before reading any code. It took a minute; measuring it afterwards gave `left [0,0,0] right [0,0,0] top [0,0,0] bottom [46,46,46]` against `[46,46,46]` on all four sides closed. |

## Mine, found by me or by an agent

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 19 | `test_gallery.py` booted a GL context per test and never shut one down, poisoning unrelated tests — and I reported those failures as a subagent's in-flight work | Boot, measure, tear down, then render | **Check `git diff` before attributing a failure.** My file was in the failing set the whole time. |
| 20 | The first "no scrollbar" test passed against the broken code — it read pixels in a region nothing ever painted | Assert at the call site instead | **Verify every new test against the broken code it covers.** A test that cannot fail is worse than no test, because it is counted. |
| 21 | `invisible_button` cannot take keyboard focus in ImGui 1.92.9, so the Button's focus ring — the "reference implementation" — had never painted | `ButtonFlags_.enable_nav` on `Ui.hit` | **Check that a reference implementation works before porting it.** Copying it would have shipped four more rings that cannot appear and four tests that cannot fail. |
| 22 | `combobox_size` reserved 36px for a search field the widget had stopped drawing | Removed | **Ask both halves the same question.** A size function and the thing it sizes should be tested against each other. |
| 23 | The empty state was still the Command recipe's — 68 tall, `popover-foreground` | Re-measured: 36, `muted-foreground`, `data-empty:p-0` | Same as 8: a correct measurement of the wrong component is still wrong. |

| 24 | A scrollbar flashing inside the Combobox popover — and I told the user there wasn't one | `begin_popup` adds `AlwaysAutoResize` to your flags, so the WINDOW sizes from the cursor extent and draws its own bar; `no_scrollbar` on every `begin_popup` | **Two bars, two switches.** I checked `bars=False` on the list and answered for the window. Asserting one thing says nothing about a different thing with the same name — and "I read the flag" is not a measurement. |


## Mine, from the Combobox ergonomics pass

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 25 | The field's value was painted TWICE whenever the list was open — the parent's copy and the popup's both drew it, and the glyphs came out at 255 against a `foreground` of 250 | One `ink` flag: the copy that owns the caret paints the text, the other pushes `Col_.text` transparent | **A pixel brighter than the token it is drawn in is two passes, not one.** The ceiling is a measurement: nothing drawn in `foreground` can exceed `foreground`, so sampling a glyph's peak against the token says whether it was painted once. Nobody had ever compared the open field's ink to the closed field's. |
| 26 | An open always highlighted none / the first / the last row. The real one highlights the **committed value's** row for all four gestures | `resolve_open` — the value beats the gesture, and the gesture is only the fallback | **Row 17's lesson, one level down, and it cost a second round.** The keyboard model was measured on `combobox.kb`, which carries no `defaultValue`, so the valued half of the table was never asked — and six driven tests then asserted the valueless rules against the dashboard's combobox, which holds a value. **When a component has a state (a value, a selection, a disabled flag), probe it with the state AND without. One probe block answers one column.** |
| 27 | A clamped panel was 260 tall where the browser's is 252, and the test that covered it asked the source for the number and still passed | `list_max_h` clamps the PADDED list, which is the panel; the rows get it less the rails | **"A test asks the source" is not enough if the model behind the number is wrong.** 252 was read correctly off `max-h-[...]` and then applied to the rows. What settles it is the browser's own box: `combobox.tight` reports the content element AND the list at 319x**252** with `scrollHeight` 456. **Assert the measured RECT, not an arithmetic identity over the token.** |
| 28 | The group heading was `font-medium` and the separator had no margin — both read off `command.tsx` rather than `combobox.tsx` | Measured 400 and `margin: 4px -4px` on the real slots | Two files ship a `-mx-1 h-px bg-border` separator and only one of them is this component's. **When a recipe is replaced, re-measure every slot on the NEW file's own `data-slot`, not the ones that look unchanged.** Same failure as 23, twice more, in the two slots nothing on the page happened to exercise. |
| 29 | The field's padding was a dead hit area: a press in the left 10px or right of the text box did nothing at all | `FramePadding` IS the field's padding, so the frame is the whole input box | **An ImGui InputText's hit area is its FRAME**, and zeroing `FramePadding` to control where the glyphs land silently shrinks it to the text box. **Drive every edge of a control, not its middle** — a click at `x+2` is a thing a person does and no test had ever tried one. |
| 30 | The list never scrolled to follow its keyboard highlight, so arrowing past the ninth of sixteen rows moved something nobody could see | Minimum scroll on a keyboard move only; the wheel and a parked pointer leave it alone | **Drive a list that is longer than its clamp.** Every test and every specimen used six rows in a 252px box, where no scroll is ever needed, so the behaviour had no way to be wrong. The Gallery's sixteen-item cell existed and nothing drove its keyboard. |
| 31 | The `xfail` that recorded the clipped ring could not have passed OR failed honestly — with `RING_PAD` at 0 its band scan was `max()` of an empty range | Rewritten to compare the open ring against the closed one, both measured | **An `xfail` is still a test and still needs to be run against the fixed code before it is believed.** `strict=False` hides the difference between "fails for the reason stated" and "raises before it reaches the assertion". |

| 32 | Scrolling was 9x too fast, then 10x too slow, and the text sheared as it moved | One unit is ten points of finger travel, so `px_per_unit` is 10 — which also makes every step land on a whole pixel | **When a knob does nothing, check it is connected before turning it.** I changed the constant twice and wrote two commit messages about feel, while the function was reading a value that is zero at that point in the frame. The user running the probe and seeing NO OUTPUT found it in one line. |
| 33 | The GLFW scale factor sat unverified through three commits | `--wheel-probe` printed the raw deltas; every one was a multiple of 0.1, which proves the 0.1 I had been asserting from memory | **Build the instrument before the third guess.** The probe took twenty minutes and ended the argument permanently; it belonged before the first constant, not after the second. It answered inertia for free — the decaying tail of a flick is right there in the output. |

| 34 | Text snapped up and back down on a slow trackpad scroll — and Hyperspace, scrolling far faster, never did | The scroll OFFSET is snapped to a whole pixel, so every line keeps its fractional part and the page moves together | **A thing that works elsewhere in the same codebase is a free control experiment.** `draw.label` rounds a glyph origin and `ui.py` does not — that one difference named the cause in a minute, after I had spent the session assuming anything scroll-shaped was the scroll rate. Ask what the working case does differently before theorising. |
| 35 | My instrument for the above said "7 jumps back up" on correct code | Measure the frame-to-frame SHIFT by alignment, not "which row is brightest" | **Third time this session a bad probe reported a defect that was not there** (a tick mark read as a scrollbar, pixels sampled where nothing paints, now this). A probe needs its own sanity check: run it against a case you know is good, and if it reports a fault there, fix the probe first. |

| 36 | Text still wobbled after the scroll offset was snapped | Python's `round()` is half-to-EVEN; a coordinate on a .5 boundary steps 126, 124, 124, 122, 122 — lurch two, stay, lurch two. `draw.px` is `floor(v + 0.5)` | **A rounding function is part of the animation.** I snapped the offset and declared it fixed without asking whether the rounding itself was monotone. The signature is unmistakable once looked for: a steady drag measured 0, -2, 0, -2 a frame with -1/-3 pairs, straight off a screen recording the user sent. |

## The habits these reduce to

1. **Refresh, then measure, then build.** `refresh_shadcn.sh` → `?probe` → kit → diff. Rule zero exists because an oracle built on a stale component is a confident wrong answer.
2. **Assert what a person sees.** Ink, not line boxes. A click, not a render. If the assertion needs a model of ImGui's internals to be meaningful, it is the wrong assertion.
3. **Make every new test fail first.** Revert the fix, watch it go red, put the fix back. Three tests in this session could not fail when written.
4. **Drive it before saying it works.** Not a screenshot of the chrome — a script that clicks, types, scrolls and dwells past the 150ms transition. Eleven of the sixteen reported defects were behaviours, and the pixel diff is blind to all of them by construction.
5. **Probe every state the component HAS, and drive every edge of it.** Rows 17, 26, 28, 29 and 30 are one shape: the measurement was exact and the thing measured was one state or one region short. A probe block answers one COLUMN of the table — a combobox with a value and one without, a list longer than its clamp and one shorter, a press at the control's edge as well as its middle. The gap never shows in the result, only in what was never asked.

## Mine, from the menu keyboard pass

Appended below the habits rather than beside the other tables on
purpose: this file was being edited in parallel, and adding to the end
is the only change that cannot collide with someone else's. The rows
carry on the one numbering, and rows 2, 3, 4 and 5 of the habits above
are each earned again here.

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 37 | `grep -c is_key_pressed menu.py` was **0**: no menu in the kit — the dropdown, the ContextMenu and every Select — could be driven by the keyboard. What looked like a working highlight was ImGui's nav leaking through `is_item_hovered`, which reports True for a merely NAV-focused `invisible_button`. It started on the SECOND row, it WRAPPED at both ends where the real one clamps, and Enter never took the row | The measured model in `menu.popup`, rows submitted `nav=False` so the kit owns the highlight | **An accidental behaviour is worse than none, because it looks like a decision.** The off-by-one and the wrap had been on screen for the whole life of the kit and nobody had asked what was drawing them: the fill came from a hover value that ImGui was setting from the keyboard. Ask what paints a thing before believing it is yours. |
| 38 | I nearly ported the Combobox's keyboard table wholesale, and two of its rows are the OPPOSITE of a menu's | Measured the menus on their own probe blocks | **The differences between two similar components are the entire reason to measure the second one.** A menu's arrows CLAMP (Radix's menus do not pass `loop` to their roving-focus group) where the Combobox falls into a none-state, and Tab is SWALLOWED (`if (event.key === "Tab") event.preventDefault()`) where the Combobox closes and moves on. A port would have shipped both backwards with a confident comment. |
| 39 | `interact.select` called `menu.popup` only `if open_`, so the CLOSED branch — the one that pops `menu.LAST_RECT` and resets the open animation — never ran for a Select, and the rect outlived the panel for the rest of the process | Call it either way, as `comp_context_menu` already did | **A test that reads a seam has to be able to tell the seam is stale.** `test_a_key_on_a_closed_select_trigger_opens_it` PASSED against the unfixed code, because the rect was truthy however the key behaved — a fifth test this session that could not fail. The rect now says WHERE and a pixel against `popover` says WHETHER. |
| 40 | `armed` gated the MOVEMENT keys and not the activation keys, so an Enter on a closed Select trigger opened the panel and committed a row in the same frame | Pop the flag in the activation handler, which runs last in the frame, and only read it in the movement one | **The Combobox's `armed` trap has a second half nobody had met, because the Combobox opens with an arrow and a menu opens with Enter.** Any key that both opens a panel and does something inside it needs the flag; the list of such keys is a property of the component, not of the flag. |
| 41 | A menu's highlight counts the rows it can land on; the draw loop walks every item. The dashboard's kebab menu has a separator AND a label above its last row, so the two numberings differ by two there | One `highlighted_item`, and `item_rows` is the only definition of "a row" | **Drive a list with FURNITURE in it.** Every menu on the browser probe is a flat run of items, so the browser could not have shown this at all; the dashboard's menu is the only one in the project with a separator and a label in the middle, and the fourth row of it is the only place the bug is visible. The measurement was exact and the thing measured had no separators — row 30's shape again. |

## Mine, from putting the last four components into the pixel diff

Appended at the end for the reason the previous section gives. The rows
carry on the one numbering. The shape of this batch is different from the
earlier ones: almost every entry is a MEASUREMENT THAT NOTHING WAS CHECKING,
rather than a number that was wrong. Four components had been built, tested
and looked at, and the two things wrong with the Combobox trigger were found
in the first ten minutes of its first pixel pass.

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 42 | The Combobox chevron was drawn at `muted-foreground` **0.5** where the browser paints it at full strength: 185 against 115, seventy levels, on every combobox in the kit | `field_icon_ink` at 1.0, and the disabled factor named separately | **The component was outside the pixel diff.** That is the whole of it. `0.5 * dim`, with dim itself 0.5 when disabled, is right for the disabled case and wrong for the enabled one, and one folded constant cannot be both — so it survived every unit test and every look at the running app. A cell in the diff found it immediately. |
| 43 | The same chevron sat 3 px too far right: the kit used `1 + SPACE[1]` = 5 where the measured right inset is 8.203 | `field_chevron_right`, measured at two widths | Same as 42. A geometry that comes out of arithmetic over the spacing scale rather than off the real component is a guess with a tidy derivation. |
| 44 | **`icon_boxes` dropped every icon out of every metric while its own docstring said "nothing is simply dropped: the chevron still has to land on the right pixels".** Nothing implemented that. Worse, the excluded region is derived from the same token the draw site reads, so the hole MOVES WITH the icon — with the mask in place and 42 and 43 put back, both cells report "ok" | `contour.icon_ink`: ink mass and centroid, which survive the cap disagreement, reported and FAILED on | **Re-read what a docstring promises and check something enforces it.** This one named the gap it was leaving and then left it. A mask whose geometry comes from the code under test cannot catch a placement error by construction, and that is worth saying out loud wherever one is used: the Select's chevron had been in the same hole since it landed. |
| 45 | The gallery's ScrollArea cells passed `draw.scroll_bar` the already-inset VIEWPORT where it takes the ROOT and insets by the border itself, so the border was counted twice — track at (y+2, 114) against the browser's (y+1, 116) | Pass the root, as `interact.scroll_area` already did | **The diff was failing and the figure in HANDOFF said it was not.** 26 levels on three cells, recorded as "flat 0-2 levels". A number in a handoff doc is a claim with a date on it; re-run it before believing it. The component was fine — `box.scroll_thumb` reproduces all three browser rects exactly — so this was invisible in `--live` and only ever wrong in the harness. |
| 46 | `capture_react.js` hardcoded a 1600 px viewport against what was a 1300 px canvas. Adding cells took the canvas past it and a pointer-anchored popper was collision-clamped to the corner of the page, 1490 px from its cell | Derive the viewport from `spec.canvas` | **A margin that has to be remembered when the spec grows is a margin that will not be.** The comment above it even explained why the viewport must exceed the canvas; it just did it with a constant. |
| 47 | `probe_react.js` never right-clicked the ContextMenu, so `contextmenu.target` only ever reported the TRIGGER — while Probe.tsx said the panel is "opened with a real right-click from playwright". Every number in `comp_context_menu.py` had been read off the classes | Open it, measure it (the table turned out right) | **A comment that describes a measurement is not a measurement.** Two files disagreed about whether a thing happened and neither was checked. Grep the harness for the gesture a comment claims it makes. |
| 48 | `probe_react.js` crashed with "blk.parts is not iterable" on the `_states` entry — after the JSON was written, so with `--json` you lost the printout and without it you lost everything | Skip it in the printer; give it its own section | **Run the tool both ways.** Every use of it in the repo passes `--json`, so the crash was downstream of the only thing anyone read. |
| 49 | **`is_item_hovered()` is True for a merely NAV-focused `invisible_button`**, so every control reading `State.hot` lit its hover tint off the keyboard — the sidebar item, the tabs trigger, the table row, the kebab, and `comp_button.ui_button`. `interact.py` carried a comment asserting the opposite, and naming `enable_nav` as the way to avoid it | `Ui.hit` also requires the pointer inside the rect | **RETRO row 37, one level up, and the lesson had already been written down here.** Row 37 was the menus' highlight turning out to be ImGui's nav leaking through this exact call; the fix there was local and the general claim was never re-tested. A measured finding that contradicts a comment should delete the comment, not sit beside it. Found by a test asserting an INVISIBLE kebab does not ring — it was ringing at 35 levels. |
| 50 | `field_icon_x` (9.0) and `field_text_x` (31.0) described the leading magnifier of the Popover+Command search field, which the component has not had since that recipe was replaced. Nothing read either but a test asserting `field_icon_x == 1.0 + T.SPACE[2]` | Deleted; the test now asserts the measured chevron | **RETRO row 27 in miniature, over a dead token.** An arithmetic identity over a constant cannot fail; one over a constant nothing reads cannot even go stale visibly. When a recipe is replaced, grep the old recipe's tokens for readers — row 22 found `combobox_size` doing the same thing and the rest of the family was left. |
| 51 | My own first `icon_ink` used the box's MODAL level as the background, which is degenerate on a small box: a scroll thumb's end cap fills most of its own box, so the mode was the thumb and "ink" came out as the background around it — a 2.36 px centroid shift reported between two images that are pixel-identical there | The median of the box's PERIMETER | **Fourth time in two sessions a bad probe reported a defect that was not there.** RETRO row 35 already says a probe needs its own sanity check against a case known to be good. I had one — the chevrons — and read the scroll figure before asking why only one shape disagreed. |
| 52 | Opening the ContextMenu cell with a real right-click dismissed the menu cell's dropdown: it is a DismissableLayer with `modal={false}`. `menu.panel` went to 34 levels over 1364 px with NaN corners | `onInteractOutside`/`onEscapeKeyDown` prevented on both menu cells | **A cell reporting a fidelity failure because a DIFFERENT cell's setup closed it.** The gallery is a static contact sheet; nothing in it should be dismissable, and the first suspect for a cell that breaks when an unrelated cell is added is the new cell's gesture, not the old cell's chrome. |
| 53 | `comp_combobox._panel_chrome` was still a copy of `menu.panel_chrome`'s four lines, under a note saying the right fix "means editing menu.py, which this change may not do" — and `menu.panel_chrome` had since been created, with a docstring naming a Combobox as one of the three callers it was pulled out for | Delegate | **A deferral with a stated unblocking condition should be re-read when that condition is met.** Both halves of this were in the repo, pointing at each other, for two sessions. On the way it turned out menu.panel_chrome looped SHADOW_MD forward and dropped `dx` where CSS lists shadows front to back — pixel-neutral on this token, by luck of it being two layers of one colour. |

### What this batch says about the method

Rule zero and rule one held up: `refresh_shadcn.sh` reported no change, and
every number that came out of `?probe` was right. What failed was one level
out from the component — **the harness that decides which pixels get
compared**. Rows 44, 45, 46 and 52 are all the measuring rig, not the kit,
and row 44 is the sharp one: a region excluded from the diff, derived from
the same constant the drawing reads, is a hole that follows the bug.

So the rule this batch adds, which is rule 1 pointed at the rig:

**Whatever the diff excludes needs its own metric, and that metric must not
be derived from the code under test.** If a region is dropped because one
metric is wrong for it, say what measures it instead, implement that, and
make it fail. "Nothing is simply dropped" has to be a function, not a
sentence.

And the corollary, which is cheap: **a figure in a handoff document is a
claim with a date on it.** Re-run the diff and the suite before building on
either. HANDOFF said 733 passed and 0-2 levels; the suite was 734 with a
flake and three cells were failing at 26.

## Mine, from preparing item 3 — and one from the first five minutes

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 54 | **I told the user that `RETRO.md`, `HANDOFF.md`, `refresh_shadcn.sh` and the `?probe` route did not exist, with a table and a `git log --all` to back it up.** All four existed. The branch had thirty-eight commits I could not see | `git fetch` | **`git log --all` does not mean "all commits that exist".** It means all refs this clone has, and a cloud session's remote-tracking refs are frozen at the moment the container cloned. A container that starts mid-task is a stale clone by definition. **Fetch before concluding anything is absent** — the cost is two seconds and the failure mode is a confident, evidenced, wrong report. Worse than guessing, because it came with proof. The user's "did you pull" was the whole fix. |
| 55 | My module-surface scanner reported two dangling references (`draw.lay_out`, `draw.HEADER_H`) on a module that was fine: `test_components.py` has `import draw as D` at the top and `D = _dashboard()` inside a test, so those attributes belong to the dashboard | Made the scanner scope-aware | **Fifth time a probe of mine has reported a defect that is not there** (rows 35, 51, and the tick-mark and the empty-region reads before them). The pattern is now unmistakable enough to be a habit rather than a note: **when a new instrument fires, check the thing it accuses before changing it.** Both of these took one `sed -n` to dismiss. |
| 56 | Then the fixed scanner went quiet on seven files — and the **pass count did not drop, the SKIP count rose**, because a function-local `import menu as M` was being treated as shadowing the identical module-level alias | Track local imports as aliases, not as shadows | **A skip is not a pass, and a suite that reports them together will hide a broken instrument.** `27 passed, 13 skipped` and `20 passed, 20 skipped` both read as green. The only reason this was caught is that the two numbers were compared across a change; nothing in the output flagged it. If a check can skip, print WHY it skipped, or assert how many cases it actually ran — which is what `test_the_check_actually_finds_references` now does. |

### The one rule from this batch

**Fetch, then look.** Row 54 is the cheapest mistake in this file to avoid and
the most expensive to make, because the output of a stale clone is
indistinguishable from the truth and arrives with evidence attached.

## Mine, from building the Checkbox

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 57 | **The Switch's hit area was `x - 3, y - 2`** — the Tailwind STEP numbers of `after:-inset-x-3 -inset-y-2` read as pixels. The real one is the pointer target 11px past each end and 7px above and below, so the kit had an 8px dead strip at each end that the browser does not. Its own docstring named the class | `rect.stretched_hit`, one answer for the Switch and the Checkbox, from `tokens.HIT_STRETCH` | Found only because the Checkbox carries the identical class and its hit area was MEASURED rather than read. **A number in a class name is an index into a scale, not a length.** And row 29's rule again: nothing ever clicked the Switch off its track. `test_the_switch_takes_a_click_off_its_left_end` does now. |
| 58 | My first hit scan of the Checkbox read its target as LOPSIDED — reaching 12px left and 8 up but stopping short right and down | A dense scan plus the `::after`'s own computed box: 38 x 30, symmetric, 11px and 7px — the pseudo element is inset from the PADDING box, a border inside the edge | **Sixth time a probe of mine reported a defect that is not there** (rows 35, 51, 55). Sparse sampling across a half-pixel edge. The fix was the same as every time: a second instrument that does not share the first one's assumption, and only then a conclusion. |
| 59 | The transition probe recorded an UNCHECK under the label "check": it assumed the box was unchecked, and the hit scan before it had left it checked | The probe sets its own starting state | **A probe step owns its precondition.** It ran after another step that mutated the same control, so it measured whatever that step left behind. The data was right and the label was wrong, which is the more dangerous way round. |
| 60 | One of the six revert-checks for the new tests went red for the WRONG reason: the mutation I wrote raised a NameError, so "the Switch tests fail on the old hit area" was briefly a claim about a crash | Rewritten as a clean mutation; the failure is now the missed click itself (`False is True`) | **A mutation that crashes is not a mutation.** Habit 3 says watch the test go red; read WHY it went red, or a typo in the revert passes for a proof. |

### What this batch says

The Checkbox itself came out right on the first diff - every cell within
0-1 levels in both themes - because every number came off `?probe` first.
What the measuring found was in the component NEXT to it. Measuring the
second of two similar components is how the first one's bugs surface (row
38 said the same of menus); it is worth doing even when the second one is
"the cheap one".

## Mine, from building the Kbd

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 61 | **(FIXED - rows 64-69.)** **The kit's text is not Chromium's text, by measurement.** Glyph advances come out of the baked font as WHOLE pixels ("Ctrl" 22 against 21.192, "Save Changes" 82 against 78.541, `medium` and `regular` identical where Chromium's differ), and 12px text sits ~0.93px LOWER than Chromium's while 14px agrees to ~0.1 | Not fixed - it is the font loader, kit-wide. The Kbd cells pin their width as Button's do; the width LAW is tested against Chromium's own text widths; the 12px height is a STRICT xfail in `test_kbd.py` | Found because the Kbd is the first component whose box size comes from its text AND whose cells were drawn at intrinsic width - the diff failed two cells on the right edge. Every earlier text-sized component pinned its width in the spec, which is exactly why this had never been measured. **A pinned dimension is a dimension nobody is checking.** |
| 62 | `kbd.word` failed the dark diff at 6 levels: a 29.203 wide box drawn at its fraction | `draw.snap`, as `draw.switch` already did | The README's finding - Chromium lays out on fractions and SNAPS what it paints - applied to every fractional box, and draw.kbd was written without it. Caught in the first diff, which is the point of a diff; the habit is to reach for `snap` whenever a size is not a whole number. |
| 63 | I inferred the KbdGroup "+" was 9.61 wide by SUBTRACTION and assumed it was Geist at the parent's 16px (8.93) | Measured the span: **monospace**. KbdGroup renders a <kbd>, the UA gives <kbd> `font-family: monospace`, and the group never resets it | A number derived by subtraction carries every assumption of the subtraction. **Measure the element, not the gap between two others.** The 0.68px discrepancy was the clue and would have been easy to call rounding. |

### What this batch says

The component was trivial and came out at 0-1 levels. What it surfaced was
one level down again - the text measurement every component shares - and it
surfaced only because the gallery cell was allowed to size itself. That is
worth doing deliberately: one cell per text-sized component drawn at its
OWN width, not the spec's, is a cheap standing check on the font loader.

## Mine, from fixing the font loader (row 61)

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 64 | **Row 61, root-caused: four separate faults, none in a component.** (a) The loader is **FreeType**, not stb_truetype as README, FINDINGS and the code comments all said, and it HINTS by default - a hinted advance is a whole pixel. (b) **ImGui 1.92 rounds every font size** to a whole pixel, so `css x FONT_SPAN_EM` - 15.6 at 12px - became 16: 12px text 2.6% large, 14px (18.2 -> 18) 1.1% small. (c) Its baked ascent is CEIL'd (13 at 16) where Blink ROUNDS ascent and descent separately (12 + 4): that is the whole 0.93px. (d) ImGui applies no `kern` and no `liga`; Chromium applies both, and Geist's `tt`/`ff` ligatures are 0.05em narrower than their letters | `NoHinting`; a one-em line box built into the TTFs so the size pushed IS the CSS px; kerning, ligatures, advances and Geist's real metrics frozen to `fonts/metrics.json`; `draw.baseline_y`; glyphs drawn one quad each at the fractional pen. Widths now within 0.016px of `measureText` on 156 strings, the Kbd glyph within 0.04px vertically | **`io.fonts.font_loader_name` was one attribute away the whole time.** Three documents reasoned about stb_truetype's algorithm without checking that stb_truetype was running. Before explaining a library's behaviour by its algorithm, read which implementation is loaded. And (b) only shows when the multiplied size is fractional - 14px x 1.30 is 18.2, which rounds to nearly itself, which is why 14px "agreed". |
| 65 | My first baseline rule floored the half-leading, from memory of Blink's `CalculateLeadingSpace`; the measurement (252 cells) said the line box's offset in a flex box rounds half UP, and only the leading INSIDE a line box floors | `baseline_y` composes both; `test_text.py` keeps a sample of the 252 | Remembered source is a hypothesis. It was half right, which is the dangerous amount: a 1-in-2 rule passes the cases you happen to think of. The probe took two minutes and settled it. |
| 66 | I widened every glyph quad by the atlas padding, reasoning that ink sliding past a quad's edge would otherwise be lost at a fractional pen. It made the Kbd "W" centroid WORSE (0.18 vs 0.08 off) and, in a full atlas, sampled a neighbour's texels - a 13-level speck outside the `text.mixed` cell | Removed; each quad is its bitmap | Caught only because the diff's summary line moved, **8 -> 13 levels, while every cell still said ok**, and I asked which pixel. A summary figure that moves is a pixel to find, not a number to note. And a fix argued from first principles is still a change to measure - this one had no measurement behind it at all. |
| 67 | `test_the_caret_lands_where_the_field_was_clicked` went red: its click was 4.0px into an "X" that hinting made 8 wide - EXACTLY its midpoint, a tie the old rounding sent to caret 1. The real "X" is 8.484, so 4.0 is before the middle and caret 0 is what Chromium does too | The click moves to +16, 6px in | A driven click on a glyph's midpoint measures the rounding, not the caret. Pick probe points well inside the region they claim to test. |
| 68 | Reverting `stock_text_y` turned nothing red: the TTFs' 800 / -200 split was chosen so ImGui's own centring lands on Blink's baseline at 14px in an even box - the only size the kit's Inputs use - so the guard was guarding a coincidence | `test_a_stock_input_puts_its_glyphs_on_the_labels_baseline`, at 11px/20 and 16px/36 where the two disagree; the revert fails both | Habit 3 again, and why it is a habit: the revert check is what found that the existing test could not tell. **A revert that stays green at the tested parameters means the parameters are the coincidence**, not that the code is redundant. |
| 69 | The KbdGroup test fed "B" as 7.9 wide, labelled as Chromium's `measureText`. Chromium says 8.256 | Corrected; harmless, since B's Kbd is min-w 20 either way | A constant labelled "measured" is a claim like any other. This one was never re-run, and nothing depended on it enough to fail. |

### What this batch says

The fix was in the font LOADER, and every component's text moved with it -
yet the pixel diff changed in only the six text cells and one speck,
because every text-sized chrome cell had its width pinned. Unpinning them
(the Kbd cells, and four Button sizes on both sides with `"intrinsic":
true`) is what turns the diff into a standing check on the text measure:
rendered with the OLD loader, those five cells FAIL at 26 levels / 2-3px;
with the new one they pass at 0-1. Row 61's lesson, applied: a pinned
dimension is a dimension nobody is checking.
