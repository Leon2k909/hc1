# Riverside trailer-yard edge — installed review trial, 2026-11-05

Following the user's instruction to choose an appropriate location, a shallow crown now raises
the open yard between the low trailers by at most 1.5 inches (3.81 cm). Plan bounds are
E -1130..-900, N 1690..1870, base Z 0. The four boundaries remain level; maximum triangle
slope is 1.58 degrees. The area clears trailer steps, the barrel and the main cross lane.
The earlier rejected large mound remains reverted.

`Tools/riverside_trailer_yard_relief.py` builds a separate overlay. Mud uses the original
ground UV alignment. Clipped, subdivided grass triangles preserve the original patch coverage
and interpolated UVs, following the same rise while retaining their small original height offset.
The render mesh has 3,564 triangles and a matching static dirt mesh collider. Existing meshes
and props are unchanged.

Native asset APIs imported and compiled
`models/maps/riverside/trailer-yard-relief-v1/trailer_yard_relief.vmdl` successfully. Native scene
tools saved `Trailer yard relief - REVIEW TRIAL`, object ID
`93af2e40-45e0-4685-b5ec-f1a12215e1bd`, with ModelRenderer and static ModelCollider.
A runtime ground ray at world (1780,1015) hits this object at Z 1.6559601 (grass surface).
The comparison images use the same camera and original map lighting. Play is left running.

`output/riverside/trailer-yard-relief-v1/` contains geometry checks, matched before/after images,
the pre-install scene reference, object receipt and runtime check. This is a reversible installed
review trial; the canonical generator does not yet recreate it. AI navigation and performance
have not been tested. Previous terrain trials are preserved. No Git staging, commit or push.

To reject the trial, delete the named object through native scene tools and save. Do not restore
the whole reference scene over later unrelated edits.
