# Ares automatic sliding doors

The two middle hall-to-wing openings use `Facepunch.AutomaticSlidingDoor` with
moving model colliders. Their 224 x 176-inch openings have 114 inches of leaf
travel. The scene instances and `Tools/ares_sliding_doors.py` generator hook
keep the same model path, controller, GUID and collision across rebuilds.

After the initial plain leaf was rejected, its render geometry was replaced
with the existing `Tools/ares_pressure_formed.py` pressure-door design: formed
panels and channels, recessed service grips, worn edges, kick plates and the
orange wheel. Both faces are detailed. That original pressure door was a sealed
hatch; these panels use the existing automatic sliding behavior. Nine existing
`materials/ares/pressure-doors-v3/` materials are reused. Its pressure-lock
lettering is omitted on these passage doors.

`Tools/ares_sliding_pressure_leaf.py` generated and installed the adaptation,
preserving the old ModelDoc physics suffix and the entire saved scene.
`Tools/ares_clean_pressure_leaf.py` removed four triangles that collapsed during
OBJ coordinate rounding. Each final leaf has 34,468 triangles. Backups and
`installation.json` are under `output/ares/sliding-pressure-leaf-20261031/`.
`Tools/ares_verify_pressure_leaf.py` verifies both instances and their model
references, all nine materials, nondegenerate geometry within the original
collision, and closed/open clearance. No native appearance, frame-time or
multiplayer playtest has been performed for this revision.
