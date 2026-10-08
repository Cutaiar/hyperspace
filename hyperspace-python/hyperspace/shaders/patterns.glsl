// Hyperspace face patterns — EDIT THIS FILE WHILE THE APP RUNS.
// It hot-reloads on save; a compile error keeps the last good version and
// shows the message in the panel.
//
// Contract: vec4 pattern(int mode, vec2 uv, float fid)
//   .rgb  face colour (full colour space — blended over the black ground)
//   .a    intensity in [0, 1]; multiplies the face fill alpha
// Available uniforms:
//   u_time      seconds since launch (the patterns read u_ptime instead)
//   u_ptime     the patterns' clock: seconds × SPEED, integrated by the
//               renderer, so a SPEED that moves never jumps the phase
//   u_mod[8]    the eight pattern inputs — pattern.mod.0–7 in the
//               registry, range 0..2.6, 1.0 = the un-driven look
//   u_levels[8], u_nlevels
//               the analyzer's lanes as a route reads them (out / CEIL,
//               0..1, low band first) and how many there are — 0 with no
//               audio. Read them through band(i). Only the modes that draw
//               the music itself (METER, PULSE) do: every other mode is
//               moved by the music through the inputs, as routed.
//   fid         face index within the shape
// uv is face-local: (0.5, 0.5) is the face centre, circumradius 0.5,
// identical framing on every congruent face.
//
// THE EIGHT INPUTS mean the same kind of change in every mode, so a route
// that works on one pattern works on the next. 1.0 is always the design.
// hyperspace/patterns.py holds the names, the meanings and what each one
// does per mode (the panel reads them from there — keep it in step).
//   0 SCALE   how big the elements are: 0 small and many (0.6×), 2.6 big
//             and few (2.3×) — k_size()
//   1 GLOW    how brightly it burns: 0 dim (0.3×), 2.6 bright and
//             white-hot (2.4×) — every mode alike, in finish()
//   2 WARP    how far its lines bend: 0 straight, 2.6 heavily warped —
//             warp(); a straight design stays straight from 0 to 1
//   3 SPEED   how fast it moves: 0 frozen, 2.6 2.6× — never read here:
//             the renderer folds it into u_ptime
//   4 COLOUR  how much colour: 0 grey, 2.6 more hues, stronger — finish()
//             and the mode's own hue spread (spread_hue(), m_colour())
//   5 SHARP   how hard its edges are: 0 soft and broad, 2.6 thin and
//             crisp — sharpen(), k_edge()
//   6 HUE     turns the palette round the wheel, half a turn per unit:
//             0 half a turn back, 2.6 four fifths forward — finish()
//   7 SPREAD  how differently each face plays: 0 every face in unison,
//             2.6 each face its own phase and colour — face_rad()
// The order is for the factory routes, which put the analyzer's lane i on
// input i: SUB swells the scale, BASS flashes the glow, MIDB bends, MID
// drives the speed, UPR flares the colour, AIR sharpens. HUE and SPREAD
// are left for an LFO, a macro or a knob.
//
// TAU, PI, hsv(h, s, v), pal(t, a, b, c, d), hue_rotate and luma come from
// shaders/_common.glsl, prepended to this file (and to every effect).
// A new mode: a case in design() that reads the inputs through the
// helpers below, and its name and its eight effects in patterns.py.

// 2D hashes and value noise, for the cellular / stochastic modes. These
// are this file's own on purpose — fx/_lib.glsl has a different pair, and
// the cellular modes were tuned on these; changing them moves every cell.
float hash21(vec2 p) {
    p = fract(p * vec2(234.34, 435.345));
    p += dot(p, p + 34.23);
    return fract(p.x * p.y);
}

vec2 hash22(vec2 p) {
    vec3 q = fract(p.xyx * vec3(127.1, 311.7, 74.7));
    q += dot(q, q.yzx + 19.19);
    return fract(vec2(q.x * q.y, q.y * q.z));
}

float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + vec2(1.0, 0.0)), u.x),
               mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), u.x),
               u.y);
}

// fractal value noise, three octaves (MARBLE)
float fbm3(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 3; i++) {
        v += a * vnoise(p);
        p = p * 2.02 + vec2(3.1, 1.7);
        a *= 0.5;
    }
    return v / 0.875;
}

// the analyzer's band i, 0..1; 0 past the last band and with no audio.
// An if-chain, not u_levels[i]: a constant index on every compiler
float band(int i) {
    if (i < 0 || i >= u_nlevels) return 0.0;
    if (i == 0) return u_levels[0];
    if (i == 1) return u_levels[1];
    if (i == 2) return u_levels[2];
    if (i == 3) return u_levels[3];
    if (i == 4) return u_levels[4];
    if (i == 5) return u_levels[5];
    if (i == 6) return u_levels[6];
    if (i == 7) return u_levels[7];
    return 0.0;
}

// ---- the eight inputs, by name — a mode reads them only through these ----
float m_scale()  { return u_mod[0]; }
float m_glow()   { return u_mod[1]; }
float m_warp()   { return u_mod[2]; }
float m_speed()  { return u_mod[3]; }   // already in u_ptime: no mode reads it
float m_colour() { return u_mod[4]; }
float m_sharp()  { return u_mod[5]; }
float m_hue()    { return u_mod[6]; }
float m_spread() { return u_mod[7]; }

// SCALE as a factor on feature size — divide a frequency by it, multiply
// a length by it: 0 → 0.59, 1 → 1, 2.6 → 2.3
float k_size() { return exp2(0.75 * (m_scale() - 1.0)); }

// SHARP as an exponent on a 0–1 profile whose bright part is the line:
// 0 → ^0.33 (broad and soft), 1 → as designed, 2.6 → ^5.9 (thin, crisp)
float k_sharp() { return exp2(1.6 * (m_sharp() - 1.0)); }
float sharpen(float v) { return pow(clamp(v, 0.0, 1.0), k_sharp()); }
// SHARP as a factor on an edge's width: 0 → 2.8× softer, 2.6 → 0.19×
float k_edge() { return exp2(-1.5 * (m_sharp() - 1.0)); }

// WARP: a slow flow displacing the face coordinates. `own` is the bend the
// design has at 1.0 — 0 for a straight design, which then stays straight
// from 0 to 1 and bends above
vec2 warp(vec2 p, float own) {
    float a = own * m_warp() + 0.07 * max(m_warp() - 1.0, 0.0);
    return p + a * vec2(sin(p.y * 9.0 + u_ptime * 0.9 + 1.3),
                        sin(p.x * 8.0 - u_ptime * 0.8 + 0.4));
}

// SPREAD: how far each face is set apart from face 0. A design that set
// face `fid` off by fid·k — a phase in radians, a hue in turns — reads it
// through face_rad / face_turn: the same offset folded into one turn (so
// identical at 1.0) times SPREAD, so a moving SPREAD shifts a face by at
// most a turn per unit, however many faces the shape has. face_k1 is for
// a design whose faces play in unison: a golden-ratio scatter that holds
// them together from 0 to 1 and parts them above; face_gold, the same
// scatter from 0, for an offset that is not periodic.
float face_rad(float fid, float k)  { return mod(fid * k, TAU) * m_spread(); }
float face_turn(float fid, float k) { return fract(fid * k) * m_spread(); }
float face_gold(float fid) { return fract(fid * 0.6180339887) * m_spread(); }
float face_k1(float fid)   { return fract(fid * 0.6180339887) * max(m_spread() - 1.0, 0.0); }

// COLOUR above 1 brings in more hues: `col` turned by (COLOUR − 1)·x, x a
// −1..1 variable of the mode's that runs across the face independently of
// its palette (a petal, a swell, a thread), so the hues spread apart
vec3 spread_hue(vec3 col, float x) {
    float h = max(m_colour() - 1.0, 0.0) * x * 0.7;
    return abs(h) > 1e-4 ? hue_rotate(col, h) : col;
}

// GLOW, COLOUR and HUE, the same on every mode, over what the mode drew.
// Every term is the identity at 1.0, so the un-driven look is the design.
vec4 finish(vec4 c) {
    vec3 rgb = c.rgb;
    float a = clamp(c.a, 0.0, 1.0);
    float cm = m_colour();
    if (cm != 1.0)                                    // grey … stronger
        rgb = mix(vec3(luma(rgb)), rgb, cm < 1.0 ? cm : 1.0 + 0.3 * (cm - 1.0));
    float h = (m_hue() - 1.0) * PI;
    if (abs(h) > 1e-4)
        rgb = hue_rotate(rgb, h);
    float g = m_glow();
    a *= g < 1.0 ? 0.3 + 0.7 * g : 1.0 + 0.9 * (g - 1.0);
    rgb = mix(rgb, vec3(1.0), 0.35 * clamp((g - 1.0) / 1.6, 0.0, 1.0) * clamp(a, 0.0, 1.0));
    return vec4(clamp(rgb, 0.0, 1.0), clamp(a, 0.0, 1.0));
}

// ---- the modes after EMBER, each a function of its own ----

// METER — the bands themselves: a radial equaliser, a wedge of LED
// segments per band (SUB's starts at twelve o'clock, the rest clockwise,
// the wheel turning slowly), lit out from the hub as far as the band
// reads, the top segment white-hot. With
// no audio the six empty tracks still show. Spectrum palette, red to
// violet, on black.
vec4 meter(vec2 p, float t, float fid) {
    vec2 q = warp(p, 0.0);
    float r = length(q) / 0.47;
    float nb = u_nlevels > 0 ? float(u_nlevels) : 6.0;
    // clockwise from twelve o'clock, SUB's wedge centred there
    float turn = fract(atan(q.x, q.y) / TAU + 0.5 / nb + 0.02 * t + face_rad(fid, 1.0) / TAU);
    float s = floor(turn * nb);
    float L = band(int(s));
    float nseg = floor(9.0 / k_size()) + 1.0;
    float seg = floor(r * nseg);
    vec2 cell = vec2(fract(turn * nb), fract(r * nseg));
    float e = 0.06 * k_edge();
    float hw = 0.40 * pow(k_sharp(), -0.2);       // an LED's half-size: SHARP thins them
    vec2 c = abs(cell - 0.5);
    float led = smoothstep(hw + e, hw - e, c.x) * smoothstep(hw - 0.04 + e, hw - 0.04 - e, c.y);
    float lit = step(seg + 0.5, L * nseg) * step(r, 1.0);
    float top = lit * (1.0 - step(seg + 1.5, L * nseg));     // the last lit segment
    vec3 col = hsv(fract(0.78 * m_colour() * s / max(nb - 1.0, 1.0)), 0.9, 1.0);
    col = mix(col, vec3(1.0), 0.6 * top);
    float track = 0.32 * step(r, 1.0) * step(0.18, r);
    float hub = smoothstep(0.16, 0.16 - 0.05 * k_edge(), r);
    float a = led * max(lit, track) + hub * (0.25 + 0.75 * band(0));
    return vec4(col, clamp(a, 0.0, 1.0));
}

// PULSE — the beat as shapes: the kick swells a hot disc in a speaker
// cone and throws a ring out from it, the snare shoots four rays, the
// hats sparkle in a field of points. Silence plays an idle heartbeat (its rate is SPEED)
// so the mode reads at rest. Magenta-red kick, yellow snare, ice-cyan
// hats, on black.
vec4 pulse(vec2 p, float t, float fid) {
    int top = u_nlevels - 1;
    int mid = u_nlevels / 2;
    float kick = max(band(0), band(1));
    float snare = max(band(mid - 1), band(mid));
    float hats = max(band(top), band(top - 1));
    float idle = 1.0 - clamp((kick + snare + hats) * 4.0, 0.0, 1.0);
    float beat = exp(-fract(t * 0.8 + face_rad(fid, 1.0) / TAU) * 5.0);
    kick = max(kick, idle * 0.75 * beat);
    snare = max(snare, idle * 0.45 * exp(-fract(t * 0.8 + 0.5 + face_rad(fid, 1.0) / TAU) * 6.0));
    hats = max(hats, idle * 0.12);
    vec2 q = warp(p, 0.0) / k_size();
    float r = length(q);
    float e = 0.02 * k_edge();
    float disc = smoothstep(0.08 + 0.16 * kick + e, 0.08 + 0.16 * kick - e, r);
    float rr = 0.16 + 0.30 * kick;
    float ring = smoothstep(0.035 + e, 0.035 - e, abs(r - rr)) * kick;
    float th = atan(q.y, q.x) + 0.3 * t + face_rad(fid, 0.7);
    float ray = pow(abs(cos(th * 2.0)), 24.0 * k_sharp()) * step(r, 0.12 + 0.36 * snare) * snare;
    vec2 g = q * 14.0;
    vec2 id = floor(g);
    // the sparkle's step, wrapped: hash21 reads the fraction of its input
    // × 435, so an unwrapped step (21600 an hour in) leaves float32 no
    // fraction and every point lit or dark together
    float tw = hash21(id + mod(floor(t * 6.0), 241.0) + fract(face_rad(fid, 1.3)));
    float dot_ = smoothstep(0.24, 0.24 - 0.10 * k_edge(), length(fract(g) - 0.5))
               * step(1.0 - hats * 0.7, tw);
    vec3 kc = vec3(1.0, 0.12, 0.38), sc = vec3(1.0, 0.85, 0.10), hc = vec3(0.55, 0.95, 1.0);
    float halo = exp(-r * 5.0 / (0.6 + kick)) * (0.30 + 0.45 * kick);  // the hot core's air
    // the cone: faint grooves round the core, pushed outward by the kick
    float cone = (0.16 + 0.25 * kick) * sharpen(0.5 + 0.5 * cos(r * 38.0 - kick * 6.0))
               * smoothstep(0.62, 0.20, r);
    // colour is which shape a point belongs to; how bright, the alpha
    float wk = disc + ring + halo + cone;
    vec3 col = (kc * wk + sc * ray + hc * dot_) / max(wk + ray + dot_, 1e-3);
    float a = max(max(max(disc, ring), max(ray, dot_)), max(halo, cone)) + 0.10 * kick * kick;
    return vec4(spread_hue(col, cos(r * 14.0)), clamp(a, 0.0, 1.0));
}

// MARBLE — domain-warped noise folded through itself twice: lapis ink
// with teal currents and gold veins, flowing. WARP is how far the noise
// folds (1 as designed, 0 plain clouds).
vec4 marble(vec2 p, float t, float fid) {
    vec2 q = warp(p, 0.0) * (3.0 / k_size()) + face_gold(fid) * vec2(4.1, 2.9);
    float fold = 3.5 * m_warp();
    vec2 a = vec2(fbm3(q + vec2(0.0, 0.07 * t)), fbm3(q + vec2(5.2, 1.3) - 0.05 * t));
    vec2 b = vec2(fbm3(q + fold * a + vec2(1.7, 9.2) + 0.09 * t),
                  fbm3(q + fold * a + vec2(8.3, 2.8)));
    float v = fbm3(q + fold * b);
    vec3 ink = vec3(0.02, 0.04, 0.16), lapis = vec3(0.10, 0.22, 0.62);
    vec3 teal = vec3(0.05, 0.65, 0.62), gold = vec3(1.0, 0.78, 0.30);
    vec3 col = mix(ink, lapis, smoothstep(0.25, 0.75, v));
    col = mix(col, teal, smoothstep(0.35, 0.95, length(a)) * 0.7);
    float vein = sharpen(1.0 - smoothstep(0.0, 0.07, abs(b.x - 0.5)));
    col = mix(col, gold, vein);
    col = spread_hue(col, 2.0 * a.y - 1.0);
    return vec4(col, clamp(0.35 + 0.65 * max(v, vein), 0.0, 1.0));
}

// TRUCHET — a maze of quarter arcs, tiles flipping now and then, a
// current running along the paths. Neon cyan to magenta on deep navy.
vec4 truchet(vec2 p, float t, float fid) {
    vec2 g = warp(p, 0.0) * (6.0 / k_size()) + face_gold(fid) * vec2(3.0, 7.0);
    vec2 id = floor(g);
    vec2 f = fract(g) - 0.5;
    float h = hash21(id);
    float flip = step(0.5, fract(h + floor(t * 0.12 + h * 4.0) * 0.5));
    if (flip > 0.5) f.x = -f.x;
    vec2 c = f.x + f.y > 0.0 ? vec2(0.5) : vec2(-0.5);
    vec2 d = f - c;
    float dist = abs(length(d) - 0.5);
    float w = 0.09 * pow(k_sharp(), -0.35);
    float e = 0.03 * k_edge();
    float line = smoothstep(w + e, w - e, dist);
    float along = atan(d.y, d.x) * 2.0 / PI + id.x + id.y;
    float current = 0.5 + 0.5 * sin(along * 3.0 - t * 3.0);
    vec3 col = pal(along * 0.12 * m_colour(), vec3(0.5), vec3(0.5), vec3(1.0),
                   vec3(0.50, 0.70, 0.95));
    col = mix(col, vec3(1.0), 0.5 * pow(current, 6.0) * line);
    vec3 ground = vec3(0.03, 0.04, 0.12) * (0.7 + 0.3 * mod(id.x + id.y, 2.0));
    float a = line * (0.45 + 0.55 * current);
    return vec4(mix(ground, col, line), clamp(max(a, 0.08), 0.0, 1.0));
}

// KALEIDO — six mirrored wedges of flat pop colour: bands and dots in
// magenta, yellow, cyan and black, turning. Bold, hard-edged, no blends.
vec3 pop(float k) {
    float i = mod(floor(k), 4.0);
    if (i < 0.5) return vec3(1.0, 0.18, 0.53);      // magenta
    if (i < 1.5) return vec3(1.0, 0.83, 0.0);       // yellow
    if (i < 2.5) return vec3(0.0, 0.78, 1.0);       // cyan
    return vec3(0.04, 0.02, 0.10);                  // ink
}

vec4 kaleido(vec2 p, float t, float fid) {
    vec2 w = warp(p, 0.0);
    float r = length(w);
    float wedge = TAU / 6.0;
    float th = atan(w.y, w.x) + 0.15 * t + face_rad(fid, 0.5);
    th = abs(mod(th, wedge) - 0.5 * wedge);
    vec2 q = r * vec2(cos(th), sin(th)) / k_size();
    float e = 0.012 * k_edge();
    float k = q.x * 9.0 - t * 0.6;
    float bandEdge = smoothstep(0.5 - e * 9.0, 0.5 + e * 9.0, fract(k));
    vec3 col = mix(pop(k), pop(k + 1.0), bandEdge);
    vec2 cell = fract(q * 7.0 + vec2(0.0, 0.1 * t)) - 0.5;
    float dots = smoothstep(0.24 + e * 7.0, 0.24 - e * 7.0, length(cell));
    col = mix(col, pop(k + 2.0), dots);
    float ink = step(peak(col), 0.2);
    col = spread_hue(col, sin(r * 9.0));
    return vec4(col, mix(0.85, 0.15, ink));
}

// the modes as designed; pattern() puts finish() over them
vec4 design(int mode, vec2 uv, float fid) {
    vec2 p = uv - 0.5;                       // centred face coordinates
    float t = u_ptime;                       // SPEED is in it

    if (mode == 1) {
        // RINGS — two ring sources beating; hue rides the ring phase.
        vec2 q = warp(p, 0.0);
        float r = length(q);
        float f = 28.0 / k_size();
        float ph = r * f - t * 3.0 / TAU;
        float a = sin(ph * TAU * 0.5);
        float b = sin(r * f * TAU * 0.31 + t * 1.7 + face_rad(fid, 0.7));
        float v = sharpen(0.5 + 0.5 * a * b);
        vec3 col = pal(ph * 0.15 * m_colour() + face_turn(fid, 0.03),
                       vec3(0.55), vec3(0.45), vec3(1.0), vec3(0.0, 0.33, 0.67));
        return vec4(col, v);
    }
    if (mode == 2) {
        // PLAID — two coloured wave systems crossing; where they agree the
        // colours add (constructive), where they cancel the face goes dark.
        // Every face weaves in step.
        vec2 q = warp(p, 0.0);
        float f = 16.0 / k_size();
        float off = face_k1(fid) * TAU;
        float a = sin(q.x * f * TAU + t + off);
        float b = sin(q.y * f * TAU - t * 1.3 + off * 1.7);
        vec3 ca = vec3(1.0, 0.25, 0.35) * sharpen(0.5 + 0.5 * a);   // warm axis
        vec3 cb = vec3(0.15, 0.55, 1.0) * sharpen(0.5 + 0.5 * b);   // cool axis
        vec3 col = ca + cb;
        col = spread_hue(col / max(max(col.r, col.g), max(col.b, 1.0)),
                         sin((q.x + q.y) * 6.0 + t * 0.3));
        return vec4(col, sharpen(0.5 + 0.5 * a * b));
    }
    if (mode == 3) {
        // MOIRE — near-frequency stripe fields; the interference envelope
        // sweeps a slow duotone between teal and magenta.
        vec2 w = warp(p, 0.0);
        float ang = 0.15 * sin(t * 0.23) + face_rad(fid, 0.05);
        vec2 q = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * w;
        float f = 10.0 * TAU / k_size();
        float a = sin(w.x * f);
        float b = sin(q.x * f * 0.96);
        float v = sharpen(0.5 + 0.5 * a * b);
        vec3 col = mix(vec3(0.10, 0.85, 0.75), vec3(0.90, 0.20, 0.80),
                       0.5 + 0.5 * sin(w.x * 3.0 + t * 0.4));
        col = spread_hue(col, sin(w.y * 7.0 - t * 0.3));
        return vec4(col, v);
    }
    if (mode == 4) {
        // BLOOM — a ring of seven petals turning, hue round the wheel.
        vec2 q = warp(p, 0.0);
        float r = length(q);
        float th = atan(q.y, q.x);
        float petals = cos(th * 7.0 + t * 1.4 + face_k1(fid) * TAU);
        float ring = exp(-abs(r - 0.30 * sqrt(k_size())) * 9.0 * sqrt(k_sharp() / k_size()));
        float v = sharpen(0.5 + 0.5 * petals) * ring * 1.6;
        vec3 col = spread_hue(hsv(fract(th / TAU + t * 0.05 + face_turn(fid, 0.02)), 0.8, 1.0),
                              petals);
        return vec4(col, v);
    }
    if (mode == 5) {
        // CAUSTIC — deep-water palette: dark blue troughs, bright cyan-white
        // filaments where three swells cross.
        vec2 q = warp(p, 0.0) / k_size();
        float s = sin(q.x * 21.0 + t * 1.1)
                + sin((q.x * 0.5 + q.y * 0.87) * 23.0 - t * 0.9)
                + sin((q.x * 0.5 - q.y * 0.87) * 19.0 + t * 1.3 + face_rad(fid, 1.0));
        float v = sharpen(clamp(1.0 - pow(abs(s) / 3.0, 4.0), 0.0, 1.0));
        vec3 col = spread_hue(mix(vec3(0.02, 0.10, 0.35), vec3(0.55, 0.95, 1.0), v * v),
                              s / 3.0);
        return vec4(col, v);
    }
    if (mode == 6) {
        // HEX — honeycomb lattice, every cell firing on its own phase.
        vec2 q = warp(p, 0.0) * (10.0 / k_size());
        vec2 rep = vec2(1.0, 1.7320508);
        vec2 ha = mod(q, rep) - rep * 0.5;
        vec2 hb = mod(q - rep * 0.5, rep) - rep * 0.5;
        vec2 gv = dot(ha, ha) < dot(hb, hb) ? ha : hb;
        vec2 id = q - gv;
        float fire = sharpen(0.5 + 0.5 * sin(t * 3.0 + hash21(id) * TAU + face_rad(fid, 1.0)));
        float e = 0.05 * k_edge();
        float cell = smoothstep(0.45 + e, 0.45 - e, length(gv));
        vec3 col = hsv(fract(hash21(id + 7.31) * m_colour() + t * 0.03), 0.7, 1.0);
        return vec4(col, cell * (0.25 + 0.75 * fire));
    }
    if (mode == 7) {
        // SPIRAL — galaxy arms winding out of a hot core, colour running
        // outward along each arm.
        vec2 q = warp(p, 0.0);
        float r = length(q);
        float th = atan(q.y, q.x);
        float ph = th * 5.0 + log(max(r, 1e-4)) * 8.0 / k_size()
                 - t * 1.8 + face_rad(fid, 0.5);
        float arm = pow(0.5 + 0.5 * cos(ph), 2.0 * k_sharp());
        float core = exp(-r * 5.0 / k_size());
        vec3 col = pal(r * 1.5 * m_colour() - t * 0.05,
                       vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.85, 0.60, 0.30));
        return vec4(col + core,
                    clamp(arm * smoothstep(0.55, 0.15, r) + core, 0.0, 1.0));
    }
    if (mode == 8) {
        // CELLS — living voronoi: bright membranes between drifting
        // nuclei, each cell keeping its own slow hue.
        vec2 q = warp(p, 0.0) * (8.0 / k_size());
        vec2 g = floor(q), f = fract(q);
        float d1 = 8.0, d2 = 8.0;
        vec2 best = vec2(0.0);
        for (int yy = -1; yy <= 1; yy++)
        for (int xx = -1; xx <= 1; xx++) {
            vec2 o = vec2(float(xx), float(yy));
            vec2 n = hash22(g + o);
            vec2 site = o + 0.5
                      + 0.38 * sin(t * 1.5 + n * TAU + face_rad(fid, 1.0)) - f;
            float d = dot(site, site);
            if (d < d1) { d2 = d1; d1 = d; best = g + o; }
            else if (d < d2) { d2 = d; }
        }
        float wall = 1.0 - smoothstep(0.0, 0.10 * k_edge(), d2 - d1);
        vec3 col = hsv(fract(hash21(best) * m_colour() + t * 0.02 + face_turn(fid, 0.05)), 0.85, 1.0);
        return vec4(mix(col, vec3(1.0), wall * 0.8), 0.45 + 0.55 * wall);
    }
    if (mode == 9) {
        // PLASMA — the classic folded sin-field on the full hue wheel.
        vec2 q = warp(p, 0.0) * (7.0 / k_size());
        float s = sin(q.x + t) + sin(q.y + t * 0.7)
                + sin(q.x + q.y + t * 1.3)
                + sin(length(q) * 2.0 - t * 2.0 + face_rad(fid, 1.0));
        vec3 col = hsv(fract(s * 0.15 * m_colour() + t * 0.02), 0.75, 1.0);
        return vec4(col, 0.1 + 0.9 * sharpen(0.5 + 0.5 * sin(s * TAU * 0.25)));
    }
    if (mode == 10) {
        // WEAVE — warp and weft ribbons interlaced over/under on a
        // checker, every face woven in step.
        vec2 q = warp(p, 0.0) * (10.0 / k_size()) + 0.5;
        vec2 cell = floor(q);
        vec2 f = fract(q) - 0.5;
        float tf = t + face_k1(fid) * TAU;
        float bend = 0.08 * m_warp();                 // the ribbons' own wobble
        float wdt = (0.30 + 0.08 * sin(tf + 2.0)) * pow(k_sharp(), -0.25);
        float e = 0.06 * k_edge();
        float wx = smoothstep(wdt, wdt - e, abs(f.y + bend * sin(q.x * 2.0 + tf)));
        float wy = smoothstep(wdt, wdt - e, abs(f.x + bend * sin(q.y * 2.0 - tf)));
        float over = mod(cell.x + cell.y, 2.0);   // who crosses on top here
        float hx = wx * (0.55 + 0.45 * over);
        float hy = wy * (1.00 - 0.45 * over);
        vec3 cw = vec3(1.0, 0.45, 0.20) * (0.6 + 0.4 * sin(cell.y * 0.7 + tf * 0.5));
        vec3 cv = vec3(0.20, 0.60, 1.0) * (0.6 + 0.4 * sin(cell.x * 0.7 - tf * 0.4));
        vec3 col = spread_hue((cw * hx + cv * hy) / max(hx + hy, 1e-3),
                              sin(cell.x * 1.3 + cell.y * 0.8));
        return vec4(col, max(hx, hy));
    }
    if (mode == 11) {
        // EMBER — coals breathing under ash: four-octave value noise rising
        // slowly, blowing white-hot where it peaks.
        vec2 q = warp(p, 0.0) * (6.0 / k_size()) + vec2(0.0, -t * 0.5)
               + face_gold(fid) * vec2(7.3, 5.1);
        float nse = 0.0, amp = 0.55;
        for (int i = 0; i < 4; i++) {
            nse += amp * vnoise(q);
            q = q * 2.03 + 11.7;
            amp *= 0.5;
        }
        float heat = pow(clamp(nse + 0.10, 0.0, 1.2), 1.1 * k_sharp());
        vec3 col = mix(vec3(0.10, 0.01, 0.0), vec3(1.0, 0.35, 0.05),
                       clamp(heat * 1.4, 0.0, 1.0));
        col = mix(col, vec3(1.0, 0.95, 0.60),
                  clamp(heat * heat * 1.2 - 0.35, 0.0, 1.0));
        return vec4(spread_hue(col, 2.0 * clamp(heat, 0.0, 1.0) - 1.0), clamp(heat, 0.0, 1.0));
    }
    if (mode == 12) return meter(p, t, fid);
    if (mode == 13) return pulse(p, t, fid);
    if (mode == 14) return marble(p, t, fid);
    if (mode == 15) return truchet(p, t, fid);
    if (mode == 16) return kaleido(p, t, fid);
    return vec4(1.0);
}

vec4 pattern(int mode, vec2 uv, float fid) {
    if (mode == 0)
        return vec4(1.0);                    // FLAT — plain white fill
    return finish(design(mode, uv, fid));
}
