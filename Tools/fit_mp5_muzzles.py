"""Seat shared MW19 muzzle devices against the existing MP5 muzzle."""

from __future__ import annotations

import json
from pathlib import Path

from audit_mw19_mp5 import active_choices


PREFABS = Path(__file__).resolve().parents[1] / "Assets/attachments/mpapa5/prefabs"
MOUNT = "12,0,8.13"


def main() -> None:
    keys = next(row[1:] for row in active_choices() if row[0] == "att_muzzle")
    for key in keys:
        path = PREFABS / f"{key}.prefab"
        data = json.loads(path.read_text(encoding="utf-8"))
        mount = next(c for c in data["RootObject"]["Components"]
                     if c["__type"] == "Facepunch.Gunsmith.GunsmithBoneAttachment")
        mount["WeaponSpaceOffset"] = MOUNT
        mount["FitMp5MuzzleToBarrel"] = True
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Fitted {len(keys)} MP5 muzzle devices")


if __name__ == "__main__":
    main()
