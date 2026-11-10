"""Rigged hand meshes, skinned to the tracked bones — a leaf: numpy only.

A model is a glTF binary (`.glb`) with one skinned mesh: positions,
normals, four joints and weights a vertex, and the skin's inverse bind
matrices. `load` reads one (`read_glb`, no glTF library) into a
`HandModel`, in mm; `MODELS` names the ones the package ships (in
`handmodels/`, each with its licence) and how each one's joints map onto
the tracker's.

The tracker's hand is `hands.core.skeleton`'s: per digit (thumb … pinky)
five joints, base to tip — a `HandPose.joints` (5, 5, 3). A model joint
maps to one of those (`(digit, k)`), or to the palm (`PALM`: the wrist,
a palm bone, a forearm — anything that moves with the back of the hand).

The skinning (`bone_matrices`) never reads the tracker's rotations or the
model's: every bone gets a frame built by one recipe — origin at its
base joint, z along the bone, x the knuckle line (index knuckle to
pinky's) made square to it — once on the model's rest joints and once a
frame on the tracked ones. The palm stays rigid, in the model's shape,
scaled by the hand's size (its metacarpals' length); each finger is a
chain from its knuckle on it, each bone turned to its tracked direction
and stretched to its tracked length — so the fingers follow the
performer's, whatever the two hands' sizes, and no axis convention of
either side matters.

Which file draws a pose is the pose's own handedness (`chirality`), not
the side the tracker named — a mirrored stage flips it, and a mirrored
hand needs the other model. A model with one side only gets the other by
reflection (`HandModel.mirrored`).
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent / "handmodels"

PALM = "palm"            # a joint that moves with the palm
MAX_BONES = 32           # the skinning shader's array

# glTF component types → numpy
_COMPONENT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16,
              5125: np.uint32, 5126: np.float32}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# ------------------------------------------------------------------ reading

def read_glb(data: bytes) -> tuple[dict, bytes]:
    """A `.glb`'s JSON and its binary chunk."""
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError("not a glTF 2 binary")
    off, doc, blob = 12, None, b""
    while off < min(length, len(data)):
        n, kind = struct.unpack_from("<I4s", data, off)
        chunk = data[off + 8: off + 8 + n]
        if kind == b"JSON":
            doc = json.loads(chunk.decode("utf-8"))
        elif kind == b"BIN\x00":
            blob = chunk
        off += 8 + n
    if doc is None:
        raise ValueError("a glTF binary with no JSON chunk")
    return doc, blob


def accessor(doc: dict, blob: bytes, i: int) -> np.ndarray:
    """Accessor `i` as an array (count, width) — normalised integers as
    0–1 floats, as glTF reads them."""
    acc = doc["accessors"][i]
    dt = np.dtype(_COMPONENT[acc["componentType"]])
    width, count = _WIDTH[acc["type"]], acc["count"]
    if "bufferView" not in acc:
        return np.zeros((count, width), dtype=dt)
    bv = doc["bufferViews"][acc["bufferView"]]
    start = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride") or dt.itemsize * width
    rows = np.ndarray((count, width), dtype=dt, buffer=blob, offset=start,
                      strides=(stride, dt.itemsize)).copy()
    if acc.get("normalized") and dt.kind in "iu":
        rows = rows.astype(np.float64) / np.iinfo(dt).max
    return rows


def _local(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    x, y, z, w = node.get("rotation", (0.0, 0.0, 0.0, 1.0))
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * np.asarray(node.get("scale", (1.0, 1.0, 1.0)))
    m[:3, 3] = node.get("translation", (0.0, 0.0, 0.0))
    return m


# ------------------------------------------------------------------ the model

@dataclass
class HandModel:
    """One skinned hand, in mm, in its bind pose. `joints` / `weights`
    (V, 4) index `names`; `rest` (J, 3) each joint's bind position."""

    positions: np.ndarray
    normals: np.ndarray
    indices: np.ndarray
    joints: np.ndarray
    weights: np.ndarray
    names: list[str]
    rest: np.ndarray
    side: str = "right"
    slots: dict = field(default_factory=dict)     # joint name → (digit, k) or PALM

    def mirrored(self) -> HandModel:
        """The other hand: x reflected, the winding turned back."""
        f = np.array([-1.0, 1.0, 1.0])
        tri = self.indices.reshape(-1, 3)[:, ::-1].reshape(-1)
        return HandModel(self.positions * f, self.normals * f, tri.copy(), self.joints,
                         self.weights, self.names, self.rest * f,
                         "left" if self.side == "right" else "right", self.slots)


def load(path: Path, slots: dict, side: str, scale: float = 1000.0) -> HandModel:
    """The skinned mesh in `path` (a `.glb`), scaled to mm (glTF is in
    metres), its joints mapped by `slots` (name → (digit, k) or PALM;
    a joint not named is PALM)."""
    doc, blob = read_glb(Path(path).read_bytes())
    skin_node = next(n for n in doc["nodes"] if "skin" in n and "mesh" in n)
    skin = doc["skins"][skin_node["skin"]]
    names = [doc["nodes"][j].get("name", f"joint{j}") for j in skin["joints"]]
    if len(names) > MAX_BONES:
        raise ValueError(f"{Path(path).name}: {len(names)} joints, at most {MAX_BONES}")
    if "inverseBindMatrices" in skin:
        ibm = accessor(doc, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4)
        ibm = np.transpose(ibm, (0, 2, 1))                  # column-major
        rest = np.array([np.linalg.inv(m)[:3, 3] for m in ibm])
    else:                                                   # identity binds
        rest = np.zeros((len(names), 3))
    pos, nrm, idx, jnt, wgt = [], [], [], [], []
    base = 0
    for prim in doc["meshes"][skin_node["mesh"]]["primitives"]:
        a = prim["attributes"]
        p = accessor(doc, blob, a["POSITION"]).astype(np.float64)
        n = (accessor(doc, blob, a["NORMAL"]).astype(np.float64) if "NORMAL" in a
             else np.zeros_like(p))
        j = accessor(doc, blob, a["JOINTS_0"]).astype(np.int32)
        w = accessor(doc, blob, a["WEIGHTS_0"]).astype(np.float64)
        i = (accessor(doc, blob, prim["indices"]).reshape(-1).astype(np.uint32)
             if "indices" in prim else np.arange(len(p), dtype=np.uint32))
        pos.append(p)
        nrm.append(n)
        jnt.append(j)
        wgt.append(w)
        idx.append(i + base)
        base += len(p)
    w = np.concatenate(wgt)
    w /= np.maximum(w.sum(axis=1, keepdims=True), 1e-9)
    m = HandModel(np.concatenate(pos) * scale, np.concatenate(nrm), np.concatenate(idx),
                  np.concatenate(jnt), w, names, rest * scale, side,
                  {nm: slots.get(nm, PALM) for nm in names})
    if not np.any(np.linalg.norm(m.normals, axis=1) > 0):
        m.normals = _vertex_normals(m.positions, m.indices)
    return m


def _vertex_normals(p: np.ndarray, idx: np.ndarray) -> np.ndarray:
    t = idx.reshape(-1, 3)
    fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
    n = np.zeros_like(p)
    for k in range(3):
        np.add.at(n, t[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


# ------------------------------------------------------------------ the models shipped

def _webxr_slots() -> dict:
    out = {"thumb-metacarpal": (0, 1), "thumb-phalanx-proximal": (0, 2),
           "thumb-phalanx-distal": (0, 3), "thumb-tip": (0, 4)}
    for d, f in enumerate(("index", "middle", "ring", "pinky"), start=1):
        for k, part in enumerate(("metacarpal", "phalanx-proximal", "phalanx-intermediate",
                                  "phalanx-distal", "tip")):
            out[f"{f}-finger-{part}"] = (d, k)
    return out


def _ultraleap_slots(prefix: str = "") -> dict:
    """Ultraleap's rigs: `{finger}_{meta,a,b,c,end}`, `thumb_{meta,a,b,end}`
    (their thumb_meta is the tracker's thumb proximal)."""
    out = {f"{prefix}thumb_meta": (0, 1), f"{prefix}thumb_a": (0, 2),
           f"{prefix}thumb_b": (0, 3), f"{prefix}thumb_end": (0, 4)}
    for d, f in enumerate(("index", "middle", "ring", "pinky"), start=1):
        for k, part in enumerate(("meta", "a", "b", "c", "end")):
            out[f"{prefix}{f}_{part}"] = (d, k)
    return out


@dataclass(frozen=True)
class Spec:
    """A shipped model: its files per side (one side alone is mirrored for
    the other) and its joints' slots."""

    files: tuple[tuple[str, str], ...]     # (side, path under handmodels/)
    slots: dict
    scale: float = 1000.0


MODELS: dict[str, Spec] = {
    "webxr": Spec((("left", "webxr/left.glb"), ("right", "webxr/right.glb")), _webxr_slots()),
    # Ultraleap's generic hand: left only (mirrored), a forearm to the elbow
    # that moves with the palm
    "ultraleap": Spec((("left", "ultraleap/generic_left.glb"),), _ultraleap_slots()),
    # their low-poly pair, each joint prefixed by its side ("L_", "R_")
    "lowpoly": Spec((("left", "ultraleap/lowpoly_left.glb"),
                     ("right", "ultraleap/lowpoly_right.glb")), _ultraleap_slots("{s}_")),
}

# kept across a hot reload of this module: the files are read once a run
_loaded: dict[str, dict[str, HandModel] | None] = globals().get("_loaded", {})


def models(name: str) -> dict[str, HandModel] | None:
    """The shipped model `name`, both sides, loaded once (None when its
    files are missing or unreadable)."""
    if name in _loaded:
        return _loaded[name]
    spec = MODELS.get(name)
    out: dict[str, HandModel] | None = None
    if spec is not None:
        try:
            out = {}
            for side, rel in spec.files:
                slots = {k.replace("{s}", side[0].upper()): v for k, v in spec.slots.items()}
                out[side] = load(HERE / rel, slots, side, spec.scale)
            for side, other in (("left", "right"), ("right", "left")):
                if side not in out and other in out:
                    out[side] = out[other].mirrored()
        except (OSError, ValueError, KeyError, StopIteration) as e:
            print(f"handmesh: {name}: {type(e).__name__}: {e}")
            out = None
    _loaded[name] = out
    return out


# ------------------------------------------------------------------ the skinning

def _unit(v: np.ndarray, fallback=(0.0, 0.0, 1.0)) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.asarray(fallback, dtype=np.float64)


def frame(origin: np.ndarray, z: np.ndarray, across: np.ndarray) -> np.ndarray:
    """A rigid 4 × 4 frame: z along `z`, x `across` made square to it."""
    z = _unit(z)
    x = across - z * float(across @ z)
    if np.linalg.norm(x) < 1e-6 * max(np.linalg.norm(across), 1e-9):
        x = np.cross(z, (0.0, 1.0, 0.0) if abs(z[1]) < 0.9 else (1.0, 0.0, 0.0))
    x = _unit(x)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, np.cross(z, x), z, origin
    return m


def hand_axes(J: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(palm origin, forward, knuckle line) from (5, 5, 3) joints: the
    metacarpals' mean base, toward their mean knuckle, index knuckle to
    pinky's."""
    base = J[1:5, 0].mean(axis=0)
    return base, J[1:5, 1].mean(axis=0) - base, J[1, 1] - J[4, 1]


def chirality(J: np.ndarray, normal: np.ndarray) -> str:
    """"right" or "left" by the joints' own shape, against the palm's
    normal (out of the palm): which model draws them."""
    _, f, t = hand_axes(J)
    return "right" if float(np.cross(t, f) @ normal) > 0.0 else "left"


def rest_joints(model: HandModel) -> np.ndarray:
    """The model's rest joints as the tracker's (5, 5, 3) — slots the
    model lacks (a thumb metacarpal, say) at the next one's place."""
    J = np.full((5, 5, 3), np.nan)
    for name, slot in model.slots.items():
        if slot != PALM:
            J[slot] = model.rest[model.names.index(name)]
    for d in range(5):
        for k in range(4, -1, -1):
            if np.isnan(J[d, k, 0]):
                J[d, k] = J[d, k + 1] if k < 4 else J[d, k - 1]
    return J


def _palm_length(J: np.ndarray) -> float:
    """The four finger metacarpals' mean length."""
    return float(np.mean(np.linalg.norm(J[1:5, 1] - J[1:5, 0], axis=1)))


def bone_matrices(model: HandModel, J: np.ndarray, rest: np.ndarray | None = None
                  ) -> np.ndarray:
    """(len(model.names), 4, 4): each joint's skinning matrix taking the
    model's bind pose onto the tracked joints `J` (5, 5, 3, mm).

    The palm is rigid, in the model's own shape: placed by the tracked
    palm's frame and scaled by the hand's size, its metacarpals with it —
    the tracker fans them as the fingers spread, which would stretch the
    web between two knuckles into a V. Each finger is a chain from its
    knuckle on that palm (the thumb from its tracked base): every bone
    turned to its tracked direction,
    stretched to its tracked length, and starting where the one before it
    ends, so the joints stay whole and a fingertip lands within a few mm
    of the tracked one."""
    R = rest_joints(model) if rest is None else rest
    o_r, f_r, t_r = hand_axes(R)
    o_p, f_p, t_p = hand_axes(J)
    # the hand's size: its metacarpals' length, which a spread or a fist
    # leaves alone (the knuckle span does not: spread fingers widen it)
    g = _palm_length(J) / max(_palm_length(R), 1e-9)
    g = min(max(g, 0.8), 1.25)
    palm = frame(o_p, f_p, t_p) @ np.diag((g, g, g, 1.0)) @ np.linalg.inv(frame(o_r, f_r, t_r))
    chain: dict = {}
    for d in range(5):
        parent = palm
        # every digit's first bone starts at its own tracked base — a
        # finger's metacarpal as much as the thumb's proximal. Riding the
        # rigid palm instead cost each finger its knuckle's whole offset,
        # the same displacement all the way to the tip (the pinky's 13 mm
        # open, 15 mm spread: a finger's own width, and the ring-pinky web
        # with it). The metacarpals are what these rigs fan the palm by,
        # so the web between two knuckles is the model's own weights now,
        # not a gap the skinning opened.
        for k in range(1 if d == 0 else 0, 4):
            a_r, b_r, a_p, b_p = R[d, k], R[d, k + 1], J[d, k], J[d, k + 1]
            l_r, l_p = float(np.linalg.norm(b_r - a_r)), float(np.linalg.norm(b_p - a_p))
            if l_r > 1e-6 and l_p > 1e-6:
                origin = a_p if parent is palm else parent[:3, :3] @ a_r + parent[:3, 3]
                s = min(max(l_p / l_r, 0.5), 2.0)
                parent = (frame(origin, b_p - a_p, t_p) @ np.diag((g, g, s, 1.0))
                          @ np.linalg.inv(frame(a_r, b_r - a_r, t_r)))
            chain[(d, k)] = parent
        chain[(d, 4)] = parent           # a tip rides on its digit's last bone
    out = np.repeat(palm[None], len(model.names), axis=0)
    for i, name in enumerate(model.names):
        slot = model.slots.get(name, PALM)
        if slot != PALM and slot in chain:   # the thumb's (0, 0) stays on the palm
            out[i] = chain[slot]
    return out
