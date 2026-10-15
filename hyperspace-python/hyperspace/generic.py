"""The `generic` MIDI profile (plan 27 B2): any controller that sends
plain CC, note and pitch-bend messages, with no feedback at all.

A profile is a duck-typed module (apc40.py is the first): midi.MidiIO and
learn.Learn ask it for a port to match, the messages that wake the device
and put it to sleep, which knobs are relative encoders, what feedback a
learned control can show, and the controls' names. This one knows nothing
about the device, so a second controller — a pad box, a fader bank, a
keyboard's knobs — maps on the desk's Learn with no code:

  * **No port of its own.** `PORT_MATCH` is None: the `[[devices]]` entry
    names its port (``port = "nanoKONTROL"``, a substring of the name the
    system gives it); an entry without one is an error line, never the
    first port that happens to be there.
  * **No feedback.** `FEEDBACK` is False: MidiIO sends the device nothing —
    no power-up SysEx, no ring, no LED — so a controller that echoes what
    it receives never sees its own knob come back.
  * **Absolute knobs.** Every CC learns as an ``abs`` row with soft
    pickup (no encoder is relative), a note as a ``toggle``, pitch bend as
    an ``abs`` 14-bit fader — exactly what Learn makes with no profile.
  * **Plain names.** A control is named by its row ("MIDI CC 7 ch1 on
    launch"); there is no layout to draw, so the desk page (ui_desk.py)
    stays the APC40's, and the device line counts no sources.
  * **One layer.** It has no SHIFT: its rows are the loaded preset's (a
    learn) or the session's invariant ones; plan 28 is where a device with
    a mode switch becomes one node per mode.

Imports nothing from the package.
"""

from __future__ import annotations

PORT_MATCH = None          # the entry's `port` names it
FEEDBACK = False           # nothing is ever sent to the device
RING_REBASES_KNOB = False  # (no ring) every absolute knob keeps soft pickup
LAYOUT: tuple = ()         # no controls known in advance: none to draw or to darken
DEFAULT_MAP: list = []     # no factory rows: every row is learned


def enter() -> list:
    """Nothing wakes a generic device."""
    return []


def leave() -> list:
    """Nothing puts it to sleep."""
    return []


def is_relative(cc: int) -> bool:
    """No encoder is relative: every CC is an absolute knob or fader."""
    return False


def ring_setup(channel: int, cc: int, style: int) -> list:
    """No rings."""
    return []


def feedback_for(kind: str, channel: int, number: int) -> dict | None:
    """No learned control shows anything."""
    return None


def control_name(source: str) -> str | None:
    """No names of its own: the row describes itself."""
    return None
