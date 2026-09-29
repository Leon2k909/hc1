"""Build the PP-19 Bizon materials and sounds from the MWII Kastovia Platform addon (its "Minibak", mg_iw9_beta).

Same source pack and material/sound conversion as ks74u_assets.py (see there); the model/animation side runs through
the shared Kastov pipeline (Tools/port_kastov.py --weapon bizon). The stocks and pistol grips are Kastovia platform
parts the 74u already builds, and the side-mount rail is the 74u's rail texture, so they map to its materials.

Sounds: the Bizon's shot files are whole shots (its sound script plays them alone), so each is only levelled to the
Vityaz's mixed shots. Reload foley is the Bizon's own, at the frames the viewmodel's QC events play it (30 fps).

Run: python Tools/bizon_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from ks74u_assets import ASSETS, EXTRACTED, asset_path, build_material, ffmpeg, sound_event

DEST = ASSETS / "Weapons" / "Bizon"
KASTOV74U_MANIFEST = ASSETS / "Weapons" / "Kastov74u" / "ks74u_assets.json"
BASE = "pwci/mw/weapons/beta"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "wpn_p04_sm_beta_receiver_v0": ("bizon_receiver", f"{BASE}/wpn_p04_sm_beta_receiver_v0"),
    "wpn_p04_sm_beta_barrel_v0": ("bizon_barrel", f"{BASE}/wpn_p04_sm_beta_barrel_v0"),
    "wpn_p04_sm_beta_brake_v0": ("bizon_brake", f"{BASE}/wpn_p04_sm_beta_brake_v0"),
    "wpn_p04_sm_beta_magheli_9m_v0": ("bizon_mag", f"{BASE}/wpn_p04_sm_beta_magheli_9m_v0"),
    # att_ammo_9m_df.vmt's textures.
    "att_ammo_9m_df": ("bizon_rounds", f"{BASE}/ximage_7b0eb55b231d7932"),
}
# The side-mount rail's vmt (wpn_p04_lm_rkilo_optic_rail_v0) draws the 74u's rail texture.
RAIL = ("wpn_p04_lm_rkilo_optic_rail_v0", "xmaterial_7915a70e03b314a")
# The stocks and pistol grips (kastov_weapons.BIZON.part_choices) are the 74u's: its materials.
SHARED_MATERIALS = re.compile(r"/ks74u_(stock|grip|pistolgrip)")

SHOTS = 8
# The Bizon's shots average ~4 dB louder than the Vityaz's mixed ones (vityaz_shot_*.wav, -24.3 dB mean): level them.
SHOT_GAIN_DB = -4
SOUND_DIR = "fritz/weapons/beta"

# Friendly sound name -> source .ogg under sound/fritz/weapons/beta
FOLEY = {
    "raise": "p04_sm_beta_raise.ogg",
    "drop": "p04_sm_beta_drop_quick.ogg",
    **{f"reload.{part}": f"p04_sm_beta_reload_{part}.ogg"
       for part in ("raise", "magout", "armdown", "mvmnt", "maghit", "magin", "end")},
    **{f"reload_empty.{part}": f"p04_sm_beta_reload_empty_{part}.ogg"
       for part in ("raise", "magout", "mvmnt", "maghit", "magin", "charge", "end")},
}

# The v_iw9_beta QC's sound events (frame at 30 fps -> sound). tactical: the magazine catch is pressed ~0.23s, the
# old helical magazine comes off the bottom and the arm drops ~0.57s, the new one is brought up ~1.03s, hits its front
# lug ~1.27s and latches at 1.6s; empty: the same, then the bolt handle is pulled at ~2.13s and let go by 2.3s. Reload
# sounds are keyed by time, so the second of two sounds on one frame goes a frame later.
RELOAD_SOUNDS = {2: "reload.raise", 7: "reload.magout", 17: "reload.armdown", 31: "reload.mvmnt", 38: "reload.maghit",
                 48: "reload.magin", 49: "reload.end"}
EMPTY_RELOAD_SOUNDS = {1: "reload_empty.raise", 2: "reload_empty.magout", 31: "reload_empty.mvmnt",
                       40: "reload_empty.maghit", 48: "reload_empty.magin", 64: "reload_empty.charge",
                       69: "reload_empty.end"}


def level_shots(out: Path, layer: str, name: str) -> list[Path]:
    """Each variant of a shot layer, turned down SHOT_GAIN_DB and limited like the Vityaz's."""
    src = EXTRACTED / "sound" / SOUND_DIR
    shots = []
    for index in range(1, SHOTS + 1):
        wav = out / f"{name}_{index:02d}.wav"
        ffmpeg(["-i", str(src / f"weap_beta_{layer}_{index:02d}_mech.ogg"),
                "-af", f"volume={SHOT_GAIN_DB}dB,alimiter=limit=0.891:attack=1:release=50:level=false",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        shots.append(wav)
    return shots


def build_sounds() -> dict[str, str]:
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "bizon.fire.sound"
    sound_event(fire, level_shots(out, "fire_plr_shot", "bizon_shot"), pitch="0.98 1.02", decibels=m4["Decibels"],
                distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-SMG event's settings and curve, with the Bizon's own suppressed shots.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_smg.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(s.with_suffix(".vsnd"))
                            for s in level_shots(out, "sup_plr_shot", "bizon_suppressed_shot")]
    fire_suppressed = out / "bizon.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}
    for name, file in FOLEY.items():
        wav = out / f"bizon_{name.replace('.', '_')}.wav"
        ffmpeg(["-i", str(EXTRACTED / "sound" / SOUND_DIR / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le",
                str(wav)])
        event = out / f"bizon.{name}.sound"
        sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
        events[name] = asset_path(event)
    return events


def timed(frames: dict[int, str], sounds: dict[str, str]) -> dict[str, str]:
    return {f"{round(frame / 30, 3):g}": sounds[name] for frame, name in frames.items()}


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials"))
                 for source, (name, base) in MATERIALS.items()}
    shared = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["materials"]
    materials[RAIL[0]] = shared[RAIL[1]]
    materials.update({source: vmat for source, vmat in shared.items() if SHARED_MATERIALS.search(vmat)})
    manifest_path = DEST / "bizon_assets.json"
    if "--materials-only" in sys.argv[1:]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["materials"] = materials
        sounds = manifest["sounds"]
    else:
        sounds = build_sounds()
        manifest = {
            "materials": materials,
            "sounds": sounds,
            "reload_sounds": timed(RELOAD_SOUNDS, sounds),
            "empty_reload_sounds": timed(EMPTY_RELOAD_SOUNDS, sounds),
        }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(materials)} materials, {len(sounds)} sound events -> {DEST}")


if __name__ == "__main__":
    main()
