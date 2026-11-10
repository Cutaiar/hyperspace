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

// Each cell of a grid can hold a root (Density says how many do, Jitter how
// far from the cell's middle, Offset X and Y slide the grid over the
// picture); from each root run Blades paths. A path
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
// Position 0 the effect is a copy of its input, byte for byte.
// Profile shades what the paste shows. Behind the head a pixel always lies at
// the edge of its furthest paste, wherever it is across the tube, so rim
// (that paste's edge) is one even shade with the head's disc lit, and the
// relief profiles read how far the pixel is from the path itself instead.
uniform float u_pos;     // @param 0 1 0.5 "Position" How far along its path each stamp has been dragged: 0 at the root, 1 at the tip. The knob to scrub, or ride with an LFO.
uniform int   u_mode;    // @param choice [grass|noodles|curls] 0 "Field" The paths: blades of grass from above, each curling over toward its tip; noodles wiggling from end to end; or curls winding in like a fern's fiddlehead.
uniform float u_scale;   // @param 1 24 5 log "Scale" Roots across the frame's height.
uniform float u_density; // @param 0 1 1 "Density" How many of the roots grow a path: 1 every one, lower thins the field out; a path fades in by its brush widening, never pops.
uniform float u_jitter;  // @param 0 1 0.7 "Jitter" How far each root strays from the middle of its cell: 0 a regular grid, 1 anywhere in its cell.
uniform float u_offset_x; // @param -1 1 0 "Offset X" Slides the field of paths across the picture, in frame heights; each root copies what is under it now.
uniform float u_offset_y; // @param -1 1 0 "Offset Y" Slides the field of paths up and down the picture, in frame heights.
uniform float u_length;  // @param 0.2 1.5 0.9 "Length" How long each path is, in cells between roots.
uniform float u_brush;   // @param 0.03 0.5 0.15 log "Brush" The stamp's radius, in cells: how much of the picture about each root is copied and dragged.
uniform int   u_blades;  // @param 1 5 1 "Blades" Paths from each root, fanned around it: a tuft extrudes the same stamp several ways at once.
uniform float u_trail;   // @param 0 1 1 "Trail" How much of the drag stays pasted behind the head: 1 the whole extrusion back to the root, 0 only the stamp where it is now.
uniform float u_stagger; // @param 0 1 0 "Stagger" Starts each path late by its own amount, so they set off one by one; at 1 Position reaches every tip.
uniform float u_flow;    // @param 0 4 0.3 "Flow" How fast the paths sway and wiggle; a step changes the speed, never where the paths are.
uniform int   u_profile; // @param choice [rim|round|bevel|ridge|groove|fluted|flat] 0 "Profile" How the tube is shaded: rim darkens each paste toward its edge, which leaves the tube one even shade and its head a lit disc; or a cross-section: round, bevel (a flat top, chamfered), ridge (a peaked roof), groove (a gutter) and fluted (ribs along it) light it as relief from the upper left; flat leaves the copies as they are.
uniform float u_depth;   // @param 0 1 0.35 "Depth" How strongly the profile shows: the rim's darkening, or the relief's light and shadow.

const int SEGS = 4;
const int REACH = 3;          // the cell search's widest half width: Length + Brush + a root's reach into its neighbour ≤ 3 cells
const float PHI = 1.6180340;
const float STRAIGHT = 0.02;  // a curvature (per cell) under this is a straight segment

// FS_TAIL's: the pixel under this one, read 1:1. A displaced read goes through
// src, which filters; one that has not moved must come back exactly
vec4 here();

// the point at arc length t along an arc from o heading dir, curvature k
vec2 arc_point(vec2 o, vec2 dir, float k, float t) {
    if (abs(k) < STRAIGHT) return o + t * dir;
    float a = k * t;
    vec2 d = vec2(cos(a) * dir.x - sin(a) * dir.y, sin(a) * dir.x + cos(a) * dir.y);
    return o + (vec2(-dir.y, dir.x) - vec2(-d.y, d.x)) / k;
}

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

// from one segment's start to the next's, a turn of the heading th
void next_segment(inout vec2 o, inout vec2 dir, inout float th, float turn, float k, float len) {
    th += turn;
    vec2 next = vec2(cos(th), sin(th));
    o = abs(k) < STRAIGHT ? o + len * dir
      : o + (vec2(-dir.y, dir.x) - vec2(-next.y, next.x)) / k;
    dir = next;
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
        next_segment(o, dir, th, turn, k, len);
    }
    if (best >= 0.0) c = arc_point(bo, bdir, bk, bt);
    return best;
}

// the point of one path nearest p between arc lengths s0 and s1. Per arc:
// the foot of p on its line or circle when that lies on the arc, else an end
vec2 path_nearest(vec2 p, vec2 root, float th, float seed, float s0, float s1) {
    float len = u_length / float(SEGS);
    float sway = sin(u_flow_t + seed * TAU);
    vec2 o = root, dir = vec2(cos(th), sin(th));
    vec2 near = p;
    float nearest = 1e9;
    for (int i = 0; i < SEGS; i++) {
        float start = float(i) * len;
        if (start > s1) break;
        float turn = seg_turn(i, seed, sway);
        float k = turn / len;
        float lo = max(s0 - start, 0.0), hi = min(s1 - start, len);
        if (hi >= lo) {
            float foot = dot(p - o, dir);
            if (abs(k) >= STRAIGHT) {
                vec2 q = p - (o + vec2(-dir.y, dir.x) / k);
                vec2 qo = -vec2(-dir.y, dir.x) * sign(k);
                foot = sign(k) * atan(qo.x * q.y - qo.y * q.x, dot(qo, q)) / abs(k);
            }
            vec2 at[3];
            at[0] = arc_point(o, dir, k, clamp(foot, lo, hi));
            at[1] = arc_point(o, dir, k, lo);
            at[2] = arc_point(o, dir, k, hi);
            for (int n = 0; n < 3; n++) {
                float d = dot(p - at[n], p - at[n]);
                if (d < nearest) { nearest = d; near = at[n]; }
            }
        }
        next_segment(o, dir, th, turn, k, len);
    }
    return near;
}

// the profile's light, x the pixel from a point of the paste in brushes
// (|x| ≤ 1): rim darkens toward the edge; the others are a height
// across the tube, h(|x|), lit from the upper left as grow lights its
// relief — a flat top lights to 1 — so only the slope h′ shows
float profile(vec2 x, float depth) {
    float d = min(length(x), 1.0);
    if (u_profile == 0) return 1.0 - depth * smoothstep(0.65, 1.0, d);
    if (u_profile == 6) return 1.0;
    float slope;                                             // dh/d|x|
    if (u_profile == 1) slope = -d / sqrt(max(1.0 - d * d, 0.04));        // round: a half cylinder
    else if (u_profile == 2) slope = d < 0.6 ? 0.0 : -2.5;               // bevel: flat top, a chamfer
    else if (u_profile == 3) slope = -1.5;                                // ridge: a peaked roof
    else if (u_profile == 4) slope = 2.0 * d;                            // groove: a gutter, lowest along the middle
    else slope = -2.5 * sin(d * 3.0 * PI);                               // fluted: three ribs a side
    vec2 g = slope * (d > 1e-4 ? x / length(x) : vec2(0.0));
    vec3 n = normalize(vec3(-g, 1.0));
    vec3 l = normalize(vec3(-0.5, 0.6, 0.6));
    return mix(1.0, clamp(dot(n, l) / l.z, 0.0, 1.6), depth);
}

vec4 effect(vec2 uv) {
    vec2 p = (centred(uv) - vec2(u_offset_x, u_offset_y)) * u_scale;
    float r = u_brush;
    // no head has gone past Position × Length, so no paste lies further
    // than that and a brush from its root, the root up to half a cell
    // and half its jitter from its cell's middle
    float most = u_length * u_pos;
    float stray = 0.5 * u_jitter;
    int reach = min(int(ceil(most + r + 0.5 + stray)), REACH);
    vec2 c0 = floor(p);
    float best = -1.0;
    vec2 from = p, to = p;      // the stamp's root and where it was pasted
    float br = r;               // that path's brush
    float bth = 0.0, bseed = 0.0, btail = 0.0;   // and the rest of that path
    for (int j = -reach; j <= reach; j++)
    for (int i = -reach; i <= reach; i++) {
        vec2 cell = c0 + vec2(i, j);
        vec2 root = cell + 0.5 + u_jitter * (hash22(cell) - 0.5);
        float far = length(p - root);
        if (far > most + r) continue;
        // Density: a root grows once Density passes its own share, its
        // brush widening over the next 0.08 so it never pops in
        float rr = r * clamp((u_density - 0.92 * hash21(cell + 11.0)) / 0.08, 0.0, 1.0);
        if (rr <= 0.0) continue;
        float seed = hash21(cell + 3.0);
        for (int b = 0; b < 5; b++) {
            if (b >= u_blades) break;
            float blade_seed = fract(seed + float(b) * PHI);
            float th = seed * TAU + float(b) * TAU / float(u_blades)
                     + 0.6 * (fract(blade_seed * 3.7) - 0.5) / float(u_blades);
            float delay = u_stagger * 0.6 * fract(blade_seed * PHI * 5.0);
            float head = u_length * clamp((u_pos - delay) / (1.0 - delay), 0.0, 1.0);
            if (far > head + rr) continue;                 // a path's arc length bounds its reach
            float tail = max(head - u_trail * u_length, 0.0);
            vec2 c;
            float s = path_hit(p, root, th, blade_seed, tail, head, rr, c);
            if (s > best) { best = s; from = root; to = c; br = rr; bth = th; bseed = blade_seed; btail = tail; }
        }
    }
    // nothing covers it, or only a paste that has not moved
    if (best <= 0.0) return here();
    vec2 aspect = vec2(u_res.y / u_res.x, 1.0);
    vec4 col = src(uv + (from - to) / u_scale * aspect);
    // the profile, faded in over the first brush of travel so Position 0
    // stays the frame
    vec2 across = (p - to) / br;           // from the stamp's centre, 1 at its edge
    // relief is across the tube: from the path, on this strand of it. A strand
    // lying over an earlier turn of its own path keeps its own cross-section,
    // so look no further back than two brushes
    if (u_profile >= 1 && u_profile <= 5)
        across = (p - path_nearest(p, from, bth, bseed, max(btail, best - 2.0 * br), best)) / br;
    col.rgb *= profile(across, u_depth * min(1.0, best / br));
    return col;
}
