# Cerro Blanco North Gallery terrace doors — 2026-11-06

Added and saved a usable glazed pair in the upper North Gallery doorway to the café roof terrace. Reused `models/props/veridant/reception_doors_v1/leaf.vmdl` with BoxCollider and Facepunch.Door components. Roots are `North gallery terrace glazed door left/right`, at (453.15,-1009,180) and (546.85,-1009,180), yaw 90/-90, scale (1,46.65/29.15,1.18).

Updated `Tools/cerroblanco_doors.py` and its `Tools/cerroblanco_map.py` integration so regeneration retains this pair. Saved/generated root counts and unique generated GUIDs checked.

Actual displayed editor-window captures, matched camera and lighting, are in `output/cerroblanco/north-gallery-terrace-doors-v1/before-window.png` and `after-window.png`. Camera position (500,-781,240), angles (3,-90,0), FOV 80. Captured using the native screenshot_game PrintWindow helper, without an offscreen render. Immediate scene backup: `before.scene` in the same directory.

Runtime checks in Cerro Blanco passed: both leaves reached Open and Closed through OnUse; two rays across the doorway cleared when open and hit the corresponding leaves when closed. Bots and multiplayer were not tested. Stopped play and restored the prior Cerro editor camera and active Veridant tab. Compile status clean.
