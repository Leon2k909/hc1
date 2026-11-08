# Veridant south garden relief — installed review trial, 2026-11-05

The user requested another subtle ground rise after the earlier map trials. A grass strip in
Veridant's south garden, between the operations building and the gravel cross path, now has a
shallow crown. Plan bounds are E 350..530, N -808..-712, at base Z 0. Maximum rise is 2.5 inches
(6.35 cm). All four edges stay level; the maximum triangle slope is 4.48 degrees. The gravel paths,
building entrances, lamps and other props are outside the changed footprint.

`Tools/veridant_garden_relief.py` generates a separate 528-triangle overlay with one matching static
collision mesh. It reuses `materials/veridant/vr_lawn.vmat`, the original grounds UV phase and
128-inch tile scale. An initial native render exposed per-face UV projection rotating on the
curved surface; explicit flat-ground UVs now preserve the original texture alignment across the crown.

Native editor APIs imported, compiled and loaded
`models/maps/veridant/garden-relief-v1/garden_strip_relief.vmdl` without an error model. Native scene
tools placed one `South garden relief - REVIEW TRIAL` object, ID
`3737efd6-52f6-4e75-a341-743787742825`, with a ModelRenderer and static ModelCollider. The scene was
saved for play-mode inspection. The rise includes a 0.015-inch render offset to avoid coplanar faces.

`output/veridant/garden-relief-v1/` contains a pre-install scene backup, geometry checks, the object
receipt, runtime ground trace and matched native before/after images. This is an installed review
trial, not a canonical map rebuild; the map generator has not been changed to preserve the extra
instance on regeneration. AI routes, navmesh bake and performance remain unverified. Earlier trials
are unchanged, and no Git staging, commit or push was performed.

To reject it, remove the named trial object through native scene tools and save. Keep the backup as
a reference rather than overwriting unrelated scene work added later.
