using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text;
using System.Reflection;
using System.Collections.Generic;
using Sandbox.UI;
using Label = Sandbox.UI.Label;

public static class Hc1RearMagazineQa
{
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "Sources/RearMagazine/qa" );
    private static bool uiRunning;

    [ConCmd( "hc1_rear_mag_refresh" )]
    public static void Refresh()
    {
        foreach ( var path in Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/attachments/rear_mag" ), "*.vmdl", SearchOption.AllDirectories ) )
            AssetSystem.FindByPath( path )?.Compile( true );
        foreach ( var weapon in new[] { "m4a1", "scarh" } )
        {
            foreach ( var key in new[] { "rubber_grip", "taped_grip", "short_mag", "extended_mag" } )
            {
                AssetSystem.FindByPath( $"gunsmith/{weapon}/rear_mag/{key}.prefab" )?.Compile( true );
                AssetSystem.FindByPath( $"gunsmith/{weapon}/rear_mag/{key}.gnsmth" )?.Compile( true );
            }
            foreach ( var prefix in new[] { "vm", "wm" } ) AssetSystem.FindByPath( $"weapons/{weapon}/{prefix}_{weapon}.prefab" )?.Compile( true );
        }
        foreach ( var variant in new[] { "v_scarh", "v_scarh_gunsmith", "w_scarh" } )
            AssetSystem.FindByPath( $"weapons/swb/scarh/{variant}.vmdl" )?.Compile( true );
        Log.Info( "HC1_REAR_MAG refresh complete" );
    }

    [ConCmd( "hc1_rear_mag_preview" )]
    public static void Preview( string weapon = "m4a1", bool world = false, bool extended = false, string suffix = "draft" )
    {
        Directory.CreateDirectory( Folder );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/{weapon}/{(world ? "wm" : "vm")}_{weapon}.prefab" );
            var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
            foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
                component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
            var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
            var path = weapon == "scarh" ? $"weapons/swb/scarh/{(world ? "w_scarh" : "v_scarh_gunsmith")}.vmdl" : $"models/weapons/sbox_assault_m4a1/{(world ? "w" : "v")}_m4a1.vmdl";
            renderer.Model = Model.Load( path );
            Require( !renderer.Model.IsError, path );
            renderer.UseAnimGraph = false;
            renderer.BodyGroups = weapon == "scarh" ? 81UL : world ? 395UL : 9251UL;
            renderer.SetBodyGroup( "foregrip", 0 );
            renderer.RenderOptions.Game = true; renderer.RenderOptions.Overlay = false; renderer.RenderType = ModelRenderer.ShadowRenderType.On;
            foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
                if ( other != renderer ) other.Enabled = false;
            renderer.Sequence.Name = weapon == "m4a1" ? "IdlePose" : "idle";
            renderer.PlaybackRate = 0;
            var originalMask = renderer.BodyGroups;
            foreach ( var (category, key) in new[] { (GunsmithPartType.RearGrip, extended ? "taped_grip" : "rubber_grip"), (GunsmithPartType.Magazine, extended ? "extended_mag" : "short_mag") } )
            {
                var point = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == category );
                var part = ResourceLibrary.Get<GunsmithPart>( $"gunsmith/{weapon}/rear_mag/{key}.gnsmth" );
                Require( part.IsValid() && part.Category == category, $"part {weapon}/{key}" );
                point.SetPart( part );
                var first = point.CurrentGameObject;
                Require( first.IsValid(), "prefab instance" );
                point.SetPart( null );
                first.DestroyImmediate();
                Require( (renderer.BodyGroups & renderer.Model.Parts.Get( "magazine" ).Mask) == (originalMask & renderer.Model.Parts.Get( "magazine" ).Mask), "original magazine restored" );
                point.SetPart( part );
                var mesh = point.CurrentGameObject.Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
                Require( mesh.IsValid() && !mesh.Model.IsError && mesh.Model.Materials.All( m => !m.Name.Contains( "error" ) ), $"valid authored model/material {key}: model={mesh?.Model?.Name} materials={string.Join( "|", mesh?.Model?.Materials.Select( m => m.Name ) ?? Array.Empty<string>() )}" );
            }
            root.Enabled = true;
            scene.EditorTick( .01f, .01f );
            foreach ( var mount in root.Components.GetAll<GunsmithBoneAttachment>( FindMode.EverythingInSelfAndDescendants ) ) mount.RefreshMount();
            Require( (renderer.BodyGroups & renderer.Model.Parts.Get( "magazine" ).Mask) == 0, "factory magazine hidden" );
            var magazineMount = root.Components.GetAll<GunsmithBoneAttachment>( FindMode.EverythingInSelfAndDescendants ).Single( m => m.HiddenBodygroup == "magazine" );
            if ( renderer.TryGetBoneTransform( magazineMount.BoneName, out var boneBefore ) )
            {
                var boneId = Enumerable.Range( 0, renderer.Model.BoneCount ).Single( i => renderer.Model.GetBoneName( i ) == magazineMount.BoneName );
                var beforePosition = magazineMount.WorldPosition;
                renderer.SceneModel.SetBoneWorldTransform( boneId, boneBefore.WithPosition( boneBefore.Position + Vector3.Down * 5 ) );
                magazineMount.RefreshMount();
                Require( magazineMount.WorldPosition.Distance( beforePosition + Vector3.Down * 5 ) < .05f, "magazine follows moving reload bone" );
                renderer.SceneModel.SetBoneWorldTransform( boneId, boneBefore );magazineMount.RefreshMount();
            }
            var camera = new GameObject( true, "Rear/magazine QA camera" ).Components.Create<CameraComponent>();
            camera.BackgroundColor = new Color( .055f, .065f, .075f ); camera.FieldOfView = 33;
            var center = renderer.Model.Bounds.Center + Vector3.Down * 1.5f;
            camera.WorldPosition = center + new Vector3( 7, -65, 13 ); camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
            var light = new GameObject( true, "QA key" ).Components.Create<DirectionalLight>();
            light.WorldRotation = Rotation.From( new Angles( 40, 35, 0 ) );light.LightColor = Color.White * 2.0f;light.SkyColor = Color.White * .6f;
            scene.EditorTick( .01f, .01f );
            using var bitmap = new Bitmap( 1600, 900 );camera.RenderToBitmap( bitmap );
            File.WriteAllBytes( Path.Combine( Folder, $"{weapon}-{(world ? "world" : "view")}-{(extended ? "extended" : "short")}-{suffix}.png" ), bitmap.ToPng() );
            foreach ( var mount in root.Components.GetAll<GunsmithBoneAttachment>( FindMode.EverythingInSelfAndDescendants ) )
                Log.Info( $"HC1_REAR_MAG mount {weapon} {world} {mount.BoneName}: {mount.WorldTransform}" );
        }
        finally { scene.Destroy(); }
        Log.Info( $"HC1_REAR_MAG preview PASS {weapon} world={world} extended={extended}" );
    }

    private static void Require( bool condition, string label ) { if ( !condition ) throw new Exception( "HC1_REAR_MAG FAIL: " + label ); }

    [ConCmd( "hc1_rear_mag_ui_test" )]
    public static async void UiTest( string suffix = "final" )
    {
        if ( uiRunning ) return;
        var panel = Game.ActiveScene.GetAllComponents<GunsmithPanel>().FirstOrDefault();
        Require( panel is not null && panel.IsValid() && panel.System.IsValid(), "Gunsmith must be open" );
        var weapon = panel.System.Weapon;
        var browser = Descendants( panel.Panel ).OfType<GunsmithAttachmentBrowser>().First();
        var before = new Dictionary<string, string>();
        foreach ( var id in new[] { weapon.Resource.ResourcePath, weapon.Resource.ResourceName }.Distinct() )
        foreach ( var category in new[] { "RearGrip", "Magazine" } )
        {
            var key = $"hc1.gunsmith.class{GunsmithLoadoutManager.GetActiveClassIndex()}.{id}.{category}";
            before[key] = Game.Cookies.Get<string>( key, "" );
        }
        var oldSelection = browser.SelectedPoint;
        uiRunning = true;
        try
        {
            foreach ( var (category, names) in new[] {
                (GunsmithPartType.RearGrip, new[] { "Rubberized Grip", "Taped Grip", "Standard" }),
                (GunsmithPartType.Magazine, new[] { "20 Round Compact", "40 Round Extended", "Standard" }) } )
            {
                GunsmithAttachmentPoint point;
                using ( panel.Scene.Push() )
                {
                    point = weapon.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( p => p.Category == category );
                    browser.SelectPoint( point );
                }
                await GameTask.DelaySeconds( .3f );
                foreach ( var name in names )
                {
                    using ( panel.Scene.Push() )
                    {
                        var option = Descendants( browser ).Single( p => p.HasClass( "attachment-option" ) && Descendants( p ).OfType<Label>().Any( l => l.Text == name ) );
                        Require( !option.HasClass( "locked" ), "unlocked option " + name );
                        option.CreateEvent( "onclick" );
                    }
                    await GameTask.DelaySeconds( .6f );
                    using ( panel.Scene.Push() )
                    {
                        Require( GunsmithLoadoutManager.TryGetAttachment( weapon.Resource, category, out var saved ) && (saved?.Name ?? "Standard") == name && saved == point.CurrentPart, "UI saves and previews " + name );
                        if ( name != "Standard" )
                        {
                            Directory.CreateDirectory( Folder );
                            using var bitmap = new Bitmap( 1920, 1080 );
                            panel.Scene.Camera.RenderToBitmap( bitmap, true );
                            File.WriteAllBytes( Path.Combine( Folder, "ui-" + name.Replace( ' ', '-' ).ToLowerInvariant() + "-" + suffix + ".png" ), bitmap.ToPng() );
                        }
                    }
                }
            }
            var slots = Descendants( browser ).Where( p => p.HasClass( "attachment-slot" ) ).ToArray();
            Require( slots.Length == 8, "eight visible attachment categories" );
            File.WriteAllLines( Path.Combine( Folder, "ui-layout.txt" ), slots.Select( p => $"{p.Box.Rect}: {string.Join( " / ", Descendants( p ).OfType<Label>().Select( l => l.Text ) )}" ) );
            File.WriteAllText( Path.Combine( Folder, "ui-validation.txt" ), "PASS: clicked both rear grips and both magazines, verified saved selection and preview, Standard restored both original parts; eight categories available. Original selections restored.\n" );
            Log.Info( "HC1_REAR_MAG UI PASS" );
        }
        finally
        {
            uiRunning = false;
            foreach ( var cookie in before ) Game.Cookies.Set( cookie.Key, cookie.Value );
            if ( weapon.IsValid() )
            {
                using var scope = panel.Scene.Push();
                GunsmithLoadoutManager.ApplyAttachments( weapon.Resource, weapon.GameObject );
                if ( oldSelection.IsValid() ) browser.SelectPoint( oldSelection );else browser.Close();
            }
        }
    }

    private static IEnumerable<Panel> Descendants( Panel panel )
    {
        yield return panel;
        foreach ( var child in panel.Children )
        foreach ( var descendant in Descendants( child ) ) yield return descendant;
    }

    [ConCmd( "hc1_rear_mag_test" )]
    public static void Test()
    {
        var rifle = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
        var scar = ResourceLibrary.Get<EquipmentResource>( "weapons/scarh/scarh.equip" );
        var active = GunsmithLoadoutManager.GetActiveClassIndex();
        var before = new Dictionary<string, string>();
        foreach ( var classId in new[] { active, 9875 } )
        foreach ( var weapon in new[] { rifle, scar } )
        foreach ( var id in new[] { weapon.ResourcePath, weapon.ResourceName } )
        foreach ( var category in new[] { "RearGrip", "Magazine", "Ammunition" } )
        {
            var key = $"hc1.gunsmith.class{classId}.{id}.{category}";
            before[key] = Game.Cookies.Get<string>( key, "" );
        }
        var current = typeof( Pawn ).GetProperty( "Current", BindingFlags.Static | BindingFlags.NonPublic );
        var oldPawn = current.GetValue( null );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            foreach ( var w in new[] { "m4a1", "scarh" } )
            foreach ( var partName in new[] { "rubber_grip", "taped_grip", "short_mag", "extended_mag" } )
            {
                var part = ResourceLibrary.Get<GunsmithPart>( $"gunsmith/{w}/rear_mag/{partName}.gnsmth" );
                Require( part.IsValid() && part.MainPrefab.IsValid(), "authored resource " + w + "/" + partName );
                Require( part.Supports( w == "m4a1" ? rifle : scar ) && !part.Supports( w == "m4a1" ? scar : rifle ), "weapon-specific eligibility" );
            }
            var longMag = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/rear_mag/extended_mag.gnsmth" );
            var shortMag = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/rear_mag/short_mag.gnsmth" );
            var grip = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/rear_mag/taped_grip.gnsmth" );
            var tracer = ResourceLibrary.Get<GunsmithPart>( "gunsmith/ammunition/tracer_rounds.gnsmth" );
            GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.RearGrip, grip );
            GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Magazine, longMag );
            GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Ammunition, tracer );
            GunsmithLoadoutManager.SetAttachment( scar, GunsmithPartType.Magazine, null );
            Require( GunsmithLoadoutManager.TryGetAttachment( scar, GunsmithPartType.Magazine, out var other ) && other is null, "weapon isolation" );
            GunsmithLoadoutManager.SetActiveClassIndex( 9875 );
            GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Magazine, shortMag );
            GunsmithLoadoutManager.SetActiveClassIndex( active );
            Require( GunsmithLoadoutManager.HasAttachment( rifle, longMag ), "class isolation" );
            var code = GunsmithLoadoutManager.ExportWeaponBuildCode( rifle ).Substring( "HC1W1-".Length ).Replace( '-', '+' ).Replace( '_', '/' );
            code = code.PadRight( (code.Length + 3) / 4 * 4, '=' );
            var decoded = Encoding.UTF8.GetString( Convert.FromBase64String( code ) );
            Require( decoded.Contains( "RearGrip" ) && decoded.Contains( "Magazine" ) && decoded.Contains( "Ammunition" ), "share code contains independent slots" );
            var pawn = new GameObject( false, "Magazine QA owner" ).Components.Create<PlayerPawn>();
            current.SetValue( null, pawn );
            var root = new GameObject( false, "Magazine QA weapon" );
            var equipment = root.Components.Create<Equipment>();equipment.Owner = pawn;equipment.Resource = rifle;
            var child = new GameObject( root, false, "Ammo" );
            var ammo = child.Components.Create<WeaponAmmo>();ammo.MaxAmmo = 30;ammo.Ammo = 12;
            var refresh = typeof( Equipment ).GetMethod( "RefreshAmmunitionLoadout", BindingFlags.NonPublic | BindingFlags.Instance );
            var tune = WeaponTuningManager.GetTuning( rifle.ResourceName );
            refresh.Invoke( equipment, null );
            Require( ammo.GetEffectiveMaxAmmo() == (int)(40 * (1f + tune.MagSize * .04f)), "extended capacity respects tuning" );
            Require( Math.Abs( equipment.AttachmentReloadMultiplier - 1.15f ) < .001f && equipment.UsesTracerRounds, "reload tradeoff and tracer independence" );
            Require( ammo.Ammo == 12, "equipping does not refill" );
            ammo.Ammo = 100;
            GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Magazine, shortMag );refresh.Invoke( equipment, null );
            Require( ammo.GetEffectiveMaxAmmo() == (int)(20 * (1f + tune.MagSize * .04f)) && ammo.Ammo == ammo.GetMaxAmmoWithChamber(), "smaller magazine clamps excess including chamber" );
            GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Magazine, null );refresh.Invoke( equipment, null );
            Require( equipment.AttachmentMagazineCapacity == 0 && equipment.AttachmentReloadMultiplier == 1, "standard restores defaults" );
            Require( ammo.GetEffectiveMaxAmmo() == (int)(30 * (1f + tune.MagSize * .04f)) && equipment.UsesTracerRounds, "standard magazine keeps tracer selection" );
            current.SetValue( null, null );
            GunsmithLoadoutManager.SetAttachment( rifle, GunsmithPartType.Magazine, longMag );refresh.Invoke( equipment, null );
            Require( equipment.AttachmentMagazineCapacity == 0, "remote weapon ignores local cookies" );
            Directory.CreateDirectory( Folder );
            File.WriteAllText( Path.Combine( Folder, "loadout-validation.txt" ), "PASS: eight resources, weapon/class isolation, independent grip/magazine/tracer selections, share-code contents, 20/40-round capacity with tuning, chamber clamp, no free ammo, reload modifiers, standard restoration, remote isolation.\n" );
        }
        finally
        {
            current.SetValue( null, oldPawn );GunsmithLoadoutManager.SetActiveClassIndex( active );
            foreach ( var item in before ) Game.Cookies.Set( item.Key, item.Value );
            scene.Destroy();
        }
        Log.Info( "HC1_REAR_MAG loadout PASS" );
    }

    [ConCmd( "hc1_rear_mag_inspect" )]
    public static void Inspect()
    {
        Directory.CreateDirectory( Folder );
        foreach ( var path in new[] { "models/weapons/sbox_assault_m4a1/v_m4a1.vmdl", "models/weapons/sbox_assault_m4a1/w_m4a1.vmdl", "weapons/swb/scarh/v_scarh_gunsmith.vmdl", "weapons/swb/scarh/w_scarh.vmdl" } )
        {
            var model = Model.Load( path );
            var name = Path.GetFileNameWithoutExtension( path );
            var report = new StringBuilder( $"MODEL {path}\nBOUNDS {model.Bounds}\nMATERIALS {string.Join( "|", model.Materials.Select( m => m.Name ) )}\n" );
            for ( int i = 0; i < model.BoneCount; i++ )
                report.AppendLine( $"BONE {model.GetBoneName( i )}: {model.GetBoneTransform( i )}" );
            foreach ( var part in model.Parts.All )
                report.AppendLine( $"PART {part.Name}: {part.Mask} choices={string.Join( "|", part.Choices.Select( c => c.Name + "=" + c.Mask ) )}" );
            foreach ( var mesh in model.MeshInfo.Meshes )
                report.AppendLine( $"MESH {mesh.Name}: {mesh.BoundsMin} / {mesh.BoundsMax}" );
            File.WriteAllText( Path.Combine( Folder, name + ".txt" ), report.ToString() );
            var vertices = model.GetVertices();
            var indices = model.GetIndices();
            File.WriteAllText( Path.Combine( Folder, name + ".json" ), JsonSerializer.Serialize( new {
                positions = vertices.Select( v => new[] { v.Position.x, v.Position.y, v.Position.z } ),
                normals = vertices.Select( v => new[] { v.Normal.x, v.Normal.y, v.Normal.z } ),
                indices = indices.Take( model.GetIndexCountForLod( 0 ) ),
            } ) );
        }
        Log.Info( "HC1_REAR_MAG inspect saved" );
    }
}
