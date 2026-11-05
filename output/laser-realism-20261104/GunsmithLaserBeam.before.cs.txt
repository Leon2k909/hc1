namespace Facepunch.Gunsmith;

/// <summary>
/// A held visible aiming laser's spot and beam, each as bright as the real ones look (<see cref="LaserOptics"/>).
/// The spot is the beam's Gaussian patch of light on what it hits, bright enough indoors to bloom and faint on a sunlit
/// wall far off. The beam is only the light the air scatters toward the eye: in clean air, by day or in a lit room, none
/// that shows, and looking down your own beam you see its weak backscatter. Haze, mist, a smoke cloud, rain or the dark
/// bring it out, most of all looking toward the laser.
/// </summary>
public sealed class GunsmithLaserBeam : Component
{
	/// <summary> The laser's colour: its hue, and from it the wavelength (<see cref="LaserOptics.WavelengthOf"/>). </summary>
	public Color BeamColor { get; set; } = new Color( .08f, 1f, .12f );
	public float Range { get; set; } = 8192f;
	public Vector3 Start { get; private set; }
	public Vector3 End { get; private set; }
	public bool HasHit { get; private set; }
	/// <summary> Whether any of it is drawn: the beam, or the spot. </summary>
	public bool IsVisible => (beam.IsValid() && beam.RenderingEnabled) || (spot?.Any( x => x.IsValid() && x.RenderingEnabled ) ?? false);

	/// <summary> Output (W): Class 3R's 5 mW, the most a visible weapon aiming laser puts out. </summary>
	private const float Power = 0.005f;
	/// <summary> The beam's 1/e² diameter at the aperture (m). </summary>
	private const float Aperture = 0.003f;
	/// <summary> Full-angle divergence (rad): the 0.5 mrad weapon aiming lasers quote, a 15 mm spot at 25 m. </summary>
	private const float Divergence = 0.0005f;
	/// <summary> The beam's points: closer together near the emitter, where it changes fastest on screen. </summary>
	private const int BeamPoints = 16;
	/// <summary> Nothing narrower than this many pixels is drawn: thinner is spread wider and dimmer, keeping its light. </summary>
	private const float MinimumPixels = 1.25f;
	/// <summary> Under this contrast against what the eye is adapted to (1%, about the least a thin line shows), it isn't drawn. </summary>
	private const float VisibleContrast = 0.01f;
	/// <summary>
	/// The brightest the spot's core is drawn, in adapted greys: about where the tone curve still holds its colour. Past
	/// it a screen can't show more; the glare round it (<see cref="GlareLayers"/>) shows how bright it is, as in the eye.
	/// </summary>
	private const float CoreLimit = 8f;
	private const float OutdoorReach = 3000f;
	/// <summary>
	/// The engine drops a line point within 0.1 units of the one before (SceneLineObject.AddLinePoint), so a disc is drawn
	/// as a capsule at least this long, its light spread over the extra length.
	/// </summary>
	private const float MinimumSegment = 0.105f;

	/// <summary>
	/// A Gaussian spot as three discs added together: radii of 0.5, 1 and 1.5 times the 1/e² radius, each lit so the
	/// rings between them carry the light the profile puts there (39%, 47% and 12%), relative to the peak.
	/// </summary>
	private static readonly (float Radius, float Level)[] SpotLayers = { (0.5f, 0.471f), (1f, 0.264f), (1.5f, 0.0496f) };

	/// <summary>
	/// The glare a bright point casts in the eye, by the CIE's glare spread (veiling luminance 10·E/θ², E the lux it puts
	/// on the eye, θ in degrees), as discs added together: each disc's radius (degrees) and its luminance per lux, so the
	/// rings between carry that ring's average. Indoors a 5 mW spot glows ~0.2° round; at night far more.
	/// </summary>
	private static readonly (float Degrees, float Level)[] GlareLayers = { (0.08f, 1017f), (0.2f, 458f), (0.5f, 72.3f), (1.2f, 12.3f), (3f, 2.42f) };

	private static readonly string[] PassThrough = { "trigger", "playerclip", "movement", "glass", "particles" };
	private static readonly string[] SkyIgnore = { "trigger", "playerclip", "movement", "player", "ragdoll", "particles" };

	private SceneLineObject beam;
	// Made on first use: a hotload leaves new fields of a live component unset.
	private SceneLineObject[] spot, glare;
	private Material material;
	private LaserOptics.Medium medium;
	private float[] distances, extinction;
	private (Vector3 Position, float Level, float Radius)[] points;

	/// <param name="start">The emitter's aperture.</param>
	/// <param name="direction">Where the laser points: on a held gun, zeroed to its sights.</param>
	/// <param name="ignore">The holder, whose own body the beam leaves through.</param>
	/// <param name="viewer">The camera it's drawn for, else the scene's: brightness is relative to what that eye is adapted to.</param>
	public void TraceBeam( Vector3 start, Vector3 direction, GameObject ignore, CameraComponent viewer = null )
	{
		if ( !viewer.IsValid() ) viewer = Scene.Camera;
		if ( Application.IsDedicatedServer || Range <= 0f || direction.LengthSquared < .001f || !viewer.IsValid() ) { Hide(); return; }
		direction = direction.Normal;
		var hit = Trace( start, start + direction * Range, ignore );
		Start = start; End = hit.EndPosition; HasHit = hit.Hit && !hit.StartedSolid;
		if ( hit.StartedSolid || Start.Distance( End ) < .05f ) { Hide(); return; }

		var adapted = LaserOptics.Adapted( viewer );
		if ( adapted.Luminance <= 0f ) { Hide(); return; }
		EnsureObjects();
		medium.Gather( Scene );

		var wavelength = LaserOptics.WavelengthOf( BeamColor );
		var light = new Light( LaserOptics.Hue( BeamColor ), LaserOptics.LumensPerWatt( wavelength ),
			LaserOptics.MoleculeScattering( wavelength ), LaserOptics.AerosolScattering( wavelength ),
			adapted.EngineGrey / adapted.Luminance, adapted.EngineGrey );
		var pixel = 2f * MathF.Tan( viewer.FieldOfView.Clamp( 1f, 170f ).DegreeToRadian() * 0.5f ) / MathF.Max( Screen.Width, 1f );
		var eye = viewer.WorldPosition;
		var eyeScattering = medium.ParticlesAt( eye, Outdoors( eye ) ) + light.Aerosol + light.Molecules;

		var transmitted = DrawBeam( direction, eye, eyeScattering, pixel, light );
		if ( HasHit ) DrawSpot( direction, hit.Normal, transmitted, eye, eyeScattering, pixel, light );
		else HideSpot();
	}

	/// <param name="Hue">Linear colour at a luminance of 1.</param>
	/// <param name="Efficacy">Lumens per watt.</param>
	/// <param name="Molecules">The air's molecular scattering at this wavelength (1/m).</param>
	/// <param name="Aerosol">Clean air's aerosol scattering at this wavelength (1/m).</param>
	/// <param name="Scale">Renderer units per cd/m².</param>
	/// <param name="Grey">The adapted grey, in renderer units.</param>
	private readonly record struct Light( Vector3 Hue, float Efficacy, float Molecules, float Aerosol, float Scale, float Grey );

	/// <summary>
	/// Draws the light scattered out of the beam toward the eye, and returns the share of the laser's power that reaches
	/// its end. Each point's luminance is that scattered across the beam's width, over the width drawn:
	/// L = η·P·(βₚ·pₚ(Θ) + βₘ·pₘ(Θ)) / (sin ψ · W), with ψ the angle between the line of sight and the beam and Θ the
	/// angle the light turns through to reach the eye.
	/// </summary>
	private float DrawBeam( Vector3 direction, Vector3 eye, float eyeScattering, float pixel, in Light light )
	{
		var length = Start.Distance( End );
		var outdoorStart = medium.Rain > 0f ? Outdoors( Start ) : 0f;
		var outdoorEnd = medium.Rain > 0f ? Outdoors( End - direction * 8f ) : 0f;

		var brightest = 0f;
		var optical = 0f;
		for ( var i = 0; i < BeamPoints; i++ )
		{
			var t = i / (BeamPoints - 1f);
			distances[i] = length * t * t;
			var position = Start + direction * distances[i];
			var scattering = medium.ParticlesAt( position, MathX.Lerp( outdoorStart, outdoorEnd, t ) ) + light.Aerosol;
			if ( i > 0 ) optical += 0.5f * (extinction[i - 1] + scattering + light.Molecules) * (distances[i] - distances[i - 1]) / LaserOptics.UnitsPerMetre;
			extinction[i] = scattering + light.Molecules;

			var toEye = eye - position;
			var range = MathF.Max( toEye.Length, 0.5f );
			var cosTurn = Vector3.Dot( direction, toEye / range );
			var sinView = MathF.Sqrt( MathF.Max( 1f - cosTurn * cosTurn, 0f ) );
			var rangeMetres = range / LaserOptics.UnitsPerMetre;
			var width = MathF.Max( 2f * LaserOptics.BeamRadius( distances[i] / LaserOptics.UnitsPerMetre, Aperture, Divergence ),
				MinimumPixels * rangeMetres * pixel );
			var power = Power * MathF.Exp( -optical );
			var radiance = light.Efficacy * power
				* (scattering * LaserOptics.ParticlePhase( cosTurn ) + light.Molecules * LaserOptics.MoleculePhase( cosTurn ))
				/ (MathF.Max( sinView, 0.01f ) * width);
			// What's between it and the eye dims it on the way.
			radiance *= MathF.Exp( -0.5f * (extinction[i] + eyeScattering) * rangeMetres );
			var level = radiance * light.Scale;
			brightest = MathF.Max( brightest, level );
			points[i] = (position, level, width * 0.5f * LaserOptics.UnitsPerMetre);
		}

		if ( brightest < VisibleContrast * light.Grey ) beam.RenderingEnabled = false;
		else
		{
			beam.RenderingEnabled = true;
			beam.StartLine();
			foreach ( var (position, level, radius) in points )
				beam.AddLinePoint( position, Encode( light.Hue * level ), radius );
			beam.EndLine();
		}
		return MathF.Exp( -optical );
	}

	/// <summary>
	/// The spot: the beam's irradiance where it lands, spread over a footprint that lengthens as it strikes at a slant, and
	/// reflected by an ordinary surface (<see cref="LaserOptics.SurfaceReflectance"/>); then the glare it makes in the eye.
	/// </summary>
	private void DrawSpot( Vector3 direction, Vector3 normal, float transmitted, Vector3 eye, float eyeScattering, float pixel, in Light light )
	{
		var metres = Start.Distance( End ) / LaserOptics.UnitsPerMetre;
		var radius = LaserOptics.BeamRadius( metres, Aperture, Divergence );
		var incidence = MathF.Max( Vector3.Dot( normal, -direction ), 0.05f );
		var power = Power * transmitted;
		var peak = 2f * power / (MathF.PI * radius * radius) * incidence;
		var luminance = LaserOptics.SurfaceReflectance * light.Efficacy * peak / MathF.PI;

		var toEye = eye - End;
		var range = MathF.Max( toEye.Length, 0.5f );
		var rangeMetres = range / LaserOptics.UnitsPerMetre;
		var seen = MathF.Exp( -0.5f * (extinction[BeamPoints - 1] + eyeScattering) * rangeMetres );
		luminance *= seen;

		// Along the surface, the way the beam runs; with a beam square on, any way.
		var along = direction - normal * Vector3.Dot( direction, normal );
		if ( along.LengthSquared < 1e-6f ) along = Vector3.Cross( normal, MathF.Abs( normal.z ) < 0.9f ? Vector3.Up : Vector3.Forward );
		along = along.Normal;
		var centre = End + normal * (0.02f + range * 0.0004f);
		var pixelSize = pixel * range;

		// Each disc as drawn: at least a pixel round, with its light spread over what it covers.
		Span<float> drawnRadius = stackalloc float[SpotLayers.Length];
		Span<float> halfLength = stackalloc float[SpotLayers.Length];
		Span<float> layerLevel = stackalloc float[SpotLayers.Length];
		var centreLevel = 0f;
		for ( var i = 0; i < SpotLayers.Length; i++ )
		{
			var across = radius * SpotLayers[i].Radius * LaserOptics.UnitsPerMetre;
			var lengthwise = across / incidence;
			drawnRadius[i] = MathF.Max( across, pixelSize );
			halfLength[i] = MathF.Max( MathF.Max( lengthwise, drawnRadius[i] ) - drawnRadius[i], MinimumSegment * 0.5f );
			// An ellipse's area against the capsule's (a disc and a strip 2·half long).
			var area = MathF.PI * across * lengthwise / (MathF.PI * drawnRadius[i] * drawnRadius[i] + 4f * drawnRadius[i] * halfLength[i]);
			layerLevel[i] = luminance * SpotLayers[i].Level * area * light.Scale;
			centreLevel += layerLevel[i];
		}
		var limit = MathF.Min( 1f, CoreLimit * light.Grey / MathF.Max( centreLevel, 1e-9f ) );
		for ( var i = 0; i < SpotLayers.Length; i++ )
		{
			var colour = Encode( light.Hue * (layerLevel[i] * limit) );
			var layer = spot[i];
			layer.RenderingEnabled = true;
			layer.StartLine();
			layer.AddLinePoint( centre - along * halfLength[i], normal, colour, drawnRadius[i], 0f );
			layer.AddLinePoint( centre + along * halfLength[i], normal, colour, drawnRadius[i], 1f );
			layer.EndLine();
		}

		// The spot as a light toward the eye: a Lambertian patch reflecting ρ of the flux, I = ρ·η·P·cos θ / π (cd), so
		// E = I / d² on the eye. The glare is drawn a little toward the eye so the surface doesn't cut it.
		var facing = MathF.Max( Vector3.Dot( normal, toEye / range ), 0f );
		var lux = LaserOptics.SurfaceReflectance * light.Efficacy * power * facing / MathF.PI / (rangeMetres * rangeMetres) * seen;
		var lift = MathF.Min( range * 0.1f, 8f );
		var glareAt = End + toEye / range * lift;
		var glareRange = range - lift;
		var side = Vector3.Cross( toEye / range, MathF.Abs( toEye.z / range ) < 0.9f ? Vector3.Up : Vector3.Forward ).Normal;
		for ( var i = 0; i < GlareLayers.Length; i++ )
		{
			var (degrees, level) = GlareLayers[i];
			var intensity = level * lux * light.Scale;
			var layer = glare[i];
			if ( intensity < VisibleContrast * light.Grey * 0.25f ) { layer.RenderingEnabled = false; continue; }
			var size = glareRange * MathF.Tan( degrees.DegreeToRadian() );
			intensity *= MathF.PI * size / (MathF.PI * size + 2f * MinimumSegment);
			layer.RenderingEnabled = true;
			layer.StartLine();
			layer.AddLinePoint( glareAt - side * (MinimumSegment * 0.5f), Encode( light.Hue * intensity ), size );
			layer.AddLinePoint( glareAt + side * (MinimumSegment * 0.5f), Encode( light.Hue * intensity ), size );
			layer.EndLine();
		}
	}

	/// <summary> How far open to the sky a point is (0 or 1): rain only falls on what's out under it. </summary>
	private float Outdoors( Vector3 position )
	{
		if ( medium.Rain <= 0f ) return 0f;
		var up = Scene.Trace.Ray( position, position + Vector3.Up * OutdoorReach ).WithoutTags( SkyIgnore ).Run();
		return up.StartedSolid ? 0f : !up.Hit || (up.Surface?.ResourceName ?? "").Contains( "sky", StringComparison.OrdinalIgnoreCase ) ? 1f : 0f;
	}

	/// <summary> The line shader reads vertex colour as sRGB: encode linear (and brighter than white) light for it. </summary>
	private static Color Encode( Vector3 linear ) => new( Gamma( linear.x ), Gamma( linear.y ), Gamma( linear.z ), 1f );

	private static float Gamma( float linear ) => linear <= 0.0031308f
		? MathF.Max( linear, 0f ) * 12.92f
		: 1.055f * MathF.Pow( linear, 1f / 2.4f ) - 0.055f;

	private SceneTraceResult Trace( Vector3 start, Vector3 end, GameObject ignore )
	{
		var trace = Scene.Trace.Ray( start, end ).UseHitboxes().WithoutTags( PassThrough );
		if ( ignore.IsValid() ) trace = trace.IgnoreGameObjectHierarchy( ignore );
		return trace.Run();
	}

	private void EnsureObjects()
	{
		if ( material is null )
		{
			material = Material.Load( "materials/default/default_line.vmat" ).CreateCopy();
			material.Set( "Color", Texture.White );
		}
		medium ??= new LaserOptics.Medium();
		distances ??= new float[BeamPoints];
		extinction ??= new float[BeamPoints];
		points ??= new (Vector3, float, float)[BeamPoints];
		spot ??= new SceneLineObject[SpotLayers.Length];
		glare ??= new SceneLineObject[GlareLayers.Length];
		beam ??= CreateLine( SceneLineObject.FaceMode.Camera );
		for ( var i = 0; i < spot.Length; i++ )
			spot[i] ??= CreateLine( SceneLineObject.FaceMode.Normal );
		for ( var i = 0; i < glare.Length; i++ )
			glare[i] ??= CreateLine( SceneLineObject.FaceMode.Camera );
	}

	private SceneLineObject CreateLine( SceneLineObject.FaceMode face )
	{
		var line = new SceneLineObject( Scene.SceneWorld )
		{
			Material = material, Opaque = false, Lighting = false, Face = face,
			StartCap = SceneLineObject.CapStyle.Rounded, EndCap = SceneLineObject.CapStyle.Rounded,
			RenderLayer = SceneRenderLayer.Default
		};
		line.Flags.CastShadows = false;
		line.Attributes.SetCombo( "D_BLEND", 1 );
		return line;
	}

	public void Hide()
	{
		HasHit = false;
		if ( beam.IsValid() ) beam.RenderingEnabled = false;
		HideSpot();
	}

	private void HideSpot()
	{
		foreach ( var layers in new[] { spot, glare } )
			if ( layers is not null )
				foreach ( var layer in layers )
					if ( layer.IsValid() ) layer.RenderingEnabled = false;
	}

	protected override void OnDisabled() => Release();
	protected override void OnDestroy() => Release();

	private void Release()
	{
		beam?.Delete();
		beam = null;
		foreach ( var layers in new[] { spot, glare } )
			if ( layers is not null )
				for ( var i = 0; i < layers.Length; i++ )
				{
					layers[i]?.Delete();
					layers[i] = null;
				}
		HasHit = false;
	}
}
