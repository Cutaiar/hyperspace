// The adaptive trigger film: one finger squeezing the module (trigger.js) in the studio (stage.js)
// under the console (console.js). The operator walks the effects — free, a wall, the sniper break,
// a shaped curve, detents, a buzz, recoil, and mass, the one that only exists in the loop — opening
// the shell, cutting it away and exploding it on the way. A pure function of t.
import {runSim} from 'teardown-kit/runtime.js';
import * as THREE from 'three';
import {createConsole, DISPLAY} from './console.js';
import {createTriggerStage} from './stage.js';
import {clamp, clamp01, M, P, RECIPES, solve, zoneU} from './trigger.js';

const D2R = Math.PI / 180;
const smoother = (x) => {
  const u = clamp01(x);
  return u * u * u * (u * (u * 6 - 15) + 10);
};
const ss = (a, b, t) => smoother((t - a) / (b - a));

// ------------------------------------------------------------ the script
// `press` entries are the finger: [start, length, how far, shape]
export const PRESS = [
  [1.0, 2.6, 1.0, 'slow'], [4.6, 2.2, 1.0, 'slow'],
  [8.4, 3.0, 1.0, 'creep'],                      // the sniper: ease on to the wall, then through
  [12.4, 2.4, 1.0, 'slow'], [15.4, 2.6, 1.0, 'slow'],
  [19.0, 2.0, 1.0, 'slow'],
  [22.0, 0.85, 1.0, 'stab'], [23.1, 0.85, 1.0, 'stab'], [24.2, 1.9, 1.0, 'hold'],
  [27.0, 1.5, 1.0, 'stab'], [28.8, 2.4, 1.0, 'slow'],
  [32.0, 2.6, 1.0, 'slow'],
];
export const SCRIPT = [
  {t: 0, effect: 'free', view: 'hero'},
  {t: 2.0, display: 'labels'},
  {t: 4.4, effect: 'wall'},
  {t: 5.4, display: 'xray'},
  {t: 6.2, view: 'train'},
  {t: 8.2, effect: 'sniper'},
  {t: 8.3, view: 'blade'},
  {t: 11.4, display: 'labels'},
  {t: 11.8, view: 'side'},
  {t: 12.0, effect: 'curve'},
  {t: 12.1, display: 'section'},
  {t: 15.2, effect: 'detents'},
  {t: 18.0, view: 'train'},
  {t: 18.6, effect: 'buzz'},
  {t: 21.4, effect: 'recoil'},
  {t: 21.6, view: 'hero'},
  {t: 21.7, display: 'section'},
  {t: 26.4, view: 'top'},
  {t: 26.6, effect: 'mass'},
  {t: 26.8, display: 'xray'},
  {t: 31.0, view: 'hero'},
  {t: 31.2, display: 'exploded'},
  {t: 31.4, display: 'labels'},
  {t: 34.8, display: 'orbit'},
];
export const DURATION = 38;
export const DEFAULTS = {duration: DURATION, fps: 60, theme: 'light', hud: {enabled: false}, director: {enabled: false}, watermark: ''};

export const effectAt = (t) => (SCRIPT.filter((x) => x.effect && x.t <= t).pop() || SCRIPT[0]).effect;
export const displayAt = (t) => {
  const out = Object.fromEntries(DISPLAY.map((k) => [k, 0]));
  for (const e of SCRIPT) if (e.display && e.t <= t) out[e.display] = out[e.display] ? 0 : 1;
  return out;
};
const lastFlip = (key, t) => SCRIPT.filter((e) => e.display === key && e.t <= t).pop()?.t ?? -9;
export const easedDisplay = (key, t, dur = 0.7) => {
  const on = displayAt(t)[key];
  const k = ss(lastFlip(key, t), lastFlip(key, t) + dur, t);
  return on ? k : 1 - k;
};
/** The finger at film time t: 0 at rest, 1 fully down. */
export function demandAt(t) {
  let d = 0;
  for (const [t0, dur, peak, shape] of PRESS) {
    if (t < t0 || t > t0 + dur + 0.5) continue;
    const u = (t - t0) / dur;
    let k;
    if (shape === 'stab') k = u < 0.28 ? smoother(u / 0.28) : 1 - smoother(clamp01((u - 0.34) / 0.3));
    else if (shape === 'hold') k = u < 0.18 ? smoother(u / 0.18) : u < 0.86 ? 1 : 1 - smoother((u - 0.86) / 0.14);
    else if (shape === 'creep') k = u < 0.68 ? smoother(u / 0.68) * 0.78 : 0.78 + smoother((u - 0.68) / 0.18) * 0.22;
    else k = u < 0.46 ? smoother(u / 0.46) : u < 0.72 ? 1 : 1 - smoother((u - 0.72) / 0.28);
    d = Math.max(d, peak * clamp01(k));
  }
  return d;
}
export const GRIP = 6;

// ------------------------------------------------------------ the loop's state, tabulated once
// Two recipes need what happened before this frame: mass reads the finger's speed, recoil needs to
// know whether a shot has gone off. Both are integrated here at load, so render(t) stays pure.
const DT = 1 / 240;
const N = Math.ceil((DURATION + 1) / DT) + 2;
const VEL = new Float32Array(N);
const FIRE = new Uint8Array(N);
{
  let fireT = -9, armed = 1;
  for (let i = 1; i < N; i++) {
    const t = i * DT, d0 = demandAt(t - DT), d = demandAt(t);
    VEL[i] = VEL[i - 1] + ((d - d0) / DT - VEL[i - 1]) * clamp01(DT * 18);
    const R = RECIPES[effectAt(t)];
    if (R.breakAt != null) {
      const u = d;                                   // the finger's own demand decides when it breaks through
      const bp = zoneU(R.breakAt);
      if (u >= bp && armed) { armed = 0; fireT = t; }
      if (u < bp - 0.06) armed = 1;
    } else { armed = 1; fireT = -9; }
    FIRE[i] = t - fireT < 0.12 ? 1 : 0;
  }
}
const look = (A, t) => A[clamp(Math.round(t / DT), 0, N - 1)];
export const stateAt = (t) => ({vel: look(VEL, t), firing: !!look(FIRE, t)});
export const solveAt = (t) => solve({demand: demandAt(t), recipe: effectAt(t), t, grip: GRIP, st: stateAt(t)});
/** Writes a second: the host only sends on a change, so a still shape is quiet and a buzz is not. */
export function writesAt(t) {
  const R = RECIPES[effectAt(t)];
  const d = R.make(t, stateAt(t));
  if (d.mode === 'vibration' || R.loop) return 60;
  if (R.breakAt != null && look(FIRE, t)) return 60;
  return 0;
}

// ------------------------------------------------------------ views: the target is in the module's frame
const TY = -0.016;
export const VIEW_FN = {
  hero: (u) => ({tx: -0.001, ty: TY, tz: -0.008, az: -36 - 2.2 * u, el: 15, d: 0.30, sx: 8, sy: -46}),
  side: (u) => ({tx: 0.0, ty: TY, tz: -0.010, az: -89 - 1.0 * u, el: 4, d: 0.26, sx: 8, sy: -46}),
  train: (u) => ({tx: -0.003, ty: -0.028, tz: -0.018, az: -68 - 3 * u, el: 10, d: 0.20, sx: 8, sy: -40}),
  blade: (u) => ({tx: 0.001, ty: -0.024, tz: 0.004, az: -28 - 2.5 * u, el: 2, d: 0.175, sx: 8, sy: -42}),
  top: (u) => ({tx: 0.0, ty: -0.016, tz: -0.012, az: -42 - 2 * u, el: 60, d: 0.285, sx: 8, sy: -40}),
};
const VIEWS = SCRIPT.filter((e) => e.view).map((e) => [e.t, e.view]);
const blend = (a, b, k) => {
  const o = {};
  for (const key in b) o[key] = key === 'az' ? a.az + ((((b.az - a.az + 540) % 360) - 180) * k) : a[key] + (b[key] - a[key]) * k;
  const swing = Math.min(1, Math.abs(((b.az - a.az + 540) % 360) - 180) / 90);
  o.d += Math.max(0, Math.max(a.d, b.d) * (1 + 0.14 * swing) - o.d) * Math.sin(Math.PI * k);
  return o;
};
export const camAt = (t, orbit = 0) => {
  let i = 0;
  while (i < VIEWS.length - 1 && VIEWS[i + 1][0] <= t) i++;
  const cur = VIEW_FN[VIEWS[i][1]](t - VIEWS[i][0]);
  let o = cur;
  if (i > 0) {
    const k = ss(VIEWS[i][0], VIEWS[i][0] + 1.5, t);
    if (k < 1) o = blend(VIEW_FN[VIEWS[i - 1][1]](t - VIEWS[i - 1][0]), cur, k);
  }
  if (orbit > 0) o = {...o, az: o.az + 13 * Math.max(0, t - lastFlip('orbit', t)) * orbit};
  return o;
};
export const viewAt = (t) => VIEWS.filter(([a]) => a <= t).pop();

// ------------------------------------------------------------ the operator's pointer
const REST = [[800, 430], [700, 390], [900, 470], [760, 360]];
export function makeCursor(ui) {
  const EV = SCRIPT.filter((e) => e.t > 0).flatMap((e) => {
    const out = [];
    if (e.effect) out.push({t: e.t, spot: ui.spots[e.effect]});
    if (e.view) out.push({t: e.t + (e.effect ? 0.3 : 0), spot: ui.spots[e.view]});
    if (e.display) out.push({t: e.t + (e.view || e.effect ? 0.5 : 0), spot: ui.spots[e.display]});
    return out;
  }).filter((e) => e.spot);
  const WP = [[0, 900, 600]];
  EV.forEach((e, i) => {
    WP.push([e.t - 0.16, ...e.spot], [e.t + 0.22, ...e.spot]);
    WP.push([e.t + 1.2, ...REST[i % REST.length]]);
  });
  WP.sort((a, b) => a[0] - b[0]);
  return (t) => {
    let i = 0;
    while (i < WP.length - 2 && t > WP[i + 1][0]) i++;
    const [t0, x0, y0] = WP[i];
    const [t1, x1, y1] = WP[i + 1];
    const k = ss(t0, t1, t);
    const len = Math.hypot(x1 - x0, y1 - y0);
    const bow = Math.sin(Math.PI * k) * Math.min(22, len * 0.07);
    let press = false, ring = 0, rx = 0, ry = 0;
    for (const e of EV) {
      if (t >= e.t - 0.07 && t < e.t + 0.09) press = true;
      if (t >= e.t && t < e.t + 0.55) {
        ring = 1 - (t - e.t) / 0.55;
        [rx, ry] = e.spot;
      }
    }
    return {x: x0 + (x1 - x0) * k + (len ? (-(y1 - y0) / len) * bow : 0), y: y0 + (y1 - y0) * k + (len ? ((x1 - x0) / len) * bow : 0), press, ring, ringX: rx, ringY: ry};
  };
}

// ------------------------------------------------------------ the labels, in the module's frame
const V3 = THREE.Vector3;
const PARTS = [
  {name: 'TRIGGER BLADE', sub: 'SWINGS 15° ON ITS PIVOT', at: (m) => new V3(0.008, -M.bladeLen * 0.52, 0.009).applyAxisAngle(new V3(1, 0, 0), m.theta)},
  {name: 'ARC RACK', sub: 'ON THE BLADE, ABOUT THE PIVOT', at: (m) => new V3(0, -M.rackR * 0.74, -M.rackR * 0.74).applyAxisAngle(new V3(1, 0, 0), m.theta)},
  {name: 'POSITION SENSOR', sub: 'THE BLADE TO 8 BITS, 0-255', at: () => new V3(-(M.bladeW / 2 + 0.004), 0, 0)},
  {name: 'OUTPUT GEAR', sub: '18 TEETH, DRIVEN BY THE RACK', at: () => new V3(0.006, P.gear[1] + M.gearR * 0.6, P.gear[2])},
  {name: 'WORM WHEEL', sub: '20 TEETH, MODULE 0.5', at: () => new V3(-0.0085, P.wheel[1] - M.wheelR * 0.7, P.wheel[2])},
  {name: 'WORM', sub: 'SINGLE START — SELF-LOCKING', at: () => new V3(-0.0056, P.worm[1] - M.wormR * 2.2, P.worm[2])},
  {name: 'DC MOTOR', sub: 'HOLDS, OR DRIVES IN AND OUT', at: () => new V3(-0.0056, P.motor[1] - M.motorR, P.motor[2])},
  {name: 'MODULE SHELL', sub: 'ONE SELF-CONTAINED ASSEMBLY', at: () => new V3(M.housing[0] / 2, -0.030, -0.030)},
  {name: 'THE FINGER', sub: 'THE ONLY INPUT', at: (m) => new V3(0.009, -M.bladeLen * 0.66 + 0.016, 0.0225).applyAxisAngle(new V3(1, 0, 0), m.theta * 0.92)},
];
export function makeLabels(st) {
  return (m, o) => {
    if (o < 0.02) return [];
    const pts = PARTS.map((p) => {
      const q = p.at(m);
      return {p, at: st.project(q.x, q.y, q.z)};
    }).filter((x) => x.at && x.at[0] > 318 && x.at[0] < 1302 && x.at[1] > 118 && x.at[1] < 680);
    const L = pts.filter((x) => x.at[0] < 800).sort((a, b) => a.at[1] - b.at[1]);
    const R = pts.filter((x) => x.at[0] >= 800).sort((a, b) => a.at[1] - b.at[1]);
    const out = [];
    const stack = (col, x, w) => {
      let y = 140;
      for (const c of col) {
        y = Math.max(y, Math.min(630, c.at[1] - 10));
        out.push({name: c.p.name, sub: c.p.sub, at: c.at, label: [x, y], w, o});
        y += 34;
      }
    };
    stack(L, 334, 176);
    stack(R, 1118, 176);
    return out;
  };
}

export function makeConsoleFrame(ui, st) {
  const labels = makeLabels(st);
  return (t, s) => {
    ui.update({
      mech: s.mech,
      recipe: s.recipe,
      view: s.view,
      display: s.display,
      grip: s.grip,
      writes: s.writes,
      callouts: labels(s.mech, s.labels),
      cursor: s.cursor,
    });
  };
}

export function makeFilm() {
  return async ({canvas, capture}) => {
    const st = createTriggerStage({canvas});
    const resize = () => st.resize(1600, 900, capture ? devicePixelRatio || 1 : Math.min(devicePixelRatio || 1, 2));
    resize();
    const ui = createConsole(document.getElementById('app'));
    const cursorAt = makeCursor(ui);
    const frame = makeConsoleFrame(ui, st);
    window.CS = st;
    return {
      resize,
      render(t) {
        const m = solveAt(t);
        const disp = displayAt(t);
        const cam = camAt(t, disp.orbit);
        st.frame(
          {...m, xray: easedDisplay('xray', t), section: !!disp.section, explode: easedDisplay('exploded', t, 0.85)},
          {...cam, az: cam.az * D2R, el: cam.el * D2R},
        );
        const [vt0, view] = viewAt(t);
        frame(t, {
          mech: m, recipe: effectAt(t), view, display: disp, grip: GRIP, writes: writesAt(t),
          labels: easedDisplay('labels', t, 0.5) * ss(vt0 + 1.0, vt0 + 1.6, t),
          cursor: cursorAt(t),
        });
        return {};
      },
    };
  };
}

export const run = () => runSim(DEFAULTS, makeFilm());
