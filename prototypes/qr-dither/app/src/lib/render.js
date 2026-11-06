// Classic QR styling over a solved module matrix: dot shapes, styled eyes,
// colours and gradients.  Everything here is presentation -- it never changes
// which modules are ink, so it cannot change what the code decodes to.  It can
// still change whether a camera manages to READ it, which is the thing to test.

const FINDER = 7;

function finders(n) {
  return [[0, 0], [n - FINDER, 0], [0, n - FINDER]];
}

export function inFinder(x, y, n) {
  for (const [fx, fy] of finders(n))
    if (x >= fx && x < fx + FINDER && y >= fy && y < fy + FINDER) return true;
  return false;
}

function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.moveTo(x + rr, y);          // moveTo opens a SUBpath; no beginPath here
  ctx.arcTo(x + w, y,     x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x,     y + h, rr);
  ctx.arcTo(x,     y + h, x,     y,     rr);
  ctx.arcTo(x,     y,     x + w, y,     rr);
  ctx.closePath();
}

// A cell with the corners rounded only where it has no orthogonal neighbour on
// both adjacent sides -- this is what makes runs of modules read as one
// connected, flowing stroke instead of a row of separate beads.
function cell(ctx, x, y, s, r, nb) {
  const [up, right, down, left] = nb;
  const e = 0.001;
  ctx.beginPath();
  const tl = (!up && !left) ? r : 0, tr = (!up && !right) ? r : 0;
  const br = (!down && !right) ? r : 0, bl = (!down && !left) ? r : 0;
  ctx.moveTo(x + tl, y);
  ctx.lineTo(x + s - tr, y);
  if (tr) ctx.arcTo(x + s, y, x + s, y + tr, tr);
  ctx.lineTo(x + s, y + s - br);
  if (br) ctx.arcTo(x + s, y + s, x + s - br, y + s, br);
  ctx.lineTo(x + bl, y + s);
  if (bl) ctx.arcTo(x, y + s, x, y + s - bl, bl);
  ctx.lineTo(x, y + tl);
  if (tl) ctx.arcTo(x, y, x + tl, y, tl);
  ctx.closePath();
  ctx.fill();
}

const DOT = {
  square:            { kind: 'cell',  r: 0 },
  rounded:           { kind: 'cell',  r: 0.25 },
  'extra-rounded':   { kind: 'cell',  r: 0.5 },
  dots:              { kind: 'dot',   shrink: 0 },
  'dots-tight':      { kind: 'dot',   shrink: -0.08 },
  classy:            { kind: 'classy', r: 0.5, round: false },
  'classy-rounded':  { kind: 'classy', r: 0.5, round: true },
};

export const DOT_TYPES = Object.keys(DOT);
export const EYE_TYPES = ['square', 'rounded', 'extra-rounded', 'dot'];

export function drawStyled(ctx, mods, n, quiet, o = {}) {
  const px = o.px || 10;
  const side = (n + 2 * quiet) * px;
  const dot = DOT[o.dotType] || DOT.square;

  ctx.canvas.width = ctx.canvas.height = side;
  ctx.imageSmoothingEnabled = true;
  ctx.clearRect(0, 0, side, side);
  if (o.bg && o.bg !== 'transparent') {
    ctx.fillStyle = o.bg;
    ctx.fillRect(0, 0, side, side);
  }

  let fill = o.fg || '#000000';
  if (o.gradient) {
    const g = ctx.createLinearGradient(0, 0, side, side);
    g.addColorStop(0, o.fg || '#000000');
    g.addColorStop(1, o.fg2 || '#ff2b2b');
    fill = g;
  }
  ctx.fillStyle = fill;

  const at = (x, y) => (x < 0 || y < 0 || x >= n || y >= n) ? 0 : mods[y * n + x];
  const styleEyes = o.styleEyes !== false;

  for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
    if (!mods[y * n + x]) continue;
    if (styleEyes && inFinder(x, y, n)) continue;      // drawn as a unit below
    const X = (x + quiet) * px, Y = (y + quiet) * px;
    if (dot.kind === 'dot') {
      const rad = px / 2 * (1 - (dot.shrink || 0));
      ctx.beginPath();
      ctx.arc(X + px / 2, Y + px / 2, rad, 0, Math.PI * 2);
      ctx.fill();
    } else if (dot.kind === 'classy') {
      // two opposite corners rounded, the leaf shape
      const r = dot.r * px, nb = [at(x, y-1), at(x+1, y), at(x, y+1), at(x-1, y)];
      ctx.beginPath();
      ctx.moveTo(X + r, Y);
      ctx.lineTo(X + px, Y);
      ctx.lineTo(X + px, Y + px - (dot.round ? r : 0));
      if (dot.round) ctx.arcTo(X + px, Y + px, X + px - r, Y + px, r);
      ctx.lineTo(X, Y + px);
      ctx.lineTo(X, Y + r);
      ctx.arcTo(X, Y, X + r, Y, r);
      ctx.closePath();
      ctx.fill();
      void nb;
    } else {
      cell(ctx, X, Y, px, dot.r * px,
           [at(x, y-1), at(x+1, y), at(x, y+1), at(x-1, y)]);
    }
  }

  if (styleEyes) {
    const sq = o.eyeFrame || 'square', ct = o.eyeCore || 'square';
    for (const [fx, fy] of finders(n)) {
      const X = (fx + quiet) * px, Y = (fy + quiet) * px, S = FINDER * px;
      // outer ring: a 1-module-thick frame, drawn as outer minus inner
      const ro = sq === 'extra-rounded' ? S * 0.32 : sq === 'rounded' ? S * 0.18
               : sq === 'dot' ? S / 2 : 0;
      ctx.beginPath();
      roundRect(ctx, X, Y, S, S, ro);
      roundRect(ctx, X + px, Y + px, S - 2 * px, S - 2 * px, Math.max(0, ro - px));
      ctx.fill('evenodd');
      // core: 3x3
      const cX = X + 2 * px, cS = 3 * px;
      if (ct === 'dot') {
        ctx.beginPath();
        ctx.arc(cX + cS / 2, Y + 2 * px + cS / 2, cS / 2, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.beginPath();
        roundRect(ctx, cX, Y + 2 * px, cS, cS,
                  ct === 'extra-rounded' ? cS * 0.34 : ct === 'rounded' ? cS * 0.18 : 0);
        ctx.fill();
      }
    }
  }
  return side;
}
