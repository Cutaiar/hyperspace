# Testing guide — what a person still has to check

This is everything about Hyperspace that only a person at the machine can
test, written so that someone who has never seen the project can follow
it. **None of it has been run by a person yet.** Part 1 is everything you
can do with the laptop alone. Part 2 is everything that needs a device
plugged in, grouped by device so that each one is set up once.

Each entry says what it **needs**, what to **do**, what you should see if
it is **right**, what **wrong** looks like, and, where the test changes a
file, what **changes** and how to put it back. The numbers in brackets at
the end of each entry, such as *(check 57, 84)*, are the check numbers in
[`plans/11-hand-checks.md`](plans/11-hand-checks.md), which has the longer
version of each test: an automated test you can run first to see what
"right" looks like, and where in the code a failure points. If something
is wrong, write down the check number and what you saw.

Terms a newcomer may not know (APC40, preset, route, the glass…) are
explained in the [glossary](#glossary) at the end.

## Before you start

1. **Back up the home folder before anything else:**
   `cp -R ~/Hyperspace ~/Hyperspace-backup-<today's date>`, then make a
   second copy to experiment on: `cp -R ~/Hyperspace ~/Hyperspace-try`.
2. **Launch the app:** on branch `finish-line` (`git checkout finish-line`,
   `git pull`), run `cd hyperspace-python && uv sync && uv run hyperspace`.
   Two windows open: the picture (the *render window*) and the *control
   window*. **Esc** quits.
3. **Use the copy instead of the real home folder:** in the terminal,
   `export HYPERSPACE_HOME=~/Hyperspace-try` before launching. The app
   then reads and writes only the copy, its config file included. Open a
   new terminal to go back to the real home folder.
4. **The config file** is `config.toml` in the home folder
   (`~/Hyperspace/config.toml`, or `~/Hyperspace-try/config.toml` on the
   copy). Every setting is explained in
   `hyperspace-python/hyperspace/config.py`. Edit it with the app closed,
   then launch again.
5. **The control window's pages** are the column of names down its left
   edge — OUTPUT, VIEW, FACES, BITMAP, CAMERA, LOOKBACK, FX, AUDIO,
   ANALYZER, ROUTING, LFO, HANDS, PRESETS, SYSTEM. Click a name to open
   that page. Messages appear in the *footer*, the line along the bottom.

Below, `<home>` means whichever home folder the app is using. ⌘ is the
Command key, ⇧ is Shift; "right-click" is a two-finger click on the
trackpad. F1–F8 are the function keys (hold **fn** if your Mac's top row
changes brightness or volume instead).

> **Known risks while testing**
>
> 1. **For a long session with no APC40, switch MIDI off.** When the
>    APC40 is not plugged in, the app keeps looking for it: every two
>    seconds for the first ten seconds, then every ten seconds (it was
>    every two seconds all night until a fix on 2026-10-05). In rare
>    cases macOS can kill the app while it looks (seen once during
>    automated testing, never yet in the app). The risk is now smaller,
>    not gone; putting `enabled = false` under `[midi]` in the config
>    file removes it (put it back before testing the desk). A desk
>    plugged in while the app runs is found within ten seconds.
> 2. **Plug every screen in before launching.** A screen plugged in after
>    the app starts is not used until you restart it (⌘R or quit and
>    launch again).

### The order to run things

1. Back up and make the copy (above).
2. **On the copy**, the first launch of this build: L1, then L2 and L3.
   Do not launch on the real home folder before this: the first launch
   rewrites a file there (with a backup).
3. The rest of Part 1, in any order: L39–L42 on the copy, the others on
   the real home folder. Leave L43 (git, on the copy) until after step 4:
   it is the last test done on the copy.
4. Part 2 (a), the APC40. Its entries marked "on the copy" run with
   `HYPERSPACE_HOME` set to the copy. A1 before A4.
5. Back on the copy: L43.
6. Part 2 (b), the hand camera: **B1 (calibration) first**, with nobody
   else in the camera's view. Leave the APC40 plugged in for the entries
   that need both.
7. Part 2 (c), the projector.
8. Part 2 (d), the glass and the projector: D1 first (it sets up two
   outputs in the config file), D12 and D13 last.
9. Part 2 (e), a mouse — any time.

## Summary

| Entry | What it tests | Part | Needs | Checks |
|---|---|---|---|---|
| L1 | First launch updates the control-mapping file, with a backup | 1 | laptop, the copy | 57, 84, 81 |
| L2 | Presets saved before load without a fuss | 1 | laptop, the copy | 83, 57 |
| L3 | The page holds twenty-four presets | 1 | laptop, the copy | 81 |
| L4 | The app starts, runs and quits; the keys | 1 | laptop | 1 |
| L5 | A config mistake is shown, not a crash | 1 | laptop | 2 |
| L6 | Sound from the microphone | 1 | laptop, music or clapping | 3 |
| L7 | Every page fits and reads from a distance | 1 | laptop | 4 |
| L8 | The stall log | 1 | laptop | 44 |
| L9 | A backup before an old mapping file is converted | 1 | laptop | 30 |
| L10 | The older home-folder conversion lost nothing | 1 | laptop | 33 |
| L11 | Windows reopen where you left them | 1 | laptop | 61 |
| L12 | The effects by eye | 1 | laptop | 5 |
| L13 | Clicking an effect's name opens it without switching it | 1 | laptop | 59 |
| L14 | An effect that is not running says why | 1 | laptop | 60 |
| L15 | An effect aimed at the faces | 1 | laptop | 91 |
| L16 | Nothing aimed at the faces changes nothing | 1 | laptop | 92 |
| L17 | The trail carries the faces' effects | 1 | laptop | 93 |
| L18 | Drag an effect to reorder (trackpad) | 1 | laptop | 94 |
| L19 | No see-through picture | 1 | laptop | 6 |
| L20 | Tap tempo and the LFO's downbeat | 1 | laptop, music or metronome | 7 |
| L21 | Code edits take effect while running | 1 | laptop | 8 |
| L22 | Tuning the dream, and the rare stall | 1 | laptop, music | 9 |
| L23 | The LOOKBACK page reads | 1 | laptop | 95 |
| L24 | Dream speed | 1 | laptop | 96 |
| L25 | The dream's layer cannot be performed | 1 | laptop | 63 |
| L26 | WAKE without the dream still draws | 1 | laptop | 46 |
| L27 | Instances down to zero | 1 | laptop | 62 |
| L28 | Instance layouts | 1 | laptop | 97 |
| L29 | Loading a preset resets everything it should | 1 | laptop | 38 |
| L30 | What the show starts on | 1 | laptop | 40 |
| L31 | Undo a slider drag | 1 | laptop | 48 |
| L32 | Undo a preset load | 1 | laptop | 50 |
| L33 | The Home key | 1 | laptop | 54 |
| L34 | The key legend is off at launch | 1 | laptop | 58 |
| L35 | One Unbind | 1 | laptop | 64 |
| L36 | The right-click menu from labels and meters | 1 | laptop | 68 |
| L37 | The big desk drawing | 1 | laptop | 69 |
| L38 | The ROUTING filter | 1 | laptop | 71 |
| L39 | Hide presets from the list | 1 | laptop, the copy | 86 |
| L40 | Rename a preset | 1 | laptop, the copy | 87 |
| L41 | The trash | 1 | laptop, the copy | 53, 88 |
| L42 | The unsaved dot from a step back | 1 | laptop, the copy | 89 |
| L43 | The home folder in git | 1 | laptop, the copy, last | 90 |
| L44 | One output is as it was | 1 | laptop (recorded hands) | 99 |
| L45 | The HANDS page explains a bad setting | 1 | laptop | 100 |
| L46 | Sending to FL Studio | 1 | laptop, FL Studio | 27 |
| L47 | Receiving from FL Studio | 1 | laptop, FL Studio | 28 |
| A1 | Knobs follow the app when it changes a value | 2a | APC40 | 31 |
| A2 | The desk wakes up; knobs, rings, faders | 2a | APC40 | 10 |
| A3 | SHIFT latches and lights | 2a | APC40 | 34 |
| A4 | Switching layer: knobs jump, faders wait | 2a | APC40 | 35 |
| A5 | Rings show the setting, lights show the state | 2a | APC40, music | 11 |
| A6 | Tempo buttons and the pad grid | 2a | APC40, music or metronome | 12 |
| A7 | The on-screen desk matches the real one | 2a | APC40 | 45, 69, 58 |
| A8 | Device knobs on each preset | 2a | APC40, the copy | 36, 85 |
| A9 | One knob, two directions | 2a | APC40 | 39 |
| A10 | Undo a knob turn, and a load from the desk | 2a | APC40 | 49, 50 |
| A11 | Undo a Learn and an Unbind | 2a | APC40 | 51 |
| A12 | OVERDUB is Home | 2a | APC40 | 54 |
| A13 | The crossfader is the master dimmer | 2a | APC40 | 55 |
| A14 | Hold the clip-stop row to save a new preset | 2a | APC40, the copy | 56, 83 |
| A15 | Pad rows 4 and 5 are presets | 2a | APC40, the copy | 82 |
| A16 | Click a control, then a setting | 2a | APC40 | 70 |
| A17 | Knob smoothing | 2a | APC40 | 78 |
| A18 | The instances knob at the bottom | 2a | APC40 | 62 |
| B1 | Calibrate, and the box it draws | 2b | hand camera | 72, 15 |
| B2 | The probe sees both hands | 2b | hand camera | 13 |
| B3 | The HANDS page and which way is up | 2b | hand camera | 14, 4 |
| B4 | A hand outside the box | 2b | hand camera | 73 |
| B5 | The default feel | 2b | hand camera | 16 |
| B6 | Tilt and turn without moving height | 2b | hand camera | 17 |
| B7 | The thumb-to-ring-finger pinch | 2b | hand camera | 18 |
| B8 | Learn onto a setting a hand already drives | 2b | hand camera | 19 |
| B9 | Pinch zoom while scrolling | 2b | hand camera, scroll | 20 |
| B10 | The right hand deepens the breathing | 2b | hand camera | 21 |
| B11 | A second pinch at another height | 2b | hand camera | 23 |
| B12 | A hand leaving, and "hold" | 2b | hand camera | 24 |
| B13 | A hand moving makes no undo step | 2b | hand camera | 52 |
| B14 | A hand Learn listens to one hand | 2b | hand camera | 66 |
| B15 | A tilt learned is gentle | 2b | hand camera | 75 |
| B16 | Height is still a fader where it should be | 2b | hand camera | 76 |
| B17 | A Learn moves the axis | 2b | hand camera | 77 |
| B18 | Two hands steer the camera | 2b | hand camera | 80 |
| B19 | Hand routes follow the axis by name | 2b | hand camera | 42 |
| B20 | The "screentop" warning | 2b | hand camera | 100 |
| B21 | Zero instances with hands in | 2b | hand camera | 62 |
| B22 | The hands' own port in FL Studio | 2b | hand camera, FL Studio | 29 |
| B23 | A knob on a setting a hand drives | 2b | hand camera, APC40 | 22 |
| B24 | A hand on the desk does not perform; reset | 2b | hand camera, APC40 | 74 |
| B25 | A desk Learn ignores the hands | 2b | hand camera, APC40 | 65 |
| B26 | A knob bumped during a hand Learn | 2b | hand camera, APC40 | 67 |
| B27 | A smoothed knob with everything else | 2b | hand camera, APC40 | 79 |
| B28 | A hand cannot learn a ghost-hand setting | 2b | hand camera, APC40 | 110 |
| B29 | Hand-to-picture delay | 2b | hand camera, 120 fps phone camera | 25 |
| C1 | Choosing the screen; the see-through mode locked | 2c | projector | 26 |
| C2 | A black ground, never see-through | 2c | projector | 43 |
| C3 | Windows reopen on the right screen | 2c | projector | 61 |
| C4 | Dream speed on the rig | 2c | projector | 96 |
| D1 | Two outputs open where the config says | 2d | glass, projector | 101 |
| D2 | The eight output states | 2d | glass, projector, camera | 102 |
| D3 | Hands over or through the effects | 2d | glass, projector, camera | 103, 47 |
| D4 | The dims | 2d | glass, projector, APC40 | 104, 55, 43 |
| D5 | Black is never a mystery | 2d | glass, projector | 105 |
| D6 | An output of another shape | 2d | glass, projector, camera | 106 |
| D7 | Frame rate and tearing with two screens | 2d | glass, projector, camera | 107 |
| D8 | The ghost hands follow the real ones | 2d | glass, camera | 108, 47 |
| D9 | The five hand styles from the audience | 2d | glass, camera | 109 |
| D10 | Effects on the faces, on the rig | 2d | glass, projector | 98 |
| D11 | The party presets on the rig | 2d | glass, projector, camera, APC40 | 41, 32 |
| D12 | A screen not plugged in at launch | 2d | glass, projector | 111 |
| D13 | Unplug the projector mid-run | 2d | glass, projector | 112 |
| E1 | Drag an effect with a mouse | 2e | mouse | 94 |

Covered by other entries: check 32 is part of D11; check 37 is replaced
by B25; check 47 is finished by D8 (with D3, D9 and B28).

---

# Part 1 — the laptop alone

Keyboard, trackpad, the laptop's screen and its microphone. Nothing
plugged in. (See the known risks box about the APC40 being unplugged.)

## On the copy: the first launch of this build

Run L1–L3 in a terminal where `HYPERSPACE_HOME` points at the copy
(Before you start, step 3).

#### L1. The first launch updates the control-mapping file, with a backup

**Needs:** the copy, never launched on this build.

**Do:**
1. `ls -la $HYPERSPACE_HOME $HYPERSPACE_HOME/projects` and keep what it
   prints.
2. Launch, saving what the app prints:
   `uv run hyperspace 2>&1 | tee ~/first-launch.txt`.
3. PRESETS page → **show ▾** → open your own show; press F1 to F8 in
   turn; quit.
4. Read `~/first-launch.txt`, and run the `ls -la` again.
5. Launch again and quit.

**Right if:**
- The first launch printed one backup line, "backup: bindings.json kept
  as bindings.json.bak-v3" (or a name with a date if that name was
  taken), and one line per change: the crossfader moved to the master
  dimmer (`remapped cc:0:15: overlay.bg → output.dim`), OVERDUB added as
  Home (`added note:0:64 → preset.home`), eight `added note:…:52 →
  preset.save_new` lines (the clip-stop buttons), `added key:…` lines for
  ⌘Z, ⌘⇧Z, Ctrl+Z, Ctrl+⇧Z and Home, and sixteen `added note:…:56` /
  `…:57 → preset.select` lines (pad rows 4 and 5; "remapped …
  view.shape → preset.select" where your file still had the old shape
  pads), then "updated … (N rows changed)". Lines for changes an earlier launch already made do not
  appear.
- The SYSTEM page shows the same as one line: "bindings.json updated (N
  rows changed), the old file kept as bindings.json.bak-v3 — each change
  is on stderr".
- `grep -c preset.select $HYPERSPACE_HOME/bindings.json` prints 24.
- The ROUTING page's session section lists X → `output.dim`, B11 →
  `preset.home` and G6·1–G6·8 → `preset.save_new hold`, under
  "invariant · both layers".
- Your show files have the same size and time as before.
- A crossfader, OVERDUB, clip-stop or pad mapping you had changed by hand
  is left as you had it.
- The second launch prints nothing about the mapping file, the SYSTEM
  page has no such line, and no file's time moves.

**Wrong if:** the file changed with no backup; one of your own mappings
was replaced; the same lines appear on every launch.

**Changes:** `bindings.json` is rewritten, the old one kept beside it as
`bindings.json.bak-v3`. To put it back, copy that file over
`bindings.json`.

**Later:** the first time you launch on the real home folder, the same
lines and its own backup appear there: read them the same way. If your
mapping file was itself just made from a very old `midi_map.json`, the
OVERDUB and clip-stop lines arrive on the second launch instead, and it
says so. If you later delete the OVERDUB or a clip-stop line from
`bindings.json`, it comes back on the next launch; to switch a button
off, keep its line and add `"enabled": false`.

*(check 57, 84, 81)*

#### L2. Presets saved before load without a fuss

**Needs:** the copy; presets of your own saved on an earlier build.

**Do:** `ls -l $HYPERSPACE_HOME/presets/`. Load three of your presets
from the preset list (PRESETS page → click the preset's name). Run the
`ls -l` again.

**Right if:** no warning, no unsaved dot, and no preset file's time
moved. Exception: if one of them had a control learned onto OVERDUB, a
clip-stop button or a pad in rows 4–5, a warning names it ("dropped … —
that control is invariant …"): that mapping is gone from the live desk
and stays in the file until you save the preset; saving then moves the
old file to the trash.

**Wrong if:** a warning on every load; a file's time moving on a load.

*(check 83, 57)*

#### L3. The page holds twenty-four presets

**Needs:** the copy.

**Do:**
1. PRESETS page. Under the F1–F8 buttons are sixteen smaller buttons,
   four a row, "9" to "24", each "—" when empty (on the factory party
   show, 9 reads TRACER). Open **more** as well.
2. Right-click button 12 → **put preset here…** → pick one of yours.
3. Put another preset on button 20.

**Right if:** no scrollbar on the page, even with "more" open; button 12
reads "12" and the name; the footer says "slot 12: <name>"; the
`projects` folder now holds `<show>.hyp.json.bak-v2-bank8` (the show
file as it was — a factory show opened as shipped has none: its first
change makes your copy); no second backup after button 20.

**Known, not a fail:** with "more" open, a warning line (press an empty
far slot: "slot 13: an empty slot") pushes the page down 11 pixels. Say
whether that is a nuisance.

**Changes:** the show file now has 24 slots; the 8-slot version is kept
as `.bak-v2-bank8`.

*(check 81)*

## Starting, keys and settings

#### L4. The app starts, runs and quits; the keys

**Needs:** laptop.

**Do:**
1. `HYPERSPACE_FRAMES=3 uv run hyperspace`: it should open both windows,
   draw three frames and quit by itself.
2. `uv run hyperspace`. Then: **R**; **F1**; **⇧F1**; **T**; **⌘R**;
   **/**.

**Right if:** step 1 exits cleanly with nothing in the terminal but
one-line notes. In step 2 the *party show* opens (PRESETS page: SHOW
`party`) on its first *preset*, TUMBLE; R resets the view; F1 loads
TUMBLE; ⇧F1 saves the current look as your own TUMBLE; T does nothing
(the see-through *overlay* mode is off unless the config has `[output]`
`overlay = true`); ⌘R restarts the app without resetting the view first;
`/` shows the key legend (the *cheat sheet*), its rows including R
("reset view + camera"), F1–F8 ("load preset · ⇧ saves"), a "Cmd+Z" row
reading "undo · ⇧ redo (or Ctrl+Z)" and a "Home" row reading "home
preset (fn ←)".

**Wrong if:** an error printed, the app not quitting, or a missing row.

**Changes:** ⇧F1 writes your own copy of TUMBLE,
`<home>/presets/tumble.json`, which then takes the factory one's place,
and rewrites the show file, `<home>/projects/party.hyp.json`; remove the
preset with × in the preset list (it goes to the trash) if you do not
want it.

*(check 1)*

#### L5. A config mistake is shown, not a crash

**Needs:** laptop; a config file that still has an `[overlay]` section
(if it already says `[output]`, skip step 1).

**Do:**
1. Launch, SYSTEM page.
2. Quit; add a line `output = 3` as the very first line of the config
   file (above every `[section]` line); launch; SYSTEM page.
3. Remove that line. Move the keys under `[overlay]` to `[output]` and
   delete `[overlay]`; launch.

**Right if:** (1) one note asks for `[overlay]` to be renamed `[output]`.
(2) the SYSTEM page shows the error in the warning colour ("config:
[output] must be a table, not 3") and the app runs. (3) the note is
gone.

**Wrong if:** no note, or the app crashes on the bad line.

**Changes:** the config file; the end state (the section renamed) is the
intended one.

*(check 2)*

#### L6. Sound from the microphone

**Needs:** laptop microphone; clapping or music.

**Do:**
1. AUDIO page: open the input list.
2. Press **M**. Clap.
3. PRESETS page → show ▾ → `house`, then F1 (BIG BLUE WAVE, where sound
   drives the spin). Clap.
4. Plug in or switch on another sound input and press **rescan** beside
   the list.

**Right if:** the list shows the MacBook microphone (and BlackHole, if
installed, already chosen, shown as "● BlackHole…"); macOS asks for
microphone permission once; on the ANALYZER page the six bars' white
input columns jump on a clap and settle, and their red output columns
follow; on BIG BLUE WAVE the spin
changes with the clap; after rescan the new input is listed and your
choice is kept.

**Wrong if:** no permission prompt and flat meters; meters stuck at the
top with a blinking warning in a quiet room; rescan losing the choice.

*(check 3)*

#### L7. Every page fits and reads from a distance

**Needs:** laptop.

**Do:** click through all fourteen pages. Stand about two metres back.

**Right if:** every label and number is readable from there; no page
shows a scrollbar of its own (the ROUTING page's list of rows scrolls
inside its own box, which is intended). The HANDS page with the camera
running is checked in B3.

**Wrong if:** a page scrollbar; a value you cannot read.

*(check 4)*

#### L8. The stall log

**Needs:** laptop; a second terminal.

**Do:** launch. In the second terminal:
`kill -USR1 $(pgrep -f "bin/hyperspace")`.

**Right if:** `<home>/stall.log` gains a block of text (the program's
current state, ending in `app.py` `main` for the main thread); the app
keeps running; the SYSTEM page shows "stall log: …/stall.log (1 raw
dump)".

**Wrong if:** no file, an empty one, or the app quits.

**From now on:** if the picture ever freezes, or a red banner at the
bottom of the control window mentions a render error or a render stall,
keep `stall.log`.

*(check 44)*

#### L9. A backup before an old mapping file is converted

**Needs:** laptop; the old file `~/Hyperspace/bindings.json.bak-plan09`
(made by hand some weeks ago). If you do not have it, skip this.

**Do:**
1. `mkdir -p /tmp/h && cp ~/Hyperspace/bindings.json.bak-plan09 /tmp/h/bindings.json`
2. `HYPERSPACE_HOME=/tmp/h HYPERSPACE_FRAMES=3 uv run hyperspace`
3. Run step 2 again.

**Right if:** the first run prints what it sorted and changed,
`backup: bindings.json kept as bindings.json.bak-v1`, and three
`migrate:` lines; `/tmp/h/` then holds a new `bindings.json`, the old
one as `bindings.json.bak-v1`, `presets/migrated.json` (a preset called
MIGRATED holding the old file's routes, knobs and *macros*) and
`projects/mine.hyp.json` (a show that starts on it). The second run makes
no new backup and rewrites nothing. Your real home folder's hand-made
backups are untouched.

**Wrong if:** no `.bak-v1`; an existing backup overwritten.

**Changes:** only `/tmp/h`; delete it afterwards.

*(check 30)*

#### L10. The older home-folder conversion lost nothing

**Needs:** laptop; the backup from "Before you start".

**Context:** a build from late September converted the home folder to
its current layout the first time it ran. Your home folder has probably
been converted already; then the app prints no `migrate:` lines and you
can only check the result.

**Do:** launch and read what it prints. Compare `ls -la ~/Hyperspace`
with the backup.

**Right if** (if it converts now): one `migrate:` line per rewritten
file naming its backup (`projects/<name>.hyp.json.bak-v1`,
`bindings.json.bak-v2`) and one per preset written. **Right if** (either
way): `<home>/presets/` holds a preset for each filled F-key of each of
your shows; opening a show brings back the look it had; `bindings.json`
holds only your keys, pad and MIDI rows; your hand-learned rows and
knobs are inside the presets (ROUTING page: the routes and the DESK
section); the old `<home>/bindings/` folder is as it was, with a
`NOT-READ.txt` in it; every backup file you made by hand is untouched. A
second launch prints nothing and changes no file.

**Wrong if:** a slot missing; a learned row gone; a backup overwritten.

*(check 33)*

#### L11. Windows reopen where you left them (laptop part)

**Needs:** laptop. The projector part is C3.

**Do:** drag and resize both windows; Esc; launch again. Then ⌘R with a
window moved. Then delete `<home>/windows.json` and launch.

**Right if:** both windows come back where and as large as they were;
`<home>/windows.json` has one `control` entry and one `render` entry;
after ⌘R the moved window stays where you put it; with the file deleted,
the old default placement returns (render window top-left, control
window flush right, both full size — on a small screen they may overlap).

**Wrong if:** a window off every screen or not where it was; no file
after Esc. If a window ever opens out of reach, delete `windows.json`.

*(check 61)*

## The effects

#### L12. The effects by eye

**Needs:** laptop.

**Do:**
1. FX page: from its preset strip load `acid`, then `noita-tripping`,
   then `noita-heavily-tripping`. Untick and tick **Effects** at the top.
   Pull **FX mix** to 0.
2. While the app runs, edit any file in `hyperspace-python/hyperspace/shaders/fx/`
   (change a number) and save; then add a deliberate typo and save; then
   undo your edit (`git checkout` the file).
3. Party show: press F6 (ACID), F7 (MANDALA), F8 (NOITA). Then switch on
   one more effect by hand and press the same F-key.

**Right if:** Effects off is the plain picture; each preset is clearly
its own look; FX mix at 0 is the same as off; a saved edit changes the
picture within a second; the typo keeps the last good picture and shows
the error on the page. F6 lights exactly acid, wobble, deconverge and hue
cycle; F7 plasma, kaleidoscope, fractals and glimmer; F8 trip warp, trip
colour, fractals and double vision; pressing the F-key again switches off
the extra one. A one-line note on the page says a preset load resets the
stack.

**Wrong if:** two presets looking alike; a typo blanking the picture (a
broken shared file falls back to the shipped one and says so on the
LOOKBACK page); a chip left dark or a stray one lit.

**Changes:** your shader edit — put it back with `git checkout`.

*(check 5)*

#### L13. Clicking an effect's name opens it without switching it

**Needs:** laptop.

**Do:**
1. F5 (TRIP), FX page. The effect *chips* are three to a row, each with a
   dot (on) or ring (off) at its left end. Click the **name** of an
   effect that is off.
2. Click the ring at the left end of that chip. Hover the dot.
3. Open Kaleidoscope and drag its **order** slider end to end.
4. Press F6, then F5.

**Right if:** (1) its settings strip opens, the chip gets a white
outline, and it stays off (no red, the picture unchanged). (2) it
switches on: the chip goes red, the ring becomes a filled dot, the open
strip does not change; the hover says "on — click to switch off". (3)
the strip stays Kaleidoscope's while its chip moves along the rows. (4)
the same effect is still open. Only the two longest names are cut short.

**Wrong if:** clicking a name switches the effect; the strip jumps to
another effect.

*(check 59)*

#### L14. An effect that is not running says why

**Needs:** laptop.

**Do:** FX page, open an effect that is off. Then: click **turn on**;
untick **Effects** at the top; tick it back and pull **FX mix** to 0;
put it back and pull the effect's own mix to 0. Also right-click one of
its dimmed sliders.

**Right if:** the strip reads "off — nothing below shows until it is on"
with a **turn on** chip; the sliders under it are dimmed but still move;
the right-click menu opens at full brightness; **turn on** switches it on
and the line and dimming go. With Effects unticked: "the whole stack is
bypassed" with **effects on**. FX mix at 0: "FX mix is at 0". Its own mix
at 0: "its mix is at 0", and that slider is not dimmed. No page
scrolls. Say whether the dimming is too faint or too strong from a step
back.

**Wrong if:** no line, the wrong reason, or the dimmed sliders dead.

*(check 60)*

#### L15. An effect aimed at the faces

**Needs:** laptop; any picture file.

**Do:**
1. F2 (FACES). BITMAP page: load a picture.
2. FX page: click Kaleidoscope's name to open its strip and switch it
   on; at the right end of the strip's title line, after **ONTO**, click
   **faces** (lit: **frame**).
3. Click **screen**, then **per face**.
4. Unload the picture, set the FACES page's pattern to FLAT, aim Plasma
   at the faces too.
5. VIEW page: switch Faces off. Then set Instances to 0.
6. ⌘Z after the **faces** click and after a screen / per face click.

**Right if:** (2) **faces** lights; the outline shape is no longer folded
but the picture inside each face is; the strip reads "faint on the
translucent faces — Brightness lifts them"; the status at the top of the FX page becomes two
rows, `frame …` and `faces Kaleidoscope`, the second ending in two chips
**per face** (lit) and **screen**; Kaleidoscope's chip shows a filled
diamond (an outlined one when off) and its hover says "on the faces".
(3) **screen**: the faces become windows onto one still, upright picture
while the shape turns across it; **per face**: the picture turns with
the shape again. (4) the faces glow and the space between them stays
black. (5) the faces row reads `faces (Faces is off)` in the warning
colour and the strip reads "aimed at the faces, and Faces is off" with a
**faces on** chip; at 0 instances: `faces (no copies to show them)`. (6)
each is one undo step.

**Judge:** whether the diamond can be told from the dot from a step
back. Per face, a subtle effect (Double vision, Deconverge, Trip colour,
Wobble) may be hard to see; strong ones (Hue cycle, Kaleidoscope) should
show. Every face showing the same picture is expected; say if it matters.

**Wrong if:** nothing changes in the faces; the whole frame still folds;
the picture upside down or mirrored.

*(check 91)*

#### L16. Nothing aimed at the faces changes nothing

**Needs:** laptop.

**Do:** press F1 to F8 in turn. Then F5 (TRIP): aim its four effects
(Plasma, Kaleidoscope, Zoom burst, Hue cycle) at the faces; watch the
frame rate in the footer. Press F5 again.

**Right if:** every preset looks as it did before this build; the FX
status is one line with no `frame` prefix; the frame rate does not
visibly drop with the four on the faces; F5 again puts them back on the
frame.

**Wrong if:** any preset looks different; a visible frame-rate drop (say
on which machine).

*(check 92)*

#### L17. The trail carries the faces' effects

**Needs:** laptop; the dream running (LOOKBACK page's status names a
device).

**Do:** F4 (WAKE). Aim Hue cycle at the faces and switch it on.

**Right if:** the trail behind the shape has the faces' cycling colours
and the dream grows out of them; an effect left on `frame` still never
appears in the trail.

**Wrong if:** the trail stays in the old colours.

*(check 93)*

#### L18. Drag an effect to reorder (trackpad)

**Needs:** laptop. The same with a mouse is E1.

**Do:**
1. F5 (TRIP), FX page. Drag the Hue cycle chip **by its name** onto the
   Plasma chip and let go. ⌘Z.
2. Drag a chip onto the right half of the last chip's name.
3. Click a name; press on a name, slip a little and let go on it; click a
   dot. Use the order slider in the strip.

**Right if:** while dragging, the name follows the pointer and a white
bar marks the left edge of the chip underneath; after the drop Hue cycle
is first, the status line starts with it, the picture changes, and its
strip is open; ⌘Z puts the order back in one press ("undid reorder
effects"). (2) the bar shows on that chip's right edge and the effect
lands last. (3) a click or a slipped press only opens; a dot only
switches; the slider still reorders. A drag never changes an effect's
target or switch.

**Known, not a fail:** a 2-pixel gap between a chip's dot and its name
takes no drop; the floating name can be cut at the window's edge.

**Wrong if:** a click starts a drag, or a drag cannot be started (use the
order slider and say so); the wrong effect moved; ⌘Z needed twice.

*(check 94)*

#### L19. No see-through picture

**Needs:** laptop; a white web page full screen behind the render
window.

**Do:**
1. Press **F** (faces on). FACES page: pick a pattern. VIEW page: tick
   and untick **Cut-through**. Do this in a window, then with the OUTPUT
   page's **Fullscreen** on.
2. Quit, add `overlay = true` under `[output]` in the config, launch.
   Press **T**, then tick and untick Cut-through again. Press **T** again.

**Right if:** (1) in a window and fullscreen the picture is solid with
Cut-through on and off: black ground, faces lit, nothing of the desktop
anywhere. (2) after T the window floats over the desktop: with
Cut-through on, the desktop shows through where faces overlap; off, the
faces hide it and only the empty ground is see-through. T again returns
the window. Cut-through only makes a difference in this floating mode.

**Wrong if:** the desktop shows through the faces in window or
fullscreen; no difference at all in the floating mode.

**Changes:** remove the `overlay = true` line afterwards.

*(check 6)*

## Tempo, the dream and the look-back

#### L20. Tap tempo and the LFO's downbeat

**Needs:** laptop; music (press **K** to play a file chosen on the AUDIO
page) or a metronome app at 140 beats a minute.

**Do:**
1. PRESETS page: load `lfo-breathe` from the preset list. LFO page.
2. Tap **B** four times on the beat; press **⇧B** on the "one".
3. Tap B again a few times. Click the page's trigger chip.

**Right if:** the BPM reads 140 ± 1; the beat light blinks on the beat;
*LFO* 1's little graph shows one smooth wave per bar and the brightness
swells with it, starting from your ⇧B; tapping B again changes the BPM
reading but never makes the swell jump (not even before the first ⇧B);
the trigger chip does the same as ⇧B.

**Wrong if:** the swell jumps on a tap; the BPM more than 1 off; no
swell at all (look at the ROUTING page: is the LFO's row onto Brightness
switched on?).

*(check 7)*

#### L21. Code edits take effect while running

**Needs:** laptop.

**Do:** with the app running, edit `hyperspace-python/hyperspace/lfo.py`:
make the sine wave twice as fast (in `wave()`, change
`return math.sin(2 * math.pi * x)` to `4 * math.pi * x`), save. Then undo the edit. Then save
`hyperspace/params.py` without changing it (`touch` it), and press
**F**, **P**, **L**.

**Right if:** LFO 1's graph doubles its speed within a second; the
SYSTEM page shows "hot reload: watching"; after the touch, F, P and L
still switch faces, points and lines, and SYSTEM shows no error or
"restart" line.

**Wrong if:** no change on save; a switch that stops working.

**Changes:** put `lfo.py` back (`git checkout hyperspace/lfo.py`).

*(check 8)*

#### L22. Tuning the dream, and the rare stall

**Needs:** laptop; music; `[dream] enabled = true` in the config (the
usual setting).

**Do:**
1. Launch normally. LOOKBACK page: the DREAM section's status names a
   device (not "no worker").
2. From the page's preset strip load `default`, then `tracer-only`. Turn
   on the page's **Look-back** switch. Play music.
3. Try each of the six layer chips, **passes**, **strength**, **speed**
   and the colour settings (hue, saturation, tint, tint from). Save two
   or three looks you like as presets in `<home>/dream/` — candidates to
   ship.
4. Watch the frame rate in the footer for ten minutes.
5. Load TRACER from the PRESETS list, then press F4 (WAKE). Hover
   **fade time**, **time apart** and **count** in the ECHOES section.
6. If the screen runs at 120 Hz, switch it to 60 Hz (System Settings →
   Displays → refresh rate) and compare TRACER's trail.

**Right if:** the dream is in its own colours and re-tinted by the
colour settings; the *echoes* are not; **shape hides** keeps the dream
off the shape; the rare stall (about one frame in 300) is one dropped
frame, not more. Each hover says what it does in seconds; on TRACER the
ECHOES note reads "24 × 67 MS · THE TRAIL REACHES 1.60 S", and its trail
is a clear fan of copies behind the turning shape; WAKE's trail reaches
past the faces with the dream painted into it; the trail is the same
length at 60 and 120 Hz.

**Wrong if:** a stall longer than a frame, or every few seconds; no
dream; a trail half as long at 120 Hz; a saved look-back preset of yours
looking different (the old file is kept as `<file>.bak-v2-frames`).

**Judge:** the dream's look (see the last section).

*(check 9)*

#### L23. The LOOKBACK page reads

**Needs:** laptop; the dream running.

**Do:** F4 (WAKE), LOOKBACK page. Read every label aloud. Click each of
the six layer chips in turn and wait for the status line to say it has
loaded. Right-click a chip.

**Right if:** three sections — **ECHOES** (brightness, fade time, count,
time apart, then thumbnails; the note reads "24 × 50 MS · THE TRAIL
REACHES 1.20 S"; time apart `50 ms`, fade time `0.60 s`), **DREAM**
(status, at most three lines; six layer chips; brightness, speed,
strength, passes, linger, jitter, scales, hue, saturation, tint, tint
from, tint hue, tint sat, and the tint swatch) and **BOTH** (darken,
contrast, shape hides, detail). The page does not scroll. Each label
says what it does without the hover. On the ROUTING page the longer
names read "Echo time apart", "Dream brightness", "Shape hides wake".
Right-click on a chip: "not modulatable".

**Judge:** the layer chips are called grain, swirl, blot, 3b, 4c and 4e.
These names were guessed: say whether the first three fit and what the
last three should be called (about five letters fit).

**Wrong if:** the page scrolls; a chip does not load its layer; a label
is cut.

*(check 95)*

#### L24. Dream speed

**Needs:** laptop; the dream running. (Comparing on the rig is C4.)

**Do:** F4 (WAKE), DREAM section, **speed**. Drag it end to end while
the shape moves.

**Right if:** right is faster: at the fast end the dream keeps up with
the shape, lets go almost at once and is shallower; at the slow end it
trails well behind and grows deeper. The reading is in dream frames:
"≈23 frames" at the slow end, "≈14 frames" at the default, one decimal
under ten ("1.9 frames" at the fast end); slower than about 17 frames
the status says "step clamped".

**Judge:** whether this is the "speed" you meant, and whether one knob
is enough (faster is also shallower, by design).

*(check 96)*

#### L25. The dream's layer cannot be performed

**Needs:** laptop.

**Do:** LOOKBACK page, right-click a layer chip. ROUTING page: add a
route and open its target list. Change the layer with a chip.

**Right if:** the menu says "not modulatable" where other controls offer
"Route a lane here…"; "Dream layer" is not in the target list; the
chips, a preset and a learned knob still change it. If a preset of yours
had a route onto the layer: load it — the route is dropped and the footer
says "preset <NAME>: dropped <source> → dream.layer: not modulatable";
the file is not rewritten.

**Wrong if:** a route onto the layer is offered.

*(check 63)*

#### L26. WAKE without the dream still draws

**Needs:** laptop.

**Do:** set `[dream]` `enabled = false` in the config, launch. Party
show, F4 (WAKE). Leave it a minute; press F1–F5 and back to F4.

**Right if:** the picture keeps moving the whole time — the shape turns,
the echoes trail it; a red banner says "WAKE turns the dream on, but
there is no dream worker (…)" until you click **dismiss**; `stall.log`
has that warning and no "stranded target" entry.

**Wrong if:** the picture freezes while the control window carries on.

**Changes:** put `[dream] enabled = true` back.

*(check 46)*

## The shape, the copies and presets

#### L27. Instances down to zero

**Needs:** laptop. (The APC40 and hand parts are A18 and B21.)

**Do:**
1. F1 (TUMBLE), VIEW page: drag **Instances** to the left end. ⌘Z. Set
   it to 1 by hand.
2. F4 (WAKE): take Instances to 0. F5 (TRIP) with Plasma's level up:
   Instances 0.

**Right if:** it reads "0 · nothing drawn" and the picture is black; ⌘Z
brings the count back; at 1 the shape is there. On WAKE the trail fades
out over black rather than cutting off. On TRIP, effects that make their
own picture (Plasma) still show.

**Know:** a route of your own that pushes Instances both ways now blanks
the picture half the time.

**Wrong if:** one copy still drawn at 0; an error or frozen picture.

*(check 62)*

#### L28. Instance layouts

**Needs:** laptop.

**Do:** F3 (FIELD), VIEW page. Under Instances: set **layout** to HEX with
7, then 19 copies, raising the count slowly; RING with 12, then
**motion** ORBIT and RIPPLE; in each layout take the count to 1 and 0;
⌘Z after a layout change. Then HEX + ORBIT with **amp** about 0.35.
Right-click the layout list and a rate cell. Then the house show's F1
and look at a rate cell.

**Right if:** FIELD looks as before; the page does not scroll; one row
under Instances holds layout, motion, and (unless motion is STILL) amp
and rate; the six rotation rates are three rows of two labelled "XY"
etc. HEX 7 is one in the middle and six round it, 19 two rings, and
copies already there do not move as the count rises; RING 12 is one
circle; ORBIT sends a wave round it, RIPPLE makes it breathe; 1 is one
copy in the centre and 0 nothing, in every layout; ⌘Z puts the layout
back; each right-click opens its own menu. On the house show a rate
reads `base → effective` in full. ROUTING and Learn say "Field motion",
"Field amp", "Field rate".

**Judge:** on HEX + ORBIT neighbours overlap — a look or a fault?

**Wrong if:** the grid different from before; copies jumping in HEX.

*(check 97)*

#### L29. Loading a preset resets everything it should

**Needs:** laptop.

**Do:** party show, F5 (TRIP). Tap **B** eight times at about 100 a
minute. F1 (TUMBLE). Then F6 (ACID) → F1, and F8 (NOITA) → F4 (WAKE).

**Right if:** after F1 every effect is off (FX page), the look-back is
back to its default, the ROUTING page shows TUMBLE's rows and none for
effects, the BPM still reads about 100, the sound-band settings have not
changed. F6 → F1 the same; F8 → F4: every effect off and WAKE's
look-back on (24 echoes, fade 0.60 s) with the dream, no extra step.

**Wrong if:** an effect still on; the BPM reset.

*(check 38)*

#### L30. What the show starts on

**Needs:** laptop.

**Do:**
1. Launch. PRESETS page: the **STARTS ON / HOME** list → WAKE (no save needed).
2. Quit, launch.
3. **show ▾** → `house`; quit; launch.
4. Open `party` again and set its "starts on" back to TUMBLE.

**Right if:** (1) the party show opened with its name in full, "factory"
beside it, no unsaved dot, on TUMBLE. (2) it comes up on WAKE, with the
desk lit for WAKE and the status line saying so. (3) the house show
opens (the last show opened is remembered).

**Wrong if:** the wrong look or show at launch; the choice not kept.

**Changes:** picking "starts on" writes your own copy of the party show
(`<home>/projects/party.hyp.json`); step 4 puts the choice back.

*(check 40)*

#### L31. Undo a slider drag

**Needs:** laptop.

**Do:**
1. VIEW page: note Brightness, drag it in one move, let go, wait a
   second, ⌘Z (or Ctrl+Z). Then ⌘⇧Z.
2. Drag Brightness, wait, drag Speed, wait, ⌘Z twice.
3. ROUTING page: change a route's depth, ⌘Z.
4. Click in a text field (a macro's label) and press ⌘Z there.
5. Press ⌘Z until nothing is left.
6. Drag a slider, hold still with the button down for a full second,
   drag on.

**Right if:** (1) Brightness returns, nothing else moves, the footer
says "undid Brightness … → …" for about four seconds; ⌘⇧Z redoes it
("redid …"). (2) Speed returns first, then Brightness. (3) the depth
returns. (4) only the text changes. (5) the footer says "nothing to
undo" on every press. (6) this counts as **two** steps — say if it
should be one.

**Wrong if:** nothing returns; two presses needed for one drag; ⌘⇧Z
undoes instead of redoing.

*(check 48)*

#### L32. Undo a preset load

**Needs:** laptop. (Undo of a load from the desk is in A10.)

**Do:** F1 (TUMBLE). Change three things (brightness, the shape, faces
on) so the unsaved dot lights. F5 (TRIP). ⌘Z once. ⌘⇧Z. ⌘Z, then press
F5 by hand and try ⌘⇧Z. Then load a preset from the PRESETS list and ⌘Z.

**Right if:** after the first ⌘Z the look is TUMBLE with your three
changes, the PRESETS page says TUMBLE with its dot lit, F1's button is
lit, ROUTING shows TUMBLE's routes and desk, the footer says "undid load
TRIP"; ⌘⇧Z gives TRIP again, clean; after pressing F5 by hand there is
nothing to redo; a load from the list is one ⌘Z.

**Wrong if:** the look returns but the name still says TRIP; two
presses for one load; routes not back.

*(check 50)*

#### L33. The Home key (laptop part)

**Needs:** laptop. The APC40 part is A12.

**Do:** party show; the PRESETS page's STARTS ON / HOME list reads TUMBLE. F3,
then **fn+←** (Home). ⌘Z. Then set "starts on" to — (none) and press
fn+← twice. Set it back to TUMBLE.

**Right if:** fn+← loads TUMBLE; ⌘Z brings back the earlier look ("undid
home → TUMBLE"); with no "starts on", nothing loads and each press puts "home: this
show names no 'starts on' preset — pick one on the PRESETS page" in the
footer; that line goes when you set it back.

**Wrong if:** fn+← does nothing (say so: the laptop may not send Home
for fn+←, and the key can be changed).

*(check 54)*

## The control window

#### L34. The key legend is off at launch

**Needs:** laptop. (The APC40's DETAIL button is in A7.)

**Do:** launch. Press **/**, then **/** again. Look at the SYSTEM page's
**Cheat sheet** box. Quit with the legend showing and launch again.

**Right if:** no key legend at launch; the desk drawing sits in the
bottom-left corner; `/` shows the legend with the drawing above it,
already in place on the first frame (no flicker); `/` again hides it and
the drawing drops back; the SYSTEM box follows and its hover says `/`
toggles; after relaunch it is off again.

**Wrong if:** the legend at launch; the drawing missing, jumping or
floating with a gap.

*(check 58)*

#### L35. One Unbind

**Needs:** laptop, APC40 unplugged, `[midi] enabled = true`.

**Do:**
1. F1 (TUMBLE), VIEW page, right-click **Speed**. Choose **Unbind** →
   **both**. Right-click Speed again. ⌘Z.
2. Right-click **Brightness**.
3. Set `[midi] enabled = false`, launch, repeat 1–2.
4. AUDIO page, right-click **Input trim**.

**Right if:** (1) under the setting's name the menu lists "K2 (track knob
2)" and the right hand's height route (if hands are on, "R height pushes
…"), then **Learn desk**, **Learn hand** (left / right, only with hand
tracking on), one **Unbind** with a submenu "desk — K2", "route — R
height", "both", then (hand tracking on) "Gate: none", and "Route a lane
here…". After "both" the two lines and Unbind are gone, the preset's
unsaved dot is lit, and the footer said "unbound view.speed from K2
(track knob 2) and R height …"; ⌘Z brings both back ("undid unbind
view.speed"). (2) lines "K1 (track knob 1)", "B16 (▲) · step +3", "B17 (▼)
· step -3", and Unbind is a single item. (3) the same with MIDI off. (4)
"S8 (track fader 8) · invariant", dim, and no Unbind.

**Wrong if:** no desk line with MIDI off; ⌘Z bringing back only half.

**Changes:** put `[midi] enabled = true` back.

*(check 64)*

#### L36. The right-click menu from labels and meters

**Needs:** laptop, with hand tracking off for one step.

**Do:** CAMERA page: right-click the word ZOOM. VIEW page: right-click
the word BRIGHTNESS above its slider. ANALYZER page: right-click the
fourth meter, choose **Learn desk**, cancel it by clicking the footer's
line. BITMAP page: right-click the file name. HANDS page: right-click
Steadiness.

**Right if:** a label opens the same menu as its slider, at the pointer,
without moving the value; the meter opens the band-select menu without
selecting the band (a left click still selects), and while the Learn is
armed every meter is framed red; the file name offers no Learn, over a
dim "not modulatable"; with hand tracking off there is no "Learn hand"
anywhere; on HANDS settings there is "Learn desk" but never "Learn
hand".

**Known, not a fail:** some labels a page draws itself open nothing (FX
"blend", LOOKBACK's "from", "scene", "path"); on the LFO page the two
nudge chips' menu lists its items twice.

**Wrong if:** nothing opens on a label; a two-finger click not counting
as a right-click (say on which page).

*(check 68)*

#### L37. The big desk drawing (laptop part)

**Needs:** laptop. Holding the real APC40 beside it is A7.

**Do:** F5 (TRIP). Press **H** (or the `big` chip on the desk's header).
Step back two paces. Hover a control. Press `/`. Press H to bring the
panel back.

**Right if:** the panel goes and the desk drawing fills the window; every
lit control carries a name, its short code small in the corner, and dark
controls only the code; the top pad row reads TUMBLE … NOITA with TRIP
green; the track knobs read Brightness, Speed, Instances, Pattern mix,
Field amp, Field rate, Bitmap alpha, Zoom; the device knobs FX mix, Plasma
level, Kaleidoscope segments, Kaleidoscope zoom, Zoom burst amount, Zoom
burst glow, Hue cycle paint, Hue cycle spread; the clip-stop row reads
"Save as a new preset" once; names the desk keeps on every preset are
grey, the preset's white. Pad rows 4–5: a filled slot amber at half
strength with its name (on the factory party show G4·1 reads TRACER), an
empty one dark with no label. Nothing overlaps, no scrollbar. The hover
reads like "D3 · fx.kaleido.segments · Kaleidoscope segments · preset
layer", the device's own name, and what a click would do. With `/` the
desk moves beside the legend.

**Expect:** at the standard size most names are 13 px, about a dozen 11
px, and a few cut with "…". Labels beside the open panel need a window about 1200
px wide (drag the panel to the right edge after widening).

**Judge:** which names you can read from two paces.

*(check 69)*

#### L38. The ROUTING filter

**Needs:** laptop. Nobody has typed in this field yet.

**Do:**
1. F7 (MANDALA), ROUTING page. Click the field marked "filter" (left of
   `+ route`) and type `kaleido`. Try B, F, R and number keys while
   typing.
2. Clear it; type `d3`; then `r roll`. On F5 (TRIP), type `lfo 1`.
3. With `kaleido` typed, press F5.
4. With a filter set, press `+ route`. Drag a filtered route's depth.
5. Click the ×. Type a filter again and press Esc, backspace and ⌘Z
   inside the field.

**Right if:** (1) only the kaleidoscope's lines remain (two right-hand
routes, R depth and R roll, and desk lines D3 and D4); MACROS and
SESSION say "no row matches"; the count reads "n of m rows" in red; a ×
appears; typed keys do nothing else. (2) one desk line; that route;
LFO 1's route (a route from LFO 2 would also show — say if that
matters). (3) the filter stays, now over TRIP's rows. (4) the new route
may not show — the red count is the only sign (say if that is a trap); a
line you are dragging stays put until you let go. (5) every row returns;
say what Esc, backspace and ⌘Z did.

**Wrong if:** the × deletes a different row than the one shown; the page
scrolls; a typed key also fires its shortcut.

*(check 71)*

## On the copy: tidying presets

Run L39–L42 in a terminal where `HYPERSPACE_HOME` points at the copy.

#### L39. Hide presets from the list

**Needs:** the copy.

**Do:** PRESETS page → click the preset name → the list. Click × on
`legacy6`, on `hands-*` presets you do not want, and on one house mood.
Click **show hidden**. Then × one of **your own** presets that sits on a
slot, and press that slot.

**Right if:** every row has ×, your own (white) also **rename**; each
goes; the footer says "hidden legacy6 — show hidden in the list brings
it back" (or "… — F3 still loads it" for one on a slot); the list ends
"show hidden (n)"; `<home>/hidden.json` lists them; "show hidden" shows
them struck through with **unhide**; an F-key or pad naming a hidden
preset still loads it. Your own preset goes to the trash: the footer
says in the warning colour "<name> is in the trash — F6 still names it
…", its slot button turns the warning colour, and pressing it says "F6:
no preset '<name>'".

**Wrong if:** a hidden preset will not load from its slot.

**Changes:** `<home>/hidden.json`; the trashed preset is restored in L41.

*(check 86)*

#### L40. Rename a preset

**Needs:** the copy; one of your presets on a slot in two of your shows.

**Do:** in the list: **rename** → type a name → Enter. Open the other
show. Rename it to a name another preset has. Look for rename on a
factory preset. Rename the loaded preset while it has an unsaved
change. Press ⌘Z.

**Right if:** the footer says "renamed TRIP 3 → SUNRISE (2 shows
updated)" (your names); the list, slot and "starts on" show the new
name at once, in both shows; `<home>/trash/presets` and
`<home>/trash/projects` hold the old files; a taken name is refused
("… that name is taken — pick another"); factory presets have no rename;
the unsaved dot stays lit; ⌘Z does not undo a rename (rename it back by
hand).

**Wrong if:** a slot saying "no preset" after a rename.

*(check 87)*

#### L41. The trash

**Needs:** the copy.

**Do:**
1. Load a preset of yours (or make one with **as…**: "CHECK 53"). Change
   the brightness, press **save**. Press save again with no change. Then
   open the list and × it. `ls <home>/trash/presets/`.
2. The list → **trash (n) ▸**. Restore the preset from L39.
3. Save over one preset twice, then restore the older copy.
4. Click **empty trash…** once and wait 4 seconds. Click it, then
   something else. Click it twice.

**Right if:** (1) two files `check-53.<date>-<time>.json` — the look
before the save and the one deleted; no third file for the save with no
change; "more" lists no "trash" strip. (2) a second list, "trash · n
files", newest first, each with folder, name, time and **restore**,
scrolling past twelve rows; restoring says "restored <name>", it is back
in the list and its slot loads. (3) "restored as TRIP 4 — TRIP 3 is
taken" (the next free name), the newer one untouched. (4) one click
reads "delete n files for good? — click again" in the warning colour and
after 4 s goes back with nothing deleted; clicking elsewhere disarms it;
two clicks: "trash: n files deleted for good", the trash line gone,
`<home>/trash` empty.

**Know:** emptying the trash is the only action in the app that deletes
with no copy kept.

**Wrong if:** a restore replacing a preset (the backup has it); one
click emptying the trash.

*(check 53, 88)*

#### L42. The unsaved dot from a step back

**Needs:** the copy.

**Do:** load a factory preset on a slot that you have no copy of (dim in
the list). Stand at arm's length, move a slider. Press the save chip.

**Right if:** you can see it is unsaved without leaning in: the save
chip solid red, a red disc by the name, a small white disc on the slot
button; the chip reads **save copy** and there is no reset; pressing it
makes it read "save", the dot goes, the list shows the preset once,
white (yours). ROUTING's header shows the same disc. A preset of yours
reads "save".

**Known, not a fail:** under "more", a module strip's save chip overlaps
the end of its name.

*(check 89)*

#### L43. The home folder in git (run last on the copy)

**Needs:** the copy; run after A8, A14 and A15. Optional feature.

**Do:**
1. `git -C $HYPERSPACE_HOME rev-parse --show-toplevel` — it should say
   "not a git repository".
2. In the copy's config add `[library]` and under it `git = true`.
   Launch.
3. Save a preset (**as…**). Then save it after a change, rename it, × it,
   × a factory preset, put a preset on a slot.
4. `touch $HYPERSPACE_HOME/.git/index.lock`, save twice;
   `rm $HYPERSPACE_HOME/.git/index.lock`, save once more.

**Right if:** (2) SYSTEM's library line ends "· git"; no `.git` folder
yet. (3) after the first save, `git -C $HYPERSPACE_HOME log --oneline`
shows one commit "Hyperspace: the home as it was when git was switched
on" whose body names your save; `.gitignore` exists; then one commit per
action in plain words ("save preset …", "rename preset … → …", "trash
preset …", "hide preset …", "show …: bank"); `git status --short` is
empty; no weights, trash, `last_show`, `windows.json` or backup files
are tracked; no remote. (4) saves stay instant, the warning line says
"git: not committed (…); saves are not affected" once; after removing
the lock one commit holds all three saves. Emptying the trash makes no
commit.

**Wrong if:** a save that waits; a `.git` before the first save. If step
1 names a folder above the copy, git refuses by design (one note, nothing
written).

**Changes:** the copy only. Leave it off on the real home unless you want
it.

*(check 90)*

## Outputs and hands without the camera

#### L44. One output is as it was

**Needs:** laptop; the config with no `[[output.screens]]` list. Run
before any config change for Part 2 (d). Without the camera, use
recorded fake hands: `uv run python tools/hands_tape.py synth
/tmp/hands.json`, then in the config under `[hands]` set `enabled =
true` and `tape = "/tmp/hands.json"`.

**Do:** launch. OUTPUT page. HANDS page: tick **Ghost hands**; press F5
(TRIP).

**Right if:** two windows as before, the render window where it was; the
OUTPUT page shows under **Master dim** one block "1" with **scene** and
**hands** ticked and **through effects** unticked, no dim of its own,
and a "shows: scene" line ("shows: scene + hands over the effects" with
a ghost hand showing); Screen, Fullscreen and the overlay rows follow as
before; the picture is as on earlier builds; on TRIP the ghost hands are
clean over a warped shape.

**Wrong if:** any difference in the picture; a dim row of its own.

**Changes:** remove the `tape` line afterwards.

*(check 99)*

#### L45. The HANDS page explains a bad setting

**Needs:** laptop. (The camera part is B20.)

**Do:** in the config under `[hands]` set `tape = "/tmp/no-such-tape.json"`;
launch.

**Right if:** the SYSTEM page lists a note starting `hands: `, and the
HANDS page shows it in the warning colour where it used to say "tracker
off".

**Changes:** remove the `tape` line.

*(check 100)*

## With FL Studio (no hardware)

These need FL Studio installed and the Mac's built-in virtual MIDI
cable: open Audio MIDI Setup → MIDI Studio → IAC Driver, tick "Device is
online", with one bus.

#### L46. Sending to FL Studio

**Needs:** FL Studio; the *IAC bus*; music playing in the app.

**Do:** in the config set `[bridge]` `enabled = true` and `out = "IAC"`.
Launch, SYSTEM page. In FL Studio, take IAC as input and put a Fruity
Formula Controller or Peak Controller on pitch bend, channel 1.

**Right if:** SYSTEM's bridge line names the port, `pitch`, 16 lanes and
a rising `sent` count; the FL controller moves with the lowest sound
band.

**Wrong if:** "bridge: no port" (check the IAC name); no bridge line.

**Changes:** set `[bridge] enabled = false` afterwards.

*(check 27)*

#### L47. Receiving from FL Studio

**Needs:** as L46, plus `[bridge]` `in = "IAC"` (a second IAC bus, or
FL's own MIDI out).

**Do:** ROUTING page: add a route from `ext:0` to Brightness, **push**,
depth 0.5. Send pitch bend on channel 1 from FL. Then stop FL.

**Right if:** brightness follows the pitch wheel; when FL stops,
brightness returns to its setting within a frame.

**Wrong if:** nothing moves (check the encoding on both ends, and that the
row is switched on).

**Changes:** delete the route; undo the `[bridge]` lines.

*(check 28)*

---

# Part 2 — tests that need hardware

## (a) The APC40

Plug the APC40 in by USB before launching. On the desk: the 8 × 5 grid
of *pads* is top-left, with a column of scene buttons on its right; under
it the *clip-stop row*; along the bottom nine faders (*track faders* and
the master) and, bottom right, the *crossfader*. On the right are the
eight *track knobs* (top) and the eight *device knobs* (bottom), the
*SHIFT* button, TAP TEMPO, NUDGE − / +, and the small buttons
QUANT, OVERDUB, METRONOME and DETAIL. The *on-screen desk* in the
control window's bottom-left corner names each control with a short code
(K1–K8 track knobs, D1–D8 device knobs, S1–S8 faders; see *glyph*).

#### A1. Knobs follow the app when it changes a value — run first

**Needs:** APC40.

**Do:** house show (PRESETS → show ▾ → `house`), F1 (BIG BLUE WAVE,
brightness 1.25×). Turn track knob 1 (Brightness, K1) to about a quarter.
Press F2 (EMBER ORBIT, brightness 1.5×). Turn K1 a little.

**Right if:** the knob's light ring jumps to the new brightness at once,
and the next turn carries on from there — no jump back toward a quarter.

**Wrong if:** the first turn snaps brightness to where the knob was. Then
the desk's knobs keep their own position and ignore the app; note it and
skip A4's knob half.

*(check 31)*

#### A2. The desk wakes up; knobs, rings, faders

**Needs:** APC40.

**Do:**
1. `uv run python tools/midi_probe.py`: move controls (it prints each
   message and lights the desk); Ctrl-C.
2. Launch, ANALYZER page. Turn the track knobs; turn the device knobs;
   latch SHIFT and turn them again; move a track fader; pick another band
   with the track-select buttons and turn a device knob (SHIFT latched).
3. Move a fader while the app's value is elsewhere (drag it on screen
   first).

**Right if:** at launch the desk's lights come on in their layout and
the knob rings light; track knobs move the VIEW page's settings; without
SHIFT the device knobs do the preset's job (on TUMBLE D1–D4: 4D depth,
camera yaw, camera pitch, face pattern; D5–D8 dark and dead); with SHIFT
latched they move the open band's settings; a track fader moves that
band's drive on either layer; after changing band the ring redraws and
the knob carries on from it; a fader whose value moved does nothing
until it passes that value, then follows. The on-screen desk lights each
control as you use it.

**Wrong if:** no lights (check `[midi] port`); a knob moving the wrong
setting; a fader jumping instead of catching.

*(check 10)*

#### A3. SHIFT latches and lights

**Needs:** APC40.

**Do:** press SHIFT once and let go; try the knobs; press SHIFT again.
Then hold a filled pad in row 4, press and release SHIFT while holding
it, let go of the pad.

**Right if:** SHIFT's light stays lit; the device knobs move the open
band (ANALYZER page); track knobs 1–5 move the hands' Steadiness,
Response, Catch, the selected axis's Return (HANDS page) and the BPM;
6–8 are dark and do nothing. SHIFT again: light off, the preset's
meanings back. Holding the pad: one preset load, nothing else.

**Wrong if:** lit only while held; a knob keeping its preset job under
SHIFT; a second action on release.

*(check 34)*

#### A4. Switching layer: knobs jump, faders wait

**Needs:** APC40; A1 done (if A1 was wrong, note it and skip the knob
half).

**Do:** turn K1 (Brightness) to a quarter; latch SHIFT (K1 is now
Steadiness); turn it a little; SHIFT back. Then ANALYZER page: drag SUB's
drive to the top with the trackpad, and move track fader 1 up from the
bottom.

**Right if:** each switch moves the ring at once to that layer's value,
and the next turn carries on from the ring. The fader does nothing until
it passes the new value, then follows.

**Wrong if:** a knob snapping back to where it physically was; a fader
jumping.

*(check 35)*

#### A5. Rings show the setting, lights show the state

**Needs:** APC40; music playing.

**Do:** house show, F1 (BIG BLUE WAVE). Watch the track-knob rings.
Press the scene buttons for points, lines, faces and rotate. Then on the
ROUTING page add a route from `lane:0` to Faces, **push**.

**Right if:** the rings sit at the setting and do not flicker with the
sound; the scene-button lights match the switches and flip at once when
pressed; with the route, the FACES light follows the sound while the
control window's tick box shows the setting underneath.

**Wrong if:** a ring chasing the sound.

**Changes:** delete the route.

*(check 11)*

#### A6. Tempo buttons and the pad grid

**Needs:** APC40; music or a metronome.

**Do:** load `lfo-breathe`. Tap TAP TEMPO four times on the beat and
press METRONOME on the "one". Press NUDGE + and NUDGE −. Press QUANT a
few times. Press pads in row 1; latch SHIFT and press pads in rows 2–3;
press a filled pad in rows 4–5; turn the cue knob; press STOP ALL.

**Right if:** as L20 (BPM right, a tap never jumps the swell); the
METRONOME light blinks on the beat; NUDGE moves the tempo nudge by 0.01
and the swell with it; QUANT steps to the next filled slot (empty ones are skipped); row 1 picks
presets 1–8; rows 2–3 with SHIFT pick a sound-band scene; rows 4–5 load
presets 9–24 (on both layers); the cue knob changes the shape; STOP ALL
resets every band to the selected scene, and a second press within 8 s
undoes that reset (the ANALYZER page's button says so meanwhile).

**Wrong if:** METRONOME's light steady; a button doing an older job (your
`bindings.json` kept an old line: it shows on the ROUTING page's session
section; delete it from the file by hand).

*(check 12)*

#### A7. The on-screen desk matches the real one

**Needs:** APC40.

**Do:** party show, F5 (TRIP), ROUTING page. Press H (or the APC40's
DEVICE ON/OFF) for the big drawing. Hold the APC40 beside the screen and
walk every control with the pointer. Turn D1. Latch SHIFT. Pick a row in
ROUTING's DESK section, read its code (say D4), find it on the drawing,
then on the desk, and turn it. Press DETAIL twice.

**Right if:** the drawing is the desk's face, every control in the same
place; each hover names the control the maker's way; every control lit
on screen is lit on the desk and every dark one dark, pads in the same
colours; D1's arc moves with its ring; with SHIFT, the ⇧ turns red, the
header says GLOBAL LAYER · SHIFT, D1–D8 and K1–K5 stay lit and K6–K8 go
dark — on the desk too; the row's setting moves. DETAIL shows and hides
the key legend like `/`, and its light is dark at launch. A click on a
drawn control picks it (A16); click again to let go.

**Wrong if:** a control drawn in the wrong place (note its code); lit on
one and dark on the other.

*(check 45, 69, 58)*

#### A8. Device knobs on each preset (on the copy)

**Needs:** APC40; the copy.

**Do:** F1 (TUMBLE): turn D1–D8. Then a house mood, TRIP, WAKE, ACID,
and from the list `hands-fx`, `hands-pinch`, `lfo-breathe`. Look at the
ROUTING page's DESK section on TUMBLE.

**Right if:** on TUMBLE, D1 is 4D depth, D2 camera yaw, D3 camera pitch,
D4 the face pattern (one pattern a step), each ring following; D5–D8
dark and dead, listed on ROUTING as "D5 unmapped — dark" … "D8", drawn
dark on screen; latching SHIFT lights them for the band settings and the
ROUTING header reads DESK LAYER: GLOBAL. A house mood has the same four; TRIP,
WAKE and ACID their eight; `hands-fx`: D1 FX mix, D2–D6 the Acid effect
(bend, twist, reach, breathe, speed), D7 4D depth, D8 yaw;
`hands-pinch`: D1 FX mix, D2–D3 hue cycle paint and spread, then depth,
yaw, pitch, pattern, D8 dark; `lfo-breathe`: D1 still "Breathe", then FX
mix, Plasma level, LFO 1 depth, depth, yaw, pitch, D8 dark. If TUMBLE is
white in the list (your own, saved earlier) its knobs stay as you saved
them — dark — and that is right. D4 changes nothing visible with faces
off.

**Judge:** which knobs you reached for and found dark or useless (K7,
Bitmap alpha, does nothing on a factory preset).

**Wrong if:** a lit knob moving nothing; one knob doing two things; D4
skipping patterns; an unmapped knob moving the band settings without
SHIFT.

*(check 36, 85)*

#### A9. One knob, two directions

**Needs:** APC40.

**Do:** load `lfo-breathe` (it starts with brightness 1×, speed 0.25×).
Turn device knob 1 ("Breathe") from bottom to top and back. ROUTING
page, MACROS section.

**Right if:** the picture brightens from 1× to 2× while the spin slows
from 0.25× to a crawl (about 0.06×), together, smoothly, and the LFO's
breathing of the effect mix deepens from nothing; MACROS shows knob 1
"Breathe" with three lines — two `base` lines (one runs the other way)
and one `depth` line naming the LFO's route.

**Wrong if:** both move the same way; nothing moves.

*(check 39)*

#### A10. Undo a knob turn, and a load from the desk

**Needs:** APC40.

**Do:** F5 (TRIP). Sweep D1 (FX mix) to the other end, wait, ⌘Z, turn D1
again. Latch SHIFT, move S1 a little, wait, ⌘Z. Unlatch, then press QUANT
and ⌘Z.

**Right if:** the mix and D1's ring return; the next turn carries on
from the ring; after the fader ⌘Z the drive is back, SHIFT still lit, and
S1 does nothing until it passes the value again; the QUANT load is one
⌘Z.

**Wrong if:** SHIFT dropping or every fader losing its hold; the ring
not following.

*(check 49, 50)*

#### A11. Undo a Learn and an Unbind

**Needs:** APC40.

**Do:** F5 (TRIP), ROUTING page. `ls -l <home>/presets`. Right-click
Brightness → **Learn desk**, turn D3. ⌘Z. Right-click a setting a desk
knob drives → **Unbind** (choose **both** if it has a route too); ⌘Z.
Delete a route with its ×; ⌘Z. `ls -l` again.

**Right if:** after the Learn the DESK section shows "D3 view.bright",
D3's old job is gone, and the footer line ends "; K1 let go"; ⌘Z gives
D3 its old job, K1 its row and the footer says "undid learn
view.bright", the unsaved dot as it was; after Unbind the ring goes dark
and ⌘Z brings row and ring back ("both" is one ⌘Z); the route returns
with its depth and gate; no preset file's time moved.

**Wrong if:** a row not back; a ring staying dark.

*(check 51)*

#### A12. OVERDUB is Home

**Needs:** APC40. The laptop part is L33.

**Do:** party show (home TUMBLE). F5 (TRIP), change a few things, press
OVERDUB. ⌘Z. F7, latch SHIFT, press OVERDUB. Set "starts on" to none,
press OVERDUB; set it back. Right-click any setting → **Learn desk**,
press OVERDUB, then cancel the Learn from the footer.

**Right if:** OVERDUB is lit; it loads TUMBLE with its desk lit; ⌘Z
brings TRIP back with your changes ("undid home → TUMBLE"); under SHIFT
it loads TUMBLE too and SHIFT drops; with no "starts on" its light goes
dark and pressing it loads nothing; during a Learn it still loads the
start preset, says nothing, and the Learn stays armed.

**Wrong if:** OVERDUB dark or dead; something else under SHIFT.

*(check 54)*

#### A13. The crossfader is the master dimmer

**Needs:** APC40. The ghost-hand part of step 4 needs the hand camera
(leave it out without one); the glass part is D4.

**Do:**
1. Quit. Push the crossfader hard left. Launch.
2. Nudge it a little from the left.
3. Slide it all the way right, then back to the left.
4. F5 (TRIP), then F4 for the look-back, with the ghost hands on: set
   the crossfader half way.
5. Leave it at half; press F1, F5, OVERDUB; then move it.
6. Latch SHIFT and move it.
7. Quit at half and launch.

**Right if:** (1) full brightness; the OUTPUT page's first row, **Master
dim**, reads 100%. (2) nothing happens. (3) from the right end it takes
hold and dims smoothly to black at the left, the footer reading "dim
…%" in the warning colour and "dim black" at the end; back right, full,
and the reading goes. (4) the shape, effects, trail and ghost hands are
all half as bright. (5) it stays at half through each load and the next
move carries on from half. (6) it still dims. (7) full again.

**Wrong if:** dark at launch; black at the right end (the direction was
read from the maker's notes, never from the device — say so); a jump
when first touched; dead after a load; something not dimming; a line
under Master dim on the OUTPUT page (the graphics driver refused it).

*(check 55)*

#### A14. Hold the clip-stop row to save a new preset (on the copy)

**Needs:** APC40; the copy.

**Do:**
1. Party show. PRESETS page: right-click F8 → **clear slot**.
2. F5 (TRIP); change the look. Tap a clip-stop button quickly.
3. Hold a clip-stop button; let go after the blinking.
4. Press pad 1, then pad 8.
5. Change the look, hold the row again (another button). Hold once more.
6. Lay two fingers on the row and hold for five seconds.
7. Latch SHIFT and hold the row.
8. Right-click F8 → **put preset here…** → NOITA.
9. Right-click a setting → **Learn desk**, then hold the row.

**Right if:** (1) F8 reads "—" and the footer says "F8: cleared — NOITA
is still in the preset list". (2) the row lights while your finger is
down and nothing is saved. (3) after a little over half a second the row
and pad 8 of row 1 blink for about 1.5 s and TRIP's pad goes out; F8
reads **TRIP 2**, lit, the PRESETS strip says TRIP 2 with no dot, the
footer "saved TRIP 2 → F8", and `<home>/presets/trip-2.json` exists. (4)
your look is back. (5) the next empty slot is now a far one: on the
factory party show slot 10 (row 4's second pad blinks, "→ slot 10"); on
a show of your own slot 9 (row 4's first pad, "→ slot 9"); TRIP 2 is
unchanged. "The bank is full" appears only once all 24 slots are filled.
(6) one new preset, not two. (7) it saves the same way. (8) F8 is NOITA
again and TRIP 2 etc. stay in the list; **clear slot** is greyed on an
empty slot. (9) it saves, nothing is said, and the Learn stays armed.

**Not fails:** the on-screen desk lights the row while held but does not
blink; the key legend does not mention it. If the desk's lights never
light or blink, note what they do (the colours come from the maker's
table and were never seen on this model); the footer line is the real
sign.

**Wrong if:** a tap saving; a save over a taken slot or file; two
presets from one hold.

*(check 56, 83)*

#### A15. Pad rows 4 and 5 are presets (on the copy)

**Needs:** APC40; the copy, with a preset on slot 12 (L3).

**Do:** look at the pad grid. Press row 4's fourth pad. Press an empty
pad in rows 4–5. Latch SHIFT and press another filled far pad. Turn the
cue knob. Right-click a setting → **Learn desk**, press a far pad.

**Right if:** row 1 has one green pad (the loaded preset) and amber on
the other filled slots; row 4's fourth pad is amber; empty ones dark;
the on-screen desk shows the same, amber at half strength with names.
The pressed pad turns green, the old one amber, the picture changes and
slot 12's button is lit. An empty pad: nothing loads, "slot 16: an empty
slot". Under SHIFT: same lights, it loads, SHIFT drops. The cue knob
steps through all 25 shapes (no pad shows the shape any more). During a
Learn the pad loads and the Learn stays armed.

**Judge:** whether amber can be told from green on the real desk — say
what you see.

**Wrong if:** no amber; a pad changing the shape (an old line in
`bindings.json`); nothing under SHIFT.

*(check 82)*

#### A16. Click a control, then a setting

**Needs:** APC40. The first real clicks this feature gets.

**Do:**
1. F1, ROUTING page. Click D6 on the drawn desk.
2. Open VIEW. Point at Speed, click. Turn D6. ⌘Z.
3. Click D6 again, open VIEW, wait 20 seconds without touching anything.
4. Pick D6 and click it again; pick it and click empty ground between
   controls; pick it and click the footer's line.
5. Press H, click D6. Click again without moving the pointer. Then move
   to Speed and click. ⌘Z.
6. Click S2. Latch SHIFT, click K1.
7. SHIFT off: right-click Brightness → **Learn desk**, then click D7 on
   the drawing. ⌘Z.
8. Pull the APC40's cable and map D8 both ways (steps 1–2 and 7).

**Right if:** (1) D6 framed red; ROUTING's row list (not the page)
scrolls to D6's line, framed red; ROUTING not dimmed; the footer counts
down "D6 picked (20 s): click a param on any other page". (2) VIEW is
dimmed and takes no input except the click — page list and footer still
work; Speed is framed red with "click: put D6 on Speed"; the click says
"learned view.speed ← D6 (device knob 6) (into the preset); K2 let go",
Speed does not move, the page brightens; D6's ring lights and moves
Speed; K2 goes dark; ⌘Z undoes it. (3) the page comes back by itself:
"D6 let go — no click for 20 s"; any click restarts the count. (4) each
lets go at once. (5) the panel returns with VIEW dimmed; the second
click without moving maps nothing; after moving, the click maps. (6) S2:
"S2 (track fader 2) is invariant (the session's): BASS Post-drive", VIEW
not dimmed, ROUTING scrolls to it; K1 under SHIFT: "… on the global
layer … latch SHIFT off to map into the preset: Steadiness". (7)
"learned view.bright ← D7 (device knob 7) (into the preset); K1 let go",
K1 dark (▲ ▼ keep Brightness). (8) the same lines, the dot lit.

**Judge:** whether the dimming reads as "waiting for a click", whether
20 s is long enough, and whether you would rather the click opened
ROUTING.

**Wrong if:** the click moves the slider; nothing maps; the page never
returns; ROUTING's whole page scrolls; a map lands on a fader or under
SHIFT.

*(check 70)*

#### A17. Knob smoothing

**Needs:** APC40.

**Do:** F3 (FIELD). SYSTEM page, under "midi": **Knob smoothing**. Turn
K8 (Zoom) slowly, then fast. Set smoothing to "off" and turn K8 slowly.
Try 50 ms and 200 ms. Move S1 and the crossfader. Turn the cue knob,
press a pad.

**Right if:** it reads "80 ms" and the show's dot is clean; the zoom
glides, settles within a blink when you stop, the ring sits where your
fingers left it; a fast spin neither lags noticeably nor overshoots; the
ring never crawls backwards and the next turn carries on from it. Off:
the picture steps, as before, and the show's dot lights (the number is
saved with the show). Faders and the crossfader glide too, and an
uncaught fader still waits. Cue knob and pads: one step per click.

**Judge:** whether 80 ms feels right — leave it where it feels right.

**Wrong if:** the knob fights you; a value that never settles; "off" at
launch on a show that never saved the number.

**Changes:** the number is saved with the show.

*(check 78)*

#### A18. The instances knob at the bottom

**Needs:** APC40.

**Do:** F1 (TUMBLE). Turn track knob 3 (K3) fully left.

**Right if:** the bottom of that knob is now "nothing drawn", not one
copy.

**Judge:** whether that is too easy to land on.

*(check 62)*

## (b) The hand camera

Plug in the hand camera (Ultraleap Leap Motion Controller 2) by USB
before launching; the Ultraleap Hand Tracking service must be running.
The config has `[hands]` `enabled = true` and `mode = "desktop"`.
**B1 first**, with nobody else in the camera's view. Leave the APC40
plugged in for B23–B28.

#### B1. Calibrate, and the box it draws — run first

**Needs:** hand camera; nobody but you in its view.

**Do:**
1. Launch, HANDS page. Before touching anything, look at the box view.
2. Open **feel & calibration**, press **calibrate 20 s**, and move both
   hands through everything they should reach: side to side, low to
   high, near to far, and each tilt end to end. Each hand must travel
   more than 12 cm in a direction for it to count.

**Right if:** (1) if `<home>/hands.json` existed, the ranges are its
ones, there is no inner rectangle, and the line under the axis's range
reads "box open". (2) the note reads "calibrated 12 axes · box W × H × D
mm · the old file kept as hands.json.bak-v1" (the last part only if the
file existed); the box view now has an inner rectangle and the height
gauge a bracket; both hands' dots stay inside it wherever you played;
`hands.json` holds `"schema": "hyperspace.hands/2"` and a `box`; every
axis still reaches both ends of its row.

**Wrong if:** "x open (not swept)" — sweep wider on that direction and
run it again; "box left as it was (too few palm samples)" — the camera
barely saw a hand; no rectangle; no `.bak-v1`. A rectangle pressed
against the view's edge is not a fail: say whether it reads.

**Changes:** `<home>/hands.json` rewritten, the old one kept as
`hands.json.bak-v1`.

*(check 72, 15)*

#### B2. The probe sees both hands

**Needs:** hand camera; app closed.

**Do:** `uv run python tools/hands_probe.py`; move both hands; pinch;
Ctrl-C.

**Right if:** both hands appear within a second of entering; every
axis's readings change as you move; the pinch gaps print live; Ctrl-C
exits cleanly.

**Wrong if:** "no service" or nothing (the Ultraleap service is not
running or not found); a hand seen only very high (the `mode` setting).

*(check 13)*

#### B3. The HANDS page and which way is up

**Needs:** hand camera.

**Do:** HANDS page. Both hands in the box. Roll thumb-up, tilt fingers
up, turn fingers outward. Pinch each finger to the thumb.

**Right if:** two dots (left white, right red) follow the palms; on both
hands, thumb-up roll reads up, fingers-up reads up, fingers-outward reads
up; the eight pinch switches close on a pinch and show the gap. The page
fits with no scrollbar with the tracker on: switches beside the box, the
feel knobs two to a row.

**Wrong if:** a direction the wrong way (flip it for now with that axis's
invert setting and note it); a scrollbar.

*(check 14, 4)*

#### B4. A hand outside the box

**Needs:** hand camera.

**Do:** load `hands-play` (right hand height = brightness). Right hand
mid-height in the box; move it slowly out through the right side. Wobble
it a centimetre at the edge. Bring it back. Repeat upward past the
bracket and toward yourself.

**Right if:** a centimetre or two past the rectangle the dot becomes a
hollow dim ring, the status line shows `R◌` (hover: "tracked, but outside
the box"), its rows dim, and brightness returns to its setting at once;
at the edge it does not flicker; coming back the value glides onto the
hand, no jump.

**Judge:** whether `◌` can be told from `●` and `○` at arm's length.

**Wrong if:** still performing far outside; flicker at the edge; a jump
on re-entry.

*(check 73)*

#### B5. The default feel

**Needs:** hand camera.

**Do:** load `hands-play`. Raise and lower the right hand; watch
brightness. On the HANDS page the defaults are Steadiness 1 Hz, Response
4, Catch 150 ms, Return 500 ms, bounce 0.15, dead zone 0.04. Tune them
until it feels right, then save from the HANDS page's strip as
`factory`.

**Right if:** a still hand does not shimmer, a fast one does not lag, a
returning hand glides on rather than jumping.

**Wrong if:** shimmer at rest (Steadiness too high); lag (Response too
low).

**Changes:** writes `<home>/hands/factory.json`; tell the developers so
it can be shipped.

*(check 16)*

#### B6. Tilt and turn without moving height

**Needs:** hand camera.

**Do:** load `hands-fx`. Hold the right hand still; tilt it (fingers up
and down), then turn it (fingers left and right).

**Right if:** the Acid effect's twist (tilt) and bend (turn) move while
FX mix (height) stays within a few percent.

**Wrong if:** height moving with a tilt (widen the right hand's height
dead zone, or note it as a feel finding).

*(check 17)*

#### B7. The thumb-to-ring-finger pinch

**Needs:** hand camera.

**Do:** HANDS page; watch the ring finger's gap. Pinch thumb to ring
finger deliberately; open.

**Right if:** the gap drops below 0.34 (of the palm's size) and the
switch closes; opening past 0.46 lets go.

**Wrong if:** never below 0.34 on a deliberate pinch — note the gap you
read (the thresholds are the same for every finger).

*(check 18)*

#### B8. Learn onto a setting a hand already drives

**Needs:** hand camera. (Optionally a relaunch with `[midi] enabled =
false`.)

**Do:** load `hands-play`. VIEW page: right-click Brightness → **Learn
hand ▸ left**; move the left hand up and down. Choose **Keep**. Repeat
and choose **Replace**. Optionally set `[midi] enabled = false`, launch
and repeat, then put it back.

**Right if:** while armed, the footer reads "learning view.bright — move
the left hand…" on every page and only the left hand can complete it; a
prompt appears whichever page you are on — "ONE PERFORMER PER
PARAMETER", "Brightness is already performed by R height positions.",
"L height positions asks for it.", **Replace** / **Keep**; moving hands while it is up
learns nothing more; Keep changes nothing on ROUTING; Replace makes the
row read "L height positions", the line ends "moved from view.speed"
(the preset's own left-height row on Speed is gone), the unsaved dot
lights, and `<home>/bindings.json` is not written. (Had a tilt moved
most, the row would read "pushes +0.25" — also fine.) With MIDI off it
still works.

**Wrong if:** it lands with no prompt; the wrong axis learned.

*(check 19)*

#### B9. Pinch zoom while scrolling

**Needs:** hand camera; a scroll wheel or trackpad.

**Do:** load `hands-pinch`. Pinch left thumb to middle finger and move
the left hand: zoom follows. Keep pinching and scroll a few notches in
the render window. Open the pinch.

**Right if:** zoom does not run away while scrolling; when the pinch
opens, zoom lands on the value the scroll set, not where the hand left
it.

**Wrong if:** drift while scrolling; a jump to the hand's last value.

*(check 20)*

#### B10. The right hand deepens the breathing

**Needs:** hand camera.

**Do:** load `lfo-breathe`; LFO page. Raise the right hand, then lower
it, then take it out.

**Right if:** LFO 1's depth slider's ghost bar rises with the hand and
the brightness swell deepens; nothing else moves (speed, zoom, effects);
lowered or gone, depth returns to 0.6.

**Wrong if:** something else moving (a route on the ROUTING page); depth
not returning when the hand leaves.

*(check 21)*

#### B11. A second pinch at another height

**Needs:** hand camera.

**Do:** `hands-pinch`: pinch right index low (dark), open, raise the
hand, pinch again, open.

**Right if:** brightness takes the hand's new height at once and returns
to its setting on open.

**Judge:** whether that jump should glide (the 150 ms catch) instead.

*(check 23)*

#### B12. A hand leaving, and "hold"

**Needs:** hand camera.

**Do:** `hands-play`, HANDS page. Take the right hand out. Set the right
hand height's **rest** to *hold*; take it out again. Bring it back.

**Right if:** its rows dim and say "DAW only; lane —"; brightness is
back at its setting the same frame; with *hold* the value sent to
outside music software holds but the picture still returns; on re-entry
the row glides onto the hand.

**Wrong if:** the setting parked at the rest value.

*(check 24)*

#### B13. A hand moving makes no undo step

**Needs:** hand camera; music.

**Do:** F1 (TUMBLE). VIEW page: drag Brightness, wait a second. Play for
half a minute with both hands, in and out several times. ⌘Z once.

**Right if:** Brightness goes back — the one thing you did by hand.

**Wrong if:** the footer says "undid Speed …" (or another setting a hand
drives), or names a rotation or the BPM.

*(check 52)*

#### B14. A hand Learn listens to one hand

**Needs:** hand camera; B1 done.

**Do:** F1. Left hand still in the box. With the right hand on the
trackpad, CAMERA page: right-click Zoom → **Learn hand ▸ left**. Move the
right hand freely over the box for five seconds. Raise the left hand
slowly. ⌘Z. Repeat with **right** and the hands swapped. Then arm **left**,
click the footer's line to cancel, arm again at once and keep both hands
still.

**Right if:** nothing is learned from the right hand; the footer reads
"learning camera.zoom — move the left hand… (click to cancel)"; raising
the left hand gives "learned camera.zoom ← hand left.y positions (into
the preset; moved from master.gain)" — any left-hand axis is a pass —
ROUTING lists "L height" and Zoom follows the left hand only; TUMBLE's
own left-height row on the sound drive goes with it (⌘Z brings it back).
After re-arming, nothing is learned until the left hand moves.

**Wrong if:** the right hand took it; learned the moment it was armed.

*(check 66)*

#### B15. A tilt learned is gentle

**Needs:** hand camera.

**Do:** `hands-play`. VIEW page: right-click Speed → **Learn hand ▸
right**, roll the right hand, choose **Replace**. Then learn the right
hand's turn onto the XY rotation rate. Then lower **Learn depth** (HANDS
page, feel & calibration) and learn the right hand's tilt onto the XZ
rate.

**Right if:** the row reads "R roll pushes +0.25"; with the hand level
the speed is the preset's; a full roll takes it to about half or double,
not to stop or flat out; the XY rate turns as set with the hand level,
and a small turn nudges it; the XZ row carries the new depth, the others
keep 0.25, and the line ends "moved from view.depth4". Learning the same
axis onto the same setting again changes only its gate.

**Wrong if:** "positions" on a tilt; the setting jumping when the hand
enters.

*(check 75)*

#### B16. Height is still a fader where it should be

**Needs:** hand camera; after B15.

**Do:** learn the left hand's height onto Pattern mix; then onto the YZ
rate; then a tilt onto Faces; then a tilt onto Instances. Then load
`hands-play`, `hands-pinch` and F1–F8 and look at ROUTING each time.

**Right if:** Pattern mix: "L height positions" (low none, high full);
YZ rate: "L height pushes +0.25", the Pattern mix row gone, the plane
turns as set with the hand low and faster as it rises, never backwards
and never stopped; Faces: "positions", flipping past the middle;
Instances: "positions". Every factory preset's rows read as before.

**Wrong if:** a factory row changed.

*(check 76)*

#### B17. A Learn moves the axis

**Needs:** hand camera.

**Do:** F1 (TUMBLE): right roll turns the XW plane. Learn right roll
onto Brightness (**Learn hand ▸ right**, roll). ⌘Z.

**Right if:** the line says "learned view.bright ← … pushes +0.25 (into
the preset; moved from rot.phase.XW)", ROUTING no longer has the XW row,
roll moves brightness only; ⌘Z brings the XW row back and removes the
new one.

**Judge:** whether a Learn should instead add a row and keep the old one.

*(check 77)*

#### B18. Two hands steer the camera

**Needs:** hand camera.

**Do:** load `hands-orbit` from the list. Right hand in, level, mid box;
slide it left and right; tip fingers up. Left hand: side to side,
reaching in, raising. Take both out. Press R with a hand in.

**Right if:** a still level hand moves nothing; right hand side to side
orbits about a quarter turn each way; fingers up looks down onto the
shape; left hand pans and raising it zooms to about 2.2×; with both out
the camera is back where the mouse left it.

R with a hand in snaps the view to its reset at once. **Know:** the
reset is made under the hand's push, so when the hand then leaves the
camera lands past the reset view by what the hand was adding — say
whether that matters.

**Judge:** the directions, the zoom depth, and whether this is the
"orbit" you meant.

*(check 80)*

#### B19. Hand routes follow the axis by name

**Needs:** hand camera.

**Do:** in the config under `[hands]` set
`dofs = ["yaw", "pitch", "roll", "y", "x", "z"]`; launch; load
`hands-play`, then `hands-pinch`. Then set `dofs = ["x", "y", "z"]`;
launch; `hands-play`.

**Right if:** first: right height still drives brightness, left height
speed, right tilt 4D depth; ROUTING reads "R y positions", "L y
positions", "R pitch positions" and the source lists show `hand R y`
etc.; a right index pinch still picks brightness. Second: the right tilt
row does nothing while both heights work.

**Wrong if:** a row moving with the wrong axis; raw `hand:<n>` in the
lists.

**Changes:** remove the `dofs` line.

*(check 42)*

#### B20. The "screentop" warning

**Needs:** hand camera.

**Do:** set `[hands]` `mode = "screentop"`; launch; tick **Ghost hands**.

**Right if:** the ghost's **more ▸** chip reads **! more ▸** in the
warning colour, and clicking it shows "ghost axes for screentop are
unmeasured: left/right and up may be wrong — Mirror flips left for
right" (in desktop mode the chip reads **more ▸** and says nothing); the
page does not scroll with every ghost control showing, and no control
is drawn over another or over the **Ghost hands** label.

**Changes:** put `mode = "desktop"` back.

*(check 100)*

#### B21. Zero instances with hands in

**Needs:** hand camera.

**Do:** F3 (FIELD): right hand at the bottom of the box, then the top.
Then ghost hands on and Instances 0.

**Right if:** at the bottom nine copies, never none; at the top the room
fills (69 copies); the ghost hands still draw at 0.

**Wrong if:** FIELD blanks with a low hand.

*(check 62)*

#### B22. The hands' own port in FL Studio

**Needs:** hand camera; FL Studio; the IAC bus (see Part 1, FL Studio).

**Do:** hands on, launch. In FL Studio look for a "Hyperspace Hands"
input; raise the right hand. Then set `[hands] out = "IAC"` (the app's
own virtual port never goes away, so only a named bus tests the
rejoin), launch, take the IAC bus offline in Audio MIDI Setup while
running, then bring it back. Put `out` back afterwards.

**Right if:** FL sees "Hyperspace Hands"; right-hand height shows on CC
109, channel 16; the port is rejoined within 2 s if the bus was back
within about ten seconds, otherwise within 10 s.

**Wrong if:** no rejoin.

*(check 29)*

#### B23. A knob on a setting a hand drives

**Needs:** hand camera, APC40.

**Do:** `hands-play`; right hand in the box (it drives brightness). Turn
K1 (Brightness). Take the hand out of the box.

**Right if:** the setting moves (the ring follows), the picture does not;
with smoothing on (80 ms) it glides; when the hand leaves, brightness
lands on the knob's value at once — no fade to minimum.

**Wrong if:** brightness dropping when the hand leaves; the knob dead
while the hand is in.

*(check 22)*

#### B24. A hand on the desk does not perform; reset

**Needs:** hand camera, APC40 where it will stand for the show.

**Do:** `hands-play`. Reach for the APC40 with the right hand and turn a
knob (left hand away). Tick Ghost hands; move a hand out of the box. Then
press **reset ranges**; afterwards run B1 again.

**Right if:** brightness moves only by the knob; the right hand's mark is
a hollow ring (or gone) the whole time; the ghost hand fades out at the
frame's edge, and the frame shows the whole box; reset removes the
rectangle and bracket, the note reads "ranges back to the defaults, box
open", and a hand is present wherever the camera sees it.

**Wrong if:** the dot filled while your hand is on the desk — the desk is
inside the box: move it, or calibrate again keeping clear of it; the
ghost drawn outside.

**Changes:** reset clears the box; B1 puts it back.

*(check 74)*

#### B25. A desk Learn ignores the hands

**Needs:** hand camera, APC40.

**Do:**
1. F1. VIEW page: right-click 4D depth → **Learn desk**.
2. Wave both hands through the box for five seconds.
3. Move S3 a little. Tap TAP TEMPO. Press SHIFT; turn K2.
4. Press SHIFT again; turn D5.
5. Arm **Learn desk** again and press a pad in row 1; cancel by clicking
   the footer's line.

**Right if:** (1) its control framed red, the footer in red "learning
view.depth4 — turn a knob or press a button on th…" on every page (the
full line in its hover). (2) still armed; no new route (TUMBLE's own
hand route still moves depth). (3) S3 moves the third band's drive and
TAP taps, nothing said, still armed; SHIFT lights and the desk header
says GLOBAL LAYER; K2 shows for four seconds in the warning colour "K2
(track knob 2) is on the global layer (the session's) — latch SHIFT off
to learn into the preset", then the red line returns — still armed —
and K2 did not move Response. (4) "learned view.depth4 ← D5 (device
knob 5) (into the preset); D1 let go" (D1 had 4D depth), D5's ring
lights, the frame and red line go.
(5) the preset loads and the Learn stays armed.

**Judge:** whether swallowing every control under SHIFT during a desk
Learn is a trap.

**Wrong if:** the hands took it; a fader or TAP ended it; SHIFT did not
latch.

*(check 65; replaces check 37)*

#### B26. A knob bumped during a hand Learn

**Needs:** hand camera, APC40.

**Do:** F5 (TRIP), hands out. VIEW page: right-click Speed → **Learn hand
▸ right**. Turn D1, turn the cue knob, press a filled pad in row 4 and
an empty one. Click a control on the drawn desk. Click the footer's red
line.

**Right if:** FX mix moves with D1, the cue knob changes the shape; a
filled row-4 pad loads its preset (Learn still armed), an empty one says
"slot N: an empty slot"; the footer still reads "learning view.speed —
move the right hand…"; no new desk line, K2 still has Speed; the click
on the drawing does nothing; the footer click cancels.

**Wrong if:** D1 now drives Speed; the drawing click mapped something.

*(check 67)*

#### B27. A smoothed knob with everything else

**Needs:** hand camera, APC40.

**Do:** Knob smoothing at 250 ms (SYSTEM page). Spin K1 and press F5 at
the same moment; then the same with F5's pad. Spin K1 and latch SHIFT.
Sweep K1, wait, ⌘Z; sweep and ⌘Z while it moves. `hands-play`, hand in:
turn K1; take the hand out. Slide the crossfader and press F2 mid-slide.

**Right if:** the look is TRIP's with TRIP's brightness, not the knob's;
under SHIFT brightness still arrives and K1's ring shows the SHIFT
layer's value; one ⌘Z undoes a whole sweep (the footer names where it
landed); ⌘Z mid-glide goes back and stays; with the hand in the picture
does not move, and when the hand leaves brightness is where the knob put
it; the dim finishes arriving after F2.

**Changes:** put Knob smoothing back where A17 left it.

*(check 79)*

#### B28. A hand cannot learn a ghost-hand setting

**Needs:** hand camera, APC40.

**Do:** HANDS page, Ghost hands on: right-click **Guide** and **Style**,
and in **more ▸** right-click **Mirror** and **Tethers**; then Ghost
hands and Opacity. Learn desk on Mirror, then press a pad. OUTPUT page: right-click its ticks.

**Right if:** the four have **Learn desk** but no **Learn hand ▸**; Ghost
hands and Ghost opacity still have Learn hand; the pad flips the mirror;
the OUTPUT ticks: Learn desk, no Learn hand. A preset of yours with a
route onto mirror, guide or tethers (if any) loads with the note
"dropped … → ghost.mirror: not modulatable" and its file is not
rewritten.

**Wrong if:** a Learn hand item on one of the four; a row made.

*(check 110)*

#### B29. Hand-to-picture delay

**Needs:** hand camera; a phone that films at 120 frames a second.

**Do:** `hands-play`. Film the hand and the render window together; flick
the right hand up. Count video frames between the hand moving and
brightness changing.

**Right if:** under about 4 frames at 60 per second (this is a target
nobody has measured).

*(check 25)*

## (c) One projector, or any second screen

Plug it in before launching. For C1–C4 the config has no
`[[output.screens]]` list.

#### C1. Choosing the screen; the see-through mode locked

**Needs:** projector.

**Do:**
1. OUTPUT page: open **Screen**; pick the projector; tick
   **Fullscreen**. Press T and the APC40's MASTER button if plugged in.
   Back to "follow window", Fullscreen off.
2. In the config, `[output]` `monitor = 1` and `fullscreen = true`;
   launch.

**Right if:** the list shows "follow window" first, then each screen by
name; the picture fills the projector at its own sharpness (edges as
fine as on the laptop); the control window stays on the laptop; with no
`overlay` line in the config the Overlay switch is greyed with "overlay
off in the config: set [output] overlay = true in config.toml", and T
and MASTER change nothing; "follow window" with fullscreen off returns a
normal window. (2) it opens straight on the projector. (Screen and
Fullscreen are output 1's only; with an output list they come from the
list — see D1.)

**Wrong if:** the wrong screen; blurry edges; the desktop showing through
or T floating the window.

**Changes:** take out `monitor` and `fullscreen` (or leave them for C2).

*(check 26)*

#### C2. A black ground, never see-through

**Needs:** projector; a white web page full screen on the projector,
behind the render window.

**Do:** fullscreen the render window on the projector (OUTPUT page).
Press F for faces. Press F1–F5 in turn, ticking and unticking
**Cut-through** on each.

**Right if:** no desktop anywhere, ever: black ground, faces and lines lit
on black, on every preset, Cut-through on or off, with effects on (TRIP)
and the look-back on (WAKE).

**Wrong if:** the desktop through the faces or faint lines; through the
whole ground (check the OUTPUT page: is it in overlay mode?).

*(check 43; with two outputs, D4 runs it on each)*

#### C3. Windows reopen on the right screen

**Needs:** projector (and unplugging it once).

**Do:**
1. Drag the render window onto the projector; Esc; launch.
2. Set `[output] fullscreen = true` (no `monitor`); launch. Esc; look at
   `<home>/windows.json`.
3. Unplug the projector; launch. Put `fullscreen` back to false.
4. Projector in. Set `monitor = 0`, `control_monitor = 1`; launch. Then
   `monitor = 7`; launch. Then `monitor = "left"`; launch. Remove both
   lines.

**Right if:** (1) it opens on the projector, the control window on the
laptop. (2) fullscreen on the projector with no drag; the file still
holds the windowed size. (3) the render window opens on the laptop at
its default spot, and the terminal and SYSTEM page name the screen it
was last on. (4) the windows swap (render on screen 0, controls on
screen 1); with 7, the note "monitor = 7, but 2 screens are connected
(0–1) — using the last position"; with "left", the app still launches
with "monitor = 'left' is not a screen index — using the last position".

**Know:** a screen number that is not there at launch is ignored for the
whole run — plug in first.

**Wrong if:** a window off every screen; the wrong screen for a number;
the app not launching with "left". If a window cannot be reached, delete
`windows.json`.

*(check 61)*

#### C4. Dream speed on the rig

**Needs:** projector; the dream running.

**Do:** with the render window on the projector, repeat L24 at the same
speed setting.

**Right if:** the dream feels the same speed as on the laptop screen at
the same number (it counts the dream's own frames, not seconds).

**Judge:** if it feels different, say so.

*(check 96)*

## (d) The glass and the projector together

*The glass* is the Pepper's Ghost screen. Plug both screens in before
launching; read their numbers off the OUTPUT page's **Screen** list
first (they can change when a display is plugged in). D1 sets up the
config the rest use. Most entries also need the hand camera (calibrated,
B1) and some the APC40. **D12 and D13 last.**

#### D1. Two outputs open where the config says

**Needs:** glass, projector.

**Do:** in the config, under `[output]`, set `control_monitor` to the
laptop's number and remove `monitor` and `fullscreen`. Below that
section paste, with your numbers:

```toml
[[output.screens]]         # output 1: the glass — sets the frame size and pace
name = "glass"
monitor = 1
fullscreen = true

[[output.screens]]         # output 2: the projector
name = "projector"
monitor = 2
fullscreen = true
dim = 0.6                  # optional: its own dim at launch (never under 0.1)
```

Launch. Quit and launch again.

**Right if:** the glass and the projector each go fullscreen with the
same picture; the control window is on the laptop; SYSTEM has no config
note; the OUTPUT page shows two blocks, "1 glass" and "2 projector",
each with three ticks and a **dim** row (100% and 60%), and under them
"paced by output 1 · frame W×H · below: output 1's window"; the same
after relaunch; `<home>/windows.json` has two `render` entries in this
order.

**Wrong if:** one window; outputs swapped (output 1 is the first entry);
an output on the laptop. If the screens differ in size, list the larger
first.

**Changes:** the config; take the `[[output.screens]]` entries out to go
back to one output.

*(check 101)*

#### D2. The eight output states

**Needs:** glass, projector, hand camera.

**Do:** Ghost hands on (HANDS page), a hand in the box, F5 (TRIP). On the
OUTPUT page, walk output 1 through the eight combinations of its
**scene**, **hands** and **through effects** ticks, then output 2:

| scene | hands | through effects | What it shows |
|---|---|---|---|
| on | on | off | the scene with its effects, hands clean on top (the default) |
| on | on | on | scene and hands, both bent by the effects |
| on | off | off | the scene with its effects |
| on | off | on | the same as the row above |
| off | on | off | the hands alone on black |
| off | on | on | the hands alone through the effects; an effect that makes its own light lights the ground |
| off | off | off | black |
| off | off | on | black |

Then switch every effect off; then untick Ghost hands.

**Right if:** each state shows its row on that output only, the other
does not change, and the "shows:" line says what you see; with every
effect off, "through" changes nothing; with Ghost hands off, the hands
leave every output.

**Wrong if:** a change on the other output; echoes showing in the "hands
alone through the effects" state.

*(check 102)*

#### D3. Hands over or through the effects; the guide never bent

**Needs:** glass, projector, hand camera.

**Do:** glass: through effects **on**; projector: **off**. F5 (TRIP),
then F4 (WAKE). Switch every effect off. Then HANDS page: Guide
BESIDE, then ON HAND, Tethers (in **more ▸**) on.

**Right if:** on the glass the hands bend and recolour with the shape; on
the projector they are clean; on neither do the hands leave echoes or
feed the dream, and the echoes are the same on both; with effects off
the two look alike and the glass's block says "through: no effect on";
the guide gauges and tether labels are sharp and identical on both,
never folded or warped.

**Wrong if:** hand echoes; warped labels; different echoes on the two.

*(check 103, 47)*

#### D4. The dims

**Needs:** glass, projector, APC40.

**Do:**
1. Crossfader to the middle. Output 2's dim to half. Crossfader left.
2. Untick and tick an output switch, ⌘Z. Press F1, and load a show.
3. Quit, launch.
4. With a white page behind each output, repeat C2 (faces, F1–F5,
   Cut-through on and off) on both.

**Right if:** (1) both dim together; only the projector dims further and
its "shows:" line ends in the product ("· 30%" at master 60%); left:
both black, the footer "dim black". On the glass the ground stays solid
black at every dim, never grey or see-through. (2) ⌘Z does not take a
switch back; loads leave switches and dims alone. (3) master full, the
projector's dim back to the config's 60%, switches as the config says.
(4) no desktop on either (every output after the first is always
solid).

**Wrong if:** the wrong product; a switch moved by ⌘Z or a preset; the
desktop through the glass.

*(check 104, 55, 43)*

#### D5. Black is never a mystery

**Needs:** glass, projector.

**Do:** on the OUTPUT page, one output at a time: untick scene and
hands; then scene off and hands on with no hand in the box; then scene
on and its own dim to 0; then the crossfader left. Then Ghost hands off
with an output's hands ticked; then through effects ticked with no
effect on.

**Right if:** its "shows:" line, in the warning colour, reads in turn
"black — nothing switched on", "black — the scene is off and no hand
shows", "black — dim 0", "black — master dim"; for the first three the
footer on every page adds "· output 2 black" ("· outputs 1, 2 black" for
both); for the master only "dim black". With Ghost hands off: "hands:
ghost hands are off (HANDS page)" (with no camera: "hands: no
tracker"); with nothing to go through: "through: no effect on".

*(check 105)*

#### D6. An output of another shape

**Needs:** glass, projector, hand camera.

**Do:** if the two screens differ in shape, look at output 2. If not, set
its `fullscreen = false`, launch, and drag its window tall and narrow.

**Right if:** output 2 shows the whole frame centred with black bars,
circles round, nothing cropped, the hands on the same part of the shape
as on the glass.

**Wrong if:** stretched or cropped; the hands off their place.

**Changes:** put `fullscreen = true` back.

*(check 106)*

#### D7. Frame rate and tearing with two screens

**Needs:** glass, projector, hand camera. Nobody has seen this hold: in
scripted runs on one screen the app ran unlimited, at about 270–380
frames a second, and the one-window path did the same.

**Do:** both fullscreen, F5, a hand in the box, output 1 through effects
on and output 2 off. Note both screens' refresh rates (System Settings →
Displays). Watch the footer's FPS; watch the projector during fast
rotation; after five minutes look at `stall.log`.

**Right if:** FPS holds at the glass's refresh rate; no tearing (a
horizontal split in the picture) on the projector; no new stall log
entry.

**Wrong if:** half the refresh rate; tearing on the projector; far above
the refresh rate (the screen is not pacing the app at all). Note what
you see either way.

*(check 107)*

#### D8. The ghost hands follow the real ones

**Needs:** glass, hand camera.

**Do:** HANDS page: tick **Ghost hands**, opacity about 60%. Sit where
you perform, both hands in the box. Check:
- **Left and right not swapped:** raise only the left hand — the
  near-white hand on the left of the picture moves; the light red one is
  on the right.
- **Fingers:** spread, fist, pinch thumb to each finger, point: every
  finger follows, thumb on the correct side, nothing bending backwards.
- **Directions from the performer's side:** right is right, up is up,
  toward the screen goes away; palm down shows the back of the hand.
  Then tick **Mirror** (in **more ▸**) and look in the glass as the
  audience will.
- **No lag:** shake a hand — the ghost stays on it; hold still — no
  shimmer.
- **The box fills the frame:** reach each calibrated corner — the hand
  stays in frame, near the edge.
- **Leaving:** pull a hand out — it fades where it was in about a third
  of a second and fades back in on return; nothing freezes or jumps.
- **Off is off:** untick Ghost hands — the picture is as before.
- **The guide:** Guide BESIDE. Move the right hand straight right,
  then up, then toward the screen: each time one ball moves (red, green,
  blue) and the others stay. Tilt fingers up, turn them outward, roll
  thumb-up: the red arc's dot rises, the green's goes out, the blue's
  turns; no dot leaves its arc. Pinch each finger: its bead lights. Fist:
  the grab ring shrinks round a full ball. Route a few left-hand axes and
  none on the right (ROUTING): the routed left ones keep their colour,
  everything on the right is grey and smaller but still moves. ON HAND:
  the gauge rides the palm. Tick **Tethers** (in **more ▸**): each routed left axis
  gets a line in its colour to a label at the left edge naming its
  setting; the lines hold still while the balls move; untick and the
  gauges stay.
- If the rig ever uses `screentop`, repeat the directions there.

Then record the hand tape others will test against: `uv run python
tools/hands_tape.py record tests/fixtures/hands/rig.json --seconds 6` —
both hands, open, fist, pinches, in and out of the box — and commit it.

**Right if:** every point above holds. Note which Ghost mirror setting
the rig wants and save it in the show.

**Wrong if:** swapped or mirrored hands; a finger on the wrong digit or
bending wrongly; lag.

**Changes:** the tape file, a new file in the repository.

*(check 108, 47)*

#### D9. The five hand styles from the audience

**Needs:** glass, hand camera.

**Do:** HANDS page, Ghost hands on: the **Style** list. With both hands in
the box, step through from where the audience stands: HANDS (capsule
hands), JOINTS (a bead per joint, largest at the fingertips), PALMS (an
orb that swells as the hand opens, a ring, a spoke where the fingers
point), CAGE (a wire diamond shape that turns with the palm and breathes
with the grip), MARIONETTE (fingertip beads on strings from a bar above).
Try the guide ON HAND with each. Quit and launch.

**Right if:** each follows with no lag; the orb and cage open and close
with your grip; a leaving hand fades in every style; ON HAND, the guide
is on top in the four new styles and partly behind the palm in HANDS;
the frame rate does not change; the style is kept after relaunch.

**Judge:** which styles to keep; whether a real fist or open hand reads
wrong (the grip was tuned on fake hands only).

*(check 109)*

#### D10. Effects on the faces, on the rig

**Needs:** projector, then glass.

**Do:** repeat L15's looks on the projector and then on the glass:
Kaleidoscope on the faces with a picture loaded, per face and screen;
Plasma on the faces over FLAT. Stand where the audience will.

**Right if:** in screen mode the picture is sharp enough at room size and
not stretched (cropped top and bottom on a wide output); per face, a
face near the camera shows no blocks; on the glass, no desktop or grey
through the faces.

**Judge:** whether the faces' effects read at all at the faces'
brightness, per face especially, or need the pattern mix or brightness
up (say which preset).

**Wrong if:** soft or blocky; squashed; see-through faces on the glass.

*(check 98)*

#### D11. The party presets on the rig

**Needs:** glass, projector, hand camera, APC40.

**Do:** party show. F1 TUMBLE, F2 FACES, F3 FIELD, F4 WAKE, F5 TRIP, F6
ACID, F7 MANDALA, F8 NOITA, then TRACER from the list. The performer
cards in `docs/plans/assets/12-presets/party-*.md` say what each hand
does. For TRIP, first tap TAP TEMPO eight times and press METRONOME once.
Turn the device knobs on each.

**Right if:**
- faces at 2.5× (FACES) and 2.0× (TUMBLE, WAKE) read in the room, and the
  left hand's headroom up to 4× is usable, not a white-out;
- a tilt's ±45° feels like holding the object, and the half-second
  spring back when you let go reads as "let go", not a slip;
- thumb up is up, fingers out is out, reaching in is away, on every row
  (the cards' words);
- FIELD at the right hand's top (69 copies, faces on) holds its frame
  rate and the swing looks deliberate, not messy;
- WAKE with the dream: right roll turns the dream's colour round the
  wheel, fingers up brings the dream in; the wake reaches past the faces;
- TRIP: the left hand's height opens a pump on the beat and the burst at
  the right hand's top is light, not glare;
- ACID, MANDALA, NOITA and TRACER keep a black ground with no hand in the
  box (MANDALA's plasma comes in only with right fingers up);
- the device knobs D1–D8, each ring showing its value — WAKE: echo
  brightness, echo fade time, darken, contrast, shape hides, dream
  brightness, dream saturation, dream speed; TRIP: FX mix, plasma level,
  kaleidoscope segments, kaleidoscope zoom, zoom burst amount, zoom burst
  glow, hue cycle paint, hue cycle spread; ACID: FX mix, acid bend, twist,
  reach, breathe, wobble amount, deconverge amount, hue cycle spread;
  MANDALA: FX mix, plasma level, kaleidoscope segments, kaleidoscope zoom,
  fractals amount, fractals ground, glimmer amount, glimmer ground; NOITA:
  FX mix, trip warp amount, trip warp scale, trip colour amount, fractals
  amount, fractals size, double vision amount, double vision ghost;
  TRACER: echo brightness, echo fade time, echo count, echo time apart,
  darken, contrast, shape hides, 4D depth; on TUMBLE, FACES and FIELD
  D1–D4 are 4D depth, yaw, pitch and pattern and D5–D8 dark; TUMBLE's
  left height still pushes the sound drive, marked "session" on ROUTING.

**Wrong if:** a look off (a number in the preset); a knob on the wrong
setting; an axis flipped on every preset (then flip it on the HANDS page
and save the hands setup).

*(check 41, 32)*

#### D12. A screen not plugged in at launch

**Needs:** glass, projector; D1's config.

**Do:** quit, unplug the projector, launch. Plug it in while running.
Then ⌘R.

**Right if:** only the glass opens; the OUTPUT page shows output 1's
block and one greyed line "2 projector — screen 2 is not connected";
SYSTEM and the terminal say "config: output 2 (projector): monitor = 2,
but 2 screens are connected (0–1) — not opened" (your numbers); plugging
in while running does nothing; ⌘R opens it.

**Wrong if:** a third window on the laptop; output 2's settings present.

*(check 111)*

#### D13. Unplug the projector mid-run — last

**Needs:** glass, projector; D1's config. Last, since it may leave a
window somewhere odd.

**Do:** both outputs running, pull the projector's cable; wait ten
seconds; plug it back.

**Right if:** the glass never stops or freezes; the app keeps running;
the control window names output 2 if its picture failed ("output 2
(projector): its picture failed — …" or "… no picture for 2 s — …");
after replugging the projector shows the picture again (or say what it
does — it may need ⌘R). Nobody knows yet what macOS does with a
fullscreen window whose screen disappears: note it.

**Wrong if:** the app dies; the glass freezes; a projector window ends
up over the laptop's controls.

*(check 112)*

## (e) A mouse

#### E1. Drag an effect with a mouse

**Needs:** a mouse. The trackpad version is L18.

**Do:** repeat L18 with the mouse.

**Right if:** the same as L18.

*(check 94)*

---

## What a person has to judge

These are opinions, not pass or fail. Each has a sensible default; say
what you want changed.

- **Knob smoothing at 80 ms** — does a knob feel late or right? Try 50
  and 200 ms. (A17, B27; checks 78, 79)
- **The names of the six dream-layer buttons** — grain, swirl, blot, 3b,
  4c, 4e were guessed. (L23; check 95)
- **Which hand styles to keep** — HANDS, JOINTS, PALMS, CAGE, MARIONETTE.
  (D9; check 109)
- **The dream's look** — save two or three dream presets you like as
  candidates to ship; and whether "speed" is the speed you meant. (L22,
  L24, C4; checks 9, 96)
- **The default hand feel** — Steadiness, Response, Catch, Return;
  saved as `factory`. (B5; check 16)

Smaller calls along the way: the Ghost mirror setting for the glass (D8;
108); `hands-orbit`'s directions and zoom (B18; 80); whether faces'
effects read from the audience (D10; 98); whether amber pads can be told
from green on the real desk (A15; 82); whether a Learn should add rather
than move a row (B17; 77); whether a second pinch should glide (B11; 23);
the click-a-control dimming and its 20 seconds (A16; 70); whether a
pause mid-drag should be one undo step or two (L31; 48); HEX with ORBIT
overlapping (L28; 97); the bottom of the instances knob being nothing
(A18; 62); the dimmed sliders of an idle effect (L14; 60); readable desk
labels and the `◌` mark from a distance (L37, B4; 69, 73); the 11-pixel
page shift (L3; 81); the filter's hidden new route (L38; 71).

## Unclear in the source

Places where the check text did not say exactly what to do; the entries
above follow the most likely reading, flagged here.

- **L10 (check 33):** written for the first launch of a build from late
  September; whether your home folder still needs that conversion is not
  known.
- **L6 (check 3):** "plug in or switch on another sound input" — which second sound input
  is not said; any will do.

## Glossary

**4D depth** — how strongly the four-dimensional shape is projected into
three dimensions; a VIEW page setting.

**ANALYZER page** — the page showing the sound split into frequency
*bands*, with each band's settings.

**APC40** — the Akai APC40 (first model), a USB MIDI control desk with
pads, knobs and faders; the app's main hardware controller.

**APC40 buttons** — TAP TEMPO (tap the beat), NUDGE − / + (shift the
beat slightly), METRONOME (marks the "one"), QUANT (next preset), OVERDUB
(Home), DETAIL (key legend), SHIFT (the second layer), DEVICE ON/OFF
(the big desk drawing), MASTER (overlay mode), STOP ALL (reset the
scene). The labels printed on the desk are the maker's; these are the
jobs the app gives them.

**AUDIO page** — the page for the sound input (microphone or music file)
and its master levels.

**Axis (hand)** — one measured movement of a hand: side to side (x),
height (y), reach (z), roll, tilt (pitch) and turn (yaw). Twelve for two
hands.

**Band** — one slice of the sound's frequency range (SUB, BASS…). Each
band produces a *lane*.

**Band scene** — a saved set of all the sound bands' settings, picked
from pad rows 2–3 with SHIFT latched.

**Bank / slot** — a show's list of 24 numbered places for presets: slots
1–8 are F1–F8 and pad row 1, slots 9–24 are pad rows 4–5 and the small
numbered buttons on the PRESETS page.

**Bindings file** — `bindings.json` in the home folder: the control
mapping that belongs to the setup rather than to any preset (keys, the
desk's fixed buttons, faders).

**Bitmap** — a picture file shown inside the faces.

**BITMAP page** — the page for loading a picture to show inside the
faces.

**Box view** — the HANDS page's drawing of the camera's view, with a dot
for each palm.

**BPM** — beats per minute, the tempo.

**Cage, joints, marionette, palms** — ghost-hand *styles*; see D9.

**CAMERA page** — the virtual camera's settings (zoom, yaw, pitch).

**Catch** — how quickly a value glides onto a hand that has just come
back into the box, instead of jumping.

**Cheat sheet** — the key legend in the control window, shown and hidden
with `/`.

**Chip** — a small clickable label, such as one effect on the FX page.

**Click-through** — an OUTPUT page switch that lets mouse clicks pass
through the render window to whatever is behind it.

**Clip-stop row** — the row of eight buttons under the APC40's pad grid;
holding it saves the current look as a new preset.

**Control window** — the window with the pages and settings, as opposed
to the render window.

**Crossfader** — the APC40's horizontal slider at the bottom right; it is
the *master dimmer*.

**Cue knob** — the single knob in the APC40's master column; here it
steps through the 25 shapes.

**Cut-through** — a VIEW page switch; it only matters in *overlay* mode,
where it lets the desktop show through overlapping faces.

**DAW** — music software such as FL Studio.

**Dead zone** — a small range around the middle of a hand axis that
counts as no movement.

**Desk** — the APC40. "The on-screen desk" is its drawing in the control
window's bottom-left corner.

**DESK section** — the part of the ROUTING page listing which desk
control does what in the loaded preset.

**Desktop / screentop mode** — how the hand camera is mounted: face-up
on a table (desktop, the usual) or on top of a screen facing the
performer (screentop).

**Device knobs** — the eight lower-right knobs on the APC40 (D1–D8).

**Dirty dot / unsaved dot** — the red disc that shows the loaded preset
has changes not yet saved.

**Dream (the)** — a neural-network effect that "dreams" patterns into
the trail behind the shape; it needs the *dream worker*.

**Dream worker** — the background process that computes the dream; the
LOOKBACK page's status names its device when it runs.

**Drive** — how strongly a sound band pushes what it moves.

**Echoes** — the fading copies of earlier frames that trail behind the
moving shape.

**Effect chain / stack** — the list of picture effects (kaleidoscope,
plasma, hue cycle…) applied in order; managed on the FX page.

**FACES page** — the page for the faces' pattern and colours.

**Factory** — shipped with the app, as opposed to saved by you (shown dim
in the preset list; yours are white).

**FL Studio** — music software (a DAW) that the app can exchange MIDI
with.

**Footer** — the message line at the bottom of the control window.

**Frame rate (FPS)** — pictures drawn per second; shown in the footer.

**FX page** — the page for the picture effects.

**Gate** — a condition on a route, such as "only while pinching".

**Ghost hands** — drawn copies of the performer's hands in the picture,
switched on on the HANDS page.

**Ghost mirror** — flips the ghost hands left to right, for viewing in
the glass (HANDS page, **Mirror** in the ghost's **more ▸**).

**Glass (the) / Pepper's Ghost** — the stage rig: a screen reflected in
angled glass so the picture seems to float in the air. Any see-through
or grey ground spoils the illusion, hence the many "solid black" checks.

**Glyph** — the short code naming each desk control: K1–K8 track knobs,
D1–D8 device knobs, S1–S8 track faders, X the crossfader, G row·column
the pad grid (G6 is the clip-stop row), B-numbers the single buttons
(B11 OVERDUB, B20 TAP TEMPO…).

**Ground** — the empty background of the picture. The OUTPUT page's
Ground setting is how see-through it is in overlay mode.

**Guide and tethers** — the guide is a gauge drawn beside or on a ghost
hand showing each axis as a ball or arc; tethers are lines from the
routed axes to labels naming what they drive.

**Hand camera / Leap** — the Ultraleap Leap Motion Controller 2, a small
USB camera that tracks hands above it.

**Hand presets** — `hands-play`, `hands-pinch`, `hands-fx`,
`hands-orbit` and `lfo-breathe`: factory presets for trying the hands
and the LFO, found in the preset list (on no F-key).

**HANDS page** — the page for hand tracking: the box view, the feel
settings, calibration and the ghost hands.

**Home** — loading the preset the show "starts on" (fn+← or OVERDUB).

**Home folder** — `~/Hyperspace`, where the app keeps your config,
presets, shows, mapping file and logs; another folder can be used with
`HYPERSPACE_HOME`. Written `<home>` in this guide.

**Hot reload** — the app picking up a saved code or effect file while it
runs.

**House mood** — one of the factory presets of the house show.

**IAC bus** — the Mac's built-in virtual MIDI cable (Audio MIDI Setup →
IAC Driver), used to connect the app to FL Studio with no hardware.

**Instances** — how many copies of the shape are drawn (0 is none).

**Interaction box** — the region above the hand camera set by
calibration; a hand outside it counts as absent.

**Invariant** — a desk control whose job is fixed by the setup and is
the same on every preset and both layers (faders, OVERDUB, the clip-stop
row, the bank pads, TAP TEMPO); it cannot be learned.

**Lane** — a moving value that can drive a setting: a sound band
(written `lane:0` for the first), an LFO (`lfo:0`), a hand axis (`hand R
y`, "R height"), or an outside source such as FL Studio (`ext:0`).

**Layer (preset / global)** — the desk has two layers: normally its
knobs do the loaded preset's jobs; with SHIFT latched (the global layer)
they do the setup's jobs (band settings, hand feel, BPM).

**Learn / Unbind** — Learn assigns a desk control (**Learn desk**) or a
hand axis (**Learn hand ▸ left / right**) to a setting by moving it;
Unbind removes what drives a setting. Both are on a setting's
right-click menu.

**Learn depth** — how strongly the next tilt learned with Learn hand
moves its setting; on the HANDS page.

**LFO** — "low-frequency oscillator": a slow repeating wave, synced to
the tempo, that can move a setting (for example make brightness
"breathe"). The LFO page shows four.

**Look-back** — the LOOKBACK page's own switch, which turns the echoes
and the dream on.

**LOOKBACK page** — the page for the echoes and the dream (sections
ECHOES, DREAM, BOTH).

**Macro** — one knob that moves several settings at once, each over its
own range.

**Master dimmer (master dim)** — the overall brightness of everything
shown, set by the crossfader; the first row of the OUTPUT page.

**MIDI** — the standard way music hardware and software send control
messages.

**Modulatable** — able to be moved by a lane; "not modulatable" settings
can be set but not performed.

**Output** — a screen the picture is drawn on (the glass, the
projector); each can show different layers and has its own dim.

**OUTPUT page** — the page for screens, fullscreen, the master dimmer and
each output's switches.

**Overlay** — a mode where the render window floats see-through over the
desktop; only possible when the config has `[output] overlay = true`.

**Pad** — one of the 40 square buttons in the APC40's grid. Pad row 1
loads presets 1–8; rows 2–3 with SHIFT pick band scenes; rows 4–5 load
presets 9–24.

**Party show** — the factory show the app opens with: F1 TUMBLE, F2
FACES, F3 FIELD, F4 WAKE, F5 TRIP, F6 ACID, F7 MANDALA, F8 NOITA, slot 9
TRACER. The **house show** is another factory show (F1 BIG BLUE WAVE).

**Pattern** — the texture drawn on the faces (FLAT is plain); chosen on
the FACES page.

**Pickup** — a fader whose value moved elsewhere does nothing until you
move it past the current value, so the picture never jumps.

**Pinch switch** — a switch that closes when thumb and a finger touch.

**Preset** — a saved look: every performance setting, its routes and
what the desk's knobs do.

**PRESETS page** — the page for shows, presets, the bank and "starts on".

**Projector** — here, any second screen.

**Refresh rate** — how many times a second a screen redraws (60 or 120
Hz); System Settings → Displays.

**Render window** — the window that shows the picture.

**Rest / hold** — what a hand axis does when the hand leaves: go back to
rest, or hold its last value (hold only affects what is sent to outside
music software; the picture always returns).

**Ring** — the circle of lights around an APC40 knob, showing its value.

**Rotation planes (XY, XZ, YZ, XW…)** — the four-dimensional shape spins
in six planes, each with its own rate on the VIEW page.

**Route / routing** — a connection from a lane to a setting: **push**
moves the setting up and down around its own value; **positions** sets
it directly from the lane. The ROUTING page lists them all.

**ROUTING page** — the page listing every route, what the desk's
controls do on the loaded preset (DESK section), the macros (MACROS) and
the setup's own controls (SESSION).

**Scene buttons** — the column of buttons right of the APC40's pad grid;
here they switch points, lines, faces and rotation.

**Session** — the setup's own controls and settings, kept in the
bindings file and config rather than in a preset.

**Shape** — the four-dimensional object being drawn; there are 25.

**SHIFT layer** — the desk's second layer, latched by pressing SHIFT once
(its light stays on); see *Layer*.

**Show (project file)** — a file in `<home>/projects/` holding a bank of
presets and the one it starts on.

**Stall log** — `<home>/stall.log`, where the app writes what it was
doing when it froze or hit a drawing error.

**Starts on** — the preset a show opens with, also what Home loads.

**Stderr** — what the app prints in the terminal it was launched from.

**Steadiness, Response, Return** — hand feel settings on the HANDS page:
steadiness smooths jitter, response sets how quickly a value follows the
hand, return how quickly it goes back when the hand leaves (see also
*Catch*).

**Synthetic tape** — a recording of made-up hand movements, played in
place of the hand camera (`tools/hands_tape.py synth`).

**SYSTEM page** — the page for notes, errors, the MIDI and library
status, and app-wide settings.

**Tape (hand recording)** — a file of recorded hand movements that can
be played back instead of the hand camera; a *synthetic tape* is made
up, a real one is recorded at the rig (D8).

**Tearing** — a horizontal break across the picture where its top and
bottom come from different frames.

**Through effects** — an output switch: on, the ghost hands are bent by
the effects with the shape; off, they are drawn clean on top.

**Track faders** — the eight vertical faders along the APC40's bottom
(S1–S8); here they set the sound bands' drive.

**Track knobs** — the eight upper-right knobs on the APC40 (K1–K8).

**Track-select buttons** — the row of eight buttons just under the
APC40's clip-stop row; here they choose which sound band the device
knobs edit (with SHIFT latched).

**Trash** — `<home>/trash/`, where replaced or deleted presets and shows
are kept; viewable from the preset list.

**Undo step** — one action that ⌘Z takes back as a whole.

**Unmapped** — a desk control with no job on the loaded preset; its
light is off and it does nothing.

**VIEW page** — the page for the shape's look: brightness, speed,
points, lines, faces, instances, rotation rates.

**Weights** — the dream's neural-network data files.
