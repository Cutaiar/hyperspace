//! The window's frame: the top bar (the two decks and the crossfader between them), the
//! library down the left (the program and preview monitors, the patches, the devices) and the
//! status bar.

use rune::tok::motion;
use rune::{Color, Drag, El, Phase, Spring, TextCase, canvas, col, el, oklch, row, text};
use rune_kit::{Button, ButtonVariant, ControlSize, IconButton, IconButtonVariant, Kit, glyphs};

use crate::App;
use crate::data::{DEVICES, PATCHES, Status};
use crate::polytope::{self, Pose};
use crate::theme::{Look, ty};
use crate::widgets::{caps, dot, glow_dot};

pub const LIBRARY_W: f32 = 264.0;

pub fn top_bar(s: &App, l: &Look, k: &Kit) -> El {
    let logo = canvas(polytope::wire(&s.logo_poly, &Pose::at(s.t * 0.5, 0.6), 26.0, l.accent, 1.0)).key("logo").size(26.0, 26.0);
    let brand = row()
        .key("brand")
        .gap(10.0)
        .center_y()
        .child(logo)
        .child(text("Hyperspace").font(ty::TITLE).color(l.text))
        .child(text("/").font(ty::LABEL).color(l.text3))
        .child(text("party").font(ty::LABEL).color(l.text2))
        .child(rune::icon(&glyphs::CHEVRON_DOWN, 10.0).color(l.text3));
    let bpm = row()
        .key("bpm")
        .gap(8.0)
        .center_y()
        .child(beat_light(s, l))
        .child(text(format!("{:.1}", s.bpm)).font(ty::VALUE).color(l.text))
        .child(text("BPM").font(ty::SMALL).color(l.text3));
    let warn = row()
        .key("devices-missing")
        .role("button")
        .focusable(true)
        .label("2 devices missing")
        .h(28.0)
        .px(10.0)
        .gap(7.0)
        .center_y()
        .radius(14.0)
        .fill(l.warn.alpha(0.1))
        .border(1.0, l.warn.alpha(0.25))
        .hover(l.warn.alpha(0.08))
        .child(dot(l.warn, 6.0))
        .child(text("2 devices missing").font(ty::SMALL).color(l.warn).a11y_hidden());
    row()
        .key("top-bar")
        .w_full()
        .h(56.0)
        .px(16.0)
        .gap(16.0)
        .center_y()
        .fill(l.window)
        .border_sides([0.0, 0.0, 1.0, 0.0], l.line)
        .child(brand.w(LIBRARY_W - 32.0))
        .child(el().grow(1.0))
        .child(decks(s, l, k))
        .child(el().grow(1.0))
        .child(warn)
        .child(bpm)
        .child(
            IconButton::new(&rune_kit::shell::INSPECTOR)
                .variant(IconButtonVariant::GhostMuted)
                .label("Inspector")
                .build(k),
        )
}

fn beat_light(s: &App, l: &Look) -> El {
    let phase = (s.t * s.bpm / 60.0).fract();
    let a = (1.0 - phase).powf(3.0);
    el().key("beat").size(8.0, 8.0).radius(4.0).fill(l.accent.alpha(0.25 + 0.75 * a)).shadow(0.0, 10.0 * a, l.accent.alpha(0.8 * a))
}

/// Deck 1 on air, the crossfader, deck 2 cued, the fade time and Take.
fn decks(s: &App, l: &Look, k: &Kit) -> El {
    let deck = |key: &'static str, n: usize, patch: usize, on_air: bool| {
        // Two elements, not one restyled: CUE leaves and ON AIR arrives rather than one
        // morphing into the other mid-fade.
        let badge = if on_air {
            row()
                .key("on-air")
                .h(18.0)
                .px(7.0)
                .gap(5.0)
                .center()
                .radius(4.0)
                .fill(l.live)
                .child(el().size(5.0, 5.0).radius(2.5).fill(Color::WHITE))
                .child(text("ON AIR").font(ty::VALUE_SMALL).color(Color::WHITE))
        } else {
            row()
                .key("cue")
                .h(18.0)
                .px(7.0)
                .center()
                .radius(4.0)
                .border(1.0, l.accent.alpha(0.6))
                .child(text("CUE").font(ty::VALUE_SMALL).color(l.accent))
        };
        row()
            .key(key)
            .h(40.0)
            .pl(8.0)
            .pr(12.0)
            .gap(10.0)
            .center_y()
            .radius(9.0)
            .fill(l.raised)
            .border(1.0, if on_air { l.live.alpha(0.45) } else { l.line_strong })
            .child(monitor_thumb(s, l, n))
            .child(
                col()
                    .gap(2.0)
                    .child(text(PATCHES[patch].name).font(ty::LABEL_STRONG).color(l.text))
                    .child(text(format!("Deck {n}")).font(ty::SMALL).color(l.text3)),
            )
            .child(badge)
    };
    row()
        .key("decks")
        .gap(12.0)
        .center_y()
        .child(deck("deck-1", 1, s.on_air, s.live_deck() == 1))
        .child(crossfader(s, l))
        .child(deck("deck-2", 2, s.cue, s.live_deck() == 2))
        .child(
            col()
                .gap(1.0)
                .items_end()
                .child(text(format!("{:.1} s", s.fade_s)).font(ty::VALUE).color(l.text2))
                .child(text("fade").font(ty::SMALL).color(l.text3)),
        )
        .child(
            Button::new("Take")
                .variant(ButtonVariant::Contrast)
                .control_size(ControlSize::Regular)
                .on_press_tx(|s: &mut App, tx| {
                    s.xfade = if s.xfade < 0.5 { 1.0 } else { 0.0 };
                    tx.motion(Spring::new(s.fade_s.min(1.2), 0.0));
                })
                .build(k)
                .key("take"),
        )
        .child(
            IconButton::new(&glyphs::COPY)
                .variant(IconButtonVariant::GhostMuted)
                .label("Copy on air to off air")
                .help("Copy on air to off air")
                .on_press(|s: &mut App| {
                    if s.live_deck() == 1 { s.cue = s.on_air } else { s.on_air = s.cue }
                })
                .build(k)
                .key("copy-to-off-air"),
        )
}

/// A small live picture of a deck, for the deck pill.
fn monitor_thumb(s: &App, l: &Look, deck: usize) -> El {
    let poly = if deck == 1 { &s.shape_poly } else { &s.cue_poly };
    canvas(polytope::wire(poly, &Pose::at(s.t + deck as f32 * 3.0, 0.8), 28.0, l.text, 0.7))
        .key("thumb")
        .size(28.0, 28.0)
        .radius(6.0)
        .fill(Color::BLACK)
        .clip_soft(0.0)
}

fn crossfader(s: &App, l: &Look) -> El {
    let (w, h, cap) = (180.0, 40.0, 12.0);
    let travel = w - cap;
    let v = s.xfade;
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
        .child(el().key("rail").size(w, 6.0).absolute(0.0, (h - 6.0) / 2.0).radius(3.0).linear_gradient(
            std::f32::consts::FRAC_PI_2,
            [(0.0, l.live.alpha(0.7)), (0.5, l.track), (1.0, l.accent.alpha(0.6))],
        ))
        .child(el().key("mid").size(1.0, 14.0).absolute(w / 2.0, (h - 14.0) / 2.0).fill(l.text3))
        .child(
            el().key("cap")
                .size(cap, 26.0)
                .absolute(v * travel, (h - 26.0) / 2.0)
                .radius(3.0)
                .gradient(oklch(0.96, 0.0, 0.0), oklch(0.80, 0.0, 0.0))
                .shadow(2.0, 6.0, Color::BLACK.alpha(0.5))
                .child(el().size(cap, 1.5).absolute(0.0, 12.25).fill(Color::BLACK.alpha(0.5)))
                .motion(motion::SNAPPY),
        )
}

pub fn library(s: &App, l: &Look, k: &Kit) -> El {
    let monitors = col()
        .key("monitors")
        .w_full()
        .gap(10.0)
        .child(monitor(s, l, "Program", s.live_deck(), true))
        .child(monitor(s, l, "Preview", 3 - s.live_deck(), false));
    let patches = rune::memo("patches", (s.on_air, s.cue, s.live_deck()), || {
        PATCHES.iter().enumerate().fold(col().key("patches").w_full().gap(2.0), |c, (i, p)| c.child(patch_row(s, l, i, p)))
    });
    let mut devices = col().key("devices").w_full().gap(0.0);
    for d in DEVICES.iter() {
        let light = match d.status {
            Status::Live => glow_dot(l.ok, 6.0),
            Status::Idle => dot(l.text3, 6.0),
            Status::Missing(_) => dot(l.warn, 6.0),
        };
        devices = devices.child(
            row()
                .key(d.name)
                .w_full()
                .h(30.0)
                .px(8.0)
                .gap(10.0)
                .center_y()
                .radius(6.0)
                .hover(l.hover)
                .child(light)
                .child(text(d.name).font(ty::LABEL).color(l.text))
                .child(el().grow(1.0))
                .child(
                    text(d.detail)
                        .font(ty::SMALL)
                        .color(if matches!(d.status, Status::Missing(_)) { l.warn.alpha(0.8) } else { l.text3 })
                        .truncate(),
                ),
        );
    }
    let search = row()
        .key("search")
        .w_full()
        .h(30.0)
        .px(10.0)
        .gap(8.0)
        .center_y()
        .radius(7.0)
        .fill(l.raised)
        .border(1.0, l.line)
        .child(rune::icon(&glyphs::SEARCH, 13.0).color(l.text3))
        .child(text("Search patches").font(ty::LABEL).color(l.text3))
        .child(el().grow(1.0))
        .child(text("⌘K").font(ty::VALUE_SMALL).color(l.text3));
    let head = |title: &'static str, right: El| row().w_full().h(28.0).px(4.0).center_y().justify_between().child(caps(l, title)).child(right);
    col()
        .key("library")
        .w(LIBRARY_W)
        .h_full()
        .fill(l.panel)
        .border_sides([0.0, 0.0, 0.0, 1.0], l.line)
        .child(
            col()
                .key("library-scroll")
                .w_full()
                .grow(1.0)
                .min_h(0.0)
                .scroll(rune::ScrollSpec { stick_bottom: false })
                .child(
                    col()
                        .w_full()
                        .padding(14.0)
                        .gap(14.0)
                        .child(monitors)
                        .child(
                            col().w_full().gap(8.0).child(head(
                                "Patches",
                                IconButton::new(&crate::icons::PLUS)
                                    .variant(IconButtonVariant::GhostMuted)
                                    .control_size(ControlSize::Small)
                                    .label("New patch")
                                    .build(k),
                            ))
                            .child(search)
                            .child(patches),
                        )
                        .child(
                            col()
                                .w_full()
                                .gap(4.0)
                                .child(head("Devices", text("2 missing").font(ty::SMALL).color(l.warn)))
                                .child(devices),
                        ),
                ),
        )
}

fn monitor(s: &App, l: &Look, what: &'static str, deck: usize, program: bool) -> El {
    let (w, h) = (LIBRARY_W - 28.0, (LIBRARY_W - 28.0) * 9.0 / 16.0);
    let poly = if deck == 1 { &s.shape_poly } else { &s.cue_poly };
    let patch = PATCHES[if deck == 1 { s.on_air } else { s.cue }].name;
    let pose = Pose::at(s.t + deck as f32 * 3.0, 0.4 + s.speed * 1.6);
    let size = h * 1.25;
    let ink = if program { oklch(0.92, 0.04, 215.0) } else { oklch(0.9, 0.06, 140.0) };
    let label = row()
        .key("label")
        .absolute(8.0, 8.0)
        .h(18.0)
        .px(6.0)
        .gap(5.0)
        .center_y()
        .radius(4.0)
        .fill(if program { l.live } else { Color::BLACK.alpha(0.55) })
        .border(1.0, if program { l.live } else { l.accent.alpha(0.5) })
        .child(text(what).font(ty::VALUE_SMALL).text_case(TextCase::Uppercase).color(if program { Color::WHITE } else { l.accent }));
    el().key(what)
        .w(w)
        .h(h)
        .radius(8.0)
        .fill(Color::BLACK)
        .radial_gradient([0.5, 0.55], [w * 0.7, h * 0.9], [(0.0, oklch(0.2, 0.03, 260.0)), (1.0, Color::BLACK)])
        .border(1.0, if program { l.live.alpha(0.5) } else { l.line_strong })
        .clip_soft(0.0)
        .child(
            canvas(polytope::wire(poly, &pose, size, ink, 1.1))
                .key("wire")
                .size(size, size)
                .absolute((w - size) / 2.0, (h - size) / 2.0)
                .opacity(s.dim * if program { 1.0 } else { 0.8 }),
        )
        .child(label)
        .child(
            text(patch)
                .key("patch")
                .font(ty::VALUE_SMALL)
                .color(Color::WHITE.alpha(0.7))
                .absolute(w - 8.0 - patch.len() as f32 * 7.0, h - 22.0),
        )
}

fn patch_row(s: &App, l: &Look, i: usize, p: &crate::data::Patch) -> El {
    let on_air = i == s.live_patch();
    let cue = !on_air && (i == s.on_air || i == s.cue);
    let swatch = el()
        .key("swatch")
        .size(30.0, 30.0)
        .radius(7.0)
        .linear_gradient(2.2, [(0.0, oklch(0.62, 0.16, p.hue)), (1.0, oklch(0.32, 0.12, p.hue + 50.0))])
        .border(1.0, Color::WHITE.alpha(0.08));
    let trailing = if on_air {
        Some(text("ON AIR").font(ty::VALUE_SMALL).color(l.live))
    } else if cue {
        Some(text("CUE").font(ty::VALUE_SMALL).color(l.accent))
    } else {
        None
    };
    let mut r = row()
        .key(p.name)
        .role("button")
        .label(p.name)
        .focusable(true)
        .w_full()
        .h(44.0)
        .px(7.0)
        .gap(10.0)
        .center_y()
        .radius(8.0)
        .fill(if cue { l.accent_soft } else { Color::TRANSPARENT })
        .hover(l.hover)
        .on_press(move |s: &mut App| {
            // Load it on the deck that is off air.
            if i != s.live_patch() {
                if s.live_deck() == 1 { s.cue = i } else { s.on_air = i }
            }
        })
        .child(swatch)
        .child(
            col()
                .grow(1.0)
                .min_w(0.0)
                .gap(1.0)
                .child(text(p.name).font(ty::LABEL_STRONG).color(l.text))
                .child(text(p.detail).font(ty::SMALL).color(l.text3).truncate()),
        );
    if let Some(t) = trailing {
        r = r.child(t);
    }
    r
}

pub fn status_bar(s: &App, l: &Look) -> El {
    let live = s.cables.iter().filter(|c| c.live).count();
    let idle = s.nodes.iter().filter(|n| n.status != Status::Live).count();
    let sep = || text("·").font(ty::SMALL).color(l.text3);
    let item = |t: String| text(t).font(ty::VALUE_SMALL).color(l.text3);
    row()
        .key("status-bar")
        .w_full()
        .h(28.0)
        .px(14.0)
        .gap(8.0)
        .center_y()
        .fill(l.window)
        .border_sides([1.0, 0.0, 0.0, 0.0], l.line)
        .child(glow_dot(l.ok, 6.0))
        .child(text("60 fps").font(ty::VALUE_SMALL).color(l.text2))
        .child(sep())
        .child(item(format!("{} nodes ({idle} idle)", s.nodes.len())))
        .child(sep())
        .child(item("35 hidden".into()))
        .child(sep())
        .child(item(format!("{} wires", s.cables.len())))
        .child(sep())
        .child(item("213 cables".into()))
        .child(sep())
        .child(item(format!("{live} live")))
        .child(el().grow(1.0))
        .child(item(format!("players: on air {} · off air {}", s.live_deck(), 3 - s.live_deck())))
        .child(sep())
        .child(item("library ~/Hyperspace".into()))
        .child(sep())
        .child(text("party").font(ty::VALUE_SMALL).color(l.text2))
}
