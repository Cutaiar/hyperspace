# Hyperspace (Raycast)

[Raycast](https://raycast.com) script commands for starting the app, so a show
begins from the launcher instead of a terminal.

`hyperspace.sh` is the whole thing: it runs `uv run hyperspace` in
[`hyperspace-python/`](../hyperspace-python/), detached, and hands the window
back to you.

## Install

Raycast only reads directories a person has added by hand, once:

> Raycast → Settings → Extensions → Script Commands → **Add Script Directory**

Point it at this directory and the command appears in root search as
"Hyperspace" — give it an alias (`hs`) or a hotkey there. Pointing Raycast at
the repo means a `git pull` updates the command; if you would rather keep your
Raycast scripts in one place of your own, symlink the script into that
directory instead (the script resolves symlinks to find the app).

## The command

A **Mode** dropdown, optional:

- *Rig (projector)* — the default, plain `uv run hyperspace`: fullscreen render
  output on the projector, controls on the laptop.
- *Laptop (one screen)* — `uv run hyperspace --laptop`: the render output stays
  a plain window.

If the app is already running the command focuses that window instead of
starting a second process, so an accidental second invocation costs nothing.
macOS asks Raycast for Accessibility permission the first time that happens;
denied, the command still refuses to launch a duplicate, it just cannot raise
the window.

## Notes

- Raycast runs scripts with a bare `PATH`, so `uv` is named in full
  (`/opt/homebrew/bin/uv`). A different install location goes in `UV`.
- The app is launched with `nohup … &` and disowned. Without that, Raycast
  waits on the app's whole run and reports it as a command that never ends.
- Output goes to `~/Hyperspace/launch.log`, next to the app's other files, so a
  start that fails before any window opens is still readable. The render
  stalls the app itself records are a different file,
  [`~/Hyperspace/stall.log`](../hyperspace-python/README.md).
