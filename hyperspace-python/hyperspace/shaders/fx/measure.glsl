// @label Measure
// @order 11
// @family field
// @makes field
// @takes image none
// @tip A field: a number at every pixel, counted across the frame — the distance along
// @tip a line, the distance from a point (rings), the angle round it (spokes), a cell's
// @tip number on a grid, or noise. It draws nothing itself: wire it into a node that
// @tip reads a field (Displace's field port) to say where that node acts and how much.
// @tip Out direction gives the way the count grows instead, a vector field.

// plan 67 F1: the first field generator, `_lib.glsl`'s measures as a node.
// A scalar field is in units of Scale: the line and rings in frame heights
// × Scale, spokes in turns × Scale, cells by their rule, noise about −1 … 1
uniform int u_along;     // @param choice [line|rings|spokes|cells|noise] 0 "Along" What is counted: the distance along the angle, the distance from the point, the angle round it, a cell's number by its rule, or noise.
uniform int u_out;       // @param choice [value|direction] 0 "Out" Value: the count, a scalar field. Direction: the unit way the count grows, a vector field (line, rings, spokes).
uniform float u_scale;   // @param 0.0625 64 1 log "Scale" How fast it counts: line and rings, per frame height; spokes, per turn; cells and noise, cells to a frame height.
uniform float u_angle;   // @param 0 6.2832 0 wrap "Angle" Line: the direction it counts along, radians (0 across, a quarter turn up).
uniform int u_rule;      // @param choice [rows|columns|diagonal|rings|random] 0 "Rule" Cells: how the number runs over the grid.
uniform float u_spread;  // @param 0 1 1 "Spread" Cells: how far one cell's number is from the next along the rule (random: 1 is thoroughly shuffled).
uniform float u_cx;      // @param -1 1 0 "Centre X" The point the count starts at: −1 the left edge … +1 the right.
uniform float u_cy;      // @param -1 1 0 "Centre Y" The point the count starts at: −1 the bottom … +1 the top.

vec4 effect(vec2 uv) {
    vec2 p = from_point(uv, u_cx, u_cy);
    Measure m;
    if (u_along == 1) m = measure_rings(p);
    else if (u_along == 2) m = measure_spokes(p);
    else if (u_along == 0) m = measure_line(p, u_angle);
    else if (u_along == 3) {
        vec2 id = floor(p * u_scale + 0.5);          // a cell sits on the point
        m = Measure(measure_cells(id, u_rule, u_spread), vec2(0.0));
        return u_out == 1 ? as_vector(m.g) : as_scalar(m.x);
    } else {
        m = Measure(perlin(p * u_scale) * 2.0, vec2(0.0));
        return u_out == 1 ? as_vector(m.g) : as_scalar(m.x);
    }
    return u_out == 1 ? as_vector(m.g) : as_scalar(m.x * u_scale);
}
