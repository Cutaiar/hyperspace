# party-mandala — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The preset's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L pitch | `rot.phase.YZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L yaw | `rot.phase.XZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| R y | `fx.fractals.amount` | push +0.4 | 1.20 | 1.20 | 1.50 | 1.80 | 2.10 | 2.40 | 1.20 | 1.20 |
| R z | `fx.kaleido.zoom` | push -0.5 | 1.00 | 2.00 | 1.39 | 1.00 | 0.72 | 0.50 | 1.00 | 1.00 |
| R roll | `fx.kaleido.swirl` | position | 0.00 | -2.00 | -0.96 | 0.00 | 0.96 | 2.00 | 0.00 | 0.00 |
| R pitch | `fx.plasma.level` | push +0.4 | 0.00 | 0.00 | 0.00 | 0.00 | 0.10 | 0.20 | 0.00 | 0.00 |
| R yaw | `fx.fractals.cells` | push -0.4 | 20.0 | 34.4 | 25.9 | 20.0 | 15.4 | 11.6 | 20.0 | 20.0 |
| L y | `fx.glimmer.amount` | push +0.5 | 1.00 | 1.00 | 1.38 | 1.75 | 2.12 | 2.50 | 1.00 | 1.00 |
