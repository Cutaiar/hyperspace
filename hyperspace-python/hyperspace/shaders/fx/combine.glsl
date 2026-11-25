// @label Combine
// @order 14
// @family field
// @makes field
// @takes image field
// @takes field field
// @tip Two fields made one: added, multiplied, the lesser or the greater, pixel by pixel.
// @tip The first comes into its input, the second into its field port. A direction
// @tip (a vector field) times a value (a scalar one) is that direction scaled: how a
// @tip waveform says how far to push and a measure says which way.

// plan 67: the `combine` op (the modifiers' name) on fields. Scalar with
// scalar is a scalar; with a vector, each of its components takes the scalar;
// two vectors combine component by component
uniform int u_how;      // @param choice [add|multiply|min|max] 1 "How" Added, multiplied, the lesser of the two, or the greater.

vec2 both(vec2 a, vec2 b) {
    if (u_how == 1) return a * b;
    if (u_how == 2) return min(a, b);
    if (u_how == 3) return max(a, b);
    return a + b;
}

vec4 effect(vec2 uv) {
    vec4 a = field_in(uv), b = field_port(uv);
    bool av = a.a > 0.5, bv = b.a > 0.5;
    if (!av && !bv) return as_scalar(combine(a.x, b.x, u_how));
    if (av && !bv) return as_vector(u_how == 1 ? a.xy * b.x : both(a.xy, vec2(b.x)));
    if (!av) return as_vector(u_how == 1 ? b.xy * a.x : both(vec2(a.x), b.xy));
    return as_vector(both(a.xy, b.xy));
}
