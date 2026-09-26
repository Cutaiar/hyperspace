// @label Kaleidoscope
// @order 15
// @blend mix
// @speed 0.2
// @tip The frame folded into mirrored wedges about the centre, slowly turning — the
// @tip trip's mandala. Zoom pulls the fold in so more of the scene lands in a wedge.

uniform int u_segments;  // @param 2 16 6 "Segments" Mirrored wedges around the circle.
uniform float u_zoom;    // @param 0.25 4 1 log "Zoom" Below 1 each wedge sees more of the frame.
uniform float u_swirl;   // @param -2 2 0 "Swirl" Twist that grows with the radius, radians.

vec4 effect(vec2 uv) {
    vec2 p = centred(uv) * u_zoom;
    float r = length(p);
    float a = atan(p.y, p.x) + u_phase + u_swirl * r;
    float w = TAU / float(u_segments);
    a = mod(a, w);
    a = abs(a - 0.5 * w);                 // mirror within the wedge
    return src(uncentred(r * vec2(cos(a), sin(a))));
}
