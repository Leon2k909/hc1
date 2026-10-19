using System;
using System.Collections.Generic;

namespace Facepunch;

/// <summary>One vote per connected human connection, for one shared replay at a time.</summary>
public sealed class SndReplayVotes
{
	private readonly HashSet<Guid> _eligible = new();
	private readonly HashSet<Guid> _votes = new();
	private int _replayId;

	public int Count => _votes.Count;
	public int EligibleCount => _eligible.Count;
	public int Required => EligibleCount / 2 + 1;
	public bool HasMajority => _replayId > 0 && EligibleCount > 0 && Count >= Required;

	/// <summary>Positive IDs identify replays. An invalid ID clears and closes voting.</summary>
	public void Begin( int replayId, IEnumerable<Guid> eligible )
	{
		_replayId = replayId > 0 ? replayId : 0;
		_votes.Clear();
		Refresh( eligible );
	}

	/// <summary>Late joiners can vote; votes from departed connections no longer count.</summary>
	public void Refresh( IEnumerable<Guid> eligible )
	{
		_eligible.Clear();
		if ( _replayId > 0 && eligible is not null )
		{
			foreach ( var connection in eligible )
			{
				if ( connection != Guid.Empty )
					_eligible.Add( connection );
			}
		}

		_votes.IntersectWith( _eligible );
	}

	/// <summary>The caller supplies the connection identity authenticated by its host RPC.</summary>
	public bool TryVote( int replayId, Guid voter )
	{
		return _replayId > 0 && replayId == _replayId && voter != Guid.Empty
			&& _eligible.Contains( voter ) && _votes.Add( voter );
	}
}

public readonly record struct SndReplayScore( int Value, int Kills, int Headshots );

/// <summary>Scores eligible enemy kills in a rolling window. The caller validates each kill.</summary>
public sealed class SndReplayScoring
{
	public const float WindowSeconds = 6f;
	private const float UnitsPerMetre = 39.37f;
	private readonly Dictionary<Guid, Streak> _attackers = new();

	private readonly record struct Kill( double Time, bool Headshot, int DistancePoints );

	private sealed class Streak
	{
		public double LatestTime = double.NegativeInfinity;
		public readonly List<Kill> Kills = new();
	}

	/// <summary>
	/// Kills are worth 1000, headshots another 100, and the longest shot in the window contributes up to 99
	/// whole metres as a tiebreaker. Invalid distances contribute nothing. Out-of-order events can join the latest
	/// window, but cannot move its clock backwards or restore an expired streak. Nonfinite times are ignored.
	/// </summary>
	public SndReplayScore Record( Guid attacker, double time, bool headshot, float distance )
	{
		if ( attacker == Guid.Empty || !double.IsFinite( time ) )
			return default;

		if ( !_attackers.TryGetValue( attacker, out var streak ) )
		{
			streak = new Streak();
			_attackers.Add( attacker, streak );
		}

		streak.LatestTime = Math.Max( streak.LatestTime, time );
		streak.Kills.RemoveAll( kill => streak.LatestTime - kill.Time > WindowSeconds );

		if ( streak.LatestTime - time <= WindowSeconds )
		{
			var distancePoints = float.IsFinite( distance ) && distance > 0f
				? (int)Math.Min( distance / UnitsPerMetre, 99f )
				: 0;
			streak.Kills.Add( new Kill( time, headshot, distancePoints ) );
		}

		var headshots = 0;
		var furthest = 0;
		foreach ( var kill in streak.Kills )
		{
			if ( kill.Headshot ) headshots++;
			furthest = Math.Max( furthest, kill.DistancePoints );
		}

		var kills = streak.Kills.Count;
		return new SndReplayScore( kills * 1000 + headshots * 100 + furthest, kills, headshots );
	}

	public void Reset() => _attackers.Clear();
}
