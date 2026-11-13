// @label Blocks
// @order 28
// @blend mix
// @speed 1
// @clock u_drift_t drift 4096
// @tip The frame cut into a grid of cells, each moved by a number its rule hands it.
// @tip Rule is how the number runs over the grid (row by row, column by column, on the
// @tip diagonal, in square rings from the middle, or at random); Shape and Drift are how
// @tip it changes in time; Action is what a cell does with it — shift sideways, zoom,
// @tip stretch along one way until it streaks, turn, bulge like a lens, or swap places
// @tip with a neighbour. Group hands one number to a whole block of cells, so 4 is
// @tip "4 × 4 blocks of 16-px units, each block doing its own thing".

uniform float u_amount; // @param 0 4 0.5 amount "Amount" How much a cell does at its number's peak — shift and swap: cells moved; zoom, stretch and bulge: doublings of size; turn: quarter turns.
uniform float u_cell;   // @param 4 512 48 log "Cell" One cell's height, px.
uniform float u_aspect; // @param 0.0625 16 1 log "Aspect" A cell's width over its height: 16 is long strips across, 1/16 tall slats.
uniform int u_group;    // @param 1 8 1 "Group" Cells on a side that share one number: 4 moves the grid in 4 × 4 blocks.
uniform int u_action;   // @param choice [shift|zoom|stretch|turn|bulge|swap] 0 "Action" What a cell does with its number.
uniform int u_rule;     // @param choice [rows|columns|diagonal|rings|random] 4 "Rule" How the number runs over the grid.
uniform int u_shape;    // @param choice [sine|triangle|square|saw|noise] 0 "Shape" How a cell's number moves in time: swinging, snapping between two ends (square), sliding and wrapping (saw), or wandering (noise).
uniform float u_spread; // @param 0 1 0.5 "Spread" How far out of step one block is with the next along its rule: 0.5 on rows is every other row the other way.
uniform float u_angle;  // @param 0 6.2832 0 wrap "Angle" Shift, stretch and swap: the way they go, radians (0 across).
uniform float u_drift;  // @param 0 8 0.25 "Drift" Cycles a second. 0 holds the grid still.
uniform float u_split;  // @param 0 1 0 "Split" Parts the colours along each cell's move: red this much further, blue this much less.

vec4 effect(vec2 uv) {
    vec2 cs = vec2(u_cell * u_aspect, u_cell);          // a cell, px
    vec2 q = (uv - 0.5) * u_res / cs + 0.5;             // a cell sits on the frame's centre
    vec2 l = fract(q) - 0.5;                            // this pixel within its cell, −½ … ½
    vec2 id = floor(floor(q) / float(u_group));         // its block
    float c;                                            // the block's place along the rule
    if (u_rule == 0) c = id.y * u_spread;
    else if (u_rule == 1) c = id.x * u_spread;
    else if (u_rule == 2) c = (id.x + id.y) * u_spread;
    else if (u_rule == 3) c = max(abs(id.x), abs(id.y)) * u_spread;
    else c = hash21(id + 64.5) * (1.0 + 63.0 * u_spread);
    // a quarter cycle on: at rest (Drift 0) a sine sits on its crest, not its zero
    float a = wave(u_shape, c - u_drift_t + 0.25) * u_amount;
    vec2 dir = vec2(cos(u_angle), sin(u_angle));
    vec2 dl;                                            // how far it reads, in cells
    if (u_action == 1) {
        dl = l * (exp2(a) - 1.0);
    } else if (u_action == 2) {
        vec2 lp = l * cs;
        dl = dir * dot(lp, dir) * (exp2(a) - 1.0) / cs;
    } else if (u_action == 3) {
        vec2 lp = l * cs;
        dl = (rot(a * 0.5 * PI) * lp - lp) / cs;
    } else if (u_action == 4) {
        // a lens inside the cell's inscribed circle, still at its rim, so
        // the picture stays joined across cells
        float rr = length(l) * 2.0;
        dl = rr < 1.0 ? l * (pow(max(rr, 1e-4), exp2(a) - 1.0) - 1.0) : vec2(0.0);
    } else if (u_action == 5) {
        dl = floor(dir * a + 0.5);
    } else {
        dl = dir * a;
    }
    return pushed(uv, dl * cs / u_res.y, u_split);
}
