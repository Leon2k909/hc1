"""Build the PP-19-01 Vityaz materials and sounds from the MWII Kastovia Platform addon (its Vaznev-9K, mg_iw9_aviktor).

Same source pack and material/sound conversion as ks74u_assets.py (see there); the model/animation side runs through
the shared Kastov pipeline (Tools/port_kastov.py --weapon vityaz). The stocks and pistol grips are Kastovia platform
parts the 74u already builds, so they map to its materials.

Sounds: each shot variant is the shot layer mixed with its mechanical layer, and the suppressed shot is the addon's
own suppressed layer with the same mechanical layer. Reload foley is the Vityaz's own; the addon's animations.lua
points at MW2019 sounds, so each file is timed from the reload clips' bone motion instead (RELOAD_SOUNDS).

Run: python Tools/vityaz_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ported_foley
import ported_shots
import suppressed_shots
from ks74u_assets import ASSETS, EXTRACTED, asset_path, build_material, ffmpeg, sound_event

DEST = ASSETS / "Weapons" / "Vityaz"
KASTOV74U_MANIFEST = ASSETS / "Weapons" / "Kastov74u" / "ks74u_assets.json"
BASE = "pwci/mw/weapons/aviktor"

# Source material (the SMD material name) -> (friendly name, vtf base path under materials/)
MATERIALS = {
    "ximage_70eb638a9a70670f": ("vityaz_receiver", f"{BASE}/wpn_p04_sm_aviktor_receiver_v0"),
    "ximage_1242d1cf91d4bf3": ("vityaz_toprail", f"{BASE}/wpn_p04_sm_aviktor_toprail_v0"),
    "ximage_677c5f5598bf5318": ("vityaz_barrel", f"{BASE}/wpn_p04_sm_aviktor_barrel_v0"),
    "ximage_6575aebf2991ff6f": ("vityaz_brake", f"{BASE}/wpn_p04_sm_aviktor_brake_v0"),
    "wpn_p04_sm_aviktor_mag_9p_v0": ("vityaz_mag", f"{BASE}/wpn_p04_sm_aviktor_mag_9p_v0"),
    "wpn_p04_sm_aviktor_xmag_9p_v0": ("vityaz_xmag", f"{BASE}/wpn_p04_sm_aviktor_xmag_9p_v0"),
    "att_ammo_9p": ("vityaz_rounds", f"{BASE}/att_ammo_9p"),
}
# The long barrel's SMDs name the factory barrel's and brake's textures directly.
ALIASES = {"wpn_p04_sm_aviktor_barrel_v0": "ximage_677c5f5598bf5318",
           "wpn_p04_sm_aviktor_brake_v0": "ximage_6575aebf2991ff6f"}
# The stocks and pistol grips (kastov_weapons.VITYAZ.part_choices) are the 74u's: its materials.
SHARED_MATERIALS = re.compile(r"/ks74u_(stock|grip|pistolgrip)")

SHOTS = 8
# Sits the 9mm shot ~3 dB under the 74u's 5.45 (ks74u_shot_*.wav).
SHOT_GAIN_DB = -5
SOUND_DIR = "fritz/weapons/aviktor"

# Friendly sound name -> source .ogg under sound/fritz/weapons/aviktor
FOLEY = {
    "raise": "p04_sm_avictor_raise_quick.ogg",
    "drop": "p04_sm_aviktor_drop_quick.ogg",
    **{f"reload.{part}": f"p04_sm_aviktor_reload_{part}.ogg"
       for part in ("rattle", "arm", "magout", "magslide", "maghit", "magin", "raise", "end")},
    **{f"reload_empty.{part}": f"p04_sm_aviktor_reload_empty_{part}.ogg"
       for part in ("rattle", "arm", "magout", "maghit", "magin", "rotate", "charge", "raise", "end")},
}

# Seconds into the reload clips (played at 1x). Each sound starts early by the time of its loudest hit, so that hit
# lands on the motion it belongs to:
# tactical - left hand leaves the guard ~0.25s, the new magazine knocks the old one out ~1.17s, slides in 1.45-1.8s and
#            seats at 1.8s, the old one is stowed 2.1-2.4s, hand back and gun level at 2.5s;
# empty    - old magazine drops ~1.2s, new one seats at 1.8s, gun rolls left 2.1-2.5s, bolt pulled ~2.74s and
#            released by ~2.87s, right hand back ~3.03s, gun level ~3.2s.
RELOAD_SOUNDS = {
    0.0: "reload.rattle", 0.1: "reload.arm", 0.91: "reload.magout", 1.36: "reload.magslide", 1.5: "reload.maghit",
    1.77: "reload.magin", 1.93: "reload.raise", 2.05: "reload.end",
}
EMPTY_RELOAD_SOUNDS = {
    0.0: "reload_empty.rattle", 0.1: "reload_empty.arm", 1.04: "reload_empty.magout", 1.54: "reload_empty.maghit",
    1.77: "reload_empty.magin", 1.92: "reload_empty.rotate", 2.53: "reload_empty.charge", 2.6: "reload_empty.raise",
    2.74: "reload_empty.end",
}


def mix_shots(out: Path, layer: str, name: str) -> list[Path]:
    """Each variant of a shot layer mixed with the same-numbered mechanical layer. The sum peaks ~8 dB over full
    scale, so it's turned down SHOT_GAIN_DB and limited instead of clipping."""
    src = EXTRACTED / "sound" / SOUND_DIR
    shots = []
    for index in range(1, SHOTS + 1):
        wav = out / f"{name}_{index:02d}.wav"
        ffmpeg(["-i", str(src / f"weap_aviktor_{layer}_{index:02d}.ogg"),
                "-i", str(src / f"weap_aviktor_fire_plr_mech_{index:02d}.ogg"),
                "-filter_complex", f"amix=inputs=2:duration=longest:normalize=0,volume={SHOT_GAIN_DB}dB,"
                                   "alimiter=limit=0.891:attack=1:release=50:level=false",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        shots.append(wav)
    return shots


def build_sounds() -> dict[str, str]:
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "vityaz.fire.sound"
    # The rip's shot, voiced away from CoD's sound design (ported_shots.py).
    sound_event(fire, ported_shots.build("vityaz", out), pitch=ported_shots.event_pitch("vityaz"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-SMG event's settings and curve, with the Vityaz's own suppressed shots.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_smg.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    suppressed["Sounds"] = [asset_path(s.with_suffix(".vsnd"))
                            for s in mix_shots(out, "sup_plr_shot", "vityaz_suppressed_shot")]
    fire_suppressed = out / "vityaz.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    events = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed)}
    for name, file in FOLEY.items():
        wav = out / f"vityaz_{name.replace('.', '_')}.wav"
        ffmpeg(["-i", str(EXTRACTED / "sound" / SOUND_DIR / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le",
                str(wav)])
        event = out / f"vityaz.{name}.sound"
        sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
        events[name] = asset_path(event)
    # The suppressed shots, voiced like the open shot (suppressed_shots.py).
    suppressed_shots.voice("vityaz")
    # The foley, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("vityaz")
    return events


def main() -> None:
    materials = {source: asset_path(build_material(name, base, DEST / "materials"))
                 for source, (name, base) in MATERIALS.items()}
    materials.update({alias: materials[source] for alias, source in ALIASES.items()})
    shared = json.loads(KASTOV74U_MANIFEST.read_text(encoding="utf-8"))["materials"]
    materials.update({source: vmat for source, vmat in shared.items() if SHARED_MATERIALS.search(vmat)})
    manifest_path = DEST / "vityaz_assets.json"
    if "--materials-only" in sys.argv[1:]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["materials"] = materials
        sounds = manifest["sounds"]
    else:
        sounds = build_sounds()
        manifest = {
            "materials": materials,
            "sounds": sounds,
            "reload_sounds": {str(t): sounds[n] for t, n in RELOAD_SOUNDS.items()},
            "empty_reload_sounds": {str(t): sounds[n] for t, n in EMPTY_RELOAD_SOUNDS.items()},
        }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(materials)} materials, {len(sounds)} sound events -> {DEST}")


if __name__ == "__main__":
    main()
