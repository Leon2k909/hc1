"""Verify saved native static flags, scope and moving-shadow rendering evidence."""
import copy
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
FOLDER = Path(__file__).parent
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_static as static

before = json.loads((FOLDER / "static-shadow-before.scene").read_text())
saved = json.loads((ROOT / "Assets/scenes/maps/Lowtide/lowtide.scene").read_text())
expected = copy.deepcopy(before)
static.apply_scene(expected)
assert saved == expected, "Saved scene may only change the 33 reviewed Flags fields"
static.apply_scene(expected)
assert expected == saved, "Static flags must be idempotent"
assert len(list(static.targets(saved))) == 33
native = json.loads((FOLDER / "static-shadow-engine-checks.json").read_text())
assert sum(m["IsStatic"] and m["nativeStatic"] for m in native["models"]) == 9
assert all(l["IsStatic"] for l in native["lights"])
assert native["points"] == 6 and native["spots"] == 18 and native["volumes"] == 2
assert native["userScenePreserved"] and not native["HasUnsavedChanges"]
dynamic = json.loads((FOLDER / "static-dynamic-shadows.json").read_text())
assert dynamic["userScenePreserved"] and dynamic["userEditorPreserved"]
a, b = dynamic["evidence"][:2]
assert a["cacheId"] != 0 and a["cacheId"] == b["cacheId"]
assert all(e["staticFloor"] and not e["dynamicCaster"] for e in dynamic["evidence"])
masks = []
for pos in ("a", "b"):
    clear = np.asarray(Image.open(FOLDER / f"static-dynamic-{pos}-clear.png").convert("RGB"), dtype=float)
    shadow = np.asarray(Image.open(FOLDER / f"static-dynamic-{pos}-shadow.png").convert("RGB"), dtype=float)
    mask = np.maximum(0, clear - shadow).mean(2) > 12
    assert mask.sum() > 1000, "Expected an observable cast shadow"
    masks.append(mask)
assert not np.any(masks[0] & masks[1]), "Previous shadow must disappear after the caster moves"
diagnostics = (FOLDER / "live-static-shadow-saved-diagnostics.txt").read_text()
assert diagnostics.count("modelError=False; materialErrors=0") == 15
report = {
    "status": "PASS", "changedObjectFlags": 33, "staticWorldMeshes": 9,
    "staticLocalLamps": 24, "allOtherSceneDataUnchanged": True,
    "movingCasterShadowUpdates": True, "staticCacheReused": True,
    "movingShadowPixelCounts": [int(m.sum()) for m in masks],
    "userMatchPreserved": True, "measuredGameFpsImprovement": None,
}
(FOLDER / "static-shadow-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print("PASS: 33 Flags-only changes; native static casters; cache reused; moving shadows update; clean saved-scene render")
