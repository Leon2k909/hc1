"""Inspect the C: checkout without changing any game assets."""
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def walk(objects):
    for obj in objects:
        for c in obj.get("Components", []):
            yield obj, c
        yield from walk(obj.get("Children", []))

reports = []
for path in sorted((ROOT / "Assets/scenes/maps").rglob("*.scene")):
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    entries = list(walk(data.get("GameObjects", [])))
    wanted = ("DirectionalLight", "SkyBox2D", "GradientFog", "Tonemapping", "ColorGrading", "IndirectLightVolume", "EnvmapProbe")
    lights = [{"object": obj.get("Name"), "object_id": obj.get("__guid"), "rotation": obj.get("Rotation"), "component": c}
              for obj, c in entries if c.get("__type", "").split(".")[-1] in wanted]
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    report = {"path": rel, "title": data.get("Title"), "lighting": lights}
    reports.append(report)
    backup = OUT / "before-scenes" / Path(rel).relative_to("Assets/scenes/maps")
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_bytes(raw)
    summary = {"map": data.get("Title") or path.stem, "components": []}
    for entry in lights:
        c = entry["component"]
        kind = c["__type"].split(".")[-1]
        if kind in ("IndirectLightVolume", "EnvmapProbe"):
            continue
        keys = {"DirectionalLight": ("LightColor", "SkyColor", "ShadowHardness"),
                "SkyBox2D": ("SkyMaterial", "Tint"),
                "GradientFog": ("Color", "StartDistance", "EndDistance"),
                "Tonemapping": ("Mode", "MinimumExposure", "MaximumExposure"),
                "ColorGrading": ("ColorTempK", "BlendFactor")}[kind]
        summary["components"].append({"type": kind, **{k:c.get(k) for k in keys}})
    summary["GI"] = sum(c["component"]["__type"].endswith("IndirectLightVolume") for c in lights)
    print(json.dumps(summary))
(OUT / "before-inventory.json").write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")

