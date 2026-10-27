## Play-start stalls in the editor (network file hashing, 2026-10-15)
- The user saw the editor stall for 300+ seconds on most play starts. `GameNetworkManager.OnStart` creates a lobby on
  every play start, and the engine then runs `BuildNetworkedFiles` on the main thread. It reads every file a joining
  client could download and takes a CRC64 of each (`LargeNetworkFiles.AddFile`). A file counts if it's compiled (`_c`),
  `.scss` or `.ttf`, or if it matches hc1.sbproj's `Resources` patterns. Those patterns are also what a publish uploads.
  - `WildcardMatch` ignores case, and its `*` crosses folders. The game's file system mounts Code as well as Assets,
    so `/UI/*` sent Code/UI's .razor and .cs files.
  - `/weapons/*` took in every source file under Assets/Weapons: 1.26 GB of DMX, 790 MB of PNG, WAVs, .blend, FBX and
    SMD files.
  - With the old patterns it was 18,639 files and 5.84 GB a play start. The recorded stalls lasted about 6-7 minutes
    (`output/belltower/quality/startup-recovery/editor-stall-16792*`).
  - Since 2026-10-15 the patterns are `/ui/*.png|jpg|svg`, the fonts, and the swb icon PNGs the swb prefabs name by
    path. That's 9,840 files and 3.64 GB, nearly all of it compiled assets clients need. Since 2026-10-17 only the
    SCAR-H's (`weapons/swb/scarh/scarh.png`) is left: the other five swb guns (Colt, L96A1, Remington 870, Revolver,
    Veresk) were unused and were removed. The SCAR-H still uses `weapons/swb/hands` (its viewmodel's gloves and
    sleeves) and `sounds/swb/animations` and `clip`, and the game uses the swb code, muzzle effects and suppressed
    shots, so those stay.
  - The engine adds the patterns to its list on every play start and never clears it, so the old ones apply until
    the editor restarts.
  - Don't put a folder-wide pattern back. List the raw files that code loads by path.
- Since 2026-10-15 editor play makes no lobby (the user asked for it): `GameNetworkManager` joins the local player
  offline, as `IsMultiplayer` false does (the firing range's scene). So editor play skips the scan and the cloud
  references below.
  - `hc1_editor_lobby 1` (saved) makes editor play host again from the next play start, with the scan.
  - The editor's Start Hosting still hosts. Start it in the main menu before a map loads, as for the second-instance
    tests (see Map changes with players connected). Hosting partway through an offline match hasn't been tried.
  - Ranked makes its own lobby, so it's unchanged. A custom game started in the editor plays offline unless the
    ConVar is on.
  - Only `Game.IsEditor` changes: a real game hosts as before.
  - Compiled with dotnet, not yet tried in the editor.
- After the lobby comes up, the engine adds the scenes' 51-52 cloud references to the ServerPackage table, which took
  10-20 s each time.
- Every map but Reef Hall builds its navmesh at load. The 23:28 stall's stack had the navmesh's load in its chain.
- Two of the last eight GPU crashes (VK_ERROR_DEVICE_LOST, 2026-10-14 and 15) faulted in the engine's
  `envmap_filtering_cs`. That's the reflection probes' filtering, which runs for every realtime probe as a map loads:
  Reef Hall has 14, Lowtide, Railhead and Cerro Blanco 11, Riverdale 9, Boxyard 7 and Ares 4. Belltower's three are
  baked. Earlier crashes faulted in the UI's `ui_cssbox_batched` (2) and `foliage` (1).
- On 2026-10-14 sessions rewrote map OBJs while the user played. Loading those maps then recompiled the models on
  demand: `lowtide_finish.vmdl` six times in an hour, each taking 4-15 minutes.

