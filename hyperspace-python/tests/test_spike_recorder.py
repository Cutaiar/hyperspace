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
