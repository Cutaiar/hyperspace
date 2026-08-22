// Hyperspace face patterns — EDIT THIS FILE WHILE THE APP RUNS.
// It hot-reloads on save; a compile error keeps the last good version and
// shows the message in the panel.
//
// Contract: float pattern(int mode, vec2 uv, float fid) returns intensity
// in [0, 1]; it multiplies the face fill alpha. Available uniforms:
//   u_time      seconds since launch
//   u_bands[6]  the chain's fader outputs: SUB BASS MIDB MID UPR AIR
//               (0..~2.6, 1.0 is nominal; all 1.0 when no audio source)
//   fid         face index within the shape — vary phase per face with it
// uv is face-local: (0.5, 0.5) is the face centre, circumradius 0.5,
// identical framing on every congruent face.
//
// Add a case, bump PATTERN_COUNT, and list the name in ui.py's PATTERNS.

const float TAU = 6.28318530718;

float pattern(int mode, vec2 uv, float fid) {
    vec2 p = uv - 0.5;                       // centred face coordinates
    float r = length(p);
    float th = atan(p.y, p.x);
    float t = u_time;

    if (mode == 1) {
        // RINGS — two ring sources beating against each other; SUB widens
        // the spacing, BASS drives the beat rate.
        float f = 18.0 + 10.0 * u_bands[0];
        float a = sin(r * f * TAU * 0.5 - t * (1.0 + 2.0 * u_bands[1]));
        float b = sin(r * f * TAU * 0.31 + t * 1.7 + fid * 0.7);
        return 0.5 + 0.5 * a * b;            // product = constructive/destructive
    }
    if (mode == 2) {
        // PLAID — crossed travelling waves; MIDB and MID set the two axes.
        float a = sin((p.x * (10.0 + 6.0 * u_bands[2])) * TAU + t);
        float b = sin((p.y * (10.0 + 6.0 * u_bands[3])) * TAU - t * 1.3);
        return 0.5 + 0.5 * a * b;
    }
    if (mode == 3) {
        // MOIRE — two stripe fields at a slowly opening angle; the
        // interference pattern is the point, so keep frequencies close.
        float ang = 0.15 * sin(t * 0.23) + fid * 0.05;
        vec2 q = mat2(cos(ang), -sin(ang), sin(ang), cos(ang)) * p;
        float a = sin(p.x * 40.0 * TAU * 0.25);
        float b = sin(q.x * 40.0 * TAU * 0.24);
        return 0.5 + 0.5 * a * b;
    }
    if (mode == 4) {
        // BLOOM — angular harmonics on a ring; UPR sharpens the petals,
        // AIR spins them.
        float n = floor(3.0 + 4.0 * min(u_bands[4], 1.5));
        float petals = cos(th * n + t * (0.4 + u_bands[5]));
        float ring = exp(-abs(r - 0.30) * 9.0);
        return clamp(0.5 + 0.5 * petals, 0.0, 1.0) * ring * 1.6;
    }
    if (mode == 5) {
        // CAUSTIC — three travelling waves summed then folded; loud bands
        // push it toward hard bright filaments.
        float s = sin(p.x * 21.0 + t * 1.1)
                + sin((p.x * 0.5 + p.y * 0.87) * 23.0 - t * 0.9)
                + sin((p.x * 0.5 - p.y * 0.87) * 19.0 + t * 1.3 + fid);
        float v = pow(abs(s) / 3.0, 2.0 + 2.0 * u_bands[1]);
        return clamp(1.0 - v, 0.0, 1.0);
    }
    return 1.0;                              // mode 0: FLAT — plain fill
}
