using Sandbox.MovieMaker;
using Sandbox.MovieMaker.Compiled;
using Sandbox.MovieMaker.Properties;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

/// <summary>
/// A Theater recording as <see cref="TheaterController"/>'s MoviePlayer sees it. MovieMaker evaluates every track of a
/// clip on every frame, which for a long match is tens of thousands of tracks, most of them lives long over. This clip
/// gives it only the tracks of the lives around the current time (<see cref="SetTime"/>), and hides the objects of the
/// lives it leaves out, which their own tracks would otherwise have hidden.
/// </summary>
public sealed class TheaterClip : IMovieClip
{
	/// <summary> How long before and after its recorded time a life's tracks are still played. </summary>
	const double Margin = 0.5;

	public MovieClip Clip { get; }

	/// <summary> Every life in the recording: a player's or bot's root track and everything under it. </summary>
	public IReadOnlyList<Life> Lives => _lives;

	/// <summary> The lives being played at the time last given to <see cref="SetTime"/>. </summary>
	public IReadOnlyList<Life> Active => _active;

	/// <summary>
	/// Lists every track, as the MoviePlayer needs while it creates the objects to play them on. Once they're made it
	/// only asks again if the clip changes.
	/// </summary>
	public bool ListAllTracks { get; set; } = true;

	public MovieTime Duration => Clip.Duration;

	readonly TrackBinder _binder;
	readonly List<ITrack> _allTracks;
	readonly List<ITrack> _sharedTracks = new();
	readonly List<Life> _lives = new();
	readonly List<Life> _active = new();
	readonly List<ITrack> _activeTracks = new();
	bool _started;

	public TheaterClip( MovieClip clip, TrackBinder binder, IEnumerable<TheaterReplays.Soldier> soldiers )
	{
		Clip = clip;
		_binder = binder;
		_allTracks = clip.Tracks.Cast<ITrack>().ToList();

		var soldiersByTrack = new Dictionary<string, TheaterReplays.Soldier>();
		foreach ( var soldier in soldiers ?? Enumerable.Empty<TheaterReplays.Soldier>() )
			soldiersByTrack.TryAdd( soldier.Track ?? "", soldier );

		var livesByRoot = new Dictionary<Guid, Life>();

		// In the clip's order, so each life applies parents before children as the whole clip would.
		foreach ( var track in _allTracks )
		{
			if ( RootOf( track ) is not IReferenceTrack<GameObject> root )
			{
				_sharedTracks.Add( track );
				continue;
			}

			if ( !livesByRoot.TryGetValue( root.Id, out var life ) )
			{
				life = new Life( root, soldiersByTrack.GetValueOrDefault( root.Name ) );
				livesByRoot[root.Id] = life;
				_lives.Add( life );
			}

			life.Add( track );
		}

		foreach ( var life in _lives )
			life.Finish();
	}

	public IEnumerable<ITrack> Tracks => ListAllTracks ? _allTracks : _activeTracks;

	public IReferenceTrack GetTrack( Guid trackId ) => Clip.GetTrack( trackId );

	public IEnumerable<ITrack> GetTracks( MovieTime time ) => _activeTracks;

	/// <summary> Picks the lives to play at <paramref name="seconds"/>, and hides those it stops playing. </summary>
	public void SetTime( double seconds )
	{
		var time = MovieTime.FromSeconds( seconds );
		var changed = !_started;
		_started = true;

		foreach ( var life in _lives )
		{
			var active = life.IsActiveAt( time );
			if ( active == life.IsActive )
				continue;

			life.IsActive = active;
			changed = true;

			if ( !active )
				life.Hide( _binder );
		}

		if ( !changed )
			return;

		_active.Clear();
		_activeTracks.Clear();
		_activeTracks.AddRange( _sharedTracks );

		foreach ( var life in _lives )
		{
			if ( !life.IsActive )
				continue;

			_active.Add( life );
			_activeTracks.AddRange( life.Tracks );
		}
	}

	static ITrack RootOf( ITrack track )
	{
		while ( track.Parent is { } parent )
			track = parent;

		return track;
	}

	/// <summary> One player's or bot's life: its root track and every track under it. </summary>
	public sealed class Life
	{
		public IReferenceTrack<GameObject> Root { get; }

		/// <summary> Who it was, from the replay's sidecar. Null for a track the sidecar doesn't name. </summary>
		public TheaterReplays.Soldier Soldier { get; }

		/// <summary> From its first recorded value to its last. </summary>
		public MovieTimeRange Range { get; private set; }

		/// <summary> Whether its tracks are being played. Every life starts out so: its objects are made enabled. </summary>
		public bool IsActive { get; internal set; } = true;

		internal readonly List<ITrack> Tracks = new();

		/// <summary> Objects with an Enabled track, which shows and hides them while the life plays. </summary>
		readonly List<Guid> _hideable = new();
		readonly List<Guid> _renderers = new();

		IReferenceTrack _body;
		IReferenceTrack<GameObject> _weaponHold;
		bool _hasRange;

		internal Life( IReferenceTrack<GameObject> root, TheaterReplays.Soldier soldier )
		{
			Root = root;
			Soldier = soldier;
		}

		internal void Add( ITrack track )
		{
			Tracks.Add( track );

			if ( track is not ICompiledBlockTrack blockTrack || blockTrack.Blocks.Count == 0 )
				return;

			var range = blockTrack.TimeRange;
			Range = _hasRange ? Range.Union( range ) : range;
			_hasRange = true;
		}

		internal void Finish()
		{
			foreach ( var track in Tracks )
			{
				if ( track is IPropertyTrack { Name: "Enabled", Parent: IReferenceTrack<GameObject> go } )
					_hideable.Add( go.Id );

				if ( track is IReferenceTrack<SkinnedModelRenderer> renderer )
					_renderers.Add( renderer.Id );
			}

			_body = FindBody();

			// Bots have no bone objects (BotSystem.FollowHands): a bot's gun is on this, which it moved to the hand every frame.
			_weaponHold = Tracks.OfType<IReferenceTrack<GameObject>>()
				.FirstOrDefault( x => x.Parent?.Id == Root.Id && x.Name == "WeaponHold" );
		}

		IReferenceTrack FindBody()
		{
			IReferenceTrack<GameObject> bodyObject = Root;

			foreach ( var name in (Soldier?.Body ?? "").Split( '/', StringSplitOptions.RemoveEmptyEntries ) )
			{
				var parent = bodyObject;
				bodyObject = Tracks.OfType<IReferenceTrack<GameObject>>()
					.FirstOrDefault( x => x.Parent?.Id == parent.Id && x.Name == name );

				if ( bodyObject is null )
					break;
			}

			var renderers = Tracks.OfType<IReferenceTrack<SkinnedModelRenderer>>().ToList();

			if ( bodyObject is not null && renderers.FirstOrDefault( x => x.Parent?.Id == bodyObject.Id ) is { } body )
				return body;

			// The renderer that recorded anim graph parameters or bones is the body.
			return renderers.FirstOrDefault( x => Tracks.Any( t => t is IPropertyTrack { Name: "Parameters" or "Bones" } && t.Parent is IReferenceTrack { } p && p.Id == x.Id ) )
				?? renderers.FirstOrDefault();
		}

		public bool IsActiveAt( MovieTime time )
		{
			if ( !_hasRange )
				return false;

			var margin = MovieTime.FromSeconds( Margin );
			return time >= Range.Start - margin && time <= Range.End + margin;
		}

		public GameObject GetRoot( TrackBinder binder ) => Get<GameObject>( binder, Root.Id );

		public SkinnedModelRenderer GetBody( TrackBinder binder ) => _body is null ? null : Get<SkinnedModelRenderer>( binder, _body.Id );

		public GameObject GetWeaponHold( TrackBinder binder ) => _weaponHold is null ? null : Get<GameObject>( binder, _weaponHold.Id );

		public IEnumerable<SkinnedModelRenderer> GetRenderers( TrackBinder binder )
		{
			foreach ( var id in _renderers )
			{
				if ( Get<SkinnedModelRenderer>( binder, id ) is { } renderer )
					yield return renderer;
			}
		}

		internal void Hide( TrackBinder binder )
		{
			foreach ( var id in _hideable )
			{
				if ( Get<GameObject>( binder, id ) is { } go )
					go.Enabled = false;
			}

			// Its ragdoll's bones, so they don't come back for a frame when it plays again.
			foreach ( var renderer in GetRenderers( binder ) )
				MovieBoneAnimatorSystem.Current?.ClearBones( renderer );
		}

		static T Get<T>( TrackBinder binder, Guid id ) where T : class, IValid
		{
			return binder.TryGetBinding<T>( id, out var target ) && target.IsValid() ? target : null;
		}
	}
}
