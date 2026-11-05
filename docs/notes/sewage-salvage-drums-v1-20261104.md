## Sewage salvage drums (2026-11-04)

- Six coarse cylinders replaced with detailed salvage overpacks, adapting the frozen Boxyard drum v2 mesh and
  freshly painted olive/oxide finishes. Old size, cover positions and original cylinder collision retained.
- `Tools/sewage_map.build` calls `Tools/sewage_salvage_drums.py`. Sources and guarded native integration:
  `Sources/Sewage/salvage-drums-v1/`. Existing Boxyard assets are unchanged; no whole Sewage map rebuild.
- Remove9,984 faces, add37,524, retain55,350 others exactly, including all26,900 approved crane-block faces.
  Full details ModelDoc physics, all hull sources and saved scene remain unchanged. Old drum kept as an alternate.
- Matched native renders, map-placement views, snapshots and verification: `output/sewage/salvage-drums-v1/`.
