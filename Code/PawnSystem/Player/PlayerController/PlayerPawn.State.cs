using Sandbox.Diagnostics;
using Sandbox.Events;

namespace Facepunch;

public record OnPlayerRagdolledEvent : IGameEvent
{
	public float DestroyTime { get; set; } = 0f;
}

public partial class PlayerPawn
{
	/// <summary>
	/// The player's health component
	/// </summary>
	[RequireComponent] public ArmorComponent ArmorComponent { get; private set; }

	/// <summary>
	/// The player's inventory, items, etc.
	/// </summary>
	[RequireComponent] public PlayerInventory Inventory { get; private set; }

	/// <summary>
	/// How long since the player last respawned?
	/// </summary>
	[Sync( SyncFlags.FromHost )] public TimeSince TimeSinceLastRespawn { get; private set; }

	public override void OnKill( DamageInfo damageInfo )
	{
		// How they go down depends on how they stood, so it's worked out before prone and the knockdown are cleared.
		var death = Networking.IsHost ? ChooseDeath( damageInfo ) : DeathPlan.Limp;

		IsFallKnockedDown = false;
		IsProne = false;
		var client = Client;

		if ( Networking.IsHost )
		{
			ArmorComponent.HasHelmet = false;
			ArmorComponent.Armor = 0f;

			if ( client.IsValid() )
			{
				var defaultRespawnState = Scene.GetAllComponents<DefaultRespawnState>().FirstOrDefault();
				client.RespawnState = defaultRespawnState.IsValid()
					? defaultRespawnState.RespawnState
					: RespawnState.Requested;
			}

			Inventory.Clear();
			CreateRagdoll( (int)death.Style, death.Duration, death.FallDirection, death.HitSide, death.Velocity,
				death.HitPosition, death.HitVelocity, death.Blast );
		}

		PlayerBoxCollider.Enabled = false;

		if ( IsProxy || !client.IsValid() )
			return;

		client.OnKill( damageInfo );

		Holster();

		_previousVelocity = Vector3.Zero;
		CameraController.Mode = CameraMode.ThirdPerson;
	}

	public void SetSpawnPoint( SpawnPointInfo spawnPoint )
	{
		SpawnPosition = spawnPoint.Position;
		SpawnRotation = spawnPoint.Rotation;

		SpawnPointTags.Clear();

		foreach ( var tag in spawnPoint.Tags )
		{
			SpawnPointTags.Add( tag );
		}
	}

	public override void OnRespawn()
	{
		Assert.True( Networking.IsHost );

		OnHostRespawn();

		if ( !Client.IsBot )
		{
			OnClientRespawn();
		}
	}

	private void OnHostRespawn()
	{
		Assert.True( Networking.IsHost );

		_previousVelocity = Vector3.Zero;

		Teleport( SpawnPosition, SpawnRotation );

		if ( Body is not null )
		{
			Body.DamageTakenForce = Vector3.Zero;
		}

		if ( HealthComponent.State != LifeState.Alive )
		{
			ArmorComponent.HasHelmet = false;
			ArmorComponent.Armor = 0f;
		}

		CustomGameSettings.ApplyMaxHealth( HealthComponent );
		HealthComponent.Health = HealthComponent.MaxHealth;
		HealthComponent.ClearWounds();

		TimeSinceLastRespawn = 0f;

		ResetBody();
		Scene.Dispatch( new PlayerSpawnedEvent( this ) );
	}

	[Rpc.Owner]
	private void OnClientRespawn()
	{
		if ( !Client.IsValid() )
			return;

		if ( Client.IsBot )
			return;

		Possess();
		UsageStats.CountLife();
	}

	public void Teleport( Transform transform )
	{
		Teleport( transform.Position, transform.Rotation );
	}

	[Rpc.Owner]
	public void Teleport( Vector3 position, Rotation rotation )
	{
		Transform.World = new( position, rotation );
		Transform.ClearInterpolation();
		EyeAngles = rotation.Angles();

		if ( CharacterController.IsValid() )
		{
			CharacterController.Velocity = Vector3.Zero;
			CharacterController.IsOnGround = true;
		}
	}

	/// <summary> The host's pick of how this player goes down (<see cref="DeathPlan"/>), sent to everyone with the ragdoll. </summary>
	private DeathPlan ChooseDeath( DamageInfo damageInfo )
	{
		var cc = CharacterController;
		var local = IsLocallyControlled && cc.IsValid();
		var velocity = local ? cc.Velocity : SyncedVelocity;
		var grounded = local ? IsGrounded : SyncedIsGrounded;
		var down = IsProne || IsFallKnockedDown || !grounded;

		return DeathPlan.Choose( damageInfo, GameObject.Id, WorldPosition, Rotation.FromYaw( EyeAngles.yaw ), velocity,
			IsCrouching, down );
	}

	[Rpc.Broadcast( NetFlags.HostOnly )]
	private void CreateRagdoll( int style, float duration, Vector3 fallDirection, Vector3 hitSide, Vector3 velocity,
		Vector3 hitPosition, Vector3 hitVelocity, bool blast )
	{
		if ( !Body.IsValid() )
			return;

		var death = new DeathPlan
		{
			Style = (DeathStyle)style, Duration = duration, FallDirection = fallDirection, HitSide = hitSide,
			Velocity = velocity, HitPosition = hitPosition, HitVelocity = hitVelocity, Blast = blast
		};

		// The death's own jolt replaces the old shove on every part (5-20 times the damage, at random).
		Body.DamageTakenForce = Vector3.Zero;

		// The body leaves the pawn before it goes limp. The engine builds no ragdoll on an object another machine owns
		// (ModelPhysics.CreatePhysics returns on a proxy), so everyone else saw a player's body stand in its bind pose,
		// a T-pose, when it left the pawn after. Out on its own it's a local object, and every machine plays out the
		// same DeathPlan.
		Body.GameObject.SetParent( null, true );

		if ( Client.IsValid() && Client.IsBot )
		{
			Body.SetRagdoll( true );
			DyingBody.Begin( Body.Physics, death );
			Body.GameObject.Name = $"Ragdoll (BOT {DisplayName})";

			var comp = Body.Components.Create<DestroyAfter>();
			comp.Time = 15f;

			Body = null;
			return;
		}

		Body.SetRagdoll( true );
		DyingBody.Begin( Body.Physics, death );
		Body.GameObject.Name = $"Ragdoll ({DisplayName})";

		var ev = new OnPlayerRagdolledEvent();
		Scene.Dispatch( ev );

		if ( ev.DestroyTime > 0f )
		{
			var comp = Body.Components.Create<DestroyAfter>();
			comp.Time = ev.DestroyTime;
		}
		else
		{
			Body.Components.Create<DestroyBetweenRounds>();
		}

		Body = null;
	}

	private void ResetBody()
	{
		if ( Body is not null )
		{
			Body.DamageTakenForce = Vector3.Zero;
		}

		PlayerBoxCollider.Enabled = true;

		foreach ( var outfitter in GetComponentsInChildren<HumanOutfitter>( true ) )
		{
			outfitter.UpdateFromTeam( Team );
		}
	}
}
