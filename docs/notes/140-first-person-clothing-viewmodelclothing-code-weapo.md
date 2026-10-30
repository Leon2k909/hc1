## First-person clothing (`ViewModelClothing`, `Code/Weapons/ViewModelClothing.cs`)
- Clothing surface revision 4 (2026-10-21, user: material still looks wrong): first-person army-shirt slots use
  `materials/operators/first_person/v4/shirt.vmat`; gloves retain v2. V3's coarse weave was baked into the
  albedo and read as pebbled leather even with its normal layers disabled. Four cleaned colour regions retain
  the camo print/stitches while removing that relief; the right sleeve's false painted highlight was removed.
  The v4 shader uses filtered fold normals and a separate 256-square analytic cotton height map. Fine threads
  sample model coordinates captured before standard vertex processing, with triplanar height and surface-gradient
  bump shading so their scale is independent of the narrow cuff UV islands. Texture streaming includes this map.
  `Sources/Clothing/firstperson-v4/imagegen-prompts.json` records exact built-in edit prompts and raw sources.
  Clean/fibre builders and guarded native imports preserve the rejected colour-filter experiment; do not replay
  earlier one-shot stages over the final profile. `output/firstperson-clothing-v4-20261021/applied-report.json`
  records final hashes and checks. Native bright/dim close-ups and the production Field Operator `Dress` check
  passed (v4 shirt, v2 gloves, body tint retained, bare arms hidden). The shared editor stayed stopped/saved;
  these are private engine previews, not a live-match check of this revision. Geometry/animation are unchanged.
- Clothing surface revision 3 (2026-10-21, user: sleeve still pixelated): army-shirt first-person slots now use
  `materials/operators/first_person/v3/shirt.vmat` and `shaders/viewmodel_fabric_v3.shader`; gloves retain v2.
  Four separately authored, registered UV regions give sleeves approximately 2.45x the native linear pixel
  density of the v2 whole-atlas crop; cuff regions gain 3.13x and 4.94x. Generated source sizes and exact prompts
  are recorded under `Sources/Clothing/firstperson-v3/` and `output/firstperson-clothing-v3-20261021/`.
  `Tools/build_firstperson_clothing_v3.py` stages these sources and filtered fold normals; native publication
  resamples only for compiler dimensions and does not count that conversion as new detail. Region sampling
  uses remapped UV gradients and feathered boundaries. Streaming requests include all four region textures.
  Fixed-camera native v2/v3 comparisons cover both sleeves and the cuff; a read-only check of the actual live
  Belltower `ViewModelClothing` confirms the v3 material, shader and all nine valid loaded texture bindings.
  `live-after/camera_screenshot.png` is an actual in-game capture. No scene/play/camera edits were required.
- Clothing surface revision 2 (2026-10-21, user: blurry sleeves still not improved):
  `ViewModelClothing.Materials.cs` assigns authored `materials/operators/first_person/v2/shirt.vmat` and
  `gloves.vmat` to the army-shirt and fingerless-glove slots. The renderer retains its outfit tint and skin slots.
  `shaders/viewmodel_fabric_v2.shader` adds independently repeating fine normals/roughness variation, 16x
  anisotropic filtering and explicit cutout clipping. Active first-person clothing renews its texture-streaming
  requests in `LateSetup`, including when the materials are already cached.
  - `Tools/build_firstperson_clothing_v2.py` and `Sources/Clothing/firstperson-v2/` record the sources and native
    publication/QA. Imagegen's base atlases were natively 1254 square, converted to 2048 for compiler mip filtering;
    this conversion is not a claim of newly resolved 2K detail. Fine weave is a separate repeating texture.
    Original coverage and tint masks are retained. Reconstruct the exported packed normal's Z from XY; treating
    all three exported channels as an RGB source normal exaggerates the surface. The engine's single-channel AO
    readback returned black; the new material uses a neutral AO fallback, not that unreadable black map.
  - Native shader/material and C# compilation passed. Native close-ups and the actual production `Dress` routine
    on an isolated Field Operator verified both v2 material bindings, tint/skin preservation and hidden bare arms.
    Evidence: `output/firstperson-clothing-v2-20261021/native-r5/` and `dressing-proof.json`. This did not run a live
    match or alter the shared Belltower scene/play state; do not label these captures live gameplay.
- The user (2026-10-08): "when holding a gun i dont see my clothes on my arms". Every viewmodel's arms are
  `v_first_person_arms_human.vmdl`, bare skin whatever the outfit.
- `Equipment.CreateViewModel` adds a `ViewModelClothing` to the viewmodel (`Fit`). Once the body wears a uniform
  (the human model with a `MilitaryUniform`), it dresses the arms:
  - It hides the arms' own mesh: their `arms` bodygroup goes to its last, empty choice, and comes back when it undresses.
  - In its place it draws a copy of the body (a "Clothing" child of the arms), dressed by its own `MilitaryUniform` in
    the body's style and pieces: the shirt's sleeves, the gloves (the Tactical and Desert Operators' tints too), and the
    skin where nothing covers it (the Military Operator's bare hands).
  - The Head, Legs and Feet bodygroups are hidden, and so is every garment with no arm, hand or finger bones (helmet,
    balaclava, trousers, boots).
  - It's drawn on the overlay layer with no shadow, like the arms, so `ViewModelMask` counts it as the gun.
  - It checks the body every 0.5 s and dresses again when the style changes (an outfit pick reaching the host).
  - It follows the arms' Enabled, so it goes while the tablet flies the drone, and with the developer menu's Toggle
    View Model.
- Why not sleeves over the first-person arms: their forearm is 0.2-0.35" thicker than the body's, so the body's
  garments poked through. The body's own arms keep its garments fitted as in third person.
- The pose, in `ICameraSetup.LateSetup` (new: after PostSetup, so after `SwbArmsRetarget` and the tablet's, the
  defuse kit's and the throwables' arm posers):
  - The arm and finger bones (the two skeletons share their names and axes) take the first-person arms' model-space
    transforms as they are.
  - The torso has no first-person bones. It's held behind the eyes, as a body's is: the body's eye centre (between
    eye_L and eye_R) at the camera, facing the way it looks, and every bone off the arms in its bind pose from there.
    So neck_0 is 4.5 behind the camera and 7.4 under it, and the chest about 87 degrees under the view.
    - It used to put spine_2 half way between where each clavicle put it. The ported guns' clips swing the clavicles
      about, and the user saw their clothes in the camera aiming and reloading aimed with the M18 (2026-10-09). The
      M18's clips bring the clavicles 4" forward aimed and 8" in its reloads, which put that torso's eyes 1.4" and
      6.1" in front of the camera, and the shirt's collar and shoulders across the view. Even at the hip its eyes were
      3-4" ahead on the FAL, Uzi and P90.
    - The clavicles still take the first-person arms' own, so the sleeves are where they were. The shirt stretches
      between the neck and the shoulders, all under the view: across eight guns' clips no shoulder joint comes into a
      120-degree view (the nearest, the FAL's, is 45 degrees under its centre).
    - Every camera in the scene runs `ICameraSetup`, so only a main camera places the body (not a scope's lens, the
      minimap or the gunsmith's thumbnails).
  - The forearm's twist bones take the hand's turn about the forearm as the citizen's constraints do (twist0 none, twist1
    two thirds), and the elbow helper sits half way between the upper arm and the forearm.
  - It goes in as bone overrides in model space plus the world transforms, as `SwbArmsRetarget`'s does. Garments are
    posed from the same pose (not bone-merged a frame behind), and a garment bone the body lacks keeps its bind pose
    against the torso.
- The camo pass (`GunsmithLoadoutManager`) skips it, as it skips the arms: it leaves any renderer under a
  `MilitaryUniform`.
- Not on the gunsmith's stage or in Theater (no owner), nor on the legacy player models.
- Compiled offline with dotnet (2026-10-08), with the editor closed. Nothing has been seen in-game. To check: the
  sleeves and gloves on each outfit at the hip, aiming, reloading and sprinting; that the first-person arms' longer
  bones don't stretch the elbows or wrists; the cuffs against the gloves; whether the shirt's collar, the vest or the
  chest shows when looking down or sprinting; and the hands on the tablet and the defuse kit.
  - The torso held at the camera compiled with dotnet on 2026-10-09, with the editor closed. To check: the M18 aimed and
    reloading aimed, and a rifle's sprint and reloads, for the collar, the shoulders and stretched sleeves.
- `hc1_vm_clothing [weapon] [style] [view]` (`Editor/Hc1ViewModelClothingQa.cs`) renders a gun's viewmodel offscreen
  with the clothing at the hip, aimed, and through aimed and hip reloads, into `output/vm-clothing/` (view 0 the eye,
  1 from behind and above, 2 from the left, 3 from the right), and logs each garment's bone nearest the eye.
- Camera movement (2026-10-14): the camera places the viewmodel in `OnPreRender`, when its renderers can still have
  the previous frame's `SceneModel.Transform`. Using that cached transform for the eye added the movement to the
  torso again when the renderer caught up, stretching the shirt and vest through the camera on AK-74u jumps.
  `ViewModelClothing.Apply` now uses the renderers' current `WorldTransform`, carries the arms' cached model-space
  pose into that space, and synchronises each clothing SceneModel before writing its overrides. This is shared by
  every weapon. Native isolated checks passed for 42 viewmodels and all five outfits: hip, ADS, reload, sprint and
  jump poses, rising/falling, translation and rotation, and four renderer update orders (33,600 movement samples).
  The maximum clothing pose drift was 0.000221 units. Screenshots, results and the `run_csharp` regression script
  are in `output/viewmodel-jump-clipping/`; the user's scene and play state were kept during validation.

