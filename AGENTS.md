# Project location

The canonical checkout is `C:\sbox-projects\hc1\forked-shooter-main`.
Use that C: path for shell working directories, editor connections and project work.
The former `D:\Documents\s&box projects\hc1\forked-shooter-main` path is a
compatibility junction to the same files on C:, with no separate working copy.

# Editor control

**Never start a second s&box editor.** Two editors at once (or one beside other heavy work) freeze the user's PC:
it has 32 GB of RAM, one hc1 editor in a match uses about 16 GB, and Windows then pages to a hard disk until the
machine locks up (hard resets on 2026-11-12 at 18:43 and 20:57 both had two editors running). Before any launch,
check `tasklist | findstr sbox-dev` (or `Get-Process sbox-dev`); if one is running, attach to it or ask the user.
This includes `sbox-cli --project`, test projects and retries after a failed `--connect`. Keep only the scene tab
you are working on open (Depot alone streams about 3 GB of textures).

Use the engine-provided `sbox` skill and native s&box MCP as the primary editor connection.
The configured server is `sbox`; if its tools are not loaded in the current chat, use
`sbox-cli --call` from this project. Resolve the executable through `FACEPUNCH_ENGINE`
(including the Windows user environment) and read the installed `--skill sbox-cli`.
Prefix shell commands with `rtk`, as required by the user-level instructions.

- Start with `editor_status`. Verify `Paths.ProjectRoot` matches this checkout, then inspect
  compile state, active scene, unsaved changes and play state before acting.
- Discover tools with `search_tools` or `list_toolsets` / `describe_toolset`; use their actual schemas.
- Prefer native scene, component, asset, Hammer, UI, network and performance tools. Use
  `run_csharp` for operations they do not cover, with scripts in the session exchange directory
  rather than temporary editor source files or frame callbacks.
- The `bridge_helpers` native toolset preserves all registered Claude Bridge helpers in process.
  Use `bridge_list_handlers`, then `bridge_describe_handler` for parameters and restrictions.
  Use `bridge_read` for read-only helpers and `bridge_call` for specialised mutations.
  `bridge_simulate_input` and `bridge_scatter_props` provide explicit parameter schemas.
- Prefer the native route to those helpers. The existing `sbox_claude_bridge` connection remains
  a fallback if the native connection is unavailable; do not dispatch the same mutation through
  both connections or retry a timed-out mutation before inspecting its result.
- Helper calls retain Bridge's play-mode guards and original undo behaviour. Do not promise
  automatic undo for arbitrary scripts or Bridge handlers. Keep the user's scene and play state
  during integration checks; stop play when required by an authorised scene-editing task.
- When the editor is open, edit scenes, prefabs and resources through it. After C# changes,
  wait for compilation and check `compile_status`. Verify visual edits with screenshots and save
  scene edits when the task requires them to persist.
- Attach to the existing editor with `--connect` / `--call`. Use `--project` only for a requested
  launch: an editor owned by that CLI closes when the connection exits.

# Visual reviews: use the actual viewport

- User preference (2026-11-06): retain all created model and material variants for
  possible reuse, including unselected proposals. Removing replaced geometry from
  an active map does not mean deleting reusable assets or historical variants.
- User preference (2026-11-06): use native s&box frame captures for before/after pictures
  without Computer Use. This applies across chats; do not invoke Computer Use for visual
  reviews unless explicitly requested. Use native `bridge_call` with `command=screenshot_game`
  for a direct window capture (works while occluded). Discover/describe that handler first.
  If `ScreenshotService.RequestCapture()` does not write a frame, use this native window
  capture before asking the user to bring the editor into view.
- User preference (2026-11-05): visual judgments, upgrade recommendations and before/after
  reviews must use the actual running game view or live editor viewport as displayed on screen.
  Prefer a direct capture of the existing application window. Confirm the correct project,
  scene and view first. A native MCP connection alone does not make a render representative.
- Do not create temporary cameras, clone or isolate scenes, call `RenderToBitmap`, or change
  exposure, lighting, post-processing or render settings to produce review evidence. Screenshot
  helpers that create cameras or rerender a view are subject to this same restriction.
- Temporary/offscreen renders are allowed only when the user explicitly requests that type of
  preview. Label them clearly as temporary/offscreen previews; never present them as game or
  editor viewport captures or use them to claim how the map looks during normal play.
- For comparisons, use the same real viewport camera, framing, lighting and display settings.
  If an actual viewport capture is unavailable, state that limitation and defer the visual
  judgment instead of substituting a temporary render. Keep the user's scene/play state.
- Verified native frame capture: `Sandbox.ScreenshotService.RequestCapture()` captures the
  currently displayed scene layer and returns a path under the engine's `screenshots` folder.
  Verify the saved image shows the intended scene; another tab may have become active, and a
  background/minimized editor may not write the requested frame until it displays again.
  `editor_camera_screenshot` uses `RenderToBitmap` and is not a substitute for this workflow.

`CLAUDE.md` contains subsystem notes and verified asset values. Read the relevant sections
before changing those systems. Keep work single-agent and follow the existing local
performance hygiene instructions.
