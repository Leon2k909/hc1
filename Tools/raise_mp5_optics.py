"""Fit the shared raised rail and ADS height to every imported MP5 optic."""

from decimal import Decimal
import json
from pathlib import Path
import uuid


ROOT = Path(__file__).resolve().parents[1]
PREFABS = ROOT / "Assets/attachments/mpapa5/prefabs"
OPTICS = ROOT / "Assets/gunsmith/mpapa5/optics"
TARGET_HEIGHT = Decimal("10.55")


def number(value):
    return format(value.normalize(), "f")


for optic_file in sorted(OPTICS.glob("*.gnsmth")):
    prefab_file = PREFABS / f"{optic_file.stem}.prefab"
    optic = json.loads(optic_file.read_text(encoding="utf-8"))
    prefab = json.loads(prefab_file.read_text(encoding="utf-8"))
    root = prefab["RootObject"]
    mount = next(c for c in root["Components"] if c["__type"].endswith("GunsmithBoneAttachment"))

    has_riser = any(
        any(c["__type"].endswith("GunsmithMp5OpticRiser") for c in child.get("Components", []))
        for child in root["Children"]
    )

    offset = [Decimal(x) for x in mount["WeaponSpaceOffset"].split(",")]
    aim = [Decimal(x) for x in optic["OpticAimOffset"].split(",")]
    delta = TARGET_HEIGHT - offset[2]
    if not delta and has_riser:
        continue
    offset[2] += delta
    aim[2] -= delta
    mount["WeaponSpaceOffset"] = ",".join(map(number, offset))
    optic["OpticAimOffset"] = ",".join(map(number, aim))

    def guid(part):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mp5/optic-riser/{optic_file.stem}/{part}"))

    if not has_riser:
        root["Children"].append(
        {
            "__guid": guid("object"),
            "Flags": 0,
            "Name": "MP5 raised optic rail",
            "Position": "0,0,0",
            "Rotation": "0,0,0,1",
            "Scale": "1,1,1",
            "Enabled": True,
            "NetworkMode": 1,
            "Components": [
                {
                    "__type": "Sandbox.ModelRenderer",
                    "__guid": guid("renderer"),
                    "__enabled": True,
                    "Model": "attachments/mpapa5/optic_riser/optic_riser.vmdl",
                    "Tint": "1,1,1,1",
                },
                {
                    "__type": "Facepunch.Gunsmith.GunsmithMp5OpticRiser",
                    "__guid": guid("follower"),
                    "__enabled": True,
                },
            ],
            "Children": [],
        }
        )

    prefab_file.write_text(json.dumps(prefab, indent=2) + "\n", encoding="utf-8")
    optic_file.write_text(json.dumps(optic, indent=2) + "\n", encoding="utf-8")
    print(optic_file.stem)
