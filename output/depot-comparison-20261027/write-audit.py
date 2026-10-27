"""Summarize the read-only Depot inspection without touching game content."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
native = json.loads((out / "native-content.json").read_text(encoding="utf-8"))
scenes = json.loads((out / "scene-summary.json").read_text(encoding="utf-8"))

def rows(path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for item in raw["content"]:
        if item["type"] != "text":
            continue
        try:
            result.append(json.loads(item["text"]))
        except ValueError:
            pass
    return result

initial = rows(out / "initial-status-current/editor_status.json")[0]
last = rows(out / "final-read/call_tools.json")
status = next(r for r in last if "ActiveScenePath" in r)
camera = next(r for r in last if "FieldOfView" in r)
before_camera = rows(out / "current-view/call_tools.json")[0]
assert initial == status, "The shared editor state changed during inspection."
assert before_camera == camera, "The user's camera moved during inspection."
decal_materials = [m["Path"] for m in native["Materials"] if "/decals/" in m["Path"]]
assert len(decal_materials) == 32

inputs = [
    "Assets/scenes/maps/Depot/Depot.scene",
    "Assets/materials/collider/co_concrete.vmat",
    "Assets/materials/ares/ar_concrete.vmat",
    "Assets/materials/veridant/vr_concrete.vmat",
    "Assets/materials/belltower/scans/limestone.vmat",
    "Assets/materials/belltower/plaster_cream.vmat",
    "Tools/collider_materials.py",
    "Tools/collider_map.py",
]
report = {
    "date": "2026-10-27",
    "scope": "Read-only visual and asset comparison; no game files changed.",
    "project_root": str(root),
    "reference": native["Map"],
    "depot_native": {
        "unique_model_resource_paths": len(native["Models"]),
        "distinct_non_error_materials": len(native["Materials"]),
        "distinct_decal_materials": len(decal_materials),
        "decal_materials": decal_materials,
        "reflection_probes": len(native["Reflections"]),
        "reflection_modes": {"Realtime": 55},
        "spot_lights": native["SceneObjectTypes"]["Sandbox.SceneSpotLight"],
        "point_lights": native["SceneObjectTypes"]["Sandbox.ScenePointLight"],
    },
    "custom_scene_authored_reflection_counts": {
        Path(path).parent.name: data["types"].get("Sandbox.EnvmapProbe", 0)
        for path, data in scenes.items() if "/Depot/" not in path
    },
    "observations": [
        "Depot's viewed concrete room has localized runoff, layered wall/base dirt, irregular rubble, damaged thresholds and recessed construction joints.",
        "Native model materials include concrete trim sheets, damaged blend materials, and distinct dirt, leak, crack, footprint and stain decals.",
        "The reviewed Belltower square has more uninterrupted paving, continuous facade edges and repetitive construction than Depot's inspected room.",
        "The reviewed Ares hall and Veridant courtyard have broad repeating panel/stone patterns, simple silhouette transitions and limited localized wear between props.",
        "Custom materials already contain color, normal and roughness textures. Collider concrete is 1024 square; Ares and Veridant concrete are 2048 square; Belltower scanned limestone is 4096 square with its own AO.",
        "Belltower's scanned and layered plaster surfaces demonstrate that increasing texture resolution alone cannot address all of the perceived quality gap.",
    ],
    "priority_order": [
        "Choose one representative player-height area per map and review the full composition at consistent FOV.",
        "Improve primary architecture: appropriate bevels, recesses, trim junctions, construction thickness and selectively damaged edges.",
        "Apply location-dependent wear and material blending at wall bases, corners, thresholds, water paths and traffic routes; preserve the intended clean or weathered character of each map.",
        "Unify material scale, normal strength and roughness across architecture and props.",
        "Review bounced light, contact shadows and local reflections after geometry/material work, then rebake changed areas and verify player visibility and performance.",
    ],
    "limits": [
        "Depot was inspected live in the stopped editor; comparison visuals for Belltower, Ares and Veridant are existing native captures from their recent work.",
        "Different environments and capture profiles prevent treating these images as a controlled lighting comparison.",
        "Material, object and probe counts are inventories, not quality scores or recommendations to duplicate those counts.",
        "Mounted-file enumeration returned no Depot files; this does not establish whether legacy map lightmaps are present or missing. No lightmap warnings matched the current console buffer.",
        "No gameplay, multiplayer or GPU benchmark was run.",
    ],
    "input_sha256": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in inputs},
    "depot_capture": str(out / "current-view/call_tools.png"),
    "comparison_captures": [
        "output/belltower/quality/lamp-placement-installed/square-east.png",
        "output/photographic-look-20261027/ares-gi-reduced/ares-hall-after.png",
        "output/photographic-look-20261027/daylight-review/veridant-courtyard-after.png",
    ],
    "editor_state_preserved": True,
    "editor_camera_preserved": True,
    "final_compile_errors": status["LastCompileErrors"],
}
(out / "audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"report": str(out / "audit.json"), "decal_materials": len(decal_materials), "editor_preserved": True, "camera_preserved": True}))
