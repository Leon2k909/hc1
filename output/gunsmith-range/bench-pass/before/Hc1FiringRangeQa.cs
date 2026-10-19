using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Practice-scene render and end-to-end checks, kept out of normal game UI.</summary>
public static class Hc1FiringRangeQa
{
    private static bool busy;
    private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/gunsmith-range" );

    [ConCmd( "hc1_firing_range_shot" )]
    public static async void Shot()
    {
        if ( busy ) return;
        busy = true;
        Directory.CreateDirectory( Folder );
        var scene = new Scene();
        try
        {
            var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/gunsmith_range.scene" ) ) ).AsObject();
            var objects = new JsonArray();
            foreach ( var item in root["GameObjects"].AsArray() )
                if ( item["Name"]?.GetValue<string>() is { } name && name != "Practice Session" && name != "Range HUD" )
                    objects.Add( item.DeepClone() );
            root["GameObjects"] = objects;
            root["SceneProperties"]["WantsSystemScene"] = false;
            CameraComponent camera;
            using ( scene.Push() )
            {
                scene.Deserialize( root );
                camera = scene.GetAllComponents<CameraComponent>().First();
                camera.WorldPosition = new Vector3( -190, -570, 85 );
                camera.WorldRotation = Rotation.LookAt( new Vector3( 900, -60, 55 ) - camera.WorldPosition );
                camera.FieldOfView = 80;
            }
            using var bitmap = new Bitmap( 1672, 941 );
            float elapsed = 0;
            for ( var frame = 0; frame < 12; frame++ )
            {
                using ( scene.Push() )
                {
                    scene.EditorTick( elapsed += .016f, .016f );
                    camera.RenderToBitmap( bitmap );
                }
                await Task.Delay( frame == 0 ? 2500 : 32 );
            }
            File.WriteAllBytes( Path.Combine( Folder, "range.png" ), bitmap.ToPng() );
        }
        catch ( Exception e ) { File.WriteAllText( Path.Combine( Folder, "render-error.txt" ), e.ToString() ); }
        finally { scene.Destroy(); busy = false; }
    }

    [ConCmd( "hc1_firing_range_test" )]
    public static async void Test()
    {
        if ( busy ) return;
        busy = true;
        Directory.CreateDirectory( Folder );
        var report = new StringBuilder();
        var failures = 0;
        var entered = false;
        void Check( string label, bool pass ) { report.AppendLine( $"{(pass ? "PASS" : "FAIL")} {label}" ); if ( !pass ) failures++; }
        try
        {
            var studio = Game.ActiveScene?.GetAllComponents<GunsmithSystem>().FirstOrDefault();
            if ( !Game.IsPlaying || !studio.IsValid() || Connection.All.Count() > 1 )
                throw new InvalidOperationException( "Run this while playing the standalone Gunsmith with no other players connected." );
            var equipment = studio.Equipment;
            var classIndex = GunsmithLoadoutManager.GetActiveClassIndex();
            var build = GunsmithLoadoutManager.ExportWeaponBuildCode( equipment );
            entered = await GunsmithRangeSession.Enter( equipment );
            Check( "range entry", entered );
            if ( !entered ) return;
            FiringRangeSystem range = null;
            for ( var attempt = 0; attempt < 150; attempt++ )
            {
                await GameTask.DelaySeconds( .1f );
                range = FiringRangeSystem.Current;
                if ( range?.Player?.CurrentEquipment.IsValid() == true ) break;
            }
            Check( "private offline session", !Networking.IsActive && Networking.IsHost );
            Check( "normal player spawned", range?.Player.IsValid() == true );
            if ( !range.IsValid() || !range.Player.IsValid() ) return;
            var pawn = range.Player;
            var held = pawn.CurrentEquipment;
            Check( "selected weapon deployed", held?.Resource == equipment );
            Check( "viewmodel created", held?.ViewModel.IsValid() == true );
            var targets = Game.ActiveScene.GetAllComponents<FiringRangeTarget>().OrderBy( t => t.DistanceMetres ).ToArray();
            Check( "four distance targets", targets.Select( t => t.DistanceMetres ).SequenceEqual( new[] { 10f,25f,50f,100f } ) );
            var target = targets.First();
            var aim = Rotation.LookAt( target.WorldPosition + Vector3.Up * 44 - pawn.EyePosition );
            pawn.Teleport( pawn.WorldPosition, aim );
            await GameTask.DelaySeconds( 1 );
            var shoot = held?.GetComponentInChildren<Shootable>();
            var ammo = held?.GetComponentInChildren<WeaponAmmo>();
            var magazine = ammo?.Ammo ?? 0;
            shoot?.Shoot();
            await GameTask.DelaySeconds( .3f );
            Check( "real firing consumes a magazine round", ammo is not null && ammo.Ammo < magazine );
            Check( "real projectile damages target", range.Hits > 0 && range.LastDamage > 0 );
            Check( "shots recorded", range.Shots > 0 );
            target.OnDamage( new Sandbox.DamageInfo( target.MaxHealth, pawn.GameObject, held.GameObject )
                { Position = target.WorldPosition + Vector3.Up * 66 } );
            Check( "knockdown and head impact recorded", target.IsDown && range.Knockdowns > 0 && range.LastHeadshot );
            await GameTask.DelaySeconds( 1.65f );
            Check( "knocked-down target automatically resets", !target.IsDown && target.Health == target.MaxHealth );
            if ( ammo is not null )
            {
                ammo.Ammo = 0;
                held.GetComponentInChildren<Reloadable>()?.StartReload();
                for ( var i = 0; i < 100 && ammo.Ammo == 0; i++ ) await GameTask.DelaySeconds( .1f );
                Check( "normal empty reload completes", ammo.Ammo == ammo.GetEffectiveMaxAmmo() );
                await GameTask.DelaySeconds( .35f );
                Check( "unlimited reserve replenished", ammo.ReserveAmmo == ammo.GetMaxReserve() );
            }
            var position = target.WorldPosition;
            range.ToggleMovingTargets();
            await GameTask.DelaySeconds( .5f );
            Check( "moving targets move", target.WorldPosition.Distance( position ) > 1 );
            range.ToggleMenu();
            Check( "range menu freezes input and releases cursor", pawn.IsFrozen && !GameUtils.ShouldHideCombatMouse( pawn ) );
            range.Resume();
            range.ResetTargets();
            Check( "target and statistics reset", targets.All( t => !t.IsDown && t.Health == t.MaxHealth ) && range.Shots == 0 && range.Hits == 0 );
            using ( var bitmap = new Bitmap( 1672,941 ) )
            {
                pawn.Camera.RenderToBitmap( bitmap, true );
                File.WriteAllBytes( Path.Combine( Folder,"in-game.png" ), bitmap.ToPng() );
            }
            GunsmithRangeSession.ReturnToGunsmith();
            entered = false;
            await GameTask.DelaySeconds( 1 );
            studio = Game.ActiveScene.GetAllComponents<GunsmithSystem>().FirstOrDefault();
            Check( "returns to the same weapon in Gunsmith", studio?.Equipment == equipment );
            Check( "saved class and attachments retained", GunsmithLoadoutManager.GetActiveClassIndex() == classIndex && GunsmithLoadoutManager.ExportWeaponBuildCode( equipment ) == build );
        }
        catch ( Exception e ) { failures++; report.AppendLine( $"ERROR {e}" ); }
        finally
        {
            if ( entered && FiringRangeSystem.IsActive ) GunsmithRangeSession.ReturnToGunsmith();
            report.AppendLine( $"failures={failures}" );
            File.WriteAllText( Path.Combine( Folder, "checks.txt" ), report.ToString() );
            busy = false;
        }
    }
}

