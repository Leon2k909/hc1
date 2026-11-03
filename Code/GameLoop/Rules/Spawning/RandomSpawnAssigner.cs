
namespace Facepunch;

public sealed class RandomSpawnAssigner : Component, ISpawnAssigner
{
	/// <summary>
	/// Use spawns that include at least one of these tags.
	/// </summary>
	[Property, Title( "Tags" )]
	public TagSet SpawnTags { get; private set; } = new();

	/// <summary>
	/// Avoid spawning within this radius of an enemy player.
	/// </summary>
	[Property]
	public float MinEnemyDistance { get; set; } = 512f;

	/// <summary>
	/// Assume an enemy player is out of line-of-sight if at least this far away.
	/// </summary>
	[Property]
	public float SkipLineOfSightTestDistance { get; set; } = 2048;

	private (int Danger, float EnemyDistanceSquared) GetSpawnSafety( SpawnPointInfo spawn, IReadOnlyList<Transform> allPlayers, IReadOnlyList<Transform> enemyPlayers )
	{
		var occupied = allPlayers.Any( player => (player.Position - spawn.Position).LengthSquared < 64f * 64f );
		var nearestEnemySquared = enemyPlayers
			.Select( player => (player.Position - spawn.Position).LengthSquared )
			.DefaultIfEmpty( float.PositiveInfinity ).Min();
		var tooClose = nearestEnemySquared < MinEnemyDistance * MinEnemyDistance;
		var visible = false;

		foreach ( var player in enemyPlayers )
		{
			if ( (player.Position - spawn.Position).LengthSquared > SkipLineOfSightTestDistance * SkipLineOfSightTestDistance )
			{
				continue;
			}

			var tr = Scene.Trace
				.FromTo( spawn.Position + Vector3.Up * 64f, player.Position + Vector3.Up * 64f )
				.Size( 0.01f )
				.WithoutTags( "player", "ragdoll", "glass", "np_player", "trigger" )
				.Run();

			if ( !tr.Hit )
			{
				visible = true;
				break;
			}
		}

		// Each penalty outweighs every lower priority combined: never choose an occupied
		// spawn over a free one, then avoid close enemies, then exposed positions.
		return ((occupied ? 4 : 0) + (tooClose ? 2 : 0) + (visible ? 1 : 0), nearestEnemySquared);
	}

	SpawnPointInfo ISpawnAssigner.GetSpawnPoint( Client player )
	{
		var allPlayers = GameUtils.PlayerPawns
			.Where( x => x.IsValid() )
			.Where( x => x.Client != player )
			.Where( x => x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.Transform.World )
			.Concat( GameUtils.LightweightBots
				.Where( x => x.IsValid() && x.IsAlive )
				.Select( x => x.Transform.World ) )
			.ToArray();

		var enemyPlayers = GameUtils.PlayerPawns
			.Where( x => x.IsValid() )
			.Where( x => x.Client != player )
			.Where( x => !x.Client.IsFriendly( player ) )
			.Where( x => x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.Transform.World )
			.Concat( GameUtils.LightweightBots
				.Where( x => x.IsValid() && x.IsAlive )
				.Where( x => player.Team == Team.Unassigned || x.Team != player.Team )
				.Select( x => x.Transform.World ) )
			.ToArray();

		var spawns = GameUtils.GetSpawnPoints( SpawnTags.ToArray() )
			.Shuffle();

		if ( spawns.Count == 0 )
		{
			Log.Warning( $"No matching spawn points for {player.DisplayName}, using a map spawn." );
			return GameUtils.GetRandomSpawnPoint( Team.Unassigned );
		}

		var bestSpawn = spawns[0];
		var bestSafety = (Danger: int.MaxValue, EnemyDistanceSquared: float.NegativeInfinity);
		foreach ( var spawn in spawns )
		{
			var safety = GetSpawnSafety( spawn, allPlayers, enemyPlayers );
			if ( safety.Danger == 0 )
			{
				return spawn;
			}

			if ( safety.Danger < bestSafety.Danger ||
				(safety.Danger == bestSafety.Danger && safety.EnemyDistanceSquared > bestSafety.EnemyDistanceSquared) )
			{
				bestSpawn = spawn;
				bestSafety = safety;
			}
		}

		Log.Warning( $"Used safest available fallback spawn for {player.DisplayName}" );

		return bestSpawn;
	}
}
