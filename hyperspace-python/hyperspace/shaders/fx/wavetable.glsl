// @label Wave Table
// @order 24
// @blend mix
// @speed 1
// @tip A field of paths seen from above — blades of grass, noodles or curls — and a
// @tip stamp at the root of each: the picture inside it, copied and dragged along its
// @tip path like a lasso selection pasted again and again under the mouse in Paint,
// @tip leaving an extruded trail. Position is how far along the path the drag has come,
// @tip the knob to scrub or ride with an LFO. At 0 nothing has moved.
// @clock u_flow_t flow

// Each cell of a jittered grid has a root; from it run Blades paths. A path
// is a chain of SEGS circular arcs, each with its own turn, so its shape is
// closed form: a blade curling more toward its tip, a noodle wiggling, a
// curl winding in. The stamp is a disc of Brush radius at the root, and the
// drag pastes it at every point of the path from s0 to s1 (arc length, in
// cells): s1 = Position × Length is the head, s0 = s1 − Trail × Length the
// tail. A later paste covers an earlier one, so a pixel shows the paste
// with the largest s that covers it, and that is solved exactly per arc —
// the points of a circle within r of the pixel are one interval of angle
// about the nearest — never marched. Where no paste lands the frame shows
// through, and a root's own disc at s 0 is the frame itself, so at
// Position 0 the effect is a copy of its input.
uniform float u_pos;     // @param 0 1 0.5 "Position" How far along its path each stamp has been dragged: 0 at the root, 1 at the tip. The knob to scrub, or ride with an LFO.
uniform int   u_mode;    // @param choice [grass|noodles|curls] 0 "Field" The paths: blades of grass from above, each curling over toward its tip; noodles wiggling from end to end; or curls winding in like a fern's fiddlehead.
uniform float u_scale;   // @param 1 24 5 log "Scale" Roots across the frame's height.
uniform float u_length;  // @param 0.2 1.5 0.9 "Length" How long each path is, in cells between roots.
uniform float u_brush;   // @param 0.03 0.5 0.15 log "Brush" The stamp's radius, in cells: how much of the picture about each root is copied and dragged.
uniform int   u_blades;  // @param 1 5 1 "Blades" Paths from each root, fanned around it: a tuft extrudes the same stamp several ways at once.
uniform float u_trail;   // @param 0 1 1 "Trail" How much of the drag stays pasted behind the head: 1 the whole extrusion back to the root, 0 only the stamp where it is now.
uniform float u_stagger; // @param 0 1 0 "Stagger" Starts each path late by its own amount, so they set off one by one; at 1 Position reaches every tip.
uniform float u_flow;    // @param 0 4 0.3 "Flow" How fast the paths sway and wiggle; a step changes the speed, never where the paths are.
uniform float u_rim;     // @param 0 1 0.35 "Rim" Darkens each paste toward its edge, so the copies under the head read as the sides of an extrusion.

const int SEGS = 4;
const int REACH = 3;          // the cell search's widest half width: Length + Brush + root jitter ≤ 3 cells
const float PHI = 1.6180340;
const float STRAIGHT = 0.02;  // a curvature (per cell) under this is a straight segment

// one arc: from o heading dir, curvature k. The largest arc length t in
// [lo, hi] at which the disc of radius r about the arc's point covers p, or −1
float arc_hit(vec2 p, vec2 o, vec2 dir, float k, float lo, float hi, float r) {
    if (abs(k) < STRAIGHT) {
        // straight (a circle 50 cells across bends under a thousandth of a
        // cell over a segment; past it the circle's sums lose float precision)
        vec2 w = p - o;
        float b = dot(w, dir);
        float disc = b * b - (dot(w, w) - r * r);
        if (disc < 0.0) return -1.0;
        float a0 = max(b - sqrt(disc), lo), a1 = min(b + sqrt(disc), hi);
        return a1 >= a0 ? a1 : -1.0;
    }
    float R = 1.0 / abs(k), sg = sign(k);
    vec2 q = p - (o + vec2(-dir.y, dir.x) / k);           // from the circle's centre
    float rho = max(length(q), 1e-6);
    // |p − point|² = (ρ − R)² + 4ρR sin²(Δ/2), Δ the angle between them
    // about the centre: the form that keeps its precision when R is large
    float v = (r * r - (rho - R) * (rho - R)) / (4.0 * rho * R);
    if (v < 0.0) return -1.0;
    float delta = v >= 1.0 ? PI : 2.0 * asin(sqrt(v));
    // the point's angle about the centre starts at o's and runs k t; m is
    // p's angle past o's, in units of t·|k| (the cross and dot of the two
    // radii, so no angle of o's is needed)
    vec2 qo = -vec2(-dir.y, dir.x) * sg;                   // o's radius, unit
    float m = sg * atan(qo.x * q.y - qo.y * q.x, dot(qo, q));
    float best = -1.0;
    for (int n = -1; n <= 1; n++) {
        float mid = m + float(n) * TAU;
        float a0 = max((mid - delta) * R, lo), a1 = min((mid + delta) * R, hi);
        if (a1 >= a0) best = max(best, a1);
    }
    return best;
}

// how far a segment turns, radians: by the field, the path's seed and its
// sway (the flow clock through the seed's own phase). Each is under π, so
// one arc is never more than half a circle
float seg_turn(int i, float seed, float sway) {
    float fi = float(i);
    float side = seed < 0.5 ? -1.0 : 1.0;
    if (u_mode == 0) {
        // grass: curls over more toward the tip, the whole blade swaying
        float curl = side * (0.3 + 0.9 * fract(seed * 7.13)) + 0.25 * sway;
        return curl * 2.0 * (fi + 0.5) / float(SEGS * SEGS);
    }
    if (u_mode == 1) {
        // noodles: a wave along the path, travelling with the flow
        return 1.4 * sin(fi * 2.1 + seed * TAU + u_flow_t);
    }
    // curls: winding in, each segment tighter than the last
    return side * (0.4 + 0.7 * fi) * (0.85 + 0.15 * sway);
}

// the furthest paste along one path that covers p: its arc length, or −1,
// and its stamp's centre in c
float path_hit(vec2 p, vec2 root, float th, float seed, float s0, float s1, float r,
               out vec2 c) {
    float len = u_length / float(SEGS);
    float sway = sin(u_flow_t + seed * TAU);
    vec2 o = root, dir = vec2(cos(th), sin(th));
    float best = -1.0;
    vec2 bo, bdir;
    float bk = 0.0, bt = 0.0;
    for (int i = 0; i < SEGS; i++) {
        float start = float(i) * len;
        if (start > s1) break;
        float turn = seg_turn(i, seed, sway);
        float k = turn / len;
        float hi = min(s1 - start, len);
        // a segment's points lie within its arc length of its start
        if (length(p - o) <= hi + r) {
            float t = arc_hit(p, o, dir, k, max(s0 - start, 0.0), hi, r);
            if (t >= 0.0) { best = start + t; bo = o; bdir = dir; bk = k; bt = t; }   // later segments lie further along
        }
        // on to the segment's end
        th += turn;
        vec2 next = vec2(cos(th), sin(th));
        o = abs(k) < STRAIGHT ? o + len * dir
          : o + (vec2(-dir.y, dir.x) - vec2(-next.y, next.x)) / k;
        dir = next;
    }
    if (best >= 0.0) {
        if (abs(bk) < STRAIGHT) {
            c = bo + bt * bdir;
        } else {
            float a = bk * bt;
            vec2 d = vec2(cos(a) * bdir.x - sin(a) * bdir.y, sin(a) * bdir.x + cos(a) * bdir.y);
            c = bo + (vec2(-bdir.y, bdir.x) - vec2(-d.y, d.x)) / bk;
        }
    }
    return best;
}

vec4 effect(vec2 uv) {
    vec2 p = centred(uv) * u_scale;
    float r = u_brush;
    // no head has gone past Position × Length, so no paste lies further
    // than that and a brush from its root (the root within 0.85 of its cell)
    float most = u_length * u_pos;
    int reach = min(int(ceil(most + r + 0.85)), REACH);
    vec2 c0 = floor(p);
    float best = -1.0;
    vec2 from = p, to = p;      // the stamp's root and where it was pasted
    for (int j = -reach; j <= reach; j++)
    for (int i = -reach; i <= reach; i++) {
        vec2 cell = c0 + vec2(i, j);
        vec2 root = cell + 0.15 + 0.7 * hash22(cell);
        float far = length(p - root);
        if (far > most + r) continue;
        float seed = hash21(cell + 3.0);
        for (int b = 0; b < 5; b++) {
            if (b >= u_blades) break;
            float bseed = fract(seed + float(b) * PHI);
            float th = seed * TAU + float(b) * TAU / float(u_blades)
                     + 0.6 * (fract(bseed * 3.7) - 0.5) / float(u_blades);
            float delay = u_stagger * 0.6 * fract(bseed * PHI * 5.0);
            float head = u_length * clamp((u_pos - delay) / (1.0 - delay), 0.0, 1.0);
            if (far > head + r) continue;                  // a path's arc length bounds its reach
            float tail = max(head - u_trail * u_length, 0.0);
            vec2 c;
            float s = path_hit(p, root, th, bseed, tail, head, r, c);
            if (s > best) { best = s; from = root; to = c; }
        }
    }
    if (best < 0.0) return src(uv);
    vec2 aspect = vec2(u_res.y / u_res.x, 1.0);
    vec4 col = src(uv + (from - to) / u_scale * aspect);
    // the rim, faded in over the first brush of travel so Position 0 stays the frame
    float edge = smoothstep(0.65, 1.0, length(p - to) / r);
    col.rgb *= 1.0 - u_rim * edge * min(1.0, best / r);
    return col;
}
