namespace Facepunch.UI;

/// <summary>Opaque scope shadow, clipped to the lens and drawn over its reticle and markers.</summary>
public sealed class ScopeShadow : Panel
{
	public override void OnDraw( Painter painter ) => Paint( painter, painter.Bounds, OpticZoom.EyeBox );

	public static void Paint( Painter painter, Rect bounds, ScopeEyeBox eyeBox )
	{
		var radius = MathF.Min( bounds.Width, bounds.Height ) * 0.5f;
		if ( radius <= 0f ) return;
		var centre = bounds.Center + eyeBox.Offset * radius;
		var aperture = MathF.Max( eyeBox.Radius * radius, 1f );
		// The black outside the displaced clear aperture stays opaque. It never exposes the unzoomed world.
		painter.Fill = Fill.RadialGradient( centre, centre + new Vector2( aperture, 0f ),
			[
				new( 0f, Color.Black.WithAlpha( eyeBox.Blackout ) ),
				new( 0.85f, Color.Black.WithAlpha( eyeBox.Blackout ) ),
				new( 0.93f, Color.Black.WithAlpha( 0.35f + eyeBox.Blackout * 0.65f ) ),
				new( 1f, Color.Black )
			] );
		painter.Rect( bounds );
	}
}
