# party-tumble — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The scene's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L pitch | `rot.phase.YZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L yaw | `rot.phase.XZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L y | `master.gain` | push +0.375 | 1.00× | 1.00× | 1.68× | 2.83× | 4.76× | 8.00× | 1.00× | 1.00× |
| R y | `view.speed` | push +0.45 | 0.300 | 0.300 | 0.560 | 1.04 | 1.95 | 3.64 | 0.300 | 0.300 |
| R z | `view.depth4` | push +0.35 | 2.60 | 1.61 | 2.01 | 2.60 | 3.55 | 5.22 | 2.60 | 2.60 |
| R roll | `rot.phase.XW` | push +0.25 | 0° | -45° | -21° | +0° | +22° | +45° | +0° | +0° |
| R yaw | `rot.phase.ZW` | push +0.25 | 0° | -45° | -21° | +0° | +22° | +45° | +0° | +0° |
