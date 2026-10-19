"""Keep only the intentional editor change while avoiding its whole-scene reserialization.

Safe because Lowtide scene had a clean worktree before this edit. Verify all
pre-existing keys still match before writing the sparse original representation.
"""
from pathlib import Path
import json
import subprocess

root = Path(__file__).resolve().parents[3]
scene_rel = "Assets/scenes/maps/Lowtide/lowtide.scene"
path = root / scene_rel
original_text = subprocess.check_output(["git", "show", "HEAD:" + scene_rel], cwd=root).decode("utf-8")
original = json.loads(original_text)
saved = json.loads(path.read_text(encoding="utf-8"))


def fleet_south(data):
    group = next(x for x in data["GameObjects"] if x.get("Name") == "Reflection Probes")
    target = next(x for x in group["Children"] if x.get("Name") == "Probe Fleet South")
    return next(c for c in target["Components"] if c["__type"] == "Sandbox.EnvmapProbe")


old = fleet_south(original)
new = fleet_south(saved)
assert old["Bounds"]["Mins"] == "-1150,-240,-90"
assert old["Feathering"] == .04
assert new["Bounds"]["Mins"] == "-1800,-240,-90"
assert new["Feathering"] == .30


def changed_values(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        for key in before:
            if key in after:
                yield from changed_values(before[key], after[key], f"{path}.{key}")
    elif isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            yield f"{path} length: {len(before)} => {len(after)}"
        for i, (a, b) in enumerate(zip(before, after)):
            yield from changed_values(a, b, f"{path}[{i}]")
    elif before != after:
        # The editor serializes asset strings as JSON with a resource identifier.
        if isinstance(before, str) and isinstance(after, dict) and after.get("Path") == before:
            return
        yield f"{path}: {str(before)[:80]} => {str(after)[:80]}"


deltas = list(changed_values(original, saved))
print(f"Editor reserialization changed {len(deltas)} pre-existing values or list sizes")
expected = (".Rotation:", ".Tags:", ".LightColor:", ".Position:", ".Center:",
            ".Bounds.Mins:", ".Feathering:", ".Description:")
unexpected = [change for change in deltas if not any(token in change for token in expected)]
assert not unexpected, "Unexpected scene changes: " + "\n".join(unexpected)
for change in deltas:
    if any(token in change for token in (".Bounds.Mins:", ".Feathering:", ".Description:")):
        print(change)

old["Bounds"]["Mins"] = new["Bounds"]["Mins"]
old["Feathering"] = new["Feathering"]
start = original_text.index('"Name": "Probe Fleet South"')
end = original_text.index('"Name": "Probe Bridge"', start)
block = original_text[start:end]
assert block.count('"Mins": "-1150,-240,-90"') == 1
assert block.count('"Feathering": 0.04') == 1
new_block = (block.replace('"Mins": "-1150,-240,-90"', '"Mins": "-1800,-240,-90"')
                 .replace('"Feathering": 0.04', '"Feathering": 0.3'))
new_text = original_text[:start] + new_block + original_text[end:]
# Minimal patch: keep original scene bytes/format and only change the two
# fields explicitly modified through the editor.
path.write_bytes(new_text.encode("utf-8"))
print("Saved sparse scene with the live editor probe settings and unchanged original structure")
