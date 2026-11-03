## Zombie in the open shirt (`zombie_male_02`, a third zombie body, `Tools/zombie_male_02.py`, 2026-11-03)
- Source: the user's Meshy AI scan `C:/Users/leon2/Desktop/test/zombie` (copied to `sources/Zombies/zombie_male_02`,
  not in git): a barefoot man in an open short-sleeved shirt over a T-shirt, and ripped jeans. One mesh of 1.9M
  triangles, unrigged, 2048 colour, normal and roughness maps (its metallic map is black). It stands 1.90 m with a
  torso a fifth longer than the citizen's, its head tilted to its left.
- Game-ready model: `Assets/models/zombie/zombie_male_02.vmdl`, DMX in `models/zombie/zombie_male_02/`, materials in
  `materials/zombies/zombie_male_02/`. Four LODs: 30k / 15k / 7k / 3k triangles, switching at 15, 30 and 60 (about 7,
  14 and 29 m). The old cloud zombie's LOD0 is 46k.
- Zombies wear a body at random: `ZombiesGameMode.ZombieBodyModels` (passed to `ZombiesRoundSystem`), in
  `zombies.prefab` the old `zombie_project/models/zombie_male.vmdl`, this one and `zombie_female_01`. A pick that
  won't load falls back to `ZombieBodyModel`.
- `Tools/zombie_male_02_blender.py` "lods" makes the LODs. The scan's UV atlas has more seams than LOD0 has edges, so
  decimating it scattered shards of the wrong texture over the neck, collar and cheek. Each LOD is unwrapped afresh
  (smart UV project, 800-2,700 islands on decimated cloth, 2 px apart, repacked) and gets its own colour, roughness
  and normal maps baked from the scan (2048 / 1024 / 1024 / 512). The scan's custom normals are cleared first: after
  decimation the bake made up for them triangle by triangle, which the engine's tangents wouldn't match. The install
  fills every pixel outside the islands from the nearest one, so the lower mips don't bleed black at the seams.
- The rig (`Tools/zombie_male_02.py`, its docstring has the steps):
  - `FIT` is where the citizen's main joints sit in the scan, from its cross-sections. The trunk's joints share out
    pelvis to neck_0 as the citizen's do. Each main bone maps the scan onto the citizen's rest pose: limbs turn and
    stretch along their length, the trunk only moves and shortens (keeping the scan's posture and head tilt), and
    everything is 0.95 as thick (hands 0.92).
  - The scan's hands hang turned about 37 degrees in from the citizen's resting hand. Bound like that, every clip
    would turn them further (the "twisted hands" the user disliked in September), so the forearms are untwisted,
    ramping from elbow to wrist, until the palms face the thighs like the citizen's.
  - Weights: the citizen's REF body (`citizen_human_male_REF.fbx`, in s&box's citizen addon; Source2Viewer can't
    export the compiled citizen's R10G10B10A2 normals) is carried into the scan's shape by the inverse maps, and each
    scan vertex takes the nearest point's weights, from its own arm or leg only, smoothed 3 rounds. The fingers are
    rigid with the hand. A hanging arm is the scan below the armpit wider than 0.26 m and above 0.7 m: without the
    height limit the turned-out feet counted as hands and were spun by the untwist.
  - The skeleton is the compiled citizen's (Source2Viewer's DATA dump of `citizen_human_male.vmdl_c`, GUID block
    stripped), all 96 bones. The REF FBX's bone heads match it to 0.0004".
- `python Tools/zombie_male_02.py --preview` renders the fit, the rest pose over the citizen, and the body on the
  driver's clips (idle, three walk frames, run, attacks A, C and E, ported by `zombie_anims.port_all`). Checked in
  those renders: the hands hang palm to thigh in the idle and grab palm down in the attacks, the shoulders and elbows
  bend cleanly. `--install` writes the assets; without it nothing goes into `Assets`.
