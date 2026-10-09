"""Build the SIG MCX-SPEAR's materials and sounds, from Escape from Tarkov's MCX-SPEAR (ARC9 EFT Assault Rifles, Workshop
2962829818, and the EFT SHARED pack it requires, Workshop 2917343547).

Materials, built like the AK-12's (ak12_assets.build_eft: no metal, roughness from the phong exponent), all in the pack's
first skin, the coyote tan SIG's MCX-SPEAR and the US Army's XM7 come in. Every vmt's $color2 only blends by the colour
map's alpha, so none is tinted:
- the lower (with the trigger guard and the magazine well), the upper and its details (the ejection port cover, the
  forward assist's cover, the bolt release), the internals (the bolt carrier, trigger and selector), the 330 mm barrel,
  the adjustable gas piston, the side charging handle, the M-LOK handguard and the Clutch-LOK QD flash hider, from the
  pack's spear folder;
- the stock (SIG's locking hinge, its low-profile tube and a Magpul MOE SL-K), SIG's reduced-angle pistol grip and the
  Lancer L7 AWM 20- and 25-round magazines, from its mods folder;
- the 6.8x51 FMJ rounds in the magazine's lips, from its shared folder;
- SIG's flip-up sights, from EFT SHARED.

Sounds:
- The shot is Tarkov's MCX-SPEAR: the pack plays a single shot as one of four takes of the shot's start
  (mcx_spear_outdoor_close_loop1-4) under the tail of the last round (mcx_spear_outdoor_close_loopt), so each take here
  is those two mixed. Mixed and limited to -1 dBFS, the takes' loudest 100 ms (K-weighted) is -7.0 to -7.4 dB, with the
  peaks already at the limit, so turning them up only squashes them. 6.8x51 is loaded to ~80,000 psi, where 5.56 and
  7.62x39 run 52-55,000, and the shooter of a 13-inch SPEAR hears more blast than one of a 20-inch M16A4 (-5.4) or an
  AK-15 (-5.2), so each take is lifted through the voicing's soft clipper and limiter (shot_voicing.master) to -4.8 dB
  (LOUDNESS). Then it's voiced like the other ported guns (ported_shots.py).
- The suppressed shot is Tarkov's four suppressed MCX-SPEAR takes under their own tail, built the same way and set 10 dB
  under the voiced open shot (suppressed_shots.py).
- The reloads are the MCX's: the SPEAR plays the MCX's clips (MW2019's M13, the same SIG MCX family, with an AR-15
  pattern magazine well and bolt release), so its draw, holster and reload foley are the MCX's, voiced already.

Run (after spear_rig.py and mcx_assets.py): python Tools/spear_assets.py [--materials-only]
"""

from __future__ import annotations

import json
import sys

import ak12_assets
import ported_shots
import shot_voicing
import suppressed_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, sound_event

EXTRACTED = ak12_assets.EXTRACTED
SHARED = TOOLS / "extracted" / "2917343547"  # ARC9 EFT SHARED, which the Assault Rifles pack requires
DEST = ASSETS / "Weapons" / "SPEAR"
FIRE = "weapons/darsu_eft/spear/fire_new"
MCX = ASSETS / "Weapons" / "MCX" / "mcx_assets.json"

# Source material (the SMD material name) -> (friendly name, the pack its vmt is in, the pack its textures are in).
MATERIALS = {
    "weapon_sig_mcx_spear_68x51_LOD0": ("spear_lower", EXTRACTED, EXTRACTED),
    "reciever_mcx_sig_spear_upper_LOD0": ("spear_upper", EXTRACTED, EXTRACTED),
    "reciever_mcx_sig_spear_upper_details_LOD0": ("spear_upper_details", EXTRACTED, EXTRACTED),
    "spear_internals_LOD0": ("spear_internals", EXTRACTED, EXTRACTED),
    "barrel_mcx_sig_spear_330mm_68x51_LOD0": ("spear_barrel", EXTRACTED, EXTRACTED),
    "gas_block_mcx_sig_adjustable_gas_piston_LOD0": ("spear_gas_block", EXTRACTED, EXTRACTED),
    "charge_spear_sig_spear_std_LOD0": ("spear_charging_handle", EXTRACTED, EXTRACTED),
    "handguard_mcx_sig_spear_m_lok_LOD0": ("spear_handguard", EXTRACTED, EXTRACTED),
    "muzzle_ar10_sig_clutch_lok_qd_flash_hider_68x51_LOD0": ("spear_flash_hider", EXTRACTED, EXTRACTED),
    "stock_all_sig_stock_locking_hinge_assembly_LOD0": ("spear_stock_hinge", EXTRACTED, EXTRACTED),
    "stock_base_sig_low_profile_tube_LOD0": ("spear_stock_tube", EXTRACTED, EXTRACTED),
    "stock_ar15_magpul_moe_sl_k_carbine_LOD0": ("spear_stock", EXTRACTED, EXTRACTED),
    "pistolgrip_ar15_sig_reduced_angle_pistol_grip_LOD0": ("spear_pistol_grip", EXTRACTED, EXTRACTED),
    "mag_ar10_lancer_l7_awm_762x51_20_LOD0": ("spear_mag", EXTRACTED, EXTRACTED),
    "mag_ar10_lancer_l7_awm_762x51_25_LOD0": ("spear_mag25", EXTRACTED, EXTRACTED),
    "patron_68x51_fmj": ("spear_rounds", EXTRACTED, EXTRACTED),
    "sight_rear_all_sig_flip_up_LOD0": ("spear_rear_sight", SHARED, SHARED),
    "sight_front_all_sig_flip_up_LOD0": ("spear_front_sight", SHARED, SHARED),
}

# Tarkov's MCX-SPEAR shots (each start under the tail) and gain_db; see the docstring. suppressed_shots.py sets the
# suppressed ones where they belong.
SHOTS = ([f"{FIRE}/mcx_spear_outdoor_close_loop{n}.wav" for n in range(1, 5)],
         f"{FIRE}/mcx_spear_outdoor_close_loopt.wav", 0)
SUPPRESSED = ([f"{FIRE}/mcx_spear_outdoor_silenced_close_loop{n}.wav" for n in range(1, 5)],
              f"{FIRE}/mcx_spear_outdoor_silenced_close_loopt.wav", -8)
# The open shot's takes' loudest 100 ms (K-weighted, dB); see the docstring.
LOUDNESS = -4.8


def build_materials() -> dict[str, str]:
    """Source material -> vmat path."""
    out = DEST / "materials"
    out.mkdir(parents=True, exist_ok=True)
    return {source: ak12_assets.build_eft(source, name, out, root, texture_root)
            for source, (name, root, texture_root) in MATERIALS.items()}


def level_shots(out, name: str) -> list:
    """The open shot's takes, <name>_01.wav to _04: each mixed as the pack plays it, then lifted to LOUDNESS."""
    starts, tail, gain = SHOTS
    takes = []
    for index, start in enumerate(starts, 1):
        wav = ak12_assets.mix_take(out, start, tail, f"{name}_{index:02d}", gain)
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
    mcx = json.loads(MCX.read_text(encoding="utf-8"))

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "spear.fire.sound"
    # The rip's shots, voiced towards what a shooter hears outdoors (ported_shots.py).
    sound_event(fire, ported_shots.build("spear", out), pitch=ported_shots.event_pitch("spear"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the SPEAR's own suppressed takes.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    starts, tail, gain = SUPPRESSED
    suppressed["Sounds"] = [asset_path(ak12_assets.mix_take(out, start, tail, f"spear_suppressed_shot_{index:02d}", gain)
                                       .with_suffix(".vsnd")) for index, start in enumerate(starts, 1)]
    fire_suppressed = out / "spear.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Everything else is the MCX's: its draw and holster, its foley events and every reload.
    sounds = {**mcx["sounds"], "fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}
    # The suppressed shot, voiced like the open shots (suppressed_shots.py). The foley is the MCX's, voiced already.
    suppressed_shots.voice("spear")
    return sounds, dict(mcx["reloads"])


def main() -> None:
    materials = build_materials()
    manifest_path = DEST / "spear_assets.json"
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
