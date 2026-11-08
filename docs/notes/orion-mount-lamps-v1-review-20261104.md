## Orion launch-platform cage lights — installed, old removed (2026-11-04)

- Candidate rebuild of four7-inch glowing cubes atop the launch-mount equipment boxes, z276 at plan(524,2630),
  (864,2630), (864,2970), (524,2970). Cast bases, rounded diffusers, rain caps, guard rings/bent uprights and screws.
- Reuses the existing `oa_steel`, `oa_dark`, `oa_lamp_warm` materials unchanged. No new textures or lights.
  Original footprint and top height retained; base extends2.5 inches down to meet the unchanged box top.
- Accepted and installed in public pad and generator; remove48 old faces, add22,384, preserve90,294 other pad faces
  exactly. Original saved scene, light declarations and collision unchanged. All3 models compiled successfully.
- Sources, checks, actual native before/after and placement captures: `Sources/Orion/mount-lamps-v1/`, local `review/`.
  Temporary isolated scenes only; no play/scene control calls. The user's scene/play state changed externally
  during the closeup capture (state receipt false), from Riverside to a running Riverdale scene; do not restore it.
- Narrow splice and exact-coordinate hook in `orion_parts.work_lamp` installed. Point-light handling and other
  work lamps untouched. User requested deleting old: six `before.*` files removed from game Assets; rollback copy
  and receipt at `Sources/Orion/mount-lamps-v1/review/retired-before` / `retirement.json`. No full map rebuild.
