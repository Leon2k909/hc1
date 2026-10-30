## Depot (cloud map integration and performance, 2026-10-27)
- `Assets/scenes/maps/Depot/Depot.scene` keeps the original `facepunch.depot` cloud map. Its Map object now has
  `DepotMapCleanup` (`Code/World/DepotMapCleanup.cs`), which disables 69 inert legacy pickup/charger roots when the
  map loads. Those roots contain 183 model renderers and 69 colliders, including 16 error-model placeholders.
  The compiled map geometry and all lighting are unchanged; the only authored scene-data addition is this component.
- Cleanup matches only direct `ammo_`, `item_` and `charger_` children with the exact known presentation/collider
  component types. It preserves a root if an updated map adds another component, and disabling cleanup restores the
  objects it suppressed. There is no per-frame cleanup callback. Native checks verify a functional pickup guard,
  protected object/component identities, unchanged floor traces in three areas, 55 probes, 82 point lights and 77 spots.
- Final native 1080p/4x MSAA offline TDM comparison: one stationary invulnerable player and nine active bots,
  900 frames per before/after run in three fixed views (5,400 measured frames). Pump: 63.02 to 63.83 FPS;
  stairs: 71.69 to 75.93; upper: 67.69 to 72.80. Mean frame time across the views: 14.863 to 14.191 ms (-4.52%).
  This is one pair per view with stochastic bot combat and desktop/editor overhead, so small changes are observations,
  not a statistically established FPS guarantee. CPU rendering/gameplay remains the main limit; lighting was not reduced.
- `Sources/Depot/performance-v1/results.json` records conditions, checks, timings and final source hashes.
  Raw frames, source fingerprints, captures and native CPU/GPU snapshots are in `output/depot-performance-20261027/`.
  The final `stable-*` runs have identical code/shader revisions and game assembly, no detected compiler activity,
  matching camera/player positions, nine bots and no cap wait. Earlier menu, match-transition, concurrent shader/hotload
  and incomplete samples are excluded. Native compilation has zero errors. Benchmark settings are restored and play stopped.
- This does not change `IsMatchReadyMap`: Depot's match readiness and exhaustive spawn/multiplayer acceptance remain separate.

