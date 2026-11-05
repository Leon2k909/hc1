## Sewage crane lower blocks (2026-11-04)

- Two hanging lower blocks upgraded with cast housings, bearing covers, fasteners, chain guides, load plates,
  swivel collars and curved safety hooks. Existing suspension chains and anchors retained exactly.
- `Tools/sewage_map.build` calls `Tools/sewage_crane_blocks.py` after each original chain loop. Sources and
  guarded native installation: `Sources/Sewage/crane-blocks-v1/`. No full map rebuild.
- Targeted splice removes1,440 faces, adds26,900 and preserves38,434 others. Complete details ModelDoc physics,
  all hull sources and saved scene stay unchanged. Old model retained as inactive `crane-blocks-v1/before.vmdl`.
- Matched native renders, installed context, snapshots and verification: `output/sewage/crane-blocks-v1/`.
