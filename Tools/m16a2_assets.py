"""Build the Colt M16A2's materials and sounds, from Escape from Tarkov's M16A2 (ARC9 EFT Assault Rifles, Workshop
2962829818, and the EFT SHARED pack it requires, Workshop 2917343547).

Materials, built like the AK-12's (ak12_assets.build_eft: no metal, roughness from the phong exponent), in the pack's
first skin, the black and dark grey the M16A2 was issued in:
- the M16A2's lower (with the trigger guard, the magazine well and the burst trigger group's selector markings), the
  internals (the trigger and hammer), the bolt carrier, the A2 upper with its fixed carry handle and rear sight, the
  round ribbed A2 handguard and its retainer ring and slip ring, the A2 fixed stock, the 20-inch (508 mm) barrel, the
  early charging handle, the front sight base on its gas block, the gas tube, the receiver end plate, the A2 birdcage
  flash hider and Colt's 30-round aluminium magazine, from the pack's m4a1 and mods folders;
- the A2 buffer tube, the A2 pistol grip and the 5.56x45 rounds, from EFT SHARED.

Sounds:
- The shot is Tarkov's M4A1, the pack's only Colt 5.56 recordings (its M16A1 and M16A2 play them too): four outdoor close
  single shots (m4a1_outdoor_close_onseshot_01-04), each with its echo in it, not a start under a separate tail. They
  were made at -7.2 to -8.2 dB (K-weighted, loudest 100 ms) with their peaks at full scale. The M16A2 fires the M16A4's
  round from the same 20-inch barrel, so each is lifted through the voicing's soft clipper and limiter
  (shot_voicing.master) to the M16A4's -5.4 dB (LOUDNESS). Then it's voiced like the other ported guns (ported_shots.py).
- The suppressed shot is Tarkov's four suppressed M4A1 takes under their own tail, mixed as the pack plays a single one
  and set 10 dB under the voiced open shot (suppressed_shots.py).
- The reloads are the M16A4's: the M16A2 plays the M16A4's clips (MWII's M16, the same Colt rifle on the same lower), so
  its draw, holster and reload foley are the M16A4's, voiced already.

Run (after m16a2_rig.py and m16_assets.py): python Tools/m16a2_assets.py [--materials-only]
"""

from __future__ import annotations

import json
import sys

import ak12_assets
import ported_shots
import shot_voicing
import suppressed_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, ffmpeg, sound_event

EXTRACTED = ak12_assets.EXTRACTED
SHARED = TOOLS / "extracted" / "2917343547"  # ARC9 EFT SHARED, which the Assault Rifles pack requires
DEST = ASSETS / "Weapons" / "M16A2"
FIRE = "weapons/darsu_eft/m4a1/fire_new"
M16 = ASSETS / "Weapons" / "M16" / "m16_assets.json"

# Source material (the SMD material name) -> (friendly name, the pack its vmt is in, the pack its textures are in).
MATERIALS = {
    "weapon_colt_m16a2_556x45_LOD0": ("m16a2_lower", EXTRACTED, EXTRACTED),
    "weapon_colt_m16_556x45_internals_LOD0": ("m16a2_internals", EXTRACTED, EXTRACTED),
    "weapon_colt_m16_556x45_bolt_LOD0": ("m16a2_bolt", EXTRACTED, EXTRACTED),
    "reciever_ar15_colt_m16a2_std_LOD0": ("m16a2_upper", EXTRACTED, EXTRACTED),
    "handguard_ar15_colt_m16a2_std_LOD0": ("m16a2_handguard", EXTRACTED, EXTRACTED),
    "handguard_ar15_colt_retainers_LOD0": ("m16a2_handguard_retainers", EXTRACTED, EXTRACTED),
    "stock_ar15_colt_a2_std_LOD0": ("m16a2_stock", EXTRACTED, EXTRACTED),
    "barrel_ar15_colt_m16_std_508mm_LOD0": ("m16a2_barrel", EXTRACTED, EXTRACTED),
    "charge_ar15_colt_charging_handle_early_LOD0": ("m16a2_charging_handle", EXTRACTED, EXTRACTED),
    "gas_block_ar15_colt_m4_front_sight_gas_block_std_LOD0": ("m16a2_front_sight", EXTRACTED, EXTRACTED),
    "barrel_ar15_gastube_set_LOD0": ("m16a2_gas_tube", EXTRACTED, EXTRACTED),
    "endplate_ar15_colt_a15_std_LOD0": ("m16a2_end_plate", EXTRACTED, EXTRACTED),
    "muzzle_ar15_colt_usgi_a2_556x45_LOD0": ("m16a2_flash_hider", EXTRACTED, EXTRACTED),
    "mag_stanag_colt_ar15_std_556x45_30_LOD0": ("m16a2_mag", EXTRACTED, EXTRACTED),
    "stock_ar15_colt_stock_tube_A2_LOD0": ("m16a2_stock_tube", SHARED, SHARED),
    "pistolgrip_ar15_colt_a2_LOD0": ("m16a2_pistol_grip", SHARED, SHARED),
    "patron_556x45nato": ("m16a2_rounds", SHARED, SHARED),
}

# Tarkov's M4A1 single shots, and (starts, tail, gain_db) for its suppressed ones; see the docstring.
# suppressed_shots.py sets the suppressed ones where they belong.
SHOTS = [f"{FIRE}/m4a1_outdoor_close_onseshot_0{n}.wav" for n in range(1, 5)]
SUPPRESSED = ([f"{FIRE}/m4a1_fire_silenced_close_loop{n}.wav" for n in range(1, 5)],
              f"{FIRE}/m4a1_fire_silenced_close_loop_tail.wav", -8)
# The open shot's takes' loudest 100 ms (K-weighted, dB): the M16A4's voiced shot's.
LOUDNESS = -5.4


def build_materials() -> dict[str, str]:
    """Source material -> vmat path."""
    out = DEST / "materials"
    out.mkdir(parents=True, exist_ok=True)
    return {source: ak12_assets.build_eft(source, name, out, root, texture_root)
            for source, (name, root, texture_root) in MATERIALS.items()}


def level_shots(out, name: str) -> list:
    """The open shot's takes, <name>_01.wav to _04: each limited like the other shots, then lifted to LOUDNESS."""
    takes = []
    for index, source in enumerate(SHOTS, 1):
        wav = out / f"{name}_{index:02d}.wav"
        ffmpeg(["-i", str(EXTRACTED / "sound" / source),
                "-af", "volume=0dB,alimiter=limit=0.891:attack=1:release=50:level=false",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        x = shot_voicing.read_wav(str(wav))
        lift = 0.0
        for _ in range(12):
            y = shot_voicing.master(x * 10 ** (lift / 20))
            miss = LOUDNESS - shot_voicing.loudest(y)[0]
            if abs(miss) < 0.02:
                break
            lift += miss
        shot_voicing.write_wav(str(wav), y)
        takes.append(wav)
    return takes


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name, and each reload clip's {seconds: event}."""
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    m16 = json.loads(M16.read_text(encoding="utf-8"))

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "m16a2.fire.sound"
    # The rip's shots, voiced towards what a shooter hears outdoors (ported_shots.py).
    sound_event(fire, ported_shots.build("m16a2", out), pitch=ported_shots.event_pitch("m16a2"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the M16A2's own suppressed takes.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    starts, tail, gain = SUPPRESSED
    suppressed["Sounds"] = [asset_path(ak12_assets.mix_take(out, start, tail, f"m16a2_suppressed_shot_{index:02d}", gain)
                                       .with_suffix(".vsnd")) for index, start in enumerate(starts, 1)]
    fire_suppressed = out / "m16a2.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Everything else is the M16A4's: its draw and holster, its foley events and every reload.
    sounds = {**m16["sounds"], "fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}
    # The suppressed shot, voiced like the open shots (suppressed_shots.py). The foley is the M16A4's, voiced already.
    suppressed_shots.voice("m16a2")
    return sounds, dict(m16["reloads"])


def main() -> None:
    materials = build_materials()
    manifest_path = DEST / "m16a2_assets.json"
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
