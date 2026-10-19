using Sandbox.MovieMaker;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

public sealed partial class MatchRecorder
{
	/// <summary>Freeze the bounded recorder and sidecars without changing the live recording.</summary>
	public SndReplayClip CaptureReplay( Guid shooter, float killedAt, float seconds )
	{
		if ( _replayRecorder is null || _actions is null || _finished ) return null;
		var end = MathF.Min( (float)_replayRecorder.Time.TotalSeconds, (float)(killedAt - _startTime) + ReplayAfterKill );
		var start = MathF.Max( _replayRoundStart, end - Math.Clamp( seconds, 0f, ReplayBufferSeconds ) );
		if ( end <= start ) return null;
		var followed = _replaySoldiers.Values.FirstOrDefault( s => s.Entry.ObjectId == shooter
			&& s.Entry.Spawned <= end && (s.Entry.Removed < 0 || s.Entry.Removed >= start) );
		if ( followed is null ) return null;
		var lives = _replaySoldiers.Values.Where( s => s.Entry.Spawned <= end
			&& (s.Entry.Removed < 0 || s.Entry.Removed >= start) ).ToArray();
		var actions = Snapshot( _actions );
		var tracks = lives.Select( s => s.Entry.Track ).ToHashSet();
		foreach ( var track in actions.Lives.Keys.Where( key => !tracks.Contains( key ) ).ToArray() ) actions.Lives.Remove( track );
		return new SndReplayClip( _replayRecorder.ToClip(), lives.Select( s => Snapshot( s.Entry ) ).ToList(),
			actions, followed.Entry.Track, start, end );
	}

	public void ResetReplayRound()
	{
		_replayRoundStart = (float)(Time.NowDouble - _startTime);
		_nextReplayTrim = _replayRoundStart;
		_replaySoldiers.Clear();
		foreach ( var soldier in _soldiers.Values ) soldier.ReplayNamed = false;
		if ( _replayRecorder is not null ) _replayRecorder = new MovieRecorder( Scene,
			CaptureOptions( MovieTime.FromSeconds( ReplayBufferSeconds ) ) );
		if ( _recorder is null ) TrimReplayActions( _replayRoundStart );
	}

	static T Snapshot<T>( T value ) => Json.Deserialize<T>( Json.Serialize( value ) );

	void DetachReplayMetadata( float seconds )
	{
		_actions = Snapshot( _actions );
		foreach ( var soldier in _soldiers.Values.Concat( _replaySoldiers.Values ).Distinct() )
		{
			soldier.Entry = Snapshot( soldier.Entry );
			soldier.Actions = _actions.Lives.GetValueOrDefault( soldier.Entry.Track ) ?? new();
			_actions.Lives[soldier.Entry.Track] = soldier.Actions;
		}
		_info = null;
		TrimReplayActions( MathF.Max( _replayRoundStart, seconds - ReplayBufferSeconds ) );
	}

	void TrimReplayActions( float cutoff )
	{
		if ( _actions is null ) return;
		foreach ( var pair in _replaySoldiers.Where( p => p.Value.Entry.Removed >= 0
			&& p.Value.Entry.Removed < cutoff ).ToArray() )
		{
			_replaySoldiers.Remove( pair.Key );
			_actions.Lives.Remove( pair.Key );
		}
		foreach ( var life in _actions.Lives.Values )
		{
			life.Shots.RemoveAll( time => time < cutoff );
			TrimToggles( life.Aiming, cutoff );
			TrimToggles( life.Sprinting, cutoff );
			TrimToggles( life.Reloading, cutoff );
			TrimToggles( life.Empty, cutoff );
			var held = life.Held.FindLastIndex( item => item.At <= cutoff );
			if ( held > 0 ) life.Held.RemoveRange( 0, held );
		}
	}

	static void TrimToggles( List<float> times, float cutoff )
	{
		if ( times is null ) return;
		// Remove complete on/off pairs; retaining an unmatched start preserves the state at the boundary.
		var remove = times.TakeWhile( time => time < cutoff ).Count();
		remove -= remove % 2;
		if ( remove > 0 ) times.RemoveRange( 0, remove );
	}
}
