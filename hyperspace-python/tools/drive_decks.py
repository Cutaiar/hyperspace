"""tools/app_driver.py script: the two verbs in the real app, by mouse (plan 44 D5d).
Copy on air to off air, the panel moved to the deck off air (the red head chip, the
red frame, the inset of what is on air), a look loaded there, a timed fade across, the
fader by hand to the middle and home, then a press on air, which loads off air (row
700), and a ⌘Z, which takes nothing back from the room (row 753). Each step says what it left, on stderr.

    uv run python tools/app_driver.py tools/drive_decks.py --out <scratch>/run --every 20
"""

import sys

from hyperspace import undo as undos
from hyperspace.library import PRESETS


def say(panel, what: str) -> None:
    meta = panel.meta
    print(f"{what}: {panel.meta.words(meta.panel)} | on air deck "
          f"{1 if meta.on_air is meta.decks[0] else 2} | xfade {meta.mix.xfade:.3f} | "
          f"deck 1 {meta.decks[0].presets.current} | deck 2 {meta.decks[1].presets.current}", file=sys.stderr)


def script(d, panel):
    meta = panel.meta
    one, two = meta.decks
    panel.render_watch = None     # the banner a covered render window raises sits on the footer
    panel.reg["output.xfade_s"].set(1.0)
    yield from d.park()
    yield from d.wait(40)         # deck 1 on air, deck 2 empty
    say(panel, "start")
    assert two.presets.current is None and meta.on_air is one

    yield from d.click("graph.copy", frames=10)
    yield from d.park()
    yield from d.wait(40)
    say(panel, "copied")
    assert two.presets.current == one.presets.current and meta.on_air is one

    yield from d.click("graph.deck", frames=10)
    yield from d.park()
    yield from d.wait(40)         # the chip red, the canvas framed, the inset up
    say(panel, "the panel on deck 2")
    assert meta.panel is two

    panel.library.load(PRESETS, "party-trip")
    yield from d.wait(60)         # deck 2 is another look; on air has not moved
    say(panel, "loaded off air")
    assert two.presets.current != one.presets.current

    yield from d.click("graph.fade", frames=10)
    yield from d.park()
    yield from d.wait(20)         # part way
    say(panel, "fading")
    yield from d.wait(100)
    say(panel, "faded")
    assert meta.on_air is two and meta.mix.xfade == 1.0 and meta.timed is None

    yield from d.slide("output.xfade", 0.25, frames=30)
    yield from d.park()
    yield from d.wait(30)         # by hand, past the middle: deck 1 on air again
    say(panel, "by hand to a quarter")
    assert meta.on_air is one
    yield from d.slide("output.xfade", 0.0, frames=20)
    yield from d.click("graph.deck", frames=10)
    yield from d.park()
    yield from d.wait(30)
    say(panel, "home")
    assert meta.panel is one and meta.on_air is one

    on_air, off_air = one.presets.current, two.presets.current
    one.reg["preset.next"].fire()     # the press a pad or a key makes, from the deck on air
    yield from d.wait(40)
    say(panel, "a press on air")
    print(f"status line: {panel.library.status}", file=sys.stderr)
    assert one.presets.current == on_air and two.presets.current != off_air
    assert "loaded off air on deck 2" in panel.library.status
    assert "⌘Z" not in panel.library.status      # the panel is on air: ⌘Z does not reach it

    held = one.reg.snapshot(part="performance")
    panel.reg["edit.undo"].fire()     # a mis-pressed pad and ⌘Z: the latch (row 753)
    yield from d.wait(10)
    at = undos.here()
    print(f"status line: {at.status}", file=sys.stderr)
    assert at.status.startswith("nothing to undo here yet")
    assert one.reg.snapshot(part="performance") == held
