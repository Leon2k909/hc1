## Spillway's yard hose v2 (`hose_coil_v2`, 2026-11-03, validation 2026-11-04)

- Installed after approval of the matched s&box comparison. The original was three closed five-sided rings with visible segment joints,
  930 triangles. The replacement is one continuous 2.65-turn coil with loose ends, hollow cam couplings, ferrules, folded arms, retaining
  rings and worn rubber. Roughly 51.6 ft along the centreline, 2.4 in outside diameter, with a faded yellow identification wrap.
- Model: `models/maps/spillway/hose_coil_v2/hose_coil.vmdl`. 16,132 / 8,066 / 2,818 triangles at LOD thresholds 30 / 80; one 2048 atlas.
  The cost is substantially higher than the old rings. Local bounds X -23.49..25.51, Y -49.57..48.78, Z .05..3.85 in.
- The scene adds only `Yard Hose`, one renderer under `Spillway`, position `-1080,-90,0`, no rotation and no collider. The cargo OBJ loses
  exactly the 930 hose triangles; all other lines and all physics hulls are retained. `cargo_yard()` no longer draws the rings and
  `scene()` places the replacement, so regeneration retains it. The map generator was not rerun.
- Installed while the editor was closed by guarded `Sources/Spillway/hose-coil-v2/install.py`. It refuses changed review inputs, duplicate
  placement, existing backups, or an open editor. The scene matches its backup after removing only the new object.
- Validated natively on engine 26.11.03a: cargo model compiled, one valid hose, no new collider or error models, three floor rays at
  the hose/ends hit Ground at z 0, two installed renders checked. No match playtest. The active Railhead document and play state were
  preserved. Twelve temporary hose comparison files/caches were archived; shared `models/compare_old/hidden.vmat` retained.
- Sources and reruns: `Sources/Spillway/hose-coil-v2/README.md`. Captures, validation receipts and pre-install backups:
  `output/asset-improvement-20261030/spillway-hose/`, with backups under `retired/`. Nothing committed.
