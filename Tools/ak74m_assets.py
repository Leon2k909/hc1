"""Build the AK-74M's materials and sounds, from Escape from Tarkov's AK-74M (ARC9 EFT Assault Rifles, Workshop
2962829818, and the EFT SHARED pack it requires, Workshop 2917343547).

Materials, built like the AK-12's (ak12_assets.build_eft: no metal, roughness from the phong exponent). Each vmt's
$color2 only blends where the colour map's alpha is set, so it's left out, except the pistol grip's, which tints the
whole map (0.46: Tarkov darkens the AK-74's plum polymer grip to the AK-74M's black):
- the receiver and barrel (one set of textures), the AKS-74N's shared parts and bolt, the front sight block, the side
  rail (Tarkov draws it with the PP-19-01's Sb.9 mount's textures), the dust cover, the muzzle brake, the rear sight and
  the 6L23 magazine, from the Assault Rifles pack;
- the stock and the pistol grip, from EFT SHARED;
- the black polymer handguard, whose vmt is in the Assault Rifles pack and whose textures are in EFT SHARED;
- the gas tube, in the AKM's handguard set, whose texture sheet has the tube beside the wood;
- the optic mount, Zenit's B-13 (the pack's shared attachment, under models/weapons/arc9_eft_shared), in its grey-black
  anodised aluminium (its $color2 only blends by the colour map's alpha, so it's left out like the others');
- the rounds in the magazine's lips, the AK-12's (ak12_rounds: the same 5.45 rounds, greened towards lacquered steel);
- the AK-105's magazines and the AK grips, which it takes as parts, keep the AK-105's and Kastov-74u's materials (from
  the AK-12's manifest).

Sounds:
- The shot is Tarkov's AK-74M: the pack plays a single shot as one of four takes of the shot's start
  (ak74m_outdoor_close_loop_1-4) under the tail of the last round (ak74m_outdoor_close_loop_tail), so each take here is
  those two mixed. Mixed and limited to -1 dBFS at -1 dB, the takes' loudest 100 ms (K-weighted) is -6.1 to -7.2 dB,
  where the AK-12's (the same 7N6 from the same 415 mm barrel) are, -6.2 to -6.9. Then voiced like the other ported
  guns (ported_shots.py).
- The suppressed shot is Tarkov's four suppressed AK-74M takes under the AK-74's suppressed tail (as the pack's lua plays
  them), built the same way and set 10 dB under the voiced open shot (suppressed_shots.py).
- The reloads are the AK-12's: the AK-105's clips, with Tarkov's AK-74 charging handle and polymer magazine foley
  (ak12_assets.py), which is the AK-74M's own 6L23 polymer magazine's.

Run (after ak12_assets.py): python Tools/ak74m_assets.py [--materials-only]
"""

from __future__ import annotations

import json
import sys

import ak12_assets
import suppressed_shots
import ported_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, sound_event

EXTRACTED = ak12_assets.EXTRACTED
SHARED = TOOLS / "extracted" / "2917343547"  # ARC9 EFT SHARED, which the Assault Rifles pack requires
DEST = ASSETS / "Weapons" / "AK74M"
FIRE = ak12_assets.FIRE
AK12 = ASSETS / "Weapons" / "AK12" / "ak12_assets.json"

# The packs' shared attachments' materials folder (the B-13's), beside the guns' (ak12_assets.EFT).
SHARED_ATTACHMENTS = "models/weapons/arc9_eft_shared"

# Source material (the SMD material name) -> (friendly name, the pack its vmt is in, the pack its textures are in[,
# the vmt's materials folder, if not ak12_assets.EFT]).
MATERIALS = {
    "weapon_izhmash_ak74m_545x39_LOD0": ("ak74m_receiver", EXTRACTED, EXTRACTED),
    "weapon_izhmash_aks74n_545x39_LOD0": ("ak74m_parts", EXTRACTED, EXTRACTED),  # selector, trigger, mag catch
    "weapon_izhmash_aks74n_bolt_LOD0": ("ak74m_bolt", EXTRACTED, EXTRACTED),
    "mount_pp-19-01_izhmash_izh-9x19_sb9_LOD0": ("ak74m_side_rail", EXTRACTED, EXTRACTED),
    "weapon_izhmash_ak74_kolodka_LOD0": ("ak74m_front_sight", EXTRACTED, EXTRACTED),
    "reciever_ak74_izhmash_ak74m_std_LOD0": ("ak74m_dust_cover", EXTRACTED, EXTRACTED),
    "stock_ak74m_izhmash_ak74m_std_LOD0": ("ak74m_stock", SHARED, SHARED),
    "handguard_ak_izhmash_akm_std_wood_LOD0": ("ak74m_gas_tube", EXTRACTED, EXTRACTED),
    "handguard_ak_izhmash_ak74m_std_plastic_LOD0": ("ak74m_handguard", EXTRACTED, SHARED),
    "muzzle_ak74_izhmash_ak74m_std_545x39_LOD0": ("ak74m_muzzle_brake", EXTRACTED, EXTRACTED),
    "sight_rear_ak_izhmash_ak74m_std_LOD0": ("ak74m_rear_sight", EXTRACTED, EXTRACTED),
    "pistolgrip_ak_izhmash_ak74_plastic_LOD0": ("ak74m_pistol_grip", SHARED, SHARED),
    "mag_ak74_izhmash_6L23_545x39_30_LOD0": ("ak74m_mag", EXTRACTED, EXTRACTED),
    "mount_dovetail_zenit_b13_LOD0": ("ak74m_mount", EXTRACTED, EXTRACTED, SHARED_ATTACHMENTS),
}
# The barrel's vmt names the receiver's textures.
SAME = {"weapon_izhmash_ak74m_545x39_Barrel": "weapon_izhmash_ak74m_545x39_LOD0"}

# Tarkov's AK-74M shots (each start under the tail) and gain_db; see the docstring. suppressed_shots.py sets the
# suppressed ones where they belong.
SHOTS = ([f"{FIRE}/ak74m_outdoor_close_loop_{n}.wav" for n in range(1, 5)],
         f"{FIRE}/ak74m_outdoor_close_loop_tail.wav", -1)
SUPPRESSED = ([f"{FIRE}/ak74m_outdoor_silenced_close_loop_{n}.wav" for n in range(1, 5)],
              f"{FIRE}/ak74_loop_outdoor_close_silenced_tail.wav", -8)


def build_materials() -> dict[str, str]:
    """Source material -> vmat path: the AK-12's manifest's (the parts' materials and the rounds), then the AK-74M's."""
    out = DEST / "materials"
    out.mkdir(parents=True, exist_ok=True)
    materials = json.loads(AK12.read_text(encoding="utf-8"))["materials"]
    for source, (name, root, texture_root, *folder) in MATERIALS.items():
        materials[source] = ak12_assets.build_eft(source, name, out, root, texture_root, *folder)
    for source, same in SAME.items():
        materials[source] = materials[same]
    return materials


def level_shots(out, name: str) -> list:
    """The open shot's takes: <name>_01.wav to _04."""
    starts, tail, gain = SHOTS
    return [ak12_assets.mix_take(out, start, tail, f"{name}_{index:02d}", gain) for index, start in enumerate(starts, 1)]


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name, and each reload clip's {seconds: event}."""
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    ak12 = json.loads(AK12.read_text(encoding="utf-8"))

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "ak74m.fire.sound"
    # The rip's shots, voiced towards what a shooter hears outdoors (ported_shots.py).
    sound_event(fire, ported_shots.build("ak74m", out), pitch=ported_shots.event_pitch("ak74m"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the AK-74M's own suppressed takes.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    starts, tail, gain = SUPPRESSED
    suppressed["Sounds"] = [asset_path(ak12_assets.mix_take(out, start, tail, f"ak74m_suppressed_shot_{index:02d}", gain)
                                       .with_suffix(".vsnd")) for index, start in enumerate(starts, 1)]
    fire_suppressed = out / "ak74m.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Everything else is the AK-12's: its draw and holster (the AK-105's), its foley events and every reload.
    sounds = {**ak12["sounds"], "fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}
    # The suppressed shot, voiced like the open shots (suppressed_shots.py). The foley is the AK-12's, voiced already.
    suppressed_shots.voice("ak74m")
    return sounds, dict(ak12["reloads"])


def main() -> None:
    materials = build_materials()
    manifest_path = DEST / "ak74m_assets.json"
    if "--materials-only" in sys.argv[1:]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["materials"] = materials
    else:
        sounds, reloads = build_sounds()
        manifest = {"materials": materials, "sounds": sounds, "reloads": reloads}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(set(materials.values()))} materials, {len(manifest['sounds'])} sound events -> {DEST}")


if __name__ == "__main__":
    main()
