# Railhead taxi-rank head sign — review candidate

Selected after an existing-upgrade audit. Project asset/source/status/note and historical-output searches found no newer taxi-rank post. The `rw_taxi_sign`/`railhead_furniture.taxi_sign` variant is a car roof lamp, and Riverside's installed speed-limit sign is a different single-sided sheet on a perforated channel. Existing planter, speaker, chair and inspection-cover upgrades were excluded. Audit receipt: `output/railhead/taxi-post-v1/existing-upgrade-audit.json`.

The east rank-head post at plan (1488, 1180, 0) keeps its 102-inch height, 24.4 × 12.6-inch panel outline and unchanged blue Taxi artwork on both faces. The proposal adds a smooth stainless pole, formed weather cap, anchored foot, split collars with lugs/bolts, rounded rolled-edge double-sided cassette, edge rivets and underside straps. The cassette is thick enough to enclose the pole rather than letting the old thin slab intersect it. No new artwork, material/texture files, glow or lights; the existing sign atlas and finishes are reused.

4,472 render triangles replace 124 in a private copy of the live `cable-drum-v1/east_without_drum.obj`. Every unrelated face and vertex/UV/normal record, approved ashtray/pallet/reel/barrier/extinguisher imports, public ModelDoc physics and saved scene remain unchanged. The original thin post collider is retained in the private background; the candidate adds no collision. The small anchor flange changes the visible foot only. Other taxi signs remain unchanged. Public installation awaits approval. No performance benchmark or full-map regeneration.

From the canonical checkout, waiting for each command to finish:

```powershell
rtk python Sources/Railhead/taxi-post-v1/build.py
rtk python Sources/Railhead/taxi-post-v1/setup.py
rtk python Sources/Railhead/taxi-post-v1/review.py
rtk python Sources/Railhead/taxi-post-v1/verify.py
```

`--candidate-only` rebuilds just the candidate after checking the live-base hash. Editor imports/compiles private preview sources. Actual offline play uses a player, copied gameplay effects, matched camera/exposure and 180 ordinary streaming frames per view, with no added lights or forced texture residency. Front, rear and whole-post views are captured. Only the task's play session is stopped and the prior editor scene/play/dirty state restored.

Evidence after successful verification: `output/railhead/taxi-post-v1/{sign,whole,rear}-comparison.png`, `validation.json`, `runtime-review/checked.json` and `play-state-restored.json`. Inspect all actual final images before claiming the in-game check passed.
