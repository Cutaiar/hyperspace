# party-faces — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The scene's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L pitch | `rot.phase.YZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L yaw | `rot.phase.XZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L y | `view.bright` | push +0.14 | 2.50× | 2.50× | 2.82× | 3.19× | 3.60× | 4.00× | 2.50× | 2.50× |
| R y | `view.pattern_mix` | push +0.6 | mix 0.50 | mix 0.50 | mix 0.65 | mix 0.80 | mix 0.95 | mix 1.00 | mix 0.50 | mix 0.50 |
| R z | `camera.zoom` | push -0.3 | 1.10× | 3.00× | 1.78× | 1.10× | 0.68× | 0.40× | 1.10× | 1.10× |
| R roll | `pattern.mod.2` | push +0.7 | 1.00 | 0.09 | 0.56 | 1.00 | 1.44 | 1.91 | 1.00 | 1.00 |
| R pitch | `camera.pitch` | push +0.5 | 0° | -44° | -21° | 0° | 21° | 44° | -0° | 0° |
