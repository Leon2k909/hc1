"""Audit the native camera preset without opening or changing an editor scene."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "Assets/prefabs/player/cameras/default_player_camera.prefab",
    "Assets/scenes/theater_playback.scene",
)
LOOK_TYPES = {
    "Sandbox.Tonemapping", "Sandbox.Bloom", "Sandbox.Sharpen",
    "Sandbox.AmbientOcclusion", "Sandbox.ColorAdjustments", "Sandbox.Vignette",
}


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def without_look(value):
    if isinstance(value, dict):
        return {key: without_look(child) for key, child in value.items()}
    if isinstance(value, list):
        return [without_look(child) for child in value
                if not isinstance(child, dict) or child.get("__type") not in LOOK_TYPES]
    return value


def profile(value):
    return {obj["__type"]: {key: child for key, child in obj.items()
                            if not key.startswith("OnComponent")
                            and key not in ("__guid", "Flags")}
            for obj in walk(value) if obj.get("__type") in LOOK_TYPES}


report = {"files": [], "native_runtime_verified": False}
profiles = []
for filename in FILES:
    path = ROOT / filename
    current = json.loads(path.read_text(encoding="utf-8-sig"))
    previous = json.loads(subprocess.check_output(
        ["git", "show", f"HEAD:{filename}"], cwd=ROOT, text=True, encoding="utf-8"))
    # These two input files were clean before this pass. Every component identity,
    # camera transform, FOV, visibility mask and gameplay/UI setting outside the look must match.
    assert without_look(current) == without_look(previous), f"Unrelated asset change: {filename}"
    old_ids = {obj["__guid"] for obj in walk(previous) if "__guid" in obj}
    new_ids = [obj["__guid"] for obj in walk(current) if "__guid" in obj]
    assert len(new_ids) == len(set(new_ids)), f"Duplicate component identity: {filename}"
    assert old_ids <= set(new_ids), f"Existing component identity lost: {filename}"
    before, after = profile(previous), profile(current)
    profiles.append(after)
    report["files"].append({
        "path": filename,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "unrelated_content_preserved": True,
        "existing_component_ids_preserved": True,
        "changes": {name: {"before": before.get(name), "after": effect}
                    for name, effect in after.items() if before.get(name) != effect},
    })

assert profiles[0] == profiles[1], "Player and replay camera profiles differ"
report["player_and_replay_profiles_match"] = True
report["notes"] = [
    "Native map volumes still supply local exposure, grading, atmosphere, AO and bloom.",
    "See visual-review.json for the native Lowtide camera comparison. Full-match temporal behaviour and GPU frame time remain unmeasured.",
]
(Path(__file__).parent / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("PASS: valid JSON; unique and retained component IDs; unchanged camera/gameplay/UI content; matching player/replay profiles.")
print("Native camera comparison: see visual-review.json. Full-match temporal and performance checks remain unmeasured.")
