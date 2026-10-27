# Ares wall-pipe rebuild — 26 October 2026

The 16 existing wing and cargo pipe runs now have 32/48-sided smooth profiles,
160 paired weld-neck flanges with gasket seams and four through-bolts each,
and 72 wall-anchored cantilever/drop hangers with rounded isolation saddles.
Routes, pipe radii and existing collision remain the same.

`Tools/ares_pipework.py` supplies the drawn-only geometry. `ares_map.pipe_run`
delegates to it, while `ares_map.configure` preserves its `ar_pw_` overrides.
`Tools/ares_pipework_materials.py` generates five dedicated PBR finishes:
satin grey coating, copper, cast housings, machined contact metal and rubber.
The 1024 px maps use fine colour/roughness variation; manufactured tube surfaces
retain flat normals. All normal maps are powers of two.

The current hall's active base import remains
`models/maps/ares/pressure-doors-v2/hall_base.obj`. Exactly 2,240 original pipe
triangles were removed by material/position matching. The complete retained OBJ
data and index allocation were kept, and 296,128 replacement triangles appended
after every existing attribute table. Other hall geometry, door imports and the
entire physics suffix were preserved. Five `ar_pw_` material aliases were added
to the existing ModelDoc, with matching MTL definitions. The original canonical
hall OBJ/MTL and the pressure-door meshes were not changed.

Geometry stage `output/ares/pipework-v1/stage-v3` is the immutable input for the
final finish migration. `Tools/ares_finish_pipework.py --from-stage stage-v3
--stage <fresh-stage>` reuses the inspected geometry, only retags its appended
material groups, and stages the private finishes. The final installed stage is
`stage-v5`; intermediate stages retain development evidence. The original pipe
generator is in `legacy.py`, and the validated pre-finish geometry source in
`geometry-before-materials.py`. The geometry staging script is a one-time
migration from the original pipe mesh, not a command to run on the installed mesh.
Do not run the full Ares map generator just to refresh these assets: it rewrites
scenes and would interfere with other work.

`import.cs.txt` runs in the native CLI session exchange directory. Preview is
the default. It validates sources, backups and scope before publishing. On live
publication it merges only the five private aliases into the current ModelDoc,
preserving concurrent door edits, and installs aliases before the new OBJ so
background recompiles always see valid mappings. Its exact current-document
backup is `stage-v5/native-before-hall-<sha256>.vmdl`.

Native compilation passed for the five materials, the separate trial and the
live hall. The 16 wall traces match the original results exactly. Cargo and wing
captures were inspected both with the temporary trial and after actual install;
the final images have no renderer override. `verify.py`, `installed.json` and
`output/ares/pipework-v1/validation.json` record scope and restoration checks.
No scene save was performed by this task; the current editor camera and play
state were preserved. Another shared-editor save occurred during the task, so
the final matched cargo comparison was recaptured against the current scene.
