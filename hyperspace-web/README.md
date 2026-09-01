# Hyperspace (web)

> **No longer under active development.** This is the original single-file HTML
> version of Hyperspace. Development has moved to the Python re-platform in
> [`../hyperspace-python/`](../hyperspace-python/). See the repository on
> [GitHub](https://github.com/Cutaiar/hyperspace) for the current work.

A 4D polytope viewer in a single HTML file. 18 shapes, from the 5-cell to the
600-cell, rotating through six planes. Audio-reactive: six frequency bands each
drive one plane via a Peak Controller-style transfer chain.

**Live: https://hyperspace-lake.vercel.app**

## Running it

`hyperspace.html` is self-contained — no build, no dependencies. Opening it
directly works for everything except live audio: Chrome refuses the microphone
on `file://`. Serve the folder instead:

```bash
cd hyperspace-web && python3 -m http.server 8000
```

Then open **http://localhost:8000/hyperspace.html**, or just use the live link —
both are secure contexts, so live input prompts normally.

## Audio sources

| Source | Key | Notes |
| --- | --- | --- |
| **Listen to mic** | `m` | Any input device. Pick which one under **Input device**. |
| **System audio** | `s` | Captures a browser tab's audio. Chrome and Edge only. |
| **Load a track** | — | Local mp3, wav, m4a or ogg, with play / pause / restart. |

### System audio

**A browser tab** — click **System audio**, pick the **Tab** list, tick **Share
tab audio**. No install, but Chrome and Edge only, and on macOS screen and window
shares come back silent.

**Anything on the machine** — [BlackHole](https://existential.audio/blackhole/),
a free virtual audio driver that installs as an ordinary *input* device, so
routed audio arrives through the normal microphone path.

```bash
brew install blackhole-2ch
```

If macOS blocks the driver, allow "Existential Audio" at the bottom of **System
Settings → Privacy & Security**, then restart. To hear the audio *and* visualise
it, make a Multi-Output Device in **Audio MIDI Setup** containing BlackHole and
your speakers, and set it as your output. Hyperspace preselects loopback devices,
so **Listen to mic** then just works.

Once that device exists, [`loopback`](https://github.com/Cutaiar/loopback) —
a small CLI extracted from this project — switches to it and back, and restores
your normal devices afterwards:

```bash
git clone https://github.com/Cutaiar/loopback.git
loopback/audio-route on       # snapshot, then route output and input via BlackHole
loopback/audio-route off      # restore the snapshot and discard it
loopback/audio-route status   # what is selected now, and whether a snapshot is held
```

It snapshots by device UID before changing anything, so a renamed device still
restores, and a second `on` keeps the first snapshot. `LOOPBACK_OUTPUT` /
`LOOPBACK_INPUT` override the auto-detected targets.

AirPlay speakers can't join a Multi-Output Device;
[Loopback](https://rogueamoeba.com/loopback/) can capture per-app audio instead.

### If live input is refused

Embedded previews (artifact viewers, doc embeds) run the page in an iframe with
no microphone or screen capture, so the request fails before any prompt. Use the
**Open in a new tab** button the page offers.

## Deployment

Hosted on Vercel as the project `hyperspace` under `cutaiar`. The Vercel
project's Root Directory is set to `hyperspace-web/`, so pushing to `main`
deploys; `vercel deploy --prod` from this directory ships manually.
`vercel.json` rewrites `/` → `/hyperspace.html` and sends the
`Permissions-Policy` header that lets the deployed origin use the microphone.
