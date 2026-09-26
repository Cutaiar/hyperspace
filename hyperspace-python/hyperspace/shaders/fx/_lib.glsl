// Helpers for every effect in this folder — prepended to each one (fx.py).
// EDIT WHILE THE APP RUNS: every effect recompiles on save.
//
// What an effect has to work with:
//   u_src      sampler2D — the frame so far (premultiplied RGBA)
//   u_res      vec2      — its size in pixels
//   u_phase    float     — the effect's clock: seconds × its speed fader
//   u_time     float     — seconds, wall clock (for flicker that must not
//                          stop when the speed is 0)
//   v_uv       vec2      — this pixel, 0..1 across the frame, y up
// and must define  vec4 effect(vec2 uv)  — premultiplied colour that the
// chain then blends onto the frame by the effect's blend and mix.

const float PI = 3.14159265359;
const float TAU = 6.28318530718;
const vec3 LUMA = vec3(0.299, 0.587, 0.114);

float luma(vec3 c) { return dot(c, LUMA); }
float peak(vec3 c) { return max(c.r, max(c.g, c.b)); }

// the frame at uv, mirrored past the edges so a warp never smears a border
vec4 src(vec2 uv) {
    uv = 1.0 - abs(1.0 - mod(uv, 2.0));
    return texture(u_src, uv);
}

// centred coordinates: the frame's height is 1, x runs with the aspect
vec2 centred(vec2 uv) { return (uv - 0.5) * vec2(u_res.x / u_res.y, 1.0); }
vec2 uncentred(vec2 p) { return p / vec2(u_res.x / u_res.y, 1.0) + 0.5; }

mat2 rot(float a) {
    float c = cos(a), s = sin(a);
    return mat2(c, s, -s, c);
}

vec3 hsv2rgb(vec3 c) {
    vec3 k = mod(vec3(5.0, 3.0, 1.0) + c.x * 6.0, 6.0);
    return c.z - c.z * c.y * clamp(min(k, 4.0 - k), 0.0, 1.0);
}

vec3 rgb2hsv(vec3 c) {
    vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
    vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
    vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
    float d = q.x - min(q.w, q.y);
    return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + 1e-10)), d / (q.x + 1e-10), q.x);
}

// the chroma plane turned about the grey axis (YIQ): luminance is kept
vec3 hue_rotate(vec3 c, float a) {
    float y = dot(c, LUMA);
    float i = dot(c, vec3(0.596, -0.274, -0.322));
    float q = dot(c, vec3(0.211, -0.523, 0.312));
    float ca = cos(a), sa = sin(a);
    float i2 = i * ca - q * sa, q2 = i * sa + q * ca;
    return vec3(y + 0.956 * i2 + 0.621 * q2, y - 0.272 * i2 - 0.647 * q2,
                y - 1.106 * i2 + 1.703 * q2);
}

// cosine palette (iq): a + b·cos(2π(c·t + d))
vec3 pal(float t, vec3 a, vec3 b, vec3 c, vec3 d) { return a + b * cos(TAU * (c * t + d)); }

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
