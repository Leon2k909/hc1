## Orion yard lamp (2026-11-04)

- Single box light beside the yard forklift replaced with an oval cast head, diffuser, gasket, cooling ribs,
  fasteners and attached guard supports. Full original pole and original point-light declaration retained.
- `Tools/orion_map.yard_props` calls `Tools/orion_yard_lamp.py`. Sources and guarded native installer:
  `Sources/Orion/yard-lamp-v1/`. No full map rebuild or scene/lighting changes.
- Remove14 old triangles, add2,984 and preserve102,866 unrelated faces exactly. Full props ModelDoc physics,
  all hull sources and saved scene stay unchanged. Accepted new head is active; old `before.*` files removed from
  game Assets on user request. Rollback copy and receipt: `Sources/Orion/yard-lamp-v1/retirement/`.
- Matched native renders, full-pole map placement, snapshots and checks: `output/orion/yard-lamp-v1/`.
