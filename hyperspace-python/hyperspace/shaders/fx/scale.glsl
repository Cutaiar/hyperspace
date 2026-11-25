// @label Scale
// @order 33
// @family field
// @makes field
// @takes image field
// @tip A field multiplied (×) and then added to (+), pixel by pixel — a vector's two
// @tip components alike. The lane modifier of the same name, on a field: turn a field
// @tip down, flip it (× below 0), or lift it.

// plan 67 §3.2: the modifiers' `scale` (× then +) as a field op; a field is
// signed, so there is no clamp
uniform float u_mul;     // @param -4 4 1 "×" Multiplies the field (below 0 it flips).
uniform float u_offset;  // @param -1 1 0 "+" Added after the multiply.

vec4 effect(vec2 uv) {
    // a scalar's value is x (y and z carry what rides with it: a cell's size);
    // a vector's, x and y
    vec4 f = field_in(uv);
    if (f.a > 0.5) return vec4(f.xy * u_mul + vec2(u_offset), f.z, f.a);
    return vec4(f.x * u_mul + u_offset, f.yzw);
}
