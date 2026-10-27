## Zombies, doors and players (`ZombieAI.KeepOut`)
- The user (2026-10-01): zombies walked through doors on Innocent Hotel, and players got stuck in Zombies.
- Doors: a NavMeshAgent moves a zombie with no collision, and doors are left out of the navmesh (the `door` tag), so
  paths go through doorways. `MapMover.FindDoorAhead` stopped a zombie only for a door within 80 straight ahead, so one
  coming at a door from an angle walked through it. Now each host update `KeepOut` sweeps a 16-unit sphere at the waist
  along the agent's last step. If it meets a door that's less than `OpenEnough` open, the step is taken back
  (`Agent.SetAgentPosition`) and the zombie opens the door and waits for it, as `WaitForDoor` does. A step that starts
  inside a door (one shut on it) isn't stopped.
- Players: zombies walked up to the player's centre. Once a zombie's capsule (16) was over a player's box, the box
  started solid, and `CharacterController.TryUnstuck` hopped them about on the spot.
  - A zombie now stops at `StandOff` (40, horizontally) from its target to swing, inside its 64 reach.
  - `KeepOut` takes back any step that brings it within `PlayerClearance` (34) of a living player, downed ones included,
    and it goes for whoever that was.
  - A player whose box starts inside a zombie walks through zombies until clear of them all
    (`CharacterController._throughEnemies`, the `enemy` tag).
- Not yet checked in-game.

