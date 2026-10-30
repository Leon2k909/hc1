## Teammate glow (`TeammateOcclusionGlow`, `hc1_teammate_occlusion.shader`)
- Living teammates (players and bots) get a faint silhouette in their team colour only where the world hides them,
  through the camera's `Highlight` and a private copy of the engine's highlight shader. `Sources/TeammateGlow/README.md`
  has the build, install and checks.
- 2026-10-27, the user: "bots not behind a wall but has glow". A single depth tap read the nearer surface at the
  character's own edges (vest hem, belt, pockets) and on slopes, so streaks lit visible teammates. Now a pixel is hidden
  only if the scene is nearer across its whole 3x3 neighbourhood, by ~1.5 pixels' world size (at least 0.25).
- The first-person gun's overlay depth counted as cover, so a teammate behind your gun glowed over it. `UpdateShield`
  (from `ViewModel.OnUpdate`) puts a transparent zero-width outline on the viewer's viewmodel while any teammate glow is
  set up, so the gun blocks the glow. It draws whole models, so a red dot's window blocks it too.
- Checked in isolated render fixtures (`visible-check.cs.txt`) and live in a Depot match (shield on, four glows), but no
  teammate was in view there.

