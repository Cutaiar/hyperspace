//! Hyperspace's control window, redrawn in Rune as a glass cockpit: a UI-only proof of
//! concept.
//!
//! Nothing here drives a renderer or reads a device. The graph, the decks, the inspector and
//! the library are the real app's information, laid out again with Rune's layout, springs and
//! rune-kit's components. `cargo run` opens the window; `-- --snap out.png` renders it headless
//! (see the README for the scenes).

mod chrome;
mod data;
mod graph;
mod icons;
mod inspector;
mod instruments;
mod polytope;
mod theme;
mod widgets;

use rune::{AppSpec, Cx, El, KeyEvent, Tx, col, row};

use crate::data::{Cable, Node, SHAPES};
use crate::polytope::Polytope;

pub struct App {
    /// Seconds since launch (virtual when headless).
    pub t: f32,
    pub spin: bool,

    // Decks
    pub on_air: usize,
    pub cue: usize,
    /// 0: deck 1 fully on air; 1: deck 2.
    pub xfade: f32,
    pub fade_s: f32,

    // Graph
    pub nodes: Vec<Node>,
    pub cables: Vec<Cable>,
    pub selected: Option<usize>,
    pub drag0: [f32; 2],
    pub pan: [f32; 2],
    pub pan0: [f32; 2],
    pub filter: usize,
    pub behind: bool,
    pub behind_opacity: f32,
    pub pictures: bool,
    pub tint: bool,

    // Inspector: which sections are open, and the values, each 0..1 along its control.
    pub open: [bool; 5],
    pub menu: Option<&'static str>,
    pub shape: String,
    pub shape_poly: Polytope,
    pub cue_poly: Polytope,
    pub logo_poly: Polytope,
    pub brightness: f32,
    pub speed: f32,
    pub depth: f32,
    pub audio_src: usize,
    pub drive: f32,
    pub gain: f32,
    pub bpm: f32,
    pub nudge: f32,
    pub zoom: f32,
    pub yaw: f32,
    pub pitch: f32,
    pub pan_x: f32,
    pub pan_y: f32,
    pub fov: f32,
    pub dim: f32,
    pub screen: String,
    pub fullscreen: bool,
    pub flip_x: bool,
    pub flip_y: bool,
    pub overlay: bool,
}

fn init() -> App {
    let (nodes, cables) = data::patch();
    App {
        t: 0.0,
        spin: true,
        on_air: 0,
        cue: 1,
        xfade: 0.0,
        fade_s: 2.0,
        nodes,
        cables,
        selected: None,
        drag0: [0.0; 2],
        pan: [0.0; 2],
        pan0: [0.0; 2],
        filter: 0,
        behind: true,
        behind_opacity: 0.35,
        pictures: true,
        tint: true,
        open: [true, true, true, false, false],
        menu: None,
        shape: "24-cell".into(),
        shape_poly: polytope::cell24(),
        cue_poly: polytope::tesseract(),
        logo_poly: polytope::tesseract(),
        brightness: 0.75,
        // 0.300 on the log taper
        speed: 15f32.ln() / 50f32.ln(),
        depth: 0.4,
        audio_src: 0,
        drive: 0.5,
        gain: 24.0 / 36.0,
        bpm: 120.0,
        nudge: 0.5,
        zoom: (1.3f32 / 0.5).ln() / 6f32.ln(),
        yaw: 0.5,
        pitch: 0.5,
        pan_x: 0.5,
        pan_y: 0.5,
        fov: (47.6 - 20.0) / 80.0,
        dim: 1.0,
        screen: "Output 1".into(),
        fullscreen: true,
        flip_x: false,
        flip_y: false,
        overlay: false,
    }
}

impl App {
    /// 0.25× to 4×, log, 1× in the middle.
    pub fn brightness_x(&self) -> f32 {
        0.25 * 16f32.powf(self.brightness)
    }
    pub fn speed_x(&self) -> f32 {
        0.02 * 50f32.powf(self.speed)
    }
    pub fn drive_x(&self) -> f32 {
        0.25 * 16f32.powf(self.drive)
    }
    pub fn gain_db(&self) -> f32 {
        -24.0 + self.gain * 36.0
    }
    pub fn zoom_x(&self) -> f32 {
        0.5 * 6f32.powf(self.zoom)
    }
    pub fn yaw_deg(&self) -> f32 {
        (self.yaw - 0.5) * 360.0
    }

    /// A band's level and held peak: a made-up signal, steady enough to read.
    pub fn level(&self, i: usize) -> (f32, f32) {
        let f = i as f32;
        let beat = (self.t * self.bpm / 60.0).fract();
        let kick = if i < 2 { (1.0 - beat).powf(4.0) * 0.5 } else { 0.0 };
        let v = 0.3 + 0.18 * (self.t * (1.3 + f * 0.7) + f).sin() + 0.1 * (self.t * 5.1 + f * 2.0).sin() + kick;
        let v = (v * (0.8 + 0.4 * self.drive)).clamp(0.04, 1.0);
        (v, (v + 0.12 + 0.05 * (self.t * 0.7 + f).sin()).min(1.0))
    }

    /// Which deck the crossfader puts on air: 1 or 2.
    pub fn live_deck(&self) -> usize {
        if self.xfade < 0.5 { 1 } else { 2 }
    }
    /// The patch on air, whichever deck holds it.
    pub fn live_patch(&self) -> usize {
        if self.live_deck() == 1 { self.on_air } else { self.cue }
    }

    pub fn set_shape(&mut self, name: &str) {
        self.shape = name.to_string();
        self.shape_poly = match name {
            "Tesseract" => polytope::tesseract(),
            "16-cell" => polytope::cell16(),
            _ => polytope::cell24(),
        };
        self.menu = None;
    }

    pub fn step_patch(&mut self, d: isize) {
        let n = data::PATCHES.len() as isize;
        self.on_air = ((self.on_air as isize + d).rem_euclid(n)) as usize;
        if self.cue == self.on_air {
            self.cue = (self.cue + 1) % data::PATCHES.len();
        }
    }

    /// Re-stacks every column, as the GRAPH's Tidy does.
    pub fn tidy(&mut self) {
        let (fresh, _) = data::patch();
        for (n, f) in self.nodes.iter_mut().zip(fresh) {
            n.pos = f.pos;
        }
        self.pan = [0.0, 0.0];
    }
}

fn view(s: &App, cx: &mut Cx<App>) -> El {
    let vw = cx.layout_size("viewport").map_or(1076.0, |sz| sz[0]);
    let l = theme::look();
    let k = theme::kit(&l);
    let mut layer = Vec::new();
    let body = col()
        .key("window")
        .w_full()
        .h_full()
        .fill(l.bezel)
        .child(chrome::top_bar(s, &l, &k))
        .child(
            row()
                .key("main")
                .w_full()
                .grow(1.0)
                .min_h(0.0)
                .child(chrome::library(s, &l))
                .child(graph::pane(s, &l, &k, vw))
                .child(inspector::pane(s, &l, &k, &mut layer)),
        )
        .child(chrome::status_bar(s, &l));
    rune_kit::root(body, layer)
}

/// The shape turns, the meters move and the cables pulse: a frame whenever the clock moves.
fn poll(s: &mut App, t: f64, tx: &mut Tx) -> bool {
    if !s.spin {
        return false;
    }
    s.t = t as f32;
    tx.wake_after(std::time::Duration::from_millis(16));
    true
}

fn on_key(s: &mut App, ev: &KeyEvent, _: &mut Tx) -> bool {
    if matches!(ev.key, rune::Key::Escape) {
        s.selected = None;
        s.menu = None;
        return true;
    }
    false
}

fn main() {
    rune::run(AppSpec::<App> {
        scenes: &[
            ("default", |_| {}),
            ("selected", |s| s.selected = Some(10)),
            ("analyzer", |s| s.selected = Some(3)),
            ("effects", |s| s.pan[0] = graph::pan_limit(-(data::column_x(theme::Cat::Media) - data::MARGIN), 1076.0)),
            ("folded", |s| s.open = [false; 5]),
            ("camera", |s| s.open = [false, false, false, true, true]),
            ("shape-menu", |s| s.menu = Some("shape")),
            ("tesseract", |s| s.set_shape(SHAPES[1])),
            ("patched", |s| s.filter = 2),
            ("plain", |s| {
                s.tint = false;
                s.pictures = false;
                s.behind = false;
            }),
            ("taken", |s| s.xfade = 1.0),
            ("still", |s| s.spin = false),
        ],
        poll: Some(poll),
        on_key: Some(on_key),
        min_size: Some((1280.0, 760.0)),
        fonts: theme::FONTS,
        families: (theme::SANS, theme::MONO),
        ..AppSpec::new("Hyperspace", (1680.0, 1000.0), init, view)
    });
}
