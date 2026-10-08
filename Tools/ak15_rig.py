"""The AK-15's magazine on the AK-12's rig (decompiled/ak12/rig/ak15_mag.smd), and its HUD icon.

The AK-15 is the AK-12 in 7.62x39 (Kalashnikov's 6P71: the same receiver, furniture, sights and brake on a 7.62 barrel),
so it's Tarkov's AK-12 as Tools/ak12_rig.py puts it on the AK-105's rig, with a 7.62 magazine. The magazine is Tarkov's
AK-103 polymer 30-rounder (ARC9 EFT Assault Rifles, Workshop 2962829818, decompiled to decompiled/ak15), and the rounds
in its lips are the pack's c_ak100 7.62 bodygroup (762.smd). c_ak100 and c_ak12 share their skeleton and clips (both
include ak_anims.mdl), so the rounds pose on the AK-12's bones, and the magazine goes where the pack's AK-103 puts it on
mod_magazine: Pos (0, -0.05, -0.25), where the AK-12's 5.45 magazine is at (0, 0, -0.2).

The icon (Assets/ui/weapons/guns/ak15_01.png) is the AK-12's with this magazine.

Run (after ak12_rig.py and the decompile, before port_kastov.py --weapon ak15): python Tools/ak15_rig.py
"""
from __future__ import annotations

from ak12_rig import (ROUND_SKIP, SMDS, Rig, add_mesh, assemble, attachment_pose, icon, place_model,
                      weapon_bones)
from kastov_weapons import ASSETS, DECOMPILED

SOURCE = DECOMPILED / "ak15"
MAGAZINE = "mag_ak_izhmash_ak103_std_762x39_30_LOD0_0.smd"
ROUNDS = "762.smd"
MAG_POS = (0, -0.05, -0.25)  # the pack's AK-103 magazine slot
ICON = ASSETS / "ui" / "weapons" / "guns" / "ak15_01.png"


def main() -> None:
    pieces = assemble()
    bones = weapon_bones()
    del pieces["magazine"], pieces["rounds"]
    place_model(pieces, "magazine", attachment_pose(bones["mod_magazine"], MAG_POS, (0, 0, 0)), SOURCE / MAGAZINE)
    add_mesh(pieces, bones, "rounds", SOURCE / ROUNDS, skip=ROUND_SKIP)
    rig = Rig()
    rig.write("ak15_mag", rig.magazine(pieces))
    smds = {name: [tri for piece in names for tri in rig.triangles(pieces, piece)] for name, names in SMDS.items()}
    smds["ak15_mag"] = rig.magazine(pieces, spare=False)
    icon(smds, ICON)


if __name__ == "__main__":
    main()
