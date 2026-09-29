namespace Facepunch;

/// <summary>
/// Battle royale (<see cref="BattleRoyaleMatch"/>): every bot for itself, fighting whoever it runs into anywhere on the
/// map, and keeping ahead of the zone (<see cref="SafeZoneManager"/>) the way a player does. Cautious bots head for the
/// next circle early, aggressive ones cut it fine, and nobody follows a fight out into the gas.
/// </summary>
public sealed partial class LightweightCombatBot
{
	/// <summary> Battle royale: how far a bot goes after someone it knows is about. Further off, it roams toward the next circle. </summary>
	private const float RoyaleHuntRange = 2500f;
	/// <summary> A route's length over the straight line, roughly, for how long a run into the zone takes. </summary>
	private const float RouteFactor = 1.3f;

	private Vector3? _zonePoint;
	private int _zonePointPhase = -1;
	private TimeUntil _nextZonePick;

	/// <summary> The battle royale's zone once it's closing, else null (every other mode). </summary>
	private static SafeZoneManager RunningZone =>
		GameUtils.IsBattleRoyale && SafeZoneManager.Current is { IsRunning: true } zone ? zone : null;

	/// <summary> Battle royale: is <paramref name="position"/> out in the zone's damage? Never, in other modes. </summary>
	private static bool OutsideZone( Vector3 position ) => RunningZone is { } zone && zone.DistanceOutside( position ) > 0f;

	/// <summary>
	/// Battle royale: out in the gas, or outside the next circle while it closes (or about to), head for a spot inside
	/// the next circle, still shooting at anyone seen on the way. The time a bot leaves itself runs from 45 s for the most
	/// cautious to 10 s for the most aggressive. True while it's on its way.
	/// </summary>
	private bool HeadForZone()
	{
		if ( RunningZone is not { } zone )
		{
			_zonePoint = null;
			return false;
		}

		var outsideNext = zone.DistanceOutsideNext( WorldPosition );
		if ( outsideNext <= 0f )
		{
			_zonePoint = null;
			return false;
		}

		if ( !zone.IsShrinking && zone.DistanceOutside( WorldPosition ) <= 0f )
		{
			// Safe for now, and the hold has time left: fight on until it's time to go.
			var runTime = outsideNext * RouteFactor / MathF.Max( MoveSpeed, 1f );
			if ( zone.StageTimeLeft > runTime + MathX.Lerp( 45f, 10f, Aggression ) )
				return false;
		}

		if ( _zonePointPhase != zone.PhaseNumber || (!_zonePoint.HasValue && _nextZonePick.Relative <= 0f) )
		{
			_zonePoint = PickZonePoint( zone );
			_zonePointPhase = zone.PhaseNumber;
			_nextZonePick = 1f;
		}

		if ( _zonePoint is not { } point )
			return false;

		IsCrouching = false;
		if ( GoTo( point, UrgentSpeed ) )
			return true;

		_zonePoint = null;
		return false;
	}

	/// <summary> Somewhere inside the next circle, on this bot's side of it and well in from the edge, that it can walk to. </summary>
	private Vector3? PickZonePoint( SafeZoneManager zone )
	{
		var center = zone.NextCenter;
		var away = (WorldPosition - center).WithZ( 0f );
		var direction = away.IsNearZeroLength ? Vector3.Forward : away.Normal;
		for ( var i = 0; i < 4; i++ )
		{
			var turned = Rotation.FromYaw( Game.Random.Float( -50f, 50f ) ) * direction;
			var point = NavPoint( center + turned * zone.NextRadius * Game.Random.Float( 0.35f, 0.75f ) );
			if ( zone.DistanceOutsideNext( point ) <= 0f && CanWalkTo( point ) )
				return point;
		}

		var middle = NavPoint( center );
		return CanWalkTo( middle ) ? middle : null;
	}

	/// <summary>
	/// Battle royale's hunt: after someone it knows is about (<see cref="RoyaleHuntRange"/>, the nearest most likely),
	/// with a rough idea of where, else a stretch of the way toward somewhere in the next circle. Players aren't picked
	/// out over bots, and nobody is chased into the gas. As in <see cref="PickHuntTarget"/>, a bot stays after the one it
	/// picked for 20 to 30 s, and <paramref name="current"/> is where it's still on its way to (see <see cref="Hunt"/>).
	/// </summary>
	private Vector3 RoyaleHuntDestination( Vector3? current )
	{
		var enemies = EnemyScratch;
		enemies.Clear();
		CollectEnemies( enemies );
		var keep = _nextHuntTargetPick.Relative > 0f;
		Component chosen = null;
		var total = 0f;
		foreach ( var enemy in enemies )
		{
			var distance = enemy.WorldPosition.Distance( WorldPosition );
			if ( distance > RoyaleHuntRange || OutsideZone( enemy.WorldPosition ) )
				continue;

			if ( keep && enemy == _huntTarget )
			{
				chosen = enemy;
				break;
			}

			var weight = 1f / (distance + 600f);
			total += weight;
			if ( Game.Random.Float( 0f, total ) < weight )
				chosen = enemy;
		}

		enemies.Clear();
		if ( !keep || chosen != _huntTarget )
			_nextHuntTargetPick = Game.Random.Float( 20f, 30f );

		if ( chosen.IsValid() && HuntSpot( chosen, current ) is { } destination )
			return destination;

		return KeepRoaming( current ) ?? ZoneRoamPoint() ?? RandomPatrolPoint();
	}

	/// <summary> Up to 2500 units of the way toward a random spot in the next circle, somewhere it can walk to. </summary>
	private Vector3? ZoneRoamPoint()
	{
		if ( RunningZone is not { } zone )
			return null;

		for ( var i = 0; i < 3; i++ )
		{
			var angle = Game.Random.Float( 0f, MathF.PI * 2f );
			var goal = zone.NextCenter + new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f )
				* (zone.NextRadius * 0.9f * MathF.Sqrt( Game.Random.Float() ));
			var step = (goal - WorldPosition).WithZ( 0f );
			if ( step.Length > 2500f )
				goal = WorldPosition + step.Normal * Game.Random.Float( 1200f, 2500f );

			var point = NavPoint( goal );
			if ( !OutsideZone( point ) && CanWalkTo( point ) )
				return point;
		}

		return null;
	}
}
