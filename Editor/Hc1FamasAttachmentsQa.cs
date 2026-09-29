using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;

/// <summary>Isolated attachment renders and integration checks; never edits the player's saved build.</summary>
public static class Hc1FamasAttachmentsQa
{
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/famas/attachments" );
    private static void Require( bool ok, string message )
    {
        if ( !ok ) throw new Exception( "FAMAS_PARTS FAIL: " + message );
    }

    [ConCmd( "hc1_famas_parts_check" )]
    public static async void Run()
    {
        Directory.CreateDirectory( Folder );
        var weapon = await ResourceLibrary.LoadAsync<EquipmentResource>( "weapons/famas/famas.equip" );
        var parts = AttachmentUnlocks.GetWeaponParts( weapon ).Where( p => p.ResourcePath.StartsWith( "gunsmith/famas/" ) ).ToArray();
        Require( parts.Length == 8, $"eight new parts offered, found {parts.Length}" );
        Require( AttachmentUnlocks.GetSlots( weapon ).Count == 7, "seven build slots (no magazine: the F1 feeds only from its own 25-round magazine)" );
        foreach ( var part in parts ) Require( AttachmentUnlocks.GetRequiredLevel( weapon, part ) >= 2, "unlock ladder: " + part.Name );
        var optic = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/mw2022/att_vm_minireddot03_tall.gnsmth" );
        var muzzle = AttachmentUnlocks.GetWeaponParts( weapon ).First( p => p.Category == GunsmithPartType.Muzzle && p.IsSuppressor );
        var low = parts.Single( p => p.ResourceName.EndsWith( "_low" ) );
        var report = new List<string>();
        foreach ( var world in new[] { true, false } )
        {
            var scene = new Scene();
            try
            {
                using var scope = scene.Push();
                var root = (world ? weapon.WorldModelPrefab : weapon.ViewModelPrefab).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
                var marker = root.GetComponent<GunsmithWeapon>( true ) ?? root.AddComponent<GunsmithWeapon>();
                marker.Resource = weapon;
                foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
                    component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
                var renderer = root.GetComponent<SkinnedModelRenderer>( true );
                renderer.UseAnimGraph = false;
                renderer.PlayAnimationsInEditorScene = true;
                renderer.PlaybackRate = 0;
                renderer.Sequence.Blending = false;
                renderer.Sequence.Name = "idle";
                var baseline = renderer.BodyGroups;
                var points = root.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).ToDictionary( p => p.Category );
                var camera = new GameObject( true, "Attachment QA camera" ).AddComponent<CameraComponent>();
                camera.BackgroundColor = new Color( .07f, .08f, .09f ); camera.ZNear = .1f;
                camera.FieldOfView = world ? 34 : 80;
                if ( world )
                {
                    var center = new Vector3( -1, 0, 3 );
                    camera.WorldPosition = center + new Vector3( 4, -70, 10 );
                    camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
                }
                var light = new GameObject( true, "Attachment QA light" ).AddComponent<DirectionalLight>();
                light.WorldRotation = Rotation.From( new Angles( 40, 35, 0 ) );
                light.LightColor = Color.White * 2; light.SkyColor = Color.White * .7f;
                foreach ( var model in root.GetComponentsInChildren<ModelRenderer>( true ) )
                { model.RenderOptions.Game = true; model.RenderOptions.Overlay = false; }
                root.Enabled = true;
                void Tick()
                {
                    scene.ProcessDeletes();
                    scene.EditorTick( .01f, .01f ); renderer.SceneModel.Update( 0 );
                    renderer.SceneModel.Transform = renderer.WorldTransform;
                    renderer.PostAnimationUpdate();
                    foreach ( var arms in root.GetComponentsInChildren<SkinnedModelRenderer>( true ).Where( r => r != renderer ) )
                        arms.SceneModel.MergeBones( renderer.SceneModel );
                    foreach ( var mount in root.GetComponentsInChildren<GunsmithMw22Attachment>( true ) ) mount.RefreshMount();
                }
                void Render( string name, string sequence = "idle", float cycle = 0 )
                {
                    renderer.Sequence.Name = sequence; renderer.Sequence.TimeNormalized = cycle; Tick();
                    using var bitmap = new Bitmap( 1200, 675 ); camera.RenderToBitmap( bitmap, false );
                    File.WriteAllBytes( Path.Combine( Folder, name + ".png" ), bitmap.ToPng() );
                }
                foreach ( var part in parts )
                {
                    var point = points[part.Category]; point.SetPart( part );
                    foreach ( var group in part.GetBodygroups( renderer.Model ) )
                        Require( renderer.GetBodyGroup( group.Key ) == group.Value, part.Name + " mesh " + group.Key );
                    Require( renderer.BodyGroups != baseline, part.Name + " changes visible mesh" );
                    if ( world ) Render( part.ResourceName );
                    if ( !world && part.MagazineCapacity > 0 )
                    {
                        var variant = part.ReloadAnimation == 1 ? "_xmag" : "_xmag2";
                        Require( part.MagazineCapacity == (part.ReloadAnimation == 1 ? 50 : 60), "magazine capacity and reload selection" );
                        Require( part.EmptyReloadSounds.Count > 0 && part.ReloadSounds.Count > 0, "magazine reload sounds" );
                        Require( part.EmptyReloadSounds.Keys.Max() <= part.EmptyReloadTime, "empty reload foley completes" );
                        Render( part.ResourceName + "-reload", "reload_empty" + variant, .5f );
                        Render( part.ResourceName + "-reload-end", "reload_empty" + variant, .85f );
                    }
                    point.SetPart( null );
                    Require( renderer.BodyGroups == baseline, part.Name + " removal restores factory meshes" );
                    report.Add( $"{(world ? "world" : "view")}: {part.Name} PASS" );
                }
                foreach ( var barrel in parts.Where( p => p.Category == GunsmithPartType.Barrel ) )
                {
                    foreach ( var reverse in new[] { false, true } )
                    {
                        points[reverse ? GunsmithPartType.Muzzle : GunsmithPartType.Barrel].SetPart( reverse ? muzzle : barrel );
                        points[reverse ? GunsmithPartType.Barrel : GunsmithPartType.Muzzle].SetPart( reverse ? barrel : muzzle );
                        Require( renderer.GetBodyGroup( "muzzle_tip" ) == 4, "suppressor hides barrel tip in both equip orders" );
                        Tick();
                        points[GunsmithPartType.Muzzle].SetPart( null );
                        Require( renderer.GetBodyGroup( "muzzle_tip" ) == barrel.Bodygroups["muzzle_tip"], "restored barrel tip" );
                        points[GunsmithPartType.Barrel].SetPart( null );
                        Require( renderer.BodyGroups == baseline, "barrel/muzzle removal" );
                    }
                }
                points[GunsmithPartType.Rail].SetPart( low );
                foreach ( var reverse in new[] { false, true } )
                {
                    points[GunsmithPartType.Rail].SetPart( null );
                    points[reverse ? GunsmithPartType.Optic : GunsmithPartType.Rail].SetPart( reverse ? optic : low );
                    points[reverse ? GunsmithPartType.Rail : GunsmithPartType.Optic].SetPart( reverse ? low : optic );
                    Require( renderer.GetBodyGroup( "iron_sights" ) == 2 && renderer.GetBodyGroup( "sight_folded" ) == 2, "low rail optic folds matching sights in both orders" );
                    points[GunsmithPartType.Optic].SetPart( null );
                    Require( renderer.GetBodyGroup( "iron_sights" ) == 1 && renderer.GetBodyGroup( "sight_folded" ) == 0, "low rail irons restored" );
                    points[GunsmithPartType.Rail].SetPart( null );
                    Require( renderer.BodyGroups == baseline, "rail and optic removal restores factory" );
                }
            }
            finally { scene.Destroy(); }
        }
        File.WriteAllLines( Path.Combine( Folder, "report.txt" ), report );
        Log.Info( "FAMAS_PARTS PASS: eight parts, both models, unlock ladder, reload poses, muzzle/rail combinations" );
    }

    [ConCmd( "hc1_famas_loadout_check" )]
    public static void LoadoutCheck()
    {
        var weapon = ResourceLibrary.Get<EquipmentResource>( "weapons/famas/famas.equip" );
        var before = new Dictionary<string, string>();
        foreach ( var id in new[] { weapon.ResourcePath, weapon.ResourceName }.Distinct() )
        foreach ( var slot in new[] { "Magazine", "Rail", "Optic" } )
        {
            var key = $"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.{slot}";
            before[key] = Game.Cookies.Get<string>( key, "" );
        }
        var current = typeof( Pawn ).GetProperty( "Current", BindingFlags.Static | BindingFlags.NonPublic );
        var oldPawn = current.GetValue( null );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            var pawn = new GameObject( false, "FAMAS QA owner" ).AddComponent<PlayerPawn>();
            current.SetValue( null, pawn );
            var root = new GameObject( false, "FAMAS QA equipment" );
            var equipment = root.AddComponent<Equipment>(); equipment.Owner = pawn; equipment.Resource = weapon;
            var ammo = new GameObject( root, false, "Ammo" ).AddComponent<WeaponAmmo>(); ammo.MaxAmmo = 25; ammo.Ammo = 12;
            var refresh = typeof( Equipment ).GetMethod( "RefreshAmmunitionLoadout", BindingFlags.Instance | BindingFlags.NonPublic );
            Require( !AttachmentUnlocks.GetWeaponParts( weapon ).Any( p => p.Category == GunsmithPartType.Magazine ), "no magazine parts: the F1 feeds only from its own 25-round magazine" );
            foreach ( var part in AttachmentUnlocks.GetWeaponParts( weapon ).Where( p => p.Category == GunsmithPartType.Magazine ) )
            {
                GunsmithLoadoutManager.SetAttachment( weapon, GunsmithPartType.Magazine, part );
                refresh.Invoke( equipment, null );
                Require( ammo.GetEffectiveMaxAmmo() == part.MagazineCapacity, "physical capacity " + part.Name );
                Require( ammo.Ammo == 12, "changing magazine does not grant ammo" );
                Require( equipment.ReloadMagazine == part, "matching reload selected " + part.Name );
            }
            GunsmithLoadoutManager.SetAttachment( weapon, GunsmithPartType.Magazine, null );
            refresh.Invoke( equipment, null );
            Require( equipment.AttachmentMagazineCapacity == 0 && equipment.ReloadMagazine is null, "factory magazine restored" );
            var rail = ResourceLibrary.Get<GunsmithPart>( "gunsmith/famas/rails/att_vm_p04_low.gnsmth" );
            GunsmithLoadoutManager.SetAttachment( weapon, GunsmithPartType.Rail, rail );
            GunsmithLoadoutManager.SetAttachment( weapon, GunsmithPartType.Optic, null );
            var ads = new GameObject( root, false, "ADS" ).AddComponent<ManualOffset>();
            typeof( EquipmentComponent ).GetProperty( "Equipment", BindingFlags.Instance | BindingFlags.NonPublic ).SetValue( ads, equipment );
            ads.IsAiming = true;
            Require( ((IViewModelOffset)ads).PositionOffset.Distance( rail.RailIronAimCorrection ) < .001f, "saved rail changes iron ADS" );
            var optic = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/mw2022/att_vm_minireddot03_tall.gnsmth" );
            GunsmithLoadoutManager.SetAttachment( weapon, GunsmithPartType.Optic, optic );
            Require( ((IViewModelOffset)ads).PositionOffset.Distance( optic.OpticAimOffset + rail.RailOpticAimCorrection ) < .001f, "saved rail changes optical ADS" );
            Log.Info( "FAMAS_LOADOUT PASS: factory 25-round magazine only, factory restore, saved rail iron/optic ADS" );
        }
        finally
        {
            current.SetValue( null, oldPawn );
            foreach ( var cookie in before ) Game.Cookies.Set( cookie.Key, cookie.Value );
            scene.Destroy();
        }
    }

    [ConCmd( "hc1_famas_refresh" )]
    public static void Refresh()
    {
        var systems = Game.ActiveScene?.GetAllComponents<GunsmithSystem>().Where( s => s.Equipment?.ResourcePath == "weapons/famas/famas.equip" ).ToArray();
        foreach ( var system in systems ?? Array.Empty<GunsmithSystem>() ) system.SetEquipment( system.Equipment );
        Log.Info( $"FAMAS_PARTS refreshed {systems?.Length ?? 0} active FAMAS previews" );
    }
}
