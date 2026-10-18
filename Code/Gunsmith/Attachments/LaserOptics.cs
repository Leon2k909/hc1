namespace Facepunch.Gunsmith;

/// <summary>
/// What the eye really sees of a visible aiming laser: its spot, and the light the air, haze, smoke and rain scatter out
/// of its beam, against the brightness the eye is adapted to. Figures are photometric (cd/m², lux) until
/// <see cref="Adapted"/> turns them into the renderer's linear units for one camera.
/// </summary>
public static class LaserOptics
{
	public const float UnitsPerMetre = 39.37f;

	/// <summary>
	/// What a lit surface reflects (diffuse, 0-1), for a spot on a surface whose own reflectance isn't known: painted
	/// walls, concrete and wood are 0.2-0.5.
	/// </summary>
	public const float SurfaceReflectance = 0.35f;

	// CIE 1924 photopic luminosity V(λ), 500-680 nm in 10 nm steps.
	private static readonly float[] Photopic =
		{ 0.323f, 0.503f, 0.710f, 0.862f, 0.954f, 0.995f, 0.995f, 0.952f, 0.870f, 0.757f, 0.631f, 0.503f, 0.381f, 0.265f, 0.175f, 0.107f, 0.061f, 0.032f, 0.017f };

	/// <summary> Lumens per watt of light at a wavelength: 603 lm/W at 532 nm, 148 at 635 nm. </summary>
	public static float LumensPerWatt( float nanometres )
	{
		var x = ((nanometres - 500f) / 10f).Clamp( 0f, Photopic.Length - 1.001f );
		var i = (int)x;
		return 683f * MathX.Lerp( Photopic[i], Photopic[i + 1], x - i );
	}

	/// <summary> The wavelength a laser of this colour has: a red diode's 635 nm, else a green DPSS laser's 532 nm. </summary>
	public static float WavelengthOf( Color colour ) => colour.r > colour.g ? 635f : 532f;

	/// <summary> The colour at a luminance of 1, in linear units. </summary>
	public static Vector3 Hue( Color colour )
	{
		var c = new Vector3( MathF.Max( colour.r, 0f ), MathF.Max( colour.g, 0f ), MathF.Max( colour.b, 0f ) );
		var luminance = 0.2126f * c.x + 0.7152f * c.y + 0.0722f * c.z;
		return luminance > 1e-4f ? c / luminance : new Vector3( 0f, 1f / 0.7152f, 0f );
	}

	private static float HenyeyGreenstein( float g, float cosTheta ) =>
		(1f - g * g) / (4f * MathF.PI * MathF.Pow( MathF.Max( 1f + g * g - 2f * g * cosTheta, 1e-6f ), 1.5f ));

	/// <summary>
	/// Particles (aerosol, haze, smoke, mist and rain), per steradian: a strong forward peak, with the ~0.02/sr straight
	/// back that lidar measures for haze (a lidar ratio near 50 sr).
	/// </summary>
	public static float ParticlePhase( float cosTheta ) =>
		0.96f * HenyeyGreenstein( 0.72f, cosTheta ) + 0.04f * HenyeyGreenstein( -0.5f, cosTheta );

	/// <summary> The air's molecules (Rayleigh), per steradian. </summary>
	public static float MoleculePhase( float cosTheta ) => 3f / (16f * MathF.PI) * (1f + cosTheta * cosTheta);

	/// <summary> The air's own scattering (1/m): molecules, falling as λ⁻⁴. </summary>
	public static float MoleculeScattering( float nanometres ) => 1.16e-5f * MathF.Pow( 550f / nanometres, 4f );

	/// <summary> Clean air's fine dust and aerosol (1/m), about 40 km of visibility, falling as λ⁻¹·³. </summary>
	public static float AerosolScattering( float nanometres ) => 9e-5f * MathF.Pow( 550f / nanometres, 1.3f );

	/// <summary>
	/// The radius (1/e²) of a Gaussian beam this far from the emitter (metres): its waist at the aperture, spreading by
	/// the full-angle divergence.
	/// </summary>
	public static float BeamRadius( float metres, float apertureMetres, float divergenceRadians )
	{
		var waist = apertureMetres * 0.5f;
		var spread = divergenceRadians * 0.5f * metres;
		return MathF.Sqrt( waist * waist + spread * spread );
	}

	private static Scene _skyScene;
	private static bool _hasSky;
	private static float _skyCheckedAt = -10f;

	/// <summary>
	/// Whether the map has a sky, as the weather asks (<see cref="Weather"/>): one without is all interior, lit by lamps,
	/// with no sun and no rain. Looked for once every two seconds, since a cloud map's sky can load late.
	/// </summary>
	public static bool HasSky( Scene scene )
	{
		if ( scene is null ) return false;
		if ( scene == _skyScene && Time.Now >= _skyCheckedAt && Time.Now - _skyCheckedAt < 2f ) return _hasSky;
		_skyScene = scene;
		_skyCheckedAt = Time.Now;
		return _hasSky = scene.GetAllComponents<SkyBox2D>().Any( x => x.Active )
			|| scene.SceneWorld.SceneObjects.OfType<SceneSkyBox>().Any();
	}

	/// <summary>
	/// What one camera's eye is adapted to: the luminance (cd/m²) of the place in view, and the renderer's own grey for
	/// that view at the camera's exposure. A camera adapts to what's in view as the eye does, so light drawn at
	/// <c>EngineGrey / Luminance</c> renderer units per cd/m² is as bright against the scene as the real light is against
	/// the real place.
	/// </summary>
	public readonly record struct AdaptedView( float Luminance, float EngineGrey );

	public static AdaptedView Adapted( CameraComponent camera ) => Adaptation.For( camera );

	/// <summary>
	/// The luminance (cd/m²) the eye is adapted to, worked out from what's in view a few times a second: sunlit, in the
	/// shade, indoors, or at night, as the map's sun and weather say.
	/// </summary>
	private static class Adaptation
	{
		private const float SampleInterval = 0.2f;
		/// <summary> A lit interior (lux): offices and labs are lit to 300-500. </summary>
		private const float InteriorLux = 400f;
		/// <summary> How fast the eye follows a change (1/s): it adapts to most of a step in about a second. </summary>
		private const float AdaptRate = 2.5f;
		/// <summary> Adapting to a dark place is slower than to a bright one. </summary>
		private const float DarkAdaptRate = 0.8f;
		private const float ViewRange = 8000f;
		private const float SkyReach = 3000f;
		private static readonly string[] Ignore = { "trigger", "playerclip", "movement", "player", "ragdoll", "particles", "viewer" };

		private static CameraComponent _camera;
		private static float _luminance;
		private static float _target;
		private static float _nextSample;
		private static float _lastTime;

		public static AdaptedView For( CameraComponent camera )
		{
			if ( !camera.IsValid() || camera.Scene is not { } scene ) return default;
			var now = Time.Now;
			if ( camera != _camera || now < _lastTime || now - _lastTime > 2f )
			{
				_camera = camera;
				_luminance = 0f;
				_nextSample = 0f;
			}
			if ( now >= _nextSample )
			{
				_nextSample = now + SampleInterval;
				_target = Sample( scene, camera );
				if ( _luminance <= 0f ) _luminance = _target;
			}
			var delta = MathF.Max( now - _lastTime, 0f );
			_lastTime = now;
			var rate = _target < _luminance ? DarkAdaptRate : AdaptRate;
			// The eye adapts in log luminance.
			_luminance = MathF.Exp( MathX.Lerp( MathF.Log( _luminance ), MathF.Log( _target ), 1f - MathF.Exp( -delta * rate ) ) );
			return new AdaptedView( _luminance, EngineGrey( camera ) );
		}

		/// <summary>
		/// The scene's adapted grey in renderer units: auto exposure brings the view's level to about a quarter of white,
		/// within the camera's exposure range.
		/// </summary>
		private static float EngineGrey( CameraComponent camera )
		{
			var exposure = camera.AutoExposure;
			var scale = exposure.Enabled
				? MathF.Sqrt( MathF.Max( exposure.MinimumExposure, 0.05f ) * MathF.Max( exposure.MaximumExposure, 0.05f ) )
				: 1f;
			return 0.25f / (scale * MathF.Pow( 2f, exposure.Compensation ));
		}

		private static float Sample( Scene scene, CameraComponent camera )
		{
			// A map with no sky is an interior, lit by its lamps: a lit lab, hall or warehouse.
			var sky = HasSky( scene );
			if ( !sky ) return SurfaceReflectance * InteriorLux / MathF.PI;

			var sun = scene.GetAllComponents<DirectionalLight>().Where( x => x.Active ).OrderByDescending( x => Luminance( x.LightColor ) ).FirstOrDefault();
			var weather = scene.GetAllComponents<Weather>().FirstOrDefault();
			var overcast = weather.IsValid() ? weather.OvercastAmount.Clamp( 0f, 1f ) : 0f;

			// Daylight by the map's sun: the night maps' moon is a quarter of the day maps' 1.1-3.2.
			var sunLuminance = sun.IsValid() ? Luminance( sun.LightColor ) : 1.4f;
			var day = ((sunLuminance - 0.45f) / 0.55f).Clamp( 0f, 1f );
			day = day * day * (3f - 2f * day);

			// Illuminance (lux): direct sun or moon, the sky's light in the shade, and lamps indoors or in a lit street at night.
			var direct = MathX.Lerp( 0.25f, 90000f, day ) * (1f - 0.95f * overcast);
			var shade = MathX.Lerp( 3f, 15000f * (1f - 0.6f * overcast), day );
			var indoor = MathX.Lerp( 150f, InteriorLux, day );
			// A clear blue sky and an overcast one, or the night sky's glow.
			var skyLuminance = MathX.Lerp( 0.01f, MathX.Lerp( 6000f, 2500f, overcast ), day );

			var view = camera.WorldTransform;
			var toSun = sun.IsValid() ? -sun.WorldRotation.Forward : Vector3.Up;
			var tan = MathF.Tan( camera.FieldOfView.Clamp( 10f, 150f ).DegreeToRadian() * 0.5f ) * 0.6f;
			var logSum = 0f;
			var samples = 0;
			for ( var y = -1; y <= 1; y++ )
				for ( var x = -1; x <= 1; x++ )
				{
					var direction = (view.Rotation.Forward + view.Rotation.Right * (x * tan) + view.Rotation.Up * (y * tan * 0.6f)).Normal;
					var hit = scene.Trace.Ray( view.Position, view.Position + direction * ViewRange ).WithoutTags( Ignore ).Run();
					float luminance;
					if ( !hit.Hit || IsSky( hit ) ) luminance = skyLuminance;
					else
					{
						var from = hit.HitPosition + hit.Normal * 2f;
						var sunlit = Vector3.Dot( hit.Normal, toSun ) > 0f && IsOpen( scene, from, toSun );
						var outdoors = sunlit || IsOpen( scene, from, (Vector3.Up + hit.Normal * 0.3f).Normal );
						var illuminance = (sunlit ? direct * Vector3.Dot( hit.Normal, toSun ) : 0f) + (outdoors ? shade : indoor);
						luminance = SurfaceReflectance * illuminance / MathF.PI;
					}
					logSum += MathF.Log( MathF.Max( luminance, 1e-4f ) );
					samples++;
				}
			return MathF.Exp( logSum / samples );
		}

		private static bool IsOpen( Scene scene, Vector3 from, Vector3 direction )
		{
			var hit = scene.Trace.Ray( from, from + direction * SkyReach ).WithoutTags( Ignore ).Run();
			return !hit.StartedSolid && (!hit.Hit || IsSky( hit ));
		}

		private static bool IsSky( SceneTraceResult hit ) =>
			(hit.Surface?.ResourceName ?? "").Contains( "sky", StringComparison.OrdinalIgnoreCase );

		private static float Luminance( Color c ) => 0.2126f * c.r + 0.7152f * c.g + 0.0722f * c.b;
	}

	/// <summary>
	/// What scatters light out of the beam here (1/m): the maps' haze and mist (<see cref="VolumetricFogVolume"/>), smoke
	/// grenades' clouds and rain, gathered once a frame.
	/// </summary>
	public sealed class Medium
	{
		private readonly record struct FogBox( Transform Transform, BBox Bounds, float Scattering, float Exponent );
		private readonly record struct Puff( Vector3 Position, float RadiusSquared, float Scattering );

		/// <summary>
		/// The volumetric fog's scattering per unit of a volume's strength (1/m): the renderer's 0.0022 per inch
		/// (Sandbox.SceneRenderer's VolumetricFog), so Riverdale's hall haze at 0.24 lets you see ~190 m.
		/// </summary>
		private const float FogScatteringPerStrength = 0.0022f * UnitsPerMetre;

		/// <summary>
		/// Rain (1/m): Marshall and Palmer's drops, each blocking twice its cross-section, half of it scattered outside
		/// the diffraction peak: 1 mm/h is ~0.2 km⁻¹, 25 mm/h ~1.4 km⁻¹.
		/// </summary>
		public static float RainScattering( float millimetresPerHour ) =>
			millimetresPerHour <= 0f ? 0f : 1.8e-4f * MathF.Pow( millimetresPerHour, 0.63f );

		private readonly List<FogBox> _fog = new();
		private readonly List<Puff> _smoke = new();
		private float _gatheredAt = -1f;
		private Scene _scene;

		public float Rain { get; private set; }

		public void Gather( Scene scene )
		{
			if ( scene == _scene && _gatheredAt == Time.Now ) return;
			_scene = scene;
			_gatheredAt = Time.Now;
			_fog.Clear();
			_smoke.Clear();

			foreach ( var volume in scene.GetAllComponents<VolumetricFogVolume>() )
				if ( volume.Active && volume.Strength > 0f )
					_fog.Add( new FogBox( volume.WorldTransform, volume.Bounds, volume.Strength * FogScatteringPerStrength,
						MathF.Max( volume.FalloffExponent, 0.1f ) ) );

			foreach ( var simulation in scene.GetAllComponents<SmokeSimulation>() )
			{
				var effect = simulation.ParticleEffect;
				if ( !effect.IsValid() ) continue;
				foreach ( var p in effect.Particles )
				{
					// A puff's sprite blocks about its alpha of the light through its middle. As a ball of radius r whose
					// density falls as 1 - (d/r)², that's an optical depth τ = β₀·4r/3 through it.
					var radius = MathF.Max( p.Size.x, p.Size.y ) * SmokeMath.PuffReach;
					var alpha = (p.Alpha * 0.9f).Clamp( 0f, 0.98f );
					if ( radius < 1f || alpha < 0.005f ) continue;
					var depth = -MathF.Log( 1f - alpha );
					_smoke.Add( new Puff( p.Position, radius * radius, 0.75f * depth / (radius / UnitsPerMetre) ) );
				}
			}

			var weather = scene.GetAllComponents<Weather>().FirstOrDefault();
			Rain = weather.IsValid() && HasSky( scene ) ? RainScattering( weather.RainRate ) : 0f;
		}

		/// <summary> Particle scattering here (1/m), less the open-air rain, which only falls outdoors (<paramref name="outdoors"/>). </summary>
		public float ParticlesAt( Vector3 position, float outdoors )
		{
			var scattering = Rain * outdoors;
			foreach ( var fog in _fog )
			{
				var local = fog.Transform.PointToLocal( position );
				var size = fog.Bounds.Size * 0.5f;
				if ( size.x <= 0f || size.y <= 0f || size.z <= 0f ) continue;
				var offset = (local - fog.Bounds.Center).Abs();
				var edge = MathF.Max( offset.x / size.x, MathF.Max( offset.y / size.y, offset.z / size.z ) );
				if ( edge >= 1f ) continue;
				// Full in the middle, thinning over the volume's outer quarter.
				scattering += fog.Scattering * MathF.Pow( ((1f - edge) / 0.25f).Clamp( 0f, 1f ), fog.Exponent );
			}
			foreach ( var puff in _smoke )
			{
				var d2 = puff.Position.DistanceSquared( position );
				if ( d2 < puff.RadiusSquared ) scattering += puff.Scattering * (1f - d2 / puff.RadiusSquared);
			}
			return scattering;
		}
	}
}
