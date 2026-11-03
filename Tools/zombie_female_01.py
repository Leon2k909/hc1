"""Make the Zombies mode's second zombie type: a woman in a blouse, a skirt and heeled knee boots (zombie_female_01).

The source is a Meshy AI scan (C:/Users/leon2/Desktop/test/zombie2/Meshy_AI_Zombie_hungry_Woman_*.glb): one mesh of
1.88M triangles with no skeleton, 4096 colour and normal maps and a 2048 metal/roughness map. A zombie is an invisible
citizen "driver" playing the zombie clips with the body bone-merged onto it (ZombiesRoundSystem.SpawnZombie), so the
body has to be skinned to the citizen's own skeleton in the citizen's own rest pose: bone merge puts each of its bones
where the driver's is.

Stages (python Tools/zombie_female_01.py <stage>):
  lods      Blender (zombie_female_01_blender.py): decimate to LODS (36k, 18k, 8k triangles) with the scan's UVs,
            and bake what LOD0 loses (and the scan's normal map) into LOD0's normal map.
  citizen   Blender: the citizen's reference body (citizen_human_male_REF.fbx), with its bone weights.
  atlas     Blender (zombie_female_01_atlas.py): a continuous facial UV chart and rebaked PBR textures.
  textures  Install the repaired atlas (4096 colour, 2048 normal/roughness).
  rig       Fit, skin and warp each LOD, and write the DMX, vmdl and vmat to Assets/models/zombie/zombie_female_01/.
  preview   Her LOD0 on sample frames of the driver's clips, rendered in Blender.

The rig:
  - Her pose (`JOINTS`, measured from gridded renders and horizontal slices of the scan) is the citizen's skeleton
    bent to her: she stands with her weight on her right leg, the left leg out to the side and its knee bent a
    little, her hips turned 28 degrees to her right and her shoulders 18, the head facing forward, the arms hanging
    with the palms to the thighs.
  - Each citizen bone gets an affine map D from the citizen's rest pose to her pose (`deformations`): turned to her
    bone's direction, stretched along the bone to her bone's length, and moved to her joint. The trunk's and the
    head's turn come from their side-to-side lines; the limbs carry their parent's turn down the chain, except the
    thighs, which take their twist from her feet (both point forward), so her knees bend over her toes. Bones that
    aren't fitted (twist bones, fingers, helpers) move with their parent.
  - Her boots' heels are 12 cm high, and the citizen's ankle is 9 cm off the floor against her 16: a foot turned
    rigidly onto the citizen's would put the heel through the floor. So the ankle's and the ball's maps are affine
    fits of her ankle, ball, toe tip and heel tip onto the citizen's flat foot: in game she wears lower heels.
  - Weights: the citizen's body, moved into her pose by the same maps, gives its weights where it lies within
    `NEAR` of her surface and faces the same way (within `FACING`); the rest of her (hair, the flared skirt, the
    sleeves' edges) is filled in smoothly from there over her surface (a harmonic fill, as in Abdrashitov et al.,
    "Robust Skin Weights Transfer via Weight Inpainting", 2023). Hair takes no arm weights. Four bones at most.
  - Her mesh is then taken back through the weighted maps (each vertex by the inverse of its blend), which puts her
    into the citizen's rest pose on the citizen's joints. LOD1-3 take their weights from LOD0.
  - `SCALE` (inches per scan unit) sets her girth against the citizen's joints; lengths are the citizen's.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kastov_dmx as dmx  # noqa: E402
import zombie_anims as za  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = Path("D:/tmp/hc1-mw22-tools/zombie_female_01_work")
SCAN = Path("C:/Users/leon2/Desktop/test/zombie2/Meshy_AI_Zombie_hungry_Woman_1103182602_texture.glb")
CITIZEN_FBX = Path("C:/Program Files (x86)/Steam/steamapps/common/sbox/addons/citizen/Assets/models/citizen_human/"
                   "citizen_human_male_REF.fbx")
CITIZEN_DATA = Path("D:/tmp/hc1-mw22-tools/zombie_work/citizen_human_male_data.txt")
BLENDER = Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
ASSET_DIR = "models/zombie/zombie_female_01"
NAME = "zombie_female_01"
LOD_COUNT = 3
USE_ATLAS = True
# LOD switch thresholds: about 19 inches each at 1080p and 90 degrees (props-from-a-distance notes): LOD1 from ~14 m,
# LOD2 from ~29 m.
LOD_THRESHOLDS = [0.0, 30.0, 60.0]

SCALE = 37.0  # inches per scan unit (she is 1.90 units tall in her heels and hair, so about 5' 9" in bare feet)
NEAR = 1.4    # inches: the citizen's surface gives its weights to hers within this
FACING = np.cos(np.radians(40.0))
SMOOTH = 3    # passes of weight smoothing after the fill
MAX_LINKS = 4

# Her joints in the scan's Blender axes (she faces -Y, her left is +X, feet on z = 0), in scan units. The limbs' are
# the centres of their outlines in horizontal slices; the rest are read off gridded front and side renders.
JOINTS = {
    "neck_0": (0.025, -0.010, 1.600),
    "head": (0.030, -0.030, 1.688),
    "arm_upper_R": (-0.150, 0.100, 1.500), "arm_upper_L": (0.215, -0.015, 1.500),
    "arm_lower_R": (-0.205, 0.105, 1.200), "arm_lower_L": (0.278, -0.025, 1.220),
    "hand_R": (-0.282, -0.012, 0.990), "hand_L": (0.272, -0.125, 1.000),
    "finger_middle_0_R": (-0.300, -0.033, 0.915), "finger_middle_0_L": (0.265, -0.148, 0.915),
    "leg_lower_R": (-0.113, 0.030, 0.560), "leg_lower_L": (0.145, -0.108, 0.560),
    "ankle_R": (-0.110, 0.045, 0.165), "ankle_L": (0.250, -0.022, 0.165),
    "ball_R": (-0.132, -0.075, 0.025), "ball_L": (0.272, -0.128, 0.025),
}
TOES = {"R": (-0.140, -0.150, 0.020), "L": (0.282, -0.210, 0.020)}
HEELS = {"R": (-0.110, 0.076, 0.000), "L": (0.256, 0.029, 0.000)}  # the heels' tips
# The hips' centre, and the line through the thighs' centres 17 cm below the hips (right thigh to left).
HIPS = (0.000, -0.020, 0.950)
HIP_LINE = (0.213, -0.113, 0.0)
# Her left eye's height against her right's gives the head's tilt; the face looks straight out (-Y).
HEAD_SIDE = (1.0, 0.0, -0.17)
HEAD_FORWARD = (0.0, -1.0, 0.0)

ARM_BONES = ("clavicle", "arm_", "hand_", "finger_")
WAIST = 1.24      # scan units: the blouse's hem; below it the hands hang against the skirt
WARM = 15.0       # red less blue in the colour map (0-255) above which a vertex is skin
ARM_REACH = 0.07  # scan units from her forearm's, hand's and fingers' lines that an arm's skin can be
STRETCH = 2.5     # an edge that grows past this many times its scanned length...
WELD = 2.0        # ...and by more than this (inches) belongs to a weld (`unstretched`)
HEAD_BASE = 1.54  # scan units: blend the neck into the head below the jaw
HEAD_RIGID = 1.61 # face/scalp move rigidly; transferred torso weights otherwise fold the cheeks in the rest pose


# ── Geometry ────────────────────────────────────────────────────────────────────

def to_model(p) -> np.ndarray:
    """Scan (Blender axes, units) -> model space (+X forward, +Y left, inches)."""
    p = np.asarray(p, float)
    return SCALE * np.stack([-p[..., 1], p[..., 0], p[..., 2]], axis=-1)


def unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(primary, secondary) -> np.ndarray:
    a = unit(primary)
    b = unit(secondary - a * np.dot(a, secondary))
    return np.column_stack([a, b, np.cross(a, b)])


def rotation_between(a, b) -> np.ndarray:
    return za.rotation_between(unit(a), unit(b))


def affine(origin_from, origin_to, linear) -> np.ndarray:
    m = np.eye(4)
    m[:3, :3] = linear
    m[:3, 3] = origin_to - linear @ origin_from
    return m


def vertex_normals(positions: np.ndarray, tris: np.ndarray) -> np.ndarray:
    face = np.cross(positions[tris[:, 1]] - positions[tris[:, 0]], positions[tris[:, 2]] - positions[tris[:, 0]])
    n = np.zeros_like(positions)
    for k in range(3):
        np.add.at(n, tris[:, k], face)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def surface_samples(positions: np.ndarray, tris: np.ndarray, steps: int = 6):
    """Points spread over each triangle, with their triangle and barycentric coordinates."""
    bary = np.array([(i, j, steps - i - j) for i in range(steps + 1) for j in range(steps + 1 - i)], float) / steps
    pts = np.einsum("sk,tkd->tsd", bary, positions[tris]).reshape(-1, 3)
    tri_of = np.repeat(np.arange(len(tris)), len(bary))
    return pts, tri_of, np.tile(bary, (len(tris), 1))


def adjacency(n: int, tris: np.ndarray) -> sparse.csr_matrix:
    i = np.concatenate([tris[:, 0], tris[:, 1], tris[:, 2], tris[:, 1], tris[:, 2], tris[:, 0]])
    j = np.concatenate([tris[:, 1], tris[:, 2], tris[:, 0], tris[:, 0], tris[:, 1], tris[:, 2]])
    a = sparse.coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)).tocsr()
    a.data[:] = 1.0
    return a


# ── Inputs ──────────────────────────────────────────────────────────────────────

def load_lod(i: int) -> dict:
    d = np.load(WORK / f"{'atlas_' if USE_ATLAS else ''}lod{i}.npz")
    return {k: d[k] for k in d.files}


def load_citizen(cit: za.Skeleton) -> dict:
    """The citizen's reference body in model space, with its weights over cit's bones."""
    d = np.load(WORK / "citizen.npz")
    bones = list(d["bones"])
    # The FBX's bone heads against the skeleton's: a similarity (39.37 and a quarter turn), fitted to be exact.
    a = d["heads"]
    b = np.array([cit.bind_world[cit.index[n]][:3, 3] for n in bones])
    ma, mb = a.mean(0), b.mean(0)
    u, s, vt = np.linalg.svd((a - ma).T @ (b - mb))
    r = (u @ vt).T
    scale = s.sum() / ((a - ma) ** 2).sum()
    t = mb - scale * r @ ma
    err = np.abs((scale * (r @ a.T)).T + t - b).max()
    assert err < 0.01, err
    pos = (scale * (r @ d["positions"].T)).T + t
    w = np.zeros((len(pos), len(cit.names)))
    for k, n in enumerate(bones):
        w[:, cit.index[n]] = d["weights"][:, k]
    w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
    return {"positions": pos, "triangles": d["triangles"], "weights": w}


# ── The fit ─────────────────────────────────────────────────────────────────────

def her_joints(cit: za.Skeleton) -> dict[str, np.ndarray]:
    """Her joints in model space, the measured ones plus those placed by the citizen's proportions."""
    j = {k: to_model(v) for k, v in JOINTS.items()}
    cw = {n: cit.bind_world[cit.index[n]][:3, 3] for n in cit.names}
    hips = to_model(HIPS)
    side = unit(to_model(HIP_LINE) / SCALE)
    half = np.linalg.norm(cw["leg_upper_L"] - cw["leg_upper_R"]) / 2
    j["leg_upper_L"], j["leg_upper_R"] = hips + half * side, hips - half * side
    # The pelvis stands above the hips' line as far as the citizen's does.
    j["pelvis"] = hips + (cw["pelvis"] - (cw["leg_upper_L"] + cw["leg_upper_R"]) / 2)
    # The spine's joints at the citizen's fractions of the way from the pelvis to the neck.
    for n in ("spine_0", "spine_1", "spine_2"):
        t = (cw[n][2] - cw["pelvis"][2]) / (cw["neck_0"][2] - cw["pelvis"][2])
        j[n] = j["pelvis"] + t * (j["neck_0"] - j["pelvis"])
    # The clavicles start below the neck as the citizen's do, on her shoulders' line.
    shoulders = unit(j["arm_upper_L"] - j["arm_upper_R"])
    for s, sign in (("L", 1), ("R", -1)):
        drop = cw["neck_0"][2] - cw[f"clavicle_{s}"][2]
        out = abs(cw[f"clavicle_{s}"][1])
        j[f"clavicle_{s}"] = j["neck_0"] + np.array([0, 0, -drop]) + sign * out * shoulders
    return j


def citizen_foot(cit_body: dict, cw: dict, side: str) -> tuple[np.ndarray, np.ndarray]:
    """The citizen's toe tip and the back of its heel on the floor."""
    p = cit_body["positions"]
    y = cw[f"ankle_{side}"][1]
    near = p[(np.abs(p[:, 1] - y) < 1.5) & (p[:, 2] < 1.5)]
    toe = near[np.argmax(near[:, 0])]
    heel = near[np.argmin(near[:, 0])]
    return np.array([toe[0], y, 0.5]), np.array([heel[0] + 0.6, y, 0.0])


def deformations(cit: za.Skeleton, cit_body: dict) -> list[np.ndarray]:
    """Per bone, the affine map from the citizen's rest pose to her pose (model space)."""
    j = her_joints(cit)
    cw = {n: cit.bind_world[cit.index[n]][:3, 3] for n in cit.names}
    q: dict[str, np.ndarray] = {}
    d: dict[str, np.ndarray] = {}

    def fit(name: str, rot: np.ndarray, child: str | None, extra: np.ndarray | None = None):
        q[name] = rot
        lin = rot.copy()
        if child:
            a = unit(cw[child] - cw[name])
            s = np.linalg.norm(j[child] - j[name]) / np.linalg.norm(cw[child] - cw[name])
            lin = rot @ (np.eye(3) + (s - 1) * np.outer(a, a))
        if extra is not None:
            lin = lin @ extra
        d[name] = affine(cw[name], j[name], lin)

    def chain(name: str, parent_rot: np.ndarray, child: str):
        rot = rotation_between(parent_rot @ (cw[child] - cw[name]), j[child] - j[name]) @ parent_rot
        fit(name, rot, child)

    # The trunk: each bone turned to her spine's direction and her side-to-side line, which turns from the hips' 28
    # degrees to the shoulders' 18 on the way up.
    hip_c = cw["leg_upper_L"] - cw["leg_upper_R"]
    hip_h = j["leg_upper_L"] - j["leg_upper_R"]
    sh_c = cw["arm_upper_L"] - cw["arm_upper_R"]
    sh_h = j["arm_upper_L"] - j["arm_upper_R"]
    width = np.linalg.norm(hip_h) / np.linalg.norm(hip_c)
    side = unit(hip_c)
    fit("pelvis", frame(j["spine_0"] - j["pelvis"], hip_h) @ frame(cw["spine_0"] - cw["pelvis"], hip_c).T, "spine_0",
        np.eye(3) + (width - 1) * np.outer(side, side))
    trunk = [("spine_0", "spine_1", 0.25), ("spine_1", "spine_2", 0.55), ("spine_2", "neck_0", 0.85),
             ("neck_0", "head", 1.0)]
    for name, child, t in trunk:
        lat_h = (1 - t) * unit(hip_h) + t * unit(sh_h)
        lat_c = (1 - t) * unit(hip_c) + t * unit(sh_c)
        fit(name, frame(j[child] - j[name], lat_h) @ frame(cw[child] - cw[name], lat_c).T, child)
    # The head keeps its own size: it is turned to her face and tilted as her eyes are.
    fit("head", frame(to_model(HEAD_FORWARD) / SCALE, to_model(HEAD_SIDE) / SCALE)
        @ frame(np.array([1.0, 0, 0]), np.array([0, 1.0, 0])).T, None)

    for s in "LR":
        chain(f"clavicle_{s}", q["spine_2"], f"arm_upper_{s}")
        chain(f"arm_upper_{s}", q[f"clavicle_{s}"], f"arm_lower_{s}")
        chain(f"arm_lower_{s}", q[f"arm_upper_{s}"], f"hand_{s}")
        # The hand keeps its size: its line to the middle knuckle only turns it.
        rot = rotation_between(q[f"arm_lower_{s}"] @ (cw[f"finger_middle_0_{s}"] - cw[f"hand_{s}"]),
                               j[f"finger_middle_0_{s}"] - j[f"hand_{s}"]) @ q[f"arm_lower_{s}"]
        fit(f"hand_{s}", rot, None)

        # The thigh's twist comes from her foot: the citizen's foot, turned about the vertical, points where hers does.
        foot_c = cw[f"ball_{s}"] - cw[f"ankle_{s}"]
        foot_h = to_model(TOES[s]) - j[f"ankle_{s}"]
        yaw = rotation_between(foot_c * [1, 1, 0], foot_h * [1, 1, 0])
        chain(f"leg_upper_{s}", yaw, f"leg_lower_{s}")
        chain(f"leg_lower_{s}", q[f"leg_upper_{s}"], f"ankle_{s}")

        # The foot: an affine fit of her ankle, ball and heel's tip onto the citizen's ankle, ball and heel, keeping
        # its width. Then the toes: her ball and toe tip onto the citizen's.
        toe_c, heel_c = citizen_foot(cit_body, cw, s)
        lat_c = unit(np.cross([0, 0, 1.0], foot_c * [1, 1, 0]))
        lat_h = unit(np.cross([0, 0, 1.0], foot_h * [1, 1, 0]))
        src = np.column_stack([cw[f"ball_{s}"] - cw[f"ankle_{s}"], heel_c - cw[f"ankle_{s}"], lat_c])
        dst = np.column_stack([j[f"ball_{s}"] - j[f"ankle_{s}"], to_model(HEELS[s]) - j[f"ankle_{s}"], lat_h])
        lin = dst @ np.linalg.inv(src)
        d[f"ankle_{s}"] = affine(cw[f"ankle_{s}"], j[f"ankle_{s}"], lin)
        up_c = unit(np.cross(lat_c, toe_c - cw[f"ball_{s}"]))
        src = np.column_stack([toe_c - cw[f"ball_{s}"], up_c, lat_c])
        dst = np.column_stack([to_model(TOES[s]) - j[f"ball_{s}"], lin @ up_c, lat_h])
        d[f"ball_{s}"] = affine(cw[f"ball_{s}"], j[f"ball_{s}"], dst @ np.linalg.inv(src))

    out = []
    for i, n in enumerate(cit.names):
        if n not in d:
            p = cit.parents[i]
            d[n] = out[p] if p >= 0 else d["pelvis"]
        out.append(d[n])
    return out


def blend(weights: np.ndarray, maps: np.ndarray) -> np.ndarray:
    """Per vertex, the weighted sum of the bones' 4x4 maps."""
    return np.einsum("vb,bij->vij", weights, maps)


def apply(m: np.ndarray, p: np.ndarray) -> np.ndarray:
    return np.einsum("vij,vj->vi", m[:, :3, :3], p) + m[:, :3, 3]


# ── Weights ─────────────────────────────────────────────────────────────────────

def nearest_on(src_pos, src_tris, dst_pos, src_class=None, dst_class=None):
    """Nearest point of the source surface to each destination vertex (its distance, triangle and barycentric
    coordinates). With classes, a vertex of class c > 0 looks only at triangles of class c, and one of class 0 at all."""
    pts, tri_of, bary = surface_samples(src_pos, src_tris)
    dist = np.empty(len(dst_pos))
    idx = np.empty(len(dst_pos), int)
    groups = [(None, None)] if src_class is None else [(c, c) for c in np.unique(dst_class)]
    for sc, dc in groups:
        pick = np.ones(len(pts), bool) if not sc else src_class[src_tris[tri_of, 0]] == sc
        who = np.ones(len(dst_pos), bool) if dc is None else dst_class == dc
        where = np.flatnonzero(pick)
        d, i = cKDTree(pts[where]).query(dst_pos[who])
        dist[who], idx[who] = d, where[i]
    return dist, tri_of[idx], bary[idx]


def transfer(src_pos, src_tris, src_w, dst_pos, dst_tris, near: float | None = None, facing: float | None = None,
             keep=None, src_class=None, dst_class=None):
    """Weights from the nearest point of the source surface. With near/facing, only where it is that close and faces
    the same way (and keep(w) leaves something), the rest filled in harmonically over the destination's surface."""
    dist, t, bary = nearest_on(src_pos, src_tris, dst_pos, src_class, dst_class)
    w = np.einsum("vk,vkb->vb", bary, src_w[src_tris[t]])
    if near is None:
        return w
    sn = vertex_normals(src_pos, src_tris)
    sn_at = unit_rows(np.einsum("vk,vkd->vd", bary, sn[src_tris[t]]))
    dn = vertex_normals(dst_pos, dst_tris)
    known = (dist < near) & (np.einsum("vd,vd->v", sn_at, dn) > facing)
    if keep is not None:
        w, left = keep(w)
        known &= left
    adj = adjacency(len(dst_pos), dst_tris)
    # Pieces of her surface that nothing reached keep their nearest weights.
    n_comp, comp = connected_components(adj, directed=False)
    for c in range(n_comp):
        members = comp == c
        if not known[members].any():
            known |= members
    print(f"  weights: {known.mean():.0%} of {len(dst_pos)} vertices from the citizen, "
          f"{n_comp} pieces, the rest filled")
    lap = sparse.diags(np.asarray(adj.sum(1)).ravel()) - adj
    u = np.flatnonzero(~known)
    k = np.flatnonzero(known)
    if len(u):
        solve = splu(lap[u][:, u].tocsc())
        w[u] = solve.solve(-(lap[u][:, k] @ w[k]))
    return np.clip(w, 0, None)


def unit_rows(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)


def smooth(w: np.ndarray, tris: np.ndarray, passes: int) -> np.ndarray:
    adj = adjacency(len(w), tris)
    deg = np.asarray(adj.sum(1)).ravel()[:, None]
    for _ in range(passes):
        w = 0.5 * w + 0.5 * (adj @ w) / np.maximum(deg, 1)
    return w


def prune(w: np.ndarray, links: int) -> np.ndarray:
    keep = np.argsort(-w, axis=1)[:, :links]
    out = np.zeros_like(w)
    rows = np.arange(len(w))[:, None]
    out[rows, keep] = w[rows, keep]
    out[out < 0.02] = 0
    return out / out.sum(1, keepdims=True)


def stabilize_head(w: np.ndarray, positions: np.ndarray, cit: za.Skeleton) -> np.ndarray:
    """Keep the scanned face rigid, with a smooth neck transition. Nearest-body transfer can borrow neck/chest
    weights even around the eyes; inverting those varying affine blends folds the face over itself."""
    t = np.clip((positions[:, 2] - HEAD_BASE) / (HEAD_RIGID - HEAD_BASE), 0, 1)
    t = t * t * (3 - 2 * t)
    out = w * (1 - t[:, None])
    out[:, cit.index["head"]] += t
    return prune(out, MAX_LINKS)


def vertex_colours(lod: dict, color: np.ndarray) -> np.ndarray:
    """The colour map's mean over each vertex's corners (0-255)."""
    h, wd = color.shape[:2]
    uv = lod["uvs"].reshape(-1, 2)
    px = np.clip((uv[:, 0] % 1) * (wd - 1), 0, wd - 1).astype(int)
    py = np.clip((1 - uv[:, 1] % 1) * (h - 1), 0, h - 1).astype(int)
    out = np.zeros((len(lod["positions"]), 3))
    count = np.zeros(len(lod["positions"]))
    for k in range(3):
        np.add.at(out[:, k], lod["triangles"].ravel(), color[py, px, k])
    np.add.at(count, lod["triangles"].ravel(), 1)
    return out / np.maximum(count, 1)[:, None]


def segment_distance(p: np.ndarray, a, b) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    t = np.clip(((p - a) @ (b - a)) / ((b - a) @ (b - a)), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * (b - a)), axis=1)


def regions(lod: dict, color: np.ndarray) -> np.ndarray:
    """Below the waist (WAIST), each vertex is her left arm (1), her right arm (2) or her body (3); above it, 0.
    Her hands hang against the skirt and the scan welds them to it where they touch. Skin is warm in the colour map
    (red less blue 30-56 on the hands and forearms) and the skirt isn't (about -2): an arm is warm skin near its
    forearm, hand and fingers."""
    p = lod["positions"]
    c = vertex_colours(lod, color)
    warm = c[:, 0] - c[:, 2] > WARM
    out = np.where(p[:, 2] < WAIST, 3, 0)
    for label, s in ((1, "L"), (2, "R")):
        tip = np.array(JOINTS[f"finger_middle_0_{s}"]) + [0, 0, -0.09]
        d = np.minimum.reduce([segment_distance(p, JOINTS[f"arm_lower_{s}"], JOINTS[f"hand_{s}"]),
                               segment_distance(p, JOINTS[f"hand_{s}"], JOINTS[f"finger_middle_0_{s}"]),
                               segment_distance(p, JOINTS[f"finger_middle_0_{s}"], tip)])
        out[(out == 3) & warm & (d < ARM_REACH)] = label
    return out


def hair_mask(lod: dict, color: np.ndarray) -> np.ndarray:
    """Her hair: dark and not warm in the colour map, and above the shoulders' line."""
    c = vertex_colours(lod, color)
    lum = c @ [0.2126, 0.7152, 0.0722] / 255.0
    return (lum < 0.12) & (c[:, 0] - c[:, 2] < WARM) & (lod["positions"][:, 2] > 1.45)


def bone_sets(cit: za.Skeleton) -> dict[str, list[int]]:
    """Each arm's bones below the clavicle (its twist bones carry most of its skin: arm_lower_L_twist0, ...)."""
    def side(n: str, s: str) -> bool:
        return n.endswith(f"_{s}") or f"_{s}_" in n
    arms = {s: [i for i, n in enumerate(cit.names) if n.startswith(ARM_BONES) and side(n, s)
                and not n.startswith("clavicle")] for s in "LR"}
    every_arm = [i for i, n in enumerate(cit.names) if n.startswith(ARM_BONES)]
    return {"L": arms["L"], "R": arms["R"], "arms": every_arm}


def constrain(w: np.ndarray, region: np.ndarray, hair: np.ndarray, cit: za.Skeleton) -> tuple[np.ndarray, np.ndarray]:
    """Arms below the waist take only their own arm's bones, the body there none of the arms', and hair none of the
    arms'. Returns the weights and whether anything was left (a vertex with nothing left is for the fill)."""
    sets = bone_sets(cit)
    w = w.copy()
    for label, s in ((1, "L"), (2, "R")):
        others = np.setdiff1d(np.arange(w.shape[1]), sets[s])
        w[np.ix_(region == label, others)] = 0
    w[np.ix_((region == 3) | hair, sets["arms"])] = 0
    total = w.sum(1)
    left = total > 1e-3
    w[left] /= total[left, None]
    # Nothing left: the region's own bone, until the fill (if it runs) does better.
    for label, bone in ((0, "spine_2"), (1, "hand_L"), (2, "hand_R"), (3, "pelvis")):
        w[~left & (region == label), cit.index[bone]] = 1
    w[~left & hair] = 0
    w[~left & hair, cit.index["head"]] = 1
    return w, left


def unstretched(tris, scan_pos, rest, weights, poses) -> np.ndarray:
    """Triangles that are not welds. The scan joins her skin to whatever it touched (the upper arms to the blouse's
    sides, hair ends to the shoulders, fingertips to the skirt), and those triangles tear into spikes and webs once the
    two move apart: in the rest pose or on some clip frame an edge grows past STRETCH times its scanned length and by
    more than WELD inches. Cloth and skin that only stretch (sleeves, the skirt's hem) grow by less."""
    def edges(p):
        return np.stack([np.linalg.norm(p[tris[:, k]] - p[tris[:, (k + 1) % 3]], axis=1) for k in range(3)], 1)
    base = edges(scan_pos)
    grown = edges(rest)
    for world in poses:
        grown = np.maximum(grown, edges(apply(blend(weights, world), rest)))
    weld = (grown > STRETCH * np.maximum(base, 0.05)) & (grown - base > WELD)
    return ~weld.any(1)


def clip_poses(cit: za.Skeleton, per_clip: int = 8) -> list[np.ndarray]:
    """Skinning matrices (pose x inverse bind) for sample frames of every driver clip."""
    a = argparse.Namespace(walk_pack="D:/tmp/hc1-mw22-tools/decompiled/nmrih_3255961963",
                           run_pack="D:/tmp/hc1-mw22-tools/decompiled/nmrih_3255991053", citizen_data=str(CITIZEN_DATA))
    _, ported = za.port_all(a)
    inv_bind = np.array([np.linalg.inv(b) for b in cit.bind_world])
    out = []
    for p in ported:
        for t in np.linspace(0, len(p.world) - 1, per_clip).round().astype(int):
            out.append(np.array(p.world[t]) @ inv_bind)
    return out


def apart(tris: np.ndarray, region: np.ndarray) -> np.ndarray:
    """Triangles that don't span an arm and the body below the waist (where the hands are welded to the skirt)."""
    r = region[tris]
    arm = (r == 1) | (r == 2)
    body = r == 3
    return ~(arm.any(1) & body.any(1)) & ~((r == 1).any(1) & (r == 2).any(1))


# ── Stages ──────────────────────────────────────────────────────────────────────

def blender(stage: str, arg: Path) -> None:
    script = Path(__file__).resolve().parent / "zombie_female_01_blender.py"
    subprocess.run([str(BLENDER), "-b", "--factory-startup", "--python", str(script), "--", stage, str(WORK), str(arg)],
                   check=True)


def textures() -> None:
    out = ROOT / "Assets" / ASSET_DIR
    out.mkdir(parents=True, exist_ok=True)
    Image.open(WORK / ("atlas_color.png" if USE_ATLAS else "base_color.jpg")).convert("RGB").resize(
        (4096, 4096) if USE_ATLAS else (2048, 2048), Image.LANCZOS) \
        .save(out / f"{NAME}_color.png")
    normal = np.asarray(Image.open(WORK / ("atlas_normal.png" if USE_ATLAS else "normal_lod0.png")))[..., :3]
    n = normal.astype(np.float64) / np.iinfo(normal.dtype).max * 2 - 1
    # Where the bake's rays found the far side of a thin strand of hair, the normal tilts nearly backwards: flat there.
    wild = n[..., 2] < 0.25
    n[wild] = (0, 0, 1)
    print(f"normal map: {wild.mean():.2%} of texels flattened")
    Image.fromarray(((n + 1) / 2 * 255 + 0.5).clip(0, 255).astype(np.uint8)).save(out / f"{NAME}_normal.png")
    if USE_ATLAS:
        Image.open(WORK / "atlas_rough.png").convert("L").save(out / f"{NAME}_rough.png")
    else:
        mr = np.asarray(Image.open(WORK / "metallic_roughness.jpg").convert("RGB"))
        Image.fromarray(mr[..., 1]).save(out / f"{NAME}_rough.png")
    print("textures written")


def rig(write: bool, meshes_only: bool = False) -> None:
    """Without write, only rigged.npz (for preview): the open editor compiles whatever lands in Assets."""
    cit = za.read_model_skeleton(CITIZEN_DATA)
    body = load_citizen(cit)
    maps = np.array(deformations(cit, body))
    posed_cit = apply(blend(body["weights"], maps), body["positions"])
    color = np.asarray(Image.open(WORK / ("atlas_color.png" if USE_ATLAS else "base_color.jpg")).convert("RGB").reduce(4))
    out = ROOT / "Assets" / ASSET_DIR
    nodes = [(n, p) for n, p in zip(cit.names, cit.parents)]
    poses = clip_poses(cit)
    lod0_pose = lod0_w = None
    saved = {}
    lod0_tris = lod0_region = None
    for i in range(LOD_COUNT):
        lod = load_lod(i)
        pos = to_model(lod["positions"])
        region = regions(lod, color)
        hair = hair_mask(lod, color)
        whole = len(lod["triangles"])
        kept = apart(lod["triangles"], region)
        lod["triangles"], lod["uvs"], lod["normals"] = (lod["triangles"][kept], lod["uvs"][kept],
                                                        lod["normals"][kept])
        tris = lod["triangles"]
        print(f"lod{i}: {len(tris)} triangles ({whole - len(tris)} joining a hand to the skirt left out), "
              f"{(region == 1).sum()} + {(region == 2).sum()} hand vertices, {hair.sum()} hair")
        def keep(w):
            return constrain(w, region, hair, cit)
        if i == 0:
            w = transfer(posed_cit, body["triangles"], body["weights"], pos, tris, NEAR, FACING, keep)
            w = keep(smooth(keep(w)[0], tris, SMOOTH))[0]
            w = stabilize_head(prune(w, MAX_LINKS), lod["positions"], cit)
            lod0_pose, lod0_w, lod0_tris, lod0_region = pos, w, tris, region
        else:
            w = transfer(lod0_pose, lod0_tris, lod0_w, pos, tris, src_class=lod0_region, dst_class=region)
            w = stabilize_head(prune(keep(w)[0], MAX_LINKS), lod["positions"], cit)
        m = blend(w, maps)
        det = np.linalg.det(m[:, :3, :3])
        print(f"  blend determinants {det.min():.3f} to {det.max():.3f}")
        inv = np.linalg.inv(m)
        rest = apply(inv, pos)
        whole = len(tris)
        kept = unstretched(tris, pos, rest, w, poses)
        lod["triangles"], lod["uvs"], lod["normals"] = tris[kept], lod["uvs"][kept], lod["normals"][kept]
        tris = lod["triangles"]
        if i == 0:
            lod0_tris = tris  # the lower LODs take their weights from LOD0's surface without its welds
        print(f"  {whole - len(tris)} welded triangles left out")
        # Normals go back by the inverse transpose of the inverse: the blend's own transpose.
        corner_n = np.stack([-lod["normals"][..., 1], lod["normals"][..., 0], lod["normals"][..., 2]], axis=-1)
        lin_t = np.transpose(m[:, :3, :3], (0, 2, 1))
        rest_n = np.einsum("tkij,tkj->tki", lin_t[tris], corner_n)
        rest_n /= np.linalg.norm(rest_n, axis=-1, keepdims=True)
        saved[i] = {"rest": rest, "weights": w, "triangles": tris, "uvs": lod["uvs"]}
        if not write:
            continue
        out.mkdir(parents=True, exist_ok=True)
        triangles = []
        for t in range(len(tris)):
            corners = []
            for k in range(3):
                v = tris[t, k]
                links = [(b, w[v, b]) for b in np.flatnonzero(w[v])]
                corners.append((rest[v], rest_n[t, k], lod["uvs"][t, k], links))
            triangles.append((NAME, corners))
        dmx.write_model(out / f"{NAME}_lod{i}.dmx", NAME, nodes, cit.bind_local, triangles)
    np.savez(WORK / "rigged.npz", **{f"{k}{i}": v for i in saved for k, v in saved[i].items()},
             posed_citizen=posed_cit, citizen_triangles=body["triangles"])
    if write and not meshes_only:
        write_vmat(out)
        write_vmdl(out)
    if write:
        print("rig written")


def write_vmat(out: Path) -> None:
    (out / f"{NAME}.vmat").write_text(f"""// Generated by Tools/zombie_female_01.py: the Meshy scan's colour and roughness at 2048, LOD0's baked normal map.

Layer0
{{
	shader "shaders/complex.shader"

	//---- PBR ----
	F_SPECULAR 1
	// The skirt and the hair are single sheets.
	F_RENDER_BACKFACES 1

	//---- Color ----
	g_flModelTintAmount "1.000"
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "{ASSET_DIR}/{NAME}_color.png"

	//---- Fog ----
	g_bFogEnabled "1"

	//---- Metalness ----
	g_flMetalness "0.000"

	//---- Normal ----
	TextureNormal "{ASSET_DIR}/{NAME}_normal.png"

	//---- Roughness ----
	g_flRoughnessScaleFactor "1.000"
	TextureRoughness "{ASSET_DIR}/{NAME}_rough.png"
}}
""")


def write_vmdl(out: Path) -> None:
    meshes = "".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{ASSET_DIR}/{NAME}_lod{i}.dmx" '
        'import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" '
        'import_filter = { exclude_by_default = false exception_list = [ ] } },\n' for i in range(LOD_COUNT))
    lods = "".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{i}" ] }},\n'
                   for i, t in enumerate(LOD_THRESHOLDS))
    (out / f"{NAME}.vmdl").write_text(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
// Generated by Tools/zombie_female_01.py: skinned to the citizen's skeleton in its rest pose, for bone merge onto
// models/zombie/zombie_driver.vmdl (ZombiesRoundSystem's ZombieBodyModels).
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{{ from = "{NAME}.vmat" to = "{ASSET_DIR}/{NAME}.vmat" }}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
{meshes}				]
			}},
			{{
				_class = "LODGroupList"
				children =
				[
{lods}				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
""")


def preview(views: list[str], clips: list[str], lod: int, frames_per_clip: int) -> None:
    """A LOD skinned on sample frames of the driver's clips (as bone merge shows it), and in its rest pose."""
    rigged = np.load(WORK / "rigged.npz")
    rest, w = rigged[f"rest{lod}"], rigged[f"weights{lod}"]
    a = argparse.Namespace(walk_pack="D:/tmp/hc1-mw22-tools/decompiled/nmrih_3255961963",
                           run_pack="D:/tmp/hc1-mw22-tools/decompiled/nmrih_3255991053", citizen_data=str(CITIZEN_DATA))
    cit, ported = za.port_all(a)
    inv_bind = np.array([np.linalg.inv(b) for b in cit.bind_world])
    rows = [("rest", [np.array(cit.bind_world)])]
    for p in ported:
        if p.clip.name not in clips:
            continue
        n = len(p.world)
        picks = np.linspace(0, n - 2 if p.clip.kind == "move" else n - 1, frames_per_clip).round().astype(int)
        rows.append((p.clip.name, [np.array(p.world[t]) for t in picks]))
    posed = [[apply(blend(w, world @ inv_bind), rest) for world in frames] for _, frames in rows]
    spacing, row_height = 40.0 / SCALE, 80.0 / SCALE
    cols = max(len(f) for _, f in rows)
    size = max(cols * spacing, len(rows) * row_height) + 0.3
    for view in views:
        # Across the picture: +X for the front, +Y (her back) for the side (seen from her left), -X for the back.
        across, axis = {"front": ([1, 0, 0], "-y"), "side": ([0, 1, 0], "+x"), "back": ([-1, 0, 0], "+y")}[view]
        across = np.array(across, float)
        meshes = []
        for r, (name, _) in enumerate(rows):
            for k, v in enumerate(posed[r]):
                # Back to Blender's axes in scan units, laid out in a grid.
                b = np.stack([v[:, 1], -v[:, 0], v[:, 2]], axis=-1) / SCALE
                b += k * spacing * across + [0, 0, -r * row_height]
                path = WORK / f"pv_{view}_{name}_{k}.npz"
                np.savez(path, positions=b, triangles=rigged[f"triangles{lod}"], uvs=rigged[f"uvs{lod}"])
                meshes.append({"npz": str(path)})
        centre = (cols - 1) * spacing / 2 * across + [0, 0, row_height / 2 - (len(rows) - 1) * row_height / 2 + 0.05]
        px = int(330 * size / row_height)
        spec = {"meshes": meshes, "color": str(WORK / ("atlas_color.png" if USE_ATLAS else "base_color.jpg")),
                "views": [{"name": f"preview_{view}", "center": centre.tolist(), "axis": axis, "scale": size,
                           "width": px, "height": px}]}
        (WORK / f"spec_preview_{view}.json").write_text(json.dumps(spec))
        blender("preview", WORK / f"spec_preview_{view}.json")


def main() -> None:
    global USE_ATLAS
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["lods", "atlas", "citizen", "textures", "rig", "preview"])
    parser.add_argument("--views", default="front,side")
    parser.add_argument("--clips", default="idle,walk_a,run,attack_a")
    parser.add_argument("--write", action="store_true", help="rig: write the DMX, vmdl and vmat into Assets")
    parser.add_argument("--meshes-only", action="store_true", help="rig --write: update mesh inputs without rewriting editor resources")
    parser.add_argument("--atlas", action="store_true", help="use the repaired UV atlas (the default)")
    parser.add_argument("--scan-uvs", action="store_true", help="reference/debug only: use the original scan UVs and maps")
    parser.add_argument("--lod", type=int, default=0)
    parser.add_argument("--frames", type=int, default=6)
    args = parser.parse_args()
    USE_ATLAS = not args.scan_uvs
    WORK.mkdir(parents=True, exist_ok=True)
    if args.stage == "lods":
        blender("lods", SCAN)
    elif args.stage == "atlas":
        subprocess.run([str(BLENDER), "-b", "--factory-startup", "--python",
                        str(Path(__file__).with_name("zombie_female_01_atlas.py"))], check=True)
    elif args.stage == "citizen":
        blender("citizen", CITIZEN_FBX)
    elif args.stage == "textures":
        textures()
    elif args.stage == "rig":
        rig(args.write, args.meshes_only)
    else:
        preview(args.views.split(","), args.clips.split(","), args.lod, args.frames)


if __name__ == "__main__":
    main()
