namespace Facepunch;

public sealed class CrosshairInputSystem : GameObjectSystem<CrosshairInputSystem>
{
	public CrosshairInputSystem( Scene scene ) : base( scene )
	{
		Listen( Stage.FinishUpdate, 0, Tick, "CrosshairInput" );
	}

	void Tick()
	{
		// The hitmarker is drawn with the frame's flash, then the flash runs down.
		HitmarkerPainter.Draw( Scene );
		CrosshairManager.Tick();
	}
}