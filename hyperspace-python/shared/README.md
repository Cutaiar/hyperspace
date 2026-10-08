# Shared presets

Presets, shows and module presets that someone saved on their own machine
and committed here so everyone can pull them. Each folder mirrors a home
(`~/Hyperspace`): `presets/`, `projects/`, and one folder per module group.

## Take someone's

```
git pull
cd hyperspace-python
uv run python tools/shared_presets.py install shared/dan-2026-10-04 --dry-run   # see what it would do
uv run python tools/shared_presets.py install shared/dan-2026-10-04
```

It copies into your own home (`~/Hyperspace`, or `HYPERSPACE_HOME`) and
**never writes over a file**: a preset you already have under the same
name is kept and said so. A file that would shadow a factory one (a show
called `party`) is skipped unless you pass `--shadow`. The running app
picks the new presets up within a couple of seconds; they appear in the
PRESETS page's list.

## Share yours

```
cd hyperspace-python
uv run python tools/shared_presets.py export shared/<you>-<date>
git add shared/<you>-<date> && git commit
```

It reads your home and writes only that folder. Left out, because they
are your machine's: `config.toml`, `bindings.json`, `hands.json`, logs,
backups, the trash and the dream weights.

## What is here

| Folder | From | What |
|---|---|---|
| `dan-2026-10-04/` | Dan's rig, copied 2026-10-04 | The sixteen presets saved at the Oct 3–4 session (`3x3`, `civilization`, `crystal-drill`, `dyson-ring`, `flashlights`, `hand-game`, `hi-frek` and `hi-frek-variation-1`, `light-realm` and its variations `-1`, `-2`, `-3` and `-steady`, `lightning-mandala`, `manifold-burst`, `percussive-central-burst`) and `MIGRATED`; the shows `after-hamdi`, `mine` and `party` as they were (none of their banks names the new presets: load them from the list); the module presets `fx/wobbly-pinch` and `dream/loud`. Saved on main fa9b3a1. |
| `plan-22-macro-candidates/` | Plan 22 B5, generated | Four presets of macro configurations to audition, unjudged: `macro-performance` (eight knobs for a set), `macro-streams` (one knob per band and LFO), `macro-intensity` (one idea three ways), `macro-breakdown-drop` (one knob against a pair). What each macro is meant to do: `docs/plans/22-macro-candidates.md`. |

A preset here is a plain `hyperspace.preset/2` file: values, hand and
audio routes, the desk's preset layer and macros. The hand routes assume
a calibrated box; the desk rows assume an APC40 mk1.
