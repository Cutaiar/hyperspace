"""Hand tapes (hands/tape.py): record real frames once, replay them anywhere.

Recorded here from the fake ``leap`` the other source tests use, so the
round trip runs on every machine. A real tape the owner records with
`tools/hands_tape.py record` goes under tests/fixtures/hands/ and is
replayed by the last test: through `HandsIO` and the ghost hands, the
way the app plays one under `[hands] tape`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest
from fake_hands import hand
from test_hands_leap import Clock, FakeLeap, source

from hyperspace import ghost as G
from hyperspace.hands import HandSettings, HandsIO
from hyperspace.hands import tape as T


@pytest.fixture()
def leap(monkeypatch):
    fake = FakeLeap()
    monkeypatch.setitem(sys.modules, "leap", fake)
    return fake


TAPES = sorted((Path(__file__).parent / "fixtures" / "hands").glob("*.json"))


def _recorded(leap, tmp_path, n=12):
    """A tape of n frames from the fake camera: both hands, the right
    closing to a fist, the left leaving for the last three."""
    clock = Clock()
    src, conn = source(leap, "screentop", clock=clock)
    k = [0]

    def sleep(dt):                 # each poll: the next camera frame, 1/90 s on
        clock.t += 1 / 90
        if k[0] < n:
            hs = [hand("right", "fist" if k[0] > n // 2 else "open", (80.0, 200.0, 0.0))]
            if k[0] < n - 3:
                hs.append(hand("left", "open", (-80.0, 210.0 + k[0], 0.0)))
            conn.fire("on_tracking_event", NS(hands=hs))
            k[0] += 1

    sleep(0)
    t = T.record(src, n / 90 + 0.05, mode="screentop", clock=clock, sleep=sleep)
    path = tmp_path / "rig.json"
    T.save(t, path)
    return t, path, src


def test_a_recorded_tape_keeps_every_frame_with_its_skeletons(leap, tmp_path):
    t, path, _ = _recorded(leap, tmp_path)
    assert len(t["frames"]) == 12 and t["mode"] == "screentop"
    assert [sorted(f["hands"]) for f in t["frames"]][-1] == ["right"]   # leaving is data
    back = T.load(path)
    f0 = back["frames"][0]["hands"]["left"]
    assert f0["confidence"] == 1.0 and "roll" in f0["features"]
    sk = f0["skeleton"]
    assert len(sk["digits"]) == 5 and all(len(d) == 4 for d in sk["digits"])
    assert isinstance(sk["palm"], tuple) and sk["palm"] == (-80.0, 210.0, 0.0)
    assert back["frames"][1]["t"] == pytest.approx(1 / 90, abs=1e-4)


def test_a_tape_that_is_not_one_is_refused(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"schema": "hyperspace.hands/1", "axes": {}}')
    with pytest.raises(ValueError, match="not a hand tape"):
        T.load(p)


def test_the_app_plays_a_tape_instead_of_the_camera(leap, tmp_path):
    """`[hands] tape`: HandsIO plays it — its mode, its frames, looping —
    and the ghost hands draw it like the camera."""
    _, path, _ = _recorded(leap, tmp_path)
    n_conn = len(leap.connections)
    clock = Clock()
    io = HandsIO(HandSettings.from_config({}), {"out": "", "tape": str(path)}, clock=clock)
    assert isinstance(io.source, T.TapeSource) and len(leap.connections) == n_conn
    assert io.cfg["mode"] == "screentop" and io.source.on
    io.poll(1 / 60)
    assert set(io.skeleton) == {"left", "right"} and io.present["left"]
    clock.t = 11 / 90                                  # the last frames: the left hand gone
    io.poll(1 / 60)
    assert set(io.skeleton) == {"right"} and not io.present["left"]
    clock.t = io.source.length + 0.001                 # and round again
    seq = io.source.latest()[0]
    io.poll(1 / 60)
    assert seq > 12 and set(io.skeleton) == {"left", "right"}
    gh = G.Ghost(ctx=None, state=G.GhostState(on=True))
    gh.source = io
    poses, _, _ = gh.poses(0.0, 1.6)
    assert [p.side for p in poses] == ["left", "right"]
    # screentop: the stage is the camera turned over (ghost.MODES)
    assert np.allclose(poses[1].palm, (-80.0, -200.0, 0.0))


def test_a_tape_that_does_not_loop_goes_stale_after_its_end(leap, tmp_path):
    _, path, _ = _recorded(leap, tmp_path)
    clock = Clock()
    src = T.TapeSource(path, clock, loop=False)
    assert set(src.skeletons()[2]) == {"left", "right"}
    clock.t = src.length                               # the last frame holds briefly…
    assert set(src.latest()[2]) == {"right"}
    clock.t = src.length + T.STALE_S + 0.01            # …then the hands are gone
    assert src.latest()[2] == {} and src.skeletons()[2] == {}


@pytest.mark.parametrize("bad", ["missing", "not a tape"])
def test_a_bad_tape_path_is_a_note_the_pages_show(tmp_path, capsys, bad):
    """Plan 21 WP5 R10: a `[hands] tape` that is missing or is not a tape
    leaves no tracker, as before, and now says why in `cfg["notes"]` —
    which the SYSTEM page lists and the HANDS page shows in place of
    "tracker off" (test_ui_shell) — not on stderr alone."""
    from hyperspace import app

    path = tmp_path / "tape.json"
    if bad == "not a tape":
        path.write_text('{"schema": "something else"}')
    cfg = {"hands": {"enabled": True, "out": "", "tape": str(path)},
           "notes": ["config: an earlier note"]}
    assert app._open_hands(cfg, HandSettings.from_config({})) is None
    assert cfg["notes"][0] == "config: an earlier note" and len(cfg["notes"]) == 2
    note = cfg["notes"][1]
    assert note.startswith("hands: ") and str(path) in note
    assert note in capsys.readouterr().err
    fresh = {"hands": {"enabled": True, "out": "", "tape": str(path)}}   # no notes yet
    app._open_hands(fresh, HandSettings.from_config({}))
    assert fresh["notes"] == [note]


def test_the_stale_time_and_the_palm_width_are_defined_once(monkeypatch):
    """Plan 21 WP5 R13: `STALE_S` is assigned in one module of the hands
    package (tape.py, the leaf; core.py imports it) and the ghost's palm
    fallback is core's `PALM_W`, not a second 85.0."""
    import ast

    import hyperspace.hands.core as hc

    pkg = Path(G.__file__).parent
    where = [f.name for f in sorted((pkg / "hands").glob("*.py"))
             for n in ast.parse(f.read_text()).body
             if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "STALE_S"
                                                  for t in n.targets)]
    assert where == ["tape.py"] and hc.STALE_S == T.STALE_S
    assert "85.0" not in (pkg / "ghost.py").read_text()
    sk = {"palm": (0.0, 200.0, 0.0), "normal": (0.0, -1.0, 0.0),
          "direction": (0.0, 0.0, -1.0), "width": 0.0, "digits": []}
    with monkeypatch.context() as m:
        m.setattr(hc, "PALM_W", 70.0)
        assert G.pose("left", sk, np.eye(3)).width == 70.0


@pytest.mark.skipif(not TAPES, reason="no recorded tape — tools/hands_tape.py record "
                                      "tests/fixtures/hands/<name>.json on the rig")
@pytest.mark.parametrize("path", TAPES, ids=[p.stem for p in TAPES])
def test_every_recorded_tape_replays_through_the_ghost(path):
    tape = T.load(path)
    assert tape["frames"], f"{path.name} is empty"
    clock = Clock()
    io = HandsIO(HandSettings.from_config({}), {"out": "", "tape": str(path)}, clock=clock)
    gh = G.Ghost(ctx=None, state=G.GhostState(on=True))
    gh.source = io
    seen = set()
    for k in range(int(io.source.length * 60)):
        clock.t = k / 60
        io.poll(1 / 60)
        got = gh.poses(clock.t, 16 / 9)
        for p in got[0] if got else ():
            seen.add(p.side)
            assert np.isfinite(p.joints).all() and p.joints.shape[1:] == (5, 3)
    assert seen, f"{path.name}: no hand ever showed"
