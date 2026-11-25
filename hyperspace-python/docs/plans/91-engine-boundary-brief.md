# Plan 91 (brief): the engine's boundary — a network-addressable parameter surface

**Status: a brief, not a design.** Written 2026-11-25 for a long session the
owner will lead. Nothing here is decided except "What the owner said".
Tags: [R] read in the repository, [M] measured, [I] inferred, unverified.

## The goal, as the owner put it

Work out what the engine's parameter boundary should look like — a clean split
between the engine and any interface that controls its parameters, "a network
bridge, more or less" — so that ease of use is greatest for all future
consumers. Collate the disparate concerns: every faction of this program, the
areas it may expand into, and anyone with a stake in that split. Each belongs at
the table before an abstraction is chosen.

## What the owner said (2026-11-24/25)

- No move of the UI to Rust for now; the Python UI as efficient as possible.
- Not ready to decouple the UI from the renderer: many stakeholders, so the
  abstraction has to be done properly.
- The wish behind it: as much of each frame as possible for pictures, the UI
  out of the hot path.
- The owner leads this session, and it will be long.

## Who has a stake

A starting list, to be corrected and added to. For each: what it reads, what it
writes, how fast, what ordering and latency it needs, what it does on loss, and
what it must never see.

| Stakeholder | Where to look |
|---|---|
| The imgui panel and GRAPH editor (edit registry, table and graph objects directly) | `ui*.py`, `graphview.py` |
| Registry, shared meta params, parts (patch / shared meta / per-deck) | `params.py`, DECISIONS |
| Router, routes, modifiers, macros; LFO, envelope and sequencer banks | `routing*.py` |
| Two decks, the meta controller, crossfade, per-player pointers | `deck.py`, plans 44, 55 |
| Undo (what is a step, who may write) | `undo.py`, draft PR #506 (its list of writers) |
| Loadable patches, shows, the shared library, schema migration | `loadable.py`, `library.py` |
| Render graph, outputs, displays, hotplug | `graph.py`, `render.py`, `hotplug.py` |
| Thumbnails, previews, `panel:graph` (pictures crossing the boundary) | `outputs.py`, `replay.py` |
| Desks, pads, hands, totem, poi, Kinect (draft PR #503), OSC, MIDI bridge | `devices.py`, `midi.py`, `osc.py`, `bridge.py` |
| Dylan's desk work (another person's: a stake, not ours to redesign) | plans 13, 17, 31 |
| Audio analysis and tempo | `audio.py`, `analysis.py`, `tempo.py` |
| NDI and Syphon, two Macs | `media/publish.py` |
| Hot reload (live objects re-classed) | `hotreload.py` |
| Tests, `headless.py`, `tools/app_driver.py` (drive the panel by control id) | `tests/ui_driver.py` |
| The VST / DAW plugin: needs R1–R8 | branch `claude/vst-scope`, `docs/plans/90-vst-scope.md` §4 |
| Possible: phone, tablet or web controllers; remote or multi-person control; an agent or script as a client; recording and replay; a server or windowless engine | [I] |

Two other sessions of the owner's bear on this: **"Hyperspace architecture
exploration"** and **"Scope a Hyperspace VST plugin"**. The VST plan calls this
boundary "the control surface, being designed in parallel". This brief was
written without the first session's findings: ask the owner for them.

## Facts to start from

- One Python process, one frame loop (`app.frame`), with writes applied at fixed
  slots (ARCHITECTURE §2). [R]
- Python 3.14 with the GIL on this build, so a UI thread would share the
  interpreter with the renderer. [M]
- macOS wants window events on the main thread. [I: check GLFW's documentation]
- The UI's CPU cost on `field-wave-slow`, plain clocks, a fresh home with no
  devices: about 5.75 ms a frame on main at 40a23dc6, 3.8 with draft PR #502;
  drafts #505–#508 cut further. A sampling profiler roughly doubles it. [M]
- Many params' getters and setters close over plain attributes, and some code
  writes those directly; under a route a bare write and `Param.set` do different
  things. Draft PR #506 observes such writes, which the owner accepted, rather
  than migrating them. [R]
- `headless.py` is registry + library + router with no GL, audio or window: a
  test harness, not an engine. [R]
- Plan 58 §6 declined the UI-decoupling phases, for other reasons. [R, in plan 90]

## Questions to answer with the owner

1. What is addressable: values only, or routes, graph edits, patches, transport,
   pictures? One surface or several (state, commands, fast feeds, pictures)?
2. Who owns the truth, and what is an id's lifetime and version?
3. Base against effective value; subscription or snapshot; rates.
4. Where in the frame do outside writes land; what is one undo step; how do two
   writers meet (last touch, pointers, catch)?
5. Threads, processes or machines: what does each stakeholder really need, and
   what would the panel need to live out of the render process?
6. Transport, encoding, discovery, security on a venue network, loss.
7. What must not change: show safety, hot reload, the frame budget, the corpus's
   pictures, WYSIWYG graphs (no hidden edges).
8. The smallest first slice that serves two real consumers.

## How to work

Read REVIEW.md, ARCHITECTURE, DECISIONS and CHECKPOINT first. Gather each
stakeholder's needs before proposing; show the conflicts between them; offer
alternatives with costs; the owner decides. Findings become a plan in
`docs/plans/`. No application code and no merges until the owner says.
