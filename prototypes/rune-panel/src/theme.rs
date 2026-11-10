//! The look: an instrument panel, where colour is meaning and never decoration. Every view
//! paints from the roles below; a scheme says what colour each role is.
//!
//! - `label`, `dim`, `faint`: legends and scales, at three intensities;
//! - `live`: what is measured, normal, live;
//! - `set`: what the operator set;
//! - `driven`: what automation drives (LFOs, envelopes, the sequencer);
//! - `caution`;
//! - `alert`: warning, and on air.
//!
//! The default scheme lights the panel as late-2000s BMW dashboards were lit: one dark
//! burnt orange on black, legends a dimmer orange, the hottest lamp for what you set and the
//! needle's red-orange for what automation drives. `Phosphor` is the glass cockpit before it:
//! green phosphor, white legends, cyan and magenta.
//!
//! Type is B612, the face Airbus had made for cockpit screens.

use rune::tok::{Family, TextStyle};
use rune::{Color, oklch};
use rune_kit::{Kit, PaletteSeed};

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub enum Scheme {
    /// Burnt orange on black.
    Orange,
    /// Green phosphor, white legends.
    Phosphor,
}

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
    pub live: Color,
    pub set: Color,
    pub driven: Color,
    pub caution: Color,
    pub alert: Color,
    pub hover: Color,
}

pub fn look(scheme: Scheme) -> Look {
    match scheme {
        Scheme::Orange => Look {
            bezel: oklch(0.165, 0.004, 50.0),
            module: oklch(0.135, 0.004, 50.0),
            glass: oklch(0.075, 0.003, 50.0),
            grid: oklch(0.63, 0.165, 43.0).alpha(0.09),
            line: oklch(0.85, 0.03, 60.0).alpha(0.08),
            line_strong: oklch(0.85, 0.03, 60.0).alpha(0.15),
            label: oklch(0.78, 0.08, 58.0),
            dim: oklch(0.58, 0.07, 52.0),
            faint: oklch(0.43, 0.05, 50.0),
            live: oklch(0.63, 0.165, 43.0),
            set: oklch(0.90, 0.075, 75.0),
            driven: oklch(0.67, 0.19, 34.0),
            caution: oklch(0.86, 0.16, 92.0),
            alert: oklch(0.53, 0.21, 25.0),
            hover: oklch(0.85, 0.05, 60.0).alpha(0.04),
        },
        Scheme::Phosphor => Look {
            bezel: oklch(0.175, 0.004, 250.0),
            module: oklch(0.145, 0.004, 250.0),
            glass: oklch(0.085, 0.003, 250.0),
            grid: oklch(0.7, 0.02, 160.0).alpha(0.10),
            line: oklch(0.9, 0.0, 0.0).alpha(0.08),
            line_strong: oklch(0.9, 0.0, 0.0).alpha(0.16),
            label: oklch(0.90, 0.004, 95.0),
            dim: oklch(0.64, 0.006, 250.0),
            faint: oklch(0.46, 0.006, 250.0),
            live: oklch(0.82, 0.17, 145.0),
            set: oklch(0.83, 0.11, 205.0),
            driven: oklch(0.72, 0.19, 335.0),
            caution: oklch(0.81, 0.15, 78.0),
            alert: oklch(0.64, 0.21, 27.0),
            hover: oklch(0.9, 0.0, 0.0).alpha(0.04),
        },
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
    let mut k = Kit::from_palette(PaletteSeed { bg: l.module, fg: l.label, accent: l.set });
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
