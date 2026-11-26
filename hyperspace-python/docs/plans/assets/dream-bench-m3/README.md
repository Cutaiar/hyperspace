# Dream bench G on the M3 Max

Date: 2026-11-25 (runs 23:37 to 00:13 local, into 2026-11-26).
Branch: `ccr-c1d722dd-uud8ns` at b4b24223. Tool: `tools/dream_bench/g_layers.py`.

Machine line (from every `.log`):

```
machine arm64 · system Darwin · macos 26.6 · python 3.14.4 · torch 2.14.0 · torchvision 0.29.0 · chip Apple M3 Max · memory 64 GB · device mps · weights /Users/dallman/Hyperspace/weights
```

## Machine state

- Power: AC power, battery 100% charged (`pmset -g batt`).
- Low Power Mode: off. `pmset -g` reports `powermode 2` (High Power); there is no `lowpowermode` key on this machine.
- Background load at the first check: the Docker Desktop VM (`com.apple.Virtualization`) at about 105% CPU and 32 GB, Docker Desktop's helper at about 15%, VS Code helpers at about 9%. Another session also saw `dolt sql-server` at about 133% and `bd` at about 92%.
- Before any timing, with the owner's approval: Docker Desktop was quit, and the Gas Town services (dolt sql-server, the gt daemon, and the opencode agents that call `bd`) were stopped and kept from restarting for the whole run. After that the busiest processes were kernel_task, WindowServer and Claude Code sessions, each about 5–12% CPU.
- Another benchmark (the frame spike recorder, which opens the Hyperspace app) ran from 23:34 to about 23:37, before these runs. The two sessions took turns, so nothing else was benchmarking during runs 1–3.
- Hyperspace app: closed for runs 1, 2 and 3 (checked before starting; no hyperspace process).

## Runs

| Run | Label | Started | Wall-clock | Exit | App open |
|---|---|---|---|---|---|
| 1 | sweep | 23:37:33 | 796 s (13 min 16 s) | 0 | no |
| 2 | forward | 23:50:49 | 143 s (2 min 23 s) | 0 | no |
| 3 | compile | 23:53:12 | 1199 s (19 min 59 s) | 0 | no |
| 4 | show | — | — | skipped | — |

Run 4 (show) was skipped: the owner wasn't available to open the app on a show patch, and there was no answer within 10 minutes, as the instructions allow.

No run crashed. No log has a warning, error, traceback or skipped row.

## Anything odd

- `pmset -g therm` after each run: no thermal warning, no performance warning, no CPU power status recorded. Fan speed was not read; it needs sudo.
- No slowdown over time: the GoogLeNet eager and fold fp32 rows that ran in both sweep (first) and compile (last) came out the same or slightly faster in compile (for example inception5b fold at 1920×1080: p50 60.59 ms in sweep, 58.60 ms in compile). The largest relative gap is on conv1, the cheapest layer: eager at 456×256 was p50 2.34 ms in sweep and 1.96 ms in compile.
