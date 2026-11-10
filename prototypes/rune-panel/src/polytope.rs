//! The shape: a 4-polytope's edges, turned through the six rotation planes and projected to
//! the page, drawn as one `Shape` of round-capped segments. Far edges fade, near ones brighten,
//! as the renderer's depth cue does.

use rune::{Color, LineCap, Shape};

pub struct Polytope {
    verts: Vec<[f32; 4]>,
    edges: Vec<(usize, usize)>,
}

/// Every pair of vertices `d2` apart (squared) is an edge.
fn polytope(verts: Vec<[f32; 4]>, d2: f32) -> Polytope {
    let mut edges = Vec::new();
    for i in 0..verts.len() {
        for j in i + 1..verts.len() {
            let d: f32 = (0..4).map(|k| (verts[i][k] - verts[j][k]).powi(2)).sum();
            if (d - d2).abs() < 1e-3 {
                edges.push((i, j));
            }
        }
    }
    let r = verts.iter().map(|v| v.iter().map(|x| x * x).sum::<f32>().sqrt()).fold(0.0, f32::max);
    let verts = verts.into_iter().map(|v| v.map(|x| x / r)).collect();
    Polytope { verts, edges }
}

/// The 24-cell, {3,4,3}: every permutation of (±1, ±1, 0, 0). 24 vertices, 96 edges.
pub fn cell24() -> Polytope {
    let mut v = Vec::new();
    for i in 0..4 {
        for j in i + 1..4 {
            for si in [-1.0, 1.0] {
                for sj in [-1.0, 1.0] {
                    let mut p = [0.0; 4];
                    p[i] = si;
                    p[j] = sj;
                    v.push(p);
                }
            }
        }
    }
    polytope(v, 2.0)
}

/// The tesseract, {4,3,3}: (±1, ±1, ±1, ±1). 16 vertices, 32 edges.
pub fn tesseract() -> Polytope {
    let v = (0..16).map(|b| [0, 1, 2, 3].map(|k| if b >> k & 1 == 1 { 1.0 } else { -1.0 })).collect();
    polytope(v, 4.0)
}

/// The 16-cell, {3,3,4}: ±1 on each axis. 8 vertices, 24 edges.
pub fn cell16() -> Polytope {
    let mut v = Vec::new();
    for k in 0..4 {
        for s in [-1.0, 1.0] {
            let mut p = [0.0; 4];
            p[k] = s;
            v.push(p);
        }
    }
    polytope(v, 2.0)
}

/// Angles in the six planes, in the app's order: XY, XZ, YZ, XW, YW, ZW.
pub const PLANES: [(usize, usize); 6] = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3), (2, 3)];

#[derive(Clone, Copy)]
pub struct Pose {
    pub angles: [f32; 6],
    /// Camera yaw and pitch, radians.
    pub yaw: f32,
    pub pitch: f32,
    /// Distance of the 4D eye; smaller is more extreme.
    pub depth4: f32,
}

impl Pose {
    /// A pose that drifts with time `t`, each plane at its own rate.
    pub fn at(t: f32, speed: f32) -> Pose {
        let rates = [0.0, 0.11, 0.07, 0.23, 0.17, 0.13];
        let mut angles = [0.0; 6];
        for (i, r) in rates.iter().enumerate() {
            angles[i] = 0.6 + i as f32 * 0.4 + t * r * speed * 3.0;
        }
        Pose { angles, yaw: 0.45, pitch: 0.3, depth4: 2.4 }
    }
}

/// Projects `p` into a `size`-point square: segments with a 0..1 nearness each.
fn project(p: &Polytope, pose: &Pose, size: f32) -> Vec<([f32; 2], [f32; 2], f32)> {
    let (cy, sy, cp, sp) = (pose.yaw.cos(), pose.yaw.sin(), pose.pitch.cos(), pose.pitch.sin());
    let pts: Vec<([f32; 2], f32)> = p
        .verts
        .iter()
        .map(|v| {
            let mut x = *v;
            for (i, (a, b)) in PLANES.iter().enumerate() {
                let (c, s) = (pose.angles[i].cos(), pose.angles[i].sin());
                let (xa, xb) = (x[*a], x[*b]);
                x[*a] = c * xa - s * xb;
                x[*b] = s * xa + c * xb;
            }
            let k4 = pose.depth4 / (pose.depth4 - x[3]);
            let (x3, y3, z3) = (x[0] * k4, x[1] * k4, x[2] * k4);
            // The camera: yaw about Y, then pitch about X.
            let (x3, z3) = (cy * x3 + sy * z3, -sy * x3 + cy * z3);
            let (y3, z3) = (cp * y3 - sp * z3, sp * y3 + cp * z3);
            let k3 = 4.2 / (4.2 - z3);
            let scale = size * 0.27;
            let near = ((z3 + x[3] * 0.6) * 0.5 + 0.5).clamp(0.0, 1.0);
            ([size / 2.0 + x3 * k3 * scale, size / 2.0 - y3 * k3 * scale], near)
        })
        .collect();
    let mut segs: Vec<_> = p.edges.iter().map(|(a, b)| (pts[*a].0, pts[*b].0, (pts[*a].1 + pts[*b].1) * 0.5)).collect();
    segs.sort_by(|a, b| a.2.total_cmp(&b.2));
    segs
}

/// The wireframe as one shape in a `size`-point square.
pub fn wire(p: &Polytope, pose: &Pose, size: f32, ink: Color, width: f32) -> Shape {
    project(p, pose, size).into_iter().fold(Shape::new(), |sh, (a, b, near)| {
        sh.line(a, b, width * (0.6 + 0.6 * near), LineCap::Round, ink.alpha(0.12 + 0.88 * near * near))
    })
}
