"""Preserve the native lighting bake and its source hashes for scene regeneration."""
import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
import belltower_map as B

ROOT = Path(__file__).resolve().parents[1]


def texture_path(value):
    # New engine serializers emit a resource handle; old captures use a path.
    # Keep the regeneration cache portable instead of storing session IDs.
    path = value.get("Path") if isinstance(value, dict) else value
    if not isinstance(path, str) or not path.startswith("lighting/belltower/") or not path.endswith(".vtex"):
        raise ValueError(f"Unexpected Belltower lighting texture: {path!r}")
    resolved = (ROOT / "Assets" / (path + "_c")).resolve()
    if not resolved.is_relative_to(ROOT / "Assets/lighting/belltower"):
        raise ValueError("Lighting texture must remain inside Belltower assets")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", help="Native capture folder under output/belltower/quality")
    parser.add_argument("--volume-id", default="town", help="Stable volume key; local volumes preserve the town bake")
    parser.add_argument("--normal-bias", type=float, help="Reviewed runtime normal bias; does not rebake")
    parser.add_argument("--view-bias", type=float, help="Reviewed runtime view bias; does not rebake")
    parser.add_argument("--check", action="store_true", help="Validate the capture without publishing its cache")
    args = parser.parse_args()
    directory = (ROOT / "output/belltower/quality" / args.capture).resolve()
    if not directory.is_relative_to(ROOT / "output/belltower/quality"):
        raise ValueError("Capture must be in the Belltower quality folder")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.volume_id):
        raise ValueError("Volume ID must contain lowercase letters, digits or hyphens")
    # Finish all validation before writing anything to the accepted cache. A
    # failed relocation can leave a directory without a completed bake.
    status = (directory/"bake-status.txt").read_text().strip()
    if not status.startswith("Complete "):
        raise ValueError("The native bake has not completed")
    grid = list(map(int,status.removeprefix("Complete ").split(",")))
    if len(grid)!=3 or min(grid)<1:
        raise ValueError("Invalid native probe counts")
    bake = json.loads((directory / "bake-result.json").read_text())
    if (bake.get("Passes") != 2 or bake.get("SavedFinalIrradiance") is not True
            or bake.get("Grid") != ",".join(map(str, grid))):
        raise ValueError("The completed second lighting pass has not been verified")
    volume = json.loads((directory / "indirect-light.json").read_text())
    volume["__guid"] = B.ids("indirect/" + args.volume_id)
    component = next(c for c in volume["Components"] if c["__type"] == "Sandbox.IndirectLightVolume")
    component["__guid"] = B.ids("indirect/" + args.volume_id + "/volume")
    for key, value in (("NormalBias", args.normal_bias), ("ViewBias", args.view_bias)):
        if value is not None:
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
            component[key] = value
    for key in ("IrradianceTexture", "DistanceTexture", "RelocationTexture"):
        component[key] = texture_path(component[key])
        resource = ROOT / "Assets" / (component[key] + "_c")
        if not resource.is_file() or resource.stat().st_size == 0:
            raise FileNotFoundError(resource)
    destination = ROOT / "Sources/Belltower/lighting"
    existing_path = destination / "indirect.json"
    group = json.loads(existing_path.read_text()) if existing_path.is_file() else B.K.game_object(B.ids,"Indirect Light","indirect",children=[])
    # Replace just this volume, keeping overlapping smaller volumes and the
    # broad town volume. The engine prioritizes the smallest volume at runtime.
    group["Children"] = [c for c in group.get("Children",[]) if c.get("__guid") != volume["__guid"]] + [volume]
    reflections_path = directory / "reflections-baked.json"
    reflections = None
    if reflections_path.is_file():
        reflections = json.loads(reflections_path.read_text())
        for child in reflections["Children"]:
            probe = next(c for c in child["Components"] if c["__type"] == "Sandbox.EnvmapProbe")
            probe["BakedTexture"] = texture_path(probe["BakedTexture"])
            if probe["Mode"] != "Baked" or not (ROOT/"Assets"/(probe["BakedTexture"]+"_c")).is_file():
                raise ValueError(f"Missing baked reflection for {child['Name']}")
    sources = [ROOT/"Assets/models/maps/belltower"/f"belltower_{part}.obj" for part in ("centre","west","east")]
    materials = sorted((ROOT/"Assets/materials/belltower").glob("*.vmat"))
    sources += materials
    # A material definition alone cannot reveal a changed shader or texture.
    # Record the local source dependencies used by those definitions as well.
    for material in materials:
        for relative in re.findall(r'^\s*(?:shader|Texture\w+)\s+"([^"]+)"', material.read_text(), re.MULTILINE):
            dependency = ROOT/"Assets"/relative
            if dependency.is_file():
                sources.append(dependency)
    sources += [ROOT/"Sources/Belltower/scans/manifest.json"]
    sources += [ROOT/"Sources/Belltower/landscape/trees.json"]
    landscape_textures = ROOT/"Sources/Belltower/landscape/textures.json"
    if landscape_textures.is_file():
        sources.append(landscape_textures)
        sources += [ROOT/path for path in json.loads(landscape_textures.read_text())["source_sha256"]]
    hashes = {}
    for source in sorted(set(sources)):
        with source.open("rb") as stream:
            hashes[source.relative_to(ROOT).as_posix()] = hashlib.file_digest(stream,"sha256").hexdigest()
    rendered = json.loads((directory/"visual-scene.json").read_text())
    bake_lights = [g for g in rendered["GameObjects"] if g.get("Name") in ("Sun","Sky","Fog")]
    record = {"capture":args.capture,"preserved_at_utc":datetime.now(timezone.utc).isoformat(),
                "engine":"26.10.13","probe_grid":grid,"runtime_strength":component["RuntimeIntensity"],
                "native_bake":bake,
                "normal_bias":component["NormalBias"],"view_bias":component["ViewBias"],
                "bake_lights":bake_lights,
                "source_sha256":hashes,"rebake":"Use the native engine after changing geometry, materials, or lighting."}
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    if "capture" in manifest:
        manifest = {"volumes": {"town": manifest}}
    manifest.setdefault("volumes", {})[args.volume_id] = record
    if args.check:
        print(f"Validated {args.volume_id}: {grid}; bias {component['NormalBias']}/{component['ViewBias']}; {len(group['Children'])} volumes would be retained. Cache unchanged.")
        return
    destination.mkdir(parents=True,exist_ok=True)
    payloads = {"indirect.json": group, "manifest.json": manifest}
    if reflections is not None:
        payloads["reflections.json"] = reflections
    for name, value in payloads.items():
        pending = destination / (name + ".pending")
        pending.write_text(json.dumps(value,indent=2)+"\n")
        pending.replace(destination / name)
    print(f"Preserved native {args.volume_id} lighting and source hashes; scene save remains in the editor.")


if __name__ == "__main__":
    main()
