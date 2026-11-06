# What went wrong in this session, and what would have caught it

Every row is a real defect. Most were found by a person looking at the
running app, which is the part worth fixing: the kit has a pixel diff, a
browser oracle and 673 tests, and none of them saw these.

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

## Mine, found by me or by an agent

| # | Issue | Fix | What would have caught it |
|---|---|---|---|
| 18 | `test_gallery.py` booted a GL context per test and never shut one down, poisoning unrelated tests — and I reported those failures as a subagent's in-flight work | Boot, measure, tear down, then render | **Check `git diff` before attributing a failure.** My file was in the failing set the whole time. |
| 19 | The first "no scrollbar" test passed against the broken code — it read pixels in a region nothing ever painted | Assert at the call site instead | **Verify every new test against the broken code it covers.** A test that cannot fail is worse than no test, because it is counted. |
| 20 | `invisible_button` cannot take keyboard focus in ImGui 1.92.9, so the Button's focus ring — the "reference implementation" — had never painted | `ButtonFlags_.enable_nav` on `Ui.hit` | **Check that a reference implementation works before porting it.** Copying it would have shipped four more rings that cannot appear and four tests that cannot fail. |
| 21 | `combobox_size` reserved 36px for a search field the widget had stopped drawing | Removed | **Ask both halves the same question.** A size function and the thing it sizes should be tested against each other. |
| 22 | The empty state was still the Command recipe's — 68 tall, `popover-foreground` | Re-measured: 36, `muted-foreground`, `data-empty:p-0` | Same as 8: a correct measurement of the wrong component is still wrong. |

## The four habits these reduce to

1. **Refresh, then measure, then build.** `refresh_shadcn.sh` → `?probe` → kit → diff. Rule zero exists because an oracle built on a stale component is a confident wrong answer.
2. **Assert what a person sees.** Ink, not line boxes. A click, not a render. If the assertion needs a model of ImGui's internals to be meaningful, it is the wrong assertion.
3. **Make every new test fail first.** Revert the fix, watch it go red, put the fix back. Three tests in this session could not fail when written.
4. **Drive it before saying it works.** Not a screenshot of the chrome — a script that clicks, types, scrolls and dwells past the 150ms transition. Eleven of the sixteen reported defects were behaviours, and the pixel diff is blind to all of them by construction.
