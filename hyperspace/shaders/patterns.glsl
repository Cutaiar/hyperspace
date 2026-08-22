// Hyperspace face patterns — EDIT THIS FILE WHILE THE APP RUNS.
// It hot-reloads on save; a compile error keeps the last good version and
// shows the message in the panel.
//
// Contract: vec4 pattern(int mode, vec2 uv, float fid)
//   .rgb  face colour (full colour space — blended over the black ground)
//   .a    intensity in [0, 1]; multiplies the face fill alpha
// Available uniforms:
//   u_time      seconds since launch
//   u_bands[6]  the chain's fader outputs: SUB BASS MIDB MID UPR AIR
//               (0..~2.6, 1.0 is nominal; all 1.0 when no audio source)
//   fid         face index within the shape — vary phase per face with it
// uv is face-local: (0.5, 0.5) is the face centre, circumradius 0.5,
// identical framing on every congruent face.
//
// Helpers below; add a case, and list the name in ui.py's PATTERNS.

const float TAU = 6.28318530718;

// hue [0,1), saturation, value → rgb
vec3 hsv(float h, float s, float v) {
    vec3 k = mod(vec3(5.0, 3.0, 1.0) + h * 6.0, 6.0);
    return v - v * s * clamp(min(k, 4.0 - k), 0.0, 1.0);
}

// cosine palette: smooth colour cycles without hue banding.
// a = base, b = amplitude, c = frequency, d = per-channel phase.
vec3 pal(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
    return a + b * cos(TAU * (c * t + d));
}

vec4 pattern(int mode, vec2 uv, float fid) {
    vec2 p = uv - 0.5;                       // centred face coordinates
    float r = length(p);
    float th = atan(p.y, p.x);
    float t = u_time;

    if (mode == 1) {
        // RINGS — two ring sources beating; hue rides the ring phase, SUB
        // widens spacing, BASS drives the beat rate.
        float f = 18.0 + 10.0 * u_bands[0];
        float ph = r * f - t * (1.0 + 2.0 * u_bands[1]) / TAU;
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
        float a = sin((p.x * (10.0 + 6.0 * u_bands[2])) * TAU + t);
        float b = sin((p.y * (10.0 + 6.0 * u_bands[3])) * TAU - t * 1.3);
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
        float n = floor(3.0 + 4.0 * min(u_bands[4], 1.5));
        float petals = cos(th * n + t * (0.4 + u_bands[5]));
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
        float v = clamp(1.0 - pow(abs(s) / 3.0, 2.0 + 2.0 * u_bands[1]), 0.0, 1.0);
        vec3 col = mix(vec3(0.02, 0.10, 0.35), vec3(0.55, 0.95, 1.0), v * v);
        return vec4(col, v);
    }
    return vec4(1.0);                        // mode 0: FLAT — plain white fill
}
