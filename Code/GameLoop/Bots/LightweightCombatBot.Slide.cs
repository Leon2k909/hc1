namespace Facepunch;

public sealed partial class LightweightCombatBot
{
	[Sync( SyncFlags.FromHost )] public bool IsSliding { get; private set; }
	public float SlideBlend { get; private set; }

	private readonly ThirdPersonSlidePose _slidePose = new();
	private TimeUntil _nextSlide;
	private TimeUntil _nextSlideCheck;
	private TimeSince _slideTime;
	private float _slideSpeed, _slideAcceleration, _slideResumeSpeed, _sprintForSlide;
	private Vector3 _slideDirection;
	private Vector3? _slideResumeTarget;

	// Match the player's push and speed decay. Decisions are much less frequent than a player's Duck presses.
	private const float SlideMinSpeed = 225f;
	private const float SlideMaxDistance = 450f;
	private const float SlideMaxDuration = 1.5f;
	private const float SlideStopSpeed = 180f;
	private static readonly Vector3 SlideEye = new( 0f, 0f, 40f );

	private bool TryStartSlide()
	{
		var velocity = Agent.Velocity.WithZ( 0f );
		if ( velocity.Length < SlideMinSpeed || Agent.MaxSpeed <= MaxShoulderedSpeed || IsCrouching || IsProne
			|| _proneBlend > 0f || SlideBlend > .05f || IsReloading || IsReloadClipPlaying )
		{
			_sprintForSlide = 0f;
			return false;
		}
		_sprintForSlide += Time.Delta;
		if ( _sprintForSlide < .3f || _nextSlide.Relative > 0f || _nextSlideCheck.Relative > 0f ) return false;
		_nextSlideCheck = Game.Random.Float( 1.2f, 2.4f );
		var chance = Habits.Style switch
		{
			BotStyle.Rusher => .32f,
			BotStyle.Flanker => .24f,
			BotStyle.Anchor or BotStyle.Marksman => .08f,
			_ => .16f
		};
		// Sometimes slide into a close encounter, but never turn into a sideways slide at someone behind us.
		if ( _targetVisible )
		{
			var enemy = (LiveTargetPoint - EyePosition).WithZ( 0f );
			if ( enemy.Length < 200f || enemy.Length > 1000f || enemy.Normal.Dot( velocity.Normal ) < .8f ) return false;
			chance = MathF.Min( .5f, chance * 1.5f );
		}
		if ( Game.Random.Float() >= chance || !TrySlideRoute( velocity.Normal, out var end ) ) return false;
		StartSlide( end );
		return true;
	}

	private bool TrySlideRoute( Vector3 direction, out Vector3 end )
	{
		end = WorldPosition;
		if ( !Agent.IsNavigating ) return false;
		end = Agent.GetLookAhead( SlideMaxDistance );
		var travel = (end - WorldPosition).WithZ( 0f );
		if ( travel.Length < 300f || travel.Normal.Dot( direction ) < .98f
			|| WorldRotation.Forward.Dot( direction ) < .85f || !CanWalkTo( end ) ) return false;
		// Keep the slide on a straight, supported stretch of navmesh, away from stairs, ledges and other soldiers.
		if ( !SlideClear( WorldPosition, end ) ) return false;
		for ( var d = 0f; d <= travel.Length; d += 75f )
			if ( !SlideFloor( WorldPosition + travel.Normal * d, WorldPosition.z ) ) return false;
		return SlideFloor( end, WorldPosition.z );
	}

	private bool SlideFloor( Vector3 point, float height )
	{
		var floor = Scene.Trace.Ray( point.WithZ( height + 12f ), point.WithZ( height - 16f ) )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "corpse", "ragdoll", "movement", "player", LightweightBotManager.BotTag, BreakableGlass.Tag )
			.Run();
		return floor.Hit && floor.Normal.z > .94f && MathF.Abs( floor.EndPosition.z - height ) < 8f;
	}

	private bool SlideClear( Vector3 start, Vector3 end ) => !Scene.Trace.Ray( start, end )
		.Size( new Vector3( -18f, -18f, 2f ), new Vector3( 30f, 18f, 44f ) )
		.IgnoreGameObjectHierarchy( GameObject )
		.WithoutTags( "trigger", "corpse", "ragdoll" )
		.UseHitboxes().Run().Hit;

	private void StartSlide( Vector3 end )
	{
		_slideResumeTarget = _moveTarget;
		_slideResumeSpeed = Agent.MaxSpeed;
		_slideAcceleration = Agent.Acceleration;
		_slideSpeed = (Agent.Velocity.WithZ( 0f ).Length + 115f).Clamp( 340f, 430f );
		_slideDirection = (end - WorldPosition).WithZ( 0f ).Normal;
		_slideTime = 0f;
		IsSliding = true;
		IsCrouching = true;
		_sprintForSlide = 0f;
		Agent.Acceleration = MathF.Max( Agent.Acceleration, 2200f );
		Agent.MaxSpeed = _slideSpeed;
		Agent.MoveTo( end );
		PlayBotSlideSound();
	}

	private void ContinueSlide()
	{
		var ahead = WorldPosition + _slideDirection * MathF.Max( 64f, _slideSpeed * .2f );
		if ( _slideTime > SlideMaxDuration || _slideSpeed < SlideStopSpeed || !Agent.IsNavigating
			|| Agent.Velocity.WithZ( 0f ).Length < 40f || !SlideFloor( ahead, WorldPosition.z ) || !SlideClear( WorldPosition, ahead ) )
		{
			StopSlide();
			return;
		}
		var ramp = (((float)_slideTime - .35f) / .7f).Clamp( 0f, 1f );
		ramp = ramp * ramp * (3f - 2f * ramp);
		_slideSpeed *= MathF.Exp( -MathX.Lerp( .12f, 1.6f, ramp ) * Time.Delta );
		Agent.MaxSpeed = _slideSpeed;
	}

	private void StopSlide( bool resume = true )
	{
		if ( !IsSliding ) return;
		IsSliding = false;
		IsCrouching = false;
		_nextSlide = Game.Random.Float( 8f, 16f );
		_sprintForSlide = 0f;
		_moveTarget = null;
		if ( !Agent.IsValid() ) return;
		Agent.Acceleration = _slideAcceleration;
		Agent.MaxSpeed = _slideResumeSpeed;
		if ( resume && _slideResumeTarget is { } destination ) Agent.MoveTo( NavPoint( destination ) );
		else Agent.Stop();
		_slideResumeTarget = null;
	}

	[Rpc.Broadcast]
	private void PlayBotSlideSound()
	{
		var floor = Scene.Trace.Ray( WorldPosition + Vector3.Up * 8f, WorldPosition - Vector3.Up * 16f )
			.IgnoreGameObjectHierarchy( GameObject ).WithoutTags( "corpse", "ragdoll", "movement" ).Run();
		var sound = floor.Hit ? WorldSounds.Landing( WorldSounds.SurfaceAt( floor ) ) : null;
		if ( sound is null || !BotSystem.CanHear( sound, WorldPosition ) ) return;
		var handle = Sound.Play( sound, floor.HitPosition );
		if ( handle.IsValid() ) handle.Volume *= .7f;
	}
}
