/**
 * HYPERSPACE HOME SCREEN WIDGET
 * https://hyperspace.cutaiar.io
 *
 * SETUP
 * 1. Install Scriptable from the iOS App Store.
 * 2. Create a new script named "Hyperspace".
 * 3. Paste this file and save it.
 * 4. Run once to preview the widget.
 * 5. Long-press the Home Screen and tap Edit > Add Widget.
 * 6. Find Scriptable and add the LARGE widget.
 * 7. Long-press the widget, choose Edit Widget,
 *    and select the "Hyperspace" script.
 *
 * NOTE
 * Update QR_VALUE to match the actual QR payload
 * displayed by your website.
 */

// Configuration
const SITE_URL = "https://hyperspace.cutaiar.io";
const QR_VALUE = "https://hyperspace.cutaiar.io";
const TITLE = "Hyperspace";

const QR_SIZE = 164;
const QR_PADDING = 8;

// Widget setup
const widget = new ListWidget();
widget.backgroundColor = new Color("#000000");
widget.setPadding(16, 16, 16, 16);
widget.url = SITE_URL;

// Title
const title = widget.addText(TITLE);
title.font = Font.boldSystemFont(16);
title.textColor = Color.white();
title.centerAlignText();

widget.addSpacer(12);

// Generate QR code
const qrURL =
  "https://api.qrserver.com/v1/create-qr-code/" +
  "?size=400x400&margin=0&data=" +
  encodeURIComponent(QR_VALUE);

const request = new Request(qrURL);
const qrImage = await request.loadImage();

// Center QR tile
widget.addSpacer();

const row = widget.addStack();
row.layoutHorizontally();
row.addSpacer();

const qrContainer = row.addStack();
qrContainer.backgroundColor = Color.white();
qrContainer.setPadding(
  QR_PADDING,
  QR_PADDING,
  QR_PADDING,
  QR_PADDING
);
qrContainer.cornerRadius = 8;

const qr = qrContainer.addImage(qrImage);
qr.imageSize = new Size(QR_SIZE, QR_SIZE);

row.addSpacer();
widget.addSpacer();

// Present widget
Script.setWidget(widget);
Script.complete();
