// Hyperspace face patterns — EDIT THIS FILE WHILE THE APP RUNS.
// It hot-reloads on save; a compile error keeps the last good version and
// shows the message in the panel.
//
// Contract: vec4 pattern(int mode, vec2 uv, float fid)
//   .rgb  face colour (full colour space — blended over the black ground)
//   .a    intensity in [0, 1]; multiplies the face fill alpha
// Available uniforms:
//   u_time      seconds since launch
//   u_mod[8]    the pattern's modulation inputs — pattern.mod.0–7 in the
//               registry (0..2.6, base 1.0 = the un-driven look). What
//               drives them is the routing table (routing.py): the
//               factory "legacy6" routes put analyzer lane i on u_mod[i],
//               so with the six reference bands 0–5 read SUB BASS MIDB MID
//               UPR AIR — but any lane, LFO or MIDI lane can be routed to
//               any of the eight, and the comments below name the legacy
//               band each pattern was written against.
//   fid         face index within the shape — vary phase per face with it
// uv is face-local: (0.5, 0.5) is the face centre, circumradius 0.5,
// identical framing on every congruent face.
//
// TAU, hsv(h, s, v), pal(t, a, b, c, d), hue_rotate and LUMA come from
// shaders/_common.glsl, prepended to this file (and to every effect).
// Add a case below, and list the name in params.py's PATTERNS.

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

vec4 pattern(int mode, vec2 uv, float fid) {
    vec2 p = uv - 0.5;                       // centred face coordinates
    float r = length(p);
    float th = atan(p.y, p.x);
    float t = u_time;

    if (mode == 1) {
        // RINGS — two ring sources beating; hue rides the ring phase, SUB
        // widens spacing, BASS drives the beat rate.
        float f = 18.0 + 10.0 * u_mod[0];
        float ph = r * f - t * (1.0 + 2.0 * u_mod[1]) / TAU;
        float a = sin(ph * TAU * 0.5);
        float b = sin(r * f * TAU * 0.31 + t * 1.7 + fid * 0.7);
        float v = 0.5 + 0.5 * a * b;
        vec3 col = pal(ph * 0.15 + fid * 0.03,
                       vec3(0.55), vec3(0.45), vec3(1.0), vec3(0.0, 0.33, 0.67));
        return vec4(col, v);
    }
    if (mode == 2) {
        // PLAID — two coloured wave systems crossing; where they agree the
        // colours add (constructive), where they cancel the face goes dark.
        float a = sin((p.x * (10.0 + 6.0 * u_mod[2])) * TAU + t);
        float b = sin((p.y * (10.0 + 6.0 * u_mod[3])) * TAU - t * 1.3);
        vec3 ca = vec3(1.0, 0.25, 0.35) * (0.5 + 0.5 * a);   // warm axis
        vec3 cb = vec3(0.15, 0.55, 1.0) * (0.5 + 0.5 * b);   // cool axis
        vec3 col = ca + cb;
        return vec4(col / max(max(col.r, col.g), max(col.b, 1.0)),
                    0.5 + 0.5 * a * b);
    }
    if (mode == 3) {
        // MOIRE — near-frequency stripe fields; the interference envelope
        // sweeps a slow duotone between teal and magenta.
        float ang = 0.15 * sin(t * 0.23) + fid * 0.05;
        vec2 q = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * p;
        float a = sin(p.x * 40.0 * TAU * 0.25);
        float b = sin(q.x * 40.0 * TAU * 0.24);
        float v = 0.5 + 0.5 * a * b;
        vec3 col = mix(vec3(0.10, 0.85, 0.75), vec3(0.90, 0.20, 0.80),
                       0.5 + 0.5 * sin(p.x * 3.0 + t * 0.4));
        return vec4(col, v);
    }
    if (mode == 4) {
        // BLOOM — petals hue-rotate with AIR; UPR adds petals.
        float n = floor(3.0 + 4.0 * min(u_mod[4], 1.5));
        float petals = cos(th * n + t * (0.4 + u_mod[5]));
        float ring = exp(-abs(r - 0.30) * 9.0);
        float v = clamp(0.5 + 0.5 * petals, 0.0, 1.0) * ring * 1.6;
        vec3 col = hsv(fract(th / TAU + t * 0.05 + fid * 0.02),
                       0.8, 1.0);
        return vec4(col, v);
    }
    if (mode == 5) {
        // CAUSTIC — deep-water palette: dark blue troughs, bright cyan-white
        // filaments; loud BASS hardens the filaments.
        float s = sin(p.x * 21.0 + t * 1.1)
                + sin((p.x * 0.5 + p.y * 0.87) * 23.0 - t * 0.9)
                + sin((p.x * 0.5 - p.y * 0.87) * 19.0 + t * 1.3 + fid);
        float v = clamp(1.0 - pow(abs(s) / 3.0, 2.0 + 2.0 * u_mod[1]), 0.0, 1.0);
        vec3 col = mix(vec3(0.02, 0.10, 0.35), vec3(0.55, 0.95, 1.0), v * v);
        return vec4(col, v);
    }
    if (mode == 6) {
        // HEX — honeycomb lattice, every cell firing on its own phase.
        // MIDB packs the cells tighter, AIR speeds the shimmer.
        float scale = 6.0 + 4.0 * u_mod[2];
        vec2 q = p * scale;
        vec2 rep = vec2(1.0, 1.7320508);
        vec2 ha = mod(q, rep) - rep * 0.5;
        vec2 hb = mod(q - rep * 0.5, rep) - rep * 0.5;
        vec2 gv = dot(ha, ha) < dot(hb, hb) ? ha : hb;
        vec2 id = q - gv;
        float pulse = 0.5 + 0.5 * sin(t * (1.0 + 2.0 * u_mod[5])
                                      + hash21(id) * TAU + fid);
        float cell = smoothstep(0.50, 0.40, length(gv));
        vec3 col = hsv(fract(hash21(id + 7.31) + t * 0.03), 0.7, 1.0);
        return vec4(col, cell * (0.25 + 0.75 * pulse));
    }
    if (mode == 7) {
        // SPIRAL — galaxy arms winding out of a hot core; MID adds arms,
        // BASS tightens the twist, colour runs outward along each arm.
        float arms = floor(2.0 + 3.0 * min(u_mod[3], 1.5));
        float twist = 5.0 + 3.0 * u_mod[1];
        float ph = th * arms + log(max(r, 1e-4)) * twist
                 - t * (0.8 + u_mod[3]) + fid * 0.5;
        float arm = pow(0.5 + 0.5 * cos(ph), 2.0);
        float core = exp(-r * 5.0);
        vec3 col = pal(r * 1.5 - t * 0.05,
                       vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.85, 0.60, 0.30));
        return vec4(col + core,
                    clamp(arm * smoothstep(0.55, 0.15, r) + core, 0.0, 1.0));
    }
    if (mode == 8) {
        // CELLS — living voronoi: bright membranes between drifting nuclei.
        // UPR agitates the drift, each cell keeps its own slow hue.
        vec2 q = p * (5.0 + 3.0 * u_mod[2]);
        vec2 g = floor(q), f = fract(q);
        float d1 = 8.0, d2 = 8.0;
        vec2 best = vec2(0.0);
        for (int yy = -1; yy <= 1; yy++)
        for (int xx = -1; xx <= 1; xx++) {
            vec2 o = vec2(float(xx), float(yy));
            vec2 n = hash22(g + o);
            vec2 site = o + 0.5
                      + 0.38 * sin(t * (0.5 + u_mod[4]) + n * TAU + fid) - f;
            float d = dot(site, site);
            if (d < d1) { d2 = d1; d1 = d; best = g + o; }
            else if (d < d2) { d2 = d; }
        }
        float wall = 1.0 - smoothstep(0.0, 0.10, d2 - d1);
        vec3 col = hsv(fract(hash21(best) + t * 0.02 + fid * 0.05), 0.85, 1.0);
        return vec4(mix(col, vec3(1.0), wall * 0.8), 0.45 + 0.55 * wall);
    }
    if (mode == 9) {
        // PLASMA — the classic folded sin-field on the full hue wheel;
        // MID zooms the folds, SUB rolls the radial term.
        vec2 q = p * (5.0 + 2.0 * u_mod[3]);
        float s = sin(q.x + t) + sin(q.y + t * 0.7)
                + sin(q.x + q.y + t * 1.3)
                + sin(length(q) * 2.0 - t * (1.0 + u_mod[0]) + fid);
        vec3 col = hsv(fract(s * 0.15 + t * 0.02), 0.75, 1.0);
        return vec4(col, 0.55 + 0.45 * sin(s * TAU * 0.25));
    }
    if (mode == 10) {
        // WEAVE — warp and weft ribbons interlaced over/under on a checker;
        // MIDB adds threads, BASS breathes the ribbon width.
        float n = 6.0 + 4.0 * u_mod[2];
        vec2 q = p * n + 0.5;
        vec2 cell = floor(q);
        vec2 f = fract(q) - 0.5;
        float wdt = 0.30 + 0.08 * sin(t + 2.0 * u_mod[1]);
        float wx = smoothstep(wdt, wdt - 0.06,
                              abs(f.y + 0.08 * sin(q.x * 2.0 + t)));
        float wy = smoothstep(wdt, wdt - 0.06,
                              abs(f.x + 0.08 * sin(q.y * 2.0 - t)));
        float over = mod(cell.x + cell.y, 2.0);   // who crosses on top here
        float hx = wx * (0.55 + 0.45 * over);
        float hy = wy * (1.00 - 0.45 * over);
        vec3 cw = vec3(1.0, 0.45, 0.20) * (0.6 + 0.4 * sin(cell.y * 0.7 + t * 0.5));
        vec3 cv = vec3(0.20, 0.60, 1.0) * (0.6 + 0.4 * sin(cell.x * 0.7 - t * 0.4));
        vec3 col = (cw * hx + cv * hy) / max(hx + hy, 1e-3);
        return vec4(col, max(hx, hy));
    }
    if (mode == 11) {
        // EMBER — coals breathing under ash: four-octave value noise rising
        // slowly; BASS banks the heat, SUB blows patches white-hot.
        vec2 q = p * 6.0 + vec2(0.0, -t * 0.5) + fid;
        float nse = 0.0, amp = 0.55;
        for (int i = 0; i < 4; i++) {
            nse += amp * vnoise(q);
            q = q * 2.03 + 11.7;
            amp *= 0.5;
        }
        float heat = pow(clamp(nse + 0.35 * u_mod[1] - 0.25, 0.0, 1.2),
                         1.8 - 0.7 * min(u_mod[0], 1.0));
        vec3 col = mix(vec3(0.10, 0.01, 0.0), vec3(1.0, 0.35, 0.05),
                       clamp(heat * 1.4, 0.0, 1.0));
        col = mix(col, vec3(1.0, 0.95, 0.60),
                  clamp(heat * heat * 1.2 - 0.35, 0.0, 1.0));
        return vec4(col, clamp(heat, 0.0, 1.0));
    }
    return vec4(1.0);                        // mode 0: FLAT — plain white fill
}
