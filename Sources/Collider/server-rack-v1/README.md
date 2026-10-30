# East stair server rack

Requested repair, 2026-10-27, canonical `C:/sbox-projects/hc1/forked-shooter-main`.

The pictured cabinet was 48 x 60 x 138 inches at plan `(430, 80, 0)` and blocked part
of the first three east-atrium stair treads. Its replacement is a 28 x 44 x 84 inch
enclosure at `(430, -60, 0)`. Its north edge is 78 inches clear of the stair's near
edge. The 42U-size frame has separate side skins, open louvres, levelling feet,
rear fan cartridges, recessed equipment of varied heights, mounting uprights,
fasteners, hinges and a flush access latch. It reuses the existing Collider PBR
materials and only small status lamps.

`Tools/collider_server_rack.py` owns the geometry and placement; the east-cabinet
branch of `Tools/collider_map.py::detail` owns regeneration. The west cabinet is
unchanged. The live migration removes exactly the 276 original east-cabinet render
triangles from the combined detail mesh, preserving every other original OBJ line
in order. It appends 17,044 triangles; the resulting detail mesh is 158,720 triangles
including the concurrently completed ceiling work. No runtime component or texture
is added. The model's single east-cabinet collision box moves and resizes with the
new enclosure. Every other ModelDoc byte, material binding and physics shape stays
identical.

`stage.py` writes a private candidate and before copies. `import.cs.txt` applies
only the detail OBJ and VMDL through native s&box, with hashes, a rollback path,
stopped-play guards and preserved editor document state. It does not replace or
save a scene. The structure/machine assets are excluded from this repair so that
the independent wall/ceiling work can continue.

Evidence is in `output/collider-server-rack-20261027/`:

- Native detail-model compilation succeeded.
- All 40 standing-body probes across five interior stair lanes pass. Ramp clearance
  accounts for the uphill floor edge within the ordinary step height; each ray must
  hit the expected stair surface rather than the old cabinet's top.
- The old cabinet volume is clear; the new rack has solid collision and floor support.
- All four stair routes/under-stair checks pass; all 68 map support/clearance/Complete
  navmesh checks pass, with no missing models or materials.
- Added geometry has finite coordinates, no reversed triangle winding and minimum
  triangle area 0.000070148 square inches.
- `before/` and `after/` contain matched native screenshots with restored camera and
  editor state. They also include independent wall/ceiling edits completed between
  the captures; the after images prove current placement and appearance, not an
  isolated whole-scene graphics comparison.

The native import and images preserve the clean, stopped Collider document. The
saved scene hash remains `bf6a9feabd22b988276ec8cdb80f383e734e2ac733f38a4f923d404a14729802`.
This is a local asset and traversal check, not a new full-match performance result.

Keep `stage-v1/before/` for rollback and `stage-v1/assets/` for the accepted result.
Review any later detail-model changes before restoring either file through the
editor. `installed.json` records the accepted hashes and native evidence.
