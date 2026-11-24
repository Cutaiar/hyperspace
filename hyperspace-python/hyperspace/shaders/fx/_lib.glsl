// Helpers for every effect in this folder — prepended to each one (fx.py)
// after shaders/_common.glsl, which holds the colour maths every shader
// shares: PI, TAU, LUMA, luma, peak, rot, hsv2rgb, hsv, rgb2hsv, hue_rotate, pal.
// EDIT WHILE THE APP RUNS: every effect recompiles on save.
//
// Where an effect sits is its wires on the GRAPH page (plan 33): there is
// no stack. `// @order N` at the top of a file is parsed and ignored by
// the renderer; only the migration of a preset saved before plan 33 reads
// it, to give an effect without a saved order its place in that preset's
// run. A new effect file does not need one.
//
// What an effect has to work with:
//   u_src      sampler2D — the picture wired into the effect's image port
//                          (premultiplied RGBA)
//   u_res      vec2      — its size in pixels
//   u_phase    float     — the effect's clock: seconds × its speed fader
//   u_time     float     — seconds, wall clock (for flicker that must not
//                          stop when the speed is 0)
//   u_<clock>  float     — a `// @clock u_<clock> <rate-param> [period]` line
//                          at the top of a file: a phase fx.py integrates
//                          every frame at speed × that param (wrapped to the
//                          period if one is given) and declares beside u_phase.
//                          The rate may be a product, `drift*scale` (each of
//                          the file's own params once): warp's scroll counted
//                          in cells, so a scale step slides nothing.
//                          THE RULE: no shader multiplies u_phase or u_time by
//                          a param — `u_phase * u_drift` jumps the field by
//                          phase × Δdrift on a knob step, hours into a set;
//                          declare a @clock and read the phase instead
//                          (tests/test_shader_time_lint.py holds every file to it)
//   v_uv       vec2      — this pixel, 0..1 across the frame, y up
//   u_aux      sampler2D — the second picture, wired into the effect's aux
//                          port (plan 32 R: a channel, the scene, the history);
//                          read it with aux(uv) / aux_luma(uv) below
//   u_aux_on   int       — 1 while one is wired; 0: aux(uv) is transparent black
//   u_aux_size vec2      — its size in pixels (0, 0 with none)
// and must define  vec4 effect(vec2 uv)  — premultiplied colour that the
// pass then blends onto its input by the effect's blend and mix.

// the frame at uv, mirrored past the edges so a warp never smears a border
vec4 src(vec2 uv) {
    uv = 1.0 - abs(1.0 - mod(uv, 2.0));
    return texture(u_src, uv);
}

// the aux picture at uv, mirrored past the edges like src; transparent
// black while nothing is wired into the effect's aux port
vec4 aux(vec2 uv) {
    if (u_aux_on == 0) return vec4(0.0);
    uv = 1.0 - abs(1.0 - mod(uv, 2.0));
    return texture(u_aux, uv);
}

// its brightness (premultiplied: a see-through pixel is dark)
float aux_luma(vec2 uv) { return luma(aux(uv).rgb); }

// centred coordinates: the frame's height is 1, x runs with the aspect
vec2 centred(vec2 uv) { return (uv - 0.5) * vec2(u_res.x / u_res.y, 1.0); }
vec2 uncentred(vec2 p) { return p / vec2(u_res.x / u_res.y, 1.0) + 0.5; }

// hashes without sin(): stable across GPUs
float hash21(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec2 hash22(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.xx + p3.yz) * p3.zy);
}

// Perlin gradient noise, about −0.5..0.5 — the stand-in for the noise
// texture Noita's post shader samples
float perlin(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    float a = hash21(i) * TAU, b = hash21(i + vec2(1, 0)) * TAU;
    float c = hash21(i + vec2(0, 1)) * TAU, d = hash21(i + vec2(1, 1)) * TAU;
    float na = dot(vec2(cos(a), sin(a)), f);
    float nb = dot(vec2(cos(b), sin(b)), f - vec2(1, 0));
    float nc = dot(vec2(cos(c), sin(c)), f - vec2(0, 1));
    float nd = dot(vec2(cos(d), sin(d)), f - vec2(1, 1));
    return mix(mix(na, nb, u.x), mix(nc, nd, u.x), u.y) * 0.75;
}

// two decorrelated channels of it — a noise texture's .xy − 0.5
vec2 perlin2(vec2 p) { return vec2(perlin(p), perlin(p + vec2(31.7, 11.3))); }

// the brightest of the frame in a ring of radius r px about uv — a cheap
// dilation, so an effect keyed on content reaches past a 1-px line
float reach(vec2 uv, float r) {
    float m = peak(texture(u_src, uv).rgb);
    if (r <= 0.0) return m;
    vec2 px = r / u_res;
    for (int k = 0; k < 8; k++) {
        float a = float(k) * (TAU / 8.0);
        m = max(m, peak(texture(u_src, uv + px * vec2(cos(a), sin(a))).rgb));
        m = max(m, peak(texture(u_src, uv + 0.5 * px * vec2(cos(a + 0.39), sin(a + 0.39))).rgb));
    }
    return m;
}

// ---- distortion: where each pixel reads from -------------------------------
// A distortion is a field of offsets: for every pixel, how far away it
// reads the frame. Three questions make one — what is measured across the
// frame (a distance along a line, a radius, a block's number), what shape
// is laid over that measure (`wave`), and which way the result pushes —
// and `pushed` does the read. shake, wave and blocks are all this.

// A new random level at each whole x, eased between, −1 … 1, the same
// again every `every` (a whole number): 4096 is a @clock's period, and a
// count round a circle is how many waves meet there, so the last joins the first
float noise1(float x, float every) {
    float i = floor(x), f = fract(x);
    f = f * f * (3.0 - 2.0 * f);
    return mix(hash21(vec2(mod(i, every), 7.3)),
               hash21(vec2(mod(i + 1.0, every), 7.3)), f) * 2.0 - 1.0;
}

// One cycle of a waveform over x (period 1), −1 … 1, all in step with the
// sine: 0 sine, 1 triangle, 2 square, 3 saw, 4 noise (`noise1`, repeating
// every 4096)
float wave(int shape, float x) {
    if (shape == 1) return 4.0 * abs(fract(x - 0.25) - 0.5) - 1.0;
    if (shape == 2) return fract(x) < 0.5 ? 1.0 : -1.0;
    if (shape == 3) return 2.0 * fract(x) - 1.0;
    if (shape == 4) return noise1(x, 4096.0);
    return sin(x * TAU);
}

// the frame read d away from uv (d in frame heights, so a push is as long
// across as it is up). Split parts the colours along the push: red reads
// (1 + split) × as far, green as far, blue (1 − split) × — every distortion
// its own chromatic aberration, widest where it moves the most
vec4 pushed(vec2 uv, vec2 d, float split) {
    vec2 o = d * vec2(u_res.y / u_res.x, 1.0);
    if (split <= 0.0) return src(uv + o);
    vec4 R = src(uv + o * (1.0 + split)), G = src(uv + o), B = src(uv + o * (1.0 - split));
    return vec4(R.r, G.g, B.b, max(R.a, max(G.a, B.a)));
}

// ---- fields: the shared pieces (plan 67 P2) ---------------------------------
// A field is a value (or a pair) at every pixel. These are the primitives the
// field nodes are built from (plan 67 §3), written once, so an effect file that
// still computes its field inline calls the same code and agrees with the
// patch that replaces it to the bit. Units: frame heights for distance (the
// frame's height is 1, `centred`), turns for an angle round a point, radians
// for an Angle knob, as every file already reads it.

// -- point: a Centre X / Centre Y pair (−1 … 1: the left or bottom edge … the
// right or top) as a place in centred coordinates
vec2 point_at(float cx, float cy) { return vec2(cx * 0.5 * u_res.x / u_res.y, cy * 0.5); }

// this pixel seen from that point, in frame heights
vec2 from_point(vec2 uv, float cx, float cy) { return centred(uv) - point_at(cx, cy); }

// -- measure: what is counted across the frame (DISTORTION.md's first
// question). `x` is the measure, `g` the unit direction it grows in (0 where
// it has none: the centre of rings and spokes)
struct Measure { float x; vec2 g; };

// distance along the direction `angle` (radians, 0 across), in frame heights
Measure measure_line(vec2 p, float angle) {
    vec2 g = vec2(cos(angle), sin(angle));
    return Measure(dot(p, g), g);
}

// distance from p's origin, in frame heights; it grows outward
Measure measure_rings(vec2 p) {
    float r = length(p);
    return Measure(r, r > 1e-5 ? p / r : vec2(0.0));
}

// the angle round p's origin, in turns, −½ … ½ (0 across to the right, ½ the
// seam on the left); it grows anticlockwise
Measure measure_spokes(vec2 p) {
    Measure m = measure_rings(p);
    return Measure(atan(p.y, p.x) / TAU, vec2(-m.g.y, m.g.x));
}

// a cell's place along a rule over a grid of cells `id` (Blocks): rows,
// columns, the diagonal, square rings from the middle, or random; `spread` is
// how far out of step one cell is with the next (random: × 64, so 1 is
// thoroughly shuffled and 0 every cell in step)
float measure_cells(vec2 id, int rule, float spread) {
    if (rule == 0) return id.y * spread;
    if (rule == 1) return id.x * spread;
    if (rule == 2) return (id.x + id.y) * spread;
    if (rule == 3) return max(abs(id.x), abs(id.y)) * spread;
    return hash21(id + 64.5) * 64.0 * spread;
}

// -- cells: a grid over grid coordinates q (a cell a unit, a cell's corner at
// each whole q). `id` is the pixel's block (`group` cells on a side share
// one), `l` its place in its cell, −½ … ½ (Blocks, Measure's cells)
struct Cell { vec2 id; vec2 l; };
Cell cell_of(vec2 q, int group) { return Cell(floor(floor(q) / float(group)), fract(q) - 0.5); }

// blocks paired off along `ax` (across or up), so a pair shares one number
// (Blocks' swap): `id` becomes the pair's; +1 in its first block, −1 its second
float cell_pair(inout vec2 id, vec2 ax) {
    float along = dot(id, ax);
    id -= ax * (along - floor(along * 0.5));
    return 1.0 - 2.0 * mod(along, 2.0);
}

// -- picture: a picture read as a field. `luma`, `peak` and `reach` (above)
// read it unsigned; these read it signed about mid-grey, premultiplied, so
// a see-through pixel (and an unwired aux) is 0 — Displace's convention
float read_signed(float v, float alpha) { return (v - 0.5 * alpha) * 2.0; }
vec2 read_signed(vec2 v, float alpha) { return (v - 0.5 * alpha) * 2.0; }

// -- ops (plan 67 §3.2: the modifiers' names) --------------------------------

// x flattened to `steps` levels each side of 0 (steps ≤ 0: x as it is)
float quantise(float x, int steps) {
    return steps > 0 ? floor(x * float(steps) + 0.5) / float(steps) : x;
}

// a soft key: 0 below key − soft, 1 above key + soft, a ramp between
// (soft 0: a hard step at the key)
float threshold_soft(float x, float key, float soft) {
    return clamp((x - key + soft) / max(2.0 * soft, 1e-4), 0.0, 1.0);
}

// x from in_lo … in_hi onto out_lo … out_hi, straight, unclamped
float remap(float x, float in_lo, float in_hi, float out_lo, float out_hi) {
    return out_lo + (x - in_lo) / (in_hi - in_lo) * (out_hi - out_lo);
}

// two fields into one: 0 add, 1 multiply, 2 min, 3 max
float combine(float a, float b, int how) {
    if (how == 1) return a * b;
    if (how == 2) return min(a, b);
    if (how == 3) return max(a, b);
    return a + b;
}

// -- the field wire (plan 67 F1) ----------------------------------------------
// A field travels as float32 RGBA at the frame's size: x (and y) its value,
// .a 0 for a scalar field and 1 for a vector one. A file that makes one says
// `// @makes field` and returns `as_scalar(x)` or `as_vector(v)` from
// `effect`; one that reads one says `// @takes image field` (its input is a
// field: `field_in`) or `// @takes field field` (a field beside its picture:
// `field_port`). Read texel for texel: a field is never filtered.
vec4 as_scalar(float x) { return vec4(x, 0.0, 0.0, 0.0); }
vec4 as_vector(vec2 v) { return vec4(v, 0.0, 1.0); }

// the field in sampler `s` at uv, its nearest texel
vec4 field_at(sampler2D s, vec2 uv) {
    ivec2 n = textureSize(s, 0);
    return texelFetch(s, clamp(ivec2(uv * vec2(n)), ivec2(0), n - 1), 0);
}

// the field on the image port (a field op's input) and on the field port
// (no field wired: 0, a scalar)
vec4 field_in(vec2 uv) { return field_at(u_src, uv); }
vec4 field_port(vec2 uv) { return u_field_on != 0 ? field_at(u_field, uv) : vec4(0.0); }

// a field read as a vector: a vector field's pair; a scalar field pushes
// along `dir` (radians) by its value
vec2 field_vector(vec4 f, float dir) {
    return f.a > 0.5 ? f.xy : f.x * vec2(cos(dir), sin(dir));
}

// a field shown as a picture, the grey promotion: a scalar grey about
// mid-grey (−1 black, 1 white), a vector its x in red and y in green
vec3 field_grey(vec4 f) {
    vec3 c = f.a > 0.5 ? vec3(0.5 + 0.5 * f.xy, 0.5) : vec3(0.5 + 0.5 * f.x);
    return clamp(c, 0.0, 1.0);
}
