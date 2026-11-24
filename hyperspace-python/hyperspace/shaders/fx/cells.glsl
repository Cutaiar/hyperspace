// @label Cells
// @order 31
// @family field
// @makes field
// @takes image none
// @takes field field
// @tip A grid of cells, a cell sitting on the point (a Point on its field port; the middle
// @tip with none), each numbered by a Rule: row by row, column by column, on the diagonal,
// @tip in square rings or at random. Out place gives each pixel's place in its cell
// @tip instead, a vector −½ … ½ (into Displace: every cell zooms). Wire the number into a
// @tip Waveform and that into a Cell action, the place into its field port: Blocks.

// plan 67 §15: Measure's cells, on their own — Blocks' grid (`cell_of`,
// `cell_pair`). The number carries the cell's size (frame heights) in y and z;
// the place its side of a pair × Group in z: what Cell action reads (row 1098)
uniform float u_scale;   // @param 0.0625 512 8 log "Scale" Cells to a frame height.
uniform float u_aspect;  // @param 0.0625 16 1 log "Aspect" A cell's width over its height — 16 long strips across, 1/16 tall slats.
uniform int u_group;     // @param 1 8 1 "Group" Cells on a side that share one number, so 4 numbers the grid in 4 × 4 blocks.
uniform int u_rule;      // @param choice [rows|columns|diagonal|rings|random] 0 "Rule" How the number runs over the grid.
uniform float u_spread;  // @param 0 1 1 "Spread" How far one block's number is from the next along the rule: 0 every block alike, 1 one apart (random: 1 thoroughly shuffled).
uniform int u_pairs;     // @param choice [none|across|up] 0 "Pairs" Blocks paired off across, or up and down, each pair sharing one number — what Cell action's swap trades.
uniform int u_out;       // @param choice [value|place] 0 "Out" Value: the cell's number, a scalar field. Place: this pixel's place in its cell, a vector, −½ … ½ across and up.

vec4 effect(vec2 uv) {
    vec2 p = from_field_point(uv);
    vec2 cs = vec2(u_aspect, 1.0) / u_scale;            // a cell, frame heights
    Cell k = cell_of(p * u_scale / vec2(u_aspect, 1.0) + 0.5, u_group);
    float side = u_pairs == 0 ? 0.0
        : cell_pair(k.id, u_pairs == 1 ? vec2(1.0, 0.0) : vec2(0.0, 1.0)) * float(u_group);
    if (u_out == 1) return vec4(k.l, side, 1.0);
    return vec4(measure_cells(k.id, u_rule, u_spread), cs, 0.0);
}
