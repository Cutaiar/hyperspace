# party-wake — hand sweeps

Each cell is the target's value after the hand has held that position for 90 frames (1.5 s) through the real hand chain (default feel: dead zone 0.04 on the centred axes, return 0.5 s), then *out* is the value 90 frames after the hand left at u = 1, and *never* the value when that hand was never seen. The scene's base is the first column; a rotation phase is shown as the hand's offset from the base, since a live plane keeps turning underneath.

| hand axis | target | op | base | u=0 | u=¼ | u=½ | u=¾ | u=1 | out | never |
|---|---|---|---|---|---|---|---|---|---|---|
| L roll | `rot.phase.XY` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L pitch | `rot.phase.YZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L yaw | `rot.phase.XZ` | push +0.25 | 0° | -45° | -22° | +0° | +22° | +45° | -0° | +0° |
| L y | `view.speed` | push +0.4 | 0.350 | 0.350 | 0.609 | 1.06 | 1.85 | 3.22 | 0.350 | 0.350 |
| R y | `dream.echo_mix` | push +0.7 | echo 0.30 | echo 0.30 | echo 0.47 | echo 0.65 | echo 0.82 | echo 1.00 | echo 0.30 | echo 0.30 |
| R z | `dream.decay` | push -0.12 | 0.930 / frame | 0.990 / frame | 0.959 / frame | 0.930 / frame | 0.901 / frame | 0.870 / frame | 0.930 / frame | 0.930 / frame |
| R roll | `dream.hue` | position | +0° | -180° | -86° | +0° | +86° | -180° | -0° | +0° |
| R pitch | `dream.mix` | push +0.5 | dream 0.50 | dream 0.25 | dream 0.38 | dream 0.50 | dream 0.62 | dream 0.75 | dream 0.50 | dream 0.50 |
