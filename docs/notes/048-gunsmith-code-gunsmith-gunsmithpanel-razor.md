## Gunsmith (`Code/Gunsmith/GunsmithPanel.razor`)
- Laid out like the main menu, after the user's CoD-style mockup: MainMenuRoot's header, a breadcrumb bar, then
  LOADOUT (left), the gun in `.gs-stage` (centre) and BUILD / CUSTOMIZE (right). The header's styles are copied into
  GunsmithPanel.razor.scss under the same `gnav-*` names, so change both. Its nav tabs load the menu on that page
  (`GameUtils.ReturnToMainMenu( route )`, `MainMenuRoot.PendingRoute`). Over a match (the "GunsmithStudio" prefab) the
  tabs, party and settings are hidden.
- `GunsmithController.FrameWeapon` fits the gun (the Reticle tab: its optic) into `GunsmithPanel.StageRect` by
  widening the FOV and sliding the camera. Only drags and scrolls over the stage turn and zoom it.
- The stage gun is the weapon's viewmodel prefab (`GunsmithSystem.LoadEquipment`). `HidePreviewArms` swaps every
  material named like a hand or an arm (`IsPreviewArmMaterial`: sleeve, glove, `_hand`, `_arm`, ...) for toolsnodraw,
  which a model draws as its yellow NODRAW texture instead of hiding it. Names with "handguard" or "handle" are left
  alone: the M16A4's `m16_carry_handle.vmat` matched `_hand`, so its carry handle showed yellow (fixed 2026-09-28).
  Name new gun materials so they don't match.
- The 1911's viewmodel has its gun renderer on a child ("Viewmodel"), not the prefab's root like every other gun's.
  `SetFirstPerson` moves the renderer out under the camera and back, so it puts a child renderer back under its gun
  object, and `LoadEquipment` destroys a renderer left outside it. Before that fix (2026-09-29) every 1911 load left
  its model on the stage: the user saw it over the USP. It also didn't turn with a drag or frame properly.
  - The fix hotloaded into a gunsmith that had been open since before it, so that scene kept four 1911s from its earlier
    loads, and the user saw them again over the USP and the M18. So `LoadEquipment` also destroys every model under the
    GunsmithSystem's object before it loads a gun (any child with a SkinnedModelRenderer): only the gun it's loading
    belongs on the stage. That also takes off the MP5 the gunsmith scene starts with.
- The bars are `GunsmithStats`, read from the prefabs with the class's parts and tuning, on one scale for every gun, with
  the change from the factory gun in green or red. HANDLING (ADS time) stands where CoD has accuracy, since the game has
  no spread or bloom. FIRING RANGE opens `scenes/gunsmith_range.scene` through
  `GunsmithRangeSession.Enter`, carrying the selected weapon into a private practice session.
  From a match the card says LEAVE MATCH & TEST BUILD; entry disconnects the local player
  before loading the range. `FiringRangeSystem` uses the regular pawn/weapons, replenishes
  reserve ammunition, and provides target reset, moving targets and shot/damage feedback.
  `Tools/gunsmith_range_bench.py` supplies generated long-grain/end-grain oak and beveled
  bench timbers; the range model maps both oak materials. These are current source facts,
  not a replacement for an end-to-end play test.
- Every pick saves as it's made, and `PlayerLoadout` sends the saved class to the host every second, so there's no
  apply step (the user had the mockup's APPLY BUILD removed). SAVE LOADOUT, which only confirmed, was removed too at
  the user's ask (2026-10-13). Over a match, picking a class (`SelectClass`) picks it as the class menu does, which swaps
  it in straight after a spawn.
- BUILDS (`GunsmithPresets`, 2026-10-13, the user: "i might want different attachments on the same gun, as a separate
  build"): named builds of a gun (its parts, camo, finish, reticle and optic tune), 8 a gun, shared by every class.
  - Each is a build code (`ExportWeaponBuildCode( resource, withLockedParts: true )`, so a part not yet unlocked stays
    in it and comes back once it is) with an Id and a name (24 letters at most, "BUILD n" if left blank), in the cookie
    `hc1.gunsmith.presets.<weapon>`. Presets saved before Ids get one when they're loaded.
  - Each class links one build per gun by its Id (`hc1.gunsmith.class<n>.<weapon>.build`).
    The gun is "modified" when its fitted build's code differs from the linked build's (`GetCurrent`).
  - The BUILDS card opens the list: name a build and SAVE AS NEW, the bin deletes, APPLY puts a build on the gun in
    this class, and a modified one offers UPDATE (save over it) or REVERT.
  - The pencil, or a click on a build's name, renames it (the equipped one too). The box takes the keyboard at once
    (`FocusRenameEntry`), Enter saves, and Escape leaves the rename before it closes the list. The user didn't find the
    pencil at first (2026-10-13): another session's firing range code had stopped the game compiling, so their editor
    still ran a build without it.
  - The weapon cards carry the build's name under the gun's ("*" when modified). In the weapon picker each gun lists
    its builds, and a click puts that gun in the class wearing that build (`PickBuild`). The panel reads the states
    twice a second (`RefreshBuildStates`).
  - Compiled with dotnet, not yet seen in-game.
- Escape and the back button close one layer at a time (tuning, compare, builds, share, first person, a slot's parts,
  the picker, the class list), then leave. MainHUD and PauseMenuPanel ask `GunsmithPanel.HandleEscapeAny()` first.
- Clicks bubble to every parent's handler and `@onclick:stopPropagation` does nothing here. A control inside a clickable
  row uses `ClickInside` (`e.StopPropagation()`), and a modal's backdrop closes only when `e.Target == e.This`
  (`ClickBackdrop`). Without that, the tuning panel's DONE closed it and the backdrop's toggle opened it again.
- Header hover labels (`.gnav-tip`) on an open round button are hidden with `opacity: 0`, not `display: none`, in the
  menu and the gunsmith: a label back from `display: none` was sometimes drawn as bare text with no box.
- A label in a row with a `flex-grow` sibling can shrink to one letter's width and wrap letter by letter. The weapon
  cards' "LV" did, beside the XP bar (the user's report, 2026-10-01). Short labels like that get `flex-shrink: 0` and
  `white-space: nowrap` (`.gs-lv-key`, `.gs-lv-num`), and the growing sibling `min-width: 0`.
- Equipment icons (lethal, tactical) are drawn in a square about twice their box, and the box clips them: the
  loadout's 56 px `.gs-gear-img` holds a 110 px `.gs-img-square`, the picker's 44 px box a 90 px one. So an icon must
  be framed like the grenade PNGs, with the item centred and about 40% of the canvas wide. The Recon Drone's SVG filled
  its canvas, so its plane overflowed the Tactical box (the user: "img is too big"). On 2026-09-28 its viewBox was
  widened round the drawing (`-142.5 -187.5 525 525`, `ui/weapons/recon_drone.svg`).
- Attachments unlock by weapon level (`AttachmentUnlocks`, levels 2-30). Each weapon's parts are dealt out one slot at a
  time (optic, muzzle, underbarrel, magazine, ...), plainest first; a part's own `RequiredLevel` above 1 overrides that.
  `GunsmithLoadoutManager.TryGetAttachment` treats a locked part as not fitted (it stays saved). Prestige resets
  weapon levels, so parts lock again.
- Unlock points: one every 5 player levels (`AttachmentUnlocks.LevelsPerPoint`), spent on any locked attachment for
  one weapon (click a locked row, then click again). A point comes back once that weapon reaches the part's level.
  Purchases are in the cookie `hc1.gunsmith.point_unlocks.p<prestige>`, so a new prestige starts them again.
- Leon's Steam account (`AttachmentUnlocks.DeveloperSteamId`) alone sees UNLOCK ALL in the hero, which opens every
  attachment and camo (cookie `hc1.gunsmith.dev_unlock_all`).
- The parts list shows a picture of each part (`AttachmentThumbnails`), rendered at runtime in a scene of its own, one
  per frame, cached for the session; nothing is saved to Assets. Prefab parts are drawn from their prefab's meshes,
  turned by their mount; bodygroup parts from the gun's model with only their choices shown. The bind pose leaves some
  animated bits floating (the RPK mags' top round), so `DropLooseBits` removes small pieces away from the part's main
  one. The studio scene is never ticked, and a destroyed subject's meshes kept rendering into the next part's framing
  look, so `Render` hides them (`SceneObject.RenderingEnabled`) and destroys the subject inside `_studio.Push()`. `dev_thumbnails <weapon> [filter] [probes]` writes them as PNGs to the game's data folder
  (`thumbnails/<weapon>/`) for checking; `probes` also writes the framing looks and the raw shot.
- COMPARE (`WeaponComparePanel`, WEAPON STATS) shows the real figures behind the bars, beside another weapon or
  (the FACTORY chip) this one from the factory:
  - damage, RPM, DPS and the time to empty a magazine;
  - hardcore kill chance, hits to kill and the time to kill (first hit to the killing one, at the full rate);
  - one shot's damage at 10, 25, 50, 100 and 200 m (`GunsmithStats.RangeDamage`: the falloff curve as
    `Shootable.CalculateDamageFalloff` applies it, "-" past MaxRange, where the trace ends);
  - full damage range, muzzle velocity, ADS and reload times, recoil control and its vertical and horizontal parts (on
    control's scale, out of `NoControlKick`), walk/sprint/crouch/prone speeds in m/s and ammo.
  It reads `GunsmithStats`, whose raw fields follow the game's own rules (`PlayerPawn.GetWishSpeed`,
  `Reloadable.GetReloadTime`, `WeaponAmmo.GetMaxReserve`, `HealthComponent.HardcoreBullet`), so change them together.
  - The COMPARE WITH list has category chips over it (2026-10-13, the user: "need filters for assault rifles etc"):
    ALL, then each kind of gun it has. They're bigger than the gun chips and sit over a rule, so they read as its tabs.
    It opens on the compared gun's kind.
  - The YOUR BUILDS / FACTORY toggle is commented out (2026-10-13, the user: "just your build is enough to compare";
    they may want it back), so both columns are the saved builds. The FACTORY chip in COMPARE WITH stays.
  - Saved builds (BUILDS, `GunsmithPresets`) can be compared in either column, two builds of the same gun included
    (2026-10-13, the user: "if i have 2 ak 74us, i wanna be able to compare them too").
    - Over the left column, YOUR BUILD chips: CURRENT BUILD and this gun's builds.
    - COMPARE WITH has a SAVED BUILDS tab after the categories: every gun's builds, and this gun's CURRENT BUILD.
    - Any gun's builds from its chip (2026-10-13, the user: "i need to be able to compare other guns builds for other
      weapons"). Each gun chip shows how many saved builds it has. Picking a gun lists a BUILDS row under the chips:
      CURRENT BUILD (that gun in the active class) and its saved builds. Picking your own gun starts on one of its
      other saved builds. The list opens on the compared gun's kind.
    - A build's figures come from `GunsmithStats.Compute( resource, buildCode )`, through
      `GunsmithLoadoutManager.TryReadWithBuild`, with any part the player hasn't unlocked left off.
    - Picks are kept by the build's Id, so renaming one keeps it picked. The column heads show each build's name under
      its gun.
    - Compiled with dotnet, not yet seen in-game.
- DETAILS (the stats card's `.gs-stats-details`, `ShowDetails`): the same figures in the loadout column, as the build
  beside the factory gun (`WeaponComparePanel.Live`, fed GunsmithPanel's `_stats` / `_baseStats`, so they change when
  the bars do). The user asked for more than the bars (2026-09-29), then to watch those figures while changing parts.
  So it isn't a modal like COMPARE: the parts list on the right stays usable. The build's figures, and their rows,
  are green or red where they beat or fall short of the factory's. Escape closes it after a slot's parts list, before
  the picker. Compiled offline; the editor closed before it hotloaded, so it hasn't been seen in-game.
- The user removed the gunsmith's CHECK / NEEDS CHECKING badges and review-note box on 2026-10-12, including in the
  editor and on the developer's account. Existing `EquipmentResource.ReviewNote` / `kastov_prefabs.Prefabs.review_note`
  metadata stays in the assets for development reference; the gunsmith does not display it.
- Parts are what the real gun takes (the user: "as close to real as possible"; optics are left alone). On 2026-09-29
  the FAMAS F1's 50- and 60-round magazines (the F1 only feeds from its own 25-round one) and the MP5's 10mm 30-round
  magazine (the MP5/10 is another gun) came out. Their files are in `Backups/disabled_gunsmith_parts/` under their
  Assets paths; copy them back to restore. A kastov gun's choice the real gun can't take is `Part(..., offered=False)`:
  the model keeps the bodygroup, `own_parts` writes no part, and a group with nothing offered gets no slot (the FAMAS
  has no Magazine slot). A saved build with a removed part gets the factory part (`TryGetSavedAttachment`).
- A part's `MainPrefab` is written `{"_type": "gameobject", "prefab": "<path>.prefab"}`. Six parts had the bare string
  (`"MainPrefab": "gunsmith/.../x.prefab"`), which didn't resolve in-game, so they were never offered: the SCAR-H's
  Barrel and Underbarrel rows and the USP's Barrel row were empty until 2026-09-29. `dev_thumbnails <weapon>` logs
  what a gun really offers.
- The HC1 grips and suppressors (`gunsmith/hc1/`) are the SCAR-H's alone: the M4 has its own grips, and its Barrel
  slot is for barrels, where a can would stack with a Muzzle-slot one. They sit on the model's `muzzle` socket
  (`GunsmithSocketAttachment`, `hc1_attachment_preview scarh` renders them), and the cans' `MuzzleShift` (6.26, 4.36)
  puts the shots at their front in first person. The old "Tactical Suppressor" (`gunsmith/scarh/barrel/`) is still
  a bare string with no socket fit, so it stays unoffered. The SCAR-H has no Stock, Muzzle or Laser slot yet, though the
  real one takes them.
- The USP's suppressor is its model's own threaded barrel and 9mm can: `muzzle` 2 on v_usp, `barrel` 2 on w_usp
  (`ModelBodygroups`), 6.696 past the bare muzzle (`MuzzleShift`). Choice 1 of each is a match compensator, not offered.

