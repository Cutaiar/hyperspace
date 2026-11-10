//! The look: a glass cockpit. Colour is meaning, as on a flight deck's displays, never
//! decoration:
//!
//! - white: labels and scales;
//! - green: what is measured, normal, live;
//! - cyan: what the operator set;
//! - magenta: what automation drives (LFOs, envelopes, the sequencer);
//! - amber: caution;
//! - red: warning, and on air.
//!
//! Type is B612, the face Airbus had made for cockpit screens, and its mono for numbers.

use rune::tok::{Family, TextStyle};
use rune::{Color, oklch};
use rune_kit::{Kit, PaletteSeed};

#[derive(Clone, Copy)]
pub struct Look {
    /// The panel the instruments are set in.
    pub bezel: Color,
    /// A module's face.
    pub module: Color,
    /// A screen: the canvas, the monitors, readouts.
    pub glass: Color,
    pub grid: Color,
    pub line: Color,
    pub line_strong: Color,
    pub label: Color,
    pub dim: Color,
    pub faint: Color,
    pub green: Color,
    pub cyan: Color,
    pub magenta: Color,
    pub amber: Color,
    pub red: Color,
    pub hover: Color,
}

pub fn look() -> Look {
    Look {
        bezel: oklch(0.175, 0.004, 250.0),
        module: oklch(0.145, 0.004, 250.0),
        glass: oklch(0.085, 0.003, 250.0),
        grid: oklch(0.7, 0.02, 160.0).alpha(0.10),
        line: oklch(0.9, 0.0, 0.0).alpha(0.08),
        line_strong: oklch(0.9, 0.0, 0.0).alpha(0.16),
        label: oklch(0.90, 0.004, 95.0),
        dim: oklch(0.64, 0.006, 250.0),
        faint: oklch(0.46, 0.006, 250.0),
        green: oklch(0.82, 0.17, 145.0),
        cyan: oklch(0.83, 0.11, 205.0),
        magenta: oklch(0.72, 0.19, 335.0),
        amber: oklch(0.81, 0.15, 78.0),
        red: oklch(0.64, 0.21, 27.0),
        hover: oklch(0.9, 0.0, 0.0).alpha(0.04),
    }
}

pub const SANS: &str = "B612";
pub const MONO: &str = "B612 Mono";
pub const FONTS: &[&[u8]] = &[
    include_bytes!("../fonts/B612-Regular.ttf"),
    include_bytes!("../fonts/B612-Bold.ttf"),
    include_bytes!("../fonts/B612Mono-Regular.ttf"),
    include_bytes!("../fonts/B612Mono-Bold.ttf"),
];

/// The kit, squared off and set in B612, so its menus sit in the same panel.
pub fn kit(l: &Look) -> Kit {
    let mut k = Kit::from_palette(PaletteSeed { bg: l.module, fg: l.label, accent: l.cyan });
    k.radius.xs = 1.0;
    k.radius.sm = 2.0;
    k.radius.md = 2.0;
    k.radius.lg = 3.0;
    k.radius.xl = 4.0;
    let sans = |size: f32, w: f32| TextStyle::new(size, w).family(Family::Sans);
    k.ty.ui = sans(12.0, 400.0);
    k.ty.ui_medium = sans(12.0, 700.0);
    k.ty.ui_compact = sans(12.0, 400.0).lh(16.0);
    k.ty.small = sans(10.5, 400.0);
    k.ty.small_medium = sans(10.5, 700.0);
    k.ty.text_small = sans(12.0, 400.0);
    k.ty.text_small_medium = sans(12.0, 700.0);
    k.ty.text_xsmall = sans(11.0, 400.0);
    k.ty.text_xsmall_medium = sans(11.0, 700.0);
    k.ty.mono = TextStyle::new(12.0, 400.0).mono();
    k
}

pub mod ty {
    use super::TextStyle;

    // Numbers are set in B612 with tabular figures: B612 Mono gives a point or a colon a whole
    // cell, which reads "2. 00". Mono is kept for codes (CTL, AUD) and key caps.
    const TNUM: &str = "'tnum' 1";

    /// Module titles: small, bold, tracked capitals.
    pub const CAPS: TextStyle = TextStyle::new(10.0, 700.0).tracking(1.4);
    /// Control legends, in capitals.
    pub const LABEL: TextStyle = TextStyle::new(10.5, 400.0).tracking(0.6);
    pub const LABEL_STRONG: TextStyle = TextStyle::new(11.0, 700.0).tracking(0.5);
    pub const VALUE: TextStyle = TextStyle::new(12.0, 400.0).features(TNUM);
    pub const VALUE_SMALL: TextStyle = TextStyle::new(10.0, 400.0).features(TNUM).tracking(0.3);
    pub const VALUE_BOLD: TextStyle = TextStyle::new(10.5, 700.0).features(TNUM).tracking(0.8);
    pub const CODE: TextStyle = TextStyle::new(9.5, 400.0).mono();
    pub const NODE: TextStyle = TextStyle::new(11.0, 700.0).tracking(0.5);
    pub const HERO: TextStyle = TextStyle::new(30.0, 400.0).features(TNUM);
    pub const BIG: TextStyle = TextStyle::new(20.0, 400.0).features(TNUM).tracking(0.5);
    pub const COLUMN: TextStyle = TextStyle::new(10.0, 700.0).tracking(1.6);
}

/// The graph's columns, in the order a signal travels.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Cat {
    Controllers,
    Audio,
    Modulation,
    Media,
    Scene,
    LookBack,
    Effects,
    Outputs,
}

impl Cat {
    pub const ALL: [Cat; 8] =
        [Cat::Controllers, Cat::Audio, Cat::Modulation, Cat::Media, Cat::Scene, Cat::LookBack, Cat::Effects, Cat::Outputs];

    pub fn name(self) -> &'static str {
        match self {
            Cat::Controllers => "Controllers",
            Cat::Audio => "Audio",
            Cat::Modulation => "Modulation",
            Cat::Media => "Media",
            Cat::Scene => "Scene",
            Cat::LookBack => "Look-back",
            Cat::Effects => "Effects",
            Cat::Outputs => "Outputs",
        }
    }

    /// The three-letter code a node's header carries.
    pub fn code(self) -> &'static str {
        match self {
            Cat::Controllers => "CTL",
            Cat::Audio => "AUD",
            Cat::Modulation => "MOD",
            Cat::Media => "MED",
            Cat::Scene => "SCN",
            Cat::LookBack => "LBK",
            Cat::Effects => "FX",
            Cat::Outputs => "OUT",
        }
    }

    pub fn index(self) -> usize {
        Cat::ALL.iter().position(|c| *c == self).unwrap_or(0)
    }
}
