using System.Threading.Tasks;

namespace Facepunch.Gunsmith;

/// <summary>A private practice scene, carrying the weapon being edited across scene loads.</summary>
public static class GunsmithRangeSession
{
    public const string ScenePath = "scenes/gunsmith_range.scene";
    public static string WeaponPath { get; private set; }
    private static string returnWeaponPath;
    private static bool previousHardcore;
    private static bool entering;

    public static async Task<bool> Enter( EquipmentResource equipment )
    {
        if ( entering || !equipment.IsValid() || !Game.ActiveScene.IsValid() ) return false;
        var scene = ResourceLibrary.Get<SceneFile>( ScenePath );
        if ( !scene.IsValid() ) return false;

        entering = true;
        try
        {
            // Scene.Load is local. Leave the current lobby first so this private
            // scene never replaces a match for the other connected players.
            if ( Networking.IsActive )
            {
                Networking.Disconnect();
                for ( var attempt = 0; attempt < 100 && Networking.IsActive; attempt++ )
                    await GameTask.DelaySeconds( .05f );
                if ( Networking.IsActive ) return false;
            }

            WeaponPath = equipment.ResourcePath;
            previousHardcore = GameMode.ActiveHardcore;
            GameMode.SetCurrent( null );
            GameMode.SetHardcore( false );
            Game.ActiveScene.Load( scene );
            return true;
        }
        catch ( System.Exception e )
        {
            Log.Warning( $"Firing range could not load: {e.Message}" );
            return false;
        }
        finally { entering = false; }
    }

    public static void ReturnToGunsmith()
    {
        var scene = ResourceLibrary.Get<SceneFile>( "scenes/gunsmith.scene" );
        if ( !scene.IsValid() || !Game.ActiveScene.IsValid() ) return;
        returnWeaponPath = Client.Local?.PlayerPawn?.CurrentEquipment?.Resource?.ResourcePath ?? WeaponPath;
        GameMode.SetCurrent( null );
        GameMode.SetHardcore( previousHardcore );
        Game.ActiveScene.Load( scene );
    }

    public static EquipmentResource TakeReturnWeapon()
    {
        var path = returnWeaponPath;
        returnWeaponPath = null;
        return string.IsNullOrWhiteSpace( path ) ? null : ResourceLibrary.Get<EquipmentResource>( path );
    }
}
