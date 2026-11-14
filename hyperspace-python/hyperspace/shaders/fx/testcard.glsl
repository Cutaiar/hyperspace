// @label Test card
// @order 3
// @blend mix
// @speed 0
// @tip A generator, not a filter: a grid, a circle, a cross and colour bars, drawn in
// @tip place of its picture. Wire it ahead of an effect and that effect's thumbnail shows
// @tip what it does to straight lines, round things and flat colour; switch it off and
// @tip the picture comes through again. Its mix lays the card over the picture.

uniform float u_grid;    // @param 2 64 12 log "Grid" Squares up the frame's height. A line always runs through the centre.
uniform float u_line;    // @param 0.5 8 1.5 log "Line" The lines' width, px.
uniform float u_circle;  // @param 0 1 0.7 "Circle" The circle's diameter, in frame heights. 0 draws none.
uniform float u_bars;    // @param 0 0.5 0.12 "Bars" How much of the frame's foot the six colour bars take. 0 draws none.
uniform float u_ground;  // @param 0 1 0.07 "Ground" The grey behind the lines.

// 1 on a line of half-width w px at distance d px, eased over a pixel
float ink(float d, float w) { return 1.0 - smoothstep(w - 0.5, w + 0.5, d); }

vec4 effect(vec2 uv) {
    vec2 p = centred(uv);                               // frame heights from the centre
    float px = u_res.y;                                 // px in one frame height
    float w = 0.5 * u_line;
    // the grid: how far, in px, to the nearest line each way
    vec2 g = abs(fract(p * u_grid + 0.5) - 0.5) / u_grid * px;
    float lines = max(ink(g.x, w), ink(g.y, w));
    // the cross through the centre, twice as heavy, and the circle
    float heavy = max(ink(abs(p.x) * px, 2.0 * w), ink(abs(p.y) * px, 2.0 * w));
    if (u_circle > 0.0)
        heavy = max(heavy, ink(abs(length(p) - 0.5 * u_circle) * px, 2.0 * w));
    vec3 c = mix(vec3(u_ground), vec3(0.8), lines);
    c = mix(c, vec3(1.0), heavy);
    if (uv.y < u_bars) {
        // red, yellow, green, cyan, blue, magenta: the hue wheel in sixths
        float k = min(floor(uv.x * 6.0), 5.0);
        c = hsv2rgb(vec3(k / 6.0, 0.75, 0.9));
    }
    return vec4(c, 1.0);
}
