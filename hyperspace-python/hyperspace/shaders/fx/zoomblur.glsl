// @label Zoom burst
// @order 17
// @blend mix
// @tip Radial streaks: every pixel is smeared along the line to a burst centre, so the
// @tip light shoots outward from that point and brightens as it spreads. Amount is how
// @tip far the smear reaches; the centre is where the burst sits — put a hand's x and
// @tip z on Centre X / Y and the burst follows the hand across the box.

uniform float u_amount; // @param 0 1 0.3 "Amount" How far each pixel smears toward the centre, as a fraction of its distance.
uniform float u_cx;     // @param -1 1 0 "Centre X" Where the burst sits: −1 the left edge … +1 the right (frame heights from the middle).
uniform float u_cy;     // @param -1 1 0 "Centre Y" Where the burst sits: −1 the bottom … +1 the top.
uniform float u_glow;   // @param 0 2 0.6 "Glow" How much the light the streaks spread is lifted as the burst grows.
uniform int u_taps;     // @param 4 32 16 "Taps" Samples along each streak — smoother costs more.

vec4 effect(vec2 uv) {
    vec2 c = vec2(u_cx * 0.5 * u_res.x / u_res.y, u_cy * 0.5);
    vec2 p = centred(uv);
    vec2 d = (p - c) * u_amount;                 // the streak: from the pixel toward the centre
    float n = float(u_taps);
    // a per-pixel dither along the streak hides the banding of few taps
    float j = hash21(uv * u_res) / n;
    vec4 acc = vec4(0.0);
    float wsum = 0.0;
    for (int k = 0; k < u_taps; k++) {
        float t = float(k) / n + j;
        float w = 1.0 - 0.5 * t;                 // the nearer samples count more
        acc += w * src(uncentred(p - d * t));
        wsum += w;
    }
    acc /= wsum;
    // the glow lifts only what the streaks brought in — light spread into
    // darker pixels — so the frame's own bright pixels never clip
    vec3 spread = max(acc.rgb - texture(u_src, uv).rgb, 0.0);
    acc.rgb += u_glow * u_amount * 2.0 * spread;
    return acc;
}
