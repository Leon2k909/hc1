"""Separate Lowtide's LPG bottles from the existing dressing, preserving every other face.

Run once (or safely again) to write the leak/jet audio and four damageable scene objects.
The models themselves are built by Sources/Lowtide/lpg_canister_v2/. lowtide_map.py also emits these objects on rebuild.
"""
import argparse
import json
import math
import wave
from collections import Counter
from pathlib import Path

import numpy as np

import map_kit as K
import lowtide_forklift as F

# Built by Sources/Lowtide/lpg_canister_v2/; this tool only places them.
MODEL_RESOURCE = "models/props/lowtide/lpg_canister_v2"
SCENE = K.ASSETS / "scenes/maps/Lowtide/lowtide.scene"
IDS = K.SceneIds("42831158-c0ca-45b1-a99e-b3b3f5f2d624")


def placements():
    for sign, side in ((1, "east"), (-1, "west")):
        yield side, "warehouse", sign * 640, 560, "-e" if sign == 1 else "+e"
        yield side, "quay", sign * 1100, -1180, "+e" if sign == 1 else "-e"


def scene_objects():
    objects = []
    for side, area, e, n, facing in placements():
        key = f"lpg/{side}/{area}"
        frame = F.Forklift(K.Model(), e, n, facing)
        centre = K.to_world(frame.p((0, -42.2, 49.8)))
        # Keep each bottle a root: blast raycasts must ignore this bottle, not the entire Lowtide map.
        obj = K.game_object(IDS, f"Forklift LPG ({side} {area})", key, centre,
            K.yaw_rotation(K.plan_yaw(frame.frame.y)), tags="lpg_canister", components=[
                K.component(IDS, "Sandbox.ModelRenderer", key + "/renderer",
                    Model=MODEL_RESOURCE + "/lpg_canister.vmdl", RenderType="On", Tint="1,1,1,1"),
                K.component(IDS, "Sandbox.ModelCollider", key + "/collider",
                    Model=MODEL_RESOURCE + "/lpg_canister.vmdl", IsTrigger=False, Static=True),
                K.component(IDS, "Sandbox.SphereCollider", key + "/valve", Center="0,17.8,0",
                    Radius=1.5, IsTrigger=False, Static=True, Surface="surfaces/metal.surface"),
                K.component(IDS, "Facepunch.LpgCanister", key + "/behaviour",
                    IntactModel=MODEL_RESOURCE + "/lpg_canister.vmdl",
                    RupturedModel=MODEL_RESOURCE + "/lpg_canister_ruptured.vmdl",
                    LeakSound="sounds/world/lpg/leak.sound", FireSound="sounds/world/lpg/jet.sound",
                    RuptureSound="sounds/weapons/grenade/he_grenade_explode.sound", BlastRadius=240, BlastDamage=120),
            ])
        objects.append(obj)
    return objects


def triangle_key(paint, points):
    # Compare in exactly the OBJ writer's axes/precision, including material. No bounding-box guesses.
    return paint, tuple(sorted(tuple(float(x) for x in K.obj_vector(K.to_world(p)).split()) for p in points))


def split_dressing():
    for side in ("east", "west"):
        expected = Counter()
        for part_side, area, e, n, facing in placements():
            if side != part_side:
                continue
            tank = K.Model()
            F.Forklift(tank, e, n, facing).gas_tank()
            for paint, polygons in tank.polygons.items():
                for points, _ in polygons:
                    for i in range(1, len(points) - 1):
                        expected[triangle_key(paint, [points[0], points[i], points[i + 1]])] += 1
        path = K.ASSETS / f"models/maps/lowtide/lowtide_dress_{side}.obj"
        lines = path.read_text().splitlines(keepends=True)
        vertices, material, removed, output = [], None, Counter(), []
        for line in lines:
            if line.startswith("v "):
                vertices.append(tuple(float(x) for x in line.split()[1:4]))
            elif line.startswith("usemtl "):
                material = line.split()[1]
            elif line.startswith("f "):
                points = [vertices[int(x.split("/")[0]) - 1] for x in line.split()[1:]]
                key = material, tuple(sorted(points))
                if removed[key] < expected[key]:
                    removed[key] += 1
                    continue
            output.append(line)
        count = sum(removed.values())
        # A partially matched bottle signals different source geometry; do not modify the map then.
        if count and removed != expected:
            raise RuntimeError(f"{path.name}: partial match {count}/{sum(expected.values())}; dressing untouched")
        if count:
            path.write_text("".join(output), newline="\n")
        print(f"{path.name}: removed {count} bottle triangles; all other vertices/faces preserved")


def update_scene():
    text = SCENE.read_text()
    current = json.loads(text)
    existing = [o for o in current["GameObjects"] if any(c.get("__type") == "Facepunch.LpgCanister" for c in o.get("Components", []))]
    if existing:
        replacement = {o["__guid"]: o for o in scene_objects()}
        for old in existing:
            def formatted(obj):
                return "\n".join("    " + line for line in json.dumps(obj, indent=2).splitlines())
            text = text.replace(formatted(old), formatted(replacement[old["__guid"]]), 1)
        assert len([o for o in json.loads(text)["GameObjects"] if o.get("__guid") in replacement]) == 4
        SCENE.write_text(text, newline="\r\n")
        print("Updated the four reactive bottles without changing other scene objects")
        return
    # Append only new root objects. Preserve all existing scene text and current local edits.
    marker = '\n  ],\n  "SceneProperties"'
    assert marker in text, "Unexpected scene format"
    extra = ",\n" + ",\n".join("\n".join("    " + line for line in json.dumps(o, indent=2).splitlines()) for o in scene_objects())
    text = text.replace(marker, extra + marker, 1)
    parsed = json.loads(text)
    assert len(parsed["GameObjects"]) == len(current["GameObjects"]) + 4
    SCENE.write_text(text, newline="\r\n")
    print("Added four damageable LPG cylinders to Lowtide")


def write_audio():
    folder = K.ASSETS / "sounds/world/lpg"
    folder.mkdir(parents=True, exist_ok=True)
    rate, seconds = 44100, 4
    rng = np.random.default_rng(74219)
    noise = rng.normal(size=rate * seconds)
    for name, cutoff, volume in (("leak", (1600, 10000), .28), ("jet", (120, 3500), .4)):
        spectrum = np.fft.rfft(noise)
        freq = np.fft.rfftfreq(len(noise), 1 / rate)
        low, high = cutoff
        gain = np.minimum(1, (freq / low) ** 2) / (1 + (freq / high) ** 6)
        sound = np.fft.irfft(spectrum * gain, n=len(noise))
        sound /= max(abs(sound))
        # Periodic modulation and frequency-domain filtering make the loop continuous.
        t = np.arange(len(sound)) / rate
        sound *= volume * (0.85 + 0.15 * np.sin(2 * math.pi * (3 if name == "jet" else 1) * t))
        with wave.open(str(folder / f"{name}.wav"), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            output.writeframes((sound * 32767).astype("<i2").tobytes())
        (folder / f"{name}.wav.meta").write_text(json.dumps(dict(loop=True, start=0, end=0, rate=rate, compress=False, stream=False), indent=2))
        event = dict(UI=False, Volume="1", Pitch="1", Decibels=70, SelectionMode="Random",
            Sounds=[f"sounds/world/lpg/{name}.vsnd"], Occlusion=True, AirAbsorption=True, Transmission=True,
            OcclusionRadius=12, DistanceAttenuation=True, Distance=900 if name == "leak" else 1500,
            Falloff=[dict(x=0, y=1, **{"in": 0, "out": 0, "mode": "Linear"}),
                     dict(x=1, y=0, **{"in": 0, "out": 0, "mode": "Linear"})],
            __references=[], __version=1)
        (folder / f"{name}.sound").write_text(json.dumps(event, indent=2))
        print(f"{name}: {seconds}s loop")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-only", action="store_true")
    args = parser.parse_args()
    write_audio()
    if not args.audio_only:
        split_dressing()
        update_scene()


if __name__ == "__main__":
    main()
