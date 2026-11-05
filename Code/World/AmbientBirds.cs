namespace Facepunch;

/// <summary>
/// Local scenery made by Weather on maps with a sky. Finds visible outdoor air near the camera,
/// validates complete orbits before using them, then keeps small flocks circling in world space.
/// No physics bodies, colliders, networking, or per-bird game objects.
/// </summary>
[Title( "Ambient Birds" ), Category( "Environment" )]
public sealed class AmbientBirds : Component
{
	private const int MaxFlocks = 3;
	private const int Samples = 24;
	// Covers formation spread, vertical undulation, wingspan and the arc between samples.
	private const float Clearance = 150f;
	private readonly List<Flock> _flocks = [];
	private readonly Random _random = new();
	private Model _body, _wing, _rightWing;
	private float _time;
	private RealTimeSince _sinceSearch = 999f;

	private sealed class Bird
	{
		public SceneObject Body, Left, Right;
		public float Phase, Offset, Height, Scale;
		public void Delete()
		{
			Body?.Delete();
			Left?.Delete();
			Right?.Delete();
		}
	}

	private sealed class Flock
	{
		public Vector3 Center;
		public float Radius, Speed, Phase, Born;
		public readonly List<Bird> Birds = [];
	}

	protected override void OnUpdate()
	{
		if ( Application.IsDedicatedServer || !Scene.Camera.IsValid() ) return;
		_time += Time.Delta;
		var eye = Scene.Camera.WorldPosition;

		for ( var i = _flocks.Count - 1; i >= 0; i-- )
		{
			var flock = _flocks[i];
			// Recycle only well beyond normal visibility; looking away doesn't relocate a flock.
			if ( eye.Distance( flock.Center ) > 6500f )
			{
				foreach ( var bird in flock.Birds ) bird.Delete();
				_flocks.RemoveAt( i );
				continue;
			}
			Place( flock, eye );
		}

		// One candidate per second, with early exits on sheltered or obstructed locations.
		if ( _flocks.Count >= MaxFlocks || _sinceSearch < 1f ) return;
		_sinceSearch = 0f;
		TrySpawn( eye );
	}

	private static Vector3 Circle( Flock flock, float angle ) => flock.Center
		+ new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0f ) * flock.Radius;

	private void TrySpawn( Vector3 eye )
	{
		var bearing = _random.Float( 0f, MathF.Tau );
		var distance = _random.Float( 700f, 2300f );
		var flock = new Flock
		{
			Center = eye + new Vector3( MathF.Cos( bearing ) * distance, MathF.Sin( bearing ) * distance, _random.Float( 500f, 1050f ) ),
			Radius = _random.Float( 320f, 620f ),
			Speed = _random.Float( 0.3f, 0.48f ) * (_random.NextSingle() < 0.5f ? -1f : 1f),
			Phase = _random.Float( 0f, MathF.Tau ),
			Born = _time
		};
		if ( _flocks.Any( f => f.Center.Distance( flock.Center ) < f.Radius + flock.Radius + 200f ) ) return;

		var visible = false;
		for ( var i = 0; i < Samples; i++ )
		{
			var point = Circle( flock, i * MathF.Tau / Samples );
			var next = Circle( flock, (i + 1) * MathF.Tau / Samples );
			var sweep = Scene.Trace.Sphere( Clearance, point, next ).WithoutTags( RainView.ShelterGrid.Ignore ).Run();
			if ( sweep.Hit || sweep.StartedSolid ) return;
			if ( i % 6 != 0 ) continue;
			var sky = Scene.Trace.Ray( point, point + Vector3.Up * 32000f ).WithoutTags( RainView.ShelterGrid.Ignore ).Run();
			if ( sky.StartedSolid || (sky.Hit && !(sky.Surface?.ResourceName ?? "").Contains( "sky", StringComparison.OrdinalIgnoreCase )) ) return;
			var sight = Scene.Trace.Ray( eye, point ).WithoutTags( RainView.ShelterGrid.Ignore ).Run();
			visible |= !sight.Hit && !sight.StartedSolid;
		}
		if ( !visible ) return;

		EnsureModels();
		var count = _random.Next( 3, 6 );
		for ( var i = 0; i < count; i++ )
		{
			flock.Birds.Add( new Bird
			{
				Body = MakeObject( _body ), Left = MakeObject( _wing ), Right = MakeObject( _rightWing ),
				Phase = _random.Float( 0f, MathF.Tau ), Offset = (i - (count - 1) * 0.5f) * 0.065f,
				Height = _random.Float( -25f, 25f ), Scale = _random.Float( 0.85f, 1.15f )
			} );
		}
		_flocks.Add( flock );
		Place( flock, eye );
	}

	private SceneObject MakeObject( Model model )
	{
		var obj = new SceneObject( Scene.SceneWorld, model, global::Transform.Zero );
		obj.Flags.CastShadows = false;
		return obj;
	}

	private void Place( Flock flock, Vector3 eye )
	{
		foreach ( var bird in flock.Birds )
		{
			var angle = flock.Phase + _time * flock.Speed + bird.Offset;
			var direction = MathF.Sign( flock.Speed );
			var position = Circle( flock, angle ) + Vector3.Up * (bird.Height + 15f * MathF.Sin( _time * 0.7f + bird.Phase ));
			var forward = new Vector3( -MathF.Sin( angle ) * direction, MathF.Cos( angle ) * direction, 0f );
			var rotation = Rotation.LookAt( forward ) * Rotation.FromRoll( direction * -12f );
			// Several wingbeats, then a smooth glide. Every bird has its own phase and rate.
			var cycle = _time * 0.65f + bird.Phase;
			var effort = Math.Clamp( (MathF.Sin( cycle ) + 0.25f) * 3f, 0f, 1f );
			var flap = 8f + 38f * effort * MathF.Sin( _time * (15f + bird.Scale) + bird.Phase );
			// Grow from a distant speck at creation and shrink into the distance at the visibility limit.
			var emergence = Math.Clamp( (_time - flock.Born) / 4f, 0.001f, 1f );
			var range = Math.Clamp( (6000f - position.Distance( eye )) / 1200f, 0.001f, 1f );
			var scale = bird.Scale * emergence * range;
			bird.Body.Transform = new Transform( position, rotation, scale );
			bird.Left.Transform = new Transform( position, rotation * Rotation.FromRoll( flap ), scale );
			bird.Right.Transform = new Transform( position, rotation * Rotation.FromRoll( -flap ), scale );
		}
	}

	private void EnsureModels()
	{
		if ( _body is not null ) return;
		var plumage = BirdMaterial( "Crow plumage", new Color( .025f, .029f, .037f ), .65f );
		var flight = BirdMaterial( "Crow flight feathers", new Color( .018f, .020f, .025f ), .75f );
		var beak = BirdMaterial( "Crow beak", new Color( .022f, .023f, .026f ), .4f );
		var eye = BirdMaterial( "Crow eyes", new Color( .003f, .003f, .004f ), .12f );
		_body = AmbientCrowMesh.Body( plumage, flight, beak, eye );
		_wing = AmbientCrowMesh.Left( plumage, flight, beak, eye );
		_rightWing = AmbientCrowMesh.Right( plumage, flight, beak, eye );
	}

	private static Material BirdMaterial( string name, Color color, float roughness )
	{
		var material = Material.FromShader( "shaders/complex.shader" ).CreateCopy( name );
		material.SetFeature( "F_SPECULAR", 1 );
		material.Set( "g_tColor", Texture.White );
		material.Set( "g_tNormal", Texture.Load( "materials/default/default_normal.tga" ) );
		material.Set( "g_tRoughness", Texture.White );
		material.Set( "g_vColorTint", color );
		material.Set( "g_flRoughnessScaleFactor", roughness );
		material.Set( "g_flMetalness", 0f );
		return material;
	}

	protected override void OnDisabled()
	{
		foreach ( var flock in _flocks )
			foreach ( var bird in flock.Birds ) bird.Delete();
		_flocks.Clear();
	}
}
