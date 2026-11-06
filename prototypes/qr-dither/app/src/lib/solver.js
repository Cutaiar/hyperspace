// Live QArt solver: result = base XOR sum over pivots of (base_p != want_p) * u_p
export class QArtSolver {
  constructor(meta, buf) {
    this.meta = meta;
    this.n = meta.modules;
    const sec = (name) => {
      const s = meta.sections[name];
      return buf.slice(s.offset, s.offset + s.bytes);
    };
    this.base = new Uint8Array(sec('base'));
    this.blocks = meta.blocks.map((b, i) => {
      const curB = sec(`cur${i}`);
      const usB = sec(`us${i}`);
      return {
        L: b.L, words: b.words, nPiv: b.pivots,
        mods: new Uint16Array(sec(`mods${i}`)),
        curBytes: new Uint8Array(curB),
        cur: new Uint32Array(curB),
        pivJ: new Uint16Array(sec(`pivj${i}`)),
        pivF: new Uint8Array(sec(`pivf${i}`)),
        us: new Uint32Array(usB),
        acc: new Uint32Array(b.words),
        res: new Uint32Array(b.words),
      };
    });
    this.out = new Uint8Array(this.n * this.n);
  }

  static bit(bytes, j) { return (bytes[(j >> 5) * 4 + ((j >> 3) & 3)] >> (7 - (j & 7))) & 1; }

  // want: Uint8Array(n*n), 1 = ink
  solve(want) {
    const n = this.n, out = this.out;
    for (let i = 0; i < n * n; i++) out[i] = QArtSolver.bit(this.base, i);

    for (const b of this.blocks) {
      const { L, words, nPiv, mods, curBytes, cur, pivJ, pivF, us, acc, res } = b;
      acc.fill(0);
      for (let k = 0; k < nPiv; k++) {
        const j = pivJ[k], f = pivF[k];
        let d;
        if (f !== 255) d = f;
        else {
          const m = mods[j];
          if (m === 0xFFFF) continue;
          const v = want[m & 0x7FFF];
          d = (m & 0x8000) ? (v ^ 1) : v;
        }
        // u_k is zero at every other pivot, so the live bit here is cur's
        if (QArtSolver.bit(curBytes, j) !== d) {
          const o = k * words;
          for (let w = 0; w < words; w++) acc[w] ^= us[o + w];
        }
      }
      for (let w = 0; w < words; w++) res[w] = cur[w] ^ acc[w];
      const resB = new Uint8Array(res.buffer);
      for (let j = 0; j < L; j++) {
        const m = mods[j];
        if (m === 0xFFFF) continue;
        const v = QArtSolver.bit(resB, j);
        out[m & 0x7FFF] = (m & 0x8000) ? (v ^ 1) : v;
      }
    }
    return out;
  }
}

// --- tesseract, matching tesseract.py ---
export const VERTS = [];
for (let i = 0; i < 16; i++)
  VERTS.push([(i & 1) ? 1 : -1, (i & 2) ? 1 : -1, (i & 4) ? 1 : -1, (i & 8) ? 1 : -1]);
export const EDGES = [];
for (let i = 0; i < 16; i++)
  for (let j = i + 1; j < 16; j++) {
    let d = 0;
    for (let k = 0; k < 4; k++) if (VERTS[i][k] !== VERTS[j][k]) d++;
    if (d === 1) EDGES.push([i, j]);
  }

function rot(p, i, j, t) {
  const c = Math.cos(t), s = Math.sin(t);
  const a = p[i] * c - p[j] * s, b = p[i] * s + p[j] * c;
  p = p.slice(); p[i] = a; p[j] = b; return p;
}

export function project(angles, wDist = 7.0, zDist = 3.0) {
  return VERTS.map(v => {
    let p = v.slice();
    for (const [[i, j], t] of angles) p = rot(p, i, j, t);
    let k = wDist / (wDist - p[3]);
    p = [p[0] * k, p[1] * k, p[2] * k];
    k = zDist / (zDist - p[2]);
    return [p[0] * k, p[1] * k];
  });
}

// The circumradius of {-1,1}^4.  A rotation can put all of a vertex's length
// on one axis, so after rotating, |p[3]| reaches this and so does |p[2]| once
// the w-projection has scaled it.  Both cameras must stay outside that reach
// or the projection has a pole.
export const RADIUS = 2;

/** Nearest the z camera may sit, given where the w camera is.
 *  k_w peaks at wDist / (wDist - RADIUS), so |p[2]| reaches RADIUS times that. */
export function minZDist(wDist) {
  return wDist <= RADIUS ? Infinity : (RADIUS * wDist) / (wDist - RADIUS);
}

// The widest the shape ever gets, for a given projection setting.  Without
// this the scale is recomputed per frame and the shape visibly snaps to refill
// the frame as it folds; sampling the worst case once keeps it still.
//
// Samples that land on or behind a camera plane are skipped rather than
// averaged in.  They are not large, they are infinite: one vertex grazing the
// camera returns a span in the thousands, and every ordinary pose then scales
// to well under a module, erasing the drawing.  The UI keeps the sliders out
// of that range; this is the backstop for anything that calls in regardless.
const SPAN_CACHE = new Map();
export function maxSpan(wDist = 7.0, zDist = 3.0, samples = 3000) {
  const key = wDist + ':' + zDist;
  if (SPAN_CACHE.has(key)) return SPAN_CACHE.get(key);
  const PL = [[0,1],[0,2],[1,2],[0,3],[1,3],[2,3]];
  const LIMIT = 24;                       // a span no sane camera exceeds
  let best = 0;
  for (let s = 0; s < samples; s++) {
    const a = PL.map(p => [p, Math.random() * Math.PI * 2]);
    for (const [x, y] of project(a, wDist, zDist)) {
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      const m = Math.max(Math.abs(x), Math.abs(y));
      if (m <= LIMIT) best = Math.max(best, m);
    }
  }
  if (!best) best = 1;                    // every sample was degenerate
  SPAN_CACHE.set(key, best);
  return best;
}

export function rasterise(ctx, n, angles, stroke, margin = 0.08, opts = {}) {
  const pts = project(angles, opts.wDist, opts.zDist);
  const span = opts.span ?? maxSpan(opts.wDist ?? 7.0, opts.zDist ?? 3.0);
  const scale = (n * (1 - 2 * margin)) / (2 * (span || 1));
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, n, n);
  ctx.strokeStyle = '#000'; ctx.lineWidth = stroke;
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  for (const [a, b] of EDGES) {
    ctx.moveTo(pts[a][0] * scale + n / 2, pts[a][1] * scale + n / 2);
    ctx.lineTo(pts[b][0] * scale + n / 2, pts[b][1] * scale + n / 2);
  }
  ctx.stroke();
  const d = ctx.getImageData(0, 0, n, n).data;
  const want = new Uint8Array(n * n);
  for (let i = 0; i < n * n; i++) want[i] = d[i * 4] < 150 ? 1 : 0;
  return want;
}
