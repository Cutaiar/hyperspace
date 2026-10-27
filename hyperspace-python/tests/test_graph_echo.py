# ruff: noqa: F811 — `ctx` is test_graph_faces' fixture, taken as each GL test's argument
"""Plan 34 T3 — the look-back's frames as sources (E, rows 360–363):
`echo.<k>`, the ring's k-th newest commit, and `dream`, the dream buffer,
wireable into any picture port. Plan 36 T4: an echo is the look-back's own
output, `lookback.echo.<k>` (an old section's `echo.<k>` migrates to it),
and the dream is the dream node, fed the look-back.

What it must keep honest: echo.1 is the newest commit and echo.k the k-th
newest; one the ring does not hold yet (fewer than k commits, the ring
just remade for a `dream.res` change) reads nothing, so the faces show the
pattern and an output its ground; the ring keeps capturing while the graph
reads it with the look-back off, and the wake still shows only with
`dream.on`; an echo read this frame is last frame's capture; the words say
the echo's size, cadence and what it holds.

The GL tests use test_graph_faces' harness; they skip without a standalone
context."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from test_graph_faces import (
    Still,
    _draw,
    _empty,
    _faces,
    _fbo,
    _media,
    _px,
    _renderer,
    _rgba,
    _rig_frame,
    ctx,  # noqa: F401 — the GL context fixture, taken as each GL test's argument
)

from hyperspace import graph as G
from hyperspace.graphmigrate import wired_wiring
from hyperspace.lookback import MAX_ECHOES
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View

RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)
moderngl = pytest.importorskip("moderngl")


REMAKING = "the look-back is remaking its frames (resolution changed)"


def _reading(node):
    """Whether an echo's words say it read (its size first)."""
    return node.said[:1].isdigit()


def _echo(k):
    return {"kind": "echo", "index": k}


def _views(ctx, size, n=2):
    return [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(n)]


def _frame(ctx, r, s, vs, size, k):
    r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


def _mid(px):
    h, w = px.shape[:2]
    return tuple(int(c) for c in px[h // 2, w // 2, :3])


def _near(a, b, d=2):
    return all(abs(x - y) <= d for x, y in zip(a, b, strict=True))


def _off(r, gap=0.0):
    """A capture every frame (plan 36 T4: the old words' look-back off —
    drawn only for the echoes read off its ring)."""
    st = r.lookback.state
    st.on, st.gap = False, gap
    return r


def _three(r, size):
    """The ring made at `size` and three captures written by hand: red,
    green, blue at t = 1, 2, 3 (echo.1 the blue)."""
    lb = r.lookback
    assert lb._ensure(*size)
    ew, eh = lb.echo
    for slot, colour in enumerate((RED, GREEN, BLUE)):
        lb.write_slot(slot, _rgba(ew, eh, colour), at=float(slot + 1))
    assert lb.held() == 3


def test_the_echo_nodes_say_what_they_are():
    """The two nodes' shapes (plan 36 T4: an echo a look-back's pin, the
    dream picture in → picture out), and the graph built from an old
    section's wires out of them: the echo its look-back's, the dream fed
    the look-back."""
    assert G.EchoNode.KIND == "echo" and G.EchoNode.INPUTS == {}
    assert G.EchoNode.OUTPUT == G.IMAGE and not G.EchoNode.TIMED
    assert G.DreamNode.KIND == "dream" and G.DreamNode.INPUTS == {"image": G.IMAGE}
    assert G.DreamNode.OUTPUT == G.IMAGE
    assert G.EchoNode("lookback.echo.3", 3).k == 3
    vs = [View(Switches(), (64, 48)), View(Switches(), (64, 48))]
    spec = G.read_graph({"nodes": [_echo(3), {"kind": "dream"}],
                         "wires": [{"from": "frame", "to": "fx.image"},
                                   {"from": "echo.3", "to": "shape.faces"},
                                   {"from": "dream", "to": "output.2.image"}]})
    assert not spec.notes, spec.notes
    g = G.build_graph(vs, wired_wiring(spec.wiring()))
    echo = g.nodes["lookback.echo.3"]
    assert isinstance(echo, G.EchoNode) and echo.k == 3 and echo.lookback == "lookback"
    assert isinstance(g.nodes["dream"], G.DreamNode)
    assert g.nodes["dream"].inputs["image"] is g.nodes["lookback"]
    assert g.nodes["shape"].inputs["faces"] is echo
    assert not g.dormant
    assert "lookback" not in G.build_graph(vs, wired_wiring(G.Wiring(run=()))).nodes


def test_echo_k_is_the_kth_newest_capture(ctx):
    """Three slots written red, green, blue at t = 1, 2, 3: `echo.1 →
    output.2.image` shows blue, echo.2 green and echo.3 red, each at the
    output's centre (row 360)."""
    size = (160, 120)
    for k, want in ((1, BLUE), (2, GREEN), (3, RED)):
        r = _off(_renderer(ctx, None, [(f"echo.{k}", "output.2.image")], [_echo(k)]))
        _three(r, size)
        out = _frame(ctx, r, _faces(), _views(ctx, size), size, 0)[1]
        assert _near(_mid(out), want), (k, _mid(out))


def test_an_echo_past_the_ring_reads_nothing(ctx):
    """With three captures, `echo.4 → shape.faces` draws the faces-unwired
    frame (the pattern, row 361) and `echo.4 → output.2.image` the
    ground; the node says how many the ring holds."""
    size = (160, 120)
    s = _faces(pattern=2)
    plain = _draw(ctx, _off(_renderer(ctx)), s)[0]
    r = _off(_renderer(ctx, None, [("echo.4", "shape.faces")], [_echo(4)]))
    _three(r, size)
    (got,) = _frame(ctx, r, s, _views(ctx, size, 1), size, 0)
    assert np.array_equal(got, plain) and r.face_error == ""
    assert r._graph.nodes["lookback.echo.4"].said == f"not held yet: the ring holds 3 of {MAX_ECHOES}"
    r = _off(_renderer(ctx, None, [("echo.4", "output.2.image")], [_echo(4)]))
    _three(r, size)
    out = _frame(ctx, r, s, _views(ctx, size), size, 0)[1]
    assert _mid(out) == (0, 0, 0)


def test_the_ring_keeps_capturing_for_an_echo_with_the_look_back_off(ctx):
    """`dream.on` off, gap 0, `echo.1 → output.2.image`: after three frames
    the ring holds three (row 362), and output 1 — no wake — is the same
    section's frame without the echo wire. The wire removed, the ring goes
    idle in one frame."""
    size, s = (160, 120), _faces()
    r = _off(_renderer(ctx, None, [("echo.1", "output.2.image")], [_echo(1)]))
    plain_r = _off(_renderer(ctx))
    vs, plain_vs = _views(ctx, size), _views(ctx, size)
    for k in range(3):
        got = _frame(ctx, r, s, vs, size, k)[0]
        want = _frame(ctx, plain_r, s, plain_vs, size, k)[0]
        assert np.array_equal(got, want), k
    assert r.lookback.held() == 3 and "lookback" in r._graph.nodes
    assert plain_r.lookback.held() == 0 and "lookback" not in plain_r._graph.nodes
    r.wiring = wired_wiring(G.read_graph({"nodes": [], "wires": [{"from": "frame",
                                                      "to": "fx.image"}]}).wiring())
    _frame(ctx, r, s, vs, size, 3)
    assert r.lookback.held() == 0


def test_an_echo_read_this_frame_is_last_frames_capture(ctx):
    """Gap 0, a still changing colour each frame on the backdrop (the
    history holding it), `echo.1 → output.2.image`: output 2 at frame n is
    the backdrop's colour at frame n−1 (row 363) — the echo is read before
    this frame's capture writes."""
    size = (160, 120)
    still = Still(_rgba(16, 9, RED))
    m = _media(a=still)
    m.channels["a"].fit = 2                                   # stretch: fills
    r = _off(_renderer(ctx, m, [("media.a", "backdrop.image"),
                                ("echo.1", "output.2.image")], [_echo(1)], history=True))
    vs = _views(ctx, size)
    s = _empty(backdrop_history=True)
    colours = (RED, GREEN, BLUE, RED, GREEN)
    got = []
    for k, colour in enumerate(colours):
        still.f = MediaFrame(_rgba(16, 9, colour), 1.0, k)
        got.append(_mid(_frame(ctx, r, s, vs, size, k)[1]))
    assert got[0] == (0, 0, 0), got
    for k in range(1, len(colours)):
        assert _near(got[k], colours[k - 1]), (k, got)


def test_a_res_change_empties_the_echoes(ctx):
    """After four frames `dream.res` goes 2 → 3: echo.1 reads nothing the
    next frame (the ring is remade), reads again the frame after, and
    echo.2 only once two commits have landed (row 361)."""
    size, s = (160, 120), _faces()
    r = _off(_renderer(ctx, None, [("echo.1", "output.2.image"),
                                   ("echo.2", "output.3.image")], [_echo(1), _echo(2)]))
    vs = _views(ctx, size, 3)
    for k in range(4):
        _frame(ctx, r, s, vs, size, k)
    g = r._graph
    assert g.nodes["lookback.echo.1"].said.startswith("344×256 · ")
    r.lookback.state.res = 3
    reads = []
    for k in range(4, 7):
        _frame(ctx, r, s, vs, size, k)
        g = r._graph
        reads.append((_reading(g.nodes["lookback.echo.1"]), _reading(g.nodes["lookback.echo.2"])))
        if k == 4:
            assert g.nodes["lookback.echo.1"].said == REMAKING
    assert reads == [(False, False), (True, False), (True, True)], reads
    assert r.lookback.echo == (512, 384)


def test_a_res_change_to_the_same_size_keeps_the_echoes(ctx):
    """Fix round 1 (minor 1): a `dream.res` whose echo size comes out the
    same (here the atlas capped by `fit_atlas` to the driver's largest
    texture) makes no new ring, so the echoes go on reading."""
    size, s = (160, 120), _faces()
    r = _off(_renderer(ctx, None, [("echo.1", "output.2.image")], [_echo(1)]))
    r.lookback.max_texture = lambda: 2048
    vs = _views(ctx, size)
    for k in range(3):
        _frame(ctx, r, s, vs, size, k)
    assert r.lookback.echo == (80, 64)
    r.lookback.state.res = 3
    for k in range(3, 5):
        _frame(ctx, r, s, vs, size, k)
        assert _reading(r._graph.nodes["lookback.echo.1"]), (k, r._graph.nodes["lookback.echo.1"].said)
    assert r.lookback.echo == (80, 64) and r.lookback.held() == 5


def test_an_echo_into_an_outputs_hands_reads_last_frames_capture(ctx):
    """Fix round 1 (Important 1): an echo at an output's `hands` is read
    before this frame's capture, as at its `image`: at
    frame 0 the ring holds nothing yet, and over three hand-written
    captures echo.k laid over output 2 is the k-th newest — not the
    (black) commit this frame's capture lands."""
    size = (160, 120)
    r = _off(_renderer(ctx, None, [("echo.1", "output.2.hands")], [_echo(1)]))
    _frame(ctx, r, _empty(), _views(ctx, size), size, 0)
    g = r._graph
    assert g.nodes["lookback.echo.1"] in g.nodes["lookback(capture)"].after
    assert g.nodes["lookback.echo.1"].said == f"not held yet: the ring holds 0 of {MAX_ECHOES}"
    # (an echo never reaches a `readout`: that port takes a hands layer's
    # guide, refused at read — what is wired there runs before the capture too)
    spec = G.read_graph({"nodes": [_echo(1)],
                         "wires": [{"from": "echo.1", "to": "output.2.readout"}]})
    # (an old section's: its own words, before the migration)
    assert spec.notes and "takes a hands layer's guide" in spec.notes[0]
    for k, want in ((1, BLUE), (3, RED)):
        r = _off(_renderer(ctx, None, [(f"echo.{k}", "output.2.hands")], [_echo(k)]))
        _three(r, size)
        out = _frame(ctx, r, _empty(), _views(ctx, size), size, 0)[1]
        assert _near(_mid(out), want), (k, _mid(out))


def test_the_dream_reads_nothing_until_written(ctx):
    """`dream → output.2.image` (plan 36 T4: the dream node, fed the
    look-back's trail): off it passes the trail through — nothing in the
    ring yet, the ground — and says so. On, with pixels written into the
    dream buffer (a fake worker attached), output 2 shows them laid over
    at mix 1, and the words name the buffer's size (row 361)."""
    size, s = (160, 120), _faces()
    r = _off(_renderer(ctx, None, [("dream", "output.2.image")], [{"kind": "dream"}]))
    vs = _views(ctx, size)
    out = _frame(ctx, r, s, vs, size, 0)[1]
    assert _mid(out) == (0, 0, 0)
    assert r._graph.nodes["dream"].said.startswith("off: the picture passes through")
    dr = r.dreamer
    dr.state.on, dr.state.mix, dr.state.darken = True, 1.0, 0.0
    dr.source = SimpleNamespace(latest=lambda: None, submit=lambda *a: None)
    assert dr._ensure(*size)
    ew, eh = dr.size
    dr.write_from(_rgba(ew, eh, GREEN), 1)
    out = _frame(ctx, r, s, vs, size, 1)[1]
    assert _near(_mid(out), GREEN), _mid(out)
    assert r._graph.nodes["dream"].said.startswith(f"{ew}×{eh} · ")


def _holds(ctx, size, gap, nodes=(), frames=2):
    r = _off(_renderer(ctx, None, [("echo.1", "output.2.image")], [_echo(1), *nodes]), gap)
    vs = _views(ctx, size)
    for k in range(frames):
        _frame(ctx, r, _faces(), vs, size, k)
    return r._graph.nodes["lookback.echo.1"].said


def test_echo_words_say_size_and_cadence(ctx):
    """At 960×600, `dream.res` 2 (256), after two frames (eight at a gap of
    0.1 s, its first commit six frames in): the echo's size, its cadence
    and what the capture holds (row 363)."""
    size = (960, 600)
    assert _holds(ctx, size, 0.0) == "408×256 · every frame · the scene"
    assert _holds(ctx, size, 0.1, frames=8) == "408×256 · every 0.10 s · the scene"
    said = _holds(ctx, size, 0.0, [{"kind": "history", "holds": "scene+hands"}])
    assert said == "408×256 · every frame · the scene + hands"


def test_an_echo_on_the_faces_is_fitted(ctx):
    """`echo.1 → shape.faces`: the shape's prepare paints the slot into the
    faces' picture (1024²), cover-fitted — its centre the slot's colour,
    no face error (row 368)."""
    size = (160, 120)
    r = _off(_renderer(ctx, None, [("echo.1", "shape.faces")], [_echo(1)]))
    lb = r.lookback
    assert lb._ensure(*size)
    ew, eh = lb.echo
    lb.write_slot(4, _rgba(ew, eh, GREEN), at=1.0)
    lb.write_slot(5, _rgba(ew, eh, BLUE), at=0.5)       # an older one beside it
    _frame(ctx, r, _faces(), _views(ctx, size, 1), size, 0)
    assert r.face_error == ""
    tex = r.face_pic.tex
    w, h = tex.size
    px = np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4)
    assert _near(tuple(int(c) for c in px[h // 2, w // 2, :3]), GREEN)


def test_the_echo_faces_fixture_shows_the_ring(ctx):
    """The `echo-faces` golden (`echo.3 → shape.faces`, look-back off, gap
    0) after the golden's 8 frames: the ring held for the graph, echo.3
    read, and the faces not the pattern's — the frame is not party-faces'."""
    got, r = _rig_frame(ctx, "echo-faces", frames=8)
    plain, _ = _rig_frame(ctx, "party-faces", frames=8)
    lb = r.lookback
    assert lb.held() >= 3 and "lookback" in r._graph.nodes
    node = r._graph.nodes["lookback.echo.3"]
    assert isinstance(node, G.EchoNode) and not node.said.startswith("not held"), node.said
    assert r.face_error == "" and not r._graph.dormant
    assert np.abs(got[..., :3] - plain[..., :3]).max() > 40


def test_an_echo_into_hands_reads_nothing_when_the_ring_failed_to_rebuild(ctx):
    """Fix round 2: echo.1 at output 2's `hands` takes its slot before the
    capture; the capture then fails to make the ring again (a resize: here
    the ring released right after it, `atlas` None). The frame draws — no
    raise, no GL error — with the hands the picture made before the capture
    (`Output.settle` asks for it first: last frame's blue). Anything asking
    the echo after that failed remake, with the slot it took, reads nothing
    (R7): no own size, and `paint` clears to the ground rather than handing
    `_refit` no texture."""
    size = (160, 120)
    r = _off(_renderer(ctx, None, [("echo.1", "output.2.hands")], [_echo(1)]))
    _three(r, size)
    lb = r.lookback
    real = lb.capture

    def failed(scene, target):
        real(scene, target)
        lb.release_ring()                  # the remake that could not be made

    lb.capture = failed
    out = _frame(ctx, r, _empty(), _views(ctx, size), size, 0)[1]
    assert lb.atlas is None and _near(_mid(out), BLUE), _mid(out)
    node = r._graph.nodes["lookback.echo.1"]
    frame = SimpleNamespace(r=r, ctx=ctx, bg_alpha=1.0, size=size,
                            data={"lookback.echo.1#slot": (2, lb.frame - 1)})
    frame.root = frame
    assert node._slot(frame) == 2                   # the slot it took …
    assert not node.reads(frame) and node.own_size(frame) is None   # … reads nothing
    fbo = _fbo(ctx, *size)
    fbo.viewport = (0, 0, *size)
    fbo.use()
    fbo.clear(0.5, 0.5, 0.5, 1.0)
    node.paint(frame, fbo)
    assert ctx.error == "GL_NO_ERROR" and _mid(_px(fbo)) == (0, 0, 0)
