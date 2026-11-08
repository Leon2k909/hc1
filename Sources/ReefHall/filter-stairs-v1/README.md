# Reef Hall filter-hall steel stairs — approved by the user and kept, old geometry and backups deleted, 2026-11-06

Replaces the two open steel flights (26 thin slats between plain blue beams, square-post rail) with `filter_stair_a/b.vmdl`
(`Assets/models/props/reefhall/stairs_v1/`): C-channel stringers with a bottom flange, grating treads with a nosing bar and
under-tread angle, round posts on base plates, a handrail with domed ends, a midrail and a toe board (east flight both sides,
north flight east side, as before). Existing materials only (rh_grate, rh_gunmetal, rh_steel, rh_steel_blue).

- Triangles LOD0/1/2: A 5,076/2,736/1,780, B 3,482/2,000/1,522 (0 degenerate). Old: 900 triangles in the room mesh; room 31,665 -> 30,765.
- Collision unchanged (generator keeps hulls; `equiv_check.py` identical in every room); 604 rays identical before / after / reverted.
- Scene objects "Filter Stair A/B" under Aquarium at the origin; generator flag `RS.FILTER`.
- Pictures: output/model-trial-20261106/reefhall_filter_stairs/pair_fil_*.png. The room is dark, so the change is subtle.
- Revert: `python revert.py filter` was tested before approval; old/ and stage/ deleted, so it no longer works.
