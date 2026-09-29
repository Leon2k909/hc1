using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;

/// <summary>Isolated M16 attachment fixtures. They never write player loadouts or the active scene.</summary>
public static class Hc1M16GunsmithQa
{
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/m16-gunsmith" );

    private static void Clear( GunsmithAttachmentPoint point )
    {
        var previous = point.CurrentGameObject;
        point.SetPart( null );
        // This isolated scene has no game frame to flush deferred destruction between fixture cases.
        previous?.DestroyImmediate();
    }

    [ConCmd( "hc1_m16_compile" )]
    public static void Compile()
    {
        foreach ( var folder in new[] { "Assets/Weapons/M16", "Assets/gunsmith/m16" } )
        foreach ( var file in Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), folder ), "*", SearchOption.AllDirectories ) )
        {
            var ext = Path.GetExtension( file );
            if ( ext == ".meta" || file.EndsWith( "_c" ) ) continue;
            var asset = AssetSystem.FindByPath( file ) ?? AssetSystem.RegisterFile( file );
            if ( ext is ".vmdl" or ".prefab" or ".gnsmth" or ".vanmgrph" or ".sound" ) asset?.Compile( true );
        }
        Log.Info( "M16_QA compilation requested" );
    }

    [ConCmd( "hc1_m16_parts_check" )]
    public static async void Check( bool world = true )
    {
        Directory.CreateDirectory( Folder );
        var report = new List<string>();
        var scene = new Scene();
        var mode = world ? "world" : "view";
        try
        {
            using var scope = scene.Push();
            var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/m16/{(world ? "wm" : "vm")}_m16.prefab" );
            var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
            root.Components.GetOrCreate<GunsmithWeapon>().Resource = ResourceLibrary.Get<EquipmentResource>( "weapons/m16/m16.equip" );
            foreach ( var c in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
                c.Enabled = c is ModelRenderer || c is GunsmithAttachmentPoint;
            var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
            Require( renderer.Model is not null && !renderer.Model.IsError, "M16 model compiled" );
            renderer.UseAnimGraph = false;
            renderer.RenderOptions.Game = true;
            renderer.RenderOptions.Overlay = false;
            renderer.RenderType = ModelRenderer.ShadowRenderType.On;
            renderer.PlaybackRate = 0;
            foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
                if ( other != renderer ) other.Enabled = false;
            var prefabMask = renderer.BodyGroups;
            foreach ( var group in renderer.Model.Parts.All ) renderer.SetBodyGroup( group.Name, 0 );
            var factoryMask = renderer.BodyGroups;
            report.Add( $"Factory mask={factoryMask}; prefab mask={prefabMask}" );
            File.WriteAllText( Path.Combine( Folder, $"default-{mode}.txt" ), factoryMask.ToString() );
            Require( prefabMask == factoryMask, "default prefab bodygroups" );
            Require( renderer.Model.Materials.All( m => !m.Name.Contains( "error" ) ), "factory materials" );
            var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/m16/m16.equip" );
            var parts = new List<GunsmithPart>();
            foreach ( var file in Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/gunsmith/m16" ), "*.gnsmth" ) )
            {
                var path = Path.GetRelativePath( Project.Current.GetAssetsPath(), file ).Replace( '\\', '/' );
                parts.Add( await ResourceLibrary.LoadAsync<GunsmithPart>( path ) );
            }
            Require( parts.Count == 20 && parts.All( p => p.IsValid() && p.Supports( resource ) ), "twenty M16 parts registered" );
            var points = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
                .ToDictionary( p => p.Category );
            root.Enabled = true;
            scene.EditorTick( .01f, .01f );
            Require( new[] { GunsmithPartType.Stock, GunsmithPartType.Barrel, GunsmithPartType.RearGrip, GunsmithPartType.Magazine }
                .All( points.ContainsKey ), "all four added categories" );
            foreach ( var part in parts )
            {
                var point = points[part.Category];
                point.SetPart( part );
                foreach ( var entry in point.FittedBodygroups )
                    // Both empty laser-rail choices resolve to choice 0 when read back from the mesh mask.
                    Require( renderer.GetBodyGroup( entry.Key ) == (entry.Key == "laser_rail" && entry.Value == 2 ? 0 : entry.Value),
                        $"factory mesh replaced: {entry.Key}, actual={renderer.GetBodyGroup( entry.Key )}, requested={entry.Value}" );
                if ( part.ModifyBodygroups )
                    foreach ( var entry in part.Bodygroups ) Require( renderer.GetBodyGroup( entry.Key ) == entry.Value, "magazine choice" );
                if ( part.Category == GunsmithPartType.Magazine )
                {
                    Require( part.MagazineCapacity is 15 or 45 or 60, "magazine capacity" );
                    Require( part.ReloadAnimation is >= 1 and <= 3 && part.ReloadTime > 0 && part.EmptyReloadTime > 0
                        && part.ReloadSounds.Count > 0 && part.EmptyReloadSounds.Count > 0, "matching magazine reload and sounds" );
                }
                if ( point.CurrentGameObject.IsValid() )
                    foreach ( var mesh in point.CurrentGameObject.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
                        Require( mesh.Model is not null && !mesh.Model.IsError && mesh.Model.Materials.All( m => !m.Name.Contains( "error" ) ), "attachment model/materials" );
                Clear( point );
                Require( renderer.BodyGroups == factoryMask, "Standard restores factory geometry: " + part.Name );
                report.Add( "PASS equip/reset " + part.Name );
            }
            var muzzle = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/mw2022/att_vm_silencer02.gnsmth" );
            var laser = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/mw2022/att_vm_p01_ar_mike4_laser01.gnsmth" );
            var grip = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/mw2022/att_vm_p01_ar_mike4_angledgrip01.gnsmth" );
            foreach ( var part in parts.Where( p => p.Category == GunsmithPartType.Barrel ) )
            {
                points[GunsmithPartType.Barrel].SetPart( part );
                var barrel = points[GunsmithPartType.Barrel].CurrentGameObject.Components.Get<GunsmithMw22Attachment>( FindMode.EverythingInSelf );
                Require( barrel.IsValid(), "barrel mount initialized" );
                var offset = points[GunsmithPartType.Barrel].MountOffset;
                foreach ( var (attachment, target) in new[] { (muzzle, barrel.BarrelMuzzle), (laser, barrel.BarrelLaser), (grip, barrel.BarrelGrip) } )
                {
                    var point = points[attachment.Category];
                    Require( attachment.MainPrefab.IsValid(), "accessory prefab loaded: " + attachment.Name );
                    point.SetPart( attachment );
                    var mount = point.CurrentGameObject.Components.Get<GunsmithMw22Attachment>( FindMode.EverythingInSelf );
                    Require( mount.IsValid(), "accessory mount initialized: " + attachment.Name );
                    mount.RefreshMount();
                    Require( mount.WorldPosition.Distance( target + offset ) < .02f, "accessory follows barrel: " + attachment.Name );
                }
                Require( renderer.GetBodyGroup( "laser_rail" ) == 0, "replacement barrel hides factory laser rail" );
                Require( renderer.GetBodyGroup( "muzzle_tip" ) == 1, "replacement barrel hides factory flash hider" );
                foreach ( var category in new[] { GunsmithPartType.Muzzle, GunsmithPartType.Laser, GunsmithPartType.Underbarrel } )
                    Clear( points[category] );
                var factory = renderer.Components.Get<GunsmithMw22Factory>( FindMode.EverythingInSelf );
                factory.Refresh();
                var effect = factory.MuzzleEffectPoint;
                Require( effect.WorldPosition.Distance( barrel.BarrelFlash + offset ) < .02f, "discharge follows barrel" );
                Clear( points[GunsmithPartType.Barrel] );
                Require( renderer.BodyGroups == factoryMask, "barrel combination resets" );
                report.Add( "PASS barrel/muzzle/laser/grip combination: " + part.Name );
            }
            var camera = new GameObject( true, "M16 QA camera" ).AddComponent<CameraComponent>();
            camera.BackgroundColor = new Color( .025f, .03f, .035f );
            camera.FieldOfView = 34;
            var center = new Vector3( 3, 0, 2.5f );
            camera.WorldPosition = center + new Vector3( 7, -77, 15 );
            camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
            var light = new GameObject( true, "M16 QA light" ).AddComponent<DirectionalLight>();
            light.WorldRotation = Rotation.From( new Angles( 35, 35, 0 ) );
            light.LightColor = Color.White * 2;
            light.SkyColor = Color.White * .7f;
            void Render( string name )
            {
                // Flush the scene's queued starts/removals before taking the settled frame.
                scene.EditorTick( .01f, .01f );
                scene.EditorTick( .01f, .01f );
                using var bitmap = new Bitmap( 1600, 900 );
                camera.RenderToBitmap( bitmap, false );
                scene.EditorTick( .01f, .01f );
                camera.RenderToBitmap( bitmap, false );
                File.WriteAllBytes( Path.Combine( Folder, $"{mode}-{name}.png" ), bitmap.ToPng() );
            }
            report.Add( "Standard fixture meshes=" + root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ).Count() );
            Render( "standard" );
            foreach ( var part in parts.Where( p => p.Category == GunsmithPartType.Stock ) )
            {
                Clear( points[GunsmithPartType.Stock] );
                points[GunsmithPartType.Stock].SetPart( part );
                Render( Path.GetFileNameWithoutExtension( part.ResourcePath ) );
            }
            foreach ( var category in new[] { GunsmithPartType.Barrel, GunsmithPartType.RearGrip, GunsmithPartType.Magazine } )
                points[category].SetPart( parts.Last( p => p.Category == category ) );
            Render( "combined" );
            report.Add( "PASS all checks" );
        }
        catch ( Exception e ) { report.Add( "FAIL " + e ); Log.Error( e ); }
        finally
        {
            File.WriteAllLines( Path.Combine( Folder, $"parts-{mode}.txt" ), report );
            scene.Destroy();
        }
    }

    [ConCmd( "hc1_m16_ammo_check" )]
    public static void AmmoCheck()
    {
        Directory.CreateDirectory( Folder );
        var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/m16/m16.equip" );
        var report = new List<string>();
        var before = new Dictionary<string, string>();
        foreach ( var id in new[] { resource.ResourcePath, resource.ResourceName }.Distinct() )
        {
            var key = $"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.Magazine";
            before[key] = Game.Cookies.Get<string>( key, "" );
        }
        var current = typeof( Pawn ).GetProperty( "Current", BindingFlags.Static | BindingFlags.NonPublic );
        var previousPawn = current.GetValue( null );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            Require( AttachmentUnlocks.GetSlots( resource ).Count == 9, "nine Gunsmith categories" );
            var pawn = new GameObject( false, "M16 QA owner" ).AddComponent<PlayerPawn>();
            current.SetValue( null, pawn );
            var root = new GameObject( false, "M16 QA ammo" );
            var equipment = root.AddComponent<Equipment>(); equipment.Owner = pawn; equipment.Resource = resource;
            var ammo = new GameObject( root, false, "Ammo" ).AddComponent<WeaponAmmo>(); ammo.MaxAmmo = 30; ammo.Ammo = 12;
            var refresh = typeof( Equipment ).GetMethod( "RefreshAmmunitionLoadout", BindingFlags.NonPublic | BindingFlags.Instance );
            foreach ( var part in ResourceLibrary.GetAll<GunsmithPart>().Where( p => p.Category == GunsmithPartType.Magazine && p.Supports( resource ) ) )
            {
                GunsmithLoadoutManager.SetAttachment( resource, GunsmithPartType.Magazine, part );
                refresh.Invoke( equipment, null );
                var tune = WeaponTuningManager.GetTuning( resource.ResourceName );
                Require( ammo.GetEffectiveMaxAmmo() == (int)(part.MagazineCapacity * (1f + tune.MagSize * .04f)), "capacity " + part.Name );
                Require( equipment.ReloadMagazine == part && part.ReloadSounds.Count > 0 && part.EmptyReloadSounds.Count > 0, "reload " + part.Name );
                Require( ammo.Ammo == 12, "changing magazines does not refill ammo" );
                report.Add( "PASS capacity/reload/no free ammo: " + part.Name );
            }
            GunsmithLoadoutManager.SetAttachment( resource, GunsmithPartType.Magazine, null );
            refresh.Invoke( equipment, null );
            var standardTuning = WeaponTuningManager.GetTuning( resource.ResourceName );
            Require( ammo.GetEffectiveMaxAmmo() == (int)(30 * (1f + standardTuning.MagSize * .04f)) && equipment.ReloadMagazine is null, "standard magazine restored" );
            report.Add( "PASS nine categories and standard 30-round magazine restoration" );
        }
        catch ( Exception e ) { report.Add( "FAIL " + e ); Log.Error( e ); }
        finally
        {
            current.SetValue( null, previousPawn );
            foreach ( var cookie in before ) Game.Cookies.Set( cookie.Key, cookie.Value );
            scene.Destroy();
            File.WriteAllLines( Path.Combine( Folder, "ammo-validation.txt" ), report );
        }
    }

    private static void Require( bool condition, string message )
    {
        if ( !condition ) throw new Exception( "M16_QA " + message );
    }
}
