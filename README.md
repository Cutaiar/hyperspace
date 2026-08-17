# Hyperspace

A 4D polytope viewer in a single HTML file. 18 shapes, from the 5-cell to the
600-cell, rotating through six planes. Audio-reactive: six frequency bands each
drive one plane via a Peak Controller-style transfer chain.

Open `hyperspace.html` in a browser.

## Audio sources

| Source | Key | Notes |
| --- | --- | --- |
| **Listen to mic** | `m` | Any input device. Pick which one under **Input device**. |
| **System audio** | `s` | Captures a browser tab's audio. Chrome and Edge only. |
| **Load a track** | — | Local mp3, wav, m4a or ogg, with play / pause / restart. |

### Visualising system audio

Two routes, because neither one covers everything.

**A browser tab** — click **System audio**, choose the **Tab** list in the
picker, and tick **Share tab audio**. No install, but Chrome and Edge only, and
on macOS it captures tabs only: screen and window shares come back silent.

**Anything on the machine** — use [BlackHole](https://existential.audio/blackhole/),
a free virtual audio driver. It installs as an ordinary *input* device, so once
your output is routed through it, everything playing on the Mac arrives through
the normal microphone path — any app, any browser. This is the same approach
[`samples`](https://github.com/Cutaiar/samples) uses.

```bash
brew install blackhole-2ch
```

macOS may block the driver: **System Settings → Privacy & Security**, scroll to
the bottom, allow the software from "Existential Audio", then restart.

To hear the audio *and* feed it to Hyperspace at the same time, create a
Multi-Output Device:

1. Open **Audio MIDI Setup**
2. **+ → Create Multi-Output Device**
3. Check both **BlackHole 2ch** and your speakers or headphones
4. Set that Multi-Output Device as your output in **System Settings → Sound**
5. In Hyperspace, pick **BlackHole 2ch** under **Input device** and click
   **Listen to mic**

Hyperspace detects a loopback device by name and preselects it, so in practice
step 5 is already done for you.

**AirPlay / wifi speakers** don't appear in Audio MIDI Setup and can't join a
Multi-Output Device. [Loopback](https://rogueamoeba.com/loopback/) by Rogue
Amoeba can capture per-app audio and route it to BlackHole regardless of where
the app is sending its output.

### If live input is refused

Embedded previews (artifact viewers, cloud previews, doc embeds) render the page
in an iframe that is not granted the microphone or screen capture, so the
request is refused before any prompt appears — no amount of clicking "allow"
helps. The page detects this and offers **Open in a new tab**, which reopens the
same URL top-level, where both work normally. `file://` pages in Chrome are
similarly hopeless; serve the folder over localhost instead.
