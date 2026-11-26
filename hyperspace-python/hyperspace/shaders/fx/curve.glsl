// @label Curve
// @order 92
// @blend mix
// @tip Bends every colour channel as a lane's curve bends a value: Shape 0 leaves the
// @tip picture as it is; towards 1 the mid-tones sink and only the bright parts stay
// @tip (x⁴, a contrast that keeps black black); towards −1 they lift (x^¼). Invert turns
// @tip it over: bright for dark, the picture's own alpha kept.

// plan 90 (H1): plan 67 §3.2's remap row in the picture kind, written to the
// lane modifier's name and knobs (`modifiers.PARAMS["curve"]`: shape −1 … 1, an
// exponent of 4^shape, and invert). The look-back's and the dream's contrast,
// `pow(c, contrast)`, is Shape log₄(contrast)
uniform float u_shape;   // @param -1 1 0 "Shape" Bends every channel: 0 straight, up to 1 only the bright parts stay (x⁴), down to −1 lifted (x^¼).
uniform int u_invert;    // @param choice [off|on] 0 "Invert" Turn it over: bright for dark (within the picture's own alpha).

// on straight colour, premultiplied again after (Devin on #519): black stays
// black at any shape, and a see-through pixel stays as see-through
vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    if (c.a <= 0.0) return vec4(0.0);
    vec3 s = clamp(c.rgb / c.a, 0.0, 1.0);
    vec3 y = pow(s, vec3(exp2(2.0 * u_shape)));
    if (u_invert == 1) y = 1.0 - y;
    return vec4(y * c.a, c.a);
}
