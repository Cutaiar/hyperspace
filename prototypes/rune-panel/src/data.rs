//! The mock patch: nodes and cables as the GRAPH page lists them, with the names the real app
//! uses (ports, bands, planes, effects). Nothing here is live; it is what the view draws.

use crate::theme::Cat;

#[derive(Clone, Copy, PartialEq)]
pub enum Status {
    /// Something arrives on it this frame.
    Live,
    /// Patched, nothing arriving.
    Idle,
    /// Patched, but the device isn't here.
    Missing(&'static str),
}

pub struct Node {
    pub id: &'static str,
    pub title: &'static str,
    pub cat: Cat,
    pub detail: &'static str,
    pub status: Status,
    pub ins: Vec<&'static str>,
    pub outs: Vec<&'static str>,
    /// Draws a thumbnail of its picture (a media node).
    pub thumb: bool,
    /// Top-left, in canvas points.
    pub pos: [f32; 2],
}

pub struct Cable {
    pub from: (usize, usize),
    pub to: (usize, usize),
    pub live: bool,
}

pub const NODE_W: f32 = 158.0;
pub const PITCH: f32 = 186.0;
pub const MARGIN: f32 = 28.0;
pub const TOP: f32 = 64.0;
pub const HEADER: f32 = 34.0;
pub const ROW: f32 = 19.0;
pub const FOOTER: f32 = 26.0;
pub const THUMB: f32 = 74.0;

impl Node {
    pub fn rows(&self) -> usize {
        self.ins.len().max(self.outs.len())
    }
    pub fn height(&self) -> f32 {
        HEADER + if self.thumb { THUMB + 8.0 } else { 0.0 } + self.rows() as f32 * ROW + 6.0 + FOOTER
    }
    fn port_y(&self, i: usize) -> f32 {
        self.pos[1] + HEADER + if self.thumb { THUMB + 8.0 } else { 0.0 } + i as f32 * ROW + ROW / 2.0
    }
    pub fn out_at(&self, i: usize) -> [f32; 2] {
        [self.pos[0] + NODE_W, self.port_y(i)]
    }
    pub fn in_at(&self, i: usize) -> [f32; 2] {
        [self.pos[0], self.port_y(i)]
    }
}

pub fn world_w() -> f32 {
    MARGIN * 2.0 + PITCH * 7.0 + NODE_W
}

pub fn column_x(c: Cat) -> f32 {
    MARGIN + c.index() as f32 * PITCH
}

/// The party show's TUMBLE patch, roughly.
pub fn patch() -> (Vec<Node>, Vec<Cable>) {
    use Cat::*;
    use Status::*;
    let n = |id, title, cat, detail, status, ins: &[&'static str], outs: &[&'static str]| Node {
        id,
        title,
        cat,
        detail,
        status,
        ins: ins.to_vec(),
        outs: outs.to_vec(),
        thumb: false,
        pos: [0.0, 0.0],
    };
    let mut nodes = vec![
        n("keys", "Keyboard", Controllers, "47 ports · 47 patched", Idle, &[], &["space", "arrows", "1 … 9", "shift"]),
        n("leap", "Leap Motion", Controllers, "7 ports · 7 patched", Missing("not set up on this Mac"), &[], &[
            "left.roll",
            "left.pitch",
            "right.y",
            "right.z",
        ]),
        n("apc", "APC40 mkII", Controllers, "117 ports · 117 patched", Missing("unplugged"), &[], &[
            "faders 1–8",
            "knobs 1–8",
            "clip grid",
        ]),
        n("analyzer", "Analyzer", Audio, "6 bands · mic", Live, &["input"], &["SUB", "BASS", "MIDB", "MID", "UPR", "AIR"]),
        n("tempo", "Tempo", Audio, "120.0 BPM · tap", Live, &[], &["beat", "bar", "phase"]),
        n("lfo", "LFO bank", Modulation, "4 voices", Live, &["rate"], &["LFO 1 · sine", "LFO 2 · tri", "LFO 3 · saw", "LFO 4 · S&H"]),
        n("seq", "Sequencer", Modulation, "5 lanes × 8 steps", Live, &["clock"], &["lanes 1–5"]),
        n("env", "Envelopes", Modulation, "AHDSR × 5", Idle, &["trigger"], &["env 1", "env 2"]),
        Node { thumb: true, ..n("faces", "Faces pattern", Media, "voronoi · 17 patterns", Live, &[], &["texture"]) },
        n("chan", "Channel A", Media, "camera · 1280×720", Idle, &[], &["frame"]),
        n("shape", "Shape", Scene, "24-cell · {3,4,3}", Live, &[
            "faces", "camera", "rot.XY", "rot.XZ", "rot.XW", "rot.YW", "rot.ZW", "speed", "brightness",
        ], &["geometry"]),
        n("camera", "Camera", Scene, "1.30× · 47.6°", Idle, &["zoom", "yaw", "pitch"], &["view"]),
        n("lookback", "Look-back", LookBack, "32 frames · trails", Live, &["frame", "feedback"], &["trails"]),
        n("acid", "Acid", Effects, "fx/acid.glsl", Live, &["in", "mix"], &["out"]),
        n("kaleido", "Kaleido", Effects, "fx/kaleido.glsl", Idle, &["in", "segments"], &["out"]),
        n("out1", "Output 1", Outputs, "1920×1080 · 60 Hz", Live, &["program"], &[]),
        n("syphon", "Syphon", Outputs, "publishing", Idle, &["program"], &[]),
    ];
    // Stack each column.
    for c in Cat::ALL {
        let mut y = TOP;
        for node in nodes.iter_mut().filter(|x| x.cat == c) {
            node.pos = [column_x(c), y];
            y += node.height() + 18.0;
        }
    }
    let at = |id: &str| nodes.iter().position(|x| x.id == id).unwrap();
    let w = |a: &str, ap: usize, b: &str, bp: usize, live: bool| Cable { from: (at(a), ap), to: (at(b), bp), live };
    let cables = vec![
        w("leap", 0, "shape", 2, false),
        w("leap", 2, "shape", 7, false),
        w("keys", 1, "camera", 2, false),
        w("apc", 0, "shape", 8, false),
        w("analyzer", 0, "shape", 6, true),
        w("analyzer", 1, "shape", 4, true),
        w("analyzer", 2, "shape", 5, true),
        w("analyzer", 3, "shape", 2, true),
        w("analyzer", 4, "shape", 3, true),
        w("tempo", 0, "lfo", 0, true),
        w("tempo", 0, "seq", 0, true),
        w("seq", 0, "env", 0, true),
        w("lfo", 0, "shape", 8, true),
        w("lfo", 1, "camera", 1, true),
        w("env", 0, "acid", 1, false),
        w("faces", 0, "shape", 0, true),
        w("camera", 0, "shape", 1, false),
        w("shape", 0, "lookback", 0, true),
        w("lookback", 0, "acid", 0, true),
        w("acid", 0, "kaleido", 0, true),
        w("kaleido", 0, "out1", 0, true),
        w("kaleido", 0, "syphon", 0, false),
    ];
    (nodes, cables)
}

pub struct Patch {
    pub name: &'static str,
    pub detail: &'static str,
    pub hue: f32,
}

pub const PATCHES: [Patch; 10] = [
    Patch { name: "TUMBLE", detail: "24-cell · bands → planes", hue: 215.0 },
    Patch { name: "ACID", detail: "tesseract · acid, kaleido", hue: 140.0 },
    Patch { name: "FACES", detail: "16-cell · voronoi faces", hue: 350.0 },
    Patch { name: "TRACER", detail: "600-cell · look-back", hue: 260.0 },
    Patch { name: "FIELD", detail: "instances · FCC lattice", hue: 190.0 },
    Patch { name: "WAKE", detail: "Clifford torus · dream", hue: 300.0 },
    Patch { name: "TRIP", detail: "grand antiprism · warp", hue: 40.0 },
    Patch { name: "MANDALA", detail: "120-cell · kaleido", hue: 80.0 },
    Patch { name: "NOITA", detail: "5-cell · plasma", hue: 20.0 },
    Patch { name: "TUMBLE II", detail: "24-cell · slow", hue: 230.0 },
];

pub struct Device {
    pub name: &'static str,
    pub detail: &'static str,
    pub status: Status,
}

pub const DEVICES: [Device; 5] = [
    Device { name: "Keyboard", detail: "47 ports", status: Status::Idle },
    Device { name: "Microphone", detail: "MacBook Pro mic · 48 kHz", status: Status::Live },
    Device { name: "Leap Motion", detail: "not set up on this Mac", status: Status::Missing("") },
    Device { name: "APC40 mkII", detail: "unplugged", status: Status::Missing("") },
    Device { name: "DualSense Edge", detail: "Bluetooth · 82%", status: Status::Live },
];

/// The analyzer's bands, low to high, and the plane each one turns.
pub const BANDS: [(&str, &str, &str); 6] = [
    ("SUB", "ZW", "20–60 Hz"),
    ("BASS", "XW", "60–160"),
    ("MIDB", "YW", "160–400"),
    ("MID", "XY", "400–1.2k"),
    ("UPR", "XZ", "1.2–4k"),
    ("AIR", "YZ", "4–14k"),
];

pub const SHAPES: [&str; 12] = [
    "5-cell",
    "Tesseract",
    "16-cell",
    "24-cell",
    "120-cell",
    "600-cell",
    "Rectified 5-cell",
    "Truncated tesseract",
    "6,6-duoprism",
    "Grand antiprism",
    "Clifford torus",
    "Klein bottle",
];
