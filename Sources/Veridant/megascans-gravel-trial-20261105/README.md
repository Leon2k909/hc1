# Veridant garden path: Megascans gravel comparison

Installed and accepted by the user on 2026-11-05. The ground model's gravel
material remap now references this scan. `Tools/veridant_map.py.configure()` keeps
the same mapping during regeneration. The original gravel material and textures,
saved scene and all collision remain unchanged. Native model compile and live
verification confirmed the new material in the editor and running play session.
`installed-ground-before.vmdl` is the original model backup in the output folder;
`install-receipt.json` records before/after hashes. `installed.png` verifies the
saved model's own material mapping, with no temporary material overrides.

The earlier comparison was preview only:
Native captures deserialize only the saved map's visual roots in an isolated
editor scene, override the vr_gravel slot, then destroy that temporary scene.
The user's active Veridant scene, camera and play state remain unchanged.

Source: Quixel Megascans Gravel Ground, `vi0maebg`, free on Fab:
https://www.fab.com/listings/c19d425f-4957-4238-b1d7-34c984e9867f
Downloaded 2026-11-05 after explicit approval to accept the Fab Standard Licence.
`provenance.json` records archive, source, target and protected file hashes.
Original 2K base colour, normal, roughness and AO maps are copied unchanged.
The 2x2 metre scan repeats 1.2192 times per existing 96-inch UV tile, retaining
physical stone scale. No displacement or additional geometry is used.

Camera: world (-850,150,64), angles (25,-90,0), horizontal FOV 65,
1200x900 pixels, fixed exposure 2.2, identical scene and lighting for both renders.
Images: `output/veridant/quality/megascans-gravel-trial-20261105/`.
Native receipts and validation: `output/veridant/megascans-gravel-trial-20261105/`.

Assessment: the original garden path is a cloudy noise field without readable
pebbles. The scan supplies actual irregular stone shapes and convincing surface
relief. The scan is noticeably darker, but reads more convincingly as gravel.
The trial is ready for the user to compare before choosing an installation.
