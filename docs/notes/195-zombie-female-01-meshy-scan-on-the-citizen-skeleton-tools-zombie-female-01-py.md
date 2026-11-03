## Zombie woman (`zombie_female_01`, the second zombie body, `Tools/zombie_female_01.py`, 2026-11-03)
- Source: the user's Meshy AI scan `C:/Users/leon2/Desktop/test/zombie2/Meshy_AI_Zombie_hungry_Woman_1103182602_texture.glb`
  (a woman in a blouse, a skirt and heeled knee boots): one mesh of 1.88M triangles, no skeleton, 4096 colour and
  normal maps, a 2048 metal/roughness map. Work files: `D:/tmp/hc1-mw22-tools/zombie_female_01_work`.
- Game-ready model: `Assets/models/zombie/zombie_female_01/zombie_female_01.vmdl`. Three LODs from Blender's collapse
  decimation, 36k / 18k / 8k triangles (switching at 30 and 60, about 14 m and 29 m). A 3.5k fourth LOD lost her legs
  and skirt: the hair's strands keep most of the vertices, so the body collapses first. The colour and roughness maps
  are the scan's at 2048, and LOD0's normal map is baked from the scan (its geometry and its own normal map). The
  material draws back faces, since the skirt and hair are single sheets.
- It is a body for bone merge onto `models/zombie/zombie_driver.vmdl`, like `zombie_project/models/zombie_male.vmdl`.
  It is skinned to the citizen's own skeleton in the citizen's rest pose. Checked in the editor: its 57 kept bones
  match the driver's rest locals exactly. The other session's `ZombieBodyModels` list in `ZombiesRoundSystem` picks
  a body for each spawn; this model joins that list.
- The rig (`rig`): her pose is the citizen's skeleton bent to her (`JOINTS`, from gridded renders and horizontal slices
  of the scan). Her hips are turned 28 degrees to her right and her shoulders 18, her weight is on her right leg, and
  her arms hang with the palms to the thighs. Each citizen bone gets an affine map from its rest pose to hers. The
  citizen's REF body (`citizen_human_male_REF.fbx`), moved by those maps, gives its weights where it lies within 1.4"
  and faces the same way. The rest (hair, the skirt's flare) is filled in harmonically over her surface. Then her mesh
  goes back through the weighted maps into the citizen's rest pose.
- Traps found on the way:
  - The citizen skins its arms and legs almost entirely to the twist bones (`arm_lower_L_twist0`, ...), whose names
    end in a digit. A side test by "ends in _L/_R" stripped them, and her forearms bent like rubber hoses.
  - Her hands hang against the skirt and the scan welds them together. Below the blouse's hem, warm skin near a
    forearm or hand is that arm's (red less blue over 15 in the colour map; the skirt is about -2). The arms take only
    their own arm's bones and the skirt none of an arm's, and the welded triangles between them go.
  - Other welds (the upper arms against the blouse's sides, hair ends on the shoulders, fingertips on the skirt) tear
    into spikes. Triangles whose edges grow past 2.5 times their scanned length and by over 2" on some clip frame are
    left out (200 on LOD0). A pure ratio test caught 900, most of them the shoulders', knees' and hem's ordinary
    stretching.
  - Her heels are 12 cm and the citizen's ankle is 9 cm off the floor against her 16. So the ankle and ball maps are
    affine fits onto the citizen's flat foot, and in game she wears lower heels with the heel tip on the floor.
- `python Tools/zombie_female_01.py preview` renders her on the driver's clips (idle, walk_a, run, attacks). The walk,
  run and attacks look right in Blender. Not yet seen in s&box: the editor was over its video memory budget, so no
  offscreen capture was taken. Not yet seen in a match.

### Facial texture repair (2026-11-03)
- The original model was subsequently opened in ModelDoc. Native fixed-LOD and albedo captures reproduced the
  angular patches below the eyes and across the cheeks. The same mesh was much cleaner in Cycles; Eevee also
  revealed texture patches. Exported DMX positions and UVs matched the rig arrays to their written precision.
- `Tools/zombie_female_01_atlas.py` preserves the scan's body/hair UVs in the lower half of a replacement atlas and
  gives the visible face a continuous planar chart in its upper half. The open mouth keeps its separate original
  charts so inner surfaces cannot paint over the lips. Colour (4096), normals and roughness (2048 each) are rebaked
  from the original scan. Lower LODs inherit this atlas from LOD0. The material and model paths are unchanged.
- The face/scalp above 1.61 scan units now take only the head bone, with a smooth neck transition from 1.54 to 1.61.
  This avoids importing stray neck/chest weights into the face and keeps the head intact during weld removal.
  Zero custom normals left by collapsed slivers use geometric vertex normals instead of exporting NaNs.
- Rebuild: `python Tools/zombie_female_01.py lods`, `python Tools/zombie_female_01.py atlas`,
  `python Tools/zombie_female_01.py rig --write --meshes-only`, then `python Tools/zombie_female_01.py textures`.
  Repaired UVs are the default; `--scan-uvs` is only for comparing with the original. `--meshes-only` preserves the
  existing ModelDoc/material resources while replacing their generated mesh inputs.
- Raw/repaired work arrays and review renders are in `D:/tmp/hc1-mw22-tools/zombie_female_01_work`; the original
  installed inputs/textures were backed up to its `before_face_fix` folder. Editor was closed during final atlas
  work; final rendering checks use Eevee. A live-match check remains outstanding.
