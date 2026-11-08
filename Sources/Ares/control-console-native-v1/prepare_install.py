from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/ares/control-console-native-v1';STAGE=OUT/'stage/Assets';sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,ares_control_console as C
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((OUT/'manifest.json').read_text())
# Reuse the previously verified exact baseline, abort on concurrent edits.
for f,h in old['protected'].items():assert sha(ROOT/f)==h,f
base=ROOT/'Assets'/old['active_base'];raw=base.read_text().splitlines(keepends=True);cut=set(old['cut']);assert len(cut)==40
stage=OUT/'install-stage';stage.mkdir(exist_ok=True)
(stage/'dressing_without_console.obj').write_text(''.join(l for i,l in enumerate(raw) if i not in cut))
(stage/'node.json').write_text(json.dumps(C.scene_object(K.SceneIds('4e8a1c37-92d5-4b6f-a0e3-7c15d9b2f846'))))
files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()}
old['files']=files;old['lods']=3;old['lod_triangles']=json.loads((OUT/'lods.json').read_text())['triangles'];(OUT/'manifest.json').write_text(json.dumps(old,indent=2))
plan=dict(active_base=old['active_base'],protected=old['protected'],base_hash=sha(base),scene_hash=sha(ROOT/'Assets/scenes/maps/Ares/ares.scene'),cut=old['cut'],files={p.name:sha(p) for p in stage.iterdir() if p.is_file()})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2));print({'stage_ready':True,'lod_triangles':old['lod_triangles']})
