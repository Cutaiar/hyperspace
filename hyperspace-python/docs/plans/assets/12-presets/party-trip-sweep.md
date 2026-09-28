# party-trip — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The scene's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| R y | `fx.zoomblur.amount` | push +0.8 | 0.10 | 0.10 | 0.30 | 0.50 | 0.70 | 0.90 | 0.10 | 0.10 |
| R z | `fx.kaleido.zoom` | push -0.5 | 1.00 | 2.00 | 1.39 | 1.00 | 0.72 | 0.50 | 1.00 | 1.00 |
| R roll | `fx.kaleido.swirl` | position | 0.00 | -2.00 | -0.96 | 0.00 | 0.96 | 2.00 | -0.00 | 0.00 |
| R yaw | `fx.huecycle.spread` | push +0.4 | 0.80 | 0.00 | 0.42 | 0.80 | 1.18 | 1.60 | 0.80 | 0.80 |
| R pitch | `fx.plasma.level` | push +0.4 | 0.20 | 0.00 | 0.10 | 0.20 | 0.30 | 0.40 | 0.20 | 0.20 |
| L y | `lfo.1.depth` | position | depth 0.00 | depth 0.00 | depth 0.25 | depth 0.50 | depth 0.75 | depth 1.00 | depth 0.00 | depth 0.00 |
| L x | `fx.zoomblur.cx` | push +0.8 | 0.00 | -0.80 | -0.38 | 0.00 | 0.38 | 0.80 | -0.00 | 0.00 |
| L z | `fx.zoomblur.cy` | push -0.8 | 0.00 | 0.80 | 0.38 | 0.00 | -0.38 | -0.80 | 0.00 | 0.00 |
