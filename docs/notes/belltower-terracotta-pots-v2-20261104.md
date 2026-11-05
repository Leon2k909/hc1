# Belltower terracotta pots v2 — installed 2026-11-04

The user approved the matched before/after comparison. All twelve doorway pots now use
`models/maps/belltower/terracotta-pot-v2/terracotta_pot.vmdl`, with 4,736 / 1,472 / 544 triangle LODs.
The existing clay material, soil, shrubs, placement and collision are preserved. Both town models compiled.

The native install saved one new group, `Doorway flowerpots`, preserved existing scene object IDs,
and removed the old clay render imports and 1,680 old canonical triangles. Other canonical OBJ bytes,
referenced mesh sources and physics remain exact. The native scene save refreshed new engine default
fields, resource-reference representations and rotation number formatting. Existing authored common
values remain equivalent. The previous selected document and running game were preserved at save time.

`Tools/belltower_pots.py` and `door_pot`/`write_scene` in `Tools/belltower_map.py` retain the new instances
without changing old planting indices. `Sources/Belltower/terracotta-pot-v2/` holds the builder,
review/import/install scripts and `installed.json`. Captures are in `output/belltower/terracotta-pot-v2/`.
