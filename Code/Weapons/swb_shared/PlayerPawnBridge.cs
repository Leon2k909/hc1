using SWB.Shared;

namespace SWB;

/// <summary>
/// Add this component to the player GameObject so SWB weapons can find an IPlayerBase owner.
/// </summary>
[Group( "SWB" )]
[Title( "Player Pawn Bridge" )]
public sealed partial class PlayerPawnBridge : Component, IPlayerBase
{
	private Facepunch.PlayerPawn _player;
	private Facepunch.PlayerPawn Player => _player ??= Components.GetInAncestors<Facepunch.PlayerPawn>( true );

	[Property] public CameraComponent ViewModelCamera { get; set; }
	public CameraComponent Camera => Player?.CameraController?.Camera;

	bool IPlayerBase.IsFirstPerson => true;
	Vector3 IPlayerBase.Velocity => Player?.CharacterController?.Velocity ?? Vector3.Zero;
	bool IPlayerBase.IsCrouching => Player?.IsCrouching ?? false;
	bool IPlayerBase.IsRunning => Player?.IsSprinting ?? false;
	bool IPlayerBase.IsOnGround => Player?.IsGrounded ?? false;
	bool IPlayerBase.IsClimbingLadder => false;
	bool IPlayerBase.IsAlive => (Player?.HealthComponent?.State == Facepunch.LifeState.Alive);
	[Sync] public bool IsBot { get; set; }
	Angles IPlayerBase.EyeAngles => Player?.EyeAngles ?? Angles.Zero;
	Vector3 IPlayerBase.EyePos => Player?.CameraGameObject?.WorldPosition ?? WorldPosition;
	public float InputSensitivity { get; set; } = 1.0f;
	public float FieldOfView { get; set; } = 75f;

	HoldTypes IPlayerBase.HoldType
	{
		set
		{
			// Hold type is handled by the existing equipment system
		}
	}

	protected override void OnAwake()
	{
		_player = Components.GetInAncestors<Facepunch.PlayerPawn>( true );
	}

	public int AmmoCount( string type ) => 999; // SWB weapons manage their own ammo

	public void TriggerAnimation( Animations animation ) { }

	public void ApplyEyeAnglesOffset( Angles offset )
	{
		if ( Player?.IsValid() ?? false )
			Player.EyeAngles += offset;
	}

	public void ParentToBone( GameObject obj, string boneName, bool deleteOnFail = true, Action<GameObject> onFail = null )
	{
		var body = Player?.Body;
		if ( !body?.IsValid() ?? true )
		{
			if ( deleteOnFail ) obj?.Destroy();
			onFail?.Invoke( obj );
			return;
		}

		var bone = body.Components.Get<SkinnedModelRenderer>()?.GetBoneObject( boneName );
		if ( !bone?.IsValid() ?? true )
		{
			if ( deleteOnFail ) obj?.Destroy();
			onFail?.Invoke( obj );
			return;
		}

		obj.Parent = bone;
	}

	public int TakeAmmo( string type, int amount ) => amount; // always grant requested amount

	public void ShakeScreen( SWB.Shared.ScreenShake screenShake ) { }

	public void OnDamage( in Sandbox.DamageInfo info )
	{
		if ( Player?.HealthComponent?.IsValid() ?? false )
		{
			var attacker = info.Attacker?.Components?.Get<Component>();
			Player.HealthComponent.TakeDamage( new Facepunch.DamageInfo( attacker, info.Damage ) );
		}
	}
}
