
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.Json;

public static class MemberCheck
{
    public static int Main(string[] args)
    {
        using var stream = File.OpenRead(args[0]);
        using var pe = new PEReader(stream);
        var md = pe.GetMetadataReader();
        string Name(TypeDefinition t)
        {
            var own = md.GetString(t.Name);
            var declaring = t.GetDeclaringType();
            if(!declaring.IsNil) return Name(md.GetTypeDefinition(declaring))+"+"+own;
            var ns = md.GetString(t.Namespace);
            return ns.Length>0 ? ns+"."+own : own;
        }
        var types = new Dictionary<string,TypeDefinition>();
        foreach(var handle in md.TypeDefinitions) types[Name(md.GetTypeDefinition(handle))] = md.GetTypeDefinition(handle);
        var spec = JsonSerializer.Deserialize<List<object[]>>(File.ReadAllText(args[1]));
        var results = new List<object>();
        var missing = 0;
        foreach(var row in spec)
        {
            var typeName = row[0].ToString(); var kind = row[1].ToString(); var member = row[2].ToString();
            int? count = row[3] is JsonElement e && e.ValueKind==JsonValueKind.Number ? e.GetInt32() : null;
            var found = new List<string>();
            if(types.TryGetValue(typeName,out var type))
            {
                if(kind=="property")
                    foreach(var h in type.GetProperties()) { var p = md.GetPropertyDefinition(h); if(md.GetString(p.Name)==member) found.Add("property"); }
                if(kind=="field")
                    foreach(var h in type.GetFields()) { var f = md.GetFieldDefinition(h); if(md.GetString(f.Name)==member) found.Add("field"); }
                if(kind=="method")
                    foreach(var h in type.GetMethods())
                    {
                        var m = md.GetMethodDefinition(h);
                        if(md.GetString(m.Name)!=member) continue;
                        var parameters = m.GetParameters().Select(md.GetParameter).Count(p => p.SequenceNumber>0);
                        var blob = md.GetBlobReader(m.Signature);
                        var header = blob.ReadSignatureHeader();
                        if(header.IsGeneric) blob.ReadCompressedInteger();
                        var declared = blob.ReadCompressedInteger();
                        found.Add($"{declared} parameter(s), {m.Attributes}");
                        if(count is null || declared==count) found.Add("match");
                    }
            }
            var ok = types.ContainsKey(typeName) && (kind=="method" ? found.Contains("match") : found.Count>0);
            if(!ok) missing++;
            results.Add(new { Type=typeName, Kind=kind, Member=member, Parameters=count, Found=ok, Detail=found.Where(x => x!="match").ToArray() });
        }
        Console.WriteLine(JsonSerializer.Serialize(new { Assembly=Path.GetFileName(args[0]), Missing=missing, Members=results }, new JsonSerializerOptions{ WriteIndented=true }));
        return missing==0 ? 0 : 2;
    }
}
