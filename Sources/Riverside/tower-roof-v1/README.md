# Riverside guard-tower corrugated roof v1 - installed

Rebuilds the flat four-triangle roof as four overlapping formed metal sheets with thin edges, folded perimeter flashing,
washered hex fasteners, three timber purlins and two tapered bearers. Fits the existing tower posts at Z620; roof origin
is engine 1600,530,628, yaw -163.3007557660064. The original 136-inch footprint and shallow pitch are retained.

4676 / 3156 / 468 triangles, thresholds 25/60. Model models/props/riverside/tower_roof_v1/roof.vmdl. No new physics.
Reuses Riverside roof color/roughness, timber/dark materials and Lowtide steel. A dedicated sheet.vmat uses a neutral normal
and roughness scale 1.2 because the corrugation is now geometry; shared materials and images are unchanged.

Checked existing approved resources, source notes, pending candidates and active model chats before selection. No existing
replacement canopy was found. Leaves the approved guard-tower ladder, water vessel, searchlight/beam and structure untouched.
The rejected full water-tower candidate B remains deleted.

Run build.py to stage, review.py import for native resource writes/compilation, verify.py for resource/hash/geometry checks,
review.py isolated and review.py context for matching native before/after renders, then compose.py. Scripts use the existing
editor connection and disposable render scenes. The preview never writes the saved map. The private dressing copy removes
only four fingerprint-matched original roof triangles and must never be installed as the public dressing model.

Approved and installed on 2026-11-04. Removed exactly four original roof triangles from the active public dressing input,
saved one native renderer under Guard Tower Roofs, and added the narrow generator hook. Existing tower physics, posts,
deck, ladder, lights and beam are preserved. Native saved-map capture reports no error models and preserves editor state.
All three LODs compile. Original and private comparison resources (12 files) were removed from Assets; installation receipts
and a retired-review archive remain outside Assets in output/riverside/tower-roof-v1/.

User requests future improvements focus on props visible to players up close, avoiding roofs or similarly inaccessible details.
