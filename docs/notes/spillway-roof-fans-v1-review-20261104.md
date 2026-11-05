## Spillway rooftop extractor fans — installed, old retained (2026-11-04)

- Accepted rebuild of seven fan tops: three above the west turbine hall, four atop the east service tower.
  Seven swept pitched blades, rolled housing, motor hub, domed welded guard, clamps, mounting bolts and lifting eyes.
  Four private PBR materials. No external assets or generated imagery. Exact old roof unit footprints retained;
  fan height grows from 7.5 to 14.8 inches. Existing curbs, louvers and all collision remain unchanged.
- Installed through the guarded native editor route; public models and generator use the new fans. Narrow splices remove
  4,062 west / 5,416 east triangles, add 52,164 / 69,552, and retain 54,678 / 48,556 unrelated faces exactly.
  Full ModelDoc physics, all hulls and saved scene are unchanged, including accepted wall vent and waterline work.
- User explicitly requested retaining the old assets. Keep all `before.*` comparison sources and the reusable alias
  `models/maps/spillway/roof-fans-v1/legacy_fan.vmdl`. Frozen original generator handles both old sizes. Receipt:
  `Sources/Spillway/roof-fans-v1/review/retained-variants.json`.
- Sources, native import, guarded installer, matched before/after and roof placement images:
  `Sources/Spillway/roof-fans-v1/`. Evidence and snapshots in local `review/` on C: to avoid offloaded output writes.
- All four review models compiled and loaded; no error models in placement views. Finite/nondegenerate geometry,
  exact retained faces, bounds, material bindings and hashes checked. Isolated native captures destroyed temporary
  scenes and preserved the active clean Riverside document and stopped play state. No envmap bake or FPS benchmark.
