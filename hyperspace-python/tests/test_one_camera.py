"""Plan 43 C2 — one orbit camera (the owner, 2026-11-02; register rows 555,
572–576): the eye (`eye.fov`, `eye.distance`) is the loadable patch's beside
`camera.*`, modulatable; every save is `hyperspace.preset/9` and records
the spin's pose (`pose`, `view.body` folded in), which a load sets; an old
loadable patch takes the eye its old show held; the hands' calibration is fitted
to the rig's reference eye, so hands drawn in the scene scale with the
shape and a hands layer keeps its size; the migration tool moves a
library (the retaper first, a backup, the shows' eye kept as
``.bak-v2-eye``).

Every library here is a scratch one under tmp_path; nothing reads or
writes ~/Hyperspace (conftest's HYPERSPACE_HOME)."""

from __future__ import annotations

import gc
import importlib.util
import json
import math
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest
from conftest import CORPUS
from test_loadable import boot

from hyperspace import geometry as G
from hyperspace import ghost, graphmigrate, graphview, headless, loadable
from hyperspace import library as L
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.learn import Learn
from hyperspace.params import (
    PATCH_GROUPS,
    PLANES,
    POSE_IDS,
    SHARED_META_GROUPS,
    build_registry,
    part_of,
)
from hyperspace.routing import Bindings
from hyperspace.view import ViewState

ROOT = Path(__file__).resolve().parents[1]
TRIP = CORPUS / "loadable" / "party-trip.json"
OLD_PATCH = ROOT / "tests" / "fixtures" / "patches" / "acid-wash.json"
EYE = {"eye.fov": 30.0, "eye.distance": 5.0}
CAMERA_AT = [40, 50]


def old_loadable(src: Path = TRIP, *, marked: bool = True) -> dict:
    """A corpus loadable patch as it was before `/9`: `/7`, no eye in its values
    (and, unmarked, its depths still measured along the linear ranges'
    words — wave 0 T1's marker gone)."""
    doc = json.loads(src.read_text())
    doc["schema"] = graphmigrate.WIRED_SCHEMA
    doc["values"] = {k: v for k, v in doc["values"].items() if not k.startswith("eye.")}
    if not marked:
        doc["units"] = {k: v for k, v in doc["units"].items() if k != "fx.depth"}
    return doc


def old_show(**extra) -> dict:
    """A show from before C2 (`hyperspace.project/2`): the eye in its
    meta controller, the camera node's GRAPH position in its layout."""
    return {"schema": L.PROJECT_V2, "name": "rig", "bank": [None] * 8,
            "session": {"tempo.bpm": 128.0, **EYE},
            "layout": {"render:camera": CAMERA_AT, "device:apc40": [1, 2]}, **extra}


def _write(path: Path, doc: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n")
    return path


# ---------------------------------------------------------------- the params


def test_the_eye_is_the_looks_and_the_pose_is_no_base(tmp_path):
    """Row 555: the eye leaves the meta controller for the patch part, ids
    kept; the pose's ids are the six phases, which stay `persist=False` —
    no base, so no undo step and no dirty dot as the turn moves."""
    assert "eye" in PATCH_GROUPS and "eye" not in SHARED_META_GROUPS
    assert POSE_IDS == tuple(f"rot.phase.{n}" for n in PLANES)
    rig = boot(tmp_path)
    snap = rig.reg.snapshot(part="patch")
    for pid in POSE_IDS:
        p = rig.reg[pid]
        assert not p.persist and pid not in snap and part_of(p) == "patch"
    assert {"eye.fov", "eye.distance"} <= set(snap)


# ---------------------------------------------------------------- the pose


def test_pose_angles_reads_back_any_turn():
    """`geometry.pose_angles` is `rot_matrix`'s inverse on SO(4): any six
    angles, and any rotation at all (a body is no product of six angles
    by construction), read back to the same matrix."""
    rng = np.random.default_rng(43)
    for _ in range(300):
        R = G.rot_matrix(rng.uniform(-math.pi, math.pi, 6))
        assert np.allclose(G.rot_matrix(G.pose_angles(R)), R, atol=1e-12)
    for _ in range(300):
        q, r = np.linalg.qr(rng.normal(size=(4, 4)))
        q = q @ np.diag(np.sign(np.diag(r)))
        if np.linalg.det(q) < 0:
            q[:, 0] *= -1
        assert np.allclose(G.rot_matrix(G.pose_angles(q)), q, atol=1e-12)
    assert G.pose_angles(np.eye(4)) == [0.0] * 6
    assert all(math.copysign(1.0, a) > 0 for a in G.pose_angles(np.eye(4)))   # no −0.0


@pytest.mark.parametrize("three_d", [False, True])
def test_a_saved_pose_draws_the_same_shape_whichever_way_the_switch_stands(three_d):
    """`ViewState.pose` folds `body` into six angles; `set_pose` lands them
    with no body and the switch not holding — the shape is drawn where it
    was both before the next `integrate` and after it (the switch then
    folds a fresh body), for 4D shapes and 3D ones."""
    four = [i for i in range(len(G.SHAPES)) if not G.is_3d(i)][:3]
    three = [i for i in range(len(G.SHAPES)) if G.is_3d(i)][:2]
    rng = np.random.default_rng(7)
    for i in four + three:
        v = ViewState(shape=i, ang=list(rng.uniform(-3, 3, 6)), planes=[True] * 6)
        v.integrate(0.3)
        v.three_d = three_d
        v.integrate(0.5)
        v.integrate(0.2)
        want = G.shape_view(i, v.ang, 0.1, 0.2, flat=v.held, body=v.body)[:2]
        pose = v.pose()
        assert all(-math.pi <= a <= math.pi for a in pose)
        w = ViewState(shape=i, three_d=three_d)
        w.set_pose(pose)
        assert w.body is None and not w.held
        got = G.shape_view(i, w.ang, 0.1, 0.2, flat=w.held, body=w.body)[:2]
        assert all(np.allclose(a, b, atol=1e-9) for a, b in zip(got, want)), i
        w.playing = False
        w.integrate(0.0)
        assert w.held == three_d
        got = G.shape_view(i, w.ang, 0.1, 0.2, flat=w.held, body=w.body)[:2]
        assert all(np.allclose(a, b, atol=1e-9) for a, b in zip(got, want)), i


def test_frame_save_load_another_and_load_back_puts_the_framing_and_the_turn_back(tmp_path):
    """Hand check 431's road, headless: the eye, the camera and the turn
    (a 3D switch's body included) are saved; another loadable patch moves the
    framing and leaves the turn spinning (it has no pose); loading the
    first again puts both back and the shape is drawn as it was."""
    rig = boot(tmp_path)
    reg, view = rig.reg, rig.view
    reg["eye.fov"].set(31.0)
    reg["eye.distance"].set(6.0)
    reg["camera.zoom"].set(1.7)
    reg["view.shape"].set(next(i for i in range(len(G.SHAPES)) if not G.is_3d(i)))
    view.ang = [0.3, -0.2, 0.9, 1.1, -0.4, 0.25]
    view.three_d = True
    view.integrate(0.0)                       # the switch folds a body in
    view.ang[:3] = [0.5, 0.1, -0.7]           # and the 3D planes turn on
    shape = view.shape
    want = G.shape_view(shape, view.ang, 0.0, 0.0, flat=view.held, body=view.body)[:2]
    pose = view.pose()
    path = rig.loaded_patch.save_as("FRAMED")
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.loadable/11" == loadable.SAVE_SCHEMA   # (plan 44 D3)
    assert doc["values"]["eye.fov"] == 31.0 and doc["values"]["eye.distance"] == 6.0
    assert list(doc[loadable.POSE_KEY]) == list(POSE_IDS)
    assert [doc[loadable.POSE_KEY][k] for k in POSE_IDS] == pytest.approx(pose, abs=1e-6)
    assert not any(k.startswith("rot.phase.") for k in doc["values"])
    keys = list(doc)
    assert keys.index(loadable.POSE_KEY) == keys.index("values") + 1
    # another loadable patch (a corpus /9: the default eye, no pose)
    turn = list(view.ang)
    rig.loaded_patch.load("DIAL")
    assert reg["eye.fov"].value == pytest.approx(G.EYE_FOV)
    assert view.ang == turn                   # no pose: left spinning
    # …and back
    rig.loaded_patch.load("FRAMED")
    assert reg["eye.fov"].value == 31.0 and reg["eye.distance"].value == 6.0
    assert reg["camera.zoom"].value == pytest.approx(1.7)
    assert view.ang == pytest.approx(pose, abs=1e-6) and view.body is None
    got = G.shape_view(shape, view.ang, 0.0, 0.0, flat=view.held, body=view.body)[:2]
    assert all(np.allclose(a, b, atol=1e-4) for a, b in zip(got, want))
    assert rig.loaded_patch.notes == [] and not rig.lib.is_dirty("loadable")
    # the turn moving is no edit
    view.integrate(0.5)
    view.ang[0] += 1.0
    assert not rig.lib.is_dirty("loadable")


def test_a_pose_that_is_not_six_numbers_is_said_and_the_turn_left_spinning(tmp_path):
    rig = boot(tmp_path)
    doc = json.loads((CORPUS / "loadable" / "dial.json").read_text())
    for bad in ({k: 0.5 for k in POSE_IDS[:5]}, {**{k: 0.5 for k in POSE_IDS}, "rot.phase.XY": "x"},
                {**{k: 0.5 for k in POSE_IDS}, "rot.phase.ZW": float("nan")}, [0.5] * 6):
        rig.view.ang = [0.1] * 6
        rig.loaded_patch.load_doc({**doc, loadable.POSE_KEY: bad})
        assert loadable.POSE_UNREAD in rig.loaded_patch.notes, bad
        assert rig.view.ang == [0.1] * 6


def test_a_pose_in_values_is_no_pose(tmp_path):
    """A hand-edited `rot.phase.*` in `values` is not part of a loadable patch (it
    is no base), said as ever; the turn is left."""
    rig = boot(tmp_path)
    doc = json.loads((CORPUS / "loadable" / "dial.json").read_text())
    doc["values"]["rot.phase.XY"] = 1.0
    rig.view.ang = [0.1] * 6
    rig.loaded_patch.load_doc(doc)
    assert "rot.phase.XY is not part of a patch, ignored" in rig.loaded_patch.notes
    assert rig.view.ang == [0.1] * 6


def test_the_migrations_resave_writes_a_pose_only_where_the_file_had_one(tmp_path):
    """`headless.resave` is the migration's: an old file keeps spinning (no
    pose written, so its `/9` is a fixed point), a `/9` with a pose keeps
    it as it was."""
    old = _write(tmp_path / "old.json", old_loadable())
    data, notes, _ = headless.resave(old, tmp_path / "a")
    doc = json.loads(data)
    assert notes == [] and loadable.POSE_KEY not in doc and doc["schema"] == loadable.SAVE_SCHEMA
    posed = dict(doc, **{loadable.POSE_KEY: dict(zip(POSE_IDS, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
                                                   strict=True))})
    path = tmp_path / "posed.json"
    path.write_text(loadable.dumps(posed))
    again, _, _ = headless.resave(path, tmp_path / "b")
    assert json.loads(again)[loadable.POSE_KEY] == posed[loadable.POSE_KEY]


# ---------------------------------------------------------------- old files


def test_nine_is_pure_one_way_and_keeps_what_the_file_says():
    doc = old_loadable()
    out = graphmigrate.nine(doc, EYE, CAMERA_AT)
    assert out is not doc and doc["values"].get("eye.fov") is None       # pure
    assert {k: out["values"][k] for k in EYE} == EYE
    assert out["layout"]["render:camera"] == CAMERA_AT
    assert loadable.POSE_KEY not in out
    # a value or a position the file has stays; an id the show lacks is left out
    mine = dict(doc, values={**doc["values"], "eye.fov": 60.0}, layout={"render:camera": [1, 2]})
    out = graphmigrate.nine(mine, {"eye.distance": 9.0}, CAMERA_AT)
    assert out["values"]["eye.fov"] == 60.0 and out["values"]["eye.distance"] == 9.0
    assert out["layout"] == {"render:camera": [1, 2]}
    assert "eye.fov" not in graphmigrate.nine(doc, {"eye.distance": 9.0})["values"]
    # no values at all; a /9 and no document come back as they are
    assert graphmigrate.nine({"schema": "hyperspace.preset/7"}, EYE)["values"] == EYE
    nine = {"schema": loadable.SAVE_SCHEMA, "values": {}}
    assert graphmigrate.nine(nine, EYE, CAMERA_AT) is nine
    assert graphmigrate.nine(None, EYE) is None


def test_an_old_show_hands_its_eye_to_old_loadables_and_keeps_none_itself(tmp_path):
    """REVIEW.md "Files on disk are a format", end to end: an old show
    (eye in its session, the camera's position in its layout) and an old
    `/7` loadable patch. The show lands no eye and is clean; the old loadable patch takes
    the show's eye and position, a `/9` its own; the loadable patch's save is `/9`
    with that eye; the show's save drops the eye after keeping the file as
    ``.bak-v2-eye`` (once); a fresh launch on the saved files draws the
    same framing."""
    home = tmp_path / "lib"
    _write(home / "projects" / "rig.hyp.json", old_show())
    (home / "loadable").mkdir(parents=True)
    (home / "loadable" / "old.json").write_text(loadable.dumps({**old_loadable(), "name": "OLD"}))
    rig = boot(home, show="rig")
    pr, reg = rig.lib.install, rig.reg
    assert pr.name == "rig" and pr.old_eye == EYE and pr.camera_at == CAMERA_AT
    assert not any(k.startswith("eye.") for k in pr.session)
    assert "render:camera" not in pr.layout and pr.layout["device:apc40"] == [1, 2]
    assert reg["tempo.bpm"].value == pytest.approx(128.0)
    assert not pr.is_dirty()
    rig.loaded_patch.load("OLD")
    assert reg["eye.fov"].value == 30.0 and reg["eye.distance"].value == 5.0
    assert rig.loaded_patch.layout["render:camera"] == CAMERA_AT and rig.loaded_patch.notes == []
    rig.loaded_patch.load("DIAL")                                      # a /9: its own eye
    assert reg["eye.fov"].value == pytest.approx(G.EYE_FOV)
    rig.loaded_patch.load("OLD")
    saved = json.loads(rig.loaded_patch.save_as("OLD").read_text())
    assert saved["schema"] == loadable.SAVE_SCHEMA
    assert {k: saved["values"][k] for k in EYE} == EYE
    assert saved["layout"]["render:camera"] == CAMERA_AT
    # the show: written without the eye, the old file kept first
    show = home / "projects" / "rig.hyp.json"
    before = show.read_bytes()
    pr.save()
    doc = json.loads(show.read_text())
    assert not any(k.startswith("eye.") for k in doc["tuning"])
    assert "render:camera" not in doc.get("layout", {})
    bak = home / "projects" / "rig.hyp.json.bak-v2-eye"
    assert bak.read_bytes() == before
    pr.save()
    # (plan 44 D3: a /2 show's first write keeps it as .bak-v2-look too)
    assert sorted(p.name for p in show.parent.glob("rig.hyp.json.bak-*")) == [
        bak.name, "rig.hyp.json.bak-v2-look"]
    # a fresh launch: the show holds no eye now, but its `.bak-v2-eye` does
    # — still handed to old loadable patches (review 2.2) — and the /9 carries its own
    again = boot(home, show="rig")
    assert again.lib.install.old_eye == EYE and again.lib.install.camera_at == CAMERA_AT
    assert not any(k.startswith("eye.") for k in again.lib.install.session)
    again.loaded_patch.load("OLD")
    assert again.reg["eye.fov"].value == 30.0 and again.reg["eye.distance"].value == 5.0


def test_a_bank_autosave_before_the_tool_still_hands_old_loadables_the_eye(tmp_path):
    """Review 2.2: the first write of an old show on this build (here the
    bank's autosave, `Project.write`) drops its eye into `.bak-v2-eye`; an
    old loadable patch opened on the next launch — before the tool ran — still
    takes that eye and the camera's position from the backup."""
    home = tmp_path / "lib"
    _write(home / "projects" / "rig.hyp.json", old_show())
    (home / "loadable").mkdir(parents=True)
    (home / "loadable" / "old.json").write_text(loadable.dumps({**old_loadable(), "name": "OLD"}))
    rig = boot(home, show="rig")
    rig.lib.install.put_slot(0, "OLD")                # a pad: the bank's autosave
    show = json.loads((home / "projects" / "rig.hyp.json").read_text())
    assert "eye.fov" not in show["tuning"]
    assert (home / "projects" / "rig.hyp.json.bak-v2-eye").is_file()
    again = boot(home, show="rig")
    assert again.lib.install.old_eye == EYE and again.lib.install.camera_at == CAMERA_AT
    again.reg["eye.fov"].set(90.0)
    again.loaded_patch.load("OLD")
    assert again.reg["eye.fov"].value == 30.0 and again.reg["eye.distance"].value == 5.0
    assert again.loaded_patch.layout["render:camera"] == CAMERA_AT


def test_the_tool_copies_nothing_when_nothing_it_reads_is_retapered(tmp_path, monkeypatch):
    """Review 2.7: a dry run reads the library itself (no retapered copy)
    — and since plan 44 D3 retired the desk templates, a left-over unmarked
    one makes no copy either: nothing a load reads is retapered."""
    tool = _tool()
    made = []
    real = tool.retapered_copy
    monkeypatch.setattr(tool, "retapered_copy", lambda *a: made.append(a) or real(*a))
    lib = _library(tmp_path)
    shutil.rmtree(lib / "desk")
    tool.main(["--library", str(lib)], picture=same_picture)
    assert made == []
    lib2 = _library(tmp_path / "two")
    tool.main(["--library", str(lib2)], picture=same_picture)
    assert made == []


def test_an_old_loadable_with_no_old_eye_takes_the_builds(tmp_path):
    """A show from C2 on (the corpus's) holds no eye: an old loadable patch lands
    the build's default, the picture it drew before."""
    rig = boot(tmp_path)
    rig.reg["eye.fov"].set(90.0)
    (tmp_path / "loadable" / "old.json").write_text(loadable.dumps({**old_loadable(), "name": "OLD"}))
    rig.loaded_patch.load("OLD")
    assert rig.lib.install.old_eye == {}
    assert rig.reg["eye.fov"].value == pytest.approx(G.EYE_FOV)
    assert rig.reg["eye.distance"].value == pytest.approx(G.EYE_DISTANCE)


def test_the_shows_mark_carries_its_old_eye(tmp_path):
    home = tmp_path / "lib"
    _write(home / "projects" / "rig.hyp.json", old_show())
    rig = boot(home, show="rig")
    pr = rig.lib.install
    mark = pr.mark()
    pr.old_eye, pr.camera_at = {}, None
    pr.remark(mark)
    assert pr.old_eye == EYE and pr.camera_at == CAMERA_AT


def test_show_without_eye_is_pure():
    doc = old_show()
    out = L.show_without_eye(doc)
    assert out["session"] == {"tempo.bpm": 128.0} and out["layout"] == {"device:apc40": [1, 2]}
    assert doc["session"]["eye.fov"] == 30.0                    # untouched
    assert L.show_without_eye(out) is None
    only = L.show_without_eye({**doc, "layout": {"render:eye": [3, 4]}})
    assert "layout" not in only


# ---------------------------------------------------------------- the eye: modulatable, on GRAPH, held


def test_a_hand_axis_learns_onto_the_eye_and_breathes_the_framing(tmp_path):
    """Row 574 (row 182 overturned): Learn and the referee accept a
    performer on the eye; a lane's offset rides on the base, in the fov's
    own linear range (its taper unchanged, review 4)."""
    chain = Analyzer(Analyser())
    view = ViewState()
    reg = build_registry(view, Control(chain), NS(chain=chain), L.Library(tmp_path).install)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    lrn = Learn(reg, table)
    for pid, axis in (("eye.fov", "hand:right.y"), ("eye.distance", "hand:left.y")):
        lrn.arm(pid, axis.partition(".")[0])
        lrn.learn_source(axis)
        assert not lrn.refused and table.owner(pid).source == axis, (pid, lrn.last)
    p = reg["eye.fov"]
    base = p.base
    p.modulate(0.1)
    p.apply()
    assert view.eye_fov == pytest.approx(base + 0.1 * (p.hi - p.lo), rel=1e-6)
    assert p.base == pytest.approx(base)
    p.apply()                                                    # let go: the base back
    assert view.eye_fov == pytest.approx(base)


def test_a_layer_is_in_the_world_only_when_laid_depth_aware():
    """Review 2.1: `HandsLayer.in_world` — laid depth-aware at an output
    (`laid` "depth") or by a depth composite (`depth_laid`, set by the
    build) — and nothing else."""
    from hyperspace.graph import HandsLayer
    layer = HandsLayer("hands.layer")
    assert not layer.in_world
    for laid in ("over", "add"):
        layer.laid = laid
        assert not layer.in_world
    layer.laid = "depth"
    assert layer.in_world
    other = HandsLayer("hands.2.layer")
    other.depth_laid = True
    assert other.in_world


def test_a_fresh_hands_layer_has_its_downstream():
    """Review 3.2: `HandsLayer.__init__` sets `downstream` (the effects
    reading it, `_Build._split`) — the `in_world` property sits after it."""
    from hyperspace.graph import HandsLayer
    layer = HandsLayer("hands.layer")
    assert layer.downstream == () and layer.readout == "downstream"
    assert layer.depth_laid is False and not layer.in_world


def test_the_layer_behind_a_picture_is_found_through_every_pass():
    """Review 3.3: one walk (`graph.layers_behind`) for how a layer is laid
    on at an output and for which layer a depth composite lays — through
    an effect, a resize, a switch's inputs and a delay's write — so a
    layer behind a resize laid depth-aware is marked in the world too."""
    from hyperspace import graph as gr
    layer = gr.HandsLayer("hands.layer")
    layer.laid = "depth"
    resized = gr.ResizeNode("resize", image=layer)
    assert gr.layers_behind(resized) == [layer]
    assert gr._laid_of(resized) == "depth"
    warped = gr.Effect("warp", image=resized)
    assert gr.layers_behind(warped) == [layer]
    other = gr.HandsLayer("hands.2.layer")
    switch = gr.SwitchNode("switch", in1=warped, in3=other)
    assert gr.layers_behind(switch) == [layer, other]
    write = gr.DelayWrite("delay#write", "delay", image=switch)
    read = gr.Delay("delay")
    assert gr.layers_behind(read) == []                        # (no write map: unknown)
    assert gr.layers_behind(read, {"delay": write}) == [layer, other]
    assert gr.layers_behind(gr.ResizeNode("r2", image=None)) == []
    loop = gr.ResizeNode("loop")                                 # a cycle ends
    loop.inputs["image"] = loop
    assert gr.layers_behind(loop) == []


def test_one_reader_of_a_shows_camera_and_its_backup_is_remembered(tmp_path):
    """Reviews 3.4 and 3.5: `library.show_eye` is the one reader of what a
    show kept of the camera (`kept_eye` reads the backups with it,
    `headless.show_seed` builds its seed with it); `kept_eye` remembers what
    it found per show file and folder state — a copy rewritten in place is
    not read again — and looks again once the folder changes."""
    assert L.show_eye(old_show()) == (EYE, CAMERA_AT)
    assert L.show_eye({"layout": {"render:eye": [3, 4]}}) == ({}, [3, 4])
    assert L.show_eye(None) == ({}, None)
    assert headless.show_seed({"session": {}}, EYE, CAMERA_AT)["session"] == EYE
    show = _write(tmp_path / "projects" / "rig.hyp.json", {"session": {}})
    assert L.kept_eye(show) == ({}, None)
    bak = _write(tmp_path / "projects" / "rig.hyp.json.bak-v2-eye", old_show())
    assert L.kept_eye(show) == (EYE, CAMERA_AT)               # (a new file: looked again)
    mtime = bak.parent.stat().st_mtime_ns
    bak.write_text("not json")                                 # in place: the folder stands
    os.utime(bak.parent, ns=(mtime, mtime))
    assert L.kept_eye(show) == (EYE, CAMERA_AT)               # remembered, not re-read
    bak.unlink()
    assert L.kept_eye(show) == ({}, None)


def test_nine_leaves_values_that_are_no_map_to_the_load():
    """Review 3.7: a `values` that is no map is left as it is (the load's
    own reading refuses or reads it); a non-number eye is never written."""
    odd = {"schema": "hyperspace.preset/7", "values": ["not", "a", "map"]}
    assert graphmigrate.nine(odd, EYE)["values"] == ["not", "a", "map"]
    out = graphmigrate.nine({"schema": "hyperspace.preset/7", "values": {}},
                            {"eye.fov": "wide", "eye.distance": 5.0, "tempo.bpm": 1.0})
    assert out["values"] == {"eye.distance": 5.0}


def test_the_camera_node_is_the_looks():
    """GRAPH: the camera is no fixture node any more — its position is the
    loadable patch's and its refusal says it is the look's one camera."""
    assert "camera" not in graphview.FIXTURE_KINDS and "camera" in graphview.ALWAYS_KINDS
    cam = graphview.VNode("render:camera", "render", "Camera")
    assert graphview.home(cam) == graphview.PATCH_SECTION
    got, why = graphview.spec_name("render:camera")
    assert got is None and why == graphview.CAMERA_KEPT.format(label="Camera")


def test_the_hands_calibration_is_the_meta_reference_eye():
    """Row 575, no GL: the box is fitted into the world against the rig's
    reference eye whatever the loadable patch's; through a zoomed eye the hands'
    picture scales about the centre as the shape's does (the scene's
    camera), and the reference eye's picture — a layer's — does not move."""
    import inspect
    m, box = ghost.basis("desktop"), ghost.box_of(None)
    # no argument takes an eye: nobody can pass the loadable patch's back in
    assert list(inspect.signature(ghost.calibration).parameters) == ["box", "m", "units"]
    ref = ghost.calibration(box, m)
    cal_zoomed = ghost.through_eye(ref, m, 1.6, 30.0)
    assert np.allclose(cal_zoomed[0], ghost.shared_camera(box, m, 1.6, fov=30.0)[0])
    lo, hi = ghost.stage_box(box, m)
    pts = np.array([lo, hi, (lo + hi) / 2 + [30.0, 20.0, 0.0]])

    def ndc(vp, q):
        c = np.c_[q, np.ones(len(q))] @ vp.T
        return c[:, :2] / c[:, 3:4]

    base, _ = ghost.shared_camera(box, m, 1.6)
    zoomed, _ = ghost.shared_camera(box, m, 1.6, fov=30.0)
    ratio = math.tan(math.radians(G.EYE_FOV) / 2) / math.tan(math.radians(30.0) / 2)
    assert ndc(zoomed, pts) == pytest.approx(ndc(base, pts) * ratio)
    # the shape's points through the same two eyes scale by the same ratio
    world = np.array([[1.0, 0.0, 0.0, 1.0], [0.0, -0.7, 0.0, 1.0]])
    a = world @ G.eye_matrix(1.6, 1.0).T
    b = world @ G.eye_matrix(1.6, 1.0, 30.0).T
    assert b[:, :2] / b[:, 3:] == pytest.approx(a[:, :2] / a[:, 3:] * ratio)


def test_the_ghost_fits_its_calibration_once_until_the_meta_changes(monkeypatch):
    """Review 7: `Ghost.calibrated` fits once and keeps it while the box,
    the basis and the units stand — whatever the eye or the output's shape
    — and fits again when one of them moves."""
    from hyperspace.hands import core as hc
    fits = []
    real = ghost.calibration
    monkeypatch.setattr(ghost, "calibration", lambda *a: fits.append(a) or real(*a))
    gh = ghost.Ghost.__new__(ghost.Ghost)            # no GL: the cache alone
    m, box = ghost.basis("desktop"), ghost.box_of(None)
    a = gh.calibrated(box, m)
    for _ in range(3):
        assert gh.calibrated(box, m) is a
    assert len(fits) == 1
    gh.calibrated(box, ghost.basis("desktop", True))        # the mirror
    u = hc.Units(mm=150.0, origin=(0.0, 200.0, 0.0), tilt=10.0)
    gh.calibrated(box, m, u)
    gh.calibrated(box, m, u)
    gh.calibrated(((-1.0, 1.0), (0.0, 2.0), (-1.0, 1.0)), m, u)  # another box
    assert len(fits) == 4


# ---------------------------------------------------------------- the migration tool


def _tool():
    if "migrate_library" in sys.modules:
        return sys.modules["migrate_library"]
    spec = importlib.util.spec_from_file_location("migrate_library",
                                                  ROOT / "tools" / "migrate_library.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_library"] = mod
    spec.loader.exec_module(mod)
    return mod


def same_picture(path, *, library=None, show=None):
    return ["x"] * 8, []


def _library(tmp_path: Path) -> Path:
    """A library like the owner's before C2: an old show holding the eye,
    two `/7` loadable patches (one with the taper marker, one without), a `/9`
    already, a patch and a desk template from before the tapers."""
    lib = tmp_path / "Drive" / "Hyperspace"
    loadable_dir = lib / "loadable"
    loadable_dir.mkdir(parents=True)
    (loadable_dir / "trip-old.json").write_text(loadable.dumps(old_loadable()))
    (loadable_dir / "trip-unmarked.json").write_text(
        loadable.dumps({**old_loadable(marked=False), "name": "TRIP UNMARKED"}))
    shutil.copyfile(CORPUS / "loadable" / "dial.json", loadable_dir / "dial.json")
    _write(lib / "projects" / "rig.hyp.json", old_show())
    (lib / "patches").mkdir()
    shutil.copyfile(OLD_PATCH, lib / "patches" / "acid-wash.json")
    # (plan 44 D3: a desk template left over — never read, never rewritten)
    _write(lib / "desk" / "old-desk.json", {"schema": "hyperspace.desk/1", "name": "old desk",
                                            "desk": [{"source": "cc:0:49", "target":
                                                      "fx.warp.speed", "op": "set",
                                                      "value": 0.75}]})
    return lib


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file()}


def test_the_tool_retapers_backs_up_and_moves_the_eye_into_every_loadable(tmp_path, capsys):
    """The whole bump over a scratch copy: a dry run writes nothing and says
    the show, its eye, the retaper and the shows it would rewrite; --apply
    backs the library up first, retapers the patch and the desk template,
    writes every old loadable patch as `/9` with the show's eye and camera position
    (no pose: they keep spinning), leaves the `/9` alone, and rewrites the
    show without the eye beside its ``.bak-v2-eye``. A second run finds
    nothing to do — and reads the eye from that backup."""
    lib = _library(tmp_path)
    home = Path(os.environ["HYPERSPACE_HOME"])
    before = _tree(lib)
    tool = _tool()
    assert tool.main(["--library", str(lib)], picture=same_picture) == 0
    out = capsys.readouterr().out
    assert _tree(lib) == before and not list(home.glob("library-backup-*"))
    assert "show: rig (the library's one show) — eye.distance 5, eye.fov 30" in out
    assert "retaper first: 1 document(s)" in out and "patch acid-wash.json" in out
    assert "desk old-desk.json" not in out                  # (plan 44 D3: retired)
    assert "show rig.hyp.json → installs/rig.json" in out
    assert "would rewrite 2 as /11, leave 1 untouched (already /11), skip 0" in out
    assert tool.main(["--library", str(lib), "--apply"], picture=same_picture) == 0
    out = capsys.readouterr().out
    backups = list(home.glob("library-backup-*"))
    assert len(backups) == 1 and f"backup: {backups[0]}" in out
    assert _tree(backups[0]) == before
    for name in ("trip-old", "trip-unmarked"):
        doc = json.loads((lib / "loadable" / f"{name}.json").read_text())
        assert doc["schema"] == loadable.SAVE_SCHEMA, name
        assert {k: doc["values"][k] for k in EYE} == EYE, name
        assert doc["layout"]["render:camera"] == CAMERA_AT, name
        assert loadable.POSE_KEY not in doc, name
        assert doc["units"]["fx.depth"] == "taper", name
    assert (lib / "loadable" / "dial.json").read_bytes() == before["loadable/dial.json"]
    show = json.loads((lib / "installs" / "rig.json").read_text())
    assert show["tuning"] == {"tempo.bpm": 128.0} and show["layout"] == {"device:apc40": [1, 2]}
    assert show["schema"] == "hyperspace.install/1" and "rig" not in show
    assert not (lib / "projects").exists()                     # (the backup holds the show)
    assert json.loads((lib / "patches/acid-wash.json").read_text())["units"]["fx.depth"] == \
        "taper"
    assert (lib / "desk/old-desk.json").read_bytes() == before["desk/old-desk.json"]
    assert "retapered 1 document(s)" in out and "rewrote 2 as /11" in out
    assert "wrote 1 install file(s)" in out
    # once more: nothing to do
    after = _tree(lib)
    assert tool.main(["--library", str(lib), "--apply"], picture=same_picture) == 0
    out = capsys.readouterr().out
    assert "retaper first" not in out and "show rig" not in out
    assert "nothing to do" in out
    assert _tree(lib) == after


def test_the_tool_takes_the_named_or_last_show_and_refuses_an_unknown_one(tmp_path, capsys):
    lib = _library(tmp_path)
    _write(lib / "projects" / "other.hyp.json", {**old_show(), "session": {"eye.fov": 70.0}})
    home = Path(os.environ["HYPERSPACE_HOME"])
    tool = _tool()
    assert tool.main(["--library", str(lib)], picture=same_picture) == 0
    assert "show: none (2 shows and none is this Mac's last" in capsys.readouterr().out
    home.mkdir(parents=True, exist_ok=True)
    (home / "last_install").write_text("other\n")
    tool.main(["--library", str(lib)], picture=same_picture)
    assert "show: other (this Mac's last show) — eye.fov 70" in capsys.readouterr().out
    tool.main(["--library", str(lib), "--show", "rig"], picture=same_picture)
    assert "show: rig (--show)" in capsys.readouterr().out
    assert tool.main(["--library", str(lib), "--show", "nope"], picture=same_picture) == 2


def test_the_tool_draws_the_old_file_with_the_show_open_as_its_nine(tmp_path, capsys):
    """The round trip's picture with the golden rig itself (no stand-in):
    an old `/7` with the old show open draws what its `/9` draws — and not
    what it draws with no show (the eye is in the picture)."""
    pytest.importorskip("moderngl")
    sys.path.insert(0, str(ROOT / "tools"))
    import golden_frames
    try:
        golden_frames.context()
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    old = _write(tmp_path / "old" / "trip-old.json", old_loadable())
    seed = headless.show_seed(old_show())
    data, _, _ = headless.resave(old, tmp_path / "scratch", show=seed)
    nine = tmp_path / "nine" / "trip-old.json"
    nine.parent.mkdir()
    nine.write_bytes(data)
    kw = {"slug": "lib-trip-old", "states": golden_frames.SHIPPED}
    with_show, _ = golden_frames.picture(old, show=seed, **kw)
    assert golden_frames.picture(nine, **kw)[0] == with_show
    assert golden_frames.picture(old, **kw)[0] != with_show
    # the rig's GL objects went with the picture: collected later, on a test's
    # own context, they would delete that context's objects of the same names
    released = []
    moderngl = sys.modules["moderngl"]
    with pytest.MonkeyPatch.context() as m:
        m.setattr(moderngl.VertexArray, "release", lambda self: released.append(self))
        gc.collect()
    assert released == []


# ---------------------------------------------------------------- the hands, drawn (GL)


def _shot(ctx, r, eye_fov):
    """Four frames of `draw_outputs` with the eye at `eye_fov`: output 1."""
    from test_outputs import H, W, px, scene_view, views

    from hyperspace import outputs as O
    s = scene_view()
    s.lines, s.bright = True, 1.6
    if getattr(r, "_no_shape", False):
        s.instances = 0
    s.eye_fov = eye_fov
    vs = views(ctx, O.Switches())
    for k in range(4):
        s.ang = [a + 0.05 for a in s.ang]
        r.draw_outputs(s, W, H, 1.0, vs, t_now=2.0 + k / 30)
    assert ctx.error == "GL_NO_ERROR"
    return px(ctx, vs[0].target)


def _span(pic) -> tuple[int, int]:
    """The width and height of what was drawn over the black ground."""
    ys, xs = np.nonzero(np.abs(pic[..., :3]).sum(axis=2) > 0)
    assert len(xs) > 50
    return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def test_hands_in_the_scene_scale_with_the_shape_and_a_layer_keeps_its_size(ctx):
    """Row 575 / hand check 433, drawn: widening the loadable patch's eye (47.6° →
    60°, out, so nothing leaves the frame) shrinks the shape, and the hands
    drawn in the scene shrink with it by the same ratio; the hands drawn
    as a layer are the same picture, pixel for pixel, whatever the eye."""
    from test_hands_node import _rig

    from hyperspace.graph import Wiring
    wide = 60.0
    ratio = math.tan(math.radians(G.EYE_FOV) / 2) / math.tan(math.radians(wide) / 2)
    shape = [_span(_shot(ctx, _rig(ctx, None, hands=False), f)) for f in (G.EYE_FOV, wide)]
    scene = [_span(_shot(ctx, _rig(ctx, Wiring(hands="scene"), shape=False), f))
             for f in (G.EYE_FOV, wide)]
    for (w0, h0), (w1, h1) in (shape, scene):
        assert w1 / w0 == pytest.approx(ratio, rel=0.06)
        assert h1 / h0 == pytest.approx(ratio, rel=0.06)
    layer = [_shot(ctx, _rig(ctx, None, shape=False), f) for f in (G.EYE_FOV, wide)]
    assert np.array_equal(layer[0], layer[1]) and _span(layer[0])[0] > 20


def test_a_layer_laid_depth_aware_is_in_the_world_through_the_loadables_eye(ctx):
    """Review 2.1 (the ruling): a hands layer laid depth-aware compares its
    depth with the scene's, so it is drawn through the scene's eye — it
    scales with the shape as the eye widens, and behind the shape at a
    non-default eye the texels it hides show the picture under them
    exactly (one projection for both depths). Laid plain over it keeps the
    reference eye (the test above)."""
    from test_hands_node import BEHIND, _rig

    from hyperspace.graph import Wiring
    wide = 60.0
    ratio = math.tan(math.radians(G.EYE_FOV) / 2) / math.tan(math.radians(wide) / 2)
    alone = [_span(_shot(ctx, _rig(ctx, Wiring(blend="depth"), shape=False), f))
             for f in (G.EYE_FOV, wide)]
    (w0, h0), (w1, h1) = alone
    assert w1 / w0 == pytest.approx(ratio, rel=0.06) and h1 / h0 == pytest.approx(ratio, rel=0.06)
    depth = _shot(ctx, _rig(ctx, Wiring(blend="depth"), BEHIND), wide)
    over = _shot(ctx, _rig(ctx, Wiring(hands="scene"), BEHIND), wide)   # (in the scene)
    bare = _shot(ctx, _rig(ctx, None, BEHIND, hands=False), wide)
    hidden = np.abs(depth - bare).sum(axis=2) == 0
    drawn = np.abs(over - bare).sum(axis=2) > 0                          # where hands fall
    assert (hidden & drawn).sum() > 50   # behind the shape, hidden where the shape is nearer


# ---------------------------------------------------------------- review fixes


def test_a_pose_at_the_edge_of_the_turn_saves_loads_and_saves_as_itself(tmp_path):
    """Review 1: an angle at or near ±π (or any turn past it) is written
    strictly inside (−π, π) and save → load → save is a fixed point — so
    the migration's fixed-point check and the file never flip sign."""
    edges = [math.pi, -math.pi, math.pi - 1e-7, -math.pi + 1e-7, 3.1415925, -3.1415925,
             7 * math.pi, -5 * math.pi, 2.5, -2.5, 0.0, 1e-9]
    for a in edges:
        b = loadable.pose_angle(a)
        assert loadable.pose_angle(b) == b and b == round(b, 6), a
        if -math.pi <= a <= math.pi:                 # a folded road's angle
            assert -math.pi < b < math.pi and math.remainder(b, 2 * math.pi) == b, a
    rig = boot(tmp_path)
    for k in range(0, len(edges), 6):
        rig.view.set_pose((edges[k:k + 6] + [0.0] * 6)[:6])
        one = rig.loaded_patch.document("EDGE")
        rig.loaded_patch.load_doc(one)
        two = rig.loaded_patch.document("EDGE")
        assert two[loadable.POSE_KEY] == one[loadable.POSE_KEY]
        assert loadable.dumps(two) == loadable.dumps(one)


def test_one_picture_saves_one_pose_and_save_load_save_is_byte_stable(tmp_path):
    """Review 2.4: a 3D shape saves its folded XY/XZ/YZ and W 0 whether a
    body was ever turned in or not; a 4D shape saves the same six whether
    the 3D switch was ever toggled or not (one branch for one turn); a
    scene saves its angles unfolded (its layers spin at fractions of them).
    Each, saved, loaded (a frame integrated, the switch folding a fresh
    body) and saved again, writes the same bytes."""
    rig = boot(tmp_path)
    reg, view = rig.reg, rig.view
    four = next(i for i in range(len(G.SHAPES)) if not G.is_3d(i) and not G.SHAPES[i].layers)
    three = next(i for i in range(len(G.SHAPES)) if G.is_3d(i) and not G.SHAPES[i].layers)
    scene = next(i for i in range(len(G.SHAPES)) if G.SHAPES[i].layers)
    ang = [2.9, -2.2, 3.0, 2.4, -1.9, 2.6]

    def save_load_save(three_d: bool) -> dict:
        reg["view.rotate"].set(False)
        reg["view.three_d"].set(three_d)
        one = rig.loaded_patch.document("P")
        rig.loaded_patch.load_doc(one)
        view.integrate(0.0)                       # a frame: the switch folds a body
        two = rig.loaded_patch.document("P")
        assert loadable.dumps(two) == loadable.dumps(one)
        return one[loadable.POSE_KEY]

    for shape in (three, four):
        reg["view.shape"].set(shape)
        poses = []
        for toggled in (False, True):
            view.set_pose(ang)
            if toggled:                           # the switch on and off: a body turned in
                view.three_d = True
                view.integrate(0.0)
                view.ang[:3] = [a + 0.0 for a in ang[:3]]
            poses.append(save_load_save(toggled))
        if shape == three:
            assert poses[0] == poses[1]
            assert [poses[0][k] for k in POSE_IDS[3:]] == [0.0, 0.0, 0.0]
        else:                         # (review 3.1: a body folds through the matrix,
            pics = []                 # its branch its own — one picture either way)
            for p in poses:
                w = ViewState(shape=shape)
                w.set_pose([p[k] for k in POSE_IDS])
                pics.append(G.shape_view(shape, w.ang, 0.0, 0.0, flat=w.held, body=w.body)[:2])
            assert all(np.allclose(a, b, atol=1e-3) for a, b in zip(*pics))
    reg["view.shape"].set(scene)
    view.set_pose([a + 40.0 for a in ang])        # a long run: far past one turn
    pose = save_load_save(False)
    assert pose[POSE_IDS[0]] == pytest.approx(ang[0] + 40.0)


@pytest.mark.parametrize("plane", range(6))
def test_a_loaded_pose_turns_on_as_the_saved_shape_did(plane):
    """Review 3.1: an angle past π/2 on any plane (cos < 0) saves as that
    plane's own fold, not another Euler branch of the same matrix — so
    after a load the integrator turns every plane the way it turned:
    save → load → one frame draws what the unloaded shape draws a frame on."""
    shape = next(i for i in range(len(G.SHAPES)) if not G.is_3d(i) and not G.SHAPES[i].layers)
    ang = [0.1] * 6
    ang[plane] = 2.0
    v = ViewState(shape=shape, ang=list(ang), planes=[True] * 6)
    w = ViewState(shape=shape, planes=[True] * 6)
    w.set_pose([loadable.pose_angle(a) for a in v.pose()])
    assert w.ang == pytest.approx(ang, abs=1e-6)
    for s in (v, w):
        s.integrate(0.25)
    a = G.shape_view(shape, v.ang, 0.0, 0.0, flat=v.held, body=v.body)[:2]
    b = G.shape_view(shape, w.ang, 0.0, 0.0, flat=w.held, body=w.body)[:2]
    assert all(np.allclose(x, y, atol=1e-2) for x, y in zip(a, b))


def test_an_old_show_with_the_camera_under_its_old_id_and_no_eye(tmp_path):
    """Reviews 2 and 3: a show whose layout holds the camera under the old
    canvas id (`render:eye`) and whose meta controller holds no eye — the position
    is the old loadable patches' (`camera_at`), never the show's; its write drops it
    and keeps the file first as ``.bak-v2-eye``."""
    home = tmp_path / "lib"
    show = _write(home / "projects" / "rig.hyp.json",
                  {**old_show(), "session": {"tempo.bpm": 128.0},
                   "layout": {"render:eye": [7, 8], "device:apc40": [1, 2]}})
    before = show.read_bytes()
    rig = boot(home, show="rig")
    pr = rig.lib.install
    assert pr.camera_at == [7, 8] and pr.old_eye == {}
    assert not any(k in pr.layout for k in graphmigrate.CAMERA_NODES)
    assert L.show_without_eye(json.loads(before)) is not None
    pr.save()
    doc = json.loads(show.read_text())
    assert doc["layout"] == {"device:apc40": [1, 2]}
    assert (home / "projects" / "rig.hyp.json.bak-v2-eye").read_bytes() == before
    assert headless.show_seed(json.loads(before)) == {
        "schema": L.PROJECT_V2, "name": headless.SEED_SHOW, "session": {},
        "layout": {"render:camera": [7, 8]}}


def test_a_show_with_nothing_of_the_camera_seeds_nothing(tmp_path, monkeypatch, capsys):
    """Review 6: `show_seed` is None when a show kept no eye and no camera
    position (or there is no show), so the tool's resaves open no scratch
    show and its "the build's default" line is what happens; with an eye
    every resave opens the seed."""
    assert headless.show_seed(None) is None
    assert headless.show_seed({"schema": L.PROJECT_SCHEMA, "session": {"tempo.bpm": 1.0}}) is None
    assert headless.show_seed(old_show())["session"] == EYE
    lib = _library(tmp_path)
    _write(lib / "projects" / "rig.hyp.json", {**old_show(), "session": {}, "layout": {}})
    seen = []
    real = headless.resave

    def resave(path, scratch, **kw):
        seen.append(kw.get("show"))
        return real(path, scratch, **kw)

    monkeypatch.setattr(headless, "resave", resave)
    tool = _tool()
    tool.main(["--library", str(lib)], picture=same_picture)
    assert "show: rig (the library's one show) — no eye nor look (the build's defaults)" in \
        capsys.readouterr().out
    assert seen and all(s is None for s in seen)
    seen.clear()
    _write(lib / "projects" / "rig.hyp.json", old_show())
    tool.main(["--library", str(lib)], picture=same_picture)
    assert seen and all(s is not None and s["session"] == EYE for s in seen)
