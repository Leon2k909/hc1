# Lucky Stop roof sign v1 — installed 2026-11-04

Approved formed steel lightbox and gooseneck lamps replace the old sign. 9,016/5,548/2,248 triangles, masks 7/56/64 across the existing seven store LOD groups. Placement (514,-220,150), original 168×8×48-inch cabinet volume and all public ModelDoc physics retained. Public store imports shop-sign-v1/store_without_shop_sign.obj and installed_lod0/1/2.obj, with shopsignv1_ aliases. Face uses verified face_toned.vmat (non-emissive, roughness 0.72); private bulb brightness 1.0. Global materials and camera look unchanged.

The existing store sign PointLight (7867677a-76dd-57bc-9e53-006ab54770cb, component ad251c23-5036-51ff-9ecb-932578dc96f1) was saved through native set_component with Intensity 0.20. LightColor 2.2,1.584,0.924,1, radius420 and animation remain unchanged. Bridge set_property did not mark the scene dirty, so native set_component was used and the saved JSON/runtime were checked. Authoring equivalent scale0.44.

Old standalone sign and bright lighting control resources deleted via native Asset.Delete; exactly136 old faces removed from six source variants. Other upgrades preserved, no full-map regeneration. Tools/riverside_shop_sign.py reproduces all three approved meshes; riverside_map hook uses it and preserves the cabinet collider. Actual public model checked in offline play: one player, zero error models, no renderer substitution or extra lights. Editor returned to Sewage, clean and stopped.

Evidence: output/riverside/shop-sign-v1/installed.json, installed-runtime.json, in-game-installed.png; scripts in Sources/Riverside/shop-sign-v1. Pre-install review sources are archival and may reference deleted control assets.
