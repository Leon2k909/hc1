## Equipment skins (`EquipmentSkins`, the gear picker, 2026-10-30)
- The user asked for a skins option for equipment, as other shooters have, after liking both the old frag grenade and its
  v2 ("i like both"). So both stay: the frag has two skins, Standard (the cloud model) and K-31 (`he_grenade_v2`).
  Standard is first, so it's the default. The smoke grenade has the same pair for the same reason: Standard and K-44
  (`smoke_grenade_v2`), and the flashbang too: Standard and K-47 (`flashbang_v2`, "i like both of those, they should be
  skins"). The incendiary grenade has Standard and K-52 (`incendiary_grenade_v2`, "i like both do skins"), plus whatever
  `thermite_grenade_v2` adds. Gear in either slot gets its rows, Tactical as well as Lethal.
- `EquipmentSkins.All` is the list. A skin is another model in place of the stock one, on the same origin with the same body
  groups. To add one, add a line and a 256 px picture in `ui/weapons/grenades/`: no prefab changes.
- Where to pick: the loadout's LETHAL picker, in rows under the item, as builds sit under a gun. Picking a skin also puts the
  item in the class, and the picker stays open to compare. It's per item, not per class: cookie
  `hc1.equipment_skin.<resource name>`.
- Everyone sees it. Each client sends its picks to the host (`Client.EquipmentSkinPicks`, as `OperatorPicks` goes), and each
  machine dresses its own copies with `EquipmentSkins.Apply`:
  - in first person and third person (`Equipment.CreateViewModel`, `CreateWorldModel`);
  - holstered on the body (`MountPoint.Mount`);
  - thrown (`Throwable.SpawnProjectile` sets `BaseGrenade.SkinId`, a sync property);
  - dropped (`DroppedEquipment.SkinId`).
- `Apply` swaps any `ModelRenderer` drawing the skin's `StockModel`, by name, which leaves a viewmodel's arms alone. It keeps
  the renderer's body groups, and leaves a model that hasn't compiled as stock rather than showing an error model.
- `Apply` must run before `ApplyAttachments` in `Equipment.CreateViewModel`. The attachments' camo pass pins every material slot to the model's own
  material, and those overrides outlast a model swap: with the old order, every skin drew the stock texture on its own mesh in first person, and
  all of them looked the same (found and fixed 2026-10-31). `Sources/Weapons/thermite_grenade_v2/skin_order_check.cs.txt` shows it without play mode.
- Not covered: Theater replays and bots draw the stock model. The HUD's gear icon is a white silhouette shared by both.
- The "Skins" heading is in every language table. Skin names aren't translated, like camos.
- Made without the editor (2026-10-30). Compiled with dotnet against the installed s&box with 0 errors, but never run: not
  seen in the menu or a match, and `he_grenade.vmdl` hasn't been compiled, so picking K-31 shows the stock model until it
  has. To check: the picker's layout and pictures, K-31 in the hand with the fingers on the lever, on the body, thrown,
  dropped, and another player seeing it.
