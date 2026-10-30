# Ares formed pressure doors

The reference is `concept-v1.png`, generated from the user's existing door screenshot.
`Tools/ares_pressure_formed.py` builds the three door assemblies as actual geometry:
four recessed pressings per door, rolled edges, service covers with recessed pulls,
six cast spindle clamps and connected lock rods, a recessed release wheel, a guarded
control station, a glass-covered pressure gauge, bolted kick plates and a treaded
threshold. Wear follows the rolled edges; dedicated PBR maps add coating texture,
small scratches and shallow dents. Equipment markings are printed into a separate
cassette atlas, with room for the latch footprints on the narrower wing doors.

`Tools/ares_pressure_formed_materials.py` generates 15 private materials under
`Assets/materials/ares/pressure-doors-v3`. Normal maps and atlases are power-of-two.
The pressure-door entry point for full future map builds is `Tools/ares_airlock.py`.
The previous v2 geometry and material code are archived in this directory.

`Tools/ares_stage_formed_doors.py` replaces only the three v2 door import filenames
and their private material remaps in the current hall ModelDoc. It keeps the original
current 317,588-triangle hall base import, all its source bytes, every import transform and
the complete physics suffix. It never runs the full map generator or writes a scene.
The wings contain 74,518 triangles each; the cargo door contains 78,448. The complete
hall contains 545,072 triangles. No frame-time benchmark is claimed.

Staging and import workflow:

1. Stage to a fresh directory under `output/ares/pressure-door-v3`. Material-only
   revisions can use `--geometry-from` after exact geometry-input checks.
2. Run `import.cs.txt` through the native editor exchange directory. It defaults to
   preview mode and validates source, target, backup, physics and editor state.
3. Compile `trial_hall.vmdl` and inspect it with `ares_formed_capture.py --trial`.
   The renderer, camera, exposure and source scene are checked and restored.
4. Set `preview` to false only after the separate trial compiled and rendered.
   Run the same import script and compile the live hall.
5. Capture the installed model, run native asset checks and collision traces, then
   run `verify.py`. It writes `installed.json` only after those checks pass.

The final verification stage is `stage-v6`; its full backups and scope hashes remain in the output
directory. All 27 sealed-door physics traces are compared with the original results.
`restore-live-hall.cs.txt` can restore the exact working v2 ModelDoc from the stage-v5 backup
after checking current and backup hashes, without touching the scene or original OBJ.

The first preview's folded inner seal was replaced by a monotonic machined throat
and separately seated gasket. The throat's rounded corners exceed its largest inset
so the offset curves remain valid. A diagnostic shadow-cache reset did not resolve
the artifact and was removed from the capture workflow. No global shadow-cache API
is used by the final capture helper.

The base had already been expanded by shared geometry work before this task's
staging. Its full hash is preserved. Stage-v6 corrects the legacy triangle-count
assumption in the reporting workflow; its installed asset bytes match stage-v5.

The shared Ares scene received a separate save adding stair rear closures during
the work. The current scene was reviewed and retained; this door task performs no
scene save, lighting edit, collision edit or gameplay change. Native screenshots are
under `output/ares/quality/pressure-door-v3-installed`.
