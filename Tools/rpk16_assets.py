"""Build the RPK-16's materials and sounds, from Escape from Tarkov's RPK-16 (ARC9 EFT Assault Rifles, Workshop
2962829818).

Materials, built like the AK-12's (ak12_assets.build_eft: no metal, roughness from the phong exponent), every one from
the Assault Rifles pack: the receiver (with the gas block, front sight and the moving parts), the long barrel, the
railed dust cover, the handguard, its side rail sections, the rear sight, the muzzle brake, the folding stock tube and
the 95-round drum. The AK-12's telescoping stock and pistol grip, which the RPK-16 is issued with, and the 5.45 rounds
keep the AK-12's materials, and the magazines and grips it takes as parts keep the AK-12's, AK-74M's and AK-105's (from
the AK-74M's manifest, which holds the AK-12's).

Sounds:
- The shot is Tarkov's RPK-16: the pack plays a single shot as one of four takes of the shot's start
  (rpk16_outdoor_close_loop_1-4) under the tail of the last round (rpk16_outdoor_close_loop_tail), so each take here is
  those two mixed. Mixed and limited to -1 dBFS at 0 dB, the takes' loudest 100 ms (K-weighted) is -6.2 to -7.1 dB,
  where the AK-12's (the same 7N6 from a 415 mm barrel, mixed at -1 dB) are, -6.2 to -6.9: the longer barrel puts the
  muzzle further from the ear, which takes back what its fuller burn adds. Then voiced like the other ported guns
  (ported_shots.py).
- The suppressed shot is Tarkov's four suppressed RPK-16 takes under their own tail, built the same way and set 10 dB
  under the voiced open shot (suppressed_shots.py).
- The draw, holster and reloads are the RPK's: it plays the RPK's clips (the drum's reload, and the AKM 30's and RPK
  40's for the box magazines it takes), whose foley is voiced already (rpk_foley.py).

Run (after ak74m_assets.py and rpk_assets.py): python Tools/rpk16_assets.py [--materials-only]
"""

from __future__ import annotations

import json
import sys

import ak12_assets
import suppressed_shots
import ported_shots
from ks74u_assets import ASSETS, asset_path, sound_event

EXTRACTED = ak12_assets.EXTRACTED
DEST = ASSETS / "Weapons" / "RPK16"
FIRE = ak12_assets.FIRE
AK74M = ASSETS / "Weapons" / "AK74M" / "ak74m_assets.json"
RPK = ASSETS / "Weapons" / "RPK" / "rpk_assets.json"

# Source material (the SMD material name) -> (friendly name, the pack its vmt is in, the pack its textures are in).
MATERIALS = {
    "weapon_izhmash_rpk16_545x39_LOD0": ("rpk16_receiver", EXTRACTED, EXTRACTED),
    "barrel_rpk16_izhmash_rpk16_barrels_LOD0": ("rpk16_barrel", EXTRACTED, EXTRACTED),
    "reciever_rpk16_izhmash_rpk16_std_LOD0": ("rpk16_dust_cover", EXTRACTED, EXTRACTED),
    "handguard_rpk16_izhmash_rpk16_std_LOD0": ("rpk16_handguard", EXTRACTED, EXTRACTED),
    "mount_rpk16_izhmash_rpk16_side_rail_LOD0": ("rpk16_side_rail", EXTRACTED, EXTRACTED),
    "sight_rear_ak_izhmash_rpk16_rear_sight_std_LOD0": ("rpk16_rear_sight", EXTRACTED, EXTRACTED),
    "muzzle_rpk16_izhmash_rpk16_std_545x39_LOD0": ("rpk16_muzzle_brake", EXTRACTED, EXTRACTED),
    "stock_rpk16_izhmash_rpk_stock_tube_LOD0": ("rpk16_stock_tube", EXTRACTED, EXTRACTED),
    "mag_ak_izhmash_rpk16_drum_545x39_95_LOD0": ("rpk16_mag", EXTRACTED, EXTRACTED),
}

# Tarkov's RPK-16 shots (each start under the tail) and gain_db; see the docstring. suppressed_shots.py sets the
# suppressed ones where they belong.
SHOTS = ([f"{FIRE}/rpk16_outdoor_close_loop_{n}.wav" for n in range(1, 5)],
         f"{FIRE}/rpk16_outdoor_close_loop_tail.wav", 0)
SUPPRESSED = ([f"{FIRE}/rpk16_outdoor_silenced_close_loop_{n}.wav" for n in range(1, 5)],
              f"{FIRE}/rpk16_outdoor_silenced_close_loop_tail.wav", -8)


def build_materials() -> dict[str, str]:
    """Source material -> vmat path: the AK-74M's manifest's (the AK-12's, the parts' and the rounds), then the
    RPK-16's."""
    out = DEST / "materials"
    out.mkdir(parents=True, exist_ok=True)
    materials = json.loads(AK74M.read_text(encoding="utf-8"))["materials"]
    for source, (name, root, texture_root) in MATERIALS.items():
        materials[source] = ak12_assets.build_eft(source, name, out, root, texture_root)
    return materials


def level_shots(out, name: str) -> list:
    """The open shot's takes: <name>_01.wav to _04."""
    starts, tail, gain = SHOTS
    return [ak12_assets.mix_take(out, start, tail, f"{name}_{index:02d}", gain)
            for index, start in enumerate(starts, 1)]


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name, and each reload clip's {seconds: event}."""
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    rpk = json.loads(RPK.read_text(encoding="utf-8"))

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "rpk16.fire.sound"
    # The rip's shots, voiced towards what a shooter hears outdoors (ported_shots.py).
    sound_event(fire, ported_shots.build("rpk16", out), pitch=ported_shots.event_pitch("rpk16"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the RPK-16's own suppressed takes.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    starts, tail, gain = SUPPRESSED
    suppressed["Sounds"] = [
        asset_path(ak12_assets.mix_take(out, start, tail, f"rpk16_suppressed_shot_{index:02d}", gain)
                   .with_suffix(".vsnd"))
        for index, start in enumerate(starts, 1)]
    fire_suppressed = out / "rpk16.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Everything else is the RPK's: its draw and holster, its foley events and every reload.
    sounds = {**rpk["sounds"], "fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}
    # The suppressed shot, voiced like the open shots (suppressed_shots.py). The foley is the RPK's, voiced already.
    suppressed_shots.voice("rpk16")
    return sounds, dict(rpk["reloads"])


def main() -> None:
    materials = build_materials()
    manifest_path = DEST / "rpk16_assets.json"
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
