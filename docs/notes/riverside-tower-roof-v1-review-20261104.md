# Riverside guard-tower roof v1 - installed

Four overlapping corrugated sheets, folded edge flashing, washered fasteners and fitted timber bearers/purlins replace the
flat roof in an isolated review. 4676 / 3156 / 468 triangles; no collision. Reuses existing textures through a dedicated sheet
material with neutral normal, avoiding the original normal map doubling the geometric ribs. Shared materials are unchanged.

Source/workflow: Sources/Riverside/tower-roof-v1/README.md. Model models/props/riverside/tower_roof_v1/roof.vmdl.
Engine 1600,530,628, yaw -163.3007557660064. Original roof was four fingerprint-matched triangles. Approved and installed;
approved ladder, searchlight/beam, water vessel and tower structure are preserved. Existing assets and active chats checked
before selection. Work/validation/native receipts and matching views: output/riverside/tower-roof-v1/. installed.json records
one saved renderer, four removed original triangles, preserved source ModelDoc/physics/lights and 12 retired comparison files.

Final checks: all four resources compile; all LODs have zero degenerate or inverted triangles. Imported resource and protected
source hashes pass. Matching studio and map captures report no error models and preserve the active editor scene/play state.
Top and underside images were inspected; purlins sit below the sheets and bearers meet the existing posts. Saved-map installation
was recaptured successfully with no error models. Generator removes only the old roof; original collision and searchlight match.
Future work should focus on close-range props players see, as requested by the user.
