# NLM Visible Human hand — Creative Commons Attribution 4.0

`bones_right.glb` ← "Skeletal Hand" by **Jeremy Swan**, from Poly Pizza
(https://poly.pizza/m/3b3VmmxXZ7S), licensed CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). The author's note: "Kristen
Browne's hand model constructed from the Visible Human at NLM" (the U.S.
National Library of Medicine).

**Modified** (CC BY 4.0 §3(a)(1)(B)), with no change to the shape of a
single bone:

- The file as published is one unrigged mesh whose faces share no
  vertices. Welding them at 1e-4 leaves 27 whole pieces — the hand's 27
  bones (8 carpals, 5 metacarpals, 14 phalanges).
- An armature was fitted to those pieces and the mesh skinned to it: the
  carpals to a `wrist` bone, each digit bone rigidly to its own, one
  bone a piece and weight 1 throughout, so no bone bends. Its joints are
  named for the WebXR `generic-hand` profile, which is what
  `handmesh._webxr_slots` reads.
- Faces are flat-shaded, as the unwelded file drew them.

Built with Blender 5.1. Nothing here is endorsed by the NLM or the author.
