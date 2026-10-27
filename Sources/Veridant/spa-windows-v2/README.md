# Veridant spa windows

The eight south-facing spa windows and single west-facing window previously
used shallow opaque black or uniformly emissive boxes over a solid wall.
They now have real visual openings in the two facade faces, masonry reveals,
eased stone sills, bronze profiles, seals, handles, weep slots and four glass
panes per opening. Pleated linen, walnut consoles, lamps, framed artwork and
small vases occupy shallow 3D rooms behind the glazing.

`Tools/veridant_spa_windows.py` owns the geometry and twelve local materials.
`Tools/veridant_map.py:spa` delegates its building and facade generation to it;
the original signs and existing lamps remain. The spa's two collision boxes
retain their exact dimensions, transforms and surfaces. The model's complete
PhysicsShapeList suffix is byte-identical to the original.

The old 208 facade/window triangles were removed only from the active
`lounger-v2/veridant_buildings-base.obj`. A dedicated
`spa-windows-v2/spa-facades.obj` render import and twelve material remaps were
added to the existing buildings ModelDoc. All other OBJ bytes and index
mappings were retained. The current canonical OBJ and other render imports
were protected rather than regenerated.

Close-up review found four existing exterior fixture meshes overlapping the
new openings. A further 16 old fixture triangles were removed from the same
base import, and their replacement faces were added below the sills. The four
existing point-light objects were moved to the matching heights through the
native `set_game_object` tools and the scene was saved with `save_scene`.
Structural comparison of all 450 scene objects verifies that only those four
Position properties changed relative to the immediate pre-move scene backup.
Source generation now retains these corrected fixture heights. The west
interior is shortened to keep it separate from the first south-facing room.

Publication and verification:

- Initial facade publication: `output/veridant/spa-windows-v2/stage-v2/manifest.json`.
- Final refinement: `output/veridant/spa-windows-v2/stage-v4/manifest.json`.
- Stage-v3 was rejected before mutation because another chat saved the shared
  scene. Stage-v4 preserves that newer scene, including its added bar lights.
- Guarded native publisher: `import.cs.txt`. It copies staged resources
  atomically, validates source/target hashes and retains editor scene/play state.
- Final validation: `output/veridant/spa-windows-v2/validation.json`.
- Twelve materials and the buildings model compiled successfully.
- Original and generated collision definitions match; no gameplay clips changed.
- Final geometry: 43,420 triangles across nine windows, two facade faces and
  the four existing fixture replacements. Frame-rate impact was not benchmarked.

Reviewed native captures use ACES at exposure 2.2, restore all camera and
post-processing state, and retain the selected saved Veridant document:

- `output/veridant/quality/spa-windows-v2-before/front.png`
- `output/veridant/quality/spa-windows-v2-final/front.png`
- `output/veridant/quality/spa-windows-v2-final/angle.png`
- `output/veridant/quality/spa-windows-v2-final/west.png`

The front comparison uses the same pose, projection, dimensions and exposure.
The scene hash differs because the existing light positions were corrected
and a separate chat saved unrelated changes during the task; those newer
changes were preserved. No broad scene or whole-map generator was run.
