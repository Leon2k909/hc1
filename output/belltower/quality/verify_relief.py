from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/belltower/quality/saved-relief-v1"
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

before = read(ROOT / "output/belltower/quality/before-relief-v1/Assets/scenes/maps/Belltower/belltower.scene")
scene = read(ROOT / "Assets/scenes/maps/Belltower/belltower.scene")
visual = {"Sun", "Sky", "Fog", "Look", "Reflections", "Indirect Light", "Landscape trees"}
gameplay = lambda data: [g for g in data["GameObjects"] if g.get("Name") not in visual]
assert gameplay(before) == gameplay(scene)
assert before["SceneProperties"] == scene["SceneProperties"]
tree_group = next(g for g in scene["GameObjects"] if g.get("Name") == "Landscape trees")
assert len(tree_group["Children"]) == 1600
assert tree_group == next(g for g in before["GameObjects"] if g.get("Name") == "Landscape trees")
lighting = read(ROOT / "Sources/Belltower/lighting/manifest.json")["volumes"]["town"]
assert lighting["capture"] == "daylight-v7"
assert lighting["native_bake"]["Passes"] == 2 and lighting["native_bake"]["SavedFinalIrradiance"]
mismatch = [p for p, digest in lighting["source_sha256"].items() if sha(ROOT/p) != digest]
assert not mismatch, mismatch
old_lighting = read(ROOT / "output/belltower/quality/before-relief-v1/Sources/Belltower/lighting/manifest.json")["volumes"]["town"]
for part in ("centre", "west", "east"):
    p = f"Assets/models/maps/belltower/belltower_{part}.obj"
    assert lighting["source_sha256"][p] == old_lighting["source_sha256"][p]
assert (ROOT / "Sources/Belltower/shaders/belltower_relief.shader").read_bytes() == (ROOT / "Assets/shaders/belltower_relief.shader").read_bytes()
sys.path.insert(0, str(ROOT/"Tools"))
import belltower_quality_materials as materials
for name in ("street_cobbles", "rubble"):
    assert materials.material_text(name) == (ROOT/f"Assets/materials/belltower/{name}.vmat").read_text()

raw = read(OUT / "run_csharp.json")
native = json.loads(next(c["text"] for c in raw["content"] if c["type"] == "text"))
assert native["SourceUnchanged"] and native["Before"]["Scene"] == "lowtide" and not native["IsPlaying"]
views = read(ROOT / "Sources/Belltower/editor/capture-config.json")["views"]
assert len(views) == len(set(views)) == 13
images = {}
for view in views:
    p = OUT / (view + ".png")
    png = p.read_bytes()
    assert int.from_bytes(png[16:20], "big") == 1920 and int.from_bytes(png[20:24], "big") == 1080
    images[p.name] = sha(p)
assert sha(ROOT/"Assets/ui/maps/belltower.png") == images["map_art.png"]
assert "daylight-v7" in json.dumps(next(g for g in scene["GameObjects"] if g.get("Name") == "Indirect Light"))
assert "daylight-v7" in json.dumps(next(g for g in scene["GameObjects"] if g.get("Name") == "Reflections"))
timings = {}
for view in ("west_street", "street_surface", "wall_stone", "terrace", "council_hall"):
    folder = "relief-v1-before-wall" if view == "wall_stone" else "relief-v1-before"
    previous = read(ROOT/f"output/belltower/quality/{folder}/{view}-timing.json")
    current = read(OUT / (view + "-timing.json"))
    timings[view] = {"before_median_ms": previous["MedianMs"], "after_median_ms": current["MedianMs"]}

record = {
    "saved_capture": "saved-relief-v1", "bake": "daylight-v7", "views": views,
    "gameplay_roots_preserved": True, "scene_properties_preserved": True,
    "town_geometry_preserved": True, "landscape_trees_preserved": 1600,
    "native_capture_source_unchanged": native["SourceUnchanged"], "before_editor": native["Before"],
    "source_hashes_verified": len(lighting["source_sha256"]), "map_art_matches_native_capture": True,
    "native_bake": lighting["native_bake"], "image_sha256": images,
    "materials": {name: materials.definitions()[name] for name in ("street_cobbles", "rubble")},
    "render_timings": {"scope": "Native RenderToBitmap including GPU readback; not game FPS", "samples_per_view": 16, "views": timings},
    "controlled_relief_comparison": read(ROOT/"output/belltower/quality/relief-cost-check/summary.json"),
    "limitations": ["Parallax does not alter silhouettes or collision.", "No new full-game FPS measurement.", "The overall AAA visual goal remains open; distant canopy, facade repetition, lamps and furniture still need work."]
}
(OUT/"verification.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"verified": True, "views": len(views), "source_hashes": len(lighting["source_sha256"]), "render_timings": timings}, indent=2))
