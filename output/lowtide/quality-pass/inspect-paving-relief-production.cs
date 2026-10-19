var paths=new[]{"materials/lowtide/lt_setts.vmat","materials/lowtide/paving_relief/lt_setts_relief.vmat"};
return paths.Select(path=>{
 var material=Material.Load(path);
 return new {path,material.IsError,
  textures=new[]{"g_tColor","g_tNormal","g_tRma","g_tHeight"}.Select(name=>new{name,width=material.GetTexture(name)?.Width,height=material.GetTexture(name)?.Height}).ToArray(),
  depth=material.GetVector4("g_flReliefDepth"),scale=material.GetVector4("g_vPavingScale"),region=material.GetVector4("g_vPavingRegion")};
}).ToArray();
