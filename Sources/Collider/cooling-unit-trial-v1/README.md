# Collider cooling unit — accepted and installed, 2026-10-30

The user approved the refined image and requested replacement of the old unit.
Exactly 170 old render triangles are removed at the reviewed placement and the
45,890 approved triangles inserted. The machine source now has 182,141 triangles
(was 136,421). Fourteen private material bindings are added; approved positions,
UVs and normals match exactly. All unrelated original face lines and attribute
tables, material bindings, saved scene, other packed model sources and previously
approved private sources remain unchanged. The original absence of authored
collision is retained. Other cooling-unit placements are unchanged.

`Tools/collider_cooling_unit.py` and `collider_map.cooling_unit` retain the exact
reviewed mesh on regeneration. Old standalone before resources are removed from
Assets; rollback and scope checks are at `output/collider-cooling-unit-accepted-20261030/`.
Newer/different primary staged machine sources were preserved. `installed.json`
and `verify_accepted.py` record/prove integration. Older whole-machine hashes in
previous acceptance receipts are historical; this receipt proves their assets
are preserved. No editor used; native compilation, appearance, LODs and performance
checks remain pending. The text below describes the historical proposal.

After approving the control console, the user requested its old resources removed
and another asset improved. This proposal selects the actual cooling unit in the
machine hall at plan **(-1470, 1702, 20)** (the local model origin, not its centre).

`build.py` matches and copies **all 170 original triangles**, including exact saved
UVs, normals and materials, from `collider_machine.obj`. The original is a rectangular
housing, eleven flat vent strips, a screen and its bezel/status block. The candidate
is a separately authored mesh in private model/material directories. No packed map
model or scene is edited. Original assets remain until the user approves.

The new unit has six recessed fan cartridges with genuinely open apertures, curved
closed blade shells, deep motors, radial supports and independent wire guards. It
adds a side fin/heat-exchanger bank, pipe headers, service covers, slotted screws,
pressure dials, status lenses and identification plates. Separate coating, blackened
blade, brushed metal and pipe materials use fine physical grain, nicks and variable
roughness. The original active display size (56 × 28 inches), placement and telemetry
atlas quadrant are retained. No collision is authored by either variant.

The first internal render is archived outside Assets under `revisions/first-pass/`.
Visual QA refined the header clearance and ensured the control lenses, gauge cases
and warning plates attach to their backing panels. The final public after image is
`after-refined.png`. The original image is reused only after its mesh hash, image
hash, camera, scale, ground and render settings have been checked unchanged.

The original housing starts twenty inches above the map floor. The replacement adds
levelling feet to the actual ground plane, retaining the existing body envelope.
The comparison floor is at the same actual plan height **z=0** for both variants,
not moved separately to conceal that gap. All four packed Collider model source sets,
the scene and previous approved private asset sources are guarded by SHA256.

`verify.py` checks source scope, dependencies, finite attributes, winding and
degenerate triangles, screen UVs and closed consistently oriented fan-blade shells.
The thin exchanger fins use economical closed boxes; unnecessary tiny bevel geometry
was removed. LOD generation and native performance validation are pending.

Run with `rtk proxy python -X utf8`, in order:

1. `Sources/Collider/cooling-unit-trial-v1/build.py`
2. `Sources/Collider/cooling-unit-trial-v1/verify.py`
3. `Sources/Collider/cooling-unit-trial-v1/prepare_render.py`
4. `Sources/Collider/cooling-unit-trial-v1/render_low_impact.py`
5. `Sources/Collider/cooling-unit-trial-v1/finalize_review.py`

The wrapper runs one Blender process at Windows idle priority, confined to two
logical CPUs, using two Cycles CPU threads and no GPU rendering. It collects the
process before finishing. No editor, browser, server or background compiler is used.
The two 1050 × 1400 images share the camera, lights, physical scale, exposure and
settings. They are actual-source-mesh renders, **not engine screenshots**.

Evidence: `output/asset-improvement-20261030/cooling-unit/`. In-engine import,
appearance, LODs and performance remain pending. Do not install this proposal or
delete the original until the user approves this particular replacement.
