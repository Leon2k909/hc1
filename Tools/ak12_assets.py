"""Build the AK-12's materials and sounds from Escape from Tarkov's AK-12 in the ARC9 EFT Assault Rifles pack (Workshop
2962829818, darsu_eft).

The model is Tarkov's (Tools/ak12_rig.py puts its pieces on the AK-105's CoD rig); the clips are the AK-105's. The model
and animation side runs through the shared Kastov pipeline (Tools/port_kastov.py --weapon ak12).

Materials: every piece is a Tarkov sheet in Source's VertexLitGeneric packing, a _diff colour map, a _nrm normal map and
a _gloss phong exponent map (each vmt names its own). They're built like hk416_assets.build_eft's: no metal (Source's
phong over the diffuse, as Tarkov's own shader draws them), roughness from the exponent. The vmts' $color2 0.88 only
blends where the colour map's alpha is set ($blendtintbybasealpha), and the $detail ak12h grain is left out.
- The magazine's window (newglass) points at a glass texture the pack doesn't ship, so it's a flat smoked polymer:
  translucent, the colour and opacity of the window seen in Tarkov's own renders.
- The rounds seen through it (ak12_fakeammo) are a stack drawn on a card, alpha tested: the pack's proxy picks a frame
  by how many rounds are left, and frame 0 is the full magazine. Its $color2 greens the brass towards Russian lacquered
  steel cases, as the loose rounds' (patron_545x39) does.
- The AK-105's magazines and the AK grips, which the AK-12 takes as parts, keep the AK-105's (and the 74u's) materials.

Sounds:
- The shot is Tarkov's: the pack plays a single shot as one of four takes of the shot's start (_loop1-4, 81 ms) under
  the tail of the last round (_loopt), so each take here is those two mixed. Levelled to the AK-105's (the same 7N6
  from a 415 mm barrel against its 314), then voiced like the other ported guns (ported_shots.py).
- The suppressed shot is Tarkov's three suppressed takes, built the same way and set 10 dB under the voiced open shot
  (suppressed_shots.py).
- Reload foley: the clips are the AK-105's, and so are their moves (the gun turning, the hand to the pouch, the return
  to the shoulder) and the part magazines' sounds. Tarkov's own AK-74 recordings take the AK-12's own parts, each timed
  to where its clip moves the part (j_boltcarrier and j_mag1 / j_mag2 in the AK-105's clips, read at 30 fps), by where
  in the file its loudest 10 ms is:
  - the charging handle going back (ak74_slider_up, its clack 0.21 s in) as the bolt carrier reaches the rear, frame 11
    of every empty reload, and going home (ak74_slider_down, 0.08 s in) as it gets there;
  - for the factory magazine's two clips (which the AK-74M's polymer magazine shares): the mag catch pressed
    (ak74_magrelease_button), the magazine pulled out (ak74_magout_plastic, 0.135 s in) as it leaves the well, and
    going in (ak74_magin_plastic), split at 0.25 s into its front lug catching (0.14 s in) and the catch locking
    (0.06 s into the second piece), on the frames the AK-105's own maghit and magin clicks land.
  Voiced as one set (ported_foley.py), so Tarkov's balance between its files stays: the magazine's clicks ~9 dB under
  the bolt.

Run: python Tools/ak12_assets.py [--materials-only]  (--materials-only keeps the sound events as they are)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import ported_foley
import ported_shots
import suppressed_shots
from hk416_assets import roughness_from_exponent
from ks74u_assets import ASSETS, TOOLS, asset_path, ffmpeg, load_vtf, markings, sound_event

EXTRACTED = TOOLS / "extracted" / "2962829818"
DEST = ASSETS / "Weapons" / "AK12"
EFT = "models/weapons/arc9/darsu_eft"
FIRE = "weapons/darsu_eft/ak/fire_new"
FOLEY = "weapons/darsu_eft/ak"
AK105 = ASSETS / "Weapons" / "AK105" / "ak105_assets.json"

# Source material (the SMD material name) -> friendly name. Each one's textures come from its vmt.
MATERIALS = {
    "weapon_izhmash_ak12_545x39_LOD0": "ak12_receiver",  # the receiver, trigger guard and magazine well
    "weapon_izhmash_ak12_internals_545x39_LOD0": "ak12_internals",
    "weapon_izhmash_ak12_bolt_LOD0": "ak12_bolt_carrier",
    "weapon_izhmash_ak12_bolt_larva_LOD0": "ak12_bolt",
    "weapon_izhmash_ak12_selector_LOD0": "ak12_selector",
    "reciever_ak12_izhmash_ak12_std_LOD0": "ak12_dust_cover",  # the railed dust cover
    "barrel_ak12_izhmash_415mm_545x39_LOD0": "ak12_barrel",
    "gas_block_ak12_izhmash_ak12_std_LOD0": "ak12_gas_block",
    "sight_front_ak12_izhmash_front_sight_gas_block_std_LOD0": "ak12_front_sight",
    "muzzle_ak12_izhmash_muzzle_mount_545x39_LOD0": "ak12_muzzle_mount",
    "muzzle_ak12_izhmash_ak12_muzzle_brake_std_545x39_LOD0": "ak12_muzzle_brake",
    "handguard_ak12_izhmash_ak12_std_LOD0": "ak12_handguard",
    "handguard_ak12_izhmash_ak12_cover_std_LOD0": "ak12_gas_tube_cover",
    "stock_ak12_izhmash_ak12_stock_tube_std_LOD0": "ak12_stock_tube",
    "stock_ar15_izhmash_ak12_std_LOD0": "ak12_stock",
    "pistolgrip_ak_izhmash_ak12_std_LOD0": "ak12_pistol_grip",
    "sight_rear_ak_izhmash_ak12_rear_sight_std_LOD0": "ak12_rear_sight",
    "sight_rear_all_izhmash_ak12_rear_sight_base_LOD0": "ak12_rear_sight_base",
    "mag_ak_izhmash_ak12_std_545x39_30_LOD0_new": "ak12_mag",
    "patron_545x39": "ak12_rounds",
}
WINDOW = "mag_ak_izhmash_ak12_std_545x39_30_LOD0_newglass"
FAKE_AMMO = "ak12_fakeammo"
# The window: a smoked grey polymer, ~half see-through (Tarkov draws it with a glass texture the pack doesn't ship).
WINDOW_COLOUR, WINDOW_OPACITY, WINDOW_ROUGHNESS = (36, 43, 53), 132, 80

# Tarkov's shots (_loop1-4, each under _loopt, the tail), each take turned up or down by gain_db. Mixed, the open takes'
# loudest 100 ms (K-weighted) is about -6 dB, which the AK-105's voiced shot sits near, so they're only taken down 1 dB;
# suppressed_shots.py sets the suppressed ones where they belong.
SHOTS = ([f"{FIRE}/ak12_outdoor_close_loop{n}.wav" for n in range(1, 5)], f"{FIRE}/ak12_outdoor_close_loopt.wav", -1)
SUPPRESSED = ([f"{FIRE}/ak12_outdoor_silence_close_loop{n}.wav" for n in range(1, 4)],
              f"{FIRE}/ak12_outdoor_silence_close_loopt.wav", -8)

# Tarkov's foley: friendly name -> (file under sound/, start s, end s or None). The magazine going in is two sounds.
FOLEY_FILES = {
    "slider_up": (f"{FOLEY}/ak74_slider_up.ogg", 0.0, None),
    "slider_down": (f"{FOLEY}/ak74_slider_down.ogg", 0.0, None),
    "magrelease": (f"{FOLEY}/ak74_magrelease_button.ogg", 0.0, None),
    "magout": (f"{FOLEY}/ak74_magout_plastic.ogg", 0.0, None),
    "magin_catch": (f"{FOLEY}/ak74_magin_plastic.ogg", 0.0, 0.25),
    "magin_lock": (f"{FOLEY}/ak74_magin_plastic.ogg", 0.25, None),
}
# Where in each file its loudest 10 ms is (s).
CLACK = {"slider_up": 0.21, "slider_down": 0.08, "magrelease": 0.07, "magout": 0.135, "magin_catch": 0.14,
         "magin_lock": 0.06}

FPS = 30
# The AK-105's empty clips, by the reloads' name: the bolt carrier back (frame 11 in every one) and home.
BOLT_HOME = {"reload_empty": 63, "reload_empty_smag": 55, "reload_empty_xmag": 68, "reload_empty_xmaglrg": 69}
BOLT_BACK = 11
# The AK-105's sounds these replace: its bolt's, and the factory magazine's in its own two clips.
REPLACED = re.compile(r"_boltpull|_boltrelease")
REPLACED_FACTORY = re.compile(r"_magout|_maghit|_magin")
# The factory magazine's two clips: (event, time its clack lands). The magazine leaves the well at frame 21 (reload) and
# 35 (reload_empty). The catch and the lock land where the AK-105's own maghit and magin clicks do (their events' times
# plus where the click is in each file: 0.04 and 0.03 s); the release is pressed as the AK-105's clip turns the catch,
# 0.117 s before the magazine comes away.
FACTORY = {
    "reload": [("magrelease", 21 / FPS - 0.117), ("magout", 21 / FPS), ("magin_catch", 1.6 + 0.04),
               ("magin_lock", 1.833 + 0.03)],
    "reload_empty": [("magrelease", 35 / FPS - 0.117), ("magout", 35 / FPS), ("magin_catch", 1.533 + 0.04),
                     ("magin_lock", 1.833 + 0.03)],
}


def vmt_textures(source: str) -> dict[str, str]:
    """The textures a material's vmt names ($basetexture, $bumpmap, $phongexponenttexture), as paths under materials/,
    and its $color2 if it isn't only blended by the colour map's alpha."""
    matches = [p for p in (EXTRACTED / "materials" / EFT).rglob("*.vmt") if p.stem.lower() == source.lower()]
    assert len(matches) == 1, f"{source}: {matches}"
    text = matches[0].read_text(encoding="utf-8", errors="replace")
    pattern = r'^\s*"?(\$\w+)"?\s+"?([^"\n]*?)"?\s*$'
    keys = {key.lower(): value for key, value in re.findall(pattern, text, re.MULTILINE)}
    textures = {key: keys[key].replace("\\", "/") for key in ("$basetexture", "$bumpmap", "$phongexponenttexture")
                if key in keys}
    if "$color2" in keys and keys.get("$blendtintbybasealpha", "0").strip() != "1":
        textures["$color2"] = keys["$color2"]
    return textures


def tint(colour: np.ndarray, color2: str | None) -> np.ndarray:
    if not color2:
        return colour
    factor = np.array([float(v) for v in color2.strip("[] ").split()], np.float32)
    return np.clip(colour.astype(np.float32) * factor + 0.5, 0, 255).astype(np.uint8)


def write_vmat(name: str, out: Path, lines: list[str]) -> str:
    vmat = out / f"{name}.vmat"
    vmat.write_text("\n".join(['"Layer0"', "{", '\tshader "shaders/complex.shader"', *lines, "}"]) + "\n",
                    encoding="utf-8", newline="\n")
    markings.after_rip(asset_path(vmat))
    return asset_path(vmat)


def build_eft(source: str, name: str, out: Path) -> str:
    """A complex.shader material from the vmt's _diff / _nrm / _gloss set: no metal, roughness from the exponent."""
    textures = vmt_textures(source)
    colour = tint(load_vtf(textures["$basetexture"], EXTRACTED)[:, :, :3], textures.get("$color2"))
    rel = lambda suffix: asset_path(out / f"{name}_{suffix}.png")
    Image.fromarray(colour.copy()).save(out / f"{name}_color.png")
    exponent = load_vtf(textures["$phongexponenttexture"], EXTRACTED)
    Image.fromarray(roughness_from_exponent(exponent[:, :, 0])).save(out / f"{name}_roughness.png")
    normal = load_vtf(textures["$bumpmap"], EXTRACTED)[:, :, :3].copy()
    normal[:, :, 1] = 255 - normal[:, :, 1]
    Image.fromarray(normal).save(out / f"{name}_normal.png")
    return write_vmat(name, out, [
        '\tF_SPECULAR "1"', '\tg_flMetalness "0"', '\tg_flRoughnessScaleFactor "1"', '\tg_vColorTint "[1 1 1 1]"',
        f'\tTextureColor "{rel("color")}"', f'\tTextureNormal "{rel("normal")}"',
        f'\tTextureRoughness "{rel("roughness")}"', '\tTextureAmbientOcclusion "materials/default/default_ao.tga"'])


def build_window(out: Path) -> str:
    name = "ak12_mag_window"
    for suffix, value in (("color", WINDOW_COLOUR), ("opacity", WINDOW_OPACITY), ("roughness", WINDOW_ROUGHNESS)):
        Image.new("RGB" if suffix == "color" else "L", (4, 4), value).save(out / f"{name}_{suffix}.png")
    rel = lambda suffix: asset_path(out / f"{name}_{suffix}.png")
    return write_vmat(name, out, [
        '\tF_SPECULAR "1"', '\tF_TRANSLUCENT "1"', '\tg_flMetalness "0"', '\tg_flRoughnessScaleFactor "1"',
        '\tg_vColorTint "[1 1 1 1]"', f'\tTextureColor "{rel("color")}"',
        '\tTextureNormal "materials/default/default_normal.tga"', f'\tTextureRoughness "{rel("roughness")}"',
        f'\tTextureTranslucency "{rel("opacity")}"', '\tTextureAmbientOcclusion "materials/default/default_ao.tga"'])


def build_fake_ammo(out: Path) -> str:
    """The rounds behind the window: the full magazine's frame of the stack, alpha tested, with the vmt's $color2."""
    name = "ak12_mag_rounds"
    textures = vmt_textures(FAKE_AMMO)
    pixels = load_vtf(textures["$basetexture"], EXTRACTED)
    Image.fromarray(tint(pixels[:, :, :3], textures.get("$color2")).copy()).save(out / f"{name}_color.png")
    Image.fromarray(pixels[:, :, 3].copy()).save(out / f"{name}_opacity.png")
    # Its vmt has a flat phong exponent of 0.5 and a strong boost: lacquered cases, about as glossy as the rounds'.
    Image.new("L", (4, 4), 115).save(out / f"{name}_roughness.png")
    rel = lambda suffix: asset_path(out / f"{name}_{suffix}.png")
    return write_vmat(name, out, [
        '\tF_SPECULAR "1"', '\tF_ALPHA_TEST "1"', '\tg_flAlphaTestReference "0.5"', '\tg_flAntiAliasedEdgeStrength "1"',
        '\tg_flMetalness "0"', '\tg_flRoughnessScaleFactor "1"', '\tg_vColorTint "[1 1 1 1]"',
        f'\tTextureColor "{rel("color")}"', '\tTextureNormal "materials/default/default_normal.tga"',
        f'\tTextureRoughness "{rel("roughness")}"', f'\tTextureTranslucency "{rel("opacity")}"',
        '\tTextureAmbientOcclusion "materials/default/default_ao.tga"'])


def build_materials() -> dict[str, str]:
    """Source material -> vmat path: the AK-12's own, then the AK-105's (its magazines and the AK grips, as parts)."""
    out = DEST / "materials"
    out.mkdir(parents=True, exist_ok=True)
    materials = json.loads(AK105.read_text(encoding="utf-8"))["materials"]
    for source, name in MATERIALS.items():
        materials[source] = build_eft(source, name, out)
    materials[WINDOW] = build_window(out)
    materials[FAKE_AMMO] = build_fake_ammo(out)
    return materials


def mix_take(out: Path, start: str, tail: str, name: str, gain_db: int) -> Path:
    """One shot: the start of a shot under the last round's tail, as the pack plays a single shot, turned up or down
    gain_db and limited like the other shots."""
    wav = out / f"{name}.wav"
    ffmpeg(["-i", str(EXTRACTED / "sound" / start), "-i", str(EXTRACTED / "sound" / tail), "-filter_complex",
            f"[0:a][1:a]amix=inputs=2:duration=longest:normalize=0,volume={gain_db}dB,"
            "alimiter=limit=0.891:attack=1:release=50:level=false",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
    return wav


def level_shots(out: Path, name: str) -> list[Path]:
    """The open shot's takes: <name>_01.wav to _04."""
    starts, tail, gain = SHOTS
    return [mix_take(out, start, tail, f"{name}_{index:02d}", gain) for index, start in enumerate(starts, 1)]


def foley_event(out: Path, name: str) -> str:
    source, start, end = FOLEY_FILES[name]
    wav = out / f"ak12_{name}.wav"
    trim = ["-ss", str(start)] + (["-to", str(end)] if end is not None else [])
    ffmpeg([*trim, "-i", str(EXTRACTED / "sound" / source), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
    event = out / f"ak12.{name}.sound"
    sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
    return asset_path(event)


def at(sounds: dict[str, str], seconds: float, event: str) -> None:
    """Adds a sound at seconds; two sounds can't share a key, so a later one plays 10 ms after."""
    seconds = max(0.0, seconds)
    while f"{round(seconds, 3):g}" in sounds:
        seconds += 0.01
    sounds[f"{round(seconds, 3):g}"] = event


def build_sounds() -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """The sound events by friendly name, and each reload clip's {seconds: event}."""
    out = DEST / "sounds"
    out.mkdir(parents=True, exist_ok=True)
    ak105 = json.loads(AK105.read_text(encoding="utf-8"))

    # Same curve as sounds/weapons/m4a1/m4_shot.sound.
    m4 = json.loads((ASSETS / "sounds" / "weapons" / "m4a1" / "m4_shot.sound").read_text(encoding="utf-8"))
    fire = out / "ak12.fire.sound"
    # The rip's shots, voiced towards what a shooter hears outdoors (ported_shots.py).
    sound_event(fire, ported_shots.build("ak12", out), pitch=ported_shots.event_pitch("ak12"),
                decibels=m4["Decibels"], distance=m4["Distance"], falloff=m4["Falloff"])

    # The shared suppressed-rifle event's settings and curve, with the AK-12's own suppressed takes.
    suppressed = json.loads((ASSETS / "sounds" / "swb" / "attachments" / "silencer" / "swb_rifle.silenced.fire.sound")
                            .read_text(encoding="utf-8"))
    starts, tail, gain = SUPPRESSED
    suppressed["Sounds"] = [asset_path(mix_take(out, start, tail, f"ak12_suppressed_shot_{index:02d}", gain)
                                       .with_suffix(".vsnd")) for index, start in enumerate(starts, 1)]
    fire_suppressed = out / "ak12.fire_suppressed.sound"
    fire_suppressed.write_text(json.dumps(suppressed, indent=2) + "\n", encoding="utf-8", newline="\n")

    own = {name: foley_event(out, name) for name in FOLEY_FILES}
    # The draw and holster are the AK-105's (its raise and drop).
    sounds = {"fire": asset_path(fire), "fire_suppressed": asset_path(fire_suppressed),
              "raise": ak105["sounds"]["raise"], "drop": ak105["sounds"]["drop"], **own}

    reloads = {}
    for clip, events in ak105["reloads"].items():
        factory = clip in FACTORY
        timed: dict[str, str] = {}
        for seconds, event in sorted(events.items(), key=lambda item: float(item[0])):
            if REPLACED.search(event) or (factory and REPLACED_FACTORY.search(event)):
                continue
            at(timed, float(seconds), event)
        if clip in BOLT_HOME:
            at(timed, BOLT_BACK / FPS - CLACK["slider_up"], own["slider_up"])
            at(timed, BOLT_HOME[clip] / FPS - CLACK["slider_down"], own["slider_down"])
        for name, clack in FACTORY.get(clip, []):
            at(timed, clack - CLACK[name], own[name])
        reloads[clip] = dict(sorted(timed.items(), key=lambda item: float(item[0])))
    # The suppressed shot, voiced like the open shots (suppressed_shots.py).
    suppressed_shots.voice("ak12")
    # Tarkov's foley, voiced away from the game's sound design (ported_foley.py). The AK-105's are voiced already.
    ported_foley.voice("ak12")
    return sounds, reloads


def main() -> None:
    materials = build_materials()
    manifest_path = DEST / "ak12_assets.json"
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
