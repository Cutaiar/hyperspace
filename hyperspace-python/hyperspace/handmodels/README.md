# Hand models

Rigged hand meshes the ghost hands' mesh styles draw (`hyperspace/handmesh.py`,
`ghost.style` MESH, LEAP HAND, LOW POLY). Each folder keeps its own licence.

## `webxr/` — MIT

`left.glb`, `right.glb`: the `generic-hand` profile of the WebXR Input
Profiles assets, unmodified, from the npm package
`@webxr-input-profiles/assets@1.0.20`
(`dist/profiles/generic-hand/`). Copyright (c) 2019 Amazon; MIT, see
`webxr/LICENSE.md`.

## `ultraleap/` — Apache License 2.0

From Ultraleap's Unity plugin (github.com/ultraleap/UnityPlugin, commit
08ea531c78d70364ae13d3a02467bbcb6404d582), `Packages/Tracking/Hands/Runtime/Models/`.
Copyright Ultraleap Limited; Apache License 2.0, see `ultraleap/LICENSE.md`.

**Modified** (Apache 2.0 §4(b)): each file was converted from FBX to glTF
binary, with no change to the mesh, the rig or the weights:

- `generic_left.glb` ← `GenericHand/GenericHand.fbx` (Blender 5.0.1's FBX
  import, then its glTF export). Left hand only; the right is its mirror.
- `lowpoly_left.glb`, `lowpoly_right.glb` ← `Low Poly/LowPoly_Rigged_Hand_Left.fbx`
  and `…_Right.fbx` (ASCII FBX: Assimp's export to binary FBX, then
  Blender as above). The colour texture is not carried.

Ultraleap's names and marks are theirs; nothing here is endorsed by Ultraleap.

## At load

The files themselves are as described above. Two things happen to them in
`hyperspace/handmesh.py`, to the data only, never to the files:

- **The wrist is shortened** (`shorten_wrist`, `WRIST_MM`). Each rig was
  built with more arm than the tracker drives — Ultraleap's generic hand a
  forearm to the elbow, 100 mm behind the palm, the others a 50 mm cuff —
  and none of it follows the performer. Everything behind the palm's base
  is squeezed along the hand's forward axis until it reaches back no more
  than 25 mm. The palm and the fingers are untouched.
- **A one-sided model is mirrored** for the other hand
  (`HandModel.mirrored`), as noted above.
