// @label Wave
// @order 27
// @blend mix
// @speed 1
// @clock u_drift_t drift 4096
// @tip A waveform laid across the frame, pushing the picture where it is high and pulling
// @tip it where it is low. Along says what the wave is counted over: a straight line, the
// @tip distance from a centre (rings) or the angle round it (spokes). Push says which way
// @tip it moves the pixels: slide carries them sideways to the wave's travel — rows
// @tip slipping past each other, rings twisting — and squeeze carries them along it, so
// @tip the picture bunches up and stretches out like a spring. Shape is the waveform;
// @tip Steps flattens it into slabs. Wobble is two fixed sines; this is one wave you aim.
// @pair u_cx u_cy "Centre"

uniform float u_amount; // @param 0 0.5 0.03 amount "Amount" How far the crest pushes, in frame heights.
uniform float u_waves;  // @param 0.25 64 3 log "Waves" Waves in one frame height (spokes: waves in one turn, to the nearest whole one).
uniform int u_along;    // @param choice [line|rings|spokes] 0 "Along" What the wave is counted over: distance along the angle, distance from the centre, or the angle round the centre.
uniform int u_push;     // @param choice [slide|squeeze] 0 "Push" Slide: sideways to the wave's travel (a shear). Squeeze: along it (bunching and stretching).
uniform int u_shape;    // @param choice [sine|triangle|square|saw|noise] 0 "Shape" The waveform. Square and saw have an edge, so they cut the picture; noise is a new random level each wave.
uniform int u_steps;    // @param 0 16 0 "Steps" Levels each side of rest the wave is flattened to, so a smooth wave becomes slabs. 0 leaves it smooth.
uniform float u_angle;  // @param 0 6.2832 1.5708 wrap "Angle" Line: the way the wave travels, radians (a quarter turn is up the frame, so rows slide sideways).
uniform float u_drift;  // @param 0 8 0.5 "Drift" Waves passing a second.
uniform float u_split;  // @param 0 1 0 "Split" Parts the colours along the push: red moves this much further, blue this much less.
uniform float u_cx;     // @param -1 1 0 "Centre X" Rings and spokes: the centre, −1 the left edge … +1 the right (frame heights from the middle).
uniform float u_cy;     // @param -1 1 0 "Centre Y" Rings and spokes: the centre, −1 the bottom … +1 the top.

// the measure and the push are _lib.glsl's field pieces (plan 67 P2): a patch of
// measure → waveform → quantise → displace computes this file's field to the bit
vec4 effect(vec2 uv) {
    vec2 p = from_point(uv, u_cx, u_cy);
    float every = 4096.0;   // where the noise repeats
    Measure m;
    if (u_along == 1) {
        m = measure_rings(p);
    } else if (u_along == 2) {
        m = measure_spokes(p);
        every = max(floor(u_waves + 0.5), 1.0);
    } else {
        m = measure_line(p, u_angle);
    }
    vec2 g = m.g;                                   // the way the measure grows
    float x = m.x * (u_along == 2 ? every : u_waves);   // the measure, in waves
    // round a circle the noise repeats every turn, so it has no seam where
    // the angle wraps (the other shapes have period 1 and need nothing)
    float w = u_shape == 4 ? noise1(x - u_drift_t, every) : wave(u_shape, x - u_drift_t);
    w = quantise(w, u_steps);
    vec2 dir = u_push == 0 ? vec2(-g.y, g.x) : g;
    return pushed(uv, dir * w * u_amount, u_split);
}
