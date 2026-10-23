// @label Displace
// @order 22
// @blend mix
// @tip Moves the frame's pixels by a second picture wired into its aux input (a media
// @tip channel, the scene, the history): by the aux's brightness along an angle, or by
// @tip its red and green as x and y. Mid-grey moves nothing; nothing wired moves nothing.

// plan 32 R (row 332). The aux is premultiplied, so the offset is taken
// about half its alpha: a see-through aux pixel (and an unwired aux, all
// transparent black) is no slope at all
uniform float u_amount;  // @param 0 0.5 0.05 "Amount" How far the brightest and darkest of the aux push, in frame heights.
uniform int   u_mode;    // @param choice [luma|red/green] 0 "Mode" Luma pushes along the angle by the aux's brightness; red/green pushes x by its red and y by its green.
uniform float u_angle;   // @param 0 6.2832 0 "Angle" Luma mode: the direction a bright aux pushes, radians (0 right, a quarter turn up).

vec4 effect(vec2 uv) {
    vec4 a = aux(uv);
    vec2 d = u_mode == 0
        ? (luma(a.rgb) - 0.5 * a.a) * 2.0 * vec2(cos(u_angle), sin(u_angle))
        : (a.rg - 0.5 * a.a) * 2.0;
    // frame heights → uv: x runs with the aspect
    return src(uv + d * u_amount * vec2(u_res.y / u_res.x, 1.0));
}
