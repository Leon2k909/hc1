namespace Facepunch;

public partial class Melee
{
	[Property, Category( "Throwing" )] public float ThrowSpeed { get; set; } = 1600f;
	[Property, Category( "Throwing" )] public float ThrowDamage { get; set; } = 100f;
	[Sync( SyncFlags.FromHost )] public bool IsThrowingKnife { get; private set; }

	public const float KnifeReleaseDelay = 0.18f;
	private TimeSince _sinceKnifeThrow;
	private bool _knifeReleased;

	/// <summary>Secondary attack throws the held blade; the ordinary primary attack still swings it.</summary>
	public bool TryThrowKnife()
	{
		if ( !CanSwing() || !CanKeepThrowingKnife() ) return false;

		// Throttle requests locally while the host starts the throw and replicates its state.
		TimeSinceSwing = 0f;
		BeginKnifeThrow();
		return true;
	}

	private bool CanKeepThrowingKnife()
	{
		return Equipment.IsValid() && Equipment.IsDeployed && Equipment.Resource?.Slot == EquipmentSlot.Melee
			&& Equipment.Resource.WorldModel is not null && Equipment.Owner.IsValid()
			&& Equipment.Owner.CurrentEquipment == Equipment && !Equipment.Owner.IsFrozen
			&& !Equipment.Owner.IsPipeClimbing && !Equipment.Owner.IsMantling
			&& Equipment.Owner.HealthComponent is { State: LifeState.Alive } && !_knifeReleased;
	}

	[Rpc.Host]
	private void BeginKnifeThrow()
	{
		if ( !Networking.IsHost || IsThrowingKnife || !CanKeepThrowingKnife() ) return;
		if ( Rpc.Caller is not null && Rpc.Caller != Connection.Host && Rpc.Caller != Equipment.Owner.Network.Owner ) return;

		IsThrowingKnife = true;
		_sinceKnifeThrow = 0f;
		DoEffects( null );
	}

	protected override void OnUpdate()
	{
		if ( !Networking.IsHost || !IsThrowingKnife ) return;

		// Switching weapons, dying or becoming frozen during the wind-up cancels the release.
		if ( !CanKeepThrowingKnife() )
		{
			IsThrowingKnife = false;
			return;
		}

		if ( _sinceKnifeThrow < KnifeReleaseDelay ) return;

		_knifeReleased = true;
		var player = Equipment.Owner;
		// A remote player's AimRay can use the host's viewer camera; use the replicated eyes instead.
		var forward = player.EyeAngles.ToRotation().Forward;
		var inheritedVelocity = player.IsLocallyControlled && player.CharacterController.IsValid()
			? player.CharacterController.Velocity : player.SyncedVelocity;
		ThrownKnife.Launch( Equipment, player.EyePosition,
			forward * ThrowSpeed + Vector3.Up * 80f + inheritedVelocity, ThrowDamage );

		if ( !player.Inventory.Equipment.Any( item => item != Equipment ) )
			player.Holster();
		player.Inventory.RemoveWeapon( Equipment );
	}
}
