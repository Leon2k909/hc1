# Photographic map finish

The accepted pass combines a shared camera finish with baked indirect lighting in Ares.
The maps retain their authored ACES tone mapping, exposure ranges, white balance, fog and bloom.

## Camera response

`Code/Utils/PhotographicResponse.cs` and `Assets/shaders/hc1_photographic_response.shader` add one
post-processing pass before the HUD. The saved gameplay and Theater cameras use:

| Control | Value |
| --- | ---: |
| Strength | 0.65 |
| Local contrast | 0.15 |
| Highlight desaturation | 0.12 |
| Edge softness | 0.18 |
| Radial aberration at 1080p | 0.3 pixels before strength |
| Monochrome grain | 0.012 before strength |

Local contrast operates on luminance, with a bounded correction and protection at deep shadows and
hard silhouettes. The central aiming region has no lens softness or colour separation. The pass
does not distort geometry or add motion blur or depth of field. Grain is restrained in blacks and
bright highlights. Strength zero skips the pass.

The player, spectator and free-flying drone prefabs reference the shared camera prefab. Recon camera
feeds copy the effect through the existing identity-safe `CameraPostProcess.Copy` helper. A scope's
image receives the main camera's final pass after it is drawn into the view, so a second photographic
pass is not added to its render target. Theater has the same saved profile.

## Ares indirect light

The new `Ares bounced lighting` object contains one native DDGI volume. Its 11 × 23 × 5 grid has
1,265 probes, with 1,260 active after relocation. The native cubemapper completed two lighting passes.
The three saved textures total 415,124 bytes. Runtime intensity is 0.65; full intensity was rejected
because the cargo corridor's floor lost too much contrast.

`ares-indirect-light.json` is the accepted native volume. `Tools/ares_lighting.py` applies it
idempotently at the end of Ares scene generation. Geometry or light changes require a fresh bake.
The three compiled lighting textures are explicitly included by `.gitignore`.

## Validation and evidence

Evidence is in `output/photographic-look-20261027/`:

- `ares-gi-reduced/`: accepted Ares hall, wing and cargo corridor comparisons at exposure 2.4.
- `daylight-review/`: matched camera comparisons in Belltower, Lowtide, Veridant and Boxyard.
- `identity-control/`: effect-on, repeated baseline and zero-parameter controls on a static Boxyard view.
- `integration-verification-native.json`: native loading of both saved camera profiles, enabled and
  disabled secondary-camera copying with unique identities, and successful shader/lighting texture loads.
- `source-validation.json`: the saved Ares scene differs from the pre-bake scene only by the new
  volume; the generator profile matches and is idempotent.
- `final-compile-status.json`: game and editor compile successfully, with no diagnostics in the changed C# files.

The original `first-trial` captures are superseded: exposure had not settled, making the second image
artificially brighter. Accepted comparisons warm up each variant for 100 frames. The zero-parameter
control and repeated baseline establish the capture noise floor. The animated plasma moves between
Ares images; it is not evidence of a lighting change.

Native bake completion and texture readback were verified. Its first cleanup assertion ran before
deferred object destruction finished and reported an error after saving the staged result. The task
opened Ares document was closed without saving, removing the temporary world. The helper now waits
for deferred cleanup; the completed bake was inspected and was not repeated.

These are native rendering and integration checks. Offscreen readback timings are retained as
diagnostics; a full multiplayer match and a controlled GPU frame-time benchmark have not been run.

## Review commands

Run from the canonical checkout with the installed editor open:

```powershell
rtk python Tools/photographic_look.py audit --label audit
rtk python Tools/photographic_look.py verify --label integration-verification
rtk python Tools/photographic_look.py capture --request Sources/Rendering/photographic-look-v1/daylight-review.json --label daylight-review
rtk python Tools/photographic_look.py capture --request Sources/Rendering/photographic-look-v1/control-review.json --label identity-control
rtk python Tools/photographic_look.py report
```

The scripts use native sbox-cli and session exchange files, preserve the selected document and play
state during captures, and destroy their temporary scenes. `bake` stages a fresh native bake and
refuses existing output; choose a fresh resource revision before rebaking. Shader import uses the
engine's shader compiler. Camera and scene publication use native resource read/write tools with
readback checks. Windows-sized scene documents travel over MCP stdin, avoiding command-line limits.
