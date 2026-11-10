# Kinetic presets

Six whole-frame presets (`hyperspace.loadable/11`) played with the body:
the Ultraleap hands first, a gamepad or Joy-Con second, and two setups of
the hand rig (plan 60, the grip) for the two presets built on it. They are
not part of the app (nothing ships with it). Copy the ones you want into
the library and they appear in the list and on the grip's strip:

```bash
cp presets/kinetic/*.json ~/Hyperspace/loadable/
```

```bash
mkdir -p ~/Hyperspace/patches/grip && cp presets/kinetic/grip/*.json ~/Hyperspace/patches/grip/
```

Each has the default APC40 patch layer (no `desk` key) and the six audio
lanes on the six rotation planes, as the corpus presets do. The ghost hands
are on at 35%, so a player sees where their hands are. A stick with no
route keeps its usual job: the left orbits, the right zooms.

`tests/test_kinetic_presets.py` opens each through the library's own load
and fails on any note or dropped route.

## The grip is the show's, not a preset's

The grip's settings (`grip.*`) belong to the meta controller and are saved
in the show, so no preset can turn the grip on or set its coupling.
`kinetic-clay` and `kinetic-comet` are looks made to be held and thrown;
the physics comes from a grip setup, loaded from the grip's strip on the
HANDS page:

| Setup | For | What it is |
| --- | --- | --- |
| `held` | `kinetic-clay` | Coupling 0.7, drag 1.2, even inertia. Firm with a little give; a throw dies away in a second or two. |
| `gyro` | `kinetic-comet` | Coupling 0.4, drag 0.9, shaped inertia and the skater on. A loose spring: it lags, overshoots and flies on. |

With the grip on, a closed fist of the holding hand takes the shape in
every preset, and the other fist shapes its inertia. The other four presets
here use no fist, so nothing in them fights it. Reset world puts a shape
that was thrown away back home.

## The gestures

### kinetic-clay: hold it

A 24-cell in your hand. Needs the grip on (the `held` setup).

| Do this | It does this |
| --- | --- |
| Close the right fist | The shape is in your hand: it moves and turns as the hand does. Open the hand to let go. |
| Flick the wrist as you let go | Throws it; it coasts and settles |
| Raise the left hand | Pushes it through 4D (the inner cells swell) |
| Roll the left hand | Sets the spin speed |
| Move the right hand fast | Leaves a wake behind the shape |

With the grip off, the fist does nothing here; the left hand and the wake
still play.

### kinetic-comet: throw it

A trefoil knot in a feedback loop, so wherever it goes it paints a tail of
turning colour. Needs the grip on (the `gyro` setup).

| Do this | It does this |
| --- | --- |
| Close the right fist and swing | The knot follows on a loose spring, lagging and overshooting |
| Let go mid-swing | It flies on, tumbling, and coasts to a stop; a hard throw stops at the edge of the picture |
| Close the left fist too, then pull the hands together | Spins it up; apart slows it. Open the left fist and that inertia stays in the knot, so it wobbles as it turns. |
| Raise the left hand | A longer tail |
| Move the right hand fast | The knot glows |

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
as the tables above say. For the two grip presets the world and the grip
were stepped as `app._step_world` does, with a synthetic grab, swing and
release: the shape followed the fist, flew on when let go and stayed in the
picture.

Not checked: anything on a real sensor. Precession and the skater's spin-up
were not judged by eye, only that shaping changed the inertia. The grip
setups were loaded through the library with the grip's params registered,
not from the HANDS page's strip in the running app. The depths were set by eye from
rendered frames, not by hand, so expect to trim them on the rig. The
`motion:` routes of `kinetic-wand` and the two `axis:RT` routes were only
checked to load, since nothing here simulates a pad's motion sensors. The
webcam was a test picture.
