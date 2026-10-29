"""motion.py — the analyzer's followers, shared — and the feel a route row
or the pad runs them with (routing.Binding.motion, Router.feel_of, the pad's
`desk.pad.*` session params)."""

import math
from types import SimpleNamespace as NS

import pytest

import hyperspace.gamepad as gp
from hyperspace import motion
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.motion import OFF, Follower, Motion, follow, pole, spring
from hyperspace.params import build_registry
from hyperspace.render import ViewState
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.ui_routing import next_feel

DT = 1 / 60


def _spring(hz: float, damp: float) -> Motion:
    """A spring by the kernel's numbers, in the perceptual knobs it stores."""
    dur, bounce = motion.spring_feel(hz, damp)
    return Motion("spring", dur=dur, bounce=bounce)


class ScriptedPad(gp.Pad):
    def __init__(self):
        super().__init__()
        self.source = "usb"

    def frame(self, axes=None) -> None:
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        self.buttons, self.hat = [0] * gp.N_BUTTONS, 0
        self.axes = list(axes) if axes is not None else [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]


@pytest.fixture()
def rig(tmp_path):
    chain = Analyzer(Analyser())
    lib = Library(tmp_path)
    reg = build_registry(ViewState(), Control(chain), NS(chain=chain), lib.project)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    return NS(reg=reg, table=table, router=Router(reg, table))


# ---- the kernels ----

def test_pole_is_the_analyzers_line_to_the_bit():
    x, tgt, dt, tau = 0.3, 0.9, DT, 0.05
    assert pole(x, tgt, dt, tau) == x + (tgt - x) * (1 - math.exp(-dt / tau))
    assert pole(x, tgt, dt, 0.0) == tgt


def test_follow_at_rest_zero_is_attack_up_decay_down():
    assert follow(0.2, 0.8, DT, 0.01, 1.0) == pole(0.2, 0.8, DT, 0.01)
    assert follow(0.8, 0.2, DT, 0.01, 1.0) == pole(0.8, 0.2, DT, 1.0)


def test_follow_about_a_centred_rest_is_fast_out_slow_home_both_ways():
    # a stick at 0.5: pushed down (away) is attack, let go (toward rest) is release
    assert follow(0.5, 0.0, DT, 0.01, 1.0, rest=0.5) == pole(0.5, 0.0, DT, 0.01)
    assert follow(0.0, 0.5, DT, 0.01, 1.0, rest=0.5) == pole(0.0, 0.5, DT, 1.0)
    assert follow(1.0, 0.5, DT, 0.01, 1.0, rest=0.5) == pole(1.0, 0.5, DT, 1.0)


def _run(hz, damp, dt, t_end=3.0):
    x, v, xs = 0.0, 0.0, []
    for _ in range(round(t_end / dt)):
        x, v = spring(x, v, 1.0, dt, hz, damp)
        xs.append(x)
    return xs


@pytest.mark.parametrize("damp", [0.2, 1.0, 2.5])
def test_spring_is_exact_so_the_frame_rate_does_not_matter(damp):
    fine, coarse = _run(2.0, damp, 1 / 240), _run(2.0, damp, 1 / 30)
    assert coarse[-1] == pytest.approx(fine[-1], abs=1e-9)
    assert coarse[14] == pytest.approx(fine[14 * 8 + 7], abs=1e-9)   # t = 0.5 s
    x, v = spring(0.0, 0.0, 1.0, 10.0, 2.0, damp)                    # one huge step
    assert x == pytest.approx(1.0, abs=1e-6) and abs(v) < 1e-4


def test_spring_rings_below_critical_and_never_overshoots_at_or_above():
    assert max(_run(2.0, 0.2, DT)) > 1.3
    assert max(_run(2.0, 1.0, DT)) <= 1.0 + 1e-12
    assert max(_run(2.0, 2.5, DT)) <= 1.0 + 1e-12
    # critical arrives sooner than over-damped
    assert _run(2.0, 1.0, DT, 0.3)[-1] > _run(2.0, 2.5, DT, 0.3)[-1]


def test_spring_near_critical_is_continuous():
    a = spring(0.0, 0.0, 1.0, 0.1, 2.0, 1.0)
    for d in (1 - 1e-5, 1 + 1e-5):
        b = spring(0.0, 0.0, 1.0, 0.1, 2.0, d)
        assert b[0] == pytest.approx(a[0], abs=1e-4)


def test_a_follower_lands_once_settled():
    f, m = Follower(1.0), Motion("follow", atk=0.0, rel=0.05)
    for _ in range(200):
        f.step(0.5, DT, m, rest=0.5)
    assert f.x == 0.5 and f.v == 0.0                  # exactly: nothing keeps writing


def test_the_spring_shaper_is_motion_spring():
    from hyperspace.bands import SHAPERS
    sh = next(s for s in SHAPERS if s.tag == "SPRG")
    st, ys = {}, []
    for _ in range(30):
        ys.append(sh.f(st, 1.0, DT))
    assert max(ys) > 1.0 and min(ys) >= 0.0          # kicks overshoot, never runs backwards


# ---- what a feel does to a jump (the panel's plot, ui_feel) ----

def test_a_response_is_the_kernel_stepped_once_over_the_whole_time():
    sp, fo = _spring(2.0, 0.5), Motion("follow", atk=0.1, rel=0.4)
    assert motion.response(sp, 0.3) == pytest.approx(spring(0.0, 0.0, 1.0, 0.3, 2.0, 0.5)[0])
    assert motion.response(fo, 0.3) == pytest.approx(1 - math.exp(-0.3 / 0.1))
    # home: back toward rest on the release
    assert motion.response(fo, 0.3, x=1.0, target=0.0) == pytest.approx(math.exp(-0.3 / 0.4))
    assert motion.response(OFF, 0.3) == 1.0 and motion.response(sp, 0.0) == 0.0
    # and it is what a Follower stepping frame by frame lands on
    f = Follower()
    for _ in range(30):
        f.step(1.0, DT, sp)
    assert f.x == pytest.approx(motion.response(sp, 30 * DT), abs=1e-9)


def test_settle_is_when_a_jump_stays_within_the_band():
    fo = Motion("follow", atk=0.1, rel=0.4)
    assert motion.settle(fo) == pytest.approx(0.1 * math.log(1 / motion.BAND))
    assert motion.settle(fo, home=True) == pytest.approx(0.4 * math.log(1 / motion.BAND))
    for m in (_spring(1.5, 0.3), _spring(1.5, 1.0),
              _spring(1.5, 2.5)):
        st = motion.settle(m)
        tail = [abs(motion.response(m, st + k * 0.01) - 1) for k in range(200)]
        assert max(tail) <= motion.BAND + 1e-9              # stays in, from then on
        assert abs(motion.response(m, st * 0.9) - 1) > motion.BAND or m.damp >= 1
    assert motion.settle(_spring(4, 1)) < motion.settle(_spring(1, 1))
    assert math.isinf(motion.settle(_spring(2.0, 0.0)))
    assert motion.settle(OFF) == 0.0


# ---- the perceptual spring: duration and bounce (Apple's model) ----

def test_duration_and_bounce_are_exactly_a_frequency_and_a_damping_ratio():
    assert motion.spring_hz(0.5, 0.0) == (2.0, 1.0)              # no bounce: critical
    assert motion.spring_hz(0.5, 0.3) == pytest.approx((2.0, 0.7))
    assert motion.spring_hz(0.5, -0.5) == pytest.approx((2.0, 2.0))   # creeps
    for dur, bounce in ((0.3, 0.15), (1.2, 0.0), (0.8, -0.4), (2.0, 0.9)):
        assert motion.spring_feel(*motion.spring_hz(dur, bounce)) == \
            pytest.approx((dur, bounce))
    m = Motion("spring", dur=0.5, bounce=0.3)
    assert (m.hz, m.damp) == pytest.approx((2.0, 0.7))
    # no frequency is no motion, both ways: duration 0
    assert motion.spring_feel(0.0, 0.7) == (0.0, pytest.approx(0.3))
    assert motion.spring_hz(0.0, 0.3)[0] == 0.0
    # every spring the old Hz knob reached (0.1–12 Hz) is a duration the panel holds
    assert motion.DUR_MIN <= 1 / 12 and 1 / 0.1 <= motion.DUR_MAX
    assert Motion().hz == pytest.approx(1.5) and Motion().damp == pytest.approx(0.6)


def test_the_named_springs_and_custom():
    assert motion.spring_name(*motion.SPRINGS["smooth"]) == "smooth"
    assert motion.spring_name(0.5, 0.31) is None
    assert set(motion.SPRINGS) >= {"smooth", "snappy", "bouncy"}
    for dur, bounce in motion.SPRINGS.values():
        assert motion.DUR_MIN <= dur <= motion.DUR_MAX
        assert motion.BOUNCE_MIN <= bounce <= motion.BOUNCE_MAX
    assert Motion("spring", dur=0.5, bounce=0.3).describe() == "spring bouncy"
    assert Motion("spring", dur=0.4, bounce=0.2).describe() == "spring 400 ms, bounce 20 %"


def test_a_spring_written_as_hz_and_damping_reads_as_the_same_spring():
    old = Motion.from_json({"mode": "spring", "hz": 2.0, "damp": 0.7})
    assert (old.dur, old.bounce) == pytest.approx((0.5, 0.3))
    assert (old.hz, old.damp) == pytest.approx((2.0, 0.7))
    assert old.to_json() == {"mode": "spring", "dur": pytest.approx(0.5),
                             "bounce": pytest.approx(0.3)}
    # the new knobs win over stale ones beside them
    both = Motion.from_json({"mode": "spring", "dur": 1.0, "bounce": 0.0, "hz": 9})
    assert (both.dur, both.bounce) == (1.0, 0.0)


def test_an_old_shows_stick_spring_ids_read_as_todays():
    """A show saved before 2026-10-29 holds `desk.pad.hz` / `.damp`; its
    session reads them as today's duration and bounce, each on its own."""
    from hyperspace import routing
    old = {"desk.pad.hz": 2.0, "desk.pad.damp": 0.7, "desk.pad.feel": 2, "view.bright": 0.4}
    new = routing.renamed_session(old)
    assert new == {"desk.pad.duration": pytest.approx(0.5), "desk.pad.bounce": pytest.approx(0.3),
                   "desk.pad.feel": 2, "view.bright": 0.4}
    assert "desk.pad.hz" in old                                   # left as it was
    assert routing.renamed_session({"desk.pad.damp": 2.0}) == \
        {"desk.pad.bounce": pytest.approx(-0.5)}                  # creeps: below 0
    assert routing.renamed_session({"desk.pad.hz": 2.0, "desk.pad.duration": 1.0}) == \
        {"desk.pad.duration": 1.0}                                # today's wins
    assert routing.renamed_session({"desk.pad.damp": "loose"}) == {}
    same = {"view.bright": 0.4}
    assert routing.renamed_session(same) is same


# ---- the feel on file ----

def test_motion_files_only_the_knobs_its_mode_reads():
    assert Motion("follow", 0.01, 0.5).to_json() == {"mode": "follow", "atk": 0.01, "rel": 0.5}
    assert Motion("spring", dur=0.5, bounce=0.3).to_json() == \
        {"mode": "spring", "dur": 0.5, "bounce": 0.3}
    assert Motion.from_json({"mode": "wobble", "zzz": 1}) == OFF
    assert Motion.from_json(None) is None


def test_a_route_rows_motion_round_trips_and_is_absent_by_default():
    b = Binding("axis:LX", "view.inst_amp", "push", 0.5)
    assert "motion" not in b.to_json()
    b.motion = Motion("spring", dur=0.5, bounce=0.5)
    d = b.to_json()
    assert d["motion"] == {"mode": "spring", "dur": 0.5, "bounce": 0.5}
    back = Binding.from_json(d)
    assert back.motion == b.motion and back == b
    assert Binding.from_json({**d, "motion": {"mode": "off"}}).motion == OFF


def test_a_preset_keeps_a_rows_motion_and_its_dirty_dot_sees_it():
    import json

    from hyperspace import preset
    b = Binding("axis:LX", "view.inst_amp", "push", 0.5, motion=Motion("follow", 0.02, 0.4))
    text = preset.dumps({"routes": [b.to_json()]})
    back = Binding.from_json(json.loads(text)["routes"][0])
    assert back.motion == Motion("follow", 0.02, 0.4)
    before = json.dumps([b.to_json()])
    b.motion = Motion("follow", 0.02, 0.8)            # what Presets.signature compares
    assert json.dumps([b.to_json()]) != before


# ---- the router ----

def _push(rig, motion_=None, src="lfo:0"):
    rig.table.add(Binding(src, "view.inst_amp", "push", 1.0, rest=0.5, motion=motion_))
    return rig.reg["view.inst_amp"]


def _frame(rig, u, scheme="lfo", dt=DT):
    rig.router.feed(scheme, [u])
    rig.router.modulate(None, dt)
    rig.reg.apply()


def test_a_row_without_motion_is_as_before(rig):
    p = _push(rig)
    base = p.norm
    _frame(rig, 0.8)
    assert p.eff_norm == pytest.approx(min(1.0, base + 0.3))


def test_a_follow_row_glides_out_and_home_at_its_own_times(rig):
    p = _push(rig, Motion("follow", atk=0.05, rel=0.5))
    p.set_norm(0.2)
    _frame(rig, 0.9)                     # one frame of attack from rest
    out = pole(0.5, 0.9, DT, 0.05) - 0.5
    assert p.eff_norm == pytest.approx(0.2 + out)
    for _ in range(60):
        _frame(rig, 0.9)
    assert p.eff_norm == pytest.approx(0.6, abs=1e-3)   # arrived
    _frame(rig, 0.5)                     # let go: release, slow
    assert p.eff_norm > 0.55
    for _ in range(600):
        _frame(rig, 0.5)
    assert p.eff_norm == pytest.approx(0.2)              # home, landed


def test_a_spring_row_overshoots_and_settles(rig):
    p = _push(rig, _spring(2.0, 0.2))
    p.set_norm(0.2)
    seen = []
    for _ in range(240):
        _frame(rig, 0.8)
        seen.append(p.eff_norm)
    assert max(seen) > 0.5 + 0.05        # past 0.2 + 0.3
    assert seen[-1] == pytest.approx(0.5, abs=1e-3)


def test_a_row_that_stops_acting_starts_afresh_from_rest(rig):
    p = _push(rig, Motion("follow", atk=0.5, rel=0.5))
    p.set_norm(0.2)
    for _ in range(120):
        _frame(rig, 1.0)
    rig.router.feed("lfo", None)         # not live: the row lets go
    rig.router.modulate(None, DT)
    assert rig.router._movers == {}
    _frame(rig, 1.0)                     # back: glides in from the base again
    assert p.eff_norm == pytest.approx(0.2 + pole(0.5, 1.0, DT, 0.5) - 0.5)


def test_a_row_that_does_not_act_has_no_felt_value(rig):
    """`Router.felt_now`, what the panel's live plot reads: the row's
    follower after this frame's pass, None for a row that did not act —
    disabled, or its gate shut — and for one with no feel."""
    p = _push(rig, Motion("follow", atk=0.2, rel=0.2))
    b = rig.table.routes()[-1]
    _frame(rig, 0.9)
    assert rig.router.felt_now(b) == pytest.approx(pole(0.5, 0.9, DT, 0.2))
    b.enabled = False
    _frame(rig, 0.9)
    assert rig.router.felt_now(b) is None
    b.enabled, b.when = True, "lfo:1"     # gated on a lane that reads off
    rig.router.feed("lfo", [0.9, 0.0])
    rig.router.modulate(None, DT)
    assert rig.router.felt_now(b) is None
    plain = Binding("lfo:0", "view.bright", "push", 1.0)
    rig.table.add(plain)
    _frame(rig, 0.9)
    assert rig.router.felt_now(plain) is None and p is not None


def test_a_position_row_glides_in_from_the_base(rig):
    rig.table.add(Binding("lfo:0", "view.inst_amp", "position", 1.0,
                          motion=Motion("follow", atk=0.2, rel=0.2)))
    p = rig.reg["view.inst_amp"]
    p.set_norm(0.3)
    _frame(rig, 0.9)
    assert p.eff_norm == pytest.approx(pole(0.3, 0.9, DT, 0.2))


# ---- the pad's feel ----

def test_the_pad_feel_is_six_session_params_over_the_table(rig):
    reg, t = rig.reg, rig.table
    assert t.pad_feel == OFF
    reg["desk.pad.feel"].set(motion.MODES.index("spring"))
    reg["desk.pad.duration"].set(0.25)
    reg["desk.pad.bounce"].set(0.3)
    reg["desk.pad.attack"].set(0.01)
    reg["desk.pad.release"].set(9.0)     # clamped to the throw
    assert t.pad_feel == Motion("spring", atk=0.01, rel=motion.REL_MAX, dur=0.25, bounce=0.3)
    for k in ("feel", "attack", "release", "duration", "bounce"):
        p = reg[f"desk.pad.{k}"]
        assert p.group == "desk" and not p.modulatable and p.persist
    # the preset: derived from duration and bounce, so it does not persist
    spring = reg["desk.pad.spring"]
    assert spring.text() == "custom" and not spring.persist
    spring.set(list(motion.SPRINGS).index("bouncy"))
    assert (t.pad_feel.dur, t.pad_feel.bounce) == motion.SPRINGS["bouncy"]
    assert spring.text() == "bouncy"
    reg["desk.pad.bounce"].set(0.31)     # moved off it
    assert spring.text() == "custom"


def test_an_axis_row_takes_the_pads_feel_unless_it_has_its_own(rig):
    r, t = rig.router, rig.table
    b = Binding("axis:LX", "view.inst_amp", "push", 1.0)
    assert r.feel_of(b) == OFF
    t.pad_feel = Motion("follow", 0.0, 0.3)
    assert r.feel_of(b) == t.pad_feel
    assert r.feel_of(Binding("lfo:0", "view.inst_amp", "push")) == OFF
    b.motion = OFF                       # still: even the pad's off for this row
    assert r.feel_of(b) == OFF


def test_a_stick_let_go_glides_home_through_its_route(rig):
    pad, r, t = ScriptedPad(), rig.router, rig.table
    t.pad_feel = Motion("follow", atk=0.0, rel=0.4)
    t.add(Binding("axis:LX", "view.inst_amp", "push", 1.0))
    p = rig.reg["view.inst_amp"]
    p.set_norm(0.2)
    pad.frame(axes=[1.0, 0, 0, 0, -1, -1])
    r.pad(pad)
    r.modulate(None, DT)
    rig.reg.apply()
    assert p.eff_norm == pytest.approx(0.7)          # attack 0: there at once
    pad.frame()                                      # let go: the spring snaps it to 0
    r.pad(pad)
    r.modulate(None, DT)
    rig.reg.apply()
    assert p.eff_norm == pytest.approx(0.2 + pole(0.5, 0.0, DT, 0.4))   # still most of the way out


def test_felt_is_none_while_the_feel_is_off_and_follows_when_on(rig):
    r, t = rig.router, rig.table
    gp.publish(r)                        # the pad's names and rests (plan 27 B2: the pad's)
    assert r.felt("axis", [1.0, 0.5, 0.5, 0.5, 0.0, 0.0], DT) is None
    t.pad_feel = Motion("follow", atk=0.0, rel=0.4)
    out = r.felt("axis", [1.0, 0.5, 0.5, 0.5, 0.0, 0.0], DT)
    assert out[0] == 1.0
    out = r.felt("axis", [0.5, 0.5, 0.5, 0.5, 0.0, 0.0], DT)
    assert out[0] == pytest.approx(pole(1.0, 0.5, DT, 0.4))
    assert r.felt("axis", None, DT) is None and "axis" not in r._felt


# ---- the panel's chip ----

def test_the_feel_chip_cycles_auto_follow_spring_still_and_keeps_knobs():
    m = next_feel(None)
    assert m.mode == "follow"
    m = next_feel(Motion("follow", atk=0.1, rel=0.9))
    assert m == Motion("spring", atk=0.1, rel=0.9)
    assert next_feel(m).mode == "off"
    assert next_feel(next_feel(m)) is None
