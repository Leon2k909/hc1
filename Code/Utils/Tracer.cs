public sealed class Tracer : Renderer, Component.ExecuteInEditor, Component.ITemporaryEffect
{
	[Header( "Position" )]
	[Property, Feature( "Tracer" )] public WorldPoint EndPoint { get; set; }

	[Header( "Speed" )]
	[Property, Feature( "Tracer" )] public float DistancePerSecond { get; set; } = 1.0f;
	[Property, Feature( "Tracer" )] public float Length { get; set; } = 100.0f;
	[Property, Feature( "Tracer" )] public float StartDistance { get; set; } = 200.0f;

	[Header( "Rendering" )]
	[Property, Feature( "Tracer" )] public Gradient LineColor { get; set; } = new Gradient( new Gradient.ColorFrame( 0, Color.White ), new Gradient.ColorFrame( 1, Color.White.WithAlpha( 0 ) ) );
	[Property, Feature( "Tracer" )] public Curve LineWidth { get; set; } = new Curve( new Curve.Frame( 0, 2 ), new Curve.Frame( 1, 0 ) );
	[Property, Feature( "Tracer" )] public SceneLineObject.CapStyle StartCap { get; set; }
	[Property, Feature( "Tracer" )] public SceneLineObject.CapStyle EndCap { get; set; }

	[Group( "Rendering" )]
	[Property] public bool Opaque { get; set; } = true;

	[Group( "Rendering" )]
	[Property] public bool CastShadows { get; set; } = true;

	[Property, FeatureEnabled( "Light" )]
	public bool EnableLight { get; set; }

	[Property, Feature( "Light" )]
	public Gradient LightColor { get; set; } = new Gradient( new Gradient.ColorFrame( 0, Color.White ), new Gradient.ColorFrame( 1, Color.White ) );

	[Property, Feature( "Light" )]
	public Curve LightRadius { get; set; } = new Curve( new Curve.Frame( 0, 128 ), new Curve.Frame( 0.5f, 256 ), new Curve.Frame( 1, 128 ) );

	[Property, Feature( "Light" ), Range( 0, 1 )]
	public float LightPosition { get; set; }

	[Property] public Material Material { get; set; }

	bool Component.ITemporaryEffect.IsActive => !_finished;

	private float _distance;
	private bool _finished;
	private Material _defaultMaterial;
	private SceneLineObject _line;
	private SceneLight _light;

	protected override void OnEnabled()
	{
		_line = new SceneLineObject( Scene.SceneWorld );
		_line.Transform = Transform.World;
		_defaultMaterial = Material.Load( "materials/default/default_line.vmat" ).CreateCopy();
		_distance = StartDistance;
		_finished = false;
	}

	protected override void OnDisabled()
	{
		_line?.Delete();
		_line = null;

		_light?.Delete();
		_light = null;
	}

	protected override void OnUpdate()
	{
		var length = WorldPosition.Distance( EndPoint.Get() );
		_distance += DistancePerSecond * Time.Delta;

		if ( _distance > length + Length )
		{
			_finished = true;

			if ( Scene.IsEditor )
				_distance = 0;
		}
	}

	protected override void OnPreRender()
	{
		if ( !_line.IsValid() )
			return;

		var travel = EndPoint.Get() - WorldPosition;
		var maxLength = travel.Length;

		if ( _distance - Length > maxLength )
		{
			_line.RenderingEnabled = false;

			_light?.Delete();
			_light = null;
			return;
		}

		var midDistance = (_distance - Length * 0.5f).Clamp( 0, maxLength );
		var delta = midDistance.LerpInverse( 0, maxLength );

		if ( EnableLight )
		{
			_light ??= new ScenePointLight( Scene.SceneWorld );
			_light.Transform = Transform.World;
			_light.QuadraticAttenuation = 10;
			_light.LightColor = LightColor.Evaluate( delta );
			_light.ShadowsEnabled = false;
			_light.Radius = LightRadius.Evaluate( delta );
			_light.Position = WorldPosition + travel.Normal * (_distance - Length * LightPosition).Clamp( 0, maxLength - 5 );
		}
		else
		{
			_light?.Delete();
			_light = null;
		}

		_line.StartCap = StartCap;
		_line.EndCap = EndCap;
		_line.Opaque = Opaque;
		_line.RenderingEnabled = true;
		_line.Transform = WorldTransform;
		_line.Flags.CastShadows = CastShadows;

		if ( Material.IsValid() )
		{
			_line.Material = Material;
		}
		else
		{
			_defaultMaterial.Set( "Color", Texture.White );
			_line.Material = _defaultMaterial;
		}

		_line.Attributes.SetCombo( "D_BLEND", Opaque ? 0 : 1 );
		_line.StartLine();

		for ( var sample = 0f; sample <= 1.0f; sample += 0.1f )
		{
			var distance = (_distance - Length * sample).Clamp( 0, maxLength );
			_line.AddLinePoint( WorldPosition + travel.Normal * distance, LineColor.Evaluate( sample ), LineWidth.Evaluate( sample ) );
		}

		_line.EndLine();
	}
}

public struct WorldPoint
{
	[KeyProperty] public Vector3 Origin { get; set; }
	public GameObject Parent { get; set; }

	public Vector3 Get()
	{
		if ( Parent.IsValid() )
			return Parent.WorldTransform.PointToWorld( Origin );

		return Origin;
	}

	public static implicit operator WorldPoint( Vector3 position )
	{
		return new WorldPoint { Origin = position };
	}
}