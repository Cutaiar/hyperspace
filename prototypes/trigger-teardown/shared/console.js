// The console around the module, laid out at 1600 x 900: the mechanism's state with a live side
// schematic, the loop panel (256 steps in, ten zones out), the effect and display switches, the
// mode table with the refused ones struck through, and the wide panel that holds the ten zones and
// the eleven bytes side by side — because the ladder is what the bytes mean.
// update(s) redraws every live part from the frame's state.
import {MODE_NAME, REFUSED, RECIPE_KEYS, RECIPES, T_FEEDBACK, T_OFF, T_VIBRATION, T_WEAPON, ZONES} from './trigger.js';

export const C = {ink: '#23201c', mute: '#8d8578', faint: '#d7d0c4', line: '#e6e0d5', panel: 'rgba(253,252,249,.95)',
  or: '#e3562a', vi: '#8b5cf6', bl: '#3c79a8', gr: '#2fa36b', dim: '#b9b1a3'};
export const VIEWS = ['hero', 'side', 'train', 'blade', 'top'];
export const VIEW_LABEL = {hero: 'HERO', side: 'SECTION', train: 'GEAR TRAIN', blade: 'THE BLADE', top: 'TOP'};
export const DISPLAY = ['labels', 'xray', 'section', 'exploded', 'orbit'];
export const DISPLAY_LABEL = {labels: 'LABELS', xray: 'X-RAY SHELL', section: 'CUT AWAY', exploded: 'EXPLODED', orbit: 'ORBIT'};

const CSS = `
#app{font-family:Inter,system-ui,sans-serif;color:${C.ink};-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.ui{position:absolute;inset:0;pointer-events:none}
.mo{font-family:'JetBrains Mono',ui-monospace,monospace}
.cp{position:absolute;background:${C.panel};border:1px solid ${C.line};border-radius:6px;box-shadow:0 2px 10px rgba(90,75,50,.07)}
.ph{position:absolute;display:flex;align-items:center;gap:9px;font:700 10.5px 'JetBrains Mono',monospace;letter-spacing:1.8px}
.ph i{display:block;width:3px;height:13px;background:${C.or}}
.pn{position:absolute;font:500 9.5px 'JetBrains Mono',monospace;color:${C.mute};letter-spacing:1px}
.sm{font:500 9px 'JetBrains Mono',monospace;letter-spacing:1.6px;color:${C.mute};text-transform:uppercase;white-space:nowrap}
.bt{position:absolute;height:21px;padding:0 10px;display:flex;align-items:center;justify-content:center;border:1px solid ${C.faint};border-radius:4px;background:#fffefb;font:700 9.4px 'JetBrains Mono',monospace;letter-spacing:1.3px;color:${C.ink};white-space:nowrap}
.call{position:absolute;white-space:nowrap}
.call b{display:flex;align-items:center;gap:6px;font:700 9.4px 'JetBrains Mono',monospace;letter-spacing:1.3px;color:${C.ink}}
.call b i{display:block;width:6px;height:6px;background:${C.or}}
.call span{display:block;font:500 7.8px 'JetBrains Mono',monospace;letter-spacing:1.2px;color:${C.mute};margin-top:2px}
.cur{position:absolute;left:0;top:0;z-index:50;filter:drop-shadow(0 1px 2px rgba(0,0,0,.3))}
.ring{position:absolute;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;border:1.5px solid ${C.or};opacity:0;z-index:49}
`;
const el = (h) => {
  const d = document.createElement('div');
  d.innerHTML = h.trim();
  return d.firstElementChild;
};
const hex2 = (n) => n.toString(16).padStart(2, '0');

export function createConsole(app) {
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);
  const ui = el(`<div class="ui"></div>`);
  app.appendChild(ui);
  const add = (h) => {
    const n = el(h);
    ui.appendChild(n);
    return n;
  };
  const panel = (x, y, w, h, title, n) => {
    add(`<div class="cp" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px"></div>`);
    add(`<div class="ph" style="left:${x + 14}px;top:${y + 13}px"><i></i>${title}</div>`);
    add(`<div class="pn" style="right:${1600 - x - w + 14}px;top:${y + 15}px">${n}</div>`);
  };
  const btn = {};

  // ------------------------------------------------------------ header
  add(`<div style="position:absolute;left:0;top:0;width:160px;height:89px;background:${C.or}"></div>`);
  add(`<svg style="position:absolute;left:30px;top:26px" width="100" height="38" viewBox="0 0 100 38"><g fill="none" stroke="#fff" stroke-width="3.2" stroke-linejoin="round"><path d="M14 34V10a6 6 0 0 1 12 0v10"/><path d="M26 20h22"/></g><rect x="48" y="12" width="30" height="16" rx="4" fill="#fff"/><g fill="${C.or}"><rect x="52" y="16" width="3" height="8"/><rect x="58" y="16" width="3" height="8"/><rect x="64" y="16" width="3" height="8"/><rect x="70" y="16" width="3" height="8"/></g></svg>`);
  add(`<div class="sm" style="position:absolute;left:182px;top:22px;letter-spacing:2.4px">SONY DUALSENSE · WIRELESS CONTROLLER</div>`);
  add(`<div style="position:absolute;left:181px;top:37px;font-size:33px;font-weight:700;letter-spacing:-.6px;line-height:1">Adaptive trigger <span style="color:${C.or};font-weight:400">/</span> R2</div>`);
  add(`<div class="mo" style="position:absolute;left:182px;top:77px;font-size:11.2px;letter-spacing:2.2px;color:#6d6357">GEARED STOP · TEN ZONES · ELEVEN BYTES</div>`);
  add(`<div class="sm" style="position:absolute;left:1040px;top:49px;letter-spacing:2.6px;font-size:9.6px">SELF-LOCKING WORM DRIVE</div>`);
  add(`<div class="mo" style="position:absolute;left:1352px;top:47px;color:${C.or};font-size:12px;letter-spacing:-1px">//////</div>`);
  add(`<div style="position:absolute;left:1414px;top:33px;color:${C.or};font-size:30px;font-weight:700;letter-spacing:-.5px;line-height:1">0x21</div>`);
  add(`<div style="position:absolute;left:1500px;top:33px;width:1px;height:44px;background:${C.faint}"></div>`);
  add(`<div class="sm" style="position:absolute;left:1516px;top:34px;line-height:14px;letter-spacing:2.2px">SQUEEZE<br>SENSE<br>PUSH BACK</div>`);
  {
    let h = '';
    for (let r = 0; r < 3; r++) for (let c = 0; c < 10; c++) h += `<path d="M${c * 25.5 + 4} ${r * 25.5}v8M${c * 25.5} ${r * 25.5 + 4}h8" stroke="${C.or}" stroke-width="1.1" opacity=".7"/>`;
    add(`<svg style="position:absolute;left:800px;top:80px" width="255" height="64">${h}</svg>`);
  }

  // ------------------------------------------------------------ 01 mechanism state
  panel(28, 126, 282, 262, 'MECHANISM STATE', '01');
  const chip = add(`<div style="position:absolute;left:42px;top:166px;width:13px;height:24px;border-radius:2px"></div>`);
  const stTitle = add(`<div style="position:absolute;left:66px;top:164px;font-size:15px;font-weight:600"></div>`);
  const stSub = add(`<div class="sm" style="position:absolute;left:67px;top:183px"></div>`);
  add(`<div style="position:absolute;left:42px;top:202px;width:254px;height:1px;background:${C.line}"></div>`);
  const sch = add(`<svg style="position:absolute;left:42px;top:212px" width="254" height="112"></svg>`);
  const rows01 = [['TRAVEL', 'travel'], ['BLADE', 'blade'], ['ZONE', 'zone'], ['FORCE', 'force']].map(([n], i) => {
    const y = 330 + (i % 2) * 24;
    const x = 42 + Math.floor(i / 2) * 130;
    add(`<div class="sm" style="position:absolute;left:${x}px;top:${y}px">${n}</div>`);
    return add(`<div class="mo" style="position:absolute;left:${x + 62}px;top:${y - 3}px;font-size:12px;font-weight:700"></div>`);
  });

  // ------------------------------------------------------------ 02 the loop
  panel(28, 402, 282, 236, 'THE LOOP', '02');
  add(`<div class="mo" style="position:absolute;left:42px;top:438px;width:254px;font-size:9.4px;line-height:1.7;color:#5f564b">The module reads the blade to <b>8 bits</b> and reports it. The host answers with ten zones of eight levels, at most a hundred times a second. The write is coarser than the read — so the fine detail lives in the loop, not the packet.</div>`);
  const loopSvg = add(`<svg style="position:absolute;left:42px;top:512px" width="254" height="74"></svg>`);
  const lr = [['POT · IN', 'pot'], ['WRITES', 'wr']].map(([n], i) => {
    const y = 596 + i * 22;
    add(`<div class="sm" style="position:absolute;left:42px;top:${y}px">${n}</div>`);
    return add(`<div class="mo" style="position:absolute;left:150px;top:${y - 3}px;font-size:11.5px;font-weight:700"></div>`);
  });

  // ------------------------------------------------------------ 03 effect, 04 views, 05 display, 06 modes
  const btnRow = (keys, labels, x0, y, wmax = 230) => {
    let x = x0, yy = y;
    for (const k of keys) {
      const w = Math.round(labels[k].length * 7.1 + 22);
      if (x + w > x0 + wmax) { x = x0; yy += 31; }
      btn[k] = add(`<div class="bt" style="left:${x}px;top:${yy}px;width:${w}px;height:23px">${labels[k]}</div>`);
      x += w + 6;
    }
  };
  panel(1313, 126, 258, 170, 'EFFECT', '03');
  btnRow(RECIPE_KEYS, Object.fromEntries(RECIPE_KEYS.map((k) => [k, RECIPES[k].name])), 1327, 163);
  const effNote = add(`<div class="mo" style="position:absolute;left:1327px;top:256px;width:232px;font-size:8.6px;line-height:1.55;color:#5f564b"></div>`);
  panel(1313, 312, 258, 140, 'VIEWS', '04');
  btnRow(VIEWS, VIEW_LABEL, 1327, 349);
  panel(1313, 468, 258, 140, 'DISPLAY', '05');
  btnRow(DISPLAY, DISPLAY_LABEL, 1327, 505);
  panel(1313, 624, 258, 186, 'TRIGGER MODES', '06');
  const modeRows = [[T_OFF, 'Off', '0x05'], [T_FEEDBACK, 'Feedback', '0x21'], [T_WEAPON, 'Weapon', '0x25'], [T_VIBRATION, 'Vibration', '0x26']].map(([code, name, hx], i) => {
    const y = 660 + i * 20;
    const dot = add(`<div style="position:absolute;left:1328px;top:${y + 4}px;width:7px;height:7px;border-radius:50%;background:${C.faint}"></div>`);
    const lab = add(`<div class="mo" style="position:absolute;left:1344px;top:${y}px;font-size:10px;letter-spacing:1px;color:${C.mute}">${hx}&nbsp;&nbsp;${name}</div>`);
    return {code, dot, lab};
  });
  add(`<div style="position:absolute;left:1327px;top:744px;width:232px;height:1px;background:${C.line}"></div>`);
  add(`<div class="sm" style="position:absolute;left:1327px;top:754px;color:${C.dim}">REFUSED BEFORE ANY WRITE</div>`);
  add(`<div class="mo" style="position:absolute;left:1327px;top:770px;width:232px;font-size:9px;line-height:1.5;color:${C.dim};text-decoration:line-through">${REFUSED.map(([h, n]) => `${h} ${n}`).join(' · ')}</div>`);

  // ------------------------------------------------------------ 07 what was sent: the zones and the bytes
  const BX = 340, BY = 688, BW = 950, BH = 190;
  panel(BX, BY, BW, BH, 'WHAT WAS SENT · THE TEN ZONES AND THE ELEVEN BYTES', '07');
  const ladder = add(`<svg style="position:absolute;left:${BX + 16}px;top:${BY + 32}px" width="430" height="108"></svg>`);
  const bytesG = add(`<div style="position:absolute;left:${BX + 470}px;top:${BY + 34}px;display:flex;gap:4px"></div>`);
  const BYTE_FIELD = [
    ['mode', C.or], ['mask', C.bl], ['mask', C.bl], ['force', C.gr], ['force', C.gr], ['force', C.gr], ['force', C.gr],
    ['—', C.dim], ['—', C.dim], ['hz', C.vi], ['—', C.dim],
  ];
  const byteEls = BYTE_FIELD.map(([f, col], i) => {
    const d = el(`<div style="width:34px"><div class="mo" data-v style="height:28px;display:flex;align-items:center;justify-content:center;border:1px solid ${C.faint};border-radius:3px;font-size:12.5px;font-weight:700;background:#fffefb"></div><div class="mo" style="text-align:center;font-size:7.4px;letter-spacing:.6px;color:${C.mute};margin-top:3px">${i}</div></div>`);
    bytesG.appendChild(d);
    return {box: d.querySelector('[data-v]'), col, field: f};
  });
  const legend = add(`<div class="mo" style="position:absolute;left:${BX + 470}px;top:${BY + 82}px;font-size:8.8px;letter-spacing:.8px;color:${C.mute}"></div>`);
  const decode = add(`<div class="mo" style="position:absolute;left:${BX + 470}px;top:${BY + 102}px;width:464px;font-size:9.6px;line-height:1.6;color:#5f564b"></div>`);
  // the squeeze slider: the one input the visitor drives
  add(`<div class="sm" style="position:absolute;left:${BX + 16}px;top:${BY + 150}px">SQUEEZE</div>`);
  const SQ = {x: BX + 84, w: 250, y: BY + 156};
  add(`<div style="position:absolute;left:${SQ.x}px;top:${SQ.y}px;width:${SQ.w}px;height:3px;background:#eae3d6;border-radius:2px"></div>`);
  const sqFill = add(`<div style="position:absolute;left:${SQ.x}px;top:${SQ.y}px;height:3px;background:${C.or};border-radius:2px"></div>`);
  const sqKnob = add(`<div style="position:absolute;top:${SQ.y - 6}px;width:15px;height:15px;margin-left:-7.5px;border-radius:50%;background:#fff;border:2px solid ${C.or};box-sizing:border-box"></div>`);
  const sqGhost = add(`<div style="position:absolute;top:${SQ.y - 3}px;width:2px;height:9px;background:${C.dim}"></div>`);
  add(`<div class="sm" style="position:absolute;left:${BX + 364}px;top:${BY + 150}px">GRIP</div>`);
  const GR = {x: BX + 412, w: 120, y: BY + 156};
  add(`<div style="position:absolute;left:${GR.x}px;top:${GR.y}px;width:${GR.w}px;height:3px;background:#eae3d6;border-radius:2px"></div>`);
  const grFill = add(`<div style="position:absolute;left:${GR.x}px;top:${GR.y}px;height:3px;background:${C.ink};border-radius:2px"></div>`);
  const grKnob = add(`<div style="position:absolute;top:${GR.y - 6}px;width:15px;height:15px;margin-left:-7.5px;border-radius:50%;background:#fff;border:2px solid ${C.ink};box-sizing:border-box"></div>`);
  const grVal = add(`<div class="mo" style="position:absolute;left:${GR.x + GR.w + 12}px;top:${GR.y - 5}px;font-size:10.5px;font-weight:700"></div>`);
  const sqNote = add(`<div class="mo" style="position:absolute;left:${BX + 600}px;top:${BY + 150}px;width:330px;font-size:9px;line-height:1.5;color:${C.mute}"></div>`);

  // ------------------------------------------------------------ footer, labels, pointer
  add(`<div class="sm" style="position:absolute;left:27px;top:882px;letter-spacing:2.2px">MECHANISM SCHEMATIC FROM TEARDOWNS &nbsp;·&nbsp; PROTOCOL EXACT, SONY-HID §6 &nbsp;·&nbsp; ONE DEGREE OF FREEDOM</div>`);
  add(`<div class="sm" style="position:absolute;right:28px;top:882px;letter-spacing:2.2px">HYPERSPACE / EDGE LAB <span style="color:${C.or}">//////</span></div>`);
  const callSvg = add(`<svg data-callouts style="position:absolute;inset:0;overflow:visible" width="1600" height="900"></svg>`);
  const callG = add(`<div data-callouts style="position:absolute;inset:0"></div>`);
  const ring = add(`<div class="ring"></div>`);
  const cur = add(`<div class="cur"><svg width="22" height="22" viewBox="0 0 34 34"><path d="M4 3 L30 13.5 L17.5 17.5 L13.5 30 Z" fill="#111" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/></svg></div>`);
  const centre = (n) => {
    const r = n.getBoundingClientRect();
    return [r.left + r.width / 2, r.top + r.height / 2];
  };
  const spots = Object.fromEntries(Object.entries(btn).map(([k, n]) => [k, centre(n)]));
  const pointer = (c) => {
    cur.style.display = c.x < 0 ? 'none' : 'block';
    cur.style.transform = `translate(${(c.x - 3).toFixed(2)}px, ${(c.y - 2).toFixed(2)}px) scale(${c.press ? 0.88 : 1})`;
    ring.style.left = `${c.ringX}px`;
    ring.style.top = `${c.ringY}px`;
    ring.style.opacity = String(c.ring * 0.85);
    ring.style.transform = `scale(${(0.35 + 0.9 * (1 - c.ring)).toFixed(3)})`;
  };

  return {
    root: ui, btn, spots, SQ, GR,
    update(s) {
      const m = s.mech;
      // ---- state chip
      const st = m.mode === 'off' ? ['FREE', 'nothing in the way', 'ok']
        : m.buzzing ? ['BUZZING', `${Math.round(m.desc.freq)} Hz under the finger`, 'hot']
        : m.blocked ? ['HELD', 'the worm is self-locking', 'hot']
        : m.force > 0 ? ['PUSHING BACK', `${m.force} of 8 in zone ${m.zone}`, 'hot']
        : ['SLACK', 'no force in this zone', 'ok'];
      chip.style.background = st[2] === 'ok' ? C.gr : C.or;
      stTitle.textContent = st[0];
      stSub.textContent = st[1];
      // ---- the side schematic: blade, rack, gear, worm, motor
      {
        const th = m.theta;
        const px = 58, py = 10;                       // the pivot in the svg
        const L = 76, R = 30;
        const bx = px + Math.sin(th) * 0 + Math.sin(th) * L * 0 + L * Math.sin(th);
        const tipx = px + L * Math.sin(th), tipy = py + L * Math.cos(th);
        const gx = px + 43, gy = py + 43;
        let h = `<line x1="${px}" y1="${py}" x2="${tipx.toFixed(1)}" y2="${tipy.toFixed(1)}" stroke="${C.ink}" stroke-width="5.5" stroke-linecap="round"/>`;
        // the arc rack
        const a0 = th - 0.34, a1 = th + 0.34;
        const ax = (a) => px + R * Math.sin(a), ay = (a) => py + R * Math.cos(a);
        h += `<path d="M${ax(a0).toFixed(1)} ${ay(a0).toFixed(1)} A${R} ${R} 0 0 0 ${ax(a1).toFixed(1)} ${ay(a1).toFixed(1)}" fill="none" stroke="${C.mute}" stroke-width="2.4"/>`;
        h += `<circle cx="${px}" cy="${py}" r="3.4" fill="${C.ink}"/>`;
        // the gear and worm wheel, turning
        const ga = -m.gearA;
        h += `<g transform="translate(${gx} ${gy}) rotate(${((ga * 180) / Math.PI).toFixed(1)})"><circle r="13" fill="none" stroke="${C.ink}" stroke-width="1.2"/>${Array.from({length: 12}, (_, i) => `<line x1="0" y1="-13" x2="0" y2="-16" stroke="${C.ink}" stroke-width="1.1" transform="rotate(${i * 30})"/>`).join('')}<line x1="-9" y1="0" x2="9" y2="0" stroke="${C.ink}" stroke-width="1"/></g>`;
        // the worm under it, its hatching sliding with the motor angle
        const wy = gy + 22;
        h += `<rect x="${gx - 17}" y="${wy - 4}" width="34" height="8" rx="4" fill="#fffefb" stroke="${C.ink}" stroke-width="1.2"/>`;
        const off = ((m.motorA * 2) % 6 + 6) % 6;
        for (let i = 0; i < 7; i++) h += `<line x1="${(gx - 16 + ((i * 6 + off) % 34)).toFixed(1)}" y1="${wy - 3.4}" x2="${(gx - 19 + ((i * 6 + off) % 34)).toFixed(1)}" y2="${wy + 3.4}" stroke="${C.mute}" stroke-width="1"/>`;
        // the motor
        h += `<rect x="${gx + 20}" y="${wy - 7}" width="26" height="14" rx="3" fill="#fffefb" stroke="${C.ink}" stroke-width="1.2"/>`;
        h += `<text x="${gx + 33}" y="${wy + 3.4}" font-size="7.4" text-anchor="middle" fill="${C.mute}" font-family="JetBrains Mono">M</text>`;
        // the torque the motor is holding: the accent
        if (m.torque > 0.02) {
          h += `<path d="M${gx - 24} ${gy} a 24 24 0 0 1 10 -19" fill="none" stroke="${C.or}" stroke-width="${(1 + m.torque * 2.6).toFixed(2)}"/>`;
          h += `<path d="M${gx - 15.5} ${gy - 22.5}l5.5 4l-6.5 2.5z" fill="${C.or}"/>`;
        }
        h += `<text x="4" y="104" font-size="7.4" letter-spacing="1" fill="${C.mute}" font-family="JetBrains Mono">BLADE</text>`;
        h += `<text x="${gx + 12}" y="${gy - 16}" font-size="7.4" letter-spacing="1" fill="${C.mute}" font-family="JetBrains Mono">WHEEL</text>`;
        h += `<text x="${gx + 54}" y="${wy + 3}" font-size="7.4" letter-spacing="1" fill="${C.mute}" font-family="JetBrains Mono">MOTOR</text>`;
        sch.innerHTML = h;
      }
      rows01[0].textContent = `${(m.u * 100).toFixed(0)} %`;
      rows01[1].textContent = `${((m.theta * 180) / Math.PI).toFixed(1)}°`;
      rows01[2].textContent = String(m.zone);
      rows01[3].textContent = m.mode === 'off' ? '—' : `${m.force} / 8`;
      // ---- the loop: 256 steps in, ten by eight out
      {
        const W = 254;
        let h = `<rect x="0" y="6" width="${W}" height="18" rx="3" fill="#f3efe6" stroke="${C.line}"/>`;
        for (let i = 0; i < 64; i++) h += `<line x1="${(2 + i * (W - 4) / 64).toFixed(1)}" y1="8" x2="${(2 + i * (W - 4) / 64).toFixed(1)}" y2="22" stroke="${C.faint}" stroke-width=".6"/>`;
        const px = 2 + (m.pot / 255) * (W - 4);
        h += `<rect x="${(px - 1.5).toFixed(1)}" y="4" width="3" height="22" fill="${C.or}"/>`;
        h += `<text x="0" y="40" font-size="7.6" letter-spacing="1" fill="${C.mute}" font-family="JetBrains Mono">READ · 256 STEPS</text>`;
        h += `<text x="${W}" y="40" font-size="7.6" letter-spacing="1" text-anchor="end" fill="${C.mute}" font-family="JetBrains Mono">WRITE · 10 × 8</text>`;
        for (let z = 0; z < ZONES; z++) {
          const x = 2 + z * ((W - 4) / ZONES), w = (W - 4) / ZONES - 2;
          const f = m.zones[z] || 0;
          h += `<rect x="${x.toFixed(1)}" y="48" width="${w.toFixed(1)}" height="18" rx="2" fill="${f ? C.or : '#f3efe6'}" opacity="${f ? (0.25 + 0.75 * f / 8).toFixed(2) : 1}" stroke="${C.line}"/>`;
        }
        loopSvg.innerHTML = h;
      }
      lr[0].textContent = `${m.pot} / 255`;
      lr[1].textContent = `${s.writes} /s`;
      // ---- effect, views, display
      const onBtn = (k, on) => {
        btn[k].style.background = on ? C.or : '#fffefb';
        btn[k].style.color = on ? '#fff' : C.ink;
        btn[k].style.borderColor = on ? C.or : C.faint;
      };
      for (const k of RECIPE_KEYS) onBtn(k, s.recipe === k);
      for (const k of VIEWS) onBtn(k, s.view === k);
      for (const k of DISPLAY) onBtn(k, !!s.display[k]);
      effNote.textContent = RECIPES[s.recipe].note;
      for (const r of modeRows) {
        const on = m.bytes[0] === r.code;
        r.dot.style.background = on ? C.or : C.faint;
        r.lab.style.color = on ? C.ink : C.mute;
        r.lab.style.fontWeight = on ? '700' : '500';
      }
      // ---- the ten zones
      {
        const W = 430, H = 108, x0 = 18, y0 = 6, w = W - x0 - 6, hh = 70, bw = w / ZONES, span = w - bw;
        let h = '';
        for (let f = 0; f <= 8; f += 4) {
          const y = y0 + hh * (1 - f / 8);
          h += `<line x1="${x0}" y1="${y}" x2="${x0 + w}" y2="${y}" stroke="${C.line}"/><text x="${x0 - 5}" y="${y + 3}" font-size="7.6" text-anchor="end" fill="${C.dim}" font-family="JetBrains Mono">${f}</text>`;
        }
        const ink = m.buzzing ? C.vi : C.or;
        for (let z = 0; z < ZONES; z++) {
          const f = m.zones[z] || 0, x = x0 + (span * z) / 9;
          const bh = hh * ((f || 0.05) / 8);
          h += `<rect x="${(x + 1).toFixed(1)}" y="${(y0 + hh - bh).toFixed(1)}" width="${(bw - 2).toFixed(1)}" height="${bh.toFixed(1)}" rx="1.5" fill="${f ? ink : C.faint}" opacity="${f ? (0.3 + 0.7 * f / 8).toFixed(2) : 0.6}"/>`;
          h += `<text x="${(x + bw / 2).toFixed(1)}" y="${y0 + hh + 13}" font-size="8" text-anchor="middle" fill="${z === m.zone ? C.ink : C.dim}" font-weight="${z === m.zone ? 700 : 400}" font-family="JetBrains Mono">${z}</text>`;
        }
        const ux = x0 + bw / 2 + span * m.u;
        const dx = x0 + bw / 2 + span * m.demand;
        if (m.demand > m.u + 0.004)
          h += `<line x1="${dx.toFixed(1)}" y1="${y0 - 2}" x2="${dx.toFixed(1)}" y2="${y0 + hh + 2}" stroke="${C.dim}" stroke-width="1.4" stroke-dasharray="3 3"/><text x="${dx.toFixed(1)}" y="${y0 + hh + 26}" font-size="7.6" text-anchor="middle" fill="${C.dim}" font-family="JetBrains Mono">ASKED</text>`;
        h += `<line x1="${ux.toFixed(1)}" y1="${y0 - 4}" x2="${ux.toFixed(1)}" y2="${y0 + hh + 4}" stroke="${C.ink}" stroke-width="2"/><circle cx="${ux.toFixed(1)}" cy="${y0 - 5}" r="3.4" fill="${C.ink}"/>`;
        h += `<text x="${x0}" y="${H - 2}" font-size="7.6" letter-spacing="1" fill="${C.mute}" font-family="JetBrains Mono">FORCE PER ZONE, 1-8</text>`;
        ladder.innerHTML = h;
      }
      // ---- the eleven bytes
      byteEls.forEach((b, i) => {
        const v = m.bytes[i];
        b.box.textContent = hex2(v);
        const live = v !== 0 || i === 0;
        b.box.style.color = live ? b.col : C.dim;
        b.box.style.borderColor = live ? b.col : C.faint;
        b.box.style.background = live ? `${b.col}14` : '#fffefb';
        b.box.style.fontWeight = i === 0 ? '700' : '600';
      });
      legend.innerHTML = `<span style="color:${C.or}">■</span> mode &nbsp; <span style="color:${C.bl}">■</span> zone mask, 10 bits &nbsp; <span style="color:${C.gr}">■</span> force, 3 bits a zone &nbsp; <span style="color:${C.vi}">■</span> Hz`;
      {
        const mask = m.bytes[1] | (m.bytes[2] << 8);
        const bits = Array.from({length: ZONES}, (_, z) => (mask & (1 << z) ? '1' : '0')).join('');
        const name = MODE_NAME[m.bytes[0]] || '—';
        decode.innerHTML = m.bytes[0] === T_OFF
          ? `<b>Off 0x05</b> — every parameter zero. The motor lets the train run; the blade is on its spring alone.`
          : m.bytes[0] === T_WEAPON
          ? `<b>Weapon 0x25</b> — mask ${bits} is just two bits: the wall at zone ${m.desc.start} and the break at zone ${m.desc.end}. Byte 3 is the strength, ${m.desc.strength} of 8, minus one.`
          : `<b>${name} 0x${hex2(m.bytes[0])}</b> — mask ${bits} (zone 0 first), forces ${m.zones.map((f) => f || '·').join('')}${m.bytes[0] === T_VIBRATION ? `, ${m.bytes[9]} Hz in byte 9` : ''}. A gap in the mask is what makes it a <i>multiple position</i> effect.`;
      }
      // ---- the two sliders
      sqFill.style.width = `${(m.demand * SQ.w).toFixed(1)}px`;
      sqKnob.style.left = `${(SQ.x + m.demand * SQ.w).toFixed(1)}px`;
      sqGhost.style.left = `${(SQ.x + m.u * SQ.w - 1).toFixed(1)}px`;
      sqGhost.style.opacity = m.demand > m.u + 0.004 ? '1' : '0';
      const gk = (s.grip - 1) / 7;
      grFill.style.width = `${(gk * GR.w).toFixed(1)}px`;
      grKnob.style.left = `${(GR.x + gk * GR.w).toFixed(1)}px`;
      grVal.textContent = `${s.grip} / 8`;
      sqNote.textContent = m.broke ? 'through the break — it gave way at once'
        : m.blocked ? 'the finger is asking for more travel than the stop will give'
        : 'the grip is how hard the finger pushes: a zone that pushes harder is a wall';
      // ---- labels
      let lh = '', ch = '';
      for (const c of s.callouts) {
        if (c.o < 0.02 || !c.at) continue;
        const [ax, ay] = c.at, [lx, ly] = c.label;
        const right = lx > ax;
        const ex = right ? lx - 6 : lx + c.w + 6;
        lh += `<polyline points="${ax.toFixed(1)},${ay.toFixed(1)} ${ex.toFixed(1)},${(ly + 6).toFixed(1)}" fill="none" stroke="${C.or}" stroke-width=".9" opacity="${c.o.toFixed(2)}"/><circle cx="${ax.toFixed(1)}" cy="${ay.toFixed(1)}" r="2.4" fill="${C.or}" opacity="${c.o.toFixed(2)}"/>`;
        ch += `<div class="call" style="left:${lx.toFixed(1)}px;top:${(ly - 1).toFixed(1)}px;opacity:${c.o.toFixed(2)}"><b><i></i>${c.name}</b><span>${c.sub}</span></div>`;
      }
      callSvg.innerHTML = lh;
      callG.innerHTML = ch;
      pointer(s.cursor);
    },
    pointer,
  };
}
