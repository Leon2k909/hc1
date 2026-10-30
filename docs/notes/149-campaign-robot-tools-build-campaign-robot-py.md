## Campaign robot (`Tools/build_campaign_robot.py`)
- The user asked for a humanoid robot for the campaign, made in Blender (2026-09-28). The script builds it in Blender
  5.1 and writes everything to `Assets/models/campaign/robot/`:
  - `combat_robot.fbx` and `.vmdl`: one mesh of rigid armour parts;
  - the paint, `combat_robot.vmat` and `combat_robot_light.vmat`, and the self-lit optics, `combat_robot_glow.vmat`,
    `_glow_amber` and `_glow_cyan`;
  - one 2048 texture atlas: a `_color` map per paint scheme, and shared `_rough`, `_metal`, `_ao` and `_normal`
    (OpenGL normals, as s&box reads them);
  - `combat_robot_hitboxes.vmdl_prefab` and `combat_robot_physics_shapes.vmdl_prefab`, metal copies of the soldiers'
    (below);
  - `combat_robot.blend`, a copy of the build scene.
- The skeleton is the CT soldier's (`ct_side_player_01_V2.fbx`, rigged_human), exported unchanged. So the vmdl takes the
  soldiers' animation list, weight lists, ragdoll joints, game data, IK and attachments from
  `models/player/prefabs_v2/`, and `rigged_human.vanmgrph`. Every part is rigid on one bone. ModelDoc drops bones with
  no skinned vertices, so there's geometry on exactly the 72 bones the soldier keeps (`KEEP_BONES`).
- The hitboxes and ragdoll shapes are the soldiers' with the `metal` surface instead of `flesh`. A shot's impact effect
  and sound come from the surface it hits (`Shootable.CreateImpactEffects`, `GetImpactSurface`), so on flesh the robot
  bled. Metal is three times as dense (2700 against 900), so the corpse is three times as heavy and the death impulse
  (`OnKill`) gives it a third of the speed.
- Material groups (`SkinnedModelRenderer.MaterialGroup`):
  - the default: gunmetal armour, red optics;
  - `amber` and `cyan`: the optics only;
  - `light`: pale grey armour, dark stencils, cyan optics.
  The markings are the robot's own: "07" and "RZ" stencils, "RZ-07" on the back, orange bands and hazard stripes.
- Running it: `blender -b --python Tools/build_campaign_robot.py`, or in a running Blender
  `exec(compile(open(p).read(), p, "exec"), {"__file__": p, "__name__": "__main__", ...})` with optional globals:
  - `ROBOT_STAGES`: comma-separated, default all: `geometry`, `preview` (workbench shots), `bake`, `textures`,
    `export`, `beauty` (Cycles renders). Later stages alone pick up the robot an earlier run left in that Blender
    session. Baking again needs `geometry` first: export parents the mesh to the rig.
  - `PREVIEW_DIR`: where the preview and beauty renders go. The default, `%TEMP%/combat_robot_preview`, is outside the
    project.
  - `ROBOT_TEX`: the atlas size (2048).
  Geometry to export takes about 50 s in a running Blender.
- The build empties the open .blend (`reset_scene`). It refuses unless the file is new, an earlier build (the scene's
  `combat_robot_build` property) or `combat_robot.blend`, or `ROBOT_FORCE_RESET` is set. `bpy.data.is_dirty` can't
  tell: scripted edits don't set it.
- Textures: Cycles bakes facts about every texel into float images (part and surface, position, normal, the parts' own
  UVs, noise, edges, AO, cavity), and numpy paints the atlas from them (`compose`). Scratches are plane cuts through
  the robot (`scratch_lines`), at least a texel wide: noise ridges came out as dotted lines or wavy contours.
- The bot: `Assets/prefabs/bots/hc1_combat_robot.prefab` is `hc1_combat_bot.prefab` with the robot's body, no
  `MilitaryUniform`, sparks for `BloodEffect` and `BotName` "RZ-07"; the same health, gun and tuning. Its
  `TeamBaseModels` is empty, so `ApplyTeamModel` keeps the prefab's model instead of dressing a soldier.
  `LightweightCombatBot`'s legacy-skeleton path does the rest: the gun on `r_hand` at `HandHoldOffset`, the left
  hand's IK on `left_arm_IK`, the ragdoll from the model. Place it in a scene, or make it a `LightweightBotManager`'s
  `BotPrefabPath` (the manager then names each one from its soldier roster).
- Campaign is locked in the menu (`HubModeRail`) and has no mode yet, so nothing spawns the robot.
- Offscreen renders in the editor: textures stream in, so a render straight after loading is blurry. Call
  `Texture.MarkUsed( 4096 )` on the materials' textures and wait a few seconds first. In a `new Scene()` that isn't
  ticking, set a GameObject's transform before creating its components, or its SceneObjects never get it.
- Checked 2026-09-28 in offscreen renders of an isolated scene in the editor: the model compiles, its 72 bones match
  the soldier's, the 54 animations and the graph play, the ragdoll has 16 bodies and 15 joints, and the 21 hitboxes,
  the four material groups and the textures work. The metal copies compile (the compiled model has `metal` and no
  `flesh`). Not yet checked: the bot prefab in a match (spawning, fighting, the gun in its hand, dying), the metal
  impacts and the heavier ragdoll.

