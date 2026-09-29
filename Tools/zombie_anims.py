"""Port No More Room in Hell's zombie mocap onto the citizen skeleton, for the Zombies mode's zombies.

A zombie is an invisible citizen "driver" with the zombie mesh bone-merged onto it (ZombiesRoundSystem.SpawnZombie).
The citizen's own animgraph walks like a person, so the driver is models/zombie/zombie_driver.vmdl instead: the
citizen's body, physics, hitboxes and constraints (its prefabs) with the NMRIH clips below and no animgraph. ZombieAI
plays them as sequences, using the table this writes to Code/NPCs/Zombies/ZombieClips.cs.

Inputs (not in the repo):
  - The two GMod workshop addons that carry NMRIH's zombie animations on HL2's classic zombie: 3255961963 (walks,
    idle, attacks) and 3255991053 (run), downloaded with SteamCMD, extracted with gmad and decompiled with Crowbar
    (models/zombie/classic.mdl -> classic.qc, Zombie_reference.smd, classic_anims/*.smd).
  - The citizen skeleton: `Source2Viewer-CLI -i citizen_human_male.vmdl_c -b DATA` (s&box's addons/citizen), whose
    m_modelSkeleton is read here.

Retargeting: every mapped bone takes its ValveBiped counterpart's world-space rotation change from the reference pose.
Limbs are first turned so their rest direction matches the ValveBiped's (the two A-poses differ). Hands and fingers
are aimed at where the source's knuckles and finger joints are instead (some clips were made on a skeleton with
differently rolled hand bones). The elbows bend only as hinges, and the forearms turn the hands only as far as a
person's can (`Clip.turn`). The ValveBiped has no
neck or head; its headcrab bone sits on the head, so the head follows that, and the neck goes halfway. The pelvis
moves by the ValveBiped's, scaled by leg length, with the forward travel taken out (ZombieAI moves the zombie) and the
lowest foot kept at the ValveBiped's height.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import kastov_dmx as dmx

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = "models/zombie"
WORK = Path("D:/tmp/hc1-mw22-tools")
CM = 0.3937  # the citizen's sources are in centimetres; its ScaleAndMirror modifier turns them into inches


@dataclass(frozen=True)
class Clip:
    name: str      # sequence name in the driver model
    pack: str      # "walk" (3255961963) or "run" (3255991053)
    source: str    # NMRIH sequence
    kind: str      # "idle", "move" (looping, in place) or "attack"
    sway: float = 1.0  # move clips: share of the hips' and spine's side-to-side roll, yaw and shift that's kept
    stance: float = 1.0  # move clips (with sway): share of the feet's sideways spread from the midline that's kept
    stride: float = 1.0  # move clips: the feet's forward and back reach is scaled by this (so is the clip's speed), the
                         # hips sinking as far as the longer steps need
    turn: tuple[float, float] = (5.0, 170.0)  # degrees the forearms may turn the hands to (see forearm_turn)


# The walk (a_WalkN) and the classic zombie's own attacks (B, D, E and F) hold the claws palm up, on average 0-40
# degrees from full supination, and bent ~60 degrees at the wrist: on a person's hands that reads as twisted, the hand
# bent back towards the zombie. Their hands are kept turned palm down instead, so the bent wrists droop like a zombie's.
CLAW_TURN = (100.0, 170.0)

# NMRIH's other shambles (walk1-10) are 12-22 units/s, or walk upright like a person (walk7): too slow for a 70 u/s
# Walker without racing the clip. walk3 (one arm reaching out) and walk2/walk9 (lurching, head lolling back) would suit
# slower zombies.
CLIPS = [
    Clip("idle", "walk", "Idle01", "idle"),
    # a_WalkN rolls and twists the hips and chest ~22/35 and ~34/57 degrees, swinging the head 21" side to side, on
    # feet planted 19" apart; at the Walkers' sped-up cadence that waddle looks like dancing. Its 17" steps also only
    # cover 32 u/s, so a Walker (70) had to play it at 1.7x, a frantic scurry: its steps are made 1.5x as long (hips
    # ~3" lower), which brings that down to ~1.45x. Longer steps turn it into a squatting lunge.
    Clip("walk_a", "walk", "a_WalkN", "move", sway=0.35, stance=0.6, stride=1.5, turn=CLAW_TURN),
    Clip("run", "run", "walk1", "move", sway=0.6),
    Clip("attack_a", "walk", "attackA", "attack"),
    Clip("attack_b", "walk", "attackB", "attack", turn=CLAW_TURN),
    Clip("attack_c", "walk", "attackC", "attack"),
    Clip("attack_d", "walk", "attackD", "attack", turn=CLAW_TURN),
    Clip("attack_e", "walk", "attackE", "attack", turn=CLAW_TURN),
    Clip("attack_f", "walk", "attackF", "attack", turn=CLAW_TURN),
]

# SMD space faces -Y (studiomdl turns it 90 degrees); model space faces +X.
G = np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)

# Citizen bone: (ValveBiped bone, citizen child, ValveBiped child). Turned to the ValveBiped's rest direction first.
LIMBS: dict[str, tuple[str, str, str]] = {}
for s in "LR":
    LIMBS.update({
        f"clavicle_{s}": (f"{s}_Clavicle", f"arm_upper_{s}", f"{s}_UpperArm"),
        f"arm_upper_{s}": (f"{s}_UpperArm", f"arm_lower_{s}", f"{s}_Forearm"),
        f"arm_lower_{s}": (f"{s}_Forearm", f"hand_{s}", f"{s}_Hand"),
        f"leg_upper_{s}": (f"{s}_Thigh", f"leg_lower_{s}", f"{s}_Calf"),
        f"leg_lower_{s}": (f"{s}_Calf", f"ankle_{s}", f"{s}_Foot"),
        f"ankle_{s}": (f"{s}_Foot", f"ball_{s}", f"{s}_Toe0"),
    })

# Upper arms have their roll matched too, not just their direction: their elbows' bend axes (the citizen bends about
# local +Z, the ValveBiped about -Z) line up, so the elbows bend the same way.
ROLLS = {f"arm_upper_{s}": ((0, 0, 1), (0, 0, -1)) for s in "LR"}
# The run (from the other addon) bends the forearm up to 60 degrees off its upper arm's hinge, which bent the citizen's
# elbows sideways. So each frame the upper arm (key) also rolls about itself to bring its forearm (value) into the plane
# the elbow bends in. The fix fades in over ELBOW_LOOSE of bend, since a straight arm's bend plane means nothing.
ELBOWS = {f"arm_upper_{s}": f"arm_lower_{s}" for s in "LR"}
ELBOW_LOOSE = (np.radians(5.0), np.radians(20.0))

# Forearms keep no roll of their own: the elbow is a hinge, and turning the hand turns the forearm's twist bones.
# The ValveBiped (a Max Biped) rolls its forearm with the hand, which twisted the citizen's arms at the elbow.
HINGES = {f"arm_lower_{s}" for s in "LR"}
# How far the forearm turns the hand (pronation/supination) is measured from the elbow's hinge (`forearm_turn`): 0 has
# the palm turned fully towards the biceps (supinated), 180 fully away (pronated); the citizen's rest pose is ~102, and
# a person reaches ~5 to ~170 (`Clip.turn`). The classic zombie's claw swipes turn the hands past full supination, palm
# out, and attack E's right hand a whole turn; rolling the forearm at the elbow to follow that wrung the arms. A hand
# turned past the clip's limits stays at the nearer one, and turns back round through the range no faster than this:
FOREARM_TURN_RATE = np.radians(720.0)  # per second

# Hands and fingers are posed from where the source's knuckles and finger joints are, not from rotation changes: the
# NMRIH clips (idle, walk, run, attacks A and C) were made on NMRIH's own skeleton, whose hand bone is rolled ~90 degrees
# from the classic zombie's reference pose, so a change from that pose turned the palms sideways.
# Hand: (ValveBiped hand, middle knuckle, index knuckle, ring knuckle).
HANDS = {f"hand_{s}": (f"{s}_Hand", f"{s}_Finger2", f"{s}_Finger1", f"{s}_Finger3") for s in "LR"}
# Finger joint: (ValveBiped joint, ValveBiped next joint), aimed along that segment. The last joints have no segment
# after them in the source and bend like the joint before (`TIPS`).
FINGERS: dict[str, tuple[str, str]] = {}
TIPS: dict[str, str] = {}
for s in "LR":
    for finger, vb in (("thumb", "0"), ("index", "1"), ("middle", "2"), ("ring", "3")):
        FINGERS[f"finger_{finger}_0_{s}"] = (f"{s}_Finger{vb}", f"{s}_Finger{vb}1")
        FINGERS[f"finger_{finger}_1_{s}"] = (f"{s}_Finger{vb}1", f"{s}_Finger{vb}2")
        TIPS[f"finger_{finger}_2_{s}"] = f"finger_{finger}_1_{s}"

# Citizen bone: ValveBiped bone. Rotation change only (both rest poses stand upright).
TRUNK = {"pelvis": "Pelvis", "spine_0": "Spine", "spine_1": "Spine1", "spine_2": "Spine4", "head": "HC_Body_Bone"}

# Citizen bone: (ValveBiped bone, the limb whose rest-direction turn it shares).
INHERIT = {f"ball_{s}": (f"{s}_Toe0", f"ankle_{s}") for s in "LR"}

# The ValveBiped has no pinky: it curls with the ring finger.
PINKY = {f"finger_pinky_{j}_{s}": f"finger_ring_{j}_{s}" for s in "LR" for j in range(3)}

# The citizen's skin mostly follows its twist and helper bones, which its animgraph moves with anim constraints. The
# clips carry them too, so they don't depend on constraints running for sequences.
# Twist bone: (bone whose twist it takes, twist axis from, axis to, share). Upper-limb twist bones undo the limb's own
# twist (the shoulder and hip don't roll with the arm/leg); lower-limb ones take some of the wrist's/ankle's.
TWISTS: dict[str, tuple[str, str, str, float]] = {}
# Helper: (upper bone, lower bone); it turns halfway between the two.
HELPERS: dict[str, tuple[str, str]] = {}
for s in "LR":
    TWISTS.update({
        f"arm_upper_{s}_twist0": (f"arm_upper_{s}", f"arm_upper_{s}", f"arm_lower_{s}", -1.0),
        f"arm_upper_{s}_twist1": (f"arm_upper_{s}", f"arm_upper_{s}", f"arm_lower_{s}", -0.5),
        f"arm_lower_{s}_twist0": (f"hand_{s}", f"arm_lower_{s}", f"hand_{s}", 0.2),
        f"arm_lower_{s}_twist1": (f"hand_{s}", f"arm_lower_{s}", f"hand_{s}", 0.6),
        f"leg_upper_{s}_twist0": (f"leg_upper_{s}", f"leg_upper_{s}", f"leg_lower_{s}", -1.0),
        f"leg_upper_{s}_twist1": (f"leg_upper_{s}", f"leg_upper_{s}", f"leg_lower_{s}", -0.5),
        f"leg_lower_{s}_twist1": (f"ankle_{s}", f"leg_lower_{s}", f"ankle_{s}", 0.5),
    })
    HELPERS[f"arm_elbow_helper_{s}"] = (f"arm_upper_{s}", f"arm_lower_{s}")
    HELPERS[f"leg_knee_helper_{s}"] = (f"leg_upper_{s}", f"leg_lower_{s}")


# ── Math ────────────────────────────────────────────────────────────────────────

def quat_to_matrix(q) -> np.ndarray:
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def euler_matrix(rx: float, ry: float, rz: float) -> np.ndarray:
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


def rotation_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    axis = np.cross(a, b)
    s, c = np.linalg.norm(axis), float(np.dot(a, b))
    if s < 1e-8:
        return np.eye(3)
    k = axis / s
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    angle = np.arctan2(s, c)
    return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * K @ K


def axis_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    k = axis / np.linalg.norm(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * K @ K


def twist_angle(rotation: np.ndarray, axis: np.ndarray) -> float:
    """Angle of the rotation's twist about the axis (swing-twist decomposition), -180 to 180 degrees."""
    x, y, z, w = dmx.rotation_to_quaternion(rotation)
    sign = 1.0 if w >= 0 else -1.0  # q and -q are the same rotation; take the short way round
    return 2.0 * float(np.arctan2(sign * np.dot([x, y, z], axis / np.linalg.norm(axis)), sign * w))


def frame_turn(d_from: np.ndarray, side_from: np.ndarray, d_to: np.ndarray, side_to: np.ndarray) -> np.ndarray:
    """Turn d_from onto d_to, then roll about d_to so side_from lines up with side_to."""
    r = rotation_between(d_from, d_to)
    axis = d_to / np.linalg.norm(d_to)
    a, b = r @ side_from, side_to
    a, b = a - np.dot(a, axis) * axis, b - np.dot(b, axis) * axis
    return axis_rotation(axis, float(np.arctan2(np.dot(np.cross(a, b), axis), np.dot(a, b)))) @ r


def nearest_within(angle: float, lo: float, hi: float) -> float:
    """The angle if it's between lo and hi (radians, round the circle), else whichever of the two is nearer."""
    angle = lo + (angle - lo) % (2 * np.pi)
    if angle <= hi:
        return angle
    return hi if angle - hi < lo + 2 * np.pi - angle else lo


def forearm_turn(world: list[np.ndarray], index: dict[str, int], side: str) -> float:
    """How far the forearm has turned the hand (see Clip.turn), from the knuckles and the upper arm's hinge (+Z)."""
    at = lambda bone: world[index[f"{bone}_{side}"]][:3, 3]
    forearm = at("hand") - at("arm_lower")
    forearm = forearm / np.linalg.norm(forearm)
    flexion = np.cross(world[index[f"arm_upper_{side}"]][:3, 2], forearm)
    palm = np.cross(at("finger_middle_0") - at("hand"), at("finger_ring_0") - at("finger_index_0"))
    if side == "L":
        palm = -palm
    angle = float(np.arctan2(np.dot(np.cross(flexion, palm), forearm), np.dot(flexion, palm)))
    return -angle if side == "R" else angle


def yaw(angle: float) -> np.ndarray:
    m = np.eye(4)
    m[:3, :3] = euler_matrix(0, 0, angle)
    return m


def slerp(r0: np.ndarray, r1: np.ndarray, t: float) -> np.ndarray:
    q0 = np.array(dmx.rotation_to_quaternion(r0))
    q1 = np.array(dmx.rotation_to_quaternion(r1))
    if np.dot(q0, q1) < 0:
        q1 = -q1
    angle = np.arccos(np.clip(np.dot(q0, q1), -1, 1))
    if angle < 1e-6:
        q = q0
    else:
        q = (np.sin((1 - t) * angle) * q0 + np.sin(t * angle) * q1) / np.sin(angle)
    return quat_to_matrix(q / np.linalg.norm(q))


def rotation_vector(rotation: np.ndarray) -> np.ndarray:
    x, y, z, w = dmx.rotation_to_quaternion(rotation)
    v = np.array([x, y, z]) * (1 if w >= 0 else -1)
    s = float(np.linalg.norm(v))
    return v * (2 * np.arctan2(s, abs(w)) / s) if s > 1e-9 else np.zeros(3)


def from_rotation_vector(v: np.ndarray) -> np.ndarray:
    angle = float(np.linalg.norm(v))
    return axis_rotation(v, angle) if angle > 1e-9 else np.eye(3)


def mean_rotation(rotations: list[np.ndarray]) -> np.ndarray:
    qs = [np.array(dmx.rotation_to_quaternion(r)) for r in rotations]
    q = sum(q if np.dot(q, qs[0]) >= 0 else -q for q in qs)
    return quat_to_matrix(q / np.linalg.norm(q))


def world_of(parents: list[int], locals_: list[np.ndarray]) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for i, p in enumerate(parents):
        out.append(locals_[i] if p < 0 else out[p] @ locals_[i])
    return out


# ── Inputs ──────────────────────────────────────────────────────────────────────

@dataclass
class Skeleton:
    names: list[str]
    parents: list[int]
    bind_local: list[np.ndarray]  # inches

    def __post_init__(self):
        self.index = {n: i for i, n in enumerate(self.names)}
        self.bind_world = world_of(self.parents, self.bind_local)


def read_model_skeleton(dump: Path) -> Skeleton:
    """m_modelSkeleton of a Source2Viewer DATA dump."""
    text = dump.read_text(encoding="utf-8-sig")
    start = text.index("m_modelSkeleton")

    def array(key: str) -> str:
        i = text.index("[", text.index(key + " = ", start))
        depth = 0
        for j in range(i, len(text)):
            depth += {"[": 1, "]": -1}.get(text[j], 0)
            if depth == 0:
                return text[i + 1:j]
        raise ValueError(key)

    number = r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?"
    names = re.findall(r'"([^"]*)"', array("m_boneName"))
    parents = [int(v) for v in re.findall(r"-?\d+", array("m_nParent"))]
    positions = [[float(v) for v in re.findall(number, m)] for m in re.findall(r"\[([^\]]*)\]", array("m_bonePosParent"))]
    rotations = [[float(v) for v in re.findall(number, m)] for m in re.findall(r"\[([^\]]*)\]", array("m_boneRotParent"))]
    bind = []
    for p, q in zip(positions, rotations):
        m = np.eye(4)
        m[:3, :3] = quat_to_matrix(q)
        m[:3, 3] = p
        bind.append(m)
    return Skeleton(names, parents, bind)


def read_smd(path: Path) -> tuple[list[str], list[int], list[list[np.ndarray]]]:
    """Bone names (ValveBiped./Bip01_ stripped), parents and per-frame local transforms in SMD space."""
    names: list[str] = []
    parents: list[int] = []
    frames: list[dict[int, np.ndarray]] = []
    section = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        if s in ("nodes", "skeleton", "triangles"):
            section = s
        elif s == "end":
            section = None
        elif section == "nodes":
            parts = s.split('"')
            names.append(parts[1].replace("ValveBiped.", "").replace("Bip01_", ""))
            parents.append(int(parts[2]))
        elif section == "skeleton":
            if s.startswith("time"):
                frames.append({})
            else:
                v = s.split()
                m = np.eye(4)
                m[:3, :3] = euler_matrix(*map(float, v[4:7]))
                m[:3, 3] = [float(x) for x in v[1:4]]
                frames[-1][int(v[0])] = m
    full, last = [], {}
    for frame in frames:
        last = {**last, **frame}
        full.append([last.get(i, np.eye(4)) for i in range(len(names))])
    return names, parents, full


def qc_fps(qc: Path) -> dict[str, float]:
    text = qc.read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(r'\$(?:sequence|animation) "([^"]+)" \{(.*?)\n\}', text, re.S):
        f = re.search(r"\bfps (\d+(?:\.\d+)?)", m.group(2))
        out[m.group(1).lower()] = float(f.group(1)) if f else 30.0
    return out


# ── Retarget ────────────────────────────────────────────────────────────────────

@dataclass
class Ported:
    clip: Clip
    fps: float
    world: list[list[np.ndarray]]   # per frame, citizen bone world transforms (model space, inches)
    speed: float                     # in-place travel speed the clip was authored for, at citizen scale (units/s)
    hit: float                       # attacks: seconds to the swing's furthest reach


def sole_points(skel_world: list[np.ndarray], index: dict[str, int], heel_bone: str, toe_bone: str,
                ground_ref: list[np.ndarray]) -> list[tuple[int, np.ndarray]]:
    """Heel and toe on the ground under the rest pose, in their bones' local space."""
    points = []
    for bone in (heel_bone, toe_bone):
        w = ground_ref[index[bone]]
        on_ground = np.array([w[0, 3], w[1, 3], 0.0, 1.0])
        points.append((index[bone], np.linalg.inv(w) @ on_ground))
    return points


def lowest(world: list[np.ndarray], points) -> float:
    return min(float((world[b] @ p)[2]) for b, p in points)


def damp_sway(anim: list[list[np.ndarray]], bones: list[int], carried: dict[int, int], pelvis: int,
              keep: float) -> list[list[np.ndarray]]:
    """Scale the bones' roll (about +X, forward) and yaw (about +Z) about their loop average by `keep`, and the
    pelvis's sideways (Y) shift. Pitch (the forward lean and bob) is left alone. Carried bones (the arms) turn with
    their damped bone (the chest), so they don't swing further across it than they did."""
    out = [[w.copy() for w in f] for f in anim]
    for b in bones:
        mean = mean_rotation([f[b][:3, :3] for f in anim])
        for f in out:
            v = rotation_vector(f[b][:3, :3] @ mean.T)
            v[[0, 2]] *= keep
            f[b][:3, :3] = from_rotation_vector(v) @ mean
    for f, g in zip(anim, out):
        for b, by in carried.items():
            turn = g[by][:3, :3] @ f[by][:3, :3].T
            g[b][:3, :3] = turn @ f[b][:3, :3]
            g[b][:3, 3] = g[by][:3, 3] + turn @ (f[b][:3, 3] - f[by][:3, 3])
    side = np.mean([f[pelvis][1, 3] for f in anim])
    for f in out:
        f[pelvis][1, 3] = side + keep * (f[pelvis][1, 3] - side)
    return out


def plant_leg(world: list[np.ndarray], cit: "Skeleton", side: str, ankle: np.ndarray) -> None:
    """Two-bone IK: bend the thigh and shin so the ankle reaches `ankle`, keeping the knee's side and the foot's turn."""
    ci = cit.index
    up, lo = ci[f"leg_upper_{side}"], ci[f"leg_lower_{side}"]
    hip = (world[cit.parents[up]] @ cit.bind_local[up])[:3, 3]
    thigh, shin = cit.bind_local[lo][:3, 3], cit.bind_local[ci[f"ankle_{side}"]][:3, 3]
    a, b = float(np.linalg.norm(thigh)), float(np.linalg.norm(shin))
    to = ankle - hip
    d = float(np.clip(np.linalg.norm(to), abs(a - b) + 1e-3, (a + b) * 0.9999))
    u = to / np.linalg.norm(to)
    knee_now = world[up][:3, :3] @ thigh
    pole = knee_now - np.dot(knee_now, u) * u
    pole /= np.linalg.norm(pole)
    cos_hip = (a * a + d * d - b * b) / (2 * a * d)
    knee = a * (cos_hip * u + np.sqrt(max(0.0, 1 - cos_hip * cos_hip)) * pole)
    world[up][:3, :3] = rotation_between(knee_now, knee) @ world[up][:3, :3]
    shin_now = world[lo][:3, :3] @ shin
    world[lo][:3, :3] = rotation_between(shin_now, d * u - knee) @ world[lo][:3, :3]


def hips_drop(cit: "Skeleton", worlds: list[list[np.ndarray]], ankles: dict[str, np.ndarray], reach: float = 0.96) -> float:
    """How far the hips must sink (inches) so no leg has to stretch past `reach` of its length to its ankle target."""
    ci = cit.index
    length = float(np.linalg.norm(cit.bind_local[ci["leg_lower_L"]][:3, 3]) + np.linalg.norm(cit.bind_local[ci["ankle_L"]][:3, 3]))
    drop = 0.0
    for t, world in enumerate(worlds):
        for s in "LR":
            hip = (world[ci["pelvis"]] @ np.linalg.inv(cit.bind_world[ci["pelvis"]]) @ cit.bind_world[ci[f"leg_upper_{s}"]])[:3, 3]
            to = ankles[s][t] - hip
            # With the ankle this far out, the hip can be at most this high above it.
            highest = float(np.sqrt(max(0.0, (reach * length) ** 2 - float(np.dot(to[:2], to[:2])))))
            drop = max(drop, -float(to[2]) - highest)
    return drop


def port(clip: Clip, cit: Skeleton, src_dir: Path, fps: float) -> Ported:
    ref_names, ref_parents, ref_frames = read_smd(src_dir / "Zombie_reference.smd")
    names, parents, frames = read_smd(src_dir / "classic_anims" / f"{clip.source}.smd")
    assert names == ref_names, clip
    si = {n: i for i, n in enumerate(names)}
    ref = [G @ w for w in world_of(parents, ref_frames[0])]
    anim = [[G @ w for w in world_of(parents, f)] for f in frames]
    n = len(anim)

    # Locomotion: face the travel direction and take the travel out.
    pelvis = np.array([f[si["Pelvis"]][:3, 3] for f in anim])
    travel = pelvis[-1] - pelvis[0]
    travel[2] = 0
    distance = float(np.linalg.norm(travel))
    if clip.kind == "move" and distance > 1:
        turn = yaw(-np.arctan2(travel[1], travel[0]))
        anim = [[turn @ w for w in f] for f in anim]
        for t, f in enumerate(anim):
            shift = np.eye(4)
            shift[0, 3] = -distance * t / (n - 1)
            anim[t] = [shift @ w for w in f]

    ci = cit.index
    leg = lambda w, i, a, b, c: np.linalg.norm(w[i[a]][:3, 3] - w[i[b]][:3, 3]) + np.linalg.norm(w[i[b]][:3, 3] - w[i[c]][:3, 3])
    scale = leg(cit.bind_world, ci, "leg_upper_L", "leg_lower_L", "ankle_L") / leg(ref, si, "L_Thigh", "L_Calf", "L_Foot")

    turns = {}
    for bone, (vb, child, vb_child) in LIMBS.items():
        d_cit = cit.bind_world[ci[child]][:3, 3] - cit.bind_world[ci[bone]][:3, 3]
        d_src = ref[si[vb_child]][:3, 3] - ref[si[vb]][:3, 3]
        if bone in ROLLS:
            side_cit, side_src = (np.array(v, float) for v in ROLLS[bone])
            turns[bone] = frame_turn(d_cit, cit.bind_world[ci[bone]][:3, :3] @ side_cit,
                                     d_src, ref[si[vb]][:3, :3] @ side_src)
        else:
            turns[bone] = rotation_between(d_cit, d_src)

    rotate: dict[str, tuple[str, np.ndarray]] = {b: (vb, turns[b]) for b, (vb, _, _) in LIMBS.items()}
    rotate.update({b: (vb, np.eye(3)) for b, vb in TRUNK.items()})
    rotate.update({b: (vb, turns[limb]) for b, (vb, limb) in INHERIT.items()})

    src_feet = [p for s in "LR" for p in sole_points(ref, si, f"{s}_Foot", f"{s}_Toe0", ref)]
    cit_feet = [p for s in "LR" for p in sole_points(cit.bind_world, ci, f"ankle_{s}", f"ball_{s}", cit.bind_world)]

    ref_pelvis = ref[si["Pelvis"]][:3, 3]

    bind_at = lambda bone: cit.bind_world[ci[bone]][:3, 3]
    # The citizen's hands in their rest pose: (towards the middle knuckle, along the knuckles from index to ring).
    cit_hands = {h: (bind_at(f"finger_middle_0_{h[-1]}") - bind_at(h),
                     bind_at(f"finger_ring_0_{h[-1]}") - bind_at(f"finger_index_0_{h[-1]}")) for h in HANDS}
    next_joint = {name: ci[name[:-3] + str(int(name[-3]) + 1) + name[-2:]] for name in FINGERS}

    def hand(f: list[np.ndarray], name: str) -> np.ndarray:
        vb, middle, index, ring = (f[si[b]][:3, 3] for b in HANDS[name])
        return frame_turn(*cit_hands[name], middle - vb, ring - index) @ cit.bind_world[ci[name]][:3, :3]

    # The hand's twist on its forearm (about the hand's X) as the clip's range of turns: twisting it turns the left
    # hand one way and the right the other.
    rest = {s: forearm_turn(cit.bind_world, ci, s) for s in "LR"}
    lo, hi = np.radians(clip.turn)
    twist_range = {"L": (lo - rest["L"], hi - rest["L"]), "R": (rest["R"] - hi, rest["R"] - lo)}
    x_axis, z_axis = np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])

    def pose(f: list[np.ndarray], wrists: dict[str, float]) -> list[np.ndarray]:
        """`wrists` carries each hand's twist on its forearm from the frame before, to limit how fast it turns."""
        at = lambda bone: f[si[bone]][:3, 3]
        world: list[np.ndarray] = [None] * len(cit.names)  # type: ignore[list-item]
        hand_twists: dict[str, float] = {}  # hand: how much further it twists on its forearm than the source's
        turned: dict[str, np.ndarray] = {}  # side: that twist as a world rotation, which the fingers' aims take too
        for i, name in enumerate(cit.names):
            p = cit.parents[i]
            w = cit.bind_local[i].copy() if p < 0 else world[p] @ cit.bind_local[i]
            if name in rotate:
                vb, turn = rotate[name]
                delta = f[si[vb]][:3, :3] @ ref[si[vb]][:3, :3].T
                w[:3, :3] = delta @ turn @ cit.bind_world[i][:3, :3]
            elif name in HANDS:
                source = hand(f, name)
                w[:3, :3] = source @ axis_rotation(x_axis, hand_twists[name])
                turned[name[-1]] = w[:3, :3] @ source.T
            elif name in FINGERS:
                a, b = FINGERS[name]
                aim = turned[name[-1]] @ (at(b) - at(a))
                w[:3, :3] = rotation_between(w[:3, :3] @ cit.bind_local[next_joint[name]][:3, 3], aim) @ w[:3, :3]
            elif name in TIPS:
                j = ci[TIPS[name]]
                bend = cit.bind_local[j][:3, :3].T @ world[cit.parents[j]][:3, :3].T @ world[j][:3, :3]
                w[:3, :3] = w[:3, :3] @ bend
            elif name in PINKY:
                ring = ci[PINKY[name]]
                ring_local = np.linalg.inv(world[cit.parents[ring]]) @ world[ring]
                change = np.linalg.inv(cit.bind_local[ring]) @ ring_local
                w = world[p] @ cit.bind_local[i] @ change
            if name == "pelvis":
                w[:3, 3] = cit.bind_world[i][:3, 3] + scale * (f[si["Pelvis"]][:3, 3] - ref_pelvis)
            if name in ELBOWS:
                # Roll the upper arm so the forearm, aimed as the source's, lies in the plane its elbow bends in.
                vb, turn = rotate[ELBOWS[name]]
                forearm = (f[si[vb]][:3, :3] @ ref[si[vb]][:3, :3].T @ turn
                           @ cit.bind_world[ci[ELBOWS[name]]][:3, :3] @ x_axis)
                along = w[:3, :3] @ x_axis
                normal = np.cross(along, forearm)
                bend = float(np.arctan2(np.linalg.norm(normal), np.dot(along, forearm)))
                if bend > ELBOW_LOOSE[0]:
                    hinge = w[:3, :3] @ z_axis
                    roll = float(np.arctan2(np.dot(np.cross(hinge, normal), along), np.dot(hinge, normal)))
                    fade = min(1.0, (bend - ELBOW_LOOSE[0]) / (ELBOW_LOOSE[1] - ELBOW_LOOSE[0]))
                    w[:3, :3] = axis_rotation(along, fade * roll) @ w[:3, :3]
            if name in HINGES:
                # Keep the direction, drop the roll about the bone (its local X) relative to the parent.
                change = cit.bind_local[i][:3, :3].T @ world[p][:3, :3].T @ w[:3, :3]
                w[:3, :3] = (world[p][:3, :3] @ cit.bind_local[i][:3, :3] @ change
                             @ axis_rotation(x_axis, -twist_angle(change, x_axis)))
                # The hand's twist on the forearm, kept within a person's range.
                h = f"hand_{name[-1]}"
                source = twist_angle(cit.bind_local[ci[h]][:3, :3].T @ w[:3, :3].T @ hand(f, h), x_axis)
                twist = nearest_within(source, *twist_range[name[-1]])
                if name in wrists:
                    step = FOREARM_TURN_RATE / fps
                    twist = wrists[name] + float(np.clip(twist - wrists[name], -step, step))
                wrists[name] = twist
                hand_twists[h] = twist - source
            world[i] = w
        # Neck: halfway between following the chest and following the head.
        neck, chest, head = ci["neck_0"], ci["spine_2"], ci["head"]
        with_chest = world[chest][:3, :3] @ cit.bind_local[neck][:3, :3]
        with_head = world[head][:3, :3] @ (cit.bind_world[head][:3, :3].T @ cit.bind_world[neck][:3, :3])
        world[neck][:3, :3] = slerp(with_chest, with_head, 0.5)
        return world

    def finish(world: list[np.ndarray]) -> None:
        for name, (measured, a, b, share) in TWISTS.items():
            m, i, p = ci[measured], ci[name], cit.parents[ci[name]]
            axis = cit.bind_world[ci[b]][:3, 3] - cit.bind_world[ci[a]][:3, 3]
            change = cit.bind_local[m][:3, :3].T @ world[cit.parents[m]][:3, :3].T @ world[m][:3, :3]
            angle = twist_angle(change, cit.bind_world[m][:3, :3].T @ axis)
            world[i][:3, :3] = (world[p][:3, :3] @ cit.bind_local[i][:3, :3]
                                @ axis_rotation(cit.bind_world[i][:3, :3].T @ axis, share * angle))
        for name, (upper, lower) in HELPERS.items():
            i, u, lo = ci[name], ci[upper], ci[lower]
            rest = cit.bind_world[i][:3, :3]
            world[i][:3, :3] = slerp(world[u][:3, :3] @ cit.bind_world[u][:3, :3].T @ rest,
                                     world[lo][:3, :3] @ cit.bind_world[lo][:3, :3].T @ rest, 0.5)
        # Rebuild the chain below the pelvis so children follow their (retargeted) parents' positions.
        for i in range(len(cit.names)):
            p = cit.parents[i]
            if p >= 0:
                world[i][:3, 3] = (world[p] @ cit.bind_local[i])[:3, 3]

    out = []
    wrists: dict[str, float] = {}
    for f in anim:
        out.append(pose(f, wrists))
        finish(out[-1])

    if clip.kind == "move" and (clip.sway < 1 or clip.stride != 1):
        # Calmer hips and chest, the arms turning with the chest. The legs are bent to put the feet where the full sway
        # did, drawn in towards the midline (a constant sideways scale, so planted feet don't slide), and stretched
        # forward and back by the stride (planted feet then slide back that much faster, so the clip's speed goes up).
        chest = si["Spine4"]
        trunk = [si[vb] for vb in TRUNK.values()]
        below_chest = lambda b: parents[b] >= 0 and (parents[b] == chest or below_chest(parents[b]))
        arms = {b: chest for b in range(len(names)) if b not in trunk and below_chest(b)}
        damped = damp_sway(anim, trunk, arms, si["Pelvis"], clip.sway)
        ankles = {s: np.array([w[ci[f"ankle_{s}"]][:3, 3] for w in out]) for s in "LR"}
        mid = float(np.mean([ankles[s][:, 1] for s in "LR"]))
        for s in "LR":
            ankles[s][:, 1] = mid + clip.stance * (ankles[s][:, 1] - mid)
            centre = float(np.mean(ankles[s][:, 0]))
            ankles[s][:, 0] = centre + clip.stride * (ankles[s][:, 0] - centre)
        wrists = {}
        posed = [pose(g, wrists) for g in damped]
        crouch = hips_drop(cit, posed, ankles)
        for t, world in enumerate(posed):
            world[ci["pelvis"]][2, 3] -= crouch
            for s in "LR":
                plant_leg(world, cit, s, ankles[s][t])
            finish(world)
            out[t] = world

    for f, world in zip(anim, out):
        # Feet: the lowest sole point stays at the ValveBiped's (scaled) height.
        drop = scale * lowest(f, src_feet) - lowest(world, cit_feet)
        for w in world:
            w[2, 3] += drop

    if clip.kind == "move":
        # Centre the loop's sway on the driver's origin.
        mean = np.mean([w[ci["pelvis"]][:3, 3] for w in out], axis=0) - cit.bind_world[ci["pelvis"]][:3, 3]
        for world in out:
            for w in world:
                w[:2, 3] -= mean[:2]

    hit = 0.0
    if clip.kind == "attack":
        reach = [max(f[si["L_Hand"]][0, 3], f[si["R_Hand"]][0, 3]) - f[si["Pelvis"]][0, 3] for f in anim]
        hit = int(np.argmax(reach)) / fps
    speed = clip.stride * scale * distance / ((n - 1) / fps) if clip.kind == "move" else 0.0
    return Ported(clip, fps, out, speed, hit)


def local_frames(cit: Skeleton, world: list[np.ndarray]) -> list[np.ndarray]:
    out = []
    for i, p in enumerate(cit.parents):
        local = world[i].copy() if p < 0 else np.linalg.inv(world[p]) @ world[i]
        local[:3, 3] /= CM
        out.append(local)
    return out


# ── Outputs ─────────────────────────────────────────────────────────────────────

def prefab(target: str) -> str:
    return ("\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"Prefab\"\n"
            f"\t\t\t\t\t\ttarget_file = \"models/citizen_human/prefabs/{target}.vmdl_prefab\"\n\t\t\t\t\t}},\n")


def node_list(cls: str, body: str, extra: str = "") -> str:
    return (f"\t\t\t{{\n\t\t\t\t_class = \"{cls}\"\n\t\t\t\tchildren = \n\t\t\t\t[\n{body}\t\t\t\t]\n{extra}\t\t\t}},\n")


def anim_file(ported: Ported) -> str:
    looping = "false" if ported.clip.kind == "attack" else "true"
    return ("\t\t\t\t\t{\n"
            "\t\t\t\t\t\t_class = \"AnimFile\"\n"
            f"\t\t\t\t\t\tname = \"{ported.clip.name}\"\n"
            "\t\t\t\t\t\tactivity_name = \"\"\n"
            "\t\t\t\t\t\tactivity_weight = 1\n"
            "\t\t\t\t\t\tweight_list_name = \"\"\n"
            "\t\t\t\t\t\tfade_in_time = 0.25\n"
            "\t\t\t\t\t\tfade_out_time = 0.25\n"
            f"\t\t\t\t\t\tlooping = {looping}\n"
            "\t\t\t\t\t\tdelta = false\n"
            "\t\t\t\t\t\tworldSpace = false\n"
            "\t\t\t\t\t\thidden = false\n"
            "\t\t\t\t\t\tanim_markup_ordered = false\n"
            "\t\t\t\t\t\tdisable_compression = false\n"
            "\t\t\t\t\t\tdisable_interpolation = false\n"
            "\t\t\t\t\t\tenable_scale = false\n"
            f"\t\t\t\t\t\tsource_filename = \"{ASSET_DIR}/anims/{ported.clip.name}.dmx\"\n"
            "\t\t\t\t\t\tstart_frame = -1\n"
            "\t\t\t\t\t\tend_frame = -1\n"
            "\t\t\t\t\t\tframerate = -1.0\n"
            "\t\t\t\t\t\ttake = 0\n"
            "\t\t\t\t\t\treverse = false\n"
            "\t\t\t\t\t},\n")


def write_vmdl(ported: list[Ported]) -> None:
    scale = ("\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"ModelModifier_ScaleAndMirror\"\n\t\t\t\t\t\tscale = 0.3937\n"
             "\t\t\t\t\t\tmirror_x = false\n\t\t\t\t\t\tmirror_y = false\n\t\t\t\t\t\tmirror_z = false\n"
             "\t\t\t\t\t\tflip_bone_forward = false\n\t\t\t\t\t\tswap_left_and_right_bones = false\n\t\t\t\t\t},\n")
    # The body is never drawn (the zombie mesh is), but its materials still need to resolve.
    remaps = {"male_body.vmat": "models/citizen_human/bodies/male/body_mode_dark.vmat",
              "underwear.vmat": "models/citizen_human/bodies/underwear.vmat"}
    materials = ("\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n\t\t\t\t\t\tremaps = \n\t\t\t\t\t\t[\n"
                 + "".join(f"\t\t\t\t\t\t\t{{\n\t\t\t\t\t\t\t\tfrom = \"{a}\"\n\t\t\t\t\t\t\t\tto = \"{b}\"\n\t\t\t\t\t\t\t}},\n"
                           for a, b in remaps.items())
                 + "\t\t\t\t\t\t]\n\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n"
                 "\t\t\t\t\t},\n")
    body = ("\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"RenderMeshFile\"\n\t\t\t\t\t\tname = \"body\"\n"
            "\t\t\t\t\t\tfilename = \"models/citizen_human/bodies/male/citizen_human_body_male.fbx\"\n"
            "\t\t\t\t\t\timport_translation = [ 0.0, 0.0, 0.0 ]\n\t\t\t\t\t\timport_rotation = [ 0.0, 0.0, 0.0 ]\n"
            "\t\t\t\t\t\timport_scale = 1.0\n\t\t\t\t\t\talign_origin_x_type = \"None\"\n"
            "\t\t\t\t\t\talign_origin_y_type = \"None\"\n\t\t\t\t\t\talign_origin_z_type = \"None\"\n"
            "\t\t\t\t\t\tparent_bone = \"\"\n"
            "\t\t\t\t\t\timport_filter = \n\t\t\t\t\t\t{\n\t\t\t\t\t\t\texclude_by_default = false\n"
            "\t\t\t\t\t\t\texception_list = [  ]\n\t\t\t\t\t\t}\n\t\t\t\t\t},\n")
    text = ("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} "
            "format:modeldoc30:version{8c2d7a91-9c42-4bf0-883a-5a3b1762d4f1} -->\n"
            "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren = \n\t\t[\n"
            + node_list("ModelModifierList", scale)
            + node_list("MaterialGroupList", materials)
            + node_list("RenderMeshList", body)
            + node_list("AnimationList", "".join(anim_file(p) for p in ported), "\t\t\t\tdefault_root_bone_name = \"pelvis\"\n")
            + node_list("BoneMarkupList", prefab("human_bonemarkuplist"))
            + node_list("AnimConstraintList", prefab("human_animconstraintlist"))
            + node_list("PhysicsJointList", prefab("human_physicsjointlist"))
            + node_list("PhysicsShapeList", prefab("human_physicsshapelist"))
            + node_list("HitboxSetList", prefab("human_hitboxsetlist"))
            + "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n"
            "\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n")
    path = ROOT / "Assets" / ASSET_DIR / "zombie_driver.vmdl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_table(ported: list[Ported]) -> None:
    def entry(p: Ported) -> str:
        return f'new( "{p.clip.name}", {(len(p.world) - 1) / p.fps:.3f}f, {p.speed:.1f}f, {p.hit:.2f}f )'

    walks = [p for p in ported if p.clip.kind == "move" and p.clip.name.startswith("walk")]
    run = next(p for p in ported if p.clip.name == "run")
    idle = next(p for p in ported if p.clip.kind == "idle")
    attacks = [p for p in ported if p.clip.kind == "attack"]
    text = ("// Generated by Tools/zombie_anims.py: the sequences of models/zombie/zombie_driver.vmdl.\n"
            "namespace Facepunch;\n\n"
            "public readonly struct ZombieClip\n{\n"
            "\tpublic readonly string Name;\n"
            "\t/// <summary>Seconds.</summary>\n"
            "\tpublic readonly float Duration;\n"
            "\t/// <summary>Ground speed the clip was authored for (units/s); 0 for clips that stay put.</summary>\n"
            "\tpublic readonly float Speed;\n"
            "\t/// <summary>Attacks: seconds from the start to the swing's furthest reach.</summary>\n"
            "\tpublic readonly float Hit;\n\n"
            "\tpublic ZombieClip( string name, float duration, float speed, float hit )\n\t{\n"
            "\t\tName = name;\n\t\tDuration = duration;\n\t\tSpeed = speed;\n\t\tHit = hit;\n\t}\n}\n\n"
            "/// <summary>No More Room in Hell's zombie mocap, ported onto the citizen skeleton.</summary>\n"
            "public static class ZombieClips\n{\n"
            f"\tpublic static readonly ZombieClip Idle = {entry(idle)};\n"
            f"\tpublic static readonly ZombieClip Run = {entry(run)};\n"
            "\tpublic static readonly ZombieClip[] Walks =\n\t{\n"
            + "".join(f"\t\t{entry(p)},\n" for p in walks)
            + "\t};\n"
            "\tpublic static readonly ZombieClip[] Attacks =\n\t{\n"
            + "".join(f"\t\t{entry(p)},\n" for p in attacks)
            + "\t};\n}\n")
    (ROOT / "Code" / "NPCs" / "Zombies" / "ZombieClips.cs").write_text(text, encoding="utf-8", newline="\n")


def port_all(args) -> tuple[Skeleton, list[Ported]]:
    cit = read_model_skeleton(Path(args.citizen_data))
    dirs = {"walk": Path(args.walk_pack), "run": Path(args.run_pack)}
    fps = {pack: qc_fps(d / "classic.qc") for pack, d in dirs.items()}
    ported = [port(c, cit, dirs[c.pack], fps[c.pack].get(c.source.lower(), 30.0)) for c in CLIPS]
    return cit, ported


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--walk-pack", default=str(WORK / "decompiled/nmrih_3255961963"))
    parser.add_argument("--run-pack", default=str(WORK / "decompiled/nmrih_3255991053"))
    parser.add_argument("--citizen-data", default=str(WORK / "zombie_work/citizen_human_male_data.txt"))
    args = parser.parse_args()

    cit, ported = port_all(args)
    nodes = list(zip(cit.names, cit.parents))
    for p in ported:
        frames = [local_frames(cit, w) for w in p.world]
        dmx.write_animation(ROOT / "Assets" / ASSET_DIR / "anims" / f"{p.clip.name}.dmx", p.clip.name, nodes, frames, p.fps)
        print(f"{p.clip.name:10} {p.clip.source:9} {len(frames):4} frames @ {p.fps:g} fps"
              + (f"  speed {p.speed:.1f}" if p.speed else "") + (f"  hit {p.hit:.2f}s" if p.clip.kind == "attack" else ""))
    write_vmdl(ported)
    write_table(ported)


if __name__ == "__main__":
    main()
