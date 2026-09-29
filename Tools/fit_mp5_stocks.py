"""Mount the MW19 stocks on the existing MP5 where MW19's own MP5 mounts them.

Every stock mesh is authored around MW19's tag_stock_attach (the back of its stock adapter), so each stock goes at
that point carried onto the s&box MP5 by RECEIVER_FIT, whole: the front of each stock wraps the MP5's end cap like
it does on MW19's receiver.

RECEIVER_FIT maps MW19's v_mpapa5 gun space (j_gun) onto the MP5's weapon space. It is the best side-on silhouette
match of MW19's receiver and stock adapter (attachment_vm_sm_mpapa5_receiver.smd, _stock_adapter.smd) against the
s&box v_mp5 with its own stock bone left out (Source2Viewer export): scale 0.955, 84% overlap, with the pistol grip,
trigger guard, magazine well and end cap lined up. Only the MP5's own stock (bone "stock") is hidden, so its end
cap stays.
"""

from __future__ import annotations

import json
from pathlib import Path

import part_names


ASSETS = Path(__file__).resolve().parents[1] / "Assets"
ATTACHMENTS = ASSETS / "attachments/mpapa5"
PREFABS = ATTACHMENTS / "prefabs"
# MW19 gun space -> MP5 weapon space: scale, then offset.
RECEIVER_FIT = (0.955, (-4.275, 0.0, 7.075))
# MW19 v_mpapa5's tag_stock_attach in gun space.
MW19_STOCK_ATTACH = (-1.769, 0.0, 1.19)
# Stock prefab -> its ModelDoc, which shows the whole stock mesh.
STOCKS = {
    "att_vm_stock_heavy01": "shared/att_vm_stock_heavy01/att_vm_stock_heavy01.vmdl",
    "att_vm_stock_heavy02": "shared/att_vm_stock_heavy02/att_vm_stock_heavy02.vmdl",
    "att_vm_stock_light01": "shared/att_vm_stock_light01/att_vm_stock_light01.vmdl",
    "att_vm_stock_medium01": "shared/att_vm_stock_medium01/att_vm_stock_medium01.vmdl",
    "att_vm_stock_no": "shared/att_vm_stock_no/att_vm_stock_no.vmdl",
    "stock_classic_full": "stocks/stock_classic_full/stock_classic_full.vmdl",
    "stock_collapsible": "stocks/stock_collapsible/stock_collapsible.vmdl",
    "stock_standard": "stocks/stock_standard/stock_standard.vmdl",
}


def mount() -> tuple[str, float]:
    scale, offset = RECEIVER_FIT
    position = [round(scale * value + shift, 3) for value, shift in zip(MW19_STOCK_ATTACH, offset)]
    return ",".join(f"{value:g}" for value in position), scale


def main() -> None:
    position, scale = mount()
    for prefab_name, modeldoc in STOCKS.items():
        prefab = PREFABS / f"{prefab_name}.prefab"
        data = json.loads(prefab.read_text(encoding="utf-8"))
        for component in data["RootObject"]["Components"]:
            if component["__type"] == "Facepunch.Gunsmith.GunsmithBoneAttachment":
                component["WeaponSpaceOffset"] = position
                component["WeaponSpaceScale"] = scale
        prefab.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # The whole stock, not the clipped *_fitted.obj an earlier fit used.
        model = ATTACHMENTS / modeldoc
        model.write_text(model.read_text(encoding="utf-8").replace("_fitted.obj", ".obj"), encoding="utf-8")
    print(f"{len(STOCKS)} stocks at {position}, scale {scale:g}")

    # The MP5-specific bare receiver is a distinct Workshop choice.
    collapsible = ASSETS / "gunsmith/mpapa5/stocks/stock_collapsible.gnsmth"
    part = json.loads(collapsible.read_text(encoding="utf-8"))
    part["Name"] = part_names.name("stock_collapsible")
    part["Description"] = "MP5 collapsible configuration with the factory stock removed."
    collapsible.write_text(json.dumps(part, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
