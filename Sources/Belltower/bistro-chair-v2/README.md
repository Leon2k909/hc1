# Belltower bistro chair v2 — installed

Approved by the user and installed on 2026-11-04: all 21 café chairs (12 west, 9 east).
The old baked chair geometry was removed from both canonical meshes and their referenced visual partitions.

The selected chair is beside the cafe menu board, at plan `-602.566956,-193.862329`, yaw `445.619487`.
The candidate retains the green steel/wood character, with smoother continuous bent rear supports,
a rounded seat carrier, eased timber slats, continuous curved back boards, visible end grain,
low-domed fasteners, weld collars and protective foot caps. Existing materials/scans are reused.
Three source LODs: 4,376 / 2,376 / 684 triangles; the original selected chair has 384 triangles.
All source faces are finite and nonzero, and native compilation passed.

The original review builder generated private assets and a west visual variant with exactly the selected chair's old
faces removed. No other source records are changed. A second private definition, `west_baseline.vmdl`,
is byte-identical to the current production west VMDL. Rendering the original cached hidden-document
model directly produced inconsistent texture residency, so both comparison versions are freshly
compiled, warmed through discarded captures, then rendered through the same path.

Final images are `before-final.png` / `after-final.png`, with identical camera, projection and temporary
inspection light. The temporary model/light and all camera/tone/editor state are restored after each
capture. Shared source guards, including the scene with twelve new pots and six new menu boards,
remain unchanged. Initial captures with inconsistent texture loading are not the review evidence.

Evidence: `output/belltower/bistro-chair-v2/`; final checks: `review.json`.
Installation removed 8,064 old triangles from eight source meshes and deleted eleven private review files.
All seven affected current/historic model definitions compiled successfully. Existing objects and physics were
preserved; the scene was saved through the editor. `installed.json` records the native receipts.
Regeneration delegates to `Tools/belltower_bistro_chairs.py`; the east spacing and inward-facing rotations
are preserved. `build.py` now stages only the accepted chair resource, without recreating retired review files.

The final asset-info refresh had no editor connection available after the completed captures.
The successful native compile receipts and rendered/restored comparisons are the validation evidence.
