# Three-model trial — shared brief (2026-11-06)

The user asked for **three parallel sessions, each rebuilding one crude 3D map model**, with a matched
**BEFORE / AFTER** from the real game/editor viewport "in case the new one is not good". When all three
finish, the orchestrator session ("3D map model improvements", id `3a5dab`) compares the three models by
polygons, texture size and so on — so your numbers must be measured the way section 5 says.

| Session name | Map | Fallback map if the first has nothing crude and visible |
|---|---|---|
| `boxyard-model` | Boxyard (`Assets/scenes/maps/Boxyard/boxyard.scene`, `Tools/boxyard_map.py`, models in `Assets/models/maps/boxyard/`) | Sewage |
| `reefhall-model` | Reef Hall (`Assets/scenes/maps/ReefHall/reefhall.scene`, `Tools/reefhall_map.py`, models in `Assets/models/maps/reefhall/`) | Orion |
| `spillway-model` | Spillway (`Assets/scenes/maps/spillway/spillway.scene`, `Tools/spillway_map.py`, models in `Assets/models/maps/spillway/`) | Riverdale |

These three maps were picked because their generators have had the fewest detail passes (Boxyard 5 scripts, Reef Hall 12,
Spillway 14, against 60-120 for Lowtide/Railhead/Belltower/Veridant), so crude geometry is most likely left there.
Already done, so do not repeat it: Boxyard gantry crane, pipe stacks, IBC totes, oil drums, cones, wheelie bins, skip,
shipping crates; Reef Hall benches, info stands, pump, wall light, pedestal, planter, office chair/desk/doors (coral
rejected; whale skeleton is a pending candidate); Spillway control desks, cargo pallets, canvas cover, hose coil, wall
vent, roof fans, trench grates, service cabinet.

Do the work yourself, in this session; do not start further sessions. A peer session, "3D map model
improvement" (`local_e0b8bab8-94e5-4a00-a572-209116cce154`), is busy on **Riverside's** spawn-pad watch deck:
do not touch Riverside's files, models or scene. Also leave Veridant, Cerro Blanco, Belltower, Lowtide and Railhead alone
(already heavily upgraded), and the other two sessions' maps.

## 0. Read first
1. `CLAUDE.md` (key rules) and `AGENTS.md` — "Editor control" and "Visual reviews: use the actual viewport"
   are mandatory.
2. Memory files in `C:\Users\leon2\.claude\projects\C--sbox-projects-hc1-forked-shooter-main\memory\`:
   `pick-props-that-actually-look-bad.md`, `compare-assets-in-engine.md`, `prop-distance-look.md`,
   `hyper-real-textures-from-scans.md`, `shared-editor-sessions.md`, `sbox-hotload-gotchas.md`,
   `offscreen-capture-vram.md`, `reset-dev-toggles.md`.
3. How earlier upgrades were done: `Sources/Veridant/forecourt-posts-v1/README.md`,
   `Sources/Railhead/help-point-v1/README.md`, `Sources/Ares/control-console-native-v1/`, and your map's
   generator in `Tools/`.

## 1. Choose the model (the user's rules)
- Pick ONE prop that looks genuinely **bad** (flat boxes, no bevels, blocky cylinders, stretched or solid-colour
  texture) and that a player sees **up close at eye level on a main route or at a frequently used spot**. No hidden
  rooftop/background details. Small detail passes are not enough: the change must be a clear, substantial step up (a real rebuild, or a swap to a clearly better existing model).
- Look at it in the real editor viewport first (section 4) and shortlist 2-3 candidates; take the worst and most
  visible. Do not rebuild something already decent (the user rejected a rebuild of Railhead's luggage trolley: "before
  is better"). Keep the old one's colour identity and wear contrast.
- Check what exists before building: the index in `CLAUDE.md`, `Sources/<Map>/`, `Assets/models/props/**`. The project
  rule is to reuse a suitable approved model or review candidate, and the user added (2026-11-06): "you can use existing
  textures or models if we have a better one, you dont necessarily need to make new ones every time". So search first
  (`CLAUDE.md` index, `Sources/**/README.md`, `Assets/models/props/**` including `*_v2` props from other maps and
  `models/props/shared/**`, and `Assets/materials/**` for textures/scan sets). If something existing is clearly better
  than the bad prop, adapt it (scale, material remaps, LODs, collision) instead of building from scratch; it must still
  suit this map's colours, scale and materials. Build new only where nothing suitable
  exists.
- No Call of Duty names, logos or markings. Match the map's existing materials and lighting (a new prop has to sit in
  its map, not just look good alone).

## 2. Build
- If you reuse a better existing model, adapt it and go to section 3. Otherwise build a standalone model
  (OBJ + MTL -> `.vmdl` with material remaps, as in the earlier work), real proportions in
  inches, bevels/curves in the silhouette (spend triangles on silhouette, not padding), sensible **LODs**
  (see `prop-distance-look.md`: review at 12-40 m too), and collision that keeps the old behaviour (do not make a
  route impassable for bots; test collision with rays as well as by eye).
- Textures: reuse an existing project material/scan when one fits (`Assets/materials/**`, the scan sets). Where
  nothing fits, make them from the project's real scans at about 40 px/in for the surfaces seen close, strong values, soft wear
  masks; keep bold colour (not paler or cleaner than the old one). Choose texture resolution by the texel density
  needed, and say what you chose.
- Files: models in `Assets/models/props/<map>/<name>_v1/`, materials in `Assets/materials/<map>/<name>_v1/`,
  sources, generator, README and `revert.py` in `Sources/<Map>/<name>-v1/`.
- **Keep the old geometry/asset.** If the old prop is baked into a merged map model, extract its faces to an
  `old_*.obj` (that is also your BEFORE geometry for the numbers), cut them from the render model only through the
  generator/script, and keep collision unchanged. Write a tested `revert.py` that restores the old state exactly.
  Delete nothing: the user decides whether to keep the new one.

## 3. Install
Install it into the live scene (all instances of that exact prop if a script makes that cheap, otherwise the ones on
the main route; say which and how many), let the editor compile it, check the log for errors, save the scene, and
leave no temporary objects, play sessions or dev toggles behind.

## 4. BEFORE / AFTER pictures (hard rules from AGENTS.md)
- Native frame capture of the actual editor viewport/game window (AGENTS.md: `bridge_call` with
  `command=screenshot_game`, or `ScreenshotService.RequestCapture()`; describe the handler first). Check the image
  shows the right scene. **No** temporary cameras, isolated/cloned scenes, `RenderToBitmap`, `capture_view`, changed
  exposure/lighting/post settings, Blender renders or Computer Use as evidence.
- Same camera position, framing, lighting and display settings for BEFORE and AFTER. At least one close view and one
  ~12 m play-distance view of the same spot. Make sure the new textures have streamed in before the AFTER shot
  (`MarkUsed` on just that model's textures, `offscreen-capture-vram.md`). Never `MarkUsed( 4096 )` a whole map.
- Save them as `output/model-trial-20261106/<map>/before.png`, `after.png`, `before_far.png`, `after_far.png`.

## 5. Numbers (so the three sessions are comparable)
Use `Tools/model_stats.py` (read its docstring) for BOTH the old and the new model and quote its numbers:

```
python -I Tools/model_stats.py --label BEFORE --obj <old.obj> --vmat <old materials ...> --json Sources/<Map>/<name>-v1/stats_before.json
python -I Tools/model_stats.py --label AFTER  --vmdl models/props/<map>/<name>_v1/<model>.vmdl --json Sources/<Map>/<name>-v1/stats_after.json
```

For BEFORE use the old prop's own faces (the `old_*.obj`) and the textures its materials really use; if those are
shared map atlases, list them and mark them `shared`. If AFTER reuses an existing model or textures, say so with their paths and still report their numbers. Report this table
in your README and in your final message:

| | BEFORE | AFTER |
|---|---|---|
| LOD0 triangles / vertices | | |
| LOD1 / LOD2 triangles (switch thresholds) | | |
| Materials / unique texture files | | |
| Largest texture (px) | | |
| Total texture pixels (MP) | | |
| Est. GPU texture memory (MB, RGBA8 + mips) | | |
| Compiled `vmdl_c` / `vtex_c` total (KB) | | |
| Object size (in / m) | | |
| Instances in the map -> total LOD0 triangles added | | |
| Collision (hulls/boxes) | | |

## 6. Shared editor rules (3 sessions + the Riverside peer use ONE s&box editor)
- Do the heavy modelling offline (Python/Blender: the Blender MCP may be available); touch the editor only in short
  bursts.
- **Editor lock.** Before you change the front scene (`load_scene`), move the viewport camera, start/stop play or
  hotload a snippet for a capture, take the lock: `mkdir "C:/sbox-projects/hc1/forked-shooter-main/output/editor-lock"`
  in Bash (atomic: it fails when held; wait 30 s and retry; treat it as stale only when older than 10 minutes). Put
  your session name in `owner.txt` inside. First read `editor_status` `ActiveScene` and the viewport camera pose;
  afterwards restore exactly that scene and pose, then delete the lock. Hold it for minutes, not hours.
- Never stop or start a play session you did not start (it may be the user's own match: then wait and carry on offline).
- **Do not commit, push, stash, switch branches or `git add -A`:** the working tree holds ~800 other uncommitted
  files. Edit only your own files and list them at the end.
- Never force-compile a big map model; after any timed-out snippet check `Editor/__Exec_*` leftovers.

## 7. Final message (the last thing you write — put the key line first)
1. One line: model, map, where it is, how many instances.
2. BEFORE and AFTER images (same camera): send both with `SendUserFile` (`display: "render"`) and give their paths;
   also the far pair.
3. The stats table from section 5.
4. Files created/changed, how to revert (`revert.py`), what you could not verify.
5. An honest verdict: is the new one clearly better, and where is it weaker? The user may reject it.
