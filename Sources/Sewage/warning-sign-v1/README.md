# Sewage warning sign model v1

Replaces the foreground warning board's paper-thin silhouette with a solid metal backing, chamfered folded rim, six washers and hex-head fasteners, two rear channels, and four saddle clamps around the existing handrails. Original lettering, sign UVs, position, other signage geometry, collision and saved scene are retained.

`Tools/sewage_warning_sign.py` authors hardware in Sewage plan coordinates. `Tools/sewage_map.py` calls it for the warning face, so later staged map generation retains the geometry. This work does not rebuild the map.

`build.py` stages an additive splice onto the published signage model. It checks that all 140 existing triangles survive exactly and that all 3,700 added triangles are finite and non-degenerate. The shared signage model totals 3,840 triangles. There is no added collision or runtime component.

Native workflow: use `native.py script import.cs.txt`, compile the before/after models, then `native.py script capture.cs.txt`. Captures deserialize only visual scene roots into an isolated scene, use matched cameras and lighting, and destroy that scene afterward. Neither the active editor scene nor the running game is switched or stopped. `install.cs.txt` refuses installation if the published model changed since the snapshot.

Review captures, original asset snapshots, hashes and reports are in `output/sewage/warning-sign-v1/`. The close pair shows the front rim/bolt detail; the rear pair shows channels/clamps. Existing source texture artwork is reused; no AI image generation was used for this model change.
