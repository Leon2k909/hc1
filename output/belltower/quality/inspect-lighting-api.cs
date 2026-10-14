var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.Static;
var opcodes=typeof(System.Reflection.Emit.OpCodes).GetFields(System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Static)
    .Where(f=>f.FieldType==typeof(System.Reflection.Emit.OpCode)).Select(f=>(System.Reflection.Emit.OpCode)f.GetValue(null)).ToDictionary(o=>(ushort)o.Value);
object Read(System.Reflection.MethodBase method) {
    var il=method.GetMethodBody()?.GetILAsByteArray(); var calls=new System.Collections.Generic.List<string>();
    if(il==null)return calls;
    for(var i=0;i<il.Length;) {
        var at=i; ushort value=il[i++]; if(value==0xfe)value=(ushort)(0xfe00|il[i++]);
        var op=opcodes[value];
        var size=op.OperandType switch {
            System.Reflection.Emit.OperandType.InlineNone=>0,
            System.Reflection.Emit.OperandType.ShortInlineBrTarget or System.Reflection.Emit.OperandType.ShortInlineI or System.Reflection.Emit.OperandType.ShortInlineVar=>1,
            System.Reflection.Emit.OperandType.InlineVar=>2,
            System.Reflection.Emit.OperandType.InlineI8 or System.Reflection.Emit.OperandType.InlineR=>8,
            System.Reflection.Emit.OperandType.InlineSwitch=>4+4*BitConverter.ToInt32(il,i),_=>4};
        if(op.OperandType is System.Reflection.Emit.OperandType.InlineMethod or System.Reflection.Emit.OperandType.InlineField or System.Reflection.Emit.OperandType.InlineType) {
            try {var member=method.Module.ResolveMember(BitConverter.ToInt32(il,i)); calls.Add(at+" "+op.Name+" "+member.DeclaringType+"."+member);}catch{}
        } else if(op.OperandType==System.Reflection.Emit.OperandType.InlineString)calls.Add(at+" string "+method.Module.ResolveString(BitConverter.ToInt32(il,i)));
        i+=size;
    }
    return calls;
}
return new{
    Create=Read(typeof(Editor.SceneEditorSession).GetMethod("CreateFromPath",flags)),
    Constructor=Read(typeof(Editor.SceneEditorSession).GetConstructors(flags).First(c=>!c.IsStatic)),
    IsSaved=Read(typeof(IndirectLightVolume).GetProperty("IsSceneSaved",flags).GetMethod),
    SaveTexture=Read(typeof(IndirectLightVolume).GetMethod("SaveTexture",flags)),
    Bake=Read(typeof(IndirectLightVolume).GetNestedTypes(flags).First(t=>t.Name.StartsWith("<BakeProbes>")).GetMethod("MoveNext",flags)),
    CaptureConstructor=Read(typeof(IndirectLightVolume).Assembly.GetType("Sandbox.DDGIProbeUpdaterCubemapper").GetConstructors(flags).First(c=>!c.IsStatic)),
    CaptureProbe=Read(typeof(IndirectLightVolume).Assembly.GetType("Sandbox.DDGIProbeUpdaterCubemapper").GetNestedTypes(flags).First(t=>t.Name.StartsWith("<RenderProbe>")).GetMethod("MoveNext",flags)),
    UpdaterConstructors=typeof(IndirectLightVolume).Assembly.GetType("Sandbox.DDGIProbeUpdaterCubemapper").GetConstructors(flags).Select(c=>new{Signature=c.ToString(),c.IsPublic}),
    VolumeMethods=typeof(IndirectLightVolume).GetMethods(flags).Where(m=>m.Name.Contains("Relocat")||m.Name.Contains("Texture")||m.Name.Contains("BakeVersion")).Select(m=>new{Signature=m.ToString(),m.IsPublic}),
    SceneFolder=typeof(Editor.SceneFolder).GetMembers(flags).Select(m=>m.ToString())
};
