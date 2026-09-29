// Helpers shared by every shader — the face patterns (patterns.glsl), every
// effect in fx/ (after this comes fx/_lib.glsl) and the look-back's post
// pass. Prepended by glsl.py; EDIT WHILE THE APP RUNS and the patterns and
// effects recompile. Nothing here reads a uniform, so it compiles anywhere.

const float PI = 3.14159265359;
const float TAU = 6.28318530718;
const vec3 LUMA = vec3(0.299, 0.587, 0.114);

float luma(vec3 c) { return dot(c, LUMA); }
float peak(vec3 c) { return max(c.r, max(c.g, c.b)); }

mat2 rot(float a) {
    float c = cos(a), s = sin(a);
    return mat2(c, s, -s, c);
}

// hue [0,1), saturation, value → rgb
vec3 hsv2rgb(vec3 c) {
    vec3 k = mod(vec3(5.0, 3.0, 1.0) + c.x * 6.0, 6.0);
    return c.z - c.z * c.y * clamp(min(k, 4.0 - k), 0.0, 1.0);
}
vec3 hsv(float h, float s, float v) { return hsv2rgb(vec3(h, s, v)); }

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

// cosine palette (iq): a + b·cos(2π(c·t + d)) — smooth colour cycles
// without hue banding. a = base, b = amplitude, c = frequency, d = phase.
vec3 pal(float t, vec3 a, vec3 b, vec3 c, vec3 d) { return a + b * cos(TAU * (c * t + d)); }
