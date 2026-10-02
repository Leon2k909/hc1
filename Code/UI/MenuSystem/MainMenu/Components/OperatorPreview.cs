using Sandbox.UI;

namespace Facepunch.UI;

/// <summary>A self-contained outfit viewer. ScenePanel owns its preview scene; no gameplay pawn is spawned.</summary>
public sealed class OperatorPreview : ScenePanel
{
	public string OutfitId { get; set; } = "military";
	public bool HasError { get; private set; }
	private string loadedId;
	private SkinnedModelRenderer body;
	private CameraComponent previewCamera;
	private float yaw = -20f;
	private float zoom;
	private bool dragging;
	private float dragX;

	public OperatorPreview()
	{
		using var scope = RenderScene.Push();
		previewCamera = new GameObject( true, "Operator camera" ).AddComponent<CameraComponent>();
		previewCamera.BackgroundColor = Color.Transparent;
		previewCamera.FieldOfView = 34;
		previewCamera.FovAxis = CameraComponent.Axis.Vertical;
		previewCamera.ZNear = 1;
		previewCamera.ZFar = 512;
		var light = new GameObject( true, "Operator light" ).AddComponent<DirectionalLight>();
		light.WorldRotation = Rotation.From( 35, 25, 0 );
		light.LightColor = new Color( 1f, .96f, .9f ) * 2f;
		light.SkyColor = new Color( .62f, .67f, .75f );
		UpdateCamera();
	}

	public void ShowOutfit( string id )
	{
		OutfitId = OperatorOutfits.Find( id ).Id;
		if ( loadedId == OutfitId && body.IsValid() ) return;
		using var scope = RenderScene.Push();
		body?.GameObject.Destroy();
		body = null;
		loadedId = OutfitId;
		HasError = false;
		ResetView();
		var outfit = OperatorOutfits.Find( OutfitId );
		var model = Model.Load( outfit.ModelPath );
		if ( model is null || model.IsError ) { HasError = true; return; }
		body = new GameObject( true, outfit.Name ).AddComponent<SkinnedModelRenderer>();
		body.Model = model;
		body.CreateBoneObjects = false;
		if ( MilitaryUniform.UsesHumanSkeleton( model ) ) MilitaryUniform.SetModel( body, model, outfit.Style );
		body.SetBool( "b_grounded", true );
		body.Set( "holdtype", 0 );
		body.WorldRotation = Rotation.FromYaw( yaw );
	}

	public void Rotate( float degrees )
	{
		yaw = (yaw + degrees) % 360f;
		if ( body.IsValid() ) body.WorldRotation = Rotation.FromYaw( yaw );
	}

	public void Zoom( float amount ) { zoom = (zoom + amount).Clamp( 0f, 1f ); UpdateCamera(); }
	public void ResetView() { yaw = -20f; zoom = 0; dragging = false; Rotate( 0 ); UpdateCamera(); }

	private void UpdateCamera()
	{
		if ( !previewCamera.IsValid() ) return;
		var target = new Vector3( 0, 0, 35f + zoom * 17f );
		previewCamera.WorldPosition = target + new Vector3( 132f - zoom * 68f, 0, 8 );
		previewCamera.WorldRotation = Rotation.LookAt( target - previewCamera.WorldPosition );
		previewCamera.ComposeView();
	}

	public override void Tick()
	{
		if ( loadedId != OutfitId ) ShowOutfit( OutfitId );
		if ( dragging && !HasActive ) dragging = false;
		if ( dragging )
		{
			var x = MousePosition.x;
			Rotate( (x - dragX) * .5f );
			dragX = x;
		}
		base.Tick();
	}

	protected override void OnMouseDown( MousePanelEvent e )
	{
		base.OnMouseDown( e );
		if ( e.MouseButton != MouseButtons.Left ) return;
		dragging = true;
		dragX = MousePosition.x;
	}

	public override void OnMouseWheel( Vector2 value ) => Zoom( value.y * .12f );

	public override void OnDeleted()
	{
		if ( RenderScene.IsValid() ) RenderScene.Destroy();
		base.OnDeleted();
	}
}
