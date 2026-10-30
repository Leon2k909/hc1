# Teammate occlusion glow

Living teammates receive a quiet silhouette only where world geometry hides
them. Visible surfaces have transparent edge and fill colours. Hidden surfaces
use 7% fill and an 18% thin edge in the existing teammate colour. Player names
and markers retain their existing settings. Free-for-all, unassigned actors,
dead actors and the possessed player receive no friendly glow.

`TeammateOcclusionGlow` shares the style between `PlayerPawn.UpdateOutline` and
`LightweightCombatBot.UpdateTeammateGlow`. Bot updates run on proxies as well as
the host; their visual-only outline components are neither saved nor networked.
Existing spectator/killer-outline behaviour is separate and retained.

The private shader derives from the installed engine's object-highlight shader.
It keeps the engine's inside/outside passes and composition and renders front
faces. A pixel counts as hidden only when the scene is nearer than the character
across the pixel's whole 3x3 neighbourhood, by more than about 1.5 pixels' world
size (at least a quarter inch). It is assigned only by the friendly style and does
not replace engine shaders or map materials.

On 2026-10-27 the user saw visible bots glowing ("bots not behind a wall but has
glow"). The earlier single depth tap with a 0.12 inch tolerance read the nearer
surface at the character's own depth edges (a vest's hem over the shirt, belts,
pockets, knee pads) and on sloped triangles, so streaks lit up on teammates in the
open. The 3x3 neighbourhood takes the farthest scene distance round each pixel.
At a cover's edge the glow now stops a pixel or so short of the line.

The first-person gun and arms draw in the overlay layer, whose depth the glow
reads as cover, so a teammate behind your own gun glowed over it. While any
teammate glow is set up, `TeammateOcclusionGlow.UpdateShield` (from
`ViewModel.OnUpdate`) puts a transparent, zero-width outline on the viewer's
viewmodel, its targets picked as `ViewModelMask` picks them. It puts the gun in
the glow's own depth buffer in front of the teammate, so nothing is drawn there.
It draws whole models, so a red dot's window also blocks the glow behind it.

`prepare-shader.py` records the SDK source checksum and derives the staged source.
`import-shader.cs.txt` publishes and compiles that one shader through the editor.
Run scripts from the native CLI exchange directory. Do not edit engine files.

`depth-check.cs.txt` renders a disposable three-mesh figure with one arm exposed
beside cover, then renders the fully exposed figure, with the same shared style
the game applies. It never switches or saves the edited map, changes its camera,
or enters play mode. `verify-depth.py` checks pixel differences: hidden torso
changes, exposed arm and empty wall do not, and the fully visible figure has zero
changed pixels. Captures and results are in `output/teammate-glow/verified`.

`visible-check.cs.txt` (run_csharp with its absolute path) renders five dressed
characters (200-850 units, standing, running, crouched) in isolated scenes,
visible, partly and fully behind cover, and behind an overlay-layer gun stand-in
with and without the shield. Results are in `output/teammate-glow/fix-20261027/`
(`installed/` for the shipped shader, `trials*/` for the candidates compared).
Close up (200-350 units), pixels changed on a fully visible character fell from
71-146 to 24-39, the frame noise every neighbourhood candidate left; hidden
coverage was unchanged (0.97-0.99). `score-visible.py <folder> installed` counts
them. Behind the gun stand-in, 529-4,603 changed pixels fell to
236-307, faint noise spread over the frame (mean 4.6 levels).

Validation is engine render fixtures and clean native compilation. On
2026-10-27 the fix hotloaded into the user's Depot match, where the viewer's gun
carried an enabled shield (20 targets) beside four teammate glows; no teammate
was in view to see it in-game.
