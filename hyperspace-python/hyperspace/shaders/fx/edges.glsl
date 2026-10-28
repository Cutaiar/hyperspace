// @label Edges
// @order 75
// @blend mix
// @tip Line art: where the brightness of the picture changes, a line; where it is flat,
// @tip black. White draws the lines in grey by how sharp they are, source in the
// @tip picture's own colours, direction in a hue by which way the edge faces.
// @tip Glow adds a wider ring around every line.

// plan 39 T0 (W5, decision 7). A Sobel over the luma of the wired picture:
// the eight neighbours one pixel away (1 / u_res), x and y kernels
// [-1 0 1; -2 0 2; -1 0 1], the gradient divided by 4 so a hard step from
// black to white is 1. Below the threshold nothing; above it the line rises
// from 0 to full at a full step, so a soft edge never pops on and off. The
// glow is a second Sobel with its taps 3 px out, added at glow / 4 of its
// strength (4: as strong as the line), so a line gets a halo about six
// pixels wide. Premultiplied, over transparent black: a flat picture is
// (0, 0, 0, 0), so a `matte` from luma turns the lines into a mask.
uniform float u_threshold; // @param 0 1 0.2 "Threshold" Edges weaker than this draw nothing; raise it to keep only the sharpest lines.
uniform float u_glow;      // @param 0 4 0 "Glow" A wider second ring around every line; 0 is none, 4 as bright as the line.
uniform int   u_colour;    // @param choice [white|source|direction] 0 "Colour" White: grey by strength. Source: the picture's colour on its edges. Direction: a hue by the way the edge faces.

// the gradient of the picture's luma at uv, taps r px apart; 1 at a hard
// black-to-white step
vec2 sobel(vec2 uv, float r) {
    vec2 d = r / u_res;
    float tl = luma(src(uv + d * vec2(-1.0,  1.0)).rgb);
    float tc = luma(src(uv + d * vec2( 0.0,  1.0)).rgb);
    float tr = luma(src(uv + d * vec2( 1.0,  1.0)).rgb);
    float ml = luma(src(uv + d * vec2(-1.0,  0.0)).rgb);
    float mr = luma(src(uv + d * vec2( 1.0,  0.0)).rgb);
    float bl = luma(src(uv + d * vec2(-1.0, -1.0)).rgb);
    float bc = luma(src(uv + d * vec2( 0.0, -1.0)).rgb);
    float br = luma(src(uv + d * vec2( 1.0, -1.0)).rgb);
    float gx = (tr + 2.0 * mr + br) - (tl + 2.0 * ml + bl);
    float gy = (tl + 2.0 * tc + tr) - (bl + 2.0 * bc + br);
    return vec2(gx, gy) * 0.25;
}

// a gradient's strength through the threshold: 0 below it, 1 at a full step
float strength(vec2 g) {
    return clamp((length(g) - u_threshold) / max(1.0 - u_threshold, 1e-4), 0.0, 1.0);
}

vec4 effect(vec2 uv) {
    vec2 g = sobel(uv, 1.0);
    float m = strength(g);
    if (u_glow > 0.0) {
        vec2 g3 = sobel(uv, 3.0);
        m += u_glow * 0.25 * strength(g3);
        g += u_glow * 0.25 * g3;           // the halo takes the line's direction
    }
    m = clamp(m, 0.0, 1.0);
    if (u_colour == 1) {
        vec4 c = src(uv);                  // premultiplied: already covered by its alpha
        return c * m;
    }
    if (u_colour == 2) {
        // the way the gradient points, round the wheel: dark→light to the
        // right red, upward chartreuse, leftward cyan, downward violet
        float hue = fract(atan(g.y, g.x) / TAU);
        return vec4(hsv(hue, 1.0, 1.0) * m, m);
    }
    return vec4(vec3(m), m);
}
