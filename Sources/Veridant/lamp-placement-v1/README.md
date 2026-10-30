# Original lantern placement correction

The user clarified that the lantern design was wanted; the problem was posts
standing in open circulation. The modern bollard prototype was never placed
and has been archived out of the project's active Assets and Tools folders.

All 32 original lantern placements were reviewed against the saved map layout.
Eight retain their original design and move to the locations in
`Tools/veridant_lamp_placement.py`. The remaining 24 keep their placements.

| Lantern | Old plan E,N | New plan E,N | Purpose |
| --- | --- | --- | --- |
| Garden lantern 0 | -600,260 | -686,260 | Beside the sea-side balustrade |
| Garden lantern 1 | -320,600 | -686,680 | Beside the balustrade, beyond the stair opening |
| North terrace lantern 0 | -20,300 | -164,240 | South-west terrace corner |
| North terrace lantern 1 | 130,650 | -92,724 | Beside the pine planter, clear of the bar approach |
| North terrace lantern 2 | 300,520 | 240,580 | To the side of the grand-stair landing |
| East terrace lantern 2 | 820,500 | 410,566 | Beside the western glass railing |
| East terrace lantern near | 930,-150 | 798,-150 | Beside the western terrace railing |
| Promenade lamp 7 | -1690,1020 | -1690,950 | Out of the north boundary wall |

Dimensions are inches. Original floor elevations, fixture geometry, height,
materials, colours, light radius and shadow settings are retained. Each moved
fixture has the same 154 triangles, with the original shape translated only.
The placement hook in `veridant_parts.lantern_post()` applies the same named
locations when regenerating the map.

The scoped correction changes five installed files:

- The active buildings and dressing base OBJs: exactly 1,232 old lantern faces
  are replaced by translated copies. All other bytes and indices remain.
- The two metal collision OBJs: only the vertices of the corresponding 16
  connected hulls move; every other collision line is retained.
- The saved scene: only the eight matching point-light Position values change.
  Object identities and all other scene properties remain.

Current VMDLs, all other render imports, the unused canonical map OBJs and the
original steel/lens materials retain their hashes. No complete map regeneration
was run. Backups and the publication manifest are under
`output/veridant/lamp-placement-v1/stage-v2/`.

The editor was closed at publication. `veridant_install_lamp_placement.py` checks
that no editor is running, verifies every source/target/backup hash, and uses
atomic replacements. `validation-installed.json` confirms the published files,
exact translated shapes, aligned light sources, physical floor support, and no
intersections against the saved map's 467 collision boxes and 238 hulls.
**Native compilation and an in-editor visual check are still pending.**

Do not place the rejected modern bollard. Its recoverable archive is
`output/veridant/modern-lamp-v1/rejected-prototype/`.
