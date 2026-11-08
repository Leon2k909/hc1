# Courtyard planter lights — unused alternative, 2026-11-06

User requested original lights remain active in Veridant. Removed the dedicated
housings scene object and generator hook. New source and compiled model remain
at models/maps/veridant/planter-lights-v1/housings.vmdl for future use. This asset
is a paired map-space housing overlay; it does not include the original lenses
or point-light components.

Added beveled recessed housings and two downward-facing metal louvres to each
of the two existing planter wall fixtures at plan (316,220,12)/(316,258,12).
Original emissive panels, dark frames and point-light settings remain. Original
fixtures are not removed. 96 added triangles, existing vr_steel, no collision.

Source Tools/veridant_planter_lights.py. Model compiled through the native editor
and loads without error. Original lights restored and scene saved.
Matching actual displayed viewport captures: output/veridant/planter-lights-v1/
before.png and after.png. No temporary cameras or lighting/display changes.
