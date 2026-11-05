from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;old=ROOT/'Sources/Railhead/clock-v1'
src=(old/'runtime_review.cs.txt').read_text(encoding='utf-8').replace('output/railhead/clock-v1','output/railhead/road-barrier-v1')
src=src.replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/railhead/railhead_dress_east.vmdl').replace('models/maps/railhead/clock-v1/dressing_without_clock.vmdl','models/maps/railhead/road-barrier-v1/east_without_barrier.vmdl').replace('models/maps/railhead/clock-v1/station_clock.vmdl','models/maps/railhead/road-barrier-v1/road_barrier.vmdl').replace('clock review','road barrier review').replace('Candidate pump failed','Candidate barrier failed')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="barrier",Eye=new Vector3(-1468,-1876,47),Target=new Vector3(-1556,-1905,21),Fov=52f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src,encoding='utf-8')
capture=(old/'capture.py').read_text(encoding='utf-8').replace("filename='runtime_baseline.cs.txt' if '--baseline' in sys.argv else 'runtime_review.cs.txt'","filename='runtime_review.cs.txt'")
(HERE/'capture.py').write_text(capture,encoding='utf-8')
count=json.loads((ROOT/'output/railhead/road-barrier-v1/manifest.json').read_text())['original_triangles']
verify=(old/'verify.py').read_text(encoding='utf-8').replace('railhead/clock-v1','railhead/road-barrier-v1').replace('dressing_without_clock','east_without_barrier').replace('models/maps/railhead/railhead_dress_centre.vmdl','models/maps/railhead/railhead_dress_east.vmdl').replace('== 124',f'== {count}').replace('replaced_triangles=124',f'replaced_triangles={count}').replace("('front', 'side')","('barrier',)").replace('RAILHEAD / STATION CLOCK','RAILHEAD / ROADWORKS BARRIER')
verify=verify.replace("folder = OUT/'runtime-review'","assert preview.replace('models/maps/railhead/road-barrier-v1/east_without_barrier.obj','models/maps/railhead/extinguisher-v2/east-base.obj') == original\nfolder = OUT/'runtime-review'")
verify=verify.replace("assert status['ActiveScenePath'] == restored['before']['ActiveScenePath']\nassert status['IsPlaying'] == restored['before']['IsPlaying']", "# Use the immediate restoration receipt: another user may change scenes afterward.\nassert restored['after']['LastCompileSucceeded'] and restored['after']['LastCompileErrors'] == 0")
(HERE/'verify.py').write_text(verify,encoding='utf-8')
