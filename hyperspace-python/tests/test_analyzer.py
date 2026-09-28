"""Plan-07 WP4a: the N-band analyzer.

The parity guard first — the "Legacy 6" layout must be the old chain bit
for bit — then the N-band behaviours: the band model, weighting curves,
add/remove/move, coupling order, spectrum history, layout round-trips and
the registry rebuild that follows a layout change.
"""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from legacy_chain import LegacyChain  # tests/legacy_chain.py — the frozen reference

from hyperspace import analyzer as A
from hyperspace.analysis import FFT_SIZE, Analyser
from hyperspace.analyzer import CURVES, RECT, Analyzer, centre_q, edges, legacy_layout
from hyperspace.bands import BANDS, CEIL, Params, default_band_params, default_params
from hyperspace.control import SCENES, Control
from hyperspace.library import FACTORY, Library, factory_doc
from hyperspace.offline import load_wav
from hyperspace.params import build_registry
from hyperspace.render import ViewState

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
SR = 48_000.0


@pytest.fixture(scope="module")
def fixture_wavs():
    if not (FIXTURES / "gate-prover.wav").exists():
        subprocess.run(
            [sys.executable, str(ROOT / "tools" / "gen_test_audio.py"), "--out", str(FIXTURES)],
            check=True,
        )
    return FIXTURES


def frames(samples: np.ndarray, sr: float, fps: float):
    hop = round(sr / fps)
    for start in range(0, len(samples) - hop, hop):
        yield samples[start : start + hop], hop / sr


def tone(freq: float, seconds: float = 0.2, sr: float = SR) -> np.ndarray:
    t = np.arange(int(sr * seconds)) / sr
    return 0.5 * np.sin(2 * np.pi * freq * t)


def rig():
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    reg = build_registry(ViewState(), control, audio)
    return reg, control, audio


# ------------------------------------------------------------ parity guard

@pytest.mark.parametrize("clip,fps,dyn", [
    ("gate-prover", 60, 1.0), ("brickwalled", 60, 1.0), ("sweep", 60, 1.0),
    ("brickwalled", 120, 0.0),
])
def test_legacy_layout_is_bit_exact(fixture_wavs, clip, fps, dyn):
    """The non-negotiable: Legacy 6 reproduces the pre-refactor chain frame
    for frame — inp and out array_equal, no tolerance (the plane drive the
    old chain also computed is the routing table's now: test_routing.py)."""
    samples, sr = load_wav(fixture_wavs / f"{clip}.wav")
    old_an, new_an = Analyser(sr), Analyser(sr)
    old = LegacyChain(old_an)
    new = Analyzer(new_an, default_params(), layout=legacy_layout())
    old.dyn = new.dyn = dyn
    for chunk, dt in frames(samples, sr, fps):
        old_an.feed(chunk)
        new_an.feed(chunk)
        old.step(dt)
        lanes = new.step(dt)
        assert lanes is new.lanes and lanes is new.out
        assert np.array_equal(old.inp, new.inp)
        assert np.array_equal(old.out, new.out)


def test_legacy_layout_bins_match_the_reference_rounding():
    for sr in (44_100.0, 48_000.0, 96_000.0):
        an = Analyser(sr)
        a = Analyzer(an)
        for i, b in enumerate(BANDS):
            assert (a._wlo[i], a._whi[i]) == an.band_bins(b.lo, b.hi)
            assert np.all(a._w[i] == 1.0)
    a = Analyzer(Analyser())
    assert a.n == 6 and a.band_names == [b.id for b in BANDS]
    assert a.layout_version > 0


# -------------------------------------------------------------- band model

def test_edges_and_centre_q_are_inverses():
    for b in BANDS:
        f, q = centre_q(b.lo, b.hi)
        lo, hi = edges(f, q)
        assert lo == pytest.approx(b.lo, rel=1e-12) and hi == pytest.approx(b.hi, rel=1e-12)
        assert f == pytest.approx(np.sqrt(lo * hi))          # log midpoint
        assert hi - lo == pytest.approx(f / q)              # Q = f / bandwidth
    a = Analyzer(Analyser())
    assert a.edges(0) == pytest.approx((20, 60), rel=1e-12)
    assert a.spec[0].edges() == a.edges(0)


def test_curve_shapes():
    """Peak 1 at the centre; edges are the half-power points (zero for TRI);
    RECT is flat inside and nothing outside."""
    a = Analyzer(Analyser())
    f, q = 1000.0, 1.0
    lo, hi = edges(f, q)
    for k, cv in enumerate(CURVES):
        a.set_band(0, f=f, q=q, curve=cv.tag)
        w = a.band_curve(0, [lo, f, hi, f * 8, f / 8])
        assert w[1] == pytest.approx(1.0)
        if cv.tag == "RECT":
            assert list(w[:3]) == [1, 1, 1] and list(w[3:]) == [0, 0]
        elif cv.tag == "TRI":
            assert w[0] == pytest.approx(0) and w[2] == pytest.approx(0)
        else:
            assert w[0] == pytest.approx(0.5) and w[2] == pytest.approx(0.5)
            assert w[3] < 0.01 and w[4] < 0.01
        # the FFT-bin weights: mean 1 over the support, symmetric in log f,
        # never negative
        assert a.spec[0].curve == k
        assert np.mean(a._w[0]) == pytest.approx(1.0)
        assert np.all(a._w[0] >= 0)
        full = a.weights(0)
        assert len(full) == FFT_SIZE // 2 and full.sum() == pytest.approx(len(a._w[0]))


def test_curves_read_the_spectrum_differently():
    """A tone at a band's edge counts fully under RECT, half under GAUSS /
    BUTTER and not at all under TRI — the weighted RMS reflects the curve."""
    levels = {}
    for cv in CURVES:
        an = Analyser()
        a = Analyzer(an, layout={"bands": [{"f": 1000, "q": 1, "curve": cv.tag}]})
        lo, _hi = a.edges(0)
        an.feed(tone(lo, seconds=0.1))
        a.step(1 / 60)
        levels[cv.tag] = a.env[0]
    assert levels["RECT"] > levels["GAUSS"] > levels["TRI"]
    assert levels["RECT"] > levels["BUTTER"] > levels["TRI"]


def test_narrow_band_falls_back_to_its_nearest_bin():
    a = Analyzer(Analyser(), layout={"bands": [{"f": 25, "q": 20, "curve": "TRI"}]})
    assert a._wlo[0] == a._whi[0] == round(25 / (SR / 2 / (FFT_SIZE // 2)))
    assert list(a._w[0]) == [1.0]


def test_set_band_keeps_trackers_and_recouples():
    a = Analyzer(Analyser())
    a.env[:] = 0.7
    v = a.layout_version
    a.set_band(2, f=9000.0)                     # MIDB jumps above AIR
    assert np.all(a.env == 0.7) and a.layout_version == v
    assert a.band_names[2] == "MIDB"            # explicit names stay
    a.set_band(2, name=None)
    assert a.band_names[2] == "9.0 kHz"         # anonymous bands read their centre
    # coupling follows frequency order: … UPR → AIR (7.5k) → MIDB (9k) → itself
    assert a._next[4] == 5 and a._next[5] == 2 and a._next[2] == 2
    assert a._next[1] == 3 and a._next[3] == 4      # BASS → MID → UPR, MIDB skipped


# --------------------------------------------------------- add/remove/move

def test_add_remove_move():
    a = Analyzer(Analyser())
    a.env[:] = np.arange(6) / 10
    v = a.layout_version
    i = a.add_band()                            # widest gap: between UPR and AIR
    assert a.n == 7 and i == 5 and a.layout_version == v + 1
    assert 2190 < a.spec[5].f < 7484 and a.spec[5].curve == RECT
    assert a.params[5] == Params(0, 0, 1, 1, 0.050, 0.300, 0.075, 0.80, 0.22)
    assert a.env[5] == 0.0 and a.env[6] == 0.5   # AIR's tracker moved with it
    assert a.band_names[6] == "AIR" and a.st[6] == {}
    assert a._next[4] == 5 and a._next[5] == 6

    a.remove_band(5)
    assert a.n == 6 and list(a.env) == list(np.arange(6) / 10)
    assert a.band_names == [b.id for b in BANDS]

    a.move_band(0, 5)                           # SUB to the end of the strip
    assert a.band_names[-1] == "SUB" and a.env[-1] == 0.0 and a.env[0] == 0.1
    assert a._next[5] == 0                      # SUB still couples to BASS (now index 0)
    assert a._next[4] == 4                      # AIR (now index 4) couples to itself

    for _ in range(6, A.N_MAX):
        a.add_band()
    assert a.n == A.N_MAX
    with pytest.raises(ValueError):
        a.add_band()
    while a.n > 1:
        a.remove_band(0)
    with pytest.raises(ValueError):
        a.remove_band(0)


def test_strip_order_does_not_change_the_math(fixture_wavs):
    """Legacy 6 reversed in the strip gives the legacy lanes reversed —
    coupling reads by frequency order, not by index."""
    samples, sr = load_wav(fixture_wavs / "brickwalled.wav")
    lay = legacy_layout()
    rev = {"bands": list(reversed(lay["bands"]))}
    an1, an2 = Analyser(sr), Analyser(sr)
    fwd = Analyzer(an1, default_params(), layout=lay)
    bwd = Analyzer(an2, list(reversed(default_params())), layout=rev)
    for k, (chunk, dt) in enumerate(frames(samples, sr, 60)):
        if k > 240:
            break
        an1.feed(chunk)
        an2.feed(chunk)
        fwd.step(dt)
        bwd.step(dt)
        assert np.array_equal(fwd.out, bwd.out[::-1])
        assert np.array_equal(fwd.inp, bwd.inp[::-1])


def test_sixteen_bands_stay_in_range(fixture_wavs):
    samples, sr = load_wav(fixture_wavs / "sweep.wav")
    an = Analyser(sr)
    a = Analyzer(an, layout={"bands": [
        {"f": 30 * 2 ** (k * 0.6), "q": 1.5, "curve": CURVES[k % 4].tag} for k in range(16)
    ]})
    assert a.n == 16 and len(a.lanes) == 16
    for chunk, dt in frames(samples, sr, 60):
        an.feed(chunk)
        lanes = a.step(dt)
        assert lanes.shape == (16,) and np.all(np.isfinite(lanes))
        assert lanes.min() >= 0 and lanes.max() < CEIL


# ---------------------------------------------------------------- history

def test_history_shape_axis_and_cadence():
    an = Analyser()
    a = Analyzer(an)
    spec, freqs = a.history()
    assert spec.shape == (A.HIST_T, A.HIST_F) and freqs.shape == (A.HIST_F,)
    assert freqs[0] == A.HIST_LO and freqs[-1] == pytest.approx(SR / 2)
    ratio = freqs[1:] / freqs[:-1]
    assert np.allclose(ratio, ratio[0])         # log-spaced
    assert np.all(spec == A.HIST_FLOOR)         # nothing written yet
    an.feed(tone(1000.0))
    for _ in range(30):
        a.step(1 / 60)                          # one column per frame at 60 fps
    spec, _ = a.history()
    assert a._hw == 30
    written = spec[-30:]
    assert np.all(spec[:-30] == A.HIST_FLOOR)
    assert np.all(written.max(axis=1) > A.HIST_FLOOR)   # every column carries signal
    peak = freqs[int(np.argmax(written[-1]))]
    assert 950 < peak < 1050                    # the tone sits where it should
    assert written.max() <= 0.0                 # 1/N-normalised FFT: never above 0 dB
    a.step(0.05)                                # a long frame repeats its column
    assert a._hw == 33
    a.step(1 / 60)
    assert a._hw == 34
    assert a.history()[0].dtype == np.float32


def test_band_curve_on_the_history_axis():
    a = Analyzer(Analyser())
    _spec, freqs = a.history()
    for i in range(a.n):
        w = a.band_curve(i, freqs)
        assert w.shape == freqs.shape and w.max() == 1.0 and w.min() == 0.0
        lo, hi = a.edges(i)
        inside = (freqs >= lo) & (freqs <= hi)
        assert np.all(w[inside] == 1.0) and np.all(w[~inside] == 0.0)


# ----------------------------------------------------------------- layout

def test_layout_round_trip():
    a = Analyzer(Analyser())
    lay = a.layout()
    assert [r["name"] for r in lay["bands"]] == [b.id for b in BANDS]
    assert all(r["curve"] == "RECT" for r in lay["bands"])
    a.set_band(1, curve="gauss", name=None)     # tags are case-insensitive
    a.add_band(f=3000, q=2, curve="TRI")
    lay = a.layout()
    assert "name" not in lay["bands"][1] and lay["bands"][1]["curve"] == "GAUSS"
    b = Analyzer(Analyser(), layout=lay)
    assert b.layout() == lay and b.n == 7 and b.band_names == a.band_names
    for i in range(b.n):
        assert (b._wlo[i], b._whi[i]) == (a._wlo[i], a._whi[i])
        assert np.array_equal(b._w[i], a._w[i])
    for bad in ({"bands": []}, {"bands": [{"f": 100, "q": 1}] * 17}):
        with pytest.raises(ValueError):
            Analyzer(Analyser(), layout=bad)
    with pytest.raises(ValueError):
        Analyzer(Analyser(), default_params(), layout={"bands": [{"f": 100, "q": 1}]})


def test_apply_layout_keeps_state_by_index_and_params_unless_given():
    a = Analyzer(Analyser())
    a.env[:] = 0.4
    a.params[3].pre = 2.5
    a.apply_layout({"bands": [{"f": 100, "q": 1}, {"f": 400, "q": 1}, {"f": 1600, "q": 1},
                              {"f": 6400, "q": 1}, {"f": 12800, "q": 2}]})
    assert a.n == 5 and np.all(a.env == 0.4) and a.params[3].pre == 2.5
    assert a.band_names == ["100 Hz", "400 Hz", "1.6 kHz", "6.4 kHz", "12.8 kHz"]
    a.apply_layout({"bands": [{"f": 100, "q": 1}] * 7})
    assert a.n == 7 and a.env[6] == 0.0 and a.params[6].pre == 1
    fresh = [Params(0, 0, 1, 1, .01, .1, .1, .5, .5) for _ in range(2)]
    a.st[0]["h"] = 1.0
    a.apply_layout({"bands": [{"f": 100, "q": 1}, {"f": 200, "q": 1}]}, params=fresh)
    assert a.params == fresh and a.st == [{}, {}]


def test_scene_rows_past_the_layout_take_the_default_row():
    a = Analyzer(Analyser())
    a.add_band()
    a.apply_scene(factory_doc("band", "Bass Engine")["values"])   # six rows onto seven bands
    assert a.n == 7, "a scene re-tunes the bands loaded; only a strip load applies a layout"
    assert a.params[3].trim == -10
    assert a.params[6] == default_band_params()


def test_scene_rows_are_the_strip_keys_only():
    values = {"band.2.atk": 0.5, "band.2.f": 440.0, "band.x.atk": 1, "view.bright": 2,
              "band.0.fn": 7}
    assert A.scene_rows(values) == {2: {"atk": 0.5}, 0: {"fn": 7}}
    a = Analyzer(Analyser())
    a.st[2]["e"] = 0.9
    a.apply_scene_band(2, {"atk": 0.5, "fn": 3.0})
    assert a.params[2].atk == 0.5 and a.params[2].fn == 3 and isinstance(a.params[2].fn, int)
    assert a.params[2].dec == default_band_params().dec and a.st[2] == {}


def wired(tmp_path):
    """A rig with a library on tmp_path, wired the way app.py wires it."""
    reg, control, audio = rig()
    lib = Library(tmp_path)
    lib.on_layout("band", control.apply_layout)
    lib.on_load("band", control.scene_loaded)
    lib.extra("band", lambda: {"layout": audio.chain.layout()})
    control.library = lib
    lib.attach(reg)
    return reg, control, audio, lib


def strip_of(chain):
    return [(p.fn, p.pre, p.post, p.atk, p.dec, p.thr, p.exp, p.trn, p.trim)
            for p in chain.params]


def test_the_scene_combo_and_the_strip_read_one_file(tmp_path):
    """Audit A1: the combo's scene and the strip's preset are the same
    document, so the two can never drift — and a strip load keeps the
    band names because the layout carries them."""
    reg, control, audio, lib = wired(tmp_path)
    assert reg["scene.select"].names == list(SCENES) and set(SCENES) == set(lib.list("band"))
    control.select_scene(SCENES.index("Kick & Sizzle"))
    by_combo = strip_of(audio.chain)
    assert lib.current("band") == "Kick & Sizzle" and not lib.is_dirty("band")
    lib.load("band", "Balanced")
    assert audio.chain.band_names == [b.id for b in BANDS], "a strip load keeps the names"
    assert control.scene == 0, "the strip moved the combo"
    lib.load("band", "Kick & Sizzle")
    assert strip_of(audio.chain) == by_combo
    assert control.scene == SCENES.index("Kick & Sizzle")


def test_a_user_scene_file_shadows_the_factory_one_for_the_combo(tmp_path):
    _, control, audio, lib = wired(tmp_path)
    doc = factory_doc("band", "Percussive")
    doc["values"]["band.1.atk"] = 0.321
    (tmp_path / "band").mkdir()
    shadow = tmp_path / "band" / "percussive.json"
    shadow.write_text(json.dumps(doc))
    control.select_scene(SCENES.index("Percussive"))
    assert audio.chain.params[1].atk == 0.321 and not lib.is_factory("band", "Percussive")
    # a broken shadow falls back to the factory copy and says so
    shadow.write_text("{not json")
    lib._docs.clear()
    control.select_scene(SCENES.index("Percussive"))
    assert audio.chain.params[1].atk == factory_doc("band", "Percussive")["values"]["band.1.atk"]
    assert "percussive.json" in lib.error


# ------------------------------------------------ control + registry rebuild

def test_band_params_follow_the_layout():
    reg, control, audio = rig()
    ids = lambda: [p.id for p in reg if p.id.startswith("band.")]
    assert "band.5.f" in reg and "band.6.f" not in reg
    assert reg["band.select"].names == [b.id for b in BANDS]
    assert reg["band.0.f"].value == pytest.approx(np.sqrt(20 * 60))
    assert reg["band.0.f"].log and reg["band.0.q"].log
    assert reg["band.0.curve"].names == [c.tag for c in CURVES]
    assert not reg["band.add"].modulatable and not reg["band.remove"].modulatable

    reg["band.add"].fire()
    assert audio.chain.n == 7 and control.selb == 5   # the new band, in frequency order
    assert "band.6.f" in reg and "band.6.reset" in reg
    assert len(reg["band.select"].names) == 7
    assert reg["band.6.fn"].label.startswith("AIR ")   # AIR moved up one
    assert reg["band.sel.f"].value == audio.chain.spec[5].f

    reg["band.sel.curve"].set(2)
    reg["band.sel.q"].set_value(2.0)
    assert audio.chain.spec[5].curve == 2 and audio.chain.spec[5].q == 2.0
    reg["band.sel.f"].set_norm(0.0)                   # the bottom of the log range
    assert audio.chain.spec[5].f == pytest.approx(A.F_LO)

    reg["band.remove"].fire()
    assert audio.chain.n == 6 and "band.6.f" not in reg and control.selb == 5
    assert sorted(ids()) == sorted(pid for pid in ids())
    for _ in range(6):
        reg["band.remove"].fire()
    assert audio.chain.n == 1 and control.selb == 0   # the last band stays
    assert "band.0.atk" in reg and "band.1.atk" not in reg


def test_control_apply_layout_rebuilds_and_restore_lands_values():
    reg, control, audio = rig()
    lay = {"bands": [{"f": 80, "q": 1}, {"f": 800, "q": 1, "curve": "BUTTER"}]}
    control.apply_layout(lay)
    assert audio.chain.n == 2 and "band.2.f" not in reg
    missing = reg.restore({"band.1.atk": 0.02, "band.1.q": 3.0, "band.9.atk": 0.5})
    assert missing == ["band.9.atk"]
    assert audio.chain.params[1].atk == 0.02 and audio.chain.spec[1].q == 3.0
    assert audio.chain.layout()["bands"][1]["curve"] == "BUTTER"
    snap = reg.snapshot("band")
    assert "band.1.q" in snap and "band.sel.q" not in snap and "band.select" not in snap


def test_move_band_keeps_the_open_strip_on_its_band():
    reg, control, audio = rig()
    control.selb = 0
    control.move_band(0, 5)
    assert control.selb == 5 and audio.chain.band_names[5] == "SUB"
    assert reg["band.5.fn"].label.startswith("SUB ")


def test_reset_all_re_tunes_the_bands_loaded_and_undo_is_whole(tmp_path):
    reg, control, audio = rig()
    control.add_band()
    audio.chain.params[2].post = 3.3
    control.scene = SCENES.index("Glacial Drift")
    control.reset_all_clicked()
    assert audio.chain.n == 7 and "band.6.f" in reg, "reset never changes the layout"
    assert audio.chain.params[2].post == 0.7 and control.undo_armed
    assert audio.chain.params[6] == default_band_params()
    control.reset_all_clicked()                       # undo: seven bands, old values
    assert audio.chain.n == 7 and audio.chain.params[2].post == 3.3 and not control.undo_armed


def test_the_combo_is_clean_on_any_layout_and_undo_gives_the_strip_back(tmp_path):
    """Code review of PR #44: the combo applies no layout, so its reference
    for "clean" is the state it landed, not the file's layout ids; and a
    reset undo puts the strip's current preset back too."""
    reg, control, audio, lib = wired(tmp_path)
    control.add_band()                                # seven bands, not the file's six
    control.select_scene(SCENES.index("Bass Engine"))
    assert audio.chain.n == 7 and lib.current("band") == "Bass Engine"
    assert not lib.is_dirty("band")
    reg["band.1.atk"].set_value(0.4)
    assert lib.is_dirty("band")
    lib.load("band", "Balanced")                      # six bands, clean
    lib.save_as("band", "Mine")
    assert lib.current("band") == "Mine" and not lib.is_dirty("band")
    control.reset_all_clicked()                       # to Balanced, the combo's scene
    assert lib.current("band") == "Balanced"
    control.reset_all_clicked()                       # undo
    assert lib.current("band") == "Mine" and not lib.is_dirty("band")


def test_an_edited_scene_file_is_re_applied_by_the_road_it_came_in(tmp_path):
    """Code review of PR #44: poll() re-applies a changed file the way it
    was landed — the combo's scene is re-tuned, never loaded whole."""
    _, control, audio, lib = wired(tmp_path)
    control.add_band()
    control.add_band()
    control.select_scene(SCENES.index("Balanced"))
    assert audio.chain.n == 8
    doc = factory_doc("band", "Balanced")
    doc["values"]["band.1.atk"] = 0.777
    (tmp_path / "band").mkdir()
    (tmp_path / "band" / "balanced.json").write_text(json.dumps(doc))
    assert lib.poll(now=10.0)
    assert audio.chain.n == 8, "an editor save of the combo's scene keeps the bands"
    assert audio.chain.params[1].atk == 0.777 and lib.current("band") == "Balanced"
    lib.load("band", "Balanced")                      # the strip's road: layout included
    assert audio.chain.n == 6
    doc["values"]["band.1.atk"] = 0.555
    (tmp_path / "band" / "balanced.json").write_text(json.dumps(doc))
    control.add_band()
    assert lib.poll(now=20.0)
    assert audio.chain.n == 6 and audio.chain.params[1].atk == 0.555


def test_a_partial_scene_file_fills_the_same_way_on_both_roads(tmp_path):
    """Code review of PR #44: the combo and the strip fill a missing id
    from the same place (Library.resolved: fresh values under Balanced)."""
    _, control, audio, lib = wired(tmp_path)
    doc = factory_doc("band", "Percussive")
    del doc["values"]["band.2.exp"]
    (tmp_path / "band").mkdir()
    (tmp_path / "band" / "percussive.json").write_text(json.dumps(doc))
    control.select_scene(SCENES.index("Percussive"))
    by_combo = audio.chain.params[2].exp
    lib.load("band", "Percussive")
    assert audio.chain.params[2].exp == by_combo == 0.95   # Balanced's MIDB contrast


def test_the_combo_reads_the_librarys_own_factory_tree(tmp_path):
    """Code review of PR #44: a Library built over another factory folder
    never falls back to the wheel's files."""
    import shutil

    other = tmp_path / "factory"
    shutil.copytree(FACTORY, other)
    doc = factory_doc("band", "Strobe Cage")
    doc["values"]["band.0.atk"] = 0.123
    (other / "band" / "strobe-cage.json").write_text(json.dumps(doc))
    reg, control, audio = rig()
    lib = Library(tmp_path / "home", factory=other)
    control.library = lib
    lib.attach(reg)
    control.select_scene(SCENES.index("Strobe Cage"))
    assert audio.chain.params[0].atk == 0.123 and lib.error == ""
    (tmp_path / "home" / "band").mkdir()
    (tmp_path / "home" / "band" / "strobe-cage.json").write_text("{not json")
    lib._docs.clear()
    audio.chain.params[0].atk = 0.5
    control.select_scene(SCENES.index("Strobe Cage"))   # a broken shadow: that factory tree
    assert audio.chain.params[0].atk == 0.123 and "strobe-cage.json" in lib.error


def test_a_strip_load_is_a_scene_change_for_the_undo(tmp_path):
    _, control, audio, lib = wired(tmp_path)
    control.add_band()
    audio.chain.params[2].pre = 3.3
    control.reset_all_clicked()
    assert control.undo_armed and audio.chain.n == 7
    lib.load("band", "Balanced")                      # six bands now
    assert audio.chain.n == 6 and not control.undo_armed


def test_audio_engine_carries_the_layout_across_sources():
    from hyperspace.audio import AudioEngine

    eng = AudioEngine()
    eng.chain.add_band(f=5000)
    eng.chain.params[0].atk = 0.123
    eng.chain.gain = 2.0
    new = eng._fresh_chain()
    assert new.n == 7 and new.layout() == eng.chain.layout()
    assert new.params[0].atk == 0.123 and new.gain == 2.0 and new.warm == 0


def test_balanced_is_the_default_table_and_the_reference_edges():
    """The reference's per-band windows live once in code (`default_params`);
    the Balanced scene file is the same numbers as a preset, and its layout
    is the six reference bands (audit A5: one table, the file pinned to it)."""
    doc = factory_doc("band", "Balanced")
    rows = A.scene_rows(doc["values"])
    table = default_params()
    assert sorted(rows) == list(range(6))
    keys = ("fn", "trim", "pre", "post", "atk", "dec", "thr", "exp", "trn")
    for i, p in enumerate(table):
        for key in keys:
            assert rows[i][key] == getattr(p, key), f"band {i} {key}: {rows[i][key]} vs {getattr(p, key)}"
    lay = doc["layout"]["bands"]
    assert [r["name"] for r in lay] == [b.id for b in BANDS]
    for r, b in zip(lay, BANDS):
        f, q = centre_q(b.lo, b.hi)
        assert r["f"] == pytest.approx(f) and r["q"] == pytest.approx(q)
