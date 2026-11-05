# Riverdale north-lane cable reel — installed

Approved and installed 2026-11-04. The public yard OBJ has exactly the reviewed 300 body/hub triangles removed; the scene contains one native-serialized instance of the existing Railhead model at the approved transform. No replacement geometry or materials were copied. `native-install.json` and `before/` in the output folder retain the receipt and rollback. `riverdale_yard.cable_reel` omits only this body's turned geometry while preserving the tail and prop registration. `riverdale_map.write_scene` appends the native instance through `Tools/riverdale_shared_reel.py`. All other scene data is unchanged. The subsequent cone review also captures the saved installed reel in actual play.

The crude reel at plan (60,2420) is previewed with the existing approved Railhead cable reel, `models/maps/railhead/cable-drum-v1/cable_drum.vmdl`. No new replacement mesh, material or texture was created. The approved original timber finish is unchanged. Orion's larger reel was considered but has map-specific labeling.

The shared model is scaled axially by 28.8/30.8 and radially by 40/47.2 to match Riverdale's old timber envelope. Engine position and scale are recorded in `output/riverdale/shared-reel-v1/placement.json`. It is authored about Railhead's map coordinates, so its world translation compensates for that offset.

Exactly 300 old body/hub triangles are removed from a private preview copy of `riverdale_yard_props.obj`; all 176 triangles of the original loose cable remain. Every vertex, UV and normal record stays unchanged. The preview ModelDoc differs only in its render source filename. The saved scene, original sources, colliders and all other reels remain unchanged.

`build.py` creates the isolated preview outside Assets, using exact material/vertex face matching and source guards. `review.py` imports those three preview files through native s&box, incrementally compiles only the preview base, then runs actual offline Riverdale play. It swaps runtime renderers, reuses the existing reel resource, copies gameplay camera effects, matches exposure and waits 180 ordinary streaming frames per view. No additional lights or forced residency are used. Both checked views show the body and preserved cable fitting together. One initial capture was interrupted when another editor operation switched scenes; that attempt did not produce the review result. The successful capture restored the clean, stopped Riverside editor state it started from.

`verify.py` checks original and reused source hashes, exact body removal, preserved cable, all unrelated geometry, ModelDoc preservation, actual map/player/error-model evidence and editor restoration. Evidence and matching comparisons are under `output/riverdale/shared-reel-v1/`.

The earlier Railhead taxi-rank sign remains staged.
