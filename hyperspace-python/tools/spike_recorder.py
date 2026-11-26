"""A low-overhead per-frame recorder for the frame-time spikes (median ~15 ms,
p95 ~40 ms on the owner's Mac), and the report that says which parts grew in
the slow frames. Run it with `tools/spike_run.py`; this file is the hooks and
the report, and `python tools/spike_recorder.py FILE.json [base,gc_frozen]` reprints a report
(its slow-frame tables of those conditions' blocks, default `base`).

What is recorded, per frame, in ms (all `time.perf_counter` wraps, nothing
sampled; a wrap costs ~0.2 µs):

  total        the whole loop turn: one `app.frame` entry to the next, so the
               poll, imgui's render, the swaps and the pacer are in it
  frame_fn     `app.frame` alone            outside   total less frame_fn, the
  draw_render  `Host.draw_render`                      swap of the control window
  draw_panel   `Host.draw_panel`: the panel and the    and the pacer: the loop's own
               driver's script step; panel_draw is `Panel.draw` alone,
               so draw_panel less panel_draw is the driver (app_driver)
  undo         `Undo.tick`, every stack
  graph        `Graph.evaluate`; node_<kind> its nodes' CPU time, by node kind
  draw_scene   `Renderer.draw_scene`   walk   `fractal.walk`
  thumbs       `Renderer._thumbnails`  field_range   `FxChain.field_range`,
               the synchronous read back   preview_copy  `PreviewTextures._copy`
  swap_<win>   `glfw.swap_buffers`, by window title      pacer   `Pacer.end_frame`
  gc           time in the collector (`gc.callbacks`), gc_n collections
  gil_late     only with `--gil`: a thread asks for 1 ms of sleep and says how
               late it woke, the most in the frame (another thread holding the GIL
               shows here; the probe is itself a thread, so it is a run of its own)
  cells_line, cells_face   the fractal walk's cells drawn (lines, solids)
  edges        line cells x the shape's new edges per cell
  gpu_total, gpu_scene     `renderer.stats["gpu_ms"]`: a rolling median over
               60 frames of GPU time, so it moves slowly (it is the *level*)

Nesting: draw_render holds graph holds node_* holds draw_scene holds walk, and
thumbs (`Renderer._thumbnails`) is inside draw_render too; draw_panel holds
panel_draw. gc and swap_* can fall inside any of them. The report says growth per column, so read it from the
outside in (outside, frame_fn, then what is in frame_fn).

Off-switches (`CONDITIONS`) run in long shuffled blocks, every condition in
every round, so slow drift (thermals, the OS) cancels: thumbs_off (no node
wants a thumbnail), readback_off (a field thumbnail keeps its last gain, no
`field_range` read), gc_frozen (`gc.disable` for the block), additive_flip
(`view.frac_additive` the other way: the GPU path against the CPU sort).
"""

from __future__ import annotations

import gc
import json
import platform
import sys
import threading
import time
from collections import Counter
from pathlib import Path

pc = time.perf_counter

SETTLE = 40          # frames at a block's start that belong to the switch, not the block
CONDITIONS = ("base", "thumbs_off", "readback_off", "gc_frozen", "additive_flip")


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.cur: dict = {}
        self.t_prev: float | None = None
        self.t_first: float | None = None
        self.cond, self.block, self.since = "warmup", -1, 0
        self.flags = {"thumbs_off": False, "readback_off": False}
        self.blocks: list[dict] = []
        self.titles: dict[int, str] = {}
        self.host = None
        self._gc_t = 0.0
        self.undone: list = []                 # (owner, name, original) to put back
        self.meta: dict = {}

    # ---- the row ----

    def add(self, name: str, dt: float) -> None:
        self.cur[name] = self.cur.get(name, 0.0) + dt * 1e3

    def set(self, name: str, v: float) -> None:
        self.cur[name] = v

    def begin_row(self, t0: float, h) -> None:
        self.host = h
        if self.t_prev is not None:
            row = self.cur
            row["total"] = (t0 - self.t_prev) * 1e3
            row["outside"] = row["total"] - row.get("frame_fn", 0.0)
            try:
                gm = h.renderer.stats.get("gpu_ms") or {}
                row["gpu_total"] = float(sum(gm.values()))
                row["gpu_scene"] = float(sum(v for k, v in gm.items() if "scene" in k))
            except Exception:  # noqa: BLE001, S110 — a stats shape that moved: no GPU columns
                pass
            row["block"], row["since"], row["cond"] = self.block, self.since, self.cond
            self.rows.append(row)
        self.since += 1
        if self.t_first is None:
            self.t_first = t0
        self.t_prev, self.cur = t0, {"t": t0 - self.t_first}

    # ---- hooks ----

    def wrap(self, owner, name: str, column: str | None = None, *, after=None, replace=None):
        """Replace `owner.name` with a timer around it (and, with `replace`, a
        function that may answer instead: `replace(orig, *a, **kw)`)."""
        orig = getattr(owner, name)
        rec = self

        def timed(*a, **kw):
            t = pc()
            try:
                if replace is not None:
                    return replace(orig, *a, **kw)
                r = orig(*a, **kw)
                if after is not None:
                    after(r)
                return r
            finally:
                if column is not None:
                    rec.add(column, pc() - t)

        timed.__wrapped__ = orig
        timed.__name__ = getattr(orig, "__name__", name)
        setattr(owner, name, timed)
        self.undone.append((owner, name, orig))

    def install(self) -> None:
        from hyperspace import app, fractal, fx, graph, outputs, pacing, render, undo

        rec = self
        orig_frame = app.frame

        def frame(h, now, dt, fps):
            t0 = pc()
            rec.begin_row(t0, h)
            if not getattr(h, "_spike_wrapped", False):
                h._spike_wrapped = True
                for nm, col in (("draw_render", "draw_render"), ("draw_panel", "draw_panel")):
                    f = getattr(h, nm)
                    setattr(h, nm, _timer(rec, col, f))
            try:
                return orig_frame(h, now, dt, fps)
            finally:
                rec.set("frame_fn", (pc() - t0) * 1e3)

        app.frame = frame
        self.undone.append((app, "frame", orig_frame))
        self.wrap(undo.Undo, "tick", "undo")
        self.wrap(render.Renderer, "draw_scene", "draw_scene")
        self.wrap(render.Renderer, "_thumbnails", "thumbs")
        self.wrap(fx.FxChain, "field_range", "field_range")
        self.wrap(outputs.PreviewTextures, "_copy", "preview_copy")
        self.wrap(pacing.Pacer, "end_frame", "pacer")
        from hyperspace import ui
        self.wrap(ui.Panel, "draw", "panel_draw")

        def walked(wk):
            rec.set("cells_line", float(len(wk.line_s)))
            rec.set("cells_face", float(len(wk.face_s)))
            try:
                rec.set("edges", float(len(wk.line_s) * len(wk.spec.new_E)))
            except Exception:  # noqa: BLE001, S110
                pass
        self.wrap(fractal, "walk", "walk", after=walked)

        # the thumbnails' off-switches: answer in place of the real call
        def take(orig, th, *a, **kw):
            return {} if rec.flags["thumbs_off"] else orig(th, *a, **kw)
        self.wrap(outputs.PreviewTextures, "take", None, replace=take)

        def gain(orig, frame, name, made):
            if rec.flags["readback_off"]:
                got = frame.r.__dict__.get("_field_gains", {}).get(name)
                return got[1] if got else 1.0
            return orig(frame, name, made)
        self.wrap(render, "_thumb_gain", None, replace=gain)

        # the graph, and each node's CPU time by kind
        orig_eval = graph.Graph.evaluate

        def evaluate(g, f):
            for node in g.order:
                if not getattr(node, "_spike", False):
                    node._spike = True
                    node.run = _timer(rec, "node_" + str(getattr(node, "KIND", "node")), node.run)
            t = pc()
            try:
                return orig_eval(g, f)
            finally:
                rec.add("graph", pc() - t)
        graph.Graph.evaluate = evaluate
        self.undone.append((graph.Graph, "evaluate", orig_eval))

        # each swap, by window (a title is read once per window)
        import glfw
        orig_swap = glfw.swap_buffers

        def swap(window):
            key = id(window)
            if key not in rec.titles:
                try:
                    t = (glfw.get_window_title(window) or "window").split("—")[-1].strip()
                except Exception:  # noqa: BLE001
                    t = "window"
                rec.titles[key] = "".join(c if c.isalnum() else "_" for c in t.lower())
            t = pc()
            try:
                return orig_swap(window)
            finally:
                rec.add("swap_" + rec.titles[key], pc() - t)
        glfw.swap_buffers = swap
        self.undone.append((glfw, "swap_buffers", orig_swap))

        # the collector, from outside: a callback at each start and stop
        def collected(phase, info):
            if phase == "start":
                rec._gc_t = pc()
            else:
                rec.add("gc", pc() - rec._gc_t)
                rec.cur["gc_n"] = rec.cur.get("gc_n", 0.0) + 1.0
        gc.callbacks.append(collected)
        self._gc_cb = collected
        self.meta["threads_start"] = sorted(t.name for t in threading.enumerate())

    def start_gil_probe(self) -> None:
        stop = self._gil_stop = threading.Event()

        def probe() -> None:
            while not stop.is_set():
                t = pc()
                time.sleep(0.001)
                late = (pc() - t - 0.001) * 1e3
                cur = self.cur
                if late > cur.get("gil_late", 0.0):
                    cur["gil_late"] = late

        threading.Thread(target=probe, name="spike-gil-probe", daemon=True).start()

    def uninstall(self) -> None:
        for owner, name, orig in reversed(self.undone):
            setattr(owner, name, orig)
        self.undone.clear()
        if getattr(self, "_gil_stop", None) is not None:
            self._gil_stop.set()
        if getattr(self, "_gc_cb", None) in gc.callbacks:
            gc.callbacks.remove(self._gc_cb)
        if not gc.isenabled():
            gc.enable()

    # ---- the blocks ----

    def start_block(self, cond: str, rnd: int) -> None:
        self.block += 1
        self.cond, self.since = cond, 0
        self.blocks.append({"id": self.block, "cond": cond, "round": rnd, "start": len(self.rows)})

    # ---- the file ----

    def save(self, path: Path, extra: dict | None = None) -> None:
        names = sorted({k for r in self.rows for k in r} - {"block", "since", "cond"})
        cols = {n: [round(r.get(n, 0.0), 3) for r in self.rows] for n in names}
        doc = {"schema": "hyperspace.spikes/1",
               "meta": {**self.meta, **(extra or {}), "python": sys.version.split()[0],
                        "platform": platform.platform(), "frames": len(self.rows),
                        "threads_end": sorted(t.name for t in threading.enumerate())},
               "conditions": list(CONDITIONS), "blocks": self.blocks,
               "block": [r["block"] for r in self.rows], "since": [r["since"] for r in self.rows],
               "cols": cols}
        path.write_text(json.dumps(doc, separators=(",", ":")))


def _timer(rec: Recorder, column: str, f):
    def timed(*a, **kw):
        t = pc()
        try:
            return f(*a, **kw)
        finally:
            rec.add(column, pc() - t)
    return timed


# ---- the report ----

def _pearson(a, b) -> float:
    import numpy as np
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def report(doc: dict, out=print, conds: tuple[str, ...] = ("base",)) -> None:
    """The report. The slow-versus-middle table, the worst frames and the spacing are
    of the blocks whose condition is in `conds` (default: the control, `base`): a
    switch that moves every frame (the additive flip doubled the Mac's) would
    otherwise be the slowest 5% and write the table. The per-condition table
    below is of every block."""
    import numpy as np

    cols = {k: np.array(v) for k, v in doc["cols"].items()}
    since, block = np.array(doc["since"]), np.array(doc["block"])
    total = cols["total"]
    kept = (since >= SETTLE) & (block >= 0)
    ids = {b["id"] for b in doc["blocks"] if b["cond"] in conds}
    keep = kept & np.isin(block, sorted(ids))
    n = int(keep.sum())
    out(f"{doc['meta'].get('patch', '?')}: {len(total)} frames, {int(kept.sum())} after warm-up and "
        f"each block's first {SETTLE}; threads at start: {', '.join(doc['meta'].get('threads_start', []))}")
    if n < 40:
        out("too few frames for a report")
        return
    t = total[keep]
    out(f"the next three tables are of the {', '.join(conds)} blocks only ({n} frames)")
    q = np.percentile
    out(f"whole frame ms: median {q(t, 50):.1f}  p90 {q(t, 90):.1f}  p95 {q(t, 95):.1f}  "
        f"p99 {q(t, 99):.1f}  max {t.max():.1f}   (frames over 2x median: "
        f"{int((t > 2 * q(t, 50)).sum())} = {100 * (t > 2 * q(t, 50)).mean():.1f}%)")

    # the slowest 5% against the frames in the middle of the pack
    lo, hi, cut = q(t, 40), q(t, 60), q(t, 95)
    slow, mid = keep & (total >= cut), keep & (total >= lo) & (total <= hi)
    excess = total[slow].mean() - total[mid].mean()
    out(f"\nslowest 5% ({int(slow.sum())} frames, mean {total[slow].mean():.1f} ms) against the "
        f"middle fifth ({int(mid.sum())} frames, mean {total[mid].mean():.1f} ms): "
        f"{excess:.1f} ms more. Which parts grew:")
    out(f"  {'part':<18}{'mid':>9}{'slow':>9}{'grew':>9}{'of excess':>11}{'corr':>7}")
    rows = []
    for name, c in cols.items():
        if name in ("total", "t"):
            continue
        d = c[slow].mean() - c[mid].mean()
        rows.append((d, name, c[mid].mean(), c[slow].mean(), _pearson(c[keep], t)))
    for d, name, a, b, r in sorted(rows, reverse=True)[:16]:
        if abs(d) < 0.01 and not abs(r) >= 0.05:        # (a constant column's r is nan)
            continue
        unit = "" if not name.startswith(("cells", "edges", "gc_n")) else " (count)"
        share = f"{100 * d / excess:5.0f}%" if excess > 0 and not unit else ""
        out(f"  {name:<18}{a:9.2f}{b:9.2f}{d:9.2f}{share:>11}{r:7.2f}{unit}")
    out("  (parts nest: outside + frame_fn = total; draw_render holds graph, node_*, "
        "draw_scene, walk; gc and swap_* can fall inside any. 'corr' is Pearson over all "
        "kept frames; a count's correlation is the useful number for it.)")

    # the worst frames one by one: a one-off (a first-time allocation) reads differently
    # from a tail every 30 frames
    parts = [k for k in cols if k not in ("t", "total", "frame_fn", "outside", "draw_render", "graph",
                                          "gpu_total", "gpu_scene", "gc_n", "cells_line",
                                          "cells_face", "edges", "gil_late")]
    out("\nthe five worst frames (frame, block's condition, frames into it, ms; biggest parts):")
    worst = np.argsort(np.where(keep, total, -1.0))[::-1][:5]
    for i in worst:
        big = sorted(((cols[k][i], k) for k in parts), reverse=True)[:3]
        cond = doc["blocks"][int(block[i])]["cond"] if block[i] >= 0 else "warmup"
        when = f" at {cols['t'][i]:.0f} s" if "t" in cols else ""
        out(f"  #{int(i)}{when} {cond} +{int(since[i])}: {total[i]:.0f} ms; "
            + ", ".join(f"{k} {v:.0f}" for v, k in big))

    # when: the spacing between slow frames
    idx = np.flatnonzero(slow)
    gaps = Counter(int(g) for g in np.diff(idx) if g <= 130)
    if gaps:
        top = ", ".join(f"{g}f x{c}" for g, c in gaps.most_common(6))
        out(f"\nframes between one slow frame and the next (<=130): {top}")

    # the off-switches, block by block
    bl = doc["blocks"]
    if len({b["cond"] for b in bl}) > 1:
        out("\nper condition (kept frames of each block; spread = the blocks' own p95 range):")
        out(f"  {'condition':<15}{'blocks':>7}{'median':>8}{'p95':>8}{'p99':>8}{'mean':>8}"
            f"  p95 by block")
        base_p95 = None
        stats = {}
        for cond in doc["conditions"]:
            ids = [b["id"] for b in bl if b["cond"] == cond]
            if not ids:
                continue
            per = [total[(block == i) & (since >= SETTLE)] for i in ids]
            per = [p for p in per if len(p) > 20]
            if not per:
                continue
            allv = np.concatenate(per)
            p95s = [float(q(p, 95)) for p in per]
            stats[cond] = (float(q(allv, 50)), float(q(allv, 95)), float(q(allv, 99)),
                           float(allv.mean()), p95s)
            if cond == "base":
                base_p95 = stats[cond][1]
            m, p, p9, mu, ps = stats[cond]
            out(f"  {cond:<15}{len(per):7d}{m:8.1f}{p:8.1f}{p9:8.1f}{mu:8.1f}  "
                + " ".join(f"{x:.0f}" for x in ps))
        if base_p95:
            out("  against base (negative: the switch made it shorter; a spike on fewer than 1 frame in\n"
                "  20 is above p95, so read p99 and the mean for those):")
            for cond, (m, p, p9, mu, ps) in stats.items():
                if cond != "base":
                    out(f"    {cond:<15} median {m - stats['base'][0]:+6.1f}  p95 {p - base_p95:+6.1f}"
                        f"  p99 {p9 - stats['base'][2]:+6.1f}  mean {mu - stats['base'][3]:+6.1f} ms")
            sp = stats["base"][4]
            if len(sp) > 1:
                out(f"    noise: base's own p95 differs between its blocks by "
                    f"{max(sp) - min(sp):.1f} ms (a difference smaller than that is not a result)")

    # the collector and the script
    if "gc" in cols:
        g = cols["gc"][keep]
        out(f"\nGC: {int((g > 0).sum())} frames of {n} held a collection; the most in a frame "
            f"{g.max():.1f} ms; {100 * g.sum() / t.sum():.2f}% of the time")
    if "panel_draw" in cols and "draw_panel" in cols:
        drv = cols["draw_panel"][keep] - cols["panel_draw"][keep]
        out(f"the driver's step (draw_panel less Panel.draw): median {np.median(drv):.3f} ms, "
            f"p99 {q(drv, 99):.2f}, max {drv.max():.2f}; correlation with the whole frame "
            f"{_pearson(drv, t):.2f}")
    if "gil_late" in cols:
        gl = cols["gil_late"][keep]
        out(f"GIL probe: a 1 ms sleep woke late by median {np.median(gl):.2f} ms, p99 {q(gl, 99):.2f}, "
            f"max {gl.max():.1f}; correlation with the whole frame {_pearson(gl, t):.2f}  "
            "(a GL call that holds the GIL for its whole run makes the probe late too: read "
            "this beside swap_* and draw_scene, not alone)")
    if "cells_line" in cols and cols["cells_line"][keep].max() > 0:
        c = cols["cells_line"][keep] + cols["cells_face"][keep]
        out(f"fractal cells drawn: median {np.median(c):.0f}, p95 {q(c, 95):.0f}, max {c.max():.0f}; "
            f"correlation with the whole frame {_pearson(c, t):.2f}")


def main() -> None:
    doc = json.loads(Path(sys.argv[1]).read_text())
    report(doc, conds=tuple(sys.argv[2].split(",")) if len(sys.argv) > 2 else ("base",))


if __name__ == "__main__":
    main()
