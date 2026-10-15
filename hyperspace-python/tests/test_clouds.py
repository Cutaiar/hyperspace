"""The point-cloud source type and the recorded-cloud device (plan 27 B4).

`devices.PointCloud` is the contract the render graph's point-cloud node
(plan 26 A4b) reads: N×3 float32 points, read-only and GPU-ready, a
timestamp, a frame id, a bounds box and optional N×3 colours. A device
publishes it on the registry under ``cloud:<role>`` (`DeviceRegistry.clouds`),
not through the Router. The `cloud` kind plays a recorded `.npz`
(tests/fixtures/clouds/knot.npz, written by tools/cloud_fixture.py) at its
own rate, so the type runs with no sensor. Every home here is a scratch one."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import numpy as np
import pytest

from hyperspace import config, devices, routing, ui

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "clouds" / "knot.npz"
GENERATOR = Path(__file__).resolve().parents[1] / "tools" / "cloud_fixture.py"


def _generator():
    spec = importlib.util.spec_from_file_location("cloud_fixture", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- the type

def test_a_point_cloud_is_a_read_only_gpu_ready_buffer_with_its_bounds():
    src = np.array([[0, 1, 2], [-1, 5, 0.5], [3, -2, 1]], dtype=np.float64)
    c = devices.PointCloud(src, t=1.25, frame=7)
    assert c.points.dtype == np.float32 and c.points.shape == (3, 3)
    assert c.points.flags.c_contiguous and not c.points.flags.writeable
    assert c.n == 3 and c.t == 1.25 and c.frame == 7 and c.colors is None
    assert c.bounds.dtype == np.float32 and c.bounds.shape == (2, 3)
    assert c.bounds.tolist() == [[-1, -2, 0.5], [3, 5, 2]]
    assert not c.bounds.flags.writeable
    with pytest.raises(ValueError):
        c.points[0, 0] = 9.0                      # nobody downstream writes the buffer
    # the caller's own float32 array is copied, never frozen under it
    mine = np.zeros((4, 3), np.float32)
    c2 = devices.PointCloud(mine, 0.0, 0, colors=np.ones((4, 3)))
    assert mine.flags.writeable and c2.points is not mine
    assert c2.colors.dtype == np.float32 and not c2.colors.flags.writeable
    # an empty cloud is a cloud: zero points, a zero box
    e = devices.PointCloud(np.zeros((0, 3)), 0.0, 0)
    assert e.n == 0 and e.bounds.tolist() == [[0, 0, 0], [0, 0, 0]]
    # shapes are checked
    with pytest.raises(ValueError, match="N×3"):
        devices.PointCloud(np.zeros((4, 2)), 0.0, 0)
    with pytest.raises(ValueError, match="rows for 4 points"):
        devices.PointCloud(np.zeros((4, 3)), 0.0, 0, colors=np.zeros((3, 3)))
    with pytest.raises(AttributeError):
        c.frame = 8                                # frozen
    assert "n=3" in repr(c) and "frame=7" in repr(c)


def test_the_cloud_file_round_trips_ragged_frames_and_refuses_a_bad_one(tmp_path):
    frames = [np.arange(9).reshape(3, 3), np.zeros((0, 3)), np.ones((5, 3))]
    cols = [np.full((3, 3), 0.5), np.zeros((0, 3)), np.ones((5, 3))]
    p = devices.write_clouds(tmp_path / "a.npz", frames, 30, cols)
    f = devices.read_clouds(p)
    assert len(f) == 3 and f.rate == 30.0 and f.offsets.tolist() == [0, 3, 3, 8]
    pts, c = f.frame(0)
    assert pts.dtype == np.float32 and pts.tolist() == frames[0].tolist()
    assert c.tolist() == cols[0].tolist()
    assert f.frame(1)[0].shape == (0, 3)
    assert devices.read_clouds(devices.write_clouds(tmp_path / "b.npz", frames, 5)).colors is None
    # what the file holds, by name: plain numpy any recorder can write
    with np.load(p) as z:
        assert set(z.files) == {"version", "rate", "offsets", "points", "colors"}
        assert int(z["version"]) == 1 and z["points"].dtype == np.float32
    # refused, each with its reason
    np.savez(tmp_path / "x.npz", points=np.zeros((2, 3), np.float32))
    with pytest.raises(ValueError, match="no 'version'"):
        devices.read_clouds(tmp_path / "x.npz")
    np.savez(tmp_path / "v.npz", version=2, rate=1.0, offsets=[0, 2], points=np.zeros((2, 3)))
    with pytest.raises(ValueError, match="version 2"):
        devices.read_clouds(tmp_path / "v.npz")
    np.savez(tmp_path / "o.npz", version=1, rate=1.0, offsets=[0, 5], points=np.zeros((2, 3)))
    with pytest.raises(ValueError, match="offsets"):
        devices.read_clouds(tmp_path / "o.npz")
    with pytest.raises(ValueError):
        devices.write_clouds(tmp_path / "r.npz", frames, 0)
    with pytest.raises(ValueError):
        devices.write_clouds(tmp_path / "r.npz", frames, 30, cols[:2])


def test_the_fixture_is_what_the_committed_generator_writes(tmp_path):
    """tests/fixtures/clouds/knot.npz is tools/cloud_fixture.py's output:
    regenerated here, every array equal (the zip's own timestamps differ)."""
    gen = _generator()
    pts, cols = gen.frames()
    again = devices.read_clouds(devices.write_clouds(tmp_path / "k.npz", pts, gen.RATE, cols))
    f = devices.read_clouds(FIXTURE)
    assert len(f) == gen.FRAMES == 16 and f.rate == gen.RATE == 12.0
    assert f.offsets.tolist() == again.offsets.tolist()
    assert np.array_equal(f.points, again.points) and np.array_equal(f.colors, again.colors)
    sizes = np.diff(f.offsets)
    assert sizes[0] == 96 and len(set(sizes.tolist())) == 16       # every frame its own size


# ---------------------------------------------------------------- the device

def _home(tmp_path, entry: str) -> tuple[Path, list[dict]]:
    """A scratch home whose config.toml lists `entry` (no [library]), the
    fixture copied in beside it; the checked entries config.load gives."""
    home = tmp_path / "home"
    (home / "clouds").mkdir(parents=True)
    shutil.copyfile(FIXTURE, home / "clouds" / FIXTURE.name)
    (home / "config.toml").write_text(entry)
    cfg = config.load(home / "config.toml")
    return home, config.devices(cfg)


SCAN = """
[[devices]]
role = "scan"
kind = "cloud"
file = "clouds/knot.npz"
"""


def test_a_cloud_entry_publishes_the_recording_at_its_own_rate(tmp_path):
    """A `[[devices]]` entry of kind `cloud` is all it takes: the device
    plays the file at the file's 12 fps against the frame clock — whatever
    the app's frame rate — and the registry holds its latest frame as
    ``cloud:scan`` with every field the contract names."""
    home, entries = _home(tmp_path, SCAN)
    assert entries == [{"role": "scan", "kind": "cloud", "enabled": True,
                        "file": "clouds/knot.npz"}]
    rig = devices.DeviceRegistry(entries, devices.Context(home=home))
    rig.open_all()
    d = rig.get("scan")
    assert isinstance(d, devices.CloudDevice) and d.status == "connected"
    assert rig.clouds == {}                                   # nothing until it is polled
    rec = devices.read_clouds(FIXTURE)
    seen: list[int] = []
    t0 = 100.0
    for k in range(121):                                       # two seconds at 60 Hz
        now = t0 + k / 60
        rig.poll(1 / 60, now)
        c = rig.clouds["cloud:scan"]
        assert c is d.cloud and c.t <= now
        if not seen or seen[-1] != c.frame:
            seen.append(c.frame)
            assert c.t == pytest.approx(now)
            i = c.frame % len(rec)
            assert np.array_equal(c.points, rec.frame(i)[0])
            assert np.array_equal(c.colors, rec.frame(i)[1])
            assert c.bounds.tolist() == [rec.frame(i)[0].min(0).tolist(),
                                         rec.frame(i)[0].max(0).tolist()]
    assert seen == list(range(25))                             # 12 fps for 2 s, frames 0…24
    assert rig.clouds["cloud:scan"].frame % 16 == 8            # …looping past frame 15
    # the line on the SYSTEM page
    assert ui.device_lines(rig) == [
        ("scan  ·  cloud  ·  connected  ·  1 source  ·  knot.npz  ·  frame 9/16  ·  "
         "160 points  ·  12 fps")]
    assert d.sources == (devices.Port("scan", "point cloud", kind="cloud", scheme="cloud"),)
    assert d.sources[0].address == "cloud:scan"
    rig.close()
    assert rig.clouds == {} and d.status == "lost"


def test_a_cloud_entry_can_set_its_rate_and_stop_at_the_end(tmp_path):
    home, entries = _home(tmp_path, SCAN + "rate = 60\nloop = false\n")
    rig = devices.DeviceRegistry(entries, devices.Context(home=home))
    rig.open_all()
    frames = []
    for k in range(40):
        rig.poll(1 / 60, k / 60)
        frames.append(rig.clouds["cloud:scan"].frame)
    assert frames[:16] == list(range(16)) and set(frames[16:]) == {15}     # held at the end


def test_a_cloud_is_on_the_registry_not_the_router(tmp_path):
    """Not a scalar lane: no Router scheme, no feed, no row, nothing to
    learn — the scheme lists and the wants are as if it were not there."""
    from hyperspace.params import Registry

    home, entries = _home(tmp_path, SCAN)
    rig = devices.DeviceRegistry(entries, devices.Context(home=home))
    rig.open_all()
    reg = Registry()
    router = routing.Router(reg, routing.Bindings(), devices=rig)
    rig.poll(0.0, 0.0, router=router)
    rig.feed(router)
    assert "cloud" not in router.feeds and "scan" not in router.feeds
    assert rig.continuous_schemes() == ("lane", "lfo")
    assert rig.row_schemes() == () and rig.wants() == ()
    assert router.schemes() == ("lane", "lfo")
    assert set(rig.clouds) == {"cloud:scan"}


def test_a_missing_recording_is_an_error_line_and_comes_up_when_it_appears(tmp_path):
    home, entries = _home(tmp_path, SCAN.replace("clouds/knot.npz", "later.npz"))
    now = [0.0]
    notes: list[str] = []
    rig = devices.DeviceRegistry(entries, devices.Context(home=home), clock=lambda: now[0],
                                 notes=notes)
    rig.open_all()
    d = rig.get("scan")
    assert d.status.startswith("error: FileNotFoundError")
    assert len(notes) == 1 and notes[0].startswith("cloud: ")
    shutil.copyfile(FIXTURE, home / "later.npz")
    now[0] = devices.RETRY_S                                   # the Ports schedule
    rig.poll(1 / 60, 50.0)
    assert d.status == "connected" and rig.clouds["cloud:scan"].frame == 0
    # an entry with no file says so
    bad = devices.DeviceRegistry([{"role": "c", "kind": "cloud", "enabled": True}])
    bad.open_all()
    assert bad.get("c").status == 'error: ValueError: a cloud entry needs file = "<recording>.npz"'


def test_an_off_cloud_entry_opens_nothing():
    rig = devices.DeviceRegistry([{"role": "scan", "kind": "cloud", "enabled": False,
                                   "file": "nowhere.npz"}])
    rig.open_all()
    assert rig.get("scan").status == "off" and rig.clouds == {}
