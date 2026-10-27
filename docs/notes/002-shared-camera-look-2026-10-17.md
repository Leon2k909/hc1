## Shared camera look (2026-10-17)
- The gameplay camera (`Assets/prefabs/player/cameras/default_player_camera.prefab`) and Theater's camera
  (`Assets/scenes/theater_playback.scene`) use native ACES. The extra camera `ColorAdjustments` is disabled.
  A same-position native camera comparison rejected AgX plus the added grade: it crushed shadow detail and
  pushed the brick colour too far. Keep map-authored white balance and grading as the starting point.
- Fallback bloom is additive, strength 0.1 and threshold 1.6. Fallback AO uses radius 48, intensity 0.45,
  falloff 0.9 and thin compensation 1; its quality and spatial denoising remain as authored. Vignette is 0.08.
- The engine groups native effects by type: the camera selects the tonemapping mode, and subsequent map volumes
  blend the numeric controls. Keep each map's exposure, fog, white balance, reflections and lighting authored in
  its own scene/generator. These camera defaults do not replace the map volumes' numeric settings.
- `CameraPostProcess.Copy` preserves component enabled state with an explicit include-disabled lookup and the
  existing identity-safe serialization helper. `OpticZoom` and `ReconOctocopter` synchronize colour values while
  their views are active, so runtime colour adjustments reach both views. The scope
  also receives the main camera's sharpening; the drone receives its fallback vignette.
- Spawn protection no longer changes screen colour: the blue `ScreenProtectionOverlay` and the camera's
  protection-only saturation override were removed. Invulnerability and the timed "Spawn Protected" toast remain.
- Offline verification is in `output/camera-look-20261017/`: the native preset JSON is valid, component IDs and
  all camera/gameplay/UI content outside the look are preserved, and player/Theater profiles match. The full
  `Code/razedtest.csproj` build passed with 0 errors and 83 warnings; none are in the changed C# files.
- The follow-up native compile passed with zero errors (69 game warnings and 4 project-editor warnings, none in
  the changed camera/HUD sources). `lowtide-camera-aces-neutral.png` and `lowtide-camera-agx-current.png` in the
  audit folder compare the accepted and rejected profiles under the same map lighting and fog. These use a
  temporary game camera and the native post-process builder; an ordinary editor viewport is not equivalent.
  The temporary camera was removed. Full-match exposure transitions, scope/drone behaviour and GPU frame times
  remain unmeasured. The comparison does not establish photorealism across every map.

