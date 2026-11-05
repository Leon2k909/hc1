# Sewage work lamp model review

24 caged bulkhead work lamps with bevelled cast housings, recessed lens gaskets,
shallow glass flutes, domed protective guards, mounting ears, hex fasteners,
cable glands and short sealed cable tails. Each stays at the original anchor.

The original amber, white, red and green emission materials are reused, with
separate material slots per colour. All scene light components, positions,
brightness, colours, radii and shadow settings remain untouched.

The targeted splice removes exactly 2,016 old lamp faces and preserves all
90,858 other details faces, including the approved drums and crane blocks,
with their exact original positions, UVs and normals. Original OBJ is untouched;
a sibling base model retains the original details physics. New lamp geometry
is 52,608 triangles across 24 fixtures, render only.

Both preview models compiled successfully through native s&box MCP.
Matched close-up renders: `output/sewage/work-lamps-v1/before.png` and `after.png`.
Capture uses an isolated temporary scene and preserves live editor/play state.

Installed in the saved Sewage scene for the current review. Existing better models
were checked before any new work: Riverside's approved porch lamp, ReefHall's sealed
wall-light candidate and the Ares bulkhead proposal. This already-authored Sewage
set was reused because it matches all 24 existing anchors and four light colours.
No replacement geometry or material was rebuilt for this installation.

`install.cs.txt` checks the current original details SHA-256, replaces the renderer
reference, adds one separate fixture renderer and saves only Sewage, verifying the
disk file. No full map rebuild; valve wheels, pipe texture, flanges and other props
stay intact. The original details mesh remains available for the old lamp variant.

Current comparison: `output/sewage/work-lamps-v1/current-review/`. The before uses
the current saved map with the approved new stairs; the after renders the actual
installed scene without adding preview fixtures. `verify_installed.py` confirms
43 light components and all eight collision components are unchanged, one lamp
group is installed, original details geometry is retained, and both old/new stair
variants remain available. Keep both stair variants at the user's explicit request.
