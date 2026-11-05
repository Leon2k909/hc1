# Riverside passive roof vent v1 — T2 installed

Installed the user-approved first T2 vent: one saved renderer under `Passive Roof Vents`, engine `1033.911476,765.044280,122`, yaw zero. Exactly 12 old box faces removed from public lowland geometry. Every other mesh line, existing scene object/property, complete ModelDoc/physics and lighting were preserved. Other vents remain as authored.

A low mushroom rain hood with rolled edge/inner skin, an open screened intake, three support straps, cap fasteners, raised curb, sealant bead and screwed flashing. No solid wall hides behind the screen. The 16-inch flashing follows the actual roof plane: relative `z=-.538902254+.095652174*x`. Hood radius 7 inches, top Z=4.34. Procedural zinc surface and mesh mask, no external assets.

Resource `models/props/riverside/roof_vent_v1/vent.vmdl`: **3,148 / 1,732 / 976 triangles**, thresholds 18/45. One 1k PBR atlas/material plus a separate screen material/512px alpha mask. No added lights, collision or runtime component. No gameplay performance or LOD-transition test.

Use `rtk` for all shell commands. `build.py .` reproduces assets from the recorded placement/roof plane. `Tools/riverside_parts.py` records `ROOF_VENTS`, preserving all random calls and original other vents; `Tools/riverside_map.py` enables the hook for T2 only and emits the model group. Do not apply this roof-specific flashing to other roofs without an audit. Never regenerate the whole shared map to install it.

`prepare_install.py .` staged the exact 12-face cut, current production hashes and deterministic group. `install.cs.txt` checked saved and live scene snapshots before/after loading the model, then applied the cut/group through the editor and saved. Native public lowland compilation succeeded. `verify-install.py .` passed saved placement, exact mesh-line removal, unchanged ModelDoc/physics, scene objects/properties and zero new lights/colliders. Only automatic prefab-ID cache normalization is ignored in scene comparisons. `capture-installed.cs.txt` rendered the actual saved group, count 1.

Nine private comparison files were archived to `output/riverside/roof-vent-v1/retired-review-assets/` and removed through the editor. The old source box is gone; shared `rs_alu` remains for other objects. Installation receipts/screenshots: `output/riverside/roof-vent-v1/installed/`. Original matched review: `compare_whole.png` in the parent folder, background luminance within .14%. Historical review scripts reference retired assets and are archival.
