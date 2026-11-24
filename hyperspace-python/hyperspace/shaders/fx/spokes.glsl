// @label Spokes
// @order 29
// @family field
// @makes field
// @takes image none
// @takes field field
// @tip A field: at every pixel, its angle round the point (a Point on its field port; the
// @tip middle with none), in turns, −½ … ½ with the seam on the left. Out direction gives
// @tip the way round, a vector field; across, the way out from the point.

// plan 67 §15: Measure's spokes, on their own (`_lib.glsl`'s `measure_spokes`)
uniform float u_scale;  // @param 0.0625 64 1 log "Scale" How fast it counts: units per turn round the point.
uniform int u_out;      // @param choice [value|direction|across] 0 "Out" Value: the angle round, a scalar field. Direction: the way round (anticlockwise), a vector. Across: that way turned a quarter turn.

vec4 effect(vec2 uv) { return measure_out(measure_spokes(from_field_point(uv)), u_out, u_scale); }
