namespace Facepunch;

public sealed partial class LightweightCombatBot
{
	[Sync( SyncFlags.FromHost )] public bool IsProne { get; private set; }

	private readonly BotPronePose _pronePose = new();
	private float _proneBlend;
	private TimeUntil _nextProne;
	private TimeUntil _nextProneCheck;
	private TimeUntil _stanceShotWait;
	private Vector3 _proneFacing;
	private static readonly float[] ProneFloorChecks = { -38f, 0f, 26f };

	/// <summary>All machines lower the body, eyes and movement box together.</summary>
	private void UpdateStance()
	{
		if ( !IsAlive ) return;
		var step = Time.Delta / 0.45f;
		_proneBlend = IsProne ? MathF.Min( 1f, _proneBlend + step ) : MathF.Max( 0f, _proneBlend - step );
		SlideBlend = MathX.Lerp( SlideBlend, IsSliding ? 1f : 0f, (Time.Delta * (IsSliding ? 16f : 7f)).Clamp( 0f, 1f ) );
		if ( SlideBlend < .001f ) SlideBlend = 0f;
		if ( !_movementBox.IsValid() ) return;
		var bounds = BotPronePose.MovementBounds( IsCrouching, _proneBlend );
		if ( SlideBlend > 0f && _proneBlend <= 0f )
			bounds = BBox.FromPositionAndSize( new Vector3( 0f, 0f, MathX.Lerp( bounds.Size.z, 40f, SlideBlend ) * .5f ),
				new Vector3( 32f, 32f, MathX.Lerp( bounds.Size.z, 40f, SlideBlend ) ) );
		_movementBox.Center = bounds.Center;
		_movementBox.Scale = bounds.Size;
	}

	private void StandFromProne()
	{
		if ( !IsProne ) return;
		IsProne = false;
		_nextProne = Game.Random.Float( 14f, 28f );
		_stanceShotWait = 0.35f;
		_moveEnds = 0f;
	}

	/// <summary>Occasionally settle into a ranged firing position, more often for holders and marksmen.</summary>
	private bool TryPlantProne( float distance )
	{
		if ( IsSliding || SlideBlend > .05f || _nextProne.Relative > 0f || _proneBlend > 0f || distance < 650f || distance > EngageRange
			|| !_targetVisible || !IsEnemyAlive( _target ) || IsReloading || _timeSinceAcquired < 0.6f )
			return false;

		var chance = Habits.Style switch
		{
			BotStyle.Marksman => 0.3f,
			BotStyle.Anchor => 0.22f,
			BotStyle.Flanker => 0.05f,
			BotStyle.Rusher => 0.02f,
			_ => 0.1f
		};
		if ( Game.Random.Float() >= chance || !HasProneSpace() || !HasProneShot() )
			return false;

		IsCrouching = false;
		IsProne = true;
		_proneFacing = WorldRotation.Forward;
		_nextProneCheck = 0.35f;
		_stanceShotWait = 0.45f;
		_move = Move.Prone;
		_moveEnds = Habits.Style switch
		{
			BotStyle.Marksman => Game.Random.Float( 3f, 4.2f ),
			BotStyle.Anchor => Game.Random.Float( 2.5f, 4f ),
			_ => Game.Random.Float( 2.2f, 3.2f )
		};
		return true;
	}

	/// <summary>Get up when rushed, hurt, reloading, turning far, or losing the low firing angle.</summary>
	private bool ContinueProne( float distance )
	{
		if ( !IsProne ) return false;
		if ( _moveEnds.Relative <= 0f || distance < 500f || _hurt || IsReloading
			|| Vector3.GetAngle( _proneFacing, WorldRotation.Forward ) > 45f )
		{
			StandFromProne();
			return false;
		}

		if ( _nextProneCheck.Relative <= 0f )
		{
			_nextProneCheck = 0.35f;
			if ( !HasProneSpace() || !HasProneShot() )
			{
				StandFromProne();
				return false;
			}
		}

		HoldPosition();
		return true;
	}

	private bool HasProneShot()
	{
		var eye = WorldTransform.PointToWorld( BotPronePose.ProneEye );
		var point = LiveTargetPoint;
		var direction = (point - eye).Normal;
		// Don't lie down to shoot steeply up/down a ledge or with the gun still swinging round.
		if ( MathF.Abs( direction.z ) > 0.4f || WorldRotation.Forward.Dot( direction ) < 0.85f ) return false;
		var trace = Scene.Trace.Ray( eye, point + direction * 12f )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "playerclip", "movement", BreakableGlass.Tag )
			.UseHitboxes()
			.Run();
		return trace.Hit && HitTarget( trace.GameObject, _target );
	}

	private bool HasProneSpace()
	{
		// Check both ends of the body have floor beneath them, at nearly the same height.
		foreach ( var offset in ProneFloorChecks )
		{
			var point = WorldPosition + WorldRotation.Forward * offset;
			var floor = Scene.Trace.Ray( point + Vector3.Up * 10f, point - Vector3.Up * 12f )
				.IgnoreGameObjectHierarchy( GameObject )
				.WithoutTags( "trigger", "playerclip", "movement", "player", LightweightBotManager.BotTag, BreakableGlass.Tag )
				.Run();
			if ( !floor.Hit || floor.Normal.z < 0.98f || MathF.Abs( floor.EndPosition.z - WorldPosition.z ) > 4f )
				return false;
		}

		// Sweep the torso's full footprint; avoid lying through a wall, prop or another soldier.
		return !Scene.Trace.Ray( WorldPosition - WorldRotation.Forward * 38f + Vector3.Up * 14f,
				WorldPosition + WorldRotation.Forward * 26f + Vector3.Up * 14f )
			.Size( new Vector3( -12f, -14f, -10f ), new Vector3( 12f, 14f, 10f ) )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "trigger", "playerclip", "movement", BreakableGlass.Tag )
			.UseHitboxes()
			.Run().Hit;
	}
}
