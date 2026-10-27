## Picking up dropped guns (`PlayerPawn.Using.cs`)
- E first tries the usual trace, then `FindDroppedEquipmentInView`: the dropped gun closest to the middle of your
  view, within `PickupReach` (96) and about 30 degrees of your aim, with a clear line of sight. A gun lying flat on the
  floor is too thin to hit with the trace. `DroppedEquipment` (`Code/Weapons/DroppedWeapon.cs`) centres its collider
  and marker on the world model's bounds (`Center`).
- Dropped guns can't stand up (2026-10-14; the user saw an AK-74M balanced upright on its magazine and stock). The
  collider was a box of the bounds, which rests stably on its narrow bottom, so a gun that fell upright (a bot's
  drop from its hand pose, the Identity-rotation swaps) stayed standing. Guns, pistols and knives now get a
  `HullCollider` (`RidgedProfile`): the box's sides kept for the middle half of the height, then a ridge along the
  bottom and top on a log spiral of 4 facets a slope, so on every facet but the sides the centre of mass hangs past
  the facet's edge (at least 0.45", 0.6" on the wide RPK/Vepr-12/Kastov 762). The ridges sit 0.2 of the half-width
  off the middle, the side picked at random, so a dead-level drop still falls. Grenades, the bomb and the like keep
  the box. Checked offscreen in the engine's physics: the old box stood up in 2-6 of 12 drops per gun, the hull lay on
  a side in all of them for 8 guns. Not yet seen in a match or with a second machine.
- Guns on the floor wear the build they were dropped with (2026-10-25, the user: "guns on the floor dont show camos and
  attachments"). They used to be the bare `EquipmentResource.WorldModel` on the root, with no attachment points.
  - The host sets `DroppedEquipment.Build` (synced) to the dropped gun's `Equipment.HolderBuild` (see Other players'
    guns, below). Bots' are none, or their suppressor (`BuildCode( resource, MuzzlePart )`).
  - Every machine clones the gun's `WorldModelPrefab` under it, not networked (`UpdateModel`), sets `sight`/`muzzle` 0 as
    `Equipment.CreateWorldModel` does, and fits the build with `ApplyBuild`. Only the cash bag and the drone (no prefab)
    keep the bare root model. The collider and `Center` come from that prefab's renderer (`FloorBounds`), so the
    M700 is sized from w_m700 (its .equip's WorldModel is v_m700) and the 1911 by its renderer's child offset.
  - Picking one up still gives the picker's own saved build (or the factory gun from a bot's), as before.
  - Checked offscreen in the editor: an M4 dropped with the saved build got all 7 parts and the camo on all 9 renderers.
    Not yet seen in a match, nor a client's drop over the network.
- Other players' guns, in their hands and holstered, wear their own build (2026-10-25, the user asked after the floor
  guns). Every machine used to fit its own saved loadout to every gun it drew (`ApplyAttachments` in
  `Equipment.CreateWorldModel` and `MountPoint.Mount`), so everyone's guns wore the viewer's parts and camo.
  - `Equipment.FitHolderBuild` (`Equipment.Build.cs`) fits the world model and the holstered copy. The local player's
    own gun (`IsOwnBuild`: its owner's Client is `Client.Local`) still gets this machine's saved loadout. Anyone else's
    gets `HolderBuild`: the build its holder shares for its slot (`Client.SharedPrimaryBuild` / `SharedSecondaryBuild`,
    sent from the gun in their hands each second), if it's for that gun, else the factory gun. Bots (player-pawn ones
    too) and knives share nothing, so they show the factory gun.
  - A shared build can arrive after the gun is drawn (a new spawn's class, a part changed mid-match), so the Client's
    `OnSharedBuildChanged` (a `Change` on both properties) fits that player's world models and holstered copies again
    in place (`RefitHolderBuild`, `EquipmentMountPoints.RefitHolderBuilds`). An empty build refits to the factory gun.
  - Only what's drawn changed. A gun's gameplay effects (recoil, rate, magazine, suppressed sound) still read the
    loadout of the machine that works them out, as before. A first-person spectator still sees the spectated player's
    viewmodel in their own build: its sight alignment (`ManualOffset`) reads the local optic.
  - Checked offscreen in the editor: a fake other player sharing an M4 with only a suppressor had only that fitted
    (the viewer's own M4 has 7 parts and a camo); sharing nothing took it back to the factory gun, and sharing it again
    put the suppressor back. Not yet seen in a match with a second player.

