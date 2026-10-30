## First-person body (`PlayerBody.FirstPersonBody`)
- A second body drawn only for the viewer, so they see their legs: 6.175 behind the pawn's origin, with no shadows.
  The main body is hidden in first person by the `viewer` tag (`PlayerBody.OnUpdate`, the camera's RenderExcludeTags).
- The legacy player models hid its upper body with procedural spine bones in player.prefab (spine1, spine3). The
  players are now the human model (`MilitaryUniform.HumanModelPath`), whose skeleton those bones don't touch, so the
  whole body showed, and walking forward leaned its face and eyes into view (the user's report, 2026-09-29).
- `MilitaryUniform.ShowLegsOnly` (from `PlayerBody.UpdateFirstPersonBodyVisibility`) hides its Head (with the eyes and
  jaw), Chest and Hands bodygroups and turns off every garment that covers neither the legs nor the feet (helmet,
  shirt, vest, gloves). The trousers and boots stay. It holds through a re-dress (`Refresh`).
- Checked in the user's match on 2026-09-29, on a fresh spawn: the body's mesh mask 0 (the trousers and boots hide the
  legs and feet), the trousers and boots on and the other garments off. A body dressed before the code hotloaded in had
  every garment off, since it had no record of what it wore; a respawn fixed it. Not yet seen from the camera.

