# Reef Hall bronze entrance planter — review, 2026-11-04

Substantial shell rebuild for the two plain tapered bronze boxes between the lobby's three entrance-door pairs.
The new shell has rounded corners, six recessed flutes per side, a rolled rim with an inner return, a bevelled
lower edge and a recessed dark toe. Fine brushed bronze color, roughness and normal maps are private to this prop.
No generated imagery or external assets. Original soil height, plants, position and metal hull remain unchanged.

The user accepted the candidate and it is **installed in the public lobby model**. Native `install.cs.txt` published
the guarded narrow splice and generator hooks. No full map rebuild was needed. The generator calls
`reefhall_bronze_planter.shell` while retaining the original soil and hull declarations. Old render shells are
removed from the map; the historical comparison remains inactive for review and rollback.

`build.py` checks all old shell faces exist exactly before splicing the candidate. It removes 52 original shell
triangles, adds 11,968 and preserves 31,290 other lobby faces including all foliage, doors and other improvements.
The full ModelDoc physics suffix and hull files are unchanged. Before/after closeups use the actual published
soil and 1,800 leaf triangles, with the same camera, lighting, exposure and floor in an isolated engine scene.
`context.cs.txt` clones saved Reef Hall visual roots and substitutes only the lobby render model for placement
views. It never switches, saves, or controls play in the user's document. Temporary capture scenes are destroyed.

`verify.py` checks exact face retention, public input hashes, unchanged physics/soil recipe, finite normals/UVs,
nondegenerate triangles and the original 22.575-inch square by 46.25-inch envelope. Native compilation, loaded
material bindings and actual screenshots complete the visual check. No performance benchmark is claimed.

Evidence and snapshots are under `review/` on the local C: drive. The project's `output` junction resolves to
`D:/hc1-offload/output`, whose writes stalled for several minutes during this task; abandoned partial snapshots
there are not used by this review. The authoritative plan and hashes are in this local `review/` directory.
