// The trigger module as a page you drive: squeeze it, change how hard the finger pushes, send any
// of the eight effects, open the shell, cut it away, explode it, orbit it. Left alone it plays the
// film's script as an auto tour with the operator's cursor; a click, drag, wheel or key hands
// control to the visitor, 25 s of quiet hands it back.
import {warmComposer} from 'teardown-kit/warm.js';
import {createConsole, DISPLAY, VIEWS} from './console.js';
import {camAt, demandAt, displayAt, DURATION, effectAt, GRIP, makeConsoleFrame, makeCursor, SCRIPT, stateAt, viewAt, VIEW_FN} from './film.js';
import {createTriggerStage} from './stage.js';
import {clamp, clamp01, RECIPE_KEYS, RECIPES, solve, zoneU} from './trigger.js';

const W = 1600, H = 900, IDLE = 25, D2R = Math.PI / 180;
const smoother = (x) => {
  const u = clamp01(x);
  return u * u * u * (u * (u * 6 - 15) + 10);
};
const ss = (a, b, t) => smoother((t - a) / (b - a));
const wrap = (d) => ((((d + 180) % 360) + 360) % 360) - 180;

const CSS = (top) => `
html,body{background:#edeae4;overflow:hidden}
#app{position:absolute!important;inset:auto!important;left:0;top:0;width:${W}px;height:${H}px;transform-origin:0 0}
#gl{touch-action:none;cursor:grab}
#gl.drag{cursor:grabbing}
.bt{pointer-events:auto;cursor:pointer}
.bt:hover{filter:brightness(.96)}
.hit{position:absolute;pointer-events:auto;cursor:ew-resize}
.tourchip{position:absolute;left:800px;top:104px;transform:translateX(-50%);display:flex;align-items:center;gap:7px;height:22px;padding:0 11px;border:1px solid #e6e0d5;border-radius:4px;background:rgba(253,252,249,.95);color:#23201c;font:700 9px 'JetBrains Mono',monospace;letter-spacing:1.3px;white-space:nowrap;cursor:pointer;pointer-events:auto}
.tourchip i{display:block;width:6px;height:6px;border-radius:50%;background:#e3562a}
.tourchip.on i{animation:blink 1.2s steps(2) infinite}
@keyframes blink{50%{opacity:.15}}
.hint{position:absolute;left:800px;top:650px;transform:translateX(-50%);font:600 9.5px 'JetBrains Mono',monospace;letter-spacing:1.6px;color:#8d8578;text-transform:uppercase;white-space:nowrap}
.turn{position:fixed;left:0;right:0;bottom:18px;text-align:center;font:600 12px/1.4 'JetBrains Mono',monospace;letter-spacing:1px;color:#9b8f80;text-transform:uppercase;display:none}
@media (orientation:portrait) and (max-width:820px){.turn{display:block}}
`;

export function runLive() {
  const top = Number(document.body.dataset.top || 0);
  const style = document.createElement('style');
  style.textContent = CSS(top);
  document.head.appendChild(style);
  const app = document.getElementById('app');
  const canvas = document.createElement('canvas');
  canvas.id = 'gl';
  app.appendChild(canvas);
  const st = createTriggerStage({canvas});
  const ui = createConsole(app);
  const tourCursor = makeCursor(ui);
  const frameConsole = makeConsoleFrame(ui, st);

  const TIERS = [
    {samples: 8, ao: true, shadow: 4096, pr: 2},
    {samples: 4, ao: false, shadow: 2048, pr: 1.5},
    {samples: 2, ao: false, shadow: 1024, pr: 1},
  ];
  const light = matchMedia('(pointer: coarse)').matches || Math.min(innerWidth, innerHeight) < 700;
  let tier = light ? 2 : 0;
  let scale = 1;
  const fit = () => {
    const h = innerHeight - top;
    scale = Math.min(innerWidth / W, h / H);
    app.style.transform = `translate(${(innerWidth - W * scale) / 2}px, ${top + (h - H * scale) / 2}px) scale(${scale})`;
    st.resize(W, H, clamp((devicePixelRatio || 1) * scale, 0.75, TIERS[tier].pr));
  };
  const applyTier = () => {
    const {pr, ...q} = TIERS[tier];
    st.setQuality(q);
    fit();
  };
  applyTier();
  addEventListener('resize', fit);
  const toStage = (cx, cy) => {
    const r = app.getBoundingClientRect();
    return [(cx - r.left) / scale, (cy - r.top) / scale];
  };
  const tourChip = document.createElement('div');
  tourChip.className = 'tourchip';
  ui.root.appendChild(tourChip);
  const hint = document.createElement('div');
  hint.className = 'hint';
  hint.textContent = 'hold SPACE to squeeze · drag to orbit · 1-8 picks an effect';
  ui.root.appendChild(hint);
  const note = document.createElement('div');
  note.className = 'turn';
  note.textContent = 'Turn your phone sideways for the full console';
  document.body.appendChild(note);

  // ------------------------------------------------------------ state
  let T = 0;
  let recipe = 'free';
  let view = 'hero';
  let viewAt0 = 0;
  let demand = 0;
  let held = false;        // the space bar is down
  let spring = false;      // ...and the blade springs back when it comes up; the slider holds instead
  let grip = GRIP;
  const live = {vel: 0, firing: false, fireT: -9, armed: true, prev: 0};
  const wr = {last: '', stamps: []};
  const disp = Object.fromEntries(DISPLAY.map((k) => [k, {on: 0, t: -9}]));
  const off = {az: 0, el: 0, k: 1};
  const cam = {...VIEW_FN.hero(0)};
  let ring = {t: -9, x: 0, y: 0};
  const eased = (k, dur = 0.7) => {
    const d = disp[k];
    const x = ss(d.t, d.t + dur, T);
    return d.on ? x : 1 - x;
  };
  const pulse = (k) => (ring = {t: T, x: ui.spots[k][0], y: ui.spots[k][1]});

  // ------------------------------------------------------------ the tour
  const AP = {on: true, t0: 0, loop: 0};
  let lastInput = 0;
  const startTour = () => {
    AP.on = true;
    AP.t0 = T;
    AP.loop = 0;
    Object.assign(off, {az: 0, el: 0, k: 1});
    grip = GRIP;
  };
  const takeOver = () => {
    lastInput = T;
    if (!AP.on) return;
    AP.on = false;
    const cyc = (T - AP.t0) % DURATION;
    const [t0, v] = viewAt(cyc);
    view = v;
    viewAt0 = T - (cyc - t0);
    recipe = effectAt(cyc);
    demand = demandAt(cyc);
  };
  tourChip.addEventListener('pointerdown', (e) => {
    e.stopPropagation();
    lastInput = T;
    if (AP.on) takeOver();
    else startTour();
  });
  addEventListener('pointerdown', (e) => {
    if (e.target !== tourChip) takeOver();
  });
  const syncDisplay = (cyc) => {
    const want = displayAt(cyc);
    for (const k of DISPLAY) {
      if (disp[k].on !== want[k]) {
        disp[k].on = want[k];
        disp[k].t = T;
      }
    }
  };

  // ------------------------------------------------------------ controls
  for (const k of RECIPE_KEYS)
    ui.btn[k].addEventListener('click', () => {
      takeOver();
      pulse(k);
      recipe = k;
      live.fireT = -9;
      live.armed = true;
    });
  for (const v of VIEWS)
    ui.btn[v].addEventListener('click', () => {
      takeOver();
      pulse(v);
      view = v;
      viewAt0 = T;
      Object.assign(off, {az: 0, el: 0, k: 1});
    });
  for (const k of DISPLAY)
    ui.btn[k].addEventListener('click', () => {
      takeOver();
      pulse(k);
      disp[k].on = disp[k].on ? 0 : 1;
      disp[k].t = T;
    });
  const slider = (geo, apply) => {
    const d = document.createElement('div');
    d.className = 'hit';
    Object.assign(d.style, {left: `${geo.x - 9}px`, top: `${geo.y - 11}px`, width: `${geo.w + 18}px`, height: '22px'});
    const move = (e) => {
      const [x] = toStage(e.clientX, e.clientY);
      apply(clamp((x - geo.x) / geo.w, 0, 1));
      lastInput = T;
    };
    d.addEventListener('pointerdown', (e) => {
      takeOver();
      d.setPointerCapture(e.pointerId);
      const up = () => {
        removeEventListener('pointermove', move);
        removeEventListener('pointerup', up);
      };
      addEventListener('pointermove', move);
      addEventListener('pointerup', up);
      move(e);
    });
    ui.root.appendChild(d);
  };
  slider(ui.SQ, (k) => {
    demand = k;
    held = false;
    spring = false;        // a dragged slider is a finger that stays put
  });
  slider(ui.GR, (k) => (grip = Math.round(1 + k * 7)));
  addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.repeat) return;
    const key = e.key.toLowerCase();
    const n = Number(key);
    if (n >= 1 && n <= RECIPE_KEYS.length) ui.btn[RECIPE_KEYS[n - 1]].click();
    else if (key === ' ') {
      takeOver();
      held = true;
      spring = true;
    } else if (key === 'x') ui.btn.xray.click();
    else if (key === 'c') ui.btn.section.click();
    else if (key === 'e') ui.btn.exploded.click();
    else if (key === 'l') ui.btn.labels.click();
    else if (key === 'o') ui.btn.orbit.click();
    else if (key === 'v') ui.btn[VIEWS[(VIEWS.indexOf(view) + 1) % VIEWS.length]].click();
    else return;
    e.preventDefault();
  });
  addEventListener('keyup', (e) => {
    if (e.key === ' ') held = false;
  });
  let drag = null;
  canvas.addEventListener('pointerdown', (e) => {
    drag = {x: e.clientX, y: e.clientY};
    canvas.setPointerCapture(e.pointerId);
    canvas.classList.add('drag');
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!drag) return;
    off.az += ((e.clientX - drag.x) / scale) * 0.3;
    off.el = clamp(off.el + ((e.clientY - drag.y) / scale) * 0.2, -25, 60);
    drag = {x: e.clientX, y: e.clientY};
    lastInput = T;
  });
  const endDrag = () => {
    drag = null;
    canvas.classList.remove('drag');
  };
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    takeOver();
    off.k = clamp(off.k * Math.exp(e.deltaY * 0.0012), 0.45, 2.2);
  }, {passive: false});

  // ------------------------------------------------------------ the frame
  startTour();
  let last = performance.now();
  const perf = {n: 0, sum: 0, slow: 0, age: 0};
  const frame = (now) => {
    const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
    last = now;
    T += dt;
    if (tier < TIERS.length - 1) {
      perf.age += dt;
      if (perf.age > 0.6) {
        perf.sum += dt;
        perf.n++;
        if (perf.sum >= 0.5 && perf.n >= 6) {
          perf.slow = perf.sum / perf.n > 0.022 ? perf.slow + 1 : 0;
          perf.sum = 0;
          perf.n = 0;
          if (perf.slow >= (perf.age < 6 ? 1 : 2)) {
            tier++;
            applyTier();
            Object.assign(perf, {age: 0, slow: 0});
          }
        }
      }
    }
    let tgt, cursor, since, lstate;
    if (AP.on) {
      const c = T - AP.t0;
      const loop = Math.floor(c / DURATION);
      const cyc = c - loop * DURATION;
      if (loop > AP.loop) AP.loop = loop;
      recipe = effectAt(cyc);
      demand = demandAt(cyc);
      grip = GRIP;
      lstate = stateAt(cyc);
      syncDisplay(cyc);
      tgt = camAt(cyc, displayAt(cyc).orbit);
      const [t0, v] = viewAt(cyc);
      view = v;
      since = cyc - t0;
      cursor = tourCursor(cyc);
      if (AP.loop > 0 && cyc < 0.8) {
        const end = tourCursor(DURATION - 0.01);
        const k = ss(0, 0.8, cyc);
        cursor = {...cursor, x: end.x + (cursor.x - end.x) * k, y: end.y + (cursor.y - end.y) * k};
      }
    } else {
      if (T - lastInput > IDLE) startTour();
      if (held) demand = clamp01(demand + dt * 0.85);
      else if (spring && demand > 0) demand = clamp01(demand - dt * 1.9);
      // the loop's own state, integrated live: the finger's speed, and whether a shot has gone off
      live.vel += ((demand - live.prev) / Math.max(1e-4, dt) - live.vel) * clamp01(dt * 18);
      live.prev = demand;
      const R = RECIPES[recipe];
      if (R.breakAt != null) {
        const bp = zoneU(R.breakAt);
        if (demand >= bp && live.armed) {
          live.armed = false;
          live.fireT = T;
        }
        if (demand < bp - 0.06) live.armed = true;
      }
      live.firing = T - live.fireT < 0.12;
      lstate = {vel: live.vel, firing: live.firing};
      since = T - viewAt0;
      tgt = VIEW_FN[view](since);
      tgt.az += off.az + (disp.orbit.on ? 13 * (T - disp.orbit.t) : 0);
      tgt.el = clamp(tgt.el + off.el, -22, 86);
      tgt.d *= off.k;
      const rk = Math.max(0, 1 - (T - ring.t) / 0.55);
      cursor = {x: -99, y: -99, press: false, ring: rk, ringX: ring.x, ringY: ring.y};
    }
    const m = solve({demand, recipe, t: T, grip, st: lstate});
    // writes a second, counted for real: the host only sends when the bytes change
    const key = Array.from(m.bytes).join(',');
    if (key !== wr.last) {
      wr.last = key;
      wr.stamps.push(T);
    }
    while (wr.stamps.length && wr.stamps[0] < T - 1) wr.stamps.shift();

    const k = 1 - Math.exp(-dt / (AP.on ? 0.18 : 0.42));
    cam.az += wrap(tgt.az - cam.az) * k;
    for (const key2 of ['tx', 'ty', 'tz', 'el', 'd', 'sx', 'sy']) cam[key2] += (tgt[key2] - cam[key2]) * k;
    st.frame(
      {...m, xray: eased('xray'), section: !!disp.section.on, explode: eased('exploded', 0.85)},
      {...cam, az: cam.az * D2R, el: cam.el * D2R},
    );
    const display = Object.fromEntries(DISPLAY.map((x) => [x, disp[x].on]));
    frameConsole(T, {
      mech: m, recipe, view, display, grip,
      writes: Math.min(60, wr.stamps.length),
      labels: eased('labels', 0.5) * ss(1.0, 1.6, since),
      cursor,
    });
    hint.style.opacity = AP.on ? '0' : '1';
    if (tourChip.classList.contains('on') !== AP.on || !tourChip.firstChild) {
      tourChip.classList.toggle('on', AP.on);
      tourChip.innerHTML = AP.on ? '<i></i>AUTO TOUR · CLICK TO TAKE OVER' : '▶ RESUME TOUR';
    }
    if (!window.SIM_SHOWN) {
      window.SIM_SHOWN = true;
      dispatchEvent(new Event('simframe'));
    }
    requestAnimationFrame(frame);
  };
  warmComposer(st.renderer, st.composer, st.scene, st.camera).then(() => requestAnimationFrame(frame));
  // a handle for the console and for capture: set the page's state without clicking
  const set = (o = {}) => {
    takeOver();
    if (o.recipe) { recipe = o.recipe; live.fireT = -9; live.armed = true; }
    if (o.view) { view = o.view; viewAt0 = T - 4; Object.assign(off, {az: 0, el: 0, k: 1}); }
    if (o.demand !== undefined) { demand = clamp01(o.demand); held = false; spring = false; }
    if (o.grip !== undefined) grip = clamp(Math.round(o.grip), 1, 8);
    for (const k of DISPLAY) if (o[k] !== undefined && !!disp[k].on !== !!o[k]) { disp[k].on = o[k] ? 1 : 0; disp[k].t = T - 2; }
  };
  window.LIVE = {st, cam, startTour, takeOver, set, get tier() { return tier; }, get T() { return T; },
    get state() { return {recipe, view, demand, grip, display: Object.fromEntries(DISPLAY.map((k) => [k, disp[k].on]))}; }};
  void SCRIPT;
}
