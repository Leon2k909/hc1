namespace Facepunch;

public abstract class BaseGrenade : Component, Component.ICollisionListener
{
	[Property] public float Lifetime { get; set; }
	[Property] public GameObject PrefabOnExplode { get; set; }
	[Property] public bool CanDealDamage { get; set; }
	[Sync] public PlayerPawn Player { get; set; }

	/// <summary> The skin it was thrown in (<see cref="EquipmentSkins"/>), which each machine puts on its own copy. </summary>
	[Sync, Change( nameof( OnSkinChanged ) )] public string SkinId { get; set; }

	private void OnSkinChanged( string before, string after ) => EquipmentSkins.Apply( GameObject, EquipmentSkins.Find( after ) );

	/// <summary>
	/// Is this player an enemy of the viewer?
	/// </summary>
	public bool IsEnemy => Client.Viewer.Team != Player.Team;

	private TimeSince TimeSinceCreated { get; set; }

	/// <summary> What the grenade is, for the sound of its bounces: a sheet-steel can unless it says otherwise. </summary>
	protected virtual WorldSounds.GrenadeBody Body => WorldSounds.GrenadeBody.Can;

	private TimeSince _sinceBounce;

	protected override void OnStart()
	{
		TimeSinceCreated = 0f;
		EquipmentSkins.Apply( GameObject, EquipmentSkins.Find( SkinId ) );

		// Its bounces are ours (WorldSounds.GrenadeBounce), once they've compiled.
		if ( WorldSounds.HasGrenadeBounces && GetComponent<Rigidbody>() is { } rigidbody && rigidbody.PhysicsBody is { } physics )
			physics.EnableCollisionSounds = false;
	}

	/// <summary>
	/// A bounce: the grenade's body striking what it hit, as loud as the speed into the surface makes it. The thrower's
	/// machine simulates the grenade, so it hears the strike and sends it to everyone else.
	/// </summary>
	void ICollisionListener.OnCollisionStart( Collision collision ) => Bounce( collision );

	private void Bounce( Collision collision )
	{
		if ( IsProxy || _sinceBounce < 0.06f || !WorldSounds.HasGrenadeBounces )
			return;

		var volume = WorldSounds.BounceVolume( MathF.Abs( collision.Contact.NormalSpeed ) );
		if ( volume <= 0f )
			return;

		var surface = collision.Other.Surface;
		var sound = WorldSounds.GrenadeBounce( surface, Body ) ?? surface?.SoundCollection.ImpactHard;
		if ( sound is null || !sound.IsValid() )
			return;

		_sinceBounce = 0f;
		PlayBounce( sound.ResourcePath, collision.Contact.Point, volume );
	}

	[Rpc.Broadcast( NetFlags.Unreliable )]
	private void PlayBounce( string sound, Vector3 position, float volume )
	{
		if ( Sound.Play( sound, position ) is { } handle && handle.IsValid() )
			handle.Volume *= volume;
	}

	protected override void OnUpdate()
	{
		if ( IsProxy || !CanExplode() ) return;
		
		if ( TimeSinceCreated > Lifetime )
		{
			Explode();
		}
	}

	/// <summary>
	/// A grenade thrown at a window goes through it, breaking the glass, rather than bouncing off.
	/// </summary>
	protected override void OnFixedUpdate()
	{
		if ( IsProxy ) return;

		var body = GetComponentInChildren<Rigidbody>();
		if ( body.IsValid() )
			BreakableGlass.BreakAhead( GameObject, body.WorldPosition, body.Velocity );
	}

	protected virtual bool CanExplode()
	{
		return true;
	}

	[Rpc.Broadcast]
	protected virtual void Explode()
	{
		if ( PrefabOnExplode.IsValid() )
			PrefabOnExplode.Clone( WorldPosition );

		if ( IsProxy ) return;
		GameObject.Destroy();
	}
}
