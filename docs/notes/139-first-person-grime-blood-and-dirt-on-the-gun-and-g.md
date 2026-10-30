## First-person grime: blood and dirt on the gun and gloves (`FirstPersonGrime`, 2026-10-16)
- The user: "blood should go onto my gun when ive been shot and dirt when ive been prone in dirt etc".
- `FirstPersonGrime` (on the local pawn, made by `PlayerPawn.OnUpdate`, not networked) keeps a `Grime` for the hands
  (sleeves and gloves) and one per gun (`For( equipment )`), cleaned at each new life:
  - Blood from `DamageTakenEvent`, by damage / 40 (0.4-1.5): arm or hand hits put most on (hands 0.45, gun 0.3), body
    hits less (0.25, 0.18), leg hits little; a blast adds the ground's dirt. It dries over `BloodDryTime` (90 s): wet
    glossy red to matte brown-black.
  - Dirt from the ground under the hands while prone or sliding (`GroundOf`: soil, mud, sand, gravel, grass, concrete
    dust, grease, by the surface's name, else `WorldSounds.Classify`): `DropDirt` going down, `CrawlRate` crawling,
    `LyingRate` lying still, the gun half the hands' (`GunShare`). The colour follows what was added last.
  - Rain outdoors (a trace up) rinses it (`RainWash` per mm/h) and wets it (mud, gloss); lying in water or snow
    washes it fast.
- It's drawn as a second skin over every renderer in the viewmodel (`GrimeSkin` marks it): the same model, bone-merged
  to the gun's renderers, or for the sleeves and gloves posed by `ViewModelClothing` (`Follow`, kept out of its
  cloth-material swap). Every slot wears `materials/effects/hc1_grime.vmat` (`shaders/hc1_grime.shader`) but lenses,
  reticles, see-through and hidden pieces (`CamoMaterialRules`). The shader pushes the skin 0.012 out along its normals,
  draws splashes, pooled stains, dust patches and grains in the model's own space, and is see-through elsewhere.
  The gunsmith's camo and hidden-piece passes skip `GrimeSkin` renderers.
- `dev_grime [blood] [dirt] [ground] [dry]` sets it on the local hands and gun in hand.
- Blood appearance revision (2026-10-21, user: circular spots look terrible): `Splashes` replaces opaque spherical
  spots with randomly oriented lobed shapes, tails, satellites, noisy edges and varied thickness. Three scales add
  clustered spray; accumulated stains have broken coverage. Wet blood is darker crimson with restrained gloss,
  drying to brown. Dirt, gameplay accumulation/drying/washing, material exclusions and clothing materials are unchanged.
  The canonical shader was published through the native editor, compiled with `EditorUtility.CompileShader`, then
  `materials/effects/hc1_grime.vmat` compiled successfully. Authoring/QA: `Sources/Effects/firstperson-grime/`.
  Native before/final Kastov74u renders (same camera and seed, light/heavy/dry/clean/dirt) and receipts are in
  `output/firstperson-grime-fix-20261021/`; clean/dirt-only RGB RMS differences are below 0.02/255. Disposable QA
  scenes were destroyed and Belltower's selection, saved state and stopped play state preserved. The independent
  shirt-model render does not exercise `ViewModelClothing.Follow`; do not treat it as a posed clothing integration test.
  Live match checks remain: hip/ADS on several guns, optics staying clear, sleeves/gloves following the hands,
  no z-fighting or lag when turning, third-person gun clean (`dev_grime 0.7 0.6 soil`, `dev_grime 0 0.8 mud`).

