//! The GRAPH: the patch as columns of nodes joined by cables, over the program output.
//!
//! The canvas pans by dragging its background, a node moves by its header, and the column
//! chips glide the canvas to a column on a spring.

use rune::tok::motion;
use rune::{Color, Drag, El, LineCap, Path, Phase, Shape, Spring, TextCase, canvas, col, el, row, text};
use rune_kit::{Button, ButtonVariant, ControlSize, Kit, SegmentedControl, Switch};

use crate::App;
use crate::data::{self, FOOTER, HEADER, NODE_W, Node, ROW, Status, THUMB};
use crate::polytope::{self, Pose};
use crate::theme::{Cat, Look, ty};
use crate::widgets::{dot, glow_dot};

/// `vw` is the viewport's width as last laid out, for the pan's range and the minimap.
pub fn pane(s: &App, l: &Look, k: &Kit, vw: f32) -> El {
    col().key("graph").grow(1.0).min_w(0.0).h_full().fill(l.canvas).child(toolbar(s, l, k)).child(viewport(s, l, vw))
}

pub fn world_h(s: &App) -> f32 {
    s.nodes.iter().map(|n| n.pos[1] + n.height()).fold(0.0, f32::max) + 80.0
}

fn toolbar(s: &App, l: &Look, k: &Kit) -> El {
    let toggle = |key: &'static str, label: &'static str, on: bool, flip: fn(&mut App)| {
        Switch::new(on).label(label).on_toggle(flip).build(k).key(key)
    };
    let behind = row()
        .key("behind")
        .gap(10.0)
        .center_y()
        .child(Switch::new(s.behind).label("Output behind").on_toggle(|s: &mut App| s.behind = !s.behind).build(k))
        .child(
            text(format!("{:.0}%", s.behind_opacity * 100.0))
                .font(ty::VALUE)
                .color(if s.behind { l.text2 } else { l.text3 }),
        );
    row()
        .key("graph-toolbar")
        .w_full()
        .h(48.0)
        .px(14.0)
        .gap(14.0)
        .center_y()
        .fill(l.panel)
        .border_sides([0.0, 0.0, 1.0, 0.0], l.line)
        .child(
            SegmentedControl::new(&["All", "Patched", "Patch only"], Some(s.filter))
                .label("Show")
                .fit()
                .on_pick(|s: &mut App, i, _| s.filter = i)
                .build(k),
        )
        .child(rule(l))
        .child(behind)
        .child(rule(l))
        .child(toggle("pictures", "Pictures", s.pictures, |s| s.pictures ^= true))
        .child(toggle("tint", "Tint cables", s.tint, |s| s.tint ^= true))
        .child(el().grow(1.0))
        .child(
            Button::new("Expand all")
                .variant(ButtonVariant::Ghost)
                .control_size(ControlSize::Small)
                .build(k),
        )
        .child(
            Button::new("Tidy")
                .variant(ButtonVariant::Outline)
                .control_size(ControlSize::Small)
                .on_press_tx(|s: &mut App, tx| {
                    s.tidy();
                    tx.motion(Spring::new(0.45, 0.1));
                })
                .build(k),
        )
}

fn rule(l: &Look) -> El {
    el().size(1.0, 20.0).fill(l.line_strong).a11y_hidden()
}

/// The pan's range: the canvas never leaves the viewport entirely.
pub fn pan_limit(x: f32, vw: f32) -> f32 {
    x.clamp(-(data::world_w() - vw).max(0.0), 0.0)
}

fn viewport(s: &App, l: &Look, vw: f32) -> El {
    let world_h = world_h(s);
    let mut world = el()
        .key("world")
        .size(data::world_w(), world_h)
        .absolute(s.pan[0], s.pan[1])
        .motion(motion::SNAPPY)
        .child(rune::memo("grid", world_h.to_bits(), || {
            canvas(grid(l, data::world_w(), world_h)).key("grid").size(data::world_w(), world_h).absolute(0.0, 0.0)
        }));
    for c in Cat::ALL {
        world = world.child(column(s, l, c, world_h));
    }
    world = world.child(canvas(cables(s, l)).key("cables").size(data::world_w(), world_h).absolute(0.0, 0.0));
    // A card changes only when it moves, is selected or the filter fades it: rebuild it then.
    for (i, n) in s.nodes.iter().enumerate() {
        let version = (n.pos.map(f32::to_bits), s.selected == Some(i), faded(s, i, n), s.pictures);
        world = world.child(rune::memo(format!("card-{}", n.id), version, || node(s, l, i, n)));
    }
    let size = 640.0;
    let pose = Pose::at(s.t, 0.4 + s.speed * 1.6);
    let backdrop = col()
        .key("program-behind")
        .absolute(0.0, 0.0)
        .w_full()
        .h_full()
        .center()
        .opacity(if s.behind { 0.35 + s.behind_opacity * 0.65 } else { 0.0 })
        .motion(motion::CALM)
        .child(canvas(polytope::wire(&s.shape_poly, &pose, size, l.text, 1.4)).key("wire").size(size, size))
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
                .padding(14.0)
                .child(hints(l))
                .child(el().grow(1.0))
                .child(minimap(s, l, vw, world_h)),
        )
}

/// The whole canvas in small: every node, and the part the viewport shows. A press on it
/// glides the viewport there.
fn minimap(s: &App, l: &Look, vw: f32, world_h: f32) -> El {
    let (mw, mh) = (176.0, 92.0);
    let (kx, ky) = (mw / data::world_w(), mh / world_h);
    let mut map = el().key("map").size(mw, mh);
    for n in &s.nodes {
        map = map.child(
            el().key(format!("mm-{}", n.id))
                .absolute(n.pos[0] * kx, n.pos[1] * ky)
                .size(NODE_W * kx, (n.height() * ky).max(3.0))
                .radius(2.0)
                .fill(n.cat.hue().alpha(if s.selected.is_some_and(|i| s.nodes[i].id == n.id) { 0.95 } else { 0.45 }))
                .a11y_hidden(),
        );
    }
    let view_w = (vw * kx).min(mw);
    map = map.child(
        el().key("view")
            .absolute(-s.pan[0] * kx, (-s.pan[1] * ky).max(0.0))
            .size(view_w, mh - (-s.pan[1] * ky).max(0.0))
            .radius(4.0)
            .fill(l.accent.alpha(0.06))
            .border(1.5, l.accent.alpha(0.8))
            .motion(motion::SNAPPY)
            .a11y_hidden(),
    );
    col()
        .key("minimap")
        .role("button")
        .label("Minimap")
        .padding(8.0)
        .gap(6.0)
        .radius(10.0)
        .fill(l.panel.alpha(0.92))
        .border(1.0, l.line_strong)
        .shadow(8.0, 24.0, Color::BLACK.alpha(0.4))
        .on_drag(move |s: &mut App, d: &mut Drag, tx| {
            if matches!(d.phase, Phase::Down | Phase::Move) {
                // Centre the viewport on the point pressed.
                let x = (d.x - 8.0) / kx - vw / 2.0;
                s.pan[0] = pan_limit(-x, vw);
                if d.phase == Phase::Down {
                    tx.motion(Spring::new(0.45, 0.0));
                } else {
                    tx.instant();
                }
            }
        })
        .child(map)
        .child(
            row()
                .w_full()
                .justify_between()
                .child(text("CONTROLLERS").font(ty::VALUE_SMALL).color(l.text3))
                .child(text("OUTPUTS").font(ty::VALUE_SMALL).color(l.text3)),
        )
}

/// What the canvas takes, along its foot.
fn hints(l: &Look) -> El {
    let hint = |k: &'static str, what: &'static str| {
        row()
            .gap(6.0)
            .center_y()
            .child(
                row()
                    .h(18.0)
                    .px(6.0)
                    .center()
                    .radius(4.0)
                    .fill(l.raised)
                    .border(1.0, l.line_strong)
                    .child(text(k).font(ty::VALUE_SMALL).color(l.text2)),
            )
            .child(text(what).font(ty::SMALL).color(l.text3))
    };
    col()
        .key("hints")
        .child(
            row()
                .gap(16.0)
                .child(hint("drag", "pin to pin: a cable"))
                .child(hint("⌥ drag", "select cables"))
                .child(hint("right-click", "Learn, insert, add"))
                .child(hint("⌫", "delete the selection")),
        )
        .a11y_hidden()
}

fn grid(l: &Look, w: f32, h: f32) -> Shape {
    let step = 24.0;
    let mut sh = Shape::new();
    let mut y = step;
    while y < h {
        let mut x = step;
        while x < w {
            sh = sh.line([x, y], [x + 0.01, y], 1.5, LineCap::Round, l.grid);
            x += step;
        }
        y += step;
    }
    sh
}

/// A column's band and its heading.
fn column(s: &App, l: &Look, c: Cat, h: f32) -> El {
    let x = data::column_x(c);
    let n = s.nodes.iter().filter(|n| n.cat == c).count();
    el().key(format!("col-{}", c.name()))
        .absolute(x - 12.0, 12.0)
        .size(NODE_W + 24.0, h - 24.0)
        .radius(14.0)
        .fill(if c.index() % 2 == 0 { Color::WHITE.alpha(0.012) } else { Color::TRANSPARENT })
        .child(
            row()
                .key("head")
                .absolute(12.0, 14.0)
                .gap(8.0)
                .center_y()
                .child(dot(c.hue(), 6.0))
                .child(text(c.name()).font(ty::COLUMN).text_case(TextCase::Uppercase).color(c.hue().mix(l.text, 0.45)))
                .child(text(format!("{n}")).font(ty::VALUE_SMALL).color(l.text3)),
        )
        .a11y_hidden()
}

fn faded(s: &App, i: usize, n: &Node) -> bool {
    match s.filter {
        1 => !s.cables.iter().any(|c| c.from.0 == i || c.to.0 == i),
        2 => n.cat == Cat::Controllers,
        _ => false,
    }
}

fn node(s: &App, l: &Look, i: usize, n: &Node) -> El {
    let selected = s.selected == Some(i);
    let hue = n.cat.hue();
    let mut card = col()
        .key(format!("node-{}", n.id))
        .role("group")
        .label(n.title)
        .absolute(n.pos[0], n.pos[1])
        .w(NODE_W)
        .h(n.height())
        .radius(10.0)
        .fill(l.raised.alpha(0.94))
        .border(1.0, if selected { l.accent } else { l.line_strong })
        .shadow(10.0, 28.0, Color::BLACK.alpha(0.35))
        .shadow(1.0, 2.0, Color::BLACK.alpha(0.4))
        .opacity(if faded(s, i, n) { 0.3 } else { 1.0 })
        .motion(motion::SNAPPY)
        .on_press(move |s: &mut App| s.selected = Some(i));
    if selected {
        card = card.box_shadow(rune::Shadow { y: 0.0, blur: 0.0, spread: 3.0, color: l.accent.alpha(0.18), ..Default::default() });
    }
    let light = match n.status {
        Status::Live => glow_dot(l.ok, 7.0),
        Status::Idle => dot(l.text3.alpha(0.6), 7.0),
        Status::Missing(_) => glow_dot(l.warn, 7.0),
    };
    let header = row()
        .key("header")
        .w_full()
        .h(HEADER)
        .px(10.0)
        .gap(8.0)
        .center_y()
        .corners([10.0, 10.0, 0.0, 0.0])
        .gradient(hue.alpha(0.13), hue.alpha(0.03))
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
        .child(el().size(3.0, 14.0).radius(1.5).fill(hue).a11y_hidden())
        .child(text(n.title).font(ty::NODE).color(l.text).truncate())
        .child(el().grow(1.0))
        .child(light);
    card = card.child(header);
    if n.thumb && s.pictures {
        card = card.child(
            canvas(faces(0.0, NODE_W - 20.0, THUMB)).key("thumb").size(NODE_W - 20.0, THUMB).mx(10.0).mt(4.0).mb(4.0).radius(6.0).clip_soft(0.0),
        );
    }
    let mut ports = col().key("ports").w_full();
    for r in 0..n.rows() {
        let mut line = row().key(format!("p{r}")).w_full().h(ROW).px(12.0).center_y().justify_between();
        line = line.child(text(n.ins.get(r).copied().unwrap_or("")).font(ty::SMALL).color(l.text2));
        line = line.child(text(n.outs.get(r).copied().unwrap_or("")).font(ty::SMALL).color(l.text2));
        if r < n.ins.len() {
            line = line.child(pin(l, hue, -4.5));
        }
        if r < n.outs.len() {
            line = line.child(pin(l, hue, NODE_W - 4.5));
        }
        ports = ports.child(line);
    }
    card = card.child(ports.pt(2.0).pb(4.0));
    let (ink, words) = match n.status {
        Status::Missing(why) => (l.warn, why),
        _ => (l.text3, n.detail),
    };
    card.child(
        row()
            .key("footer")
            .w_full()
            .h(FOOTER)
            .px(12.0)
            .center_y()
            .border_sides([1.0, 0.0, 0.0, 0.0], l.line)
            .child(text(words).font(ty::SMALL).color(ink).truncate()),
    )
}

/// A port: a ring on the card's edge, filled when something is wired to it.
fn pin(l: &Look, hue: Color, x: f32) -> El {
    el().size(9.0, 9.0).absolute(x, (ROW - 9.0) / 2.0).radius(4.5).fill(l.canvas).border(2.0, hue).a11y_hidden()
}

/// Cables as cubic curves out of a port's right and into one's left. Live ones carry a pulse;
/// the selection's cables light up in the accent.
fn cables(s: &App, l: &Look) -> Shape {
    let mut sh = Shape::new();
    for (ci, c) in s.cables.iter().enumerate() {
        let (a, b) = (s.nodes[c.from.0].out_at(c.from.1), s.nodes[c.to.0].in_at(c.to.1));
        let dx = ((b[0] - a[0]).abs() * 0.5).max(56.0);
        let (c1, c2) = ([a[0] + dx, a[1]], [b[0] - dx, b[1]]);
        let path = Path::new().move_to(a).cubic_to(c1, c2, b);
        let hot = s.selected.is_some_and(|i| c.from.0 == i || c.to.0 == i);
        let ink = match (hot, s.tint) {
            (true, _) => l.accent,
            (false, true) => s.nodes[c.from.0].cat.hue(),
            (false, false) => l.text2,
        };
        let dim = faded(s, c.from.0, &s.nodes[c.from.0]) || faded(s, c.to.0, &s.nodes[c.to.0]);
        let (w, a_) = match (hot, c.live) {
            (true, _) => (2.2, 0.95),
            (false, true) => (1.6, 0.62),
            (false, false) => (1.3, 0.22),
        };
        let a_ = if dim { a_ * 0.3 } else { a_ };
        if hot || c.live {
            sh = sh.stroke_path(&path, w + 6.0, LineCap::Round, ink.alpha(a_ * 0.12));
        }
        sh = sh.stroke_path(&path, w, LineCap::Round, ink.alpha(a_));
        if c.live && !dim {
            let u = (s.t * 0.35 + ci as f32 * 0.137).fract();
            let p = bezier(a, c1, c2, b, u);
            sh = sh.line(p, [p[0] + 0.01, p[1]], 5.0, LineCap::Round, ink.mix(Color::WHITE, 0.5).alpha(0.9));
        }
    }
    sh
}

fn bezier(a: [f32; 2], b: [f32; 2], c: [f32; 2], d: [f32; 2], t: f32) -> [f32; 2] {
    let u = 1.0 - t;
    let k = [u * u * u, 3.0 * u * u * t, 3.0 * u * t * t, t * t * t];
    [0, 1].map(|i| k[0] * a[i] + k[1] * b[i] + k[2] * c[i] + k[3] * d[i])
}

/// The faces pattern's thumbnail: a field of tinted triangles that shifts with time.
pub fn faces(t: f32, w: f32, h: f32) -> Shape {
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
                let hue = (seed * 360.0 + t * 20.0) % 360.0;
                sh = sh.fill(tri.to_vec(), rune::oklch(0.62 + seed * 0.12, 0.14, hue));
            }
        }
    }
    sh
}
