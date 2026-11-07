#!/usr/bin/env python3
"""SC3a's measurements (plan 58 §9): can the picture stop depending on any one display?

The spike's, kept because they are the owner's gate (hand checks 607–610): never
imported by the app. `today` is the old shape rebuilt here, for comparison; `guarded`
and `draw-render` run the shipped `pacing.Pacer` and `app._draw_render`. Each
subcommand is one measurement and prints one JSON line per result; run each in its
own process (a crash is an answer). Touches no `~/Hyperspace`. Check `state` first:
locked, vsync numbers mean nothing. Run from `hyperspace-python/`:

    .venv/bin/python tools/sc3a_spike.py state
    tools/sc3a_spike_pacing.sh 3 20
    .venv/bin/python tools/sc3a_spike.py handover --phase 6
    uv run python tools/sc3a_spike.py draw-render
    uv run python tools/sc3a_spike.py draw-render --overlay
    uv run python tools/sc3a_spike.py v8

    uv run python tools/sc3a_spike.py pacing --shape today --secs 20
    uv run python tools/sc3a_spike.py handover
    uv run python tools/sc3a_spike.py cycles --n 200
    uv run python tools/sc3a_spike.py root-death --case destroy-root
    uv run python tools/sc3a_spike.py msaa
    uv run python tools/sc3a_spike.py alpha
    uv run python tools/sc3a_spike.py cost --shape today --secs 10
    uv run python tools/sc3a_spike.py monitor     # adds and removes a virtual display
    uv run python tools/sc3a_spike.py soak --secs 900
"""

from __future__ import annotations

import argparse
import ctypes
import gc
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import glfw
import moderngl
import numpy as np
from OpenGL import GL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hyperspace.outputs import Handoff, Presenter

VS = """#version 330
in vec2 p; uniform float u_t; void main(){ float c=cos(u_t), s=sin(u_t);
gl_Position = vec4(c*p.x - s*p.y, s*p.x + c*p.y, 0.0, 1.0); }"""
FS = """#version 330
uniform vec4 u_c; out vec4 f; void main(){ f = u_c; }"""
QUAD_VS = """#version 330
out vec2 v; void main(){ vec2 q = vec2((gl_VertexID<<1)&2, gl_VertexID&2);
v=q; gl_Position=vec4(q*2.0-1.0,0.0,1.0);}"""
PAINT_FS = """#version 330
in vec2 v; uniform sampler2D t; out vec4 f; void main(){ f = texture(t, v); }"""


def drain() -> list[int]:
    """GL errors pending, cleared. PyOpenGL raises on them at its next call,
    and `moderngl.create_context` can leave one (its probes)."""
    from OpenGL.raw.GL.VERSION.GL_1_1 import glGetError
    out = []
    while (e := glGetError()) != 0 and len(out) < 8:
        out.append(int(e))
    return out


def say(**kw) -> None:
    print(json.dumps(kw), flush=True)


def stats(dts: list[float], skip: int = 10) -> dict:
    """Milliseconds: the loop's period, what a show would feel."""
    d = np.array(dts[skip:] or dts) * 1000.0
    if len(d) == 0:
        return {"n": 0}
    med = float(np.median(d))
    return {"n": len(d), "mean": round(float(d.mean()), 3), "p50": round(med, 3),
            "p99": round(float(np.percentile(d, 99)), 3), "max": round(float(d.max()), 3),
            "sd": round(float(d.std()), 3), "fps": round(1000.0 / float(d.mean()), 1),
            "over_1.5x": int((d > 1.5 * med).sum())}


def hints(samples=0, transparent=False, visible=True) -> None:
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.SAMPLES, samples)
    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, transparent)
    glfw.window_hint(glfw.AUTO_ICONIFY, False)
    glfw.window_hint(glfw.VISIBLE, visible)
    glfw.window_hint(glfw.FOCUS_ON_SHOW, False)
    glfw.window_hint(glfw.FOCUSED, False)


def window(size=(640, 360), share=None, pos=None, title="sc3a", **kw):
    hints(**kw)
    win = glfw.create_window(size[0], size[1], title, None, share)
    if not win:
        raise SystemExit("no window")
    if pos:
        glfw.set_window_pos(win, *pos)
    return win


def monitor_at(i: int):
    ms = glfw.get_monitors()
    return ms[min(i, len(ms) - 1)]


def spot(mon_i: int, dx=60, dy=60) -> tuple[int, int]:
    x, y, _w, _h = glfw.get_monitor_workarea(monitor_at(mon_i))
    return x + dx, y + dy


def occlusion(win) -> dict:
    """NSWindow's own say: bit 2 is NSWindowOcclusionStateVisible."""
    import objc
    ns = objc.objc_object(c_void_p=glfw.get_cocoa_window(win))
    return {"visible_bit": bool(int(ns.occlusionState()) & 2), "isVisible": bool(ns.isVisible()),
            "screen": str(ns.screen().localizedName()) if ns.screen() is not None else None}


class Work:
    """The renderer's shape on the root's context: a 4× MSAA scene, resolved
    into an RGBA8 texture (render.SceneTarget), of `lines` thin triangles."""

    def __init__(self, ctx, size=(640, 360), samples=4, lines=4000):
        self.ctx, self.size = ctx, size
        self.prog = ctx.program(vertex_shader=VS, fragment_shader=FS)
        rng = np.random.default_rng(7)
        a = rng.uniform(-1, 1, (lines, 2))
        b = a + rng.uniform(-0.5, 0.5, (lines, 2))
        n = np.stack([-(b - a)[:, 1], (b - a)[:, 0]], 1)
        n = 0.0015 * n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)
        tris = np.stack([a + n, a - n, b + n, b + n, a - n, b - n], 1).astype("f4")
        self.vbo = ctx.buffer(tris.tobytes())
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, "2f", "p")])
        self.tex = ctx.texture(size, 4)
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.msaa = (ctx.framebuffer(color_attachments=[ctx.renderbuffer(size, 4, samples=samples)])
                     if samples else self.fbo)
        self.frame = 0

    def draw(self, alpha=1.0):
        ctx = self.ctx
        self.frame += 1
        self.msaa.use()
        ctx.viewport = (0, 0, *self.size)
        ctx.clear(0.02, 0.02, 0.05, alpha)
        ctx.disable(moderngl.BLEND)
        self.prog["u_t"].value = self.frame * 0.01
        self.prog["u_c"].value = (0.9, 0.7, 0.2, 1.0)
        self.vao.render(moderngl.TRIANGLES)
        if self.msaa is not self.fbo:
            ctx.copy_framebuffer(self.fbo, self.msaa)
        return self.tex


class Paint:
    """The direct paint: a full-window triangle on this context."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=PAINT_FS)
        self.vao = ctx.vertex_array(self.prog, [])

    def to(self, fb, tex, size):
        fb.use()
        self.ctx.viewport = (0, 0, *size)
        self.ctx.disable(moderngl.BLEND)
        tex.use(0)
        self.vao.render(moderngl.TRIANGLES, vertices=3)


class Live:
    """One presenter window: its own context, the app's real `Presenter`."""

    def __init__(self, root, size=(640, 360), pos=None, interval=0, transparent=False, title="sc3a"):
        t0 = time.perf_counter()
        self.win = window(size, share=root, pos=pos, transparent=transparent, title=title)
        t1 = time.perf_counter()
        glfw.make_context_current(self.win)
        glfw.swap_interval(interval)
        self.ctx = moderngl.create_context()
        self.create_errs = drain()
        self.pres = Presenter(self.ctx)
        t2 = time.perf_counter()
        self.pres._build()
        t3 = time.perf_counter()
        self.made_ms = (round((t1 - t0) * 1e3, 2), round((t2 - t1) * 1e3, 2), round((t3 - t2) * 1e3, 2))

    def present(self, tex, tsize, swap=True, bg_alpha=1.0):
        glfw.make_context_current(self.win)
        fb = glfw.get_framebuffer_size(self.win)
        rect = (0, 0, *tsize) if tuple(fb) == tuple(tsize) else (0, 0, *fb)
        self.pres.present(Handoff(tex, tsize, rect, bg_alpha=bg_alpha), fb)
        if swap:
            glfw.swap_buffers(self.win)

    def close(self, then):
        """Current, its objects let go, the window destroyed, `then` current."""
        t0 = time.perf_counter()
        glfw.make_context_current(self.win)
        self.pres._drop()
        self.ctx.release()
        glfw.destroy_window(self.win)
        glfw.make_context_current(then)
        return round((time.perf_counter() - t0) * 1e3, 2)


def root_context(visible=False, samples=0, size=(64, 64), interval=1, **kw):
    root = window(size, visible=visible, samples=samples, title="sc3a root", **kw)
    glfw.make_context_current(root)
    glfw.swap_interval(interval)
    ctx = moderngl.create_context()
    drain()
    return root, ctx


class Timer:
    """The fallback pacer: sleep to just short of the next tick, then spin."""

    def __init__(self, hz=60.0, spin_s=0.0015):
        self.period, self.spin, self.next = 1.0 / hz, spin_s, time.perf_counter()

    def wait(self):
        self.next += self.period
        now = time.perf_counter()
        if self.next < now - self.period:        # a stall: no catching up
            self.next = now
            return
        if self.next - now > self.spin:
            time.sleep(self.next - now - self.spin)
        while time.perf_counter() < self.next:
            pass


# ------------------------------------------------------------ 1, 2: pacing

def pacing(a) -> None:
    glfw.init()
    shape = a.shape
    pos0, pos1 = spot(a.mon), spot(a.mon, 720, 60)
    extra: dict = {}
    timer = None
    if shape == "today":
        root, ctx = root_context(visible=True, samples=4, size=(640, 360))
        glfw.set_window_pos(root, *pos0)
    else:
        root, ctx = root_context(visible=False)
    work = Work(ctx)
    paint = Paint(ctx)
    pacer = control = None
    lives: list[Live] = []
    if shape in ("today", "hidden-swap", "hidden-timer", "presenter-vsync", "two-vsync", "occluded", "guarded"):
        control = Live(root, pos=pos1)
    if shape in ("presenter-vsync", "guarded"):
        lives = [Live(root, pos=pos0, interval=1)]
    if shape == "guarded":
        # the shipped floor: a swap that doesn't wait (locked, occluded from birth,
        # hidden) can't run the loop away
        from hyperspace.pacing import Pacer as ShippedPacer
        shipped = ShippedPacer(glfw)
        shipped.choose([lives[0].win], root)
        timer = SimpleNamespace(wait=shipped.end_frame)
    if shape == "two-vsync":
        lives = [Live(root, pos=pos0, interval=1), Live(root, pos=spot(a.mon2), interval=1)]
    if shape == "occluded":
        lives = [Live(root, pos=pos0, interval=1)]
        cover = window((900, 600), pos=(pos0[0] - 30, pos0[1] - 60), title="sc3a cover")
        glfw.set_window_attrib(cover, glfw.FLOATING, True)
    if shape in ("hidden-timer", "hidden-only-timer"):
        timer = Timer(a.hz)
    if lives:
        pacer = lives[0]
    glfw.make_context_current(root)
    occlusion(root)        # its first pyobjc import, before the clock starts
    last = time.perf_counter()
    dts: list[float] = []
    end = last + a.secs
    probe_at = last + min(5.0, a.secs / 2)
    while last < end:
        glfw.poll_events()
        glfw.make_context_current(root)
        tex = work.draw()
        if shape == "today":
            paint.to(ctx.screen, tex, glfw.get_framebuffer_size(root))
        GL.glFlush()
        for lv in lives[1:]:
            lv.present(tex, work.size)
        if control is not None:
            control.present(tex, work.size)
        if pacer is not None:
            pacer.present(tex, work.size)
        elif shape in ("today", "hidden-swap", "hidden-only-swap"):
            glfw.make_context_current(root)
            glfw.swap_buffers(root)
        if timer is not None:
            timer.wait()
        now = time.perf_counter()
        dts.append(now - last)
        last = now
        if probe_at and now > probe_at:
            probe_at = 0
            extra["occlusion"] = {"root": occlusion(root)}
            if pacer:
                extra["occlusion"]["pacer"] = occlusion(pacer.win)
    extra["machine_locked"] = machine()["locked"]
    say(test="pacing", shape=shape, mon=glfw.get_monitor_name(monitor_at(a.mon)).decode(),
        **stats(dts), **extra)
    glfw.terminate()


# ------------------------------------------------------------ 2: handover

class Pacer:
    """The shape on trial: the first live window waits for its display
    (interval 1), all others don't, and with none a timer."""

    def __init__(self, hz=60.0):
        self.owner: Live | None = None
        self.timer = Timer(hz)
        self.handovers: list = []

    def choose(self, lives: list[Live], then) -> None:
        want = lives[0] if lives else None
        if want is self.owner:
            return
        t0 = time.perf_counter()
        if self.owner is not None and self.owner in lives:
            glfw.make_context_current(self.owner.win)
            glfw.swap_interval(0)
        if want is not None:
            glfw.make_context_current(want.win)
            glfw.swap_interval(1)
        glfw.make_context_current(then)
        self.owner = want
        self.timer.next = time.perf_counter()
        self.handovers.append(round((time.perf_counter() - t0) * 1e3, 3))

    def end_frame(self):
        if self.owner is None:
            self.timer.wait()


def handover(a) -> None:
    glfw.init()
    root, ctx = root_context()
    work = Work(ctx)
    pacer = Pacer()
    win_a = Live(root, pos=spot(a.mon), title="A")
    win_b = Live(root, pos=spot(a.mon2), title="B")
    made = {"A": win_a.made_ms, "B": win_b.made_ms}
    lives = [win_a, win_b]
    pacer.choose(lives, root)
    events = [(a.phase, "destroy A: B paces"), (2 * a.phase, "destroy B: timer paces"),
              (3 * a.phase, "create C: C paces"), (4 * a.phase, "create D behind C"),
              (5 * a.phase, "destroy C: D paces"), (6 * a.phase, "end")]
    t0 = last = time.perf_counter()
    phase_dts: list[list[float]] = [[]]
    around = []
    ev = 0
    while True:
        glfw.poll_events()
        glfw.make_context_current(root)
        tex = work.draw()
        GL.glFlush()
        # the pacer's swap last: the others never wait, it does
        for lv in sorted(lives, key=lambda v: v is pacer.owner):
            lv.present(tex, work.size)
        glfw.make_context_current(root)
        pacer.end_frame()
        now = time.perf_counter()
        phase_dts[-1].append(now - last)
        last = now
        if now - t0 >= events[ev][0]:
            what = events[ev][1]
            if what == "end":
                break
            t_ev = time.perf_counter()
            info: dict = {"event": what}
            if what.startswith("destroy A"):
                info["close_ms"] = win_a.close(root)
                lives = [win_b]
            elif what.startswith("destroy B"):
                info["close_ms"] = win_b.close(root)
                lives = []
            elif what.startswith("create C"):
                c = Live(root, pos=spot(a.mon), title="C")
                info["make_ms(window,ctx,programs)"] = c.made_ms
                lives = [c]
            elif what.startswith("create D"):
                d = Live(root, pos=spot(a.mon, 720), title="D")
                info["make_ms(window,ctx,programs)"] = d.made_ms
                lives = [lives[0], d]
            elif what.startswith("destroy C"):
                info["close_ms"] = lives[0].close(root)
                lives = lives[1:]
            pacer.choose(lives, root)
            info["event_ms"] = round((time.perf_counter() - t_ev) * 1e3, 2)
            around.append(info)
            ev += 1
            phase_dts.append([])
    names = ["A+B, A paces", "B paces", "timer", "C paces", "C+D, C paces", "D paces"]
    for name, d in zip(names, phase_dts, strict=False):
        say(test="handover", phase=name, **stats(d),
            first_five=[round(x * 1e3, 2) for x in d[:5]])
    say(test="handover", events=around, handover_ms=pacer.handovers, made=made)
    glfw.terminate()


# ------------------------------------------------------------ 3: join and leave

def rss_kb() -> int:
    return int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())]).strip())


def footprint_kb() -> int | None:
    try:
        out = subprocess.check_output(["footprint", "-p", str(os.getpid())],
                                      stderr=subprocess.DEVNULL, timeout=30).decode()
    except Exception:  # noqa: BLE001 — a measure, not the test
        return None
    for line in out.splitlines():
        if "phys_footprint:" in line:
            v = line.split(":")[1].split()
            return int(float(v[0]) * {"KB": 1, "MB": 1024, "GB": 1048576}.get(v[1], 1))
    return None


def solid_tex(ctx, size, rgba):
    return ctx.texture(size, 4, bytes(rgba) * (size[0] * size[1]))


def read_centre(lv: Live) -> tuple[int, ...]:
    glfw.make_context_current(lv.win)
    lv.ctx.screen.use()
    w, h = glfw.get_framebuffer_size(lv.win)
    return tuple(lv.ctx.screen.read(viewport=(w // 2, h // 2, 1, 1), components=4))


def cycles(a) -> None:
    glfw.init()
    root, ctx = root_context()
    work = Work(ctx, lines=500)
    keep = Live(root, pos=spot(a.mon), interval=1)
    size = (64, 64)
    bad = errs = 0
    mem = []
    make, close = [], []
    for i in range(a.n):
        visitor = Live(root, pos=spot(a.mon, 720, 60 + i % 40), size=(320, 180))
        make.append(sum(visitor.made_ms))
        for k in range(a.frames):
            glfw.poll_events()
            glfw.make_context_current(root)
            work.draw()
            rgba = (i % 251, (i * 3) % 251, k % 251, 255)
            tex = solid_tex(ctx, size, rgba)
            GL.glFlush()
            for lv in (visitor, keep):
                lv.present(tex, size, swap=False)
                errs += len(drain())
                if read_centre(lv) != rgba:
                    bad += 1
                drain()              # moderngl's read of a default framebuffer: its own 1282
                glfw.swap_buffers(lv.win)
                errs += len(drain())
            glfw.make_context_current(root)
            tex.release()
        close.append(visitor.close(root))
        errs += len(drain())
        if i % 25 == 0 or i == a.n - 1:
            gc.collect()
            mem.append((i, rss_kb(), footprint_kb()))
            say(test="cycles", at=i, rss_kb=mem[-1][1], footprint_kb=mem[-1][2], bad=bad, gl_errs=errs)
    grow = None
    if len(mem) > 2:
        grow = round((mem[-1][1] - mem[1][1]) / max(mem[-1][0] - mem[1][0], 1), 1)
    say(test="cycles", n=a.n, frames=a.frames, wrong_pixels=bad, gl_errs=errs,
        make_ms=stats([m / 1e3 for m in make], 1), close_ms=stats([c / 1e3 for c in close], 1),
        rss_growth_kb_per_cycle=grow)
    glfw.terminate()


def leak(a) -> None:
    """Whose is the growth a join and leave costs? `--layer` adds a piece per
    run: the window alone, then its moderngl context, then the Presenter, then
    frames; `--pool` drains an autorelease pool around each cycle."""
    import objc
    glfw.init()
    root, _ctx = root_context()
    mem = []
    pos = spot(0, 720)
    for i in range(a.n):
        with objc.autorelease_pool() if a.pool else _nothing():
            hints()
            w = glfw.create_window(320, 180, "leak", None, root)
            glfw.set_window_pos(w, *pos)
            if a.layer >= 1:
                glfw.make_context_current(w)
                c = moderngl.create_context()
            if a.layer >= 2:
                pr = Presenter(c)
                pr._build()
            if a.layer >= 3:
                glfw.swap_buffers(w)
                glfw.poll_events()
            if a.layer >= 2:
                pr._drop()
                del pr
            if a.layer >= 1:
                c.release()
                del c
            glfw.destroy_window(w)
            glfw.make_context_current(root)
            glfw.poll_events()
        if i % 50 == 0 or i == a.n - 1:
            gc.collect()
            mem.append((i, rss_kb()))
    i0, r0 = mem[1]
    i1, r1 = mem[-1]
    say(test="leak", layer=a.layer, pool=a.pool, n=a.n, rss=mem,
        kb_per_cycle=round((r1 - r0) / max(i1 - i0, 1), 1))
    glfw.terminate()


class _nothing:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def root_death(a) -> None:
    """One way of tearing the group: `case` in its own process."""
    import faulthandler
    faulthandler.enable()
    glfw.init()
    root, ctx = root_context()
    size = (64, 64)
    red = (200, 10, 20, 255)
    tex = solid_tex(ctx, size, red)
    fbo = ctx.framebuffer(color_attachments=[tex])
    vao_root = Paint(ctx)
    GL.glFlush()
    a_ = Live(root, pos=spot(0), size=(320, 180))
    b_ = Live(root, pos=spot(0, 400), size=(320, 180))
    res: dict = {"case": a.case}

    def show(lv, t=None):
        lv.present(t if t is not None else tex, size, swap=False)
        got = read_centre(lv)
        glfw.swap_buffers(lv.win)
        return got

    if a.case == "destroy-member":
        res["close_ms"] = b_.close(root)
        res["a_sees"] = show(a_)
        glfw.make_context_current(root)
        fbo.use()
        res["root_fbo"] = tuple(fbo.read(viewport=(1, 1, 1, 1), components=4))
    elif a.case == "destroy-member-while-current":
        glfw.make_context_current(b_.win)
        b_.pres._drop()
        b_.ctx.release()
        glfw.destroy_window(b_.win)
        res["current_after"] = bool(glfw.get_current_context())
        res["a_sees"] = show(a_)
    elif a.case == "destroy-root":
        # what we'd never do: the root goes, the texture it made must live on
        glfw.make_context_current(root)
        ctx.release()
        glfw.make_context_current(a_.win)
        glfw.destroy_window(root)
        res["a_sees"] = show(a_)
        res["b_sees"] = show(b_)
        # …and can a new member join through a survivor?
        c_ = Live(a_.win, pos=spot(0, 400, 300), size=(320, 180))
        res["c_joined_through_a_sees"] = show(c_)
        res["gl_err"] = GL.glGetError()
    elif a.case == "release-in-wrong-context":
        # the trap: a presenter's moderngl objects let go with the ROOT current.
        # VAO names are per context, so glDeleteVertexArrays hits the root's.
        glfw.make_context_current(root)
        extra = [Paint(ctx) for _ in range(6)]   # the root's names cover the presenter's
        name = a_.pres._vao.glo
        res["presenter_vao_name"] = name
        res["root_names"] = [p.vao.glo for p in [vao_root, *extra]]
        before = bool(GL.glIsVertexArray(name))
        a_.pres._vao.release()               # wrong context on purpose
        res["same_name_on_root_alive_before"] = before
        res["same_name_on_root_alive_after"] = bool(GL.glIsVertexArray(name))
    elif a.case == "destroy-without-release":
        # the window goes, moderngl's objects dangle and are then collected
        glfw.destroy_window(b_.win)
        glfw.make_context_current(root)
        b_.pres = None
        b_.ctx = None
        gc.collect()
        res["a_sees"] = show(a_)
    res["ok"] = True
    say(test="root-death", **res)
    glfw.terminate()


# ------------------------------------------------------------ 4: the picture

def _scene(ctx, target, size, flip=False):
    """A diagonal thin triangle and a circle's rim: edges only MSAA softens."""
    prog = ctx.program(vertex_shader=VS, fragment_shader=FS)
    th = np.linspace(0, 2 * math.pi, 241)
    ring = np.stack([0.7 * np.cos(th), 0.7 * np.sin(th)], 1)
    verts = []
    for i in range(240):
        p, q = ring[i], ring[i + 1]
        verts += [p, p * 1.02, q, q, p * 1.02, q * 1.02]
    a, b = np.array([-0.9, -0.77]), np.array([0.9, 0.61])
    n = np.array([-(b - a)[1], (b - a)[0]])
    n = 0.004 * n / np.linalg.norm(n)
    verts += [a + n, a - n, b + n, b + n, a - n, b - n]
    verts = np.array(verts, dtype="f4")
    if flip:
        verts = verts * np.array([1.0, -1.0], dtype="f4")
    vbo = ctx.buffer(verts.tobytes())
    vao = ctx.vertex_array(prog, [(vbo, "2f", "p")])
    target.use()
    ctx.viewport = (0, 0, *size)
    ctx.disable(moderngl.BLEND)
    ctx.clear(0.1, 0.0, 0.2, 1.0)
    prog["u_t"].value = 0.0
    prog["u_c"].value = (1.0, 0.9, 0.3, 1.0)
    vao.render(moderngl.TRIANGLES)


def _pix(fb, size, comps=4) -> np.ndarray:
    return np.frombuffer(fb.read(viewport=(0, 0, *size), components=comps),
                         dtype=np.uint8).reshape(size[1], size[0], comps).copy()


def _screen(ctx, size) -> np.ndarray:
    """A window's back buffer, resolved by a raw blit. moderngl's `screen.read`
    raises GL_INVALID_OPERATION on a 4x window (the bytes agree), and its
    `copy_framebuffer` from `screen` GL_INVALID_ENUM, so neither is used."""
    tex = ctx.texture(size, 4)
    flat = ctx.framebuffer(color_attachments=[tex])
    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, 0)
    GL.glReadBuffer(GL.GL_BACK)
    GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, flat.glo)
    GL.glBlitFramebuffer(0, 0, size[0], size[1], 0, 0, size[0], size[1],
                         GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
    out = _pix(flat, size)
    ctx.screen.use()
    flat.release()
    tex.release()
    return out


def _levels(p) -> dict:
    """Coverage histogram along the lines' red: 4x gives 0, ¼, ½, ¾, 1."""
    k = np.round((p[..., 0].astype(float) - 0x1a) / (255 - 0x1a) * 4).astype(int)
    return {str(i): int((k == i).sum()) for i in range(5)}


def _diff(a_, b_) -> dict:
    d = np.abs(a_.astype(int) - b_.astype(int))
    return {"max": int(d.max()), "pixels_differ": int((d.max(axis=2) > 0).sum()),
            "of": int(d.shape[0] * d.shape[1])}


def _partial(p) -> int:
    """Pixels between the clear and the line: coverage only MSAA gives."""
    base, line = np.array([0x1a, 0, 0x33]), np.array([255, 230, 77])
    off_both = (np.abs(p[..., :3].astype(int) - base).max(axis=2) > 3) & (
        np.abs(p[..., :3].astype(int) - line).max(axis=2) > 3)
    return int(off_both.sum())


def msaa(a) -> None:
    glfw.init()
    size = (640, 360)
    w4 = window(size, samples=4, pos=spot(a.mon), title="direct 4x")
    glfw.make_context_current(w4)
    glfw.swap_interval(0)
    ctx = moderngl.create_context()
    res0 = drain()
    fb4 = tuple(glfw.get_framebuffer_size(w4))
    res: dict = {"create_errs": res0, "fb": fb4, "GL_SAMPLES_window": int(GL.glGetIntegerv(GL.GL_SAMPLES)),
                 "renderer": ctx.info["GL_RENDERER"]}
    _scene(ctx, ctx.screen, fb4)
    GL.glFinish()
    direct = _screen(ctx, fb4)
    glfw.swap_buffers(w4)
    res["direct_partial_pixels"] = _partial(direct)
    res["direct_levels"] = _levels(direct)

    # the same scene: an MSAA FBO on the context, resolved, through the app's Presenter
    rb = ctx.renderbuffer(fb4, 4, samples=4)
    ms = ctx.framebuffer(color_attachments=[rb])
    tex = ctx.texture(fb4, 4)
    flat = ctx.framebuffer(color_attachments=[tex])
    _scene(ctx, ms, fb4)
    ctx.copy_framebuffer(flat, ms)
    GL.glFlush()
    lv = Live(w4, size=size, pos=spot(a.mon, 720))
    fbp = tuple(glfw.get_framebuffer_size(lv.win))
    lv.pres.present(Handoff(tex, fb4, (0, 0, *fbp)), fbp)
    pres = _screen(lv.ctx, fbp)
    glfw.swap_buffers(lv.win)
    res["presenter_vs_direct"] = _diff(direct, pres)
    res["presenter_partial_pixels"] = _partial(pres)
    res["presenter_levels"] = _levels(pres)
    # the FBO's samples may sit mirrored from the window's: draw it upside
    # down, compare upside down. Equal means the same 4x in another order.
    glfw.make_context_current(w4)
    _scene(ctx, ms, fb4, flip=True)
    ctx.copy_framebuffer(flat, ms)
    res["flipped_fbo_vs_direct"] = _diff(direct, _pix(flat, fb4)[::-1])
    GL.glFlush()

    # the control: no MSAA at all. The test must see this as different.
    glfw.make_context_current(w4)
    tex0 = ctx.texture(fb4, 4)
    fb0 = ctx.framebuffer(color_attachments=[tex0])
    _scene(ctx, fb0, fb4)
    GL.glFlush()
    lv.present(tex0, fb4, swap=False)
    none = _screen(lv.ctx, fbp)
    res["no_msaa_vs_direct"] = _diff(direct, none)
    res["no_msaa_partial_pixels"] = _partial(none)
    glfw.swap_buffers(lv.win)
    say(test="msaa-synthetic", **res)
    if not a.no_rig:
        _msaa_rigs(a, ctx, w4, lv, fb4, fbp)
    glfw.terminate()


def _msaa_rigs(a, ctx, w4, lv, fb4, fbp) -> None:
    """The real renderer on real looks: `View(target=screen)` on the 4× window
    against `View(target=Offscreen, samples=4)` + the real Presenter. The rig
    keeps its library in a temp dir (`golden_frames.Rig`)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import golden_frames as gf

    from hyperspace.outputs import Offscreen, Switches, View
    ctx.gc_mode = "auto"
    slugs = a.slugs or sorted(gf.CORPUS_LOADABLES)[:6]
    off = Offscreen(ctx)
    for slug in slugs:
        for hands in ("present", "absent"):
            glfw.make_context_current(w4)
            try:
                r1 = gf.Rig(slug, hands, ctx)
                r2 = gf.Rig(slug, hands, ctx)
            except Exception as e:  # noqa: BLE001 — a look the rig won't load isn't the question
                say(test="msaa-rig", slug=slug, skipped=str(e)[:160])
                continue
            r1.renderer.max_frame = r2.renderer.max_frame = None
            out = {}
            for k in range(a.rig_frames):
                glfw.make_context_current(w4)
                ctx.screen.use()
                ctx.viewport = (0, 0, *fb4)
                r1.frame([View(Switches(), fb4, target=ctx.screen, viewport=(0, 0, *fb4))], fb4, 1.0)
                ctx.screen.use()
                d = _screen(ctx, fb4)
                glfw.swap_buffers(w4)
                if a.control:
                    ctx.screen.use()
                    ctx.viewport = (0, 0, *fb4)
                    v = View(Switches(), fb4, target=ctx.screen, viewport=(0, 0, *fb4))
                    r2.frame([v], fb4, 1.0)
                    ctx.screen.use()
                    p = _screen(ctx, fb4)
                    errv = v.error
                else:
                    target = off.fit(fb4)
                    v = View(Switches(), fb4, target=target, viewport=(0, 0, *fb4), samples=4)
                    r2.frame([v], fb4, 1.0)
                    GL.glFlush()
                    errv = v.error
                    lv.present(off.tex, fb4, swap=False)
                    p = _screen(lv.ctx, fbp)
                    glfw.swap_buffers(lv.win)
                    glfw.make_context_current(w4)
                out = {"frame": k, **_diff(d, p), "err": errv,
                       "ends": len(r1.renderer.stats.get("ends", [])),
                       "direct": r1.renderer.stats.get("direct"),
                       "lit": int((d[..., :3].max(axis=2) > 8).sum())}
            say(test="msaa-rig", control=a.control, slug=slug, hands=hands, **out)
            r1.close()
            r2.close()
            del r1, r2
            gc.collect()


def _capture(lv: Live, into: list):
    """`lv`'s presenter, its window's back buffer read straight after each present."""
    real = lv.pres.present

    def present(ho, size, target=None):
        real(ho, size, target)
        into.append(_screen(lv.ctx, tuple(size)))
    lv.pres.present = present


def draw_render(a) -> None:
    """The shipped `app._draw_render` on the real renderer and real looks: its
    window's back buffer against today's shape, the same rig drawn directly on a
    window with `SAMPLES 4` (on this context, as the old output 1 was). `--overlay`:
    both windows transparent, the renderer's ground at `--bg`, as overlay mode draws.
    The control, `--no-samples`, is `FRAME_SAMPLES` 0: what forgetting it costs."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import golden_frames as gf

    from hyperspace import app
    from hyperspace.outputs import Offscreen, Root, Slot, Switches, View
    from hyperspace.pacing import Pacer

    glfw.init()
    size = (640, 360)
    w4 = window(size, samples=4, transparent=a.overlay, pos=spot(a.mon), title="today's output 1")
    glfw.make_context_current(w4)
    glfw.swap_interval(0)
    ctx = moderngl.create_context()
    ctx.gc_mode = "auto"
    drain()
    lv = Live(w4, size=size, pos=spot(a.mon, 720), transparent=a.overlay, title="through _draw_render")
    glfw.make_context_current(w4)
    fb = tuple(glfw.get_framebuffer_size(w4))
    shots: list = []
    _capture(lv, shots)
    if a.no_samples:
        app.FRAME_SAMPLES = 0
    root = Root(w4, Offscreen(ctx), Pacer(glfw))
    slot = Slot(1, win=lv.win, presenter=lv.pres)
    if a.flip:
        slot.switches = Switches(flip_x=True, dim=0.6)
    say(test="draw-render-setup", overlay=a.overlay, fb=fb, no_samples=a.no_samples, flip=a.flip,
        window_see_through=_see_through(lv.win) if sys.platform == "darwin" else None,
        renderer=ctx.info["GL_RENDERER"], machine_locked=machine()["locked"], load=os.getloadavg()[0])
    totals = {"looks": 0, "identical": 0}
    for slug in a.slugs or sorted(gf.CORPUS_LOADABLES):
        for hands in ("present", "absent"):
            glfw.make_context_current(w4)
            try:
                r1 = gf.Rig(slug, hands, ctx)
                r2 = gf.Rig(slug, hands, ctx)
            except Exception as e:  # noqa: BLE001 — a look the rig won't load isn't the question
                say(test="draw-render", slug=slug, skipped=str(e)[:160])
                continue
            for r in (r1, r2):
                r.renderer.max_frame = a.cap and tuple(a.cap)
                r.renderer.bg_alpha = a.bg if a.overlay else 1.0
            proxy = SimpleNamespace(
                bg_alpha=r2.renderer.bg_alpha, max_frame=r2.renderer.max_frame,
                draw_outputs=lambda _s, w, h, dpr, views, r2=r2: r2.frame(views, (w, h), dpr))
            out = {}
            for k in range(a.frames):
                shots.clear()
                glfw.make_context_current(w4)
                ctx.screen.use()
                ctx.viewport = (0, 0, *fb)
                v = View(slot.switches, fb, target=ctx.screen, viewport=(0, 0, *fb),
                         bg_alpha=r1.renderer.bg_alpha)
                r1.frame([v], size, fb[0] / size[0])
                ctx.screen.use()
                d = _screen(ctx, fb)
                glfw.swap_buffers(w4)
                app._draw_render(proxy, ctx, r2.view, [slot], root)
                p = shots[-1]
                out = {"frame": k, **_diff(d, p), "scene_samples": r2.renderer.scene.samples,
                       "today_scene_samples": r1.renderer.scene.samples, "err": v.error,
                       "alpha_levels": len(np.unique(p[..., 3])), "alpha_min": int(p[..., 3].min()),
                       "lit": int((p[..., :3].max(axis=2) > 8).sum()),
                       "where_max": [int(x) for x in np.unravel_index(
                           np.abs(d.astype(int) - p.astype(int)).max(axis=2).argmax(), d.shape[:2])]}
            say(test="draw-render", slug=slug, hands=hands, **out)
            totals["looks"] += 1
            totals["identical"] += out["max"] == 0
            r1.close()
            r2.close()
            del r1, r2
            gc.collect()
    say(test="draw-render-total", **totals)
    glfw.terminate()


def v8(a) -> None:
    """Audit V8: a hot reload's hooks run with `current` current, the render context
    or the control window's (where `frame` used to run them, as `--case control`).
    What does the next frame, on the render context, then draw?"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import golden_frames as gf

    from hyperspace.outputs import Offscreen, Switches, View

    glfw.init()
    root = window((64, 64), visible=False, title="root")
    glfw.make_context_current(root)
    ctx = moderngl.create_context()
    ctx.gc_mode = "auto"
    drain()
    control = window((64, 64), visible=False, share=root, title="control")
    glfw.make_context_current(control)
    moderngl.create_context()
    drain()
    size = (640, 360)
    for slug in a.slugs:
        for hands in ("present", "absent"):
            glfw.make_context_current(root)
            drain()
            rig = gf.Rig(slug, hands, ctx)
            off = Offscreen(ctx)
            drew = []
            errors = []
            for phase in ("before", "after"):
                for _ in range(2):
                    v = View(Switches(), size, target=off.fit(size), viewport=(0, 0, *size), samples=4)
                    rig.frame([v], size, 1.0)
                drew.append(_pix(off.fbo, size))
                errors.append(v.error)
                if phase == "before":
                    glfw.make_context_current(root if a.case == "root" else control)
                    try:
                        rig.renderer.on_reload()
                        rig.renderer.ghost.on_reload()
                        errors.append(f"gl errors {drain()}")
                    except Exception as e:  # noqa: BLE001 — the answer
                        errors.append(f"on_reload raised {type(e).__name__}: {e}"[:200])
                    glfw.make_context_current(root)
                    drain()
            say(test="v8", case=a.case, slug=slug, hands=hands, lit_before=int((drew[0][..., :3].max(axis=2) > 8).sum()),
                lit_after=int((drew[1][..., :3].max(axis=2) > 8).sum()), errors=errors,
                frame_gl_errors=drain())
            rig.close()
            off.release()
            del rig
            gc.collect()
    glfw.terminate()


def _see_through(win) -> dict:
    """What makes a window see-through to the compositor: NSWindow's flag and
    the NSGL surface's opacity (GLFW sets both from TRANSPARENT_FRAMEBUFFER)."""
    import objc
    ns = objc.objc_object(c_void_p=glfw.get_cocoa_window(win))
    lib = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
    lib.sel_registerName.restype = ctypes.c_void_p
    lib.sel_registerName.argtypes = [ctypes.c_char_p]
    send = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
                            ctypes.c_long)(("objc_msgSend", lib))
    opacity = ctypes.c_int(-1)
    send(glfw.get_nsgl_context(win), lib.sel_registerName(b"getValues:forParameter:"),
         ctypes.byref(opacity), 236)                      # NSOpenGLContextParameterSurfaceOpacity
    return {"isOpaque": bool(ns.isOpaque()), "surface_opacity": opacity.value}


def alpha(a) -> None:
    """Today's transparent window against a transparent Presenter window."""
    glfw.init()
    size = (640, 360)
    w = window(size, samples=4, transparent=True, pos=spot(a.mon), title="direct transparent")
    glfw.make_context_current(w)
    glfw.swap_interval(0)
    ctx = moderngl.create_context()
    drain()
    fbw = tuple(glfw.get_framebuffer_size(w))
    h, wd = fbw[1], fbw[0]
    # premultiplied: a left-to-right alpha ramp over a colour, like the overlay
    ramp = np.zeros((h, wd, 4), dtype=np.uint8)
    al = np.linspace(0, 1, wd)[None, :].repeat(h, 0)
    ramp[..., 0] = (al * 220).astype(np.uint8)
    ramp[..., 1] = (al * 40).astype(np.uint8)
    ramp[..., 3] = (al * 255).astype(np.uint8)
    tex = ctx.texture(fbw, 4, ramp.tobytes())
    paint = Paint(ctx)
    ctx.screen.use()
    ctx.clear(0, 0, 0, 0)
    paint.to(ctx.screen, tex, fbw)
    direct = _screen(ctx, fbw)
    res: dict = {"direct_alpha_vs_ramp_max": _diff(direct[..., 3:4], ramp[..., 3:4])["max"]}
    glfw.swap_buffers(w)
    GL.glFlush()
    lv = Live(w, size=size, pos=spot(a.mon, 40, 500), transparent=True, title="presenter transparent")
    fbp = tuple(glfw.get_framebuffer_size(lv.win))

    def present():
        glfw.make_context_current(lv.win)
        lv.pres.present(Handoff(tex, fbw, (0, 0, *fbp), bg_alpha=0.0), fbp)

    present()
    pres = _screen(lv.ctx, fbp)
    res["presenter_vs_direct_rgba"] = _diff(direct, pres)
    glfw.swap_buffers(lv.win)
    res["transparent_flags"] = {n: _see_through(x) for n, x in (("direct", w), ("presenter", lv.win))}
    say(test="alpha-backbuffer", **res)
    if a.no_screen:
        glfw.terminate()
        return

    # through to the screen: magenta behind both, read what the compositor shows
    behind = []
    for win in (w, lv.win):
        x, y = glfw.get_window_pos(win)
        lw, lh = glfw.get_window_size(win)
        b = window((lw + 40, lh + 40), share=w, pos=(x - 20, y - 20), title="behind")
        glfw.make_context_current(b)
        glfw.swap_interval(0)
        glfw.set_window_attrib(b, glfw.FLOATING, True)
        behind.append(b)
    for win in (w, lv.win):
        glfw.set_window_attrib(win, glfw.FLOATING, True)
        glfw.show_window(win)
    frames = 0
    t_end = time.perf_counter() + 1.5
    while time.perf_counter() < t_end:
        glfw.poll_events()
        for b in behind:
            glfw.make_context_current(b)
            GL.glClearColor(1.0, 0.0, 1.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            glfw.swap_buffers(b)
        glfw.make_context_current(w)
        ctx.screen.use()
        ctx.clear(0, 0, 0, 0)
        paint.to(ctx.screen, tex, fbw)
        glfw.swap_buffers(w)
        present()
        glfw.swap_buffers(lv.win)
        frames += 1
    shots = []
    for name, win in (("direct", w), ("presenter", lv.win)):
        x, y = glfw.get_window_pos(win)
        lw, lh = glfw.get_window_size(win)
        path = f"/tmp/sc3a_{os.getpid()}_{name}.png"
        r = subprocess.run(["screencapture", "-x", "-R", f"{x},{y},{lw},{lh}", path],
                           capture_output=True, text=True, check=False)
        shots.append((name, path, r.returncode, r.stderr[:100]))
    from PIL import Image
    out: dict = {}
    pics = {}
    for name, path, rc, err in shots:
        if rc != 0 or not Path(path).exists():
            out[name] = {"capture_failed": err}
            continue
        im = np.array(Image.open(path).convert("RGB")).astype(int)
        row = im[im.shape[0] // 2]
        n = row.shape[0]
        pics[name] = im
        out[name] = {"size": im.shape[:2], "left": row[n // 20].tolist(), "mid": row[n // 2].tolist(),
                     "right": row[n - n // 20].tolist()}
        Path(path).unlink(missing_ok=True)
    if len(pics) == 2:
        A, B = pics["direct"], pics["presenter"]
        hh, ww = min(A.shape[0], B.shape[0]), min(A.shape[1], B.shape[1])
        d = np.abs(A[:hh, :ww] - B[:hh, :ww])
        out["screen_direct_vs_presenter"] = {"max": int(d.max()), "mean": round(float(d.mean()), 3)}
    say(test="alpha-screen", frames=frames, expect_mid_over_magenta_srgbish=[237, 20, 127], **out)
    glfw.terminate()


# ------------------------------------------------------------ 4: cost at 1080p

def cost(a) -> None:
    """Uncapped: nothing waits, glFinish on each frame, so the mean frame is
    the whole CPU + GPU price of a shape at a 1080p framebuffer."""
    glfw.init()
    size = (1920, 1080)
    shape = a.shape
    pos = spot(a.mon, 40, 40)
    lv = None
    if shape == "today":
        root, ctx = root_context(visible=True, samples=4, size=size, interval=0)
        glfw.set_window_pos(root, *pos)
        fb = tuple(glfw.get_framebuffer_size(root))
    else:
        root, ctx = root_context(visible=False, interval=0)
        lv = Live(root, size=size, pos=pos, transparent=a.transparent)
        fb = tuple(glfw.get_framebuffer_size(lv.win))
        glfw.make_context_current(root)
    work = Work(ctx, size=fb, lines=a.lines)
    paint = Paint(ctx)
    off_tex = ctx.texture(fb, 4)
    off = ctx.framebuffer(color_attachments=[off_tex])
    dts, swaps = [], []
    last = time.perf_counter()
    end = last + a.secs
    while last < end:
        glfw.poll_events()
        glfw.make_context_current(root)
        tex = work.draw()
        if lv is None:
            paint.to(ctx.screen, tex, fb)
            GL.glFinish()
            t0 = time.perf_counter()
            glfw.swap_buffers(root)
        else:
            if shape == "presenter-copy":      # the view ends on an Offscreen first
                paint.to(off, tex, fb)
                tex = off_tex
            GL.glFlush()
            lv.present(tex, fb, swap=False)
            GL.glFinish()
            t0 = time.perf_counter()
            glfw.swap_buffers(lv.win)
        swaps.append(time.perf_counter() - t0)
        now = time.perf_counter()
        dts.append(now - last)
        last = now
    say(test="cost", shape=shape, fb=fb, lines=a.lines, transparent=a.transparent, **stats(dts, 30),
        swap_ms_mean=round(statistics.mean(swaps[30:]) * 1e3, 3))
    glfw.terminate()


# ------------------------------------------------------------ 5: a display changes

def vdisplay(a) -> None:
    """A real display as the window server sees it, added now and removed when
    this process exits: CoreGraphics' private CGVirtualDisplay."""
    import objc
    from Foundation import NSDate, NSRunLoop
    ns = {c: objc.lookUpClass(c) for c in (
        "CGVirtualDisplay", "CGVirtualDisplayDescriptor", "CGVirtualDisplayMode",
        "CGVirtualDisplaySettings")}
    d = ns["CGVirtualDisplayDescriptor"].alloc().init()
    d.setName_("sc3a spike")
    d.setMaxPixelsWide_(a.w)
    d.setMaxPixelsHigh_(a.h)
    d.setSizeInMillimeters_((600.0, 340.0))
    d.setVendorID_(0x5343)
    d.setProductID_(0x3361)
    d.setSerialNum_(1)
    v = ns["CGVirtualDisplay"].alloc().initWithDescriptor_(d)
    if v is None:
        raise SystemExit("no virtual display")
    s = ns["CGVirtualDisplaySettings"].alloc().init()
    s.setHiDPI_(0)
    s.setModes_([ns["CGVirtualDisplayMode"].alloc().initWithWidth_height_refreshRate_(a.w, a.h, a.hz)])
    ok = v.applySettings_(s)
    print(json.dumps({"vdisplay": int(v.displayID()), "applied": bool(ok)}), flush=True)
    NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(a.secs))


def monitor(a) -> None:
    glfw.init()
    seen: list = []
    t0 = time.perf_counter()

    def on_monitor(m, event):
        up = event == glfw.CONNECTED
        name = glfw.get_monitor_name(m).decode() if up else "(gone)"
        seen.append((round(time.perf_counter() - t0, 3), "connected" if up else "disconnected", name))

    glfw.set_monitor_callback(on_monitor)
    root, ctx = root_context()
    work = Work(ctx, lines=500)
    keep = Live(root, pos=spot(0), size=(320, 180))    # a survivor, not pacing

    def pump(secs, lives=(), timer=None, record=None):
        end = time.perf_counter() + secs
        last = time.perf_counter()
        while time.perf_counter() < end:
            glfw.poll_events()
            glfw.make_context_current(root)
            tex = work.draw()
            GL.glFlush()
            keep.present(tex, work.size)
            for lv in lives:
                lv.present(tex, work.size)
            if timer:
                timer.wait()
            now = time.perf_counter()
            if record is not None:
                record.append(now - last)
            last = now

    timer = Timer()
    before = [glfw.get_monitor_name(m).decode() for m in glfw.get_monitors()]
    say(test="monitor", monitors_before=before)
    for cycle in range(a.cycles):
        seen.clear()
        p = subprocess.Popen([sys.executable, __file__, "vdisplay", "--secs", str(a.hold), "--hz", str(a.hz)],
                             stdout=subprocess.PIPE, text=True)
        line = p.stdout.readline()
        t_add = time.perf_counter()
        waits: list[float] = []
        mon = None
        while time.perf_counter() - t_add < 6.0 and mon is None:
            pump(0.05, timer=timer, record=waits)
            for m in glfw.get_monitors():
                if glfw.get_monitor_name(m).decode() not in before:
                    mon = m
        res: dict = {"cycle": cycle, "helper": line.strip(),
                     "seen_after_s": round(time.perf_counter() - t_add, 3), "callbacks": list(seen)}
        if mon is None:
            res["monitor_seen"] = False
            say(test="monitor", **res)
            p.kill()
            p.wait()
            break
        res["monitor"] = glfw.get_monitor_name(mon).decode()
        res["refresh"] = glfw.get_video_mode(mon).refresh_rate
        res["size"] = tuple(glfw.get_video_mode(mon).size)
        res["add_stall_loop"] = stats(waits, 0)
        x, y, w, h = glfw.get_monitor_workarea(mon)
        lv = Live(root, size=(w - 40, h - 40), pos=(x + 20, y + 20), interval=1, title="on vdisplay")
        res["made_ms"] = lv.made_ms
        res["window_screen"] = occlusion(lv.win)
        dts: list[float] = []
        pump(a.settle, lives=[lv], record=dts)
        res["paced_on_it"] = stats(dts)
        # now it goes: the pacer's display, with nothing told to the loop
        seen.clear()
        p.kill()
        gone: list[float] = []
        pump(4.0, lives=[lv], record=gone)
        p.wait()
        res["unplug_callbacks"] = list(seen)
        res["unplug_first_frames_ms"] = [round(d * 1e3, 1) for d in gone[:4]]
        res["unplug_max_ms"] = round(max(gone) * 1e3, 1)
        res["paced_after_unplug"] = stats(gone[len(gone) // 2:], 0)
        res["window_after"] = {"pos": glfw.get_window_pos(lv.win), **occlusion(lv.win),
                               "should_close": bool(glfw.window_should_close(lv.win))}
        expect = (9, 8, 7, 255)
        glfw.make_context_current(root)
        tx = solid_tex(ctx, (64, 64), expect)
        GL.glFlush()
        lv.present(tx, (64, 64), swap=False)
        res["presenter_still_draws"] = read_centre(lv) == expect
        glfw.swap_buffers(lv.win)
        glfw.make_context_current(root)
        tx.release()
        res["close_ms"] = lv.close(root)
        say(test="monitor", **res)
        pump(1.0, timer=timer)
    say(test="monitor", monitors_after=[glfw.get_monitor_name(m).decode() for m in glfw.get_monitors()])
    glfw.terminate()


# ------------------------------------------------------------ 1: indefinitely

def soak(a) -> None:
    """Rendering with nothing on screen, for a long time, bucket by bucket:
    App Nap, a dropped context, a slow leak. `--visible` adds one small
    window; `--swap` swaps the hidden root instead of the timer."""
    glfw.init()
    root, ctx = root_context()
    work = Work(ctx)
    lives = []
    if a.visible:
        lives = [Live(root, pos=spot(a.mon), size=(320, 180))]
        glfw.make_context_current(root)
    timer = None if a.swap else Timer()
    t0 = last = time.perf_counter()
    bucket: list[float] = []
    next_report = t0 + a.every
    while last - t0 < a.secs:
        glfw.poll_events()
        glfw.make_context_current(root)
        tex = work.draw()
        GL.glFlush()
        for lv in lives:
            lv.present(tex, work.size)
        glfw.make_context_current(root)
        if a.swap:
            glfw.swap_buffers(root)
        else:
            timer.wait()
        now = time.perf_counter()
        bucket.append(now - last)
        last = now
        if now >= next_report:
            px = np.frombuffer(work.fbo.read(viewport=(0, 0, 64, 64), components=4), dtype=np.uint8)
            say(test="soak", at_s=round(now - t0), **stats(bucket, 0), rss_kb=rss_kb(),
                drew=bool(px.any()), swap=a.swap, visible=a.visible)
            bucket = []
            next_report = now + a.every
    glfw.terminate()


def machine() -> dict:
    """Whether a swap can wait at all: locked, displays asleep, nobody there."""
    import Quartz
    d = Quartz.CGSessionCopyCurrentDictionary() or {}
    _err, ids, n = Quartz.CGGetOnlineDisplayList(8, None, None)
    shows = []
    for i in ids[:n]:
        shows.append({"id": int(i), "asleep": bool(Quartz.CGDisplayIsAsleep(i)),
                      "active": bool(Quartz.CGDisplayIsActive(i))})
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements, 0) or []
    top = [(str(w.get("kCGWindowOwnerName")), int(w.get("kCGWindowLayer", 0)),
            int(w["kCGWindowBounds"]["Width"]), int(w["kCGWindowBounds"]["Height"]))
           for w in list(windows)[:8]]
    return {"locked": bool(d.get("CGSSessionScreenIsLocked", False)),
            "on_console": bool(d.get("kCGSSessionOnConsoleKey", False)),
            "idle_s": round(Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateCombinedSessionState, Quartz.kCGAnyInputEventType), 1),
            "displays": shows, "top_windows": top}


def state(_a) -> None:
    say(test="machine", **machine())


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("state")
    p.set_defaults(fn=state)
    p = sub.add_parser("pacing")
    p.add_argument("--shape", required=True, choices=[
        "today", "hidden-swap", "hidden-only-swap", "hidden-timer", "hidden-only-timer",
        "presenter-vsync", "two-vsync", "occluded", "guarded"])
    p.add_argument("--secs", type=float, default=20)
    p.add_argument("--mon", type=int, default=0)
    p.add_argument("--mon2", type=int, default=2)
    p.add_argument("--hz", type=float, default=60.0)
    p.set_defaults(fn=pacing)
    p = sub.add_parser("handover")
    p.add_argument("--phase", type=float, default=6)
    p.add_argument("--mon", type=int, default=0)
    p.add_argument("--mon2", type=int, default=2)
    p.set_defaults(fn=handover)
    p = sub.add_parser("cycles")
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--frames", type=int, default=5)
    p.add_argument("--mon", type=int, default=0)
    p.set_defaults(fn=cycles)
    p = sub.add_parser("leak")
    p.add_argument("--n", type=int, default=301)
    p.add_argument("--layer", type=int, default=0)
    p.add_argument("--pool", action="store_true")
    p.set_defaults(fn=leak)
    p = sub.add_parser("root-death")
    p.add_argument("--case", required=True, choices=[
        "destroy-member", "destroy-member-while-current", "destroy-root",
        "release-in-wrong-context", "destroy-without-release"])
    p.set_defaults(fn=root_death)
    p = sub.add_parser("msaa")
    p.add_argument("--mon", type=int, default=0)
    p.add_argument("--no-rig", action="store_true")
    p.add_argument("--slugs", nargs="*")
    p.add_argument("--rig-frames", type=int, default=3)
    p.add_argument("--control", action="store_true",
                   help="both rigs direct: the noise floor of two identical draws")
    p.set_defaults(fn=msaa)
    p = sub.add_parser("draw-render")
    p.add_argument("--mon", type=int, default=0)
    p.add_argument("--slugs", nargs="*")
    p.add_argument("--frames", type=int, default=3)
    p.add_argument("--overlay", action="store_true")
    p.add_argument("--bg", type=float, default=0.0, help="overlay: the renderer's ground alpha")
    p.add_argument("--no-samples", action="store_true", help="the control: FRAME_SAMPLES 0")
    p.add_argument("--flip", action="store_true", help="output 1 flipped and dimmed")
    p.add_argument("--cap", type=int, nargs=2, help="the render cap, w h")
    p.set_defaults(fn=draw_render)
    p = sub.add_parser("v8")
    p.add_argument("--case", choices=["root", "control"], default="root")
    p.add_argument("--slugs", nargs="*", default=["party-tumble", "hands-orbit"])
    p.set_defaults(fn=v8)
    p = sub.add_parser("alpha")
    p.add_argument("--mon", type=int, default=0)
    p.add_argument("--no-screen", action="store_true")
    p.set_defaults(fn=alpha)
    p = sub.add_parser("cost")
    p.add_argument("--shape", required=True, choices=["today", "presenter", "presenter-copy"])
    p.add_argument("--secs", type=float, default=10)
    p.add_argument("--mon", type=int, default=0)
    p.add_argument("--lines", type=int, default=4000)
    p.add_argument("--transparent", action="store_true")
    p.set_defaults(fn=cost)
    p = sub.add_parser("vdisplay")
    p.add_argument("--secs", type=float, default=10)
    p.add_argument("--w", type=int, default=1280)
    p.add_argument("--h", type=int, default=720)
    p.add_argument("--hz", type=float, default=60.0)
    p.set_defaults(fn=vdisplay)
    p = sub.add_parser("monitor")
    p.add_argument("--cycles", type=int, default=3)
    p.add_argument("--hold", type=float, default=600)
    p.add_argument("--settle", type=float, default=6)
    p.add_argument("--hz", type=float, default=60.0)
    p.set_defaults(fn=monitor)
    p = sub.add_parser("soak")
    p.add_argument("--secs", type=float, default=900)
    p.add_argument("--every", type=float, default=60)
    p.add_argument("--swap", action="store_true")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--mon", type=int, default=0)
    p.set_defaults(fn=soak)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
