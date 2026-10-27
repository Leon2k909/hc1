## Theater (match replays: `MatchRecorder`, `TheaterController`)
- The user asked for a Theater that doesn't lag, or else for it to be commented out and hidden. It was rewritten to
  stay light and kept: PROFILE (Barracks) → Theater (`/theater`, `TheaterPage`) lists the replays, and WATCH REPLAY
  sets the `theater_replay` cookie and loads `scenes/theater_playback.scene`.
- Recording (`MatchRecorder`, a `[RequireComponent]` of `GameMode`) runs on every machine that plays a match, so each
  player keeps their own replays. Settings → Game → Theater Recording turns it off (`GameSettings.TheaterRecording`,
  stored inverted, on by default); it replaced the `hc1_theater_no_record` ConVar. Battle royale, Zombies, dedicated
  servers and scenes without a MapInstance aren't recorded.
  - Only soldiers go in: every player's and bot's renderers (body, clothes, guns), from spawn until the body is removed.
    A living body records the anim graph parameters the game has set (playback runs them through the same graph at the
    frame rate), and a dead one its ragdoll's key bones. The map isn't recorded: the sidecar names the MapInstances.
  - 15 captures a second (`SampleRate`), at the end of the frame (`ISceneStage.End`). A player's body leaving its pawn,
    and a corpse coming to rest, restart that soldier's blocks (`Restart`), so a corpse's remaining time is constants.
  - A soldier's first capture sets up its tracks (reflection and generic recorders in the engine, the costly part), so
    soldiers who spawn together wait (`AdmitWaiting`, 2026-10-17): each capture takes new ones, players first, each with
    a capture of its own, while it's within 3 ms (`AdmitBudgetMicroseconds`), and always one. Those held back spawn a
    capture or a few later in the replay, and one that dies first isn't recorded.
  - Anim graph parameters playback can set are found once per graph (`GetGraphParameters`): finding them throws for the
    rest, which every 2 s for every body was a source of spikes. Build codes are worked out once a capture per gun,
    no longer, since nothing announces a build changing (a level-up, a camo colour).
  - It stops 3 s after the end-of-match screen or the map vote (30 minutes at most, or when the scene unloads), and
    under 20 s isn't saved. The log line "Theater: stopped after ..., N captures, X us on average, Y us at most" is the
    recorder's own cost.
  - Saving is one job on a worker thread (`MatchRecorder.Write`), never the main thread (it used to fall back to the
    main thread when the worker task was cancelled, which also happens when play stops). `TheaterReplays.WriteClip`
    serialises each life as a clip of its own through one reused `Utf8JsonWriter`, and `TheaterClipJson` lays its entry
    into the file's Tracks, so the whole clip is never one string (a 141 MB file was 282 MB in UTF-16). It also puts back
    what .NET's default encoder escapes and the engine's `Json.Serialize` doesn't ('+' in the base64 samples, quotes), so
    the file is byte for byte what `Json.Serialize` wrote; names with letters outside ASCII stay escaped (the same JSON).
    A clip not laid out as expected is written whole instead. Pruning runs on the worker too.
    - `dotnet run --project Tools/TheaterJsonChecks` checks the splicing against .NET's serializer with the engine's
      options (300 random clips byte for byte, Unicode, 600 lives, line feeds, bad layouts). In the editor,
      `Sources/Theater/editor/check-writeclip.cs.txt` (run_csharp) compares `WriteClip` with `Json.Serialize` on a saved
      replay, with times and allocations. Not run yet (2026-10-17).
  - Each living soldier's actions, for the first-person gun (`TheaterReplays.Actions`, `CaptureActions`), at each
    capture: what's in their hands (a player's `CurrentEquipment`, each time it changes, with its build code from
    `ExportWeaponBuildCode`; a bot's `WeaponResource`), and when they start and stop aiming (the "aiming" tag, a bot's
    `IsAimingIn`), sprinting (players only), reloading (`Reloadable.IsReloading`, a bot's `IsReloading`) and running
    dry. All of it is state every machine is sent. Shots come from the shot effects every machine plays
    (`MatchRecorder.NoteShot`, from `Shootable.DoShootEffects`, `Melee.DoEffects` and the bot's `DoShootEffects`),
    with whether they were suppressed. None of it is in the clip: the viewmodel isn't a soldier's renderer, and the
    body graph's `b_attack` and `b_reload` triggers are spent by the end of the frame.
  - The recorded build is the one the gun is drawn with on the recording machine (`Equipment.FitHolderBuild`): its own
    player's saved build, anyone else's shared one (`HolderBuild`), as it was when they drew the gun. Bots' guns have
    none. Before 2026-10-25 every player's gun wore the recording machine's saved build, and so did the replay's.
- Files (`TheaterReplays`), in the data folder: `replays/<yyyyMMdd_HHmmss>.movie` (the MovieMaker clip), `.json` (the
  sidecar: maps, mode, date, length, who recorded it, and each life's track, name, team and spawn, death and removal
  times) and `.actions` (the actions, by life track, with the builds listed once). The newest 20 from the last 7 days
  are kept (`Prune`, run by the page and after each save; it also deletes `.actions` left without a `.movie`), and a
  `.movie` with no sidecar is deleted once it's an hour old. The old Theater's `UnknownMap_*.movie` files are in the old
  `razed` ident's data folder, not this project's (`razedtest`).
- Playback (`TheaterController`) loads the MapInstances again (120 s timeout), parses the clip on a worker thread and
  drives the scene's MoviePlayer itself (`IsPlaying` false, `Position` set every frame).
  - Reading is one job on a worker thread (`TheaterReplays.ReadClip`), never the main thread. It parses the file's bytes
    with a `Utf8JsonReader` given the engine's comment handling and depth (512), skipping a byte order mark. It used
    `ReadAllText`, a string twice the file's size, which `Json.Deserialize` copied back to UTF-8, and fell back to
    parsing on the main thread when the worker task was cancelled (only once play has stopped). Every saved replay
    (11, 3-30 MB) parsed to the same JSON from bytes as from text (2026-10-17, offline).
    `Sources/Theater/editor/check-readclip.cs.txt` (run_csharp) compares the two in the engine, with times and
    allocations. Not run yet. The `.actions` (under 150 KB) are still read as text.
  - Don't hand the MoviePlayer the MovieClip itself: MovieMaker evaluates every track of a clip every frame, and a long
    match has tens of thousands. `TheaterClip` (an `IMovieClip`) lists only the lives within 0.5 s of the current time
    (`SetTime`) and disables the objects of those it drops. `ListAllTracks` is on only while the player creates every
    life's objects, once, on load.
  - The anim graphs run at the replay's speed (`SceneModel.PlaybackRate`; 0 when paused, but 1 for 0.35 s after a seek
    so the soldiers take their new poses). `ISceneStage.End` clears ragdoll bones left on a body after seeking back to
    when it was alive, and puts each bot's gun back in its hand: bots have no bone objects, so the gun is on a
    `WeaponHold` that `BotSystem.FollowHands` moves, and its recorded place lags the replayed hand.
  - `TheaterOverlay` is the HUD: the followed soldier on top; the timeline (`TheaterTimeline`, with the soldier's deaths
    marked), ±10 s skips and speeds from 0.25x to 4x below. Space pauses, F switches between following and freecam, A/D
    change soldier, the right mouse button looks around, and the wheel sets the follow distance or the freecam speed
    (freecam: WASD, E up, Q down, Shift fast, Alt slow). Escape leaves for the Theater page (`OnUpdate`).
  - First person (the user asked for it): X (the spectators' Change View, `SpectatorMode`) or the HUD's button
    switches between it and following from behind, and from freecam it follows in first person
    (`ToggleFirstPerson`). The view is the body's "eyes" attachment, looking along the recorded `aim_body`, at the
    player's field of view, and the soldier's renderers draw only their shadows. While they're dead it follows from
    behind. The right mouse button and the wheel do nothing in first person.
    - `TryGetEyes` takes the attachment in the body's space and places it with the body's transform. In world space
      it goes by the SceneModel's transform, which trails the MoviePlayer's moves: offscreen, where nothing ticks, it
      stayed where the body had been.
    - Players' `aim_body` has their view's pitch; bots' may stay level.
  - The first-person gun (`TheaterViewModel`, the user asked for it) is the held weapon's own viewmodel prefab, arms
    and all, placed at the camera each frame, and fitted with the recorded build (`GunsmithLoadoutManager.ApplyBuild`:
    while it fits, `_fitting` makes the loadout getters return the build's attachments, camo, finish and reticle
    rather than the saved loadout's). `ViewModel` works without an `Equipment`: its camera setup returns early, so
    `TheaterViewModel` sets its anim graph as `ViewModel` would from the actions and the replayed body:
    - deploy when the replay plays through a switch, `b_deploy_skip` when a seek lands on one;
    - `b_attack` and the muzzle flash, smoke and spent case for each shot played through (the flash and smoke rolled
      as `DischargeEffectState` rolls them, as that isn't recorded; the gun's own fire mode, as a switch isn't);
    - the reload (a shell at a time, timed from the gun's `Reloadable`, for a shell-by-shell one), `b_empty`, sprint
      (a bot's from its speed over 190), jump, the walk's bob at the footsteps' pace, and the lag as the view turns;
    - aiming: `ironsights_weight` over `AimTime`, the sights lined up as `ManualOffset` works it out for the fitted
      optic and rail, and the field of view narrowed by the gun's `AimFovOffset` (a magnified optic's as
      `Equipment.GetAimFovOffset`);
    - the SCAR-H's own parameters and sprint pose (`ViewModel.IsScarH`, `ScarHAimOffset`, `ScarHSprint*`);
    - its camera bone moves the view, scaled by the View Bob setting. Its animations run at the replay's speed.
    - A replay recorded before the actions existed has no `.actions`: the gun is the one found in the soldier's hand
      (its world model matched to a weapon's `WorldModelPrefab`), idle, wearing the viewer's saved build (a bot's
      none).
    - Not there: the crosshair and the hit markers, sounds (no replay has any), a magnified optic's picture in the lens
      (`OpticZoom` is the live camera's), grenades' pull and throw, and the SCAR-H's slow-walk bob.
- Not in replays: shots (bar the first-person gun's), tracers, muzzle flashes (bar the first-person gun's), impacts,
  sounds, grenades, dropped guns, doors, the kill feed and the score. Per-slot materials (`Materials.SetOverride`:
  camos, reticles, and parts that hide a piece of the gun, like the MP5 barrels' `HiddenWeaponMaterials`) aren't
  recorded either, so replayed world guns have no camo and can show hidden pieces (the first-person gun is fitted
  afresh, so it has them).
- Checked in-game 2026-09-27: the Theater page (empty list) and the settings switch. On 2026-09-28 and 29 the user
  recorded matches on Flatgrass and watched a replay. From the log and the files:
  - a 15-minute TDM (182 lives) came to 36 MB, at 1.4 ms a capture on average and 57 ms at most;
  - a 20-minute Deathmatch (1,100 lives) came to 141 MB.
  - Other logged matches had a capture at most of 160-410 ms (2026-09-30), and 286 ms on 2026-10-17.
- Not yet checked: playback's frame time, and first person in-game (the first-person gun compiled on 2026-09-29, and
  needs a new match recording to show fire, reloads and aiming). The 2026-10-17 recording and loading changes compiled
  with dotnet and hotloaded into the editor with no errors, but no match has been recorded with them and no replay
  loaded: neither the log line's average and maximum nor a replay made or loaded with them has been seen.

