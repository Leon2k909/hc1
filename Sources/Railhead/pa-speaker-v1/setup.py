from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;old=ROOT/'Sources/Railhead/clock-v1'
src=(old/'runtime_review.cs.txt').read_text(encoding='utf-8').replace('output/railhead/clock-v1','output/railhead/pa-speaker-v1')
src=src.replace('models/maps/railhead/clock-v1/dressing_without_clock.vmdl','models/maps/railhead/pa-speaker-v1/centre_without_speaker.vmdl').replace('models/maps/railhead/clock-v1/station_clock.vmdl','models/maps/railhead/pa-speaker-v1/pa_speaker.vmdl').replace('clock review','PA speaker review').replace('Candidate pump failed','Candidate speaker failed')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="speaker",Eye=new Vector3(813,-43,205),Target=new Vector3(820,-14.1f,213.4f),Fov=42f},new {Name="side",Eye=new Vector3(794,-35,213),Target=new Vector3(820,-14.1f,213.4f),Fov=43f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src,encoding='utf-8')
capture=(old/'capture.py').read_text(encoding='utf-8').replace("filename='runtime_baseline.cs.txt' if '--baseline' in sys.argv else 'runtime_review.cs.txt'","filename='runtime_review.cs.txt'")
(HERE/'capture.py').write_text(capture,encoding='utf-8')
count=json.loads((ROOT/'output/railhead/pa-speaker-v1/manifest.json').read_text())['original_triangles']
verify=(old/'verify.py').read_text(encoding='utf-8').replace('railhead/clock-v1','railhead/pa-speaker-v1').replace('dressing_without_clock','centre_without_speaker').replace('== 124',f'== {count}').replace('replaced_triangles=124',f'replaced_triangles={count}').replace("('front', 'side')","('speaker', 'side')").replace('RAILHEAD / STATION CLOCK','RAILHEAD / PA SPEAKER')
verify=verify.replace("folder = OUT/'runtime-review'","assert preview.replace('models/maps/railhead/pa-speaker-v1/centre_without_speaker.obj','models/maps/railhead/clock-v1/dressing_without_clock.obj') == original\nfolder = OUT/'runtime-review'")
(HERE/'verify.py').write_text(verify,encoding='utf-8')
