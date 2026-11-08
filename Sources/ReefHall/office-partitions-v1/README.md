# Reef Hall control-room office glass walls — approved by the user and kept, old geometry and backups deleted, 2026-11-06

Replaces the office's two glass walls (4 in square posts, flat bars, 1-sided glass planes, square jambs) with
`office_partitions.vmdl` (`Assets/models/props/reefhall/stairs_v1/`): floor channel with steel cap, transom rail, head channel
with lip, slim 3.2 in mullions with steel cover strips and black gaskets, real 0.8 in glass panes (frosted below the transom, clear
above) and 5 in steel door jambs with a threshold plate. Same runs, posts and door gaps. Existing materials only.

- Triangles LOD0/1/2: 1,200 / 624 / 576 (0 degenerate). Old: 320 triangles in the control room mesh (135,204 -> 134,884 compiled).
- Collision unchanged (generator keeps posts and glass boxes; `equiv_check.py` identical in every room); 344 rays identical before / after / reverted.
- Scene object "Office Partitions" under Aquarium at the origin; generator flag `RS.OFFICE`.
- Pictures: output/model-trial-20261106/reefhall_office_partitions/pair_off_*.png. The change is subtle: the room is dark and the glass clear.
- Revert: `python revert.py office` was tested before approval; old/ and stage/ deleted, so it no longer works.
