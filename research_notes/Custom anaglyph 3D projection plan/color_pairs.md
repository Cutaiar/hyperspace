# Anaglyph color-pair options beyond red/cyan for a projected installation

Scope: which two-color filter pairs work for anaglyph 3D, with evidence on spectra, crosstalk, color, brightness balance, materials, premade glasses and rendering matrices. Research date: 2026-10-17.

Main primary sources used (full text read):
- Woods & Rourke 2004, "Ghosting in Anaglyphic Stereoscopic Images", SPIE 5291. Red/cyan only. Measured 27 pairs of glasses and 7 digital projectors. [PDF](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Woods & Harris 2010, "Comparing levels of crosstalk with red/cyan, blue/yellow, and green/magenta anaglyph 3D glasses", SPIE Stereoscopic Displays & Applications XXI. [PDF](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf), [SPIE record](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/7524/75240Q/Comparing-levels-of-crosstalk-with-red-cyan-blue-yellow-and/10.1117/12.840835.short). The author PDF header says "vol. 7253" but SPIE and Curtin list it as vol. 7524, paper 75240Q (DOI 10.1117/12.840835). 7524 is most likely correct and the header is a typo.
- ColorCode 3-D patent [US6687003B1](https://patents.google.com/patent/US6687003B1/en)
- FFmpeg `stereo3d` [docs](https://ffmpeg.org/ffmpeg-filters.html#stereo3d) and [source vf_stereo3d.c](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_stereo3d.c)
- Dubois, "Conversion of a Stereo Pair to Anaglyph with the Least-Squares Projection Method" (March 2009 note), and Dubois ICASSP 2001, via [Dubois anaglyph page](https://www.site.uottawa.ca/~edubois/anaglyph/)

---

## 1. Candidate pairs and their spectral/separation evidence (red/cyan, green/magenta, amber/blue, red/green, red/blue, Anachrome, Inficolor, magenta/cyan)

### Takeaway
Only three pairs have measured, peer-reviewed crosstalk comparisons: red/cyan, green/magenta and blue/yellow (amber/blue). In Woods & Harris 2010, red/cyan had the lowest average crosstalk, green/magenta was close behind, and blue/yellow was clearly worst except on plasma. The other pairs have only claims or descriptions behind them: red/blue and red/green (monochrome only), Anachrome (a red/cyan variant), Inficolor (green vs red+blue with proprietary processing) and magenta/cyan (experimental).

### Cited Findings

**Woods & Harris 2010: method and sample (measured spectra, simulated crosstalk)**
- Simulated 16 pairs of glasses (6 red/cyan, 6 blue/yellow, 4 green/magenta) against measured spectra of 13 LCDs, 15 plasma panels and 1 CRT. Glasses spectra came from a Perkin Elmer Lambda 35 spectrophotometer. More than 70 pairs were measured in total. Crosstalk (%) = leakage / signal x 100, weighted by CIE photopic response. The "overall crosstalk factor" is left-eye % plus right-eye %, so it is not a percentage. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- No projectors were in the 2010 set. Its displays were LCD monitors, PDPs and a CRT. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- Named glasses tested include:
  - ColorCode 3-D cardboard glasses
  - "Monsters vs. Aliens – NBC – Intel – ColorCode 3D (Superbowl 2009)"
  - "Journey to the Centre of the Earth (3D DVD) – TrioScopics, LP"
  - "My Bloody Valentine (3D DVD) – LionsGate – Trioscopics LP"
  - "Coraline (3D DVD) – LAIKA – Trioscopics LP"
  - "Ghosts of the Abyss (3D DVD)"
  - "Edmund Optics Dichroic Filters": red U52-528 / cyan U52-537, blue U52-531 / yellow U52-543, green U52-534 / magenta U52-540
  - — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- The authors note the blue/yellow and green/magenta glasses were "the only samples of those color-type of anaglyph glasses that were able to be obtained by the authors for testing". The red/cyan samples were picked "because of their good performance", so the sample favours red/cyan. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)

**Woods & Harris 2010: numerical results (quoted)**

Average overall crosstalk factor, using the best 4 gel-filter glasses of each type (best 3 for green/magenta):

| Display | Red/cyan | Green/magenta | Blue/yellow |
|---|---|---|---|
| LCD | 14.7 (min 7.6) | 20.1 (min 11.7) | 33.9 (min 24.7) |
| Plasma | 15.7 (min 8.4) | 18.4 (min 11.2) | 16.9 (min 12.5) |
| CRT | 27.1 (min 22.8) | 27.1 (min 24.9) | 36.7 (min 32.2) |
| All displays | 15.7 | 19.5 | 25.2 |

— [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)

- Per-filter averages across all displays: the better four cyan gel filters averaged 2.2% and the better four yellow gel filters 5.1%. Red averaged 13.5% and blue 20.1%. The red and blue lenses are the weak eye in each system. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- Dichroic filters (simulated from published curves, no physical samples):
  - Red/cyan dichroic (3DG70) was the best of all: average 13.6, global minimum 7.1.
  - Green/magenta dichroic averaged 17.6, better than green/magenta gel (19.5).
  - Blue/yellow dichroic was much worse at 73.9, because the blue dichroic "transition wavelength is around 505nm which is probably too high. If the transition wavelength was closer to 480 or 490nm, the result would probably be very different."
  - Inkjet-printed filters were worst: average 93.8, max 125.4. Authors: "don't use inkjet printed anaglyph filters."
  - — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- Brightness balance: "our calculations indicate that the green/magenta glasses generally have better brightness balance and blue/yellow glasses have the greatest brightness imbalance although that work isn't reported here due to space limitations." This is stated, but no numbers are published. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- Perception caveat for blue/yellow: for glasses 3DG51 on a CRT, the blue filter had "almost eight times" the crosstalk of the yellow lens. However, "the perception of the brighter yellow lens seems to dominate … and less crosstalk is perceived than a simple addition … would suggest." Adding the two eyes' crosstalk may therefore overstate perceived ghosting for blue/yellow. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- Validation was limited to 1–2 observers. The authors found "visually comparing anaglyph glasses of different colors was … very difficult" and possibly highly subjective. They also warn that "LED backlit LCD TVs are likely to have different spectral characteristics and therefore very different crosstalk results." — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- The spectral plots for each filter colour (Figs 3–8: red, cyan, green, magenta, blue, yellow) are in the paper. The numerical transmission values are not tabulated in the text, so per-wavelength numbers are only available by digitising the figures. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)

**Red/cyan: projector-specific measured data (Woods & Rourke 2004)**
- Measured 27 red/cyan glasses (Hitachi 150-20 spectrophotometer, 350–750 nm) and 7 digital projectors (two 1-chip DLP, five 3LCD). — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Best overall crosstalk factor by display:
  - Diamond CRT: 22.5
  - Acer laptop LCD: 41.2
  - NEC 1-chip DLP: 20.1
  - InFocus 1-chip DLP: 8.9
  - Epson 3LCD: 3.92
  - NEC VT540 3LCD: 4.66 and 3.93
  - Boxlight 3LCD: 3.08 and 4.59
  - Best single cyan filter on 3LCD projectors: 0.32–0.48% (Boxlight3 1.44%). Best red filter: 1.63–2.75%.
  - — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Conclusion: "3 chip LCD projectors were found to offer considerably lower anaglyphic ghosting than the other types of displays tested … (CRT displays, LCD screens, and DMD projectors)". Single-chip DMD projectors were "worse than 3-chip LCD projectors but better than CRT displays." — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Variation between glasses: "The red filter of glasses 3DG19 remains at close to 0% transmission from 400 to 570nm … whereas the red filter of glasses 3DG25 has significant leakage in this region." The 3DG25 cyan filter "has a maximum transmission of ~80% in its required pass region, but its transmission also increases rapidly in the >650 nm region." — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Design rule: low crosstalk needs "a low crossover point as well as ≈0% transmission outside their desired wavelength region … Ideally, the wavelength of the glasses' crossover point will be close to that of the display device's crossover point." Also, "even a perfect filter … will have crosstalk if the display's green channel spectral output … overlaps the filter's red domain." — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)

**Red/blue and red/green (historical)**
- "If a non-complimentary combination is used, (e.g. red/blue or red/green) pseudo-colour anaglyphs are impossible, as a large portion of the visible spectrum is missing. The overall image may also be darker." — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Red/blue can cut crosstalk on CRTs. The crosstalk factor "decreases to 5.89±0.09" compared with at least 22.5 for red/cyan, but at the cost of color and brightness. — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)

**Amber/blue (ColorCode 3-D)**
- The patent claims the system gives the viewer "in one eye, an image of nearly full color information, in the other eye, an essentially monochrome image supplying the parallactic differences". — [US6687003B1](https://patents.google.com/patent/US6687003B1/en)
- Patent Table 1 gives the spectral transmittance of example filters "B" and "Y", 400–700 nm in 25 nm steps, "maximal theoretical transmittance scaled to 1". This is an illustrative patent example, not necessarily the shipped product.
  - B: 400 nm 0.20, 425 nm 0.53, 450 nm 0.39, 475 nm 0.08, then 0 from 500 to 700 nm.
  - Y: 0.01, 0.03, 0.04, 0.06, 0.08, 0.09, 0.10 (400–550 nm), then 0.13, 0.13, 0.11, 0.18, 0.10, 0.39 (575–700 nm).
  - The patent figures (FIGS. 1–15) are filter-pair curves "measured with a spectrophotometer" over 400–700 nm.
  - — [US6687003B1](https://patents.google.com/patent/US6687003B1/en)
  - My reading of the extracted text is that the Y values are on the patent's own normalised scale, so they should not be read as absolute lens transmittance.
- Secondary (Wikipedia): "The blue filter is centered on 450 nm and the amber filter lets in light at wavelengths at above 500 nm." — [Wikipedia ColorCode 3-D](https://en.wikipedia.org/wiki/ColorCode_3-D) (pointer only; no primary source given)
- Patent status: Google Patents shows "Expired – Lifetime" with an anticipated expiration of 2019-10-18. Wikipedia says it "expired in 2020". The successor is Ogon AB's "A3D" / "A3D-EDR" (2017), which still uses amber-blue glasses. — [Google Patents](https://patents.google.com/patent/US6687003B1/en); [Wikipedia ColorCode 3-D](https://en.wikipedia.org/wiki/ColorCode_3-D); [Ogon](https://ogon3d.com)
- Deployments: 2009 Super Bowl SoBe/Monsters vs. Aliens ads, Chuck, Channel 4 "3D week" (Nov 2009) and Time Inc. magazines (April 2009). — [Wikipedia ColorCode 3-D](https://en.wikipedia.org/wiki/ColorCode_3-D). One vendor says American Paper Optics made "over 134,000,000" ColorCode glasses for the 2009 Super Bowl. — [3dglassesonline legacy page](https://www.3dglassesonline.com/solutions/legacy/) (vendor claim)

**Green/magenta (TrioScopics)**
- Coraline, My Bloody Valentine and Journey to the Centre of the Earth 3D DVDs shipped TrioScopics green/magenta glasses. The Journey listing in Woods & Harris names TrioScopics; separately, Super Bowl 2009 used ColorCode, not TrioScopics. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- Wikipedia's comparison table gives green/magenta: "better reds, oranges and wider range of blues than red/cyan … Less chromatic aberration, as the red and blue in magenta brightness balance well with green … Strong ghosting effect on contrast images." — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D) (unsourced claim)

**Inficolor 3D (TriOviz)**
- Described as "the left image using the green channel only and the right using the red and blue channels with some added post processing". It used "expensive glasses with complex color filters" and was demonstrated at IBC 2007 and deployed in 2010. — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D)
- Vendor claim: "without any ghosting or discomfort". The PR quoted on [TopTierTactics](https://www.toptiertactics.com/11908/overall-nice-guy-glenn-warrington-heads-up-trioviz-sales/) is marketing. No independent spectra or crosstalk data were found. The game pipeline added colour correction and depth of field for the Inficolor mode. — [Engadget 2010](https://www.engadget.com/2010-03-12-darkworks-shows-off-trioviz-for-games-2d-to-3d-sdk-we-get-a-goo.html)

**Anachrome (red/cyan variant)**
- Uses a dark red left filter and a cyan right filter that deliberately leaks about 1–2% red ("intentional 'leakage' of a minimal (2%) percentage of red light"). It also uses molded lenses with about +0.5 diopter on the red lens to correct red/cyan focus differences. — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D), which cites the patent [US6561646B2 (Silliphant)](https://patents.google.com/patent/US6561646B2)
- The "400% improvement in acuity" figure on Wikipedia is unsourced and should not be used.

**Magenta/cyan (experimental)**
- Proposed scheme: the blue channel is blurred horizontally and sent to both eyes, while red goes to one eye and green to the other. Claimed benefit is better brightness balance. — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D) citing [MCA-RL09 (archived)](https://web.archive.org/web/20100821221626/http://www.divideconcept.net/papers/MCA-RL09.pdf). Not peer-reviewed. No crosstalk measurements found.

### Inferences
- For a projector, the measured ranking (red/cyan < green/magenta < blue/yellow) comes from LCD, plasma and CRT spectra, not projector spectra. Projector primaries, especially 3LCD and RGB laser, are generally more separated, so absolute crosstalk should be lower. The ranking needs re-testing on the actual projector.
- The weak lens sets each system's quality: red in red/cyan, blue in blue/yellow, and either lens in green/magenta, where the data do not single one out. Sourcing a better weak-eye filter (e.g. a dichroic) is likely the biggest win.
- Dichroic green/magenta (simulated 17.6) beat dichroic red/cyan (13.6) only as a gel system. Gel versus dichroic matters as much as which pair you pick.

### Gaps
- No published crosstalk numbers for green/magenta or amber/blue on any projector. The 2010 study had no projectors.
- Woods & Harris give no per-wavelength transmission numbers for the green/magenta or blue/yellow filters, only plots. They also give no numbers for brightness imbalance.
- No independent spectra for Inficolor or TrioScopics glasses, beyond the TrioScopics DVD glasses measured, and only as plots.
- I did not find Dubois's own measured filter-spectra plots for magenta-green or amber-blue glasses on his page. The fetched index page has no spectra; the matrices are hosted on Flickr.

---

## 2. Brightness balance and luminance: why green/magenta balances and amber/blue is dim

### Takeaway
Green carries most of the luminance. A green-only eye and a red+blue eye therefore get roughly balanced luminance, while red/cyan favours the cyan eye. Amber/blue puts nearly all luminance in the amber eye and leaves the blue eye very dim. Woods & Harris's calculations agree qualitatively (green/magenta best balance, blue/yellow worst), but they did not publish the numbers.

### Cited Findings
- FFmpeg's grey anaglyph modes use luma weights 19595/38470/7471 out of 65536 for R/G/B. That is 0.299 / 0.587 / 0.114, the Rec.601 coefficients. — [FFmpeg vf_stereo3d.c](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_stereo3d.c)
- Green/magenta "generally have better brightness balance and blue/yellow glasses have the greatest brightness imbalance". — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- A brightness imbalance between the eyes "can also result in the Pulfrich effect whereby horizontal motion can be interpreted as binocular depth – which is generally undesirable." Also: "Lower light levels also make the effect of even small ghosting levels proportionally greater". — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- ColorCode: "better color rendering, but dark image, requires dark room or very bright image. Left filter darkened to equalize the brightness received by both eyes as the sensitivity to dark blue is poor. Older people may have problems perceiving the blue." A −0.7 diopter lens over the blue eye is an option. — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D) (citing an archived hobbyist page); ColorCode "does reduce the overall brightness of the viewed image" — [Wikipedia ColorCode 3-D](https://en.wikipedia.org/wiki/ColorCode_3-D)
- An informal user review says the ColorCode "blue lens is very heavy, darkens the image substantially and tints everything quite blue". — [dvinfo forum](https://dvinfo.net/forum/3d-stereoscopic-production-delivery/128661-colorcode-3-d.html) (anecdotal). A blog estimates the amber lens peak transmission at "only about 20% or so". — [brainwagon](https://brainwagon.org/blog/2009-02-04-superbowl-ads-chuck-in-3d) (informal, not measured)
- The patent's example blue filter peaks at 0.53 (at 425 nm) and is 0 from 500 nm upward. — [US6687003B1](https://patents.google.com/patent/US6687003B1/en)

### Inferences
- Rec.601 weights give an approximate luminance split:
  - Red/cyan: 0.299 vs 0.701.
  - Green/magenta: 0.587 vs 0.413.
  - Amber(R+G)/blue: about 0.886 vs 0.114, before the lenses' own losses.
  - This is a signal-level approximation only. The real split depends on the projector primaries and the filter curves.
- For an installation with ambient light or a large screen, amber/blue's dim blue eye is the main risk. Ghosting becomes more visible in the dim eye, and moving content may show Pulfrich artefacts.

### Gaps
- No published measurement of interocular luminance ratio for any commercial anaglyph glasses.

---

## 3. RGB laser vs lamp/LED, and DLP color wheel interactions

### Takeaway
Measured data exist only for lamp projectors (2004). There, 3LCD gave the lowest crosstalk and 1-chip DLP was worse. No study was found that measures anaglyph glasses on RGB-laser projectors. Narrowband primaries should help, but only if the filter crossover wavelengths fall between them.

### Cited Findings
- 3LCD projectors gave red/cyan crosstalk factors of about 3.1–4.7, against 8.9–20.1 for 1-chip DMD projectors. — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- "Using narrow bandwidths for the source or the lenses can minimize crosstalk" (vision-research context). — [JOV, crosstalk in stereoscopic display systems](https://jov.arvojournals.org/article.aspx?articleid=2594018)
- Laser 3D patents note that "Laser light sources have very narrow band emission characteristics" and suit passive spectral-separation glasses. They describe anaglyph as best "for black and white original images, and is not well suited for color images". — [US10359639B2](https://patents.google.com/patent/US10359639)
- Display colour balance alone changed crosstalk between two units of the same projector model (Boxlight2 vs Boxlight3). — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Interference filters drift towards the blue when viewed off-axis ("blue shift"), which matters for dichroic anaglyph lenses at wide viewing angles. — patent literature summarised in search results, e.g. [US9325976](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9325976)

### Inferences (not directly sourced; verify on the actual hardware)
- RGB-laser projectors (e.g. red about 635–640 nm, green about 520–532 nm, blue about 445–465 nm) have large spectral gaps between primaries.
  - Red/cyan and green/magenta gel filters with crossovers around 580–600 nm, and around 490 and 580 nm, should separate them well.
  - Blue/yellow needs the blue-lens cutoff below the green laser line. Woods & Harris's 480–490 nm recommendation fits this.
- "Laser-phosphor" projectors (blue laser plus yellow phosphor) produce broadband green and red, like lamps. They should not be assumed to behave like RGB laser.
- 1-chip DLP colour wheels with white or secondary (yellow, cyan) segments add mixed-spectrum light. This plausibly explains the worse DMD results. Disabling BrilliantColor/white-segment boost, where possible, is worth testing.
- Speckle and metamerism with laser light do not change the separation logic.

### Gaps
- No measured anaglyph crosstalk data for RGB-laser, LED or laser-phosphor projectors were found.
- No data on DLP white-segment effects specifically.

---

## 4. Retinal rivalry, color perception and comfort across pairs

### Takeaway
No controlled user study comparing red/cyan, green/magenta and amber/blue for comfort was found. Evidence is limited to patents, design claims and the observation that brightness imbalance and ghosting degrade fusion.

### Cited Findings
- Patent claim: "conventional anaglyphs generally exhibit retinal rivalry which may cause user discomfort". Similar phenomena "occur in analogous blue/yellow and green/magenta true-color anaglyphs", and true-color anaglyphs "generally [have] too much retinal rivalry for comfortable viewing". — [US8194119, Display of generalized anaglyphs without retinal rivalry](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8194119) (patent assertion, not user data)
- "Half-colour" anaglyphs (one channel greyscale) reduce rivalry; FFmpeg and Wikipedia both list half-colour modes. — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D)
- Dubois's least-squares method "retained much of the color and reduced ghosting and retinal rivalry". — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D), pointing to [Dubois 2001](https://www.researchgate.net/publication/3908713)
- Woods & Harris found visual comparison across colour types "very difficult" and possibly highly subjective, with only 1–2 observers. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- A 2013 paper on anaglyphs with minimal ghosting and rivalry reports improved viewer acceptance in subjective tests. Not read in full. — [DLSU repository](https://animorepository.dlsu.edu.ph/faculty_research/1645)
- Chromatic focus: red/cyan lenses differ by about 250 nm in passband, causing focus differences. Anachrome uses about +0.5 D on red, and ColorCode optionally −0.7 D on blue. — [Wikipedia Anaglyph 3D](https://en.wikipedia.org/wiki/Anaglyph_3D)

### Inferences
- Green/magenta puts the mid-spectrum (best-focused) band in one eye and the spectrum extremes in the other. This may reduce chromatic focus conflict compared with red/cyan, consistent with the "less chromatic aberration" claim, but it is unverified.
- For a public installation, plan a short pilot with several viewers (including older viewers for amber/blue), recording comfort and ghosting ratings per pair.

### Gaps
- No peer-reviewed comparative comfort or rivalry study across colour pairs was found.

---

## 5. Pale pink vs saturated magenta, and why visible color contrast is not spectral separation

### Takeaway
What matters is how much the filter transmits in the other eye's display bands, not how different the lenses look. A pale pink lens looks clearly "not green", yet it must be passing substantial green to look pale. A saturated magenta needs a deep stop-band in green. No pink gel spectra were retrieved, so this rests on the measured-filter principles in Woods's work.

### Cited Findings
- Filters should have "≈0% transmission outside their desired wavelength region". Filters that leak in the stop-band give "a dim, ghosted image … if the display is still active in those wavelengths". — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Inkjet-printed filters look red and cyan but have "very poor performance in the stop band" and the worst crosstalk (average 93.8). Visually plausible colour is not enough. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)
- Some 3DG25 red filters measured near 0% only between 500 and 550 nm, with "significant leakage" elsewhere in the green/blue region, despite looking red. — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Lighting-gel data point: Rosco E-Colour+/LEE 113 Magenta is listed at 10.9% total transmission. — [StageDepot listing](https://stagedepot.co.uk/node/1937) (retailer data; total luminous transmission, not spectral)
- Hobbyist report: LEE 106 Primary Red and LEE 116 Medium Blue-Green work for red/cyan ("116 … a littlebit green"). — [vvvv forum](https://forum.vvvv.org/t/what-lee-filters-for-building-custom-3d-glasses-anaglyph-effect/7793) (anecdotal)

### Inferences
- A pink lens is light because it transmits broadly, including green, so it leaks the green-eye image. Ghosting would be roughly proportional to its green-band transmission times the display's green output, weighted by photopic sensitivity, which peaks at 555 nm.
- Saturated magenta is dark (about 10.9% total for LEE 113) precisely because it blocks green.
- When choosing gels, check the manufacturer's published spectral curve (LEE and Rosco publish curves per filter) for transmission in the stop band, especially 500–580 nm for a magenta lens. Do not judge by eye.

### Gaps
- Pink gel spectral data and green-band transmission percentages were not retrieved. Download LEE or Rosco spectral curves for candidate pinks and magentas (e.g. LEE 113, 126, 128, 002, 035) before purchase.

---

## 6. Rendering matrices, materials and premade glasses

### Takeaway
Rendering matrices exist for all three main pairs: Dubois least-squares for red/cyan, green/magenta and amber/blue, and FFmpeg `stereo3d` modes for all three plus red/blue and red/green. Premade glasses are plentiful for red/cyan, available for green/magenta, and uncertain for amber/blue in 2026.

### Cited Findings
- FFmpeg `stereo3d` output modes: arbg (red/blue grey), argg (red/green grey), arcg/arch/arcc/arcd (red/cyan grey, half, colour, Dubois), agmg/agmh/agmc/agmd (green/magenta), aybg/aybh/aybc/aybd (yellow/blue). Default is `arcd`. Example: `stereo3d=sbsl:aybd`. — [FFmpeg docs](https://ffmpeg.org/ffmpeg-filters.html#stereo3d)
- FFmpeg Dubois coefficients (x/65536, rows R, G, B out; columns L.R, L.G, L.B, R.R, R.G, R.B) — [vf_stereo3d.c](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_stereo3d.c):
  - RC_DUBOIS: {29884, 32768, 11534, -2818, -5767, -131}, {-2621, -2490, -1049, 24773, 48103, -1180}, {-983, -1376, -328, -4719, -7406, 80347}
  - GM_DUBOIS: {-4063, -10354, -2556, 34669, 46203, 1573}, {18612, 43778, 9372, -1049, -983, -4260}, {-983, -1769, 1376, 590, 4915, 61407}
  - YB_DUBOIS: {69599, -13435, 19595, -1048, -8061, -1114}, {-1704, 59507, 4456, 393, 4063, -1114}, {-2490, -11338, 1442, 6160, 12124, 59703}
- Dubois's 2009 red/cyan matrices are for "red/cyan glasses and CRT/plasma display", applied in linear RGB after removing sRGB gamma, with each term clipped to [0, 1] before summing:
  - Left: [0.437 0.449 0.164; −0.062 −0.062 −0.024; −0.048 −0.050 −0.017]
  - Right: [−0.011 −0.032 −0.007; 0.377 0.761 0.009; −0.026 −0.093 1.234]
  - — Dubois, "Conversion of a Stereo Pair to Anaglyph with the Least-Squares Projection Method", March 2009, via [Dubois anaglyph page](https://www.site.uottawa.ca/~edubois/anaglyph/)
  - FFmpeg's RC_DUBOIS (0.456, 0.500, 0.176, …) differs from these 2009 values. It matches the earlier Dubois set, so it is a different and older matrix.
- Dubois's page says the method applies "equally well" to red-cyan, green-magenta and amber-blue. It links green-magenta and amber-blue matrices for StereoPhoto Maker hosted on Flickr, and notes that matrices are optimised "for a given display and given glasses". — [Dubois anaglyph page](https://www.site.uottawa.ca/~edubois/anaglyph/)
- Dubois's 2001 method uses "the spectral absorption curves of the glasses, the spectral density functions of the display primaries and the colorimetric properties of the human observer" (Sony Trinitron phosphors). With measured projector and filter spectra, custom matrices can be computed. — Dubois ICASSP 2001, via [Dubois anaglyph page](https://www.site.uottawa.ca/~edubois/anaglyph/)
- Rendering itself can cause crosstalk: "the quality of the anaglyph image generation matrix" is a crosstalk contributor. — [Woods 2010, Understanding Crosstalk](http://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-23_understanding_crosstalk_woods.pdf). Lossy compression (JPEG/MPEG) mixes channels and adds crosstalk. — [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- Premade glasses:
  - Rainbow Symphony sells magenta/green "ProView" plastic glasses (listed from $18 per pack, about $9 each) and magenta/green paper glasses, plus red/cyan and red/blue paper. — [Rainbow Symphony magenta/green](https://www.rainbowsymphony.com/products/magenta-green-proview-3d-glasses); [Rainbow Symphony red/cyan paper](https://www.rainbowsymphony.com/products/red-cyan-paper-3d-glasses)
  - TrioScopics-branded green/magenta paper glasses come from American Paper Optics. — vendor page summarised in search, [Rainbow Symphony types](https://www.rainbowsymphony.com/3d-glasses) (page returned HTTP 429 on direct fetch)
  - No current amber/blue retail listing was confirmed. Ogon AB offers ColorCode/A3D paper glasses. — [Ogon](https://ogon3d.com) via search summary
- Prototyping materials: Edmund Optics dichroic filter pairs were used in Woods & Harris simulations: red U52-528 / cyan U52-537, blue U52-531 / yellow U52-543, green U52-534 / magenta U52-540. Current availability of these part numbers was not checked. — [Woods & Harris 2010](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2010-11.pdf)

### Inferences
- FFmpeg appears to apply its matrices directly to gamma-encoded 8-bit values. Dubois's 2009 note specifies linear-light processing. For a custom pipeline, linearise first and use matrices fitted to the projector's measured spectra.
- **Comparison table summary (for the report writer):**

| Pair | Crosstalk evidence | Colour | Brightness balance | Glasses (2026) | Matrices | Prototyping | Confidence |
|---|---|---|---|---|---|---|---|
| Red/cyan | Lowest measured: 15.7 average across displays; 3–5 on 3LCD projectors | Poor reds | Cyan eye brighter | Abundant; Anachrome variants | Dubois, FFmpeg `arcd` | Easy (gels, dichroics) | High |
| Green/magenta | 19.5 average; dichroic simulated 17.6 | Better reds than red/cyan (claimed) | Best balance (claimed, numbers unpublished) | Available (Rainbow Symphony, TrioScopics) | Dubois, FFmpeg `agmd` | Gels/dichroics; needs deep green stop-band in magenta | Medium |
| Amber/blue (ColorCode) | 25.2 average, worst on LCD; blue lens weak | Near-full colour in amber eye | Worst imbalance; dim blue eye | Uncertain (Ogon) | Dubois/FFmpeg `aybd`; ColorCode proprietary | Blue cutoff must be about 480–490 nm | Medium–low |
| Red/blue, red/green | Low crosstalk on CRT (5.89, red/blue) | Monochrome only | Dark | Available | FFmpeg `arbg`/`argg` | Easy | Medium |
| Inficolor | None independent | Claimed natural | Unknown | Discontinued, eBay only | Proprietary | Not viable | Low |
| Magenta/cyan | None | Claimed better | Claimed better | None | Experimental | Custom | Very low |

- **Recommended test order:**
  1. **Red/cyan (Dubois matrix, good dichroic or high-grade gel glasses).** Lowest measured crosstalk, the most data (including projector data), abundant glasses and established matrices. Sets the baseline.
  2. **Green/magenta (FFmpeg `agmd` or Dubois GM matrix, TrioScopics/Rainbow Symphony glasses).** Measured crosstalk close to red/cyan on LCD and plasma, better claimed brightness balance and colour, and premade glasses still sold. It is the best candidate to beat red/cyan on comfort.
  3. **Amber/blue (ColorCode-style, FFmpeg `aybd`).** Best colour for the amber eye but the worst measured crosstalk and imbalance. Needs a bright projector and a dark room, and the blue cutoff should be about 480–490 nm. Test it only if colour fidelity is a priority.

### Gaps
- No current (2026) verification of Edmund Optics part numbers, ColorCode/A3D glasses retail, or TrioScopics production status.
- No published Dubois matrices fitted to RGB-laser projector spectra. These would have to be computed from measurements.
