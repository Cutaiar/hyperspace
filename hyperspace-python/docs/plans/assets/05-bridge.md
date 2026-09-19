# The lanes bridge — IAC setup and linking a lane in FL Studio

`hyperspace/bridge.py` (plan 05 task 1, plan 07 WP4c). Every frame the
analyzer's lanes go out a virtual MIDI port; the same messages coming in on
another port become `ext:<i>` sources for the routing table. Off by
default; `[bridge]` in `config.toml` turns it on (the section is documented
in `hyperspace/config.py`).

## 1. Make the virtual ports (macOS: IAC)

1. Audio MIDI Setup → Window → Show MIDI Studio → double-click **IAC Driver**.
2. Tick **Device is online**. Add a second bus with **+** so you have
   `IAC Driver Bus 1` and `IAC Driver Bus 2`.
3. Bus 1 carries Hyperspace → DAW; Bus 2 (only if you want lanes *in*)
   carries DAW → Hyperspace. Never point `in` at the bus `out` uses — IAC
   echoes, and the lanes come straight back as ext lanes.

Windows: loopMIDI, one port per direction, and use its names below.

## 2. config.toml

```toml
[bridge]
enabled = true
out = "Bus 1"          # substring of the output port name
in = "Bus 2"           # leave "" unless a DAW sends lanes back
encoding = "pitch"     # or "cc14"
channel = 0            # first lane's channel (0-based) — or the CC pair channel
rate = 100             # per-lane messages a second
send = ["lane:*"]      # every analyzer lane, in band order
```

Hyperspace prints `bridge: out IAC Driver Bus 1 (pitch, 16 lanes)` on
stderr when the port opens; it reopens on its own if the port goes away.

## 3. What is on the wire

| encoding | lane *i* | 14-bit value |
|---|---|---|
| `pitch` | pitch bend on channel `channel + i` (16 lanes) | bend + 8192 |
| `cc14` | CC `cc + i` (MSB) then CC `cc + i + 32` (LSB) on `channel` | MSB·128 + LSB |

Value: `u = lane / CEIL` (routing.py's normalization; CEIL = 2.6, the
fader asymptote), clamped to [0, 1], `v = round(u · 16383)`. A lane at
the asymptote is 16383, a nominal 1.0 is 6301. `param:<id>` entries in
`send` carry that param's effective (modulated) norm the same way.

Only changed values go out, at most `rate` a second per lane, so idle
lanes are silent.

## 4. Link a lane to a plugin knob in FL Studio

1. Options → MIDI Settings → **Input**: select the IAC bus, tick
   **Enable**, and set its controller type to *(generic controller)*.
2. Right-click the knob → **Link to controller…**.
3. Move the lane (play audio through Hyperspace) — FL latches the first
   message it sees:
   - `pitch`: FL links pitch bend natively and reads the full 14 bits —
     smooth motion, no zipper. Tick *Omni* off so the link is per channel
     (lane).
   - `cc14`: FL's *Link to controller* takes the MSB CC (7-bit motion);
     fusing the LSB needs plan 05's FL script (`fl/HyperspaceBridge/`,
     not written yet).
4. Pitch bend arriving on FL's own channels also bends any instrument
   listening there — set those instruments' MIDI input port to something
   other than the IAC bus, or drive lanes on channels no instrument uses.

## 5. Lanes into Hyperspace (`in`)

Automate a pitch bend (or a CC pair) in FL on a MIDI Out pointed at
Bus 2, or run a second Hyperspace with `out = "Bus 2"`. Both message
forms are decoded; lane *i* is `ext:i`, `u = v / 16383` — the same
normalization the sender's `lane:i` has, so a route keeps its depth when
it moves from one to the other. In `bindings.json`:

```json
{"source": "ext:0", "target": "view.bright", "op": "mod", "value": 0.3}
```

The ext vector is `in_lanes` long (16), becomes a source at the first
message, and lets its rows go when the port vanishes.

## Not yet

MIDI clock out (24 ppqn from a deck BPM) waits for a beat source (DJ
Link). OSC and the FL fusing script are plan 05 tasks 2 and 4.
