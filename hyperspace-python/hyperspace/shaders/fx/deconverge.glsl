// @label Deconverge
// @order 40
// @blend mix
// @speed 0.3
// @tip Minecraft's "deconverge" (Super Secret Settings): red, green and blue each sampled
// @tip from their own offset and scale about the centre, so edges split into rainbow
// @tip fringes. Speed turns the split directions around.

uniform float u_amount;  // @param 0 16 3 "Amount" The split, px (Minecraft: about 1).
uniform float u_radial;  // @param 0 0.05 0.006 "Radial" Each channel's own zoom about the centre, so the fringes widen to the rim.

vec4 effect(vec2 uv) {
    mat2 r = rot(u_phase);
    vec2 px = u_amount / u_res;
    // Minecraft's channel offsets in texels: R (−1, 0), G (0, −1), B (0.5, 0.5)
    vec2 c = uv - 0.5;
    vec4 R = src(c * (1.0 + u_radial) + 0.5 + r * vec2(-1.0, 0.0) * px);
    vec4 G = src(c + 0.5 + r * vec2(0.0, -1.0) * px);
    vec4 B = src(c * (1.0 - u_radial) + 0.5 + r * vec2(0.5, 0.5) * px);
    return vec4(R.r, G.g, B.b, max(R.a, max(G.a, B.a)));
}
