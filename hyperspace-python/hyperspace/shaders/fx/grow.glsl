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
uniform int   u_mode;    // @param choice [grass|sprouts|blobs|noodles|mould|coral|cells] 0 "Field" What grows: a lawn seen from above, its blades lengthening and drooping, tufts sprouting in a scatter (chia seeds), blobs inflating and merging, spaghetti noodles oozing and thickening, mould colonies spreading from spores, a brain-coral maze closing, or the walls of plant cells thickening.
uniform float u_amount;  // @param 0 0.3 0.04 amount "Amount" How far the growth moves the pixels, in frame heights.
uniform int   u_push;    // @param choice [bulge|lift] 0 "Push" Bulge magnifies the frame under each lump like a lens; lift slides the pixels inside the growth along Angle by its height.
uniform float u_angle;   // @param 0 6.2832 1.5708 wrap "Angle" Lift: the direction the growth pushes, radians (0 right, a quarter turn up).
uniform float u_scale;   // @param 1 24 6 log "Scale" Blades, tufts or noodles across the frame's height.
uniform float u_soft;    // @param 0.01 0.5 0.08 log "Softness" The knee of the slice: low is a hard edge where the growth breaks through, high a slow swell. Grass and mould have no slice: they grow by Grow alone.
uniform float u_flow;    // @param 0 4 0.5 "Flow" How fast the field sways and oozes; a step changes the speed, never where the field is.
uniform float u_shade;   // @param 0 1 0.3 "Shade" Lights the growth's relief from the upper left, so the shape shows on the picture.

// Fields that grow by Grow itself, not by a slice: each feature has its
// own clock g out of Grow, started late by a golden-ratio stagger, and its
// parts grow on golden-ratio curves — reach as g^φ (slow, then shooting
// out), width as g^(1/φ) (fills out early), curl as g^(φ²) (only the long
// ones flop over). At Grow 0 nothing has started: nothing moves.
const float PHI = 1.6180340;

float clock_of(float seed) {
    float delay = 0.4 * fract(seed * PHI);
    return clamp((u_grow - delay) / (1.0 - delay), 0.0, 1.0);
}

// grass: a lawn seen from straight above, a tuft in each cell of a jittered
// grid. A tuft is one star in polar coordinates about its root — 5 to 7
// blades, each its own length (golden-ratio steps), the angle twisted by
// the radius squared so the blades curl over as they droop. One tuft is
// one evaluation, however many blades: nine per pixel, not one per blade
float grass(vec2 q, float t) {
    vec2 c0 = floor(q);
    float h = 0.0;
    for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
        vec2 cell = c0 + vec2(i, j);
        vec2 r = hash22(cell);
        float seed = hash21(cell + 3.0);
        float g = clock_of(seed);
        if (g <= 0.0) continue;
        vec2 v = q - (cell + 0.25 + 0.5 * r);
        float rad = length(v);
        float reach = 0.7 * pow(g, PHI);
        if (rad >= reach) continue;
        float n = 5.0 + floor(3.0 * r.y);                    // blades in the tuft
        float curl = (seed - 0.5) * 3.5 * pow(g, PHI * PHI);
        float a = atan(v.y, v.x) + curl * rad * rad
                + seed * TAU + 0.12 * sin(t + seed * TAU);   // the tuft sways
        float sector = TAU / n;
        float k = floor(a / sector + 0.5);
        float da = a - k * sector;                           // off its sector's centre
        k = mod(k, n);                                       // which blade, the same across atan's seam
        float jit = hash21(cell + vec2(k, 31.0)) - 0.5;
        da = abs(da - 0.35 * sector * jit);                  // each blade a little off the even fan
        float len = reach * pow(1.0 / PHI, 2.0 * fract(k * PHI + r.x));
        float u = rad / len;
        if (u >= 1.0) continue;
        float w = 0.09 * pow(g, 1.0 / PHI) * (1.0 - 0.85 * u);
        float x = rad * da / w;
        if (x < 1.0) h = max(h, (1.0 - x * x) * (1.0 - 0.5 * u * u));
    }
    return h;
}

// mould: colonies spreading from spores, as on bread. Each cell's spore
// starts on its own clock and its disc spreads as g^φ, its rim ragged by
// one noise shared by the whole pixel, with growth rings inside it; where
// colonies meet they merge. A slice would only threshold the disc, so it
// grows by Grow like the grass
float mould(vec2 q, float t) {
    float ragged = 0.22 * perlin(q * 2.7 + vec2(t * 0.1, 0.0));
    vec2 c0 = floor(q);
    float h = 0.0;
    for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
        vec2 cell = c0 + vec2(i, j);
        vec2 r = hash22(cell);
        float g = clock_of(hash21(cell + 5.0));
        float R = 0.8 * pow(g, PHI);
        float d = length(q - cell - 0.1 - 0.8 * r) + ragged;
        if (d >= R) continue;
        float inside = R - d;
        float rings = 0.8 + 0.2 * sin(inside * 16.0);
        h = max(h, sqrt(min(1.0, inside / max(R, 0.05))) * rings);   // a dome: merged colonies keep their relief
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

// coral: a brain-coral labyrinth — the contour lines of a slow noise,
// folded tight, so a falling slice thickens them into a maze that closes
float coral(vec2 q, float t) {
    float n = perlin(q * 0.6 + vec2(0.0, t * 0.05)) + 0.5 * perlin(q * 1.3 + 11.0);
    return 0.5 + 0.5 * sin(n * 40.0 + t * 0.3);
}

// cells: the walls between cells (Voronoi, the second-nearest seed less
// the nearest), so a falling slice thickens walls into a honeycomb of
// plant cells — or, read the other way, leaf veins
float cells(vec2 q, float t) {
    vec2 c0 = floor(q);
    float f1 = 9.0, f2 = 9.0;
    for (int j = -1; j <= 1; j++)
    for (int i = -1; i <= 1; i++) {
        vec2 cell = c0 + vec2(i, j);
        vec2 r = hash22(cell);
        vec2 o = 0.5 + 0.3 * vec2(sin(t + r.x * TAU), cos(t * 0.8 + r.y * TAU));   // within reach of the 3 × 3 search
        float d = length(q - cell - o);
        if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) { f2 = d; }
    }
    return 1.0 - smoothstep(0.0, 0.5, f2 - f1);
}

float field(vec2 uv) {
    vec2 q = centred(uv) * u_scale;
    if (u_mode == 0) return grass(q, u_flow_t);
    if (u_mode == 1) return sprouts(q, u_flow_t);
    if (u_mode == 2) return blobs(q, u_flow_t);
    if (u_mode == 3) return noodles(q, u_flow_t);
    if (u_mode == 4) return mould(q, u_flow_t);
    if (u_mode == 5) return coral(q, u_flow_t);
    return cells(q, u_flow_t);
}

// the growth above the slice (grass: the lawn as it is): 0 below it, the height above it beyond the
// knee, and a smooth (C1) ramp across the knee so the slope never jumps
float growth(vec2 uv) {
    if (u_mode == 0 || u_mode == 4) return field(uv);   // grass and mould grow by Grow itself, no slice
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
