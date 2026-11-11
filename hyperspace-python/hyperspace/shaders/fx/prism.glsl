// @label Prism
// @order 41
// @blend mix
// @speed 0.1
// @tip Chromatic aberration the way a lens makes it: the frame resampled once per
// @tip wavelength across the visible band, each colour pulled a little further out
// @tip than the last, so an edge opens into a smeared rainbow — red outside, violet
// @tip in — that widens toward the rim. Deconverge splits three hard channels;
// @tip this one sweeps the whole spectrum, so the fringe is a gradient, not three ghosts.
// @tip Tilt adds a straight split on top, its direction turning with the speed.

uniform float u_amount; // @param 0 0.4 0.02 amount "Amount" How far the ends of the spectrum part at the edge of the frame, in frame heights.
uniform float u_rim;    // @param 0 3 1 "Rim" How the split grows out from the centre: 0 the same everywhere, 1 a lens, 3 only the outer ring.
uniform float u_tilt;   // @param 0 24 0 "Tilt" A straight split on top of the radial one, px — a prism in the path. Speed turns its direction.
uniform float u_fringe; // @param 0 2 0.5 "Fringe" Deepens the colour the split made, and only that — the picture's own colours are left alone.
uniform float u_cx;     // @param -1 1 0 "Centre X" Where the lens is centred: −1 the left edge … +1 the right (frame heights from the middle).
uniform float u_cy;     // @param -1 1 0 "Centre Y" Where the lens is centred: −1 the bottom … +1 the top.
uniform int u_taps;     // @param 3 32 16 "Taps" Wavelengths sampled across the band — more is a smoother rainbow and costs more.

// What the eye makes of one wavelength, t: 0 the red end … 1 the violet.
// Three overlapping lobes, so the taps summed over the whole band come back
// to the colour they started as — at Amount 0 the frame is itself again.
vec3 spectrum(float t) {
    return vec3(exp(-12.0 * pow(t - 0.08, 2.0)),
                exp(-12.0 * pow(t - 0.42, 2.0)),
                exp(-12.0 * pow(t - 0.78, 2.0)));
}

vec4 effect(vec2 uv) {
    vec2 c = vec2(u_cx * 0.5 * u_res.x / u_res.y, u_cy * 0.5);
    vec2 p = centred(uv);
    vec2 d = p - c;
    float r = length(d);
    vec2 dir = r > 1e-5 ? d / r : vec2(0.0);
    // the dispersion at this pixel: out along the radius, grown by the rim
    // (r / 0.5 is 1 at the top and bottom edges), plus the straight tilt
    vec2 split = dir * (u_amount * pow(clamp(r / 0.5, 0.0, 1.0), u_rim))
               + (rot(u_phase) * vec2(1.0, 0.0)) * (u_tilt / u_res.y);
    float n = float(u_taps);
    // a per-pixel dither along the band hides the banding of few taps
    float j = (hash21(uv * u_res) - 0.5) / n;
    vec3 acc = vec3(0.0), wsum = vec3(0.0);
    float a = 0.0, asum = 0.0;
    for (int k = 0; k < u_taps; k++) {
        float t = clamp((float(k) + 0.5) / n + j, 0.0, 1.0);
        vec3 w = spectrum(t);
        // where a tap reads is the inverse of where the light lands: a tap
        // that reaches inward puts what it finds further out. So the long
        // wavelengths reach in, and come out on the outside — red out,
        // violet in, the way a lens throws them
        vec4 s = src(uncentred(p + split * ((t - 0.5) * 2.0)));
        acc += w * s.rgb;
        wsum += w;
        float wa = w.r + w.g + w.b;
        a += wa * s.a;
        asum += wa;
    }
    vec3 col = acc / max(wsum, vec3(1e-4));
    // the fringe deepens the colour the split *made*, never the colour the
    // picture already had: what the pixel owes to the split is the chroma it
    // has now less the chroma it had, so at Amount 0 this knob does nothing
    vec3 base = src(uv).rgb;
    col += ((col - luma(col)) - (base - luma(base))) * u_fringe;
    return vec4(max(col, 0.0), a / max(asum, 1e-4));
}
