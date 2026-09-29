# party-tracer — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The preset's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L pitch | `rot.phase.YZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L yaw | `rot.phase.XZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L y | `view.speed` | push +0.4 | 0.600 | 0.600 | 1.04 | 1.82 | 3.17 | 4.00 | 0.600 | 0.600 |
| R y | `dream.echo_mix` | push +0.3 | echo 0.70 | echo 0.70 | echo 0.77 | echo 0.85 | echo 0.92 | echo 1.00 | echo 0.70 | echo 0.70 |
| R z | `dream.fade` | push -0.3 | halves in 0.76 s | halves in 1.94 s | halves in 1.19 s | halves in 0.76 s | halves in 0.49 s | halves in 0.30 s | halves in 0.76 s | halves in 0.76 s |
| R roll | `dream.occlude` | push +0.6 | occlude 0.30 | occlude 0.00 | occlude 0.16 | occlude 0.30 | occlude 0.44 | occlude 0.60 | occlude 0.30 | occlude 0.30 |
| R pitch | `dream.contrast` | push +0.3 | ^1.00 | ^0.62 | ^0.82 | ^1.00 | ^1.18 | ^1.38 | ^1.00 | ^1.00 |
