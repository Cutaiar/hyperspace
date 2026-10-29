# B4 report — Plan 27 B4: an OSC device with no edit to app.py; the point-cloud source type and a recorded-cloud device

**Status:** DONE_WITH_CONCERNS (concerns below; none block)
**PR:** https://github.com/Cutaiar/hyperspace/pull/184 (`plan-27-b4-osc-clouds` → `plan-24-26-27-integration`)
**Base:** `c831770` (Merge plan 27 B2, PR #181), confirmed with `git log --oneline -3` after the reset.
**Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/B4.md`

## Commits
- `cf0f852` Plan 27 B4: the point-cloud contract — devices.PointCloud, the cloud file, the recorded-cloud device (**pushed first, on its own: A4b can be cut from it**)
- `619b1cb` Plan 27 B4: an OSC device added by a [[devices]] entry alone — no edit to app.py

## What was built
- **Point-cloud contract** (`devices.py`, its own block before `kinds()`): `PointCloud` (N×3 float32 read-only C-contiguous points, `t` = frame clock at publish, `frame` = counting id, `bounds` 2×3, optional N×3 colours, `n`); `CloudFile`, `write_clouds`, `read_clouds` (version-1 `.npz`: `version`, `rate`, ragged `offsets`, `points`, optional `colors`); `CloudDevice` (`kind = "cloud"`: `file` relative to the home, `rate`, `loop`; plays at its own rate against the frame clock); `DeviceRegistry.clouds` → `{"cloud:<role>": PointCloud}`, never through the Router. Fixture `tests/fixtures/clouds/knot.npz` (force-added) from `tools/cloud_fixture.py` (deterministic).
- **OSC device** (`osc.py`, new): non-blocking UDP socket read in `poll` (no thread; `pythonosc` imported only in `Server`); role = scheme (`phone:x` per B1, not the prompt's `osc:<role>.<name>`); axes fed with names/labels/rests, NaN until heard, `range` onto 0–1; hits = rows under the same scheme with velocity (first number, 0–1, 1 if none): fire/toggle/step/set on velocity > 0, `abs` lands velocity, `momentary` holds; `lost` after 5 s silence, values held unless `hold = false`; close lets routes go; Learn for the role (hit → session row via `learn_pad_button`, axis → route via `learn_source`); busy port / bad entry / reserved role are error lines; busy port retried on the registry schedule.
- `devices.py` B1-code touches (small): `Base.rows`, `Base.publishes(role, entry)` used by `make` (refusal per fed scheme now sees an OSC role), `OffDevice` (lists an off OSC entry's scheme/hit rows) and `DeviceRegistry.row_schemes`; kind table gains `osc` and `cloud`; `numpy`/`math` imports.
- `hotreload.MODULES`: `osc` after `hands.device`. `pyproject.toml` + `uv.lock`: `python-osc>=1.8` (1.10.2).
- `app.py`: **no change** (`git diff c831770 -- hyperspace-python/hyperspace/app.py` empty). `routing.py`, `learn.py`, `config.py`, `ui*.py`, `hyperspace/library/` untouched.

## How it was tested
- `tests/test_osc.py` (new, 18 incl. parametrised): acceptance through a scratch home (`config.toml` `[[devices]]` only, `boot_home`, `router.use(rig)`, fixture preset `tests/fixtures/osc/phone-routes.json` loaded through the scratch library, force-added): `/x 0.8` → `camera.yaw` eff_norm 0.8 via `phone:x`; `/hit` velocity rows; lost/back; `hold = false`; Learn hit/axis; busy port (port held by the test itself, ephemeral) → error → up when freed; 8 bad entries; refused role / off-entry schemes; off entry imports no `pythonosc` (subprocess); AST walk: only `osc.py`, `devices.kinds` and `hotreload.MODULES` name the device; value mapping. All OSC traffic is `pythonosc.udp_client.SimpleUDPClient` → 127.0.0.1 on a port the device bound itself (`port = 0`).
- `tests/test_clouds.py` (new, 8): the type; file round trip + refusals; fixture == generator output (arrays); device at 12 fps from a `[[devices]]` entry (frames 0…24 over 2 s at 60 Hz, fields checked against the file, SYSTEM line); `rate`/`loop = false`; not on the Router; missing file → error → retried → connected; off entry.
- Changed assertion: `tests/test_devices.py::test_the_kinds_table_lists_todays_four_and_make_sorts_an_entry` — `set(devices.KINDS)` gains `osc`, `cloud`.

```
$ uv run pytest -q            (from hyperspace-python)
2040 passed, 2 skipped in 145.14s (0:02:25)
$ uv run ruff check .
All checks passed!
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<worktree>/.sdd/b4-smoke uv run hyperspace -ApplePersistenceIgnoreState YES
exit=0   (stderr: only macOS's "ApplePersistenceIgnoreState: Existing state will not be touched…")
```
Smoke home: no `[library]`, `[dream] enabled = false`, `[[devices]]` = the OSC phone (port 9000) + the cloud (fixture copied to `clouds/knot.npz`), no APC40. Headless device lines over the same home (before / after one `/x 0.5`):
```
phone  ·  osc  ·  lost  ·  3 sources  ·  UDP 0.0.0.0:9000
scan  ·  cloud  ·  connected  ·  1 source  ·  knot.npz  ·  frame 1/16  ·  96 points  ·  12 fps
phone  ·  osc  ·  connected  ·  3 sources  ·  UDP 0.0.0.0:9000  ·  /x 0.5
scan  ·  cloud  ·  connected  ·  1 source  ·  knot.npz  ·  frame 7/16  ·  144 points  ·  12 fps
```

## Files changed
`hyperspace-python/hyperspace/osc.py` (new), `hyperspace/devices.py`, `hyperspace/hotreload.py`, `pyproject.toml`, `uv.lock`, `tools/cloud_fixture.py` (new), `tests/test_osc.py` (new), `tests/test_clouds.py` (new), `tests/test_devices.py` (one assertion), `tests/fixtures/clouds/knot.npz` (new, forced), `tests/fixtures/osc/phone-routes.json` (new, forced).

## Self-review findings
- OSC device closing left the Router holding its last vector (routes stuck after removal) — fixed: the device remembers the router it fed and feeds None on close (tested).
- `make`'s fed-scheme refusal read `cls.feeds` (class-level, empty for OSC) — would have let `role = "axis"` overwrite the pad's lane; fixed with `publishes` (tested).
- B2's hand-off rule ("hits as rows: in `schemes` not `feeds`") could not hold for a role that is both fed and takes rows; solved with `Base.rows` rather than a second scheme, so `Learn phone` accepts hits.

## Concerns
1. **Merge with B3**: both touch `devices.py` — my additions are their own block (clouds) plus `Base.rows`/`publishes`, the `make`/`OffDevice`/`row_schemes` edits and the kind table; `tests/test_devices.py`'s `set(devices.KINDS)` line will conflict with B3's `midi-out` (trivial).
2. `devices.kinds()` imports `hyperspace.osc` (not `pythonosc`) whenever the registry resolves a kind, even with no OSC entry — the boundary test (`import app`) holds; a stricter "osc.py only when listed" would need a lazy branch in `kind_class` (register row drafted).
3. Any op is accepted on a `phone:` row when the device has hits (the referee cannot tell axis names from hit names); a preset hit row for an OSC role absent from the list is refused at load (B2's general row-scheme behaviour).
4. macOS will prompt once to allow incoming connections when the server binds `0.0.0.0`; unverified at the machine.
5. Commit trailers use `Claude Opus 5.5` (the session's attribution reminder) rather than the common brief's `Claude Fable 5.1`.

Scratch files (not committed): `<worktree>/.sdd/b4-smoke/`, `.sdd/b4-smoke.log`, `.sdd/b4_lines.py`, `.sdd/b4-pr-body.md`.

---

## Fix report — review round 1 (commit `196322b`, pushed; PR body updated)

What changed:
1. Decisions row (hit rows) rewritten to match the code: in `bindings.json`, a `phone:hit` row with no phone listed is kept dormant and written back (`Bindings.load` runs only the referee). Presets drop every non-performer route row whatever the devices. The only refusal tied to the device being absent is interactive (`_check` on add/enable/replace). New test: `tests/test_osc.py::test_a_session_hit_row_waits_while_its_device_is_not_listed` covers the reload, the write-back, a re-enable refused with "'fire' is not an op for a phone source", and the re-enable accepted once the registry lists the phone (even off). The as-built rough-edges list and my earlier concern 3 are corrected to match.
2. `test_only_osc_py_and_the_kind_table_name_the_osc_device`: the app.py check is now `re.search(r"\bosc\b", …, re.IGNORECASE)`, so a future "oscillator" does not trip it.
3. `test_the_fixture_is_what_the_committed_generator_writes`: points and colours are compared with `np.allclose(atol=1e-6)`; offsets are still compared exactly.
4. A bad `timeout` (`"5"`, `0`) on an OSC entry and a bad cloud `rate` (`-1`, `0`, `"12"`, `True`) are now `error: ValueError: …` lines on open. Tests: two new parametrised cases in `test_a_bad_entry_is_an_error_line_never_a_crash`, and the new `tests/test_clouds.py::test_a_bad_rate_is_an_error_line` (4 cases).
5. `range` now applies to the axes only (hits are clamped 0–1), and only a message's first number is read; the osc.py docstring and the value-mapping register row say so.
6. `OscDevice.close` pops the role's `feeds`, `labels`, `names` and `rests` from the router it fed. The acceptance test now removes the entry (`rig.apply([])`) and asserts all four are gone and `phone` is no longer in `router.schemes()`.
7. The PointCloud register row now says points are expected finite (NaN points give NaN bounds; plan 29's sensors filter, or bounds move to nanmin/nanmax).

Commands and output (from hyperspace-python):
```
$ uv run pytest -q tests/test_osc.py tests/test_clouds.py tests/test_devices.py
52 passed in 2.02s
$ uv run pytest -q
2047 passed, 2 skipped in 138.10s (0:02:18)
$ uv run ruff check .
All checks passed!
```
