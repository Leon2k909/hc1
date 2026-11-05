from pathlib import Path
root=Path('C:/sbox-projects/hc1/forked-shooter-main')
source=(root/'output/sewage/pipe-texture-v1/capture.cs').read_text()
source=source.replace('output/sewage/pipe-texture-v1','output/sewage/pipe-flanges-v1')
source=source.replace('var flags =', '''GameObject added;
    using (scene.Push())
    {
        added = new GameObject(false, "Bolted flange preview");
        var flangeModel = Model.Load("models/maps/sewage/pipe-flanges-v1/flanges.vmdl");
        if (flangeModel is null || flangeModel.IsError) throw new Exception("Flange model failed to compile.");
        added.Components.Create<ModelRenderer>().Model = flangeModel;
    }
    var flags =''')
source=source.replace('using (scene.Push()) renderer.MaterialOverride = variant == "after" ? material : null;', 'using (scene.Push()) added.Enabled = variant == "after";')
(root/'Sources/Sewage/pipe-flanges-v1/capture.cs.txt').write_text(source,encoding='utf-8')
close=source.replace('output/sewage/pipe-flanges-v1','output/sewage/pipe-flanges-v1/close')
close=close.replace('var material =', 'System.IO.Directory.CreateDirectory(output);\nvar material =')
close=close.replace('new Vector3(-638.180359f,661.684265f,159.773834f)','new Vector3(-473f,817f,294f)')
close=close.replace('Rotation.From(new Angles(-8.29982376f,91.0002441f,0))','Rotation.LookAt(new Vector3(-563.3778f,942f,303f)-camera.WorldPosition)')
close=close.replace('camera.FieldOfView = 80','camera.FieldOfView = 55')
(root/'Sources/Sewage/pipe-flanges-v1/close.cs.txt').write_text(close,encoding='utf-8')
