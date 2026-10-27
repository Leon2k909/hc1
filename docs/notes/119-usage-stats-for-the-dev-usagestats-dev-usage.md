## Usage stats for the dev (`UsageStats`, `dev_usage`)
- The user (Leon, the dev) wants to see which guns, attachments, camos and perks players use, to know what to change.
  Each human life in a mode with classes counts once, on the player's own client (`PlayerPawn.OnClientRespawn` →
  `UsageStats.CountLife`), `PlayerLoadout.ClassSwapWindow` (5 s) after spawning, so a class picked just after spawning
  counts. The stats are s&box's, and their global totals add every player's up. They're all `use-...`:
  `use-lives`, `use-gun-<weapon>`, `use-att-<weapon>-<part>` (part file names repeat across weapons),
  `use-camo-<camo>|none|custom`, `use-perk-<perk>`, and `use-kill-<weapon>` (sent from `WeaponStatsRule`).
- `dev_usage [filter]` prints them from the published game's global stats (`GetGlobalStats( "verarp.razedtest" )`, since
  `Stats.Global` reads 0 in the editor) and writes `usage.csv` to the data folder. On 2026-09-29 it read 97 global
  stats from the editor, and no `use-` ones yet: they only start once a build with this is published.
- `WeaponStatsRule` now skips bots, as `PlayerStatsRule` does: the host owns bot pawns, so every bot kill was going to
  the host's `kills-<weapon>` and weapon XP.

