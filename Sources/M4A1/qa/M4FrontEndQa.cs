using Editor;
using Sandbox;
using Sandbox.UI;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.Linq;
using System.IO;
using System.Collections.Generic;
using System.Reflection;

public static class M4FrontEndQa
{
    [ConCmd("m4_front_qa")]
    public static void Run(bool world=false,string muzzle="none",bool stock=false)
    {
        var eq=ResourceLibrary.Get<EquipmentResource>("weapons/m4a1/m4a1.equip");
        var saved=new Dictionary<string,string>();
        foreach(var id in new[]{eq.ResourcePath,eq.ResourceName}.Distinct())
        foreach(var cat in Enum.GetValues<GunsmithPartType>())
        {
            var key=$"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.{cat}";
            saved[key]=Game.Cookies.Get<string>(key,"");
        }
        var custom=GunsmithLoadoutManager.GetUseCustomCamoColor(eq);
        var scene=new Scene();
        try
        {
            using var scope=scene.Push();
            foreach(var key in saved.Keys)Game.Cookies.Set(key,"__none");
            GunsmithLoadoutManager.SetUseCustomCamoColor(eq,false);
            var kit=ResourceLibrary.Get<GunsmithPart>("gunsmith/m4a1/heavy_barrel/heavy_barrel.gnsmth");
            var suppressor=muzzle=="none"?null:ResourceLibrary.Get<GunsmithPart>($"gunsmith/m4a1/muzzle/{muzzle}.gnsmth");
            var customStock=stock?ResourceLibrary.Get<GunsmithPart>("gunsmith/m4a1/precision_stock/precision_stock.gnsmth"):null;
            foreach(var part in new[]{kit,suppressor,customStock}.Where(p=>p is not null))
            {
                var fresh=new GunsmithPart();
                fresh.LoadFromJson(File.ReadAllText(Path.Combine(Project.Current.GetRootPath(),"Assets",part.ResourcePath)));
                if(!fresh.MainPrefab.IsValid() || !fresh.Supports(eq))throw new Exception("Invalid serialized prefab/eligibility: "+part.ResourcePath);
                GunsmithLoadoutManager.SetAttachment(eq,part.Category,part);
            }
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Optic,ResourceLibrary.Get<GunsmithPart>("gunsmith/m4a1/optics/m4a1_optic_rmr.gnsmth"));
            var root=(world?eq.WorldModelPrefab:eq.ViewModelPrefab).Clone(new CloneConfig{StartEnabled=false});
            foreach(var c in root.Components.GetAll<Component>(FindMode.EverythingInSelfAndDescendants))c.Enabled=c is ModelRenderer || c is GunsmithAttachmentPoint || c is WeaponModel;
            var renderer=root.Components.Get<SkinnedModelRenderer>(FindMode.EverythingInSelf);
            renderer.UseAnimGraph=false;renderer.PlaybackRate=0;renderer.BodyGroups=world?395UL:9251UL;
            if(!world)renderer.Sequence.Name="IdlePose";
            foreach(var other in root.Components.GetAll<SkinnedModelRenderer>(FindMode.EverythingInSelfAndDescendants))if(other!=renderer)other.Enabled=false;
            root.Components.GetOrCreate<GunsmithWeapon>().Resource=eq;
            GunsmithLoadoutManager.ApplyAttachments(eq,root);root.Enabled=true;
            var camera=new GameObject(true,"QA camera").Components.Create<CameraComponent>();
            camera.BackgroundColor=new Color(.08f,.095f,.115f);camera.FieldOfView=37;
            var center=new Vector3(5,0,6.7f);camera.WorldPosition=center+new Vector3(5,-75,17);camera.WorldRotation=Rotation.LookAt(center-camera.WorldPosition);
            var keylight=new GameObject(true,"QA key").Components.Create<DirectionalLight>();
            keylight.WorldRotation=Rotation.From(new Angles(38,38,0));keylight.LightColor=Color.White*3;keylight.SkyColor=Color.White*.8f;
            scene.EditorTick(.01f,.01f);
            var points=root.Components.GetAll<GunsmithAttachmentPoint>(FindMode.EverythingInSelfAndDescendants).ToList();
            foreach(var point in points.Where(p=>p.Category is GunsmithPartType.Barrel or GunsmithPartType.Muzzle or GunsmithPartType.Stock))
            {
                if(point.Category==GunsmithPartType.Muzzle && suppressor is null)continue;
                if(point.Category==GunsmithPartType.Stock && customStock is null)continue;
                if(!point.CurrentGameObject.IsValid())throw new Exception("Missing mesh "+point.Category);
                point.CurrentGameObject.Components.Get<GunsmithAttachment>(FindMode.EverythingInSelf).Initialize(point);
                var partRenderer=point.CurrentGameObject.Components.Get<ModelRenderer>(FindMode.EverythingInSelf);
                if(partRenderer.Model is null || partRenderer.Model.IsError)throw new Exception("Invalid model "+point.Category);
                if(world && point.Category==GunsmithPartType.Barrel && !partRenderer.Model.Name.EndsWith("heavy_barrel_world.vmdl"))throw new Exception("World rail variant not selected");
                if(point.Category==GunsmithPartType.Stock)
                {
                    var attachment=point.CurrentGameObject.Components.Get<GunsmithStockAttachment>(FindMode.EverythingInSelf);
                    Log.Info($"M4_STOCK mount model={renderer.Model.Name} replacement={attachment.WorldBodyReplacement?.Name} error={attachment.WorldBodyReplacement?.IsError} bodymask={renderer.BodyGroups} renderers={point.CurrentGameObject.Components.GetAll<ModelRenderer>(FindMode.EverythingInSelfAndDescendants).Count()}");
                }
            }
            var handguard=renderer.Model.Materials.ToList().FindIndex(m=>m.Name.EndsWith("/v_m4a1_handguard.vmat"));
            var nodraw=Material.Load("attachments/m4a1/materials/hidden.vmat");
            if(!world && renderer.Materials.GetOverride(handguard)!=nodraw)throw new Exception("Old handguard not hidden");
            var stockMaterial=renderer.Model.Materials.ToList().FindIndex(m=>m.Name.EndsWith("/v_m4a1_stock.vmat"));
            if(stock && !world && renderer.Materials.GetOverride(stockMaterial)!=nodraw)throw new Exception("Factory stock not hidden");
            if(stock && world && (renderer.BodyGroups & 1UL)!=0)throw new Exception("Factory world stock still visible");
            var weapon=eq.MainPrefab.Clone(new CloneConfig{StartEnabled=false});
            var shoot=weapon.Components.Get<Shootable>(FindMode.EverythingInSelfAndDescendants);
            // EditorTick does not run EquipmentComponent.OnAwake; supply its cached parent.
            typeof(EquipmentComponent).GetProperty("Equipment",BindingFlags.NonPublic|BindingFlags.Instance).SetValue(shoot,weapon.Components.Get<Equipment>(FindMode.EverythingInSelf));
            var isSuppressed=typeof(Shootable).GetMethod("UseSuppressedEffects",BindingFlags.NonPublic|BindingFlags.Instance);
            if((bool)isSuppressed.Invoke(shoot,null)!=(suppressor is not null))throw new Exception("Suppression effect state incorrect");
            if(suppressor is not null && shoot.SuppressedShootSound is null)throw new Exception("Missing suppressed sound");
            var folder=Path.Combine(Project.Current.GetRootPath(),"Sources/M4A1/qa");
            using var bmp=new Bitmap(1800,760);camera.RenderToBitmap(bmp,false);File.WriteAllBytes(Path.Combine(folder,$"front-{(world?"wm":"vm")}-{muzzle}{(stock?"-stock":"")}.png"),bmp.ToPng());
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Barrel,null);
            GunsmithLoadoutManager.ApplyAttachments(eq,root);
            if(!world && renderer.Materials.GetOverride(handguard)==nodraw)throw new Exception("Stock handguard did not return");
            if(!world && renderer.GetBodyGroup("gasblock")!=1)throw new Exception("Removing barrel kit broke optic bodygroup");
            if(suppressor is not null && points.Single(p=>p.Category==GunsmithPartType.Muzzle).CurrentPart!=suppressor)throw new Exception("Barrel removal removed suppressor");
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Muzzle,null);
            if((bool)isSuppressed.Invoke(shoot,null))throw new Exception("Suppression stuck after removal");
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Optic,null);
            GunsmithLoadoutManager.ApplyAttachments(eq,root);
            if(renderer.GetBodyGroup("gasblock")!=0)throw new Exception("Default gas block did not return");
            GunsmithLoadoutManager.SetAttachment(eq,GunsmithPartType.Stock,null);
            GunsmithLoadoutManager.ApplyAttachments(eq,root);
            if(stock && world && (renderer.BodyGroups & 1UL)==0)throw new Exception("Default world body not restored");
            if(stock && !world && renderer.Materials.GetOverride(stockMaterial)==nodraw)throw new Exception("Default stock material not restored");
            Log.Info($"M4_FRONT PASS world={world} muzzle={muzzle} stock={stock}: disk load, independent slots, handguard/stock restore, suppression on/off");
        }
        finally
        {
            foreach(var kv in saved)Game.Cookies.Set(kv.Key,kv.Value);
            GunsmithLoadoutManager.SetUseCustomCamoColor(eq,custom);scene.Destroy();
        }
    }
}
