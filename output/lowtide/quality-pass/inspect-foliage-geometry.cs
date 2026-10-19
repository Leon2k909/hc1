var model=Model.Load("models/sbox_props/trees/oak/tree_oak_medium_a.vmdl");
var data=new System.Collections.Generic.List<object>();
for(int lod=0;lod<=Math.Max(0,model.MaxLodLevel);lod++)
{
 var draws=new System.Collections.Generic.List<object>();
 for(int draw=0;draw<model.GetLodDrawCallCount(lod);draw++)
 {
  if(!model.TryReadDrawCall(lod,draw,out var vertices,out var indices,out var streams))throw new Exception("Readback failed");
  draws.Add(new{draw,vertices=vertices.Length,triangles=indices.Length/3,streams=streams.ToString()});
 }
 data.Add(new{lod,draws});
}
return new{model.MaxLodLevel,model.MeshCount,bounds=model.Bounds,switchDistances=model.GetLodSwitchDistances(),data};
