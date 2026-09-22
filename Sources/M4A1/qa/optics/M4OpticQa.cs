using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.Linq;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Reflection;

public static class M4OpticQa
{
    static readonly string Folder=Path.Combine(Project.Current.GetRootPath(),"Sources/M4A1/qa/optics");
    [ConCmd("m4_optics_verify")]
    public static void Verify()
    {
        foreach(var name in new[]{"reflex","tube","scout"})
        {
            Test(name,false,false,true);
            Test(name,false,false,false);
            Test(name,true,true,false);
        }
        Test("scout",false,true,true);
        Test("tube",false,true,false,false);
        Log.Info("M4_OPTICS SUITE PASS (11 cases)");
    }
    [ConCmd("m4_optics_compile")]
    public static void Compile()
    {
        foreach(var name in new[]{"reflex","scout","tube"})
        {
            if(name!="tube")AssetSystem.FindByPath($"attachments/m4a1/optics/{name}_housing.vmat")?.Compile(true);
            AssetSystem.FindByPath($"attachments/m4a1/optics/{name}_reticle.vmat")?.Compile(true);
            // Compile model dependencies through the normal asset watcher.
        }
        Log.Info("M4_OPTICS compile finished");
    }
    [ConCmd("m4_optics_inspect")]
    public static void Inspect()
    {
        Directory.CreateDirectory(Folder);
        var report=new StringBuilder();
        var paths=new[]{"attachments/swb/sight/reflex/w_reflex_sight.vmdl","attachments/swb/sight/scope_hunter/w_scope_hunter_render.vmdl",
            "attachments/sight/aimpoint/aimpoint.vmdl","attachments/sh/scopes/2x/aimpoint2x.vmdl","attachments/sh/scopes/4x/scope4x.vmdl",
            "models/weapons/sbox_attachments/sight_ranged/sight_ranged.vmdl","models/weapons/sbox_attachments/sight_ranged/v_sight_ranged.vmdl"};
        var scene=new Scene();
        try
        {
            using var scope=scene.Push();
            var camera=new GameObject(true,"Optic camera").Components.Create<CameraComponent>();
            camera.BackgroundColor=new Color(.06f,.07f,.08f);camera.FieldOfView=32;
            var key=new GameObject(true,"Key").Components.Create<DirectionalLight>();
            key.WorldRotation=Rotation.From(new Angles(40,30,0));key.LightColor=Color.White*3;key.SkyColor=Color.White*.8f;
            for(int i=0;i<paths.Length;i++)
            {
                var model=Model.Load(paths[i]);
                report.AppendLine($"{i} {paths[i]} error={model.IsError} bounds={model.Bounds}");
                if(model.IsError)continue;
                report.AppendLine("materials: "+string.Join(" | ",model.Materials.Select(m=>m.Name)));
                var go=new GameObject(true,"Optic");var mr=go.Components.Create<ModelRenderer>();mr.Model=model;go.WorldScale=10;
                var center=model.Bounds.Center*10;var length=MathF.Max(model.Bounds.Size.Length*10,1);
                camera.WorldPosition=center+new Vector3(length*.75f,-length*1.8f,length*.8f);
                camera.WorldRotation=Rotation.LookAt(center-camera.WorldPosition);
                scene.EditorTick(.01f,.01f);
                using var bmp=new Bitmap(960,700);camera.RenderToBitmap(bmp,false);
                File.WriteAllBytes(Path.Combine(Folder,$"candidate-{i}.png"),bmp.ToPng());
                go.Enabled=false;
            }
            File.WriteAllText(Path.Combine(Folder,"candidates.txt"),report.ToString());
            Log.Info("M4_OPTICS candidate inspection saved");
        }
        finally { scene.Destroy(); }
    }

    [ConCmd("m4_optics_bones")]
    public static void Bones()
    {
        var scene=new Scene();
        try
        {
            using var scope=scene.Push();
            var eq=ResourceLibrary.Get<EquipmentResource>("weapons/m4a1/m4a1.equip");
            var root=eq.ViewModelPrefab.Clone(new CloneConfig{StartEnabled=false});
            var renderer=root.Components.Get<SkinnedModelRenderer>(FindMode.EverythingInSelf);
            renderer.UseAnimGraph=false;renderer.Sequence.Name="IdlePose";root.Enabled=true;
            scene.EditorTick(.01f,.01f);
            var text=new StringBuilder();
            foreach(var bone in new[]{"weapon","weapon_bone","ValveBiped.Bip01","root","m4a1","camera"})
                text.AppendLine($"{bone} found={renderer.TryGetBoneTransform(bone,out var tr)} {tr}");
            File.WriteAllText(Path.Combine(Folder,"mounts.txt"),text.ToString());
        }
        finally { scene.Destroy(); }
    }

    [ConCmd("m4_optics_qa")]
    public static void Test(string name="reflex",bool world=false,bool camo=false,bool ads=false,bool paintOptics=true)
    {
        Directory.CreateDirectory(Folder);
        var eq=ResourceLibrary.Get<EquipmentResource>("weapons/m4a1/m4a1.equip");
        var saved=new Dictionary<string,string>();
        foreach(var id in new[]{eq.ResourcePath,eq.ResourceName}.Distinct())
        foreach(var cat in Enum.GetValues<GunsmithPartType>())
        {
            var key=$"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.{cat}";
            saved[key]=Game.Cookies.Get<string>(key,"");
        }
        var custom=GunsmithLoadoutManager.GetUseCustomCamoColor(eq);var oldOpticCamo=GunsmithLoadoutManager.GetCamoOnOptics();
        var scene=new Scene();
        try
        {
            using var scope=scene.Push();
            foreach(var key in saved.Keys)Game.Cookies.Set(key,"__none");
            GunsmithLoadoutManager.SetUseCustomCamoColor(eq,false);GunsmithLoadoutManager.SetCamoOnOptics(camo&&paintOptics);
            var path=$"gunsmith/m4a1/optics/{name}.gnsmth";
            var part=ResourceLibrary.Get<GunsmithPart>(path);
            var fresh=new GunsmithPart();fresh.LoadFromJson(File.ReadAllText(Path.Combine(Project.Current.GetRootPath(),"Assets",path)));
            if(!fresh.MainPrefab.IsValid() || !fresh.Supports(eq))throw new Exception("Invalid prefab/eligibility "+name);
            part.OpticAimOffset=fresh.OpticAimOffset;part.OpticAimAngles=fresh.OpticAimAngles;part.OpticMagnification=fresh.OpticMagnification;
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Optic,part);
            if(camo)GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Camoflague,ResourceLibrary.Get<GunsmithPart>("gunsmith/camos/gold2.gnsmth"));
            var root=(world?eq.WorldModelPrefab:eq.ViewModelPrefab).Clone(new CloneConfig{StartEnabled=false});
            foreach(var c in root.Components.GetAll<Component>(FindMode.EverythingInSelfAndDescendants))c.Enabled=c is ModelRenderer || c is GunsmithAttachmentPoint;
            var renderer=root.Components.Get<SkinnedModelRenderer>(FindMode.EverythingInSelf);
            renderer.UseAnimGraph=false;renderer.PlaybackRate=0;renderer.BodyGroups=world?395UL:9251UL;
            renderer.RenderType=ModelRenderer.ShadowRenderType.On;renderer.RenderOptions.Game=true;renderer.RenderOptions.Overlay=false;
            if(!world)renderer.Sequence.Name="IdlePose";
            foreach(var other in root.Components.GetAll<SkinnedModelRenderer>(FindMode.EverythingInSelfAndDescendants))if(other!=renderer)other.Enabled=false;
            root.Components.GetOrCreate<GunsmithWeapon>().Resource=eq;
            GunsmithLoadoutManager.ApplyAttachments(eq,root);root.Enabled=true;
            var point=root.Components.GetAll<GunsmithAttachmentPoint>(FindMode.EverythingInSelfAndDescendants).Single(p=>p.Category==GunsmithPartType.Optic);
            if(!point.CurrentGameObject.IsValid())throw new Exception("Missing optic instance");
            var optic=point.CurrentGameObject.Components.Get<ModelRenderer>(FindMode.EverythingInSelf);
            if(optic.Model is null || optic.Model.IsError || optic.Model.Materials.Any(m=>m.Name.Contains("error")))throw new Exception("Missing optic model/material "+name+" model="+optic.Model?.Name+" materials="+string.Join("|",optic.Model.Materials.Select(m=>m.Name)));
            if(renderer.GetBodyGroup("top_rail")!=(world?1:3))throw new Exception("Carry handle still visible");
            var camera=new GameObject(true,"QA camera").Components.Create<CameraComponent>();
            camera.BackgroundColor=new Color(.075f,.087f,.10f);camera.FieldOfView=32;camera.ZNear=.1f;
            var center=new Vector3(1,0,8);camera.WorldPosition=center+new Vector3(3,-50,16);camera.WorldRotation=Rotation.LookAt(center-camera.WorldPosition);
            var keylight=new GameObject(true,"QA key").Components.Create<DirectionalLight>();
            keylight.WorldRotation=Rotation.From(new Angles(38,38,0));keylight.LightColor=Color.White*3;keylight.SkyColor=Color.White*.8f;
            var mount=point.CurrentGameObject.Components.Get<GunsmithAttachment>(FindMode.EverythingInSelf);
            scene.EditorTick(.01f,.01f);mount.Initialize(point);
            if(ads && !world)
            {
                root.WorldPosition=part.OpticAimOffset;renderer.PlaybackRate=1;renderer.UseAnimGraph=true;renderer.PlayAnimationsInEditorScene=true;
                renderer.Set("ironsights",1);renderer.Set("speed_ironsights",1);renderer.Set("b_grounded",true);
                renderer.SceneModel.Transform=renderer.WorldTransform;
                for(int i=0;i<100;i++){scene.EditorTick(.02f,.02f);renderer.SceneModel.Update(.02f);}
                mount.Initialize(point);
                camera.WorldPosition=Vector3.Zero;camera.WorldRotation=Rotation.Identity;camera.FieldOfView=75;
            }
            var lensIndex=optic.Model.Materials.ToList().FindIndex(m=>m.Name.Contains("reticle"));
            if(lensIndex<0)throw new Exception("No separate lens/reticle material");
            if(!Equals(optic.Materials.GetOverride(lensIndex)?.Shader,optic.Model.Materials[lensIndex].Shader))throw new Exception("Camo replaced lens shader");
            var housingIndex=optic.Model.Materials.ToList().FindIndex(m=>!m.Name.Contains("reticle")&&!m.Name.Contains("lens"));
            if(camo && Equals(optic.Materials.GetOverride(housingIndex),optic.Model.Materials[housingIndex])==paintOptics)throw new Exception("Housing camo toggle incorrect");
            var lensWorld=optic.WorldTransform.PointToWorld(LensCenter(optic.Model));
            if(ads && (lensWorld.x<1 || MathF.Abs(lensWorld.y)>.015f || MathF.Abs(lensWorld.z)>.015f))throw new Exception("Optic not centered on aim ray: "+lensWorld);
            Log.Info($"M4_OPTICS MOUNT {name} world={world} aim={part.OpticAimOffset} root={root.WorldPosition} renderer={renderer.WorldPosition} scene={renderer.SceneModel.Transform.Position} model={optic.Model.Bounds} transform={optic.WorldTransform} lens={LensCenter(optic.Model)} reticleWorld={optic.WorldTransform.PointToWorld(LensCenter(optic.Model))} muzzle={renderer.GetAttachment("muzzle")}");
            using var bmp=new Bitmap(1400,900);camera.RenderToBitmap(bmp,false);
            File.WriteAllBytes(Path.Combine(Folder,$"{name}-{(world?"world":"view")}{(camo?"-camo":"")}{(!paintOptics?"-unpainted":"")}{(ads?"-ads":"")}.png"),bmp.ToPng());
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Optic,null);GunsmithLoadoutManager.ApplyAttachments(eq,root);
            if(renderer.GetBodyGroup("top_rail")!=0)throw new Exception("Factory sights not restored");
            if(world)
            {
                foreach(var legacy in new[]{"m4a1_optic_eotech","m4a1_optic_rmr"})
                {
                    GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Optic,ResourceLibrary.Get<GunsmithPart>($"gunsmith/m4a1/optics/{legacy}.gnsmth"));
                    GunsmithLoadoutManager.ApplyAttachments(eq,root);
                    if(renderer.GetBodyGroup("top_rail")!=0)throw new Exception("Legacy world appearance changed: "+legacy);
                }
                GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Optic,null);
            }
            var weapon=eq.MainPrefab.Clone(new CloneConfig{StartEnabled=false});var equipment=weapon.Components.Get<Equipment>(FindMode.EverythingInSelf);
            var aim=weapon.Components.Get<ManualOffset>(FindMode.EverythingInSelfAndDescendants);
            typeof(EquipmentComponent).GetProperty("Equipment",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(aim,equipment);
            aim.IsAiming=true;
            if(((IViewModelOffset)aim).PositionOffset!=aim.AimOffset)throw new Exception("Default aim not restored");
            var baseFov=90f;var defaultOffset=equipment.GetAimFovOffset(baseFov);
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Optic,part);
            if(((IViewModelOffset)aim).PositionOffset!=part.OpticAimOffset)throw new Exception("Per-optic aim not applied");
            aim.IsAiming=false;
            if(((IViewModelOffset)aim).PositionOffset!=Vector3.Zero)throw new Exception("Optic offset leaked into hip fire");
            var mag=MathF.Tan((baseFov+defaultOffset)*MathF.PI/360f)/MathF.Tan((baseFov+equipment.GetAimFovOffset(baseFov))*MathF.PI/360f);
            if(MathF.Abs(mag-part.OpticMagnification)>.001f)throw new Exception("Incorrect magnification");
            Log.Info($"M4_OPTICS PASS {name} world={world} camo={camo} paintOptics={paintOptics} ads={ads}; model/materials, mount, lens isolation, restore, magnification={mag}");
        }
        finally
        {
            foreach(var kv in saved)Game.Cookies.Set(kv.Key,kv.Value);
            GunsmithLoadoutManager.SetUseCustomCamoColor(eq,custom);GunsmithLoadoutManager.SetCamoOnOptics(oldOpticCamo);scene.Destroy();
        }
    }

    static Vector3 LensCenter(Model model)
    {
        var flags=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
        var count=(int)typeof(Model).GetMethod("GetLodDrawCallCount",flags).Invoke(model,new object[]{0});
        var range=typeof(Model).GetMethod("GetLodDrawCallRange",flags);var vertices=model.GetVertices();var indices=model.GetIndices();
        for(int i=0;i<count;i++)
        {
            var args=new object[]{0,i,0,0,0};range.Invoke(model,args);
            if(!model.Materials[i].Name.Contains("reticle"))continue;
            var points=indices.Skip((int)args[2]).Take((int)args[3]).Select(idx=>vertices[idx+(int)args[4]].Position).ToList();
            return new Vector3((points.Min(v=>v.x)+points.Max(v=>v.x))/2,(points.Min(v=>v.y)+points.Max(v=>v.y))/2,(points.Min(v=>v.z)+points.Max(v=>v.z))/2);
        }
        return model.Bounds.Center;
    }
}
