# Reef Hall Rotunda curved stairs and rails — approved by the user and kept, old geometry and backups deleted, 2026-11-06

Replaces the Rotunda's two curved flights (26 wedge blocks each, a flat brass strip per tread, square-post rails) with
`rotunda_stair_ne/nw.vmdl` (`Assets/models/props/reefhall/stairs_v1/`): slate treads with chamfered nosing and recessed risers,
brass anti-slip strips, 4 in kerbs with plinth/panel/stringer faces, a closed end wall, and the approved glass balustrade
of the straight stairs wound on the helix (inner full length, outer 22 steps like the old rail). Existing materials only.

- Triangles per flight LOD0/1/2: 7,458 / 4,832 / 1,752 (0 degenerate). Old: 1,716 triangles in the room mesh (both flights); room mesh 10,668 -> 8,952.
- Collision unchanged: generator keeps step and rail hulls (`equiv_check.py`: identical in every room); 753 rays identical before / after / reverted.
- Scene objects "Rotunda Stair NE/NW" under Aquarium at world origin; generator flag `RS.ROTUNDA` in `Tools/reefhall_stairs.py`.
- Pictures: `output/model-trial-20261106/reefhall_rotunda_stairs/pair_rot_*.png` (native editor captures, same cameras), `pair_reverted_*` prove the revert.
- Revert was tested before approval. `old/` and `stage/` deleted on approval, so `revert.py` no longer works.
- Not done: filter-hall steel stairs and tunnel steps are separate follow-ups.
