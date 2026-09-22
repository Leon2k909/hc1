namespace Facepunch.Gunsmith;

/// <summary>A world-depth-tested beam and a surface hit dot, shared by held laser modules.</summary>
public sealed class GunsmithLaserBeam : Component
{
	public Color BeamColor { get; set; } = new Color( .08f, 1f, .12f );
	public float BeamWidth { get; set; } = .035f;
	public float Range { get; set; } = 8192f;
	public Vector3 Start { get; private set; }
	public Vector3 End { get; private set; }
	public bool HasHit { get; private set; }
	public bool IsVisible => core.IsValid() && core.RenderingEnabled;
	private SceneLineObject core, glow, dot;
	private Material material;

	public void TraceBeam( Vector3 start, Vector3 direction, GameObject ignore )
	{
		if ( Application.IsDedicatedServer || direction.LengthSquared < .001f ) { Hide(); return; }
		var trace = Scene.Trace.Ray( start, start + direction.Normal * Range ).UseHitboxes().WithoutTags( "trigger" );
		if ( ignore.IsValid() ) trace = trace.IgnoreGameObjectHierarchy( ignore );
		var hit = trace.Run();
		Start = start; End = hit.EndPosition; HasHit = hit.Hit && !hit.StartedSolid;
		if ( hit.StartedSolid || Start.Distance( End ) < .05f ) { Hide(); return; }
		if ( material is null )
		{
			material = Material.Load( "materials/default/default_line.vmat" ).CreateCopy();
			material.Set( "Color", Texture.White );
		}
		core ??= CreateLine(); glow ??= CreateLine(); dot ??= CreateLine();
		// Fade in from the emitter: a real laser is barely visible side-on, so the beam should read as a faint haze, not a solid bar.
		DrawLine( glow, Start, End, BeamColor.WithAlpha( 0 ), BeamColor.WithAlpha( .05f ), BeamWidth * 3f );
		DrawLine( core, Start, End, (BeamColor * 2f).WithAlpha( .02f ), (BeamColor * 2f).WithAlpha( .35f ), BeamWidth * .6f );
		dot.RenderingEnabled = HasHit;
		if ( HasHit )
		{
			var position = End + hit.Normal * .025f;
			var tangent = Vector3.Cross( hit.Normal, Vector3.Up );
			if ( tangent.LengthSquared < .01f ) tangent = Vector3.Cross( hit.Normal, Vector3.Right );
			// Rounded caps make a small disk resting on the hit surface.
			DrawLine( dot, position - tangent.Normal * .015f, position + tangent.Normal * .015f, (BeamColor * 3f).WithAlpha( 1 ), .2f );
		}
	}

	private SceneLineObject CreateLine()
	{
		var line = new SceneLineObject( Scene.SceneWorld )
		{
			Material = material, Opaque = false, Lighting = false,
			StartCap = SceneLineObject.CapStyle.Rounded, EndCap = SceneLineObject.CapStyle.Rounded,
			RenderLayer = SceneRenderLayer.Default
		};
		line.Flags.CastShadows = false;
		line.Attributes.SetCombo( "D_BLEND", 1 );
		return line;
	}

	private static void DrawLine( SceneLineObject line, Vector3 start, Vector3 end, Color color, float width ) => DrawLine( line, start, end, color, color, width );

	private static void DrawLine( SceneLineObject line, Vector3 start, Vector3 end, Color startColor, Color endColor, float width )
	{
		line.RenderingEnabled = true;
		line.StartLine(); line.AddLinePoint( start, startColor, width ); line.AddLinePoint( end, endColor, width ); line.EndLine();
	}

	public void Hide()
	{
		HasHit = false;
		if ( core.IsValid() ) core.RenderingEnabled = false;
		if ( glow.IsValid() ) glow.RenderingEnabled = false;
		if ( dot.IsValid() ) dot.RenderingEnabled = false;
	}
	protected override void OnDisabled() => Release();
	protected override void OnDestroy() => Release();
	private void Release()
	{
		core?.Delete(); glow?.Delete(); dot?.Delete();
		core = glow = dot = null; HasHit = false;
	}
}
