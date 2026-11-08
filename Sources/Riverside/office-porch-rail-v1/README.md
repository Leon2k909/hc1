# Riverside office porch railing - review candidate

Player-visible replacement for the office porch's300 original render triangles. No change to the porch deck, awning posts/roof, steps, lighting or collision. Existing approved metal railing models were unsuitable for this timber porch; new geometry reuses approved Riverdale pallet timber and Riverside rust/dark materials. No new materials/textures. Whole/detail/context native captures use matched camera and locked exposure with existing map lights and zero inspection fill; both resources valid. Whole/detail visually inspected.

The new rail has an eased cap, bottom stretcher, chamfered end posts, visible washer/bolt and nail joints, slightly imperfect balusters and two jagged snapped balusters. Grain is explicitly mapped lengthwise per member, replacing the original compressed board texture. No new lights/colliders/runtime components. Three LODs2552/1496/408 triangles, thresholds18/45. Resource `models/props/riverside/office_porch_rail_v1/rail.vmdl`, engine origin -500,692.767076,124, yaw0, renderer tint0.55,0.55,0.55. Main envelope160 inches long,36 high,3.8 deep. Original structural awning posts stay.

`build.py` reconstructs only the original office rail and fingerprints its exact300 current pad triangles into a private cut background, without regenerating the map. It builds three candidate LODs and protects public source/ModelDoc/material hashes. `verify.py .` checks geometry/winding/UV/public assets and absence from saved scene. `review-office-rail.cs.txt` renders a disposable scene and destroys it in finally. `compose.py .` arranges screenshots without image alterations. Prefix every shell command with rtk.

Not installed. Later integration needs user visual approval, exact300-face removal from current pad source, original collision preserved and a narrow office-only retained generator hook. Private background must never replace the public pad model. No gameplay/LOD-transition benchmark.

Evidence `output/riverside/office-porch-rail-v1/`. Previous shed-downlight approval was installed and its old comparison resources retired separately.

User requested a different prop after seeing this preview. Leave this railing uninstalled; no approval to integrate it.
