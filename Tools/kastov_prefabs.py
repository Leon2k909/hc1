#!/usr/bin/env python3
"""Write a Kastov-pipeline gun's HC1 prefabs, equipment resource and HUD icon, using the M4A1's as templates. For
the 762:

  Assets/Weapons/Kastov/kastov762.equip
  Assets/Weapons/Kastov/weapon_kastov762.prefab   gameplay components (ammo, shooting, reload, recoil, ADS)
  Assets/Weapons/Kastov/vm_kastov762.prefab       viewmodel: v_kastov + bone-merged HC1 arms
  Assets/Weapons/Kastov/wm_kastov762.prefab       third-person model held in hold_R
  Assets/Weapons/Kastov/mount_kastov762.prefab    holstered model
  Assets/ui/weapons/guns/kastov762_01.png         white silhouette icon, like the other guns
  and adds the gun to the eligible weapons of the gunsmith parts that fit its slots (FITTING_PARTS).
  A gun with part_choices (the 74u) also gets its own parts, one per non-factory choice:
  Assets/gunsmith/<gun>/<folder>/att_vm_p04_<model>.gnsmth

The 74u's gameplay prefab and icon were made by hand (see Prefabs.gameplay), so for it only the prefab's ADS fields
are set.

GUIDs are derived from the template GUIDs, so re-running produces identical files.
Run: python Tools/kastov_prefabs.py [--weapon kastov762|kastov74u|vityaz]
"""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

import kastov_weapons
from kastov_weapons import Weapon

PROJECT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT / "Assets"
M4 = ASSETS / "Weapons" / "M4A1"
MP5 = ASSETS / "Weapons" / "MP5"
EXTRACTED = Path(r"D:\tmp\hc1-mw22-tools\extracted")
NAMESPACE = uuid.UUID("5b0e4f1c-2f7e-4d8a-9a51-7c4f0e2b9d63")
GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass(frozen=True)
class Part:
    """One of a gun's own gunsmith parts: a non-factory choice of a Weapon.part_choices bodygroup.

    Recoil scales are relative to the factory part, from what the real part does (a fixed, heavier stock steadies
    the gun; no stock leaves nothing to brace against), not the addon's game-balance numbers.
    """
    name: str
    description: str
    vertical_recoil: float = 1.0
    horizontal_recoil: float = 1.0
    magazine_capacity: int = 0
    reload_time: float = 1.0
    # A barrel of another length: how far it moves the muzzle (GunsmithPart.MuzzleShift).
    muzzle_shift: tuple[float, float, float] | None = None

    def effect(self) -> str:
        """The recoil change in words, as the gunsmith lists it."""
        def change(scale: float) -> str:
            return f"{round(abs(1 - scale) * 100)}% {'less' if scale < 1 else 'more'}"
        if self.muzzle_shift:
            # GunsmithAttachmentEffects: a "long" barrel's damage falls off later.
            return "The bullet leaves faster, so damage falls off later."
        if self.magazine_capacity:
            return f"Reloads {round(abs(1 - self.reload_time) * 100)}% {'faster' if self.reload_time < 1 else 'slower'}."
        if self.vertical_recoil == self.horizontal_recoil == 1:
            return "No effect on recoil."
        if self.vertical_recoil == self.horizontal_recoil:
            return f"{change(self.vertical_recoil)} recoil.".capitalize()
        parts = [f"{change(scale)} {axis} recoil" for axis, scale in
                 (("vertical", self.vertical_recoil), ("horizontal", self.horizontal_recoil)) if scale != 1]
        return (", ".join(parts) + ".").capitalize()


# part_choices group -> (gunsmith category, folder under Assets/gunsmith/<gun>).
PART_SLOTS = {"stock": ("Stock", "stocks"), "pistol_grip": ("RearGrip", "pistol_grips"),
              "magazine": ("Magazine", "magazines"), "barrel": ("Barrel", "barrels")}

# The 74u's own parts, by part_choices choice, named as in the addon. Its factory parts are the side-folding
# K-Bloc stock, the KSTV Standard Issue grip and the 30-round magazine.
PARTS_74U = {
    "ar_akilo74_stockno_v0": Part("VLK Stockless", "Stock removed: nothing to brace against the shoulder.", 1.4, 1.4),
    "ar_akilo74_stockskel_v0": Part("Otrezat Stock", "Cut-down skeleton stock. Lighter, with a smaller buttpad.",
                                    1.05, 1.05),
    "ar_akilo_stock_v0": Part("Spetsnaz S10 Stock", "Full-length polymer folding stock with a wider buttpad.",
                              0.92, 0.92),
    "ar_akilo_stockh_v0": Part("Ivanov Wood Stock", "Fixed wooden stock. Heavier and rigid.", 0.9, 0.9),
    "ar_akilo_stocktac_v0": Part("FT Tac-Elite Stock", "Adjustable tactical stock with a rubber buttpad.",
                                 0.92, 0.92),
    "ar_akilo_stocktac02_v0": Part("Markeev R7 Stock", "Adjustable tactical stock.", 0.93, 0.93),
    "ar_akilo_stockwire_v0": Part("Prolite TL3 Stock", "Light wire stock. Flexes and shifts on the shoulder.",
                                  1.05, 1.08),
    "sh_vecho_stock_v0": Part("Broadside FCT", "Full-length fixed stock.", 0.92, 0.92),
    "sh_vecho_stocktac_v0": Part("EXO-Tac", "Adjustable skeleton tactical stock.", 0.95, 0.95),
    "lm_rkilo_stock_v0": Part("KSTV-RPK Factory", "The RPK's heavy wooden stock.", 0.88, 0.88),
    "lm_rkilo_stockh_v0": Part("Heavy Support Stock", "Heavy fixed stock with a support hand rest.", 0.85, 0.85),
    "ar_akilo_griptac_v0": Part("TRUE-TAC Grip", "Textured rubber grip.", 0.98, 0.98),
    "ar_akilo_gripstdy_v0": Part("Ivanov ST-70 Grip", "Ergonomic grip with a palm swell.", 0.97, 1.0),
    "ar_akilo_gripass_v0": Part("DEMO-X2 Grip", "Slim lightweight grip."),
    "sh_vecho_pgrip_v0": Part("KV Shotgun Grip", "Shotgun-style pistol grip."),
    "sh_vecho_gripsnp_v0": Part("Brace LS", "Grip with an extended backstrap that braces the wrist.", 0.96, 0.97),
    "ar_akilo105_smag_v0": Part("20 Round Mag", "Short 20-round magazine. Lighter and quicker to seat.",
                                magazine_capacity=20, reload_time=0.95),
    "ar_akilo105_xmag_v0": Part("45 Round Mag", "RPK-74 45-round magazine. Longer and heavier to change.",
                                magazine_capacity=45, reload_time=1.08),
}

# The Kastovia platform parts the Vityaz shares with the 74u, plus the 74u's factory stock.
_KASTOVIA_PARTS = {**PARTS_74U, "ar_akilo74_stock_v0": Part("K-Bloc Stock", "The AKS-74U's side-folding skeleton stock.")}
_VITYAZ_CHOICES = kastov_weapons.VITYAZ.part_choices


def _relative_to(factory: Part, part: Part) -> Part:
    """A part's recoil relative to another factory part than the 74u's."""
    return replace(part, vertical_recoil=round(part.vertical_recoil / factory.vertical_recoil, 2),
                   horizontal_recoil=round(part.horizontal_recoil / factory.horizontal_recoil, 2))


# The Vityaz's own parts. Its factory stock is the Spetsnaz S10, so the stocks' recoil is relative to that; its factory
# grip is the 74u's.
PARTS_VITYAZ = {
    **{choice: _relative_to(PARTS_74U["ar_akilo_stock_v0"], _KASTOVIA_PARTS[choice])
       for choice, _ in _VITYAZ_CHOICES["stock"][1:]},
    **{choice: _KASTOVIA_PARTS[choice] for choice, _ in _VITYAZ_CHOICES["pistol_grip"][1:]},
    "sm_aviktor_xmag_v0": Part("45 Round Mag", "Extended 9mm magazine. Longer and heavier to change.",
                               magazine_capacity=45, reload_time=1.08),
    # port_kastov: the long barrel's brake (barlong_tip.smd) sits 5.433 ahead of the factory one (bartip.smd).
    "sm_aviktor_barlightlong_v0": Part("SA Response III Long Barrel",
                                       "Longer barrel under the factory handguard, with the same muzzle brake.",
                                       muzzle_shift=(5.433, 0.0, 0.0)),
}


@dataclass(frozen=True)
class Gameplay:
    """A generated gameplay prefab's values, on the M4's prefab: fields by component type (Equipment is on the root,
    the rest on Functions). `borrow` first copies the named fields from another gun's gameplay prefab."""
    fields: dict[str, dict]
    borrow: tuple[Path, dict[str, list[str]]] | None = None


# The 762's sounds, and reload foley at the CoD reload's sound-event frames (30 fps).
SOUNDS_762 = "sounds/weapons/kastov"
RELOAD_SOUNDS = {0: "reload_01", 12: "reload_02", 36: "reload_03", 72: "reload_04", 78: "reload_05"}
EMPTY_RELOAD_SOUNDS = {0: "reload_empty_01", 8: "reload_empty_02", 38: "reload_empty_03", 41: "reload_empty_04",
                       69: "reload_empty_05", 72: "reload_empty_06", 86: "reload_empty_07"}


def sound_times(frames: dict[int, str]) -> dict[str, str]:
    return {f"{round(frame / 30, 3):g}": f"{SOUNDS_762}/kastov_{name}.sound" for frame, name in frames.items()}


def gameplay_762() -> Gameplay:
    return Gameplay({
        "WeaponAmmo": {"Ammo": 30, "MaxAmmo": 30},
        "Shootable": {"BaseDamage": 26, "FireRate": 600, "ShootSound": f"{SOUNDS_762}/kastov_shot.sound",
                      "SuppressedShootSound": f"{SOUNDS_762}/kastov_shot_sup.sound",
                      "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic"},
        # Ammo is back in at the CoD reloads' "ready" frames (74 and 91); the last foley plays just before.
        "Reloadable": {"ReloadTime": 2.65, "EmptyReloadTime": 3.05, "TimedReloadSounds": sound_times(RELOAD_SOUNDS),
                       "EmptyReloadSounds": sound_times(EMPTY_RELOAD_SOUNDS)},
        "ShootRecoil": {"Scale": "2.4,5.8"},  # a little more kick than the M4's 2,5
    })


def gameplay_vityaz() -> Gameplay:
    """A 9mm SMG like the MP5: its damage, falloff, range, 9mm effects, recoil pattern, view punch and move speed."""
    assets = load(ASSETS / "Weapons" / "Vityaz" / "vityaz_assets.json")
    sounds = assets["sounds"]

    def times(timed: dict[str, str]) -> dict[str, str]:
        return {f"{float(time):g}": sound for time, sound in timed.items()}

    return Gameplay(
        {
            "WeaponAmmo": {"Ammo": 30, "MaxAmmo": 30},
            # The real Vityaz's cyclic rate (700-750 rpm); automatic and semi, no burst.
            "Shootable": {"FireRate": 750, "ShootSound": sounds["fire"],
                          "SuppressedShootSound": sounds["fire_suppressed"],
                          "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic"},
            # Ammo is back in once the gun is level again (2.5s, and 3.2s after the empty reload's bolt pull).
            "Reloadable": {"ReloadTime": 2.5, "EmptyReloadTime": 3.1,
                           "TimedReloadSounds": times(assets["reload_sounds"]),
                           "EmptyReloadSounds": times(assets["empty_reload_sounds"])},
            # A straight blowback 9mm with a heavier bolt than the MP5's roller delay: a little more kick.
            "ShootRecoil": {"Scale": "0.5,3"},
        },
        borrow=(MP5 / "weapon_mp5.prefab", {
            "Equipment": ["SpeedPenalty"],
            "Shootable": ["BaseDamage", "BaseDamageFalloff", "MaxRange", "EjectionPrefab", "MuzzleFlashPrefab",
                          "MuzzleFlashScale", "MuzzleSmokeScale", "SuppressorFireRateScale"],
            "ShootRecoil": ["RecoilPattern", "HorizontalSpread", "VerticalSpread"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
        }),
    )


@dataclass(frozen=True)
class Prefabs:
    """The HC1 side of a gun: its equipment resource, prefabs and gunsmith mounts."""
    title: str
    description: str
    price: int
    deploy_sound: str
    # The addon's spawn icon the HUD icon is drawn from: a VTF under EXTRACTED, without the extension. None keeps
    # the existing icon.
    icon_source: str | None
    # A renderer's BodyGroups is its mesh-group mask: the models' Parts.DefaultMask (body and muzzle tip shown, rails
    # hidden; see kastov_vmdl.BODY_GROUPS). Read it again from the compiled model if the bodygroups change.
    default_mesh_groups: int
    # Viewmodel bone objects the prefab references (name -> parent, local position, local rotation x y z w), from
    # the v_ model's bind pose. The renderer's CreateBoneObjects adopts them and drives them with the animation.
    bones: dict[str, tuple[str | None, str, str]]
    # World model points (port_kastov.py prints them): muzzle, ejection port, left hand on the handguard.
    world_muzzle: str
    world_eject: str
    world_left_hand: str
    # Gunsmith slots taking the M4's MW22 parts: category, where the part's origin goes on the gun (world model space,
    # which is also the viewmodel's bind space; the parts reach forward from their origin), where it sits on the M4
    # (the parts' BindPosition), and the bodygroups a fitted part switches on. In first person the parts follow
    # MOUNT_BONE; the world model has no such bone, so they mount on the model itself.
    slots: list[tuple[str, tuple, tuple, dict[str, int]]]
    # Charms hang from their slot's own transform, so the viewmodel's slot rides on the tag_sling bone object: the left
    # side of the receiver, above the pistol grip.
    charm: tuple[float, float, float]
    # Optic ADS offsets are calibrated on the M4; this moves them to the gun's sight line (ManualOffset).
    optic_aim_correction: str
    # The gameplay prefab's values; None when the prefab exists already, and only its ADS fields are written.
    gameplay: Callable[[], Gameplay] | None
    category: str = "AssaultRifle"
    kill_reward: int = 300
    # The bind pose puts the grip where the M4's is; raise the gun to sit at the M4's height in the gunsmith.
    gunsmith_offset: str = "0,0,4"
    # Salts the derived GUIDs, keeping each gun's prefabs apart (the 762's predate it).
    guid_salt: str = ""
    # The gun's own parts (Part), by Weapon.part_choices choice, and where each part_choices group's slot sits (world
    # model space; the gunsmith frames the slot there).
    parts: dict[str, Part] = field(default_factory=dict)
    part_slot_positions: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    # A part_choices group slot's FittedBodygroups, e.g. a longer barrel showing its own muzzle tip
    # (Weapon.tip_choices).
    part_slot_bodygroups: dict[str, dict[str, int]] = field(default_factory=dict)


PREFABS = {
    "kastov762": Prefabs(
        title="Kastov 762",
        description="Hard-hitting 7.62 assault rifle. Fires slower and kicks harder than the M4.",
        price=2700,
        deploy_sound="sounds/weapons/kastov/kastov_raise.sound",
        icon_source="3803722029/materials/vgui/entities/mg_mw4_ak47",
        default_mesh_groups=341,
        bones={
            "tag_sling": (None, "-4.673,0,4.129", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "9.391,0.001,0.47", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "15.828,0,0", "0,0,0,1"),
            "tag_brass": ("tag_sling", "7.148,-0.636,1.023", "0.000049,0.000049,-0.707038,0.707175"),
        },
        world_muzzle="20.546,0,4.599",
        world_eject="2.476,-0.636,5.152",
        world_left_hand="9,0,2.6",
        slots=[
            ("Optic", (-2.45, 0, 6.302), (0.25, 0, 8.73), {"optic_rail": 1}),  # on the side-mount rail (-4.2 to 2.2)
            ("Muzzle", (18.515, 0, 4.599), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # tag_tip, for the slant brake
            ("Underbarrel", (8.55, 0, 3.127), (8.3, 0, 6.2), {"grip_rail": 1}),  # the front of the bottom rail (6.5 to 10.6)
            ("Laser", (7.35, -1.131, 5.14), (8.6, -1.22, 7.4147), {"laser_rail": 1}),  # on the right-side rail (7.4 to 10.1)
        ],
        charm=(0.0, 1.75, 2.3),
        # Measured in-game: puts the camera where it sits relative to a fitted optic on the M4 (dev_optic_correction
        # to retune).
        optic_aim_correction="4.084,0,-1.208",
        gameplay=gameplay_762,
    ),
    "kastov74u": Prefabs(
        title="Kastov-74u",
        description="Compact carbine. Fast fire rate, hits hard up close, falls off at range.",
        price=2300,
        deploy_sound="weapons/kastov74u/sounds/ks74u.raise.sound",
        icon_source=None,
        # The rails' mask plus the factory stock, grip and magazine (read from the compiled model).
        default_mesh_groups=605028693,
        bones={
            "tag_sling": (None, "-6.971,-0.573,3.351", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "11.839,0.573,2.436", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "8.378,0,-1.398", "0,0,0,1"),
            "tag_brass": ("tag_sling", "9.103,-0.17,1.884", "0.00001,0.00001,-0.707094,0.707119"),
        },
        world_muzzle="13.246,0,4.389",
        world_eject="2.132,-0.743,5.235",
        world_left_hand="9.1,0,2.35",  # the front of the handguard, where the hand-made world model had it
        slots=[
            ("Optic", (-2.2, 0, 6.311), (0.25, 0, 8.73), {"optic_rail": 1}),  # on the side-mount rail (-4.3 to 0.25)
            ("Muzzle", (10.264, 0, 4.383), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # tag_tip, for the muzzle booster
            ("Underbarrel", (8.1, 0, 3.107), (8.3, 0, 6.2), {"grip_rail": 1}),  # the front of the bottom rail (5.6 to 10.2)
            ("Laser", (7.44, -1.092, 5.382), (8.6, -1.22, 7.4147), {"laser_rail": 1}),  # tag_laser_attach (rail 7.45 to 10)
        ],
        charm=(0.0, 1.75, 2.3),
        # The 762's measured correction moved by how far the 74u's ADS pose puts its optic slot from the 762's
        # (port_kastov: Kastov.ads, the slot through tag_sling). Tune in-game with dev_optic_correction.
        optic_aim_correction="3.162,0,-1.226",
        gameplay=None,
        guid_salt="kastov74u/",
        parts=PARTS_74U,
        # port_kastov.py's world stock, grip and mag points (tag_stock_attach, tag_pistolgrip_attach, tag_mag_attach).
        part_slot_positions={"stock": (-5.716, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0), "magazine": (2.516, 0, 3.257)},
    ),
    "vityaz": Prefabs(
        title="PP-19-01 Vityaz",
        description="Russian 9x19mm submachine gun built on the AK-74. Straight blowback, 30-round magazine.",
        price=1500,
        deploy_sound="weapons/vityaz/sounds/vityaz.raise.sound",
        icon_source="3499492742/materials/vgui/entities/mg_iw9_aviktor",
        # The muzzle tip (factory, the long barrel's, none) and the factory stock, grip, magazine and barrel.
        default_mesh_groups=22036489,
        bones={
            "tag_sling": (None, "-6.971,-0.573,3.351", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "11.839,0.573,2.436", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "6.943,0,-1.398", "0,0,0,1"),
            "tag_brass": ("tag_sling", "7.791,-0.17,1.884", "0.000007,0.000011,-0.707094,0.707119"),
        },
        world_muzzle="11.811,0,4.389",
        world_eject="0.82,-0.743,5.235",
        world_left_hand="8.2,0,2.35",  # the front of the handguard, like the 74u's
        slots=[
            ("Optic", (-2.748, 0, 6.136), (0.25, 0, 8.73), {}),  # tag_reflex, on the top rail (-4.5 to 2.3)
            # tag_tip, for the brake. A fitted device hides either barrel's brake (choice 2 beats the barrel slot's 1).
            ("Muzzle", (10.264, 0, 4.383), (17.62, 0, 7.4147), {"muzzle_tip": 2}),
            ("Underbarrel", (7.15, 0, 3.113), (8.3, 0, 6.2), {}),  # the front of the bottom rail (5.25 to 9.25)
            ("Laser", (7.44, -1.06, 4.484), (8.6, -1.22, 7.4147), {}),  # tag_laser_attach (right-side flat 7.5 to 9.25)
        ],
        charm=(0.0, 1.75, 2.3),
        # The 762's measured correction moved by how far the Vityaz's ADS pose puts its optic slot from the 762's,
        # like the 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="1.728,0,-1.172",
        gameplay=gameplay_vityaz,
        category="SMG",
        kill_reward=600,
        guid_salt="vityaz/",
        parts=PARTS_VITYAZ,
        # port_kastov.py's world stock, grip and mag points, and the middle of the barrels.
        part_slot_positions={"stock": (-5.716, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0), "magazine": (2.516, 0, 3.257),
                             "barrel": (8.5, 0, 4.4)},
        part_slot_bodygroups={"barrel": {"muzzle_tip": 1}},
    ),
}

MOUNT_BONE = "tag_sling"

# The M4's MW22 parts that fit the guns' slots, plus loadout-only parts. The M4's barrels, stocks, grips and
# magazines are pieces of the M4 itself; its launcher needs the M4's barrel.
SLOT_CATEGORIES = {"Optic", "Muzzle", "Underbarrel", "Laser"}
FITTING_PARTS = [path for path in sorted((ASSETS / "gunsmith" / "m4a1" / "mw2022").glob("*.gnsmth"))
                 if json.loads(path.read_text(encoding="utf-8"))["Category"] in SLOT_CATEGORIES
                 and path.stem != "att_vm_p01_ar_mike4_ubgl"]
FITTING_PARTS.append(ASSETS / "gunsmith" / "ammunition" / "tracer_rounds.gnsmth")
ELIGIBLE = re.compile(r'("EligibleEquipment":\s*\[)(.*?)(\n\s*\])', re.DOTALL)

def remap_guids(document: dict, salt: str) -> dict:
    text = json.dumps(document)
    mapping = {old: str(uuid.uuid5(NAMESPACE, f"{salt}/{old}")) for old in set(GUID.findall(text))}
    return json.loads(GUID.sub(lambda match: mapping[match.group(0)], text))


def new_guid(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")


def component(game_object: dict, suffix: str) -> dict:
    return next(c for c in game_object.get("Components", []) if c["__type"].endswith(suffix))


def find(game_object: dict, name: str) -> dict:
    if game_object.get("Name") == name:
        return game_object
    for child in game_object.get("Children", []):
        found = find(child, name)
        if found is not None:
            return found
    raise KeyError(name)


def reference(game_object: dict) -> dict:
    return {"_type": "gameobject", "go": game_object["__guid"]}


def component_reference(game_object: dict, comp: dict, kind: str) -> dict:
    return {"_type": "component", "component_id": comp["__guid"], "go": game_object["__guid"],
            "component_type": kind}


def vector(values) -> str:
    return ",".join(f"{v:g}" for v in values)


def icon_path(weapon: Weapon) -> str:
    return f"ui/weapons/guns/{weapon.name}_01.png"


def all_slots(weapon: Weapon, prefabs: Prefabs) -> list[tuple[str, tuple, tuple, dict[str, int]]]:
    """The M4-part slots plus one per part_choices group, whose parts switch its bodygroup instead of mounting."""
    return prefabs.slots + [(PART_SLOTS[group][0], prefabs.part_slot_positions[group],
                             prefabs.part_slot_positions[group], prefabs.part_slot_bodygroups.get(group, {}))
                            for group in weapon.part_choices]


def attachment_points(weapon: Weapon, prefabs: Prefabs, prefix: str) -> list[dict]:
    points = []
    for category, target, m4, bodygroups in all_slots(weapon, prefabs):
        key = f"{prefabs.guid_salt}{prefix}/slot/{category}"
        points.append({
            "__guid": new_guid(key), "Flags": 0, "Name": f"{category} Attachment Point",
            "Position": vector(target), "Enabled": True,
            "Components": [{
                "__type": "Facepunch.Gunsmith.GunsmithAttachmentPoint",
                "__guid": new_guid(f"{key}/point"),
                "Category": category,
                "MountBone": MOUNT_BONE,
                "MountOffset": vector(np.subtract(target, m4).round(4)),
                "FittedBodygroups": bodygroups,
            }],
        })
    return points


def charm_point(prefabs: Prefabs, prefix: str, position) -> dict:
    key = f"{prefabs.guid_salt}{prefix}/slot/Charm"
    return {
        "__guid": new_guid(key), "Flags": 0, "Name": "Charm Attachment Point",
        "Position": vector(position), "Enabled": True,
        "Components": [{"__type": "Facepunch.Gunsmith.GunsmithAttachmentPoint",
                        "__guid": new_guid(f"{key}/point"), "Category": "Charm"}],
    }


def set_aim(functions: dict, prefabs: Prefabs) -> None:
    # ADS comes from the animgraph (ads_delta), like the M4: no manual offset.
    offset = component(functions, "ManualOffset")
    offset["AimOffset"] = "0,0,0"
    offset["AimAngleOffset"] = "0,0,0"
    offset["OpticAimCorrection"] = prefabs.optic_aim_correction


def weapon_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    """A generated gameplay prefab: the M4's, with the gun's Gameplay."""
    document = remap_guids(load(M4 / "weapon_m4a1.prefab"), f"{prefabs.guid_salt}weapon")
    root = document["RootObject"]
    root["Name"] = f"weapon_{weapon.name}"
    equipment = component(root, "Equipment")
    equipment["Resource"] = f"{weapon.asset}/{weapon.name}.equip"
    equipment["MountedPrefab"] = {"_type": "gameobject", "prefab": f"{weapon.asset}/mount_{weapon.name}.prefab"}
    equipment["DeploySound"] = prefabs.deploy_sound

    functions = find(root, "Functions")

    def target(game_object: dict, suffix: str) -> dict:
        return component(game_object if suffix == "Equipment" else find(game_object, "Functions"), suffix)

    gameplay = prefabs.gameplay()
    if gameplay.borrow is not None:
        source_path, borrowed = gameplay.borrow
        source = load(source_path)["RootObject"]
        for suffix, names in borrowed.items():
            values = target(source, suffix)
            target(root, suffix).update({name: deepcopy(values[name]) for name in names})
    for suffix, values in gameplay.fields.items():
        target(root, suffix).update(deepcopy(values))

    set_aim(functions, prefabs)
    return document


def patched_weapon_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    """An existing gameplay prefab with the viewmodel's ADS and deploy sound."""
    document = load(weapon.folder / f"weapon_{weapon.name}.prefab")
    root = document["RootObject"]
    component(root, "Equipment")["DeploySound"] = prefabs.deploy_sound
    set_aim(find(root, "Functions"), prefabs)
    return document


def viewmodel_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    salt = prefabs.guid_salt
    template = load(M4 / "vm_m4a1.prefab")
    template_root = template["RootObject"]
    root = {key: deepcopy(value) for key, value in template_root.items() if key not in ("Children", "Components")}
    root["__guid"] = new_guid(f"{salt}vm/root")
    root["Name"] = f"vm_{weapon.name}"

    view_model = deepcopy(component(template_root, "ViewModel"))
    renderer = deepcopy(component(template_root, "SkinnedModelRenderer"))
    gunsmith = deepcopy(component(template_root, "GunsmithWeapon"))
    view_model["__guid"] = new_guid(f"{salt}vm/viewmodel")
    renderer["__guid"] = new_guid(f"{salt}vm/renderer")
    gunsmith["__guid"] = new_guid(f"{salt}vm/gunsmith")
    renderer["Model"] = f"{weapon.asset}/v_{weapon.model}.vmdl"
    renderer["BodyGroups"] = prefabs.default_mesh_groups
    renderer["CreateBoneObjects"] = True

    arms_template = find(template_root, "Object")
    arms = deepcopy(arms_template)
    arms["__guid"] = new_guid(f"{salt}vm/arms")
    arms_renderer = component(arms, "SkinnedModelRenderer")
    arms_renderer["__guid"] = new_guid(f"{salt}vm/arms/renderer")
    arms_renderer["BoneMergeTarget"] = component_reference(root, renderer, "SkinnedModelRenderer")

    bones: dict[str, dict] = {}
    children = [arms]
    for name, (parent, position, rotation) in prefabs.bones.items():
        bone = {"__guid": new_guid(f"{salt}vm/bone/{name}"), "Flags": 4, "Name": name, "Position": position,
                "Rotation": rotation, "Enabled": True}
        bones[name] = bone
        if parent is None:
            children.append(bone)
        else:
            bones[parent].setdefault("Children", []).append(bone)

    view_model["Arms"] = component_reference(arms, arms_renderer, "SkinnedModelRenderer")
    view_model["ModelRenderer"] = component_reference(root, renderer, "SkinnedModelRenderer")
    view_model["Muzzle"] = reference(bones["muzzle"])
    view_model["EjectionPort"] = reference(bones["tag_brass"])
    gunsmith["Renderer"] = component_reference(root, renderer, "SkinnedModelRenderer")
    gunsmith["Resource"] = f"{weapon.asset}/{weapon.name}.equip"

    root["Components"] = [view_model, renderer, gunsmith]
    sling = np.array([float(v) for v in prefabs.bones[MOUNT_BONE][1].split(",")])
    bones[MOUNT_BONE].setdefault("Children", []).append(
        charm_point(prefabs, "vm", (np.subtract(prefabs.charm, sling)).round(4)))
    root["Children"] = children + attachment_points(weapon, prefabs, "vm")
    document = {key: deepcopy(value) for key, value in template.items() if key != "RootObject"}
    document["RootObject"] = root
    document["__references"] = []
    return document


def world_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    document = remap_guids(load(M4 / "wm_m4a1.prefab"), f"{prefabs.guid_salt}wm")
    root = document["RootObject"]
    root["Name"] = f"wm_{weapon.name}"
    renderer = component(root, "SkinnedModelRenderer")
    renderer["Model"] = f"{weapon.asset}/w_{weapon.model}.vmdl"
    renderer["BodyGroups"] = prefabs.default_mesh_groups
    keep = {"Muzzle": prefabs.world_muzzle, "EjectionPort": prefabs.world_eject, "LeftHandIK": prefabs.world_left_hand}
    root["Children"] = [child for child in root["Children"] if child["Name"] in keep]
    for child in root["Children"]:
        child["Position"] = keep[child["Name"]]
    root["Children"] += attachment_points(weapon, prefabs, "wm") + [charm_point(prefabs, "wm", prefabs.charm)]
    document["__references"] = []
    return document


def mount_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    document = remap_guids(load(M4 / "mount_m4a1.prefab"), f"{prefabs.guid_salt}mount")
    root = document["RootObject"]
    root["Name"] = f"mount_{weapon.name}"
    renderer = component(find(root, "Model"), "SkinnedModelRenderer")
    renderer["Model"] = f"{weapon.asset}/w_{weapon.model}.vmdl"
    renderer["BodyGroups"] = prefabs.default_mesh_groups
    document["__references"] = []
    return document


def equipment_resource(weapon: Weapon, prefabs: Prefabs) -> dict:
    resource = load(M4 / "m4a1.equip")
    resource.update({
        "Name": prefabs.title,
        "Description": prefabs.description,
        "Icon": icon_path(weapon),
        "Price": prefabs.price,
        "KillReward": prefabs.kill_reward,
        "MainPrefab": {"_type": "gameobject", "prefab": f"{weapon.asset}/weapon_{weapon.name}.prefab"},
        "WorldModelPrefab": {"_type": "gameobject", "prefab": f"{weapon.asset}/wm_{weapon.name}.prefab"},
        "ViewModelPrefab": {"_type": "gameobject", "prefab": f"{weapon.asset}/vm_{weapon.name}.prefab"},
        "WorldModel": f"{weapon.asset}/w_{weapon.model}.vmdl",
        "WorldModelBodyGroups": 0,
        "__references": [],
        "Category": prefabs.category,
        "GunsmithOffset": prefabs.gunsmith_offset,
    })
    return resource


def make_parts_eligible(weapon: Weapon, prefabs: Prefabs) -> int:
    """Adds the gun to FITTING_PARTS' eligible weapons, editing the list in place to keep the files' formatting."""
    assert {slot[0] for slot in prefabs.slots} == SLOT_CATEGORIES
    equip = f"{weapon.asset}/{weapon.name}.equip"
    changed = 0
    for path in FITTING_PARTS:
        text = path.read_text(encoding="utf-8")
        if equip in json.loads(text)["EligibleEquipment"]:
            continue
        match = ELIGIBLE.search(text)
        indent = re.search(r"\n(\s*)\S", match.group(2)).group(1)
        text = text[:match.end(2)] + f',\n{indent}"{equip}"' + text[match.end(2):]
        path.write_text(text, encoding="utf-8", newline="")
        changed += 1
    return changed


def own_parts(weapon: Weapon, prefabs: Prefabs) -> int:
    """Writes a gunsmith part for every non-factory part_choices choice; the gunsmith's "Standard" is choice 0."""
    assert set(prefabs.parts) == {choice for choices in weapon.part_choices.values() for choice, _ in choices[1:]}
    for group, choices in weapon.part_choices.items():
        category, folder = PART_SLOTS[group]
        for index, (choice, _) in enumerate(choices[1:], start=1):
            part = prefabs.parts[choice]
            document = {
                "Name": part.name,
                "Category": category,
                "EligibleEquipment": [f"{weapon.asset}/{weapon.name}.equip"],
                "RequiredLevel": 0,
                "Description": f"{part.description} {part.effect()}",
                "ModifyBodygroups": True,
                "Bodygroups": {group: index},
                "VerticalRecoilScale": part.vertical_recoil,
                "HorizontalRecoilScale": part.horizontal_recoil,
            }
            if category == "Magazine":
                document["MagazineCapacity"] = part.magazine_capacity
                document["ReloadTimeMultiplier"] = part.reload_time
            if part.muzzle_shift:
                document["MuzzleShift"] = vector(part.muzzle_shift)
            document.update({"__references": [], "__version": 0})
            path = ASSETS / "gunsmith" / weapon.name / folder / f"att_vm_p04_{choice}.gnsmth"
            path.parent.mkdir(parents=True, exist_ok=True)
            save(path, document)
    return len(prefabs.parts)


def icon(weapon: Weapon, prefabs: Prefabs) -> None:
    """White silhouette of the addon's spawn icon, framed like the other 1024px HC1 gun icons."""
    from kastov_materials import load_vtf_texture  # kastov_materials puts SourceIO on the path
    pixels, width, height, _ = load_vtf_texture((EXTRACTED / f"{prefabs.icon_source}.vtf").read_bytes())
    alpha = np.frombuffer(pixels, np.uint8).reshape(height, width, 4)[:, :, 3]
    # The gun is opaque; the soft, semi-transparent rim around it is a drop shadow.
    ys, xs = np.nonzero(alpha > 192)
    crop = alpha[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # The M4 icon spans ~90% of the width, centred.
    scale = 0.9 * 1024 / crop.shape[1]
    size = (round(crop.shape[1] * scale), round(crop.shape[0] * scale))
    upscaled = np.asarray(Image.fromarray(crop, "L").resize(size, Image.LANCZOS), float)
    # Cut the shadow off after upscaling, leaving a crisp, anti-aliased edge like the other icons.
    edge = np.clip((upscaled - 170) / (235 - 170), 0, 1)
    mask = Image.fromarray((edge * edge * (3 - 2 * edge) * 255).astype(np.uint8), "L")
    out = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
    white = Image.new("RGBA", size, (255, 255, 255, 255))
    white.putalpha(mask)
    out.alpha_composite(white, ((1024 - size[0]) // 2, (1024 - size[1]) // 2))
    out.save(ASSETS / icon_path(weapon), optimize=True)


def main() -> None:
    weapon = kastov_weapons.from_command_line(__doc__)
    prefabs = PREFABS[weapon.name]
    out = weapon.folder
    if prefabs.gameplay is not None:
        save(out / f"weapon_{weapon.name}.prefab", weapon_prefab(weapon, prefabs))
    else:
        save(out / f"weapon_{weapon.name}.prefab", patched_weapon_prefab(weapon, prefabs))
    save(out / f"vm_{weapon.name}.prefab", viewmodel_prefab(weapon, prefabs))
    save(out / f"wm_{weapon.name}.prefab", world_prefab(weapon, prefabs))
    save(out / f"mount_{weapon.name}.prefab", mount_prefab(weapon, prefabs))
    save(out / f"{weapon.name}.equip", equipment_resource(weapon, prefabs))
    if prefabs.icon_source is not None:
        icon(weapon, prefabs)
    print(f"wrote {weapon.name}'s prefabs and equip and {own_parts(weapon, prefabs)} own parts; "
          f"made {make_parts_eligible(weapon, prefabs)} parts eligible")


if __name__ == "__main__":
    main()
