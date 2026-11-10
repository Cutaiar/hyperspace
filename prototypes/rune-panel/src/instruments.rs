//! Two instruments drawn as shapes: the camera's attitude indicator (a pitch ladder and a
//! heading tape, the camera's pitch and yaw) and an LFO's scope.

use rune::{El, LineCap, Path, Shape, canvas, col, el, text};

use crate::theme::{Look, ty};
use crate::widgets::cross;

/// Pitch moves the horizon, yaw runs the heading tape; the camera is the fixed symbol.
pub fn attitude(l: &Look, pitch_deg: f32, yaw_deg: f32, w: f32, h: f32) -> El {
    let k = h / 64.0; // points per degree of pitch
    let y0 = h / 2.0 + pitch_deg * k;
    let mut sh = Shape::new();
    // The ground: a faint fill under the horizon.
    let gy = y0.clamp(0.0, h);
    if gy < h {
        sh = sh.fill(vec![[0.0, gy], [w, gy], [w, h], [0.0, h]], l.label.alpha(0.035));
    }
    let mut labels = Vec::new();
    for p in (-90i32..=90).step_by(5) {
        let y = y0 - p as f32 * k;
        if !(-2.0..=h + 2.0).contains(&y) {
            continue;
        }
        if p == 0 {
            sh = sh.line([0.0, y], [w, y], 1.2, LineCap::Butt, l.label.alpha(0.85));
            continue;
        }
        let half = if p % 10 == 0 { 20.0 } else { 9.0 };
        sh = sh.line([w / 2.0 - half, y], [w / 2.0 + half, y], 1.0, LineCap::Butt, l.live.alpha(0.8));
        if p % 10 == 0 {
            labels.push((p, y));
        }
    }
    // The camera: wings and a centre square, in amber as a flight deck draws the aircraft.
    let (cx, cy) = (w / 2.0, h / 2.0);
    sh = sh
        .stroke(vec![[cx - 40.0, cy], [cx - 14.0, cy], [cx - 14.0, cy + 6.0]], 2.4, l.caution)
        .stroke(vec![[cx + 40.0, cy], [cx + 14.0, cy], [cx + 14.0, cy + 6.0]], 2.4, l.caution)
        .fill(vec![[cx - 2.5, cy - 2.5], [cx + 2.5, cy - 2.5], [cx + 2.5, cy + 2.5], [cx - 2.5, cy + 2.5]], l.caution);
    let mut screen = el()
        .key("adi")
        .size(w, h)
        .radius(2.0)
        .fill(l.glass)
        .border(1.0, l.line)
        .clip_soft(0.0)
        .child(canvas(sh).size(w, h).absolute(0.0, 0.0));
    for (p, y) in labels {
        screen = screen.child(
            text(format!("{}", p.abs()))
                .font(ty::VALUE_SMALL)
                .color(l.live.alpha(0.8))
                .absolute(w / 2.0 + 24.0, y - 7.0)
                .a11y_hidden(),
        );
    }
    col().key("attitude").gap(4.0).child(screen).child(heading(l, yaw_deg, w))
}

/// The heading tape: ten-degree marks with their numbers, the set heading under a cyan mark.
fn heading(l: &Look, yaw: f32, w: f32) -> El {
    let h = 24.0;
    let k = w / 70.0; // points per degree
    let mut sh = Shape::new();
    let mut tape = el().key("hdg").size(w, h).radius(2.0).fill(l.glass).border(1.0, l.line).clip_soft(0.0);
    let first = ((yaw - 40.0) / 5.0).floor() as i32 * 5;
    for d in (first..first + 85).step_by(5) {
        let x = w / 2.0 + (d as f32 - yaw) * k;
        let major = d % 10 == 0;
        sh = sh.line([x, 0.0], [x, if major { 7.0 } else { 4.0 }], 1.0, LineCap::Butt, l.dim);
        if major && (8.0..w - 8.0).contains(&x) {
            let n = d.rem_euclid(360) / 10;
            tape = tape.child(text(format!("{n:02}")).font(ty::VALUE_SMALL).color(l.label).absolute(x - 6.0, 8.0).a11y_hidden());
        }
    }
    sh = sh.fill(vec![[w / 2.0 - 5.0, 0.0], [w / 2.0 + 5.0, 0.0], [w / 2.0, 6.0]], l.set);
    tape.child(canvas(sh).size(w, h).absolute(0.0, 0.0))
}

/// One cycle of an LFO's wave on a small scope, a dot where it is now. Magenta: automation.
pub fn scope(l: &Look, kind: usize, t: f32, w: f32, h: f32) -> El {
    let f = |u: f32| -> f32 {
        match kind {
            0 => (u * std::f32::consts::TAU).sin(),
            1 => 1.0 - 4.0 * (u - 0.5).abs(),
            2 => 2.0 * u - 1.0,
            _ => [0.6, -0.3, 0.9, -0.8, 0.2, -0.5, 0.75, -0.1][(u * 8.0) as usize % 8],
        }
    };
    let y = |v: f32| h / 2.0 - v * (h / 2.0 - 4.0);
    let mut path = Path::new().move_to([3.0, y(f(0.0))]);
    for i in 1..=40 {
        let u = i as f32 / 40.0;
        path = path.line_to([3.0 + u * (w - 6.0), y(f(u.min(0.999)))]);
    }
    let rates = [1.0, 0.25, 0.125, 2.0];
    let u = (t * rates[kind] * 0.5).fract();
    let p = [3.0 + u * (w - 6.0), y(f(u))];
    let mut sh = Shape::new().line([0.0, h / 2.0], [w, h / 2.0], 1.0, LineCap::Butt, l.grid);
    sh = cross(sh, w / 2.0, h / 2.0, 2.0, l.faint);
    sh = sh.stroke_path(&path, 1.3, LineCap::Round, l.driven.alpha(0.85)).line(p, [p[0] + 0.01, p[1]], 4.5, LineCap::Round, l.label);
    canvas(sh).key("scope").size(w, h).radius(2.0).fill(l.glass).border(1.0, l.line)
}
