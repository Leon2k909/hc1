"""Record the verified scope without changing unrelated documentation or line endings."""
from pathlib import Path
import json

project = Path(__file__).resolve().parents[2]
notes = project / "CLAUDE.md"
raw = notes.read_bytes()
old = (
    "- Validation: offline build and the editor's code compiler both passed with zero errors. Live throw/hit/pickup checks are\n"
    "  pending: the editor froze while entering Lowtide play mode before any throw was performed."
)
new = (
    "- Validation: offline build and the editor's code compiler passed with zero errors. Live host checks on Railhead passed\n"
    "  for both knives: frozen-player rejection, holster cancellation, duplicate rejection, visible flight, one 100-damage hit,\n"
    "  weapon switching, recovery and a normal melee swing after recovery. Screenshots and results are in `output/knife-throw/`.\n"
    "  A runtime Attack2 injection through WeaponInputAction also passed with only the knife enabled: empty hands after release,\n"
    "  impact and recovery. The native Bridge's frame input helper did not reach fixed-step weapon input, so that check used\n"
    "  Input.SetAction plus the actual fixed-step handler. A separate remote-client session remains untested.\n"
    "- Releasing the last held knife calls PlayerPawn.Holster directly; PlayerInventory.HolsterCurrent reaches a null Deploy call."
)
for ending in ("\r\n", "\n"):
    expected = old.replace("\n", ending).encode("utf-8")
    if expected in raw:
        notes.write_bytes(raw.replace(expected, new.replace("\n", ending).encode("utf-8"), 1))
        break
else:
    raise RuntimeError("Expected validation note was not found; documentation left unchanged.")

result = json.loads((project / "output/knife-throw/run_csharp.json").read_text(encoding="utf-8"))
(project / "output/knife-throw/live-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("Recorded live knife validation and preserved document line endings.")
