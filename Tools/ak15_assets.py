"""Build the AK-15's materials and sounds: the AK-12's (ak12_assets.py), with Tarkov's AK-103 magazine and 7.62x39 rounds
and Tarkov's AKM shot.

The AK-15 is the AK-12 in 7.62x39 (Kalashnikov's 6P71), so its model is the AK-12's with a 7.62 magazine
(Tools/ak15_rig.py), and every piece but the magazine and its rounds keeps the AK-12's material.

Materials, built like the AK-12's (ak12_assets.build_eft: no metal, roughness from the phong exponent):
- the magazine: Tarkov's AK-103 polymer 30-rounder (ARC9 EFT Assault Rifles, Workshop 2962829818). Its vmt's $color2
  only blends where the colour map's alpha is set, so it's left out, as for the AK-12's;
- the rounds in its lips: Tarkov's 7.62x39 (patron_762x39, from the pack's required EFT SHARED pack, Workshop
  2917343547). Its vmt's $color2 (0.8 0.8 0.7) greens the brass towards Russian lacquered steel cases, as the AK-12's
  5.45 rounds' does;
- the AKM's 30-round steel magazine and the RPK's 40-rounder, which it takes as parts, keep the RPK's materials.

Sounds:
- The shot is Tarkov's AKM: the AKM's 415 mm barrel and the AK-15's fire the same 7.62x39 from the same length. As for the
  AK-12, the pack plays a single shot as one of four takes of the shot's start (akm_close_loop_1-4, 102 ms) under the
  tail of the last round (akm_close_loop_tail), so each take here is those two mixed. Mixed and limited to -1 dBFS at
  0 dB, the takes' loudest 100 ms (K-weighted) is -4.7 to -5.3 dB, where the Kastov 762's voiced shot (the same round)
  sits (-4.5 to -5.4), so they're left at 0 dB. Then voiced like the other ported guns (ported_shots.py).
- The suppressed shot is Tarkov's four suppressed AKM takes (akm_close_loop_silenced_1-4 under their tail), built the
  same way and set 10 dB under the voiced open shot (suppressed_shots.py).
- The reloads are the AK-12's: the same AK-105 clips, with Tarkov's AK-74 charging handle and polymer magazine foley
  (ak12_assets.py), which suit the AK-103's polymer magazine too. The RPK's 40-rounder reloads with the AK-105's 45's
  clips (reload_xmag), and so with their foley.

Run (after ak12_assets.py and rpk_assets.py): python Tools/ak15_assets.py [--materials-only]
"""

from __future__ import annotations

import json
import sys

import ak12_assets
import ported_shots
import suppressed_shots
from ks74u_assets import ASSETS, TOOLS, asset_path, sound_event

EXTRACTED = ak12_assets.EXTRACTED
SHARED = TOOLS / "extracted" / "2917343547"  # ARC9 EFT SHARED, which the Assault Rifles pack requires
DEST = ASSETS / "Weapons" / "AK15"
FIRE = ak12_assets.FIRE
AK12 = ASSETS / "Weapons" / "AK12" / "ak12_assets.json"
RPK = ASSETS / "Weapons" / "RPK" / "rpk_assets.json"

MAGAZINE = ("mag_ak_izhmash_ak103_std_762x39_30_LOD0", "ak15_mag", EXTRACTED)
ROUNDS = ("patron_762x39", "ak15_rounds", SHARED)
# The RPK's materials of the AKM's and RPK's magazines, with their rounds.
RPK_MATERIALS = ("wpn_p04_ar_akilo_mag_762s_v0", "wpn_p04_ar_akilo_xmag_762s_v0", "att_ammo_762s_df")

# Tarkov's AKM shots (each start under the tail) and gain_db; see the docstring. suppressed_shots.py sets the suppressed
# ones where they belong.
SHOTS = ([f"{FIRE}/akm_close_loop_{n}.wav" for n in range(1, 5)], f"{FIRE}/akm_close_loop_tail.wav", 0)
SUPPRESSED = ([f"{FIRE}/akm_close_loop_silenced_{n}.wav" for n in range(1, 5)],
              f"{FIRE}/akm_close_loop_silenced_tail.wav", -8)
# The AK-12's reloads the AK-15 plays: the factory magazine's, and the RPK 40's (the AK-105's 45's clips).
RELOADS = ("reload", "reload_empty", "reload_xmag", "reload_empty_xmag")


def build_materials() -> dict[str, str]:
    """Source material -> vmat path: the AK-12's, the RPK's magazines', then the AK-15's own magazine and rounds."""
    out = DEST / "materials"
    out.mkdir(parents=True, exist_ok=True)
    materials = json.loads(AK12.read_text(encoding="utf-8"))["materials"]
    rpk = json.loads(RPK.read_text(encoding="utf-8"))["materials"]
    materials.update({source: rpk[source] for source in RPK_MATERIALS})
    for source, name, root in (MAGAZINE, ROUNDS):
        materials[source] = ak12_assets.build_eft(source, name, out, root)
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
    fire = out / "ak15.fire.sound"
    # The rip's shots, voiced towards what a shooter hears outdoors (ported_shots.py).
    sound_event(fire, ported_shots.build("ak15", out), pitch=ported_shots.event_pitch("ak15"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the AK-15's own suppressed takes.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    starts, tail, gain = SUPPRESSED
    suppressed["Sounds"] = [asset_path(ak12_assets.mix_take(out, start, tail, f"ak15_suppressed_shot_{index:02d}", gain)
                                       .with_suffix(".vsnd")) for index, start in enumerate(starts, 1)]
    fire_suppressed = out / "ak15.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    # Everything else is the AK-12's: its draw and holster (the AK-105's) and its own foley events.
    sounds = {**ak12["sounds"], "fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}
    reloads = {clip: ak12["reloads"][clip] for clip in RELOADS}
    # The suppressed shot, voiced like the open shots (suppressed_shots.py). The foley is the AK-12's, voiced already.
    suppressed_shots.voice("ak15")
    return sounds, reloads


def main() -> None:
    materials = build_materials()
    manifest_path = DEST / "ak15_assets.json"
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
