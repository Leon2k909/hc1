# Veridant fountain roaring-lion crown — rejected, original restored, 2026-11-08

The user rejected this version as a downgrade of the look ("you've downgraded the look") compared
with the installed seated Barye lions and their tall pier. The scene was restored to the Barye crown
(`SculpturalMouth 28.9,3.2,70.65`, landing 37.17, outlet 0, no crown shadows), saved, and checked
against the original before capture (`roaring-restored-a.png`, mean difference 0.5/255). The new
assets stay on disk unused for reuse. Visible weaknesses in the review captures: a light, coppery
bronze with saturated green blotches (reads as painted resin next to the old dark statuary bronze),
a short wide pier with a heavy flat cap (the old pier is tall and slender), and photogrammetry
lumps on the scanned lions' flanks and haunches.


Replaces the seated Barye lions with a crown laid out like the user's prototype (`crown-source.png`
in `../fountain-reference-top-v2/`): two recumbent bronze lions, heads raised and mouths open, rumps
against a carved limestone pier, on a lobed cast bronze base.

- Lions: "Lion Statue" by beachmouse, CC BY 4.0 (see `ATTRIBUTION.md`; credit also ships as
  `ATTRIBUTION.txt` beside the model). Scan of a recumbent, roaring lion with a long locked mane.
  `Tools/veridant_roaring_lion_blender.py` (Blender 5.1, background) cuts away the scanned slab,
  turns the head to +X, scales it to 31.5 in, centres the open mouth on Y=0, decimates to
  52k / 14k / 3.8k triangles, unwraps a smoothed copy (the raw scan splits into thousands of
  slivers) and bakes the tangent normal map plus occlusion / convexity / 3D noise ingredient maps
  at 4096.
- Crown: `Tools/veridant_fountain_roaring_crown.py` (numpy, scipy, scikit-image, Pillow; the
  TripoSG venv in `%TEMP%/veridant-reference-3d/.venv` has them) mirrors the lion into a pair
  (both tails and the slightly turned heads face the -LEFT side, the usual approach), moves it
  against the pier and scales it 6% so the heads reach ~84% of the pier height as in the
  prototype; builds the pier (round moulded cap, flaring superellipse shaft, framed acanthus panel
  on both open faces, fluted corners, square plinth) and the base (outline fitted to both lions'
  footprint); composes the verdigris bronze colour / roughness / metalness / occlusion maps from
  the ingredients; writes three LOD OBJs, the vmdl and the vmats. A second argument writes a
  trial copy of the Assets tree elsewhere.
- Runtime: `models/props/shared/veridant_fountain_roaring_crown/crown.vmdl` (LOD0 211,810 tris,
  LOD1 68,591, LOD2 15,979; switch 36 / 90). Materials `materials/veridant/fountain_roaring_lion_bronze.vmat`,
  `fountain_roaring_base_bronze.vmat` (textures in `materials/veridant/fountain_roaring/`) and the
  bowl's own `fountain_carved_limestone.vmat` for the pier.
- Scene: `ForecourtFountainFlow` 14cc7dcb on "Forecourt carved fountain bowl 1" uses the crown with
  `SculpturalMouth 33.45,0,60.95`, `SculpturalLanding 39`, `SculpturalOutlet 0.36`,
  `CrownCastsShadows true` (the last three are new properties; their defaults keep the old
  behaviour). Saved through the editor. The scene file is not tracked in git.
- Revert: set `RecliningLions` back to `models/props/shared/veridant_fountain_barye_open_mouth/crown.vmdl`,
  `SculpturalMouth 28.9,3.2,70.65`, `SculpturalLanding 37.17`, `SculpturalOutlet 0`,
  `CrownCastsShadows false`, toggle the object and save. All earlier crowns are kept.
- Review: matching live-viewport captures (same editor cameras and lighting) are
  `output/veridant/fountain-flow/roaring-before-{a,b,c}.png` / `roaring-after-{a,b,c}.png`, side by
  side in `roaring-before-after.png`. Bake work files are in `output/veridant/roaring-lion-work/`.
- Rebuild: Blender `prep` then `lods` stages with the GLB and a work directory, then the crown
  script with that work directory. Regenerating only the textures needs just the work files.
