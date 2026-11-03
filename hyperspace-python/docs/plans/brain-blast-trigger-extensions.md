# Brain blast — trigger extensions: the pad node's optional add-ons

**Speculative. Not a plan item, no decisions, no register rows, nothing
built in the app** (2026-11-02). One half of it *is* built, in the browser
lab: `prototypes/edge-lab/` grew a **Triggers** tab that plays every effect
the DualSense's triggers can make, so the feel can be settled by a hand
before any of this is designed for real. This file is the other half — the
shape of the thing that would let the app do it — written down to be rolled
into a later plan.

## The ask (Dillon, 2026-11-02)

> Dan says that when you fire a sniper rifle you've got to take the slack
> out by pressing it gently at first. Then you hit a stop point. The trigger
> has a certain amount of tension that is required in order to drop the
> hammer.
>
> That was one of the main goals of the DualSense Edge: to accurately
> simulate precision shooting and basic recoil dynamics in shooter games —
> probably brake pedal mechanics in racing games too.
>
> What we want is a **lightweight, context-free abstraction** that lets us
> control that without every single thing this controller touches having to
> be aware of it. The controller, as it stands, when it sits on the graph,
> is a gamepad node — but it probably needs **optional add-on nodes** that
> feed into the controller node and tell it how to do special things.
>
> You could maybe make that out of basic nodes if you were a real brainiac.
> Oh hey — those would just be patches, if you could make them out of basic
> nodes. We can frame this as a patch, but it's highly likely that either
> the controller node needs to be a somewhat extensible thing with different
> flavours depending on which controller it is, or the controller node has
> the ability to link to… almost like **vector extensions in x86**. You have
> one instruction set, then you get these extra instructions that you may or
> may not have, and that attaches to the main processor.

So: one base instruction set every pad answers to, and optional extensions
that attach to a pad that has them — which the rest of the graph never has
to know about.

## What the hardware can actually do

Four official effects, 11 bytes each, from
[`assets/42-controllers/sony-hid.md`](assets/42-controllers/sony-hid.md) §6:

| mode | what the finger gets | the parameters |
|---|---|---|
| Off 0x05 | nothing in the way | — |
| Feedback 0x21 | a push-back, **per zone**: ten zones down the travel, each 0–8 | a 10-bit zone mask and 3 bits of force per zone |
| Weapon 0x25 | **the sniper trigger**: slack, a wall from `start`, and past `end` it gives way at once | start 2–7, end start+1…8, strength 1–8 |
| Vibration 0x26 | it hums under the finger, **per zone**, at one frequency | the same mask and amplitudes, plus Hz in byte 9 |

Two things fall out of that table and decide everything below.

- **A zone mask with gaps is the interesting form.** One force over one run
  of zones is the boring case; ten independent forces is a *curve* — linear,
  curved either way, S, inverse, stepped, sawtooth, detents. The resolution
  is ten steps and that is all there is, so the staircase is the instrument,
  not an approximation of one.
- **One mode per trigger per report.** A shape and a buzz can never be felt
  at the same time. Recoil — a wall that fires — is therefore not one
  effect; it is *a wall, then a buzz, then the wall back*, a small state
  machine in time. Anything that feels alive is a stream of blocks, not a
  setting.

0x22 / 0x23 / 0x27 (bow, gallop, machine) are unofficial and may be removed
from the firmware; 0xFC–0xFE corrupt the trigger until the controller is
reset. Both stay out. Everything they do can be built out of the official
four by re-sending, which is what the lab now does.

## What the app can do today

The pad already **is** a node on the canvas: `device:<role>`, kind
`device` (`graphview.device_node`, `hyperspace/graphview.py:611`), grey
when nothing is connected. But it is a node with **outputs only** — its
`sources` are `axis:`, `pad:`, `hat:`, `touch:`, `motion:`
(`hyperspace/devices.py:689`). Feedback *into* a pad is deliberately not
on the canvas at all: sink rows are dropped from its cables
(`hyperspace/graphview.py:1592`) and live on the ROUTING page and in the
param right-click's **Learn sink ▸** menu instead.

A sink row is `{"source": "param:…", "target": "<role>:<n>", "op": "send"}`,
one scalar per channel, nine channels (`devices.SINKS`,
`hyperspace/devices.py:916`), applied each frame by `routing.sink_values`
→ `PadDevice.send` → `devices.pad_effects`. Channels 5 and 6 are the
triggers, and `pad_effects` turns each one into exactly this
(`hyperspace/devices.py:987`):

```python
sony.Trigger("resist", start=TRIGGER_START, strength=u)    # one wall, from 15 % of the travel
```

So the whole of the app's trigger vocabulary is **one uniform wall per
side, from a fixed zone, driven by one number**. Every pair in the lab's
new bench is outside it.

Three constraints worth keeping in mind, because they are not accidents:

- **Sinks are the rig's, not a preset's.** `is_session_row`
  (`hyperspace/routing.py:1836`) — "sinks are rig (D1/D9)" — so they live
  in `bindings.json`, never travel in a preset, and `patches.check` refuses
  a row whose target is a device port ("nothing of the patch's",
  `hyperspace/patches.py:721`). A patch cannot carry its own feedback; the
  lab's six example patches (ideas 8–13) each ship a separate
  session-rows file beside them for exactly this reason.
- **Capability gating already exists.** A channel is only offered if the
  model says it has it (`SINK_CAP` against `model.outputs`,
  `hyperspace/devices.py:751`): a Joy-Con shows rumble and player lights and
  no light bar. The CPUID check Dillon is describing is already in the
  codebase, one layer down.
- **A vector-valued wire is reserved and unbuilt.** `graph.VALUE` is
  documented as "a scalar or a small vector of floats a node publishes once
  a frame", with "no node publishes or reads a VALUE in this plan" and a
  test that enforces it
  (`hyperspace/graph.py:168`, `test_the_value_port_type_exists_and_no_node_uses_it`).

## The gap, in one line

A trigger effect is **a shape over travel, plus a state machine in time**.
A sink channel is **one float**. No amount of routing a float harder gets
you a sniper break.

## Three ways to close it

### A · A fatter pad node — more channels per flavour

Add `trigger.left.mode`, `.start`, `.end`, `.freq`, `.zone0…9`, … to
`devices.SINKS` and let the existing machinery carry them.

Cheap, and wrong. The channel list is one flat table shared by every pad;
a DualSense's zones would sit next to a Joy-Con's HD rumble and an APC40's
nothing, gated by a growing pile of caps. Ten zones as ten scalar rows is a
routing page nobody can read, and the state machines (recoil, bowstring)
still have nowhere to live. **Rejected**, but it does set the floor: if the
answer is harder than this, it had better buy something.

### B · Extension nodes attached to the pad node — the x86 analogy

The pad node keeps its base instruction set (the lanes out, the nine
channels in). An **extension** is a separate node that owns one capability
of one pad:

```
   [ trigger shape ]──┐
   lanes, params in   │  trigger:right
                      ├──▶ [ device:edge ]   ← the pad node, unchanged otherwise
   [ recoil ]─────────┘  trigger:left                axis:/pad:/touch:/motion: out ▶
```

- The extension's output port is a **trigger shape**, not a float: mode +
  ten forces + Hz. That is a small fixed record, and it is exactly what
  `graph.VALUE` was reserved for.
- Only the extension knows about zones, modes and bytes. The pad node asks
  "who is driving my right trigger this frame?" and hands the record to the
  driver. **Context-free**: nothing else in the graph learns that triggers
  exist, which is the whole ask.
- The pad node **advertises what it has**, the same way it already gates
  sink channels. Plug a trigger extension into an Xbox pad and the node
  greys out and says so, rather than silently doing nothing — a `cpuid`
  check with a visible answer.
- Different controllers get different extensions rather than one node with
  flavours: an Edge offers *trigger shape*, *weapon*, *recoil*; a Joy-Con
  would offer *HD rumble* (its own thing entirely); an Xbox pad offers none.
  New controller, new extension, no change to the pad node.
- A state machine (recoil's wall → kick → wall) lives **inside** the
  extension and is fed by the travel the pad already publishes
  (`axis:RT`) — it needs no new input plumbing, only a per-frame tick.

**This is the recommendation.** It is also the only option that answers
"without every single thing this controller touches being aware of it".

### C · Build it out of basic nodes — then it is just a patch

The seductive one, and Dillon is right that it is the real test: if a
recoil extension can be made of a modifier, an envelope and a few rows,
then it is a patch, it ships in the library, and the app needs no new node
kind at all.

Today it cannot be, for two reasons, both fixable and both worth knowing:

1. **No wire carries ten numbers.** Modifiers and params are scalar
   (`params.Kind` is continuous / enum / toggle / trigger / text). A shape
   would have to travel as ten separate rows, which is option A wearing a
   hat.
2. **A patch cannot carry its own feedback.** `patches.check` refuses a row
   aimed at a device port, by design. A patch that *is* a trigger effect
   would have to be allowed to own its outputs — a real decision about what
   a patch is, not a plumbing detail.

So: keep C as the long game and as the **design test for B**. If B's
extension node turns out to be "a record-valued output, a tick, and some
arithmetic", then C is reachable later by giving `VALUE` a producer and
letting a patch own a sink. Build B in a way that does not block that.

## What would have to be true (if it is ever built)

1. A record-valued port — `VALUE` gets its first producer and its guard
   test (`test_the_value_port_type_exists_and_no_node_uses_it`,
   `tests/test_graph_effects.py:432`) is replaced by a real one.
2. A node kind that ticks per frame and can read a lane
   (`axis:RT`) without a routing row — or a routing row that targets an
   extension's input, which is the more honest version.
3. `pad_effects` stops being the only writer of `sony.Trigger`: a pad's
   effects become "the identity, then the sink channels, then whatever an
   extension owns" — in that order, with the extension winning the side it
   owns and the channel falling back when nothing does.
4. The mode allow-list stays where it is, in `sony.trigger_block`: an
   extension names an *effect*, never a mode byte. 0xFC–0xFE stay
   unreachable from the graph.
5. Ownership: an extension that drives the rig's pad is rig-shaped, like a
   sink — unless (C) a patch is allowed to own its outputs. **This is the
   decision the whole thing rests on**, and it is the same decision plan 42
   deferred when it gave each example patch a separate session-rows file.
6. Write cadence: nothing new. Effects already go out only on change, at
   most 60 (lab) / 100 (app, §7) a second. A 110 ms recoil kick is about
   seven writes. Worth checking over Bluetooth, where plan 42 measured the
   link pacing input at about 64 reports a second.

## What the bench found out (2026-11-02)

Building all of it turned up three things the design has to answer for.

- **"Still shape" and "loop" are different kinds of thing, and the loop is
  the unexplored one.** Six of the bench's recipes — mass, stiction, the
  retreating wall, sticky memory, ratchet, idle — *cannot be written down
  as a shape at all*. They are a function of the finger's speed, or of
  where it paused, or of time alone. Every published preset bank is still
  frames, because every published tool exposes a still frame. A trigger
  with mass is three lines in a loop and feels like nothing else on the
  pad. **Whatever the extension node is, its tick is the feature; the
  record is just what the tick emits.**
- **The protocol's resolution is not the hand's.** Eight force levels is
  the firmware's limit, but a host that rewrites the block every frame can
  dither between two levels and buy fractions of a step — the bench has a
  switch for it on every recipe. It costs one write per frame (measured:
  57 a second, at the 60 Hz coalescing cap), so it is a real trade, and
  whether a finger reads it as a half-step or as a flutter is a hand's
  question. If it works, the useful vocabulary is roughly twice the size
  the spec implies.
- **The interesting inputs are not the pad's own.** The music recipes read
  ten frequency bands and the lab's tempo; the gauge reads the battery and
  the report rate; coupled reads the *other* trigger. In the app all of
  those are already lanes or analyser outputs — which means an extension
  node wants **ordinary graph inputs**, not a private channel to the pad.
  That is a point in favour of option C's end state: if the inputs are
  ordinary wires and the output is one record, the gap between "a node" and
  "a patch" is small.

## What the lab already settles

`prototypes/edge-lab/` ▸ **Triggers** is the bench: a recipe per side, the
ten zones drawn exactly as the firmware got them, the 11 bytes under them,
and a trace of your own finger with every shot marked — how long the slack
took, how long you held on the wall, how far down it broke.

Twenty-seven recipes in six families, each a candidate extension node with
the parameters it would need already named:

| family | recipes | what an extension of this kind needs |
|---|---|---|
| still shapes | wall, response curve, detents, snap-to, grit | a shape record, nothing else |
| weapons | sniper break, recoil, fatigue, the jam, bowstring, gallop | a record, a tick, and its own state |
| the loop | mass, stiction, the retreating wall, sticky memory, ratchet, idle | a tick **and the trigger's travel back as an input** |
| music | buzz, engine, play notes, the beat, the spectrum, the scope | a tick and an ordinary wire from the analyser |
| readouts | gauge, countdown | a tick and a wire from anything at all |
| both hands | coupled | the other side's travel — one pad, two extensions, talking |

The "pairs worth feeling" buttons are the demos, grouped the same way.

**What a hand still has to answer, at the pad:**

- Can a finger tell ten zones apart, or is the useful resolution three or
  four? That decides whether a *curve* is one node or a gimmick.
- Does dither read as a half-step or as a flutter? If it works, the force
  vocabulary roughly doubles for the cost of a write per frame.
- Does *mass* feel like weight, or just like a wall that comes and goes?
  The whole argument for a per-frame tick rests on that one.
- Is *idle* below the threshold of feeling? Force 1 is the firmware's
  floor; there may be nothing under it.
- Does the trigger motor's rattle read as recoil, or just as a buzz? Does
  the body's heavy motor behind it matter?
- How much of the sniper's three stages survives at the real break? Dan's
  distinction is slack / wall / break — the bench's trace will say whether
  the hand finds the wall or just squeezes through it.
- Over Bluetooth, do the re-sent recipes (engine, gallop, recoil) stay
  crisp, or smear?

Answer those with the Edge in hand, and the node list above stops being
speculative.
