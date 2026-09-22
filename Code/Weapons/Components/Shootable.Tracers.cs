namespace Facepunch;

public partial class Shootable
{
	private void PlayTracer( Vector3 endPosition, Vector3 fallbackStart )
	{
		if ( Equipment.IsValid() && Equipment.UsesTracerRounds )
			DoTracerEffects( endPosition, fallbackStart );
	}

	[Rpc.Broadcast( NetFlags.Unreliable )]
	private void DoTracerEffects( Vector3 endPosition, Vector3 fallbackStart )
	{
		if ( Application.IsDedicatedServer || !Equipment.IsValid() ) return;
		// This RPC is emitted only by a shot with tracer rounds. Do not consult the observer's cookies.
		var muzzle = Effector.IsValid() ? Effector.DischargeMuzzle : null;
		var start = muzzle.IsValid() ? muzzle.WorldPosition : fallbackStart;
		var direction = endPosition - start;
		if ( direction.LengthSquared < 1f ) return;
		var prefab = GameObject.GetPrefab( "weapons/common/effects/tracer_9mm.prefab" );
		if ( !prefab.IsValid() ) return;
		var effect = prefab.Clone( new CloneConfig
		{
			Name = "Tracer round",
			Transform = new Transform( start, Rotation.LookAt( direction ) ),
			StartEnabled = true
		} );
		effect.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		var tracer = effect.Components.Get<Tracer>( FindMode.EverythingInSelfAndDescendants );
		if ( tracer.IsValid() ) tracer.EndPoint = endPosition;
	}
}
