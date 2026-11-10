//! The inspector: the patch on air and what is selected, then the side pane's sections (shape,
//! audio, tempo and LFOs, camera, output), each folding to a one-line summary.

use rune::{El, LineCap, Path, Shape, TextCase, canvas, col, el, row, text};
use rune_kit::{Button, ButtonVariant, ControlSize, Kit, SegmentedControl, Select, SelectAppearance, Switch};

use crate::App;
use crate::data::{BANDS, SHAPES, Status};
use crate::theme::{Look, ty};
use crate::widgets::{Slider, caps, dot, fact, glow_dot, meter, section, tag};

pub const WIDTH: f32 = 340.0;

pub fn pane(s: &App, l: &Look, k: &Kit, layer: &mut Vec<El>) -> El {
    let body = col()
        .key("sections")
        .w_full()
        .child(patch_card(s, l, k))
        .child(selection(s, l))
        .child(section(l, "sec-shape", "Shape", shape_summary(s), s.open[0], |s| s.open[0] ^= true, shape(s, l, k, layer)))
        .child(section(l, "sec-audio", "Audio", format!("mic · drive {:.2}×", s.drive_x()), s.open[1], |s| s.open[1] ^= true, audio(s, l, k)))
        .child(section(l, "sec-tempo", "Tempo & LFOs", format!("{:.1} BPM · 4 LFOs", s.bpm), s.open[2], |s| s.open[2] ^= true, tempo(s, l, k)))
        .child(section(l, "sec-camera", "Camera", format!("{:.2}× · {:+.0}°", s.zoom_x(), s.yaw_deg()), s.open[3], |s| s.open[3] ^= true, camera(s, l)))
        .child(section(
            l,
            "sec-output",
            "Output",
            format!("{:.0}% · {}", s.dim * 100.0, s.screen),
            s.open[4],
            |s| s.open[4] ^= true,
            output(s, l, k, layer),
        ));
    col()
        .key("inspector")
        .w(WIDTH)
        .h_full()
        .fill(l.panel)
        .border_sides([0.0, 0.0, 0.0, 1.0], l.line)
        .child(col().key("scroll").w_full().grow(1.0).min_h(0.0).scroll(rune::ScrollSpec { stick_bottom: false }).child(body))
}

fn shape_summary(s: &App) -> String {
    format!("{} · {:.2}×", s.shape, s.brightness_x())
}

/// The patch on air: step through patches, save, and what's missing.
fn patch_card(s: &App, l: &Look, k: &Kit) -> El {
    let step = |key: &'static str, ic: &'static rune::Icon, d: isize| {
        rune_kit::IconButton::new(ic)
            .variant(rune_kit::IconButtonVariant::Neutral)
            .control_size(ControlSize::Small)
            .label(if d < 0 { "Previous patch" } else { "Next patch" })
            .on_press(move |s: &mut App| s.step_patch(d))
            .build(k)
            .key(key)
    };
    let name = crate::data::PATCHES[s.live_patch()].name;
    let detail = crate::data::PATCHES[s.live_patch()].detail;
    col()
        .key("patch")
        .w_full()
        .padding(16.0)
        .gap(12.0)
        .border_sides([0.0, 0.0, 1.0, 0.0], l.line)
        .child(
            row()
                .w_full()
                .center_y()
                .gap(8.0)
                .child(caps(l, "Patch"))
                .child(el().grow(1.0))
                .child(tag(l, format!("Deck {} · On air", s.live_deck()), l.live)),
        )
        .child(
            row()
                .w_full()
                .center_y()
                .gap(4.0)
                .child(step("prev", &crate::icons::CHEVRON_LEFT, -1))
                .child(text(name).key("name").font(ty::BIG).color(l.text).grow(1.0).align(rune::Align::Center))
                .child(step("next", &crate::icons::CHEVRON_RIGHT, 1)),
        )
        .child(
            row()
                .w_full()
                .gap(6.0)
                .child(Button::new("Save").control_size(ControlSize::Small).build(k).grow(1.0))
                .child(Button::new("Save as…").control_size(ControlSize::Small).build(k).grow(1.0))
                .child(Button::new("New").variant(ButtonVariant::Ghost).control_size(ControlSize::Small).build(k).grow(1.0)),
        )
        .child(
            row()
                .w_full()
                .justify_between()
                .child(text(detail).font(ty::SMALL).color(l.text3))
                .child(text("saved 12 min ago").font(ty::SMALL).color(l.text3)),
        )
}

fn selection(s: &App, l: &Look) -> El {
    let inner = match s.selected.map(|i| &s.nodes[i]) {
        None => col()
            .w_full()
            .h(64.0)
            .center()
            .radius(8.0)
            .border(1.0, l.line_strong)
            .child(text("Nothing selected").font(ty::LABEL_STRONG).color(l.text2))
            .child(text("Click a node, a cable or a group on the canvas").font(ty::SMALL).color(l.text3)),
        Some(n) => {
            let wired = s.cables.iter().filter(|c| s.nodes[c.from.0].id == n.id || s.nodes[c.to.0].id == n.id).count();
            let (light, state) = match n.status {
                Status::Live => (glow_dot(l.ok, 7.0), "live".to_string()),
                Status::Idle => (dot(l.text3, 7.0), "nothing live".to_string()),
                Status::Missing(why) => (glow_dot(l.warn, 7.0), why.to_string()),
            };
            col()
                .w_full()
                .gap(4.0)
                .child(
                    row()
                        .gap(8.0)
                        .center_y()
                        .child(el().size(3.0, 16.0).radius(1.5).fill(n.cat.hue()))
                        .child(text(n.title).font(ty::TITLE).color(l.text))
                        .child(el().grow(1.0))
                        .child(text(n.cat.name()).font(ty::SMALL).text_case(TextCase::Uppercase).color(n.cat.hue().mix(l.text, 0.4))),
                )
                .child(fact(l, "Ports", format!("{} in · {} out", n.ins.len(), n.outs.len())))
                .child(fact(l, "Cables", format!("{wired}")))
                .child(row().h(22.0).gap(8.0).center_y().child(light).child(text(state).font(ty::LABEL).color(l.text2)))
        }
    };
    col().key("selection").w_full().padding(16.0).gap(10.0).border_sides([0.0, 0.0, 1.0, 0.0], l.line).child(caps(l, "Selection")).child(inner)
}

fn shape(s: &App, l: &Look, k: &Kit, layer: &mut Vec<El>) -> El {
    let (cells, verts, edges, sym, note) = match s.shape.as_str() {
        "Tesseract" => ("8", 16, 32, "{4,3,3}", "hypercube"),
        "16-cell" => ("16", 8, 24, "{3,3,4}", "hyperoctahedron"),
        _ => ("24", 24, 96, "{3,4,3}", "no 3D counterpart exists"),
    };
    let hero = row()
        .key("hero")
        .gap(14.0)
        .center_y()
        .child(text(cells).font(ty::HERO).color(l.text))
        .child(
            col()
                .gap(2.0)
                .child(caps(l, "Cells"))
                .child(text(s.shape.clone()).font(ty::TITLE).color(l.text))
                .child(text(note).font(ty::SMALL).color(l.accent)),
        );
    let current = s.shape.clone();
    col()
        .w_full()
        .gap(14.0)
        .child(hero)
        .child(
            row()
                .gap(6.0)
                .child(tag(l, "4D".into(), l.text3))
                .child(tag(l, format!("{verts} V · {edges} E"), l.text3))
                .child(tag(l, sym.into(), l.text3)),
        )
        .child(
            Select::new("shape-select", &SHAPES)
                .label("Shape")
                .appearance(SelectAppearance::Field)
                .current(Some(&current))
                .open(s.menu == Some("shape"))
                .on_toggle(|s: &mut App| s.menu = if s.menu == Some("shape") { None } else { Some("shape") })
                .on_close(|s: &mut App| s.menu = None)
                .on_choose(|s: &mut App, v: &str, _| s.set_shape(v))
                .width(WIDTH - 32.0)
                .build(k, layer),
        )
        .child(Slider::new("brightness", "Brightness · log", s.brightness, format!("{:.2}×", s.brightness_x()), |s| &mut s.brightness).tick(0.5).build(l))
        .child(Slider::new("speed", "Speed · log", s.speed, format!("{:.3}", s.speed_x()), |s| &mut s.speed).build(l))
        .child(Slider::new("depth", "4D depth", s.depth, format!("{:.2}", 1.6 + s.depth * 2.0), |s| &mut s.depth).build(l))
}

fn audio(s: &App, l: &Look, k: &Kit) -> El {
    let mut bands = row().key("bands").w_full().justify_between();
    for (i, (name, plane, _hz)) in BANDS.iter().enumerate() {
        let (v, pk) = s.level(i);
        bands = bands.child(
            col()
                .key(*name)
                .gap(5.0)
                .items_center()
                .child(meter(l, format!("m{i}"), v, pk, l.ok, 30.0, 68.0))
                .child(text(*name).font(ty::VALUE_SMALL).color(l.text2))
                .child(text(*plane).font(ty::VALUE_SMALL).color(l.accent.alpha(0.85))),
        );
    }
    col()
        .w_full()
        .gap(14.0)
        .child(
            SegmentedControl::new(&["Mic", "Video sound", "Track"], Some(s.audio_src))
                .label("Audio source")
                .width(Some(WIDTH - 32.0))
                .on_pick(|s: &mut App, i, _| s.audio_src = i)
                .build(k),
        )
        .child(
            col()
                .w_full()
                .gap(8.0)
                .child(row().w_full().justify_between().child(caps(l, "Bands → planes")).child(text("MacBook Pro mic").font(ty::SMALL).color(l.text3)))
                .child(bands),
        )
        .child(Slider::new("drive", "Audio drive · log", s.drive, format!("{:.2}×", s.drive_x()), |s| &mut s.drive).tick(0.5).build(l))
        .child(Slider::new("gain", "Master", s.gain, format!("{:+.1} dB", s.gain_db()), |s| &mut s.gain).tick(24.0 / 36.0).build(l))
}

fn tempo(s: &App, l: &Look, k: &Kit) -> El {
    let beat = ((s.t * s.bpm / 60.0) as usize) % 4;
    let phase = (s.t * s.bpm / 60.0).fract();
    let mut beats = row().key("beats").gap(5.0).center_y();
    for i in 0..4 {
        let on = i == beat;
        beats = beats.child(
            el().key(format!("b{i}"))
                .size(8.0, 8.0)
                .radius(4.0)
                .fill(if on { l.accent.alpha(1.0 - phase * 0.6) } else { l.track })
                .a11y_hidden(),
        );
    }
    let bpm = row()
        .key("tempo-bpm")
        .w_full()
        .gap(10.0)
        .center_y()
        .child(text(format!("{:.1}", s.bpm)).font(ty::BIG).color(l.text))
        .child(col().gap(4.0).child(caps(l, "BPM")).child(beats))
        .child(el().grow(1.0))
        .child(Button::new("Tap").control_size(ControlSize::Small).on_press(|s: &mut App| s.bpm = 124.0).build(k))
        .child(Button::new("−").variant(ButtonVariant::Ghost).control_size(ControlSize::Small).on_press(|s: &mut App| s.bpm -= 0.5).build(k))
        .child(Button::new("+").variant(ButtonVariant::Ghost).control_size(ControlSize::Small).on_press(|s: &mut App| s.bpm += 0.5).build(k));
    let lfos: [(&str, &str, &str, usize); 4] = [
        ("LFO 1", "sine · 1/4 bar", "brightness", 0),
        ("LFO 2", "triangle · 1 bar", "camera.yaw", 1),
        ("LFO 3", "saw · 2 bars", "rot.phase.XW", 2),
        ("LFO 4", "sample & hold · 1/8", "fx.acid.mix", 3),
    ];
    let mut list = col().key("lfos").w_full().gap(2.0);
    for (name, shape, target, wave) in lfos {
        list = list.child(
            row()
                .key(name)
                .w_full()
                .h(40.0)
                .px(8.0)
                .gap(10.0)
                .center_y()
                .radius(8.0)
                .hover(l.hover)
                .child(canvas(lfo_wave(wave, s.t, l)).key("wave").size(44.0, 24.0).radius(5.0).fill(l.window))
                .child(
                    col()
                        .gap(1.0)
                        .child(text(name).font(ty::LABEL_STRONG).color(l.text))
                        .child(text(shape).font(ty::SMALL).color(l.text3)),
                )
                .child(el().grow(1.0))
                .child(text(format!("→ {target}")).font(ty::VALUE_SMALL).color(l.text2)),
        );
    }
    col()
        .w_full()
        .gap(12.0)
        .child(bpm)
        .child(Slider::new("nudge", "Nudge", s.nudge, format!("{:+.2} beat", (s.nudge - 0.5) * 2.0), |s| &mut s.nudge).bipolar().build(l))
        .child(list)
        .child(Button::new("Add LFO").icon(&crate::icons::PLUS).variant(ButtonVariant::Ghost).control_size(ControlSize::Small).build(k))
}

/// One cycle of an LFO's wave, with a dot where it is now.
fn lfo_wave(kind: usize, t: f32, l: &Look) -> Shape {
    let (w, h) = (44.0, 24.0);
    let f = |u: f32| -> f32 {
        match kind {
            0 => (u * std::f32::consts::TAU).sin(),
            1 => 1.0 - 4.0 * (u - 0.5).abs(),
            2 => 2.0 * u - 1.0,
            _ => [0.6, -0.3, 0.9, -0.8, 0.2, -0.5, 0.75, -0.1][(u * 8.0) as usize % 8],
        }
    };
    let y = |v: f32| h / 2.0 - v * (h / 2.0 - 5.0);
    let mut path = Path::new().move_to([4.0, y(f(0.0))]);
    for i in 1..=36 {
        let u = i as f32 / 36.0;
        path = path.line_to([4.0 + u * (w - 8.0), y(f(u.min(0.999)))]);
    }
    let rates = [1.0, 0.25, 0.125, 2.0];
    let u = (t * rates[kind] * 0.5).fract();
    let p = [4.0 + u * (w - 8.0), y(f(u))];
    Shape::new()
        .stroke_path(&path, 1.5, LineCap::Round, l.accent.alpha(0.75))
        .line(p, [p[0] + 0.01, p[1]], 5.0, LineCap::Round, l.text)
}

fn camera(s: &App, l: &Look) -> El {
    col()
        .w_full()
        .gap(6.0)
        .child(Slider::new("zoom", "Zoom", s.zoom, format!("{:.2}×", s.zoom_x()), |s| &mut s.zoom).build_inline(l))
        .child(Slider::new("yaw", "Yaw", s.yaw, format!("{:+.0}°", s.yaw_deg()), |s| &mut s.yaw).bipolar().build_inline(l))
        .child(Slider::new("pitch", "Pitch", s.pitch, format!("{:+.0}°", (s.pitch - 0.5) * 180.0), |s| &mut s.pitch).bipolar().build_inline(l))
        .child(Slider::new("pan-x", "Pan X", s.pan_x, format!("{:+.2}", (s.pan_x - 0.5) * 2.0), |s| &mut s.pan_x).bipolar().build_inline(l))
        .child(Slider::new("pan-y", "Pan Y", s.pan_y, format!("{:+.2}", (s.pan_y - 0.5) * 2.0), |s| &mut s.pan_y).bipolar().build_inline(l))
        .child(Slider::new("fov", "Field", s.fov, format!("{:.1}°", 20.0 + s.fov * 80.0), |s| &mut s.fov).build_inline(l))
}

const SCREENS: [&str; 3] = ["Output 1", "Output 2", "Control window"];

fn output(s: &App, l: &Look, k: &Kit, layer: &mut Vec<El>) -> El {
    let toggle = |key: &'static str, label: &'static str, on: bool, flip: fn(&mut App)| {
        row()
            .key(key)
            .w_full()
            .h(32.0)
            .center_y()
            .justify_between()
            .child(text(label).font(ty::LABEL).color(l.text2))
            .child(Switch::new(on).label(label).hide_label().on_toggle(flip).build(k))
    };
    let current = s.screen.clone();
    col()
        .w_full()
        .gap(12.0)
        .child(Slider::new("dim", "Master dim", s.dim, format!("{:.0}%", s.dim * 100.0), |s| &mut s.dim).build(l))
        .child(
            col()
                .w_full()
                .gap(6.0)
                .child(caps(l, "Screen"))
                .child(
                    Select::new("screen-select", &SCREENS)
                        .label("Screen")
                        .appearance(SelectAppearance::Field)
                        .details(&[Some("1920×1080 · 60 Hz"), Some("3840×2160 · 30 Hz"), Some("this window")])
                        .current(Some(&current))
                        .open(s.menu == Some("screen"))
                        .on_toggle(|s: &mut App| s.menu = if s.menu == Some("screen") { None } else { Some("screen") })
                        .on_close(|s: &mut App| s.menu = None)
                        .on_choose(|s: &mut App, v: &str, _| {
                            s.screen = v.to_string();
                            s.menu = None;
                        })
                        .width(WIDTH - 32.0)
                        .build(k, layer),
                ),
        )
        .child(
            col()
                .w_full()
                .child(toggle("fullscreen", "Fullscreen", s.fullscreen, |s| s.fullscreen ^= true))
                .child(toggle("flip-x", "Flip X", s.flip_x, |s| s.flip_x ^= true))
                .child(toggle("flip-y", "Flip Y", s.flip_y, |s| s.flip_y ^= true))
                .child(toggle("overlay", "Overlay", s.overlay, |s| s.overlay ^= true)),
        )
}
