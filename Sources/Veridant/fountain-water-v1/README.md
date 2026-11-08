# Forecourt fountain water — applied review, 2026-11-06

Added a shallow water surface at Z=17.5 above a stone liner at Z=14.05 inside
the original circular fountain. Both annuli span R=10.05..83.65 around plan
(1600,150), clear of the central pedestal and inside the accepted coping.
Reuses the existing approved vr_pool water shader/material and pool-v2 liner.
No materials, lighting, original geometry, collision or routes are altered.
Original black base remains underneath. Total 512 added triangles; no collision.

Source Tools/veridant_fountain_water.py. Map build hook emits liner into Dress
and surface into Water. Current scene uses two dedicated model objects,
Forecourt fountain liner / Forecourt fountain water, imported and compiled
through the native editor. Original assets remain for restoration.

Matching displayed viewport captures: output/veridant/fountain-water-v1/
before.png and after.png. Both visually verified; no offscreen render or changed
lighting/display settings. Water uses the existing animated normals, so its
instantaneous ripple phase differs naturally between captures.
