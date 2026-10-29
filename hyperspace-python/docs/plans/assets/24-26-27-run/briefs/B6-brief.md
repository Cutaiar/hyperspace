# Plan 27 B6 — several gamepads at once

Branch `plan-27-b6-pads` off `plan-24-26-27-integration` at **9744cac** (PR
#195's head; it already contains all of `main`). PR into
`plan-24-26-27-integration`, titled
`Plan 27 B6: several gamepads at once — the role qualifier on any repeatable kind, a joystick per pad device`.
Owner's ask (2026-10-15): "support multiple game controllers at once
without having to change much". Plan 29's wands and drums repeat the same
way, so the mechanism is built once, generally, and the pad is its proof.

## Where it stands today (read these; line numbers as of 9744cac)
- `routing.py:297–330`: the device qualifier `@` is **MIDI only**:
  `base_scheme()` strips it only for `MIDI_SCHEMES`; `Binding.device`
  (`:615`) returns the role only for a MIDI head; `Binding.bare`,
  `Bindings.midi_roles` / `role_of` / `is_primary` settle which MIDI role
  an unqualified row means (the first listed whose profile matches).
- `devices.py:1082–1106` `make()`: a second enabled entry whose class
  **feeds** a scheme an earlier entry already feeds becomes
  `RefusedDevice` (`:372–390`, "feeds 'axis', which pad already feeds — not
  opened"). `PadDevice` (`:508`): `kind = "gamepad"`, `schemes =
  ("axis", "pad", "hat")`, `feeds = ("axis",)`, `wants = ("pad",)`; its
  `sources` (`:543`) are unqualified ports; `MidiIO.qualifier` / `sources`
  (`:433`, `:468`) show how MIDI qualifies its ports for a non-primary role.
- `gamepad.py:264` `Pad`: on every `poll` takes the **first** present GLFW
  joystick (`:301–305`), else the one `UsbPad` libusb reader (`:173`, the
  wired Afterglow). `learn_from` (`:387`) writes unqualified `pad:` /
  `axis:` / `hat:` rows. The sticks' default camera job (`:437–449`) runs
  on every axis no route names (`router.claimed("axis")`); the pad's feel
  is the five `desk.pad.*` session params (`routing.py:1495–1515`).
- `bindings.default.json:52–56`: the factory pad rows (`pad:A` …
  `pad:MENU`), unqualified; `PAD_REMAP` / `PAD_NEW_ROWS` migrate them.
- Docs that state the one-device-per-scheme rule and must change:
  `docs/plans/27-device-registry.md:178–181`, `docs/ENGINEERING.md:1012–1015`
  (and its `[[devices]]` key table for the gamepad kind), the register row
  that records the rule (find it in `docs/DECISION-REGISTER.md`'s plan-27
  section, rows 140–168: grep "already feeds").
- Tests: `tests/test_devices.py`, `test_device_inputs.py`,
  `test_gamepad.py`, `test_pad_learn.py`, `test_routing.py` (the qualifier
  tests for MIDI are the model), `test_app_boundary.py` (the gated imports
  and ORDER: do not change them).

## The design (the orchestrator's rulings; build as written, record each as a register-row draft)
1. **The qualifier is general.** A source head may carry `@<role>` for any
   scheme: `base_scheme`, `Binding.device`, `Binding.bare`,
   `is_continuous` and whatever else keys on `MIDI_SCHEMES` for the
   qualifier work for every scheme. The rule "an unqualified row is the
   first listed device's that feeds that scheme" generalises from
   `midi_roles` to a per-scheme primary (keep the MIDI profile-matching
   rule exactly as B2 built it for MIDI schemes; for other schemes the
   primary is simply the first enabled device of that kind in list
   order). **Every MIDI test passes untouched**: MIDI's behaviour is the
   same to the byte. Every pre-run row (`pad:A`, `axis:LX`, `hat:UP`)
   means the first pad, as it does today; **no file migrates**.
2. **The registry claims (scheme, role), not scheme.** `make()` refuses
   only a true collision: two enabled entries of one role, or a kind that
   cannot qualify (see 5). A second pad (`role = "p2"`, `kind =
   "gamepad"`) publishes `axis@p2:*`, `pad@p2:*`, `hat@p2:*` as its Router
   keys and ports (`PadDevice.publishes` / `sources` qualified the way
   `MidiIO.sources` does for a non-primary desk), so Learn, ROUTING's combo,
   the live bars and the SYSTEM line all work with no page change.
3. **Each pad device reads its own controller.** `Pad` takes the next
   present GLFW joystick **not taken by another pad device** (a shared
   set of taken jids on the module or the registry context), in list
   order; an optional entry key `joystick = <n>` (0-based GLFW index,
   validated in `config.py`'s per-kind keys) pins one. Unpinned: a pad
   whose joystick leaves reads `lost` and takes the next free one that
   appears; pinned: it waits for that index. The libusb reader stays
   **one**: the first enabled pad entry with `usb = true` owns it; a
   second with `usb = true` gets a note on its line ("usb: p1 has the
   wired pad") and reads GLFW only. Say so in ENGINEERING §5.
4. **Defaults author no look (decision 24).** The sticks' default camera
   job belongs to the **primary pad only**; a second pad's unrouted axes
   do nothing until a route names them. The factory pad rows and
   `PAD_REMAP` / `PAD_NEW_ROWS` are the primary's; a second pad starts
   with no rows and gets them from Learn or ROUTING. The pad feel
   `desk.pad.*` stays one set applied to every pad (per-pad feel is a
   register-row rough edge for plan 28/29).
5. **Hands stay single.** The hands kind keeps the refusal ("feeds
   'hand', which leap already feeds") — its forty lanes are a different
   shape and two Leaps are plan 29's. Register it as the known limit.
6. **Status and words.** SYSTEM shows one line per pad device as today
   (`p2 · gamepad · connected (glfw 1)` or whatever the line format is;
   add the joystick index to the pad's `last`/status detail so two pads
   are told apart). The ROUTING combo labels a second pad's ports with
   the role, as MIDI's are.

## Tests (write them first)
- `test_routing.py`: `base_scheme("axis@p2") == "axis"`, `Binding("pad@p2:A", …).device == "p2"`, `.bare == "pad:A"`, `.scheme == "pad"`; an unqualified `pad:A` row's `device` is "" and resolves to the primary pad; `is_continuous("axis@p2")` True, `("pad@p2")` False; the MIDI cases unchanged (copy the existing assertions and keep them).
- `test_devices.py`: two enabled gamepad entries (`pad`, `p2`) both open, p2's `sources` are qualified, `schemes()` lists both sets, `wants()` includes `p2`'s; two entries with the same role → the second refused; `hands` twice → refused as today; the SYSTEM text names both pads with their joystick index; `make_all` with `joystick = 1` on p2 pins it; config rejects `joystick = "x"`.
- `test_gamepad.py`: with two fake joysticks present, two `Pad`s take different jids in list order; pad 1's joystick vanishing → `lost`, a third appearing → taken by the lost pad (unpinned); a pinned pad waits; only one `UsbPad` is ever constructed across two pads with `usb = true`.
- `test_pad_learn.py`: Learn on p2 writes `pad@p2:A` / `axis@p2:LX` rows; a `push` route from `axis@p2:LX` moves its param while `axis:LX` (the primary) is untouched, and vice versa; the camera job ignores p2's sticks; `router.claimed("axis")` semantics for the primary unchanged.
- `test_device_inputs.py` / the pre-run bindings test: a pre-run `bindings.json` with pad rows loads with no note and no dirt and every row means the primary pad.
- Boundary tests (prompt lines 1177–1245 of `docs/plans/24-26-27-orchestrator-prompt.md`) untouched.

## Docs (this WP writes its own; no docs WP follows)
- `docs/plans/27-device-registry.md`: a **B6** section as built (the
  model of its B1–B4 sections), the rule text at :178–181 rewritten, the
  `[[devices]]` block for two pads, the rough edges (one USB reader; one
  feel; hands single; no factory rows for p2).
- `docs/ENGINEERING.md` §5 (the gamepad kind's keys incl. `joystick`; the
  two-pads sentence at :1012–1015), §7 (the pad) where it says one pad.
- `docs/DECISION-REGISTER.md`: new rows from **210** under
  `## The device registry (plan 27)` (the general qualifier; the per-pad
  joystick and the one USB reader; the primary-only camera job and no
  factory rows for p2; hands single), on the answer sheet too; amend the
  row that states the one-scheme rule ("Changed in B6: …") the way B5
  marked row 60. `docs/DECISIONS.md`: the "Inputs and devices" rows that
  say one pad.
- `docs/plans/11-hand-checks.md`: check **219** in group W (after 190, keep
  V's 191–218 where they are): two pads at the machine — the Xbox pad
  over Bluetooth and the wired Afterglow over USB; both lines
  `connected` with different indices; Learn a param from each; both drive
  at once; unplug one, its line reads `lost`, the other keeps working;
  replug. *Pass:* / *Fail:* with the likely cause. README's
  "numbered 1–219"; `docs/TESTING-GUIDE.md` Part 2 (f) the pad: a short
  entry ending with its number.
- `docs/ARCHITECTURE.md` §3.3's scheme table if it says the qualifier is
  MIDI-only (grep `@`); the HTML only if the same sentence is there.
- The decisions file (path below) with the register-row drafts, the
  hand-check draft and as-built notes, as every WP in this run wrote.

## Rules
Common brief: `hyperspace-python/docs/plans/assets/24-26-27-run/briefs/common.md`
(the workspace paths are replaced by the ones here; your own session's
attribution; the "do not edit the docs" list does not apply — you write
the docs above and nothing else in them). Never touch `~/Hyperspace` or
`~/My Drive/Hyperspace`; every run uses a scratch `HYPERSPACE_HOME` under
`/Users/dallman/.claude/jobs/b8e1c57e/tmp/b6/`. `hyperspace/library/`
byte-identical; no golden moves; the core never imports the adapters;
`graph.py`/`render.py` untouched. TDD. No sub-agents. If a ruling above
cannot be built as written, build the rest and say exactly which and why.

## Setup
```
git fetch origin plan-24-26-27-integration
git reset --hard FETCH_HEAD           # HEAD must be 9744cac or later
git branch -m plan-27-b6-pads
```
Run from `<worktree>/hyperspace-python`.

## Gates
```
uv run pytest -q                      # 2196 + yours
uv run ruff check .
uv run pytest tests/test_golden_frames.py -q    # 556 match
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES
```
The smoke run: a scratch config with two gamepad entries (`pad`, `p2`),
no MIDI, no hands; exit 0, empty stall log, the SYSTEM page's two pad
lines read `lost` (no controller on the build Mac is fine) — paste them.

## Report, decisions, PR
Decisions: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/decisions/B6.md`.
Report: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reports/B6-report.md`
(fallback `<worktree>/.sdd/…`). PR body: what was built, the rulings
taken, the boundary assertions consciously changed (name each with its
reason; expected: none), the gate lines, the two-pad `[[devices]]` block.
Reply with ONLY (under 15 lines): Status; base SHA; commits; PR URL; test
summary; concerns; report path. You may be resumed with review findings.

## Amendment to ruling 3 (orchestrator, 2026-10-15, after the build)
The USB reader is **lent, not owned**: it goes to the first enabled pad
entry with `usb = true` that currently has **no GLFW joystick**, re-decided
on each poll in list order. A pad that reads a GLFW joystick never takes
the reader. So the owner's rig — the Xbox pad over Bluetooth on `pad`
and the wired Afterglow on `p2`, both `usb = true` — reads both with no
config trick; `usb = false` is no longer needed on the Bluetooth entry.
Only one `UsbPad` reader object ever exists; it is passed between pad
devices (or held on the module / the registry context) rather than
constructed per device. Update ENGINEERING §5, the B6 section, check 219
and the config block accordingly, and the note "usb: pad has the wired
pad" becomes "usb: lent to p2" (or no note when the reader is idle).
