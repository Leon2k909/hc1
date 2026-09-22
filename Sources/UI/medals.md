# RAZED combat medals

Three original transparent emblems generated with the built-in image generation tool:
- `Assets/ui/medals/precision.png` — headshot and one-shot awards.
- `Assets/ui/medals/multikill.png` — double, triple, fury, and frenzy awards.
- `Assets/ui/medals/streak.png` — bloodthirsty, merciless, and ruthless awards.

The HUD adds live rank/count plates and labels. Art contains no baked-in text. Each award uses a 460 ms impact arrival, a brief expanding ring and ribbon sweep, a 2.4 second hold, and a 280 ms exit. Awards earned together are staggered by 90 ms. At most four slots are visible; repeat awards retrigger and rapid kills upgrade their existing slot.

## Validation

Game build passed. The editor build passed during medal validation; its final run encountered four unrelated API errors in the concurrently added `Editor/Hc1InspectQa.cs` (`GameLayer`, `OverlayLayer`, and `FinishBoneUpdate`). Native s&box captures checked at 1920x1080, 1280x720, 1024x768, and 480x900. The narrow layout wraps into two rows. Runtime checks exercised repeat-award retriggering, multikill replacement, the fade state, and expiry. Native animation frames verified the staggered entrance and finished state; keep keyframes at stylesheet top level for s&box to resolve them.

The preview uses the actual HUD panels against a temporary neutral background. The temporary editor capture command and scene objects were removed after validation.

## Generation prompts

### Precision
Use case: stylized-concept. Asset type: production transparent PNG kill-medal emblem for a modern military arena shooter HUD. Create ONE original PRECISION / HEADSHOT medal. Straight-on symmetrical sculpted metal insignia: a bold ivory silver skull in a blackened steel circular crosshair, small copper-orange targeting diamond on its forehead, crisp angular split wings sweeping left and right, two short downward chevrons. Premium machined gunmetal, brushed silver bevels, restrained warm gold/orange edge accents. Strong chunky readable silhouette at 120 pixels, sophisticated embossed 3D game UI illustration, limited fine detail. Square composition, insignia fills 88% of canvas, centered. Truly transparent alpha background including all negative spaces. No text, no letters, no numbers, no backdrop, no rectangular card, no cast shadow outside emblem, no smoke, no glow or bloom. Original design, not any existing game's logo.

### Multikill
Use case: stylized-concept. Asset type: production transparent PNG multikill medal emblem for a modern military arena shooter HUD. Create ONE original RAPID KILL medal. Straight-on symmetrical sculpted metal insignia: a central bold ivory-silver skull, two smaller skull profiles behind it left and right, on an angular blackened steel hexagonal shield, short swept faceted wings and a pointed lower tip. Premium machined gunmetal, brushed silver bevels, crisp cold cyan-blue enamel inlays. Strong chunky readable silhouette at 120 pixels, sophisticated embossed 3D game UI illustration with limited fine detail. Match a prestige military medal language. Square composition, insignia fills 88% of canvas, centered. Genuinely transparent alpha background including negative spaces. No text, no letters, no numbers, no background, no rectangular card, no cast shadow outside emblem, no smoke, no glow or bloom. Original design, not any existing game's logo.

### Streak
Use case: stylized-concept. Asset type: production transparent PNG kill-streak medal emblem for a modern military arena shooter HUD. Create ONE original STREAK medal. Straight-on symmetrical sculpted metal insignia: a fierce bold ivory silver skull in front of a vertical combat dagger, angular gold laurel-blade wings that curve upward into a crown of sharp crimson enamel flame shapes, blackened steel shield backing and pointed lower tip. Premium machined gunmetal, antique gold bevels and deep crimson enamel accents, ivory skull clearly visible. Strong chunky readable silhouette at 120 pixels, sophisticated embossed 3D game UI illustration, limited fine detail. Square composition, insignia fills 88% of canvas, centered. Genuinely transparent alpha background including all negative spaces. No text, no letters, no numbers, no backdrop, no rectangular card, no cast shadow outside emblem, no smoke, no glow or bloom, no literal fire particles. Original design, not any existing game's logo.
