// @label Displace
// @order 22
// @blend mix
// @tip Moves the frame's pixels by a second picture wired into its aux input (a media
// @tip channel, the scene, the history): by the aux's brightness along an angle, or by
// @tip its red and green as x and y. Mid-grey moves nothing; nothing wired moves nothing.
// @tip A field wired into its field port moves them instead: a vector field by its pair,
// @tip a scalar one along the angle (Measure, To field).
// @takes field field

// plan 32 R (row 332). The aux is premultiplied, so the offset is taken
// about half its alpha: a see-through aux pixel (and an unwired aux, all
// transparent black) is no slope at all
uniform float u_amount;  // @param 0 0.5 0.02 amount "Amount" How far the brightest and darkest of the aux push, in frame heights.
uniform int   u_mode;    // @param choice [luma|red/green] 0 "Mode" Luma pushes along the angle by the aux's brightness; red/green pushes x by its red and y by its green.
uniform float u_angle;   // @param 0 6.2832 0 "Angle" Luma mode, or a scalar field on the field port: the direction a bright aux or a positive field pushes, radians (0 right, a quarter turn up).
uniform float u_split;   // @param 0 1 0 "Split" Parts the colours along the push: red moves this much further, blue this much less (as Wave's and Blocks').

vec4 effect(vec2 uv) {
    // plan 67 F1: a field on the field port is the offset, frame heights per
    // unit; the aux is read only while none is wired
    if (u_field_on != 0)
        return pushed(uv, field_vector(field_port(uv), u_angle) * u_amount, u_split);
    vec4 a = aux(uv);
    // the aux read as a field about mid-grey, and the push, are _lib.glsl's
    // (plan 67 P2): `read_signed`, `pushed` (frame heights, x with the aspect)
    vec2 d = u_mode == 0
        ? read_signed(luma(a.rgb), a.a) * vec2(cos(u_angle), sin(u_angle))
        : read_signed(a.rg, a.a);
    return pushed(uv, d * u_amount, u_split);
}
