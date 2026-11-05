"""Read engine update/renderer IL and legacy sheet metadata to diagnose clipping without changing the engine."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3]
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
code=r'''
var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.Static;
var ops=typeof(System.Reflection.Emit.OpCodes).GetFields().Where(f=>f.FieldType==typeof(System.Reflection.Emit.OpCode))
    .Select(f=>(System.Reflection.Emit.OpCode)f.GetValue(null)).ToDictionary(o=>(ushort)o.Value);
var output=new System.Text.StringBuilder();
void Dump(System.Reflection.MethodInfo method)
{
    var bytes=method.GetMethodBody()?.GetILAsByteArray(); if(bytes is null)return;
    output.AppendLine(method.DeclaringType.FullName+"::"+method.Name);
    for(var i=0;i<bytes.Length;)
    {
        var at=i; ushort v=bytes[i++]; if(v==254)v=(ushort)(0xfe00|bytes[i++]);
        var op=ops[v]; object value="";
        switch(op.OperandType)
        {
            case System.Reflection.Emit.OperandType.InlineNone: break;
            case System.Reflection.Emit.OperandType.ShortInlineI: case System.Reflection.Emit.OperandType.ShortInlineVar:
            case System.Reflection.Emit.OperandType.ShortInlineBrTarget: value=bytes[i++];break;
            case System.Reflection.Emit.OperandType.InlineVar: value=BitConverter.ToUInt16(bytes,i);i+=2;break;
            case System.Reflection.Emit.OperandType.ShortInlineR: value=BitConverter.ToSingle(bytes,i);i+=4;break;
            case System.Reflection.Emit.OperandType.InlineI8: value=BitConverter.ToInt64(bytes,i);i+=8;break;
            case System.Reflection.Emit.OperandType.InlineR: value=BitConverter.ToDouble(bytes,i);i+=8;break;
            case System.Reflection.Emit.OperandType.InlineSwitch: var n=BitConverter.ToInt32(bytes,i);i+=4+n*4;break;
            default:
                var token=BitConverter.ToInt32(bytes,i);i+=4;
                value=token;
                if(op.OperandType==System.Reflection.Emit.OperandType.InlineMethod || op.OperandType==System.Reflection.Emit.OperandType.InlineField || op.OperandType==System.Reflection.Emit.OperandType.InlineType || op.OperandType==System.Reflection.Emit.OperandType.InlineTok)
                    try { value=method.Module.ResolveMember(token)?.ToString(); } catch{}
                break;
        }
        output.AppendLine($"{at:X4}: {op.Name} {value}");
    }
}
foreach(var type in new[]{typeof(ParticleEffect),typeof(ParticleRenderer),typeof(ParticleSpriteRenderer).GetInterfaces().Single(t=>t.Name=="IBatchedParticleSpriteRenderer"),typeof(Texture)})
    foreach(var m in type.GetMethods(flags).Where(m=>new[]{"UpdateParticle","PostStep","GetLocalBounds","ProcessParticlesDirectly","UpdateSheetInfo"}.Any(n=>m.Name.Contains(n)))) Dump(m);
var destination=System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/riverside/drum-fire-clipping/engine-il.txt");
System.IO.File.WriteAllText(destination,output.ToString());
return new {Destination=destination,Bytes=output.Length};
'''
with Editor() as e: print(json.dumps(e.script(code,'inspect-fire-clipping.cs'),indent=2))
