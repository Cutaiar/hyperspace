// @label Trail
// @order 7
// @family past
// @takes image none
// @takes stack stack
// @tip The frames a delay keeps, laid one over another, oldest first, each fainter by its
// @tip age: wire a delay into its stack (its Depth how many, its rate how far apart — a
// @tip tracer's copies). Level is the newest's strength, Fade the seconds in which a
// @tip frame's strength halves. Lay: over (each covers the older where it is) or add.
// @tip Lay it on a picture with a composite.

// The trail as a reader of the stack (a weighted sum over indices): weights
// `level · ½^(age / fade)`, with each frame's own alpha as its coverage —
// black is clear makes that alpha from brightness
uniform float u_level;   // @param 0 1 0.4 "Level" The newest frame's strength; older ones fade from it.
uniform float u_fade;    // @param 0.02 10 0.2252 log "Fade" Seconds in which a frame's strength halves: short, a tight tracer; long, a smear.
uniform int u_lay;       // @param choice [over|add] 0 "Lay" Over: each frame covers the older ones where it is (its alpha). Add: they sum.

vec4 effect(vec2 uv) {
    vec4 wake = vec4(0.0);
    for (int i = u_stack_n - 1; i >= 0; i--) {          // oldest first
        float w = u_level * exp2(-u_stack_age[i] / max(u_fade, 1e-6));
        vec4 c = stack_frame(i, uv) * w;
        wake = u_lay == 1 ? wake + c : wake * (1.0 - c.a) + c;
    }
    return wake;
}
