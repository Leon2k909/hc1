# Veridant: remove transport cases from the map

Removed all 82 black and olive transport cases (21 in buildings, 61 in dress)
and their exact corresponding PhysicsShapeBox entries. Both parent models compile.
The twelve dedicated case render imports are detached from the map, while their
OBJ/MTL files, materials, textures and reusable generators remain intact. All other
imports and collision entries are retained. The saved scene is unchanged.

`Tools/veridant_map.py` deliberately omits transport case placements. Its argument
expressions still evaluate, preserving the layout generator's RNG consumption.
`veridant_parts.hard_case` and `case_stack` remain available for other maps.

Publication guards, original document backups and validation are recorded in
`output/veridant/remove-cases-20261105/`. The native editor published and compiled
the two model documents. Before/after captures use matching poses and settings in
an isolated editor scene, destroyed after each capture. Ridgeback's active editor
scene and play state were preserved. Images are in
`output/veridant/quality/remove-cases-20261105/`.
