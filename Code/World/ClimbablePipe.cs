namespace Facepunch;

/// <summary>A vertical pipe that can be grabbed with Use, including pipes baked into a map's decorative model.</summary>
[Title( "Climbable Pipe" ), Group( "Traversal" )]
public sealed class ClimbablePipe : Component, IUse
{
	[Property, Range( 80f, 1200f )] public float Height { get; set; } = 350f;
	[Property, Range( 2f, 32f )] public float Radius { get; set; } = 15f;
	[Property, Range( 30f, 160f )] public float ClimbSpeed { get; set; } = 90f;
	[Property] public float CollarScale { get; set; } = 1.32f;

	public Vector3 Bottom => WorldPosition;
	public Vector3 Top => WorldTransform.PointToWorld( Vector3.Up * Height );
	public float WorldRadius => Radius * MathF.Max( MathF.Abs( WorldScale.x ), MathF.Abs( WorldScale.y ) );
	public bool CanClimb => Enabled && GameObject.Active && Height >= 80f && Radius >= 2f && Radius <= 32f
		&& WorldRotation.Up.Dot( Vector3.Up ) > 0.995f && Top.z >= Bottom.z + 80f;

	protected override void OnStart()
	{
		GameObject.Tags.Add( "climbable_pipe" );
		// The map's visual pipe may have no hull. Keep its collision on the same object as its use action.
		var collider = Components.GetOrCreate<CapsuleCollider>();
		collider.Start = Vector3.Up * Radius;
		collider.End = Vector3.Up * (Height - Radius);
		collider.Radius = Radius;
		collider.Static = true;
		collider.IsTrigger = false;
	}

	public UseResult CanUse( PlayerPawn player ) => player.IsValid() && CanClimb && player.CanStartPipeClimb( this );
	public void OnUse( PlayerPawn player ) => player?.StartPipeClimb( this );
	public GrabAction GetGrabAction() => GrabAction.SweepDown;
}
