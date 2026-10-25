# Physical shop displays

The replacement is built and staged; it has not been installed in the live map.
The editor connection was lost before the first publication began. The existing
shop materials and scene were inspected afterward and no display changes had run.
No editor was launched, closed or restarted by this side task.

`Tools/belltower_shop_displays.py` builds actual recessed shelves, timber backing,
green and amber bottles, labelled stoneware jars, tins and folded paper parcels.
The eighteen existing shop apertures receive clear glazing. The exterior frames,
town meshes and gameplay collision stay in place.

The final asset set is `output/belltower/shop-displays/stage-v4/manifest.json`.
It contains thirteen files and a visual-only 92,504-triangle supplemental model.
`construction-preview-v3.png` beside the stage folders is a Blender construction
preview of the same OBJ bytes as stage-v4. Its surrounding facade/frame are a
context fixture, and its lighting is not an engine capture.

## Finish in the editor

1. Attach through the engine-provided sbox CLI. Begin with editor_status, confirm
   the canonical C: project, and inspect scene, play state, compilation and unsaved
   changes. Do not interrupt another active editor task.
2. Recheck all stage-v4 before hashes, source guards and the current aperture
   positions. If shared town inputs changed, inspect the differences and stage
   a fresh revision; do not weaken the guards or overwrite newer work.
3. With stopped, saved Belltower selected, run the method-body script
   `Sources/Belltower/editor/import-shop-displays-v1.cs.txt` through run_csharp in
   the native session exchange directory. It publishes only the reviewed files
   with backups and before-hash checks. It does not add a scene component.
4. Compile the ten materials and supplemental model through asset_compile. Check
   diagnostics and loaded asset status before altering the scene.
5. Verify the existing Town object a1a79f42-a954-5c76-ba78-52cfa046e461 still has an
   identity transform. Add one ModelRenderer using
   models/maps/belltower/shop-display-v1/shop_displays.vmdl with attachments off.
   Reuse any already installed display renderer instead of adding a duplicate.
   Do not add a collider. Save the scene through save_scene.
6. Apply only the small integration.patch to the two existing Python generators.
   It keeps later material/town regeneration consistent. Do not copy the whole
   files from output/wiring-proposal over newer shared source files.
7. Capture at least one wide and one narrow shop at two viewing angles. Confirm
   the clear glass, material loading, shelf depth and contact shadows in s&box.

When a later full town regeneration embeds the display builder in its meshes,
remove the supplemental ModelRenderer through the editor to avoid double geometry.
The original shop photo assets are preserved for rollback.
