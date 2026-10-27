## Reload times (`Reloadable`)
- ReloadTime and EmptyReloadTime are when the gun is level again in its own reload clip, the user's "real numbers
  only". The ported guns' come from their clips (see their sections). The old guns' were measured offscreen on
  2026-09-28: the viewmodel's animgraph in a SceneModel, the gun bone back within 4 degrees and 0.6 of its idle pose,
  relative to the camera bone.
  - M4A1 1.95 / 2.4 s, MP5 1.95 / 3.3 s, M700 1.95 / 2.3 s, and the USP, USP-SD and 1911 1.4 / 1.5 s.
  - The SCAR-H's own clip takes 4.45 s, empty or not.
- The clips play at their own rate whatever ReloadTime is, so the timed reload sounds stay in step with them.
- The Spaghelli loads shell by shell (`SingleReload`): 1.3 s a shell (the clip's loop) and 2.15 s for the first from
  empty. After the last shell, `ReloadExitTime` (0.5 s) holds the reload while the closing clip brings the gun up, so
  it can't fire before then. The shell's sound plays at 0.65 s, as the shell goes into the tube.
- Some ported guns' declared times end 0.1-0.4 s before their clips level the gun: the Vityaz, Kastov 762, P90 and
  the Bizon's non-empty reload. They weren't changed.

