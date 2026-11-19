// @label Mandelbrot
// @order 65
// @blend mix
// @speed 1
// @hook mandel
// @tip A Mandelbrot generator to explore live: z → z^p + c with every term a knob.
// @tip Slice 0 is the Mandelbrot set (c across the screen), 1 a Julia set (z₀ across
// @tip the screen), between them a tilt through both. Pan, Dive and the drives move
// @tip by the view, so a hand moves the picture as far at any depth.
// @tip It paints the whole frame: wire any picture into it; at mix 1 that picture is not seen.

// plan 63. The maths (smooth count, periodicity, the cardioid, the perturbation
// recurrence, the rebase) is held against float64 numpy in `hyperspace/mandel.py`,
// which also runs the Python half of this file (`// @hook mandel`): it integrates
// the drives, picks the tier, computes the reference orbit in float64, renders at
// the Size's lines and upscales, and runs the tile pre-passes that skip the black.

uniform float u_centre_x;  // @param -2.5 2.5 -0.5 "Centre x" Where the view looks, real part (the plane, not the screen). Pan moves it by the view.
uniform float u_centre_y;  // @param -2.5 2.5 0 "Centre y" Where the view looks, imaginary part.
uniform float u_zoom;      // @param 0.5 1e13 1 log "Zoom" How deep: 1 shows 3 units top to bottom. Past 10⁴ the perturbation tier takes over.
uniform float u_z0_x;      // @param -2 2 0 "z₀ x" The start z₀, real part — 0 for the Mandelbrot set. At Slice 1 the screen is z₀ and this is unused.
uniform float u_z0_y;      // @param -2 2 0 "z₀ y" The start z₀, imaginary part.
uniform float u_c_x;       // @param -2 2 -0.8 "c x" The Julia constant c, real part. At Slice 0 the screen is c and this is unused.
uniform float u_c_y;       // @param -2 2 0.156 "c y" The Julia constant c, imaginary part.
uniform float u_slice;     // @param 0 1 0 "Slice" 0 the Mandelbrot set (the screen is c), 1 a Julia set (the screen is z₀), between them a tilt through both.
uniform int   u_power;     // @param 2 8 2 "Power" The exponent p in z → z^p + c: 2 the classic set, higher more-fold.
uniform float u_iters;     // @param 16 16384 512 log "Steps" The iteration cap: more shows finer edges deep in, and costs more.
uniform int   u_size;      // @param choice [540|810|1080] 1 "Size" Lines it is rendered at, then upscaled to the output: the performance knob.
uniform int   u_interior;  // @param choice [black|coloured] 0 "Inside" Black skips the inside (fast); coloured shows how fast each point settles (full cost).
uniform int   u_output;    // @param choice [steps|ramp] 0 "Output" Steps: the smooth step count as brightness, for Palette's gradient; ramp: a built-in colour ramp.
uniform float u_cycle;     // @param 4 4096 64 log "Cycle" Steps per rise of the brightness: it climbs over Cycle steps, falls over the next, and repeats.
uniform int   u_tier;      // @param choice [auto|direct|perturb] 0 "Tier" Auto: float32 to 10⁴×, then perturbation. Direct and perturb force one.
uniform int   u_skip;      // @param choice [on|off] 0 "Skip black" On: 16×16 tiles whose border is all inside are filled black without iterating (Mandelbrot or Julia slices, inside black).
uniform float u_pan_x;     // @param -1 1 0 "Pan x" Moves the centre, in view heights a second: the same speed on screen at any depth. 0 holds.
uniform float u_pan_y;     // @param -1 1 0 "Pan y" Moves the centre up and down, in view heights a second.
uniform float u_dive;      // @param -1 1 0 "Dive" Zooms in (up) or out (down), up to four doublings a second. 0 holds.
uniform float u_c_drive_x; // @param -1 1 0 "c drive x" Moves c, in view heights a second: a slow drift deep in, a fast one zoomed out.
uniform float u_c_drive_y; // @param -1 1 0 "c drive y" Moves c's imaginary part, in view heights a second.
uniform float u_z0_drive_x; // @param -1 1 0 "z₀ drive x" Moves z₀, in view heights a second.
uniform float u_z0_drive_y; // @param -1 1 0 "z₀ drive y" Moves z₀'s imaginary part, in view heights a second.

// set by mandel.py each pass, never params
uniform int   u_pass;       // 0 the picture; 1 the tile borders' in-set flags (the skip's first pass)
uniform int   u_perturb;    // 1: iterate δ against the reference orbit
uniform int   u_lines;      // the render target's height, px (the pixel's size in the plane)
uniform int   u_width;      // … and its width
uniform float u_view_x;     // the centre as float32 (direct tier)
uniform float u_view_y;
uniform float u_shift_x;    // perturbation: centre − reference point, float64 made small
uniform float u_shift_y;
uniform float u_ref_cx;     // the reference's c and z₀ (direct tier reads them as the terms)
uniform float u_ref_cy;
uniform float u_ref_zx;
uniform float u_ref_zy;
uniform sampler2D u_ref;    // the reference orbit Z₀ … Z_N, RG32F, REF_W wide (unit 2)
uniform int   u_ref_n;      // its last index N
uniform sampler2D u_tiles;  // 1 where a tile's whole border is inside (unit 3)
uniform int   u_tiles_on;   // 1 while the skip runs this pass

const int REF_W = 1024;     // mandel.REF_W
const float BAIL = 1.0e4;   // |z|² past this has escaped (mandel.BAIL): z^8 of it stays in float32
const int TILE = 16;        // mandel.TILE

vec2 cmul(vec2 a, vec2 b) { return vec2(a.x * b.x - a.y * b.y, a.x * b.y + a.y * b.x); }

vec2 cpow(vec2 z, int p) {
    vec2 r = z;
    for (int k = 1; k < p; k++) r = cmul(r, z);
    return r;
}

vec2 ref_at(int m) { return texelFetch(u_ref, ivec2(m % REF_W, m / REF_W), 0).xy; }

// (Z + d)^p − Z^p by the binomial theorem, Horner in d: no large terms cancel,
// so it holds while d is many orders under Z (mandel.binomial_delta)
vec2 binomial_delta(vec2 Z, vec2 d, int p) {
    vec2 zp[9];
    zp[0] = vec2(1.0, 0.0);
    for (int j = 1; j < p; j++) zp[j] = cmul(zp[j - 1], Z);
    vec2 s = vec2(1.0, 0.0);              // C(p, p)
    float coef = 1.0;                     // C(p, k), walked down from k = p
    for (int k = p - 1; k >= 1; k--) {
        coef = coef * float(k + 1) / float(p - k);
        s = cmul(s, d) + coef * zp[p - k];
    }
    return cmul(s, d);
}

// the brightness a count lands at: up over Cycle steps, down over the next
float rise(float n) { return 1.0 - abs(1.0 - mod(n / u_cycle, 2.0)); }

// the closed-form inside tests (p = 2, z₀ = 0 only): the main cardioid and the period-2 bulb
bool in_cardioid(vec2 c) {
    float x = c.x - 0.25;
    float q = x * x + c.y * c.y;
    if (q * (q + x) <= 0.25 * c.y * c.y) return true;
    vec2 b = c + vec2(1.0, 0.0);
    return dot(b, b) <= 0.0625;
}

// one point's orbit. Returns the smooth escape count n + 1 − log_p log|z| when it
// escapes (inside = false), or the step at which periodicity caught it (inside =
// true; the cap when nothing did)
float orbit(vec2 off, out bool inside) {
    int p = u_power;
    float s = u_slice;
    float lp = log(float(p));
    int cap = int(u_iters + 0.5);         // Steps is a float knob (a log taper's detents)
    float pix = 3.0 / u_zoom / float(u_lines);
    float eps2 = pix * pix * 0.0025;      // periodicity: 5 % of a pixel, squared
    inside = false;
    vec2 cterm = vec2(u_ref_cx, u_ref_cy), zterm = vec2(u_ref_zx, u_ref_zy);
    if (u_perturb == 0) {
        vec2 q = vec2(u_view_x, u_view_y) + off;
        vec2 c = mix(q, cterm, s);
        vec2 z = mix(zterm, q, s);
        if (p == 2 && s == 0.0 && zterm == vec2(0.0) && u_interior == 0 && in_cardioid(c)) {
            inside = true;
            return float(cap);
        }
        vec2 saved = z;
        int lim = 8, since = 0;
        for (int n = 0; n < cap; n++) {
            z = cpow(z, p) + c;
            float r2 = dot(z, z);
            if (r2 > BAIL) return max(float(n) + 1.0 - log(0.5 * log(r2)) / lp, 0.0);
            vec2 d = z - saved;
            if (dot(d, d) < eps2) { inside = true; return float(n); }
            if (++since == lim) { saved = z; since = 0; lim *= 2; }
        }
        inside = true;
        return float(cap);
    }
    // perturbation: δc and δz₀ from the pixel's offset to the reference point
    vec2 dq = vec2(u_shift_x, u_shift_y) + off;
    vec2 dc = (1.0 - s) * dq;
    vec2 d = s * dq;                      // δ₀ = δz₀
    vec2 Z0 = ref_at(0);
    vec2 z = Z0 + d, saved = z;
    int m = 0, lim = 8, since = 0;
    for (int n = 0; n < cap; n++) {
        d = binomial_delta(ref_at(m), d, p) + dc;
        m++;
        z = ref_at(m) + d;
        float r2 = dot(z, z);
        if (r2 > BAIL) return max(float(n) + 1.0 - log(0.5 * log(r2)) / lp, 0.0);
        // the rebase (Zhuoran): when the full z is nearer the orbit's start than δ is
        // to the reference, or the reference has run out, carry on from the start
        vec2 back = z - Z0;
        if (m >= u_ref_n || dot(back, back) < dot(d, d)) { d = back; m = 0; }
        vec2 e = z - saved;
        if (dot(e, e) < eps2) { inside = true; return float(n); }
        if (++since == lim) { saved = z; since = 0; lim *= 2; }
    }
    inside = true;
    return float(cap);
}

vec4 effect(vec2 uv) {
    vec2 off = (uv - 0.5) * vec2(u_res.x / u_res.y, 1.0) * (3.0 / u_zoom);
    if (u_pass == 1) {
        // the skip's first pass: only a tile's border pixels iterate
        ivec2 px = ivec2(gl_FragCoord.xy) - u_origin;
        ivec2 at = px % TILE;
        ivec2 last = ivec2(u_width, u_lines) - 1;
        bool edge = at.x == 0 || at.y == 0 || at.x == TILE - 1 || at.y == TILE - 1
                    || px.x == last.x || px.y == last.y;
        if (!edge) return vec4(0.0, 0.0, 0.0, 1.0);
        bool inside;
        orbit(off, inside);
        return vec4(inside ? 1.0 : 0.0, 0.0, 0.0, 1.0);
    }
    if (u_tiles_on == 1) {
        ivec2 tile = (ivec2(gl_FragCoord.xy) - u_origin) / TILE;
        if (texelFetch(u_tiles, tile, 0).r > 0.5) return vec4(0.0, 0.0, 0.0, 1.0);
    }
    bool inside;
    float n = orbit(off, inside);
    if (inside && u_interior == 0) return vec4(0.0, 0.0, 0.0, 1.0);
    float b = rise(n);
    if (u_output == 1) {
        vec3 rgb = inside ? pal(b, vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.0, 0.10, 0.20)) * 0.5
                          : pal(b, vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.0, 0.33, 0.67));
        return vec4(rgb, 1.0);
    }
    return vec4(vec3(b), 1.0);
}
