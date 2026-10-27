## Teams: Red Team and Blue Team
- The user renamed the teams: `Team.Terrorist` is Red Team (was Anarchists, red "A" logo) and `Team.CounterTerrorist`
  is Blue Team (was Security/Operators). The enum keeps its old names because scenes and prefabs store them.
- The logos are the user's art (`Tools/team_logo_sources/`). `Tools/team_logos.py` builds `ui/teams/<red|blue>_team_logo.png`
  (the icon) and `_banner.png` (spawn banner) from them. The old `anarchists_*` / `operators_*` art stays, because the
  menus use `operators_logo_banner.png` as the game's brand logo. Show names through `Team.GetName()`, never hard-coded strings. A team win banner always reads
  "<GetName()> Wins!" (`Toast.Headline`/`Accent`), whatever the game-mode prefab's message says. While it's up,
  `MainHUD` hides everything else (`Toast.IsWinShowing`), including the end-of-match freecam's spectate panel.
- A team's colour means that team to every viewer (`TeamExtensions.GetColor`; Red 228,32,40, Blue 5,146,235). Red is
  the logo's pure red: the old 235,64,52 read as orange. Enemy markers and minimap dots use the enemy's team colour,
  not a generic red, which would look like Red Team's teammates. Scoreboard bot rows, avatars and AI/BOT tags take the
  bot's team colour (`ScoreboardRow.BotRowStyle`). `$terror-color` in Theme.scss is the UI's amber accent, not a team
  colour.

