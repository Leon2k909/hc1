var flags=System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance;
var t=typeof(IndirectLightVolume);
var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor&&s.Scene.Source?.ResourcePath=="scenes/maps/lowtide/lowtide.scene");
var volumes=session.Scene.GetAllComponents<IndirectLightVolume>().Select(v=>new{v.GameObject.Name,v.ProbeCounts,v.RuntimeIntensity,v.RuntimeContrast,Irradiance=v.IrradianceTexture?.ResourcePath,Distance=v.DistanceTexture?.ResourcePath,Relocation=v.RelocationTexture?.ResourcePath}).ToArray();
return new{Game.IsPlaying,session.HasUnsavedChanges,volumes,Methods=t.GetMethods(flags).Where(m=>m.Name=="BakeProbes"||m.Name=="BakeProbesUnavailableMessage").Select(m=>new{m.Name,m.IsPublic,Return=m.ReturnType.FullName,Parameters=m.GetParameters().Select(p=>new{p.Name,Type=p.ParameterType.FullName}).ToArray()}).ToArray()};
