using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using Sandbox.UI;
using Label = Sandbox.UI.Label;

public static class Hc1AugGunsmithQa
{
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/aug-gunsmith" );

    [ConCmd( "hc1_aug_compile" )]
    public static void Compile()
    {
        var root = Project.Current.GetRootPath();
        foreach ( var folder in new[] { "Assets/Weapons/AUG", "Assets/gunsmith/aug" } )
        foreach ( var file in Directory.GetFiles( Path.Combine( root, folder ), "*", SearchOption.AllDirectories ) )
        {
            var ext = Path.GetExtension( file );
            if ( ext is ".meta" || file.EndsWith( "_c" ) ) continue;
            var asset = AssetSystem.FindByPath( file ) ?? AssetSystem.RegisterFile( file );
            if ( ext is ".vmdl" or ".vmat" or ".prefab" or ".gnsmth" or ".vanmgrph" or ".sound" ) asset?.Compile( true );
        }
        Log.Info( "AUG_QA: assets registered and compilation requested" );
    }

    [ConCmd( "hc1_aug_parts_check" )]
    public static async void Check( bool world = true, int variant = 1 )
    {
        Directory.CreateDirectory( Folder );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/aug/{(world ? "wm" : "vm")}_aug.prefab" );
            var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
            foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
                component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
            var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
            Require( renderer.Model is not null && !renderer.Model.IsError, "AUG model compiled" );
            Require( renderer.Model.Materials.All( m => !m.Name.Contains( "error" ) ), "materials resolved" );
            renderer.UseAnimGraph = false;
            var prefabMask = renderer.BodyGroups;
            renderer.BodyGroups = 0;
            foreach ( var group in renderer.Model.Parts.All ) renderer.SetBodyGroup( group.Name, 0 );
            Require( prefabMask == renderer.BodyGroups, "prefab includes every factory part" );
            File.WriteAllText( Path.Combine( Folder, $"default-{(world ? "world" : "view")}.txt" ), renderer.BodyGroups.ToString() );
            Log.Info( $"AUG_QA default {(world ? "world" : "view")} mask={renderer.BodyGroups}" );
            renderer.RenderOptions.Game = true;
            renderer.RenderOptions.Overlay = false;
            renderer.RenderType = ModelRenderer.ShadowRenderType.On;
            renderer.Sequence.Name = "idle";
            renderer.PlaybackRate = 0;
            foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
                if ( other != renderer ) other.Enabled = false;
            var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/aug/aug.equip" );
            var partPaths = Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/gunsmith/aug" ), "*.gnsmth", SearchOption.AllDirectories );
            var parts = new System.Collections.Generic.List<GunsmithPart>();
            foreach ( var file in partPaths )
            {
                var path = Path.GetRelativePath( Project.Current.GetAssetsPath(), file ).Replace( '\\', '/' );
                var part = await ResourceLibrary.LoadAsync<GunsmithPart>( path );
                Log.Info( $"AUG_QA loaded {path}: {part?.Name ?? "null"}" );
                parts.Add( part );
            }
            Require( parts.Count == 4 && parts.All( p => p.IsValid() ), "four AUG-specific parts registered" );
            foreach ( var part in parts )
            {
                Require( part.Supports( resource ), "AUG eligibility" );
                var point = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == part.Category );
                var group = part.Bodygroups.Single();
                var original = renderer.BodyGroups & renderer.Model.Parts.Get( group.Key ).Mask;
                point.SetPart( part );
                Require( renderer.GetBodyGroup( group.Key ) == group.Value, $"selected {part.Name}" );
                point.SetPart( null );
                Require( (renderer.BodyGroups & renderer.Model.Parts.Get( group.Key ).Mask) == original, $"factory restored after {part.Name}" );
            }
            if ( variant > 0 )
            {
                foreach ( var part in parts.Where( p => p.Category != GunsmithPartType.Stock || p.Name == (variant == 1 ? "Lightweight Stock" : "Padded Tactical Stock") ) )
                    root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == part.Category ).SetPart( part );
                Require( renderer.GetBodyGroup( "muzzle_tip" ) == 1, "long barrel has its matching flash hider" );
                var muzzle = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == GunsmithPartType.Muzzle );
                var suppressor = ResourceLibrary.GetAll<GunsmithPart>().First( p => p.Category == GunsmithPartType.Muzzle && p.IsSuppressor && p.Supports( resource ) );
                muzzle.SetPart( suppressor );
                Require( renderer.GetBodyGroup( "muzzle_tip" ) == 2, "suppressor hides barrel flash hider" );
                Require( Math.Abs( GunsmithAttachmentPoint.MuzzleShift( root ).x - 6.102728f ) < .001f, "long barrel shifts muzzle mount" );
                muzzle.SetPart( null );
                Require( renderer.GetBodyGroup( "muzzle_tip" ) == 1, "removing suppressor restores long flash hider" );
            }
            root.Enabled = true;
            var camera = new GameObject( true, "AUG QA camera" ).AddComponent<CameraComponent>();
            camera.BackgroundColor = new Color( .025f, .03f, .035f );
            camera.FieldOfView = 34;
            var center = new Vector3( -4, 0, 2 );
            camera.WorldPosition = center + new Vector3( 5, -72, 13 );
            camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
            var light = new GameObject( true, "AUG QA light" ).AddComponent<DirectionalLight>();
            light.WorldRotation = Rotation.From( new Angles( 35, 35, 0 ) );
            light.LightColor = Color.White * 2;
            light.SkyColor = Color.White * .7f;
            scene.EditorTick( .01f, .01f );
            using var bitmap = new Bitmap( 1600, 900 );
            camera.RenderToBitmap( bitmap, false );
            File.WriteAllBytes( Path.Combine( Folder, $"{(world ? "world" : "view")}-{variant}.png" ), bitmap.ToPng() );
            File.WriteAllText( Path.Combine( Folder, $"parts-{(world ? "world" : "view")}.txt" ), "PASS: four parts equip/reset, factory prefab mask, suppressor/long-barrel flash hider and muzzle shift.\n" );
            Log.Info( $"AUG_QA PASS: four parts equip/reset, long barrel tip, models/materials; world={world}, variant={variant}" );
        }
        finally { scene.Destroy(); }
    }

    private static IEnumerable<Panel> Descendants( Panel panel )
    {
        yield return panel;
        foreach ( var child in panel.Children )
        foreach ( var descendant in Descendants( child ) ) yield return descendant;
    }

    [ConCmd( "hc1_aug_ui_check" )]
    public static async void UiCheck()
    {
        var panel = Game.ActiveScene.GetAllComponents<GunsmithPanel>().FirstOrDefault();
        Require( panel.IsValid() && panel.System.IsValid(), "Gunsmith must be open" );
        var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/aug/aug.equip" );
        var previous = panel.System.Equipment;
        var before = new Dictionary<string, string>();
        foreach ( var id in new[] { resource.ResourcePath, resource.ResourceName }.Distinct() )
        foreach ( var category in new[] { "Stock", "Barrel", "Magazine" } )
        {
            var key = $"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.{category}";
            before[key] = Game.Cookies.Get<string>( key, "" );
        }
        GunsmithAttachmentBrowser browser = null;
        try
        {
            using ( panel.Scene.Push() ) panel.System.SetEquipment( resource );
            await GameTask.DelaySeconds( .5f );
            browser = Descendants( panel.Panel ).OfType<GunsmithAttachmentBrowser>().First();
            browser.Close();
            await GameTask.DelaySeconds( .2f );
            Require( Descendants( browser ).Count( p => p.HasClass( "ab-slot" ) ) == 7, "seven attachment categories" );
            foreach ( var (category, names) in new[] {
                (GunsmithPartType.Stock, new[] { "Lightweight Stock", "Padded Tactical Stock", "Standard" }),
                (GunsmithPartType.Barrel, new[] { "Heavy Long Barrel", "Standard" }),
                (GunsmithPartType.Magazine, new[] { "60 Round Drum", "Standard" }) } )
            {
                var point = panel.System.Weapon.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( p => p.Category == category );
                using ( panel.Scene.Push() ) browser.SelectPoint( point );
                await GameTask.DelaySeconds( .2f );
                foreach ( var name in names )
                {
                    using ( panel.Scene.Push() )
                    {
                        var option = Descendants( browser ).Single( p => p.HasClass( "ab-option" ) && Descendants( p ).OfType<Label>().Any( l => l.Text == name ) );
                        Require( !option.HasClass( "locked" ), "available option " + name );
                        option.CreateEvent( "onclick" );
                    }
                    await GameTask.DelaySeconds( .3f );
                    GunsmithLoadoutManager.TryGetAttachment( resource, category, out var saved );
                    Require( (saved?.Name ?? "Standard") == name && saved == point.CurrentPart, "UI saves and previews " + category + ": " + name );
                }
            }
            browser.Close();
            await GameTask.DelaySeconds( .3f );
            Directory.CreateDirectory( Folder );
            using var bitmap = new Bitmap( 1920, 1080 );
            panel.Scene.Camera.RenderToBitmap( bitmap, true );
            File.WriteAllBytes( Path.Combine( Folder, "gunsmith.png" ), bitmap.ToPng() );
            File.WriteAllText( Path.Combine( Folder, "ui-validation.txt" ), "PASS: seven categories, clicked and saved all four options, Standard restores each category. Original selections restored after test.\n" );
            Log.Info( "AUG_QA UI PASS: seven categories, all four options selected and saved, Standard restores each category" );
        }
        finally
        {
            foreach ( var cookie in before ) Game.Cookies.Set( cookie.Key, cookie.Value );
            if ( panel.IsValid() )
            {
                using var scope = panel.Scene.Push();
                browser?.Close();
                panel.System.SetEquipment( previous );
            }
        }
    }

    [ConCmd( "hc1_aug_ammo_check" )]
    public static void AmmoCheck()
    {
        var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/aug/aug.equip" );
        var drum = ResourceLibrary.Get<GunsmithPart>( "gunsmith/aug/magazines/att_vm_p04_drum.gnsmth" );
        var before = new Dictionary<string, string>();
        foreach ( var id in new[] { resource.ResourcePath, resource.ResourceName }.Distinct() )
        {
            var key = $"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.Magazine";
            before[key] = Game.Cookies.Get<string>( key, "" );
        }
        var current = typeof( Pawn ).GetProperty( "Current", BindingFlags.Static | BindingFlags.NonPublic );
        var oldPawn = current.GetValue( null );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            var pawn = new GameObject( false, "AUG QA owner" ).AddComponent<PlayerPawn>();
            current.SetValue( null, pawn );
            var root = new GameObject( false, "AUG QA ammo" );
            var equipment = root.AddComponent<Equipment>();equipment.Owner = pawn;equipment.Resource = resource;
            var ammo = new GameObject( root, false, "Ammo" ).AddComponent<WeaponAmmo>();ammo.MaxAmmo = 30;ammo.Ammo = 12;
            var refresh = typeof( Equipment ).GetMethod( "RefreshAmmunitionLoadout", BindingFlags.NonPublic | BindingFlags.Instance );
            GunsmithLoadoutManager.SetAttachment( resource, GunsmithPartType.Magazine, drum );refresh.Invoke( equipment, null );
            var tune = WeaponTuningManager.GetTuning( resource.ResourceName );
            Require( ammo.GetEffectiveMaxAmmo() == (int)(60 * (1f + tune.MagSize * .04f)), "60-round drum respects tuning" );
            Require( equipment.ReloadMagazine == drum && drum.ReloadAnimation == 1 && drum.ReloadSounds.Count > 0 && drum.EmptyReloadSounds.Count > 0, "drum reload variant and sounds" );
            Require( ammo.Ammo == 12, "no free ammo from magazine change" );
            GunsmithLoadoutManager.SetAttachment( resource, GunsmithPartType.Magazine, null );refresh.Invoke( equipment, null );
            Require( ammo.GetEffectiveMaxAmmo() == (int)(30 * (1f + tune.MagSize * .04f)) && equipment.ReloadMagazine is null, "standard restores 30 rounds and reload" );
            Directory.CreateDirectory( Folder );
            File.WriteAllText( Path.Combine( Folder, "ammo-validation.txt" ), "PASS: 60/30-round capacity, matching drum reload animation and sound events, no free refill. Original selection restored after test.\n" );
            Log.Info( "AUG_QA AMMO PASS: 60/30-round capacity, drum reload and sounds, no free refill" );
        }
        finally
        {
            current.SetValue( null, oldPawn );
            foreach ( var cookie in before ) Game.Cookies.Set( cookie.Key, cookie.Value );
            scene.Destroy();
        }
    }

    private static void Require( bool condition, string message )
    {
        if ( !condition ) throw new Exception( "AUG_QA FAIL: " + message );
    }
}
