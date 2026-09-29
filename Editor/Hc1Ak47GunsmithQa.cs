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

public static class Hc1Ak47GunsmithQa
{
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/ak47-gunsmith" );

    [ConCmd( "hc1_ak47_compile" )]
    public static void Compile()
    {
        var root = Project.Current.GetRootPath();
        foreach ( var folder in new[] { "Assets/Weapons/Kastov", "Assets/gunsmith/kastov762", "Assets/sounds/weapons/kastov" } )
        foreach ( var file in Directory.GetFiles( Path.Combine( root, folder ), "*", SearchOption.AllDirectories ) )
        {
            var ext = Path.GetExtension( file );
            if ( ext is ".meta" || file.EndsWith( "_c" ) ) continue;
            var asset = AssetSystem.FindByPath( file ) ?? AssetSystem.RegisterFile( file );
            if ( ext is ".vmdl" or ".vmat" or ".prefab" or ".gnsmth" or ".vanmgrph" or ".sound" ) asset?.Compile( true );
        }
        Log.Info( "AK47_QA: assets registered and compilation requested" );
    }

    [ConCmd( "hc1_ak47_parts_check" )]
    public static async void Check( bool world = true, int variant = 1, string pose = "idle", float cycle = 0 )
    {
        Directory.CreateDirectory( Folder );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/kastov/{(world ? "wm" : "vm")}_kastov762.prefab" );
            var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
            foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
                component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
            var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
            Require( renderer.Model is not null && !renderer.Model.IsError, "AK-47 model compiled" );
            Require( renderer.Model.Materials.All( m => !m.Name.Contains( "error" ) ), "materials resolved" );
            renderer.UseAnimGraph = false;
            var prefabMask = renderer.BodyGroups;
            renderer.BodyGroups = 0;
            foreach ( var group in renderer.Model.Parts.All ) renderer.SetBodyGroup( group.Name, 0 );

            File.WriteAllText( Path.Combine( Folder, $"default-{(world ? "world" : "view")}.txt" ), renderer.BodyGroups.ToString() );
            Log.Info( $"AK47_QA default {(world ? "world" : "view")} mask={renderer.BodyGroups}" );
            Require( prefabMask == renderer.BodyGroups, "prefab includes every factory part: " + renderer.BodyGroups );
            renderer.RenderOptions.Game = true;
            renderer.RenderOptions.Overlay = false;
            renderer.RenderType = ModelRenderer.ShadowRenderType.On;
            renderer.PlayAnimationsInEditorScene = true;
            renderer.Sequence.Name = world ? "idle" : pose;
            renderer.PlaybackRate = 0;
            foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
                if ( other != renderer ) { other.Enabled = !world; other.RenderOptions.Game = true; other.RenderOptions.Overlay = false; }
            var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/kastov/kastov762.equip" );
            var partPaths = Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/gunsmith/kastov762" ), "*.gnsmth", SearchOption.AllDirectories );
            var parts = new System.Collections.Generic.List<GunsmithPart>();
            foreach ( var file in partPaths )
            {
                var path = Path.GetRelativePath( Project.Current.GetAssetsPath(), file ).Replace( '\\', '/' );
                var part = await ResourceLibrary.LoadAsync<GunsmithPart>( path );
                Log.Info( $"AK47_QA loaded {path}: {part?.Name ?? "null"}" );
                parts.Add( part );
            }
            Require( parts.Count == 13 && parts.All( p => p.IsValid() ), "thirteen AK-47-specific parts registered" );
            foreach ( var part in parts )
            {
                Require( part.Supports( resource ), "AK-47 eligibility" );
                var point = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == part.Category );
                var original = renderer.BodyGroups;
                point.SetPart( part );
                foreach ( var group in part.Bodygroups )
                    Require( renderer.GetBodyGroup( group.Key ) == group.Value, $"selected {part.Name}: {group.Key}" );
                point.SetPart( null );
                Require( renderer.BodyGroups == original, $"factory restored after {part.Name}" );
            }
            if ( variant > 0 )
            {
                foreach ( var group in parts.GroupBy( p => p.Category ) )
                {
                    var choices = group.OrderBy( p => p.ResourcePath ).ToArray();
                    var part = choices[(variant - 1) % choices.Length];
                    root.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( p => p.Category == part.Category ).SetPart( part );
                }
                Require( renderer.GetBodyGroup( "muzzle_tip" ) == 1, "short barrel has matching muzzle tip" );
                var muzzle = root.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( p => p.Category == GunsmithPartType.Muzzle );
                var suppressor = ResourceLibrary.GetAll<GunsmithPart>().First( p => p.Category == GunsmithPartType.Muzzle && p.IsSuppressor && p.Supports( resource ) );
                muzzle.SetPart( suppressor );
                Require( renderer.GetBodyGroup( "muzzle_tip" ) == 2, "suppressor hides barrel muzzle tip" );
                Require( Math.Abs( GunsmithAttachmentPoint.MuzzleShift( root ).x + 4.976562f ) < .001f, "short barrel shifts muzzle mount" );
                muzzle.SetPart( null );
                Require( renderer.GetBodyGroup( "muzzle_tip" ) == 1, "removing suppressor restores short tip" );
            }
            root.Enabled = true;
            renderer.Sequence.TimeNormalized = cycle;
            var camera = new GameObject( true, "AK-47 QA camera" ).AddComponent<CameraComponent>();
            camera.BackgroundColor = new Color( .025f, .03f, .035f );
            camera.FieldOfView = world ? 34 : 80;
            camera.ZNear = .1f;
            var center = new Vector3( -4, 0, 2 );
            if ( world ) { camera.WorldPosition = center + new Vector3( 5, -82, 13 );
            camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition ); }
            var light = new GameObject( true, "AK-47 QA light" ).AddComponent<DirectionalLight>();
            light.WorldRotation = Rotation.From( new Angles( 35, 35, 0 ) );
            light.LightColor = Color.White * 2;
            light.SkyColor = Color.White * .7f;
            scene.EditorTick( .01f, .01f );
            renderer.SceneModel.Update( 0 );
            if ( !world ) foreach ( var arms in root.GetComponentsInChildren<SkinnedModelRenderer>( true ).Where( r => r != renderer ) ) arms.SceneModel.MergeBones( renderer.SceneModel );
            using var bitmap = new Bitmap( 1600, 900 );
            camera.RenderToBitmap( bitmap, false );
            File.WriteAllBytes( Path.Combine( Folder, $"{(world ? "world" : "view")}-{variant}-{pose}-{cycle:0.00}.png" ), bitmap.ToPng() );
            File.WriteAllText( Path.Combine( Folder, $"parts-{(world ? "world" : "view")}.txt" ), "PASS: thirteen parts equip/reset, factory prefab mask, suppressor/short-barrel flash hider and muzzle shift.\n" );
            Log.Info( $"AK47_QA PASS: thirteen parts equip/reset, short barrel tip, models/materials; world={world}, variant={variant}" );
        }
        finally { scene.Destroy(); }
    }

    private static IEnumerable<Panel> Descendants( Panel panel )
    {
        yield return panel;
        foreach ( var child in panel.Children )
        foreach ( var descendant in Descendants( child ) ) yield return descendant;
    }

    [ConCmd( "hc1_ak47_ui_check" )]
    public static async void UiCheck()
    {
        var panel = Game.ActiveScene.GetAllComponents<GunsmithPanel>().FirstOrDefault();
        Require( panel.IsValid() && panel.System.IsValid(), "Gunsmith must be open" );
        var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/kastov/kastov762.equip" );
        var previous = panel.System.Equipment;
        var before = new Dictionary<string, string>();
        foreach ( var id in new[] { resource.ResourcePath, resource.ResourceName }.Distinct() )
        foreach ( var category in new[] { "Stock", "RearGrip", "Barrel", "Magazine" } )
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
            Require( Descendants( browser ).Count( p => p.HasClass( "ab-slot" ) ) == 9, "nine attachment categories" );
            foreach ( var group in ResourceLibrary.GetAll<GunsmithPart>().Where( p => p.ResourcePath.StartsWith( "gunsmith/kastov762/" ) ).GroupBy( p => p.Category ) )
            {
                var category = group.Key;
                var names = group.Select( p => p.Name ).Append( "Standard" );
                var point = panel.System.Weapon.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( p => p.Category == category );
                using ( panel.Scene.Push() ) browser.SelectPoint( point );
                await GameTask.DelaySeconds( .2f );
                foreach ( var name in names )
                {
                    using ( panel.Scene.Push() )
                    {
                        var options = Descendants( browser ).Where( p => p.HasClass( "ab-option" ) ).ToArray();
                        var option = options.FirstOrDefault( p => Descendants( p ).OfType<Label>().Any( l => l.Text == name ) );
                        Require( option is not null, $"UI missing {category}: {name}; visible={string.Join( " / ", options.SelectMany( p => Descendants( p ).OfType<Label>() ).Select( l => l.Text ) )}; weapon={browser.Weapon?.Resource?.Name}" );
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
            File.WriteAllText( Path.Combine( Folder, "ui-validation.txt" ), "PASS: nine categories, clicked and saved all thirteen options, Standard restores each category. Original selections restored after test.\n" );
            Log.Info( "AK47_QA UI PASS: nine categories, all thirteen options selected and saved, Standard restores each category" );
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

    [ConCmd( "hc1_ak47_ammo_check" )]
    public static void AmmoCheck()
    {
        var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/kastov/kastov762.equip" );
        var magazines = ResourceLibrary.GetAll<GunsmithPart>().Where( p => p.ResourcePath.StartsWith( "gunsmith/kastov762/magazines/" ) ).ToArray();
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
            var pawn = new GameObject( false, "AK-47 QA owner" ).AddComponent<PlayerPawn>();
            current.SetValue( null, pawn );
            var root = new GameObject( false, "AK-47 QA ammo" );
            var equipment = root.AddComponent<Equipment>();equipment.Owner = pawn;equipment.Resource = resource;
            var ammo = new GameObject( root, false, "Ammo" ).AddComponent<WeaponAmmo>();ammo.MaxAmmo = 30;ammo.Ammo = 12;
            var refresh = typeof( Equipment ).GetMethod( "RefreshAmmunitionLoadout", BindingFlags.NonPublic | BindingFlags.Instance );
            var tune = WeaponTuningManager.GetTuning( resource.ResourceName );
            Require( magazines.Length == 3, "three magazines registered" );
            foreach ( var mag in magazines )
            {
                GunsmithLoadoutManager.SetAttachment( resource, GunsmithPartType.Magazine, mag );refresh.Invoke( equipment, null );
                Require( ammo.GetEffectiveMaxAmmo() == (int)(mag.MagazineCapacity * (1f + tune.MagSize * .04f)), "capacity respects tuning: " + mag.Name );
                Require( ammo.Ammo == 12, "no free ammo from magazine change" );
                if ( mag.ReloadAnimation > 0 ) Require( equipment.ReloadMagazine == mag && mag.ReloadSounds.Count > 0 && mag.EmptyReloadSounds.Count > 0, "matching reload and foley: " + mag.Name );
            }
            GunsmithLoadoutManager.SetAttachment( resource, GunsmithPartType.Magazine, null );refresh.Invoke( equipment, null );
            Require( ammo.GetEffectiveMaxAmmo() == (int)(30 * (1f + tune.MagSize * .04f)) && equipment.ReloadMagazine is null, "standard restores 30 rounds and reload" );
            Directory.CreateDirectory( Folder );
            File.WriteAllText( Path.Combine( Folder, "ammo-validation.txt" ), "PASS: 30/40/75-round capacity, matching magazine reload animations and sound events, no free refill. Original selection restored after test.\n" );
            Log.Info( "AK47_QA AMMO PASS: 30/40/75-round capacity, magazine reloads and sounds, no free refill" );
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
        if ( !condition ) throw new Exception( "AK47_QA FAIL: " + message );
    }
}
