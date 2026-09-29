using Facepunch.Gunsmith;

namespace Facepunch;

public sealed class GunsmithController : Component
{
	[Property]
	public GunsmithWeapon Weapon { get; set; }

	[Property] 
	public GunsmithSystem System {get; set; }

	[Property] 
	public CameraComponent CameraComponent { get; set; }

	[Property]
	float OrbitSpeed { get; set; } = 0.01f;

	[Property]
	float SlowSpeed { get; set; } = 5f;

	[Property]
	RangedFloat RollRange { get; set; } = new( -10, 10 );

	[Property]
	private RangedFloat ZoomRange { get; set; } = new( -1.5f, 1f );

	public bool FPS => System.IsValid() && System.FPS;

	private Vector2 angleOffset;
	private Vector2 lastFrameMousePos = 0;
	private Vector2 dragStartMousePos = 0;
	private bool isDragging = false;
	private float viewYaw;
	private float viewRoll;
	private static Vector2 _devSpin;

	/// <summary>Test helper: rotate the gunsmith preview as if dragged (degrees of yaw, tilt).</summary>
	[ConCmd( "dev_gunsmith_spin" )]
	private static void DevSpin( float yaw, float tilt ) => _devSpin += new Vector2( yaw, tilt );
	private bool dragStartedOnPreview;
	private bool panStartedOnPreview;
	private const float DragThreshold = 4f;
	private float InitialFOV = 60;
	private float ZoomFactor = 0;
	
	private Vector2 panOffsetTarget;
	private Vector2 panStartMousePos;
	private bool isPanning;
	private Vector3 initialCameraPos;

	/// <summary> The Reticle tab turns the gun to this yaw: from behind and a little to the side, so the lens faces the camera. </summary>
	private const float ReticleViewYaw = -75f;
	private float? yawBeforeReticle;

	protected override void OnStart()
	{
		if ( !CameraComponent.IsValid() )
			return;

		InitialFOV = CameraComponent.FieldOfView;
		initialCameraPos = CameraComponent.LocalPosition;
	}

	protected override void OnUpdate()
	{
		if ( !System.IsValid() || !Weapon.IsValid() || !CameraComponent.IsValid() )
			return;

		if ( System.FPS )
		{
			CameraComponent.FieldOfView = 80;
			Weapon.LocalRotation = Rotation.Identity;
			viewYaw = 0f;
			viewRoll = 0f;

			CameraComponent.WorldRotation = Rotation.From( 0, -45, 0 );
		}
		else
		{
			CameraComponent.WorldRotation = Rotation.From( 0, -90, 0 );

			var mousePos = Mouse.Position;
			var delta = mousePos - lastFrameMousePos;
			lastFrameMousePos = Mouse.Position;
			var overControls = GunsmithPanel.Instance.IsValid() && GunsmithPanel.Instance.IsPointerOverControls();

			if ( Input.Pressed( "Attack1" ) )
			{
				dragStartMousePos = mousePos;
				isDragging = false;
				dragStartedOnPreview = !overControls;
			}

			if ( Input.Down( "Attack1" ) && dragStartedOnPreview )
			{
				if ( !isDragging && (mousePos - dragStartMousePos).Length > DragThreshold )
					isDragging = true;

				if ( isDragging )
				{
					// Rotate the camera around the orbitObject
					angleOffset += new Vector2( delta.x * OrbitSpeed, delta.y * OrbitSpeed );
				}
			}
			else
			{
				isDragging = false;
			}

			if ( Input.Pressed( "Attack2" ) )
			{
				panStartMousePos = mousePos;
				isPanning = false;
				panStartedOnPreview = !overControls;
			}

			if ( Input.Down( "Attack2" ) && panStartedOnPreview )
			{
				if ( !isPanning && (mousePos - panStartMousePos).Length > DragThreshold )
					isPanning = true;

				if ( isPanning )
				{
					panOffsetTarget += new Vector2( delta.x * -0.05f, delta.y * 0.05f );
				}
			}
			else
			{
				isPanning = false;
			}

			var scroll = overControls ? 0f : -Input.MouseWheel.y;

			ZoomFactor += scroll * 0.12f;
			ZoomFactor = ZoomFactor.Clamp( ZoomRange.Min, ZoomRange.Max );

			angleOffset = angleOffset.LerpTo( 0, Time.Delta * SlowSpeed );
			// Spin freely all the way round (yaw), tilt within RollRange to look over the top / underneath.
			// Tracked as plain angles: reading them back from the rotation wraps and fights the clamp.
			viewYaw = (viewYaw + angleOffset.x + _devSpin.x) % 360f;
			viewRoll -= _devSpin.y;
			_devSpin = default;
			viewRoll = (viewRoll - angleOffset.y).Clamp( RollRange.Min, RollRange.Max );

			// Reticle tab: turn the fitted optic's lens towards the camera. Dragging still spins the gun meanwhile.
			var reticleTab = GunsmithPanel.Instance.IsValid() && GunsmithPanel.Instance.IsReticleTabOpen && OpticRenderers().Any();
			if ( reticleTab )
			{
				yawBeforeReticle ??= viewYaw;
				if ( !isDragging )
				{
					var turn = ((ReticleViewYaw - viewYaw) % 360f + 540f) % 360f - 180f;
					viewYaw += turn * MathF.Min( 1f, Time.Delta * 8f );
					viewRoll = viewRoll.LerpTo( 0f, Time.Delta * 8f );
				}
			}
			else if ( yawBeforeReticle is { } yaw )
			{
				viewYaw = yaw;
				yawBeforeReticle = null;
			}
			Weapon.WorldRotation = Rotation.From( 0, viewYaw, viewRoll );

			panOffsetTarget.x = panOffsetTarget.x.Clamp( -25f, 25f );
			panOffsetTarget.y = panOffsetTarget.y.Clamp( -25f, 25f );

			if ( !isPanning )
				panOffsetTarget = panOffsetTarget.LerpTo( 0, Time.Delta * SlowSpeed );

			FrameWeapon( reticleTab );
		}
	}

	private bool framed;
	private float framedFov;
	private Vector2 framedOffset;

	/// <summary>
	/// Fits the gun (in the Reticle tab, its optic) into the gunsmith's stage: the empty middle of the screen between its
	/// columns (<see cref="GunsmithPanel.StageRect"/>). The field of view widens until every part (a suppressor, a long
	/// stock) fits the stage with a little room, and the camera slides so the gun sits in the stage's middle.
	/// </summary>
	private void FrameWeapon( bool reticleTab )
	{
		var panel = GunsmithPanel.Instance;
		var screen = panel.IsValid() && panel.Panel is not null && panel.Panel.Box.Rect.Width > 1f
			? panel.Panel.Box.Rect : new Rect( 0, 0, Screen.Width, Screen.Height );
		var stage = panel.IsValid() && panel.StageRect is { } stageRect ? stageRect : screen;
		var aspect = screen.Width / MathF.Max( screen.Height, 1f );

		// The stage as fractions of the screen, from its top left.
		var fx0 = ((stage.Left - screen.Left) / screen.Width).Clamp( 0f, 0.9f );
		var fx1 = ((stage.Right - screen.Left) / screen.Width).Clamp( fx0 + 0.1f, 1f );
		var fy0 = ((stage.Top - screen.Top) / screen.Height).Clamp( 0f, 0.9f );
		var fy1 = ((stage.Bottom - screen.Top) / screen.Height).Clamp( fy0 + 0.1f, 1f );

		var cameraOrigin = CameraComponent.GameObject.Parent.IsValid()
			? CameraComponent.GameObject.Parent.WorldTransform.PointToWorld( initialCameraPos ) : initialCameraPos;
		var rotation = CameraComponent.WorldRotation;

		// The gun's extent across and up the view, all at its nearest depth, which errs on the roomy side.
		var renderers = reticleTab ? OpticRenderers() : Weapon.GameObject.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants )
			.Where( x => x.Enabled && x.Model is not null );
		var minRight = float.MaxValue;
		var maxRight = float.MinValue;
		var minUp = float.MaxValue;
		var maxUp = float.MinValue;
		var depth = float.MaxValue;
		foreach ( var renderer in renderers )
		{
			foreach ( var corner in renderer.Model.Bounds.Corners )
			{
				var relative = renderer.WorldTransform.PointToWorld( corner ) - cameraOrigin;
				var right = Vector3.Dot( relative, rotation.Right );
				var up = Vector3.Dot( relative, rotation.Up );
				minRight = MathF.Min( minRight, right );
				maxRight = MathF.Max( maxRight, right );
				minUp = MathF.Min( minUp, up );
				maxUp = MathF.Max( maxUp, up );
				depth = MathF.Min( depth, Vector3.Dot( relative, rotation.Forward ) );
			}
		}

		// Tangent of half the horizontal field of view. By default the scene's own, widened to keep its height on ultrawides.
		var halfWidth = MathF.Tan( InitialFOV * MathF.PI / 360f ) * MathF.Max( 1f, aspect / (16f / 9f) );
		var offset = Vector2.Zero;
		if ( minRight < maxRight && depth > 1f )
		{
			// The share of the stage the gun may fill; the optic fills more of it, so its reticle is readable.
			var fill = reticleTab ? 0.62f : 0.9f;
			var fitWidth = (maxRight - minRight) / (2f * depth * (fx1 - fx0) * fill);
			var fitHeight = (maxUp - minUp) * aspect / (2f * depth * (fy1 - fy0) * fill);
			halfWidth = reticleTab ? MathF.Max( fitWidth, fitHeight ) : MathF.Max( halfWidth, MathF.Max( fitWidth, fitHeight ) );

			// Slide the camera so the gun's middle lands on the stage's middle.
			var halfHeight = halfWidth / aspect;
			offset.x = (minRight + maxRight) * 0.5f - (fx0 + fx1 - 1f) * depth * halfWidth;
			offset.y = (minUp + maxUp) * 0.5f + (fy0 + fy1 - 1f) * depth * halfHeight;
		}

		var fov = 2f * MathF.Atan( halfWidth ) * 180f / MathF.PI;
		fov *= MathF.Pow( 2f, ZoomFactor );
		fov = fov.Clamp( 5f, 110f );

		// Ease towards the new framing, so a new part or a panel resizing doesn't jolt the view.
		if ( !framed )
		{
			framed = true;
			framedFov = fov;
			framedOffset = offset;
		}
		else
		{
			var t = MathF.Min( 1f, Time.Delta * 12f );
			framedFov = framedFov.LerpTo( fov, t );
			framedOffset = framedOffset.LerpTo( offset, t );
		}

		CameraComponent.FieldOfView = framedFov;
		CameraComponent.LocalPosition = initialCameraPos + rotation.Right * (panOffsetTarget.x + framedOffset.x)
			+ rotation.Up * (panOffsetTarget.y + framedOffset.y);
	}

	private IEnumerable<ModelRenderer> OpticRenderers() => Weapon.GameObject.Components
		.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
		.Where( x => x.Category == GunsmithPartType.Optic && x.CurrentGameObject.IsValid() )
		.SelectMany( x => x.CurrentGameObject.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		.Where( x => x.Enabled && x.Model is not null );

	private bool TryGetOpticBounds( out BBox bounds )
	{
		var corners = OpticRenderers()
			.SelectMany( r => r.Model.Bounds.Corners.Select( c => r.WorldTransform.PointToWorld( c ) ) )
			.ToArray();
		bounds = corners.Length > 0 ? BBox.FromPoints( corners ) : default;
		return corners.Length > 0;
	}
}
