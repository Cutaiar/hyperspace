//! A few icons rune-kit's glyph set doesn't have, drawn on its 16-point grid.

use rune::Icon;

pub static PLUS: Icon = Icon {
    name: "hs-plus",
    view: 16.0,
    body: r#"<path d="M8 3.5V12.5M3.5 8H12.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>"#,
};

pub static CHEVRON_LEFT: Icon = Icon {
    name: "hs-chevron-left",
    view: 16.0,
    body: r#"<path d="M9.75 4L5.75 8L9.75 12" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>"#,
};

pub static CHEVRON_RIGHT: Icon = Icon {
    name: "hs-chevron-right",
    view: 16.0,
    body: r#"<path d="M6.25 4L10.25 8L6.25 12" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" fill="none"/>"#,
};
