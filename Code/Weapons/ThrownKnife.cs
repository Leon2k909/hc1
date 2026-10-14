namespace Facepunch;

/// <summary>A host-simulated blade, swept through hitboxes before becoming an ordinary recoverable pickup.</summary>
public sealed class ThrownKnife : Component
{
	[Property] public Equipment Credit { get; set; }
	[Property] public float Damage { get; set; } = 100f;
	[Sync( SyncFlags.FromHost )] public Vector3 Velocity { get; private set; }

	private TimeSince _flightAge;
	private bool _finished;
	public const float FlightLifetime = 8f;
	public const float HitRadius = 2f;

	public static ThrownKnife Launch( Equipment heldKnife, Vector3 position, Vector3 velocity, float damage )
	{
		Sandbox.Diagnostics.Assert.True( Networking.IsHost );
		var resource = heldKnife.Resource;
		var go = new GameObject( heldKnife.Scene, false, $"Thrown {resource.Name}" );
		go.Flags |= GameObjectFlags.NotSaved;
		go.WorldPosition = position;
		go.WorldRotation = Rotation.LookAt( velocity.Normal, Vector3.Up );
		go.Tags.Add( "weapon" );

		// The held item is consumed on release. Keep independent weapon metadata for the kill feed,
		// knife rewards and Gun Game rather than a reference to that soon-destroyed item.
		var credit = go.Components.Create<Equipment>( false );
		credit.Resource = resource;
		credit.Owner = heldKnife.Owner;
		credit.ApplySavedAttachments = heldKnife.ApplySavedAttachments;

		var modelObject = new GameObject( go, true, "Blade" );
		modelObject.LocalPosition = -resource.WorldModel.Bounds.Center;
		var renderer = modelObject.Components.Create<SkinnedModelRenderer>();
		renderer.Model = resource.WorldModel;
		renderer.BodyGroups |= resource.WorldModelBodyGroups;

		var knife = go.Components.Create<ThrownKnife>();
		knife.Credit = credit;
		knife.Damage = damage;
		knife.Velocity = velocity;
		knife._flightAge = 0f;
		go.Components.Create<DestroyBetweenRounds>();
		go.Enabled = true;
		go.Network.SetOrphanedMode( NetworkOrphaned.ClearOwner );
		go.NetworkSpawn();
		return knife;
	}

	protected override void OnFixedUpdate()
	{
		if ( !Networking.IsHost || _finished ) return;
		if ( !Credit.IsValid() || Credit.Resource?.WorldModel is null )
		{
			GameObject.Destroy();
			return;
		}
		if ( _flightAge > FlightLifetime )
		{
			BecomePickup( WorldPosition, Vector3.Zero );
			return;
		}

		var delta = Time.Delta;
		var gravity = Scene.PhysicsWorld.Gravity;
		var end = WorldPosition + Velocity * delta + gravity * (0.5f * delta * delta);
		var trace = Scene.Trace.Ray( WorldPosition, end ).Radius( HitRadius ).UseHitboxes()
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "ragdoll", "movement", "playerclip", "pickup" );
		if ( Credit.Owner.IsValid() ) trace = trace.IgnoreGameObjectHierarchy( Credit.Owner.GameObject );
		var hit = trace.Run();
		Velocity += gravity * delta;
		WorldPosition = hit.Hit ? hit.EndPosition : end;
		WorldRotation = Rotation.LookAt( Velocity.Normal, Vector3.Up ) * Rotation.FromPitch( _flightAge * 900f );
		if ( hit.Hit ) Impact( hit );
	}

	private void Impact( in SceneTraceResult hit )
	{
		// Finish before dispatching damage: kills can change the round or inventory immediately.
		_finished = true;
		var surface = hit.GetImpactSurface();
		var sound = WorldSounds.KnifeImpact( hit, surface );
		var effect = surface?.GetBluntImpact();
		ImpactEffects( sound?.ResourcePath ?? "", effect?.Scene.Source?.ResourcePath ?? "",
			hit.HitPosition, hit.Normal );

		if ( hit.GameObject.IsValid() )
		{
			var hitbox = hit.GetHitboxTags();
			hit.GameObject.TakeDamage( new DamageInfo( Credit.Owner, Damage, Credit, hit.HitPosition,
				Velocity.Normal * 64f, hitbox == HitboxTags.None ? HitboxTags.UpperBody : hitbox, DamageFlags.Melee ) );
		}

		if ( !GameObject.IsValid() ) return;
		// Keep the complete model outside the wall when its physical pickup is created.
		var clearance = Credit.Resource.WorldModel.Bounds.Size.Length * 0.5f + 2f;
		BecomePickup( hit.EndPosition + hit.Normal * clearance, hit.Normal * 30f );
	}

	private void BecomePickup( Vector3 center, Vector3 velocity )
	{
		_finished = true;
		var origin = center - WorldRotation * Credit.Resource.WorldModel.Bounds.Center;
		var dropped = DroppedEquipment.Create( Credit.Resource, origin, WorldRotation, Credit, networkSpawn: false );
		dropped.Rigidbody.Velocity = velocity;
		dropped.GameObject.NetworkSpawn();
		GameObject.Destroy();
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void ImpactEffects( string sound, string prefab, Vector3 position, Vector3 normal )
	{
		if ( !string.IsNullOrEmpty( sound ) ) Sound.Play( sound, position );
		if ( string.IsNullOrEmpty( prefab ) ) return;
		GameObject.Clone( prefab, new Transform( position + normal, Rotation.LookAt( normal ) ) );
	}
}
