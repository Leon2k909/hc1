namespace Facepunch;

/// <summary>Camera optics and conservative rotated bounds used by recon flight and hand-launch clearance.</summary>
public static class ReconFlightMath
{
	/// <summary>The release is relative to the current eye height, including crouch and prone.</summary>
	public static Vector3 HandReleasePoint( Vector3 eye, Rotation aim, float distance ) =>
		eye - aim.Up * 10f + aim.Right * 9f + aim.Forward * distance;

	public static float FieldOfView( float zoom, float widest ) => 2f * MathF.Atan(
		MathF.Tan( Math.Clamp( widest, 1f, 179f ) * MathF.PI / 360f ) / MathF.Max( zoom, 1f ) ) * 180f / MathF.PI;

	/// <summary>The axis-aligned trace box enclosing all eight corners in the aircraft's current orientation.</summary>
	public static BBox RotatedHull( BBox hull, Rotation rotation )
	{
		var first = rotation * hull.Mins;
		var mins = first;
		var maxs = first;
		for ( var i = 1; i < 8; i++ )
		{
			var corner = rotation * new Vector3( (i & 1) == 0 ? hull.Mins.x : hull.Maxs.x,
				(i & 2) == 0 ? hull.Mins.y : hull.Maxs.y, (i & 4) == 0 ? hull.Mins.z : hull.Maxs.z );
			mins = new Vector3( MathF.Min( mins.x, corner.x ), MathF.Min( mins.y, corner.y ), MathF.Min( mins.z, corner.z ) );
			maxs = new Vector3( MathF.Max( maxs.x, corner.x ), MathF.Max( maxs.y, corner.y ), MathF.Max( maxs.z, corner.z ) );
		}
		return new BBox( mins, maxs );
	}
}
