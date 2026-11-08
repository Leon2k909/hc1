## Orion launch-mount service pedestals — installed, old removed (2026-11-05)

- Rebuild candidate for the four plain28×20×40-inch boxes below the accepted cage lights. Flanged base, folded
  panels, recessed separate door/gasket, hinges/handle/lock, weather vents and side terminal cover/glands.
- Uses existing `oa_steel` and `oa_dark` materials, no new textures or lights. Roof mounting plane/footprint kept;
  corner cover screws rise0.11 inches, clear of the unchanged lamp base. Both comparison samples include the
  same accepted cage light. All point lights and collision unchanged.
- Accepted and installed in public pad and generator. Remove48 original box faces, add7,800,
  retain112,630 other faces exactly, including all four approved cage lights. Full physics/scene/hull hashes kept.
- Sources, snapshots, verification and actual native before/after/placement views:
  `Sources/Orion/mount-pedestals-v1/`, local `review/`. Three models compiled, no error models in placement views.
  Isolated temporary scenes destroyed; no document/play controls. Native state checks passed with user in Belltower.
- Narrow splice and generator hook in `orion_parts.launch_mount` installed; all four `work_lamp` calls unchanged.
  Six `before.*` files removed from game Assets at user request; receipt/archive in the local `review/` directory.
  Native pad compile and static checks passed. No full map rebuild or FPS benchmark.
