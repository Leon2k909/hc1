namespace Facepunch;

public partial class PlayerPawn
{
	[Sync] public bool IsPipeClimbing { get; private set; }
	[Sync] public Vector3 PipeGripPosition { get; private set; }
	public float PipeClimbBlend { get; private set; }
	private ClimbablePipe _climbedPipe;
	private Vector3 _pipeOutward;
	private Vector3 _lastPipePosition;
	private TimeUntil _pipeRegrab;

	internal bool CanStartPipeClimb( ClimbablePipe pipe )
	{
		if ( !pipe.IsValid() || !pipe.CanClimb || !CharacterController.IsValid() || !HealthComponent.IsValid()
			|| HealthComponent.State != LifeState.Alive || IsPipeClimbing || IsMantling || IsNoclipping || IsFrozen
			|| IsProne || IsCrouching || IsFallKnockedDown || IsPilotingDrone || _isTouchingLadder || _pipeRegrab.Relative > 0f
			|| HasEquipmentTag( "planting" ) || HasEquipmentTag( "reloading" ) || HasEquipmentTag( "ready" )
			|| ZombiesPlayerState.For( this ) is { IsDowned: true } || CharacterController.Velocity.z < -250f )
			return false;
		if ( CurrentEquipment.IsValid() && CurrentEquipment.Components.GetAll<Throwable>( FindMode.EverythingInSelfAndDescendants )
			.Any( x => x.ThrowState is Throwable.State.Cook or Throwable.State.Throwing ) ) return false;

		var hand = WorldPosition + Vector3.Up * PipeClimbMath.HandHeight;
		if ( hand.z < pipe.Bottom.z + 4f || hand.z > pipe.Top.z - 8f ) return false;
		var toward = (pipe.Bottom - WorldPosition).WithZ( 0f );
		if ( toward.Length > UseDistance + pipe.WorldRadius || toward.Length < pipe.WorldRadius ) return false;
		if ( AimRay.Forward.Dot( toward.Normal ) < 0.25f ) return false;
		var sight = Scene.Trace.Ray( AimRay, UseDistance )
			.IgnoreGameObjectHierarchy( GameObject.Root ).WithoutTags( "movement" ).Run();
		if ( !sight.Hit || !sight.GameObject.IsValid() || sight.GameObject.GetComponentInParent<ClimbablePipe>() != pipe )
			return false;

		var target = PipeMountPosition( pipe, -toward.Normal, WorldPosition.z );
		if ( target.Distance( WorldPosition ) > 32f ) return false;
		return !PipeBodyTrace( WorldPosition, target ).Hit;
	}

	internal void StartPipeClimb( ClimbablePipe pipe )
	{
		if ( !IsLocallyControlled || !CanStartPipeClimb( pipe ) ) return;
		_climbedPipe = pipe;
		_pipeOutward = (WorldPosition - pipe.Bottom).WithZ( 0f ).Normal;
		WorldPosition = PipeMountPosition( pipe, _pipeOutward, WorldPosition.z );
		_lastPipePosition = WorldPosition;
		IsPipeClimbing = true;
		IsSprinting = false;
		WantsToggleSprint = false;
		IsUsing = false;
		CharacterController.Velocity = Vector3.Zero;
		CharacterController.IsOnGround = false;
		UpdatePipeGrip();
		if ( CurrentEquipment.IsValid() )
			foreach ( var aim in CurrentEquipment.Components.GetAll<Aimable>( FindMode.EverythingInSelfAndDescendants ) )
				if ( aim.IsValid() ) aim.CancelAim();
	}

	private Vector3 PipeMountPosition( ClimbablePipe pipe, Vector3 outward, float height )
	{
		var distance = PipeClimbMath.Standoff( outward, CharacterController.BoundingBox, pipe.WorldRadius * pipe.CollarScale );
		return (pipe.Bottom + outward * distance).WithZ( height );
	}

	private SceneTraceResult PipeBodyTrace( Vector3 from, Vector3 to ) => Scene.Trace.Ray( from, to )
		.Size( CharacterController.BoundingBox.Mins.WithZ( 2f ), CharacterController.BoundingBox.Maxs )
		.WithoutTags( CharacterController.IgnoreLayers )
		.IgnoreGameObjectHierarchy( GameObject.Root )
		.Run();

	private void UpdatePipeClimb()
	{
		var cc = CharacterController;
		if ( !_climbedPipe.IsValid() || !_climbedPipe.CanClimb || IsFrozen || IsProne || IsFallKnockedDown || IsPilotingDrone
			|| ZombiesPlayerState.For( this ) is { IsDowned: true } || WorldPosition.Distance( _lastPipePosition ) > 16f )
		{
			StopPipeClimb( Vector3.Zero );
			return;
		}

		if ( Input.Pressed( "Jump" ) )
		{
			var away = _pipeOutward;
			StopPipeClimb( Vector3.Zero );
			if ( !TryStartMantle( airborne: true, ignoreInput: true ) )
			{
				cc.Velocity = PipeClimbMath.JumpVelocity( away );
				BroadcastPlayerJumped();
			}
			return;
		}

		IsSprinting = false;
		IsUsing = false;
		var outward = PipeClimbMath.OutwardAt( _pipeOutward, WishMove.y, Time.Delta );
		var height = PipeClimbMath.StepHeight( WorldPosition.z, _climbedPipe.Bottom.z, _climbedPipe.Top.z,
			WishMove.x, _climbedPipe.ClimbSpeed * HealthComponent.WoundSpeedScale, Time.Delta );
		var target = PipeMountPosition( _climbedPipe, outward, height );
		if ( target.Distance( WorldPosition ) > 24f )
		{
			StopPipeClimb( Vector3.Zero );
			return;
		}
		var trace = PipeBodyTrace( WorldPosition, target );
		if ( WishMove.x < -0.1f && trace.Hit && trace.Normal.z > 0.65f )
		{
			StopPipeClimb( Vector3.Zero );
			return;
		}
		// A ceiling, tank or wall stops the move. Never correct sideways through it.
		if ( !trace.Hit ) _pipeOutward = outward;
		cc.IsOnGround = false;
		cc.Velocity = trace.Hit ? Vector3.Zero : (target - WorldPosition) / MathF.Max( Time.Delta, 0.001f );
		cc.Move();
		_lastPipePosition = WorldPosition;
		UpdatePipeGrip();
		if ( WishMove.x < -0.1f && cc.IsOnGround ) StopPipeClimb( Vector3.Zero );
	}

	private void UpdatePipeGrip() => PipeGripPosition = (_climbedPipe.Bottom + _pipeOutward * _climbedPipe.WorldRadius)
		.WithZ( WorldPosition.z + PipeClimbMath.HandHeight );

	private void StopPipeClimb( Vector3 velocity )
	{
		if ( !IsPipeClimbing ) return;
		IsPipeClimbing = false;
		_climbedPipe = null;
		_pipeRegrab = 0.5f;
		if ( CharacterController.IsValid() ) CharacterController.Velocity = velocity;
	}

	private void UpdatePipeAnimation()
	{
		PipeClimbBlend = PipeClimbBlend.Approach( IsPipeClimbing ? 1f : 0f, Time.Delta * 6f );
		if ( !Body.IsValid() ) return;
		foreach ( var helper in Body.AnimationHelpers )
		{
			if ( !helper.IsValid() ) continue;
			helper.IsClimbing = IsPipeClimbing || _isTouchingLadder;
			helper.LeftHandOverride = null;
			if ( !IsPipeClimbing || !helper.Target.IsValid() ) continue;
			var bone = helper.Target.Model?.Bones.GetBone( "hand_L" ) ?? helper.Target.Model?.Bones.GetBone( "l_hand" );
			if ( bone is not null && helper.Target.TryGetBoneTransform( bone, out var hand ) )
				helper.LeftHandOverride = hand.WithPosition( PipeGripPosition + Vector3.Up * 6f );
		}
	}
}
