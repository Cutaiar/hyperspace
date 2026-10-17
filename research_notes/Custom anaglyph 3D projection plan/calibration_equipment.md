# Optical characterization and calibration equipment and methods for anaglyph projection (filter transmission, projector SPD, stereo crosstalk) — low-budget SF team

Research date: 2026-10-17. Price-verification legend: **[V]** = price read directly from the vendor's live page on 2026-10-17. **[S]** = price came from a search-engine snippet or reseller page whose capture date is unknown. Treat [S] prices as indicative and re-check before ordering. Shipping-to-SF estimates are given only where a source supports them; otherwise they are marked unknown.

## Q1. Spectrometers and spectral sensors: options, costs, and what each can establish (filter transmission curves, projector SPD)

### Takeaway
For the job here (projector RGB primary SPDs plus the transmission curve of each filter), the cheapest instrument that gives real spectra is the Hamamatsu C12880MA breakout from GroupGets: $69.99 [V], sensor included per a DigiKey forum post, 340–850 nm, about 15 nm resolution. That resolution is coarse but adequate for broad dye or gel filters. It is not adequate for narrow laser lines or sharp interference-filter edges. The Sekonic C-800 is the strongest turnkey "measure the projector SPD" tool and can be rented from Lensrentals for $76/3 days or $109/7 days [V]. Buying one costs about $1,899 [S]. Thorlabs, Ocean and UPRtek instruments cost $1.8k–4.3k and are justified only for Path B.

### Cited findings

**Procurement table (spectral instruments)**

| Product | Manufacturer / SKU | Link | Price | Shipping / availability | Verified |
|---|---|---|---|---|---|
| C12880MA & C16767MA Breakout Board v2 | GroupGets, SKU BO-HAMA-V2 (part BO-HAMA-C12880-V2) | https://groupgets.com/products/c12880ma-c16767ma-breakout-board | $69.99 [V] | Ships from Reno, NV. Free US shipping only over $500. Page showed both "Sold out" and "Only 257 left in stock" | 2026-10-17 |
| Sekonic C-800 SpectroMaster (rent) | Sekonic, via Lensrentals | https://www.lensrentals.com/rent/sekonic-c-800-spectromaster-color-meter | $76 (3 d), $82 (4 d), $109 (7 d), $147 (10 d), $191 (14 d) base. Damage waiver brings 7 d to $131 [V] | "Available Thursday". FedEx 2Day, FedEx Overnight, UPS Ground and UPS Next Day options. Cost depends on zip code. Return label included | 2026-10-17 |
| Sekonic C-800-U (buy) | Sekonic MFR SKU 401-800 | https://www.glazerscamera.com/products/sekonic-c-800-u-spectromaster | $1,899 [S]. Hot Rod Cameras pages show $1,899 to $2,737, the higher figures possibly from its Canadian storefront | Glazer's listing shows sold out | snippet |
| UPRtek MK350S Premium | UPRtek | https://gamma-sci.com/product/mk350s-premium-spectrometer/ | $4,125 (Gamma Sci). B&H about $4,332 as a special order with 7–14 business days lead time [S] | special order | snippet |
| Ocean ST-VIS-25 microspectrometer | Ocean Insight, Edmund stock #90-016 | https://www.edmundoptics.com/p/ocean-st-vis-microspectrometer/56524/ | $1,820 (Edmund). Knight Optical lists $2,088 [S] | unknown | snippet |
| Flame-S-VIS-NIR | Ocean Insight | https://www.oceaninsight.com/blog/flame-series-general-purpose-spectrometers/ | No USD price published (Ocean marks it "$$"). An old EU demo-sale sheet listed €3,284, discounted to €1,642 [S] | quote | snippet |
| Thorlabs CCS100 / CCS200 | Thorlabs | https://www.thorlabs.com (product page did not render) | **No price found**. The catalog PDF sits in an "Obsolete/2025" folder | possibly discontinued | not verified |
| Adafruit AS7341 10-ch breakout | Adafruit #4698 | https://www.adafruit.com/product/4698 | $18.95 for qty 1–9 [S] | unknown | snippet |
| SparkFun AS7343 Qwiic 14-ch | SparkFun SEN-23220 | https://www.sparkfun.com/sparkfun-spectral-sensor-as7343-qwiic.html | $21.95, in stock [S] | unknown | snippet |
| Adafruit TCS34725 RGB sensor | Adafruit #1334 | https://www.adafruit.com/products/1334 | $7.95, **discontinued** [S] | — | snippet |

**Hamamatsu C12880MA (GroupGets breakout)**
- Response range is 340–850 nm. Spectral resolution is 15 nm max (FWHM). The detector is a 288-pixel CMOS linear image sensor with a 50 × 500 µm slit and NA 0.22. — [Hamamatsu datasheet](https://www.hamamatsu.com/content/dam/hamamatsu-photonics/sites/documents/99_SALES_LIBRARY/ssd/c12880ma_c16767ma_kacc1226e.pdf). GoPhotonics gives 12–15 nm. — [GoPhotonics](https://www.gophotonics.com/products/spectrometers/hamamatsu/44-1154-c12880ma)
- The GroupGets v2 board is Arduino-compatible, breaks out all pins and has an onboard white LED. GroupGets provides no software or coding support. — [GroupGets](https://groupgets.com/products/c12880ma-c16767ma-breakout-board)
- A DigiKey forum reply dated 2025-08-14 says the BO-HAMA-C12880-V2-SENSOR "does include a C12880MA sensor with the board". The GroupGets page itself does not say whether a sensor is included. — [DigiKey forum](https://forum.digikey.com/t/groupgets-llc-spectrometer-eval-board-bo-hama-c12880-v2-sensor-included-components/58812)
- The bare sensor sells at RS Components for about £243.90 (UK) or €292.68 (IE), excluding VAT. — [RS UK](https://uk.rs-online.com/web/p/sensor-development-tools/0482444). That makes $69.99 for board plus sensor surprisingly low; confirm the sensor is included before relying on it (see Gaps).

**Sekonic C-800 SpectroMaster**
- Spectral range is 380–780 nm with a 1 nm output pitch. Illuminance accuracy is ±5% ±1 digit (1–3,000 lx). Repeatability is 1% + 1 digit (30–200,000 lx) and 5% + 1 digit at 1–30 lx. Range is 1–200,000 lx. Spectral mismatch f1′ is within 9% and cosine response f2 within 6%. — [Scan UK listing](https://www.scan.co.uk/products/sekonic-c-800-spectromaster-spectrometer-cmos-sensor-1600-to-40000k-1-to-200000lx-cri-ssi-tlci-tlmf), [Vistek](https://www.vistek.ca/store/427724/sekonic-c800-spectrometer-colour-meter)
- Lensrentals lists the C-800 for rent. **The C-7000 was not listed.** — [Lensrentals search](https://www.lensrentals.com/search?q=sekonic)
- I found no BorrowLenses listing for the C-800. — [search result set](https://www.lensrentals.com/search?q=sekonic) (absence noted only)
- European rental houses also rent it, e.g. Adcom Italy at €60 + VAT. — [Adcom](https://www.adcom.it/en/lighting/accessories/light-meter/sekonic-rent-spectrometer-c-800/p_n_20_467_0_60004)

**Ocean / Thorlabs**
- Ocean ST-VIS covers 350–810 nm, with 2.2 nm resolution (25 µm slit) and 3.8 ms – 6 s integration. — [Edmund Optics](https://www.edmundoptics.com/p/ocean-st-vis-microspectrometer/56524/)
- Flame-S-VIS-NIR covers 350–1000 nm with about 1.33 nm typical resolution. — [Ocean Insight blog](https://www.oceaninsight.com/blog/flame-series-general-purpose-spectrometers/)
- Thorlabs CCS100 covers 350–700 nm with <0.5 nm resolution. Its catalog page is filed under "Obsolete/2025". — [Thorlabs catalog PDF](https://www.thorlabs.com/catalogpages/Obsolete/2025/CCS200.pdf), [GoPhotonics](https://www.gophotonics.com/products/spectrometers/thorlabs-inc/44-46-ccs100)
- Used Ocean Optics USB2000+ units (about 340–1024 nm) appear on eBay at around $449. — [eBay listing](https://www.ebay.de/itm/316675600831)

**Generic "Torch Bearer Y21B7W10"-style USB spectrometers**
- No search result matched that model number. Generic 340–1050 nm USB units from Shenzhen sellers appear at about €89 plus €12 shipping. A 2023 APS abstract describes classroom USB spectrometers at $120 each covering 380–850 nm. — [eBay](https://www.ebay.de/itm/236259364969), [APS abstract](https://archive.aps.org/4cs/2023/e03/3)

**DIY / Public Lab**
- Public Lab's wiki says resolution "is mainly limited by the resolution of the camera (and its focus!)" and claims better than about 3 nm/pixel. Ordinary cameras record roughly 400–700 nm. — [Public Lab wiki](https://publiclab.org/wiki/revisions/papercraft-spectrometer)
- A 2010s article quoted the kit at $35. I found no current official price and no measured accuracy figure. — [earthendeavours](https://earthendeavours.org/making-science-simple)

**Multi-channel spectral sensors**
- The AS7341 has 8 overlapping visible bands plus clear, NIR and flicker channels. Adafruit's guide gives **no accuracy spec or calibration procedure**. — [Adafruit Learn](https://learn.adafruit.com/adafruit-as7341-10-channel-light-color-sensor-breakout.md)
- The AS7343 (SparkFun) has 14 channels on a 5×5 photodiode array covering about 380–1000 nm. — [SparkFun](https://www.sparkfun.com/sparkfun-spectral-sensor-as7343-qwiic.html)

**What a published anaglyph study actually used (benchmark for Path B)**
- Woods & Rourke (2004) measured projector output with a Zeiss MMS spectroradiometer (190–735 nm) using a fiber-bundle irradiance input. The projectors displayed full-field white, black, red, green and blue slides. Filter transmission was measured on a Hitachi 150-20 double-beam spectrophotometer (350–750 nm), which compares the beam through the filter with a reference beam. — [Woods & Rourke 2004, SPIE 5291](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)

### Inferences
- **Transmission curves need three measurements with the same spectrometer and geometry:** a dark reading D(λ), a reference reading of a stable broadband source with no filter R(λ), and a sample reading through the filter S(λ). Then T(λ) = (S − D)/(R − D). This is the single-beam version of the Hitachi double-beam measurement above.
- The source must be broadband and stable. A halogen or incandescent lamp works best. A white phosphor LED is weak below about 430 nm and has a dip near 480 nm, so transmission is noisy there.
- Because only a ratio is taken, absolute calibration of the spectrometer is not needed for T(λ). For an absolute projector SPD, the spectrometer's own response must be corrected, for example against a halogen lamp of known color temperature. Many anaglyph decisions only need *relative* SPD of each primary, which the cheap sensors can provide with a relative-response correction.
- The C12880MA's 15 nm FWHM blurs RGB laser lines (natively about 1–3 nm wide) into about 15 nm humps, so it cannot report true line width. It still locates peak wavelengths approximately, which is enough to check that a laser line falls in a filter's pass or stop band.
- Steep filter edges (dichroic or interference filters) will look smeared, which overstates leakage at the edge. Dye or gel anaglyph filters have gentler slopes and are less affected.
- AS7341/AS7343/TCS34725 give 3–14 band integrals, not spectra. They cannot produce a transmission *curve*. They can produce per-band transmission ratios or, more usefully, a relative "how much of primary X gets through filter Y" figure when the sensor sits behind the filter. That is a crosstalk-type measurement (see Q3), not a spectral one.
- The C-800 measures only illuminance-geometry SPD from 380–780 nm (cosine diffuser). Point it at the projector lens from the screen position, or place it at the screen plane facing the projector, with full-field R, G, B, W and K patterns. Put a filter in front of the diffuser and the instrument gives the through-filter SPD and illuminance directly. Note that its 1 nm figure is *output pitch*, not optical resolution.

### Gaps
- **Thorlabs CCS100/CCS200:** no current price, and the product page would not render. Status may be obsolete.
- **Ocean Flame and ST:** no official USD price. Ocean sells by quote.
- **Torch Bearer Y21B7W10:** no listing or specs found.
- **Asensetek Lighting Passport:** not researched (out of call budget). No price.
- **Theremino spectrometer:** not researched.
- **GroupGets $69.99:** whether the price includes the C12880MA is unconfirmed on GroupGets' own page. The DigiKey forum says yes, but RS sells the sensor alone for about £244. Email GroupGets before ordering.
- **Shipping time Reno→SF:** not stated by GroupGets.
- **Lensrentals shipping:** rates and transit times to SF were not shown without a zip code.
- **AS7341 band centers/FWHM:** not captured from a primary datasheet.

## Q2. Spectrophotometers, colorimeters and simple meters for transmission and through-filter luminance; rental/borrow options in SF

### Takeaway
Spectral display devices (Calibrite ColorChecker Studio, formerly the X-Rite i1Studio, and the i1Pro family) can save emissive spectra with ArgyllCMS `spotread -s`/`-O file.sp`, and ArgyllCMS also has a `-t` transparency mode. Colorimeters (Calibrite Display Plus HL, about $259–339 [S]; SpyderX) cannot output spectra. A published attempt to use a Spyder colorimeter through stereo filters failed at ghost-level luminances. The cheapest *reliable* through-filter photometric tool is therefore the rented C-800, or a spectrometer used photometrically. A lux meter (Dr.Meter LX1330B, about $38–60 [S]) is acceptable only for bright signal levels.

### Cited findings
**Procurement (photometric / colorimetric)**

| Product | Manufacturer / SKU | Link | Price | Availability | Verified |
|---|---|---|---|---|---|
| Calibrite Display Plus HL | Calibrite CCDIS3PLHL | https://www.pictureline.com/collections/peripherals/products/calibrite-display-plus-hl | $259 sale, $339 regular (Pictureline). Markertek $339, ships in 5–14 days [S] | varies | snippet |
| Calibrite ColorChecker Studio (spectro, formerly i1Studio) | Calibrite CCSTUDIO | https://www.fullcompass.com/prod/660943-calibrite-ccstudio-colorchecker-studio | $569 (Full Compass). Glazer's $499 but sold out [S] | varies | snippet |
| Dr.Meter LX1330B lux meter | Dr.Meter | https://www.ebay.com/p/2238960293 | about $38–60 depending on seller [S] | varies | snippet |
| i1Pro 3 | Calibrite/X-Rite | — | **No price found** | — | — |

- ArgyllCMS `spotread`:
  - `-s` prints spectral values "if the instrument supports this".
  - `-O fname.sp` saves a spectrum to file.
  - `-e` is emissive mode for displays and illuminants. Projectors are measured in normal emissive mode on instruments without a telephoto mode.
  - `-t` is transparency mode, aimed at backlit media.
  - The Eye-One Display and similar colorimeters "cannot read spectral information".
  — [ArgyllCMS spotread docs](https://www.argyllcms.com/doc/spotread.html)
- The ColorChecker Studio is a spectrophotometer marketed for profiling "monitors, projectors, scanners, mobile devices and printers". It is a rebrand of the i1Studio, which in turn derives from the ColorMunki Photo. — [Digital Camera World review](https://www.digitalcameraworld.com/reviews/Calibrite-ColorChecker-Studio)
- The Display Plus HL has a diffuser that doubles as a stand for projector profiling, plus a 1/4" tripod thread. — [Markertek](https://www.markertek.com/product/cbr-ccdis3plhl/calibrite-ccdis3plhl-display-plus-hl-hdr-monitor-projector-calibration-tool-powered-usb-10000-nits)
- **Colorimeter failure behind stereo filters:** Weissman & Woods (2011) mounted circular polarizers in front of a Spyder and restricted its acceptance angle with a 278 mm × 44 mm tube to 9°. Luminance "dropped by a factor of 39", and "the Spyder results were not reliable, especially at the lower intensity levels representative of the ghost image". Direct crosstalk measurements were "not successful with our current equipment". — [Weissman & Woods 2011, SPIE 7863](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-15-weissman-woods-measuring_crosstalk.pdf)
- **A spot photometer succeeded:** Baker, Kaestner & Gouws (2016) used a Minolta LS-110 spot photometer pointed through one goggle aperture in a dark room. They measured 32 luminance levels and used regression-slope ratios because point ratios at low luminance are inflated by scatter and black level. — [Baker et al. 2016, J. Vision 16(15):14](https://pmc.ncbi.nlm.nih.gov/articles/PMC5172160/)
- LX1330B: range 0.1–200,000 lx. Sellers disagree on accuracy, quoting ±(3–4% rdg + 10 digits) up to 20,000 lx and ±2% repeatability. No official spec sheet was found. — [eBay](https://www.ebay.com/p/2238960293), [Besomi](https://besomi.com/jo_en/lx-1330b-200k-lux.html)

**University and community access in SF**
- No published external-user recharge rates were found for UC Berkeley, SF State or UCSF UV-Vis. As comparators, other universities charge:
  - Colorado School of Mines: $64/hr external academic, $100/hr commercial
  - Missouri S&T Cary 50: $12/hr standard, $30/hr commercial
  - Harvard: $2.20/hr external
  — [Mines](https://sif.mines.edu/user-fees/), [Missouri S&T](https://sil.mst.edu/files/2023/01/Instrument-use-fees.pdf), [Harvard](https://mcbcore.seas.harvard.edu/?p=517)
- **Noisebridge:**
  - Location: 272 Capp St, Mission (Meetup pages; older pages say 2169 Mission St).
  - Cost: free to use, donation-funded.
  - Equipment: reported tools include laser cutter, wood/metal shop, 3D printers and darkroom.
  - Hours: an undated UCSF Library report says 11am–11pm daily and advises emailing ahead.
  - **No spectrometer is documented.**
  — [Meetup](https://meetup.com/noisebridge), [UCSF Library](https://www.library.ucsf.edu/?p=4007)

### Inferences
- **"Through-the-filter luminance" method (the most direct crosstalk matrix):**
  1. Display full-field R, G, B, W and K patterns.
  2. Place the meter at the viewer position with the left filter in front of it, then repeat with the right filter. That gives 5 × 2 readings.
  3. Normalize each eye's luminance by its own channel's white-minus-black reading. For example, red-filter crosstalk = (L_red-eye(cyan image) − L_red-eye(black)) / (L_red-eye(red image) − L_red-eye(black)). This is the Weissman–Woods observed-crosstalk formula (Q3) with "white" replaced by the eye's own primary set.
  4. Repeat for G and B separately to get a 3×2 leakage matrix for designing compensation.
  This mirrors Woods & Rourke's spectral model computed directly in photometric units. Use the same physical filter material as the glasses, at the same angle.
- **Colorimeters behind narrowband filters:** a colorimeter's XYZ estimate assumes a display-like spectrum. Behind a narrowband filter its Y reading can carry large spectral-mismatch errors, and it may lack sensitivity at ghost levels (per Weissman & Woods). Use colorimeters for *signal* levels and white point, not ghost levels.
- **Spectral alternative:** a spectral device (C-800, ColorChecker Studio/i1Pro via ArgyllCMS, or the C12880MA) avoids spectral mismatch by integrating SPD × V(λ) in software, but still needs enough signal at ghost level.
- The cosine-diffuser illuminance geometry (C-800, lux meter) at the screen plane measures *projector* output, not screen reflectance toward the eye. That is fine for ratio-based crosstalk if the screen is spectrally neutral. Metallic or silver screens may need a spot (luminance) measurement from the audience position.
- **Lux meters at ghost level:** a $40 lux meter has 0.1 lx resolution. A dim projector through a dense filter in a dark room may deliver only a few lux, so ghost readings of about 0.05–0.5 lx sit at or below the meter's resolution. Mitigations:
  - Move the meter closer to the lens.
  - Use a small, bright image.
  - Average many readings.
- **Phone lux-meter apps** use the phone's ambient-light sensor with unknown spectral weighting and auto-ranging. I found no source quantifying their error, so treat them only as relative, same-phone comparisons.
- **Path B low-cost route:** rent the C-800 for 3–7 days ($76–109). Measure the filter set on a halogen lamp (T(λ) ratio) and the projector primaries in the same week. That avoids buying a $2k–4k spectrometer.

### Gaps
- **i1Pro 2/3:** current price not found, and whether it can be rented in the US was not researched.
- **ColorChecker Studio/i1Pro transmission:** whether `spotread -t` works on these instruments without a light table is not confirmed. The ArgyllCMS page discusses `-t` mainly with SpectroScan-type devices.
- **SpyderX and Display Plus HL** low-light floors behind filters: not documented by the manufacturers.
- **BH1750 breakout:** price not captured.
- **Bay Area core facilities:** Berkeley, SF State, UCSF and Stanford UV-Vis external access and rates were not found. Email facility managers directly.
- **Exploratorium:** equipment loans not researched.
- **ShareGrid and BorrowLenses:** C-800 availability not confirmed.

## Q3. Crosstalk definitions, formulas, measurement procedure, and standards

### Takeaway
Use the black-level-corrected "observed" (system) crosstalk of Weissman & Woods (2011). It needs three full-field stereo pairs per eye (white/black, black/white, black/black):

OCT_RL = (O_GL − O_BL)/(O_WL − O_BL)

Good stereo displays are around 1%. Anaglyph systems measured in the literature range from about 2% (well-matched narrowband) to above 40% (broadband filters). For anaglyphs, Woods & Rourke (2004) give the spectral prediction method: display SPD × filter T(λ) × V(λ), integrated. ITU-R BT.2021 (stereo subjective methods) is **withdrawn** (2020). The relevant standards for glasses-based optical measurement are SID/ICDM IDMS (3D section) and IEC 62629-12-1.

### Cited findings
- **Intrinsic quantities:** transmittance τ_L = D_L/S_L, and intrinsic crosstalk χ_RL = C_L/S_R (leaked intensity in one eye ÷ source intensity of the other view). These are hard to measure because the source can't be measured before stereo processing and the black level is nonzero. — [Weissman & Woods 2011](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-15-weissman-woods-measuring_crosstalk.pdf)
- **Observed readings:** O_WL = τ_L(W) + χ_RL(B) + A_L, O_GL = τ_L(B) + χ_RL(W) + A_L, O_BL = τ_L(B) + χ_RL(B) + A_L, where A is ambient.
- **Derivation:** O_WL − O_BL = τ_L(W − B) and O_GL − O_BL = χ_RL(W − B), so χ_RL = τ_L(O_GL − O_BL)/(O_WL − O_BL).
- **Observed crosstalk** (Huang's "System Crosstalk"): **OCT_RL = χ_RL/τ_L = (O_GL − O_BL)/(O_WL − O_BL)**. The right eye is symmetric.
- **Extinction ratio:** ER = 1/OCT. "Good values for OCT and ER in a stereo display are 1% and 100:1". — [Weissman & Woods 2011](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-15-weissman-woods-measuring_crosstalk.pdf)
- **Ghosting vs crosstalk:** ghosting (the perception) depends on content. At zero disparity the leakage overlaps the direct image and is not noticed, but it "is still there and can be measured". — same source
- **Terminology problems:** Woods (2011) found that few publications define crosstalk and ghosting mathematically, and that the available definitions are sometimes contradictory. Woods (2012), "Crosstalk in stereoscopic displays: a review" (J. Electronic Imaging 21(4):040902), formalizes the definitions and covers anaglyph, measurement, simulation and cancellation. — [Curtin eSpace 2012 review](https://espace.curtin.edu.au/handle/20.500.11937/31347), [Woods 2011](https://espace.curtin.edu.au/handle/20.500.11937/12475)
- **No-instrument visual chart:** Weissman's "Stereoscopic Crosstalk Test Chart" works without instruments. The viewer wears the glasses, looks with one eye, and finds the gray patch (scaled in % intensity) that matches the ghost of a white row from the other view. Brightness and contrast are first set to avoid white and black crush. The display should be gamma-2.2 calibrated "after stereo processing". Example readings were 0.3–3.3% on passive and active 3D TVs. — [Weissman & Woods 2011](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-15-weissman-woods-measuring_crosstalk.pdf)
- **Anaglyph spectral method** (Woods & Rourke 2004):
  - Cyan output = G + B spectra.
  - Intended signal = red SPD × red filter; ghost = cyan SPD × red filter, and similarly for the cyan eye.
  - Each product is weighted by the CIE photopic V(λ), and the areas are integrated.
  - % crosstalk = ghost area ÷ intended area × 100. The worked example gives 0.389/1.411 = 2.75%. (The paper's figure lists the cyan-curve area as 0.0389 units, so the formula as printed carries an apparent decimal slip; 0.0389 ÷ 1.411 ≈ 2.76%.)
  - Results: best red/cyan combinations reached a 1.89% red-filter / 0.32% cyan-filter crosstalk on an Epson 3LCD projector, but up to 15.4% (red filter) on a DLP projector.
  - "Even a perfect filter… will have crosstalk if the display's green channel spectral output… overlaps the filter's red domain".
  — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- **Measured anaglyph crosstalk (photometer):** Baker et al. (2016) measured luminance crosstalk from <0.1% to >7% across systems. Anaglyph filters were >2%, and **broadband anaglyph filters exceeded 40%**. Narrowband anaglyph filters cut monitor luminance by more than 16×. Point ratios at low luminance are unreliable, so they used regression slopes over 32 levels. — [Baker et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5172160/)
- **Other studies:** Woods & Harris (2010) simulated 16 glasses pairs (red/cyan, blue/yellow, green/magenta) against measured SPDs of 13 LCDs, 15 plasmas and 1 CRT. — [SPIE 7524](https://spiedigitallibrary.org/conference-proceedings-of-spie/7524/75240Q/Comparing-levels-of-crosstalk-with-red-cyan-blue-yellow-and/10.1117/12.840835.full). Woods et al. also studied printed anaglyph crosstalk. — [Opt. Eng. 52(4) 043203](https://www.spiedigitallibrary.org/journals/optical-engineering/volume-52/issue-4/043203/Characterizing-and-reducing-crosstalk-in-printed-anaglyph-stereoscopic-3D-images/10.1117/1.OE.52.4.043203.pdf)
- **Standards:**
  - The SID/ICDM IDMS includes a 3D displays section emphasizing stereoscopic displays with passive and active glasses. A free PDF is at icdm-sid.org/downloads/idms1.html. — [CRS course page](https://crsltd.com/news-and-events/technical-short-courses/information-display-measurements-standard)
  - IEC 62629-12-1 covers optical measurement of glasses-type stereoscopic displays: measurement distance, set-up, glasses and input signals.
  - IEC 62629-22-1 covers autostereoscopic displays, including 3D crosstalk.
  — [IEC preview](https://webstore.iec.ch/p-preview/info_iec62629-22-1%7Bed1.0%7Db.pdf), [VDE preview 12-1](https://www.vde-verlag.de/iec-normen/preview-pdf/info_iec62629-12-1{ed1.0}b.pdf)
- **ITU-R BT.2021:** "Subjective methods for the assessment of stereoscopic 3DTV systems". BT.2021-1 (02/2015) was **suppressed on 2020-04-30**. — [ITU](https://www.itu.int/rec/R-REC-BT.2021/en)

### Inferences
- **Recommended Path A procedure:**
  1. Darken the room, set projector settings (Q5) and lock them.
  2. Display full-field pairs: L-white/R-black, L-black/R-white and L-black/R-black. For anaglyph, "white" in the left view means the left eye's primary set, e.g. pure R for red/cyan, and "white" in the right view means G+B.
  3. Measure through each filter. Compute OCT for each eye.
  4. Also measure per-primary (R, G and B separately) to build the leakage matrix for software ghost compensation.
  5. Take 5+ repeats and report mean ± SD. Where possible, fit slopes over several gray levels (Baker method) instead of single-point ratios.
- **Path B procedure:** measure the SPD of each projector primary (C-800 or spectrometer) and T(λ) of each filter (spectrometer + halogen). Compute the Woods–Rourke V(λ)-weighted crosstalk. Cross-validate against the direct through-filter photometric OCT; agreement within about 1 percentage point supports the model.
- The anaglyph's own primary leakage also depends on the content's color mixing (e.g., Dubois or half-color matrices). Crosstalk measured with pure primaries is a hardware property; perceived ghosting with real content differs.

### Gaps
- The full text of the Woods (2012) review and of the IDMS 3D chapter was not retrieved. Exact IDMS section numbering, the procedure, and whether IDMS treats anaglyph specifically are unconfirmed.
- No VESA 3D measurement standard was found.
- No successor to ITU-R BT.2021 was identified.

## Q4. Test patterns (crosstalk, ghost-busting, depth/disparity, stereoacuity screening)

### Takeaway
For crosstalk, use full-field white/black pairs plus the Weissman SCT chart concept (gray patches in % intensity interleaved with the ghost of a white row). Older Weissman and Bloos charts are scaled in gray-level and are numerically wrong unless gamma is accounted for. For depth, random-dot stereograms (Julesz) avoid monocular cues. For viewer screening, a Randot test ($205–273 [S], 400→20 arcsec) is the standard clinical tool.

### Cited findings
- Earlier charts by Weissman ("Stereoscopic Extinction Test Chart v1.0") and Bloos ("Ghost TEST") give numerical results that "are in error because the interpretation is in gray-levels rather than intensity values". The new SCT chart uses percent intensity, with white scale ranges to 10% and black to 1%. — [Weissman & Woods 2011](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-15-weissman-woods-measuring_crosstalk.pdf)
- A simple anaglyph validation pattern: red (255,0,0) and cyan (0,255,255) rectangles sharing an edge, with a filter held over the boundary. The more the complementary half goes black, the lower the crosstalk. Eye-ranking agreed with the model except for differences under 2%. — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- **Random-dot stereograms:**
  - Julesz developed RDS (*Foundations of Cyclopean Perception*, 1971). About 5% of individuals cannot see depth in RDS. — [Wikipedia: Random dot stereogram](https://en.wikipedia.org/wiki/Random_dot_stereogram)
  - Dot size significantly affects stereoacuity results when dots are too small to resolve. — [PMC7313195](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7313195/)
- **Stereo Optical Randot (SO002):**
  - Contents: graded circles from 400 to 20 arcsec, plus 500/250 arcsec gross levels, with viewers included.
  - Price: $258–273 [S]. Precision Vision sells it for $205–218.50 [S].
  - Randot Preschool: $453 [S], 800–40 arcsec.
  — [Stereo Optical](https://www.stereooptical.com/product/randot/), [Precision Vision](https://precision-vision.com/products/randot-stereo-test)

### Inferences
- **Recommended pattern set (generate in code or Blender):**
  1. Full-field W/K per eye, per primary, and a 0–100% gray ramp per eye. These cover OCT and gamma after filtering.
  2. An SCT-style chart: a white bar in one view; in the other view, gray patches at 0.5, 1, 2, 3, 5, 8, 12 and 20% *linear intensity*, converted through the measured gamma.
  3. High-contrast vertical bars or text at disparities of 0, ±5, ±10 and ±20 px, to see ghosting where it is most visible (large disparity, high contrast).
  4. Nonius/vernier lines (one line per eye) to check vertical misalignment and keystone mismatch.
  5. An RDS with known disparity steps for depth verification without monocular cues.
  6. A checkerboard for registration and warp checking.
- **Ghost-cancellation adjustment pattern:** a white bar in one view over a mid-gray background in the other. The viewer adjusts the compensation coefficient until the ghost vanishes (method of adjustment; see Q6).

### Gaps
- Paul Bourke's stereo test-pattern pages and other existing downloadable sets (e.g., the SCT chart file) were not located.
- Blender stereo test scenes were not researched.

## Q5. Viewer variability (stereoblindness, IPD, color vision) and projector-side controls (settings, SPD by light source, camera methods)

### Takeaway
Expect about 5–10% of viewers to lack usable stereopsis. A 2019 evidence synthesis converges on about 7%, and the estimate depends strongly on the test used. Adult IPD averages about 63 mm (SD about 3.8 mm; extremes about 52–78 mm in ANSUR). Lock projector settings: turn BrilliantColor/white segment, dynamic contrast and eco modes off. Phone and RGB cameras can only give relative, same-device, RAW-linear comparisons. They cannot measure spectra or absolute luminance without calibration.

### Cited findings
- **Stereoblindness prevalence:**
  - A best-evidence synthesis of adults under 60 found estimates "converge toward a prevalence of stereoblindness of 7%", possibly higher in older adults. — [SKI summary](https://www.ski.org/?p=15507)
  - 9.7% of 300 surgeons were stereoblind on the Random Dot E test, associated with age. — [Springer](https://www.springermedizin.de/age-is-highly-associated-with-stereo-blindness-among-surgeons-a-/8542764)
  - A 2024 study found that 98% of participants passed a detection task but only 69% a discrimination task. The authors attribute the 2–30% spread of published estimates to task choice. — [iScience 2024](https://doaj.org/article/ac06896eb3d34282a0bd393a92b5e803)
  - The Curtin VR study (2023) found about 5% stereoblind. — [IS&T EI 2023](https://library.imaging.org/ei/articles/35/2/SDA-225)
- **IPD:**
  - ANSUR 1988 data (n=3976) cited with Dodgson's review: mean 63.36 mm, SD 3.832 mm, min 52 mm, max 78 mm. — [USPTO patent citing Dodgson](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10429648)
  - Dodgson, "Variation and extrema of human interpupillary distance", Proc. SPIE 5291:36–46 (2004). The original numbers were not retrieved.
  - ANSUR 2012 (secondary): male 64.0 ± 3.4 mm, female 61.7 ± 3.6 mm. — [everything.explained](https://everything.explained.today/Pupillary_Distance/)
- **Anaglyph color effects:** anaglyphs inherently produce retinal rivalry, which causes "visual fatigue". — [USPTO 8194119](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8194119). **No study of color-vision-deficient (protan/deutan) viewers with anaglyphs was found.**
- **BrilliantColor / white segment (DLP):**
  - TI says BrilliantColor uses up to five colors instead of three. — [TI DLPC7540](https://www.ti.com/document-viewer/lit/html/DLPU082B/GUID-565634CC-4C7B-4FAE-904D-9AEE4004C04A)
  - On a BenQ HT3050 it raised peak white from 25.9 to 32.8 ft-L and shifted CCT. Reviewers disabled it during calibration. — [Sound & Vision](https://www.soundandvision.com/node/115199)
  - The white segment adds about 20% to white output on an Optoma HD72. — [HT HiFi](https://www.hometheaterhifi.com/volume_14_1/optoma-hd72-projector-1-2007-part-1.html)
- **Projector type matters:** Woods & Rourke found red-filter crosstalk of 15.4% (NEC 1-DMD) vs 1.9–2.8% (3LCD) with the best glasses. — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- **Viewing angle:** PROPixx (DLP) crosstalk rose from about 1% at 0° to 7% at 23° and about 20% at 45° (polarization-based). — [Baker et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5172160/)
- **Cameras** (Burggraaff et al. 2019, Opt. Express 27(14):19075, SPECTACLE):
  - Across seven consumer cameras (incl. smartphones), RAW data was highly linear and JPEG was not.
  - Inter-pixel gain variations exceeded 400%, and flat-field correction factors reached 2.79 across the field.
  - RGB spectral responses "differed wildly between camera models". The commentary notes linearity was limited to 8-bit data in some cases.
  — [arXiv 1906.04155](https://arxiv.org/pdf/1906.04155), [Optica spotlight](https://opg.optica.org/spotlight/summary.cfm?id=414726)

### Inferences
- **What phone/RGB cameras CAN establish:**
  - With locked manual exposure, ISO, white balance and focus, RAW (DNG) capture, a tripod and the same pixel region, the *ratio* of ghost to signal through each filter. This is an OCT estimate weighted by the camera's spectral response, not V(λ).
  - Registration, keystone and warp alignment.
  - Spatial uniformity of crosstalk across the screen, after flat-field correction (which matters given the 2.79× factors reported).
  - Before/after comparisons of compensation on the same device.
- **What they CANNOT establish:**
  - Spectra or filter T(λ). Three broad channels cannot resolve where a filter edge falls.
  - Absolute luminance or illuminance without calibration against a meter.
  - Human-weighted (photopic) crosstalk. The camera's R/G/B sensitivities differ from cone fundamentals, especially at long wavelengths where Bayer R cutoffs vary most between models.
  - Accurate ghost levels from JPEG or with auto-exposure, HDR, tone mapping or "scene optimization" active.
  - Ghost levels at ±1% without bracketing. Ghost and signal can be 50–100× apart, so you need multiple exposures with known exposure-time ratios, or exposure-time scaling verified as linear.
- **Laser vs lamp SPD:**
  - RGB-laser projectors have narrow lines. Their crosstalk is set mostly by whether each line falls in the stop band, and edges barely matter. The 15 nm C12880MA still locates them.
  - Lamp/LED/phosphor projectors have broad primaries that overlap filter edges, which is the case where Woods & Rourke found large differences between projectors. Measure, don't assume.
  - Single-chip DLP primaries can include a white or secondary segment (BrilliantColor) that injects broadband light into "pure" primaries. Disable it.
- **Projector settings checklist:**
  - Turn off BrilliantColor/white segment, dynamic contrast/dynamic iris, eco/auto-brightness, auto keystone and ambient-light sensors.
  - Fix the color mode, e.g. a "user" mode with gamma 2.2.
  - Warm up 20–30 min before measuring.
  - Digital keystone and warping resample the image and can soften edges or create mismatched geometry between views. Prefer physical alignment.

### Gaps
- Dodgson's original IPD table and his recommended design range were not retrieved. The figures above come from secondary citations.
- No source was found for the 8% male CVD prevalence or for CVD effects on anaglyphs specifically. The prevalence figure, though widely cited, is not sourced here.
- No source was found quantifying phone lux-app accuracy.
- Warm-up time recommendations are an inference, not sourced.

## Q6. Acceptance criteria and subjective evaluation approaches

### Takeaway
Pair an objective threshold (e.g., OCT per eye ≤ some target, with about 1% as the "good stereo display" benchmark and >2% typical for anaglyph) with simple subjective protocols: paired comparisons (A/B of filter or compensation variants) and method-of-adjustment ghost nulling. ITU-R BT.2021 is withdrawn but remains a useful methodological reference.

### Cited findings
- "Good values for OCT and ER in a stereo display are 1% and 100:1". — [Weissman & Woods 2011](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-15-weissman-woods-measuring_crosstalk.pdf)
- Anaglyph filters measured >2%, and broadband anaglyph filters >40%. — [Baker et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5172160/)
- In a visual ranking of filters, eye judgments matched the model except where the crosstalk difference was <2%. Small differences are hard to rank by eye. — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- ITU-R BT.2021 is withdrawn (suppressed 2020-04-30). A thesis applied its single-stimulus method to study quality versus crosstalk. — [ITU](https://www.itu.int/rec/R-REC-BT.2021/en), [ZČU thesis](https://otik.zcu.cz/bitstream/11025/9208/1/DP_Martin_Sindelar.pdf)

### Inferences
- **Suggested Path A acceptance:**
  1. Measured OCT through each filter, for full-field primaries, below a team-chosen target (e.g., ≤5% red eye and ≤3% cyan eye as a prototype goal). These targets are a judgment call, not a standard.
  2. 2AFC paired preference with 8–12 viewers screened by Randot (exclude or flag stereoblind viewers, report separately).
  3. Method of adjustment: each viewer nulls the ghost of a high-contrast bar at large disparity by adjusting the compensation coefficient. The mean setting gives an empirical crosstalk estimate to compare against the instrument-derived value.
- **Path B adds:**
  - Spectral validation (model vs measured within about 1 pp).
  - Multiple seat positions and angles (crosstalk can vary with angle).
  - Repeat-session reliability.
- Because differences under about 2% are hard to rank by eye, use instruments, not viewers, to choose between near-equal filter candidates.

### Gaps
- ITU-R BT.500's current method details (DSCQS, ACR scales, viewer counts) were not retrieved.
- Formal published acceptance thresholds specific to anaglyph projection were not found.
