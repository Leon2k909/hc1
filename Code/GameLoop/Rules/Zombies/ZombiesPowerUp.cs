using Sandbox;

namespace Facepunch;

public enum ZombiesPowerUpType
{
	MaxAmmo,
	InstaKill,
	DoublePoints,
	Nuke,
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
		ZombiesPowerUpType.MaxAmmo => "Max Ammo",
		ZombiesPowerUpType.InstaKill => "Insta-Kill",
		ZombiesPowerUpType.DoublePoints => "Double Points",
		ZombiesPowerUpType.Nuke => "Kaboom!",
		_ => t.ToString()
	};

	public static Color GetColor( ZombiesPowerUpType t ) => t switch
	{
		ZombiesPowerUpType.MaxAmmo => new Color( 0.3f, 1f, 0.35f ),
		ZombiesPowerUpType.InstaKill => new Color( 1f, 0.25f, 0.2f ),
		ZombiesPowerUpType.DoublePoints => new Color( 1f, 0.8f, 0.15f ),
		_ => new Color( 1f, 0.5f, 0.1f ),
	};

	public static void Spawn( Scene scene, Vector3 position, ZombiesPowerUpType type )
	{
		var go = new GameObject( true, $"PowerUp {type}" );
		go.WorldPosition = position + Vector3.Up * 36f;

		if ( type == ZombiesPowerUpType.MaxAmmo )
		{
			CreateAmmoCase( go );
		}
		else if ( type == ZombiesPowerUpType.DoublePoints )
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
		var olive = new Color( 0.24f, 0.3f, 0.12f );
		var metal = new Color( 0.12f, 0.14f, 0.11f );
		AddCasePart( parent, "Ammo case", new Vector3( 0, 0, -3 ), new Vector3( 14, 24, 14 ), olive );
		AddCasePart( parent, "Lid rim", new Vector3( 0, 0, 4 ), new Vector3( 15, 25, 2 ), metal );
		foreach ( var y in new[] { -8f, 8f } )
			AddCasePart( parent, "Latch", new Vector3( 7.5f, y, 1 ), new Vector3( 1, 3, 6 ), new Color( 0.55f, 0.5f, 0.3f ) );
		AddCasePart( parent, "Handle", new Vector3( -8, 0, 7 ), new Vector3( 2, 16, 2 ), metal );
		foreach ( var y in new[] { -7f, 7f } )
			AddCasePart( parent, "Handle support", new Vector3( -8, y, 4 ), new Vector3( 2, 2, 6 ), metal );

		// Local weapon asset: no cloud package that can disappear on restart.
		var magazine = Model.Load( "attachments/rear_mag/m4a1_short_mag/m4a1_short_mag.vmdl" );
		if ( magazine is null || magazine.IsError ) return;
		var bounds = magazine.Bounds;
		var scale = 18f / MathF.Max( bounds.Size.z, 1f );
		foreach ( var y in new[] { -7f, 0f, 7f } )
		{
			var mag = new GameObject( parent, true, "Rifle magazine" );
			mag.LocalScale = scale;
			mag.LocalPosition = new Vector3( 0, y, 2 ) - new Vector3( bounds.Center.x, bounds.Center.y, bounds.Mins.z ) * scale;
			mag.Components.Create<ModelRenderer>().Model = magazine;
		}
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
	string IMarkerObject.DisplayText => GetName( Type );
	float IMarkerObject.MarkerMaxDistance => 2000f;
	bool IMarkerObject.ShowChevron => false;
}
