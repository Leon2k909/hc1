namespace Facepunch;

/// <summary>
/// Depot's original pickups have no gameplay implementation in HC1. Keep their inert models,
/// error placeholders and pickup colliders out of the scene without changing the compiled map.
/// </summary>
public sealed class DepotMapCleanup : Component, Component.ExecuteInEditor
{
	private MapInstance _map;
	private readonly List<GameObject> _suppressed = new();

	public int SuppressedCount => _suppressed.Count;

	protected override void OnEnabled() => Attach();
	protected override void OnStart() => Attach();

	private void Attach()
	{
		var map = GetComponent<MapInstance>();
		if ( !map.IsValid() || !string.Equals( map.MapName, "facepunch.depot", StringComparison.OrdinalIgnoreCase ) )
			return;

		if ( _map != map )
		{
			Detach();
			_map = map;
			_map.OnMapLoaded += SuppressLegacyObjects;
		}

		if ( _map.IsLoaded ) SuppressLegacyObjects();
	}

	private void SuppressLegacyObjects()
	{
		if ( !_map.IsValid() ) return;
		_suppressed.RemoveAll( obj => !obj.IsValid() );

		foreach ( var obj in _map.GameObject.Children.ToArray() )
		{
			if ( !obj.Enabled || !IsLegacyPickup( obj.Name ) || HasGameplayComponent( obj ) ) continue;
			obj.Enabled = false;
			_suppressed.Add( obj );
		}
	}

	private static bool IsLegacyPickup( string name ) =>
		name.StartsWith( "ammo_", StringComparison.Ordinal )
		|| name.StartsWith( "item_", StringComparison.Ordinal )
		|| name.StartsWith( "charger_", StringComparison.Ordinal );

	private static bool HasGameplayComponent( GameObject obj )
	{
		// Fail open if an updated Depot supplies working pickup logic. Never suppress HC1 equipment,
		// spawn points, map geometry, doors, lights or trigger volumes with gameplay components.
		foreach ( var component in obj.GetComponentsInChildren<Component>( true ) )
		{
			var type = component.GetType();
			if ( type == typeof( BoxCollider ) || type == typeof( ModelRenderer ) || type == typeof( SkinnedModelRenderer )
				|| type == typeof( MissingComponent ) || type == typeof( TextRenderer ) || type == typeof( WorldModel ) ) continue;
			return true;
		}

		return false;
	}

	protected override void OnDisabled() => Detach();

	private void Detach()
	{
		if ( _map.IsValid() ) _map.OnMapLoaded -= SuppressLegacyObjects;
		_map = null;

		foreach ( var obj in _suppressed )
		{
			if ( obj.IsValid() ) obj.Enabled = true;
		}
		_suppressed.Clear();
	}
}
