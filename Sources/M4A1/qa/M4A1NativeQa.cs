using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

// To rerun in the editor, temporarily copy this file into Editor/.
public static class RazedM4Preview
{
    [ConCmd("razed_m4_refresh")]
    public static void Refresh()
    {
        foreach(var name in new[]{"precision_stock","heavy_barrel"})
        {
            AssetSystem.FindByPath($"gunsmith/m4a1/{name}/{name}.prefab")?.Compile(true);
            AssetSystem.FindByPath($"gunsmith/m4a1/{name}/{name}.gnsmth")?.Compile(true);
        }
        foreach(var name in new[]{"compact_suppressor","rifle_suppressor"})
        {
            AssetSystem.FindByPath($"gunsmith/m4a1/muzzle/{name}.prefab")?.Compile(true);
            AssetSystem.FindByPath($"gunsmith/m4a1/muzzle/{name}.gnsmth")?.Compile(true);
        }
        foreach(var variant in new[]{"vm","wm"}) AssetSystem.FindByPath($"weapons/m4a1/{variant}_m4a1.prefab")?.Compile(true);
    }

    [ConCmd("razed_m4_preview")]
    public static void Preview(bool world = false, bool camo = true, string mode = "texture")
    {
        var resource=ResourceLibrary.Get<EquipmentResource>("weapons/m4a1/m4a1.equip");
        var cls=GunsmithLoadoutManager.GetActiveClassIndex();
        var saved=new Dictionary<string,string>();
        foreach(var id in new[]{resource.ResourcePath,resource.ResourceName}.Distinct())
        foreach(var category in Enum.GetValues<GunsmithPartType>())
        {
            var key=$"hc1.gunsmith.class{cls}.{id}.{category}";
            saved[key]=Game.Cookies.Get<string>(key,"");
        }
        var optics=GunsmithLoadoutManager.GetCamoOnOptics();
        var custom=GunsmithLoadoutManager.GetUseCustomCamoColor(resource);
        var scene=new Scene();
        try
        {
            using var scope=scene.Push();
            var variant=world?"wm":"vm";
            var prefab=ResourceLibrary.Get<PrefabFile>($"weapons/m4a1/{variant}_m4a1.prefab");
            var root=SceneUtility.GetPrefabScene(prefab).Clone(new CloneConfig{StartEnabled=false,Transform=new()});
            foreach(var c in root.Components.GetAll<Component>(FindMode.EverythingInSelfAndDescendants)) c.Enabled=c is ModelRenderer || c is GunsmithAttachmentPoint || c is WeaponModel;
            var renderer=root.Components.Get<SkinnedModelRenderer>(FindMode.EverythingInSelf);
            renderer.UseAnimGraph=false;
            renderer.BodyGroups=world?395UL:9251UL;
            if(!world) renderer.Sequence.Name="IdlePose";
            renderer.PlaybackRate=0;
            foreach(var other in root.Components.GetAll<SkinnedModelRenderer>(FindMode.EverythingInSelfAndDescendants)) if(other!=renderer) other.Enabled=false;
            var gunsmith=root.Components.GetOrCreate<GunsmithWeapon>(); gunsmith.Resource=resource;
            foreach(var key in saved.Keys) Game.Cookies.Set(key, "__none");
            GunsmithLoadoutManager.SetUseCustomCamoColor(resource,mode=="solid");
            foreach(var name in new[]{"precision_stock","heavy_barrel"})
            {
                var part=ResourceLibrary.Get<GunsmithPart>($"gunsmith/m4a1/{name}/{name}.gnsmth");
                if(!part.IsValid() || !part.MainPrefab.IsValid()) throw new Exception($"Missing resource {name}");
                if(!part.Supports(resource)) throw new Exception($"Ineligible part {name}");
                GunsmithLoadoutManager.SetAttachment(resource,part.Category,part);
                if(!GunsmithLoadoutManager.TryGetAttachment(resource,part.Category,out var savedPart) || savedPart!=part) throw new Exception("Part cookie round-trip failed");
                var point=root.Components.GetAll<GunsmithAttachmentPoint>(FindMode.EverythingInSelfAndDescendants).Single(p=>p.Category==part.Category);
                point.SetPart(part);
                var previous=point.CurrentGameObject;
                if(!previous.IsValid()) throw new Exception("Part equip failed");
                point.SetPart(null);
                if(point.CurrentGameObject.IsValid()) throw new Exception("Part removal failed");
                previous.DestroyImmediate();
            }
            GunsmithLoadoutManager.SetAttachment(resource,GunsmithPartType.Optic,ResourceLibrary.Get<GunsmithPart>("gunsmith/m4a1/optics/m4a1_optic_rmr.gnsmth"));
            GunsmithLoadoutManager.SetCamoOnOptics(camo);
            var paint=ResourceLibrary.Get<GunsmithPart>(mode=="animated"?"gunsmith/Camos/water_animated.gnsmth":"gunsmith/Camos/gold2.gnsmth");
            GunsmithLoadoutManager.ApplyAttachments(resource,root,paint);
            root.Enabled=true;
            var camera=new GameObject(true,"QA camera").Components.Create<CameraComponent>();
            camera.BackgroundColor=new Color(.08f,.10f,.13f); camera.FieldOfView=38;
            var center=new Vector3(2,0,6.1f);
            camera.WorldPosition=center+new Vector3(4,-64,16);
            camera.WorldRotation=Rotation.LookAt(center-camera.WorldPosition);
            var light=new GameObject(true,"QA light").Components.Create<DirectionalLight>();
            light.WorldRotation=Rotation.From(new Angles(40,35,0)); light.LightColor=Color.White*2; light.SkyColor=Color.White*.5f;
            scene.EditorTick(.01f,.01f);
            foreach(var point in root.Components.GetAll<GunsmithAttachmentPoint>(FindMode.EverythingInSelfAndDescendants))
            {
                if(point.Category!=GunsmithPartType.Stock && point.Category!=GunsmithPartType.Barrel) continue;
                if(!point.CurrentGameObject.IsValid()) throw new Exception($"Missing equipped {point.Category}");
                var attachment=point.CurrentGameObject.Components.Get<GunsmithAttachment>(FindMode.EverythingInSelf);
                if(!attachment.IsValid()) throw new Exception($"Missing mounting component {point.Category}");
                attachment.Initialize(point);
                foreach(var partRenderer in point.CurrentGameObject.Components.GetAll<ModelRenderer>(FindMode.EverythingInSelfAndDescendants))
                    if(partRenderer.RenderOptions.Game!=renderer.RenderOptions.Game || partRenderer.RenderOptions.Overlay!=renderer.RenderOptions.Overlay) throw new Exception("Attachment render pass mismatch");
                Log.Info($"RAZED_M4_MOUNT {world} {point.Category} {point.CurrentGameObject.WorldTransform}");
            }
            if(!world)
            {
                var mats=renderer.Model.Materials.ToList();
                var body=mats.FindIndex(m=>m.Name.EndsWith("/v_rmr.vmat"));
                var glass=mats.FindIndex(m=>m.Name.EndsWith("/v_rmr_glass.vmat"));
                var dot=mats.FindIndex(m=>m.Name.EndsWith("/v_rmr_red_dot.vmat"));
                var bodyMat=renderer.Materials.GetOverride(body);
                if(renderer.GetBodyGroup("top_rail")!=2) throw new Exception("RMR bodygroup missing on initially disabled weapon");
                if(camo && bodyMat==renderer.Model.Materials[body]) throw new Exception("RMR housing camo override missing");
                if(!camo && bodyMat!=renderer.Model.Materials[body]) throw new Exception("RMR housing was painted with optics disabled");
                if(renderer.Materials.GetOverride(glass)!=renderer.Model.Materials[glass]) throw new Exception("Lens was painted");
                if(renderer.Materials.GetOverride(dot).GetTexture("TextureColor")==Texture.Load(paint.CamoTexture)) throw new Exception("Reticle was painted");
                Log.Info($"RAZED_M4_CAMO PASS mode={mode} enabled={camo}; RMR housing, lens, reticle checked");
            }
            if(renderer.TryGetBoneTransform("stock",out var bone)) Log.Info($"RAZED_M4_STOCKBONE {bone}");
            var folder=Path.Combine(Project.Current.GetRootPath(),"Sources","M4A1","qa"); Directory.CreateDirectory(folder);
            using var bitmap=new Bitmap(1600,700); camera.RenderToBitmap(bitmap,false);
            File.WriteAllBytes(Path.Combine(folder,$"m4a1-{variant}-{mode}-optics-{camo}.png"),bitmap.ToPng());
            Log.Info($"RAZED_M4_PREVIEW PASS world={world} camo={camo} mode={mode}; equip/remove/re-equip, cookie round-trip and render layers passed");
        }
        finally
        {
            foreach(var entry in saved) Game.Cookies.Set(entry.Key,entry.Value);
            GunsmithLoadoutManager.SetCamoOnOptics(optics);
            GunsmithLoadoutManager.SetUseCustomCamoColor(resource,custom);
            scene.Destroy();
        }
    }
}
