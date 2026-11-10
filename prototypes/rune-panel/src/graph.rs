//! The GRAPH: the patch as columns of modules joined by cables, over the program output, on
//! a screen with a crosshair grid.
//!
//! A cable's colour is what it carries: green a live signal, magenta modulation, cyan the
//! selection's cables, grey a dormant one. The canvas pans by its background, a module moves
//! by its title bar, and the NAV display jumps the viewport on a spring.

use rune::tok::motion;
use rune::{Color, Drag, El, LineCap, Path, Phase, Shape, Spring, TextCase, canvas, col, el, row, text};
use rune_kit::Kit;

use crate::App;
use crate::data::{self, FOOTER, HEADER, NODE_W, Node, PITCH, ROW, Status, THUMB};
use crate::polytope::{self, Pose};
use crate::theme::{Cat, Look, ty};
use crate::widgets::{brackets, cross, push, selector, state_word};

/// `vw` is the viewport's width as last laid out, for the pan's range and the NAV display.
pub fn pane(s: &App, l: &Look, _k: &Kit, vw: f32) -> El {
    col().key("graph").grow(1.0).min_w(0.0).h_full().fill(l.glass).child(toolbar(s, l)).child(viewport(s, l, vw))
}

pub fn world_h(s: &App) -> f32 {
    s.nodes.iter().map(|n| n.pos[1] + n.height()).fold(0.0, f32::max) + 80.0
}

/// A compact on/off: a lamp and its name.
fn switch(l: &Look, key: &'static str, name: &'static str, on: bool, extra: Option<String>, flip: fn(&mut App)) -> El {
    let mut r = row()
        .key(key)
        .role("switch")
        .label(name)
        .checked(on)
        .focusable(true)
        .h(28.0)
        .px(10.0)
        .gap(8.0)
        .center_y()
        .radius(2.0)
        .fill(l.module)
        .border(1.0, if on { l.green.alpha(0.3) } else { l.line_strong })
        .hover(l.hover)
        .on_press(flip)
        .child(crate::widgets::lamp(l.green, 7.0, on))
        .child(text(name).font(ty::LABEL).text_case(TextCase::Uppercase).color(if on { l.label } else { l.dim }).a11y_hidden());
    if let Some(v) = extra {
        r = r.child(text(v).font(ty::VALUE_SMALL).color(if on { l.cyan } else { l.faint }).a11y_hidden());
    }
    r
}

fn toolbar(s: &App, l: &Look) -> El {
    row()
        .key("graph-toolbar")
        .w_full()
        .h(46.0)
        .px(12.0)
        .gap(8.0)
        .center_y()
        .fill(l.bezel)
        .border_sides([0.0, 0.0, 1.0, 0.0], l.line_strong)
        .child(text("GRAPH").font(ty::CAPS).color(l.label).mr(6.0))
        .child(el().w(228.0).child(selector(l, "filter", &["All", "Patched", "Patch"], s.filter, |s, i| s.filter = i)))
        .child(el().w(6.0))
        .child(switch(l, "behind", "Behind", s.behind, Some(format!("{:.0}%", s.behind_opacity * 100.0)), |s| s.behind ^= true))
        .child(switch(l, "pictures", "Pictures", s.pictures, None, |s| s.pictures ^= true))
        .child(switch(l, "tint", "Signal colour", s.tint, None, |s| s.tint ^= true))
        .child(el().grow(1.0))
        .child(push(l, "expand", "Expand", l.label, |_| {}))
        .child(push(l, "tidy", "Tidy", l.label, |s| s.tidy()))
}

/// The pan's range: the canvas never leaves the viewport entirely.
pub fn pan_limit(x: f32, vw: f32) -> f32 {
    x.clamp(-(data::world_w() - vw).max(0.0), 0.0)
}

fn viewport(s: &App, l: &Look, vw: f32) -> El {
    let world_h = world_h(s);
    let ww = data::world_w();
    let mut world = el()
        .key("world")
        .size(ww, world_h)
        .absolute(s.pan[0], s.pan[1])
        .motion(motion::SNAPPY)
        .child(rune::memo("grid", world_h.to_bits(), || canvas(grid(l, ww, world_h)).key("grid").size(ww, world_h).absolute(0.0, 0.0)));
    for c in Cat::ALL {
        world = world.child(column(s, l, c, world_h));
    }
    world = world.child(canvas(cables(s, l)).key("cables").size(ww, world_h).absolute(0.0, 0.0));
    // A module changes only when it moves, is selected or the filter fades it: rebuild it then.
    for (i, n) in s.nodes.iter().enumerate() {
        let version = (n.pos.map(f32::to_bits), s.selected == Some(i), faded(s, i, n), s.pictures, s.tint);
        world = world.child(rune::memo(format!("node-{}", n.id), version, || node(s, l, i, n)));
    }
    let size = 640.0;
    let pose = Pose::at(s.t, 0.4 + s.speed * 1.6);
    let backdrop = col()
        .key("program-behind")
        .absolute(0.0, 0.0)
        .w_full()
        .h_full()
        .center()
        .opacity(if s.behind { 0.2 + s.behind_opacity * 0.5 } else { 0.0 })
        .motion(motion::CALM)
        .child(canvas(polytope::wire(&s.shape_poly, &pose, size, l.green, 1.3)).key("wire").size(size, size))
        .a11y_hidden();
    el().key("viewport")
        .grow(1.0)
        .w_full()
        .min_h(0.0)
        .clip_soft(0.0)
        .on_drag(move |s: &mut App, d: &mut Drag, tx| match d.phase {
            Phase::Down => s.pan0 = s.pan,
            Phase::Move => {
                s.pan = [pan_limit(s.pan0[0] + d.dx, vw), (s.pan0[1] + d.dy).clamp(-600.0, 0.0)];
                tx.instant();
            }
            Phase::Up => {}
        })
        .on_press(|s: &mut App| s.selected = None)
        .child(backdrop)
        .child(world)
        .child(
            row()
                .key("foot")
                .absolute(0.0, 0.0)
                .w_full()
                .h_full()
                .items_end()
                .padding(12.0)
                .child(hints(l))
                .child(el().grow(1.0))
                .child(nav(s, l, vw, world_h)),
        )
}

/// The whole canvas in small, as a navigation display: every module, and the viewport's box.
/// A press or drag on it moves the viewport there.
fn nav(s: &App, l: &Look, vw: f32, world_h: f32) -> El {
    let (mw, mh) = (180.0, 92.0);
    let (kx, ky) = (mw / data::world_w(), mh / world_h);
    let mut map = el().key("map").size(mw, mh);
    for (i, n) in s.nodes.iter().enumerate() {
        let sel = s.selected == Some(i);
        map = map.child(
            el().key(format!("mm-{}", n.id))
                .absolute(n.pos[0] * kx, n.pos[1] * ky)
                .size(NODE_W * kx, (n.height() * ky).max(3.0))
                .fill(if sel { l.cyan } else { l.label.alpha(0.18) })
                .border(1.0, if sel { l.cyan } else { l.label.alpha(0.3) })
                .a11y_hidden(),
        );
    }
    let top = (-s.pan[1] * ky).max(0.0);
    map = map.child(
        el().key("view")
            .absolute(-s.pan[0] * kx, top)
            .size((vw * kx).min(mw), mh - top)
            .border(1.2, l.cyan)
            .motion(motion::SNAPPY)
            .a11y_hidden(),
    );
    col()
        .key("minimap")
        .role("button")
        .label("Navigation display")
        .padding(8.0)
        .gap(6.0)
        .radius(2.0)
        .fill(l.module.alpha(0.94))
        .border(1.0, l.line_strong)
        .shadow(6.0, 18.0, Color::BLACK.alpha(0.5))
        .on_drag(move |s: &mut App, d: &mut Drag, tx| {
            if matches!(d.phase, Phase::Down | Phase::Move) {
                let x = (d.x - 8.0) / kx - vw / 2.0;
                s.pan[0] = pan_limit(-x, vw);
                if d.phase == Phase::Down {
                    tx.motion(Spring::new(0.45, 0.0));
                } else {
                    tx.instant();
                }
            }
        })
        .child(
            row()
                .w_full()
                .justify_between()
                .child(text("NAV").font(ty::CAPS).color(l.label))
                .child(text(format!("COL {:02}–{:02}", first_col(s) + 1, (first_col(s) + (vw / PITCH) as usize).min(8))).font(ty::VALUE_SMALL).color(l.green)),
        )
        .child(el().key("screen").size(mw, mh).fill(l.glass).border(1.0, l.line).child(map))
}

fn first_col(s: &App) -> usize {
    ((-s.pan[0]) / PITCH).round().clamp(0.0, 7.0) as usize
}

/// The canvas's controls, as a memo line along its foot.
fn hints(l: &Look) -> El {
    let hint = |k: &'static str, what: &'static str| {
        row()
            .gap(6.0)
            .center_y()
            .child(row().h(16.0).px(5.0).center().radius(2.0).border(1.0, l.line_strong).child(text(k).font(ty::VALUE_SMALL).color(l.dim)))
            .child(text(what).font(ty::VALUE_SMALL).color(l.faint))
    };
    row()
        .key("hints")
        .gap(14.0)
        .child(hint("DRAG", "PIN TO PIN: CABLE"))
        .child(hint("⌥ DRAG", "SELECT CABLES"))
        .child(hint("RMB", "LEARN · INSERT · ADD"))
        .child(hint("⌫", "DELETE"))
        .a11y_hidden()
}

fn grid(l: &Look, w: f32, h: f32) -> Shape {
    let step = 48.0;
    let mut sh = Shape::new();
    let mut y = step;
    while y < h {
        let mut x = step;
        while x < w {
            sh = cross(sh, x, y, 3.0, l.grid);
            x += step;
        }
        y += step;
    }
    sh
}

/// A column's heading and the rule between it and the next.
fn column(s: &App, l: &Look, c: Cat, h: f32) -> El {
    let x = data::column_x(c);
    let n = s.nodes.iter().filter(|n| n.cat == c).count();
    let gap = PITCH - NODE_W;
    let mut e = el()
        .key(format!("col-{}", c.name()))
        .absolute(x, 0.0)
        .size(NODE_W, h)
        .child(
            row()
                .key("head")
                .absolute(0.0, 22.0)
                .w(NODE_W)
                .gap(8.0)
                .center_y()
                .pb(6.0)
                .border_sides([0.0, 0.0, 1.0, 0.0], l.line_strong)
                .child(text(format!("{:02}", c.index() + 1)).font(ty::VALUE_SMALL).color(l.faint))
                .child(text(c.name()).font(ty::COLUMN).text_case(TextCase::Uppercase).color(l.dim))
                .child(el().grow(1.0))
                .child(text(format!("{n}")).font(ty::VALUE_SMALL).color(l.faint)),
        );
    if c != Cat::Outputs {
        e = e.child(el().key("rule").absolute(NODE_W + gap / 2.0, 22.0).size(1.0, h - 44.0).fill(l.line));
    }
    e.a11y_hidden()
}

fn faded(s: &App, i: usize, n: &Node) -> bool {
    match s.filter {
        1 => !s.cables.iter().any(|c| c.from.0 == i || c.to.0 == i),
        2 => n.cat == Cat::Controllers,
        _ => false,
    }
}

/// A port's state: unwired, wired and dormant, or carrying a live signal.
fn pin_state(s: &App, i: usize, r: usize, input: bool) -> Option<bool> {
    let wired = s.cables.iter().filter(|c| if input { c.to == (i, r) } else { c.from == (i, r) });
    wired.fold(None, |acc, c| Some(acc.unwrap_or(false) || c.live))
}

fn node(s: &App, l: &Look, i: usize, n: &Node) -> El {
    let selected = s.selected == Some(i);
    let (word, ink) = match n.status {
        Status::Live => ("LIVE", l.green),
        Status::Idle => ("IDLE", l.faint),
        Status::Missing(_) => ("FAULT", l.amber),
    };
    let mut card = col()
        .key(format!("node-{}", n.id))
        .role("group")
        .label(n.title)
        .absolute(n.pos[0], n.pos[1])
        .w(NODE_W)
        .h(n.height())
        .radius(2.0)
        .fill(l.module)
        .border(1.0, if selected { l.cyan } else { l.line_strong })
        .shadow(8.0, 20.0, Color::BLACK.alpha(0.5))
        .opacity(if faded(s, i, n) { 0.3 } else { 1.0 })
        .motion(motion::SNAPPY)
        .on_press(move |s: &mut App| s.selected = Some(i));
    if selected {
        card = card.shadow(0.0, 14.0, l.cyan.alpha(0.25));
    }
    let header = row()
        .key("header")
        .w_full()
        .h(HEADER)
        .px(8.0)
        .gap(7.0)
        .center_y()
        .fill(l.bezel)
        .border_sides([0.0, 0.0, 1.0, 0.0], l.line_strong)
        .on_drag(move |s: &mut App, d: &mut Drag, tx| match d.phase {
            Phase::Down => {
                s.drag0 = s.nodes[i].pos;
                s.selected = Some(i);
            }
            Phase::Move => {
                s.nodes[i].pos = [s.drag0[0] + d.dx, (s.drag0[1] + d.dy).max(48.0)];
                tx.instant();
            }
            Phase::Up => {}
        })
        .child(text(n.cat.code()).font(ty::CODE).color(l.faint))
        .child(text(n.title).font(ty::NODE).text_case(TextCase::Uppercase).color(l.label).truncate())
        .child(el().grow(1.0))
        .child(state_word(word, ink));
    card = card.child(header);
    if n.thumb && s.pictures {
        card = card.child(
            el().key("thumb")
                .size(NODE_W - 16.0, THUMB)
                .mx(8.0)
                .mt(4.0)
                .mb(4.0)
                .child(canvas(faces(NODE_W - 16.0, THUMB)).size(NODE_W - 16.0, THUMB))
                .child(brackets(NODE_W - 16.0, THUMB, 8.0, l.green.alpha(0.8))),
        );
    }
    let mut ports = col().key("ports").w_full();
    for r in 0..n.rows() {
        let mut line = row().key(format!("p{r}")).w_full().h(ROW).px(12.0).center_y().justify_between();
        line = line.child(text(n.ins.get(r).copied().unwrap_or("")).font(ty::VALUE_SMALL).color(l.dim));
        line = line.child(text(n.outs.get(r).copied().unwrap_or("")).font(ty::VALUE_SMALL).color(l.dim));
        if r < n.ins.len() {
            line = line.child(pin(l, -4.0, pin_state(s, i, r, true)));
        }
        if r < n.outs.len() {
            line = line.child(pin(l, NODE_W - 4.0, pin_state(s, i, r, false)));
        }
        ports = ports.child(line);
    }
    card = card.child(ports.pt(data::PORTS_PAD).pb(data::PORTS_PAD));
    let (ink, words) = match n.status {
        Status::Missing(why) => (l.amber, why),
        _ => (l.faint, n.detail),
    };
    card.child(
        row()
            .key("footer")
            .w_full()
            .h(FOOTER)
            .px(10.0)
            .center_y()
            .border_sides([1.0, 0.0, 0.0, 0.0], l.line)
            .child(text(words.to_uppercase()).font(ty::VALUE_SMALL).color(ink).truncate()),
    )
}

/// A port: a small square on the module's edge, filled green while a live signal passes.
fn pin(l: &Look, x: f32, state: Option<bool>) -> El {
    let (fill, edge) = match state {
        None => (l.glass, l.faint),
        Some(false) => (l.glass, l.label.alpha(0.7)),
        Some(true) => (l.green, l.green),
    };
    el().size(8.0, 8.0).absolute(x, (ROW - 8.0) / 2.0).radius(1.0).fill(fill).border(1.5, edge).a11y_hidden()
}

/// Cables as cubic curves out of a port's right and into one's left, coloured by what they
/// carry; live ones carry a moving dot.
fn cables(s: &App, l: &Look) -> Shape {
    let mut sh = Shape::new();
    for (ci, c) in s.cables.iter().enumerate() {
        let (a, b) = (s.nodes[c.from.0].out_at(c.from.1), s.nodes[c.to.0].in_at(c.to.1));
        let dx = ((b[0] - a[0]).abs() * 0.5).max(56.0);
        let (c1, c2) = ([a[0] + dx, a[1]], [b[0] - dx, b[1]]);
        let path = Path::new().move_to(a).cubic_to(c1, c2, b);
        let hot = s.selected.is_some_and(|i| c.from.0 == i || c.to.0 == i);
        let modulation = s.nodes[c.from.0].cat == Cat::Modulation;
        let ink = match (hot, s.tint, modulation, c.live) {
            (true, _, _, _) => l.cyan,
            (false, false, _, _) => l.label,
            (false, true, true, _) => l.magenta,
            (false, true, false, true) => l.green,
            (false, true, false, false) => l.dim,
        };
        let dim = faded(s, c.from.0, &s.nodes[c.from.0]) || faded(s, c.to.0, &s.nodes[c.to.0]);
        let (w, a_) = match (hot, c.live) {
            (true, _) => (1.8, 1.0),
            (false, true) => (1.3, 0.7),
            (false, false) => (1.0, 0.3),
        };
        let a_ = if dim { a_ * 0.3 } else { a_ };
        if hot {
            sh = sh.stroke_path(&path, w + 5.0, LineCap::Round, ink.alpha(0.12));
        }
        sh = sh.stroke_path(&path, w, LineCap::Round, ink.alpha(a_));
        if c.live && !dim {
            let u = (s.t * 0.35 + ci as f32 * 0.137).fract();
            let p = bezier(a, c1, c2, b, u);
            sh = sh.line(p, [p[0] + 0.01, p[1]], 4.0, LineCap::Butt, ink);
        }
    }
    sh
}

fn bezier(a: [f32; 2], b: [f32; 2], c: [f32; 2], d: [f32; 2], t: f32) -> [f32; 2] {
    let u = 1.0 - t;
    let k = [u * u * u, 3.0 * u * u * t, 3.0 * u * t * t, t * t * t];
    [0, 1].map(|i| k[0] * a[i] + k[1] * b[i] + k[2] * c[i] + k[3] * d[i])
}

/// The faces pattern's thumbnail, as a monochrome display shows a picture: triangles in
/// shades of the screen's green.
pub fn faces(w: f32, h: f32) -> Shape {
    let (nx, ny) = (9, 5);
    let (cw, ch) = (w / nx as f32, h / ny as f32);
    let jitter = |i: i32, j: i32| {
        let s = ((i * 73 + j * 151) as f32 * 12.9898).sin() * 43758.545;
        [(s.fract() - 0.5) * 0.7, ((s * 1.7).fract() - 0.5) * 0.7]
    };
    let p = |i: i32, j: i32| {
        let jt = if i == 0 || j == 0 || i == nx || j == ny { [0.0, 0.0] } else { jitter(i, j) };
        [(i as f32 + jt[0]) * cw, (j as f32 + jt[1]) * ch]
    };
    let mut sh = Shape::new();
    for j in 0..ny {
        for i in 0..nx {
            for (k, tri) in [[p(i, j), p(i + 1, j), p(i, j + 1)], [p(i + 1, j), p(i + 1, j + 1), p(i, j + 1)]].into_iter().enumerate() {
                let seed = ((i * 31 + j * 17 + k as i32 * 7) as f32 * 3.7).sin().abs();
                sh = sh.fill(tri.to_vec(), rune::oklch(0.18 + seed * 0.42, 0.06 + seed * 0.08, 150.0));
            }
        }
    }
    sh
}
