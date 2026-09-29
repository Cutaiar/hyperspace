# party-noita — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The preset's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L pitch | `rot.phase.YZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L yaw | `rot.phase.XZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| R y | `fx.warp.amount` | push +0.3 | 0.90 | 0.90 | 1.05 | 1.20 | 1.35 | 1.50 | 0.90 | 0.90 |
| R y | `fx.tripcolour.amount` | push +0.25 | 0.55 | 0.55 | 0.68 | 0.80 | 0.93 | 1.05 | 0.55 | 0.55 |
| R y | `fx.fractals.amount` | push +0.2 | 1.40 | 1.40 | 1.55 | 1.70 | 1.85 | 2.00 | 1.40 | 1.40 |
| R z | `fx.warp.scale` | push -0.4 | 3.00 | 6.00 | 4.18 | 3.00 | 2.15 | 1.50 | 3.00 | 3.00 |
| R roll | `fx.doublevision.amount` | push +0.6 | 4.00 | 0.40 | 2.27 | 4.00 | 5.72 | 7.60 | 4.00 | 4.00 |
| R pitch | `fx.tripcolour.pulse` | push +0.4 | 1.50 | 0.66 | 1.01 | 1.50 | 2.22 | 3.40 | 1.50 | 1.50 |
| L y | `fx.warp.drift` | push +0.4 | 1.00 | 1.00 | 1.80 | 2.60 | 3.40 | 4.20 | 1.00 | 1.00 |
