## Tactical Defuse (`tactical_defuse.prefab`, verified 2026-10-14)
- The 20-second Freeze Time state must have its `EnableBuyMenu` component enabled. It was disabled, so B could
  never open the buy menu. Waiting has buying disabled; the round's buy phase is when purchases become available.
- `TacticalBuyMenu` opens when buying first becomes available. B (`ChooseClass`) toggles it, Escape closes it,
  and entering combat closes it and rejects purchases. Its `visible` class is managed with `SetClass` so closing
  also releases the overlay's input capture.
- Lightweight bots use `LightweightCombatBot.Tactical.cs`, with cash and retained equipment in `BotIdentity`.
  They start with the team's authored pistol and $800. Primaries must be purchasable for their team and affordable;
  armour and helmets deduct the same prices as player purchases. Tactical bots receive factory weapon parts.
- The bank receives team income after loss bonuses, weapon kill rewards and friendly-fire penalties, capped at
  the mode's maximum. Death clears equipment; surviving weapons and remaining protection carry into the next round.
  Half resets clear gear and reset cash, and the roster follows the side swap.
- Both bot round-mode checks include `tactical_defuse`. Round respawn saves survivors before clearing their old
  positions, then fills after 0.1 seconds in the buy phase. Combat cannot replace killed bots.
- Verified against the loaded engine in temporary scenes: 18 lifecycle/spawn checks and 9 UI/input checks,
  plus the existing 34 purchase/RPC/protection checks. The real menu was captured through native `ui_screenshot`,
  and native simulated B closed and reopened it. Reports are in `output/tactical-defuse/buy-menu-fix/`.

