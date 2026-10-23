// @label Blend
// @order 90
// @blend mix
// @tip Lays a second picture wired into its aux input (a media channel, the scene, the
// @tip history) onto the frame: over, multiply, screen, difference, or a luma key that
// @tip shows the aux only where it is brighter than the key. Mix is how much.

// plan 32 R (row 332). Premultiplied throughout: an unwired aux is
// transparent black, and every mode then leaves the frame as it is
uniform int   u_mode;  // @param choice [over|multiply|screen|difference|luma key] 0 "Mode" How the aux lands on the frame.
uniform float u_key;   // @param 0 1 0.5 "Key" Luma key: the aux shows where its brightness is above this.
uniform float u_soft;  // @param 0 0.5 0.1 "Softness" Luma key: how wide the edge of the key is.

vec4 effect(vec2 uv) {
    vec4 a = src(uv);
    vec4 b = aux(uv);
    if (u_mode == 1) return vec4(a.rgb * (b.rgb + 1.0 - b.a), a.a);
    if (u_mode == 2) return a + b - a * b;
    if (u_mode == 3) return vec4(abs(a.rgb - b.rgb), max(a.a, b.a));
    if (u_mode == 4) {
        float k = clamp((luma(b.rgb) - u_key + u_soft) / max(2.0 * u_soft, 1e-4), 0.0, 1.0);
        b *= k;
    }
    return b + a * (1.0 - b.a);
}
