"""Register row 790, the owner, 2026-11-06: video sound reaching the look off air through
the analyzer is accepted, and is not a breach of "no loadable patch can affect another".

The first part names the road, on real objects: a video on the `Deck` on air, heard through
the shared mixer (`app.MediaIO`, `Mixer._callback`), pushed into the one analyzer
(`AudioEngine.start_mix`), read by the route of the `Deck` off air. It also says what this road
moves and what it doesn't; row 702 has the other known limits, which aren't this road's. The
second holds the words on the toggle: true for the state, and fitting the pane.

No audio device: the mixer gets test_media_mixer's fake stream, and a test pulls the blocks.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import cache
from types import SimpleNamespace as NS

import numpy as np
import pytest
from imgui_bundle import imgui
from test_audio import fake_sd  # noqa: F401 — the fixture
from test_audio_mix import HZ, Sine
from test_media_mixer import DT, Factory, Here, VideoOpener
from test_ui_pane import _only, _spills, _st, _tall_driver
from test_ui_shell import build_rig
from test_undo import boot
from ui_driver import WIDGETS

from hyperspace import app, lfo, ui, ui_graph, ui_pane, undo
from hyperspace.analysis import FFT_SIZE, Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.audio import AudioEngine
from hyperspace.control import Control
from hyperspace.deck import Deck, MetaController
from hyperspace.media import mixer as M
from hyperspace.media.channels import Channels, MediaSources
from hyperspace.media.video import AUDIO_RATE
from hyperspace.params import build_meta
from hyperspace.routing import Binding
from hyperspace.ui import PAGE_KEYS

TARGET = "view.bright"   # what the route off air moves
ON_AIR_VIDEO, OFF_AIR_VIDEO = "shared:on.mp4", "shared:off.mp4"
BLOCKS_A_FRAME = max(1, round(AUDIO_RATE * DT / M.BLOCK))  # the sound card keeps the transport's pace


@cache
def _lane_of_the_tone() -> int:
    """The band `Sine`'s tone lands in, asked of an analyzer of its own: a table takes one
    route to a param, so the test's one route has to be on the lane that will move."""
    probe = AudioEngine()
    tone = 0.5 * np.sin(2 * np.pi * HZ * np.arange(FFT_SIZE) / AUDIO_RATE)
    for _ in range(30):
        probe.analyser.feed(tone.astype(np.float32))
        probe.chain.step(DT)
    return int(np.argmax(probe.chain.lanes[: probe.chain.n]))


@pytest.fixture()
def road(tmp_path, fake_sd):  # noqa: F811
    """Two `Deck`s as `app.main` makes them, each with its own channels over the one
    media sources and the one analyzer, listening to the mix. Each `Deck` has one video
    with its own soundtrack; neither's sound is on yet. The `Deck` off air has one route."""
    r = boot(tmp_path / "home")
    sources = MediaSources(Here(ON_AIR_VIDEO, OFF_AIR_VIDEO), opener=VideoOpener())
    streams = Factory()
    sources.mixer = M.Mixer(make=streams)
    first, second = Channels(sources=sources), Channels(sources=sources)
    one = Deck.beside(r.deck, media=first, lfos=lfo.LFOs(seed=1))
    two = Deck.beside(r.deck, media=second, lfos=lfo.LFOs(seed=1))
    meta = MetaController(one, two, mix=r.mix)
    io = app.MediaIO(NS(stop=lambda: None), first)
    io.seat(meta)                                            # app.main's line
    first.assign("a", 0, ON_AIR_VIDEO)
    second.assign("a", 0, OFF_AIR_VIDEO)
    io.poll(DT, 0.0)                                         # the sources open
    first.channels["a"].source.audio = Sine(0.5)
    second.channels["a"].source.audio = Sine(0.5)
    engine = AudioEngine()
    assert engine.start_mix(first.live_mixer())
    t = NS(now=1.0)

    def step(n: int = 30) -> None:
        """`n` frames in the app's order: the channels, the blocks the sound card pulls,
        the analyzer, each `Deck`'s routes over the one analyzer."""
        for _ in range(n):
            t.now += DT
            io.poll(DT, t.now)
            for s in streams.made:
                for _block in range(BLOCKS_A_FRAME):
                    s.pull()
            engine.step(DT)
            for deck in (one, two):
                deck.router.modulate(engine.chain, DT, t.now)
                deck.reg.apply()

    two.table.add(Binding(f"lane:{_lane_of_the_tone()}", TARGET, "push", 0.5))
    yield NS(one=one, two=two, meta=meta, first=first, second=second, engine=engine,
             step=step, streams=streams, r=r)
    sources.mixer.close()
    undo.install(None)


def _others(reg) -> dict:
    """Every param's value on a `Deck` but the route's target and the panel's own."""
    return {p.id: repr(p.value) for p in reg if p.id != TARGET and p.group != "ui"}


def _lanes(engine) -> float:
    return float(np.max(engine.chain.lanes[: engine.chain.n]))


def test_a_video_on_air_moves_what_the_route_off_air_reads(road):
    assert road.meta.on_air is road.one and road.meta.off_air is road.two
    target = road.two.reg[TARGET]
    road.step()
    silent, silent_lanes = target.value, _lanes(road.engine)
    assert silent_lanes == 0.0

    road.first.channels["a"].play_audio = True               # the video on air, heard
    road.step()
    assert road.streams.made, "the on-air video's sound opened the mixer's stream"
    assert _lanes(road.engine) > 0.0, "the analyzer hears what the room hears"
    assert target.value != silent, "and the route off air reads the analyzer"


def test_the_analyzer_hears_the_video_on_air(road):
    road.first.channels["a"].play_audio = True
    road.step()
    spec = road.engine.analyser.float_frequency_data()
    want = round(HZ / (AUDIO_RATE / 2) * road.engine.analyser.bins)
    assert abs(int(np.argmax(spec)) - want) <= 1


def test_the_road_moves_only_what_the_route_drives(road):
    """The params of both `Deck`s, and the channels off air, stay as they were: only the one
    route's target reads the sound."""
    off, on = road.second.channels["a"], road.first.channels["a"]
    road.step()
    before = _others(road.two.reg), _others(road.one.reg)
    channel_before = off.play_audio, off.gain, off.bin[off.index()], off.index()
    on_target = road.one.reg[TARGET].value

    on.play_audio = True
    road.step()
    assert _lanes(road.engine) > 0.0                         # the sound is getting through

    moved_off = {k: v for k, v in _others(road.two.reg).items() if before[0].get(k) != v}
    moved_on = {k: v for k, v in _others(road.one.reg).items() if before[1].get(k) != v}
    assert moved_off == {}
    assert moved_on == {"media.a.audio": "True"}, "the toggle the test pressed, and no more"
    assert (off.play_audio, off.gain, off.bin[off.index()], off.index()) == channel_before
    assert off.heard is None, "the on-air sound asks nothing of a soundtrack off air"
    assert off.source.audio.reads == [], "and reads nothing of one"
    assert road.one.reg[TARGET].value == on_target, "a route off air moves nothing on air"
    assert not road.one.table.routes_to(TARGET), "and adds no row on air"


def test_a_video_off_air_never_reaches_the_analyzer(road):
    """The road runs from the `Deck` on air only: its sound on, off air's is silence."""
    road.second.channels["a"].play_audio = True
    road.step()
    assert not road.streams.made or _lanes(road.engine) == 0.0
    assert road.second.channels["a"].heard is None
    assert road.second.channels["a"].source.audio.reads == []
    assert not road.engine.analyser._buf.any()


def test_the_road_follows_the_air_when_it_moves(road):
    road.first.channels["a"].play_audio = True
    road.second.channels["a"].play_audio = True
    road.step(5)
    assert road.first.channels["a"].heard is not None and road.second.channels["a"].heard is None
    road.r.mix.xfade = 1.0                                   # the real fader, past the middle
    assert road.meta.follow_fader() and road.meta.on_air is road.two
    road.step(5)
    assert road.second.channels["a"].heard is not None and road.first.channels["a"].heard is None


@pytest.mark.parametrize("off_the_mix", ["mic", "nothing"])
def test_off_the_mix_the_road_is_shut(road, off_the_mix):
    """The line under the toggle is true only while listening to the mix."""
    if off_the_mix == "mic":
        road.engine.start_mic(0)
    else:
        road.engine.stop()
    target = road.two.reg[TARGET]
    road.step()
    still = target.value
    road.first.channels["a"].play_audio = True
    road.step()
    assert road.streams.made, "the video on air is sounding"
    assert road.first.live_mixer().tap is None and target.value == still


# ---------------------------------------------------------------- the words on the toggle


def test_the_hover_says_it_before_the_press_and_only_what_the_road_holds():
    chain = Analyzer(Analyser())
    tip = build_meta(Control(chain), NS(chain=chain), media=object())["audio.mix"].tip
    for words in ("While this is on", "the analyzer hears what the room hears",
                  "off-air look's audio routes", "It moves only what those routes drive",
                  "an on-air channel's sound"):
        assert words in tip, words
    assert "nothing else" not in tip.lower(), "row 702 keeps other limits: no absolute here"


@contextmanager
def _audio_pane(tmp_path, monkeypatch, width=ui_graph.SIDE_W):
    """The audio section alone in the real pane at `width`, with `audio.mix` declared (the
    rig has no media), noting each frame where the line is drawn: (r, d, st, lines)."""
    with build_rig(tmp_path) as r:
        r.reg.toggle("audio.mix", "Video sound", lambda: False, lambda on: None, group="audio",
                     persist=False)
        for pid in ("audio.stop", "audio.play", "audio.restart"):   # a real engine's, which the
            if pid not in r.reg:                                    # rig's stand-in doesn't have
                r.reg.trigger(pid, pid, lambda: None, group="audio")
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, monkeypatch)
        d.run(d.wait(2))
        st = _st(r)
        st["side_w"] = width
        _only(r, "audio")
        drawn = imgui.text_colored
        lines: list[tuple] = []

        def noted(color, text, *a):
            drawn(color, text, *a)
            if text == ui.VIDEO_SOUND_REACHES:
                lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
                lines.append((lo.x, lo.y, hi.x, hi.y, color.x))

        monkeypatch.setattr(imgui, "text_colored", noted)
        yield r, d, st, lines


@pytest.mark.parametrize("on, mode, says", [(False, "", False), (True, "mic", False),
                                            (True, "file", False), (True, "mix", True)])
def test_the_line_is_there_only_while_it_is_true(tmp_path, monkeypatch, on, mode, says):
    """Off the mix, off air reacts to no video: `test_off_the_mix_the_road_is_shut`."""
    with _audio_pane(tmp_path, monkeypatch) as (r, d, _pane, lines):
        audio = r.panel.audio
        audio.on, audio.mode = on, mode
        audio.playing, audio.position, audio.duration = False, lambda: 0.0, lambda: 1.0
        d.run(d.wait(3))
        assert bool(lines) is says
        d.rect("audio.mix")                                  # the toggle stands in every state


@pytest.mark.parametrize("width", [ui_graph.SIDE_MIN, ui_graph.SIDE_W])
def test_the_line_stands_under_the_toggle_and_fits_the_pane(tmp_path, monkeypatch, width):
    """Measured in the real pane: a line under the button and above Load track, whole, on
    two rows at 240 and one at 320, in the legible colour; every control inside the pane."""
    assert (ui_graph.SIDE_MIN, ui_graph.SIDE_W) == (240.0, 320.0)
    with _audio_pane(tmp_path, monkeypatch, width) as (r, d, st, lines):
        r.panel.audio.on, r.panel.audio.mode = True, "mix"
        d.run(d.wait(3))
        assert lines, "the line is drawn"
        x0, y0, x1, y1, shade = lines[-1]
        (px, _py), (pw, _ph) = st["details_rect"]
        assert x0 >= px and x1 <= px + pw, (x0, x1, px, pw)
        assert d.rect("audio.mix")[3] <= y0, "under the toggle"
        assert y1 <= d.rect("Load track")[1], "above the next row"
        rows = 2 if width == ui_graph.SIDE_MIN else 1
        assert y1 - y0 <= rows * imgui.get_text_line_height_with_spacing(), (width, y1 - y0)
        assert shade == ui.DIM.x
        assert _spills(d, st) == []


@pytest.mark.parametrize("width", [ui_graph.SIDE_MIN, ui_graph.SIDE_W])
def test_the_silent_line_says_on_air_and_stays_inside_the_pane(tmp_path, monkeypatch, width):
    with _audio_pane(tmp_path, monkeypatch, width) as (r, d, st, _lines):
        audio = r.panel.audio
        audio.on, audio.mode, audio._mixer = True, "mix", NS(playing=0, failed=False)
        drawn, seen = imgui.text_disabled, []

        def noted(text, *a):
            drawn(text, *a)
            if text.startswith("silent until"):
                seen.append((text, imgui.get_item_rect_max().x))

        monkeypatch.setattr(imgui, "text_disabled", noted)
        d.run(d.wait(3))
        text, right = seen[-1]
        assert "an on-air channel's sound" in text
        (px, _py), (pw, _ph) = st["details_rect"]
        assert right <= px + pw, (right, px, pw)


def test_one_widget_on_one_section_is_the_door_to_this_choice(tmp_path, monkeypatch):
    """Every section and the canvas, one frame each, counting each widget drawn on the id:
    a second door would have to say it too (register row 790)."""
    with build_rig(tmp_path) as r:
        r.reg.toggle("audio.mix", "Video sound", lambda: False, lambda on: None, group="audio",
                     persist=False)
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, None)
        d.run(d.wait(2))
        st = _st(r)
        st["side_w"] = ui_graph.SIDE_W
        count = {"n": 0}

        def counted(fn):
            def widget(*a, **k):
                if a and isinstance(a[0], str) and a[0].endswith("##audio.mix"):
                    count["n"] += 1
                return fn(*a, **k)
            return widget

        for name in WIDGETS:
            monkeypatch.setattr(imgui, name, counted(getattr(imgui, name)))
        seen = {}
        for key in ui_pane.KEYS:
            _only(r, key)
            d.run(d.wait(2))
            assert st["pane_drawn"] == [key]
            count["n"] = 0
            d.step()
            seen[key] = count["n"]
        assert {k: n for k, n in seen.items() if n} == {"audio": 1}
