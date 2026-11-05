# Lucky Stop fluorescent fixture v1 – installed

Built and installed 2026-11-04 after user approval of both ceiling fittings.

The store's two original ceiling fittings are plain boxes with flat glowing cards. This replacement uses two cylindrical
phosphor tubes with dimmed ends, separate metal end caps, pins and plastic sockets; a folded reflector, thin housing,
ballast-access cover and technical label, catches, screws and mounting tabs. Paint color and roughness show restrained dirt,
wear and small edge chips. The six materials include one emissive tube material. Existing point lights remain unchanged.

LODs: 2,770 / 1,594 / 458 triangles. The housing and tubes fit within the old 48 x 8 x 3.1 in envelope. Two mounting posts and
ceiling plates extend through the former 1.5 in gap to meet the ceiling (maximum local Z 4.6); the horizontal footprint is 47.7 x 7.98 in.
No physics or runtime component. The first fitting is reviewed at engine `760,-150,145.4`, yaw zero. The second identical
original fitting is at `890,-280,145.4`. The preview removes exactly 14 old triangles for the first fitting from a private copy
of the current store input, preserving its upgraded shelving, register, fridges and other resources.

Build: `rtk python Sources/Riverside/fluorescent-v1/build.py`. Source assets stage under `output/riverside/fluorescent-v1/stage`.
Import/compile: `.../review.py import`. Capture: `.../review.py isolated`, followed by `.../review.py context`. Native captures
use isolated worlds/scenes and preserve the user's editor scene, play state and dirty flag. Studio captures show underside
detail; map captures use the existing store lights and exposure 3.5. Compose with `.../compose.py`; check with `.../verify.py`.

Resource: `models/props/riverside/fluorescent_v1/fixture.vmdl`. Work, manifests, source hashes, compile reports and screenshots:
`output/riverside/fluorescent-v1/`. The original store mesh, store ModelDoc and saved scene remain hash-protected. No full map
regeneration. Geometry checks report no inverted or degenerate triangles at any LOD; nine native resources compile successfully.

Installation removed exactly 28 original triangles from the current store input and saved two native ModelRenderers under
`Store Ceiling Lights`. The public store ModelDoc, collision, existing point lights and every pre-existing scene object are
preserved. The concurrent `Pole Insulators` addition is preserved too. The generator emits both model placements and retains
identical lights and collision; its narrow comparison removes only the fourteen old polygons. Twelve legacy/private-background
comparison files were archived outside Assets and deleted through the editor. Receipts: `installed.json`, `generator-check.json`
and `installed-capture.json` in the work folder. Actual saved-map native renders contain both fittings and no error models.
The large store compile initially timed out; the newer compiled resource and successful saved-map capture verified recovery.
Do not rerun the pre-install builder/verifier against the installed map: their old-face guards intentionally reject it.
