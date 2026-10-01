using Sandbox.Events;

namespace Facepunch;

public class SpawnRule
{
	public Team Team { get; set; }
	public string Tag { get; set; }

	public int MinPlayers { get; set; }
	public int MaxPlayers { get; set; }
}

/// <summary>
/// Use team-specific spawn points.
/// </summary>
public sealed class TeamSpawnAssigner : Component,
	ISpawnAssigner
{
	/// <summary>
	/// Use spawns that include at least one of these tags.
	/// </summary>
	[Property, Title( "Tags" )]
	public TagSet SpawnTags { get; private set; } = new();

	[Property, InlineEditor]
	public List<SpawnRule> SpawnRules { get; private set; } = new();

	public SpawnPointInfo GetSpawnPoint( Client player )
	{
		// Skirmish on a big map: the arena's ring, away from the enemy.
		if ( SkirmishArena.Settled is { } arena )
			return arena.PickSpawn( player.Team, player.PlayerPawn?.GameObject );

		var team = player.Team;
		var spawns = GameUtils.GetSpawnPoints( team, SpawnTags.ToArray() ).Shuffle();

		if ( spawns.Count == 0 && player.Team != Team.Unassigned )
		{
			Log.Warning( $"No spawn points for team {team}!" );
			return GameUtils.GetRandomSpawnPoint(Team.Unassigned);
		}

		var playerPositions = GameUtils.PlayerPawns
			.Where( x => x.Client != player )
			.Where( x => x.TimeSinceLastRespawn < 1f )
			.Where( x => x.HealthComponent.State == LifeState.Alive )
			.Select( x => (x.WorldPosition, Tags: x.SpawnPointTags) )
			.ToArray();

		var occupiedPositions = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.Client != player && x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.WorldPosition )
			.Concat( GameUtils.LightweightBots
				.Where( x => x.IsValid() && x.IsAlive )
				.Select( x => x.WorldPosition ) )
			.ToArray();
		var enemyPositions = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.Client != player && x.HealthComponent.State == LifeState.Alive )
			.Where( x => team == Team.Unassigned || x.Team != team )
			.Select( x => x.WorldPosition )
			.Concat( GameUtils.LightweightBots
				.Where( x => x.IsValid() && x.IsAlive && (team == Team.Unassigned || x.Team != team) )
				.Select( x => x.WorldPosition ) )
			.ToArray();

		foreach ( var rule in SpawnRules )
		{
			if ( rule.Team != player.Team )
			{
				continue;
			}

			var matchingPlayers = playerPositions
				.Count( x => x.Tags.Contains( rule.Tag, StringComparer.OrdinalIgnoreCase ) );

			if ( matchingPlayers >= rule.MaxPlayers )
			{
				continue;
			}

			if ( matchingPlayers < rule.MinPlayers )
			{
				spawns = spawns
					.Where( x => x.Tags.Contains( rule.Tag, StringComparer.OrdinalIgnoreCase ) )
					.ToArray();
			}
		}

		var bestScore = float.NegativeInfinity;
		SpawnPointInfo bestSpawn = default;
		var found = false;
		foreach ( var spawn in spawns )
		{
			var nearestOccupant = occupiedPositions.Select( x => x.Distance( spawn.Position ) )
				.DefaultIfEmpty( 1000f ).Min();
			var nearestEnemy = enemyPositions.Select( x => x.Distance( spawn.Position ) )
				.DefaultIfEmpty( 6000f ).Min();
			var visibleToEnemy = enemyPositions.Any( enemy =>
			{
				if ( enemy.DistanceSquared( spawn.Position ) > 3000f * 3000f )
					return false;

				return !Scene.Trace.FromTo( spawn.Position + Vector3.Up * 64f, enemy + Vector3.Up * 64f )
					.WithoutTags( "player", "ragdoll", "glass", "np_player", "trigger" )
					.Run().Hit;
			} );

			// Prefer distance and cover. A crowded spawn is the last resort.
			var score = MathF.Min( nearestEnemy, 6000f )
				- (nearestEnemy < 1200f ? 6000f : 0f)
				- (visibleToEnemy ? 3000f : 0f)
				- (nearestOccupant < 96f ? 10000f : 0f);
			if ( score <= bestScore )
				continue;

			bestScore = score;
			bestSpawn = spawn;
			found = true;
		}

		if ( found )
			return bestSpawn;

		Log.Info( "Found no SpawnPoint matching the current rules, falling back to random." );
		return GameUtils.GetRandomSpawnPoint( team );
	}
}
