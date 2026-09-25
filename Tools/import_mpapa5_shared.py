"""Add MW19 MP5-compatible shared optics and muzzle devices to Gunsmith.

The source models are already compiled under Assets/attachments/mw2022/models:
these were decompiled from the same Modern Wokefare Base workshop package.
This script only creates MP5-specific resource and mount prefabs; it never
changes the MP5 weapon model or adds a second weapon.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from audit_mw19_mp5 import active_choices, attachment_source


ASSETS = Path(__file__).resolve().parents[1] / "Assets"
SHARED = ASSETS / "attachments/mw2022/models"
RESOURCE_ROOT = ASSETS / "gunsmith/mpapa5"
PREFABS = ASSETS / "attachments/mpapa5/prefabs"
M4_RESOURCES = ASSETS / "gunsmith/m4a1/mw2022"
EQUIPMENT = "weapons/mp5/mp5.equip"
NAMESPACE = uuid.UUID("cc96a3bb-f695-4494-a580-a9a13b2f1c05")


def stable_guid(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def import_choice(key: str, category: str) -> bool:
    model = SHARED / key / (key + ".vmdl")
    if not model.is_file():
        print(f"missing shared model: {key}")
        return False
    folder = "optics" if category == "Optic" else "muzzles"
    resource = RESOURCE_ROOT / folder / (key + ".gnsmth")
    prefab = PREFABS / (key + ".prefab")
    if resource.exists() and prefab.exists():
        return True

    old = M4_RESOURCES / (key + ".gnsmth")
    old_data = json.loads(old.read_text(encoding="utf-8")) if old.is_file() else {}
    _, workshop_name, _ = attachment_source(key)
    name = old_data.get("Name") or workshop_name or key.replace("att_vm_", "").replace("_", " ").title()
    position = "0.7,0,9.7" if category == "Optic" else "12,0,8.13"
    mount_type = "Facepunch.Gunsmith.GunsmithBoneAttachment"
    mount = {
        "__type": mount_type,
        "__guid": stable_guid(key + ":mount"),
        "__enabled": True,
        "BoneName": "weapon_root",
        "UseWeaponOrigin": True,
        "WeaponSpaceOffset": position,
        "WeaponSpaceScale": 1,
        "MountAtBone": False,
        "BoneOffset": "0,0,0",
        "BoneAngles": "0,0,0",
        "ModelScaleMultiplier": "1,1,1",
    }
    prefab_data = {
        "RootObject": {
            "__guid": stable_guid(key + ":object"),
            "Flags": 0,
            "Name": "MP5 " + name,
            "Position": "0,0,0",
            "Rotation": "0,0,0,1",
            "Scale": "1,1,1",
            "Enabled": True,
            "NetworkMode": 1,
            "Components": [
                {
                    "__type": "Sandbox.ModelRenderer",
                    "__guid": stable_guid(key + ":mesh"),
                    "__enabled": True,
                    "Model": f"attachments/mw2022/models/{key}/{key}.vmdl",
                    "Tint": "1,1,1,1",
                },
                mount,
            ],
            "Children": [],
        },
        "ResourceVersion": 2,
        "__version": 2,
    }
    part_data = {
        "Name": name,
        "Category": category,
        "MainPrefab": {"_type": "gameobject", "prefab": f"attachments/mpapa5/prefabs/{key}.prefab"},
        "EligibleEquipment": [EQUIPMENT],
        "RequiredLevel": 0,
        "Description": f"MW2019 {category.lower()} fitted for the existing MP5.",
        "__references": [],
        "__version": 0,
    }
    if category == "Optic":
        part_data.update({
            "ModifyBodygroups": True,
            "Bodygroups": {"top_rail": 3, "top_rail_mount": 1},
            "OpticMagnification": old_data.get("OpticMagnification", 1),
        })
    if category == "Muzzle" and old_data.get("IsSuppressor"):
        part_data["IsSuppressor"] = True
    if not prefab.exists():
        write_json(prefab, prefab_data)
    if not resource.exists():
        write_json(resource, part_data)
    return True


def main() -> None:
    category_rows = {row[0]: row[1:] for row in active_choices()}
    imported = 0
    for original, category in (("att_sight", "Optic"), ("att_muzzle", "Muzzle")):
        for key in category_rows[original]:
            imported += import_choice(key, category)
    print(f"Available MP5 shared choices: {imported}/35")


if __name__ == "__main__":
    main()
