# Ares observation sign — installed

Approved and installed on 2026-11-03, on `codex/ares-observation-sign-v1`.
The public `ares_dressing.vmdl` now imports the dressing with the original sign
removed plus the approved replacement sign mesh. Its five private aliases are
remapped in that ModelDoc. The saved scene and the full original physics suffix
are unchanged. Native compilation and installed close/context captures passed.
`output/ares/observation-sign-v1/installed.json` records the installation checks.
The first installed capture was rejected: it ran before the face texture's mips
had streamed in and showed severely blurred lettering. Captures now allow 90
rendered frames per view without forced texture residency. The corrected
`sharpness-fix/detail-installed-ready.png` matches the approved lettering pixels
exactly in the checked region. `verify_sharpness.py` records the comparison and
rejects the earlier blurry result; see `sharpness-fix/verification.json`.
`Tools/ares_observation_sign.py` retains the geometry for future map generation;
its generated mesh matches the approved OBJ exactly. `ares_map.py` calls it only
for the suspended observation sign. All other original Ares assets were hash checked.

The original suspended observation sign is a thin black box, a luminous atlas
quad, and two four-sided rods. The candidate adds an eight-sided bevelled
powder-coated housing, recessed face and gasket, cast end vents, captive
fasteners, service cover, cable grips, collars and ceiling plates. Its original
centre, 194 by 50 inch outer size, suspension locations and 720 inch ceiling
attachment height are retained. A new 2048 by 512 face uses the project's Dinish
font, restrained illumination, Ares identity and a small observation pictogram.

The replacement has 756 triangles and five material slots, sharing the existing
Ares panel, alloy, dark metal and black materials. Only its face material and
two textures are new. No extra light or collision is added. Performance has not
been benchmarked; this is one sign, rendered only in the disposable review scene.

`build.py` writes guarded staging files under `output/ares/observation-sign-v1`.
It extracts exactly 30 original triangles (14 sign and 16 suspension triangles)
from the installed dressing import into a private review-only mesh. Every other
vertex, UV, normal and face is retained. The review ModelDoc preserves the entire
original physics suffix. Installed source assets are fingerprinted separately.

`import.cs.txt` is executed in the native CLI exchange directory and imports
only the new `observation-sign-v1` asset folders. `review.py` compiles the private
material and both models, then renders the original and candidate from matching
close and contextual cameras. The map's lights and geometry are loaded in an
isolated scene; only that scene receives the replacement. It is destroyed in
`finally`. The user's scene, play state, dirty state and camera remain intact.

Native captures use fixed exposure 2.2 (within the map's 1.7–3.35 range), ACES,
and matching ambient occlusion and bloom. These are actual engine captures,
not ImageGen concepts or Blender renders. `finalize.py` verifies source hashes,
unchanged physics and unrelated geometry, native compile health and editor state,
and produces labelled comparison sheets. Scripts use one native connection at a
time and leave no background process running.

Reproduce from the canonical checkout:

```powershell
rtk python Sources/Ares/observation-sign-v1/build.py
rtk python -u Sources/Ares/observation-sign-v1/review.py
rtk python Sources/Ares/observation-sign-v1/finalize.py
```

Review images and `validation.json` are in `output/ares/observation-sign-v1/`.
`prepare_install.py` and `install.cs.txt` describe the completed guarded native
installation. Do not replay them over the installed model; they reject that state.
`check_install.py` checks the installed import, source preservation, generated
geometry and fresh native captures. Do not regenerate the whole Ares map.
