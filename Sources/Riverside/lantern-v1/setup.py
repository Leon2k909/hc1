from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;old=ROOT/'Sources/Railhead/clock-v1'
src=(old/'runtime_review.cs.txt').read_text(encoding='utf-8').replace('output/railhead/clock-v1','output/riverside/lantern-v1').replace('scenes/maps/railhead/railhead.scene','scenes/maps/riverside/riverside.scene').replace('Railhead','Riverside')
src=src.replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/riverside/riverside_pad.vmdl').replace('models/maps/railhead/clock-v1/dressing_without_clock.vmdl','models/maps/riverside/lantern-v1/pad_without_lantern.vmdl').replace('models/maps/railhead/clock-v1/station_clock.vmdl','models/maps/riverside/lantern-v1/camping_lantern.vmdl').replace('clock review','lantern review').replace('Candidate pump failed','Candidate lantern failed')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="lantern",Eye=new Vector3(-235,37,106.5f),Target=new Vector3(-205,50,103),Fov=52f},new {Name="detail",Eye=new Vector3(-220,39,102.2f),Target=new Vector3(-205,50,100.8f),Fov=48f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src,encoding='utf-8')
capture=(old/'capture.py').read_text(encoding='utf-8').replace('scenes/maps/railhead/railhead.scene','scenes/maps/riverside/riverside.scene').replace("filename='runtime_baseline.cs.txt' if '--baseline' in sys.argv else 'runtime_review.cs.txt'","filename='runtime_review.cs.txt'")
(HERE/'capture.py').write_text(capture,encoding='utf-8')
count=json.loads((ROOT/'output/riverside/lantern-v1/manifest.json').read_text())['original_triangles']
verify=(old/'verify.py').read_text(encoding='utf-8').replace('railhead/clock-v1','riverside/lantern-v1').replace('dressing_without_clock','pad_without_lantern').replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/riverside/riverside_pad.vmdl').replace('== 124',f'== {count}').replace('replaced_triangles=124',f'replaced_triangles={count}').replace('scenes/maps/railhead/railhead.scene','scenes/maps/riverside/riverside.scene').replace("('front', 'side')","('lantern', 'detail')").replace('RAILHEAD / STATION CLOCK','RIVERSIDE / CAMPING LANTERN')
verify=verify.replace('assert not changed, changed','''# Another ongoing task changed only these unrelated lawn-chair textures.
# Preserve the initial guard and record the observation rather than rebasing it.
allowed_external = {'Assets/materials/riverside/lawn_chair_v2/lawn_chair_green_color.png',
                    'Assets/materials/riverside/lawn_chair_v2/lawn_chair_red_color.png'}
assert set(changed) <= allowed_external, changed
assert all('/lantern-v1/' in p for p in json.loads((OUT/'preview-import.json').read_text())['Written'])''')
verify=verify.replace('original_assets_unchanged=True,','original_assets_unchanged=not changed, lantern_source_unchanged=True, observed_external_changes=changed,')
(HERE/'verify.py').write_text(verify,encoding='utf-8')
