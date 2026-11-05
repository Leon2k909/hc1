# Belltower doorway terracotta pot v2

Approved and installed on 2026-11-04 on `codex/belltower-terracotta-pot-v2`.

The old 14-sided, sharp-edged planter is replaced by a wheel-thrown profile with a rounded rolled rim,
subtle asymmetry, small rim nicks, a continuous inner bowl, a drainage hole and a recessed foot.
It retains the existing accepted clay material, soil height, planting position and collision.

`build.py` generates 4,736 / 1,472 / 544 triangle LODs in local temporary staging. Every LOD is a closed
manifold with outward winding. `import.cs.txt` only imports private review assets; it refuses changed
shared inputs. No map generator or shared material was changed.

`review.py compile` checks native compilation. `review.py before` and `review.py after` capture the same
doorway pot with identical camera and exposure settings. The after capture temporarily swaps only the
west visual renderer for a model with exactly the selected 140 old pot triangles removed, adds the
candidate pot at world `514,1862,0`, then restores the model, cameras, tone and scene object IDs.
The original planted bush, soil and physics stay in place. The scene source hash is unchanged.

Native before/after images and restoration receipts are in `output/belltower/terracotta-pot-v2/`.
Three private model compiles passed. The compiled candidate is up to date and unreferenced by the map.
An optional later GPU LOD-count inspection timed out; compiled per-LOD triangle counts were not verified
through that inspection. The counts above are verified from the source meshes.

All twelve pots are now standalone instances in the saved Belltower scene. The two town models no longer
reference their old clay-pot render meshes, and 1,680 old triangles were removed from the canonical OBJs.
All other canonical OBJ bytes, referenced meshes and collision sources are unchanged.
`Tools/belltower_pots.py` and the map generator retain the new placements without renumbering the old
planting objects. The native save preserved the previous scene selection and running game at save time.
It also refreshed engine serialization defaults, resource-reference objects and numeric formatting;
existing authored common-field changes are the same twelve pew resource paths and equivalent rotations.
`stage_install.py`, `install.cs.txt` and the installation receipt document the scoped publication.
