// @label Grow
// @order 23
// @blend mix
// @speed 1
// @tip Organic growth as a displacement map: a lawn seen from above, sprouting tufts,
// @tip inflating blobs or oozing spaghetti. Grow is how far along it is — the grass from
// @tip shoots to long drooping blades, the others a slice plane falling through their
// @tip field — and the growth pushes the frame's pixels. Put an LFO on Grow to phase the
// @tip growth in and out. At 0 nothing has grown and nothing moves.
// @clock u_flow_t flow

// The field h(p) is a height map, about 0..1. Grass grows its blades by
// Grow itself (below). For the others Grow sets the slice at
// 1 − grow (widened by the knee): what stands above it is the growth, f = h − slice through a
// soft knee (Softness), and the frame is moved by f — Bulge samples up the
// growth's slope, so every lump magnifies like a drop of water (the chia
// pet inflating); Lift slides the pixels inside the growth along Angle by
// its height. Shade lights the growth's relief so the shape reads.
// Flow is a rate: u_flow_t is integrated by fx.py (@clock), the sway of
// the blades and the ooze of the noodles read it, never u_phase × a knob.
uniform float u_grow;    // @param 0 1 0.5 "Grow" How far the growth has come: grass from bare ground through shoots to long drooping blades; the others a slice falling through their field, 0 nothing pokes through, 1 all of it. The knob to ride with an LFO.
uniform int   u_mode;    // @param choice [grass|sprouts|blobs|noodles] 0 "Field" What grows: a lawn seen from above, its blades lengthening and drooping, tufts sprouting in a scatter (chia seeds), blobs inflating and merging, or spaghetti noodles oozing and thickening.
uniform float u_amount;  // @param 0 0.3 0.04 amount "Amount" How far the growth moves the pixels, in frame heights.
uniform int   u_push;    // @param choice [bulge|lift] 0 "Push" Bulge magnifies the frame under each lump like a lens; lift slides the pixels inside the growth along Angle by its height.
uniform float u_angle;   // @param 0 6.2832 1.5708 wrap "Angle" Lift: the direction the growth pushes, radians (0 right, a quarter turn up).
uniform float u_scale;   // @param 1 24 6 log "Scale" Blades, tufts or noodles across the frame's height.
uniform float u_soft;    // @param 0.01 0.5 0.08 log "Softness" The knee of the slice: low is a hard edge where the growth breaks through, high a slow swell. Grass has no slice: it grows by Grow alone.
uniform float u_flow;    // @param 0 4 0.5 "Flow" How fast the field sways and oozes; a step changes the speed, never where the field is.
uniform float u_shade;   // @param 0 1 0.3 "Shade" Lights the growth's relief from the upper left, so the shape shows on the picture.

// grass: a lawn seen from straight above. A tuft in every cell of a
// jittered grid, seven blades each, fanned out by the golden angle (and a
// little jitter) so no two line up, each rooted a touch off the tuft's centre. A blade is a stroke from its root along its heading, curling
// to one side as it droops (a parabola from above), tapering to its tip;
// its height is a rounded cross-section, highest near the root, lower
// toward the drooping tip. Each blade grows on its own clock out of Grow:
// it starts late by a golden-ratio stagger, then its reach goes as g^φ
// (slow at first, then shooting out), its width as g^(1/φ) (a shoot fills
// out early) and its droop as g^(φ²) (only a long blade flops over). At
// Grow 0 every blade has no length: bare ground, nothing moves.
const float PHI = 1.6180340;
const float GOLDEN_ANGLE = 2.3999632;    // 2π / φ²

float blade(vec2 q, vec2 root, float th, float reach, float curl, float wide) {
    if (reach <= 1e-4 || wide <= 1e-5) return 0.0;
    vec2 dir = vec2(cos(th), sin(th));
    vec2 r = q - root;
    vec2 l = vec2(dot(r, dir), dot(r, vec2(-dir.y, dir.x)));   // along, across
    float s = clamp(l.x, 0.0, reach);
    float d = length(vec2(l.x - s, l.y - curl * s * s));
    float u = s / reach;                     // 0 at the root, 1 at the tip
    float w = wide * (1.0 - 0.85 * u);
    float x = d / w;
    if (x >= 1.0) return 0.0;
    return (1.0 - x * x) * (1.0 - 0.5 * u * u);
}

float grass(vec2 q, float t) {
    vec2 c0 = floor(q);
    float h = 0.0;
    for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
        vec2 cell = c0 + vec2(i, j);
        vec2 r = hash22(cell);
        vec2 root = cell + 0.15 + 0.7 * r;
        float seed = hash21(cell + 3.0);
        float th0 = seed * TAU + 0.12 * sin(t + seed * TAU);     // the tuft sways
        for (int k = 0; k < 7; k++) {
            float fk = float(k);
            vec2 b = hash22(cell + vec2(fk * 3.7, 23.0));
            float delay = 0.4 * fract(fk / PHI + seed);
            float g = clamp((u_grow - delay) / (1.0 - delay), 0.0, 1.0);
            float len = 0.75 * pow(1.0 / PHI, 2.0 * fract(fk * PHI + r.x));   // 0.75/φ² … 0.75
            float side = hash21(cell + vec2(fk, 7.0)) < 0.5 ? -1.0 : 1.0;
            float curl = side * (0.25 + 0.45 * hash21(cell + vec2(fk, 11.0)));
            float th = th0 + fk * GOLDEN_ANGLE + 0.5 * (b.x - 0.5);
            vec2 at = root + 0.06 * (b - 0.5);
            h = max(h, blade(q, at, th,
                             len * pow(g, PHI),
                             curl * pow(g, PHI * PHI),
                             0.08 * pow(g, 1.0 / PHI)));
        }
    }
    return h;
}

// sprouts: a tuft in every cell of a jittered grid, each with its own
// height, so as the slice falls they break through one by one
float sprouts(vec2 q, float t) {
    vec2 c0 = floor(q);
    float h = 0.0;
    for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
        vec2 cell = c0 + vec2(i, j);
        vec2 r = hash22(cell);
        vec2 o = 0.2 + 0.6 * r + 0.08 * vec2(sin(t + r.x * TAU), cos(t + r.y * TAU));
        float tall = 0.3 + 0.7 * hash21(cell + 17.0);
        float d = length(q - cell - o) / 0.75;
        h = max(h, tall * pow(max(0.0, 1.0 - d), 1.5));
    }
    return h;
}

// blobs: three octaves of noise, drifting — lumps that inflate and merge
float blobs(vec2 q, float t) {
    vec2 s = vec2(t * 0.15, -t * 0.1);
    float n = perlin(q + s) + 0.5 * perlin(q * 2.03 - s + 3.1) + 0.25 * perlin(q * 4.01 + 7.7);
    return clamp(0.5 + n * 0.8, 0.0, 1.0);
}

// noodles: two tangles of ridged, domain-warped noise — a tube along every
// zero line, highest on its centreline, so a falling slice fattens them
float noodles(vec2 q, float t) {
    vec2 w = q + 0.6 * perlin2(q * 0.5 + vec2(t * 0.3, -t * 0.2));
    float a = 1.0 - min(1.0, abs(perlin(w)) * 4.0);
    float b = 1.0 - min(1.0, abs(perlin(w * 1.3 + 19.0)) * 4.0);
    return pow(max(a, b * 0.85), 2.0);
}

float field(vec2 uv) {
    vec2 q = centred(uv) * u_scale;
    if (u_mode == 0) return grass(q, u_flow_t);
    if (u_mode == 1) return sprouts(q, u_flow_t);
    if (u_mode == 2) return blobs(q, u_flow_t);
    return noodles(q, u_flow_t);
}

// the growth above the slice (grass: the lawn as it is): 0 below it, the height above it beyond the
// knee, and a smooth (C1) ramp across the knee so the slope never jumps
float growth(vec2 uv) {
    if (u_mode == 0) return field(uv);       // grass grows by Grow itself, no slice
    float k = u_soft;
    // the slice runs from a knee above the field's top (grow 0: nothing,
    // exactly) to a knee below its floor (grow 1: all of it)
    float d = field(uv) - mix(1.0 + k, -k, u_grow);
    if (d <= -k) return 0.0;
    if (d >= k) return d;
    return (d + k) * (d + k) / (4.0 * k);
}

vec4 effect(vec2 uv) {
    // forward differences, a pixel and a half apart; the slope is per frame
    // height, divided by Scale so Amount means the same at every scale
    vec2 e = 1.5 / u_res;
    float f = growth(uv);
    vec2 g = vec2(growth(uv + vec2(e.x, 0.0)) - f, growth(uv + vec2(0.0, e.y)) - f)
           / (1.5 / u_res.y);
    vec2 aspect = vec2(u_res.y / u_res.x, 1.0);
    vec2 d = u_push == 0
        ? g / u_scale * u_amount
        : -vec2(cos(u_angle), sin(u_angle)) * f * u_amount;
    vec4 c = src(uv + d * aspect);
    // a flat field lights to 1; the slope tilts the normal toward or away
    // from a light at the upper left
    vec3 n = normalize(vec3(-g / u_scale, 1.0));
    vec3 l = normalize(vec3(-0.5, 0.6, 0.6));
    float light = clamp(dot(n, l) / l.z, 0.0, 1.6);
    c.rgb *= mix(1.0, light, u_shade * min(1.0, f / max(u_soft, 1e-3)));
    return c;
}
