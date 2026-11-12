using System;
using Sandbox;

namespace Facepunch;

/// <summary>
/// A capture zone's ring, laid on the ground round its centre. The ground is traced once per position and radius
/// (a Hardpoint zone moves; a Domination flag never does), not every frame: only the colour changes per frame.
/// </summary>
public sealed class GroundRing
{
	private const int Segments = 36;
	private readonly Vector3[] _points = new Vector3[Segments + 1];
	private Vector3 _center;
	private float _radius;
	private bool _traced;

	public void Draw( Component owner, Vector3 center, float radius, Color color )
	{
		// Nobody sees it on a dedicated server
		if ( Application.IsHeadless )
			return;

		if ( !_traced || center != _center || radius != _radius )
			Trace( owner, center, radius );

		var overlay = owner.DebugOverlay;
		if ( overlay is null )
			return;

		for ( int i = 1; i <= Segments; i++ )
			overlay.Line( new Line( _points[i - 1], _points[i] ), color, 0f );
	}

	private void Trace( Component owner, Vector3 center, float radius )
	{
		for ( int i = 0; i <= Segments; i++ )
		{
			float angle = (i / (float)Segments) * MathF.PI * 2f;
			var point = center + new Vector3( MathF.Cos( angle ) * radius, MathF.Sin( angle ) * radius, 5f );

			// Conform to the ground
			var tr = owner.Scene.Trace.Ray( point + Vector3.Up * 50f, point + Vector3.Down * 100f )
				.IgnoreGameObjectHierarchy( owner.GameObject )
				.WithoutTags( "trigger", "playerclip", "movement" )
				.Run();

			_points[i] = tr.Hit ? tr.HitPosition + Vector3.Up * 2f : point;
		}

		_center = center;
		_radius = radius;
		_traced = true;
	}
}
