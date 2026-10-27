## Kastov viewmodel pipeline (CoD MWII rips → HC1 arms)
- Per-weapon config lives in `Tools/kastov_weapons.py`. Run `port_kastov.py`, `kastov_vmdl.py`, `kastov_animgraph.py`
  and `kastov_prefabs.py` in that order, each with
  `--weapon kastov762|kastov74u|vityaz|rpk|bizon|ak105|vepr12|m16|p90|mp7|aug|uzi|fal|famas|m18|mcx|l85a2|hk416|ak12|ak15|ak74m|spear|m16a2|rpk16`
  (default kastov762). The 74u's, Vityaz's, RPK's, Bizon's, AK-105's, Vepr-12's, M16A4's, P90's, MP7A1's, AUG's, Uzi's,
  FAL's, M18's, MCX's, L85A2's, HK416's, AK-12's, AK-15's, AK-74M's, MCX-SPEAR's, M16A2's and RPK-16's materials and sounds come first, from `Tools/ks74u_assets.py` /
  `Tools/vityaz_assets.py` / `Tools/rpk_assets.py` / `Tools/bizon_assets.py` / `Tools/ak105_assets.py` /
  `Tools/vepr12_assets.py` / `Tools/m16_assets.py` / `Tools/p90_assets.py` / `Tools/mp7_assets.py` /
  `Tools/aug_assets.py` / `Tools/uzi_assets.py` / `Tools/fal_assets.py` / `Tools/p320_assets.py` /
  `Tools/mcx_assets.py` / `Tools/l85a2_assets.py` / `Tools/hk416_assets.py` / `Tools/ak12_assets.py` / `Tools/ak15_assets.py` /
  `Tools/ak74m_assets.py` / `Tools/spear_assets.py` / `Tools/m16a2_assets.py` / `Tools/rpk16_assets.py`.
- ADS is the animgraph's float `ironsights_weight`, which `ViewModel` moves over `AimTime` and eases, so it turns
  back from wherever it is. Don't go back to a selector on the `ironsights` enum: a Source 2 selector restarts its
  blend from the full old pose, so spamming aim snapped the gun to the sights or the hip.
- Firing while aimed: every gun's QC `fire` sequence blends `fire.smd` (the hip shot) into `fire_2.smd` (the aimed one)
  by `aim_offset`, the MW base's ADS fraction. The port only had the hip clip, which the graph plays under the ADS
  layer, so a hip clip that rolls the gun rocks the sights. `Weapon.ads_fire` (`"fire_2"`) exports the aimed clip as
  `fire_ads`, and the graph's fire state blends the two by `ironsights_weight` (`fire_aim`, not looping, so the state
  still finishes). The P90, the MP7A1, the AUG, the FAL, the M18, the MCX, the L85A2, the HK416 and the MCX-SPEAR have it so far. The 762's, 74u's, RPK's and
  AK-105's fire clips don't move the gun (the AK-12, AK-15 and AK-74M play the AK-105's), and nor do the M16A4's and the Uzi's, which `Weapon.steady_fire` holds still
  (see M16A4; the M16A2 plays the M16A4's, and the RPK-16 the RPK's), so don't give them `ads_fire`. The Vityaz's, Vepr-12's and Bizon's hip clips roll it (up to 2.6, 8.6 and 0.5
  degrees), so they rock aimed until they get `ads_fire` and a rerun of `port_kastov.py`, `kastov_vmdl.py` and
  `kastov_animgraph.py`.
- The PP-19-01 Vityaz is MWII's Vaznev-9K (mg_iw9_aviktor, addon 3499492742) under its real name. It uses the 74u's
  AK-74M-style folding stock and AK grip, like the real gun (the addon fits the 74u's stock). Its gameplay prefab is
  generated (`kastov_prefabs.gameplay_vityaz`): 750 rpm, the rest of its 9mm values copied from `weapon_mp5.prefab`.
- CoD's additive walk/sprint layers move the gun and arms separately (the game engine's IK keeps hands on the gun), so
  `port_kastov.py` `pin_hands` IKs both wrists back onto `tag_sling` for layered clips; without it the hands let go
  while sprinting. Authored clips (reload etc.) are left as animated.
- All the guns sprint with the M4's sprint (`Weapon.m4_sprint`, `Kastov.m4_sprint`), which the user asked for so the
  guns match. v_m4a1's `Shared_Sprint_Pose_delta` + `Shared_Sprint_delta` weapon_root motion moves the whole gun, and
  the camera bone stays still. CoD's `a_sprint` runs the gun pointing straight ahead with a big sideways sway, and its
  camera-bone motion shakes the view (HC1 adds the viewmodel camera bone to the view).
- All the guns sway like the M4 when the view turns (`Tools/kastov_sway.py`). The user saw them hold dead still, where
  the M4 swings and its hands move with it.
  - The graphs blend 15 single-frame poses (`anims/sway.dmx`, `Kastov.m4_sway`), each a share of one of the M4's
    `Shared_WeaponOffset_Generic_*` weapon_root poses. They're driven by `aim_yaw_inertia` / `aim_pitch_inertia`
    (set by `ViewModel`), with the M4's blend values and springs: halved at the hip, a fifth of that in ADS.
  - Then both arms are solved onto `ik_hand_L` / `ik_hand_R`: bones under tag_sling that hold each hand's pose in
    every clip frame, so the IK changes nothing on the clips' own frames (`IK_TARGETS`, `IK_CHAINS`).
  - The poses move only the gun. Don't sway the arms with additive layers of their own: those move in their own parent
    spaces, so away from idle (reloading, drawing) the left hand came an inch or two off the magazine.
  - Checked offscreen in the engine on 2026-09-28, with a SceneModel on the compiled model and graph: a hard flick
    (`aim_yaw_inertia` -40 for 0.2 s) turns every gun 12.8 degrees at the hip (the M4 13.0) and 2.56 aimed. Both hands
    stay within 0.01" of their grips, and the gun is back at rest 2 s later. Not yet checked in a match.
  - Idle hand jitter (2026-10-13): the native two-bone solver repeatedly moved the AK-105's support hand up to
    0.0067" between frames even with a stationary grip target; the clothing followed it exactly. `hand_ik_weight`
    now bypasses IK only after two seconds without sway, movement, ADS changes, firing, reloads, sprint or lowering.
    Blended clips still need IK: bypassing it during them moved some hands several inches. Held hip and ADS poses
    are stable without it. All 24 graphs compile and pass offscreen idle and action-transition checks; live settled
    AK-105 jumps fell to 0.00003". Reports and reproducible native scripts are in `output/hand-jitter/`.
- After a pipeline run changes many files at once, the editor's file watcher can miss some. Then a new DMX isn't
  registered (an endless on-demand recompile, "file stopped existing"), a vmdl fails with "Unknown bone 'ik_hand_L'",
  the compiled model silently keeps old animations (the P90's and MP7's did), or a new gun's model gets no compiled
  file and loads as an error model, so its first-person gun is invisible (the FAL's did, after an on-demand recompile
  for "Invalid Dependency Information"). Register the gun's DMX (`recompile_asset` each, or
  `Editor.AssetSystem.RegisterFile` them all in one `execute_csharp`), then recompile its vmdl and vanmgrph.
- `Weapon.moved_bones` moves a rig bone the addon left where the real gun has nothing (name -> parent and local offset,
  keeping its own turn). The L85A2's rig had `tag_brass` in the handguard, under the bore, so cases came out of it.
- `Weapon.part_mounts` places a part's model on a rig bone (bone and offset along it), as the MW base draws a
  VElement, for a part whose vertices don't sit where it fits: the HK416's Tarkov stocks.
- `Weapon.part_moves` moves a piece of a part's mesh that stands where the real gun's doesn't (mesh path -> boxes and
  offsets: each connected piece whose bounds lie inside a box moves, `port_kastov.move_pieces`). The M16A4's front sight
  post screws down 0.104 into its base this way (see M16A4).
- A ported gun's viewmodel prefab plays its model's own graph (`AnimationGraph` null; the vmdl names
  `v_<gun>.vanmgrph`). `kastov_prefabs.viewmodel_prefab` copies `vm_m4a1.prefab`, which is pinned to the M4's
  decompiled graph (see s&box 26.10.02), and until 2026-10-09 it kept that pin. So the L85A2, HK416, AK-12, AK-15 and
  AK-74M played the M4's graph, whose clips their models don't have: the gun sat 216 units behind the camera, and the
  user saw no gun in their hands (the AK-12, 2026-10-09). Checked offscreen after the fix: each holds its gun where
  the AK-105 does (the AK-12's `tag_sling` 4.4 ahead of the camera). Not yet seen in a match.
- `weapon_kastov74u.prefab` holds another session's hand-tuned gameplay values and sounds, so the prefab script only
  patches its DeploySound, aim offsets and OpticAimCorrection (`Prefabs.gameplay=None`). The 762's, Vityaz's,
  RPK's, Bizon's, AK-105's, Vepr-12's, M16A4's, P90's, MP7A1's, AUG's, Uzi's, FAL's, M18's, MCX's, L85A2's, HK416's,
  AK-12's, AK-15's, AK-74M's, MCX-SPEAR's, M16A2's and RPK-16's weapon prefabs are fully generated.
- The obj/mtl files in `Assets/Weapons/Kastov74u/models` are unused: `w_kastov74u.vmdl` now comes from the pipeline
  so the gunsmith's attachments mount on the world model.
- The 74u's stocks, pistol grips and magazines are bodygroups (`Weapon.part_choices`, choice 0 = factory part).
  `kastov_prefabs.py` writes one part per other choice to `Assets/gunsmith/kastov74u/` (names and recoil scales in
  `PARTS_74U`). New part materials go in `Tools/ks74u_assets.py` (run with `--materials-only`). Barrels are left out
  because each one moves the left hand, which the ported clips can't do.
- The Vityaz does the same (`PARTS_VITYAZ`, `Assets/gunsmith/vityaz/`): the addon's stocks (the 74u's plus the 74u's
  own, the AKS-74U Folding Stock), grips, 45-round mag and the Long Barrel. Recoil scales are relative to its factory
  polymer folding stock. Its materials, including those shared with the 74u (`vityaz_assets.SHARED_MATERIALS`), are in
  `Tools/vityaz_assets.py`. The addon's other barrel is left out because it moves the left hand.
- The long barrel is a Barrel-slot part with `GunsmithPart.MuzzleShift` (`Part.muzzle_shift`). Muzzle devices
  (`GunsmithMw22Attachment.RefreshMount`) and discharge effects (`WeaponModel.DischargeMuzzle`) move by that shift.
  Its brake is a muzzle_tip choice (`Weapon.tip_choices`): choices are on, the long barrel's tip, then off. Where
  several slots set a bodygroup through `FittedBodygroups` / `Prefabs.part_slot_bodygroups`, the highest choice wins,
  so a muzzle device (2) hides both brakes and the long barrel on its own shows its brake (1).
  - A barrel with a flash hider of its own that's shorter than the factory one (the FAL's 18-inch Barrel) also sets
    `GunsmithPart.TipShift` (`Part.tip_shift`): how much further back than MuzzleShift its bare muzzle is. Devices
    still mount at MuzzleShift, and with no device fitted the discharge effects leave from MuzzleShift plus TipShift
    (`GunsmithAttachmentPoint.DischargeShift`).
  - A barrel's length changes where damage falls off, by the muzzle energy it gives (`Part.falloff`,
    `GunsmithPart.DamageFalloffScale`), but not `MuzzleVelocity`, so bullet drop stays the factory barrel's.
    `GunsmithAttachmentEffects` reads a scale of 0 as 1, since a hotload leaves a new field at 0.
- `default_mesh_groups` is the models' `Model.Parts.DefaultMask`: one bit per bodygroup choice in vmdl order, then
  the base mesh; the default sets each group's choice 0 plus the base (762 = 341, 74u = 605028693,
  Vityaz = 22036489, RPK = 2363477, Bizon = 2129941, AK-105 = 285343829, Vepr-12 = 37814293, M16A4 = 341,
  P90 = 21 (by that rule, not yet read from its compiled model), MP7A1 = 85, AUG = 85, Uzi = 1173, FAL = 174761,
  M18 = 145, MCX = 341 (also by the rule), L85A2 = 85, HK416 = 74069, AK-12 = 135189, AK-15 = 36885 (by the rule), MCX-SPEAR = 341 (by the rule), M16A2 = 5 (by the rule), RPK-16 = 135189 (by the rule) and AK-74M =
  553713749 (read from its compiled models)).
  After changing any bodygroup, re-read it from the compiled model. An empty choice (a rail's or a folded sight's
  "off") still has its bit in the default, but the Parts API gives it mask 0, so setting each group's choice 0 with
  `SetBodyGroup` leaves those bits out (the FAL's 174209). It draws the same gun.

