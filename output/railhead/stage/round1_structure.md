# Round 1 report for the structure area (both passes)

SUMMARY: Pass 2 fixed every regression the art director listed, then worked through the fixes in order. Every station collision is exactly as it was. The final build (logs/p2build5.log) has 0 spot problems, 0 spots cut off and 0 Retakes pairs in sight. The box and hull counts match the baseline: east and west 322/38, centre 193/134, roof 0/142.

Weathering is the main change. Sandstone soot now starts under a moulding on each wall instead of at a flat z 250. The hall stays repainted cream up to its entablature, with rw_lime_dark only on the lunette band and vault above z 540, and rw_lime_dado (the materials agent's request) below z 60. The iron soot no longer cuts through the column castings: the column, capital, spandrels and bearing plate are one paint, and the girder above them is sooted.

The handrails were pale tubes that read as PVC pipe; they are now dark grey-green painted iron. The middle columns now carry the girder on a capital right under it, with spandrels springing from the shaft. Before, a capital at 236 with a 64" stool above it read as a second, thinner column (confirmed in the reference render).

Other changes:
- Valley girder rivets are only along the footbridge now.
- The shed column's plinth is 30" square, an inch outside its 28" collision box.
- Canopy fascia corners are fixed.
- Stair parapets are now smooth precast, with caps and drips.
- The arcade has a continuous impost band and sill drip grooves.
- The goods sheds have brick pilaster strips and a corbelled eaves frieze.
- The head building's south front (the concourse end) has proper pilasters, archivolts, keystones and a dentilled cornice.

The station's structure totals about 485k triangles. No model is over 175k.
NEW FILES: Tools/railhead_architecture.py (created in pass 1; pass 2 added SOOT_ZONES, split_below, RAIL, precast_face, south_front and SOUTH_CORNICE); Tools/railhead_profiles.py (untracked, from an earlier structure session; in use); output/railhead/stage/structure/preview/ (directory junctions only: models and scenes point to my stage, materials to the materials agent's stage)
NOT DONE:
- I didn't ask for a cut on the cab-road side of the wings at the string course (222). Their soot starts over the main cornice (440), so the facade players see from the street stays clean stone.
- No 12" grime band above the hall's skirting: the stone dado covers the wall to 44". The materials agent's rw_lime_dado (below 60) gives that wear instead.
- The footbridge interior still reads dark overhead in Cycles. That is the lighting (the dressing area's lamps), not geometry; the soffit is now corrugated sheeting.
- Canopies are still level (collision must stay flat) and their fascias are 18" deep, not 14"; both are left as pass 1 made them.
- No gusset plates at the lattice nodes and no lower-detail version of the far ribs (both pass 1 limits).
- The window surrounds in the vault are still moulded arches on the wall face, not true penetrations.
- A graded rw_sandstone_soot is requested from the materials agent, not drawn by me: I own no textures.
NEXT:
- Integrate the materials agent's stage together with mine: the soot, lime and brick-dark paints and rw_lime_dado are referenced by the station models.
- Look at the footbridge interior lighting (dressing): its geometry is detailed now, but it reads dark overhead.
- Materials: grade rw_sandstone_soot along its world-z texture so the soot lines under the cornices fade into the clean stone.
- Structure, if there is another pass: the wings' cab-road facades (window surrounds and Lisenen like the south front), a lower-detail version of the far roof ribs, lattice gussets, and real lunette penetrations in the vault.
- After integration and the indirect-light rebake, check in-game that the shed column reads as one casting with its spandrels, and that the sign brackets on the cast band at z 226-238 sit right.
