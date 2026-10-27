## Aiming lasers and reflex sight glass (`GunsmithLaserBeam`, `LaserOptics`, `m4_optic_lens.shader`)
- The user aimed a Kastov-74u with the Box Collimator and a green laser (2026-10-18). The beam was drawn as a bright line
  across the view, and the glass looked strongly blue. They asked whether you'd see the beam at all when aiming, and for
  1:1 realism.
- The laser parts (the M4's MWII Compact Green Laser and the Green and Red Laser Modules) are drawn as a real Class 3R
  aiming laser:
  - 5 mW, a 3 mm beam and 0.5 mrad divergence;
  - green at 532 nm (603 lm/W) or red at 635 nm (148 lm/W), picked from `LaserColor`.
- The spot is the beam's Gaussian irradiance on what it hits, reflected by an assumed 0.35 surface, and longer when it
  strikes at a slant.
  - Its core is drawn at least a pixel round, holding its light, and capped at 8 adapted greys, where ACES still keeps
    its green. A brighter spot shows through the eye's glare round it (the CIE's veiling luminance, 10·E/θ²).
  - Indoors it's a vivid green pinpoint at any range. On a sunlit wall it's a faint speck at 25 m and gone by 50 m.
- The beam is only the light the air scatters toward the eye, so its brightness depends on what's in the air:
  - clean air's aerosol and molecules;
  - the maps' `VolumetricFogVolume`s, at the renderer's 0.0022 per inch per unit of strength (Riverdale's hall haze
    lets you see ~190 m);
  - smoke grenades' puffs, from their size and alpha;
  - rain outdoors (Marshall and Palmer's drops).
  - The particles scatter with a two-term Henyey-Greenstein phase function: a strong forward peak, and the ~0.02/sr
    straight back that lidar measures.
  - A beam under 1% contrast isn't drawn. Clean air leaves it invisible by day and in lit rooms, and faint at night.
    Haze, mist, smoke and rain show it, most of all looking toward the laser. Looking down your own beam you see only
    its weak backscatter.
- Brightness is photometric (cd/m², lux) over the luminance the eye is adapted to (`LaserOptics.Adapted`):
  - Nine view rays, five times a second, sort what's in view into sunlit, shade, indoors and night, by the map's
    brightest sun, the weather's overcast and the sky.
  - A map with no sky (Collider) is a 400 lux interior. Without that rule, Collider read as night and the spot came out
    30-60 times too bright.
  - That luminance is set against the camera's grey (0.25 over the geometric mean of its exposure range).
- The zero:
  - A laser is fixed to the gun and zeroed to its sights at 25 m (`GunsmithMw22Attachment.LaserZeroMetres`), so it
    points wherever the gun does: sway, recoil, reloads, the hip. Nearer than 25 m the spot sits off the sights on the
    laser's side, and past it on the other.
  - The sights' line is learned in the laser's own frame once the gun is aimed and held still (`ScopeEyeAlignment`, as
    the magnified optics learn their eye). It's cached per gun, laser and optic for the session (`LaserZeros`).
  - Until then, and on world models, the laser points along its rail.
  - This replaced an uncommitted bend toward the crosshair (2026-10-18).
- `SceneLineObject` facts:
  - It drops a point within 0.1 units of the one before, so the spot and glare discs are capsules at least
    `MinimumSegment` long. Before this, the old spot's two points were 0.03 apart, so it never drew.
  - Its width is a radius, and the line shader reads vertex colour as sRGB.
- The glass (every 1x reflex and holographic sight's window, the vmats with `g_flLensCoatingOpacity`):
  - 2026-10-19, the user aiming a Box Collimator: "it looks like there is no glass". 11 of the 14 1x sights had no
    `g_flLensCoatingOpacity`, so they passed the view untouched. Now all 14 have it: 0.065 for the reflex sights (one
    coated objective, ~93% passed) and 0.11 for the holographic ones (two windows round the film, ~88%).
  - It blends premultiplied and passes the view at the coating's share (`g_flLensCoatingOpacity` is the loss).
  - `g_vWindowTint` passes each colour as a share of the brightest: the dot's mirror coating reflects a narrow red band
    out of the view, so the view through a reflex sight is a little cyan ((0.88, 0.96, 1); holographic (0.90, 0.97,
    1)). Scalar alpha can't tint, so the dimmest colour's share passes through the blend and the rest comes from the
    scene behind (`bWantsFBCopyTexture`, `g_tFrameBufferCopyTexture`), as the engine's layered glass does. An offscreen
    render with the tint's red at 0.4 took the window's red to 0.35-0.42 of clear glass and left green alone, so the
    backdrop copy works on the overlay layer.
  - `g_flDust` / `g_flDustSeed`: specks at three sizes and a smudge film, lit by the scene. It's 0 on all 14 sights
    since 2026-10-19 (the user: "glass texture is not good"). In a match, against a dark background in sunlight, the
    specks showed as hundreds of white dots (150 cells across the window, about 300 specks), and the film's value noise
    as blurry grey rectangles. Real dust on a sight's window doesn't show: a 50 µm speck 10 cm from a 4 mm pupil is
    blurred to a disc with ~1/6000 of its contrast. Leave it off; the shader code is still there, unused.
    `output/sight-glass/clean/` has the dust on/off renders against a dark wall (`cmp_*.png`) and their script.
  - It adds only reflected scene light: the engine's reflection times the coatings' (0.035, 0.012, 0.014) at normal
    incidence, the red band's being the dot mirror, rising to 1 at grazing.
  - Within ~35 degrees of the line back to the eye, the reflection is cut to `g_flFaceShade`: that's the shooter's own
    face in the hood's shade. It was a fixed 0.08 (the shader's default), which hid every reflection looking through
    the window, at the hip as well as aimed. With the dust off the user saw no glass at all (2026-10-20, "i dont see any
    glass now"). Now it's 0.5 on the reflex sights and 0.3 on the four holographic-strength ones (`att_vm_reflex_02`, the
    Box Collimator, and the three `holo_*`), whose coating scales their reflection 1.8 times: at 0.5 they went pink.
  - `g_flHaze` (0.02 on all 14): an even share of the light on the window that its coatings scatter, lit by the scene
    (the dust's code path with no texture), so the window lifts a little over a dark background in light and not in
    the dark.
  - Together over the dark wall in sunlight (aimed, offscreen), the window went from 89% of clear glass's brightness to
    about 118%, a faint purple-grey cast; over a pale panel it reads a little cool. Trials are in
    `output/sight-glass/visible/` (`cmp2_*.png`: the old look, then three settings; `final_cmp_*.png`: before and
    after). The isolated scene's only reflection source is its sky, so how strong reflections look on a map with
    probes hasn't been seen.
  - The reticle's light adds to the view.
  - The old glass laid a fixed (0.13, 0.28, 0.36) blue over the view at ~7% alpha. That wasn't relative to the scene,
    so it flooded dim scenes.
  - Don't bump the shader's HEADER `Version` (it's 9) while the editor is open. On 2026-10-19 Version 10 stranded all
    14 materials: the editor kept rejecting their compiled files ("special dependency mismatch"), refused to rebuild
    them ("already tried with this fingerprint"), and every model holding them loaded `materials/error.vmat` (a lit red
    checkerboard in the window). Putting 9 back and compiling the shader, then the materials, fixed it; a code-only
    change recompiles cleanly. A shader compile finishes in the background, so compile materials only after its
    `.shader_c` has been rewritten.
  - Checked 2026-10-19 in offscreen renders of the M4 aimed through all 17 1x sights against a lit wall
    (`output/sight-glass/render-glass.cs.txt`, old glass beside new: `sheet_before.png`, `sheet_after.png`, `zoom_*.png`).
    Not yet seen in a match: the backdrop copy in the overlay layer at full screen.
- Checked:
  - Offscreen renders: a lit room at 7 m and 25 m, a sunlit wall at 25 m and 50 m, haze, and a misty night.
  - The Box Collimator aimed on the M4 offscreen: through it the view is neutral, 94% of the view without the gun, dim
    and bright.
  - Live in the user's match on Collider and Orion: no beam indoors, the window neutral, and the zero learned.
- Red dots on the bullet line (2026-10-18). While aiming there's no crosshair, so a dot drawn off the screen's centre
  puts the shots beside it.
  - The 1x sights' reticles are collimated, as a real reflex or holographic sight's are (`m4_optic_lens.shader` v9, every
    material with `g_flScopeReticle` 0). The vertex shader passes the optic model's own forward and up axes, and the
    reticle is drawn by the view ray's angle off that forward axis alone (`g_flCollimationScale` 5.5 reticle units a
    radian: the dot is 1.8 mrad in radius, about what the old projection drew). So the dot shows where the sight
    points, whatever the eye's height: moving the head moves the window round the dot, and past the window's edge the
    window hides it. Only the Scout 3x (`g_flScopeReticle` 1) keeps the old projection: the MWII magnified sights leave
    it at 0, so their glass is collimated too, and once raised ScopeOverlay's lens picture (aligned by OpticZoom) covers it.
  - Before that the reticle was drawn a few inches past the glass (`g_flSightDistanceScale` 0.35), so the dot moved
    7-12° per inch of eye height (`eye-height-762.jsonl`). The first survey (`table.txt`, `results.jsonl`) had the 18
    ported guns' dots 0.2-0.45° low, nearly the same per optic on every gun; that was parallax, not aim.
  - Collimated, each gun's dots share one error, the angle its ADS pose holds its rail off the view.
    `ManualOffset.OpticAimAngleCorrection` turns the gun about the eye by it, for 1x sights only
    (`OpticAngleCorrection`; `TheaterViewModel` too). The ported guns' come from `kastov_prefabs.py` (`optic_aim_angles`,
    written by `set_aim`). The M4's (`0.328,-0.0004,0`) is set by hand in its prefab; its `AimOffset` stays `0,0,0`.
  - Measured with `output/reticle-survey-20261018/collimated/` (`survey.cs.txt`, driven by `run_survey.py`): each gun's
    viewmodel settled aimed, placed as `ViewModel.Setup` places it, the view on the camera bone at every sample. The
    rendered dot matches the optic's own axis to 0.001°, so the rig also reports the axis (`axisRight`, `axisDown`).
    - Before the corrections (`before*.jsonl`): the M4's dots 0.33° high, the RPK-16's 0.30° low, the AK-74M's 0.12°
      high, the AK-12's and AK-15's 0.10° low, eight guns already on the centre and the rest within 0.06°.
    - After (`after*.jsonl`, `table.txt`): every ported gun's 13 dots within 0.004° of the centre (the M16A4's worst;
      the rest under 0.001°). The M4's average on the centre, and its idle sway carries them round a ±0.13° loop.
    - After the M16A4's post and the five raised optics (2026-10-19, `risers-m16-b.jsonl`, `risers-all.jsonl`): the
      M16A4's dots within 0.0007°, every other ported gun's within 0.002°, their optics' axes unchanged.
  - The Kastov-74u's Box Collimator sight line (Angles `-0.4466,-0.04,0`, solved for the old reticle) is gone: with a
    collimated dot it threw that optic 0.41° off.
  - Renders at three eye heights (`renders.png`): the dot holds still while the window, post and hands move.
  - The M4's two old 1x sights (`gunsmith/m4a1/optics/`: the Reflex Sight and Patrol Red Dot) are collimated too: on the
    M4 their dots sit 0.03 degrees high and 0.05 low (`old-optics.jsonl`). Unlike the MWII optics they don't move with
    the M4's idle sway: their mounts don't follow its animated bone.
  - Not yet seen in a match: the dots, the M4's sway, and the gunsmith stage and thumbnails, where a collimated dot only
    shows looking down the sight.

