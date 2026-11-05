# T2 weathered precast entry steps — installed

Approved weathered revision installed and saved on 2026-11-04. Exactly 48 original box triangles removed from `riverside_low.obj`; every other OBJ line, complete ModelDoc/physics and existing scene object retained. One `Precast Entry Steps` child references `models/props/riverside/t2_precast_entry_v1/entry_steps.vmdl` at engine 955,891.826513,0, yaw zero. No new lights or colliders.

Continuous cast shell, formed nosings, grip grooves and two small chipped corners. Original 40 × 36 × 29-inch envelope retained. LODs 3296/896/68 triangles, thresholds18/45. Private weathered material reuses map cracked concrete colour plus precast normal/roughness unchanged, with earth tint. One new material; no new textures. Initial pale finish rejected and archived under `rejected-clean/`.

`prepare_install.py`, `install-t2-steps.cs.txt`, `verify-install.py` retain exact staging/hash guards and native save. Generator hook affects only T2: retained wedge collision and trailer-info identity passed; no full map regeneration. Native saved model captured under existing map lighting with zero inspection-light contribution, `installed_maplight_whole.png`, visually inspected. It is darker than the temporary inspection-light review. No gameplay traversal or LOD-transition test.

Evidence: `output/riverside/t2-precast-entry-v1/installed/verification.json`, `generator-verification.json`, native captures in the parent output folder. Historical candidate verification/preparation assumes uninstalled state and must not be rerun against the installed map.

Unused old comparison resources archived outside Assets and deleted through editor (9 files); only the installed steps/material remain in use.
