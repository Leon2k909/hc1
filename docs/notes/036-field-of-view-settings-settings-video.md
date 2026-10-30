## Field of view settings (Settings → Video)
- The user asked for CoD-style control over the field of view, "affected or independent etc" (2026-10-08).
  - Field Of View is 60-120 (was 65-110), horizontal, default 85.
  - ADS Field Of View (`GameSettings.IndependentAdsFov`): Affected (the default) or Independent.
  - Third Person Field Of View (`ThirdPersonFieldOfView`, 60-120, default 85) is used whenever
    `CameraController.Mode` is ThirdPerson: the deathcam and spectating from behind (`CameraController.HipFieldOfView`).
    Its getter reads 0 as 85, since a settings file or a hotloaded settings object from before it existed has 0.
- How aiming zooms now (`Equipment.AimFov`, `OffsetMagnification`, `ReferenceFov` 85):
  - A gun's `AimFovOffset` (-5 on most, the M700's -30) is degrees off 85. It's turned into a magnification, and a
    magnified optic multiplies it by `OpticZoom.ViewMagnification` (1.2).
  - Affected zooms the player's own Field Of View by that magnification. At 110 the irons aim at 105.2 (it was 110 - 5).
  - Independent zooms 85 by it, so the ADS view is the same at any Field Of View: irons 80, the M700 55 and a magnified
    optic 69.9.
  - `GetAimFovOffset`, `TheaterViewModel` and `FlatScope.GetMagnification` (its `ZoomLevels` are degrees off 85) all go
    through it. The scope lens (`OpticZoom`) works from the main camera's field of view, so it follows either choice
    unchanged.
- There's no Weapon (viewmodel) field of view. The viewmodel draws in the main camera's overlay pass, with the main
  camera's field of view. A separate one would need either:
  - a second camera, which loses the post-processing and breaks `ViewModelMask` and the scope lens;
  - or the viewmodel squashed along the view, which skews the bone-mounted attachments and misplaces the lens.
- Aim sensitivity doesn't follow the zoom: irons aren't scaled at all (`ManualOffset` only divides `AimDampening` by
  a magnified optic's power). So at a high Field Of View, Independent irons feel faster than Affected ones.
- Compiled with dotnet and hotloaded into the user's match (2026-10-08). Not yet checked in-game.
- Weapon position (2026-10-20, the user: the gun sat "further away from my screen", and they wanted it in settings):
  Weapon Distance (-4 to 4), Weapon Horizontal Position and Weapon Vertical Position (-3 to 3), in inches from where
  the gun's animations hold it at the hip (`GameSettings.WeaponDistance`, `WeaponSidePosition`, `WeaponHeightPosition`;
  0 is the default and what an old settings file reads as).
  - `ViewModel.HipOffset` adds them in the view's space in `ApplyOffsets`, faded out by the eased `ironsights_weight`,
    so aiming down the sights lines up exactly as before. It moves the arms and clothing with the gun.
  - Theater's first-person gun (`TheaterViewModel`) doesn't take them yet.
  - What had made the gun look further away wasn't found: no hip pose, viewmodel or camera change since 2026-10-15
    moves it. A wider Field Of View shrinks it, since the viewmodel draws with the main camera's.
  - Built with dotnet and compiled in the editor, not yet seen in a match.

