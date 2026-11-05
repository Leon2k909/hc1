# Sewage crane lower blocks — 2026-11-04

Replaced the two striped boxes and segmented hooks with cast cheek plates, side webs, pulley/bearing covers,
machined rings, hex fasteners, chain guides, load plates and caution bands. A swivel collar carries a smoothly
curved hook with a tapered tip and spring safety latch. Five private materials use authored enamel grain,
roughness/normal maps and readable equipment plates. No external assets or image generation.

Existing suspension chains are retained exactly, including their positions and connection into each housing.
Only the lower-block bodies, old diagonal strips and hooks are removed. The new bodies sit at the original
anchors. No collision, light, gameplay or saved scene changes. The old standalone model remains available as
the inactive `models/maps/sewage/crane-blocks-v1/before.vmdl` alternate; the map uses the new geometry.

`build.py` stages private review assets. The old faces are verified against the published merged model, then
translated with their original UVs, normals and materials preserved. Verified legacy material tile values are
set explicitly, avoiding regeneration of Sewage's material library. Native `capture.cs.txt` renders both
versions with identical camera, lighting and exposure. `context.cs.txt` renders saved Sewage visual roots in a
temporary isolated scene, without switching or saving the user's document or controlling play state.

`prepare_install.py` snapshots inputs, stages a narrow face splice and preserves the full physics suffix.
Native `install.cs.txt` refuses changed inputs and publishes only details OBJ/MTL/ModelDoc and two offline
generator files. Exactly1,440 old faces are removed,26,900 added and38,434 unrelated faces retained, including
all existing chain links. `sewage_map.build` calls `Tools/sewage_crane_blocks.py` inside the original loop;
the chain-generation loop is untouched. Do not rebuild the whole map to apply this asset revision.

Evidence and snapshots: `output/sewage/crane-blocks-v1/`. `before.png`/`after.png` are actual native engine
renders; `context/block-installed.png` shows the public map installation. `verify.py` checks installed hashes,
exact retained faces, full physics, scene/hulls, finite/nondegenerate mesh data and retained generator output.
`check_public.cs.txt` confirms the compiled public model, all five private material bindings and the old
alternate resource. No frame-time benchmark was run. The first review capture observed an external editor/play
state change; later isolated context and installation checks record state independently.

The crane blocks were accepted after the map-placement demonstration. Subsequent salvage-drum work changes
the same merged details resource; its verification confirms all26,900 approved crane faces remain exact.
Use the latest `salvage-drums-v1/verification.json` for the current merged asset's installed hashes.
