from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image

root=Path.cwd();out=root/'output/belltower/ivy-realism-v3'
verification=json.loads((out/'verification.json').read_text())
assert verification['passed']
record={
    'state':'Applied to both current town models; native technical and visual checks completed; awaiting user feedback on realism.',
    'revision':'ivy-realism-v3',
    'replaces':'Sources/Belltower/ivy/branching-ivy-v1.json',
    'user_feedback_on_previous_revision':'not realistic enough',
    'verification':'output/belltower/ivy-realism-v3/verification.json',
    'manifest':'output/belltower/ivy-realism-v3/publication/stage/manifest.json',
    'preview_manifest':'output/belltower/ivy-realism-v3/preview/stage/manifest.json',
    'generation':'Sources/Belltower/ivy/generation-v3.json',
    'generator':'Tools/belltower_ivy_realism.py',
    'canonical_hook':'Tools/belltower_ivy.py forwards the existing belltower_map.ivy helper to this revision',
    'geometry':{key:verification[key] for key in ['patches','leaf_variants','leaves','triangles_per_half','max_import_triangles']},
    'changes':['Curved climbing runners with irregularly spaced diagonal shoots and overlapping pockets of foliage.',
        'Smaller cupped blades with varied three-dimensional orientation; smaller leaves at growing tips.',
        'Eight leaf shapes with subdued veins, separate green shoots and woody stem materials.',
        'A private two-sided leaf shader with distinct upper/under surface roughness and light transmission.'],
    'native_views':verification['reviewed_views'],
    'native_compilation_passed':True,
    'canonical_generator_matches_reviewed_geometry':True,
    'non_ivy_town_geometry_and_collision_preserved':True,
    'saved_scene_unchanged':True,
    'temporary_render_scenes_destroyed':True,
    'other_editor_and_game_sessions_preserved':True,
    'runtime_performance_measured':False,
    'visual_acceptance':'Awaiting user feedback; technical checks do not establish a subjective realism target.',
    'capture_scope':'Native rendering of saved visual roots in temporary editor scenes; gameplay objects and planting props omitted. No user tab or camera changes.',
    'effective_gpu_exposure_equivalence_verified':False,
    'maintenance':['Keep the forty-five-thousand triangle bounded imports. Do not force-compile the town models.',
        'The preview source revision is archived separately; publication records its later staging-script revision.',
        'Previous manifests and native captures are historical evidence. Do not refresh their hashes over newer shared assets.']}
target=root/'Sources/Belltower/ivy/realism-v3.json'
assert not target.exists();target.write_text(json.dumps(record,indent=2)+'\n')
old=root/'Sources/Belltower/ivy/branching-ivy-v1.json'
shutil.copyfile(old,out/'before-source/branching-ivy-v1.json')
data=json.loads(old.read_text());data['historical_state']=data['state']
data['state']='Historical installed revision, superseded following user feedback about realism.'
data['user_feedback']='not realistic enough';data['superseded_by']='Sources/Belltower/ivy/realism-v3.json'
old.write_text(json.dumps(data,indent=2)+'\n')
gen=root/'Sources/Belltower/ivy/generation-v3.json';data=json.loads(gen.read_text())
image=Image.open(root/data['project_source'])
data['actual_resolution']=list(image.size);data['actual_color_mode']=image.mode
data['sha256']=hashlib.sha256((root/data['project_source']).read_bytes()).hexdigest()
data['layout']='Four columns, two rows, eight individual leaves; original pixels preserved.'
gen.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'record':target.relative_to(root).as_posix(),'applied':True,'verified':True,'user_feedback_pending':True}))
