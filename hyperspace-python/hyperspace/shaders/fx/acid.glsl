// @label Acid
// @order 10
// @blend mix
// @speed 4
// @tip The Minecraft "Acid" shader (daxnitro/Gaeel, gbuffers_terrain #define ACID) on the
// @tip screen instead of the world: the frame heaves up and down and rolls about the
// @tip centre by an amount that grows with distance from it, and breathes in and out.

uniform float u_bend;    // @param 0 0.4 0.08 "Bend" Vertical heave, in frame heights (Minecraft: 5 blocks).
uniform float u_twist;   // @param 0 3.1416 0.5 "Twist" Roll about the centre, radians at full swing.
uniform float u_reach;   // @param 1 40 10 log "Reach" How fast the wave builds with distance from the centre — high rings tighter.
uniform float u_breathe; // @param 0 1 0.35 "Breathe" The depth pulse: the frame zooms in and out with the wave.

vec4 effect(vec2 uv) {
    vec2 p = centred(uv);
    float T = u_phase * 20.0;          // Minecraft's worldTime runs 20 ticks a second
    float d2 = dot(p, p) * u_reach * u_reach;
    // quoted in form: y += 5·sin(d2·sin(T/143)/1000);
    //                 om  = sin(d2·sin(T/256)/5000)·sin(T/200);  roll xy by om;
    //                 z  *= (sin(T/256) + 1.75)/2
    p.y += u_bend * sin(d2 * sin(T / 143.0));
    float om = u_twist * sin(d2 * sin(T / 256.0) * 0.2) * sin(T / 200.0);
    p = rot(om) * p;
    p *= mix(1.0, 2.0 / (sin(T / 256.0) + 1.75), u_breathe);
    return src(uncentred(p));
}
