## Sprint and fire (`PlayerPawn.IsPullingTrigger`)
- Firing breaks a sprint (unless aimed), but only a press the gun takes counts (`WeaponInputAction.IsTakingInput`).
  It used to go by the raw button.
  - Fire held through a respawn (clicking past the deathcam) is ignored by the new gun until it's let go
    (`RunningWhileDeployed`), so the gun wouldn't shoot, but the raw button still stopped every sprint.
  - The user found they had to shoot before they could sprint (2026-10-02).
  - A click in the class menu doesn't count either.
  - Aim is the exception (`Aimable.TakesInputHeldThroughDeploy`): right-click held through a weapon switch aims the gun
    switched to (the user, 2026-10-12). Not in toggle-aim mode, where the held press would toggle it. So aim held
    through a respawn is blocked until release (`PlayerPawn.HasReleasedAimSinceRespawn`). The owner's respawn RPC
    clears aim/scope tags and each weapon's cached input, including a reused pawn's inventory. Deploy events reset only
    the deployed weapon's input; the first locally controlled update still handles deployment before possession.
    Native MCP checks covered held and toggle aim, new and reused pawns, scope/tag cleanup, delayed possession,
    death, and preserving held aim through ordinary weapon switches (19 checks, 2026-10-13).
- A new pawn's gun can be deployed before the pawn is possessed (`OnClientRespawn`'s RPC comes after), so the deploy
  event never noted the held button. `WeaponInputAction` now works it out on its first update as the owner's
  (`_heldInputChecked`).
- Compiled offline, not yet checked in-game. To check: die, hold fire through the respawn with W and Shift down. You
  should sprint, and the gun should only fire once fire is pressed again.

