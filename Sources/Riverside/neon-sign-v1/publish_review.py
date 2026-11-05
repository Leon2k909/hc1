from pathlib import Path
import json,shutil
HERE=Path(__file__).parent;REVIEW=HERE.parents[2];ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=REVIEW/'output/riverside/neon-sign-v1'
v=json.loads((OUT/'verification.json').read_text());assert v['actual_play_verified'] and v['saved_scene_unchanged'] and v['editor_state_restored']
for folder in ('Sources/Riverside/neon-sign-v1','output/riverside/neon-sign-v1'):
    dest=ROOT/folder;dest.mkdir(parents=True,exist_ok=True)
    for p in (REVIEW/folder).glob('*'):
        if p.is_file():shutil.copy2(p,dest/p.name)
note=ROOT/'docs/notes/riverside-neon-sign-v1-review-20261104.md';note.write_text('''# NO PLACE BETTER neon sign v1 — review candidate, 2026-11-04

Replaces the 36-triangle flat atlas sign with rounded emissive tubing on both faces, original hand-drawn lettering shapes, electrode boots, insulated leads, ceramic stand-offs, clips, mounting rails, a formed weathered cabinet, service hatch/hinges/lock, rain lip, cradle, junction box and conduit. Existing approved assets and active chats were checked first. This is independent of the other chat's water tower/tank work, which was left untouched.

Worktree C:/sbox-projects/hc1/neon-sign-review, branch codex/riverside-neon-sign-v1. Assets/models/maps/riverside/neon-sign-v1 and Assets/materials/riverside/neon-sign-v1 are private review resources. Placement(1150,60,0), yaw2.8624052. Original cabinet111×10×126 inches, centerz410. LODs34,908/9,660/6,444 triangles, distances0/20/45, masks1/2/4. Six materials; only neon_red.vmat emits. Final tube brightness8.0 with a red/hot-center profile and1024px coating maps. Degenerate triangles at export precision removed; all final geometry checks pass.

Actual play comparison verified one player, zero error models, matching camera/framing, unchanged red scene lights and gameplay post-processing. The temporary camera is offscreen and does not replace the main camera. No added lights. Original public riverside_dressing.vmdl, active OBJ, full PhysicsShapeList and saved Riverside scene remain unchanged. Private dressing_without_neon removes exactly36 old sign triangles only for preview. Existing other prop upgrades retained. No public replacement, original-model deletion or authoring changes yet.

Evidence: output/riverside/neon-sign-v1/in-game-front-before.png, in-game-front-after.png, verification.json, runtime-review.json, materials-verified.json, geometry-verified.json, state-restored.json and scene-unchanged.json. Both images have zero magenta/error pixels and zero green tube pixels; clipped white text pixels fall from34,480 to197 in the same crop. Supplementary native engine-before/after.png use matched studio lighting. Scripts and README: Sources/Riverside/neon-sign-v1.

Await user approval under CLAUDE.md. On installation preserve the original two red lights and public physics; replace only the old sign mesh, add the three LODs and update authoring without regenerating Riverside. Recheck source hashes first.
''',encoding='utf-8')
index=ROOT/'CLAUDE.md';line='- [Riverside NO PLACE BETTER neon sign v1 (review candidate, 2026-11-04)](docs/notes/riverside-neon-sign-v1-review-20261104.md)'
if line not in index.read_text(encoding='utf-8'):
    with index.open('a',encoding='utf-8') as stream:stream.write('\n'+line+'\n')
print(json.dumps(dict(review_saved=True,actual_gameplay_photos=True,public_sign_unchanged=True,tower_untouched=True),indent=2))
