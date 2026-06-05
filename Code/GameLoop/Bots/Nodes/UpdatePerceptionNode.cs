using Tec.AI;

namespace Facepunch;

public class UpdatePerceptionNode : BaseBehaviorNode
{
	private readonly float _range;
	private const string ENEMIES_KEY = "visible_enemies";
	private const string TEAMMATES_KEY = "visible_teammates";
	private const string ITEMS_KEY = "visible_items";
	private readonly List<Pawn> _enemies = [];
	private readonly List<Pawn> _teammates = [];
	private readonly List<Component> _items = [];
	private readonly List<Vector3> _sounds = [];

	public UpdatePerceptionNode( float range = 2048f )
	{
		_range = range;
	}

	protected override NodeResult OnEvaluate( BotContext context )
	{
		var pawn = context.Pawn;
		var origin = pawn.WorldPosition;
		var rangeSqr = _range * _range;

		_enemies.Clear();
		_teammates.Clear();
		_items.Clear();
		_sounds.Clear();

		// Scan all pawns
		foreach ( var otherPawn in pawn.Scene.GetAll<PlayerPawn>() )
		{
			if ( otherPawn == pawn )
				continue;

			if ( !otherPawn.HealthComponent.IsValid() || otherPawn.HealthComponent.Health <= 0 )
				continue;

			if ( otherPawn.WorldPosition.DistanceSquared( origin ) > rangeSqr )
				continue;

			if ( !IsInLineOfSight( pawn, otherPawn ) )
				continue;

			if ( otherPawn.Team != pawn.Team )
				_enemies.Add( otherPawn );
			else
				_teammates.Add( otherPawn );
		}
		
		// Scan all dropped equipment (or other items)
		foreach ( var pickup in pawn.Scene.GetAll<DroppedEquipment>() )
		{
			if ( pickup.WorldPosition.DistanceSquared( origin ) > rangeSqr )
				continue;

			// optional LOS for items? (if you want)
			// if ( !IsInLineOfSight( pawn, pickup ) ) continue;

			_items.Add( pickup );
		}

		context.SetData( ENEMIES_KEY, _enemies );
		context.SetData( TEAMMATES_KEY, _teammates );
		context.SetData( ITEMS_KEY, _items );
		
		
		// Hearing ///////////////////////////////////////////////////////////////////////////////////////
		
		var audioStims = AudioAIManager.Instance.GetAudioStims();

		foreach ( var audioStim in audioStims )
		{
			if ( audioStim.Faction == pawn.Team.ToFaction() )
				continue;
			
			var distSqr = audioStim.Position.DistanceSquared( pawn.Head.WorldPosition );
			if ( distSqr < audioStim.Range * audioStim.Range )
			{
				_sounds.Add( audioStim.Position );
			}
		}
		
		context.SetData( AIConst.ALERT_SOUNDS_KEY, _sounds );

		//////////////////////////////////////////////////////////////////////////////////////////////////
		
		return (_enemies.Count > 0 || _teammates.Count > 0 || _items.Count > 0 || _sounds.Count > 0)
			? NodeResult.Success
			: NodeResult.Failure;
	}

	private bool IsInLineOfSight( Pawn from, Component obj )
	{
		var targetPos = obj is Pawn p ? p.EyePosition : obj.WorldPosition;

		var trace = from.Scene.Trace.Ray( from.EyePosition, targetPos + Vector3.Down * 32f )
			.IgnoreGameObjectHierarchy( from.GameObject.Root )
			.Run();

		return trace.Hit && trace.GameObject.Root == obj.GameObject.Root;
	}
}
