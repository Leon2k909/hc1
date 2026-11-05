# Riverside ice freezer v2 — archived duplicate

**Superseded during review.** The user approved a different ice cabinet in the chat “Show project in the editor”, and that cabinet was installed concurrently. Preserve `models/maps/riverside/ice-cabinet-v1/` and its public store imports. This duplicate was never installed. Its private assets are archived outside Assets at `output/asset-improvement-20261030/riverside-ice-freezer/superseded-assets/`; `retire.cs.txt` removes only those archived duplicate assets through the native editor. Do not rebuild or propose installing this version. The next candidate in this chat is `Sources/Riverside/speed-sign-v2/`.

The remaining notes describe the historical preview. Its original production-hash check passed before the concurrent installation and correctly rejected the later changed store VMDL.

New model for the compact outdoor ice cabinet beside Lucky Stop's entrance. Built on 2026-11-04 following installation of the approved 54 sandbags. **Not installed.** The production scene and store mesh are unchanged by this candidate.

The old prop is a 38 × 30 × 60-inch box with a flat emissive image: 14 triangles in the store OBJ. The replacement keeps the cabinet footprint and height, with a separate insulated door, rubber gasket, raised illuminated ICE header, three metal hinges with fixing screws, a curved pull, latch/keyhole, recessed compressor grille with individual angled louvres, adjustable rubber feet and folded panel seams. The pull projects a few inches beyond the original box. Original generic lettering and all textures are authored procedurally; no external assets or image generation.

`models/props/riverside/ice_freezer_v2/ice_freezer.vmdl` has 2,616 / 1,464 / 460 triangles in three LODs, switching at 25 and 70. These are authored budgets, not measured frame-time results. One shared 2048 × 2048 atlas provides colour, normal, roughness, metalness, AO and a restricted header glow mask. The painted enamel has restrained rain film, lower dirt/algae and edge wear; hardware uses separate atlas regions. Canonical front is engine +X; the porch placement is position `622,-160,20`, yaw 180 degrees.

## Reproduce

Prefix shell commands with `rtk` in this repository.

1. `python Sources/Riverside/ice-freezer-v2/build.py <project-root>` builds only the private candidate assets.
2. `python Sources/Riverside/ice-freezer-v2/prepare_review.py <project-root>` creates a render-only store copy, removing exactly the 14 old freezer faces in that copy. It snapshots the live store OBJ/VMDL and saved scene hashes. It does not edit production assets or collision.
3. `python Sources/Riverside/ice-freezer-v2/native.py script Sources/Riverside/ice-freezer-v2/review.cs.txt` compiles and loads the models in the existing editor, then creates an isolated render scene. Identical cameras, locked exposure and a temporary inspection light are used for both versions. The scene is destroyed in `finally`. The script also renders the 54 sandbags from the saved public scene, without adding replacements.
4. `python Sources/Riverside/ice-freezer-v2/verify.py <project-root>` checks finite/nondegenerate triangles, winding relative to face normals, nondegenerate bounded UVs, unit normal-map vectors and the protected production hashes.
5. `python Sources/Riverside/ice-freezer-v2/compose.py <project-root>` arranges the matched native screenshots without colour edits.

Evidence: `output/asset-improvement-20261030/riverside-ice-freezer/`. Native compilation loaded both the candidate and comparison background without errors; geometry and preservation checks passed. The initial native inspection exposed mirrored front lettering and a camera inside the nearby drinks fridge; both were corrected before the final comparison. No gameplay or LOD transition playtest has been run.

For a later approved installation, preserve the original simple metal collider, porch point light and all unrelated geometry (including the newly installed drinks fridge and sandbags). Remove only the 14 original ice faces, add this model through the editor and update the narrow canonical generator hook. Do not regenerate the entire map.
