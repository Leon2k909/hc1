namespace Facepunch;

public sealed class CombatMouseVisibilitySystem : GameObjectSystem<CombatMouseVisibilitySystem>
{
	public CombatMouseVisibilitySystem( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, 1000, Tick, "CombatMouseVisibility" );
	}

	private void Tick()
	{
		GameUtils.UpdateCombatMouseVisibility();
	}
}
