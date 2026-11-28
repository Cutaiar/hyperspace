// @label Rings
// @order 19
// @family field
// @makes field
// @takes image none
// @takes field field
// @tip A field: at every pixel, how far it is from the point (a Point on its field port;
// @tip the middle with none) — rings. Out direction gives the way out from the point, a
// @tip vector field (into Displace: a lens); across, the way round it (a swirl).

// Measure's rings, on their own (`_lib.glsl`'s `measure_rings`)
uniform float u_scale;  // @param 0.0625 64 1 log "Scale" How fast it counts: units per frame height out from the point.
uniform int u_out;      // @param choice [value|direction|across] 0 "Out" Value: the distance from the point, a scalar field. Direction: the way out, a vector. Across: the way round, anticlockwise.

vec4 effect(vec2 uv) { return measure_out(measure_rings(from_field_point(uv)), u_out, u_scale); }
