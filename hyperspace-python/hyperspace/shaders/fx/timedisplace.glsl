// @label Time Displace
// @order 21
// @blend mix
// @speed 1
// @hook timedisplace
// @clock u_drift_t drift 4096
// @tip Each pixel shows the picture as it was a moment ago, and how long ago is a field
// @tip laid over the frame: a ramp across it (line) is the slit-scan, one edge now and the
// @tip other Span seconds back; rings run from a centre out, spokes round it, flat puts
// @tip every pixel at Span ago (an echo), and aux reads the brightness of a picture wired
// @tip into its aux (black now, white Span ago). The past is a look-back's frames: that
// @tip look-back's capture must be wired, or it shows its input. At Span 0 it is its input.

// plan 66 stage 3a. The Python half (`timedisplace.py`) binds the look-back's
// atlas and, newest first, every frame it holds: its slot and its age in
// seconds. The ring holds 32 frames, one every `dream.gap` seconds (1/30 s by
// default: about a second), so a Span longer than that reads the oldest frame
uniform float u_span;    // @param 0 8 1 amount "Span" How far back the field's whole value reaches, in seconds. The look-back holds 32 of its frames, one every Echo time apart: raise that to reach further.
uniform int u_shape;     // @param choice [line|rings|spokes|flat|aux] 0 "Field" How long ago each pixel shows: a ramp across the frame along the angle, rings from the centre, spokes round it, every pixel the same (an echo), or the aux picture's brightness.
uniform float u_angle;   // @param 0 6.2832 0 wrap "Angle" Line: the way time runs, radians (0: now at the left edge, the past at the right).
uniform int u_repeat;    // @param 1 16 1 "Repeat" The ramp laid that many times across (spokes: that many times round).
uniform float u_drift;   // @param 0 4 0 "Drift" The ramp sweeping on, repeats a second.
uniform int u_steps;     // @param 0 32 0 "Steps" The field flattened into that many steps past now: bands. 0 leaves it smooth.
uniform int u_flip;      // @param choice [off|on] 0 "Flip" The field turned end for end: the far edge, the rim or the dark of the aux becomes now.
uniform int u_between;   // @param choice [blend|nearest] 0 "Between" A time between two of the look-back's frames: both blended by time, or the nearer one alone (hard bands).
uniform int u_ring;      // @param 1 8 1 "Look-back" Which look-back's frames it reads: 1 the first, 2 the look-back named lookback.2, and so on.
uniform float u_cx;      // @param -1 1 0 "Centre X" Rings and spokes: the centre, −1 the left edge … +1 the right.
uniform float u_cy;      // @param -1 1 0 "Centre Y" Rings and spokes: the centre, −1 the bottom … +1 the top.

// set by the Python half, never a knob
uniform sampler2D u_ring_tex;   // the look-back's atlas: 32 slots stacked in v
uniform int u_ring_n;           // its frames held, 0 while it holds none
uniform float u_ring_age[32];   // newest first: each frame's age, seconds
uniform float u_ring_off[32];   // …and its slot's origin in atlas v
uniform float u_ring_slot;      // one slot's height in atlas v
uniform float u_ring_pad;       // half a texel of a slot, in its own v: no slot bleeds

// how long ago this pixel shows, as a share of Span, 0 … 1
float when(vec2 uv) {
    if (u_shape == 3) return u_flip == 1 ? 0.0 : 1.0;
    vec2 p = centred(uv);
    float asp = u_res.x / u_res.y;
    float x;
    if (u_shape == 4) {
        x = aux_luma(uv);
    } else if (u_shape == 0) {
        Measure m = measure_line(p, u_angle);
        // the frame's extent along it, so the ramp spans it edge to edge
        x = m.x / (abs(m.g.x) * asp + abs(m.g.y)) + 0.5;
    } else {
        vec2 q = from_point(uv, u_cx, u_cy);
        x = u_shape == 1 ? measure_rings(q).x / (0.5 * sqrt(asp * asp + 1.0))
                         : measure_spokes(q).x + 0.5;
    }
    x = clamp(x, 0.0, 0.99999);
    float f = fract(x * float(u_repeat) - u_drift_t);
    if (u_flip == 1) f = 1.0 - f;
    f = quantise(f, u_steps);
    return f;
}

// the look-back's k-th newest frame at uv
vec4 past(int k, vec2 uv) {
    float y = clamp(uv.y, u_ring_pad, 1.0 - u_ring_pad) * u_ring_slot;
    return texture(u_ring_tex, vec2(uv.x, u_ring_off[k] + y));
}

vec4 effect(vec2 uv) {
    vec4 now = src(uv);
    float a = when(uv) * u_span;
    if (u_ring_n == 0 || a <= 0.0) return now;
    float a0 = u_ring_age[0];
    if (a < a0) {        // between this picture and the look-back's newest frame
        float t = a / a0;
        if (u_between == 1) return t < 0.5 ? now : past(0, uv);
        return mix(now, past(0, uv), t);
    }
    for (int k = 0; k < 31; k++) {
        if (k + 1 >= u_ring_n) break;
        float b1 = u_ring_age[k + 1];
        if (a < b1) {
            float b0 = u_ring_age[k];
            float t = (a - b0) / max(b1 - b0, 1e-6);
            if (u_between == 1) return past(t < 0.5 ? k : k + 1, uv);
            return mix(past(k, uv), past(k + 1, uv), t);
        }
    }
    return past(u_ring_n - 1, uv);   // older than the ring holds: its oldest
}
