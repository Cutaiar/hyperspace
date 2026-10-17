# Plan 30 — performing *Father And Son* (not built)

The goal, in the owner's words (2026-10-17): perform Hyperspace to one
song, Boards of Canada's "Father And Son", from a cue sheet that is
triggered and played to the song. This file has four parts: what we know
about the song, how to perform it on today's app, cue sheet v0, and what
is missing, ranked.

The show file for cue sheet v0 is
[`assets/30-father-and-son/father-and-son.hyp.json`](assets/30-father-and-son/father-and-son.hyp.json).

## The song

| | | Source |
|---|---|---|
| Track | "Father And Son", track 5 of 18 on *Inferno* (Warp, 29 May 2026) | [Wikipedia](https://en.wikipedia.org/wiki/Inferno_(Boards_of_Canada_album)) |
| Length | 3:24.8 (204 834 ms) | Spotify |
| Tempo | 72 BPM (Shazam, Hooktheory). It may feel half-time over a ~144 BPM grid. One bar is 3.33 s, so the track is about 61 bars | [Shazam](https://www.shazam.com/song/1890015528/father-and-son), [Hooktheory](https://www.hooktheory.com/theorytab/artist/boards-of-canada) |
| Key | C♯ Locrian, the notes of B minor | Hooktheory |
| Material | A 1971 BBC *Man Alive* conversation: a son who left his family for a religious group, and his father. Auto-Tuned and "snapped to the snaking beat", answered by "corroded metallic babbles". Live drums, keys, bass, pad | [RA](https://ra.co/reviews/36354), [4columns](https://4columns.org/dayal-geeta/boards-of-canada), [WMNF](https://www.wmnf.org/sotd-7-3-26-father-and-son-by-boards-of-canada/) |
| Arc | "breaks the dam as the weirdest samples and out-there tones gush forth on a psychedelic wave … When the seismic bass line drops it's another wow moment." Elsewhere: "eerie and intense", "slightly sinister collage" | [Echoes and Dust](https://echoesanddust.com/2026/06/boards-of-canada-inferno/), 4columns |
| Timing hint | Shazam's most-identified moment is around 1:05 | Shazam |

**Not known:** where the sections fall. No review or forum gives
timestamps. The times in cue sheet v0 are guesses until someone listens
with the AUDIO page open and writes them down (step 2 below).

## Performing it on today's app

Everything below already works. No code is needed.

- **A GO button.** Put the cues on F1–F8 in song order. The APC40's
  **QUANT** (`preset.next`) steps to the next filled slot, which makes it
  GO. F1–F8 jump to any cue out of order, like hot cues. QUANT wraps from
  F8 back to F1, so don't press it after the last cue.
- **A fade.** The crossfader is the master dim (left is black). Use it to
  fade in, dip to black over a hard cut, and fade out.
- **Softer cuts.** The look-back's echoes and the dream (WAKE, TRACER)
  carry the old frame into the new one for a second or so.
- **Tempo.** TAP TEMPO four times on the beat, then METRONOME on the
  one. The synced LFOs then breathe on the bar. You can also type 72
  into `tempo.bpm`, which is K5 under SHIFT.
- **The song in the app.** AUDIO → *Load track* plays a wav, flac, mp3
  or ogg file into the analyzer and shows its position and length. K
  plays and pauses; 0 restarts. Spotify can't be loaded, so buy the
  file from Warp or Bleep. Capturing Spotify through BlackHole also
  works, but the app then has no position for the song.
- **The analyzer's scenes** are session-level, so a preset load never
  changes them. Switch them by hand with the scene pads: Glacial Drift
  for the voices, Bass Engine from the bass drop.

### The steps to a first performance

1. **Get the audio file.** Buy *Inferno* lossless from Warp or Bleep.
   The app plays a file in mono, which is fine for rehearsal. For the
   show, play the song from the DJ or DAW and capture it with BlackHole,
   or accept mono.
2. **One listening pass.** Load the track and open the AUDIO page. Each
   time the song changes, write down the time the page shows. Fill in
   the "at" column below and correct the section names.
3. **Install the show.** Copy `father-and-son.hyp.json` into your
   library's `projects/` folder, then open it on the PRESETS page. Use
   your own library or the shared one, by choice. Every cue is a
   factory preset, so nothing else needs installing.
4. **Audition each cue against its section** (F1–F8, track playing).
   Swap any preset that's wrong for the moment: right-click the slot,
   then *put preset here…*. Tune one, then ⇧F*n* saves it into that slot
   as your own copy. Shared presets need care: a tuned copy saved into
   the shared library reaches Dylan too.
5. **Rehearse three times** with the sheet printed or on the MacBook's
   screen. The QUANT presses should land on the downbeat. At 72 BPM a
   bar is 3.3 s, so there's time to count in.
6. **Record a take** (screen-record the output) and watch it back
   against the song.

## Cue sheet v0

The tempo is 72 BPM. "at" is a guess until step 2. The hands are
optional throughout; where a preset has a hand gesture, it's listed.

| Cue | Key | at | Section (guessed) | Preset | Desk | Why |
|---|---|---|---|---|---|---|
| 0 | — | before | Standby | TRACER loaded, crossfader at black | Analyzer scene **Glacial Drift** | Start from black |
| 1 | F1 | 0:00 | Voices, haze | **TRACER** (16-cell points and lines, 24 echoes) | Crossfader up over ~2 bars (7 s) | Sparse and ghostly. The talk is the subject, so the picture stays thin |
| 2 | F2 | ~0:15 ¹ | The beat locks in | **TUMBLE** (24-cell turned inside out in the 4D planes by the music) | TAP TEMPO ×4 on the beat, METRONOME on the one | The "snaking beat" drives the rotation directly |
| 3 | F3 | ~1:05 ² | The hook | **WAKE** (16-cell on plasma faces, echoes, the dream under it) | — | The warm, smeared, faded-film look, the closest to Boards of Canada |
| 4 | F4 | ? ³ | The seismic bass line drops | **HEX ENGINE** (hex grid of 24-cells rippling on the sub) | Analyzer scene **Bass Engine** | Made for a sub-bass entrance. A dip to black over the cut sells the drop |
| 5 | F5 | ? | The psychedelic wave: the weirdest samples | **NOITA** (warp, trip colour, fractals) | Right hand's height takes it a stage further. Pull back before the next cue | The peak. The only saturated, overwhelming moment |
| 6 | F6 | ? | The voices come back, eerie | **INVERSE HALO** (starfruit turning inside out under haloed rings) | Scene back to **Glacial Drift** | "Slightly sinister": slow, uncanny, after the overload |
| 7 | F7 | ? | Last groove | **FIELD** (nine 24-cells orbiting, camera pulled back) | Right hand's height fills the screen, then lets go | Pull back from the scene, a goodbye |
| 8 | F8 | ~3:10 | Outro | **TRACER** | Crossfader to black by 3:24 | Back to where it began |

¹ A guess: Boards of Canada tracks usually open with a few bars of texture.
² Shazam's peak is the only timing evidence.
³ Echoes and Dust puts the bass drop after the psychedelic wave's start, but gives no time.

The rule of thumb behind the arc: one peak (cue 5), voices bracketing it,
and the faded-film looks (TRACER, WAKE) at both ends. Hyperspace has no
colour-restraint control yet (the palette fold, plan 24 stream C), so
keep the hue-cycling looks (TRIP, ACID, MANDALA) out of this song.

## What is missing, ranked

Ranked by what it gives this performance per line of code. The research
behind it is summarised in the next section.

1. **A cue track locked to the song's playhead.** Most of the gain for
   very little new code. `AudioEngine.position()` (`audio.py:253`)
   already measures the playhead by the frames actually played, so it
   can't drift. `preset.load.k` already exists. What it needs:
   - A cue list in the show file: rows of `{at, slot, name, note, fade}`.
   - Each frame, fire the rows whose `at` the playhead has just passed.
   - A **record** mode: play the song, press GO at each change, and the
     presses become the `at` column. This replaces step 2's pen and
     paper, and matches how grandMA timecode recording works.
   - A cue strip on the PRESETS page: the playhead, the standby cue, the
     time to the next cue, and a big GO.
   - **Hold**, so the performer can stop auto-advance and take over by
     hand.
   - Audio-side changes: a seek (the engine has only restart today), an
     option to play once instead of looping (it loops today), and stereo
     output (it plays mono today).
   - Seeking should land in the state of the last cue before the new
     position (lighting's "chase"), never replay every cue before it.
     VDMX users report the replay problem.
2. **A fade time per cue.** A preset load is a hard cut today
   (`Bank.load_slot` → `presets.load`, `library.py:769`). Two versions:
   - **Cheap:** a cue's `fade` ramps `output.dim` down and back up
     around the load, an automatic dip to black.
   - **Real:** a preset morph. Glide every continuous performance param
     from the old value to the new over `fade` seconds, and switch the
     discrete ones (shape, enums, routes) at the midpoint, under the
     dip. Ambient work needs 4–30 s fades; Resolume caps layer
     transitions at 10 s and users complain about it.
3. **GO quantized to the bar.** The clock already knows the bar
   (`tempo.py`, `bar(t)`). A GO press, or a cue fired by hand, would
   wait for the next downbeat, like Resolume's Beat Snap. Not needed
   when the cue track follows the playhead.
4. **Cues from a DAW over MIDI notes.** If the song plays from Ableton
   or FL, note *n* on a cue channel would mean "load slot *n*". This is
   the usual Ableton → Resolume route. Today the MIDI adapter opens a
   single port (the APC40), and the bridge's `ext` lanes are continuous,
   with no notes and no triggers. Plan 27's device registry ("several
   MIDI ports") is the place for this, so build it there rather than
   here. MIDI notes give no absolute position, so a locate in the DAW
   doesn't restore the state.
5. **A song-section panel.** Rekordbox and SoundSwitch analyse a track
   into intro, build, drop and outro, and assign looks per section. With
   one song, a person listening once (step 2) is cheaper and better.
   Not worth building for this performance.

## How other tools do it (the research, condensed)

| Paradigm | Examples | What we take |
|---|---|---|
| GO-button cue list: playhead, standby cue, pre- and post-wait, auto-continue | QLab, grandMA3 (Go / Time / Follow triggers, CueIn fade, notes) | The cue strip, GO and Hold, a note on each cue |
| Clip grid, column launch, crossfader | Resolume, Ableton Session, Synesthesia | We already have it: the bank is the grid, the crossfader the dim |
| Beat-quantized launch | Resolume Beat Snap (beat, bar, 2, 4 or 8 bars), MadMapper 6 | Item 3 |
| Timecode-locked timeline | Resolume Arena SMPTE, grandMA3 timecode shows, Millumin LTC/MTC, MadMapper 6 Conductor | Item 1, with the app's own audio playhead as the timecode, so no SMPTE is needed |
| Timed cue list as a table | VDMX Cue List (time, target, value, title, enable; CSV in and out), the TouchDesigner Timer CHOP over a Table DAT | Item 1's data model |
| DAW MIDI notes as the cue track | Ableton → IAC → Resolume | Item 4, on plan 27 |
| Phrase analysis that scripts the show | Rekordbox Lighting, SoundSwitch Autoscript, Synesthesia Auto Transition | Item 5, skipped |
| Timed preset changes with a soft blend | MilkDrop/projectM (5 s blend, beat hard cuts) | Item 2's morph |

Sources: [QLab cue sequences](https://qlab.app/docs/v5/fundamentals/cue-sequences/),
[grandMA3 sequence sheet](https://help.malighting.com/grandMA3/2.2/HTML/cue_sequence_sheet.html),
[Resolume clips](https://resolume.com/support/en/clips),
[Resolume SMPTE](https://resolume.com/support/en/smpte),
[Resolume BPM](https://resolume.com/support/en/bpm),
[MadMapper 6 timelines](https://docs.madmapper.com/madmapper/6/10.-timelines),
[VDMX Cue List](https://vdmx.vidvox.net/tutorials/introduction-to-the-cue-list-plugin),
[TouchDesigner Timer CHOP](https://docs.derivative.ca/Timer_CHOP),
[Rekordbox Lighting](https://rekordbox.com/en/support/faq/lighting-7/),
[Millumin timecodes](https://help.millumin.com/docs/connect/timecodes/),
[VDMX cue replay issue](https://discourse.vidvox.net/t/cue-list-clips-are-triggered-even-if-playback-point-is-later-timecode-than-cue-point/1954).
