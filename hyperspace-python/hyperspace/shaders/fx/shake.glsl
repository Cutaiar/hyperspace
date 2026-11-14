// @label Shake
// @order 26
// @blend mix
// @speed 1
// @clock u_shake_t rate 4096
// @tip The whole frame shaken, the way a camera on a speaker cabinet is: back and forth
// @tip along a line (buzz), round a small circle (orbit), in and out (punch), or knocked
// @tip a new way each time and let settle (jolt). Amount is the throw — put a bass band,
// @tip a hand or a pad on it and the picture rattles as hard as that says, and is itself
// @tip at 0. Smear leaves the shutter open across the travel; Split lets red and blue
// @tip run ahead of and behind green, so the picture holds and its edges buzz in colour.

uniform float u_amount; // @param 0 0.25 0.01 amount "Amount" The throw, in frame heights: how far the frame travels each way.
uniform float u_rate;   // @param 0.5 60 12 log "Rate" Shakes a second.
uniform int u_motion;   // @param choice [buzz|orbit|punch|jolt] 0 "Motion" Buzz: back and forth along the angle. Orbit: round a circle. Punch: in and out about the centre. Jolt: knocked a random way each shake, then settling.
uniform float u_angle;  // @param 0 6.2832 0 wrap "Angle" Buzz: the line it shakes along, radians (0 across, a quarter turn up and down).
uniform float u_hard;   // @param 0 1 0 "Hard" Buzz and punch: 0 swings like a sine, 1 snaps from one end to the other.
uniform float u_smear;  // @param 0 1 0 "Smear" The shutter, in half shakes: the frame averaged over that much of its travel, so the shake blurs instead of jumping.
uniform float u_split;  // @param 0 1 0 "Split" Red runs ahead of green and blue behind, up to a third of a shake each: at 1 the three never agree, and every edge fringes.

// where the frame is at phase ph (in shakes): xy the slide, z the zoom, each −1 … 1
vec3 where(float ph) {
    float s = sin(ph * TAU);
    s = sign(s) * pow(max(abs(s), 1e-4), 1.0 - u_hard);
    if (u_motion == 1) return vec3(cos(ph * TAU), sin(ph * TAU), 0.0);
    if (u_motion == 2) return vec3(0.0, 0.0, s);
    if (u_motion == 3) {
        float i = floor(ph), f = fract(ph);
        float a = hash21(vec2(i, 3.7)) * TAU;
        return vec3(vec2(cos(a), sin(a)) * (1.0 - f) * (1.0 - f), 0.0);
    }
    return vec3(vec2(cos(u_angle), sin(u_angle)) * s, 0.0);
}

// the frame as it is at phase ph, seen from this pixel
vec4 at(vec2 p, float ph) {
    vec3 w = where(ph) * u_amount;
    // the rim travels Amount at the top and bottom edges (0.5 from the centre)
    return src(uncentred(p * (1.0 + 2.0 * w.z) + w.xy));
}

vec4 effect(vec2 uv) {
    vec2 p = centred(uv);
    int n = u_smear > 0.0 ? 8 : 1;
    float j = hash21(uv * u_res);            // dithers the shutter's taps
    float lag = u_split / 3.0;
    vec4 acc = vec4(0.0);
    for (int k = 0; k < n; k++) {
        float ph = u_shake_t - u_smear * 0.5 * (float(k) + j) / float(n);
        vec4 g = at(p, ph);
        if (u_split > 0.0) {
            vec4 r = at(p, ph + lag), b = at(p, ph - lag);
            g = vec4(r.r, g.g, b.b, max(g.a, max(r.a, b.a)));
        }
        acc += g;
    }
    return acc / float(n);
}
