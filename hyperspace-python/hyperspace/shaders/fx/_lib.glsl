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
