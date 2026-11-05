using System.Threading.Tasks;

namespace Facepunch;

/// <summary>Automatically present in runtime scenes; no prefab or editor wiring is required.</summary>
public sealed class CosmeticSystem : GameObjectSystem<CosmeticSystem>, ISceneLoadingEvents
{
	public CosmeticSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.StartUpdate, 50, UpdateCosmetics, "Cosmetics" );
	}

	void ISceneLoadingEvents.BeforeLoad( Scene scene, SceneLoadOptions options )
	{
		if ( !scene.IsEditor ) CosmeticPreferences.ApplyLoadingScreen();
	}
	Task ISceneLoadingEvents.OnLoad( Scene scene, SceneLoadOptions options )
	{
		if ( !scene.IsEditor ) CosmeticPreferences.ApplyLoadingScreen();
		return Task.CompletedTask;
	}

	private void UpdateCosmetics()
	{
		if ( Scene.IsEditor || Scene != Game.ActiveScene || Application.IsDedicatedServer ) return;
		if ( LoadingScreen.IsVisible ) CosmeticPreferences.ApplyLoadingScreen();
		if ( !Input.Pressed( "Spray" ) || Input.Suppressed || Input.MouseCursorVisible
			|| GameUtils.IsGunsmithStudioOpen() || UI.ClassSelect.IsAnyOpen || UI.TacticalBuyMenu.IsAnyOpen
			|| UI.ZombiesWorkbenchPanel.IsAnyOpen ) return;
		var client = Client.Local;
		var pawn = client.IsValid() ? client.PlayerPawn : null;
		if ( !pawn.IsValid() || !pawn.IsLocallyControlled ) return;
		client.RequestSpray( CosmeticPreferences.SprayId, pawn.EyeAngles.Forward );
	}
}
