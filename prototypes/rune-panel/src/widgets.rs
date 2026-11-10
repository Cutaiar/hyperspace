//! The panel's instruments: a tape gauge with a pointer, annunciator push-buttons, a selector,
//! a segmented level meter, readouts, lamps and the module sections. Every one paints from
//! `Look`, and its colour says what the value is: cyan set by you, magenta driven, green
//! measured.

use rune::tok::motion;
use rune::{Align, Color, Drag, El, LineCap, Phase, Shape, TextCase, canvas, col, el, row, text};

use crate::App;
use crate::theme::{Look, ty};

/// Which value a control edits.
pub type Field = fn(&mut App) -> &mut f32;

/// Whose value it is, which sets its colour.
#[derive(Clone, Copy, PartialEq)]
pub enum Source {
    /// Set by the operator: cyan.
    Set,
    /// Driven by automation (an LFO, an envelope): magenta.
    Driven,
}

pub struct Gauge {
    pub key: &'static str,
    pub label: &'static str,
    /// 0..1 along the tape.
    pub value: f32,
    pub readout: String,
    pub field: Field,
    /// Fills from the middle (a signed value: yaw, pan).
    pub bipolar: bool,
    pub source: Source,
}

impl Gauge {
    pub fn new(key: &'static str, label: &'static str, value: f32, readout: String, field: Field) -> Gauge {
        Gauge { key, label, value, readout, field, bipolar: false, source: Source::Set }
    }
    pub fn bipolar(mut self) -> Self {
        self.bipolar = true;
        self
    }
    pub fn driven(mut self) -> Self {
        self.source = Source::Driven;
        self
    }

    fn ink(&self, l: &Look) -> Color {
        match self.source {
            Source::Set => l.set,
            Source::Driven => l.driven,
        }
    }

    /// The legend and readout on one line, the tape under them.
    pub fn build(self, l: &Look) -> El {
        let ink = self.ink(l);
        let tape = tape(l, self.label, self.value, self.field, self.bipolar, ink);
        col()
            .key(self.key)
            .w_full()
            .gap(5.0)
            .child(
                row()
                    .w_full()
                    .h(20.0)
                    .justify_between()
                    .center_y()
                    .child(legend(l, self.label))
                    .child(readout(l, self.readout, ink, 64.0)),
            )
            .child(tape)
    }

    /// Legend, tape and readout on one row: denser, for a column of camera values.
    pub fn build_inline(self, l: &Look) -> El {
        let ink = self.ink(l);
        let tape = tape(l, self.label, self.value, self.field, self.bipolar, ink);
        row()
            .key(self.key)
            .w_full()
            .h(26.0)
            .gap(10.0)
            .center_y()
            .child(legend(l, self.label).w(48.0))
            .child(col().grow(1.0).min_w(0.0).child(tape))
            .child(readout(l, self.readout, ink, 64.0))
    }
}

/// A control's legend: white capitals.
pub fn legend(l: &Look, s: &'static str) -> El {
    text(s).font(ty::LABEL).text_case(TextCase::Uppercase).color(l.dim).a11y_hidden()
}

/// A boxed digital readout.
pub fn readout(l: &Look, s: String, ink: Color, w: f32) -> El {
    row()
        .key("readout")
        .w(w)
        .h(20.0)
        .px(6.0)
        .center_y()
        .justify_end()
        .radius(2.0)
        .fill(l.glass)
        .border(1.0, l.line)
        .child(text(s).font(ty::VALUE).color(ink).align(Align::End).a11y_hidden())
}

const TAPE_H: f32 = 22.0;
/// The tape's inset: the pointer's travel starts and ends this far in.
const INSET: f32 = 6.0;

/// A tape as wide as its parent: a scale of ticks, a bar to the value and a pointer on it.
/// Every mark sits in a row of flex spacers grown in proportion, so it lands at its fraction
/// whatever width the tape gets; a drag reads the width from the gesture.
fn tape(l: &Look, label: &'static str, v: f32, field: Field, bipolar: bool, ink: Color) -> El {
    let v = v.clamp(0.0, 1.0);
    let travel = |w: f32| (w - 2.0 * INSET).max(1.0);
    let to_value = move |x: f32, w: f32| ((x - INSET) / travel(w)).clamp(0.0, 1.0);
    let (lo, hi) = if bipolar { (v.min(0.5), v.max(0.5)) } else { (0.0, v) };
    let mut ticks = row().key("ticks").w_full().absolute(0.0, 0.0).h(TAPE_H).px(INSET).justify_between().items_end().pb(3.0);
    for i in 0..=20 {
        let major = i % 5 == 0;
        ticks = ticks.child(
            el().key(format!("t{i}"))
                .size(1.0, if major { 7.0 } else { 3.0 })
                .fill(if major { l.dim.alpha(0.7) } else { l.faint.alpha(0.6) })
                .a11y_hidden(),
        );
    }
    let span = |k: &'static str, y: f32, before: f32, item: El, after: f32, pad: f32| {
        row()
            .key(k)
            .w_full()
            .absolute(0.0, y)
            .px(pad)
            .child(el().key("a").grow(before).a11y_hidden())
            .child(item)
            .child(el().key("b").grow(after).a11y_hidden())
            .a11y_hidden()
    };
    let pointer = col()
        .key("ptr")
        .w(9.0)
        .items_center()
        .child(canvas(Shape::new().fill(vec![[0.0, 0.0], [9.0, 0.0], [4.5, 5.0]], ink)).size(9.0, 5.0))
        .child(el().size(1.5, TAPE_H - 7.0).fill(ink));
    el().key("tape")
        .role("slider")
        .label(label)
        .range_value(f64::from(v), 0.0, 1.0)
        .range_step(0.01)
        .on_step(move |s: &mut App, steps, _| {
            let f = field(s);
            *f = (*f + steps as f32 * 0.01).clamp(0.0, 1.0);
        })
        .focusable(true)
        .w_full()
        .h(TAPE_H)
        .radius(2.0)
        .fill(l.glass)
        .border(1.0, l.line)
        .clip_soft(0.0)
        .on_drag(move |s: &mut App, d: &mut Drag, tx| {
            let at = |val: f32| INSET + val * travel(d.w);
            match d.phase {
                Phase::Down => {
                    d.data = *field(s);
                    if (d.x - at(d.data)).abs() > 6.0 {
                        *field(s) = to_value(d.x, d.w);
                    }
                }
                Phase::Move => {
                    // A press on the pointer moves it by the drag; one away from it jumped there.
                    let base = if (d.start_x - at(d.data)).abs() > 6.0 { to_value(d.start_x, d.w) } else { d.data };
                    *field(s) = (base + d.dx / travel(d.w)).clamp(0.0, 1.0);
                    tx.instant();
                }
                Phase::Up => {
                    if d.cancelled() {
                        *field(s) = d.data;
                    }
                }
            }
        })
        .motion(motion::SNAPPY)
        .child(ticks)
        .child(span("bar", 4.0, lo, el().key("f").grow(hi - lo).h(3.0).fill(ink.alpha(0.55)), 1.0 - hi, INSET))
        .child(span("pointer", 1.0, v, pointer, 1.0 - v, INSET - 4.5))
}

/// An annunciator push-button: its name over a legend that lights when it's on.
pub fn annunciator(l: &Look, key: &'static str, name: &'static str, on: bool, lit: Color, flip: fn(&mut App)) -> El {
    col()
        .key(key)
        .role("switch")
        .label(name)
        .checked(on)
        .focusable(true)
        .grow(1.0)
        .min_w(0.0)
        .h(40.0)
        .gap(4.0)
        .center()
        .radius(2.0)
        .fill(if on { lit.alpha(0.07) } else { l.module })
        .border(1.0, if on { lit.alpha(0.35) } else { l.line_strong })
        .shadow(1.0, 0.0, Color::BLACK.alpha(0.5))
        .hover(l.hover)
        .press(Color::BLACK.alpha(0.2))
        .motion(motion::SNAPPY)
        .on_press(flip)
        .child(text(name).font(ty::LABEL).text_case(TextCase::Uppercase).color(l.label).a11y_hidden())
        .child(
            text(if on { "ON" } else { "OFF" })
                .key("legend")
                .font(ty::VALUE_BOLD)
                .color(if on { lit } else { l.faint })
                .a11y_hidden(),
        )
}

/// A row of push-buttons of which one is selected, as a mode selector.
pub fn selector(l: &Look, key: &'static str, options: &[&'static str], selected: usize, pick: fn(&mut App, usize)) -> El {
    let mut r = row().key(key).role("radiogroup").w_full().h(30.0).radius(2.0).fill(l.glass).border(1.0, l.line_strong).clip_soft(0.0);
    for (i, name) in options.iter().enumerate() {
        let on = i == selected;
        let mut seg = col()
            .key(*name)
            .role("radio")
            .label(*name)
            .checked(on)
            .focusable(true)
            .grow(1.0)
            .h_full()
            .center()
            .fill(if on { l.set.alpha(0.08) } else { Color::TRANSPARENT })
            .hover(l.hover)
            .on_press(move |s: &mut App| pick(s, i))
            .child(
                text(*name)
                    .font(ty::LABEL)
                    .text_case(TextCase::Uppercase)
                    .color(if on { l.set } else { l.dim })
                    .a11y_hidden(),
            )
            .child(
                el().key("bar")
                    .w(22.0)
                    .h(2.0)
                    .mt(4.0)
                    .fill(if on { l.set } else { Color::TRANSPARENT })
                    .shadow(0.0, if on { 6.0 } else { 0.0 }, l.set.alpha(0.6))
                    .a11y_hidden(),
            );
        if i > 0 {
            seg = seg.border_sides([0.0, 0.0, 0.0, 1.0], l.line_strong);
        }
        r = r.child(seg);
    }
    r
}

/// A module of the inspector: a numbered title bar that folds its body, and the values it
/// holds while folded.
#[allow(clippy::too_many_arguments)]
pub fn section(l: &Look, key: &'static str, n: usize, title: &'static str, summary: String, open: bool, toggle: fn(&mut App), body: El) -> El {
    let header = row()
        .key("header")
        .role("button")
        .label(title)
        .expanded(open)
        .focusable(true)
        .w_full()
        .h(34.0)
        .px(14.0)
        .gap(8.0)
        .center_y()
        .fill(l.bezel)
        .hover(l.hover)
        .on_press(toggle)
        .child(
            canvas(Shape::new().fill(vec![[0.0, 0.0], [7.0, 0.0], [3.5, 5.0]], l.dim))
                .key("caret")
                .size(7.0, 5.0)
                .rotate(if open { 0.0 } else { -std::f32::consts::FRAC_PI_2 })
                .motion(motion::SNAPPY)
                .a11y_hidden(),
        )
        .child(text(format!("{n:02}")).font(ty::VALUE_SMALL).color(l.faint).a11y_hidden())
        .child(text(title).font(ty::CAPS).text_case(TextCase::Uppercase).color(l.label).a11y_hidden())
        .child(el().grow(1.0))
        .child(text(summary).key("summary").font(ty::VALUE_SMALL).color(l.live).opacity(if open { 0.0 } else { 1.0 }).a11y_hidden());
    let mut s = col().key(key).w_full().border_sides([0.0, 0.0, 1.0, 0.0], l.line).child(header);
    if open {
        s = s.child(col().key("body").w_full().px(14.0).pt(12.0).pb(16.0).gap(12.0).border_sides([1.0, 0.0, 0.0, 0.0], l.line).child(body));
    }
    s
}

/// Capitals over a group of controls.
pub fn caps(l: &Look, s: &'static str) -> El {
    text(s).font(ty::CAPS).text_case(TextCase::Uppercase).color(l.dim)
}

/// A square status lamp; lit ones glow.
pub fn lamp(c: Color, d: f32, lit: bool) -> El {
    el().size(d, d)
        .radius(1.0)
        .fill(if lit { c } else { c.alpha(0.25) })
        .shadow(0.0, if lit { d * 1.4 } else { 0.0 }, c.alpha(0.6))
        .a11y_hidden()
}

/// A word on a status line: a short coloured state ("LIVE", "IDLE", "FAULT").
pub fn state_word(s: &'static str, c: Color) -> El {
    text(s).font(ty::VALUE_BOLD).color(c).a11y_hidden()
}

/// A segmented level meter `h` tall: green, then amber, then red at the top, with the held
/// peak lit on its own.
pub fn seg_meter(l: &Look, key: String, v: f32, peak: f32, w: f32, h: f32) -> El {
    const N: usize = 14;
    let gap = 2.0;
    let seg_h = (h - gap * (N as f32 - 1.0)) / N as f32;
    let lit = (v.clamp(0.0, 1.0) * N as f32).round() as usize;
    let pk = ((peak.clamp(0.0, 1.0) * N as f32).round() as usize).clamp(1, N) - 1;
    let mut m = col().key(key).w(w).h(h).gap(gap).a11y_hidden();
    for i in (0..N).rev() {
        let c = if i >= N - 2 {
            l.alert
        } else if i >= N - 4 {
            l.caution
        } else {
            l.live
        };
        let on = i < lit || i == pk;
        m = m.child(el().key(format!("s{i}")).w(w).h(seg_h).radius(1.0).fill(if on { c } else { c.alpha(0.09) }));
    }
    m
}

/// A key and value on one line, for read-only facts.
pub fn fact(l: &Look, k: &'static str, v: String) -> El {
    row()
        .w_full()
        .h(20.0)
        .justify_between()
        .center_y()
        .child(legend(l, k))
        .child(text(v).font(ty::VALUE).color(l.live))
}

/// A boxed tag: a short code in a thin frame.
pub fn tag(s: String, ink: Color) -> El {
    row().h(18.0).px(6.0).center().radius(2.0).border(1.0, ink.alpha(0.45)).child(text(s).font(ty::VALUE_SMALL).color(ink))
}

/// A flat push-button with a legend: SAVE, TAP, TAKE.
pub fn push(l: &Look, key: &'static str, name: &'static str, ink: Color, on_press: fn(&mut App)) -> El {
    row()
        .key(key)
        .role("button")
        .label(name)
        .focusable(true)
        .h(28.0)
        .px(12.0)
        .center()
        .radius(2.0)
        .fill(l.module)
        .border(1.0, l.line_strong)
        .shadow(1.0, 0.0, Color::BLACK.alpha(0.5))
        .hover(l.hover)
        .press(Color::BLACK.alpha(0.25))
        .on_press(on_press)
        .child(text(name).font(ty::LABEL_STRONG).text_case(TextCase::Uppercase).color(ink).a11y_hidden())
}

/// Corner brackets around a `w` × `h` screen, as a display's reticle frames it.
pub fn brackets(w: f32, h: f32, len: f32, c: Color) -> El {
    let (a, b) = (1.0, len);
    let sh = Shape::new()
        .stroke(vec![[a, b], [a, a], [b, a]], 1.2, c)
        .stroke(vec![[w - b, a], [w - a, a], [w - a, b]], 1.2, c)
        .stroke(vec![[a, h - b], [a, h - a], [b, h - a]], 1.2, c)
        .stroke(vec![[w - b, h - a], [w - a, h - a], [w - a, h - b]], 1.2, c);
    canvas(sh).key("brackets").size(w, h).absolute(0.0, 0.0).a11y_hidden()
}

/// A small cross, for the canvas's grid and the screens' centres.
pub fn cross(sh: Shape, x: f32, y: f32, r: f32, c: Color) -> Shape {
    sh.line([x - r, y], [x + r, y], 1.0, LineCap::Butt, c).line([x, y - r], [x, y + r], 1.0, LineCap::Butt, c)
}
