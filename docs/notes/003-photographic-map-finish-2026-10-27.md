## Photographic map finish (2026-10-27)
- `PhotographicResponse` adds restrained luminance contrast, highlight desaturation, peripheral lens softness,
  subpixel radial colour separation and monochrome grain after native tone mapping and before the HUD. The shared
  gameplay and Theater cameras use strength 0.65, local contrast 0.15, highlights 0.12, edge softness 0.18,
  aberration 0.3 pixels at 1080p and grain 0.012. The central aiming region has no lens softness or separation.
  It preserves the maps' existing ACES, exposure, white balance, bloom and fog. Strength zero skips its pass.
- Recon feeds copy it using `CameraPostProcess.Copy`. Scope render targets do not receive another copy: the final
  main-camera pass already covers the scope image. The shared camera prefab also serves spectators and Drone.
- Ares now has one native DDGI volume, `Ares bounced lighting`: 11x23x5 probes, two lighting passes, intensity 0.65.
  Its three textures are in `Assets/lighting/ares/photographic-v1/` and explicitly included by `.gitignore`.
  `Tools/ares_lighting.py` and `Sources/Rendering/photographic-look-v1/ares-indirect-light.json` retain it on scene
  regeneration. Rebake when facility geometry or lighting changes. No existing Ares scene object was edited.
- `Sources/Rendering/photographic-look-v1/README.md` describes the implementation, native scripts and evidence.
  Native comparisons cover Ares, Belltower, Lowtide, Veridant and Boxyard. Native profile loading, enabled/disabled
  copy identity and shader/texture loading pass; game/editor compilation reports zero errors and no diagnostics in
  the changed C# files. Full-match performance and multiplayer have not been benchmarked for this pass.

