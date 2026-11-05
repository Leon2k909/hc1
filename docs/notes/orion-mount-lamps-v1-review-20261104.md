## Orion launch-platform cage lights — review (2026-11-04)

- Candidate rebuild of four7-inch glowing cubes atop the launch-mount equipment boxes, z276 at plan(524,2630),
  (864,2630), (864,2970), (524,2970). Cast bases, rounded diffusers, rain caps, guard rings/bent uprights and screws.
- Reuses the existing `oa_steel`, `oa_dark`, `oa_lamp_warm` materials unchanged. No new textures or lights.
  Original footprint and top height retained; base extends2.5 inches down to meet the unchanged box top.
- Preview only; public map/generator unchanged. Remove48 old faces, add22,384, preserve90,294 other pad faces
  exactly. Original saved scene, light declarations and collision unchanged. All3 models compiled successfully.
- Sources, checks, actual native before/after and placement captures: `Sources/Orion/mount-lamps-v1/`, local `review/`.
  Temporary isolated scenes only; no play/scene control calls. The user's scene/play state changed externally
  during the closeup capture (state receipt false), from Riverside to a running Riverdale scene; do not restore it.
- On acceptance, narrow-splice only these four cubes and hook their exact coordinates in `orion_parts.work_lamp`,
  leaving point-light handling and all other work lamps untouched. No full map rebuild or FPS benchmark.
