# Kinetic presets

Five whole-frame presets (`hyperspace.loadable/11`) played with the body:
the Ultraleap hands first, a gamepad or Joy-Con second. They are not part
of the app (nothing ships with it). Copy the ones you want into the
library's `loadable/` folder and they appear in the list:

```bash
cp presets/kinetic/*.json ~/Hyperspace/loadable/
```

Each has the default APC40 patch layer (no `desk` key) and the six audio
lanes on the six rotation planes, as the corpus presets do. The ghost hands
are on at 35%, so a player sees where their hands are. A stick with no
route keeps its usual job: the left orbits, the right zooms.

`tests/test_kinetic_presets.py` opens each through the library's own load
and fails on any note or dropped route.

## The gestures

### kinetic-clay: grab it

A 24-cell you handle like an object.

| Do this | It does this |
| --- | --- |
| Close the right fist and turn the wrist | The shape turns with the hand and stays where you leave it. Open the hand to let go, like lifting a mouse. |
| Pull two hands apart | It gets bigger |
| Raise the left hand | Pushes it through 4D (the inner cells swell) |
| Close the left fist and twist, like a throttle | Sets the spin speed, and it stays |
| Move the right hand fast | Leaves a wake behind the shape |

### kinetic-tunnel: reach in

A tesseract fed back on itself through a mirror, a hue turn and a fade.

| Do this | It does this |
| --- | --- |
| Pull two hands apart | The tunnel draws out longer. Together again, it closes. |
| Turn the hands against each other, like a steering wheel | The tunnel spirals that way |
| Raise or lower the right hand | Drives forward or back through it |
| Pinch left thumb and index, then move that hand up | Adds mirrors (2 to 16) |
| Right trigger on a pad | Floods the tunnel with colour |

### kinetic-looking-glass: the webcam

The webcam is the backdrop, folded in a kaleidoscope, and it is on every
face of the tesseract.

| Do this | It does this |
| --- | --- |
| Raise the right hand | More mirrors |
| Roll the right hand | Swirls them |
| Pull two hands apart | Zooms in |
| Raise the left hand | Turns the webcam into neon line art |
| Roll the left hand | 4D depth of the tesseract |

Channel A's bin names `camera:FaceTime HD Camera`. If the Mac's camera has
another name, pick it on the MEDIA page and save. The camera needs its
`[[devices]]` entry in `config.toml` (`role = "camera"`, `kind = "camera"`).
With no camera the backdrop is empty and the tesseract's faces are plain.

### kinetic-wand: a Joy-Con or DualSense as a wand

Twenty-seven 16-cells in a cubic field.

| Do this | It does this |
| --- | --- |
| Tilt the controller | The whole field tilts with it, like a tray |
| Wave it about | The field sparkles |
| Shake it hard | A burst |
| Right trigger | Dives into the field |
| Pull two hands apart | Spreads the field out |
| Raise the right hand | The field swarms |
| Raise the left hand | The swarm speeds up |

The tilt, wave and shake need a pad with motion sensors (a DualSense, an
Edge or a Joy-Con); an Xbox pad has the trigger only. A Joy-Con's totem,
when it is on, drives the camera itself.

### kinetic-finger-drums: play it with your fingertips

A 24-cell with four effects at rest. Each right-hand pinch is a drum; hold
the pinch and it sustains, let go and it rings out over half a second.

| Do this | It does this |
| --- | --- |
| Right thumb to index | Radial burst |
| Right thumb to middle | Splits the colours |
| Right thumb to ring | Doubles the picture |
| Right thumb to pinky | Floods it magenta and green |
| Left thumb to index | Punches the camera in |
| Flick the left hand | Flash |
| Raise the left hand | Spin speed |

## What was checked, and what was not

Checked in a cloud session, with no hardware: each file opens with no note
through the real load; with synthetic hands fed through the real tracking
chain and router, every hand route moved its target and the picture changed
as the tables above say.

Not checked: anything on a real sensor. The depths were set by eye from
rendered frames, not by hand, so expect to trim them on the rig. The
`motion:` routes of `kinetic-wand` and the two `axis:RT` routes were only
checked to load, since nothing here simulates a pad's motion sensors. The
webcam was a test picture.
