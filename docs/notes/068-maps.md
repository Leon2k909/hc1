## Maps
- Match maps (map picker, Quick Play, end-of-match vote) are `GameUtils.IsMatchReadyMap`: Flatgrass, Innocent Hotel,
  Belltower, Reef Hall, Railhead, Lowtide, Boxyard, Cerro Blanco, Riverdale, Ares, Collider and Veridant (see their
  sections below).
- The hub (`HubPage`) is one featured screen for the tab picked on its left rail (`HubModeRail`, `HubPage.Operation`:
  Multiplayer, Battle Royale or Zombies; Campaign is locked), like the user's CoD-style mockup. Its art is
  `ui/modes/<mode>_wide.png`, a 1024x720 cut of the 2:3 card art. Battle Royale has no wide cut or blurred backdrop, so
  HubPage.razor.scss shows `battle-royale.png` in a layer of the art's own 2:3 shape (`aspect-ratio`, moved up with
  `top`) and blurs it for the backdrop. Its screen has PLAY, then MAP cards (`br_map`: Flatgrass or Ridgeback) beside
  the FIELD SIZE cards (`br_bots`), in one row (`.royale-options`) so the featured screen keeps its height.
- Quick Play (the featured screen's PLAY NOW) picks a random mode from those ticked in the filter that opens when you
  hover PLAY NOW's row, then a random ticked map that has it (`QuickPlayFilter`). The
  cookies store the modes and maps left *out*, so new ones start ticked, and at least one of each stays ticked.
  PLAY NOW is the outlined orange button the old hub cards had (the user asked for it back instead of a filled DEPLOY).
- Under the Multiplayer hero is a POPULAR PLAYLISTS row (the user asked for "popular", not the mockup's "featured"):
  the top 4 modes by the global `wins-<ident>` stat's player count, then a curated order (`PopularPlaylists`). Only
  the modes with `SendExtraGameModeStat` send that stat, and global stats read 0 in the editor, so there it's always
  the curated order. A card starts its mode on a random map (ticked ones first). Card art is
  `ui/modes/playlists/<ident>.png`, 1.7:1 cuts of the key art, named in HubPage.razor.scss by class so it's packaged.
  Swap in real per-mode art there if the user supplies it. The hero's PLAYLISTS link and the row's VIEW ALL open
  every mode's card in an overlay on the hub (`_showingAllPlaylists`): the old Multiplayer page (`/multiplayer`,
  LandingPage) was removed. Matches start through `MatchLauncher.StartMatch`.
- The end-of-match vote (`MapVoteSystem`, `MapVoteOverlay`, `MapVoteCard`) offers each match map once, in the mode
  just played: players vote on the map, not the mode. Options are networked by `GameMode.GetPrefabPath`: the modes are
  prefab roots with no `PrefabInstanceSource`, which made every option TDM. A tie, or no votes at all, is settled at
  random, and `WinnerIndex` is synced for the cards. Don't put `hud` on the overlay's root: its `pointer-events: none`
  and `cursor: none` made the cards unclickable and hid the cursor. A card's `.art` must stay `position: relative`:
  absolute panels go by the nearest positioned ancestor, so the map name landed in the screen's corner over the hint.
- The vote's ScreenPanel is ZIndex 999 and the pause menu's 1000 (`PauseMenuPanel.ScreenZIndex`, set in its OnStart
  over the prefabs' 999), so Escape over the vote opens the pause menu on top. At 999 each, the vote, made later, drew
  over the menu (the user's screenshot, 2026-10-02). Compiled offline, not yet seen in-game.
- Vote card pictures (`MapArt`) are the scene's `MapInformation.Image` if it's a wide screenshot (at least 960 px wide
  and 1.5:1), otherwise the wide thumbnail of the cloud map its MapInstance loads (`Package.FetchAsync`), cached.
- Under the maps, the vote offers every other mode (PLAY A DIFFERENT MODE, the user's ask): the playlists
  (`PopularPlaylists.Top`, each on `PopularPlaylists.PickMap`), battle royale on the hub's `br_map` and Zombies on a
  random Zombies map, less the mode just played.
  - A card leaves the lobby and starts that mode the way the hub does (`MatchLauncher.LeaveAndStart`:
    `Networking.Disconnect`, wait until it's inactive, then `StartMatch`), so the player hosts a new match with bots.
    Unranked play has no matchmaking queue to join.
  - Meanwhile `MapVoteSystem.IsLeaving` stops the vote moving that machine on: once the lobby's gone, a client's copy
    would run the host's side and load the winning map over the new mode's. A failed leave clears it again.
  - Every lobby is made with `DestroyWhenHostLeaves` (true in `new LobbyConfig()` too), so a host who leaves closes the
    lobby for everyone. The row says so when anyone else is in it.
  - The cards' art is `Code/UI/Styles/ModeArt.scss`'s `mode-art` mixin, shared with the hub's playlist cards.
  - Not yet checked in-game. `hc1_dev_mapvote` opens a vote in a running match.
- Innocent Hotel (`scenes/maps/InnocentHotel/innocent_hotel.scene`, cloud map `thieves.innocent_hotel`) is a TTT map. All
  its own spawns are in one room, and its basement and roof are reached by teleporters, so the scene has hand-placed
  team spawns (T west wing, CT east wing), and its `MapSpawnSettings` turns off map spawn points and bot navmesh spawns.
- Keep spawns out of the traitor room (the red room behind the west-wing elevator lobby's west wall, x < -1580): its
  secret door (`T room Door 4`, `AllowDirectUse` false) opens for nobody, so anything spawned there is trapped.
  T Spawn 5 was in it, which slowly trapped the whole T bot team there, with the CTs piled up against the lobby wall.
  Every spawn must have a Complete navmesh path to the other team's spawns.

