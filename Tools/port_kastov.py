#!/usr/bin/env python3
"""Port a MWII Kastov-platform viewmodel into HC1: the Kastov 762 (the AK-47 from GMod workshop item 3803722029),
the Kastov-74u, the PP-19-01 Vityaz (the Vaznev-9K), the RPK, the PP-19 Bizon, the AK-105, the Vepr-12, the M16A4
(on MWII's AR rig, which has the same bone and clip names), or MW2019's FN P90, MP7A1 or Steyr AUG A3 (whose rigs have
them too), see kastov_weapons.py.

The CoD viewmodel's animations drive CoD arm bones, so they are retargeted onto HC1's own arm skeleton (the
bones of models/first_person/v_first_person_arms_human.vmdl). The exported viewmodel carries those arm bones
plus the gun's bones; the prefab bone-merges the HC1 arms onto it, like every other HC1 viewmodel.

Outputs in the gun's folder (DMX, which ModelDoc imports as-is: X forward, Y left, Z up), shown for the 762:
  models/v_kastov.dmx         viewmodel mesh + skeleton (bind pose = level gun for the gunsmith, arms at idle)
  models/anims/<clip>.dmx     viewmodel animations (and Weapon.reload_variants' reloads, the RPK's box magazines)
  models/anims/sway.dmx       the M4's look sway poses: idle, then one pose per frame (kastov_sway.py)
  models/w_kastov.dmx         static world model, laid out like the M4's (grip mount near the origin)
  models/[vw]_kastov_<piece>.dmx  the optional_meshes bodygroup pieces for each model (and muzzle_tip_<tip_choices>)
  models/[vw]_kastov_<group>_<choice>.dmx  the part_choices bodygroup choices for each model (the 74u's)

Inputs that are not in the repo:
  Weapon.decompiled  Crowbar decompiles of the viewmodel (v_akm.mdl, v_akilo74.mdl, v_aviktor.mdl,
                     vm_iw9_rkilo.mdl, v_iw9_beta.mdl, vm_iw9_akilo105.mdl, v_vecho.mdl, vm_iw9_mike16.mdl,
                     v_papa90.mdl, v_mpapa7.mdl, v_augolf.mdl) and its attachment models.
  HC1_GLTF    Source2Viewer glTF exports (with animations) of the cloud models v_m4a1.vmdl (its IdlePose is HC1's
              rifle grip, the retarget reference) and v_first_person_arms_human.vmdl (preview render only).

Run: python Tools/port_kastov.py [--weapon kastov762|kastov74u|vityaz|rpk|bizon|ak105|vepr12|m16|p90|mp7|aug|uzi|fal|famas|m18|mcx|l85a2|hk416]
     [--preview]
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

import kastov_dmx
import kastov_sway
import kastov_weapons
from kastov_gltf import GltfModel
import kastov_smd
from kastov_smd import Smd, euler_to_mat, matrix, orthonormalize
from kastov_weapons import Weapon

HC1_GLTF = Path(r"D:\tmp\hc1-mw22-tools\kastov_work")

# HC1 forearm twist bones share the hand's twist about the forearm axis at these fractions.
TWIST_FRACTIONS = (0.0, 0.2594, 0.7406)

# Where the world model puts the pistol grip mount, matching w_m4a1's RearGrip attachment point (X forward, Z up).
WORLD_GRIP = np.array([-3.0, 0.0, 3.0])

# Weapon.left_grip applies in full while the left wrist is within the first distance of its idle grip on the gun,
# fading out by the second, so the hand keeps CoD's motion when it leaves the handguard (reloads).
GRIP_FADE = (1.0, 3.0)

# v_m4a1's sprint: a still pose and a looping run bob, both deltas on weapon_root (Weapon.m4_sprint).
M4_SPRINT_POSE = "Shared_Sprint_Pose_delta"
M4_SPRINT_BOB = "Shared_Sprint_delta"


def cod_arm_map(side: str) -> dict[str, str]:
    """HC1 arm bone -> CoD bone, for side 'R' or 'L'."""
    cod = "ri" if side == "R" else "le"
    result = {
        f"clavicle_{side}": f"j_clavicle_{cod}",
        f"arm_upper_{side}": f"j_shoulder_{cod}",
        f"arm_lower_{side}": f"j_elbow_{cod}",
        f"hand_{side}": f"j_wrist_{cod}",
    }
    for hc1, name in (("index", "index"), ("middle", "mid"), ("ring", "ring"), ("pinky", "pinky")):
        result[f"finger_{hc1}_meta_{side}"] = f"j_meta{name}_{cod}_1"
        for joint in range(3):
            result[f"finger_{hc1}_{joint}_{side}"] = f"j_{name}_{cod}_{joint + 1}"
    for joint in range(3):
        result[f"finger_thumb_{joint}_{side}"] = f"j_thumb_{cod}_{joint + 1}"
    return result


def finger_chain(finger: str, side: str) -> list[str]:
    chain = [] if finger == "thumb" else [f"finger_{finger}_meta_{side}"]
    return chain + [f"finger_{finger}_{joint}_{side}" for joint in range(3)]


def twist_bones(side: str) -> list[str]:
    return [f"arm_lower_{side}_twistctrl{i}" for i in range(3)] + [f"arm_lower_{side}_twist{i}" for i in range(3)]


def normalize(vector: np.ndarray, fallback=(0.0, 0.0, 1.0)) -> np.ndarray:
    length = np.linalg.norm(vector)
    return vector / length if length > 1e-9 else np.array(fallback, float)


def frame_from(primary: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Orthonormal frame with its first axis along primary and its second as close to reference as possible."""
    first = normalize(primary)
    second = normalize(reference - np.dot(reference, first) * first)
    return np.column_stack([first, second, np.cross(first, second)])


def anatomical_frames(pose: dict[str, np.ndarray], name: dict[str, str], side: str) -> dict[str, np.ndarray]:
    """World-space anatomical frames of one arm, keyed by HC1 bone name; pose is looked up through name."""
    position = lambda bone: pose[name[bone]][:3, 3]
    x_axis = lambda bone: pose[name[bone]][:3, 0]
    hand, lower, upper, clavicle = f"hand_{side}", f"arm_lower_{side}", f"arm_upper_{side}", f"clavicle_{side}"
    across = normalize(position(f"finger_index_0_{side}") - position(f"finger_pinky_0_{side}"))
    along = normalize(position(f"finger_middle_0_{side}") - position(hand))
    palm_normal = normalize(np.cross(along, across))
    hinge = np.cross(position(lower) - position(upper), position(hand) - position(lower))

    frames = {
        clavicle: frame_from(x_axis(clavicle), np.array([0.0, 0.0, 1.0])),
        upper: frame_from(x_axis(upper), hinge),
        lower: frame_from(x_axis(lower), hinge),
        hand: frame_from(along, across),
    }
    for finger in ("index", "middle", "ring", "pinky", "thumb"):
        reference = palm_normal if finger == "thumb" else across
        for bone in finger_chain(finger, side):
            frames[bone] = frame_from(x_axis(bone), reference)
    return frames


def twist_angle(rotation: np.ndarray) -> float:
    """Signed twist of a rotation about its X axis (swing-twist decomposition)."""
    w = math.sqrt(max(0.0, 1.0 + rotation[0, 0] + rotation[1, 1] + rotation[2, 2])) / 2.0
    x = (rotation[2, 1] - rotation[1, 2]) / (4.0 * w) if w > 1e-6 else 1.0
    return 2.0 * math.atan2(x, w)


def rot_x(angle: float) -> np.ndarray:
    return euler_to_mat(angle, 0.0, 0.0)


def local_matrices(smd: Smd, frame) -> dict[str, np.ndarray]:
    """Parent-relative 4x4 transform of every bone of one (dense) SMD frame, by bone name."""
    result = {}
    for index, (name, _) in enumerate(smd.nodes):
        position, rotation = frame.get(index, (np.zeros(3), np.zeros(3)))
        result[name] = matrix(position, euler_to_mat(*rotation))
    return result


def world_from_locals(smd: Smd, locals_: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    world: dict[str, np.ndarray] = {}

    def solve(index: int) -> np.ndarray:
        name, parent = smd.nodes[index]
        if name not in world:
            world[name] = locals_[name] if parent < 0 else solve(parent) @ locals_[name]
        return world[name]

    for index in range(len(smd.nodes)):
        solve(index)
    return world


def named_world(smd: Smd, frame) -> dict[str, np.ndarray]:
    world = smd.world(frame)
    return {smd.name(index): world[index] for index in range(len(world))}


def compose(base: Smd, base_frame: int, delta: Smd, corrective: Smd) -> list[dict[str, np.ndarray]]:
    """CoD world poses of base[base_frame] with the delta layer (delta[f] minus corrective[0]) on top.

    studiomdl's 'subtract' + 'delta' (post) semantics, per bone in parent space: rotation base * c^-1 * d,
    position base + d - c.

    Only the channels (position, rotation) the delta actually animates are layered. The rest hold export filler
    (zeros, bind values or values that don't match the corrective), which would otherwise throw e.g. the magazine
    rounds off the gun, or the RPK's carry handle (swung by rotation only, its position left at zero) off the barrel.
    """
    base_local = local_matrices(base, base.dense_frames()[base_frame])
    corrective_local = local_matrices(corrective, corrective.dense_frames()[0])
    delta_frames = delta.dense_frames()
    animated: dict[str, tuple[bool, bool]] = {}  # bone -> (position animated, rotation animated)
    for index, (name, _) in enumerate(delta.nodes):
        values = np.array([np.concatenate(frame[index]) for frame in delta_frames if index in frame])
        if len(values):
            moving = np.abs(values - values[0]).max(axis=0) > 1e-4
            if moving.any():
                animated[name] = (bool(moving[:3].any()), bool(moving[3:].any()))
    poses = []
    for frame in delta_frames:
        current = local_matrices(delta, frame)
        composed = {}
        for name, value in base_local.items():
            if name in animated and name in corrective_local:
                moves, turns = animated[name]
                c, d = corrective_local[name], current[name]
                position = value[:3, 3] + d[:3, 3] - c[:3, 3] if moves else value[:3, 3]
                rotation = orthonormalize(value[:3, :3] @ c[:3, :3].T @ d[:3, :3]) if turns else value[:3, :3]
                composed[name] = matrix(position, rotation)
            else:
                composed[name] = value
        poses.append(world_from_locals(base, composed))
    return poses


def scale_rotation(rotation: np.ndarray, factor: float) -> np.ndarray:
    """The rotation about the same axis by factor times its angle."""
    angle = math.acos(float(np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0)))
    if angle < 1e-9:
        return np.eye(3)
    axis = np.array([rotation[2, 1] - rotation[1, 2], rotation[0, 2] - rotation[2, 0],
                     rotation[1, 0] - rotation[0, 1]]) / (2.0 * math.sin(angle))
    k = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    turned = angle * factor
    return np.eye(3) + math.sin(turned) * k + (1.0 - math.cos(turned)) * (k @ k)


def rotation_between(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Smallest rotation taking direction source onto direction target."""
    a, b = normalize(source), normalize(target)
    axis = np.cross(a, b)
    sin, cos = np.linalg.norm(axis), float(np.dot(a, b))
    if sin < 1e-9:
        return np.eye(3)
    k = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]]) / sin
    return np.eye(3) + sin * k + (1.0 - cos) * (k @ k)


def two_bone_ik(shoulder: np.ndarray, elbow: np.ndarray, wrist: np.ndarray, target: np.ndarray):
    """New shoulder, elbow and wrist transforms putting the wrist on target, keeping bone lengths, the shoulder's
    position and the elbow's bend direction."""
    s, e, w, t = shoulder[:3, 3], elbow[:3, 3], wrist[:3, 3], target[:3, 3]
    upper, lower = np.linalg.norm(e - s), np.linalg.norm(w - e)
    axis = normalize(t - s)
    reach = float(np.clip(np.linalg.norm(t - s), abs(upper - lower) + 1e-4, upper + lower - 1e-4))
    pole = normalize(e - s - np.dot(e - s, axis) * axis)
    cos = (upper ** 2 + reach ** 2 - lower ** 2) / (2.0 * upper * reach)
    new_e = s + axis * upper * cos + pole * upper * math.sqrt(max(0.0, 1.0 - cos ** 2))
    swing_upper = rotation_between(e - s, new_e - s)
    new_w = new_e + normalize(t - new_e) * lower
    swing_lower = rotation_between(swing_upper @ (w - e), new_w - new_e)
    return (matrix(s, swing_upper @ shoulder[:3, :3]),
            matrix(new_e, swing_lower @ swing_upper @ elbow[:3, :3]),
            matrix(new_w, target[:3, :3]))


def pin_hands(smd: Smd, world: dict[str, np.ndarray], rest: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Puts each wrist back where the rest pose holds it on the gun (tag_sling), bending the arm to reach.

    CoD's additive movement layers (a_walk, a_sprint) move the gun and the arms separately and leave the hands to
    the engine's runtime IK (the tag_ik_loc_le/ri bones); without this the hands slide off the gun while sprinting.
    """
    children: dict[str, list[str]] = {}
    for name, parent in smd.nodes:
        if parent >= 0:
            children.setdefault(smd.name(parent), []).append(name)
    result = dict(world)
    gun_move = world["tag_sling"] @ np.linalg.inv(rest["tag_sling"])
    for side in ("le", "ri"):
        clavicle, shoulder, elbow, wrist = (f"j_{bone}_{side}" for bone in ("clavicle", "shoulder", "elbow", "wrist"))
        target = gun_move @ rest[wrist]
        arm = {bone: world[bone].copy() for bone in (clavicle, shoulder, elbow, wrist)}
        # A gun pushed beyond the arm's reach (the 762's sprint, by up to half a unit) pulls the whole arm after it
        # rather than leaving the hand short; the shift lands at the shoulder, out of view.
        gap = target[:3, 3] - arm[shoulder][:3, 3]
        length = (np.linalg.norm(arm[elbow][:3, 3] - arm[shoulder][:3, 3])
                  + np.linalg.norm(arm[wrist][:3, 3] - arm[elbow][:3, 3]))
        excess = np.linalg.norm(gap) - 0.999 * length
        if excess > 0:
            for transform in arm.values():
                transform[:3, 3] += normalize(gap) * excess
        result[clavicle] = arm[clavicle]
        result.update(zip((shoulder, elbow, wrist), two_bone_ik(arm[shoulder], arm[elbow], arm[wrist], target)))

        def follow(bone: str):
            for child in children.get(bone, []):
                if child not in arm:
                    result[child] = result[bone] @ np.linalg.inv(world[bone]) @ world[child]
                follow(child)

        follow(clavicle)
    return result


class ArmRetarget:
    """Maps CoD arm bone transforms onto HC1's arm skeleton.

    Each HC1 bone takes its CoD counterpart's rotation times a constant correction Q, chosen so that both bones'
    anatomical frames (built from the two rigs' rifle-gripping poses) line up. Hands are pinned to the CoD wrists so
    they stay on the gun; the upper arm is scaled about the wrist to HC1's arm length, and the fingers use HC1's own
    bone lengths, so the HC1 arm mesh is never stretched.
    """

    def __init__(self, cod_pose: dict[str, np.ndarray], hc1_pose: dict[str, np.ndarray], hc1_parent: dict[str, str]):
        self.parent = hc1_parent
        self.correction: dict[str, np.ndarray] = {}
        self.offset: dict[str, np.ndarray] = {}
        self.arm_scale: dict[str, float] = {}
        self.maps = {side: cod_arm_map(side) for side in "RL"}
        for side, mapping in self.maps.items():
            cod_frames = anatomical_frames(cod_pose, mapping, side)
            hc1_frames = anatomical_frames(hc1_pose, {bone: bone for bone in mapping}, side)
            for bone, cod_bone in mapping.items():
                cod_local = cod_pose[cod_bone][:3, :3].T @ cod_frames[bone]
                hc1_local = hc1_pose[bone][:3, :3].T @ hc1_frames[bone]
                self.correction[bone] = orthonormalize(cod_local @ hc1_local.T)
                parent = hc1_parent[bone]
                self.offset[bone] = (np.linalg.inv(hc1_pose[parent]) @ hc1_pose[bone])[:3, 3]

            def length(pose, a, b):
                return np.linalg.norm(pose[a][:3, 3] - pose[b][:3, 3])

            hc1_arm = (length(hc1_pose, f"arm_upper_{side}", f"arm_lower_{side}")
                       + length(hc1_pose, f"arm_lower_{side}", f"hand_{side}"))
            cod_arm = (length(cod_pose, mapping[f"arm_upper_{side}"], mapping[f"arm_lower_{side}"])
                       + length(cod_pose, mapping[f"arm_lower_{side}"], mapping[f"hand_{side}"]))
            self.arm_scale[side] = hc1_arm / cod_arm

    def solve(self, cod_world: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """HC1 arm bone world transforms for one frame of CoD bone world transforms."""
        world: dict[str, np.ndarray] = {}
        for side, mapping in self.maps.items():
            rotation = {bone: orthonormalize(cod_world[cod][:3, :3] @ self.correction[bone])
                        for bone, cod in mapping.items()}
            wrist = cod_world[mapping[f"hand_{side}"]][:3, 3]
            for bone in (f"clavicle_{side}", f"arm_upper_{side}", f"arm_lower_{side}"):
                position = wrist + self.arm_scale[side] * (cod_world[mapping[bone]][:3, 3] - wrist)
                world[bone] = matrix(position, rotation[bone])
            hand = matrix(wrist, rotation[f"hand_{side}"])
            world[f"hand_{side}"] = hand
            for finger in ("index", "middle", "ring", "pinky", "thumb"):
                parent = hand
                for bone in finger_chain(finger, side):
                    position = parent[:3, :3] @ self.offset[bone] + parent[:3, 3]
                    world[bone] = matrix(position, rotation[bone])
                    parent = world[bone]

            lower = world[f"arm_lower_{side}"]
            angle = twist_angle(lower[:3, :3].T @ hand[:3, :3])
            forearm = hand[:3, 3] - lower[:3, 3]
            for index, fraction in enumerate(TWIST_FRACTIONS):
                twisted = matrix(lower[:3, 3] + forearm * index / 3.0, lower[:3, :3] @ rot_x(fraction * angle))
                world[f"arm_lower_{side}_twistctrl{index}"] = twisted
                world[f"arm_lower_{side}_twist{index}"] = twisted.copy()
        return world


def move_pieces(triangles: list[tuple[str, list]], moves) -> list[tuple[str, list]]:
    """Weapon.part_moves: each connected piece (triangles sharing a vertex position) whose bounds lie inside a box
    moves by that box's offset, in the model's own space."""
    keys: dict[tuple, int] = {}
    corners = [[keys.setdefault(tuple(np.round(position, 4)), len(keys)) for position, *_ in vertices]
               for _, vertices in triangles]
    parent = list(range(len(keys)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b, c in corners:
        for x, y in ((a, b), (b, c)):
            parent[find(x)] = find(y)
    pieces: dict[int, list[int]] = {}
    for index, triangle in enumerate(corners):
        pieces.setdefault(find(triangle[0]), []).append(index)
    shift = [None] * len(triangles)
    for members in pieces.values():
        points = np.array([position for index in members for position, *_ in triangles[index][1]])
        low, high = points.min(0), points.max(0)
        for lowest, highest, offset in moves:
            if np.all(low >= lowest) and np.all(high <= highest):
                for index in members:
                    shift[index] = np.asarray(offset, float)
                break
    return [(material, vertices if offset is None
             else [(position + offset, normal, uv, links) for position, normal, uv, links in vertices])
            for (material, vertices), offset in zip(triangles, shift)]


def smd_file(path: str) -> str:
    """The SMD file of a mesh path: the first of several joined by +, without its #bone or @material filter."""
    return path.partition("+")[0].partition("@")[0].partition("#")[0]


class Kastov:
    """Loads the CoD rig and HC1 references and builds the output skeleton."""

    def __init__(self, weapon: Weapon):
        self.weapon = weapon
        # Before any SMD is read: a pistol rig's gun root comes in as tag_sling (Weapon.bone_renames).
        kastov_smd.BONE_RENAMES.clear()
        kastov_smd.BONE_RENAMES.update(weapon.bone_renames)
        self.decompiled = weapon.decompiled
        self.cod_anims = weapon.decompiled / weapon.cod_anims
        self.extra_bones = weapon.extra_bones
        # CoD lengths -> HC1's (Weapon.model_scale): the whole pose shrinks about the camera (to_model), and so do the
        # meshes (_vertex), the extra bones' offsets and the attachment models' bones (part_bone).
        self.shrink = 1.0 / weapon.model_scale
        self.ref = Smd(self.decompiled / smd_file(weapon.vm_meshes[0]))
        self.idle = Smd(self.cod_anims / "idle.smd")
        idle_world = named_world(self.idle, self.idle.dense_frames()[0])
        self.camera0_inv = np.linalg.inv(idle_world["tag_camera"])

        m4 = self.m4 = GltfModel(HC1_GLTF / "v_m4a1.glb")
        self.hc1_parent = m4.hierarchy()
        hc1_pose = m4.pose("IdlePose", 0.0)
        self.arms = ArmRetarget(self.to_model(idle_world, weapon.aim), hc1_pose, self.hc1_parent)
        # The left wrist's idle grip, in tag_sling space, for Weapon.left_grip.
        idle_model = self.to_model(idle_world, weapon.hip)
        self.left_grip = (np.linalg.inv(idle_model["tag_sling"]) @ idle_model["j_wrist_le"])[:3, 3]
        # Weapon.grip_pose: bone -> (corrective, delta) parent-space transforms, for the bones it moves.
        self.cod_parent = [(name, self.idle.name(parent) if parent >= 0 else None) for name, parent in self.idle.nodes]
        self.grip_delta = self._grip_delta(weapon.grip_pose) if weapon.grip_pose else {}
        # Weapon.slide_lock: the bones it moves, in idle's parent space with the delta on (the QC's empty_offset at 1).
        rest = local_matrices(self.idle, self.idle.dense_frames()[0])
        self.slide_lock = {
            name: matrix(rest[name][:3, 3] + d[:3, 3] - c[:3, 3],
                         orthonormalize(rest[name][:3, :3] @ c[:3, :3].T @ d[:3, :3]))
            for name, (c, d) in (self._grip_delta(weapon.slide_lock).items() if weapon.slide_lock else ())}

        # Output skeleton: camera, HC1 arms under root, then the CoD gun bones and extras.
        arm_bones = set()
        for side in "RL":
            arm_bones.update(cod_arm_map(side))
            arm_bones.update(twist_bones(side))
        self.nodes: list[tuple[str, int]] = [("camera", -1), ("root", -1)]
        for bone in self.hc1_parent:
            if bone in arm_bones:
                self.nodes.append((bone, -2))
        gun = self._gun_bones()
        for bone in gun:
            self.nodes.append((bone, -2))
        for bone in self.extra_bones:
            self.nodes.append((bone, -2))
        # The hands' IK targets on the gun, under tag_sling (kastov_sway.py).
        for bone in kastov_sway.IK_TARGETS:
            self.nodes.append((bone, -2))
        self.index = {name: i for i, (name, _) in enumerate(self.nodes)}
        # The gun's root bones stay roots (the Vityaz's tag_sling hangs off a GMod hand helper bone, which isn't kept).
        cod_parent = {name: (self.ref.name(parent) if parent >= 0 and self.ref.name(parent) in gun else None)
                      for name, parent in self.ref.nodes}
        resolved = []
        for name, parent in self.nodes:
            if parent == -2:
                if name in arm_bones:
                    parent_name = self.hc1_parent[name]
                elif name in self.extra_bones:
                    parent_name = self.extra_bones[name][0]
                elif name in kastov_sway.IK_TARGETS:
                    parent_name = "tag_sling"
                else:
                    parent_name = cod_parent[name]
                parent = self.index[parent_name] if parent_name is not None else -1
            resolved.append((name, parent))
        self.nodes = resolved
        self.gun_bones = gun
        self.hc1_root = hc1_pose["root"].copy()
        self.bind = self.pose(idle_world, weapon.hip)

    def _gun_bones(self) -> list[str]:
        children: dict[int, list[int]] = {}
        for index, (_, parent) in enumerate(self.ref.nodes):
            children.setdefault(parent, []).append(index)
        result = []

        def visit(index: int):
            result.append(self.ref.name(index))
            for child in children.get(index, []):
                visit(child)

        visit(self.ref.index("tag_sling"))
        # j_gun is its own root on the Kastovia rigs; on the M16's it hangs off tag_sling, so it's in already.
        if "j_gun" not in result:
            visit(self.ref.index("j_gun"))
        return result

    def to_model(self, cod_world: dict[str, np.ndarray], offset: np.ndarray) -> dict[str, np.ndarray]:
        """CoD bone transforms -> HC1 viewmodel space (origin and axes at the idle camera), offset applied to all but
        the camera, then shrunk about the camera by Weapon.model_scale: the gun comes out its real size, as far from
        the eye as that makes it, so the view through the sights doesn't change."""
        result = {}
        for name, world in cod_world.items():
            model = self.camera0_inv @ world
            if name != "tag_camera":
                model = offset @ model
            if self.shrink != 1.0:
                model = matrix(model[:3, 3] * self.shrink, model[:3, :3])
            result[name] = model
        return result

    def _grip_delta(self, clip: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        """The bones a one-frame delta clip (Weapon.grip_pose, Weapon.slide_lock) moves from its corrective, with both
        parent-space transforms."""
        delta, corrective = Smd(self.cod_anims / f"{clip}.smd"), Smd(self.cod_anims / f"{clip}_corrective_animation.smd")
        d, c = local_matrices(delta, delta.dense_frames()[0]), local_matrices(corrective, corrective.dense_frames()[0])
        moved = {}
        for name in d:
            turn = c[name][:3, :3].T @ d[name][:3, :3]
            angle = math.acos(float(np.clip((np.trace(turn) - 1.0) / 2.0, -1.0, 1.0)))
            if np.linalg.norm(d[name][:3, 3] - c[name][:3, 3]) > 1e-4 or angle > 1e-4:
                moved[name] = (c[name], d[name])
        return moved

    def with_grip_pose(self, cod_world: dict[str, np.ndarray], weight: float) -> dict[str, np.ndarray]:
        """CoD world poses with Weapon.grip_pose layered on at weight: studiomdl's subtract + delta per bone in parent
        space (as compose does), each bone's change scaled by weight; the bones below follow."""
        result = dict(cod_world)
        moved = set()
        for name, parent in self.cod_parent:  # parents first
            parent_world = result[parent] if parent is not None else np.eye(4)
            if name in self.grip_delta:
                c, d = self.grip_delta[name]
                base = np.linalg.inv(cod_world[parent]) @ cod_world[name] if parent is not None else cod_world[name]
                position = base[:3, 3] + weight * (d[:3, 3] - c[:3, 3])
                rotation = orthonormalize(base[:3, :3] @ scale_rotation(c[:3, :3].T @ d[:3, :3], weight))
                result[name] = parent_world @ matrix(position, rotation)
            elif parent in moved:
                result[name] = parent_world @ np.linalg.inv(cod_world[parent]) @ cod_world[name]
            else:
                continue
            moved.add(name)
        return result

    def pose(self, cod_world: dict[str, np.ndarray], offset: np.ndarray) -> list[np.ndarray]:
        """Model-space world transform of every output bone for one CoD pose."""
        cod = self.to_model(cod_world, offset)
        fit, weight = self.weapon.left_grip, self.grip_weight(cod)
        if self.grip_delta and weight > 0:
            # CoD's grip pose holds while the left hand is on the handguard (the QC's grip events); the same fade as
            # left_grip stands in for them.
            cod = self.to_model(self.with_grip_pose(cod_world, weight), offset)
        if fit is not None and weight > 0:
            # The whole left arm moves, so the arm mesh isn't stretched; the fingers open after the solve.
            shift = cod["tag_sling"][:3, :3] @ (weight * np.array(fit.shift, float))
            cod = dict(cod)
            for bone in cod_arm_map("L").values():
                cod[bone] = matrix(cod[bone][:3, 3] + shift, cod[bone][:3, :3])
        arms = self.arms.solve(cod)
        if fit is not None and weight > 0:
            solved = dict(arms)
            for finger in ("index", "middle", "ring", "pinky", "thumb"):
                opening = weight * (fit.thumb if finger == "thumb" else fit.fingers)
                for bone in finger_chain(finger, "L"):
                    if "meta" in bone:
                        continue
                    parent = self.hc1_parent[bone]
                    local = np.linalg.inv(solved[parent]) @ solved[bone]
                    arms[bone] = arms[parent] @ matrix(local[:3, 3], scale_rotation(local[:3, :3], 1.0 - opening))
        world: list[np.ndarray] = []
        for name, parent in self.nodes:
            if name == "camera":
                world.append(cod["tag_camera"])
            elif name == "root":
                world.append(self.hc1_root)
            elif name in arms:
                world.append(arms[name])
            elif name in self.extra_bones:
                world.append(world[parent] @ matrix(self.extra_bones[name][1] * self.shrink, np.eye(3)))
            elif name in kastov_sway.IK_TARGETS:
                # Where its hand is, so the animgraph's IK changes nothing on the clip's own frames.
                world.append(arms[kastov_sway.IK_TARGETS[name]])
            elif name in self.weapon.moved_bones:
                parent_name, offset = self.weapon.moved_bones[name]
                parent_world = cod[parent_name]
                world.append(matrix(parent_world[:3, 3] + parent_world[:3, :3] @ (offset * self.shrink), cod[name][:3, :3]))
            else:
                world.append(cod[name])
        return world

    def grip_weight(self, cod: dict[str, np.ndarray]) -> float:
        """How much of Weapon.left_grip applies: 1 with the left wrist on its idle grip, 0 away from it (GRIP_FADE)."""
        wrist = (np.linalg.inv(cod["tag_sling"]) @ cod["j_wrist_le"])[:3, 3]
        near, far = GRIP_FADE
        return float(np.clip((far - np.linalg.norm(wrist - self.left_grip)) / (far - near), 0.0, 1.0))

    def locals_(self, world: list[np.ndarray]) -> list[np.ndarray]:
        return [world[index] if parent < 0 else np.linalg.inv(world[parent]) @ world[index]
                for index, (_, parent) in enumerate(self.nodes)]

    def play(self, clip: str, offset: np.ndarray, frames: slice | None = None) -> list[list[np.ndarray]]:
        smd = self.idle if clip == "idle" else Smd(self.cod_anims / f"{clip}.smd")
        dense = smd.dense_frames()
        if frames is not None:
            dense = dense[frames]
        return [self.pose(named_world(smd, frame), offset) for frame in dense]

    def layered(self, base: str, delta: str, offset: np.ndarray) -> list[list[np.ndarray]]:
        base_smd = self.idle if base == "idle" else Smd(self.cod_anims / f"{base}.smd")
        poses = compose(base_smd, 0, Smd(self.cod_anims / f"{delta}.smd"),
                        Smd(self.cod_anims / f"{delta}_corrective_animation.smd"))
        rest = named_world(base_smd, base_smd.dense_frames()[0])
        return [self.pose(pin_hands(base_smd, world, rest), offset) for world in poses]

    def m4_sprint(self, offset: np.ndarray) -> tuple[list[list[np.ndarray]], int]:
        """HC1's M4 sprint on this gun's idle pose: one loop of the M4's run bob, and its frame rate.

        The M4's sprint moves only its weapon_root (M4_SPRINT_POSE, then the M4_SPRINT_BOB loop, both added to
        IdlePose); its hands follow by IK and its camera bone holds still. That motion moves this whole gun, about the
        point that sits where weapon_root does relative to the M4's right hand, and the hands are pinned back on.
        """
        m4_idle = self.m4.pose("IdlePose")
        root = m4_idle["weapon_root"]
        still = self.m4.pose(M4_SPRINT_POSE)["weapon_root"]
        pivot = matrix(self.bind[self.index["hand_R"]][:3, 3] - m4_idle["hand_R"][:3, 3], np.eye(3))
        view = offset @ self.camera0_inv
        rest = named_world(self.idle, self.idle.dense_frames()[0])
        # A whole frame rate (the DMX stores it as an int) that fits the loop exactly; like the CoD loops, the last
        # frame repeats the first.
        length = self.m4.length(M4_SPRINT_BOB)
        fps = next((rate for rate in range(30, 61) if abs(length * rate - round(length * rate)) < 1e-3), 30)
        count = round(length * fps)
        frames = []
        for index in range(count + 1):
            bob = self.m4.pose(M4_SPRINT_BOB, index * length / count)["weapon_root"]
            sprint = matrix(root[:3, 3] + still[:3, 3] + bob[:3, 3], root[:3, :3] @ still[:3, :3] @ bob[:3, :3])
            move = pivot @ sprint @ np.linalg.inv(root) @ np.linalg.inv(pivot)
            # A move in model space is one with 1/shrink the offset in CoD's (to_model shrinks CoD's lengths).
            move = matrix(move[:3, 3] / self.shrink, move[:3, :3])
            cod_move = np.linalg.inv(view) @ move @ view
            world = dict(rest)
            for bone in self.gun_bones:
                world[bone] = cod_move @ rest[bone]
            frames.append(self.pose(pin_hands(self.idle, world, rest), offset))
        return frames, fps

    def m4_sway(self, offset: np.ndarray) -> list[list[np.ndarray]]:
        """HC1's M4 look sway on this gun's idle pose (kastov_sway.py): idle's first frame, then one frame per
        kastov_sway.poses() entry.

        Each frame adds its share of one of the M4's weapon_root deltas to IdlePose, as the M4's animgraph adds it,
        and moves the gun and the hands' IK targets that way about the point that sits where weapon_root does
        relative to the M4's right hand, as m4_sprint does. The arms stay where they are: the animgraph's IK takes
        the hands along, as the M4's does.
        """
        m4_idle = self.m4.pose("IdlePose")
        root = m4_idle["weapon_root"]
        pivot = matrix(self.bind[self.index["hand_R"]][:3, 3] - m4_idle["hand_R"][:3, 3], np.eye(3))
        rest = self.play("idle", offset, slice(0, 1))[0]
        gun = set(self.gun_bones) | set(self.extra_bones) | set(kastov_sway.IK_TARGETS)
        moving = [name in gun for name, _ in self.nodes]
        frames = [rest]
        for _, m4_pose, share in kastov_sway.poses():
            delta = self.m4.pose(m4_pose)["weapon_root"]
            swayed = matrix(root[:3, 3] + share * delta[:3, 3], root[:3, :3] @ scale_rotation(delta[:3, :3], share))
            # In model space: m4_sprint's move before it goes into CoD's.
            move = pivot @ swayed @ np.linalg.inv(root) @ np.linalg.inv(pivot)
            frames.append([move @ world if moves else world for world, moves in zip(rest, moving)])
        return frames

    def steady_fire(self, offset: np.ndarray, count: int) -> list[list[np.ndarray]]:
        """The fire clip's first count frames with the gun and arms held still (Weapon.steady_fire): every bone keeps
        its idle parent-space transform except the gun's moving parts (the bones under tag_sling or j_gun, but not the
        spare magazine's) and the right hand's fingers, which play the clip."""
        parent = dict(self.cod_parent)

        def under(bone: str | None, ancestor: str) -> bool:
            while bone is not None:
                if bone == ancestor:
                    return True
                bone = parent.get(bone)
            return False

        fingers = {cod for hc1, cod in cod_arm_map("R").items() if hc1.startswith("finger_")}
        playing = {bone for bone in parent
                   if bone in fingers or (bone not in ("tag_sling", "j_gun") and not under(bone, self.weapon.spare_mag)
                                          and (under(bone, "tag_sling") or under(bone, "j_gun")))}
        rest = local_matrices(self.idle, self.idle.dense_frames()[0])
        fire = Smd(self.cod_anims / "fire.smd")
        frames = []
        for frame in fire.dense_frames()[:count]:
            local = local_matrices(fire, frame)
            steady = {bone: local[bone] if bone in playing and bone in local else value for bone, value in rest.items()}
            frames.append(self.pose(world_from_locals(self.idle, steady), offset))
        return frames

    def clips(self):
        """(name, frames, fps) of every exported animation."""
        hip, aim, sprint = self.weapon.hip, self.weapon.aim, self.weapon.sprint
        yield "idle", self.play("idle", hip), 30
        yield "draw", self.play("draw", hip), 30
        if self.weapon.steady_fire:
            yield "fire", self.steady_fire(hip, self.weapon.steady_fire), 30
        else:
            yield "fire", self.play("fire", hip), 30
        if self.weapon.ads_fire:
            # At the hip pose, like fire: the animgraph's ADS layer adds the aim on top.
            yield "fire_ads", self.play(self.weapon.ads_fire, hip), 30
        if self.slide_lock:
            # The last round: the slide stays back (and the barrel tilted) once it's there. Every other state but
            # reload_empty adds empty's slide lock on top while the magazine is empty (the animgraph's b_empty).
            assert not self.weapon.steady_fire, "a slide lock needs the fire clip as it is"
            yield "fire_empty", self.slide_held("fire", hip), 30
            if self.weapon.ads_fire:
                yield "fire_ads_empty", self.slide_held(self.weapon.ads_fire, hip), 30
            yield "empty", self.slide_locked(hip) * 2, 30
        factory = self.weapon.factory_reload
        yield "reload", self.play(f"reload{factory}", hip), 30
        yield "reload_empty", self.play(self.empty_reload(factory), hip), 30
        for suffix in self.weapon.reload_variants:
            yield f"reload{suffix}", self.play(self.weapon.reload_clip_overrides.get(f"reload{suffix}", f"reload{suffix}"), hip), 30
            yield f"reload_empty{suffix}", self.play(self.empty_reload(suffix), hip), 30
        yield "ads", self.ads() * 2, 30
        yield "walk", self.layered("idle", "a_walk", hip), 30
        if self.weapon.m4_sprint:
            yield "sprint", *self.m4_sprint(hip)
        else:
            yield "sprint", self.layered("sprint_in", "a_sprint", sprint), 25
        # The weapon held low (HC1's lowered toggle): the still sprint pose.
        lowered = self.weapon.lowered if self.weapon.lowered is not None else sprint
        yield "lowered", self.play("sprint_in", lowered, slice(0, 1)) * 2, 30
        # The look sway's poses, which the animgraph blends by how fast the view turns.
        yield "sway", self.m4_sway(hip), 30

    def slide_locked(self, offset: np.ndarray) -> list[list[np.ndarray]]:
        """Idle's first frame with the slide locked back (Weapon.slide_lock): the one-frame empty pose."""
        local = local_matrices(self.idle, self.idle.dense_frames()[0])
        local.update(self.slide_lock)
        return [self.pose(world_from_locals(self.idle, local), offset)]

    def slide_held(self, clip: str, offset: np.ndarray) -> list[list[np.ndarray]]:
        """A fire clip whose slide stays back from the frame it's furthest back on: the bones the slide lock moves
        hold their locked pose from then on, as a real slide stops on the slide stop after the last round."""
        smd = Smd(self.cod_anims / f"{clip}.smd")
        frames = [local_matrices(smd, frame) for frame in smd.dense_frames()]
        # The slide is the bone the lock moves furthest; its locked place is where the clip's recoil takes it.
        slide = max(self.slide_lock,
                    key=lambda name: np.linalg.norm(self.slide_lock[name][:3, 3] - frames[0][name][:3, 3]))
        locked = self.slide_lock[slide][:3, 3]
        back = int(np.argmin([np.linalg.norm(local[slide][:3, 3] - locked) for local in frames]))
        poses = []
        for index, local in enumerate(frames):
            if index >= back:
                local = {**local, **self.slide_lock}
            poses.append(self.pose(world_from_locals(smd, local), offset))
        return poses

    def empty_reload(self, suffix: str) -> str:
        """The CoD clip of a magazine's empty reload: reload_empty<suffix>, or reload<suffix>_empty (the AK-105's
        60-rounder's)."""
        empty = f"reload_empty{suffix}"
        return empty if (self.cod_anims / f"{empty}.smd").exists() else f"reload{suffix}_empty"

    def ads(self) -> list[list[np.ndarray]]:
        """The one-frame ADS pose (Weapon.ads_pose)."""
        clip, frame = self.weapon.ads_pose
        return self.play(clip, self.weapon.aim, frame)

    # --- meshes -------------------------------------------------------------------------------------------------

    def triangles(self) -> list[tuple[str, list]]:
        """All default gun meshes, moved into the output bind pose and skinned to output bones."""
        out = []
        for path in self.weapon.vm_meshes:
            out += self.part_triangles(path, None)
        for path, reference_path in self.weapon.part_meshes:
            out += self.part_triangles(path, reference_path)
        return out

    def optional_triangles(self) -> dict[str, list[tuple[str, list]]]:
        """The bodygroup pieces' meshes, by piece name; other barrels' tips are muzzle_tip_<name>."""
        pieces = {name: self.part_triangles(path, reference_path)
                  for name, (path, reference_path) in self.weapon.optional_meshes.items()}
        pieces.update({f"muzzle_tip_{name}": self.part_triangles(path, reference_path)
                       for name, (path, reference_path) in self.weapon.tip_choices.items()})
        pieces.update({f"{group}_{name}": self.part_triangles(path, reference_path)
                       for group, choices in self.weapon.optional_variants.items()
                       for name, path, reference_path in choices if path})
        return pieces

    def choice_triangles(self) -> dict[str, list[tuple[str, list]]]:
        """The part_choices meshes, by <group>_<choice>. Each model's own skeleton is its reference pose."""
        return {f"{group}_{choice}": self.part_triangles(path, path)
                for group, choices in self.weapon.part_choices.items() for choice, path in choices}

    def factory_triangles(self) -> list[tuple[str, list]]:
        """The factory part (choice 0) of every part_choices group."""
        return [triangle for choices in self.weapon.part_choices.values()
                for triangle in self.part_triangles(choices[0][1], choices[0][1])]

    def part_reference(self, reference_path: str) -> dict[str, np.ndarray]:
        reference = Smd(self.decompiled / smd_file(reference_path))
        return named_world(reference, reference.dense_frames()[0])

    def part_triangles(self, path: str, reference_path: str | None) -> list[tuple[str, list]]:
        """One attachment model's mesh, placed as the viewmodel's bone-merge would place it; with no reference, a mesh
        on the viewmodel itself. A path ending in #bone,bone keeps only the triangles on those bones, and #!bone,bone
        only the rest: CoD hides some pieces by their bones (the M16's rail cover), and a magazine's rounds are one
        mesh. After that, @material,material keeps only the triangles in those materials, and @!material,material
        only the rest: some of MW2019's meshes carry a second copy of a piece in another material (the AUG's).
        Paths joined by + are one piece from several models on one skeleton (the M18's slide and its sights, which
        its attachment model has as a bodygroup), each placed by its own reference pose when the reference is the
        path itself. A model in Weapon.part_mounts is placed on its rig bone instead, as the MW base's VElements are."""
        if "+" in path:
            pieces = path.split("+")
            references = pieces if reference_path == path else [reference_path] * len(pieces)
            return [triangle for piece, reference in zip(pieces, references)
                    for triangle in self.part_triangles(piece, reference)]
        mount = self.weapon.part_mounts.get(path)
        moves = self.weapon.part_moves.get(path)
        path, _, materials = path.partition("@")
        path, _, bones = path.partition("#")
        smd = Smd(self.decompiled / path)
        triangles = smd.triangles
        if materials:
            keep = not materials.startswith("!")
            wanted = set(materials.lstrip("!").split(","))
            triangles = [(material, vertices) for material, vertices in triangles if (material in wanted) == keep]
        if bones:
            keep = not bones.startswith("!")
            wanted = {smd.index(name) for name in bones.lstrip("!").split(",")}
            triangles = [(material, vertices) for material, vertices in triangles
                         if any(bone in wanted and weight > 0.5
                                for *_, links in vertices for bone, weight in links) == keep]
        if moves:
            triangles = move_pieces(triangles, moves)
        bind = smd.world(smd.dense_frames()[0])
        ref_world = self.part_reference(reference_path) if reference_path is not None else None
        return [(material, [self._vertex(vertex, smd, bind, ref_world, mount) for vertex in vertices])
                for material, vertices in triangles]

    def _vertex(self, vertex, smd: Smd, bind: list[np.ndarray], part_pose, mount=None):
        position, normal, uv, links = vertex
        new_position = np.zeros(3)
        new_normal = np.zeros(3)
        new_links = []
        for bone, weight in links:
            name = smd.name(bone)
            target, extra = name, np.eye(4)
            if mount is not None:
                # A VElement (Weapon.part_mounts): the model's origin at the rig bone, moved by the offset along the
                # bone's own axes, and every vertex where the model's own bind pose puts it from that origin.
                target, offset = mount
                extra = matrix(offset, np.eye(3)) @ bind[bone]
            elif part_pose is not None:
                # Bones missing from the viewmodel follow their nearest merged ancestor, as bone-merge does, and so do
                # Weapon.unmerged_bones.
                current = bone
                while smd.name(current) not in self.index or smd.name(current) in self.weapon.unmerged_bones:
                    current = smd.nodes[current][1]
                target = smd.name(current)
                extra = np.linalg.inv(part_pose[target]) @ part_pose[name]
            index = self.index[target]
            # The vertex's offset from its bone shrinks like the pose (to_model); the normal is normalized below.
            skin = self.bind[index] @ np.diag([self.shrink] * 3 + [1.0]) @ extra @ np.linalg.inv(bind[bone])
            new_position += weight * (skin[:3, :3] @ position + skin[:3, 3])
            new_normal += weight * (skin[:3, :3] @ normal)
            new_links.append((index, weight))
        return new_position, normalize(new_normal), (uv[0], uv[1]), new_links

    def world_frame(self) -> np.ndarray:
        """Viewmodel bind space -> world model space: gun level along +X, pistol grip mount at WORLD_GRIP."""
        gun = self.bind[self.index["tag_sling"]]
        axes = orthonormalize(gun[:3, :3])
        grip = self.bind[self.index["tag_pistolgrip_attach"]][:3, 3]
        frame = matrix(np.zeros(3), axes.T)
        frame[:3, 3] = WORLD_GRIP - axes.T @ grip
        return frame

    def presentation(self) -> list[np.ndarray]:
        """The bind pose written to the viewmodel. The gunsmith shows the bind pose (animation off) and frames it by
        the model's bounds, so the gun lies level in the world model's layout (the M4's grip mount at WORLD_GRIP) and the
        spare magazine sits inside the fitted one instead of parked behind the camera. The arms keep the idle pose.
        Every animation sets every bone, so none of this shows in first person."""
        frame = self.world_frame()
        spare = self.index[self.weapon.spare_mag]
        onto_mag = self.bind[self.index["j_mag1"]] @ np.linalg.inv(self.bind[spare])
        gun = set(self.gun_bones) | set(self.extra_bones) | set(kastov_sway.IK_TARGETS)
        result = []
        for index, (name, _) in enumerate(self.nodes):
            if self._descends_from(index, spare):
                result.append(frame @ onto_mag @ self.bind[index])
            elif name in gun:
                result.append(frame @ self.bind[index])
            else:
                result.append(self.bind[index])
        return result

    def _descends_from(self, index: int, ancestor: int) -> bool:
        while index >= 0:
            if index == ancestor:
                return True
            index = self.nodes[index][1]
        return False

    def rebind(self, triangles, pose: list[np.ndarray]) -> list[tuple[str, list]]:
        """Moves triangles from the idle bind pose into another bind pose, following each vertex's bone weights."""
        moves = [target @ np.linalg.inv(source) for target, source in zip(pose, self.bind)]
        out = []
        for material, vertices in triangles:
            moved = []
            for position, normal, uv, links in vertices:
                move = sum(weight * moves[bone] for bone, weight in links)
                moved.append((move[:3, :3] @ position + move[:3, 3], normalize(move[:3, :3] @ normal), uv, links))
            out.append((material, moved))
        return out

    def world_triangles(self, triangles) -> tuple[list[tuple[str, int]], list[np.ndarray], list[tuple[str, list]]]:
        """Static world model: every triangle not on the spare magazine, rigid on one root bone."""
        frame = self.world_frame()
        spare = self.index[self.weapon.spare_mag]
        out = []
        for material, vertices in triangles:
            if any(bone == spare for _, _, _, links in vertices for bone, weight in links if weight > 0.01):
                continue
            moved = [(frame[:3, :3] @ p + frame[:3, 3], frame[:3, :3] @ n, uv, [(0, 1.0)])
                     for p, n, uv, _ in vertices]
            out.append((material, moved))
        return [("root", -1)], [np.eye(4)], out

    def world_points(self) -> dict[str, np.ndarray]:
        """Attachment positions in world model space."""
        frame = self.world_frame()
        # A pistol's rig has no left-hand IK tag (tag_ik_loc_le), so that one is left out.
        points = {name: (frame @ self.bind[self.index[bone]])[:3, 3]
                  for name, bone in (("muzzle", "muzzle"), ("eject", "tag_brass"), ("left_hand", "tag_ik_loc_le"),
                                     ("grip", "tag_pistolgrip_attach"), ("mag", "tag_mag_attach"),
                                     ("stock", "tag_stock_attach"), ("barrel", "tag_barrel_attach"),
                                     ("optic", "tag_reflex")) if bone in self.index}
        for bone in self.weapon.report_bones:
            points[bone] = (frame @ self.part_bone(bone))[:3, 3]
        return points

    def part_bone(self, bone: str) -> np.ndarray:
        """Bind transform of a viewmodel bone, or of a bone of an attachment model merged onto it: it follows its
        nearest ancestor the viewmodel has, as bone-merge (and _vertex) places it. The model's root isn't always that
        ancestor: the FAL's handguard hangs its bones off tag_sling under a j_gun root, and the rig's j_gun is elsewhere."""
        if bone in self.index:
            return self.bind[self.index[bone]]
        factory_parts = [(path, path) for choices in self.weapon.part_choices.values() for _, path in choices[:1]]
        optional_parts = [(path, reference) for path, reference in self.weapon.optional_meshes.values() if reference]
        for _, reference_path in self.weapon.part_meshes + factory_parts + optional_parts:
            smd = Smd(self.decompiled / smd_file(reference_path))
            reference = named_world(smd, smd.dense_frames()[0])
            if bone in reference:
                current = smd.index(bone)
                while smd.name(current) not in self.index or smd.name(current) in self.weapon.unmerged_bones:
                    current = smd.nodes[current][1]
                ancestor = smd.name(current)
                relative = np.linalg.inv(reference[ancestor]) @ reference[bone]
                return self.bind[self.index[ancestor]] @ matrix(relative[:3, 3] * self.shrink, relative[:3, :3])
        raise KeyError(bone)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    kastov_weapons.add_argument(parser)
    parser.add_argument("--preview", action="store_true", help="also render preview images to the scratch folder")
    args = parser.parse_args()
    weapon = kastov_weapons.WEAPONS[args.weapon]
    v_name, w_name = f"v_{weapon.model}", f"w_{weapon.model}"

    kastov = Kastov(weapon)
    triangles = kastov.triangles()
    models = weapon.folder / "models"
    presentation = kastov.presentation()
    kastov_dmx.write_model(models / f"{v_name}.dmx", v_name, kastov.nodes, kastov.locals_(presentation),
                           kastov.rebind(triangles, presentation))
    for name, pieces in {**kastov.optional_triangles(), **kastov.choice_triangles()}.items():
        kastov_dmx.write_model(models / f"{v_name}_{name}.dmx", f"{v_name}_{name}", kastov.nodes,
                               kastov.locals_(presentation), kastov.rebind(pieces, presentation))
        nodes, bind, world_pieces = kastov.world_triangles(pieces)
        kastov_dmx.write_model(models / f"{w_name}_{name}.dmx", f"{w_name}_{name}", nodes, bind, world_pieces)
    sling = presentation[kastov.index["tag_sling"]]
    quaternion = kastov_dmx.rotation_to_quaternion(sling[:3, :3])
    print(f"  bind tag_sling: {','.join(f'{v:.3f}' for v in sling[:3, 3])} / {','.join(f'{v:.6f}' for v in quaternion)}")
    idle = None
    for name, frames, fps in kastov.clips():
        kastov_dmx.write_animation(models / "anims" / f"{name}.dmx", name, kastov.nodes,
                                   [kastov.locals_(world) for world in frames], fps)
        print(f"  {name}: {len(frames)} frames @ {fps}")
        if name == "idle":
            idle = frames
    nodes, bind, world_triangles = kastov.world_triangles(triangles)
    kastov_dmx.write_model(models / f"{w_name}.dmx", w_name, nodes, bind, world_triangles)
    print(f"bones={len(kastov.nodes)} triangles={len(triangles)} world triangles={len(world_triangles)}")
    for name, point in kastov.world_points().items():
        print(f"  world {name}: {point[0]:.3f},{point[1]:.3f},{point[2]:.3f}")
    if args.preview:
        import kastov_preview
        kastov_preview.render(kastov, triangles + kastov.factory_triangles(), idle[0],
                              HC1_GLTF / f"preview_{weapon.name}_idle.png")


if __name__ == "__main__":
    main()
