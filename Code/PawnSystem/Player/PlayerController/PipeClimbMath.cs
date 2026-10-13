namespace Facepunch;

/// <summary>Geometry shared by pipe mounting, climbing, and its offline checks.</summary>
public static class PipeClimbMath
{
	public const float HandHeight = 56f;
	public const float Clearance = 3f;

	public static float Standoff( Vector3 outward, BBox body, float radius )
	{
		var x = MathF.Max( MathF.Abs( body.Mins.x ), MathF.Abs( body.Maxs.x ) );
		var y = MathF.Max( MathF.Abs( body.Mins.y ), MathF.Abs( body.Maxs.y ) );
		return radius + MathF.Abs( outward.x ) * x + MathF.Abs( outward.y ) * y + Clearance;
	}

	public static float StepHeight( float height, float bottom, float top, float input, float speed, float delta ) =>
		(height + input.Clamp( -1f, 1f ) * speed * delta.Clamp( 0f, 0.05f )).Clamp( bottom - HandHeight + 4f, top - HandHeight - 8f );

	public static Vector3 OutwardAt( Vector3 outward, float input, float delta ) =>
		(Rotation.FromYaw( -input.Clamp( -1f, 1f ) * 70f * delta.Clamp( 0f, 0.05f ) ) * outward.WithZ( 0f ).Normal).Normal;

	public static Vector3 JumpVelocity( Vector3 outward ) => outward.WithZ( 0f ).Normal * 150f + Vector3.Up * 180f;
}
