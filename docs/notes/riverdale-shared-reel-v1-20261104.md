# Riverdale shared cable reel — staged review, 2026-11-04

Update: approved and installed 2026-11-04. Public OBJ now omits exactly 300 old body/hub faces and the scene has one native-serialized instance of the shared Railhead resource. All unrelated scene data is unchanged. The existing loose cable and colliders remain. Targeted regeneration hooks are in `riverdale_yard.cable_reel`, `riverdale_map.write_scene` and `Tools/riverdale_shared_reel.py`. Receipt/rollback: `output/riverdale/shared-reel-v1/native-install.json` and `before/`.

Reviewed the north-lane reel at plan (60,2420). After auditing existing upgrades, reused the approved Railhead cable reel resource without copying or regenerating replacement geometry or materials. It fits the original 40-inch diameter and 28.8-inch timber width using the transform in `output/riverdale/shared-reel-v1/placement.json`. The unchanged Railhead model has separate timber boards, an open axle bore, fastening hardware and continuous cable windings.

Only the private preview base removes the old 300 body/hub triangles. All 176 loose-cable triangles remain, as do all other geometry, collision, saved scene and original/reused source files. Checked in actual offline Riverdale play, with a player present and no error models, matching camera/effects/exposure and normal texture streaming. The successful review restored the editor's prior clean, stopped Riverside state.

Before/after: `output/riverdale/shared-reel-v1/reel-comparison.png` and `detail-comparison.png`. Audit, source guards and validation receipts are beside them. Reproduction: `Sources/Riverdale/shared-reel-v1/README.md`. Awaiting approval; not publicly installed. Previous Railhead taxi-rank sign remains staged too.
