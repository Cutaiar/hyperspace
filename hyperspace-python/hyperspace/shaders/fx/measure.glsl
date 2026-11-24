// @label Measure
// @order 11
// @family field
// @makes field
// @takes image none
// @tip A field: a number at every pixel, counted across the frame — the distance along
// @tip a line, the distance from a point (rings), the angle round it (spokes), a cell's
// @tip number on a grid, or noise. It draws nothing itself: wire it into a node that
// @tip reads a field (Displace's field port) to say where that node acts and how much.
// @tip Out direction gives the way the count grows instead, a vector field; across, that
// @tip way turned a quarter turn. For cells, direction is the pixel's place in its cell
// @tip (wired into Displace, every cell zooms).

// plan 67 F1: the first field generator, `_lib.glsl`'s measures as a node.
// A scalar field is in units of Scale: the line and rings in frame heights
// × Scale, spokes in turns × Scale, cells by their rule, noise about −1 … 1
uniform int u_along;     // @param choice [line|rings|spokes|cells|noise] 0 "Along" What is counted: the distance along the angle, the distance from the point, the angle round it, a cell's number by its rule, or noise.
uniform int u_out;       // @param choice [value|direction|across] 0 "Out" Value: the count, a scalar field. Direction: the unit way the count grows, a vector field (line, rings, spokes). Across: that way turned a quarter turn anticlockwise.
uniform float u_scale;   // @param 0.0625 512 1 log "Scale" How fast it counts: line and rings, per frame height; spokes, per turn; cells and noise, cells to a frame height.
uniform float u_angle;   // @param 0 6.2832 0 wrap "Angle" Line: the direction it counts along, radians (0 across, a quarter turn up).
uniform int u_rule;      // @param choice [rows|columns|diagonal|rings|random] 0 "Rule" Cells: how the number runs over the grid.
uniform float u_spread;  // @param 0 1 1 "Spread" Cells: how far one cell's number is from the next along the rule (random: 1 is thoroughly shuffled).
uniform float u_aspect;  // @param 0.0625 16 1 log "Aspect" Cells: a cell's width over its height — 16 long strips across, 1/16 tall slats.
uniform int u_group;     // @param 1 8 1 "Group" Cells: cells on a side that share one number, so 4 numbers the grid in 4 × 4 blocks.
uniform int u_pairs;     // @param choice [none|across|up] 0 "Pairs" Cells: blocks paired off across, or up and down, each pair sharing one number — what Cell action's swap trades.
uniform float u_cx;      // @param -1 1 0 "Centre X" The point the count starts at: −1 the left edge … +1 the right.
uniform float u_cy;      // @param -1 1 0 "Centre Y" The point the count starts at: −1 the bottom … +1 the top.

vec4 effect(vec2 uv) {
    vec2 p = from_point(uv, u_cx, u_cy);
    Measure m;
    if (u_along == 1) m = measure_rings(p);
    else if (u_along == 2) m = measure_spokes(p);
    else if (u_along == 0) m = measure_line(p, u_angle);
    else if (u_along == 3) {
        // Blocks' grid (`cell_of`, `cell_pair`), a cell sitting on the point.
        // A value carries the cell's size (frame heights) in y and z; a
        // direction is this pixel's place in its cell (frame heights, from its
        // middle), with its side of a pair × Group in z: what Cell action reads
        vec2 cs = vec2(u_aspect, 1.0) / u_scale;
        Cell k = cell_of(p * u_scale / vec2(u_aspect, 1.0) + 0.5, u_group);
        float side = u_pairs == 0 ? 0.0
            : cell_pair(k.id, u_pairs == 1 ? vec2(1.0, 0.0) : vec2(0.0, 1.0)) * float(u_group);
        vec2 at = k.l * cs;
        if (u_out == 2) return vec4(-at.y, at.x, side, 1.0);
        if (u_out == 1) return vec4(at, side, 1.0);
        return vec4(measure_cells(k.id, u_rule, u_spread), cs, 0.0);
    } else {
        m = Measure(perlin(p * u_scale) * 2.0, vec2(0.0));
        return u_out >= 1 ? as_vector(m.g) : as_scalar(m.x);
    }
    // the other half rides along in the spare channels (a value carries its
    // direction in y and z, a direction its value in z): nothing reads them
    // yet, but the count and its direction are then worked out together, as
    // wave.glsl works them out, to the bit (plan 67: Wave as a patch)
    if (u_out == 2) return vec4(-m.g.y, m.g.x, m.x, 1.0);      // across: a quarter turn on
    if (u_out == 1) return vec4(m.g, m.x, 1.0);
    return vec4(m.x * u_scale, m.g, 0.0);
}
