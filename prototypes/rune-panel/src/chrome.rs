//! The panel's frame: the top bar (the two decks, the crossfader lever, TAKE, the master
//! caution and the clocks), the library down the left (the PGM and PVW displays, the patches,
//! the devices) and the status line.

use rune::tok::motion;
use rune::{Color, Drag, El, Phase, Spring, TextCase, canvas, col, el, row, text};
use rune_kit::Kit;

use crate::App;
use crate::data::{DEVICES, PATCHES, Status};
use crate::polytope::{self, Pose};
use crate::theme::{Look, ty};
use crate::widgets::{brackets, caps, cross, lamp, legend, push, readout};

pub const LIBRARY_W: f32 = 264.0;

pub fn top_bar(s: &App, l: &Look, _k: &Kit) -> El {
    let logo = el()
        .key("logo")
        .size(30.0, 30.0)
        .radius(2.0)
        .fill(l.glass)
        .border(1.0, l.line_strong)
        .child(canvas(polytope::wire(&s.logo_poly, &Pose::at(s.t * 0.5, 0.6), 30.0, l.green, 0.9)).size(30.0, 30.0));
    let brand = row()
        .key("brand")
        .gap(10.0)
        .center_y()
        .child(logo)
        .child(
            col()
                .gap(3.0)
                .child(text("HYPERSPACE").font(ty::CAPS).color(l.label))
                .child(text("SHOW · PARTY").font(ty::VALUE_SMALL).color(l.dim)),
        );
    let met = s.t as u32 + 83;
    let caution = col()
        .key("devices-missing")
        .role("button")
        .label("Master caution: 2 devices missing")
        .focusable(true)
        .h(40.0)
        .px(10.0)
        .gap(3.0)
        .center()
        .radius(2.0)
        .fill(l.amber.alpha(0.12))
        .border(1.0, l.amber.alpha(0.7))
        .hover(l.amber.alpha(0.06))
        .child(text("CAUTION").font(ty::VALUE_BOLD).color(l.amber).a11y_hidden())
        .child(text("2 DEV").font(ty::VALUE_SMALL).color(l.amber.alpha(0.8)).a11y_hidden());
    let clock = |key: &'static str, name: &'static str, value: String, ink: Color| {
        col().key(key).gap(3.0).items_end().child(legend(l, name)).child(readout(l, value, ink, 82.0))
    };
    row()
        .key("top-bar")
        .w_full()
        .h(56.0)
        .px(14.0)
        .gap(14.0)
        .center_y()
        .fill(l.bezel)
        .border_sides([0.0, 0.0, 1.0, 0.0], l.line_strong)
        .child(brand.w(LIBRARY_W - 28.0))
        .child(el().grow(1.0))
        .child(decks(s, l))
        .child(el().grow(1.0))
        .child(caution)
        .child(clock("met", "Show", format!("{:02}:{:02}:{:02}", met / 3600, met / 60 % 60, met % 60), l.green))
        .child(
            col()
                .key("bpm")
                .gap(3.0)
                .items_end()
                .child(row().gap(6.0).center_y().child(beat_lamp(s, l)).child(legend(l, "Tempo")))
                .child(readout(l, format!("{:.1}", s.bpm), l.cyan, 82.0)),
        )
}

/// A lamp on the beat, beside the tempo's legend.
fn beat_lamp(s: &App, l: &Look) -> El {
    let phase = (s.t * s.bpm / 60.0).fract();
    lamp(l.green, 6.0, phase < 0.25).key("beat")
}

/// Deck 1, the crossfader lever, deck 2, the fade time, TAKE and copy.
fn decks(s: &App, l: &Look) -> El {
    let deck = |key: &'static str, n: usize, patch: usize, on_air: bool| {
        // Two elements, not one restyled: PVW leaves and PGM arrives rather than one morphing.
        let badge = if on_air {
            row().key("on-air").h(18.0).px(6.0).center().radius(2.0).fill(l.red).child(text("PGM").font(ty::VALUE_BOLD).color(Color::WHITE))
        } else {
            row().key("cue").h(18.0).px(6.0).center().radius(2.0).border(1.0, l.cyan.alpha(0.8)).child(text("PVW").font(ty::VALUE_BOLD).color(l.cyan))
        };
        let poly = if n == 1 { &s.shape_poly } else { &s.cue_poly };
        row()
            .key(key)
            .h(40.0)
            .pl(5.0)
            .pr(10.0)
            .gap(10.0)
            .center_y()
            .radius(2.0)
            .fill(l.module)
            .border(1.0, if on_air { l.red.alpha(0.55) } else { l.line_strong })
            .child(
                el().key("thumb")
                    .size(30.0, 30.0)
                    .radius(1.0)
                    .fill(l.glass)
                    .child(canvas(polytope::wire(poly, &Pose::at(s.t + n as f32 * 3.0, 0.8), 30.0, if on_air { l.green } else { l.dim }, 0.7)).size(30.0, 30.0)),
            )
            .child(
                col()
                    .gap(2.0)
                    .child(text(PATCHES[patch].name).font(ty::NODE).color(l.label))
                    .child(text(format!("DECK {n}")).font(ty::VALUE_SMALL).color(l.dim)),
            )
            .child(badge)
    };
    let take = row()
        .key("take")
        .role("button")
        .label("Take")
        .focusable(true)
        .h(40.0)
        .px(16.0)
        .center()
        .radius(2.0)
        .fill(l.red.alpha(0.1))
        .border(1.5, l.red.alpha(0.8))
        .hover(l.red.alpha(0.08))
        .press(Color::BLACK.alpha(0.3))
        .on_press_tx(|s: &mut App, tx| {
            s.xfade = if s.xfade < 0.5 { 1.0 } else { 0.0 };
            tx.motion(Spring::new(s.fade_s.min(1.2), 0.0));
        })
        .child(text("TAKE").font(ty::VALUE_BOLD).color(l.label).a11y_hidden());
    row()
        .key("decks")
        .gap(10.0)
        .center_y()
        .child(deck("deck-1", 1, s.on_air, s.live_deck() == 1))
        .child(lever(s, l))
        .child(deck("deck-2", 2, s.cue, s.live_deck() == 2))
        .child(col().gap(3.0).child(legend(l, "Fade")).child(readout(l, format!("{:.1}s", s.fade_s), l.cyan, 52.0)))
        .child(take)
        .child(push(l, "copy-to-off-air", "Copy", l.dim, |s| {
            if s.live_deck() == 1 {
                s.cue = s.on_air
            } else {
                s.on_air = s.cue
            }
        }))
}

/// The crossfader as a lever in a slot, detents marked.
fn lever(s: &App, l: &Look) -> El {
    let (w, h, cap) = (190.0, 40.0, 14.0);
    let travel = w - cap;
    let v = s.xfade;
    let mut slot = el().key("slot").size(w, h);
    for i in 0..=8 {
        let x = cap / 2.0 + travel * i as f32 / 8.0;
        let major = i % 4 == 0;
        let len = if major { 7.0 } else { 4.0 };
        slot = slot
            .child(el().key(format!("u{i}")).absolute(x, 2.0).size(1.0, len).fill(if major { l.dim } else { l.faint }).a11y_hidden())
            .child(el().key(format!("d{i}")).absolute(x, h - 2.0 - len).size(1.0, len).fill(if major { l.dim } else { l.faint }).a11y_hidden());
    }
    el().key("crossfader")
        .role("slider")
        .label("Crossfader")
        .range_value(f64::from(v), 0.0, 1.0)
        .range_step(0.05)
        .on_step(|s: &mut App, steps, _| s.xfade = (s.xfade + steps as f32 * 0.05).clamp(0.0, 1.0))
        .focusable(true)
        .size(w, h)
        .on_drag(move |s: &mut App, d: &mut Drag, tx| match d.phase {
            Phase::Down => d.data = s.xfade,
            Phase::Move => {
                s.xfade = (d.data + d.dx / travel).clamp(0.0, 1.0);
                tx.instant();
            }
            Phase::Up => {
                if d.cancelled() {
                    s.xfade = d.data;
                }
            }
        })
        .child(slot)
        .child(el().key("rail").size(travel, 6.0).absolute(cap / 2.0, (h - 6.0) / 2.0).radius(1.0).fill(l.glass).border(1.0, l.line_strong))
        .child(
            el().key("cap")
                .size(cap, 28.0)
                .absolute(v * travel, (h - 28.0) / 2.0)
                .radius(2.0)
                .gradient(rune::oklch(0.62, 0.005, 250.0), rune::oklch(0.42, 0.005, 250.0))
                .border(1.0, Color::BLACK.alpha(0.6))
                .shadow(2.0, 6.0, Color::BLACK.alpha(0.6))
                .child(el().size(cap - 2.0, 2.0).absolute(0.0, 13.0).fill(if v < 0.5 { l.red } else { l.cyan }))
                .motion(motion::SNAPPY),
        )
}

pub fn library(s: &App, l: &Look) -> El {
    let displays = col()
        .key("monitors")
        .w_full()
        .gap(8.0)
        .child(display(s, l, "PGM", s.live_deck(), true))
        .child(display(s, l, "PVW", 3 - s.live_deck(), false));
    let patches = rune::memo("patches", (s.on_air, s.cue, s.live_deck()), || {
        PATCHES.iter().enumerate().fold(col().key("patches").w_full().radius(2.0).border(1.0, l.line), |c, (i, p)| c.child(patch_row(s, l, i, p)))
    });
    let mut devices = col().key("devices").w_full().radius(2.0).border(1.0, l.line);
    for (i, d) in DEVICES.iter().enumerate() {
        let (ink, word) = match d.status {
            Status::Live => (l.green, "ON"),
            Status::Idle => (l.dim, "IDLE"),
            Status::Missing(_) => (l.amber, "FAULT"),
        };
        let mut r = row()
            .key(d.name)
            .w_full()
            .h(28.0)
            .px(8.0)
            .gap(8.0)
            .center_y()
            .hover(l.hover)
            .help(d.detail)
            .child(lamp(ink, 6.0, !matches!(d.status, Status::Idle)))
            .child(text(d.name).font(ty::LABEL).text_case(TextCase::Uppercase).color(l.label))
            .child(el().grow(1.0))
            .child(text(word).font(ty::VALUE_BOLD).color(ink));
        if i > 0 {
            r = r.border_sides([1.0, 0.0, 0.0, 0.0], l.line);
        }
        devices = devices.child(r);
    }
    let search = row()
        .key("search")
        .w_full()
        .h(26.0)
        .px(8.0)
        .gap(8.0)
        .center_y()
        .radius(2.0)
        .fill(l.glass)
        .border(1.0, l.line)
        .child(rune::icon(&rune_kit::glyphs::SEARCH, 12.0).color(l.faint))
        .child(text("SEARCH").font(ty::VALUE_SMALL).color(l.faint))
        .child(el().grow(1.0))
        .child(text("⌘K").font(ty::VALUE_SMALL).color(l.faint));
    let head = |title: &'static str, right: El| row().w_full().h(20.0).center_y().justify_between().child(caps(l, title)).child(right);
    col()
        .key("library")
        .w(LIBRARY_W)
        .h_full()
        .fill(l.module)
        .border_sides([0.0, 1.0, 0.0, 0.0], l.line_strong)
        .child(
            col().key("library-scroll").w_full().grow(1.0).min_h(0.0).scroll(rune::ScrollSpec { stick_bottom: false }).child(
                col()
                    .w_full()
                    .padding(12.0)
                    .gap(12.0)
                    .child(head("Displays", text("2").font(ty::VALUE_SMALL).color(l.faint)))
                    .child(displays)
                    .child(head("Patches", text(format!("{}", PATCHES.len())).font(ty::VALUE_SMALL).color(l.faint)))
                    .child(search)
                    .child(patches)
                    .child(head("Devices", text("2 FAULT").font(ty::VALUE_SMALL).color(l.amber)))
                    .child(devices),
            ),
        )
}

/// A deck's display: the shape turning in green phosphor on glass, framed by a reticle.
fn display(s: &App, l: &Look, what: &'static str, deck: usize, program: bool) -> El {
    let (w, h) = (LIBRARY_W - 24.0, (LIBRARY_W - 24.0) * 9.0 / 16.0);
    let poly = if deck == 1 { &s.shape_poly } else { &s.cue_poly };
    let patch = PATCHES[if deck == 1 { s.on_air } else { s.cue }].name;
    let pose = Pose::at(s.t + deck as f32 * 3.0, 0.4 + s.speed * 1.6);
    let size = h * 1.25;
    let ink = if program { l.green } else { l.label.alpha(0.7) };
    let corner = |t: String, c: Color| text(t).font(ty::VALUE_SMALL).color(c);
    el().key(what)
        .w(w)
        .h(h)
        .radius(2.0)
        .fill(l.glass)
        .border(1.0, if program { l.red.alpha(0.6) } else { l.line_strong })
        .clip_soft(0.0)
        .child(canvas(cross(rune::Shape::new(), w / 2.0, h / 2.0, 5.0, l.faint)).size(w, h).absolute(0.0, 0.0))
        .child(
            canvas(polytope::wire(poly, &pose, size, ink, 1.0))
                .key("wire")
                .size(size, size)
                .absolute((w - size) / 2.0, (h - size) / 2.0)
                .opacity(s.dim),
        )
        .child(brackets(w, h, 10.0, l.dim.alpha(0.8)))
        .child(
            row()
                .key("top")
                .absolute(8.0, 7.0)
                .w(w - 16.0)
                .justify_between()
                .child(
                    row()
                        .h(16.0)
                        .px(5.0)
                        .center()
                        .radius(1.0)
                        .fill(if program { l.red } else { Color::TRANSPARENT })
                        .border(1.0, if program { l.red } else { l.cyan })
                        .child(text(what).font(ty::VALUE_BOLD).color(if program { Color::WHITE } else { l.cyan })),
                )
                .child(corner(format!("DECK {deck}"), l.dim)),
        )
        .child(
            row()
                .key("bottom")
                .absolute(8.0, h - 20.0)
                .w(w - 16.0)
                .justify_between()
                .child(corner(patch.to_string(), l.label))
                .child(corner(format!("{:.0}%", s.dim * 100.0), l.green)),
        )
}

fn patch_row(s: &App, l: &Look, i: usize, p: &crate::data::Patch) -> El {
    let on_air = i == s.live_patch();
    let cue = !on_air && (i == s.on_air || i == s.cue);
    let mark = if on_air { l.red } else if cue { l.cyan } else { Color::TRANSPARENT };
    let mut r = row()
        .key(p.name)
        .role("button")
        .label(p.name)
        .focusable(true)
        .w_full()
        .h(30.0)
        .pr(8.0)
        .gap(8.0)
        .center_y()
        .fill(if cue { l.cyan.alpha(0.05) } else { Color::TRANSPARENT })
        .hover(l.hover)
        .on_press(move |s: &mut App| {
            // Load it on the deck that is off air.
            if i != s.live_patch() {
                if s.live_deck() == 1 {
                    s.cue = i
                } else {
                    s.on_air = i
                }
            }
        })
        .child(el().key("mark").w(2.0).h_full().fill(mark))
        .child(text(format!("{:02}", i + 1)).font(ty::VALUE_SMALL).color(l.faint))
        .child(text(p.name).font(ty::NODE).color(if on_air || cue { l.label } else { l.dim }))
        .child(el().grow(1.0));
    if on_air {
        r = r.child(text("PGM").font(ty::VALUE_BOLD).color(l.red));
    } else if cue {
        r = r.child(text("PVW").font(ty::VALUE_BOLD).color(l.cyan));
    }
    if i > 0 {
        r = r.border_sides([1.0, 0.0, 0.0, 0.0], l.line);
    }
    r
}

/// The status line, as an ECAM memo: names in grey, values in green.
pub fn status_bar(s: &App, l: &Look) -> El {
    let live = s.cables.iter().filter(|c| c.live).count();
    let idle = s.nodes.iter().filter(|n| n.status != Status::Live).count();
    let item = |k: &'static str, v: String, ink: Color| {
        row().gap(5.0).center_y().child(text(k).font(ty::VALUE_SMALL).color(l.faint)).child(text(v).font(ty::VALUE_SMALL).color(ink))
    };
    row()
        .key("status-bar")
        .w_full()
        .h(26.0)
        .px(14.0)
        .gap(18.0)
        .center_y()
        .fill(l.bezel)
        .border_sides([1.0, 0.0, 0.0, 0.0], l.line_strong)
        .child(item("FPS", "60".into(), l.green))
        .child(item("NODES", format!("{} ({idle} IDLE)", s.nodes.len()), l.green))
        .child(item("HIDDEN", "35".into(), l.green))
        .child(item("WIRES", format!("{}", s.cables.len()), l.green))
        .child(item("CABLES", "213".into(), l.green))
        .child(item("LIVE", format!("{live}"), l.green))
        .child(el().grow(1.0))
        .child(item("PGM", format!("DECK {}", s.live_deck()), l.red))
        .child(item("PVW", format!("DECK {}", 3 - s.live_deck()), l.cyan))
        .child(item("LIB", "~/HYPERSPACE".into(), l.label))
        .child(item("SHOW", "PARTY".into(), l.label))
}
