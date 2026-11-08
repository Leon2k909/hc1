namespace Facepunch;

public sealed class ForecourtFountainFlow : Component, Component.ExecuteInEditor, Component.DontExecuteOnServer
{
	[Property] public Model LionCentrepiece { get; set; }
	[Property] public Model RecliningLions { get; set; }
	[Property] public bool ModelIncludesPier { get; set; }
	[Property] public bool SingleSculpturalJet { get; set; }
	[Property] public Vector3 SculpturalMouth { get; set; } = new( 23.87f, 0, 62.69f );
	/// <summary>How far from the centre the mouth streams land in the upper bowl.</summary>
	[Property] public float SculpturalLanding { get; set; } = 37.17f;
	/// <summary>The mouth streams' radius as they leave the mouth; 0 keeps the crown type's default.</summary>
	[Property] public float SculpturalOutlet { get; set; }
	/// <summary>Let the sculpted crown cast shadows onto the bowl, water and itself.</summary>
	[Property] public bool CrownCastsShadows { get; set; }
	private const int StreamCount = 4;
	private const int DropsPerStream = 18;
	private const int BeadsPerStream = 36;
	private const int FallingBeadsPerStream = 22;
	private const float BowlWater = 58.35f;
	private const float PoolWater = 17.5f;
	private const float SculptureDrop = 10f;
	private SceneObject _recliningVisual;
	private readonly List<SceneObject> _visuals = new();
	private readonly List<SceneObject> _drops = new();

	protected override void OnEnabled()
	{
		var jet = Material.Load( "materials/veridant/fountain_spill.vmat" );
		var water = Material.Load( "materials/veridant/vr_pool.vmat" );
		var splash = Material.Load( "materials/belltower/fountain_splash.vmat" );
		var ripple = Material.Load( "materials/veridant/fountain_ripple.vmat" );
		var stone = Material.Load( "materials/veridant/vr_stone.vmat" );
		var brass = Material.Load( "materials/veridant/vr_brass.vmat" );
		var streams = new List<Mesh>();
		var impacts = new List<Mesh>();
		var hasLions = LionCentrepiece is not null && !LionCentrepiece.IsError;
		var sculptural = RecliningLions is not null && !RecliningLions.IsError;
		var curtain = sculptural ? Material.Load( "materials/veridant/fountain_curtain.vmat" ) : jet;
		var waterfall = sculptural ? Material.Load( "materials/veridant/fountain_refractive_fall.vmat" ) : curtain;
		if ( sculptural )
			stone = Material.Load( "materials/veridant/fountain_carved_limestone.vmat" );
		var fittings = new List<Mesh>();
		if ( sculptural )
		{
			_recliningVisual = AddVisual( RecliningLions );
			_recliningVisual.Flags.CastShadows = CrownCastsShadows;
			AddCarvedBowl( fittings, stone );
		}
		if ( sculptural && !ModelIncludesPier )
		{
			(float Radius, float Z)[] pier =
				[(9.25f, 54.5f), (9.25f, 58.2f), (8.7f, 59.1f), (7.85f, 59.5f),
				 (8.05f, 60.25f), (7.55f, 63.5f), (6.9f, 67f), (6.55f, 71f), (6.5f, 75f),
				 (6.92f, 79.7f), (7.52f, 81.9f), (8.18f, 82.4f), (8.95f, 83.15f),
				 (9.28f, 84.15f), (8.92f, 84.7f), (0f, 84.7f)];
			Vector3 PierSurface( int ring, float angle )
			{
				var (radius, height) = pier[ring];
				var axis = MathF.Cos( angle - 0.64f );
				var panel = MathF.Pow( MathF.Abs( axis ), 5 );
				var groove = ring is >= 4 and <= 10 ? 0.64f * panel : 0f;
				return new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0 ) *
					(radius * (1 + 0.42f * axis * axis) - groove) + Vector3.Up * (height - SculptureDrop);
			}
			fittings.Add( Revolve( stone, pier, 128, shape: PierSurface, planarFrom: 14 ) );
			fittings.Add( CarvedPierSprigs( stone, pier, PierSurface ) );
			for ( var panel = 0; panel < 2; panel++ )
			{
				var face = 0.64f + panel * MathF.PI;
				var outward = new Vector3( MathF.Cos( face ), MathF.Sin( face ), 0 );
				foreach ( var edge in new[] { -1f, 1f } )
				{
					fittings.Add( Tube( stone, t =>
					{
						var row = 3 + t * 8;
						var index = (int)row;
						var blend = row - index;
						var angle = face + edge * (0.34f + 0.19f * t);
						var point = PierSurface( index, angle ) * (1 - blend ) + PierSurface( index + 1, angle ) * blend;
						return point + outward * 0.12f;
					}, 0.44f, 0.55f, outward, 0.73f ) );
				}
			}
			(float Radius, float Z)[] plinth =
				[(1, 44f), (1, 46.8f), (0.97f, 47.25f), (0.97f, 48.45f),
				 (0.91f, 48.85f), (0f, 48.85f)];
			var forward = new Vector3( 0.6f, -0.8f, 0 );
			var cross = new Vector3( 0.8f, 0.6f, 0 );
			var bronzeBase = Material.Load( "materials/veridant/fountain_weathered_bronze.vmat" );
			fittings.Add( Revolve( bronzeBase, plinth, 128, shape: ( ring, angle ) =>
			{
				var (radius, height) = plinth[ring];
				return (forward * (30.7f * MathF.Cos( angle )) + cross * (10.45f * MathF.Sin( angle )))
					* radius + Vector3.Up * height;
			}, planarFrom: 4 ) );
		}
		else if ( !sculptural )
		{
			fittings.Add( Nozzle( hasLions ? stone : brass, hasLions ) );
		}

		for ( var stream = 0; stream < StreamCount; stream++ )
		{
			var direction = Direction( stream );
			var side = new Vector3( -direction.y, direction.x, 0 );
			if ( sculptural )
			{
				AddVisual( Model.Builder.AddMesh( FallingSheet( waterfall, direction, side ) ).Create() );
			}
			else
			{
				fittings.Add( Spillway( stone, direction, side ) );
				streams.Add( Tube( jet, t => direction * (29.4f + 6.5f * t) + Vector3.Up * (58.43f + 0.47f * t),
					1.22f, 2.1f, side, 0.14f ) );
				streams.Add( Tube( jet, t => Overflow( direction, t, false ), 2.1f, 0.6f, side, 0.28f ) );
				streams.Add( Tube( jet, t => Overflow( direction, t, false ) + side * (0.7f + 1.8f * t)
					+ direction * (1.3f * t), 0.65f, 0.17f, side, 0.28f ) );
			}
			var impact = Overflow( direction, 1, sculptural ).WithZ( PoolWater + 0.22f );
			impacts.Add( Disc( splash, impact, sculptural ? 8.5f : 5.5f ) );
			if ( sculptural )
			{
				impacts.Add( Disc( splash, impact + side * 4.2f + Vector3.Up * 0.04f, 4.1f ) );
				impacts.Add( Disc( splash, impact - side * 4.2f + Vector3.Up * 0.04f, 4.1f ) );
			}
			impacts.Add( Disc( ripple, impact.WithZ( PoolWater + 0.12f ), 13.5f ) );
		}

		var bowlImpacts = new List<Mesh>();
		if ( sculptural )
		{
			var landingRadius = SculpturalLanding;
			var basinHeight = BowlWater - SculptureDrop;
			var mouth = SculpturalMouth;
			var outletRadius = SculpturalOutlet > 0 ? SculpturalOutlet : ModelIncludesPier ? 0.60f : 0.92f;
			var lift = ModelIncludesPier ? 0.85f : 2f;
			foreach ( var direction in new[] { new Vector3( 0.6f, -0.8f, 0 ), new Vector3( -0.6f, 0.8f, 0 ) } )
			{
				var side = new Vector3( -direction.y, direction.x, 0 );
				var lateral = side * mouth.y;
				streams.Add( Tube( curtain, t =>
					lateral + direction * (mouth.x + (landingRadius - mouth.x) * t) +
					Vector3.Up * (mouth.z + lift * t + (basinHeight - mouth.z - lift) * t * t),
					outletRadius, 0.54f, side, 0.83f ) );
				bowlImpacts.Add( Disc( splash, lateral + direction * landingRadius + Vector3.Up * (basinHeight + 0.12f), 5.5f ) );
				if ( SingleSculpturalJet )
					break;
			}
		}
		else if ( hasLions )
		{
			AddVisual( LionCentrepiece ).Flags.CastShadows = true;
			var bronze = Material.Load( "materials/veridant/fountain_lion_patina.vmat" );
			fittings.Add( Revolve( bronze,
				[(32.22f, 58.48f), (32.19f, 58.57f), (32.05f, 58.64f),
				 (31.72f, 58.64f), (31.58f, 58.57f), (31.55f, 58.48f)], 128 ) );
			fittings.Add( Revolve( bronze,
				[(6.55f, 58.88f), (6.87f, 58.89f), (6.94f, 59.04f), (6.86f, 59.19f),
				 (6.56f, 59.24f), (6.45f, 59.15f), (6.44f, 58.92f)], 96 ) );
			// A stone core joins both masks and blends the lower mane into the capital.
			fittings.Add( Revolve( stone,
				[(5.55f, 58.89f), (5.48f, 59.47f), (4.55f, 60.15f), (3.25f, 60.78f),
				 (2.45f, 62.35f), (2.25f, 70.55f), (2.08f, 73.55f), (1.7f, 77.4f)], 64 ) );
			fittings.Add( Revolve( stone,
				[(1.7f, 76.3f), (3.1f, 76.45f), (3.75f, 76.85f), (3.75f, 77.5f),
				 (3.35f, 77.8f), (2.72f, 77.95f), (2.55f, 78.35f), (2.93f, 78.8f),
				 (3.04f, 79.55f), (2.83f, 80.3f), (2.19f, 80.97f), (1.17f, 81.6f),
				 (0.77f, 82.25f), (0.8f, 82.85f), (0.55f, 83.3f), (0f, 83.55f)], 96 ) );
			fittings.Add( Revolve( bronze,
				[(3.76f, 76.94f), (3.89f, 77.06f), (3.89f, 77.28f), (3.76f, 77.42f)], 64 ) );
			AddLionScrollwork( fittings, stone, bronze );
			foreach ( var direction in new[] { new Vector3( 0.6f, -0.8f, 0 ), new Vector3( -0.6f, 0.8f, 0 ) } )
			{
				var side = new Vector3( -direction.y, direction.x, 0 );
				streams.Add( Tube( jet, t => direction * (7.65f + 15.5f * t) +
					Vector3.Up * (64.6f - (64.6f - BowlWater) * t * t), 0.64f, 0.46f, side, 0.75f ) );
				bowlImpacts.Add( Disc( splash, direction * 23.15f + Vector3.Up * (BowlWater + 0.12f), 4.8f ) );
			}
		}
		else
		{
			streams.Add( Tube( jet, t => new Vector3( 12 * t * t, 2 * t, BowlWater + 6 * (1 - t) + 46 * t * (1 - t) ),
				0.75f, 0.36f, Vector3.Left, 0.8f ) );
			bowlImpacts.Add( Disc( splash, new Vector3( 12, 2, BowlWater + 0.12f ), 4.8f ) );
		}
		AddVisual( Model.Builder.AddMeshes( fittings.ToArray() ).Create() ).Flags.CastShadows = true;
		AddVisual( Model.Builder.AddMeshes( streams.ToArray() ).Create() );
		AddVisual( Model.Builder.AddMeshes( impacts.ToArray() ).Create() );
		var bowlWater = sculptural ? Material.Load( "materials/veridant/fountain_deep_water.vmat" ) : water;
		AddVisual( Model.Builder.AddMesh( Disc( bowlWater, Vector3.Up * (BowlWater - (sculptural ? SculptureDrop : 0)), sculptural ? 42.6f : 31.5f ) ).Create() );
		AddVisual( Model.Builder.AddMeshes( bowlImpacts.ToArray() ).Create() );

		var dropMesh = sculptural
			? Revolve( Material.Load( "materials/veridant/fountain_droplet.vmat" ),
				[(0, -0.24f), (0.11f, -0.20f), (0.17f, -0.09f), (0.17f, 0.04f),
				 (0.13f, 0.14f), (0.07f, 0.21f), (0, 0.24f)], 10 )
			: Tube( jet, t => Vector3.Up * (0.65f - 1.3f * t), 0.29f, 0.12f, Vector3.Left, 0.72f );
		var drop = Model.Builder.AddMesh( dropMesh ).Create();
		var count = sculptural ? BeadsPerStream : DropsPerStream;
		for ( var i = 0; i < StreamCount * count; i++ )
			_drops.Add( AddVisual( drop ) );
		OnUpdate();
	}

	protected override void OnUpdate()
	{
		var world = WorldTransform;
		var sculptural = RecliningLions is not null && !RecliningLions.IsError;
		for ( var i = 0; i < _visuals.Count - _drops.Count; i++ )
			_visuals[i].Transform = world;
		if ( _recliningVisual is not null && !ModelIncludesPier )
			_recliningVisual.Transform = new Transform(
				world.PointToWorld( Vector3.Down * (SculptureDrop + BowlWater * 0.18f) ),
				world.Rotation, world.Scale * new Vector3( 1.1f, 1.1f, 1.18f ) );

		if ( sculptural )
		{
			UpdateWaterBeads( world, Time.Now );
			return;
		}

		for ( var i = 0; i < _drops.Count; i++ )
		{
			var stream = i / DropsPerStream;
			var direction = Direction( stream );
			var side = new Vector3( -direction.y, direction.x, 0 );
			var t = (Time.Now * 2.1f + i * 0.618034f) % 1f;
			var spread = MathF.Sin( i * 7.13f ) * (0.45f + 4.3f * t * t);
			var point = Overflow( direction, t, sculptural ) + side * spread + direction * (1.1f * t);
			var size = (0.55f + 0.7f * MathF.Sin( MathF.PI * t )) * MathF.Min( 1, t * 5 );
			if ( i % DropsPerStream >= 12 )
			{
				var angle = i * 2.399963f;
				var radial = new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0 );
				point = Overflow( direction, 1, sculptural ) + radial * (0.9f + 5f * t)
					+ Vector3.Up * (t * (1 - t) * (12 + 6 * MathF.Sin( i )) + 0.2f);
				size = 0.85f * MathF.Sin( t * MathF.PI );
			}
			_drops[i].Transform = new Transform( world.PointToWorld( point ), world.Rotation, world.Scale * size );
		}
	}

	private void UpdateWaterBeads( Transform world, float time )
	{
		for ( var i = 0; i < _drops.Count; i++ )
		{
			var outward = Direction( i / BeadsPerStream );
			var side = new Vector3( -outward.y, outward.x, 0 );
			var seed = (i + 1) * 0.618034f;
			var offset = seed - MathF.Floor( seed );
			var jitter = MathF.Sin( i * 12.9898f );
			var falling = i % BeadsPerStream < FallingBeadsPerStream;
			var rate = falling ? 2.05f + 0.46f * jitter : 3.1f + 0.6f * jitter;
			var clock = time * rate + offset;
			var age = clock - MathF.Floor( clock );
			// Choose a new lane on each cycle so the beads do not form fixed strings.
			var lane = MathF.Sin( i * 2.399963f + MathF.Floor( clock ) * 2.17f );
			Vector3 position;
			Vector3 scale;
			if ( falling )
			{
				var detach = 0.27f + 0.40f * offset;
				var elapsed = (1 - detach) * age;
				var start = Overflow( outward, detach, true );
				var inherited = (Overflow( outward, detach + 0.005f, true ) - start) / 0.005f;
				var gravity = BowlWater - SculptureDrop + 0.1f - PoolWater;
				position = start + inherited * elapsed + Vector3.Down * (gravity * elapsed * elapsed)
					+ side * (lane * (4.8f + 1.7f * age))
					+ outward * (0.45f + 1.65f * age + 0.55f * jitter);
				scale = new Vector3( 0.9f, 0.9f, 0.95f + 0.85f * age );
			}
			else
			{
				var angle = i * 2.399963f + MathF.Floor( clock ) * 0.91f;
				var spray = side * MathF.Cos( angle ) + outward * MathF.Sin( angle );
				var rise = 7.4f + 7.5f * offset;
				position = Overflow( outward, 1, true ) + side * (lane * 4.5f)
					+ spray * ((2.7f + offset * 4.3f) * age)
					+ Vector3.Up * (0.22f + rise * age * (1 - age));
				scale = Vector3.One;
			}
			var envelope = MathF.Min( 1f, MathF.Min( age * 11f, (1 - age) * 13f ) );
			var size = (0.58f + 0.92f * offset) * envelope;
			_drops[i].Transform = new Transform( world.PointToWorld( position ), world.Rotation, world.Scale * scale * size );
		}
	}

	protected override void OnDisabled()
	{
		foreach ( var visual in _visuals )
			visual.Delete();
		_visuals.Clear();
		_drops.Clear();
		_recliningVisual = null;
	}

	private SceneObject AddVisual( Model model )
	{
		var visual = new SceneObject( Scene.SceneWorld, model, WorldTransform );
		visual.Flags.CastShadows = false;
		_visuals.Add( visual );
		return visual;
	}

	private static Vector3 Direction( int stream )
	{
		var angle = 0.54f + stream * MathF.Tau / StreamCount;
		return new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0 );
	}

	private static void AddLionScrollwork( List<Mesh> fittings, Material stone, Material bronze )
	{
		// The brackets sit along the seam between the masks, clear of the mouths.
		var front = new Vector3( 0.6f, -0.8f, 0 );
		var across = new Vector3( 0.8f, 0.6f, 0 );
		foreach ( var sign in new[] { -1f, 1f } )
		{
			var side = across * sign;
			Vector3 Scroll( float t )
			{
				var angle = -1.93f + 5.76f * t;
				var radius = 5.7f * (1 - t) + 0.65f * t;
				return side * (9.4f + radius * MathF.Cos( angle ))
					+ Vector3.Up * (66.6f + radius * MathF.Sin( angle ));
			}
			// Deep limestone volute with a separate raised metal bead tracing both faces.
			fittings.Add( Tube( stone, t => side * (4.9f + 2.55f * t)
				+ Vector3.Up * (56.8f + 4.7f * t), 1.65f, 1.84f, front, 0.9f ) );
			fittings.Add( Tube( stone, Scroll, 2.25f, 0.8f, front, 0.8f ) );
			fittings.Add( Tube( bronze, t => Scroll( t ) + front * (2.12f - 1.36f * t),
				0.36f, 0.22f, front, 1f ) );
			fittings.Add( Tube( bronze, t => Scroll( t ) - front * (2.12f - 1.36f * t),
				0.36f, 0.22f, front, 1f ) );

			// Swept upper rib ties the outer carving back into the crown.
			fittings.Add( Tube( stone, t => side * (8.6f - 6.2f * t + 0.9f * MathF.Sin( MathF.PI * t ))
				+ Vector3.Up * (68.4f + 8.8f * t), 1.27f, 0.78f, front, 0.84f ) );
		}
	}

	private static Vector3 Overflow( Vector3 direction, float t, bool sculptural )
	{
		if ( sculptural )
			return direction * (43.05f + 11.1f * t) +
				Vector3.Up * (58.45f - SculptureDrop - (58.45f - SculptureDrop - PoolWater) * t * t);

		return direction * (35.9f + 9.5f * t) +
			Vector3.Up * (58.9f - 5f * t - (53.9f - PoolWater) * t * t);
	}

	private static Mesh CarvedPierSprigs( Material stone, (float Radius, float Z)[] profile,
		Func<int, float, Vector3> surface )
	{
		var vertices = new List<Vertex>();
		var indices = new List<int>();
		const int rows = 24;
		const int columns = 8;
		for ( var side = 0; side < 2; side++ )
		{
			var panel = 0.64f + side * MathF.PI;
			for ( var leaf = -2; leaf <= 2; leaf++ )
			{
				var start = vertices.Count;
				for ( var row = 0; row <= rows; row++ )
				{
					var t = row / (float)rows;
					var height = 60.4f + (18.7f - 3.15f * MathF.Abs( leaf )) * t;
					var ring = 4;
					while ( profile[ring + 1].Z < height )
						ring++;
					var blend = (height - profile[ring].Z) / (profile[ring + 1].Z - profile[ring].Z);
					var spread = MathF.Sin( MathF.PI * t );
					var centre = panel + leaf * (0.01f + 0.22f * t * t);
					for ( var column = 0; column <= columns; column++ )
					{
						var u = 2 * column / (float)columns - 1;
						var angle = centre + u * (0.013f + 0.15f * spread * (0.72f + 0.28f * MathF.Cos( 8 * MathF.PI * t )));
						var point = surface( ring, angle ) * (1 - blend) + surface( ring + 1, angle ) * blend;
						var radial = new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0 );
						var tangent = new Vector3( -radial.y, radial.x, 0 );
						var body = 1 - u * u;
						var raised = spread * (body * 0.64f + MathF.Pow( body, 8 ) * 0.26f);
						vertices.Add( new Vertex( point + radial * (raised - 0.025f),
							(radial + tangent * u * 0.7f).Normal, tangent, new Vector4( angle / 4, height / 32, 0, 0 ) ) );
						if ( row < rows && column < columns )
						{
							var a = start + row * (columns + 1) + column;
							var b = a + columns + 1;
							indices.AddRange( [a, a + 1, b, a + 1, b + 1, b] );
						}
					}
				}
			}
		}
		return MakeMesh( stone, vertices, indices );
	}

	private static void AddCarvedBowl( List<Mesh> fittings, Material stone )
	{
		// The original pedestal and bowl proportions broaden into a carved basin.
		(float Radius, float Z)[] profile =
			[(0, 14), (18, 14), (19, 15.2f), (19, 17.8f), (18.2f, 19.2f),
			 (15.9f, 20.1f), (15.9f, 23.5f), (14.6f, 24.7f), (14.6f, 29),
			 (15.8f, 31), (18.4f, 32.6f), (21.4f, 34.4f), (24.9f, 36.1f),
			 (28.3f, 38.2f), (31.7f, 40.5f), (34.5f, 43), (37.1f, 45.6f),
			 (39.2f, 48.2f), (41.2f, 51.3f), (42.4f, 53.3f), (42.15f, 54.4f),
			 (43.65f, 54.9f), (44.15f, 56f), (44.15f, 58.65f), (43.5f, 59.35f),
			 (42.6f, 59.35f), (42.05f, 58.7f), (41.45f, 56.45f), (39.8f, 55.05f),
			 (36, 54.3f), (28, 53.8f), (15, 53.5f), (0, 53.5f)];
		Vector3 Shape( int ring, float angle )
		{
			var p = profile[ring];
			var phase = angle * 16 + 0.35f * MathF.Sin( (p.Z - 33) * 0.29f );
			var belly = MathF.Max( 0, 1 - MathF.Abs( (p.Z - 44) / 11 ) );
			var relief = ring is >= 10 and <= 20
				? belly * (1.32f * MathF.Pow( 0.5f + 0.5f * MathF.Cos( phase ), 2.1f )
					+ 0.33f * MathF.Cos( phase * 2 - p.Z * 0.6f )) : 0;
			if ( ring == 20 )
				relief += 0.48f * MathF.Pow( 0.5f + 0.5f * MathF.Cos( angle * 64 ), 2 );
			var distance = MathF.Acos( Math.Clamp( MathF.Cos( (angle - 0.54f) * StreamCount ), -1f, 1f ) ) / StreamCount;
			var cut = Math.Clamp( (0.185f - distance) / 0.031f, 0, 1 );
			cut *= cut * (3 - 2 * cut);
			var z = ring is >= 22 and <= 27 ? MathF.Min( p.Z, 57.96f + (1 - cut) * 2f ) : p.Z;
			var drop = SculptureDrop * Math.Clamp( (z - 14f) / 19f, 0, 1 );
			return new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0 ) * (p.Radius + relief) + Vector3.Up * (z - drop);
		}
		fittings.Add( Revolve( stone, profile, 256, shape: Shape, planarFrom: 27 ) );

		// Raised acanthus fans follow the curve of the outer bowl.
		var vertices = new List<Vertex>();
		var indices = new List<int>();
		for ( var panel = 0; panel < 8; panel++ )
		{
			var angle = 0.54f + (panel + 0.5f) * MathF.Tau / 8;
			for ( var leaf = -2; leaf <= 2; leaf++ )
			{
				const int length = 18;
				const int width = 8;
				var start = vertices.Count;
				for ( var row = 0; row <= length; row++ )
				{
					var t = row / (float)length;
					var spread = MathF.Sin( MathF.PI * t );
					var height = 38.5f + (14.8f - MathF.Abs( leaf ) * 2.4f) * t;
					var leafAngle = angle + leaf * (0.017f + 0.087f * t * t);
					var segment = 12;
					while ( profile[segment + 1].Z < height )
						segment++;
					var low = profile[segment];
					var high = profile[segment + 1];
					var blend = (height - low.Z) / (high.Z - low.Z);
					for ( var column = 0; column <= width; column++ )
					{
						var u = 2 * column / (float)width - 1;
						var lobes = 0.77f + 0.23f * MathF.Cos( 8 * MathF.PI * t );
						var a = leafAngle + u * (0.004f + 0.052f * spread * lobes);
						var basePoint = Shape( segment, a ) * (1 - blend) + Shape( segment + 1, a ) * blend;
						var radial = new Vector3( MathF.Cos( a ), MathF.Sin( a ), 0 );
						var tangent = new Vector3( -radial.y, radial.x, 0 );
						var edge = 1 - u * u;
						var vein = 0.45f * MathF.Pow( edge, 9 );
						var thickness = spread * (0.18f + edge * (1.7f + 0.22f * MathF.Sin( t * 34 - MathF.Abs( u ) * 3 )) + vein);
						var normal = (radial - Vector3.Up * 0.72f + tangent * (u * 0.85f)).Normal;
						vertices.Add( new Vertex( basePoint + radial * (thickness - 0.07f), normal, tangent,
							new Vector4( a * 2, height / 24, 0, 0 ) ) );
						if ( row < length && column < width )
						{
							var i = start + row * (width + 1) + column;
							var next = i + width + 1;
							indices.AddRange( [i, i + 1, next, i + 1, next + 1, next] );
						}
					}
				}
			}
		}
		fittings.Add( MakeMesh( stone, vertices, indices ) );
	}

	private static Mesh FallingSheet( Material material, Vector3 outward, Vector3 side )
	{
		const int rows = 36;
		const int columns = 32;
		var vertices = new List<Vertex>();
		var indices = new List<int>();
		Vector3 Point( float u, float t )
		{
			var growth = MathF.Sin( t * MathF.PI * 0.5f );
			var curl = MathF.Sin( u * 8.7f + t * 4.1f ) * 0.38f
				+ MathF.Sin( u * 19.2f - t * 3.6f ) * 0.17f;
			var width = 6.75f - 0.55f * t + 0.43f * growth * MathF.Sin( 9 * t + 2 * u );
			return Overflow( outward, t, true ) + side * (u * width)
				+ outward * growth * (curl + 2.25f * u * u)
				+ Vector3.Up * (0.38f * growth * MathF.Sin( 6.1f * u ));
		}
		foreach ( var face in new[] { 1f, -1f } )
		{
			var start = vertices.Count;
			for ( var row = 0; row <= rows; row++ )
			{
				var t = row / (float)rows;
				for ( var column = 0; column <= columns; column++ )
				{
					var u = 2 * column / (float)columns - 1;
					var across = Point( u + 0.005f, t ) - Point( u - 0.005f, t );
					var down = Point( u, t + 0.005f ) - Point( u, t - 0.005f );
					var normal = Vector3.Cross( down, across ).Normal * face;
					vertices.Add( new Vertex( Point( u, t ), normal, across.Normal,
						new Vector4( MathF.Acos( u ) / MathF.Tau, t, 0, 0 ) ) );
					if ( row < rows && column < columns )
					{
						var a = start + row * (columns + 1) + column;
						var b = a + columns + 1;
						if ( face > 0 )
							indices.AddRange( [a, b, a + 1, a + 1, b, b + 1] );
						else
							indices.AddRange( [a, a + 1, b, a + 1, b + 1, b] );
					}
				}
			}
		}
		return MakeMesh( material, vertices, indices );
	}

	private static Mesh Tube( Material material, Func<float, Vector3> path, float startRadius, float endRadius,
		Vector3 sideAxis, float thickness )
	{
		const int steps = 24;
		const int sides = 10;
		var vertices = new List<Vertex>();
		var indices = new List<int>();
		for ( var step = 0; step <= steps; step++ )
		{
			var t = (float)step / steps;
			var centre = path( t );
			var tangent = (path( MathF.Min( 1, t + 0.01f ) ) - path( MathF.Max( 0, t - 0.01f ) )).Normal;
			var across = (sideAxis - tangent * Vector3.Dot( tangent, sideAxis )).Normal;
			var up = Vector3.Cross( tangent, across );
			var radius = (startRadius + (endRadius - startRadius) * t)
				* (1 + 0.17f * MathF.Sin( t * 29 ) * MathF.Sin( MathF.PI * t ));

			for ( var side = 0; side <= sides; side++ )
			{
				var u = (float)side / sides;
				var angle = MathF.Tau * u;
				var offset = across * MathF.Cos( angle ) + up * (MathF.Sin( angle ) * thickness);
				var normal = (across * MathF.Cos( angle ) + up * (MathF.Sin( angle ) / thickness)).Normal;
				vertices.Add( new Vertex( centre + offset * radius, normal, tangent, new Vector4( u, t, 0, 0 ) ) );
				if ( step == steps || side == sides )
					continue;
				var a = step * (sides + 1) + side;
				var b = a + sides + 1;
				indices.AddRange( [a, a + 1, b, a + 1, b + 1, b] );
			}
		}
		return MakeMesh( material, vertices, indices );
	}

	private static Mesh Nozzle( Material material, bool plinth )
	{
		// Revolved collar, tapered stem and open bore at the jet origin.
		(float Radius, float Z)[] profile = plinth
			? [(8.4f, 49.15f), (8.4f, 51f), (7.7f, 51.5f), (6.65f, 51.9f),
				(6.65f, 56.8f), (7.35f, 57.2f), (7.35f, 58.35f), (6.85f, 58.95f), (0f, 58.95f)]
			:
			[(5.6f, 49.15f), (5.6f, 50.3f), (4.4f, 51.4f), (3.1f, 52.1f),
			 (3.1f, 56.7f), (4.6f, 57.2f), (4.6f, 59.0f), (3.8f, 59.6f), (2.3f, 59.6f),
			 (1.45f, 62.9f), (1.8f, 63.2f), (1.8f, 64.1f), (1.55f, 64.35f),
			 (0.83f, 64.35f), (0.75f, 62.4f)];
		return Revolve( material, profile, plinth ? 96 : 32, plinth );
	}

	private static Mesh Revolve( Material material, (float Radius, float Z)[] profile, int sides, bool fluted = false,
		Func<int, float, Vector3> shape = null, int planarFrom = int.MaxValue )
	{
		var wrap = shape is null ? 1f : MathF.Max( 1, profile.Max( p => p.Radius ) * MathF.Tau / 32 );
		var vertices = new List<Vertex>();
		var indices = new List<int>();
		for ( var ring = 0; ring < profile.Length; ring++ )
		{
			var point = profile[ring];
			var prev = profile[Math.Max( 0, ring - 1 )];
			var next = profile[Math.Min( profile.Length - 1, ring + 1 )];
			for ( var side = 0; side <= sides; side++ )
			{
				var u = side / (float)sides;
				var angle = u * MathF.Tau;
				var radial = new Vector3( MathF.Cos( angle ), MathF.Sin( angle ), 0 );
				var tangent = new Vector3( -radial.y, radial.x, 0 );
				var flute = fluted && ring is 3 or 4 ? 0.24f : 0f;
				var radius = point.Radius - flute * (1 - MathF.Cos( angle * 16 ));
				var normal = (radial * (next.Z - prev.Z) - Vector3.Up * (next.Radius - prev.Radius)).Normal;
				normal = (normal + tangent * (16 * flute * MathF.Sin( angle * 16 ) / MathF.Max( 1, radius ))).Normal;
				var position = radial * radius + Vector3.Up * point.Z;
				if ( shape is not null )
				{
					position = shape( ring, angle );
					var across = shape( ring, angle + 0.005f ) - shape( ring, angle - 0.005f );
					var along = shape( Math.Min( profile.Length - 1, ring + 1 ), angle )
						- shape( Math.Max( 0, ring - 1 ), angle );
					if ( across.LengthSquared > 0.000001f )
						normal = Vector3.Cross( across, along ).Normal;
				}
				var uv = shape is null
					? new Vector4( u, point.Z * 0.12f, 0, 0 )
					: new Vector4( u * wrap, point.Z / 32, 0, 0 );
				if ( ring >= planarFrom )
				{
					uv = new Vector4( position.x / 32, position.y / 32, 0, 0 );
					if ( point.Radius == 0 )
						normal = Vector3.Up;
					tangent = (Vector3.Forward - normal * Vector3.Dot( normal, Vector3.Forward )).Normal;
				}
				vertices.Add( new Vertex( position, normal, tangent, uv ) );
				if ( ring < profile.Length - 1 && side < sides )
				{
					var a = ring * (sides + 1) + side;
					var b = a + sides + 1;
					indices.AddRange( [a, a + 1, b, a + 1, b + 1, b] );
				}
			}
		}
		return MakeMesh( material, vertices, indices );
	}

	private static Mesh Spillway( Material material, Vector3 outward, Vector3 side )
	{
		// A thick, open stone chute. Its inner end sits in the bowl and its lip projects past the rim.
		(float X, float Z)[] section =
			[(-3.9f, -2.3f), (-4.15f, 0.65f), (-3.65f, 1.2f), (-2.85f, 1.03f),
			 (-2.05f, 0.08f), (2.05f, 0.08f), (2.85f, 1.03f), (3.65f, 1.2f),
			 (4.15f, 0.65f), (3.9f, -2.3f), (2.8f, -3.35f), (-2.8f, -3.35f)];
		var vertices = new List<Vertex>();
		var indices = new List<int>();
		Vector3 Point( (float X, float Z) p, float t )
			=> outward * (27.8f + t * 8.3f) + side * (p.X * (0.74f + 0.22f * t))
				+ Vector3.Up * (58.08f + t * 0.59f + p.Z * (1 - 0.29f * t));
		void Face( Vector3 a, Vector3 b, Vector3 c, Vector3 d )
		{
			var normal = Vector3.Cross( b - a, d - a ).Normal;
			var tangent = (b - a).Normal;
			var start = vertices.Count;
			vertices.Add( new Vertex( a, normal, tangent, new Vector4( 0, 0, 0, 0 ) ) );
			vertices.Add( new Vertex( b, normal, tangent, new Vector4( (b - a).Length / 24, 0, 0, 0 ) ) );
			vertices.Add( new Vertex( c, normal, tangent, new Vector4( (b - a).Length / 24, (d - a).Length / 24, 0, 0 ) ) );
			vertices.Add( new Vertex( d, normal, tangent, new Vector4( 0, (d - a).Length / 24, 0, 0 ) ) );
			indices.AddRange( [start, start + 1, start + 2, start, start + 2, start + 3] );
		}
		for ( var i = 0; i < section.Length; i++ )
		{
			var a = section[i];
			var b = section[(i + 1) % section.Length];
			Face( Point( a, 0 ), Point( a, 1 ), Point( b, 1 ), Point( b, 0 ) );
		}
		// Close the stone lip below the channel without filling the open trough.
		Face( Point( section[11], 1 ), Point( section[10], 1 ),
			Point( section[5], 1 ), Point( section[4], 1 ) );
		Face( Point( section[0], 1 ), Point( section[11], 1 ),
			Point( section[4], 1 ), Point( section[1], 1 ) );
		Face( Point( section[1], 1 ), Point( section[4], 1 ),
			Point( section[3], 1 ), Point( section[2], 1 ) );
		Face( Point( section[10], 1 ), Point( section[9], 1 ),
			Point( section[8], 1 ), Point( section[5], 1 ) );
		Face( Point( section[5], 1 ), Point( section[8], 1 ),
			Point( section[7], 1 ), Point( section[6], 1 ) );
		return MakeMesh( material, vertices, indices );
	}

	private static Mesh Disc( Material material, Vector3 centre, float radius )
	{
		const int sides = 64;
		var vertices = new List<Vertex> { new( centre, Vector3.Up, Vector3.Forward, new Vector4( 0.5f, 0.5f, 0, 0 ) ) };
		var indices = new List<int>();
		for ( var side = 0; side < sides; side++ )
		{
			var angle = side * MathF.Tau / sides;
			var x = MathF.Cos( angle );
			var y = MathF.Sin( angle );
			vertices.Add( new Vertex( centre + new Vector3( x, y, 0 ) * radius, Vector3.Up,
				Vector3.Forward, new Vector4( 0.5f + x * 0.5f, 0.5f + y * 0.5f, 0, 0 ) ) );
			indices.AddRange( [0, side + 1, (side + 1) % sides + 1] );
		}
		return MakeMesh( material, vertices, indices );
	}

	private static Mesh MakeMesh( Material material, List<Vertex> vertices, List<int> indices )
	{
		var mesh = new Mesh( material );
		mesh.CreateVertexBuffer( vertices.Count, vertices.ToArray() );
		mesh.CreateIndexBuffer( indices.Count, indices.ToArray() );
		mesh.Bounds = BBox.FromPoints( vertices.Select( vertex => vertex.Position ) );
		return mesh;
	}
}
