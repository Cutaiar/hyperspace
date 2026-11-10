// @label Bloom
// @order 50
// @blend add
// @tip Light that spills. Whatever is brighter than Threshold is spread over a disc
// @tip Radius px across and added back, so the lit parts bleed into the dark around
// @tip them and a white line gets a halo. Falloff is the shape of that halo: low is a
// @tip wide veil over the whole frame, high a tight glow at the edge of the light.
// @tip One pass samples the disc, so a wide Radius spreads the same taps thinner: for a
// @tip veil across the frame run a second Bloom over the first — the first fills the
// @tip gaps the second would have had to find. (patterns.py's `bloom` is a different
// @tip thing, a face pattern of petals.)

uniform float u_amount;    // @param 0 4 0.8 amount "Amount" How much of the spilled light is added back.
uniform float u_threshold; // @param 0 1 0.4 "Threshold" How bright a pixel has to be before it spills at all.
uniform float u_knee;      // @param 0 1 0.3 "Knee" How far above the threshold the spill comes fully in — a wide knee keeps a scene brightening from popping.
uniform float u_radius;    // @param 2 160 20 log "Radius" How far the light reaches, px.
uniform float u_falloff;   // @param 0.5 4 1.8 "Falloff" How fast the halo dims with distance: 0.5 a veil across the frame, 4 a tight rim.
uniform int u_taps;        // @param 8 96 40 "Taps" Samples of the disc — more is a smoother halo and costs more. A wide Radius spreads the same taps thinner, so it needs them.

// The light a pixel sends into the halo: what it has above the threshold,
// coming in over the knee so a scene brightening does not pop. Off the
// frame there is no light to spill — `src` would mirror the frame back in
// and leave a bright box around a wide halo — so the halo fades at the edge
// instead, which is what it should do.
vec3 spill(vec2 at) {
    if (at != clamp(at, 0.0, 1.0)) return vec3(0.0);
    vec4 s = texture(u_src, at);
    return s.rgb * smoothstep(u_threshold, u_threshold + u_knee + 1e-3, peak(s.rgb));
}

vec4 effect(vec2 uv) {
    float n = float(u_taps);
    // fixed per pixel and never moved: the dither is a still grain in the
    // halo, where one that ran on a clock would boil
    vec2 jit = hash22(uv * u_res);
    vec2 px = u_radius / u_res;
    vec3 acc = vec3(0.0);
    float wsum = 1e-5;
    for (int k = 0; k < u_taps; k++) {
        float f = (float(k) + jit.x) / n;        // 0 … 1 out from this pixel
        float a = (float(k) + jit.y) * 2.39996;  // the golden angle: no ring to band along
        float t = pow(f, 1.4);                   // the taps crowd the middle, where the light is
        // the kernel: a lens's veiling glare falls off as a power of the
        // distance — a bright core and a long skirt, not a gaussian — times
        // the ring's own area, since a tap out here stands for more of the
        // disc than one in
        float w = pow(f, 1.8) / (1.0 + pow(t * 8.0, u_falloff));
        acc += w * spill(uv + vec2(cos(a), sin(a)) * (t * px));
        wsum += w;
    }
    // the average light over the disc: Radius changes the halo's size, not
    // the brightness of what is already lit
    vec3 halo = acc / wsum * u_amount;
    return vec4(halo, peak(halo));
}
