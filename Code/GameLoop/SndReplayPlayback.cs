using Sandbox.MovieMaker;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

/// <summary>A private MovieMaker playback in the loaded map, with all live actor visibility restored on disposal.</summary>
internal sealed class SndReplayPlayback : IDisposable
{
	readonly GameObject _object;
	readonly MoviePlayer _player;
	readonly CameraComponent _camera;
	readonly TheaterClip _clip;
	readonly SndReplayClip _source;
	readonly TheaterViewModel _gun = new();
	readonly List<(ModelRenderer Renderer, bool Enabled)> _live = new();
	readonly List<(ModelRenderer Renderer, ModelRenderer.ShadowRenderType Mode)> _hidden = new();
	GameObject _followed;
	bool _first = true;
	bool _disposed;

	public SndReplayPlayback( Scene scene, SndReplayClip source )
	{
		_source = source ?? throw new ArgumentNullException( nameof(source) );
		using var scope = scene.Push();
		_object = new GameObject( true, "S&D replay playback" );
		_object.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		try
		{
			_player = _object.Components.Create<MoviePlayer>();
			_player.IsPlaying = false;
			_clip = new TheaterClip( source.Movie, _player.Binder, source.Soldiers );
			var previous = scene.Camera;
			_camera = _object.Components.Create<CameraComponent>();
			if ( previous.IsValid() )
			{
				previous.CopyPropertiesTo( _camera );
				CameraPostProcess.Copy<Tonemapping>( previous.GameObject, _object );
				CameraPostProcess.Copy<Bloom>( previous.GameObject, _object );
				CameraPostProcess.Copy<Sharpen>( previous.GameObject, _object );
				CameraPostProcess.Copy<AmbientOcclusion>( previous.GameObject, _object );
				CameraPostProcess.Copy<Vignette>( previous.GameObject, _object );
				CameraPostProcess.Copy<ColorAdjustments>( previous.GameObject, _object );
			}
			_camera.IsMainCamera = true;
			_camera.Priority = Math.Max( 100, previous.IsValid() ? previous.Priority + 1 : 100 );
			var actors = scene.GetAllComponents<PlayerPawn>().Select( p => p.GameObject )
				.Concat( scene.GetAllComponents<LightweightCombatBot>().Select( b => b.GameObject ) )
				.Concat( scene.GetAllComponents<PlayerBody>().Select( b => b.GameObject ) ).Distinct();
			foreach ( var renderer in actors.SelectMany( actor => actor.GetComponentsInChildren<ModelRenderer>( true, true ) ).Distinct() )
			{
				_live.Add( (renderer, renderer.Enabled) );
				renderer.Enabled = false;
			}
			_clip.ListAllTracks = true;
			_player.Clip = _clip;
			_clip.ListAllTracks = false;
			foreach ( var life in _clip.Lives )
			{
				var root = life.GetRoot( _player.Binder );
				if ( root.IsValid() ) root.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			}
			Update( 0 );
		}
		catch
		{
			Dispose();
			throw;
		}
	}

	public void Update( float elapsed )
	{
		if ( _disposed ) return;
		var position = Math.Clamp( _source.Start + elapsed, _source.Start, _source.End );
		_clip.SetTime( position );
		_player.Position = MovieTime.FromSeconds( position );
		var life = _clip.Active.FirstOrDefault( candidate => candidate.Root.Name == _source.FollowTrack );
		var root = life?.GetRoot( _player.Binder );
		var body = life?.GetBody( _player.Binder );
		if ( !root.IsValid() || !body.IsValid() ) return;
		if ( root != _followed )
		{
			RestoreFollowed();
			_followed = root;
			foreach ( var renderer in root.GetComponentsInChildren<ModelRenderer>( true, true ) )
			{
				_hidden.Add( (renderer, renderer.RenderType) );
				renderer.RenderType = ModelRenderer.ShadowRenderType.ShadowsOnly;
			}
			_first = true;
		}
		_camera.WorldPosition = body.GetAttachment( "eyes", false ) is { } eyes
			? body.WorldTransform.PointToWorld( eyes.Position ) : body.WorldPosition + Vector3.Up * 64;
		var look = body.GetVector( "aim_body" );
		_camera.WorldRotation = Rotation.LookAt( look.IsNearZeroLength ? body.WorldRotation.Forward : body.WorldRotation * look.Normal );
		_gun.Update( life, root, body, _source.Actions, _camera, position, 1f,
			GameSettingsSystem.Current?.FieldOfView ?? 90f, _first );
		_first = false;
	}

	void RestoreFollowed()
	{
		foreach ( var (renderer, mode) in _hidden ) if ( renderer.IsValid() ) renderer.RenderType = mode;
		_hidden.Clear();
		_followed = null;
	}

	public void Dispose()
	{
		if ( _disposed ) return;
		_disposed = true;
		_gun.Clear();
		RestoreFollowed();
		if ( _clip is not null && _player.IsValid() )
			foreach ( var life in _clip.Lives ) life.GetRoot( _player.Binder )?.Destroy();
		if ( _object.IsValid() ) _object.Destroy();
		foreach ( var (renderer, enabled) in _live ) if ( renderer.IsValid() ) renderer.Enabled = enabled;
		_live.Clear();
	}
}
