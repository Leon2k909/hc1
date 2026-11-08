# Veridant north terrace bar stools — applied review, 2026-11-06

Accepted on 2026-11-06 with the old version removed from use. The unreferenced
pre-stool base OBJ and its metadata were retired outside Assets; retirement.json
records the hashes and confirms no scene/prefab/ModelDoc referenced them. The new
stool import and regeneration code remain active. Previously retained original
umbrella and light props are unaffected. Do not restore the obsolete base path
or run historical imports from before retirement without deliberately rebasing.

The user accepted the new umbrella and requested its original be retained, then
asked for another improvement. The original umbrella is a valid separately
compiled floor-centred prop at
`models/props/shared/terrace_umbrella_original_v1/umbrella_original.vmdl`; the new
cloth canopy remains installed on Veridant.

The four solid-cylinder stools at plan E=90,140,190,240 / N=690 / floor Z=128
are replaced with pedestal stools. They have shallow shaped walnut seats with
eased rims, slim metal stems, weighted bell bases, footrest rings and three ring
supports. Each retains its original 12-inch diameter footprint, 28-inch height
and centre placement. Materials are the existing vr_steel and vr_timber_dark.
Explicit UVs keep the seat grain coherent across the shaped top.

The scoped patch removes 112 original triangles from a copy of the latest active
base and imports 11,416 replacement triangles. Every unrelated record/index,
other render import and the complete physics suffix remain unchanged. Lighting,
scene and post-processing are unchanged. Earlier accepted banner, reception light,
stair rail and umbrella remain active. The four original generators are replaced
only in north_block by Tools/veridant_terrace_stools.build_one.

`build.py` stages; `prepare_import.py` imports through native editor with guards;
`verify.py` checks finite vertices, unit normals, nondegenerate triangles, original
dimensions, retained records and physics. The loaded Buildings and Dressing models
report IsError=false; the scene has no unsaved changes and play state remains stopped.

Actual displayed editor frames with the same existing camera/settings:
`output/veridant/terrace-stools-v1/before.png` and `after.png`. No temporary camera,
isolated scene, RenderToBitmap or lighting/exposure changes. Stage, backups and
verification are in that output directory; historical imports must not overwrite
newer edits without a deliberate baseline refresh.
