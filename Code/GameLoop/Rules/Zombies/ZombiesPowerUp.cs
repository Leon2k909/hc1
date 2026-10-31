using Sandbox;

namespace Facepunch;

public enum ZombiesPowerUpType
{
	Resupply,
	OneHitKills,
	PointBoost,
	CleanSweep,
}

/// <summary>
/// A floating drop left by a killed zombie. Walk into it to pick it up.
/// </summary>
public sealed class ZombiesPowerUp : Component, IMarkerObject
{
	public const float Lifetime = 26f;
	public const float PickupRadius = 56f;

	[Sync( SyncFlags.FromHost )] public ZombiesPowerUpType Type { get; set; }

	private TimeSince _spawned;
	private Vector3 _base;

	public static string GetName( ZombiesPowerUpType t ) => t switch
	{
		ZombiesPowerUpType.Resupply => "Resupply",
		ZombiesPowerUpType.OneHitKills => "One-Hit Kills",
		ZombiesPowerUpType.PointBoost => "Point Boost",
		ZombiesPowerUpType.CleanSweep => "Clean Sweep",
		_ => t.ToString()
	};

	public static Color GetColor( ZombiesPowerUpType t ) => t switch
	{
		ZombiesPowerUpType.Resupply => new Color( 0.3f, 1f, 0.35f ),
		ZombiesPowerUpType.OneHitKills => new Color( 1f, 0.25f, 0.2f ),
		ZombiesPowerUpType.PointBoost => new Color( 1f, 0.8f, 0.15f ),
		_ => new Color( 1f, 0.5f, 0.1f ),
	};

	public static void Spawn( Scene scene, Vector3 position, ZombiesPowerUpType type )
	{
		var go = new GameObject( true, $"PowerUp {type}" );
		go.WorldPosition = position + Vector3.Up * 36f;

		if ( type == ZombiesPowerUpType.Resupply )
		{
			CreateAmmoCase( go );
		}
		else if ( type == ZombiesPowerUpType.PointBoost )
		{
			var model = go.Components.Create<ModelRenderer>();
			model.Model = Model.Load( "models/dev/duffelbag/dufflebag_money.vmdl" );
			go.LocalScale = 0.3f;
		}
		else
		{
			var model = go.Components.Create<ModelRenderer>();
			model.Model = Model.Load( "models/dev/box.vmdl" );
			model.Tint = GetColor( type );
			go.LocalScale = 0.3f;
		}

		var light = go.Components.Create<PointLight>();
		light.LightColor = GetColor( type );
		light.Radius = 180f;

		var p = go.Components.Create<ZombiesPowerUp>();
		p.Type = type;

		go.NetworkSpawn( null );
	}

	protected override void OnStart()
	{
		_spawned = 0;
		_base = WorldPosition;
	}

	protected override void OnUpdate()
	{
		// Bob and spin, and blink in the last few seconds before it vanishes.
		WorldPosition = _base + Vector3.Up * MathF.Sin( _spawned * 3f ) * 6f;
		WorldRotation = Rotation.FromYaw( _spawned * 90f );

		foreach ( var r in GetComponentsInChildren<ModelRenderer>( true ) )
			r.Enabled = _spawned < Lifetime - 6f || (int)(_spawned * 6f) % 2 == 0;

		if ( !Networking.IsHost ) return;

		if ( _spawned > Lifetime )
		{
			GameObject.Destroy();
			return;
		}

		foreach ( var pawn in Scene.GetAllComponents<PlayerPawn>() )
		{
			if ( pawn.HealthComponent.State != LifeState.Alive ) continue;
			if ( ZombiesPlayerState.For( pawn )?.IsDowned == true ) continue;
			if ( pawn.WorldPosition.WithZ( 0 ).Distance( _base.WithZ( 0 ) ) > PickupRadius ) continue;
			if ( MathF.Abs( pawn.WorldPosition.z - _base.z ) > 120f ) continue;

			ZombiesRoundSystem.Current?.ActivatePowerUp( Type, pawn );
			GameObject.Destroy();
			return;
		}
	}

	internal static void CreateAmmoCase( GameObject parent )
	{
		var model = Model.Load( "models/zombies/ammo_case_v2/ammo_case.vmdl" );
		if ( model is null || model.IsError )
		{
			Log.Warning( "[Zombies] Missing model for the ammo case; using plain boxes." );
			AddCasePart( parent, "Ammo case", new Vector3( 0, 0, -3 ), new Vector3( 14, 24, 14 ), new Color( 0.24f, 0.3f, 0.12f ) );
			AddCasePart( parent, "Lid rim", new Vector3( 0, 0, 4 ), new Vector3( 15, 25, 2 ), new Color( 0.12f, 0.14f, 0.11f ) );
			return;
		}

		var chest = new GameObject( parent, true, "Ammo case" );
		chest.Components.Create<ModelRenderer>().Model = model;
	}

	private static void AddCasePart( GameObject parent, string name, Vector3 center, Vector3 size, Color tint )
	{
		var part = new GameObject( parent, true, name );
		var renderer = part.Components.Create<ModelRenderer>();
		renderer.Model = Model.Load( "models/dev/box.vmdl" );
		renderer.Tint = tint;
		var bounds = renderer.Model.Bounds;
		part.LocalScale = new Vector3( size.x / bounds.Size.x, size.y / bounds.Size.y, size.z / bounds.Size.z );
		part.LocalPosition = center - bounds.Center * part.LocalScale;
	}

	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * 20f;
	string IMarkerObject.DisplayText => Tr( GetName( Type ) );
	float IMarkerObject.MarkerMaxDistance => 2000f;
	bool IMarkerObject.ShowChevron => false;
}
