## Play areas ("Return to the AO", `PlayArea`)
- A map scene can mark its play area with `PlayArea` zones (Belltower, Depot, Edinburgh, Motel and Refinery do). A
  player outside all of them for 5 s is killed (`PlayerPawn.UpdatePlayArea`). A scene with none has no limit.
- A scene's GameObjectSystems outlive `Scene.Load`, so `PlayAreaSystem` counts only live play areas, and each one leaves
  the list when it's disabled. It used to keep them: once a play session had loaded one of those scenes (the one open
  in the editor when play started, say), every later map counted as outside the area, and on Flatgrass the player died
  5 s after every spawn. Fixed 2026-09-29, and checked live in the user's match: no more kills after the hotload.
- `UpdatePlayArea` runs on the host, which used to judge only its own pawn: a client could stand outside the area
  forever. Since 2026-10-01 the host judges every real player's pawn (`OnFixedUpdate`, bots excluded).
- 1v1 and 2v2 Skirmish on a big map use their arena's circle instead of the map's zones (see Skirmish).

