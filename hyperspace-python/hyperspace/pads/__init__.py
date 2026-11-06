"""Game controllers as one vocabulary (plan 42).

`gamepad.Pad` is what the rest of the app reads: buttons by name
(``pad:A``), the hat, six axes, and — on a pad that has them — the
touchpad and motion lanes (``touch:``, ``motion:``) and the outputs
(light bar, rumble, trigger resistance). This package is how a pad
gets there from whatever the hardware speaks, one piece per job:

  models.py    which controllers exist: a `Model` per kind of pad (its
               USB ids, what it has, what its buttons are called), and
               `matches` — what a `[[devices]]` entry's ``controller =``
               picks. A new controller is one `Model` and, if no road
               reads it yet, one driver.
  sony.py      the DualSense / DualSense Edge report format: input over
               USB and Bluetooth decoded into the pad's vocabulary,
               output (light, rumble, triggers, LEDs) encoded, the
               Bluetooth CRC. Pure bytes in, values out.
  gesture.py   the touchpad's and the motion sensors' lanes: position,
               pinch, twist and tap; tilt, spin, shake and energy.
  hid.py       the hidapi road: one reader thread per Sony pad (USB or
               Bluetooth), the hub that lends them to pad entries by
               `matches`, and the tape (a recorded meta controller read back as
               if it were the pad).

`models`, `sony` and `gesture` are leaves: they import nothing from the
package and nothing outside the standard library, so the codec and the
gesture maths are tested without a controller or hidapi. `hid` imports
`hid` (the hidapi wheel) only inside a scan or an open.
"""
