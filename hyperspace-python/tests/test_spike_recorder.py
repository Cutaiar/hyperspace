"""tools/spike_recorder.py and spike_run.py: the pieces that need no window.
(Run end to end by hand: `uv run python tools/spike_run.py PATCH --rounds 2
--block 80`, which this suite cannot do without the real app loop.)"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import spike_recorder as sr


def _doc(n=1200, seed=0):
    """A recording where every 30th frame is slow because field_range ran."""
    rng = np.random.default_rng(seed)
    base = 12 + rng.normal(0, 0.5, n)
    spike = np.zeros(n)
    spike[::30] = 25
    cols = {"total": base + spike, "frame_fn": base + spike - 2, "outside": np.full(n, 2.0),
            "field_range": spike, "thumbs": spike + 1, "draw_render": base + spike - 3,
            "gc": np.zeros(n), "gc_n": np.zeros(n)}
    block = np.repeat(np.arange(n // 200), 200)
    since = np.tile(np.arange(200), n // 200)
    conds = ["base", "readback_off", "base", "readback_off", "base", "readback_off"]
    # readback_off blocks have no spikes
    for b, c in enumerate(conds):
        if c == "readback_off":
            m = block == b
            for k in ("total", "frame_fn", "field_range", "thumbs", "draw_render"):
                cols[k][m] = cols[k][m] - spike[m]
    return {"schema": "hyperspace.spikes/1", "meta": {"patch": "synthetic"},
            "conditions": list(sr.CONDITIONS),
            "blocks": [{"id": i, "cond": c, "round": i // 2, "start": i * 200}
                       for i, c in enumerate(conds)],
            "block": block.tolist(), "since": since.tolist(),
            "cols": {k: np.round(v, 3).tolist() for k, v in cols.items()}}


def test_the_report_names_the_planted_cause_and_the_switch_that_removes_it():
    out: list[str] = []
    sr.report(_doc(), out.append)
    text = "\n".join(out)
    grown = [ln.split()[0] for ln in text.splitlines() if ln.startswith("  ") and "%" in ln]
    assert "field_range" in grown[:4], text
    assert "30f" in text                                  # the spacing of the slow frames
    row = next(ln for ln in out if "readback_off" in ln and "median" in ln and "p95" in ln)
    assert float(row.split("p99")[1].split()[0]) < -10, row    # the tail got shorter, in words


def test_hooks_install_and_come_off_whole():
    from hyperspace import app, fractal, fx, outputs, render, undo
    before = (app.frame, undo.Undo.tick, render.Renderer.draw_scene, fx.FxChain.field_range,
              outputs.PreviewTextures._copy, fractal.walk, render._thumb_gain)
    rec = sr.Recorder()
    rec.install()
    assert app.frame is not before[0] and undo.Undo.tick is not before[1]
    rec.uninstall()
    assert before == (app.frame, undo.Undo.tick, render.Renderer.draw_scene,
                      fx.FxChain.field_range, outputs.PreviewTextures._copy, fractal.walk,
                      render._thumb_gain)
    import gc
    assert gc.isenabled() and not [c for c in gc.callbacks if getattr(c, "__name__", "") == "collected"]


def test_the_switches_answer_in_place_of_the_real_call(monkeypatch):
    from hyperspace import outputs
    rec = sr.Recorder()
    rec.install()
    try:
        th = outputs.PreviewTextures.__new__(outputs.PreviewTextures)
        rec.flags["thumbs_off"] = True
        assert outputs.PreviewTextures.take(th) == {}
    finally:
        rec.uninstall()


def test_the_runner_never_writes_beside_the_patch(tmp_path):
    """Read in the code, held here: the one write that names the patch is a
    copy *to* the scratch home, and nothing else opens it for writing."""
    src = (TOOLS / "spike_run.py").read_text()
    assert "copyfile(a.patch, scratch)" in src
    assert "a.patch.write" not in src and "open(a.patch" not in src


def test_the_run_is_not_cut_short_by_a_frame_budget(monkeypatch, tmp_path):
    """The owner's first run on the Mac stopped in round 4 of 5: the app was
    told to quit after `warmup frames + blocks + 1200`, but the warm-up is
    counted in seconds (45 s is ~3,400 frames at 75 fps), so the budget ran
    out early. The script closes the app itself; no frame budget may."""
    import os

    import spike_run

    class Stop(Exception):
        pass

    seen = {}

    def run(*a, **k):
        seen["cap"] = os.environ.get("HYPERSPACE_FRAMES")
        raise Stop

    patch = tmp_path / "p.json"
    patch.write_text("{}")
    monkeypatch.delenv("HYPERSPACE_FRAMES", raising=False)
    monkeypatch.setattr(spike_run.app_driver, "run", run)
    monkeypatch.setattr(sys, "argv", ["spike_run", str(patch), "--out", str(tmp_path / "o")])
    try:
        spike_run.main()
    except Stop:
        pass
    cap = int(seen["cap"])
    assert cap == 0 or cap >= 10**7, seen          # 0: the app's "no limit"


def test_a_condition_that_slows_every_frame_does_not_write_the_slow_table():
    """The owner's first run: `additive_flip` doubled the frame (21.8 ms against
    10.7), so the slowest 5% of the pooled run were its frames and the table
    blamed whatever that path costs. The table is of the base blocks (and any
    conditions named), not of the pool."""
    n = 1200
    rng = np.random.default_rng(1)
    base = 10 + rng.normal(0, 0.4, n)
    block = np.repeat(np.arange(6), 200)
    since = np.tile(np.arange(200), 6)
    conds = ["base", "additive_flip", "base", "additive_flip", "base", "additive_flip"]
    flip = np.isin(block, [1, 3, 5])
    spike = np.zeros(n)
    spike[::30] = 20                                # a read-back stall every 30th frame
    cols = {"total": base + spike + np.where(flip, 12.0, 0.0), "field_range": spike,
            "sort_cost": np.where(flip, 12.0, 0.0), "frame_fn": base, "outside": np.ones(n)}
    doc = {"meta": {"patch": "s"}, "conditions": list(sr.CONDITIONS),
           "blocks": [{"id": i, "cond": c, "round": i // 2, "start": i * 200}
                      for i, c in enumerate(conds)],
           "block": block.tolist(), "since": since.tolist(),
           "cols": {k: np.round(v, 3).tolist() for k, v in cols.items()}}
    out: list[str] = []
    sr.report(doc, out.append)
    text = "\n".join(out)
    table = text.split("Which parts grew:")[1].split("(parts nest")[0]
    first = [ln.split()[0] for ln in table.splitlines() if ln.strip()][1:4]
    assert "field_range" in first and "sort_cost" not in first, text
    sr.report(doc, out.append, conds=("base", "additive_flip"))     # the pooled table, asked for
