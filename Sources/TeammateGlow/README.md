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
It keeps the engine's inside/outside passes and composition, renders front faces,
and compares linear scene/object depth with a small surface tolerance. This avoids
counting equal-depth, flat visible triangles as obscured. It is assigned only by
the friendly style and does not replace engine shaders or map materials.

`prepare-shader.py` records the SDK source checksum and derives the staged source.
`import-shader.cs.txt` publishes and compiles that one shader through the editor.
Run scripts from the native CLI exchange directory. Do not edit engine files.

`depth-check.cs.txt` renders a disposable three-mesh figure with one arm exposed
beside cover, then renders the fully exposed figure, with the same shared style
the game applies. It never switches or saves the edited map, changes its camera,
or enters play mode. `verify-depth.py` checks pixel differences: hidden torso
changes, exposed arm and empty wall do not, and the fully visible figure has zero
changed pixels. Captures and results are in `output/teammate-glow/verified`.

Validation is an engine render fixture and clean native code compilation. A live
multiplayer match was not started, preserving the shared editor session.
