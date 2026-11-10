//! The panel's own controls, where rune-kit has none: a slider with a readout, a disclosure
//! section, a level meter, a status dot. Every one paints from `Look`.

use std::f32::consts::FRAC_PI_2;

use rune::tok::motion;
use rune::{Align, Color, Drag, El, Phase, TextCase, col, el, icon, row, text};
use rune_kit::glyphs;

use crate::App;
use crate::theme::{Look, ty};

/// Which value a control edits.
pub type Field = fn(&mut App) -> &mut f32;

pub struct Slider {
    pub key: &'static str,
    pub label: &'static str,
    /// 0..1 along the track.
    pub value: f32,
    pub readout: String,
    pub field: Field,
    /// Fills from the middle (a signed value: yaw, pan).
    pub bipolar: bool,
    /// Draws a tick at this point of the track (a detent, a default).
    pub tick: Option<f32>,
}

impl Slider {
    pub fn new(key: &'static str, label: &'static str, value: f32, readout: String, field: Field) -> Slider {
        Slider { key, label, value, readout, field, bipolar: false, tick: None }
    }
    pub fn bipolar(mut self) -> Self {
        self.bipolar = true;
        self.tick = Some(0.5);
        self
    }
    pub fn tick(mut self, at: f32) -> Self {
        self.tick = Some(at);
        self
    }

    /// The label and readout on one line, the track under them.
    pub fn build(self, l: &Look) -> El {
        let track = track(l, "track", self.label, self.value, self.field, self.bipolar, self.tick);
        col()
            .key(self.key)
            .w_full()
            .gap(6.0)
            .child(
                row()
                    .w_full()
                    .justify_between()
                    .center_y()
                    .child(text(self.label).font(ty::LABEL).color(l.text2).a11y_hidden())
                    .child(text(self.readout).key("readout").font(ty::VALUE).color(l.text).align(Align::End).a11y_hidden()),
            )
            .child(track)
    }

    /// Label, track and readout on one row: denser, for a list of camera values.
    pub fn build_inline(self, l: &Look) -> El {
        let track = track(l, "track", self.label, self.value, self.field, self.bipolar, self.tick);
        row()
            .key(self.key)
            .w_full()
            .h(24.0)
            .gap(10.0)
            .center_y()
            .child(text(self.label).font(ty::LABEL).color(l.text2).w(64.0).a11y_hidden())
            .child(col().grow(1.0).min_w(0.0).child(track))
            .child(text(self.readout).key("readout").font(ty::VALUE).color(l.text).w(52.0).align(Align::End).a11y_hidden())
    }
}

const KNOB: f32 = 13.0;
const BAR: f32 = 4.0;
const HIT: f32 = 18.0;

/// A track as wide as its parent. The knob and fill sit in rows of flex spacers grown in
/// proportion to the value, so they land at the right fraction whatever width the track gets;
/// the drag reads the track's width from the gesture.
#[allow(clippy::too_many_arguments)]
fn track(l: &Look, key: &'static str, label: &'static str, v: f32, field: Field, bipolar: bool, tick: Option<f32>) -> El {
    let to_value = move |x: f32, w: f32| ((x - KNOB / 2.0) / (w - KNOB).max(1.0)).clamp(0.0, 1.0);
    let v = v.clamp(0.0, 1.0);
    let (lo, hi) = if bipolar { (v.min(0.5), v.max(0.5)) } else { (0.0, v) };
    // A row spanning the knob's travel: `before`, the item, `after`.
    let travel = |k: &'static str, y: f32, before: f32, item: El, after: f32| {
        row()
            .key(k)
            .w_full()
            .absolute(0.0, y)
            .px(KNOB / 2.0)
            .child(el().key("a").grow(before).a11y_hidden())
            .child(item)
            .child(el().key("b").grow(after).a11y_hidden())
            .a11y_hidden()
    };
    let mut t = el()
        .key(key)
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
        .h(HIT)
        .on_drag(move |s: &mut App, d: &mut Drag, tx| match d.phase {
            Phase::Down => {
                d.data = *field(s);
                let knob = KNOB / 2.0 + d.data * (d.w - KNOB);
                if (d.x - knob).abs() > KNOB / 2.0 + 2.0 {
                    *field(s) = to_value(d.x, d.w);
                }
            }
            Phase::Move => {
                let knob = KNOB / 2.0 + d.data * (d.w - KNOB);
                let grab = if (d.start_x - knob).abs() <= KNOB / 2.0 + 2.0 { d.start_x - knob } else { 0.0 };
                *field(s) = to_value(d.x - grab, d.w);
                tx.instant();
            }
            Phase::Up => {
                if d.cancelled() {
                    *field(s) = d.data;
                }
            }
        })
        .motion(motion::SNAPPY)
        .child(
            el().key("rail")
                .w_full()
                .h(BAR)
                .absolute(0.0, (HIT - BAR) / 2.0)
                .radius(BAR / 2.0)
                .fill(l.track)
                .a11y_hidden(),
        );
    if let Some(at) = tick {
        t = t.child(travel("tick", (HIT - 8.0) / 2.0, at, el().key("t").size(1.0, 8.0).fill(l.text3.alpha(0.7)), 1.0 - at));
    }
    t.child(travel(
        "fill",
        (HIT - BAR) / 2.0,
        lo,
        el().key("f").grow(hi - lo).h(BAR).radius(BAR / 2.0).fill(l.accent),
        1.0 - hi,
    ))
    .child(
        row()
            .key("knob-row")
            .w_full()
            .absolute(0.0, (HIT - KNOB) / 2.0)
            .child(el().key("a").grow(v).a11y_hidden())
            .child(
                el().key("knob")
                    .size(KNOB, KNOB)
                    .radius(KNOB / 2.0)
                    .fill(l.knob)
                    .shadow(1.0, 3.0, Color::BLACK.alpha(0.45))
                    .shadow(0.0, 0.5, Color::BLACK.alpha(0.6))
                    .a11y_hidden(),
            )
            .child(el().key("b").grow(1.0 - v).a11y_hidden())
            .a11y_hidden(),
    )
}

/// A disclosure section of the inspector: a header that folds its body, with a summary of the
/// values while folded.
pub fn section(l: &Look, key: &'static str, title: &'static str, summary: String, open: bool, toggle: fn(&mut App), body: El) -> El {
    let header = row()
        .key("header")
        .role("button")
        .label(title)
        .expanded(open)
        .focusable(true)
        .w_full()
        .h(40.0)
        .px(16.0)
        .gap(8.0)
        .center_y()
        .hover(l.hover)
        .on_press(toggle)
        .child(
            icon(&glyphs::CHEVRON_DOWN, 12.0)
                .key("chevron")
                .color(l.text3)
                .rotate(if open { 0.0 } else { -FRAC_PI_2 })
                .motion(motion::SNAPPY)
                .a11y_hidden(),
        )
        .child(text(title).font(ty::CAPS).text_case(TextCase::Uppercase).color(l.text2).a11y_hidden())
        .child(el().grow(1.0))
        .child(text(summary).key("summary").font(ty::VALUE_SMALL).color(l.text3).opacity(if open { 0.0 } else { 1.0 }).a11y_hidden());
    let mut s = col().key(key).w_full().child(header);
    if open {
        s = s.child(col().key("body").w_full().px(16.0).pt(2.0).pb(18.0).gap(14.0).child(body));
    }
    s.child(el().key("rule").w_full().h(1.0).fill(l.line).a11y_hidden())
}

/// Caps label over a group of controls.
pub fn caps(l: &Look, s: &'static str) -> El {
    text(s).font(ty::CAPS).text_case(TextCase::Uppercase).color(l.text3)
}

/// A small round status light.
pub fn dot(c: Color, d: f32) -> El {
    el().size(d, d).radius(d / 2.0).fill(c).a11y_hidden()
}

/// A dot with a soft halo, for live things.
pub fn glow_dot(c: Color, d: f32) -> El {
    el().size(d, d).radius(d / 2.0).fill(c).shadow(0.0, d * 1.6, c.alpha(0.7)).a11y_hidden()
}

/// A vertical level meter, `h` tall, filled to `v` (0..1) with a held peak line.
pub fn meter(l: &Look, key: String, v: f32, peak: f32, ink: Color, w: f32, h: f32) -> El {
    let fill = (v.clamp(0.0, 1.0) * h).max(2.0);
    let pk = peak.clamp(0.0, 1.0) * (h - 2.0);
    el().key(key)
        .size(w, h)
        .radius(3.0)
        .fill(l.track)
        .clip_soft(0.0)
        .child(el().key("lvl").size(w, fill).absolute(0.0, h - fill).gradient(ink, ink.alpha(0.55)).a11y_hidden())
        .child(el().key("pk").size(w, 2.0).absolute(0.0, h - 2.0 - pk).fill(ink.mix(Color::WHITE, 0.4)).a11y_hidden())
        .a11y_hidden()
}

/// A key and value on one line, for read-only facts.
pub fn fact(l: &Look, k: &'static str, v: String) -> El {
    row()
        .w_full()
        .h(22.0)
        .justify_between()
        .center_y()
        .child(text(k).font(ty::LABEL).color(l.text3))
        .child(text(v).font(ty::VALUE).color(l.text2))
}

/// A pill-shaped tag.
pub fn tag(l: &Look, s: String, ink: Color) -> El {
    row()
        .h(20.0)
        .px(8.0)
        .center()
        .radius(10.0)
        .fill(ink.alpha(0.14))
        .border(1.0, ink.alpha(0.22))
        .child(text(s).font(ty::VALUE_SMALL).color(ink.mix(l.text, 0.25)))
}
