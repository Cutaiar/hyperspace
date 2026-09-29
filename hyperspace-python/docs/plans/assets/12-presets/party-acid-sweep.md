# party-acid — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The preset's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L pitch | `rot.phase.YZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| L yaw | `rot.phase.XZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | +0° | +0° |
| R y | `fx.acid.bend` | push +0.6 | 0.04 | 0.04 | 0.10 | 0.16 | 0.22 | 0.28 | 0.04 | 0.04 |
| R z | `fx.acid.reach` | push -0.4 | 10.0 | 20.9 | 14.2 | 10.0 | 7.0 | 4.8 | 10.0 | 10.0 |
| R roll | `fx.acid.twist` | push +0.5 | 0.90 | 0.11 | 0.52 | 0.90 | 1.28 | 1.69 | 0.90 | 0.90 |
| R pitch | `fx.deconverge.amount` | push +0.6 | 5.00 | 0.20 | 2.70 | 5.00 | 7.30 | 9.80 | 5.00 | 5.00 |
| R yaw | `fx.huecycle.spread` | push +0.4 | 1.20 | 0.40 | 0.82 | 1.20 | 1.58 | 2.00 | 1.20 | 1.20 |
| L y | `fx.wobble.amount` | push +0.5 | 0.004 | 0.004 | 0.010 | 0.017 | 0.023 | 0.029 | 0.004 | 0.004 |
