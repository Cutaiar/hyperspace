# Edge Lab

A single-page browser lab for the Sony **DualSense Edge** (and the plain
DualSense) over **WebHID**. You can see every control live, try routing
ideas on a small 4D visual, drive the light bar, rumble and triggers, and
run the hardware checks the Python driver still needs answered. It also
works with no controller: a simulator sends real report bytes through the
same decoder.

The bytes follow `hyperspace-python/docs/plans/assets/42-controllers/sony-hid.md`.
The lane names, sink channels and tape format are the Python app's
(`pads/sony.py`, `pads/gesture.py`, `devices.pad_effects`), so whatever you
find here carries over. The spec's §8 test vectors run on load: the badge in
the bottom-right corner should read `self-test 22/22 pass`; click it for the
details.

![Faithful view and the ideas canvas](shots/faithful-and-ideas.png)

## Open it

Use Chrome, Edge or Brave on the Mac. Safari and Firefox have no WebHID,
though the simulator still works in them. WebHID also needs a secure page,
so serve the folder from localhost:

```sh
cd prototypes/edge-lab
python3 -m http.server        # then open http://localhost:8000
```

**Connect the pad** with a USB-C cable, or over Bluetooth:

1. Hold **Create + PS** until the light bar flashes.
2. Open System Settings ▸ Bluetooth and connect the "DualSense Edge
   Wireless Controller".
3. Press **Connect controller…** and pick it.

Chrome remembers the device: the page reopens it on reload and when it comes
back after a disconnect.

**Only one program can hold the pad at a time.** If Chrome has it open, the
app may fail to open it, because hidapi opens it exclusively. Close the tab
(or press **Disconnect**) before you start Hyperspace with the pad. Quit the
app before you connect here. Steam can also grab the pad or its LEDs. If the
device list is empty or no reports arrive, check System Settings ▸ Privacy
& Security ▸ Input Monitoring for Chrome.

## Panels

- **Readouts.** Three views to compare for the app's on-screen pad:
  - **a · Faithful:** the Edge from above, each control lit where it sits.
    It shows the trigger travel and the resistance zone we set, the light
    bar colour, the player LEDs, both touch fingers, tilt, and the back and
    Fn buttons. In the simulator you can click controls to press them.
  - **b · Lanes:** every lane under the name a routing row uses (`pad:A`,
    `axis:LT`, `hat:UP`, `touch:pinch`, `motion:shake`, …). It also reads
    back what the sink channels `edge:0…8` were last sent.
  - **c · Cockpit:** a glanceable view for mid-set. Big stick dials have the
    trigger as an arc and the resistance as an outer band. The back and Fn
    buttons are loud on the edges, tilt is shown as a level, and presses,
    taps and shakes scroll past in a ticker.

  ![Lanes](shots/lanes.png)
- **Simulator.** Shown when nothing is connected, or turn it on with the
  checkbox.
  - Left stick `WASD`, right stick `IJKL`, D-pad on the arrow keys.
  - ✕ `Space`, ○ `B`, □ `X`, △ `Y`.
  - L1 / R1 `Q` / `E`; L2 / R2 `Z` / `C` (hold to ramp).
  - Create `V`, Options `N`, PS `G`, mic `M`; L3 / R3 `F` / `H`; touchpad
    click `T`.
  - Back buttons `[` `]`, Fn buttons `-` `=`.
  - Shake: `Enter`.
  - Drag on the touchpad for one finger, shift-drag for two (pinch and
    twist). Drag the tilt dot to tilt the pad. The model and transport can
    be switched, including the 10-byte BT simple report.
- **Ideas.** A tesseract with:
  - **4:** touch moves the zoom-blur centre, pinch zooms, twist turns XW, and
    everything springs back when the finger lifts.
  - **5:** a shake or a back button fires an envelope (10 ms attack, 300 ms
    decay).
  - **7:** feedback. The light bar follows the visual's hue, rumble.low
    pulses on a beat (metronome, tap tempo or the laptop mic's low band),
    and R2 drives a kaleido mix while the right trigger pushes back.

  **copy route** shows the app's rows for each idea and copies them.
- **Feedback.**
  - The nine sink channels in the app's order. Each has an on/off switch
    (off keeps the player identity), an auto setting driven by the demo,
    and a manual slider.
  - Raw controls: light colour, player LEDs, mic LED, both motors, and a
    trigger tester (Off 0x05, Feedback 0x21, Vibration 0x26). 0xFC–0xFE are
    refused before any write.
  - Take-over: Linux's runs automatically on the first write; SDL's reset
    is a button.
  - The last report as hex, with a write log.

  Writes go out only when something changes, at most 60 per second.

  ![Cockpit and feedback](shots/cockpit-and-feedback.png)
- **Probe.** Eleven guided steps that answer the spec's §9 open questions,
  plus the back-button, profile, Fn, axis, touch-range, USB-length,
  take-over and jitter checks. Each step saves its answer with the raw
  evidence; **Export findings JSON** downloads them all. Answers recorded in
  the simulator are marked as such.

  ![Probe](shots/probe.png)
- **Tape.** Records raw input reports in the app's tape format,
  `hyperspace.padtape/1`. The first line is
  `{"tape": …, "model": …, "transport": …}`. After it comes one
  `{"t": seconds, "r": "<hex>"}` line per report; the hex is the full
  report with its id byte first, as hidapi returns it. Notes, including the
  probe steps' prompts, become `{"t": …, "note": …}` lines.

## Back into the app

- **Tape.** Point a pad entry at the file with `tape = "file.jsonl"`. The
  app replays it (looping) as if the pad were plugged in.
- **Findings.** Give the JSON to the developer, or commit it under
  `hyperspace-python/docs/plans/assets/42-controllers/`. Its `proposed`
  block maps onto the driver's constants:

  | `proposed` field | driver constant |
  |---|---|
  | `axis_map` | `gesture.AxisMap` |
  | `touch_w` / `touch_h` | `sony.TOUCH_W` / `TOUCH_H` |
  | `usb_out_len` | `sony.USB_OUT_LENS` |
  | `bt_takeover` | the §5.3 take-over choice |
  | `update_version` | the rumble mode |
  | `stick_deadzone` | the dead zone |

  The `steps` hold the raw evidence behind each answer.

## What was checked, and what wasn't

These were checked headless with Playwright:

- The self-test: the CRC and encoder against the §8 vectors, decoding, and
  the gestures.
- The simulator: all three readouts, the ideas, the feedback writes, the
  probe steps (the axis probe proposes the identity map for the simulated
  pad), the findings export and the tape export.
- The WebHID code path, against a mock `navigator.hid`: the id-less input
  DataView, feature reads that come back with the id byte, Bluetooth
  simple → full, the outgoing BT sequence nibble and CRC, and the USB
  length taken from the descriptor.

**Real WebHID with a real pad has not been run yet.** That is what the probe
is for.
