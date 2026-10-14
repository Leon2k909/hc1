using Editor;
using Sandbox;
using Sandbox.Events;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Validate Museo's actual saved panes in an isolated scene, without changing the current match.</summary>
public static class Hc1MuseoGlassQa
{
    private static bool busy;
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/museo-glass" );

    [ConCmd( "hc1_museo_glass_qa" )]
    public static async void Run()
    {
        if ( busy ) return;
        busy = true;
        Directory.CreateDirectory( Folder );
        var scene = new Scene();
        var report = new StringBuilder();
        var failures = 0;
        void Check( string name, bool pass ) { report.AppendLine( $"{(pass ? "PASS" : "FAIL")} {name}" ); if ( !pass ) failures++; }
        void Restore( BreakableGlass glass ) => ((IGameEventHandler<BetweenRoundCleanupEvent>)glass).OnGameEvent( new BetweenRoundCleanupEvent() );
        try
        {
            var source = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(),
                "Assets/scenes/maps/CerroBlanco/cerroblanco.scene" ) ) ).AsObject();
            var objects = new JsonArray();
            foreach ( var item in source["GameObjects"].AsArray() )
                if ( item["Name"]?.GetValue<string>() is "Cerro Blanco" or "Sun" or "Sky" or "Fog" or "Lights" or "Reflection Probes" )
                    objects.Add( item.DeepClone() );
            source["GameObjects"] = objects;
            source["SceneProperties"]["WantsSystemScene"] = false;
            source["SceneProperties"]["NavMesh"]["Enabled"] = false;
            // Break's static RPC must never resolve a QA pane in the current playing scene.
            void RandomizeIds( JsonNode node )
            {
                if ( node is JsonObject obj )
                {
                    if ( obj.ContainsKey( "__guid" ) ) obj["__guid"] = JsonValue.Create( Guid.NewGuid() );
                    foreach ( var entry in obj.ToArray() ) if ( entry.Value is not null ) RandomizeIds( entry.Value );
                }
                else if ( node is JsonArray array ) foreach ( var child in array ) if ( child is not null ) RandomizeIds( child );
            }
            RandomizeIds( source );
            CameraComponent camera;
            using ( scene.Push() )
            {
                scene.Deserialize( source );
                var holder = scene.CreateObject( true );
                holder.Name = "Museo Glass QA Camera";
                camera = holder.Components.Create<CameraComponent>();
                camera.IsMainCamera = true;
                camera.WorldPosition = new Vector3( -790, 650, 90 );
                camera.WorldRotation = Rotation.LookAt( new Vector3( -1009, 650, 85 ) - camera.WorldPosition );
                camera.FieldOfView = 65;
                camera.ZFar = 60000;
                var tone = holder.Components.Create<Tonemapping>();
                tone.Mode = Tonemapping.TonemappingMode.ACES;
                tone.AutoExposureEnabled = false;
                tone.ExposureCompensation = 2;
                scene.EditorTick( .016f, .016f );
            }
            var panes = scene.GetAllComponents<BreakableGlass>().ToArray();
            var frames = scene.GetAllComponents<ModelRenderer>().Where( r => r.GetComponent<BreakableGlass>() is null ).ToArray();
            Check( "392 independently breakable panes loaded", panes.Length == 392 );
            Check( "all intact meshes load", panes.All( p => p.IntactModel is not null && !p.IntactModel.IsError ) );
            Check( "glass sound and shard prefabs load", panes.All( p => p.BreakSound is not null && p.ShardEffect.IsValid() ) );
            Check( "shard positions use unscaled pane objects", panes.All( p => p.WorldScale == Vector3.One ) );
            await Capture( scene, camera, "intact" );
            int HitCount( bool reverse )
            {
                using var scope = scene.Push();
                return panes.Count( p =>
                {
                    // Test the pane collider itself. A rail end sits inside an existing wall;
                    // the ordinary bullet trace below separately verifies collision priority.
                    var delta = p.WorldRotation.Forward * (reverse ? -2 : 2);
                    var hit = scene.Trace.Ray( p.WorldPosition - delta, p.WorldPosition + delta ).WithTag( BreakableGlass.Tag ).Run();
                    if ( hit.GameObject != p.GameObject )
                        File.AppendAllText( Path.Combine( Folder, "trace-misses.txt" ),
                            $"{p.GameObject.Name} at {p.WorldPosition}, normal {p.WorldRotation.Forward}, size {p.PaneSize}, reverse {reverse}: hit {hit.GameObject?.Name} at {hit.EndPosition}\n" );
                    return hit.GameObject == p.GameObject;
                } );
            }
            File.WriteAllText( Path.Combine( Folder, "trace-misses.txt" ), "" );
            var front = HitCount( false );
            var back = HitCount( true );
            Check( $"each pane is hittable from both sides ({front}/{back} of {panes.Length})", front == panes.Length && back == panes.Length );
            var sample = panes.OrderBy( p => p.WorldPosition.Distance( new Vector3( -1009, 650, 74.4f ) ) ).First();
            using ( scene.Push() )
            {
                var shot = scene.Trace.Ray( camera.WorldPosition, sample.WorldPosition - sample.WorldRotation.Forward * 8 )
                    .WithoutTags( "playerclip", "trigger" ).Run();
                var struck = shot.GameObject?.GetComponent<BreakableGlass>();
                Check( "bullet trace reaches the selected pane", struck == sample );
                struck?.Break( camera.WorldPosition );
            }
            Check( "a shot breaks only its pane", sample.IsBroken && panes.Count( p => p.IsBroken ) == 1 );
            Check( "broken pane disappears and stops colliding", !sample.GetComponent<ModelRenderer>( true ).Enabled &&
                sample.GetComponents<Collider>( true ).All( c => !c.Enabled ) );
            Check( "window frames and building colliders remain intact", frames.All( r => r.Enabled ) &&
                scene.GetAllComponents<ModelCollider>().Where( c => c.GetComponent<BreakableGlass>() is null ).All( c => c.Enabled ) );
            await Capture( scene, camera, "broken" );
            using ( scene.Push() )
            {
                Restore( sample );
                var normal = sample.WorldRotation.Forward;
                var thrown = scene.CreateObject( true );
                thrown.Name = "QA thrown object";
                BreakableGlass.BreakAhead( thrown, sample.WorldPosition - normal * 4, normal * 1000 );
                Check( "fast thrown object shatters glass", sample.IsBroken );
                thrown.Destroy();
                Restore( sample );
                BreakableGlass.BreakInBlast( new[] { sample.GameObject }, sample.WorldPosition - normal * 10,
                    scene.Trace.WithoutTags( BreakableGlass.Tag, "playerclip", "trigger" ) );
                Check( "blast shatters reachable glass", sample.IsBroken );
                foreach ( var pane in panes ) pane.Break( pane.WorldPosition - pane.WorldRotation.Forward * 8 );
                Check( "all pane shapes can shatter", panes.All( p => p.IsBroken && p.GetComponents<Collider>( true ).All( c => !c.Enabled ) ) );
                foreach ( var pane in panes ) Restore( pane );
                scene.EditorTick( 2, .016f );
            }
            Check( "round cleanup restores every pane and collider", panes.All( p => !p.IsBroken &&
                p.GetComponent<ModelRenderer>( true ).Enabled && p.GetComponents<Collider>( true ).All( c => c.Enabled ) ) &&
                HitCount( false ) == panes.Length );
            Check( "balustrade safety clips retained", scene.GetAllComponents<BoxCollider>().Count( c => c.GameObject.Tags.Has( "playerclip" ) ) == 12 );
        }
        catch ( Exception e ) { failures++; report.AppendLine( $"ERROR {e}" ); }
        finally
        {
            report.AppendLine( $"{failures} failure(s)" );
            File.WriteAllText( Path.Combine( Folder, "checks.txt" ), report.ToString() );
            scene.Destroy();
            busy = false;
        }
    }

    private static async Task Capture( Scene scene, CameraComponent camera, string name )
    {
        using var bitmap = new Bitmap( 1584, 900 );
        for ( var frame = 0; frame < 8; frame++ )
        {
            using ( scene.Push() )
            {
                scene.EditorTick( frame * .016f, .016f );
                camera.RenderToBitmap( bitmap );
            }
            await Task.Delay( frame == 0 ? 1800 : 32 );
        }
        File.WriteAllBytes( Path.Combine( Folder, $"{name}.png" ), bitmap.ToPng() );
    }
}
