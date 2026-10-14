"""Separate Lowtide's LPG bottles from the existing dressing, preserving every other face.

Run once (or safely again) to write the intact/torn bottle models, leak/jet audio and
four damageable scene objects. lowtide_map.py also emits these objects on rebuild.
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

MODEL_RESOURCE = "models/props/lowtide"
MODEL_OUT = K.ASSETS / MODEL_RESOURCE
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


class TornBottle(F.Forklift):
    def lathe(self, centre, axis, profile, paint=F.STEEL, segments=40, closed=False, smooth=True):
        if paint != F.SILVER or len(profile) != 10:
            return super().lathe(centre, axis, profile, paint, segments, closed, smooth)
        # A longitudinal split opens the rear of the shell; the torn lips curl outwards.
        centre = np.asarray(centre, float)
        angles = np.linspace(-math.pi * 2 / 3, math.pi * 2 / 3, 48)
        for a in range(len(profile) - 1):
            x0, r0 = profile[a]
            x1, r1 = profile[a + 1]
            for b in range(len(angles) - 1):
                points = []
                for x, radius, angle in ((x0, r0, angles[b]), (x1, r1, angles[b]),
                                         (x1, r1, angles[b + 1]), (x0, r0, angles[b + 1])):
                    lip = max(0, (abs(angle) - 1.55) / .55)
                    jagged = 1 + .15 * math.sin(x * 1.7 + angle * 8)
                    r = radius * (1 + lip * jagged * 2.8 / 6.3)
                    points.append(centre + (x, r * math.cos(angle), r * math.sin(angle)))
                angle = (angles[b] + angles[b + 1]) / 2
                normal = (0, math.cos(angle), math.sin(angle)) if x0 != x1 else (-1 if x0 < 0 else 1, 0, 0)
                uv = None if x0 == x1 else [((x0 + 17) / 34, b / 47), ((x1 + 17) / 34, b / 47),
                                            ((x1 + 17) / 34, (b + 1) / 47), ((x0 + 17) / 34, (b + 1) / 47)]
                self.poly(paint, points, normal, uv=uv)
                self.poly(F.BLACK, points[::-1], -np.asarray(normal), uv=None if uv is None else uv[::-1])


def write_models():
    for name, cls in (("lpg_canister", F.Forklift), ("lpg_canister_ruptured", TornBottle)):
        model = K.Model()
        # Recenter on the bottle rather than the truck's ground origin.
        cls(model, 0, 42.2, "+n", -49.8).gas_tank()
        if name == "lpg_canister":
            frame = F.Forklift(model, 0, 42.2, "+n", -49.8)
            profile = ((-17, 0), (-17, 2.3), (-16.4, 4.7), (-15.2, 5.9), (-13.5, 6.3),
                       (13.5, 6.3), (15.2, 5.9), (16.4, 4.7), (17, 2.3), (17, 0))
            points = {tuple(frame.p((x, -42.2 + radius * math.cos(a), 49.8 + radius * math.sin(a))))
                      for x, radius in profile for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)}
            model.hull(sorted(points), "metal")
        F.configure(model)
        F.validate(model)
        count = K.write_model(MODEL_OUT, MODEL_RESOURCE, name, model)
        print(f"{name}: {count} triangles; bounds={model.bounds()}")
    cap = K.Model()
    F.Forklift(cap, 0, 0).lathe((0, 0, 0), (1, 0, 0),
        ((-1.75, 0), (-1.75, 2.3), (-1.15, 4.7), (.05, 5.9), (1.75, 6.3), (1.75, 0)), F.SILVER, 32)
    F.configure(cap)
    F.validate(cap)
    K.write_model(MODEL_OUT, MODEL_RESOURCE, "lpg_canister_cap", cap)


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
    parser.add_argument("--models-only", action="store_true")
    args = parser.parse_args()
    write_models()
    write_audio()
    if not args.models_only:
        split_dressing()
        update_scene()


if __name__ == "__main__":
    main()
