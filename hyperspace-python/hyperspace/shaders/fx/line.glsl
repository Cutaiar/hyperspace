// @label Line
// @order 18
// @family field
// @makes field
// @takes image none
// @takes field field
// @tip A field: at every pixel, how far along a line it is — a ramp across the frame at
// @tip Angle, 0 through the point (a Point on its field port; the middle with none).
// @tip Out direction gives the way it grows, a vector field; across, that way turned a
// @tip quarter turn. Wire it into Displace for a shear, or a Waveform for rows.

// Measure's line, on its own (`_lib.glsl`'s `measure_line`)
uniform float u_scale;  // @param 0.0625 64 1 log "Scale" How fast it counts: units per frame height.
uniform float u_angle;  // @param 0 6.2832 0 wrap "Angle" The direction it counts along, radians (0 across, a quarter turn up).
uniform int u_out;      // @param choice [value|direction|across] 0 "Out" Value: the distance along, a scalar field. Direction: the way it grows, a vector. Across: that way turned a quarter turn anticlockwise.

vec4 effect(vec2 uv) { return measure_out(measure_line(from_field_point(uv), u_angle), u_out, u_scale); }
