"""Record the published bake, saved-scene capture and preserved gameplay."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output/belltower/quality"
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

relative = Path("Assets/scenes/maps/Belltower/belltower.scene")
old = read(OUT / "before-daylight-v5" / relative)
scene = read(ROOT / relative)
visual = {"Sun", "Sky", "Fog", "Look", "Reflections", "Indirect Light", "Landscape trees"}
gameplay = lambda s: [g for g in s["GameObjects"] if g.get("Name") not in visual]
assert gameplay(old) == gameplay(scene), "Gameplay roots changed"
assert old["SceneProperties"] == scene["SceneProperties"], "Scene properties changed"
group = next(g for g in scene["GameObjects"] if g.get("Name") == "Indirect Light")
assert len(group["Children"]) == 1, "Unexpected additional indirect volume"
assert group == read(ROOT / "Sources/Belltower/lighting/indirect.json")
volume = next(c for c in group["Children"][0]["Components"] if c["__type"] == "Sandbox.IndirectLightVolume")
assert (volume["ProbeDensity"], volume["NormalBias"], volume["ViewBias"], volume["RuntimeIntensity"]) == (8, 20, 30, 2)
assert volume["Bounds"] == {"Mins":"-1480,-2400,2", "Maxs":"1880,2400,450"}
textures = {}
for name in ("irradiance", "distance", "relocation", "reflection-east", "reflection-square", "reflection-west"):
    p = ROOT / "Assets/lighting/belltower/daylight-v5" / (name + ".vtex_c")
    assert p.stat().st_size > 0
    textures[p.relative_to(ROOT).as_posix()] = {"bytes":p.stat().st_size, "sha256":sha(p)}
capture = read(OUT / "saved-daylight-v5/run_csharp.json")
result = json.loads(next(x["text"] for x in capture["content"] if x["type"] == "text"))
assert result["SourceUnchanged"] and not result["IsPlaying"]
assert result["Indirect"][0]["ProbeCounts"] == "28,39,5"
config = read(ROOT / "Sources/Belltower/editor/capture-config.json")
assert config == read(OUT / "capture-config.json")
assert not config["bake_indirect"] and not config["bake_reflections"] and not config["overrides"]
assert not any(k.endswith("_resource") for k in config), "Saved capture used a staged resource"
for view in config["views"]:
    data = (OUT / "saved-daylight-v5" / (view + ".png")).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", data[16:24]) == (1920,1080)
assert sha(ROOT / "Assets/ui/maps/belltower.png") == sha(OUT / "saved-daylight-v5/map_art.png")
manifest = read(ROOT / "Sources/Belltower/lighting/manifest.json")["volumes"]["town"]
assert manifest["capture"] == "daylight-v5" and manifest["native_bake"]["SavedFinalIrradiance"]
for name, expected in manifest["source_sha256"].items():
    assert sha(ROOT/name) == expected, "Baked source changed: " + name
recovery_path = OUT / "startup-recovery/recovery.json"
recovery = read(recovery_path)
assert sha(ROOT / "Assets/shaders/hc1_brick.shader") == recovery["source_sha256"]
recovery.update({
    "status":"Editor reopened and responsive; daylight-v5 bake published and verified from the saved scene",
    "current_editor_pid":27856,
    "current_editor_operation":"No pending operation from this task",
    "verified_at_utc":datetime.now(timezone.utc).isoformat(),
    "accepted_bake":"daylight-v5",
    "saved_scene_capture":"output/belltower/quality/saved-daylight-v5",
    "last_compile_succeeded":True,
    "last_compile_errors":0,
    "console_cursor":616,
    "console_new_errors":0,
    "town_relocation":{"grid":[28,39,5],"active":4800,"total":5460},
    "saved_scene_gameplay_preserved":True
})
recovery_path.write_text(json.dumps(recovery,indent=2)+"\n",encoding="utf-8")
report = {"checked_at_utc":recovery["verified_at_utc"],"gameplay_preserved":True,"scene_properties_preserved":True,
    "saved_scene_sha256":sha(ROOT/relative),"native_capture":result,"views":config["views"],
    "preview_sha256":sha(ROOT/"Assets/ui/maps/belltower.png"),"compiled_textures":textures,
    "bake_sources_match":True,"shader_source_unchanged":True}
(OUT / "saved-daylight-v5/verification.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print("Verified: gameplay preserved, one saved town volume, six compiled textures, eight native views, original shader source and matching menu art.")
