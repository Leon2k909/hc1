"""Compare the staged Railhead builds with Assets: which files the unchanged generator reproduces (baseline), and which
the candidate changes. Writes compare.json, and with --publish the publish.json for Sources/Railhead/editor/
import-staged.cs.txt (only files whose baseline matches Assets, so nothing else's drift is published)."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSETS = ROOT / "Assets"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def files(stage):
    return sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file())


baseline, candidate = HERE / "baseline", HERE / "candidate"
report = {}
for name in sorted(set(files(baseline)) | set(files(candidate))):
    entry = {"assets": sha(ASSETS / name), "baseline": sha(baseline / name), "candidate": sha(candidate / name)}
    entry["baseline_matches"] = entry["baseline"] == entry["assets"]
    entry["candidate_changes"] = entry["candidate"] is not None and entry["candidate"] != entry["assets"]
    report[name] = entry
(HERE / "compare.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
drift = [n for n, e in report.items() if e["baseline"] and not e["baseline_matches"]]
changed = [n for n, e in report.items() if e["candidate_changes"]]
print(f"{len(report)} files; baseline differs from Assets in {len(drift)}; candidate changes {len(changed)}")
for n in drift:
    print("  drift:", n)
for n in changed:
    print("  change:", n, "(baseline matches)" if report[n]["baseline_matches"] else "(BASELINE DRIFT)")
if "--publish" in sys.argv:
    publish = {}
    for n in changed:
        e = report[n]
        if e["assets"] is not None and not e["baseline_matches"]:
            raise SystemExit(f"refusing: {n} drifts from Assets in the baseline")
        publish[n] = {"source": (candidate / n).relative_to(ROOT).as_posix(), "before": e["assets"], "after": e["candidate"]}
    (HERE / "publish.json").write_text(json.dumps({"files": publish}, indent=1), encoding="utf-8")
    print(f"publish.json: {len(publish)} files")
