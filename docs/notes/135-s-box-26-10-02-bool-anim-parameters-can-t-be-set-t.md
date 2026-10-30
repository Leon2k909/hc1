## s&box 26.10.02: bool anim parameters can't be set true (`AnimBools`, `Tools/animgraph_flags.py`)
- After the 2026-10-02 s&box update the user saw no first-person reload animations, no pistol kick, and bots gliding
  with their legs up in the air pose. Every `SkinnedModelRenderer.Set( name, true )` reaches the graph as false.
  Floats, ints, enums, vectors and rotations are fine.
- The cause is engine commit #5893 ("Simplify managed anim parameter storage", 2026-09-30):
  - Parameters now go to native code as an `AnimVariant`, and a bool is built as
    `new Vector4( value ? BitConverter.Int32BitsToSingle( 1 ) : 0f, ... )`.
  - The JIT folds that constant, a denormal float, through a double. A thread with denormals-are-zero set (the
    engine's) folds it to 0.
  - Reproduced offline on 2026-10-02 against the installed Sandbox.Engine.dll (`scratchpad/dazt`, `_controlfp_s`
    with `_DN_FLUSH`): `(AnimVariant)true` came out all zeroes, `(AnimVariant)1` (an int) didn't.
  - The replays show it: bots' `b_grounded` and IK enables false all life, where 2026-10-01's were true.
- Facepunch fixed it in sbox-public #6000 (commit 4c1a4f98, 2026-10-03): the bool picks `value ? 1 : 0` as an int
  before `Int32BitsToSingle`, which isn't folded. On 2026-10-03 the installed build (25681412, the 2026-10-02 update)
  didn't have it yet: `scratchpad/dazt` still got all zeroes for `true`, and Steam had no update waiting.
  To check a build offline, convert `true` with the installed Sandbox.Engine.dll's `AnimVariant` on a thread with
  denormals-are-zero set (`_controlfp_s` `_DN_FLUSH`), with tiered compilation off: the fixed one gives `01 00 00 00`.
- Until then our graphs' bools are enums (2026-10-04, the user asked for a fix that didn't wait for the update). An int
  set at runtime gets through, and the engine turns an int into an enum value without the bool's constructor
  (`AnimVariant.TryConvertTo`: the int as a byte). Ints reached the graphs all along (`holdtype`).
  - `Tools/animgraph_flags.py` makes each bool parameter a `CEnumAnimParameter` with the options "false" and "true", in
    that order, keeping its default and its auto-reset. Its conditions compare it with 0 and 1 (`m_nType` 2) and its
    selectors go by the enum (`SelectionSource_Enum`), so a bool selector's two children stay where they were. A bool
    used anywhere else is left a bool, with a warning. Its docstring has the rest.
  - 221 flags in 31 graphs: the 16 ported guns' viewmodel graphs (the Kastov-74u's too: it's the pipeline's output,
    and its prefab wasn't touched), the throwables', the six swb guns', `human_player` and `rigged_human` (the legacy
    player models and the robot).
  - `kastov_animgraph.py` converts the graphs it writes while `animgraph_flags.ENABLED` is set, so a rerun keeps them.
  - s&box's own viewmodels (the M4A1, MP5, M700, Spaghelli, USP, USP-SD, 1911 and both knives) come from cloud
    packages, whose graphs are compiled only. Their graphs were decompiled with Source2Viewer-CLI into
    `Assets/animgraphs/viewmodels/` (six: the 1911 uses the USP's, the knives the trench knife's) and converted, and
    the nine viewmodel prefabs use them (`animgraph_flags.VIEWMODELS`, `--import`).
- The game sets every flag with `AnimBools.SetBool` and reads it with `GetFlag`:
  - `SetBool` sends 0 or 1 as an int, read from an array so the JIT can't fold a constant 1 into the constructor.
  - `GetFlag` reads a converted flag with `GetInt`: `GetBool` can't read an enum.
  - Every anim flag the game code sets or reads goes through them (13 files). The editor's QA tools set them with
    `SetBool` and read the one they check with `GetInt`, since editor code can't use a game method from the same
    hotload.
- A bool parameter in a graph we don't have gets the same int. That's the engine's human graph (`citizen_human_male`),
  which the players' and bots' bodies use: `ik.hand_*.enabled`, `b_jump`.
  - The engine turns the int into a bool through the broken constructor (`int > 0`), yet it has come through. In the
    user's match on 2026-10-04 (replay `20261004_192134`), the bodies' hand IK read back true from the native graph
    from the hotload at 19:17:56, where it had read false all match before. Why isn't known, so it may not hold.
  - Where that graph's default is true (`b_grounded`), `SetBool` resets the parameter (`Parameters.Reset`) instead,
    since a default comes from native code. That fixed the floating bots (`AnimationHelper.IsGrounded`, bots, zombies'
    fallback, `IdleAnimator`, `OperatorPreview`).
- Checked: the editor recompiled every converted graph with no errors (2026-10-04, `sbox-dev.log`), and the replay
  above. Not yet seen: the first-person guns' reloads, fire kick, deploy, sprint, jump and the M18's slide lock.
- A replay recorded before the conversion keeps its flags as bool tracks, which don't bind to a converted graph's enums.
  Only `rigged_human` bodies (the legacy player models) have any there: the bodies' engine graph is unchanged, and the
  first-person gun is driven from the actions.
- Once an s&box build with #6000 is installed: `python Tools/animgraph_flags.py --revert` (the bools come back),
  `--unpin` (the nine prefabs go back to their models' own graphs; the copies can then go), and `ENABLED = False` in
  `animgraph_flags.py`. `SetBool` and `GetFlag` work on bools too and can stay.

