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
	private RangedFloat ZoomRange { get; set; } = new( -0.6f, 0.3f );

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

			ZoomFactor += scroll * Time.Delta * 5f;
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
			var panel = GunsmithPanel.Instance;
			var customizing = panel.IsValid() && panel.IsCustomizing;
			var size = panel.IsValid() ? panel.Panel.Box.Rect.Size : Screen.Size;
			var aspect = size.x / MathF.Max( size.y, 1f );
			// Keep the full weapon above the camo drawer, including on ultrawide displays.
			var horizontalFov = InitialFOV * (customizing ? 1.4f : 1f);
			var halfWidth = MathF.Tan( horizontalFov * MathF.PI / 360f ) * MathF.Max( 1f, aspect / (16f / 9f) );
			var horizontalOffset = 0f;
			// Include custom stocks and muzzle extensions when fitting the preview.
			// Reserve the actual armory (left) and attachment column (right) widths so a suppressor
			// or stock cannot disappear behind either of them.
			var browser = panel.IsValid() ? panel.Panel.Children.FirstOrDefault( p => p.HasClass( "weapon-browser" ) ) : null;
			var leftFraction = panel.IsValid() && panel.IsArmoryVisible && browser is not null
				? ((browser.Box.Rect.Right - panel.Panel.Box.Rect.Left + 24f) / MathF.Max( size.x, 1f )).Clamp( 0f, 0.6f ) : 0f;
			var attachments = panel.IsValid() && !customizing ? panel.Panel.Children.OfType<GunsmithAttachmentBrowser>().FirstOrDefault() : null;
			var rightFraction = attachments is not null && attachments.HasClass( "has-slots" )
				? ((panel.Panel.Box.Rect.Right - attachments.Box.Rect.Left + 24f) / MathF.Max( size.x, 1f )).Clamp( 0f, 0.6f ) : 0f;
			var cameraOrigin = CameraComponent.GameObject.Parent.IsValid()
				? CameraComponent.GameObject.Parent.WorldTransform.PointToWorld( initialCameraPos ) : initialCameraPos;
			var minRight = float.MaxValue;
			var maxRight = float.MinValue;
			var nearestDepth = float.MaxValue;
			foreach ( var renderer in Weapon.GameObject.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
			{
				if ( !renderer.Enabled || renderer.Model is null ) continue;
				foreach ( var corner in renderer.Model.Bounds.Corners )
				{
					var relative = renderer.WorldTransform.PointToWorld( corner ) - cameraOrigin;
					var right = Vector3.Dot( relative, CameraComponent.WorldRotation.Right );
					minRight = MathF.Min( minRight, right );
					maxRight = MathF.Max( maxRight, right );
					nearestDepth = MathF.Min( nearestDepth, Vector3.Dot( relative, CameraComponent.WorldRotation.Forward ) );
				}
			}
			if ( minRight < maxRight && nearestDepth > 1f )
			{
				// Fit the gun into the gap between the two columns and centre it there.
				halfWidth = MathF.Max( halfWidth, (maxRight - minRight) * 0.5f / (nearestDepth * MathF.Max( 0.3f, 0.95f - leftFraction - rightFraction )) );
				horizontalOffset = (minRight + maxRight) * 0.5f - (leftFraction - rightFraction) * nearestDepth * halfWidth;
			}
			CameraComponent.FieldOfView = 2f * MathF.Atan( halfWidth ) * 180f / MathF.PI + (ZoomFactor * 10f);

			panOffsetTarget.x = panOffsetTarget.x.Clamp( -25f, 25f );
			panOffsetTarget.y = panOffsetTarget.y.Clamp( -25f, 25f );

			if ( !isPanning )
				panOffsetTarget = panOffsetTarget.LerpTo( 0, Time.Delta * SlowSpeed );

			var framingOffset = 0f;
			if ( customizing )
			{
				var distance = Vector3.DistanceBetween( CameraComponent.WorldPosition, Weapon.WorldPosition );
				framingOffset = -0.36f * distance * halfWidth / MathF.Max( aspect, 0.5f );
			}
			// Fill the view with the optic so the reticle on its lens is readable, clear of the drawer below.
			if ( reticleTab && TryGetOpticBounds( out var opticBounds ) )
			{
				var toOptic = opticBounds.Center - cameraOrigin;
				var depth = Vector3.Dot( toOptic, CameraComponent.WorldRotation.Forward );
				if ( depth > 1f )
				{
					halfWidth = opticBounds.Size.Length * 0.5f / (depth * 0.6f) * aspect;
					CameraComponent.FieldOfView = 2f * MathF.Atan( halfWidth ) * 180f / MathF.PI * (1f + ZoomFactor);
					horizontalOffset = Vector3.Dot( toOptic, CameraComponent.WorldRotation.Right );
					framingOffset = Vector3.Dot( toOptic, CameraComponent.WorldRotation.Up ) - 0.36f * depth * halfWidth / MathF.Max( aspect, 0.5f );
				}
			}

			CameraComponent.LocalPosition = initialCameraPos + CameraComponent.WorldRotation.Right * (panOffsetTarget.x + horizontalOffset)
				+ CameraComponent.WorldRotation.Up * (panOffsetTarget.y + framingOffset);
		}
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
