//! The inspector: the patch on air and what is selected, then numbered modules (shape, audio,
//! tempo and LFOs, camera, output), each folding to the values it holds.

use rune::{El, TextCase, col, el, row, text};
use rune_kit::{Kit, Select, SelectAppearance};

use crate::App;
use crate::data::{BANDS, SHAPES, Status};
use crate::instruments::{attitude, scope};
use crate::theme::{Look, ty};
use crate::widgets::{Gauge, annunciator, caps, fact, lamp, legend, push, section, selector, seg_meter, state_word, tag};

pub const WIDTH: f32 = 340.0;
const INNER: f32 = WIDTH - 28.0;

pub fn pane(s: &App, l: &Look, k: &Kit, layer: &mut Vec<El>) -> El {
    let body = col()
        .key("sections")
        .w_full()
        .child(patch_card(s, l))
        .child(selection(s, l))
        .child(section(l, "sec-shape", 1, "Shape", format!("{} {:.2}×", s.shape.to_uppercase(), s.brightness_x()), s.open[0], |s| s.open[0] ^= true, shape(s, l, k, layer)))
        .child(section(l, "sec-audio", 2, "Audio", format!("MIC DRV {:.2}×", s.drive_x()), s.open[1], |s| s.open[1] ^= true, audio(s, l)))
        .child(section(l, "sec-tempo", 3, "Tempo · LFO", format!("{:.1} BPM 4 LFO", s.bpm), s.open[2], |s| s.open[2] ^= true, tempo(s, l)))
        .child(section(
            l,
            "sec-camera",
            4,
            "Camera",
            format!("{:.2}× HDG {:03.0}", s.zoom_x(), s.yaw_deg().rem_euclid(360.0)),
            s.open[3],
            |s| s.open[3] ^= true,
            camera(s, l),
        ))
        .child(section(l, "sec-output", 5, "Output", format!("DIM {:.0}% {}", s.dim * 100.0, s.screen.to_uppercase()), s.open[4], |s| s.open[4] ^= true, output(s, l, k, layer)));
    col()
        .key("inspector")
        .w(WIDTH)
        .h_full()
        .fill(l.module)
        .border_sides([0.0, 0.0, 0.0, 1.0], l.line_strong)
        .child(col().key("scroll").w_full().grow(1.0).min_h(0.0).scroll(rune::ScrollSpec { stick_bottom: false }).child(body))
}

/// The patch on air: step through patches, save.
fn patch_card(s: &App, l: &Look) -> El {
    let step = |key: &'static str, glyph: &'static rune::Icon, d: isize| {
        row()
            .key(key)
            .role("button")
            .label(if d < 0 { "Previous patch" } else { "Next patch" })
            .focusable(true)
            .size(28.0, 28.0)
            .center()
            .radius(2.0)
            .fill(l.module)
            .border(1.0, l.line_strong)
            .hover(l.hover)
            .on_press(move |s: &mut App| s.step_patch(d))
            .child(rune::icon(glyph, 14.0).color(l.set).a11y_hidden())
    };
    let p = &crate::data::PATCHES[s.live_patch()];
    col()
        .key("patch")
        .w_full()
        .padding(14.0)
        .gap(10.0)
        .fill(l.bezel)
        .border_sides([0.0, 0.0, 1.0, 0.0], l.line_strong)
        .child(
            row()
                .w_full()
                .center_y()
                .gap(8.0)
                .child(caps(l, "Patch"))
                .child(el().grow(1.0))
                .child(tag(format!("PGM · DECK {}", s.live_deck()), l.alert)),
        )
        .child(
            row()
                .w_full()
                .h(44.0)
                .center_y()
                .gap(8.0)
                .px(8.0)
                .radius(2.0)
                .fill(l.glass)
                .border(1.0, l.line)
                .child(step("prev", &crate::icons::CHEVRON_LEFT, -1))
                .child(text(p.name).key("name").font(ty::BIG).color(l.label).grow(1.0).align(rune::Align::Center))
                .child(step("next", &crate::icons::CHEVRON_RIGHT, 1)),
        )
        .child(
            row()
                .w_full()
                .justify_between()
                .child(text(p.detail.to_uppercase()).font(ty::VALUE_SMALL).color(l.dim))
                .child(text("SAVED 12 MIN").font(ty::VALUE_SMALL).color(l.faint)),
        )
        .child(
            row()
                .w_full()
                .gap(6.0)
                .child(push(l, "save", "Save", l.label, |_| {}).grow(1.0))
                .child(push(l, "save-as", "Save as", l.label, |_| {}).grow(1.0))
                .child(push(l, "new", "New", l.label, |_| {}).grow(1.0)),
        )
}

fn selection(s: &App, l: &Look) -> El {
    let inner = match s.selected.map(|i| &s.nodes[i]) {
        None => row()
            .w_full()
            .h(40.0)
            .center()
            .radius(2.0)
            .fill(l.glass)
            .border(1.0, l.line)
            .child(text("— NO SELECTION —").font(ty::VALUE_SMALL).color(l.faint)),
        Some(n) => {
            let wired = s.cables.iter().filter(|c| s.nodes[c.from.0].id == n.id || s.nodes[c.to.0].id == n.id).count();
            let (word, ink) = match n.status {
                Status::Live => ("LIVE", l.live),
                Status::Idle => ("IDLE", l.dim),
                Status::Missing(_) => ("FAULT", l.caution),
            };
            col()
                .w_full()
                .gap(2.0)
                .child(
                    row()
                        .h(24.0)
                        .gap(8.0)
                        .center_y()
                        .child(text(n.cat.code()).font(ty::CODE).color(l.faint))
                        .child(text(n.title).font(ty::NODE).text_case(TextCase::Uppercase).color(l.label))
                        .child(el().grow(1.0))
                        .child(state_word(word, ink)),
                )
                .child(fact(l, "Ports", format!("{} IN {} OUT", n.ins.len(), n.outs.len())))
                .child(fact(l, "Cables", format!("{wired}")))
                .child(fact(l, "Column", n.cat.name().to_uppercase()))
        }
    };
    col().key("selection").w_full().padding(14.0).gap(8.0).border_sides([0.0, 0.0, 1.0, 0.0], l.line_strong).child(caps(l, "Selection")).child(inner)
}

fn shape(s: &App, l: &Look, k: &Kit, layer: &mut Vec<El>) -> El {
    let (cells, verts, edges, sym, note) = match s.shape.as_str() {
        "Tesseract" => ("8", 16, 32, "{4,3,3}", "HYPERCUBE"),
        "16-cell" => ("16", 8, 24, "{3,3,4}", "HYPEROCTAHEDRON"),
        _ => ("24", 24, 96, "{3,4,3}", "NO 3D COUNTERPART"),
    };
    let hero = row()
        .key("hero")
        .w_full()
        .gap(14.0)
        .center_y()
        .child(
            col()
                .w(78.0)
                .h(56.0)
                .center()
                .radius(2.0)
                .fill(l.glass)
                .border(1.0, l.line)
                .child(text(cells).font(ty::HERO).color(l.live))
                .child(text("CELLS").font(ty::VALUE_SMALL).color(l.dim)),
        )
        .child(
            col()
                .gap(4.0)
                .child(text(s.shape.to_uppercase()).font(ty::NODE).color(l.label))
                .child(text(note).font(ty::VALUE_SMALL).color(l.dim))
                .child(
                    row()
                        .gap(5.0)
                        .child(tag("4D".into(), l.dim))
                        .child(tag(format!("{verts}V {edges}E"), l.dim))
                        .child(tag(sym.into(), l.dim)),
                ),
        );
    let current = s.shape.clone();
    col()
        .w_full()
        .gap(12.0)
        .child(hero)
        .child(
            Select::new("shape-select", &SHAPES)
                .label("Shape")
                .appearance(SelectAppearance::Field)
                .current(Some(&current))
                .open(s.menu == Some("shape"))
                .on_toggle(|s: &mut App| s.menu = if s.menu == Some("shape") { None } else { Some("shape") })
                .on_close(|s: &mut App| s.menu = None)
                .on_choose(|s: &mut App, v: &str, _| s.set_shape(v))
                .width(INNER)
                .build(k, layer),
        )
        .child(Gauge::new("brightness", "Bright · log", s.brightness, format!("{:.2}×", s.brightness_x()), |s| &mut s.brightness).driven().build(l))
        .child(Gauge::new("speed", "Speed · log", s.speed, format!("{:.3}", s.speed_x()), |s| &mut s.speed).build(l))
        .child(Gauge::new("depth", "4D depth", s.depth, format!("{:.2}", 1.6 + s.depth * 2.0), |s| &mut s.depth).build(l))
}

fn audio(s: &App, l: &Look) -> El {
    let mut bands = row().key("bands").w_full().justify_between().px(4.0);
    for (i, (name, plane, _hz)) in BANDS.iter().enumerate() {
        let (v, pk) = s.level(i);
        bands = bands.child(
            col()
                .key(*name)
                .gap(5.0)
                .items_center()
                .child(seg_meter(l, format!("m{i}"), v, pk, 26.0, 84.0))
                .child(text(*name).font(ty::VALUE_SMALL).color(l.label))
                .child(text(*plane).font(ty::VALUE_SMALL).color(l.set)),
        );
    }
    col()
        .w_full()
        .gap(12.0)
        .child(selector(l, "audio-source", &["Mic", "Video", "Track"], s.audio_src, |s, i| s.audio_src = i))
        .child(
            col()
                .w_full()
                .gap(8.0)
                .padding(10.0)
                .radius(2.0)
                .fill(l.glass)
                .border(1.0, l.line)
                .child(row().w_full().justify_between().child(legend(l, "Bands → planes")).child(text("MIC 48K").font(ty::VALUE_SMALL).color(l.live)))
                .child(bands),
        )
        .child(Gauge::new("drive", "Drive · log", s.drive, format!("{:.2}×", s.drive_x()), |s| &mut s.drive).build(l))
        .child(Gauge::new("gain", "Master", s.gain, format!("{:+.1}dB", s.gain_db()), |s| &mut s.gain).build(l))
}

fn tempo(s: &App, l: &Look) -> El {
    let beat = ((s.t * s.bpm / 60.0) as usize) % 4;
    let phase = (s.t * s.bpm / 60.0).fract();
    let mut beats = row().key("beats").gap(4.0).center_y();
    for i in 0..4 {
        beats = beats.child(lamp(if i == 0 { l.caution } else { l.live }, 9.0, i == beat && phase < 0.5).key(format!("b{i}")));
    }
    let bpm = row()
        .key("tempo-bpm")
        .w_full()
        .gap(10.0)
        .center_y()
        .child(
            row()
                .h(40.0)
                .px(10.0)
                .gap(8.0)
                .center_y()
                .radius(2.0)
                .fill(l.glass)
                .border(1.0, l.line)
                .child(text(format!("{:05.1}", s.bpm)).font(ty::BIG).color(l.set))
                .child(col().gap(4.0).child(text("BPM").font(ty::VALUE_SMALL).color(l.dim)).child(beats)),
        )
        .child(el().grow(1.0))
        .child(push(l, "tap", "Tap", l.label, |s| s.bpm = 124.0))
        .child(push(l, "bpm-down", "−", l.label, |s| s.bpm -= 0.5))
        .child(push(l, "bpm-up", "+", l.label, |s| s.bpm += 0.5));
    let lfos: [(&str, &str, &str, usize); 4] = [
        ("LFO 1", "SIN 1/4", "BRIGHTNESS", 0),
        ("LFO 2", "TRI 1 BAR", "CAMERA.YAW", 1),
        ("LFO 3", "SAW 2 BAR", "ROT.XW", 2),
        ("LFO 4", "S&H 1/8", "FX.ACID.MIX", 3),
    ];
    let mut list = col().key("lfos").w_full().radius(2.0).border(1.0, l.line);
    for (i, (name, shape, target, wave)) in lfos.into_iter().enumerate() {
        let mut r = row()
            .key(name)
            .w_full()
            .h(40.0)
            .px(8.0)
            .gap(10.0)
            .center_y()
            .hover(l.hover)
            .child(scope(l, wave, s.t, 52.0, 26.0))
            .child(
                col()
                    .gap(2.0)
                    .child(text(name).font(ty::VALUE_BOLD).color(l.label))
                    .child(text(shape).font(ty::VALUE_SMALL).color(l.dim)),
            )
            .child(el().grow(1.0))
            .child(text(format!("→ {target}")).font(ty::VALUE_SMALL).color(l.driven));
        if i > 0 {
            r = r.border_sides([1.0, 0.0, 0.0, 0.0], l.line);
        }
        list = list.child(r);
    }
    col()
        .w_full()
        .gap(12.0)
        .child(bpm)
        .child(Gauge::new("nudge", "Nudge", s.nudge, format!("{:+.2}", (s.nudge - 0.5) * 2.0), |s| &mut s.nudge).bipolar().build(l))
        .child(list)
        .child(push(l, "add-lfo", "+ Add LFO", l.dim, |_| {}))
}

fn camera(s: &App, l: &Look) -> El {
    col()
        .w_full()
        .gap(6.0)
        .child(attitude(l, (s.pitch - 0.5) * 180.0, s.yaw_deg(), INNER, 112.0))
        .child(el().h(4.0))
        .child(Gauge::new("zoom", "Zoom", s.zoom, format!("{:.2}×", s.zoom_x()), |s| &mut s.zoom).build_inline(l))
        .child(Gauge::new("yaw", "Yaw", s.yaw, format!("{:+.0}°", s.yaw_deg()), |s| &mut s.yaw).bipolar().driven().build_inline(l))
        .child(Gauge::new("pitch", "Pitch", s.pitch, format!("{:+.0}°", (s.pitch - 0.5) * 180.0), |s| &mut s.pitch).bipolar().build_inline(l))
        .child(Gauge::new("pan-x", "Pan X", s.pan_x, format!("{:+.2}", (s.pan_x - 0.5) * 2.0), |s| &mut s.pan_x).bipolar().build_inline(l))
        .child(Gauge::new("pan-y", "Pan Y", s.pan_y, format!("{:+.2}", (s.pan_y - 0.5) * 2.0), |s| &mut s.pan_y).bipolar().build_inline(l))
        .child(Gauge::new("fov", "FOV", s.fov, format!("{:.1}°", 20.0 + s.fov * 80.0), |s| &mut s.fov).build_inline(l))
}

const SCREENS: [&str; 3] = ["Output 1", "Output 2", "Control window"];

fn output(s: &App, l: &Look, k: &Kit, layer: &mut Vec<El>) -> El {
    let current = s.screen.clone();
    col()
        .w_full()
        .gap(12.0)
        .child(Gauge::new("dim", "Master dim", s.dim, format!("{:.0}%", s.dim * 100.0), |s| &mut s.dim).build(l))
        .child(
            col().w_full().gap(6.0).child(legend(l, "Screen")).child(
                Select::new("screen-select", &SCREENS)
                    .label("Screen")
                    .appearance(SelectAppearance::Field)
                    .details(&[Some("1920×1080 60Hz"), Some("3840×2160 30Hz"), Some("this window")])
                    .current(Some(&current))
                    .open(s.menu == Some("screen"))
                    .on_toggle(|s: &mut App| s.menu = if s.menu == Some("screen") { None } else { Some("screen") })
                    .on_close(|s: &mut App| s.menu = None)
                    .on_choose(|s: &mut App, v: &str, _| {
                        s.screen = v.to_string();
                        s.menu = None;
                    })
                    .width(INNER)
                    .build(k, layer),
            ),
        )
        .child(
            row()
                .w_full()
                .gap(6.0)
                .child(annunciator(l, "fullscreen", "Full", s.fullscreen, l.live, |s| s.fullscreen ^= true))
                .child(annunciator(l, "flip-x", "Flip X", s.flip_x, l.live, |s| s.flip_x ^= true))
                .child(annunciator(l, "flip-y", "Flip Y", s.flip_y, l.live, |s| s.flip_y ^= true))
                .child(annunciator(l, "overlay", "Ovly", s.overlay, l.live, |s| s.overlay ^= true)),
        )
}
