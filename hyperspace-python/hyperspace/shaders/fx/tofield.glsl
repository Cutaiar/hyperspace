// @label To field
// @order 12
// @family field
// @makes field
// @tip A picture read as a field: its brightness, its brightest channel, or its red and
// @tip green as a pair. Signed reads mid-grey as 0, black as −1 and white as +1 (how
// @tip Displace has always read its aux); unsigned reads black as 0 and white as 1. The
// @tip way to wire a picture into a port that takes a field.

// plan 67 F1: the converter, picture → field (the `picture` piece of the
// kit). A see-through pixel reads 0 signed, as an unwired aux does
uniform int u_read;      // @param choice [luma|peak|red/green] 0 "Read" Brightness (luma), the brightest channel (peak), or red and green as a pair (a vector field).
uniform int u_about;     // @param choice [signed|unsigned] 0 "About" Signed: mid-grey is 0, black −1, white +1. Unsigned: black 0, white 1.

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    if (u_read == 2)
        return as_vector(u_about == 0 ? read_signed(c.rg, c.a) : c.rg);
    float v = u_read == 1 ? peak(c.rgb) : luma(c.rgb);
    return as_scalar(u_about == 0 ? read_signed(v, c.a) : v);
}
