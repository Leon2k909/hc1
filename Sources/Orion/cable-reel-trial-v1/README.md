# Orion launch-deck cable reel — private review

This model rebuild targets one saved cable-drum placeholder at plan
`(380,1320,240)`, world `(1320,-380,240)`. The user approved installation on
2026-10-30 after reviewing the separate proposal. It is now installed at that
position in the saved Orion scene. The earlier Ares lamp and console proposals
remain uninstalled.

`before.json` copies all 28 triangles, original UVs and split normals directly from
the active `orion_launch_deck.obj` import. The saved Orion scene has its Launch Deck
renderer enabled, at the identity transform. The generator explicitly calls these
two placements cable drums; the current saved mesh is a 14-sided open cylinder
using the concrete-like `oa_wall_dark` material. Its missing caps and single-sided
back-face culling are retained in the comparison. Nothing is removed to make the
before look worse. The existing model also loaded successfully in the native
editor without switching the user's active Ares scene or play state.

The candidate contains individually cut circular timber boards in two crossing
layers on both flanges, genuine through bores, a hollow staved barrel, continuous
33-turn visible cable winding, retained lead-out, formed retention cleat, open
galvanized arbor rings, eight tension rods, washers, hex nuts, visible helical
threads and a fictional Orion inventory label. Small perimeter irregularities and
edge breaks support the photographic grain. Everything stays within the original
52-inch diameter and 46-inch height.

The top/bottom timber surfaces reuse the existing unmodified CC0 Brown Planks 03
scan by Rob Tuytel, recorded in `Sources/Belltower/scans/manifest.json` and
`brown_planks_03-info.json`. Source: https://polyhaven.com/a/brown_planks_03.
Each actual board selects a seam-free portion of that scan; the exposed sawn ends
have a separate cut-grain PBR material. Original scan pixels remain unchanged.
Private cable, zinc, localized oxidation and inventory-label textures complete it.

Before/after pictures are Blender Cycles studio renders with identical camera,
scale, floor, lighting, exposure and view transform. They are not engine screenshots
or a claim of native material/performance validation. The `.blend` retains editable
parts and packed textures. The GLB joins the reviewed candidate into one mesh with
material groups and embeds its textures. OBJ/MTL and private texture sources are
also supplied. Blender/OBJ uses metres, +Z up, front -Y; glTF uses its standard +Y-up
conversion.

Historical preview commands from the original source revision (the installed
map intentionally differs, so the original-source guards now reject a fresh
extraction). Existing review exports and pictures remain unchanged:

```powershell
rtk proxy python Sources/Orion/cable-reel-trial-v1/prepare.py
rtk proxy python Sources/Orion/cable-reel-trial-v1/run_render.py --validate-only
rtk proxy python Sources/Orion/cable-reel-trial-v1/run_render.py
rtk proxy python Sources/Orion/cable-reel-trial-v1/verify_export.py
```

The renderer owns a single hidden Blender process, runs at idle priority on four
CPU threads, uses no GPU rendering, and exits on completion. Existing editor and
interactive Blender processes remain alone. Geometry checks reject nonfinite or
zero-area triangles and anything outside the original outer envelope. A guard
checked 527 original files, including Orion source/model/materials, the reused scan
and both earlier proposals before integration.

## Approved installation, 2026-10-30

`models/props/orion/cable_reel_v1/cable_reel.vmdl` has four LODs: 81,443,
28,505, 9,773 and 2,850 triangles, using six private materials under
`materials/orion/cable_reel_v1/`. The closest LOD preserves every approved
vertex, normal, UV and face; only the native axis/unit conversion changes.
Native copies of normal maps encode the reviewed normal strengths; original
texture sources remain untouched. No frame-time benchmark was performed.

The old packed launch-deck OBJ loses exactly the two 28-triangle open cylinder
shells. The first original collision box remains authoritative for the new
render-only instance. The second cylinder at plan `(470,1300,240)` was inside
the stair opening; its shell and box collider are removed. All other packed
geometry, UVs, normals, hulls and boxes are preserved. The saved scene only adds
the native-serialized `ORION cable reel` child. `Tools/orion_cable_reel.py` and
the `Tools/orion_map.py` hooks preserve both decisions on future map builds.

Publication and compilation ran through the existing s&box editor using
`import_resources.cs.txt`, `compile_resources.cs.txt` and `install_map.cs.txt`.
The active editor document and play state were preserved for each native call.
The native model loads with all six intended materials, and the updated map and
scene compile successfully. Isolated native captures contain no error models.
Navigation has complete paths from both teams to all 95 targets; a separate
133-inch path runs directly up the cleared upper stair flight using the scene's
16-inch radius, 64-inch height agent. This is an editor navigation check, not a
live match playtest.

`verify_install.py` verifies exact installed resource hashes, the surgical map
and scene edits, the approved closest-LOD geometry and attributes, and the map
generator against its original implementation. Receipts, original map/scene
backups and engine screenshots are in
`output/orion-cable-reel-installed-20261030/`.

Outputs: `cable_reel_review.blend`, `cable_reel_after.glb`,
`cable_reel_after.obj`/MTL and `textures/`. Pictures and validation reports:
`output/asset-improvement-20261030/orion-cable-reel/`.
