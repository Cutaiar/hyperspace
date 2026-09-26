// @label Fractals
// @order 60
// @blend screen
// @tip Noita's trip fractals (drugged_fractals_amount): a folded, twisting trig lattice
// @tip that glows out of the bright parts of the frame and breathes on its own clock.
// @tip Ground lets it bloom over the black too, so it also runs on an empty scene.

uniform float u_amount;  // @param 0 3 1 "Amount" Noita's fractals amount — 0.1 first stage, 1 heavily tripping, 1.5 on the last (they stack).
uniform float u_size;    // @param 0 1 0 "Size" Noita's fractals_size: 0 a steady lattice, 1 its cells swell and shrink with a slow noise.
uniform float u_cells;   // @param 4 60 20 log "Cells" Lattice cells across the frame's width (Noita: 20).
uniform float u_halo;    // @param 0 32 6 "Halo" How far past the shape the pattern shows, px — Noita keys it on bright pixels, and a wireframe is thin.
uniform float u_ground;  // @param 0 1 0 "Ground" How much it glows where the frame is black; 1 is a full-screen generator.

// adapted by Noita from a ShaderToy; quoted with T = the effect's clock
float shape(vec2 uv, float T) {
    vec2 f = fract(uv) - 0.5;
    vec2 st = vec2(atan(f.x, f.y), abs(f.x) + abs(f.y));
    float k = mix(2.0, 12.0, 0.5 + 0.5 * sin(T * 0.05));
    float a = 4.0;
    return cos(st.y * k + st.x * a + T) * cos(st.y * k - st.x * a + T)
         * smoothstep(0.2, 0.8, st.y);
}

vec3 render(vec2 uv, float T) {
    uv = abs(uv) - mix(0.25, 0.5, 0.5 + 0.5 * sin(T * 0.5));
    float s = shape(uv, T);
    float t = s + clamp(abs(0.2 / s) * 0.25, 0.0, 2.0);
    uv *= rot(0.785);
    s = shape(uv, T);
    t *= s + clamp(abs(0.03 / s) * 0.25, 0.0, 0.9);
    return mix(vec3(t, 0.4, mix(0.3, 0.8, 0.5 + 0.5 * sin(T))), vec3(0.1, 0.0, 0.3), t);
}

vec4 effect(vec2 uv) {
    float T = u_phase;
    // the frame in screen widths, like Noita's pos_seed; a slow static
    // noise wobbles the lattice and, with size, its scale
    vec2 pos = uv * vec2(1.0, u_res.y / u_res.x);
    vec2 pstatic = perlin2(pos * 3.0 + T * 0.01);
    vec2 pn = perlin2(pos * 8.0 + T * 0.1);
    vec2 ps = pos + pn * 0.01 + pstatic * 0.15;
    float cells = mix(u_cells, u_cells - (pstatic.x + pstatic.y) * u_cells * 0.75, u_size);
    vec3 fr = max(render(ps * cells, T) * 0.2, 0.0);
    // Noita: alpha = sqrt(brightness)·2 — only lit pixels show it
    float lit = reach(uv, u_halo);
    float alpha = max(sqrt(lit) * 2.0, u_ground);
    vec3 glow = fr * alpha * 2.5 * u_amount;
    return vec4(glow, peak(glow));
}
