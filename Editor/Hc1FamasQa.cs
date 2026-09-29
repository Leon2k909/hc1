using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

public static class Hc1FamasQa
{
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/famas" );

    [ConCmd( "hc1_famas_compile" )]
    public static async void Compile()
    {
        var files = Directory.GetFiles( Path.Combine( Project.Current.GetAssetsPath(), "Weapons/FAMAS" ), "*", SearchOption.AllDirectories )
            .Where( p => !p.EndsWith( "_c" ) && !p.EndsWith( ".meta" ) ).ToArray();
        foreach ( var file in files )
        {
            var asset = AssetSystem.FindByPath( file ) ?? AssetSystem.RegisterFile( file );
            if ( Path.GetExtension( file ) != ".json" ) Require( asset is not null, "registered " + Path.GetFileName( file ) );
        }
        foreach ( var extension in new[] { ".vmat", ".sound", ".vanmgrph", ".vmdl", ".prefab", ".equip" } )
        foreach ( var file in files.Where( p => Path.GetExtension( p ) == extension ) )
            Require( AssetSystem.FindByPath( file )?.Compile( true ) == true, "compiled " + Path.GetFileName( file ) );
        foreach ( var file in Directory.GetFiles( Path.Combine( Project.Current.GetAssetsPath(), "gunsmith" ), "*.gnsmth", SearchOption.AllDirectories ) )
            if ( File.ReadAllText( file ).Contains( "weapons/famas/famas.equip" ) )
                AssetSystem.FindByPath( file )?.Compile( true );
        var resource = await ResourceLibrary.LoadAsync<EquipmentResource>( "weapons/famas/famas.equip" );
        Require( resource.IsValid(), "FAMAS registered in equipment library" );
        Log.Info( "FAMAS_QA compile PASS" );
    }

    [ConCmd( "hc1_famas_check" )]
    public static async void Check( string pose = "world", float cycle = 0, string partPath = "", string railPath = "" )
    {
        Directory.CreateDirectory( Folder );
        var scene = new Scene();
        try
        {
            using var scope = scene.Push();
            var resource = await ResourceLibrary.LoadAsync<EquipmentResource>( "weapons/famas/famas.equip" );
            Require( resource.IsValid() && resource.Name == "FAMAS F1", "FAMAS equipment resource" );
            Require( GunsmithLoadoutManager.GetSlotChoices( EquipmentSlot.Primary ).Contains( resource ), "available in primary weapon picker" );
            var gameplay = resource.MainPrefab.Clone( new CloneConfig { StartEnabled = false } );
            var ammo = gameplay.GetComponentInChildren<WeaponAmmo>( true );
            var shooting = gameplay.GetComponentInChildren<Shootable>( true );
            Require( ammo.MaxAmmo == 25 && ammo.Ammo == 25, "25-round factory magazine" );
            Require( shooting.FireRate == 1000 && shooting.BurstAmount == 3 && shooting.SupportedFireModes.Count() == 3, "fire modes and cyclic rate" );
            var opticCorrection = gameplay.GetComponentInChildren<ManualOffset>( true ).OpticAimCorrection;
            gameplay.Destroy();
            var world = pose is "world" or "left";
            var root = (world ? resource.WorldModelPrefab : resource.ViewModelPrefab).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
            foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
                component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
            var renderer = root.GetComponent<SkinnedModelRenderer>( true );
            Require( renderer.Model is not null && !renderer.Model.IsError, "model compiled" );
            var prefabMask = renderer.BodyGroups;
            renderer.BodyGroups = 0;
            foreach ( var group in renderer.Model.Parts.All ) renderer.SetBodyGroup( group.Name, 0 );
            File.WriteAllText( Path.Combine( Folder, "default-mask.txt" ), renderer.BodyGroups.ToString() );
            Require( prefabMask == renderer.BodyGroups, "factory prefab bodygroups " + renderer.BodyGroups );
            renderer.UseAnimGraph = false;
            renderer.PlayAnimationsInEditorScene = true;
            renderer.Sequence.Name = world ? "idle" : pose == "hip" ? "idle" : pose;
            renderer.PlaybackRate = 0;
            foreach ( var model in root.GetComponentsInChildren<ModelRenderer>( true ) )
            {
                model.RenderOptions.Game = true;model.RenderOptions.Overlay = false;
                model.RenderType = ModelRenderer.ShadowRenderType.On;
            }
            GunsmithPart rail = null;
            if ( !string.IsNullOrEmpty( railPath ) )
            {
                rail = await ResourceLibrary.LoadAsync<GunsmithPart>( railPath );
                root.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( p => p.Category == GunsmithPartType.Rail ).SetPart( rail );
                if ( pose == "ads" ) root.WorldPosition = rail.RailIronAimCorrection;
            }
            if ( !string.IsNullOrEmpty( partPath ) )
            {
                var part = await ResourceLibrary.LoadAsync<GunsmithPart>( partPath );
                Require( part.IsValid() && part.Supports( resource ), "part fits FAMAS" );
                var point = root.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).Single( p => p.Category == part.Category );
                point.SetPart( part );
                foreach ( var group in point.FittedBodygroups )
                    Require( renderer.GetBodyGroup( group.Key ) == Math.Max( group.Value, rail?.OpticBodygroups.GetValueOrDefault( group.Key ) ?? 0 ), "fitted bodygroup " + group.Key );
                point.SetPart( null );
                foreach ( var group in point.FittedBodygroups )
                    Require( renderer.GetBodyGroup( group.Key ) == (rail?.Bodygroups.GetValueOrDefault( group.Key ) ?? 0), "restored bodygroup " + group.Key );
                point.SetPart( part );
                if ( pose == "ads" && part.Category == GunsmithPartType.Optic )
                {
                    root.WorldPosition = part.OpticAimOffset + opticCorrection + (rail?.RailOpticAimCorrection ?? Vector3.Zero);
                    root.WorldRotation = Rotation.From( part.OpticAimAngles );
                }
            }
            root.Enabled = true;
            renderer.Sequence.TimeNormalized = cycle;
            var camera = new GameObject( true, "FAMAS QA camera" ).AddComponent<CameraComponent>();
            camera.BackgroundColor = new Color( .07f, .08f, .09f );
            camera.FieldOfView = world ? 34 : 80;
            camera.ZNear = .1f;
            if ( world )
            {
                var center = new Vector3( -1, 0, 3 );
                camera.WorldPosition = center + new Vector3( 4, pose == "left" ? 70 : -70, 10 );
                camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
            }
            var light = new GameObject( true, "FAMAS QA key" ).AddComponent<DirectionalLight>();
            light.WorldRotation = Rotation.From( new Angles( 40, 35, 0 ) );
            light.LightColor = Color.White * 2;light.SkyColor = Color.White * .7f;
            scene.EditorTick( .01f, .01f );
            renderer.SceneModel.Update( 0 );
            foreach ( var arms in root.GetComponentsInChildren<SkinnedModelRenderer>( true ).Where( r => r != renderer ) )
                arms.SceneModel.MergeBones( renderer.SceneModel );
            foreach ( var mount in root.GetComponentsInChildren<GunsmithMw22Attachment>( true ) ) mount.RefreshMount();
            if ( pose == "ads" && !string.IsNullOrEmpty( partPath ) )
            {
                var point = root.GetComponentsInChildren<GunsmithAttachmentPoint>( true ).FirstOrDefault( p => p.Category == GunsmithPartType.Optic && p.CurrentPart.IsValid() );
                if ( point is not null )
                {
                    var mesh = point.CurrentGameObject.GetComponent<ModelRenderer>();
                    var name = Path.GetFileNameWithoutExtension( mesh.Model.Name );
                    using var doc = System.Text.Json.JsonDocument.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), $"Sources/MW2022/models/{name}.json" ) ) );
                    var head = doc.RootElement.GetProperty( "bones" ).EnumerateArray().First( b => b.GetProperty( "name" ).GetString() == "tag_reticle_attach" ).GetProperty( "head" );
                    var target = mesh.WorldTransform.PointToWorld( new Vector3( head[0].GetSingle(), head[1].GetSingle(), head[2].GetSingle() ) );
                    File.WriteAllText( Path.Combine( Folder, "optic-target.txt" ), target.ToString() );
                    Require( target.x > .5f && MathF.Abs( target.y ) < .04f && MathF.Abs( target.z ) < .04f, "optic target aligned " + target );
                }
            }
            using var bitmap = new Bitmap( 1600, 900 );
            camera.RenderToBitmap( bitmap, false );
            var suffix = (string.IsNullOrEmpty( partPath ) ? "" : "-" + Path.GetFileNameWithoutExtension( partPath )) + (rail is null ? "" : "-low");
            File.WriteAllBytes( Path.Combine( Folder, $"{pose}-{cycle:0.00}{suffix}.png" ), bitmap.ToPng() );
            Log.Info( $"FAMAS_QA PASS pose={pose}, cycle={cycle}, default mask={prefabMask}; resource available, 25 rounds, three fire modes" );
        }
        finally { scene.Destroy(); }
    }

    private static void Require( bool condition, string message )
    {
        if ( !condition ) throw new Exception( "FAMAS_QA FAIL: " + message );
    }
}
