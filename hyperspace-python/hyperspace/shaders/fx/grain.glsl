// @label Grain
// @order 93
// @blend mix
// @speed 1
// @tip Film grain and an ordered dither. The grain is a field of noise redrawn 24 times
// @tip a second (speed is the shutter: 0 freezes it), strongest in the midtones where
// @tip film's is, and Size is how coarse it is — one px is video noise, eight is 16 mm.
// @tip Steps then crushes each channel to that many steps between black and white and
// @tip the 4×4 dither breaks the banding into a printed screen; at 0 nothing is crushed.
// @tip Ground puts grain on the black too, which lights those pixels.

uniform float u_amount; // @param 0 1 0.15 amount "Amount" How deep the grain cuts.
uniform float u_size;   // @param 0.5 8 1 log "Size" One grain, px — the film stock.
uniform float u_tone;   // @param 0 1 0.6 "Tone" How much the grain follows the picture: 1 is film (midtones only, black and white left alone), 0 is flat video noise.
uniform float u_colour; // @param 0 1 0.25 "Colour" Grey grain at 0; at 1 each channel gets its own, for colour speckle.
uniform float u_ground; // @param 0 1 0 "Ground" How much grain lands where the frame is see-through. Above 0 it lights the empty frame, so the desktop sees it too.
uniform int u_steps;    // @param 0 32 0 "Steps" Steps each channel is crushed to, counted as the gaps between its levels — 1 is a two-tone print, 4 a five-level screen. 0 crushes nothing.
uniform float u_dither; // @param 0 1 1 "Dither" How much of the 4×4 ordered pattern goes into the crush: 1 trades the bands for a dot screen, 0 leaves hard steps.

// The 4×4 ordered (Bayer) matrix as its two 2×2 levels, 0 … 1 over a 4-px tile
float bayer4(vec2 p) {
    vec2 q = mod(floor(p), 4.0), lo = mod(q, 2.0), hi = floor(q * 0.5);
    return (4.0 * mod(3.0 * lo.y + 2.0 * lo.x, 4.0)
              + mod(3.0 * hi.y + 2.0 * hi.x, 4.0) + 0.5) / 16.0;
}

vec4 effect(vec2 uv) {
    vec4 c = src(uv);
    vec2 cell = floor(uv * u_res / u_size);   // Size never reaches 0: its range starts at 0.5
    float roll = floor(u_phase * 24.0);         // the shutter: a new field of grain each frame
    float grey = hash21(cell + roll * 7.13) - 0.5;
    vec3 n = vec3(hash21(cell + roll * 7.13 + 11.0),
                  hash21(cell + roll * 7.13 + 23.0),
                  hash21(cell + roll * 7.13 + 37.0)) - 0.5;
    float b = clamp(luma(c.rgb), 0.0, 1.0);   // an effect before this one may have gone over 1
    // film grain lives in the midtones: 4·b·(1−b) is 1 at mid grey, 0 at either end
    float tone = mix(1.0, 4.0 * b * (1.0 - b), u_tone);
    // premultiplied: a see-through pixel gets no grain unless Ground says so
    vec3 col = max(c.rgb + mix(vec3(grey), n, u_colour) * (tone * u_amount
                                                           * max(c.a, u_ground)), 0.0);
    if (u_steps > 0) {
        // the gaps, not the levels: every value of the knob then means
        // something — 1 is one gap, black to white, and `steps + 1` levels
        float lv = float(u_steps);
        col = floor(col * lv + (bayer4(uv * u_res) - 0.5) * u_dither + 0.5) / lv;
    }
    return vec4(col, c.a);
}
