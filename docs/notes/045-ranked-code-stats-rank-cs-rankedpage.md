## Ranked (`Code/Stats/Rank.cs`, `RankedPage`)
- The only rating is the SR you can see (`razed.rank.sr` cookie); there's no hidden MMR. Six tiers of 600 SR (Bronze
  to Master), and every tier below Master has divisions III, II and I of 200 SR (`GetRankName`: "Gold III"). A win is
  +25 and a loss -20. Ranked lobbies are named with the tier (`MatchTag`, "[R:GOLD]"), and matchmaking only joins a
  lobby with the same tag. `Rank.RecordResult` isn't called anywhere yet, so SR doesn't change in play.
- A season is three calendar months, starting with Season 1 in September 2026 (`SeasonOneStart`). `CheckSeason` runs
  when the page opens and on Play Ranked. The first time in a new season it drops SR one tier, keeping the division, and
  restarts the season high (`razed.rank.season_high`). The first check on a machine only records the season.
- `RankedPage` (the RANKED tab), in the hub's style with no map picture:
  - Under the title, a COMING SOON notice (`.ranked-notice`), which the user asked for (2026-10-05). PLAY RANKED still
    works. Not yet seen in-game.
  - Left: your rank, Play Ranked, the season's countdown and high, and the rules. The rules restate `Rank.cs`, so change
    them together.
  - Middle: a ladder of the six tier emblems with yours lit, then the map pool. The pool is `GameUtils.GetMatchMaps()`,
    each map in its ranked mode: Defuse where the map has bomb sites, else TDM. The host picks a random map from it.
  - Right: `HubSidebar`, sized in RankedPage.razor.scss.
- The emblems are `Assets/ui/ranked/<tier>.png`, drawn by `Tools/rank_emblems.py` (numpy + PIL): a metal shield in the
  tier colour, with more trim for each tier. Keep its colours in step with `Rank.TierColors`.

