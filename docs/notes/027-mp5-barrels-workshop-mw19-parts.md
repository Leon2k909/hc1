## MP5 barrels (Workshop MW19 parts)
- The Rail Handguard (`gunsmith/mpapa5/underbarrel/rail_grip.gnsmth`) only swaps the handguard. It hides
  `v_mp5_b` (handguard + barrel + both sights) and shows `native_front.vmdl`, a copy of `v_mp5_b` without the
  handguard, so the MP5 keeps its own sights and muzzle.
- `Tools/fit_mp5_barrels.py <mp5 GLB>` generates all four parts: the native pieces, the vmdls (no bodygroups;
  the prefabs' ModelRenderer BodyGroups default to all bits set), prefabs and `HiddenWeaponMaterials`. It takes
  the stock v_mp5 mesh from a Source2Viewer GLB (`D:/tmp/hc1-mw22-tools/vrf/mp5-native.glb`). Every piece follows
  its own bone through `GunsmithMp5NativeReceiver.BoneName` (bolt, cocking lever, magazine latch). All parts share
  one transform: offset `2.652,-0.248,8.128`, scale 1.122.
- The integral and railed suppressor barrels keep the stock barrel and front sight (`native_front`), the same as the
  Rail Handguard.
  Their Workshop front sights are left out because they're taller than the stock sight, which would put the iron
  sights out of line.
- The Short Barrel (an MP5K-style shroud with no barrel of its own) hides v_mp5_a too. `native_receiver` cuts the
  cocking tube at the shroud's sight notch, moves the stock front sight back into that notch (same post height,
  so the iron sights still line up), and moves the stock muzzle back to stick out 1" past the shroud. Not yet checked
  in-game when aiming.
- Muzzle devices sit against the barrel part's front face. The shifts in `GunsmithBoneAttachment.RefreshMount`
  are printed by the script.

