using Facepunch.UI;
using Sandbox.Rendering;

namespace Facepunch;

/// <summary>
/// Draws the hitmarker (Settings → Crosshair: its style, colour, size, thickness, outline and time) with the main camera's
/// HUD painter, round exactly the point the crosshair is drawn round (<see cref="Crosshair"/>): the screen's centre,
/// to the sub-pixel. It used to be a UI panel in <c>CrosshairHud</c>, whose layout snaps to whole pixels, so with an
/// odd screen width (the editor's game view) it sat half a pixel or more off the crosshair's lines. The X and the
/// diamond are lines, as the crosshair's arms are; the ring and the dot go through the same rect call as the
/// crosshair's own dot. Run by <see cref="CrosshairInputSystem"/> every frame, so it shows in every scene with a camera
/// (a match, the firing range, and the settings page's Preview Hit), not only where a HUD with the panel is.
/// </summary>
public static class HitmarkerPainter
{
	const float Diagonal = 0.70710678f;

	public static void Draw( Scene scene )
	{
		var cfg = CrosshairManager.Config;
		if ( CrosshairManager.HitFlash <= 0f || cfg.HitDuration <= 0 || cfg.HitStyle is null or "none" )
			return;

		// Hidden where the HUD panel was: with the HUD off, under a team's win banner and on the recon drone's feed.
		if ( !MainHUD.IsHudEnabled || Toast.IsWinShowing )
			return;

		var viewer = Client.Viewer;
		if ( viewer.IsValid() && ReconOctocopter.IsPiloting( viewer.PlayerPawn ) )
			return;

		var camera = scene?.Camera;
		if ( !camera.IsValid() )
			return;

		// The panel's CSS animation (hm-fade, ease-out): in from 0.6x and clear over the first 30%, then out to 1.2x.
		var progress = (1f - CrosshairManager.HitFlash / cfg.HitDuration).Clamp( 0f, 1f );
		float opacity, grow;
		if ( progress < 0.3f )
		{
			var t = EaseOut( progress / 0.3f );
			opacity = t;
			grow = 0.6f + 0.4f * t;
		}
		else
		{
			var t = EaseOut( (progress - 0.3f) / 0.7f );
			opacity = 1f - t;
			grow = 1f + 0.2f * t;
		}

		if ( opacity <= 0f )
			return;

		// The crosshair's centre and scale (Crosshair.OnUpdate), so the two line up.
		Paint( camera.Hud, Screen.Size * 0.5f, Screen.Height / 1080f * grow, opacity, cfg );
	}

	/// <summary>
	/// Draws the marker in <paramref name="cfg"/>'s style round <paramref name="center"/>, at <paramref name="scale"/>
	/// screen pixels to the setting's pixel, with <paramref name="opacity"/> times its colours' alpha.
	/// </summary>
	public static void Paint( HudPainter hud, Vector2 center, float scale, float opacity, CrosshairConfig cfg )
	{
		var color = (Color.TryParse( cfg.HitColor ?? "#ffffff", out var parsed ) ? parsed : Color.White)
			.WithAlpha( cfg.HitAlpha * opacity );
		var outline = Color.Black.WithAlpha( cfg.HitOutlineAlpha * opacity );
		var edge = cfg.HitOutline ? cfg.HitOutlineThickness * scale : 0f;
		var size = cfg.HitSize * scale;
		var thickness = cfg.HitThickness * scale;

		hud.SetBlendMode( BlendMode.Normal );

		switch ( cfg.HitStyle )
		{
			case "x":
				// Two bars of the marker's size, crossed at 45 degrees. Both outlines go under both bars.
				var a = new Vector2( Diagonal, Diagonal );
				var b = new Vector2( Diagonal, -Diagonal );
				if ( edge > 0f )
				{
					Bar( hud, center, a, size + edge * 2f, thickness + edge * 2f, outline );
					Bar( hud, center, b, size + edge * 2f, thickness + edge * 2f, outline );
				}
				Bar( hud, center, a, size, thickness, color );
				Bar( hud, center, b, size, thickness, color );
				break;

			case "diamond":
				// A square half the marker's size, turned 45 degrees: one bar as wide as it is long, along the diagonal.
				var side = size * 0.5f;
				var axis = new Vector2( Diagonal, Diagonal );
				if ( edge > 0f )
					Bar( hud, center, axis, side + edge * 2f, side + edge * 2f, outline );
				Bar( hud, center, axis, side, side, color );
				break;

			case "ring":
				if ( edge > 0f )
					Disc( hud, center, size + edge * 2f, thickness + edge * 2f, Color.Transparent, outline );
				Disc( hud, center, size, thickness, Color.Transparent, color );
				break;

			case "dot":
				var dot = size / 3f;
				if ( edge > 0f )
					Disc( hud, center, dot + edge * 2f, 0f, outline, default );
				Disc( hud, center, dot, 0f, color, default );
				break;
		}
	}

	static float EaseOut( float t ) => 1f - (1f - t) * (1f - t);

	static void Bar( HudPainter hud, Vector2 center, Vector2 direction, float length, float width, Color color )
	{
		var half = direction * (length * 0.5f);
		hud.DrawLine( center - half, center + half, width, color );
	}

	/// <summary> A filled disc, or a ring with a <paramref name="border"/> and no fill. </summary>
	static void Disc( HudPainter hud, Vector2 center, float diameter, float border, Color fill, Color borderColor )
	{
		var size = new Vector2( Aligned( center.x, diameter ), Aligned( center.y, diameter ) );
		hud.DrawRect( new Rect( center - size * 0.5f, size ), fill, new Vector4( size.x + size.y ), new Vector4( border ), borderColor );
	}

	/// <summary>
	/// DrawRect snaps its rect to whole pixels, which moved a disc half a pixel off a centre between pixels (an odd
	/// screen width or height). A whole number of pixels across, odd round a centre between pixels and even round one on
	/// a pixel's edge, puts the corner on a whole pixel already, so the snap leaves it on the exact centre.
	/// </summary>
	static float Aligned( float center, float size )
	{
		var pixels = MathF.Max( 1f, MathF.Round( size ) );
		return ((int)MathF.Round( center * 2f ) - (int)pixels) % 2 == 0 ? pixels : pixels + 1f;
	}
}
