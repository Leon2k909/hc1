## Jump stamina (`PlayerPawn.Movement.cs`)
- Like CS2's, which the user asked for: each jump takes 15% of the jump speed left (`JumpFatigueCost`), so jumping
  again as you land goes 100%, 85%, 72%, 61%, 55% of full speed (about 50, 36, 26, 19, 15 units high), never below
  55% (`MaxJumpFatigue`). It wears off only on the ground, at 0.375/s: a full jump again ~0.4 s after one jump,
  ~1.2 s after many. Owner-side only (the pawn moves itself); bots don't jump.

