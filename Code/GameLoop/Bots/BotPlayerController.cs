using System.Text.Json.Serialization;
using Tec;

namespace Facepunch;

/// <summary>
/// The bot for players
/// </summary>
public class BotPlayerController : Component, IBotController
{
	[Property]
	public NavMeshAgent MeshAgent { get; set; }

	public PlayerPawn Player { get; set; }



	protected override void OnAwake()
	{
		Player = GetComponentInParent<PlayerPawn>( true );
		MeshAgent = GetOrAddComponent<NavMeshAgent>();
		ConfigureMeshAgent();

		_behaviors = GetComponents<IBotBehavior>( true ).ToArray();
		foreach ( var behavior in _behaviors )
		{
			behavior.Initialize( this );
		}

		Enabled = false;
	}

	private void ConfigureMeshAgent()
	{
		if ( !MeshAgent.IsValid() )
			return;

		// We want to handle this ourselves
		MeshAgent.UpdateRotation = false;
		MeshAgent.UpdatePosition = false;
		MeshAgent.Radius = 48f;
		MeshAgent.Height = 64f;
	}

	private bool EnsureReady()
	{
		if ( !Player.IsValid() )
		{
			Player = GetComponentInParent<PlayerPawn>( true );
		}

		if ( !Player.IsValid() )
		{
			_currentBehavior = null;
			return false;
		}

		if ( !MeshAgent.IsValid() )
		{
			MeshAgent = GetOrAddComponent<NavMeshAgent>();
			ConfigureMeshAgent();
		}

		return MeshAgent.IsValid();
	}

	private IBotBehavior _currentBehavior;
	private IBotBehavior[] _behaviors;
	private BotContext _frameContext;
	private readonly UpdatePerceptionNode _perceptionNode = new();

	private TimeSince _timeSincePerception = 0;
	private const float _perceptionInterval = 0.5f;

	[Property, JsonIgnore, ReadOnly]
	public BotContext Context => _frameContext;

	[Property]
	public bool ShowBehaviorDebug { get; set; } = false;

	private IReadOnlyList<IBotBehavior> GetBehaviors()
	{
		if ( _behaviors is not { Length: > 0 } )
		{
			_behaviors = GetComponents<IBotBehavior>( true ).ToArray();
			foreach ( var behavior in _behaviors )
			{
				behavior.Initialize( this );
			}
		}

		return _behaviors;
	}

	public bool testBool = false;

	internal void UpdateBehaviors()
	{
		using var _ = Sandbox.Diagnostics.Performance.Scope( "HC1::UpdateBehaviors" );

		// Build or reuse a context for this frame
		if ( _frameContext == null || _frameContext.Controller != this )
		{
			testBool  = true;
			_frameContext = new BotContext( this );
		}

		// Run perception only if interval has passed
		if ( _timeSincePerception > _perceptionInterval )
		{
			_timeSincePerception = 0;
			_perceptionNode.Evaluate( _frameContext );
		}

		var topBehavior = default( IBotBehavior );
		var topScore = 0f;
		List<(IBotBehavior Behavior, float Score)> scored = null;

		foreach ( var behavior in GetBehaviors() )
		{
			var score = behavior.Score( _frameContext );
			if ( ShowBehaviorDebug )
			{
				scored ??= [];
				scored.Add( (behavior, score) );
			}

			if ( score > topScore )
			{
				topBehavior = behavior;
				topScore = score;
			}
		}

		if ( ShowBehaviorDebug && scored is not null )
		{
			PrintScoredBehaviors( scored.OrderByDescending( x => x.Score ).ToList() );
		}

		if ( topBehavior is null || topScore <= 0f )
		{
			_currentBehavior = null;
			return;
		}

		// If a different behavior is running and a higher-scoring one appears, switch
		if ( _currentBehavior != null && _currentBehavior != topBehavior )
		{
			var currentScore = _currentBehavior.Score( _frameContext );
			if ( topScore > currentScore )
			{
				_currentBehavior = topBehavior;
				_currentBehavior.Initialize(this);
			}
		}

		// If no current behavior, pick the top-scoring one
		if ( _currentBehavior == null )
		{
			_currentBehavior = topBehavior;
		}

		// --- Tick the chosen behavior using the same context ---
		if ( _currentBehavior != null )
		{
			var result = _currentBehavior.Update( _frameContext );
			if ( result != NodeResult.Running && result != NodeResult.Success )
			{
				_currentBehavior = null;
			}
		}
	}


	/// <summary>
	/// Sometimes we need to synchronize the NavMeshAgent with the physics system.
	/// </summary>
	protected void SyncNavAgentWithPhysics()
	{
		if ( !EnsureReady() )
			return;

		MeshAgent.MaxSpeed = Player.GetWishSpeed();
		Player.WishVelocity = MeshAgent.WishVelocity;

		// Handle desync between agent and physics
		if ( WorldPosition.WithZ( 0 ).DistanceSquared( MeshAgent.AgentPosition.WithZ( 0 ) ) > MeshAgent.Radius * MeshAgent.Radius )
		{
			MeshAgent.SetAgentPosition( WorldPosition );
		}
		if ( MathF.Abs( WorldPosition.z - MeshAgent.AgentPosition.z ) > MeshAgent.Height * MeshAgent.Height )
		{
			MeshAgent.SetAgentPosition( WorldPosition );
		}
	}

	void IBotController.OnControl( BotController bot )
	{
		if ( !EnsureReady() )
			return;

		if ( Player.HealthComponent.IsValid() && Player.HealthComponent.State != LifeState.Alive )
		{
			_currentBehavior = null;
			return;
		}

		SyncNavAgentWithPhysics();
		UpdateBehaviors();
	}

	/// <summary>
	/// Useful to debug one bot behaviors.
	/// </summary>
	/// <param name="scored"></param>
	private void PrintScoredBehaviors( List<(IBotBehavior Behavior, float Score)> scored)
	{
		float y = 20;
		
		foreach (var s in scored)
		{
			DebugOverlay.ScreenText(
				new Vector2( 900, y ),
				$"{s.Behavior.ToString()}:  {s.Score}",
				14,
				TextFlag.Left,
				Color.Green,
				0.1f
			);
			y += 20f;
		}
	}
}
