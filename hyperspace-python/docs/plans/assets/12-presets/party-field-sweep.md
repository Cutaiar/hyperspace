# party-field — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The scene's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| R y | `view.instances` | push +0.6 | 9 instance(s) | 9 instance(s) | 24 instance(s) | 39 instance(s) | 54 instance(s) | 68 instance(s) | 9 instance(s) | 9 instance(s) |
| R y | `camera.zoom` | push -0.15 | 0.42× | 0.42× | 0.33× | 0.25× | 0.20× | 0.15× | 0.42× | 0.42× |
| R y | `view.bright` | push +0.1 | 1.60× | 1.60× | 1.74× | 1.90× | 2.07× | 2.26× | 1.60× | 1.60× |
| R roll | `rot.phase.XW` | push +0.25 | 0° | -45° | -21° | +0° | +22° | +45° | +0° | +0° |
| R yaw | `rot.phase.ZW` | push +0.25 | 0° | -45° | -21° | +0° | +22° | +45° | +0° | +0° |
| L x | `camera.pan.x` | push +0.1 | +0 px | -400 px | -192 px | +0 px | +192 px | +400 px | -0 px | +0 px |
| L z | `camera.pan.y` | push +0.1 | +0 px | -400 px | -192 px | +0 px | +192 px | +400 px | -0 px | +0 px |
| L y | `view.inst_amp` | push +0.5 | amp 0.15 | amp 0.15 | amp 0.28 | amp 0.40 | amp 0.53 | amp 0.65 | amp 0.15 | amp 0.15 |
