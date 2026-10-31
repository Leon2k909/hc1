## Riverside's teddy v2 (`models/zombies/teddy_v2`, `Sources/Zombies/teddy-v2/`, 2026-10-31)
- The teddy in the mud by the dog run's gate, from the reference picture, replacing eight faceted lumps at the user's word ("Yes, install it") after a before and after rendered by s&box. A plush
  bear in the old one's brown and place, facing the same way, with no collision, as before.
- `riverside_parts.teddy` only records a placement. The scene's `Teddy` object holds the model. Installed by `install_teddy.py`, which cuts its 720 triangles from `riverside_pad.obj`:
  `riverside_map.py` can't be safely rerun (note 163).
- A scene tab opened before a file install keeps the old scene, and saving it would wipe the install. After writing a scene, check the open tab (`Editor.SceneEditorSession.Resolve( file ).Reload()`,
  if it has no unsaved changes).
- Seen as installed in an isolated editor scene under the map's own light. **Not yet seen in a live match.** See the folder's README.
