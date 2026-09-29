using Sandbox.Events;

namespace Facepunch;

public record GamemodeInitializedEvent( string Title ) : IGameEvent;

/// <summary>
/// Handles the main game loop, using components that listen to state change
/// events to handle game logic.
/// </summary>
public sealed partial class GameMode : SingletonComponent<GameMode>, Component.INetworkListener
{
	[RequireComponent] public MatchRecorder MatchRecorder { get; set; }

	/// <summary>
	/// If we're the host, the path in the scene of the selected game mode.
	/// </summary>
	public static string ActivePath { get; private set; }

	/// <summary>
	/// Whether the next game session should use hardcore rules. Core modes are switched off for now, so every
	/// multiplayer match is hardcore; only Zombies turns it off.
	/// </summary>
	public static bool ActiveHardcore { get; private set; } = true;
	// Put back when Core modes return:
	// public static bool ActiveHardcore { get; private set; }

	public static string ActiveIdent { get; private set; }

	/// <summary>
	/// Sets the current gamemode for the next scene load.
	/// </summary>
	/// <param name="gameMode"></param>
	public static void SetCurrent( GameMode gameMode )
	{
		ActiveRanked = false;
		if ( gameMode is null )
		{
			ActivePath = null;
			ActiveIdent = null;
			return;
		}

		ActivePath = GetPrefabPath( gameMode );
		ActiveIdent = gameMode.Ident;
	}

	/// <summary>
	/// Stores the hardcore setting to apply when the next scene loads.
	/// </summary>
	public static void SetHardcore( bool hardcore )
	{
		ActiveHardcore = hardcore;
	}


	[Property]
	public string Title { get; set; }

	[Property]
	public string Description { get; set; }

	[Property]
	public string Ident { get; set; } = "gamemode";

	/// <summary>
	/// The title to show. Hardcore is the only ruleset while Core modes are off, so it isn't marked "HC ".
	/// </summary>
	public string DisplayTitle => Title;
	// Put back when Core modes return:
	// public string DisplayTitle => Hardcore ? $"HC {Title}" : Title;

	private StateMachineComponent _stateMachine;

	public StateMachineComponent StateMachine => _stateMachine ??= GetComponentInChildren<StateMachineComponent>();

	//private TimeSince _sinceLastSoundHandleLog;

	protected override void OnAwake()
	{
		if ( Networking.IsHost )
		{
			// Only stay enabled if host chose this game mode

			if ( !IsSelectedGameMode() && (!string.IsNullOrWhiteSpace( ActivePath ) || !string.IsNullOrWhiteSpace( ActiveIdent )) )
			{
				EnsureSelectedGameModeExists();
				GameObject.Enabled = false;
				return;
			}

			// Fallback for testing in editor - just use first active game mode

			if ( Instance is { IsValid: true, Active: true, Scene: { } scene } && scene == Scene )
			{
				Log.Info( $"A GameMode is already active, disabling {GameObject.GetScenePath()}" );
				GameObject.Enabled = false;
				return;
			}
		}

		base.OnAwake();
	}

	private bool IsSelectedGameMode()
	{
		if ( !string.IsNullOrWhiteSpace( ActiveIdent ) &&
		     ActiveIdent.Equals( Ident, StringComparison.OrdinalIgnoreCase ) )
		{
			return true;
		}

		if ( string.IsNullOrWhiteSpace( ActivePath ) )
			return false;

		var prefabPath = GetPrefabPath( this );
		return !string.IsNullOrWhiteSpace( prefabPath ) &&
		       ActivePath.Equals( prefabPath, StringComparison.OrdinalIgnoreCase );
	}

	private void EnsureSelectedGameModeExists()
	{
		if ( string.IsNullOrWhiteSpace( ActivePath ) )
			return;

		if ( Scene.GetAllComponents<GameMode>().Any( x => x.IsValid() && x != this && x.IsSelectedGameMode() ) )
			return;

		var gameModeObject = GameObject.Clone( ActivePath, new CloneConfig
		{
			Name = ActiveIdent ?? "GameMode",
			StartEnabled = true,
			Transform = global::Transform.Zero
		} );

		if ( Networking.IsActive && gameModeObject.IsValid() )
		{
			gameModeObject.NetworkSpawn( true, null );
		}
	}

	protected override void OnStart()
	{
		if ( Networking.IsHost )
		{
			Hardcore = ActiveHardcore;
			InitializeRankedMatch();
			GameObject.Components.GetOrCreate<ScorestreakManager>();
		}

		Scene.Dispatch( new GamemodeInitializedEvent( Title ) );

		base.OnStart();

		GameUtils.LogPlayers();
	}

	protected override void OnUpdate()
	{
		base.OnUpdate();

		//if ( _sinceLastSoundHandleLog > 5f )
		//{
		//	_sinceLastSoundHandleLog = 0f;

		//	var list = new List<SoundHandle>();
		//	SoundHandle.GetActive( list );

		//	var mostCommon = list
		//		.GroupBy( x => x.Name )
		//		.Select( x => (Name: x.Key, Count: x.Count()) )
		//		.OrderByDescending( x => x.Count )
		//		.FirstOrDefault();

		//	Log.Info( $"Active sound handle count: {list.Count}, most common: {mostCommon.Name} ({mostCommon.Count})" );
		//}
	}

	void INetworkListener.OnBecameHost( Connection previousHost )
	{
		Log.Info( "We became the host, taking over the game loop..." );

		GameUtils.LogPlayers();
	}

	private StateComponent _prevState;
	private readonly Dictionary<Type, Component> _componentCache = new();

	/// <summary>
	/// Gets the given component from within the game mode's object hierarchy, or null if not found / enabled.
	/// </summary>
	public T Get<T>( bool required = false )
		where T : class
	{
		if ( !StateMachine.IsValid() )
			return null;

		if ( _prevState != StateMachine.CurrentState )
		{
			_prevState = StateMachine.CurrentState;
			_componentCache.Clear();
		}

		if ( !_componentCache.TryGetValue( typeof( T ), out var component ) || component is { IsValid: false } || component is { Active: false } )
		{
			component = GetComponentInChildren<T>() as Component;
			_componentCache[typeof( T )] = component;
		}

		if ( required && component is not T )
		{
			throw new Exception( $"Expected a {typeof( T ).Name} to be active in the {nameof( GameMode )}!" );
		}

		return component as T;
	}
}
