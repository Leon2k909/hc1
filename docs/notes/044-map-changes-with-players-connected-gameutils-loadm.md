## Map changes with players connected (`GameUtils.LoadMap`)
- The user hosted from the editor's network menu (Start Hosting) in the main menu, joined with Join via new instance,
  then started a TDM from the host. The second instance was left in freecam on Flatgrass (2026-09-30).
- `Scene.Load` only loads on the machine that calls it; the engine's docs say so. After it, the host's own
  `OnJoined(Connection.Local)` makes the host's Client, and nobody else's. It also network-spawns the new map's objects
  into the clients' old scene, which is how the second instance saw Flatgrass. With no Client, `SpectateSystem` fell
  back to freecam.
- `Game.ChangeScene` loads with those spawn and destroy messages suppressed, then `LoadSceneBroadcast`s the scene. Each
  client loads it, and when it's done the host's `OnSceneLoadedMsg` runs `OnJoined`, so `GameNetworkManager.OnActive`
  makes its Client. Read from Sandbox.Engine.dll's IL on 2026-09-30.
- `GameUtils.LoadMap` uses `ChangeScene` on a networked host, and `Scene.Load` otherwise. It's used by
  `MatchLauncher.StartMatch` (the hub, playlists, the map picker), `PregameLobbyManager.StartMatch`, the map vote's next
  map, and `dev_quickplay`, `dev_zombies`, `dev_defuse` and `dev_mode`.
- Local loads stay `Scene.Load`: the main menu, the gunsmith, Theater, `dev_scene`, and the custom game and Ranked, which
  leave or make their lobby first.
- Two instances on one Steam account work, since `Client.IsLocalPlayer` goes by the connection. But the map vote keys
  votes by Steam ID, so they count as one voter.
- Tried with a second instance on 2026-09-30: it followed the host into the TDM and played in it.
- A second instance from Join via new instance loads the game's files from the editor over the network. That took over 5
  minutes, and hundreds of compiled files came up missing there (ERROR_FILEOPEN), though they're on disk:
  - the newer guns' prefabs and `.equip`s;
  - sound events;
  - gunsmith parts;
  - `first_person_arms.vmdl_c`.
  So that instance can show no first-person gun, or play no sounds. The cause is how the editor serves the files, not
  the game.
- The main menu's background map (`menu.scene`'s MapInstance, the cloud map `facepunch.depot`) is missing its lightmaps.
  While the menu is up, the log gets "Unable to stream in resource file maps/depot/lightmaps/..." about 100 times a
  second. It's harmless, and it comes from Facepunch's package.

