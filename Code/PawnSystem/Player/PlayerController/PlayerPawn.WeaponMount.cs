namespace Facepunch;

/// <summary>Rest a firearm on a nearby solid ledge while aiming down sights.</summary>
public partial class PlayerPawn
{
	private const float MountReach = 43f;
	private const float MountYawArc = 37f;
	private const float MountPitchArc = 26f;
	private const float MountMoveTolerance = 10f;
	private const float MountSurfaceTolerance = 7f;
	private static readonly string[] MountIgnoreTags = { "trigger", "playerclip", "movement", "player", "enemy", "ragdoll", "corpse", "debris", "gib", "pickup", "weapon", "viewmodel", "glass" };
	private Vector3 _mountOrigin;
	private Vector3 _mountContact;
	private Vector3 _mountForward;
	private float _mountYaw;
	private float _mountPitch;
	private GameObject _mountObject;
	private Equipment _mountedEquipment;
	private float _mountProbeCooldown;
	private bool _mountAvailable;

	[Sync] public bool IsWeaponMounted { get; private set; }
	public bool CanMountWeapon => IsWeaponMounted || _mountAvailable;

	private bool CanUseWeaponMount()
	{
		return IsLocallyControlled && HealthComponent.State == LifeState.Alive && IsGrounded
			&& !IsSprinting && !IsSliding && !IsMantling && !IsPipeClimbing && !IsProne
			&& !IsFallKnockedDown && !IsNoclipping && !IsFrozen && !IsPilotingDrone
			&& !GameUtils.IsGunsmithStudioOpen() && !UI.ClassSelect.IsAnyOpen
			&& !UI.TacticalBuyMenu.IsAnyOpen && !UI.ZombiesWorkbenchPanel.IsAnyOpen
			&& CurrentEquipment.IsValid() && CurrentEquipment.IsDeployed
			&& CurrentEquipment.GetComponentInChildren<Shootable>().IsValid()
			&& CurrentEquipment.HasTag( "aiming" );
	}

	private bool TryFindMount( out Vector3 contact, out Vector3 forward, out GameObject support, bool keepMountDirection = false )
	{
		contact = default;
		forward = default;
		support = null;
		if ( !Camera.IsValid() ) return false;

		var eye = Camera.WorldPosition;
		forward = keepMountDirection ? _mountForward : EyeAngles.WithPitch( 0f ).ToRotation().Forward;
		// The support is below the sight and ahead of the body; never count the floor at our feet.
		var front = eye + forward * MountReach;
		var ground = WorldPosition.z;
		var maxTop = MathF.Min( eye.z + 1f, ground + 64f );
		var minTop = MathF.Max( ground + 23f, eye.z - 28f );
		var rayStart = front.WithZ( maxTop + 5f );
		var rayEnd = front.WithZ( minTop - 3f );
		var top = Scene.Trace.Ray( rayStart, rayEnd )
			.IgnoreGameObjectHierarchy( GameObject.Root ).WithoutTags( MountIgnoreTags ).Run();
		if ( !top.Hit || top.StartedSolid || top.Normal.z < 0.85f
			|| top.HitPosition.z < minTop || top.HitPosition.z > maxTop ) return false;

		// Confirm this is a ledge directly ahead rather than a floor spanning the player's position.
		var behind = eye + forward * 13f;
		var near = Scene.Trace.Ray( behind.WithZ( top.HitPosition.z + 4f ), behind.WithZ( top.HitPosition.z - 8f ) )
			.IgnoreGameObjectHierarchy( GameObject.Root ).WithoutTags( MountIgnoreTags ).Run();
		if ( near.Hit && MathF.Abs( near.HitPosition.z - top.HitPosition.z ) < 5f ) return false;

		// Keep the firing line clear of the supporting object's upper edge.
		var muzzleLine = eye + forward * 10f;
		var clear = Scene.Trace.Ray( muzzleLine, eye + forward * (MountReach + 12f) )
			.IgnoreGameObjectHierarchy( GameObject.Root ).WithoutTags( MountIgnoreTags ).Run();
		if ( clear.Hit ) return false;

		contact = top.HitPosition;
		support = top.GameObject;
		return true;
	}

	private void StopWeaponMount()
	{
		IsWeaponMounted = false;
		_mountedEquipment = null;
		_mountObject = null;
	}

	private void UpdateWeaponMount()
	{
		if ( !IsLocallyControlled ) return;
		if ( !CanUseWeaponMount() )
		{
			_mountAvailable = false;
			StopWeaponMount();
			return;
		}

		if ( IsWeaponMounted )
		{
			if ( CurrentEquipment != _mountedEquipment || Input.Pressed( "WeaponMount" )
				|| Input.Pressed( "Jump" ) || Input.Pressed( "Duck" ) || Input.Pressed( "Prone" )
				|| Input.Down( "Run" ) || WishMove.WithZ( 0f ).LengthSquared > 0.01f
				|| WorldPosition.Distance( _mountOrigin ) > MountMoveTolerance )
			{
				StopWeaponMount();
				return;
			}

			// The surface must still exist at the same position (including moving or destroyed cover).
			if ( !TryFindMount( out var point, out _, out var support, keepMountDirection: true )
				|| point.Distance( _mountContact ) > MountSurfaceTolerance || support != _mountObject )
			{
				StopWeaponMount();
				return;
			}

			var yaw = _mountYaw + Angles.NormalizeAngle( EyeAngles.yaw - _mountYaw ).Clamp( -MountYawArc, MountYawArc );
			var pitch = EyeAngles.pitch.Clamp( _mountPitch - MountPitchArc, _mountPitch + MountPitchArc );
			EyeAngles = new Angles( pitch, yaw, EyeAngles.roll );
			return;
		}

		_mountProbeCooldown -= Time.Delta;
		if ( _mountProbeCooldown <= 0f )
		{
			_mountProbeCooldown = 0.09f;
			_mountAvailable = TryFindMount( out _, out _, out _ );
		}
		if ( !Input.Pressed( "WeaponMount" ) || !_mountAvailable ) return;
		if ( !TryFindMount( out _mountContact, out _mountForward, out _mountObject ) ) return;
		_mountOrigin = WorldPosition;
		_mountYaw = EyeAngles.yaw;
		_mountPitch = EyeAngles.pitch;
		_mountedEquipment = CurrentEquipment;
		IsWeaponMounted = true;
	}
}
