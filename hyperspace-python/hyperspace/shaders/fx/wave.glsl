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

vec4 effect(vec2 uv) {
    vec2 p = centred(uv) - vec2(u_cx * 0.5 * u_res.x / u_res.y, u_cy * 0.5);
    float r = length(p);
    vec2 out_ = r > 1e-5 ? p / r : vec2(0.0);
    vec2 g;          // the way the measure grows
    float x;         // the measure, in waves
    if (u_along == 1) {
        g = out_;
        x = r * u_waves;
    } else if (u_along == 2) {
        g = vec2(-out_.y, out_.x);
        x = atan(p.y, p.x) / TAU * max(floor(u_waves + 0.5), 1.0);
    } else {
        g = vec2(cos(u_angle), sin(u_angle));
        x = dot(p, g) * u_waves;
    }
    float w = wave(u_shape, x - u_drift_t);
    if (u_steps > 0) w = floor(w * float(u_steps) + 0.5) / float(u_steps);
    vec2 dir = u_push == 0 ? vec2(-g.y, g.x) : g;
    return pushed(uv, dir * w * u_amount, u_split);
}
