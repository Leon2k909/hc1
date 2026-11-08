# Riverside entrance shoulder — installed review trial, 2026-11-05

The user requested another slight terrain variation. The unpaved shoulder beside the entrance
lane, south of the office and west of the player spawns, now has a broad crown of at most 2.5
inches (6.35 cm). Plan bounds are E -680..-420, N -1080..-800, base Z 96. This is a new location
and treatment; the previously rejected metre-high rise among the low trailers remains reverted.

`Tools/riverside_entrance_relief.py` creates a separate 528-triangle overlay and matching static
collision mesh. It uses the existing mud material, original `riverside_ground` UV phase and explicit
flat-ground UVs at the original 768-inch scale, preserving texture alignment over the curved surface.
The four boundaries remain level, maximum triangle slope is 1.74 degrees, and source checks leave
clearance from the office footprint and westernmost player spawn. No props or existing meshes move.

Native editor asset APIs imported and compiled
`models/maps/riverside/entrance-relief-v1/entrance_soil_relief.vmdl`; it loads without an error flag.
Native scene tools saved one `Entrance soil relief - REVIEW TRIAL` object, ID
`13a337a6-19f4-4b14-a720-5854d391fec7`, with a ModelRenderer and static dirt ModelCollider.
In the running map, a ground ray at world (-940,550) hits the trial at Z 98.515, matching the
raised height plus its 0.015-inch anti-flicker offset. The native before/after pair keeps the same
viewpoint and original night lighting.

`output/riverside/entrance-relief-v1/` retains the pre-install scene backup, geometry checks,
object receipt, runtime check and comparison images. Play mode is left running for inspection.
This is a reversible review trial; the canonical map generator has not been changed to add the
instance on regeneration. AI route/navmesh and performance checks remain unverified. Earlier
trials on other maps are preserved. No Git staging, commit or push was performed.

To reject it, delete the named trial object through native scene tools and save. Treat the backup
as a reference rather than overwriting unrelated scene edits made since installation.
