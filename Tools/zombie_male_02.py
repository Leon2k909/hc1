"""A second Zombies body: models/zombie/zombie_male_02.vmdl, from a Meshy scan of a zombie in an open shirt and jeans.

A zombie is an invisible citizen driver with a body bone-merged onto it (ZombiesRoundSystem.SpawnZombie), so the body
must be skinned to the citizen's own skeleton, at the citizen's own rest pose. The scan (sources/Zombies/zombie_male_02,
not in git) is 1.9M triangles, unrigged, and stands 1.90 m in its own A-pose with a torso a fifth longer than the
citizen's. In order:

1. zombie_male_02_blender.py "lods": four LODs decimated from the scan, each unwrapped afresh with its own maps baked
   from it (see its docstring).
2. Joints: FIT is where each of the citizen's main joints sits in the scan, placed from its cross-sections (the arms'
   narrowest point at the wrist, the back of the knee, the heel and toes, the neck's narrowest point) and checked in
   the preview renders. The head keeps the scan's tilt: its joint sits straight above the neck's.
3. The forearms are untwisted. The scan's hands hang palm back, about 90 degrees turned in from the citizen's resting
   hand; bound like that, every clip would turn them that much further, past what a wrist can (the user's "twisted"
   hands). Each forearm turns about its own axis by UNTWIST times a ramp from elbow (none) to wrist (all), and the
   hand turns with it, so it hangs palm to the thigh like the citizen's.
4. Each main bone gets an affine map from the scan onto the citizen's rest pose: limbs turn and stretch along their
   length to the citizen's segment, the trunk only moves and shortens (keeping the scan's posture), and everything
   else is GIRTH times as thick. Twist and helper bones, fingers and the hand's extremities move with their parents.
5. Weights: the citizen's reference body (citizen_human_male_REF.fbx) is carried into the scan's shape by the inverse
   of those maps, and each scan vertex takes the weights of the nearest point on it, from the same side and limb
   (`allowed`), then a few rounds of smoothing over the mesh. The fingers are rigid with the hand (the scan's are
   curled and don't line up with the citizen's).
6. The scan is carried onto the citizen's rest pose by those maps, blended by its weights, and written as DMX against
   the citizen's compiled skeleton (Source2Viewer's DATA dump of citizen_human_male.vmdl_c).

Run: python Tools/zombie_male_02.py [--lods] [--install] [--preview]. Without --install it only writes
work/rigged_lod*.npz and work/fit.npz; --preview renders them (work/preview_*.png).
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

import kastov_dmx as dmx
import zombie_anims as za

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "Zombies" / "zombie_male_02"
WORK = SRC / "work"
MODEL = "models/zombie/zombie_male_02"
MATERIALS = "materials/zombies/zombie_male_02"
CITIZEN = Path("C:/Program Files (x86)/Steam/steamapps/common/sbox/addons/citizen/Assets/models/citizen_human")
VRF = Path("D:/tmp/hc1-mw22-tools/vrf/Source2Viewer-CLI.exe")
INCH = 0.0254
LOD_SWITCH = [0.0, 15.0, 30.0, 60.0]  # about 19 inches each: LOD1 from 7 m, LOD2 from 14 m, LOD3 from 29 m

# Where the citizen's main joints sit in the scan (metres; Blender's axes as the lods stage leaves them: the zombie
# faces -Y, its left is +X, feet on z = 0). The jeans' crotch is at 0.82 and the citizen's hip joints 0.11 above its
# own; the shoulders' tops at 1.60 (the citizen's 1.45, its neck_0); the neck narrowest at 1.66. The trunk's joints
# share out pelvis to neck_0 as the citizen's do.
TRUNK = {"pelvis": (0.005, 0.015, 0.975), "neck_0": (0.0, 0.03, 1.60), "head": (0.0, 0.0, 1.69)}
FIT = {
    # Arms: the elbow above the forearm's widest (1.14-1.22), the wrist at its narrowest (1.04).
    "clavicle_L": (0.02, 0.03, 1.53), "arm_upper_L": (0.225, 0.04, 1.52), "arm_lower_L": (0.302, 0.04, 1.245),
    "hand_L": (0.36, -0.04, 1.04),
    "clavicle_R": (-0.02, 0.03, 1.53), "arm_upper_R": (-0.225, 0.04, 1.52), "arm_lower_R": (-0.303, 0.035, 1.245),
    "hand_R": (-0.36, -0.045, 1.04),
    # Legs: the knee at the back of the knee's hollow (0.55-0.6), the ankle 6 cm in front of the heel, the ball 11 cm
    # behind the toes. The scan stands with its left foot further out.
    "leg_upper_L": (0.105, 0.0, 0.93), "leg_lower_L": (0.192, 0.01, 0.54), "ankle_L": (0.233, 0.07, 0.09),
    "ball_L": (0.268, -0.067, 0.012),
    "leg_upper_R": (-0.095, 0.0, 0.93), "leg_lower_R": (-0.148, 0.017, 0.54), "ankle_R": (-0.195, 0.09, 0.09),
    "ball_R": (-0.228, -0.055, 0.012),
}
GIRTH = 0.95  # the scan is broader and deeper than the citizen
HAND = 0.92   # its hands are bigger
HEAD = 0.95
UNTWIST = {"L": None, "R": None}  # radians about the forearm, worked out from the hands' palms (palm_turn)

SEGMENT = {  # bone: the joint its length runs to
    "clavicle_L": "arm_upper_L", "arm_upper_L": "arm_lower_L", "arm_lower_L": "hand_L",
    "clavicle_R": "arm_upper_R", "arm_upper_R": "arm_lower_R", "arm_lower_R": "hand_R",
    "leg_upper_L": "leg_lower_L", "leg_lower_L": "ankle_L", "ankle_L": "ball_L",
    "leg_upper_R": "leg_lower_R", "leg_lower_R": "ankle_R", "ankle_R": "ball_R",
}
SPINE = ["pelvis", "spine_0", "spine_1", "spine_2", "neck_0", "head"]


@dataclass
class Map:
    """v -> to + linear @ (v - origin): a scan point onto the citizen's rest pose."""
    origin: np.ndarray
    to: np.ndarray
    linear: np.ndarray

    def apply(self, v):
        return self.to + (v - self.origin) @ self.linear.T

    def inverse(self, v):
        return self.origin + (v - self.to) @ np.linalg.inv(self.linear).T


def blender(stage: str, *args) -> None:
    exe = max(Path("C:/Program Files/Blender Foundation").glob("*/blender.exe"))
    subprocess.run([str(exe), "-b", "--factory-startup", "--python", str(ROOT / "Tools" / "zombie_male_02_blender.py"),
                    "--", stage, str(WORK), *map(str, args)], check=True)


def strip_guid(src: Path, dst: Path) -> None:
    """A copy of a compiled resource without its GUID block, which Source2Viewer-CLI can't read."""
    import struct
    data = bytearray(src.read_bytes())
    _, _, _, table_rel, count = struct.unpack_from("<IHHII", data, 0)
    table = 8 + table_rel
    entries = []
    for i in range(count):
        at = table + i * 12
        rel, length = struct.unpack_from("<II", data, at + 4)
        entries.append((bytes(data[at:at + 4]), at + 4 + rel, length))
    kept = [e for e in entries if e[0] != b"GUID"]
    for i, (kind, absolute, length) in enumerate(kept):
        at = table + i * 12
        data[at:at + 4] = kind
        struct.pack_into("<II", data, at + 4, absolute - (at + 4), length)
    for i in range(len(kept), count):
        data[table + i * 12:table + i * 12 + 12] = b"\0" * 12
    struct.pack_into("<I", data, 12, len(kept))
    dst.write_bytes(data)


def engine_skeleton() -> za.Skeleton:
    dump = WORK / "citizen_data.txt"
    if not dump.exists():
        strip_guid(CITIZEN / "citizen_human_male.vmdl_c", WORK / "citizen_human_male.vmdl_c")
        out = subprocess.run([str(VRF), "-i", str(WORK / "citizen_human_male.vmdl_c"), "-b", "DATA"],
                             capture_output=True, text=True, check=True).stdout
        dump.write_text(out, encoding="utf-8")
    return za.read_model_skeleton(dump)


def rotation_between(a, b):
    """The shortest turn taking direction a onto b."""
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    v, c = np.cross(a, b), float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def axis_rotation(axis, angle):
    axis = axis / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


class Fit:
    def __init__(self, cit: dict, skel: za.Skeleton):
        self.bones = list(cit["bones"])
        self.rest = {b: np.asarray(h, float) for b, h in zip(self.bones, cit["heads"])}
        self.parent = {b: (skel.names[skel.parents[skel.index[b]]] if skel.parents[skel.index[b]] >= 0 else None)
                       for b in self.bones}
        self.scan = dict(FIT)
        # The trunk's joints share out pelvis to neck_0 as the citizen's do; the head sits straight above the neck.
        p, n = np.array(TRUNK["pelvis"]), np.array(TRUNK["neck_0"])
        rp, rn = self.rest["pelvis"], self.rest["neck_0"]
        for b in SPINE[:-1]:
            t = (self.rest[b][2] - rp[2]) / (rn[2] - rp[2])
            self.scan[b] = tuple(p + t * (n - p))
        self.scan["head"] = TRUNK["head"]
        self.maps: dict[str, Map] = {}
        for b in SPINE:
            self.maps[b] = self.trunk_map(b)
        for b in SEGMENT:
            self.maps[b] = self.limb_map(b)
        for s in "LR":
            fore = self.maps[f"arm_lower_{s}"]
            self.maps[f"hand_{s}"] = Map(np.array(self.scan[f"hand_{s}"]), self.rest[f"hand_{s}"],
                                         fore.linear_rotation * HAND)
            self.maps[f"ball_{s}"] = Map(np.array(self.scan[f"ball_{s}"]), self.rest[f"ball_{s}"],
                                         self.maps[f"ankle_{s}"].linear)
        # Everything else moves with its parent (twist and helper bones, fingers); the IK and aim bones under the root
        # stay put (none of them has weights).
        for b in self.bones:
            chain = b
            while chain not in self.maps and self.parent[chain] is not None:
                chain = self.parent[chain]
            self.maps[b] = self.maps.get(chain) or Map(self.rest[chain], self.rest[chain], np.eye(3))

    def trunk_map(self, b: str) -> Map:
        i = SPINE.index(b)
        if b == "head":
            linear = np.eye(3) * HEAD
        else:
            above = SPINE[i + 1]
            stretch = (self.rest[above][2] - self.rest[b][2]) / (self.scan[above][2] - self.scan[b][2])
            linear = np.diag([GIRTH, GIRTH, stretch])
        return Map(np.array(self.scan[b]), self.rest[b], linear)

    def limb_map(self, b: str) -> Map:
        c = SEGMENT[b]
        a = np.array(self.scan[c]) - np.array(self.scan[b])
        r = self.rest[c] - self.rest[b]
        rot = rotation_between(a, r)
        u = a / np.linalg.norm(a)
        # Along the segment: the citizen's length; across it: GIRTH.
        scale = GIRTH * np.eye(3) + (np.linalg.norm(r) / np.linalg.norm(a) - GIRTH) * np.outer(u, u)
        m = Map(np.array(self.scan[b]), self.rest[b], rot @ scale)
        m.linear_rotation = rot
        return m


def palm_normal(v: np.ndarray, side: str, fit: Fit) -> np.ndarray:
    """The scan's palm: the flattest direction of the hand between the wrist and the knuckles, towards the side the
    fingers curl to."""
    wrist = np.array(fit.scan[f"hand_{side}"])
    elbow = np.array(fit.scan[f"arm_lower_{side}"])
    axis = (wrist - elbow) / np.linalg.norm(wrist - elbow)
    d = v - wrist
    along = d @ axis
    across = np.linalg.norm(d - np.outer(along, axis), axis=1)
    plate = v[(along > 0.03) & (along < 0.10) & (across < 0.07)]
    tips = v[(along > 0.15) & (along < 0.24) & (across < 0.08)]
    centre = plate.mean(0)
    _, _, vt = np.linalg.svd(plate - centre)
    n = vt[2] - np.dot(vt[2], axis) * axis
    n /= np.linalg.norm(n)
    return n if np.dot(tips.mean(0) - centre, n) > 0 else -n


def citizen_palm(fit: Fit, side: str) -> np.ndarray:
    """The citizen's palm at rest (towards the palm from the back of the hand)."""
    h, i, p = (fit.rest[f"{n}_{side}"] for n in ("hand", "finger_index_0", "finger_pinky_0"))
    n = np.cross(i - h, p - h) if side == "L" else np.cross(p - h, i - h)
    return -n / np.linalg.norm(n)


def untwist(v: np.ndarray, turns: np.ndarray, fit: Fit, side: str, angle: float, near: np.ndarray) -> np.ndarray:
    """v with side's forearm turned about its axis by angle, ramping in from the elbow to the wrist; each vertex's
    turn is also applied to turns (V, 3, 3), for the normals."""
    elbow = np.array(fit.scan[f"arm_lower_{side}"])
    wrist = np.array(fit.scan[f"hand_{side}"])
    axis = wrist - elbow
    length = np.linalg.norm(axis)
    axis /= length
    t = np.clip(((v - elbow) @ axis) / length, 0, 1)
    ramp = t * t * (3 - 2 * t)
    out = v.copy()
    for i in np.nonzero(near & (t > 0))[0]:
        turn = axis_rotation(axis, angle * ramp[i])
        out[i] = elbow + turn @ (v[i] - elbow)
        turns[i] = turn @ turns[i]
    return out


def arm_vertices(v: np.ndarray, side: str) -> np.ndarray:
    """The scan's arm below the armpit, where it hangs clear of the trunk (the fingertips reach 0.80; the feet,
    turned out, are as wide)."""
    x = v[:, 0] if side == "L" else -v[:, 0]
    return (x > 0.26) & (v[:, 2] < 1.27) & (v[:, 2] > 0.7)


LIMB_SETS = {
    "arm": ("clavicle", "arm_upper", "arm_lower", "arm_elbow_helper", "hand", "finger"),
    "forearm": ("arm_lower", "arm_elbow_helper", "hand", "finger"),
    "leg": ("leg_upper", "leg_lower", "ankle", "ball", "leg_knee_helper"),
}


def member(bone: str, kind: str, side: str) -> bool:
    sided = bone.endswith(f"_{side}") or f"_{side}_" in bone
    return sided and any(bone.startswith(p) for p in LIMB_SETS[kind])


def allowed(v: np.ndarray, sample_bone: np.ndarray, bones: list[str]) -> list[tuple[np.ndarray, np.ndarray]]:
    """(scan vertices, the citizen surface samples they may take weights from): a hanging arm only from its own arm,
    everything else from neither forearm nor hand, and each leg below the crotch not from the other leg."""
    kind = {(k, s): np.array([member(bones[b], k, s) for b in sample_bone]) for k in LIMB_SETS for s in "LR"}
    arms = {s: arm_vertices(v, s) for s in "LR"}
    legs = {"L": (v[:, 0] > 0.02) & (v[:, 2] < 0.78), "R": (v[:, 0] < -0.02) & (v[:, 2] < 0.78)}
    rest = ~(arms["L"] | arms["R"])
    trunk = ~(kind[("forearm", "L")] | kind[("forearm", "R")])
    return [(arms["L"], kind[("arm", "L")]), (arms["R"], kind[("arm", "R")]),
            (rest & legs["L"], trunk & ~kind[("leg", "R")]), (rest & legs["R"], trunk & ~kind[("leg", "L")]),
            (rest & ~legs["L"] & ~legs["R"], trunk)]


def surface_samples(pos, tris, weights):
    """Points over each triangle (corners, edge midpoints, centre and between) with their interpolated weights."""
    bary = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [.5, .5, 0], [0, .5, .5], [.5, 0, .5], [1 / 3, 1 / 3, 1 / 3],
                     [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])
    p = np.einsum("sk,tkd->tsd", bary, pos[tris]).reshape(-1, 3)
    w = np.einsum("sk,tkb->tsb", bary, weights[tris]).reshape(-1, weights.shape[1])
    return p, w


def citizen_weights(cit: dict) -> np.ndarray:
    cw = cit["weights"].astype(float)
    return cw / np.maximum(cw.sum(1, keepdims=True), 1e-9)


def citizen_in_scan(cit: dict, fit: Fit) -> np.ndarray:
    """The citizen's body carried into the scan's shape: each vertex by its bones' inverse maps, blended."""
    cw = citizen_weights(cit)
    shaped = np.zeros_like(cit["positions"], dtype=float)
    for j, b in enumerate(fit.bones):
        if cw[:, j].any():
            shaped += cw[:, j:j + 1] * fit.maps[b].inverse(cit["positions"].astype(float))
    return shaped


def transfer(v, tris, fit: Fit, cit: dict) -> np.ndarray:
    bones = fit.bones
    sp, sw = surface_samples(citizen_in_scan(cit, fit), cit["triangles"], citizen_weights(cit))
    dominant = sw.argmax(1)
    out = np.zeros((len(v), len(bones)))
    for verts, samples in allowed(v, dominant, bones):
        if not verts.any():
            continue
        idx = np.nonzero(samples)[0]
        _, nearest = cKDTree(sp[idx]).query(v[verts])
        out[verts] = sw[idx[nearest]]
    # Smooth over the scan's own mesh, so neighbours that found different citizen triangles agree.
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    for _ in range(3):
        acc = np.zeros_like(out)
        count = np.zeros(len(v))
        np.add.at(acc, edges[:, 0], out[edges[:, 1]])
        np.add.at(acc, edges[:, 1], out[edges[:, 0]])
        np.add.at(count, edges[:, 0], 1)
        np.add.at(count, edges[:, 1], 1)
        out = 0.5 * out + 0.5 * acc / np.maximum(count, 1)[:, None]
    # Fingers are rigid with the hand.
    for j, b in enumerate(bones):
        if b.startswith("finger_"):
            out[:, bones.index(f"hand_{b[-1]}")] += out[:, j]
            out[:, j] = 0
    # Four bones at most per vertex.
    keep = np.argsort(-out, axis=1)[:, :4]
    limited = np.zeros_like(out)
    rows = np.arange(len(v))[:, None]
    limited[rows, keep] = out[rows, keep]
    limited[limited < 0.01] = 0
    return limited / limited.sum(1, keepdims=True)


def warp(v, weights, fit: Fit):
    """The scan onto the citizen's rest pose."""
    out = np.zeros_like(v)
    for j, b in enumerate(fit.bones):
        if weights[:, j].any():
            out += weights[:, j:j + 1] * fit.maps[b].apply(v)
    return out


def warp_normals(normals, corner_vertex, turns, weights, fit: Fit):
    """Per-corner normals (T, 3, 3) through each vertex's untwist (turns) and its blended map."""
    linear = np.zeros((len(weights), 3, 3))
    for j, b in enumerate(fit.bones):
        if weights[:, j].any():
            linear += weights[:, j, None, None] * fit.maps[b].linear
    m = np.transpose(np.linalg.inv(linear), (0, 2, 1)) @ turns
    n = np.einsum("cij,cj->ci", m[corner_vertex.reshape(-1)], normals.reshape(-1, 3))
    return (n / np.linalg.norm(n, axis=1, keepdims=True)).reshape(normals.shape)


def to_model(p, scale=1 / INCH):
    """Blender metres (faces -Y, left +X) -> model inches (faces +X, left +Y); scale=1 for directions."""
    p = np.asarray(p)
    return np.stack([-p[..., 1], p[..., 0], p[..., 2]], -1) * scale


def build(args) -> None:
    if args.lods or not (WORK / "lod0.npz").exists():
        blender("lods", SRC)
    if not (WORK / "citizen.npz").exists():
        blender("citizen", CITIZEN / "citizen_human_male_REF.fbx")
    cit = dict(np.load(WORK / "citizen.npz"))
    skel = engine_skeleton()
    fit = Fit(cit, skel)
    lod0 = np.load(WORK / "lod0.npz")
    for s in "LR":
        palm = palm_normal(lod0["positions"].astype(float), s, fit)
        # The citizen's palm, carried by the forearm's turn back into the scan.
        target = fit.maps[f"arm_lower_{s}"].linear_rotation.T @ citizen_palm(fit, s)
        axis = np.array(fit.scan[f"hand_{s}"]) - np.array(fit.scan[f"arm_lower_{s}"])
        axis /= np.linalg.norm(axis)
        target -= np.dot(target, axis) * axis
        target /= np.linalg.norm(target)
        UNTWIST[s] = float(np.arctan2(np.dot(np.cross(palm, target), axis), np.dot(palm, target)))
        print(f"{s} forearm untwist {np.degrees(UNTWIST[s]):.0f} degrees (scan palm {np.round(palm, 2)})")
    rigged = {}
    for i in range(len(LOD_SWITCH)):
        lod = np.load(WORK / f"lod{i}.npz")
        v = lod["positions"].astype(float)
        tris = lod["triangles"]
        turns = np.tile(np.eye(3), (len(v), 1, 1))
        for s in "LR":
            v = untwist(v, turns, fit, s, UNTWIST[s], arm_vertices(v, s))
        weights = transfer(v, tris, fit, cit)
        rigged[i] = dict(scan=v, rest=warp(v, weights, fit), weights=weights, triangles=tris, uvs=lod["uvs"],
                         normals=warp_normals(lod["normals"].astype(float), tris, turns, weights, fit))
        np.savez(WORK / f"rigged_lod{i}.npz", bones=np.array(fit.bones), **rigged[i])
        print(f"lod{i}: {len(tris)} triangles, {len(v)} vertices")
    np.savez(WORK / "fit.npz", bones=np.array(fit.bones), citizen_shaped=citizen_in_scan(cit, fit),
             scan_heads=np.array([fit.maps[b].inverse(fit.rest[b][None])[0] for b in fit.bones]))
    if args.install:
        install(rigged, fit, skel)
    if args.preview:
        preview(skel)


def install(rigged: dict, fit: Fit, skel: za.Skeleton) -> None:
    nodes = list(zip(skel.names, skel.parents))
    bone_index = {b: skel.names.index(b) for b in fit.bones}
    out_dir = ROOT / "Assets" / MODEL
    out_dir.mkdir(parents=True, exist_ok=True)
    mat_dir = ROOT / "Assets" / MATERIALS
    mat_dir.mkdir(parents=True, exist_ok=True)
    for i, r in rigged.items():
        material = f"{MATERIALS}/lod{i}.vmat"
        mp, mn, w = to_model(r["rest"]), to_model(r["normals"], 1.0), r["weights"]
        links = [[(bone_index[fit.bones[j]], w[vi, j]) for j in np.nonzero(w[vi])[0]] for vi in range(len(w))]
        triangles = [(material, [(mp[vi], mn[t, k], r["uvs"][t, k], links[vi]) for k, vi in enumerate(tri)])
                     for t, tri in enumerate(r["triangles"])]
        dmx.write_model(out_dir / f"lod{i}.dmx", f"zombie_male_02_lod{i}", nodes, skel.bind_local, triangles)
        for kind in ("color", "rough", "normal"):
            fill_gaps(WORK / f"lod{i}_{kind}.png", mat_dir / f"lod{i}_{kind}.png", r["uvs"], WORK / f"lod{i}_color.png")
        write_vmat(mat_dir / f"lod{i}.vmat", i)
        print(f"wrote lod{i}", flush=True)
    write_vmdl()


def fill_gaps(src: Path, dst: Path, uvs: np.ndarray, missed: Path) -> None:
    """A baked map with every pixel outside the UV islands taken from the nearest one inside, so the lower mips of
    the islands' 2-pixel gaps don't bleed black at the seams. Pixels whose bake ray found no scan (black in the
    colour map, `missed`) are filled the same way."""
    from PIL import Image, ImageDraw
    from scipy import ndimage
    image = np.asarray(Image.open(src).convert("RGB"))
    h, w = image.shape[:2]
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    for tri in uvs:
        draw.polygon([(u * w, (1 - v) * h) for u, v in tri], fill=255, outline=255)
    good = ndimage.binary_dilation(np.asarray(mask) > 0, iterations=1)
    good &= np.asarray(Image.open(missed).convert("RGB")).sum(2) > 0
    _, (iy, ix) = ndimage.distance_transform_edt(~good, return_indices=True)
    Image.fromarray(image[iy, ix]).save(dst)


def to_blender(p):
    """Model inches -> Blender metres (the inverse of to_model)."""
    p = np.asarray(p)
    return np.stack([p[..., 1], -p[..., 0], p[..., 2]], -1) * INCH


def posed(rest_model, weights, bones, skel: za.Skeleton, world: list[np.ndarray], world_names: list[str]):
    """rest_model (inches) skinned onto a clip frame's bone world transforms."""
    at = {n: i for i, n in enumerate(world_names)}
    out = np.zeros_like(rest_model)
    for j, b in enumerate(bones):
        if weights[:, j].any():
            m = world[at[b]] @ np.linalg.inv(skel.bind_world[skel.index[b]])
            out += weights[:, j:j + 1] * (rest_model @ m[:3, :3].T + m[:3, 3])
    return out


def preview(skel: za.Skeleton) -> None:
    """Renders (work/preview_*.png): the citizen carried into the scan's shape over the scan (the joints' fit), the
    rigged body over the citizen at rest, and the body on the zombie clips."""
    import argparse as ap
    fit = np.load(WORK / "fit.npz")
    cit = np.load(WORK / "citizen.npz")
    r = np.load(WORK / "rigged_lod0.npz")
    bones = list(r["bones"])
    old, ported = za.port_all(ap.Namespace(walk_pack=str(za.WORK / "decompiled/nmrih_3255961963"),
                                           run_pack=str(za.WORK / "decompiled/nmrih_3255991053"),
                                           citizen_data=str(za.WORK / "zombie_work/citizen_human_male_data.txt")))
    clips = {p.clip.name: p for p in ported}
    frames = [("idle", 0), ("walk_a", 0), ("walk_a", 6), ("walk_a", 13), ("run", 5), ("attack_a", None),
              ("attack_c", None), ("attack_e", None)]
    rest_model = to_model(r["rest"])
    data = {"panels": np.array(["fit", "rest", "poses"])}

    def mesh(panel, k, pos, tris, material, uvs=None):
        data[f"{panel}_{k}_pos"] = pos
        data[f"{panel}_{k}_tri"] = tris
        data[f"{panel}_{k}_mat"] = np.array(material)
        if uvs is not None:
            data[f"{panel}_{k}_uv"] = uvs

    mesh("fit", 0, r["scan"], r["triangles"], "lod0", r["uvs"])
    mesh("fit", 1, fit["citizen_shaped"], cit["triangles"], "wire")
    mesh("rest", 0, r["rest"], r["triangles"], "lod0", r["uvs"])
    mesh("rest", 1, cit["positions"], cit["triangles"], "wire")
    for k, (name, frame) in enumerate(frames):
        p = clips[name]
        f = frame if frame is not None else min(int(round(p.hit * p.fps)), len(p.world) - 1)
        pos = to_blender(posed(rest_model, r["weights"], bones, skel, p.world[f], old.names))
        mesh("poses", k, pos + np.array([0.9 * k, 0, 0]), r["triangles"], "lod0", r["uvs"])
    np.savez(WORK / "preview.npz", **data)
    blender("preview")


def write_vmat(path: Path, lod: int) -> None:
    path.write_text(
        "// Generated by Tools/zombie_male_02.py\n\n"
        "Layer0\n{\n"
        '\tshader "shaders/complex.shader"\n\n'
        "\t//---- Color ----\n"
        '\tg_flModelTintAmount "1.000"\n'
        '\tg_vColorTint "[1.000000 1.000000 1.000000 0.000000]"\n'
        f'\tTextureColor "{MATERIALS}/lod{lod}_color.png"\n\n'
        "\t//---- Fog ----\n"
        '\tg_bFogEnabled "1"\n\n'
        "\t//---- Normal ----\n"
        f'\tTextureNormal "{MATERIALS}/lod{lod}_normal.png"\n\n'
        "\t//---- Roughness ----\n"
        '\tg_flRoughnessScaleFactor "1.000"\n'
        f'\tTextureRoughness "{MATERIALS}/lod{lod}_rough.png"\n'
        "}\n", encoding="utf-8", newline="\n")


def write_vmdl() -> None:
    meshes = "".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{MODEL}/lod{i}.dmx" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        "import_filter = { exclude_by_default = false exception_list = [ ] } },\n" for i in range(len(LOD_SWITCH)))
    lods = "".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{i}" ] }},\n'
                   for i, t in enumerate(LOD_SWITCH))
    text = (
        "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} "
        "format:modeldoc30:version{8c2d7a91-9c42-4bf0-883a-5a3b1762d4f1} -->\n"
        "// Generated by Tools/zombie_male_02.py: a Zombies body, bone-merged onto models/zombie/zombie_driver.vmdl\n"
        "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
        "\t\t\t{ _class = \"BoneMarkupList\" bone_cull_type = \"None\" },\n"
        "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + meshes + "\t\t\t\t]\n\t\t\t},\n"
        "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + lods + "\t\t\t\t]\n\t\t\t},\n"
        "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n"
        "\t\tbase_model_name = \"\"\n\t}\n}\n")
    (ROOT / "Assets" / f"{MODEL}.vmdl").write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lods", action="store_true", help="decimate and bake the LODs again")
    parser.add_argument("--install", action="store_true", help="write the model and materials into Assets")
    parser.add_argument("--preview", action="store_true", help="render the fit, the rest pose and the clips")
    build(parser.parse_args())


if __name__ == "__main__":
    main()
