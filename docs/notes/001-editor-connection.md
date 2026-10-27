## Editor connection
- Active checkout on this workstation: `C:\sbox-projects\hc1\forked-shooter-main` (user direction, 2026-10-17).
  Confirm the native editor's `Paths.ProjectRoot` matches this checkout before editing.
- Use native s&box MCP (`sbox-cli --connect`) as the primary connection; see `AGENTS.md` for the workflow.
- Native `bridge_helpers` exposes every registered Claude Bridge helper in process, including
  read-only discovery and parameter inspection. Prefer the engine's dedicated tools for ordinary work.
- `bridge_simulate_input` and `bridge_scatter_props` have explicit parameter schemas. Other helpers use
  `bridge_describe_handler`, then `bridge_read` / `bridge_call`; their existing play-mode guards still apply.
- The old `sbox_claude_bridge` MCP adapter remains available as a fallback. Use one route per operation.

