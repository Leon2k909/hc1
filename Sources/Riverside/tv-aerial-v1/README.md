# Riverside T2 rooftop TV aerial v1 - installed

Built 2026-11-04 after the Lucky Stop ceiling fittings; installed after explicit user approval in the next turn.

The original T2 aerial is an uncapped pole with five vertically stacked crossbars. The replacement has a galvanized mast,
square aluminium boom, reflector, five progressively shorter directors, folded dipole, insulating saddles, end caps, balun,
connector, coax with a service loop and mast ties, U-bolt clamps and hex fasteners. A rubber boot and bolted flashing follow
the trailer's roof slope. Procedural zinc color, roughness and subtle normal maps show restrained surface mottling.

Five materials. Three LODs: 3,912 / 2,468 / 912 triangles. No physics or runtime component. Mast height matches the old 70-inch
mast; top including cap is local Z 70.3. Roof flashing extends down to meet the actual roof beneath the old floating mast root.
Engine placement `1033.5,794.772208,123`, yaw zero. Plan placement `-794.772208,1033.5,123`, trailer T2, seed 12.

Build: `rtk proxy python Sources/Riverside/tv-aerial-v1/build.py`. Staged sources live under
`output/riverside/tv-aerial-v1/stage/Assets`. `--geometry-only` updates geometry/materials and the existing manifest without
rebuilding the legacy cutout. Import/compile: `review.py import`; native captures: `review.py isolated`, `review.py context`.
Check with `verify.py` and compose with `compose.py`. `prepare_review.py` records the transformation of the proven native
capture template into the checked-in review scripts; it is not needed for normal capture runs.

Resource: `models/props/riverside/tv_aerial_v1/aerial.vmdl`. A private copy of the public lowland mesh removes exactly 52 old
triangles for this single aerial. The real public OBJ, ModelDoc and saved scene remain hash-protected. No full map regeneration.
Native review loads visual roots into isolated worlds/scenes; it preserves the user's active editor scene and play state.
Studio images show small parts, and map images use the original map lights with exposure fixed at 3.5 for both variants.

Receipts, hashes and captures: `output/riverside/tv-aerial-v1/`. Eight native resources compile; geometry checks find no inverted
or degenerate triangles. Installation removed exactly 52 original triangles from the current public lowland OBJ and saved one
native ModelRenderer under `Roof TV Aerials / T2 Rooftop TV Aerial`. The public ModelDoc, every pre-existing scene object,
collision and lights are preserved. Twelve legacy/private-background comparison files were archived outside Assets and deleted
through the editor. The generator substitutes only T2's aerial and consumes identical random choices; default trailers remain
unchanged. `generator-check.json`, `installed.json`, `native-install-compile.json` and `installed-capture.json` record the checks.
Native installed-map screenshots use the actual saved mesh and object, with no background substitution or error models.
Do not rerun the pre-install builder/verifier against the installed map: their old-face guards intentionally reject it.
