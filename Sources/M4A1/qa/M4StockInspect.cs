using Editor;
using Sandbox;
using System;
using System.Linq;
using System.IO;
using System.Text;
using System.Reflection;
public static class M4StockInspect
{
    [ConCmd("m4_stock_inspect")]
    public static void Run()
    {
        var output=new StringBuilder();
        foreach(var variant in new[]{"v","w"})
        {
            var model=Model.Load($"models/weapons/sbox_assault_m4a1/{variant}_m4a1.vmdl");
            output.AppendLine($"MODEL {model.Name} bounds={model.Bounds} bones={model.BoneCount}");
            output.AppendLine("materials "+string.Join("|",model.Materials.Select(m=>m.Name)));
            foreach(var part in model.Parts.All)
            {
                output.AppendLine("PART "+part);
                foreach(var prop in part.GetType().GetProperties())output.AppendLine(prop.Name+"="+prop.GetValue(part));
                foreach(var choice in part.Choices)
                foreach(var prop in choice.GetType().GetProperties())output.AppendLine("choice "+prop.Name+"="+prop.GetValue(choice));
            }
            var info=model.MeshInfo;
            {
                output.AppendLine("MESH "+info);
                foreach(var prop in info.GetType().GetProperties())output.AppendLine(prop.Name+"="+prop.GetValue(info));
                foreach(var mesh in info.Meshes)
                foreach(var prop in mesh.GetType().GetProperties())output.AppendLine("mesh "+prop.Name+"="+prop.GetValue(mesh));
            }
            if(variant=="w")
            {
                var verts=model.GetVertices();var indices=model.GetIndices();
                output.AppendLine($"vertices {verts.Length} indices {indices.Length} lod0 {model.GetIndexCountForLod(0)}");
                foreach(var prop in verts[0].GetType().GetFields())output.AppendLine("vertex "+prop.Name+"="+prop.GetValue(verts[0]));
                var flags=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
                var countMethod=typeof(Model).GetMethod("GetLodDrawCallCount",flags);
                var rangeMethod=typeof(Model).GetMethod("GetLodDrawCallRange",flags);
                for(int i=0;i<(int)countMethod.Invoke(model,new object[]{0});i++)
                {
                    var args=new object[]{0,i,0,0,0};rangeMethod.Invoke(model,args);
                    output.AppendLine($"draw {i} start {args[2]} count {args[3]} mat {args[4]}");
                }
            }
        }
        File.WriteAllText(Path.Combine(Project.Current.GetRootPath(),"Sources/M4A1/qa/stock-model-inspection.txt"),output.ToString());
    }

    [ConCmd("m4_export_stockless_base")]
    public static void Export()
    {
        var model=Model.Load("models/weapons/sbox_assault_m4a1/w_m4a1.vmdl");
        var verts=model.GetVertices();var indices=model.GetIndices();
        var folder=Path.Combine(Project.Current.GetRootPath(),"Assets/attachments/m4a1/world_base");Directory.CreateDirectory(folder);
        var obj=new StringBuilder("# Original M4A1 world base with factory stock removed; retains original UVs.\nmtllib world_base.mtl\no m4a1_stockless_base\nusemtl original_m4a1\n");
        foreach(var v in verts)
        {
            obj.AppendLine(FormattableString.Invariant($"v {v.Position.y} {v.Position.z} {v.Position.x}"));
            obj.AppendLine(FormattableString.Invariant($"vt {v.TexCoord0.x} {1-v.TexCoord0.y}"));
            obj.AppendLine(FormattableString.Invariant($"vn {v.Normal.y} {v.Normal.z} {v.Normal.x}"));
        }
        int kept=0,removed=0;
        for(int i=0;i<model.GetIndexCountForLod(0);i+=3)
        {
            var a=indices[i];var b=indices[i+1];var c=indices[i+2];
            var center=(verts[a].Position+verts[b].Position+verts[c].Position)/3;
            if(center.x < -4.15f && (center.z > 4.4f || center.x < -5.5f)){removed++;continue;}
            obj.AppendLine($"f {a+1}/{a+1}/{a+1} {b+1}/{b+1}/{b+1} {c+1}/{c+1}/{c+1}");kept++;
        }
        File.WriteAllText(Path.Combine(folder,"world_base.obj"),obj.ToString());
        File.WriteAllText(Path.Combine(folder,"world_base.mtl"),"newmtl original_m4a1\nKd 1 1 1\n");
        Log.Info($"M4_STOCK export kept={kept} removed={removed}");
    }
}
