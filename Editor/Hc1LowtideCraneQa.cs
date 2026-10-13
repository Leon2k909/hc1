using Editor;
using Sandbox;
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Check the compiled crane assets without changing the active scene.</summary>
public static class Hc1LowtideCraneQa
{
    private static bool rendering;

    [ConCmd( "hc1_lowtide_crane_shot" )]
    public static async void Shot( string name = "detail", float ee = -910, float en = -1110, float ez = 205,
        float te = -620, float tn = -1475, float tz = 300, float fov = 56, float exposure = 2 )
    {
        if ( rendering ) return;
        rendering = true;
        var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/crane-realism" );
        Directory.CreateDirectory( folder );
        File.WriteAllText( Path.Combine( folder, "capture-status.txt" ), $"Rendering {name}" );
        var scene = new Scene();
        try
        {
            var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Lowtide/lowtide.scene" ) ) ).AsObject();
            var visual = new HashSet<string>( StringComparer.OrdinalIgnoreCase )
            { "Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes" };
            var objects = new JsonArray();
            foreach ( var item in root["GameObjects"].AsArray() )
                if ( item["Name"] is { } label && visual.Contains( label.GetValue<string>() ) ) objects.Add( item.DeepClone() );
            root["GameObjects"] = objects;
            root["SceneProperties"]["NavMesh"]["Enabled"] = false;
            root["SceneProperties"]["WantsSystemScene"] = false;
            CameraComponent camera;
            Vector3 World( Vector3 p ) => new( p.y, -p.x, p.z );
            using ( scene.Push() )
            {
                scene.Deserialize( root );
                var holder = new GameObject( false, "Crane QA camera" );
                camera = holder.Components.Create<CameraComponent>();
                camera.WorldPosition = World( new( ee, en, ez ) );
                camera.WorldRotation = Rotation.LookAt( World( new( te, tn, tz ) ) - camera.WorldPosition );
                camera.FieldOfView = fov;
                camera.ZNear = 1;
                camera.ZFar = 100000;
                camera.EnablePostProcessing = true;
                var tone = holder.Components.Create<Tonemapping>();
                tone.Mode = Tonemapping.TonemappingMode.ACES;
                tone.AutoExposureEnabled = false;
                tone.ExposureCompensation = exposure;
                holder.Enabled = true;
            }
            using var bitmap = new Bitmap( 1672, 941 );
            float elapsed = 0;
            using ( scene.Push() )
            {
                scene.EditorTick( elapsed += .016f, .016f );
                camera.RenderToBitmap( bitmap );
            }
            await Task.Delay( 3500 );
            for ( var frame = 0; frame < 12; frame++ )
            {
                using ( scene.Push() )
                {
                    scene.EditorTick( elapsed += .016f, .016f );
                    camera.RenderToBitmap( bitmap );
                }
                await Task.Delay( 32 );
            }
            File.WriteAllBytes( Path.Combine( folder, name + ".png" ), bitmap.ToPng() );
            File.WriteAllText( Path.Combine( folder, "capture-status.txt" ), $"Finished {name}" );
        }
        catch ( Exception e ) { File.WriteAllText( Path.Combine( folder, name + "-error.txt" ), e.ToString() ); }
        finally { scene.Destroy(); rendering = false; }
    }

    [ConCmd( "hc1_lowtide_crane_report" )]
    public static void Report()
    {
        var folder = Path.Combine( Project.Current.GetRootPath(), "output/lowtide/crane-realism" );
        Directory.CreateDirectory( folder );
        var report = new StringBuilder();
        var failures = 0;
        foreach ( var paint in new[] { "lt_crane_red", "lt_crane_machined", "lt_crane_oily", "lt_crane_glass", "lt_crane_trim", "lt_crane_grate" } )
        {
            var material = Material.Load( $"materials/lowtide/{paint}.vmat" );
            if ( material.IsError ) failures++;
            var colour = material.GetTexture( "g_tColor" );
            var normal = material.GetTexture( "g_tNormal" );
            report.AppendLine( $"{paint}: error={material.IsError}, shader={material.ShaderName}, colour={colour?.Width}x{colour?.Height}, normal={normal?.Width}x{normal?.Height}, metalTexture={material.GetFeature( "F_METALNESS_TEXTURE" )}" );
        }
        foreach ( var side in new[] { "east", "west" } )
        {
            var model = Model.Load( $"models/maps/lowtide/lowtide_dress_{side}.vmdl" );
            if ( model.IsError ) failures++;
            report.AppendLine( $"Dressing {side}: error={model.IsError}, bounds={model.Bounds}" );
        }
        report.AppendLine( $"asset failures={failures}" );
        File.WriteAllText( Path.Combine( folder, "compiled-assets.txt" ), report.ToString() );
        Log.Info( $"Lowtide crane compiled asset check: {failures} failures" );
    }
}
