// @label Fade
// @order 94
// @blend mix
// @tip Multiplies the whole picture by Level, colour and alpha alike, so a see-through
// @tip pixel fades towards clear and never towards black. At 1 the picture is untouched.
// @tip The decay of a feedback loop: the feedback starter sets 0.75, how much of last
// @tip frame stays.

// wave 0 E1 (2026-11-02): the one node that scales premultiplied colour as a
// whole. A palette's val slice darkens rgb and keeps alpha, so a trail fed
// through it fades to opaque black (a ghost over a backdrop or the desktop)
// and a half-covered fringe decays faster than the face it edges; this
// scales the vec4, so a trail fades to clear at one rate everywhere.
uniform float u_level;  // @param 0 1 1 "Level" How much of the picture stays: 1 all of it, 0.75 three quarters (a feedback loop's decay), 0 nothing.

vec4 effect(vec2 uv) {
    return src(uv) * u_level;
}
