namespace Facepunch;

/// <summary>
/// Finds a random navigable point within specified radius using navmesh
/// </summary>
public class GetRandomPointNode : BaseBehaviorNode
{
	private bool _hasRun;

	protected override NodeResult OnEvaluate( BotContext context )
	{
		// Only pick a random point once per sequence run
		if ( _hasRun )
			return NodeResult.Success;

		var randomPoint = Game.ActiveScene.NavMesh.GetRandomPoint();
		if ( !randomPoint.HasValue )
			return NodeResult.Failure;
		
		context.SetData( AIConst.TARGET_POS, randomPoint.Value );
		_hasRun = true;
		return NodeResult.Success;
	}

	public override void Reset()
	{
		_hasRun = false;
	}
}
