from pathlib import Path
import shutil,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GEN=Path('C:/Users/leon2/.codex/generated_images/01a19379-8e73-7760-8fa8-3a40d8e4cc8a')
pairs={'plate-color':'exec-abd8613b-99f1-4ecf-b59f-8a06aff5d149.png',
       'grip-color':'exec-5cbc01e9-2b43-4eac-9732-66609fcd7b9f.png',
       'plate-normal':'exec-90e02c89-8a31-4245-8876-8fef30ef8962.png',
       'grip-normal':'exec-d2e4456b-6005-42ad-85e7-ec060a258bef.png',
       'plate-rough':'exec-1cfbdd1d-9701-4ca3-b52c-885c4d57e042.png',
       'grip-rough':'exec-31e3fc27-da61-4c9d-9e07-b70749574f40.png'}
(HERE/'generated').mkdir(exist_ok=True)
for name,file in pairs.items():shutil.copy2(GEN/file,HERE/'generated'/f'{name}.png')
(HERE/'provenance.json').write_text(json.dumps(dict(tool='built-in imagegen',images=pairs,reference='Sources/Ares/interior-concept-20261103/concept-v1.png',preparation='Native Bitmap.Resize from 1254 square to 2048 square; originals retained. Maps are generated visual approximations, not measured scans.'),indent=2))
s=(ROOT/'Sources/Ares/constructed-interior-v3/native.py').read_text().replace('constructed-interior-v3','floor-finish-v4')
(HERE/'native.py').write_text(s)
s=(ROOT/'Sources/Ares/constructed-interior-v3/capture.cs.txt').read_text().replace('output/ares/constructed-interior-v3','output/ares/floor-finish-v4')
s=s.replace('renderer.Model=Model.Load("models/maps/ares/constructed-v3/ares_"+model+"_trial.vmdl");','var resource=model=="hall"&&variant["newFloor"]?.GetValue<bool>()==true?"models/maps/ares/floor-finish-v4/ares_hall_trial.vmdl":"models/maps/ares/constructed-v3/ares_"+model+"_trial.vmdl";\n     renderer.Model=Model.Load(resource);')
(HERE/'capture.cs.txt').write_text(s)
OUT=ROOT/'output/ares/floor-finish-v4';OUT.mkdir(exist_ok=True,parents=True)
light=dict(lightGain=1.4,temperature=5000,bounce=1.8,contrast=.85,shadows=True,diffuseWork=True,trial=True)
config=dict(variants=[dict(name='before',**light),dict(name='after',newFloor=True,**light)],views=[
 dict(name='gallery',eye=[500,-640,272],target=[-120,-540,208],fov=86),
 dict(name='ground',eye=[500,-400,64],target=[0,-100,0],fov=85),
 dict(name='hero',eye=[940,-640,280],target=[-70,300,330],fov=78)])
(OUT/'capture-config.json').write_text(json.dumps(config,indent=2))
print('Prepared six generated maps and matched native capture workflow')
