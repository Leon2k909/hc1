using Sandbox.Events;

namespace Facepunch;

[Title( "Throw Weapon" ), Group( "Weapon Components" )]
public partial class Throwable : WeaponInputAction,
	IGameEventHandler<EquipmentHolsteredEvent>
{
	[Property, EquipmentResourceProperty] public float CookTime { get; set; } = 0.25f;
	[Property, EquipmentResourceProperty] public GameObject Prefab { get; set; }
	[Property] public float ThrowPower { get; set; } = 1200f;
	protected virtual bool SpawnOnHost => false;
	protected virtual bool PlayGrenadeRadio => true;

	public enum State
	{
		Idle,
		Cook,
		Throwing,
		Thrown
	}

	[Sync] public State ThrowState { get; private set; }

	private TimeSince TimeSinceAction { get; set; }
	private bool HasThrownOnHost { get; set; }

	void IGameEventHandler<EquipmentHolsteredEvent>.OnGameEvent( EquipmentHolsteredEvent eventArgs )
	{
		if ( IsProxy ) return;
		if ( ThrowState == State.Thrown ) return;
		ThrowState = State.Idle;
	}

	protected bool CanThrow()
	{
		if ( !Equipment.IsValid() || !Equipment.IsDeployed || !Equipment.Owner.IsValid() || ThrowState != State.Idle )
			return false;

		if ( Equipment.Owner.IsFrozen )
			return false;

		return true;
	}

	protected override void OnInputDown()
	{
		if ( !CanThrow() )
			return;

		ThrowState = State.Cook;
		TimeSinceAction = 0;
	}

	protected override void OnInputUp()
	{
		if ( TimeSinceAction > CookTime && ThrowState == State.Cook )
		{
			ThrowState = State.Throwing;
			TimeSinceAction = 0;
		}
	}

	protected override void OnUpdate()
	{
		if ( Networking.IsHost && HasThrownOnHost && TimeSinceAction > 0.25f )
		{
			// We want to remove the weapon on the host only.
			var player = Equipment.Owner;
			player.Inventory.RemoveWeapon( Equipment );
			return;
		}

		if ( IsProxy ) return;

		if ( Input.Pressed( "Attack2" ) && ThrowState == State.Cook )
		{
			ThrowState = State.Idle;
			TimeSinceAction = 0;
		}

		if ( !IsDown() && TimeSinceAction > CookTime && ThrowState == State.Cook )
		{
			ThrowState = State.Throwing;
			TimeSinceAction = 0;
			return;
		}

		if ( ThrowState == State.Throwing && TimeSinceAction > 0.15f )
		{
			Throw();
			ThrowState = State.Thrown;
			TimeSinceAction = 0f;
		}
	}

	[Rpc.Broadcast]
	protected void Throw()
	{
		var player = Equipment.Owner;
		if ( !player.IsValid() ) return;
		if ( Rpc.Caller is not null && Rpc.Caller != Connection.Host && Rpc.Caller != player.Network.Owner ) return;
		if ( Networking.IsHost && HasThrownOnHost ) return;

		if ( SpawnOnHost ? Networking.IsHost : !IsProxy )
			SpawnProjectile( player );

		if ( player.BodyRenderer.IsValid() )
			player.BodyRenderer.SetBool( "b_throw_grenade", true );

		if ( !Networking.IsHost ) return;
		if ( PlayGrenadeRadio ) RadioSounds.Play( player.GameObject.GetTeam(), RadioSound.ThrownGrenade );
		TimeSinceAction = 0f;
		HasThrownOnHost = true;
	}

	protected virtual void SpawnProjectile( PlayerPawn player )
	{
		var tr = Scene.Trace.Ray( new( player.AimRay.Position, player.AimRay.Forward ), 10f )
			.IgnoreGameObjectHierarchy( GameObject.Root )
			.WithoutTags( "trigger" )
			.Run();

		var position = tr.Hit ? tr.HitPosition + tr.Normal * Equipment.Resource.WorldModel.Bounds.Size.Length : player.AimRay.Position + player.AimRay.Forward * 32f;
		position += player.EyeAngles.ToRotation().Right * 10f;

		var rotation = Rotation.From( 0, player.EyeAngles.yaw + 180f, 90f );
		var baseVelocity = player.CharacterController.Velocity;
		var dropped = Prefab.Clone( position, rotation );
		dropped.Tags.Set( "no_player", true );

		var rb = dropped.GetComponentInChildren<Rigidbody>();
		rb.Velocity = baseVelocity + player.AimRay.Forward * ThrowPower + Vector3.Up * 100f;
		rb.AngularVelocity = Vector3.Random * 8.0f;

		var grenade = dropped.GetComponent<BaseGrenade>();
		if ( grenade.IsValid() )
			grenade.Player = player;

		dropped.Network.SetOrphanedMode( NetworkOrphaned.ClearOwner );
		dropped.NetworkSpawn();
	}
}
