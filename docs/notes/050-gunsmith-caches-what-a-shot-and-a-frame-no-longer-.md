## Gunsmith caches (what a shot and a frame no longer work out again, 2026-10-17)
- A performance audit found every shot asking `GunsmithLoadoutManager.TryGetAttachment` about 84 times: 7 effect passes
  over 11 slots (`GunsmithAttachmentEffects.For`, from Shootable, its effects, ShootRecoil and ViewPunch), plus
  `RefreshAmmunitionLoadout` and the suppressor check. Each lookup read cookies and searched all ~900 parts. Measured
  in a match on the Kastov-74u with 9 parts fitted, that took 3.56 ms a shot. It now takes 0.5 µs.
- `GunsmithLoadoutManager.Version` / `MarkChanged()` decide when anything is worked out again. Everything that can
  change a fitted part bumps it:
  - SetAttachment, SetActiveClassIndex, the optic tune setters, ApplyAttachments' barrel clear and the USP-SD migration;
  - UNLOCK ALL, spending a point, a weapon level-up (`WeaponProgression.AddXP`) and a prestige;
  - a part loading or reloading (`GunsmithPart.PostLoad`/`PostReload`, which also bump `GunsmithPart.LibraryVersion`).
  **A new cookie write that changes a part, its unlocking or its tune must call `MarkChanged()`**, or the guns keep the
  old answer.
- What it keeps:
  - TryGetAttachment's answers, per resource and slot. Parts are found through an index by path and name
    (`PartsNamed`), in the library's order.
  - Per gun: the effects (`Equipment.FittedEffects`, also keyed by prone for the bipod), the ammunition loadout (also
    keyed by possession: the first refresh runs before the pawn is possessed), the suppressor check and the tuned zero.
  - While a build is being fitted (`IsFittingBuild`: Theater, COMPARE) nothing is kept.
- The unlock ladder (`AttachmentUnlocks.GetLadder`) used to be made again every 5 s. Now it's made again when a part
  loads or the scene changes, so a viewmodel prefab's new slot shows on the next map. A rebuild takes ~0.2 ms.
- Per frame:
  - `GunsmithAttachmentPoint.On( root )` keeps each weapon's point list until a point is made, destroyed or given a part
    (`GunsmithAttachmentPoint.Version`; SetPart bumps it). Category and CurrentPart are still auto-properties, so
    hotloads keep them, so code that assigns CurrentPart directly must go through SetPart. A point walk went from 1.6 µs
    to 0.015 µs.
  - `GunsmithMw22Attachment.BoneDelta` keeps each model's bones by name: 3.8 µs to 0.12 µs a call, with identical
    transforms.
  - The mounts' camera-setup remount (`ICameraSetup.PostSetup`) now only runs for viewmodels
    (`GunsmithMw22Attachment.OnViewModel`). A world model's parts are its children and move with it. Bone attachments
    that follow an animated bone or hide one still remount.
- CameraScope (the M700's 3D scope) does its setup once instead of every frame (the texture clear, the material, the
  render target and the parent). It puts the material back when the camo pass clears it. The audit thought the scope
  camera rendered at the hip too. It doesn't: the lens is 9.7 from the eye at the hip and 3.7 aimed, so the `> 5` check
  already only draws it while the scope is up. Gating it on the aim tag was tried and taken out: the lens went black
  while the scope came down.
- The scope's picture was a fixed 512 x 512, which the lens stretched more than twice over (the user: "it looks really
  low res"). It's now the screen's height rounded up to 128, between 512 and 2048 (`CameraScope.PictureSize`: 1152 at
  1080p). Aimed, the M700's glass is about 1.06 screen heights across. That's ~5x the pixels for the scope's camera
  while scoped. A new size is made when the screen's changes, and the picture goes with its viewmodel (`OnDestroy`).
  Live in the user's match (1152 x 1152), not yet looked at through the scope.
- The scope went black while strafing aimed (the user, 2026-10-19: "when i move with a and d i dont think it should go
  completely black"). Its `OnPreRender` could run before `CameraController.OnPreRender` put the gun at the eye that
  frame, so the eye was measured against last frame's gun: moving sideways read as the eye far off the scope's axis
  (`ScopeEyeOffset`, which slides the shader's 0.43 window off the glass). Now the scope is worked out in
  `ICameraSetup.LateSetup`, after the gun and its parts are placed; `OnPreRender` only does it for a scope no camera
  sets up (Theater, test scenes). The eye box is left as it was: it goes black ~21 mm off axis, already kinder than a
  real 10x40's 4 mm exit pupil, and with a cheek weld the eye moves with the rifle, so strafing shouldn't shade it.
  Built with dotnet; the editor was closed, so not hotloaded or looked through yet.
- Checked in the editor on 2026-10-17:
  - 1,800 lookups (45 weapons, 20 slots, fresh and kept) and 17,913 index checks against the old logic: no differences.
  - In a Lowtide TDM: the kept loadout, effects and suppressor check match fresh ones, and 5 shots left the version
    alone (so no cookie reads or part searches). The M700's scope ran through hip, aim and release.
  - Not yet seen by eye: every gun's parts in first and third person, and the Theater's M700.

