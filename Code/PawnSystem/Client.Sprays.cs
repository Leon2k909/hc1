namespace Facepunch;

public partial class Client
{
	private TimeSince _sinceSpray = 100f;
	private RealTimeSince _sinceSprayRequest = 100f;
	private GameObject _activeSpray;

	[Rpc.Host]
	public void RequestSpray( string id, Vector3 direction )
	{
		if ( !Networking.IsHost || IsBot || Connection is null
			|| (Rpc.Caller != Connection && !(Rpc.Caller is null && IsLocalPlayer)) || _sinceSprayRequest < 0.25f ) return;
		_sinceSprayRequest = 0f;
		var pawn = PlayerPawn;
		if ( !pawn.IsValid() || pawn.Scene != Scene || !SprayRules.Finite( direction.x, direction.y, direction.z ) ) return;
		var blocked = pawn.IsFrozen || pawn.IsNoclipping || pawn.IsPilotingDrone || pawn.IsMantling || pawn.IsPipeClimbing;
		if ( CosmeticCatalog.FindSpray( id ) is not null && _sinceSpray < SprayRules.Cooldown )
		{
			SprayStatus( "Spray is cooling down." );
			return;
		}
		if ( !SprayRules.CanPlace( id, _sinceSpray, pawn.HealthComponent?.State == LifeState.Alive, blocked ) ) return;
		if ( direction.Length < 0.9f || direction.Length > 1.1f ) return;
		direction = direction.Normal;
		if ( direction.Dot( pawn.EyeAngles.Forward ) < 0.75f ) return;
		// The host derives the eye and hit; a client cannot supply a point beyond cover or the allowed reach.
		var origin = pawn.SprayEyePosition;
		var hit = Scene.Trace.Ray( origin, origin + direction * SprayRules.Reach )
			.IgnoreGameObjectHierarchy( pawn.GameObject ).WithoutTags( "trigger", "playerclip", "movement" ).Run();
		if ( !hit.Hit || hit.StartedSolid || hit.Normal.Length < 0.9f || hit.Surface?.ResourceName is "sky" or "water" )
		{
			SprayStatus( "Aim at a nearby solid surface." );
			return;
		}
		var target = hit.GameObject;
		if ( target.IsValid() && (target.GetComponentInParent<Rigidbody>().IsValid()
			|| target.GetComponentInParent<HealthComponent>().IsValid() || target.GetComponentInParent<ZombieAI>().IsValid()
			|| target.Tags.Has( "player" ) || target.Tags.Has( "enemy" ) || target.Tags.Has( "pickup" )) ) return;
		if ( Scene.GetAllComponents<SprayMark>().Count() >= SprayRules.SceneLimit && !_activeSpray.IsValid() ) return;
		if ( _activeSpray.IsValid() ) _activeSpray.Destroy();
		var mark = new GameObject( true, "Player spray" );
		mark.Flags |= GameObjectFlags.NotSaved;
		mark.WorldPosition = hit.HitPosition + hit.Normal * 0.1f;
		var up = MathF.Abs( hit.Normal.Dot( Vector3.Up ) ) > 0.95f ? pawn.EyeAngles.WithPitch( 0f ).Forward : Vector3.Up;
		mark.WorldRotation = Rotation.LookAt( -hit.Normal, up );
		mark.Components.Create<SprayMark>().SprayId = id;
		mark.Components.Create<DestroyBetweenRounds>();
		mark.NetworkSpawn();
		_activeSpray = mark;
		_sinceSpray = 0f;
	}

	[Rpc.Owner]
	private void SprayStatus( string message ) => UI.Toast.Instance?.Show( message, duration: 2f );
}
