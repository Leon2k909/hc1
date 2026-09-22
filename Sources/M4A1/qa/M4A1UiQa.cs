using Editor;
using Sandbox;
using Sandbox.UI;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.Linq;
using System.Collections.Generic;
using System.IO;
using System.Reflection;

// Temporarily copy into Editor/ to exercise the running Gunsmith selector.
public static class RazedM4UiAudit
{
    [ConCmd("razed_m4_ui")]
    public static void Run(string action="audit")
    {
        var scene=Game.ActiveScene;
        if(!scene.IsValid())return;
        using var scope=scene.Push();
        if(action=="disk")
        {
            foreach(var name in new[]{"precision_stock/precision_stock","heavy_barrel/heavy_barrel","muzzle/compact_suppressor","muzzle/rifle_suppressor"})
            {
                var path=$"gunsmith/m4a1/{name}.gnsmth";
                var part=new GunsmithPart();
                part.LoadFromJson(File.ReadAllText(Path.Combine(Project.Current.GetRootPath(),"Assets",path)));
                if(!part.MainPrefab.IsValid() || part.EligibleEquipment.Count!=1)throw new Exception($"Disk load failed for {path}");
                Log.Info($"M4_UI DISK PASS {part.Name} prefab={part.MainPrefab.Name} eligible={part.EligibleEquipment[0].ResourcePath}");
            }
            return;
        }
        var system=scene.GetAllComponents<GunsmithSystem>().FirstOrDefault();
        if(action=="reload" && system.IsValid())
        {
            system.SetEquipment(system.Equipment);
            return;
        }
        Log.Info($"M4_UI active={system?.Equipment?.ResourcePath}");
        foreach(var category in new[]{GunsmithPartType.Stock,GunsmithPartType.Barrel,GunsmithPartType.Muzzle})
        {
            var registered=GunsmithPart.Categories.TryGetValue(category,out var list)?list:new HashSet<GunsmithPart>();
            Log.Info($"M4_UI {category} static=[{string.Join(" | ",registered.Select(p=>p.Name))}] library=[{string.Join(" | ",ResourceLibrary.GetAll<GunsmithPart>().Where(p=>p.Category==category).Select(p=>p.Name))}]");
        }
        foreach(var root in scene.GetAllComponents<GunsmithPanel>())
        foreach(var panel in Descendants(root.Panel).OfType<GunsmithAttachmentPointPanel>().ToList())
        {
            var method=typeof(GunsmithAttachmentPointPanel).GetMethod("GetPartsForCategory",BindingFlags.Instance|BindingFlags.NonPublic);
            var parts=((IEnumerable<GunsmithPart>)method.Invoke(panel,null)).ToList();
            foreach(var part in parts.Where(p=>p.Name=="Recon Barrel Kit" || p.Name=="Recon Stock" || p.IsSuppressor))
                Log.Info($"M4_UI resource {part.ResourcePath} prefabValid={part.MainPrefab.IsValid()} prefab={part.MainPrefab?.Name} currentObject={panel.AttachmentPoint?.CurrentGameObject?.Name}");
            Log.Info($"M4_UI panel={panel.Category} options=[{string.Join(" | ",parts.Select(p=>p.Name))}] rect={panel.Box.Rect} open={panel.IsViewingOptions} selected={panel.AttachmentPoint?.CurrentPart?.Name}");
            if(action=="close") panel.IsViewingOptions=false;
            if(action=="openstock" && panel.Category==GunsmithPartType.Stock) panel.IsViewingOptions=true;
            if(action=="equipstock" && panel.Category==GunsmithPartType.Stock)
            {
                if(!panel.IsViewingOptions)throw new Exception("Open Stock first");
                var label=Descendants(panel).OfType<Sandbox.UI.Label>().Single(p=>p.Text=="Recon Stock");
                label.Parent.CreateEvent("onclick");
                Log.Info("M4_UI clicked Recon Stock");
            }
            if((action=="open" && panel.Category is GunsmithPartType.Barrel or GunsmithPartType.Muzzle) || (action=="openmuzzle" && panel.Category==GunsmithPartType.Muzzle)) panel.IsViewingOptions=true;
            if((action=="equip" && panel.Category is GunsmithPartType.Barrel or GunsmithPartType.Muzzle) || (action=="equipmuzzle" && panel.Category==GunsmithPartType.Muzzle))
            {
                if(!panel.IsViewingOptions)throw new Exception("Open the selector before exercising its option click");
                var name=panel.Category==GunsmithPartType.Muzzle?"Rifle Suppressor":"Recon Barrel Kit";
                var label=Descendants(panel).OfType<Sandbox.UI.Label>().FirstOrDefault(p=>p.Text==name);
                if(label is null) throw new Exception($"Visible option missing: {name}");
                label.Parent.CreateEvent("onclick");
                Log.Info($"M4_UI clicked visible option {name}; selected={panel.AttachmentPoint?.CurrentPart?.Name}");
            }
        }
        if(action=="capture")
        {
            var camera=scene.Camera;
            Log.Info($"M4_UI camera={camera.WorldPosition} fov={camera.FieldOfView}");
            foreach(var renderer in system.Weapon.GameObject.Components.GetAll<ModelRenderer>(FindMode.EverythingInSelfAndDescendants).Where(r=>r.Enabled && r.Model is not null))
            {
                var projected=renderer.Model.Bounds.Corners.Select(p=>camera.PointToScreenNormal(renderer.WorldTransform.PointToWorld(p))).ToList();
                Log.Info($"M4_UI screen {renderer.Model.Name}: x={projected.Min(p=>p.x)}..{projected.Max(p=>p.x)} y={projected.Min(p=>p.y)}..{projected.Max(p=>p.y)}");
            }
            var path=Path.Combine(Project.Current.GetRootPath(),"Sources/M4A1/qa/live-front-end.png");
            using var bmp=new Bitmap(1920,928); scene.Camera.RenderToBitmap(bmp,true);File.WriteAllBytes(path,bmp.ToPng());
        }
    }
    private static IEnumerable<Panel> Descendants(Panel panel)
    {
        yield return panel;
        foreach(var child in panel.Children)
        foreach(var descendant in Descendants(child))yield return descendant;
    }
}
