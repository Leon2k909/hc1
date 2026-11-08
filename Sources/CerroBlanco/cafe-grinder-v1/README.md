# Cerro Blanco cafe grinder — native review, 2026-11-06

Rebuilds the grinder beside the accepted espresso machine at plan (600,616), on
the existing 42-inch cafe counter. The former two capped 12-sided lathed shapes
become an eased motor casing on rubber feet and a formed tray, burr housing with
adjustment grip, transparent hopper and closed lid, modelled bean heap with 24
individual beans, front controls, connected dosing chute and portafilter forks.
No brands, lettering, lights, room or inspection settings are added. An audit
found no existing grinder upgrade; existing museum finishes/glass are reused,
with one texture-free brown bean material. Height remains approximately 16 inches.
The base grows slightly in depth for the tray and remains clear of its neighbours.

`build.py` stages a private fitout-fine variant and a standalone render model.
Exactly 128 original grinder triangles are removed, with 4,880 new triangles.
All 67,610 unrelated fitout-fine faces/indices/UVs remain. The installed OBJ has
later appended vertex blocks, so new records are appended after all original
records, preserving their indices. Geometry checks cover finite/unit normals,
nondegenerate outward triangles, bounds and exact unrelated-face preservation.

Native import/compilation succeeded; candidate IsError=false. Only the live
Fit-out Detail ModelRenderer was temporarily changed, then restored to the
public fine model. Public source files, scene, collision, lighting and generator
remain unchanged. The approved hooded bin and red display vase remain installed
in the separate public dressing model. No LOD/frame-time/gameplay test is claimed.

`output/cerroblanco/cafe-grinder-v1/before.png` and `after.png` are matching native
window captures from the actual editor viewport, cropped by `screenshot_game`.
Position (568,-606,62), angles (10,0,0), FOV 80, original lighting/material/display
settings. No Computer Use, temporary camera, isolated scene or RenderToBitmap.

Assets: `models/maps/cerroblanco/cafe-grinder-v1/fine.vmdl` (private packed review)
and `models/props/cerroblanco/cafe_grinder_v1/grinder.vmdl` (render-only local prop).
The user approved the grinder. `installed/` retains the original OBJ/ModelDoc;
native editor APIs replaced its 128 legacy triangles with the 4,880 new triangles
in public fitout-fine and added the bean-material remap. Native compile passed.
The renderer path and scene are unchanged. `cerroblanco_cafe_grinder.py` supplies
the scoped generator replacement in `cerroblanco_fitout.cafe`. The old grinder
is no longer drawn. All unrelated fitout geometry is retained.
