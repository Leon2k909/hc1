"""Check the incendiary grenade from its files: python verify_incendiary.py <project root> <work dir>

Its parts must face outward, it must stay close to the old model's bounds in each body group, the vmdl must keep the old body groups
in order, every texture the vmat names must exist, and the grenade's prefabs and .equip must not yet point at it.
Compiling it and seeing it in s&box is not covered by this. On the smoke grenade v2's checks: see adapt.py.
"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapt  # noqa: E402

adapt.run(
    "verify_smoke.py",
    [
        ('"Weapons/Throwable/M18_Smoke_Grenade/smoke_grenade_v2"', f'"{adapt.FOLDER}"'),
        ('f"smoke_grenade_{group}_lod{lod}.obj"', 'f"incendiary_grenade_{group}_lod{lod}.obj"'),
        ('f"smoke_grenade_{group}_lod0.obj"), "smoke_grenade"]', 'f"incendiary_grenade_{group}_lod0.obj"), "incendiary_grenade"]'),
        ('"smoke_grenade.vmdl"', '"incendiary_grenade.vmdl"'),
        ('"Assets/Weapons/Throwable/M18_Smoke_Grenade/smoke_grenade.prefab"', '"Assets/Weapons/Throwable/Molotov_Cocktail/molotov_grenade.prefab"'),
        ('"Assets/Weapons/Throwable/M18_Smoke_Grenade/vm_smoke_grenade.prefab"', '"Assets/Weapons/Throwable/Molotov_Cocktail/vm_molotov_grenade.prefab"'),
        ('"Assets/Weapons/Throwable/M18_Smoke_Grenade/wm_smoke_grenade.prefab"', '"Assets/Weapons/Throwable/Molotov_Cocktail/wm_molotov_grenade.prefab"'),
        ('"Assets/Weapons/Throwable/M18_Smoke_Grenade/smoke_grenade.equip"', '"Assets/Weapons/Throwable/Molotov_Cocktail/molotov_grenade.equip"'),
        ('("smoke_grenade.prefab", "vm_smoke_grenade.prefab", "wm_smoke_grenade.prefab", "smoke_grenade.equip")', '("molotov_grenade.prefab", "vm_molotov_grenade.prefab", "wm_molotov_grenade.prefab", "molotov_grenade.equip")'),
        ('"Weapons/Throwable/M18_Smoke_Grenade", name', '"Weapons/Throwable/Molotov_Cocktail", name'),
        ('check("smoke_grenade_v2" not in text', 'check("incendiary_grenade_v2" not in text'),
    ],
    os.path.abspath(__file__),
)
