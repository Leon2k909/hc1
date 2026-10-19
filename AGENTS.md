# Project location

The canonical checkout is `C:\sbox-projects\hc1\forked-shooter-main`.
Use that C: path for shell working directories, editor connections and project work.
The former `D:\Documents\s&box projects\hc1\forked-shooter-main` path is a
compatibility junction to the same files on C:, with no separate working copy.

# Editor control

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

`CLAUDE.md` contains subsystem notes and verified asset values. Read the relevant sections
before changing those systems. Keep work single-agent and follow the existing local
performance hygiene instructions.
