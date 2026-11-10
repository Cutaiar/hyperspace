//! The look: a small set of design tokens on top of rune-kit's `Kit`.
//!
//! One accent (a cool cyan) for interaction, red reserved for what is on air, amber for
//! warnings, and one hue per graph column so a cable says where it comes from.

use rune::tok::TextStyle;
use rune::{Color, oklch};
use rune_kit::{Kit, PaletteSeed};

#[derive(Clone, Copy)]
pub struct Look {
    /// Behind everything: the window's own colour.
    pub window: Color,
    /// The side panes.
    pub panel: Color,
    /// Cards and controls on a panel.
    pub raised: Color,
    /// The graph canvas.
    pub canvas: Color,
    pub grid: Color,
    /// Hairlines between areas, and the stronger rule around controls.
    pub line: Color,
    pub line_strong: Color,
    pub text: Color,
    pub text2: Color,
    pub text3: Color,
    pub accent: Color,
    pub accent_soft: Color,
    /// On air.
    pub live: Color,
    pub warn: Color,
    pub ok: Color,
    pub track: Color,
    pub hover: Color,
    pub knob: Color,
}

pub fn look() -> Look {
    Look {
        window: oklch(0.135, 0.006, 265.0),
        panel: oklch(0.165, 0.007, 265.0),
        raised: oklch(0.205, 0.008, 265.0),
        canvas: oklch(0.118, 0.006, 265.0),
        grid: oklch(0.62, 0.01, 265.0).alpha(0.07),
        line: oklch(0.85, 0.01, 265.0).alpha(0.08),
        line_strong: oklch(0.85, 0.01, 265.0).alpha(0.14),
        text: oklch(0.95, 0.004, 265.0),
        text2: oklch(0.74, 0.01, 265.0),
        text3: oklch(0.56, 0.012, 265.0),
        accent: oklch(0.80, 0.12, 215.0),
        accent_soft: oklch(0.80, 0.12, 215.0).alpha(0.16),
        live: oklch(0.65, 0.21, 25.0),
        warn: oklch(0.82, 0.14, 78.0),
        ok: oklch(0.78, 0.15, 152.0),
        track: oklch(0.85, 0.01, 265.0).alpha(0.10),
        hover: oklch(0.9, 0.01, 265.0).alpha(0.05),
        knob: oklch(0.97, 0.004, 265.0),
    }
}

/// The kit, seeded from the look so its buttons, switches and menus sit in the same palette.
pub fn kit(l: &Look) -> Kit {
    let mut k = Kit::from_palette(PaletteSeed { bg: l.panel, fg: l.text, accent: l.accent });
    k.radius.sm = 5.0;
    k.radius.md = 7.0;
    k
}

/// Type: Inter throughout, tabular figures wherever a number moves.
pub mod ty {
    use super::TextStyle;

    pub const CAPS: TextStyle = TextStyle::new(10.5, 600.0).tracking(0.9);
    pub const LABEL: TextStyle = TextStyle::new(12.0, 450.0);
    pub const LABEL_STRONG: TextStyle = TextStyle::new(12.0, 600.0);
    pub const SMALL: TextStyle = TextStyle::new(11.0, 450.0);
    pub const VALUE: TextStyle = TextStyle::new(11.5, 500.0).features("'tnum' 1");
    pub const VALUE_SMALL: TextStyle = TextStyle::new(10.5, 500.0).features("'tnum' 1");
    pub const TITLE: TextStyle = TextStyle::new(13.0, 600.0);
    pub const NODE: TextStyle = TextStyle::new(12.5, 600.0);
    pub const HERO: TextStyle = TextStyle::new(34.0, 600.0).tracking(-1.0).features("'tnum' 1");
    pub const BIG: TextStyle = TextStyle::new(22.0, 600.0).tracking(-0.5).features("'tnum' 1");
    pub const COLUMN: TextStyle = TextStyle::new(11.0, 650.0).tracking(1.4);
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

    pub fn index(self) -> usize {
        Cat::ALL.iter().position(|c| *c == self).unwrap_or(0)
    }

    pub fn hue(self) -> Color {
        match self {
            Cat::Controllers => oklch(0.80, 0.13, 75.0),
            Cat::Audio => oklch(0.78, 0.15, 152.0),
            Cat::Modulation => oklch(0.72, 0.16, 295.0),
            Cat::Media => oklch(0.74, 0.15, 350.0),
            Cat::Scene => oklch(0.80, 0.12, 215.0),
            Cat::LookBack => oklch(0.72, 0.13, 255.0),
            Cat::Effects => oklch(0.76, 0.15, 45.0),
            Cat::Outputs => oklch(0.86, 0.01, 265.0),
        }
    }
}
