# Ares pipe end closures — 27 October 2026

The wall-service tubes had no end faces. All 16 installed runs now have dished
heads at both ends, with smooth normals and a narrow weld transition on the grey
coated pipes. Copper heads use the existing copper finish. The 32 heads add
17,472 render triangles and join all 1,344 exposed tube-rim edges exactly.

`Tools/ares_pipework.py::pipe_end_caps` builds the heads. `pipe_run` includes
them in future map generation. `Tools/ares_close_pipe_ends.py` is the guarded,
one-time migration for the currently installed model; it rejects an already
patched OBJ. Do not run the full map generator to apply this repair.

Only the active `pressure-doors-v2/hall_base.obj` was published by the native
editor helper. Every original OBJ byte is retained as an exact prefix, with
new attribute tables and rebased faces appended. The hall ModelDoc, door imports,
materials, collision sources and scene are unchanged. The original OBJ and a
manifest are in `output/ares/pipe-end-fix/stage-v1/before` and `manifest.json`.

Native hall compilation and up-to-date checks passed. Matched cargo-east images
show the original holes and the installed caps; cargo-west checks the opposite
orientation. The saved scene, current camera and play state were preserved by
the captures. All 27 before/after collision rays agree. `verify.py` records this
evidence in `installed.json` and `output/ares/pipe-end-fix/validation.json`.

The editor was closed at the start of final verification. A temporary native
`--project` connection opened it for compilation and captures, then was released.
No scene save or gameplay-code edit was needed.
