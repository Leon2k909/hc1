"""Audit saved paving sources after native material promotion and viewport review."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

production = read(OUT / "paving-relief-production-manifest.json")
candidate = read(OUT / "paving-relief-manifest.json")
native = read(OUT / "paving-relief-production-verification.json")
for relative, expected in production["protected"].items():
    assert digest(ROOT / relative) == expected, relative
for manifest in (production, candidate):
    for relative, change in manifest["changes"].items():
        assert digest(ROOT / "Assets" / relative) == change["after"], relative
assert not native["IsError"] and not native["HasUnsavedChanges"] and not native["IsPlaying"]
assert len(native["slots"]) == 3 and all(not x["hasOverride"] for x in native["slots"])
assert len(native["textures"]) == 4 and all(x["width"] == 2048 and x["height"] == 2048 for x in native["textures"])
assert len(native["captures"]) == 4
for capture in native["captures"]:
    assert (OUT / capture["name"]).stat().st_size > 100000
assert (ROOT / "Sources/Lowtide/paving/hc1_lowtide_paving_relief.shader").read_bytes() == (ROOT / "Assets/shaders/hc1_lowtide_paving_relief.shader").read_bytes()

pending = read(OUT / "paving-relief-pending.json")
pending.update({
    "status": "installed in production, compiled, loaded and visually verified",
    "production_verification": "paving-relief-production-verification.json",
    "do_not_reapply": True,
    "next": "Paving pass complete. Do not reimport or replay the promotion script. Continue the broader Lowtide art pass and controlled gameplay performance review.",
    "preserved": "Original granite colour, roughness and world scale; all model sources, collision and scene data. Three original material slots now load the new production material without overrides.",
    "engine": "Native sbox connection recovered on PID 16792. Production material compile returned true; its immediate binding check ran before asynchronous resource reload completed. A later read confirmed all four 2048px bindings. The separate production verifier checked all 54 protected sources and captured four real viewport views. No errors since console cursor 4811 through 4843. Camera restored, scene clean, Railhead tab restored.",
    "visual_review": "All four production captures reviewed: coherent recessed joints and rough stone edges at player height on both sides, no atlas seams or shallow-angle stretching observed. Scene-wide art remains below the intended AAA target.",
})
write(OUT / "paving-relief-pending.json", pending)
status_path = ROOT / "Sources/Lowtide/paving/relief-status.json"
status = read(status_path)
status["status"] = pending["status"]
status["next"] = pending["next"]
status["production_verification"] = "output/lowtide/quality-pass/paving-relief-production-verification.json"
status["validated"].append("Production material saved and loaded in all three original slots; four production viewport views reviewed; 54 protected sources unchanged")
write(status_path, status)
print(json.dumps({"production": "verified", "protected": len(production["protected"]), "new_files": len(candidate["changes"]), "views_reviewed": 4}, indent=2))
