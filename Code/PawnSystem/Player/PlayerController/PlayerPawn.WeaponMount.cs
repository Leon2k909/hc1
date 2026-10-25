namespace Facepunch;

/// <summary>Rest a firearm on a nearby solid ledge while aiming down sights.</summary>
public partial class PlayerPawn
{
	/// <summary>
	/// Where along the view a support can be, ahead of the eye: from just in front of the body to about where the
	/// handguard ends. It used to look at one point 43 ahead, past the top of most walls, sills and crates a player stands
	/// against (their tops run from about 16 to 38 ahead), so the prompt hardly ever showed (the user's report, 2026-10-19).
	/// </summary>
	private const float MountNearest = 12f;
	private const float MountReach = 40f;
	private const float MountStep = 3f;
	/// <summary> How far a support's top has to rise from the floor in front of it: a stair tread or a ramp isn't one. </summary>
	private const float MountMinRise = 14f;
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

		forward = keepMountDirection ? _mountForward : EyeAngles.WithPitch( 0f ).ToRotation().Forward;
		return FindMountTop( Scene, GameObject.Root, Camera.WorldPosition, forward, WorldPosition.z, out contact, out support );
	}

	/// <summary>
	/// The top a gun aimed from <paramref name="eye"/> along <paramref name="forward"/> (level) can rest on, for someone
	/// standing on a floor at <paramref name="ground"/>. Static so it can be checked in a scene of its own.
	/// </summary>
	internal static bool FindMountTop( Scene scene, GameObject ignore, Vector3 eye, Vector3 forward, float ground,
		out Vector3 contact, out GameObject support )
	{
		contact = default;
		support = null;
		var maxTop = MathF.Min( eye.z + 1f, ground + 64f );
		var minTop = MathF.Max( ground + 23f, eye.z - 28f );
		// The nearest top in reach that the gun can rest on. Surfaces lower than that (the floor, steps) are what it
		// has to rise from: a top only a step above the last one is a stair or a slope going up.
		var floor = ground;
		for ( var distance = MountNearest; distance <= MountReach; distance += MountStep )
		{
			var at = eye + forward * distance;
			var down = scene.Trace.Ray( at.WithZ( maxTop + 5f ), at.WithZ( ground - 4f ) )
				.IgnoreGameObjectHierarchy( ignore ).WithoutTags( MountIgnoreTags ).Run();
			// Something taller than the gun (a wall above a sill's height): nothing further on can be reached.
			if ( down.StartedSolid ) return false;
			if ( !down.Hit ) continue;
			var height = down.HitPosition.z;
			if ( height < minTop )
			{
				floor = MathF.Max( floor, height );
				continue;
			}
			if ( height > maxTop ) return false;
			// A bevelled or rounded front edge: carry on to the flat of the top.
			if ( down.Normal.z < 0.85f ) continue;
			if ( height - floor < MountMinRise ) return false;

			// Keep the firing line clear of the supporting object's upper edge.
			var clear = scene.Trace.Ray( eye + forward * 10f, eye + forward * (distance + 16f) )
				.IgnoreGameObjectHierarchy( ignore ).WithoutTags( MountIgnoreTags ).Run();
			if ( clear.Hit ) return false;

			contact = down.HitPosition;
			support = down.GameObject;
			return true;
		}

		return false;
	}

	private void StopWeaponMount()
	{
		IsWeaponMounted = false;
		_mountedEquipment = null;
		_mountObject = null;
	}

	/// <summary>
	/// For the ticks that skip <see cref="UpdateWeaponMount"/> (dead, mantling, climbing a pipe): without it the last
	/// probe's answer stood, and the HUD kept offering a mount that wasn't there.
	/// </summary>
	private void ClearWeaponMount()
	{
		_mountAvailable = false;
		if ( IsWeaponMounted ) StopWeaponMount();
	}

	/// <summary> The gun settling onto the support, heard only by the one holding it. </summary>
	private void PlayMountSound()
	{
		var tr = Scene.Trace.Ray( _mountContact + Vector3.Up * 4f, _mountContact + Vector3.Down * 8f )
			.IgnoreGameObjectHierarchy( GameObject.Root ).WithoutTags( MountIgnoreTags ).Run();
		if ( !tr.Hit ) return;

		var sound = WorldSounds.Footstep( WorldSounds.SurfaceAt( tr ), false, true );
		if ( sound is null ) return;

		var snd = Sound.Play( sound, tr.HitPosition );
		if ( !snd.IsValid() ) return;

		snd.Volume *= 0.35f;
		snd.SpacialBlend = 0f;
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
		// Probe again on the press itself, so one pressed before the next periodic probe still mounts.
		if ( !Input.Pressed( "WeaponMount" ) ) return;
		if ( !TryFindMount( out _mountContact, out _mountForward, out _mountObject ) ) return;
		_mountAvailable = true;
		_mountOrigin = WorldPosition;
		_mountYaw = EyeAngles.yaw;
		_mountPitch = EyeAngles.pitch;
		_mountedEquipment = CurrentEquipment;
		IsWeaponMounted = true;
		PlayMountSound();
	}
}
