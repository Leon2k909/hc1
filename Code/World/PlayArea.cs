namespace Facepunch;

public partial class PlayAreaSystem : GameObjectSystem
{
	public PlayAreaSystem( Scene scene ) : base( scene )
	{
		//
	}

	public List<PlayArea> All { get; set; } = new();

	/// <summary>
	/// The play areas in the scene now. A scene's systems outlive <c>Scene.Load</c>, so a map's play area stayed listed
	/// after the next map loaded, and everyone there was outside it and killed ("Return to the AO"): those are dropped.
	/// </summary>
	public int Count
	{
		get
		{
			for ( var i = All.Count - 1; i >= 0; i-- )
			{
				if ( !All[i].IsValid() || !All[i].Active )
					All.RemoveAt( i );
			}

			return All.Count;
		}
	}
}

public partial class PlayArea : Component
{
	[Property] public Zone Zone { get; set; }


	protected override void OnEnabled()
	{
		var system = Scene.GetSystem<PlayAreaSystem>();
		if ( !system.All.Contains( this ) )
			system.All.Add( this );
	}

	protected override void OnDisabled()
	{
		Scene?.GetSystem<PlayAreaSystem>()?.All.Remove( this );
	}
}
