from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/valve-wheels-v1'
HERE=ROOT/'Sources/Sewage/valve-wheels-v1'
(OUT/'native.py').write_text((ROOT/'output/sewage/pipe-flanges-v1/native.py').read_text().replace('output/sewage/pipe-flanges-v1','output/sewage/valve-wheels-v1'),encoding='utf-8')
# (HERE/'import.cs.txt').write_text((ROOT/'Sources/Sewage/pipe-flanges-v1/import.cs.txt').read_text().replace('pipe-flanges-v1','valve-wheels-v1'),encoding='utf-8')
source=(ROOT/'Sources/Sewage/pipe-flanges-v1/capture.cs.txt').read_text(encoding='utf-8')
source=source.replace('output/sewage/pipe-flanges-v1','output/sewage/valve-wheels-v1')
source=source.replace('models/maps/sewage/pipe-flanges-v1/flanges.vmdl','models/maps/sewage/valve-wheels-v1/wheels.vmdl')
source=source.replace('using (scene.Push()) added.Enabled = variant == "after";', '''using (scene.Push())
        {
            added.Enabled = variant == "after";
            renderer.Model = Model.Load(variant == "after" ? "models/maps/sewage/valve-wheels-v1/base_pipework.vmdl" : "models/maps/sewage/sewage_pipework.vmdl");
            if(renderer.Model.IsError) throw new Exception("Pipework variant failed to compile.");
        }''')
source=source.replace('new Vector3(-638.180359f,661.684265f,159.773834f)','new Vector3(-538f,852f,215f)')
source=source.replace('Rotation.From(new Angles(-8.29982376f,91.0002441f,0))','Rotation.LookAt(new Vector3(-624f,953f,195f)-camera.WorldPosition)')
source=source.replace('camera.FieldOfView = 80','camera.FieldOfView = 42')
(HERE/'capture.cs.txt').write_text(source,encoding='utf-8')
for model in ('base_pipework','wheels'):
    (OUT/(model+'.json')).write_text('{"path":"models/maps/sewage/valve-wheels-v1/'+model+'.vmdl"}')
