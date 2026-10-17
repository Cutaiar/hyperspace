# Anaglyph rendering algorithms, optical theory and stereo geometry for the Hyperspace custom-colour anaglyph projection

Scope: algorithms and maths an engineering agent needs to build an anaglyph compositor for Hyperspace, plus what the local repo actually renders with. Researched 2026-10-17. Matrix values below were copied only from primary sources I opened: Dubois PDFs, Dubois's own SoftwarePhotoMaker screenshots on Flickr, and ffmpeg/three.js/Blender source files. Anything I could not open is listed under Gaps. "Established" means it comes from a paper or source code. "Recommendation" means it is my engineering judgement.

---

## Q1. Terminology: channel-mask, true/gray/color/half-color/optimized, Dubois, Sanders & McAllister, McAllister/Zhou/Sullivan (LAB), Zhang & McAllister, Woods crosstalk work

### Takeaway
Every classical anaglyph is a fixed linear map `A = M_L·L + M_R·R`, where L and R are RGB triples and M_L and M_R are 3x3 matrices. The variants differ only in the matrices: channel-mask "color", luminance-based "gray"/"true", "half-color" and "optimized". Dubois (2001) computes the matrices by spectral least squares instead of by hand. The McAllister group's methods (2003, 2006, 2010) drop the fixed matrix and solve a per-pixel optimisation in a perceptual space such as CIELab, which costs more compute. Woods's work defines and measures ghosting (crosstalk), the main failure mode.

### Cited Findings
- **Wimmer's taxonomy (3dtv.at, "Anaglyph Methods Comparison").** Formulas verified from the page's formula images. Notation: L = (r1,g1,b1), R = (r2,g2,b2), output (ra,ga,ba). [Wimmer, 3dtv.at](https://3dtv.at/Knowhow/AnaglyphComparison_en.aspx)
  - **True:** ra = 0.299 r1 + 0.587 g1 + 0.114 b1; ga = 0; ba = 0.299 r2 + 0.587 g2 + 0.114 b2. The page says "dark image, no color reproduction, little ghosting".
  - **Gray:** ra = Lum(L); ga = Lum(R); ba = Lum(R). The page says "no color reproduction, more ghosting than true anaglyphs".
  - **Color:** ra = r1; ga = g2; ba = b2. This is the pure channel mask. The page says "partial color reproduction, retinal rivalry", and attributes the rivalry to brightness differences of coloured objects.
  - **Half color:** ra = Lum(L); ga = g2; ba = b2. The page says "partial color, less retinal rivalry than color anaglyphs".
  - **Optimized:** ra = 0.7 g1 + 0.3 b1; ga = g2; ba = b2. The page says "partial color reproduction, but not of red shades, almost no retinal rivalry". The author adds that a gamma of 1.5 is applied to the final red channel, and that Stereoscopic Player uses a further-improved variant.
- **Dietz's definitions.** Dietz describes the same families: monochromatic, Color (left red plus right green/blue, "the most common scheme", "retinal rivalry can be severe"), Half-Color, and Optimized/"leaky" color, in which channels are "polluted" with values leaked from other channels of the same view. He names Anachrome, InfiniColor 3D and ColorCode 3D as commercial "leaky" schemes. He defines retinal rivalry as large colour/brightness differences between the two views of a region, so that the region "oscillat[es] between the colors in the two views". [Dietz, "Reprocessing Anaglyph Images", SPIE EI 2012](https://aggregate.org/DIT/SPIEEI2012/spieei2012paper.pdf)
- **Dubois 2001.** The method uses "the spectral absorption curves of the glasses, the spectral density functions of the display primaries and the colorimetric properties of the human observer". It projects the 6-D ideal stereo percept onto the 3-D subspace of percepts an anaglyph can produce, and does this in XYZ. [Dubois ICASSP 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf); [IEEE Xplore 941256](http://ieeexplore.ieee.org/xpls/abs_all.jsp?arnumber=941256). Dubois says the method is "equally well applicable to red-cyan, green-magenta and yellow (or amber)-blue glasses" and is "often called Dubois Anaglyph". [Dubois anaglyph page](https://www.site.uottawa.ca/~edubois/anaglyph/)
- **Sanders & McAllister 2003.** "Producing anaglyphs from synthetic images", Proc. SPIE 5006, Stereoscopic Displays and Virtual Reality Systems X, doi:10.1117/12.474130. I confirmed only the bibliographic record. [SPIE record](https://biomedicaloptics.spiedigitallibrary.org/conference-proceedings-of-spie/5006/0000/Producing-anaglyphs-from-synthetic-images/10.1117/12.474130.full)
- **McAllister, Zhou & Sullivan 2010.** "Methods for computing color anaglyphs" (SPIE, Feb 2010). Abstract, seen via an aggregator: the method needs "the RGB spectral distributions of the display device and the transmission functions of the filters in the viewing glasses". It "requires the solution of a nonlinear least-squares program for each pixel" and is "based on minimizing color distances in the CIEL*a*b* uniform color space". [worldwidescience aggregator](https://worldwidescience.org/topicpages/s/space+images+anaglyph.html). Li, Ma & Ngan (2013) cite it as matching the Lab values of the stereo pair and of the perceived anaglyph. [Li/Ma/Ngan SP:IC 2013](https://webarchive.lib.cuhk.edu.hk/20221211022207mp_/http:/www.ee.cuhk.edu.hk/~knngan/2013/SP-IC_v28_n6_p597-607.pdf)
- **Zhang & McAllister 2006.** "A Uniform Metric for Anaglyph Calculation", SPIE, Feb 2006, doi:10.1117/12.642898. Bibliographic record only. [Amanote record](https://research.amanote.com/publication/f56_3XMBKQvf0Bhik5L6/a-uniform-metric-for-anaglyph-calculation). A related NCSU work (author not confirmed) describes a method based on "uniform approximation in CIE color space" that solves a linear program per pixel and reports 72–89% computation-time reductions. [NCSU repository](https://repository.lib.ncsu.edu/items/8862bbff-ca28-4ebc-a7ab-469e00a3042e)
- **Woods & Rourke 2004.** "Ghosting in anaglyphic stereoscopic images", SPIE 5291 (Stereoscopic Displays and Virtual Reality Systems XI), pp. 354–365. They measured the spectral output of displays and the transmission of anaglyph glasses, then predicted crosstalk by integrating display SPD × filter transmission × CIE photopic V(λ). [Curtin PDF](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf); [TIB record](https://www.tib.eu/de/suchen/id/BLCP%3ACN052471850/Ghosting-in-anaglyphic-stereoscopic-images-5291/)
- **Woods 2012 review.** "Crosstalk in stereoscopic displays: a review", J. Electronic Imaging 21(4) 040902, doi:10.1117/1.JEI.21.4.040902. It covers crosstalk mechanisms per display technology, reduction, cancellation, measurement and simulation. [Curtin eSpace](https://espace.curtin.edu.au/handle/20.500.11937/31347)
- **Crosstalk definitions (Woods 2011, companion paper).**
  - Basic: `Crosstalk(%) = leakage / signal × 100`.
  - Black-level-corrected: `Crosstalk(%) = (leakage − black level)/(signal − black level) × 100`.
  - "System crosstalk" (= β2/α1) is distinguished from "viewer crosstalk" (= Bβ2/Aα1), which also depends on image content.
  - Woods notes that the terms crosstalk, ghosting and leakage are used inconsistently in the literature.
  - [Woods 2011, "How are crosstalk and ghosting defined…"](http://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-14-woods-crosstalk_and_ghosting.pdf)

### Inferences
- For the compositor, every method in Wimmer's table and Dubois's method is one shader with two `mat3` uniforms (or one 3x6 matrix). The algorithm choice is a data choice, not a code-path choice. Only the LAB/LP methods need per-pixel iterative solves; precomputing a 3-D LUT over (L, R) is impractical because the input space is 6-D.
- "Color" anaglyph is exactly the channel mask. "True", "gray" and "half-color" are the same mask with the masked eye's input replaced by luminance.

### Gaps
- I could not read the full text of Sanders & McAllister 2003, Zhang & McAllister 2006 or McAllister et al. 2010; only bibliographic records and abstracts. Their exact formulations (which Lab variant, which white point, the solver) are unverified.
- The 2010 paper's author list (Ya Zhou, Sophia Sullivan) comes from aggregator metadata. Verify it on SPIE.

---

## Q2. Dubois's method: exact inputs, the 6x3 least-squares maths, linear vs gamma convention, and how to recompute for custom filters + a specific projector

### Takeaway
Dubois's method needs three spectral inputs: the SPD d_j(λ) of each display primary, the transmission f_l(λ) and f_r(λ) of each filter, and the CIE XYZ colour-matching functions. It also needs one design choice, the weighting matrix W. It operates on **linear-light** RGB. The inputs are gamma-decoded first and the output is gamma-encoded last, which Dubois states explicitly both in the 2001 paper and in the 2009 note (which uses the sRGB EOTF). The result is a fixed 3x6 matrix P, so per-pixel cost is a single matrix multiply plus clipping.

### Cited Findings
- **Inputs and convention, from the paper.** The input stereo pair V′ is "gamma-corrected RGB … that can be directly displayed on a standard CRT". Linear values are `V = g(V′)`, where g is the display gamma. The display emits `Q(λ,x) = Σ_j V_j(x) d_j(λ)`. Perceived tristimulus values use CIE x̄, ȳ, z̄ over about 370–730 nm. [Dubois 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf)
- **The formulation.** Integrals are over λ. [Dubois 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf)
  - `C[k,j] = ∫ p_k(λ) d_j(λ) dλ` is the 3x3 display RGB→XYZ matrix.
  - The ideal 6-vector percept is `Ṽ = C₂ V`, where `C₂ = blockdiag(C, C)` is 6x6 and `V = [V_l; V_r]`.
  - Seen through the filters, the anaglyph a produces `A_l[k,j] = ∫ p_k d_j f_l dλ` and `A_r[k,j] = ∫ p_k d_j f_r dλ`. Stacking gives the 6x3 matrix `R = [A_l; A_r]`, and the perceived 6-vector is `Ũ = R·V_a`.
  - With the inner product `⟨v1|v2⟩ = v1ᵀ W v2` (W is 6x6 positive-definite), the least-squares solution is `V̂_a = (RᵀWR)⁻¹ RᵀW C₂ V`.
  - Normalisation: project uniform white `[1,1,1,1,1,1]ᵀ` to get `V̂_aw`, then set `N = diag(1/V̂_awj)`.
  - The final operator is `V̂_an = N (RᵀWR)⁻¹ RᵀW C₂ V = P·V`, where P is a fixed 3x6 matrix. "The final step is clipping to the range [0,1] and application of gamma correction."
- **Weighting.** W = I gives Euclidean distance in XYZ×XYZ. A diagonal W that weights Y more heavily "favor[s] reproduction of the correct luminance at the expense of greater color errors". A non-diagonal W corresponds to distances in another primary set. Dubois says no good perceptual error metric was known and that finding one is further work. [Dubois 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf)
- **Paper's example data.** The paper uses Sony Trinitron CRT phosphor SPDs (numbers from Charles Poynton), giving `C = [[0.4641, 0.3055, 0.1808], [0.2597, 0.6592, 0.08115], [0.0357, 0.1421, 0.9109]]`. The C values are also confirmed in the presentation. The filters are Roscolux #25 orange-red (left) and #69 brilliant blue (right). [Dubois 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf); [Dubois ICASSP presentation](https://www.site.uottawa.ca/~edubois/anaglyph/anaglyph_010508.pdf). The paper's Al/Ar matrices for these filters, as extracted from the PDF text layer (row ordering reconstructed, so verify visually before relying on them), are `A_l ≈ [[0.3185,0.0769,0.0109],[0.1501,0.0767,0.00565],[0.0007,0.0020,0.0156]]` and `A_r ≈ [[0.0174,0.0484,0.1402],[0.0184,0.1807,0.04585],[0.0286,0.0991,0.7662]]`. [Dubois 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf)
- **Display and glasses assumed in 2001.** The 2001 web page says the method "assumes that the resulting anaglyph images are displayed on a CRT". The sample images were "optimized for use with the cardboard-frame red/blue glasses (No. 7001)" from Reel 3-D Enterprises and "do not look very good with the more common red-cyan glasses". [Dubois ICASSP01 web page](https://www.site.uottawa.ca/~edubois/icassp01/)
- **2009 procedure (Dubois, "Conversion of a Stereo Pair to Anaglyph with the Least-Squares Projection Method", March 2009).** Input is "assumed to be sRGB". [Dubois 2009 PDF](https://www.site.uottawa.ca/~edubois/anaglyph/LeastSquaresHowToPhotoshop.pdf)
  1. Linearise with the sRGB EOTF: S = S′/12.92 if S′ ≤ 0.04045, else ((S′+0.055)/1.055)^2.4.
  2. Apply the matrices. "The first and second terms should be clipped to [0,1] before adding." That is, clip M_L·L and M_R·R separately, then sum.
  3. Re-encode with the sRGB OETF: 12.92 S if S ≤ 0.0031308, else 1.055 S^(1/2.4) − 0.055.
- **Related work Dubois lists.**
  - Tran's 2005 thesis: new rendering methods for CRTs and inkjet. [Tran thesis](http://www.eecs.uottawa.ca/~edubois/theses/Tran_thesis.pdf)
  - Thor Olson, "Optimizing anaglyph colors", CIC 2009, pp. 42–48. [IS&T](http://imaging.org/IST/store/epub.cfm?abstrid=43659)
  - Konrad & Halle, IEEE SPM 2007. [Konrad & Halle PDF](http://iss.bu.edu/jkonrad/Publications/jpapers/Konr07spm.pdf)
  - All via [Dubois anaglyph page](https://www.site.uottawa.ca/~edubois/anaglyph/)
- **How common implementations handle gamma.**
  - **ffmpeg `stereo3d`:** applies its integer matrices directly to 8-bit stored (gamma-encoded) values, `sum = Σ coeff·left + coeff·right; av_clip_uint8(sum >> 16)`, with no linearisation and a single clip after summing. [ffmpeg vf_stereo3d.c](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_stereo3d.c)
  - **three.js `AnaglyphEffect` (WebGL):** renders each eye into a `WebGLRenderTarget`, applies `clamp(colorMatrixLeft*L + colorMatrixRight*R, 0, 1)`, then runs `#include <colorspace_fragment>`. [three.js AnaglyphEffect.js](https://github.com/mrdoob/three.js/blob/dev/examples/jsm/effects/AnaglyphEffect.js). When rendering to a render target, three.js sets the program's output colour space to `ColorManagement.workingColorSpace`; only the canvas (null target) gets `renderer.outputColorSpace`. [three.js WebGLPrograms.js L217](https://github.com/mrdoob/three.js/blob/dev/src/renderers/webgl/WebGLPrograms.js)
  - **Blender:** copies channels directly with no matrix. [Blender stereoimbuf.cc](https://github.com/blender/blender/blob/main/source/blender/imbuf/intern/stereoimbuf.cc)

### Inferences
- **three.js colour space (inference from source).** The eye images are stored in the linear working space (Linear-sRGB by default), so three.js applies the Dubois matrices to **linear** values and converts to sRGB at the end. That matches Dubois's 2009 procedure, except that three.js clips once after summing rather than clipping each term. ffmpeg applies the same matrices to **gamma-encoded** values, which is not what Dubois prescribes. Treat ffmpeg's output as an approximation.
- **Recipe to recompute P for Hyperspace's custom filters and projector (engineering recommendation; follows Dubois's formulation directly).**
  1. Measure each projector primary's SPD d_j(λ) with a spectroradiometer at the actual screen position, using the actual colour mode. Drive one channel at 255 with the others at 0, and subtract the black-frame SPD. 380–780 nm at 1–5 nm steps is a typical grid.
  2. Measure f_l(λ) and f_r(λ) for the actual gel or glasses with a spectrophotometer, on the same grid.
  3. Use the CIE 1931 2° x̄ȳz̄ functions on the same grid.
  4. Integrate to get C, A_l and A_r, then form R (6x3).
  5. Choose W. Start with I, then try a diagonal that up-weights Y, per Dubois.
  6. Compute `P = N (RᵀWR)⁻¹ RᵀW C₂`.
  7. Verify that P applied to all-ones gives about 1 per channel. Every published Dubois matrix pair checked below satisfies this: row sums of M_L+M_R are ≈ 1.00.
  8. Implement as: linearise → P → clip each eye term (Dubois 2009) → encode with the projector's actual transfer function, which may not be exactly sRGB.
- **Additivity check.** Dubois assumes an additive, channel-independent display: Q = Σ V_j d_j. A single-chip DLP with a white segment or BrilliantColor processing may violate this (see Q6). Before trusting P, compare the measured SPD of white against the sum of the R, G and B SPDs. If they differ much, set the projector to a mode that disables the white boost, or fit the model to measured patches instead.
- **Normalisation is optional.** N only rescales so that white maps to white. A deliberately dimmer right channel can be compensated by changing N or by per-eye gains (see Q4).

### Gaps
- No public code I found computes Dubois matrices from measured spectra. A search turned up only hard-coded matrices. [search: Nukepedia DuboisAnaglyph gizmo](https://www.nukepedia.com/gizmos/stereo/duboisanaglyph); [Citra commit](https://git.openpunk.com/OpenPunk/citra/commit/96c375229b4d7433639d12c033b6722a95cd8f2e). The engineering agent will need to write the ~30-line numpy routine above.
- Dubois does not publish the W matrices used for his later LCD matrices.
- Dubois's own pages do not say whether the 2010 LCD matrices (GM/YB) assume linear or sRGB inputs. The 2009 note implies linear.

---

## Q3. Published Dubois matrices (red-cyan, green-magenta, amber-blue): exact values, versions and assumptions

### Takeaway
There are at least two red-cyan versions:
- **"Classic" red-cyan:** the version in ffmpeg, three.js and the SPM example dialog. I could not find it printed in the ICASSP paper itself.
- **Revised March 2009 red-cyan:** labelled "for red/cyan glasses and CRT/plasma display".

The green-magenta (TrioScopics3D) and amber-blue (ColorCode) matrices were published in late 2010 as SPM screenshots "optimized for LCD display". ffmpeg's `agmd` and `aybd` coefficients match them exactly. All are in L/R → output-row form, output = M_L·L + M_R·R.

### Cited Findings
- **Revised red-cyan (Dubois, March 2009, "red/cyan glasses and CRT/plasma display").** Applied to linear sRGB, with each term clipped before summing. [Dubois 2009 PDF](https://www.site.uottawa.ca/~edubois/anaglyph/LeastSquaresHowToPhotoshop.pdf)
  ```
  M_L = [[ 0.437,  0.449,  0.164],      M_R = [[-0.011, -0.032, -0.007],
         [-0.062, -0.062, -0.024],             [ 0.377,  0.761,  0.009],
         [-0.048, -0.050, -0.017]]             [-0.026, -0.093,  1.234]]
  ```
- **Green-magenta (Dubois, SPM screenshot uploaded 31 Oct 2010).** Captioned "Least-square algorithm (aka Dubois algorithm) optimized for LCD display and TrioScopics3D glasses". Values transcribed from the screenshot (integers /1000). Left eye = green, right eye = magenta. [Flickr SPM_GM_matrix](https://www.flickr.com/photos/e_dubois/5132528166/)
  ```
  M_L = [[-0.062, -0.158, -0.039],      M_R = [[ 0.529,  0.705,  0.024],
         [ 0.284,  0.668,  0.143],             [-0.016, -0.015, -0.065],
         [-0.015, -0.027,  0.021]]             [ 0.009,  0.075,  0.937]]
  ```
- **Amber-blue (Dubois, SPM screenshot uploaded 4 Dec 2010).** Captioned "Least-square algorithm (aka Dubois algorithm) optimized for LCD display and Colorcode glasses". Values /1000. Left eye = amber, right eye = blue. [Flickr SPM_YB_matrix](https://www.flickr.com/photos/e_dubois/5230654930/)
  ```
  M_L = [[ 1.062, -0.205,  0.299],      M_R = [[-0.016, -0.123, -0.017],
         [-0.026,  0.908,  0.068],             [ 0.006,  0.062, -0.017],
         [-0.038, -0.173,  0.022]]             [ 0.094,  0.185,  0.911]]
  ```
- **"Classic" red-cyan (as shipped by ffmpeg `arcd`, three.js and SPM's built-in example).**
  ```
  M_L = [[ 0.456,  0.500,  0.176],      M_R = [[-0.043, -0.088, -0.002],
         [-0.040, -0.038, -0.016],             [ 0.378,  0.734, -0.018],
         [-0.015, -0.021, -0.005]]             [-0.072, -0.113,  1.226]]
  ```
  - ffmpeg's integers /65536 give exactly these values. ffmpeg's `agmd` and `aybd` integers /65536 reproduce the GM and YB screenshot values above to three decimals. [ffmpeg vf_stereo3d.c `ana_coeff`](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_stereo3d.c)
  - three.js stores the same red-cyan values at higher precision (0.456100, 0.500484, 0.176381 / −0.0400822, −0.0378246, −0.0157589 / −0.0152161, −0.0205971, −0.00546856 for left; −0.0434706, −0.0879388, −0.00155529 / 0.378476, 0.73364, −0.0184503 / −0.0721527, −0.112961, 1.2264 for right). These are written via `Matrix3.fromArray`, which is column-major. The comment cites "citeseerx … doi=10.1.1.7.6968 … #page=4". [three.js AnaglyphEffect.js](https://github.com/mrdoob/three.js/blob/dev/examples/jsm/effects/AnaglyphEffect.js)
  - SPM's dialog lists "Dubois Anglyph" with 456/500/176, −43/−88/−2, and so on, /1000. Visible in both screenshots above.
- **Software that ships Dubois modes.** Dubois lists StereoPhoto Maker, Pdplayer, eyeon Fusion 6, the YouTube 3D player (RC/GM/AB), AnaBuilder, p2gStereoStage and Bino (RC/GM/AB). [Dubois anaglyph page](https://www.site.uottawa.ca/~edubois/anaglyph/)

### Inferences
- **Normalisation check (my arithmetic).** All four matrix pairs satisfy rowsum(M_L)+rowsum(M_R) ≈ 1 for each output channel, which is the white→white property of N. For example, 2009 RC gives [1.000, 0.999, 1.000] and classic RC gives [0.999, 1.000, 1.000]. This is a useful unit test for recomputed matrices.
- **Provenance of the classic red-cyan matrix.** It is *not* in the ICASSP paper or slides text I extracted; I grepped for "456" and "1.226". The paper's own example was red/blue Roscolux gels on a Trinitron CRT. The classic values are therefore probably from Dubois's pre-2009 web page, an attribution I could not verify, and they assume a CRT-era display and generic red-cyan glasses.
- **None of these matrices fit Hyperspace as-is.** All were designed for CRT/plasma (2009 RC) or LCD (2010 GM/YB) primaries with specific commercial glasses, none for a projector or custom gels. They are reasonable starting presets, but a custom filter pair needs recomputed P (Q2 recipe).

### Gaps
- I could not open the citeseerx document 10.1.1.7.6968 that three.js cites, to confirm whether it prints the classic red-cyan matrix.
- No primary Dubois source states the date of the classic red-cyan matrix or the glasses it assumes.
- I did not verify whether YouTube, Bino or SPM linearise before applying the matrices.

---

## Q4. Ghosting reduction (crosstalk cancellation), retinal rivalry, brightness balance, colour preservation, depth control

### Takeaway
Ghosting in anaglyph is set mostly by spectral overlap between the display primaries and the filters. Woods shows that it can be predicted by integrating display SPD × filter transmission × V(λ). Subtractive crosstalk cancellation, which lowers the intended eye's image where the other eye will leak in, is established for time-sequential displays. It is limited by black level: there is nothing to subtract from near-black, so the floor must be raised. Retinal rivalry is reduced by "leaky"/optimized or least-squares matrices, which trade colour fidelity for similarity between the eyes. Depth control is a geometry problem; see Q7.

### Cited Findings
- **Woods's ghosting model.** Woods computes ghosting from display SPD, filter response and the photopic eye response. A worked example gives "% Crosstalk = 0.389 ÷ 1.411 × 100 = 2.75%". A 2% ghost in the blue region "will not be very obvious since the eye is not very sensitive" there. Even a perfect bandpass filter has crosstalk if, say, the green primary's spectrum overlaps the red filter's band. [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- **Crosstalk cancellation (Konrad, Lacotte & Dubois).** They reduce "image intensity in affected areas" so that the leak brings it back to the intended level. The model is "a simple model of intensity leak", fitted to psychovisual data, giving per-channel crosstalk functions φ_R, φ_G, φ_B implemented as LUTs, and it runs in real time. Full elimination causes "unacceptable image degradation (reduced contrast)", so they studied the trade-off. Citation: IEEE Trans. Image Processing 9, pp. 897–908, May 2000. [BU VIP project page](https://vip.bu.edu/projects/3-d/crosstalk-cancellation)
- **Near-black limit.** Subtractive cancellation fails in near-black regions, where there is too little light to subtract, and raising the minimum image level helps. This is a search-snippet summary of a UBC paper. [Doutre et al., EUSIPCO 2011](https://people.ece.ubc.ca/colind/papers/doutre_EUSIPCO2011.pdf)
- **Measuring crosstalk.** Measure with black-white test patterns. Use the black-level-subtracted formula, because non-zero black (LCDs, and also projectors in ambient light) otherwise biases the number. Woods leaves open whether to measure with cancellation turned on or off. [Woods 2011](http://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-14-woods-crosstalk_and_ghosting.pdf)
- **Retinal rivalry and colour.** Rivalry is caused by brightness/colour differences between the two eyes' views. Half-color and Optimized reduce it at the cost of colour, and Optimized cannot reproduce reds. [Wimmer](https://3dtv.at/Knowhow/AnaglyphComparison_en.aspx); [Dietz 2012](https://aggregate.org/DIT/SPIEEI2012/spieei2012paper.pdf)
- **Optimized/"leaky" methods and reprocessing.** Optimized/"leaky" methods introduce "ghost (print-through) edges in color channels that should not have had edges" when the anaglyph is reprocessed. [Dietz 2012](https://aggregate.org/DIT/SPIEEI2012/spieei2012paper.pdf)
- **Brightness balance.** Woods notes that filter peak transmission differs: for example, one cyan filter peaks at about 80% and another at about 60% and "will appear dimmer". Display colour balance also changes ghosting, as two units of the same projector model gave different results. He also mentions possible Pulfrich effects from unequal eye luminance. [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- **Dubois's levers.** Dubois's W matrix trades luminance accuracy against colour error, and his normalisation N enforces white balance through the glasses. [Dubois 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf)

### Inferences (engineering recommendations)
- **Compositor stages, in linear light:**
  1. Optional per-eye gain to balance perceived luminance through each filter. Compute the ratio as ∫ȳ·d_white·f_eye.
  2. The anaglyph matrix.
  3. Optional crosstalk cancellation: `out_eye = (in_eye − k·in_other_eye_leak)`, with a raised black floor so subtraction has headroom.
  4. Clamp.
  5. Encode.

  The leak coefficients k come straight from R: the off-diagonal energy of a channel through the "wrong" filter.
- **Hyperspace content suits anaglyph well.** Its content is mostly bright wireframe lines and points on black (`RED = (1.0, 43/255, 43/255)` points colour in `hyperspace-python/hyperspace/view.py`). Thin bright lines on a dark ground are the worst case for visible ghosting, because maximum ghosting occurs at full-white-in-one-eye / black-in-the-other, as Woods notes. They are the best case for rivalry, because the colours are few. So prioritise filter–primary matching and cancellation over colour fidelity.
- **Saturated red needs special handling.** The scene's saturated red would vanish from one eye under red-cyan, which is a rivalry hazard. Either remap the palette to colours both filters pass, or rely on a Dubois/half-colour matrix that leaks luminance into both eyes.
- **Depth control.** Clamp screen parallax per Q7 rather than relying on colour processing.

### Gaps
- I could not find a published anaglyph-specific (colour-filter) crosstalk-cancellation algorithm with equations. The Konrad et al. work targets shutter (time-sequential) displays. Applying it to anaglyph per channel is my extrapolation.
- I did not read the full text of the Woods 2012 review's cancellation section.

---

## Q5. Is a simple channel mask adequate for a first prototype? When does a matrix approach pay off?

### Takeaway
Yes, for a first prototype. A channel mask (Wimmer's "Color" anaglyph, i.e. `glColorMask` or a channel swizzle) is what Blender uses. It is trivial, and it is exact when each filter passes exactly the projector primaries assigned to it. A matrix (Dubois or recomputed) pays off when:
1. the filters do not align with the projector's primaries, so a "cyan" gel also passes some red, or a custom colour pair splits a primary;
2. the content is saturated and coloured, so rivalry appears; or
3. measured crosstalk is high and needs compensation.

### Cited Findings
- **Blender's anaglyph is a pure per-channel source selection.** `anaglyph_encoding[3][3] = {{0,1,1},{1,0,1},{0,0,1}}` chooses, per output R,G,B, whether to take the left (0) or right (1) image, for red-cyan, green-magenta and yellow-blue. [Blender stereoimbuf.cc](https://github.com/blender/blender/blob/main/source/blender/imbuf/intern/stereoimbuf.cc). Blender's viewport draws anaglyph regions "with stereo frame-buffers using different shaders". [Blender wm_draw.cc](https://github.com/blender/blender/blob/main/source/blender/windowmanager/intern/wm_draw.cc)
- **Trade-offs of the colour mask.** Colour anaglyph gives partial colour but severe retinal rivalry. [Wimmer](https://3dtv.at/Knowhow/AnaglyphComparison_en.aspx); [Dietz 2012](https://aggregate.org/DIT/SPIEEI2012/spieei2012paper.pdf)
- **Ghosting depends mostly on display spectra and filters, not processing.** Woods & Rourke found CRT red-cyan crosstalk factors of 22.5 or more, and lower with red-blue only. The tested laptop LCD was 41.2 because its primaries are broadband: "there is little a filter can do". [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- **Dubois reports better results than empirical methods.** Projection-method images "are superior to those produced with classical methods". This is the author's own claim; no formal user study is reported in the paper. [Dubois 2001 PDF](https://www.site.uottawa.ca/~edubois/icassp01/anaglyphdubois.pdf)

### Inferences (engineering recommendation)
- **Prototype order:**
  1. Channel mask, with a per-eye gain and the stereo geometry from Q7.
  2. A "gray/half-colour" option, i.e. luminance into the weaker eye, to tame the red points.
  3. A generic 3x6 matrix uniform loaded from a preset file: mask, half-colour, Dubois RC 2009, GM 2010, YB 2010, and custom.
  4. A recomputed matrix from measured spectra.

  Building the matrix uniform from day one costs nothing, because a mask is just a matrix of 0s and 1s. Do it in linear light to stay compatible with later Dubois matrices.
- **For custom colour pairs, a matrix is almost certainly needed.** A pair that is not a clean partition of R/G/B (for example deep-red vs blue-green gels on a laser-phosphor projector whose "red" includes phosphor yellow) is exactly the case where a mask leaks and Dubois's projection repays the measurement effort.

### Gaps
- I found no controlled user study comparing a mask against Dubois on projectors specifically.

---

## Q6. Monitor vs projector: light sources, DLP colour wheels / white segment, screens, ambient light, colour modes

### Takeaway
Anaglyph separation is limited by how much each primary's spectrum overlaps the other eye's filter band. In Woods & Rourke's 2004 measurements, 3-chip LCD projectors had the lowest crosstalk (overall factor about 3–5), single-chip DLP projectors were intermediate (about 9–20), and CRT (22.5) and a laptop LCD (41.2) were worst. Narrowband RGB-laser primaries should separate better again. That is an inference supported by the physics, not measured for anaglyph here. Laser-phosphor sources produce broadband yellow that is filtered into red and green, and single-chip DLP white segments / BrilliantColor alter the colour mix. Both can work against both separation and the additive model behind Dubois's method. Screens with high gain or ALR coatings add hotspotting and off-axis colour shift.

### Cited Findings
- **Woods & Rourke 2004 measurements.** They used a Zeiss spectroradiometer on 7 digital projectors, plus CRT and LCD data. Best overall crosstalk factor per display (the factor is the sum of the left and right filter crosstalk percentages, which Woods says is "not a percentage"):

  | Display | Best overall crosstalk factor |
  |---|---|
  | Diamond CRT | 22.5 |
  | Acer laptop LCD | 41.2 |
  | NEC 1-chip DMD | 20.1 |
  | InFocus 1-chip DMD | 8.9 |
  | Epson 3LCD | 3.92 |
  | NEC VT540 3LCD | 4.66 / 3.93 |
  | Boxlight 3LCD | 3.08 / 4.59 |

  The best cyan filters on the 3LCD projectors gave about 0.3–0.5% crosstalk, while the red filters gave about 1.6–2.8%. Their conclusion: "3 chip LCD projectors were found to offer considerably lower anaglyphic ghosting than the other types of displays tested". Two units of the same Boxlight model differed because of colour balance, and they used default colour settings. [Woods & Rourke 2004](https://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2004-08.pdf)
- **Woods & Harris 2010.** They later simulated 16 glasses (6 red/cyan, 6 blue/yellow, 4 green/magenta) on 13 LCDs, 15 plasmas and 1 CRT. This was the first comparison across all three colour pairs; I could not access the results. [Woods & Harris, SPIE 7524](https://spiedigitallibrary.org/conference-proceedings-of-spie/7524/75240Q/Comparing-levels-of-crosstalk-with-red-cyan-blue-yellow-and/10.1117/12.840835.full); [Curtin eSpace](https://espace.curtin.edu.au/handle/20.500.11937/29921)
- **DLP white segment and BrilliantColor.** A white/clear segment raises peak white output, the headline lumen figure. Secondary colours "suffer when the white is increased without a corresponding increase in their lumen output", and white segments grew from about 30° to about 120° of the wheel. BrilliantColor adds cyan/magenta/yellow segments or uses spoke transitions, and is claimed to raise light output by 2–50% depending on the wheel. That figure is vendor marketing from 2007. [search summary: Embedded.com on BrilliantColor](https://www.embedded.com/?p=4013039); [Secrets of Home Theater, Optoma HD72 review](https://www.hometheaterhifi.com/volume_14_1/optoma-hd72-projector-1-2007-part-1.html); [Wikipedia: DLP](https://en.wikipedia.org/wiki/Digital_light_processing)
- **Laser-phosphor vs RGB laser.** In laser-phosphor, a blue laser excites a yellow phosphor whose broadband light is split into red/green by filters or a wheel, giving a relatively narrow gamut unless narrowband filtering (at a large light cost) is added. RGB laser uses a discrete laser per primary, giving purer primaries. Hybrids exist, such as red+blue lasers with phosphor green. [Celluloid Junkie, "RGB Laser vs Phosphor Laser" (2026)](https://celluloidjunkie.com/2026/03/25/cj-tech-rgb-laser-vs-phosphor-laser-understanding-the-difference/); [Barco: Laser phosphor vs RGB laser](https://barco.com/en/residential/creating-the-experience/the-architectural-digital-canvas/technology-ingredients/laser-light); [Sharp/NEC laser technologies](https://www.sharpdisplays.eu/p/laser/en/technologies.xhtml)
- **Narrowband separation in patents.** Patents note that laser sources' "very narrow band emission" suits passive spectral-separation glasses. Guard bands between opposite-eye passbands reduce crosstalk, and interference filters show a "blue shift" off-axis. Infitec-style designs use two interleaved primary triplets; one cited example is left ≈ 629/532/446 nm and right ≈ 615/518/432 nm. [search summary of USPTO patents incl. 10908486 "Spectral shaping for 3D imaging"](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10908486); [USPTO 8029139, "2D/3D switchable color display apparatus with narrow band emitters"](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8029139)
- **Screens.** Higher gain concentrates light, causing hotspotting and a narrower viewing angle. "The further you sit off axis, the darker the image becomes and you can even see a shift in some colors." [Audioholics, Stewart FireHawk G4 review](https://audioholics.com/stewart-filmscreen-firehawk-g4-screen-review). Half-gain angle is where brightness drops to 50% of peak. Bright projectors should be matched with lower-gain screens. [ProjectorReviews screen terminology](https://legacy.projectorreviews.com/articles-guides/projection-screen-terminology-and-advice/). One low-gain ALR material measured a half-gain angle of 78° horizontal and 18° vertical. [ProjectorCentral, Draper Onyx XS850E review](https://www.projectorcentral.com/draper_onyx_xs850e_screen_review.htm)
- **Black level.** Non-zero black level biases crosstalk measurement, so black must be subtracted. [Woods 2011](http://cmst.curtin.edu.au/wp-content/uploads/sites/4/2016/05/2011-14-woods-crosstalk_and_ghosting.pdf)

### Inferences (engineering recommendations)
- **Use a fixed, calibrated projector mode.** Choose a mode with BrilliantColor/white boost off (often called "sRGB", "Reference" or "Cinema"; names vary by vendor) and measure primaries in *that* mode. "Bright"/"Presentation" modes typically mix the white segment in, which breaks Dubois's additive model and moves the primaries. This is reasoning from the cited white-segment behaviour and has not been measured here.
- **Ambient light lifts black equally in both eyes**, reducing contrast but not crosstalk percentage as Woods defines it (black-subtracted). It does reduce the headroom available for subtractive cancellation.
- **For custom gels, match gel edges to the measured primaries.** A filter edge should sit in the spectral gap between primaries, and laser primaries have wide gaps. With laser-phosphor, the red and green from the same phosphor make a red|green split leakier than a blue|yellow split. This is inference; measure it.
- **Angle-dependent filters.** Interference/dichroic filters have off-axis blue shift, so an audience at wide angles sees shifted passbands. Absorptive gels (Roscolux-type, as used by Dubois) do not have this effect.
- **Screen colour shift is position-dependent**, so a single P matrix is only exact on-axis. Prefer a low-gain, neutral (non-ALR) surface for an installation with a wide audience, unless ambient light forces ALR.

### Gaps
- I found no measured anaglyph crosstalk data for RGB-laser or laser-phosphor projectors, nor any anaglyph study on ALR screens.
- I found no independent measured SPDs of current DLP BrilliantColor modes. The engineering agent should measure the actual projector; a consumer spectrometer such as an i1Pro-class device is adequate for SPD shape.

---

## Q7. Stereo camera geometry and comfort: interaxial, off-axis vs toe-in, zero-parallax plane, parallax limits, viewing distance

### Takeaway
Use parallel cameras with asymmetric (off-axis) frusta that converge on a virtual screen plane, which is the zero-parallax plane. Never toe-in, because it introduces vertical parallax. For comfort:
- keep angular disparity within about ±1° (Lambooij: classical problems are minor below 1°) to ±1.5° (Bourke);
- never let positive (uncrossed) screen parallax exceed the viewer's interocular distance, which would force divergence;
- be more conservative with crossed (in-front) parallax.

Because parallax is fixed in screen units, the same content is more demanding on a bigger screen viewed from farther away, so limits must be computed for the installation's actual screen width and audience distance. The Shibata et al. zone of comfort gives distance-dependent limits in diopters.

### Cited Findings
- **Bourke on toe-in and off-axis.** Toe-in "introduces vertical parallax", which causes discomfort. Off-axis keeps cameras parallel with asymmetric frusta and "introduces no vertical parallax". [Bourke, stereo render](http://paulbourke.net/stereographics/stereorender/)
- **Bourke's glFrustum maths.**
  - `widthdiv2 = near·tan(aperture/2)`, where aperture is the *horizontal* FOV.
  - Frustum shift `D = 0.5·eyesep·near/fo`, where fo is the focal or zero-parallax distance.
  - Right eye: `left = −aspect·widthdiv2 − D`, `right = aspect·widthdiv2 − D`. Left eye: the same with +D.
  - Cameras are translated ±eyesep/2 along the right vector.
  - Guidance: eye separation is about fo/30 ("acceptable in almost all situations"), with fo/20 as roughly the maximum. Keep objects nearer than fo/2 out; near clip is about fo/5; FOV sweet spot is 45–60°.
  - Parallax angle: `θ = 2·atan(DX/2D)`, with |θ| ≤ 1.5°. Maximum positive parallax = eye separation (an object at infinity). Many practitioners keep negative parallax closer to 0, especially at frame edges.
  - Classical "maximum separation on the display of 1/30 of the distance of the viewer to the display".
  - [Bourke, stereo render](http://paulbourke.net/stereographics/stereorender/)
- **three.js's current AnaglyphEffect does exactly this.** Eyes sit at ±eyeSep/2 (default 0.064 m) along the camera right vector. The screen rectangle sits at `planeDistance` (default 0.5), sized from the camera's FOV and aspect. Each eye's projection uses `frameCorners(camera, bottomLeft, bottomRight, topLeft, true)`, described as "physically-correct off-axis stereo projection" with "zero parallax at the plane distance". [three.js AnaglyphEffect.js](https://github.com/mrdoob/three.js/blob/dev/examples/jsm/effects/AnaglyphEffect.js)
- **Lambooij et al. 2009.** Below about 1° of disparity, "which still provides sufficient range to allow satisfactory depth perception in stereoscopic television", excessive parallax and accommodation-vergence conflict appear to be of minor importance. Discomfort can still come from fast motion in depth, 3D artefacts and unnatural blur. J. Imaging Sci. Technol. 53(3) 030201, doi:10.2352/J.ImagingSci.Technol.2009.53.3.030201. The title is cited in variants. [IS&T library](https://library.imaging.org/jist/articles/53/3/art00001)
- **Shibata, Kim, Hoffman & Banks 2011.** "The zone of comfort: Predicting visual discomfort with stereo displays", J. Vision 11(8):11, doi:10.1167/11.8.11.
  - Comfort-zone boundaries, in diopters, as focal distance D_f against vergence distance D_v:
    - far boundary: `D_f = 1.129·D_v + 0.442`;
    - near boundary: `D_f = 1.035·D_v − 0.626`.

    The authors call the estimate "arguable".
  - Negative conflicts (content behind the screen) are less comfortable at far viewing distances; positive conflicts (in front of the screen) are less comfortable at near distances.
  - Divergence was capped so it "would not exceed 0.85°", because most viewers cannot diverge more than about 1° beyond parallel.
  - Cinema's comfortable range is about 1.6 m to infinity.
  - [PMC3369815](https://pmc.ncbi.nlm.nih.gov/articles/PMC3369815)

### Inferences (geometry derived by similar triangles; engineering recommendations)
- **Screen parallax.** For viewer distance V, interocular e, and a point perceived at distance Z from the viewer: screen parallax `p = e·(1 − V/Z)`. p = 0 at the screen, p → e as Z → ∞ (the divergence limit), and p < 0 in front. Angular disparity relative to the screen is ≈ `p/V` radians.
- **Worked example for an installation**, assuming V = 4 m, screen width 4 m and 1920 px: 1° ≈ 0.0175·4 m ≈ 70 mm, which is already more than e ≈ 63–65 mm. The divergence limit (p ≤ e) is therefore the binding behind-screen constraint, at about 63 mm ≈ 30 px. Viewers closer than V see larger angles for the same p, so size limits for the *closest* seat. The ~63–65 mm interocular figure is the brief's figure and three.js's 64 mm default; I did not verify a population study this session.
- **Shibata near limit (my arithmetic).** At 3 m, D_f = 0.333 D, and the near boundary gives D_v = (0.333 + 0.626)/1.035 ≈ 0.93 D, so content should not appear nearer than about 1.08 m. The far boundary yields a negative D_v, so it is not binding; only the divergence limit applies.
- **Recommended parameters.** Pass e_world, the zero-parallax distance, and a parallax budget in *pixels*, computed from screen width (px/m), viewer distance and e. Clamp interaxial so the scene's depth range maps inside [−budget_near, +min(e, budget_far)].

### Gaps
- I did not fetch Lambooij's full text, so the exact wording around the 1° figure comes from abstract-level text.
- I did not find a primary source for the "% of screen width" rules (often quoted as about 1–2% positive and 2–3% negative). They are not cited here and should be treated as unverified folklore.
- I did not verify a population IPD statistic (for example Dodgson 2004) this session.

---

## Q8. Inspectable open-source implementations (paths, URLs, licenses)

### Takeaway
The most useful references, in order:
1. three.js `AnaglyphEffect.js` (MIT). Off-axis stereo plus a Dubois red-cyan mat3 pair, applied in linear space.
2. three.js `AnaglyphPassNode.js` (MIT). A table of True/Grey/Colour/Half-colour/Dubois/Optimised/Compromise matrices.
3. ffmpeg `vf_stereo3d.c`, whose file header is the GNU **GPL v2-or-later** notice, not LGPL. Includes the Dubois RC/GM/YB integer tables, applied on gamma-encoded 8-bit data.
4. Blender `stereoimbuf.cc` (GPL-2.0-or-later). Pure channel mask.
5. Bino (GPLv3+). Dubois RC/GM/AB modes; source not inspected.

### Cited Findings
- **three.js `examples/jsm/effects/AnaglyphEffect.js` (WebGL).**
  - Dubois matrices as above. Fragment shader: `clamp(colorMatrixLeft*colorL.rgb + colorMatrixRight*colorR.rgb, 0., 1.)`, then tonemapping and `colorspace_fragment`.
  - Off-axis via `CameraUtils.frameCorners`.
  - Render targets are RGBA with LinearFilter min / NearestFilter mag.
  - [GitHub](https://github.com/mrdoob/three.js/blob/dev/examples/jsm/effects/AnaglyphEffect.js); MIT license, "Copyright © 2010-2026 three.js authors". [LICENSE](https://github.com/mrdoob/three.js/blob/dev/LICENSE)
- **three.js `examples/jsm/tsl/display/AnaglyphPassNode.js` (WebGPU/TSL).**
  - Algorithms: TRUE, GREY, COLOUR, HALF_COLOUR, DUBOIS, OPTIMISED, COMPROMISE. Colour modes: RED_CYAN, MAGENTA_CYAN, MAGENTA_GREEN. Luminance uses BT.601 coefficients (0.299/0.587/0.114).
  - "Compromise" is attributed to Ahtik, "Techniques of Rendering Anaglyphs for Use in Art": Left R = 0.439R+0.447G+0.148B; Right G = 0.095R+0.934G+0.005B; Right B = 0.018R+0.028G+1.057B.
  - Its DUBOIS + MAGENTA_GREEN entry is *derived* by summing red-cyan Dubois rows. It is **not** Dubois's published TrioScopics GM matrix.
  - [GitHub](https://github.com/mrdoob/three.js/blob/dev/examples/jsm/tsl/display/AnaglyphPassNode.js)
- **ffmpeg `libavfilter/vf_stereo3d.c`.**
  - Output modes: `arbg`, `argg`, `arcg`, `arch`, `arcc`, `arcd` (red-cyan Dubois), `agmg/agmh/agmc/agmd` (green-magenta gray/half/color/Dubois), `aybg/aybh/aybc/aybd` (yellow-blue).
  - Coefficients are 16.16 fixed point, applied directly to 8-bit stored values, with a single clip.
  - The file header carries the GNU **General** Public License v2-or-later notice; copyright 2010 Gordon Schmidt and 2013–2015 Paul B Mahol. **Note: this file is GPL, not LGPL**, so linking it pulls in GPL.
  - [GitHub](https://github.com/FFmpeg/FFmpeg/blob/master/libavfilter/vf_stereo3d.c)
- **Blender `source/blender/imbuf/intern/stereoimbuf.cc`.** SPDX `GPL-2.0-or-later`. Channel-select anaglyph for RC/GM/YB. [GitHub](https://github.com/blender/blender/blob/main/source/blender/imbuf/intern/stereoimbuf.cc). Window-level anaglyph drawing lives in `wm_draw.cc` / `wm_stereo.cc`. [wm_stereo.cc](https://github.com/blender/blender/blob/main/source/blender/windowmanager/intern/wm_stereo.cc)
- **Bino.** GPLv3+ ([Bino 1.0.0 announcement](https://lists.nongnu.org:443/archive/html/bino-list/2011-04/msg00102.html)). Its manual lists "Green/magenta anaglyph, high-quality Dubois method" and "Amber/blue anaglyph, high-quality Dubois method", with red-cyan Dubois as the fallback output. [bino(1) man page](https://manpages.ubuntu.com/manpages/bionic/man1/bino.1.html). Bino 2.x is a Qt6 rewrite. [search summary of Bino pages](https://software.pureos.net/sw/org.bino3d.bino). Project page: [nongnu.org/bino](http://www.nongnu.org/bino/)
- **StereoPhoto Maker.** Has an "Optimized Anaglyph Setting" dialog that takes an arbitrary 3x6 integer matrix (/1000), with presets for Red/Cyan gray, Color, Half Color and Dubois. Visible in Dubois's screenshots: [Flickr SPM_GM_matrix](https://www.flickr.com/photos/e_dubois/5132528166/). Home page: [stereo.jpn.org](http://stereo.jpn.org/eng/stphmkr/)
- **Paul Bourke.** Stereo rendering notes, including the off-axis glFrustum code. [paulbourke.net/stereographics/stereorender](http://paulbourke.net/stereographics/stereorender/)
- **Other Dubois implementations.** A Nuke gizmo "DuboisAnaglyph v1.0" ([Nukepedia](https://www.nukepedia.com/gizmos/stereo/duboisanaglyph)) and a Citra emulator commit hard-coding Dubois matrices "optimized for LCD" ([Citra commit](https://git.openpunk.com/OpenPunk/citra/commit/96c375229b4d7433639d12c033b6722a95cd8f2e)), both surfaced by search and not inspected.

### Inferences
- three.js's two files are the cleanest MIT-licensed references to port. The geometry (frameCorners off-axis) and the shader are both under 300 lines. The Dubois GM/YB matrices are facts, so they can be used freely from Dubois's own screenshots instead of copying ffmpeg's GPL table.
- For a Python/moderngl port, the compositor is: two offscreen eye textures, one full-screen pass with `uniform mat3 u_ML, u_MR;` (or `mat3x2`-equivalents for a 3x6), linear-light maths, clamp, encode.

### Gaps
- I did not inspect Bino's shader source: the upstream git host returned 403 and no GitHub mirror was reachable from this session. Its linear/sRGB handling is therefore unverified.
- I did not search for Unity/Unreal anaglyph plugins.
- SPM's licence (freeware, closed-source as I understand it) is not verified here.
- I found no maintained GitHub repo that computes Dubois matrices from spectra.

---

## Q9. Local repo: what rendering stack Hyperspace actually uses (observed facts only, no files modified)

### Takeaway
Hyperspace has no stereo, anaglyph or camera-pair code today. The active app, `hyperspace-python`, is a Python/moderngl (OpenGL 3.3 core) + GLFW + imgui-bundle renderer. It projects 4D→3D→2D **on the CPU** with a single mono camera and sends pixel-space vertices plus a homogeneous divisor to simple GLSL shaders. The legacy `hyperspace-web/hyperspace.html` is a Canvas 2D page, not three.js or WebGL. No sRGB framebuffer or gamma handling was found.

### Cited Findings
All observed directly in the local working tree at commit `cdd6364`.

- **Top level of `/home/user/hyperspace`:** `README.md`, `.gitignore`, `.claude/`, `hyperspace-web/`, `hyperspace-python/`, `hyperspace-ios-widget/`, `hyperspace-contact/`, `reports/` (empty), `research_notes/`. The README describes the project as "A real-time 4D polytope visualizer", says `hyperspace-python/` is "where active development happens", and calls `hyperspace-web/` the original single-file HTML version "kept for reference and as the test oracle". (`/home/user/hyperspace/README.md`)
- **`hyperspace-web/`:** contains `hyperspace.html` (118 KB, single file, no dependencies), `README.md` and `vercel.json` (a rewrite of / to hyperspace.html plus `Permissions-Policy: microphone=(self)`).
  - Rendering is Canvas 2D: `const ctx = cv.getContext("2d", { alpha: false });` at line 683.
  - "three" occurs only as an English word, e.g. "The three w-planes". There is no three.js, WebGL or shader.
  - The UI has a "4D perspective" log slider (line 435).
  - "stereo" appears only in an audio loopback-device regex, "stereo mix" (line 2138).
- **`hyperspace-python/` dependencies** (`pyproject.toml`): `moderngl>=5.12`, `glfw>=2.10.2`, `pyopengl`, `imgui-bundle`, `numpy`, `pillow`, `sounddevice`, `soundfile`, `mido`/`python-rtmidi`, `torch`/`torchvision`/`mlx` (the dream worker), `pyobjc-framework-metal/quartz/cocoa` (macOS), Ultraleap `leap`/`leapc-cffi`, and `pyusb`. The entry point is `hyperspace.app:main`.
- **GL context** (`hyperspace/app.py` lines 288–301): OpenGL 3.3 core, forward-compatible, `glfw.SAMPLES = 4` (4x MSAA), and `TRANSPARENT_FRAMEBUFFER` toggled for overlay mode.
- **Projection is on the CPU.** `geometry.project_h()` (`hyperspace/geometry.py:1009`) runs:
  1. `_to3`, a 4D rotation followed by the 4D perspective divide `k = d4/(d4 − w)` (`geometry.py:972`);
  2. `_camera`, a yaw-then-pitch rotation (`geometry.py:988`);
  3. the 3D perspective step `div3 = CAM3 − 0.9·z1`, `k2 = CAM3/div3` with `CAM3 = 3.4` (`geometry.py:669`), `scale = min(w,h)·0.30`, `px = w/2 + x1·k2·scale`, `py = h/2 − y1·k2·scale`.

  It returns `div4·div3` as a homogeneous divisor for perspective-correct UVs. `render.py` calls it at line 1435, then applies zoom/pan in logical pixels (line 1444).
- **Shaders:** inline GLSL in `render.py`. `FACE_VS` (line 153) takes `in_pos` in pixel coordinates plus `in_wc` and outputs `gl_Position = vec4(nx*in_wc, ny*in_wc, 0, in_wc)`. Shader files live in `hyperspace/shaders/` (`_common.glsl`, `patterns.glsl`, `fx/*.glsl`).
- **Existing FX are 2D post effects**, for example `fx/deconverge.glsl`, which offsets the R, G and B channels separately ("Minecraft's deconverge"), and `fx/doublevision.glsl`, a blended ghost copy. Neither is stereo.
- **Colour handling:**
  - Alpha blending `SRC_ALPHA, ONE_MINUS_SRC_ALPHA` (`render.py:594–595`).
  - The master-dim pass notes "The multiply is linear in the framebuffer's values; a curve for the bottom of the throw would go here" (`render.py` ~1360).
  - Outputs carry "RGBA8 … premultiplied, LINEAR" frames, where LINEAR refers to texture filtering (`outputs.py:118`).
  - A grep for `srgb|gamma|anaglyph|stereo|parallax|IPD` across the Python package, shaders, web HTML, widget and contact page found no colour-space or stereo code. The only hits were test fixture names in `tests/test_fx.py`.
  - Points are red `RED = (1.0, 43/255, 43/255)` (`hyperspace/view.py`).
- **Outputs** (`hyperspace/outputs.py` docstring): "One frame is drawn per loop; each output — a window on its own screen … — shows that frame through its own switches". `MAX_OUTPUTS = 4`. Plan 21 handles multiple render outputs.
- **Other subprojects:** `hyperspace-ios-widget/` holds `Hyperspace.js`, a Scriptable widget showing a QR code. `hyperspace-contact/` holds `index.html` and `qr.svg`, a link tree. Neither renders 3D.

### Inferences (for the implementing agent)
- **Stereo can be injected at the CPU camera step.** `k2 = CAM3/(CAM3 − 0.9·z1)` is equivalent to a pinhole at distance `Zc = CAM3/0.9 ≈ 3.78` in front of the plane z1 = 0, where k2 = 1 (my derivation). So **z1 = 0 is a natural zero-parallax plane**.
  - For an eye offset `ex = ±e/2` (world units) with off-axis projection onto that plane: `x_screen = x1·k2 + ex·(1 − k2)`, so `px_eye = w/2 + (x1·k2 + ex·(1 − k2))·scale`.
  - y is unchanged, so there is no vertical parallax.
  - Screen parallax between the eyes is `e·(k2 − 1)·scale` px, with sign by convention. It is 0 at z1 = 0, crossed for z1 > 0 (nearer), and uncrossed for z1 < 0.
  - The homogeneous divisor and depth cues are unchanged per eye.

  This needs verifying against `tests/test_core.py` parity before use.
- **Render the scene twice per frame.** Because the renderer draws "one frame per loop" shared by outputs, anaglyph needs two scene passes, one per eye, into two textures, followed by a compositor pass. The FX chain should probably run per eye *before* compositing; otherwise channel-shifting FX such as deconverge would corrupt the eye separation.
- **Linear vs sRGB is a decision to make.** No sRGB framebuffers are used, so all current colour maths happens on display-encoded 8-bit values. A Dubois-correct compositor should either linearise in the shader before the matrix and re-encode after, or render eye targets as float/sRGB textures.
- **The 4D perspective is unaffected.** Stereo only concerns the final 3D→2D step, so the 4D divide (`depth4`) stays mono. Both eyes see the same 3D shadow of the 4D object, which is correct.

### Gaps
- I did not read `docs/ARCHITECTURE.md` / `ENGINEERING.md` in full, so there may be design notes on outputs/projectors I did not capture. No anaglyph/stereo mentions turned up in a docs grep.
- I did not run the app or the tests.
