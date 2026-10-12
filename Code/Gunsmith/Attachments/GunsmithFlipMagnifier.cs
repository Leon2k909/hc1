namespace Facepunch.Gunsmith;

/// <summary>
/// The magnifier of a flip-to-side mount (a magnifier behind a red dot or holographic sight). While the
/// owner has the optic's alternate sight selected (T), it swings about its hinge off the sight line, so
/// the front sight is used at 1x; switching back swings it in again. Sits on a child of the optic's root,
/// whose own ModelRenderer holds the mount and the front sight (Tools/flip_magnifiers.py).
/// </summary>
public sealed class GunsmithFlipMagnifier : Component
{
	/// <summary>A point on the hinge, in the optic's model space. The hinge runs along the bore.</summary>
	[Property] public Vector3 Hinge { get; set; }

	/// <summary>How far it swings, in degrees about the bore: positive takes its top to the gun's right.</summary>
	[Property] public float FlipAngle { get; set; } = 90f;

	/// <summary>Seconds for a full swing; a real lever-released mount snaps over in about a third of a second.</summary>
	[Property] public float SwingTime { get; set; } = 0.3f;

	private float _flip;

	protected override void OnEnabled()
	{
		_flip = Target() ? 1f : 0f;
		Apply();
	}

	protected override void OnUpdate()
	{
		var target = Target() ? 1f : 0f;
		_flip = SwingTime > 0f ? _flip.Approach( target, Time.Delta / SwingTime ) : target;
		Apply();
	}

	private void Apply()
	{
		// Ease in and out, as the arm leaves its detent and lands on its stop.
		var t = _flip * _flip * (3f - 2f * _flip);
		var rotation = Rotation.FromAxis( Vector3.Forward, FlipAngle * t );
		LocalRotation = rotation;
		LocalPosition = Hinge - rotation * Hinge;

		// Follow the mount's own renderer, so the magnifier hides and tints with the rest of the optic.
		var mount = GameObject.Parent?.Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
		var mesh = Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
		if ( !mount.IsValid() || !mesh.IsValid() ) return;
		if ( mesh.Enabled != mount.Enabled ) mesh.Enabled = mount.Enabled;
		if ( mesh.Tint != mount.Tint ) mesh.Tint = mount.Tint;
		if ( mesh.RenderType != mount.RenderType ) mesh.RenderType = mount.RenderType;
		if ( mesh.RenderOptions.Game != mount.RenderOptions.Game ) mesh.RenderOptions.Game = mount.RenderOptions.Game;
		if ( mesh.RenderOptions.Overlay != mount.RenderOptions.Overlay ) mesh.RenderOptions.Overlay = mount.RenderOptions.Overlay;
	}

	/// <summary>Whether the optic's owner has its front sight selected. In the gunsmith or on the floor it stays in.</summary>
	private bool Target()
	{
		var attachment = GameObject.Parent?.Components.Get<GunsmithAttachment>( FindMode.EverythingInSelf );
		var part = attachment?.AttachmentPoint?.CurrentPart;
		if ( !part.IsValid() || !part.HasAlternateSight ) return false;
		var equipment = FindEquipment();
		return equipment.IsValid() && equipment.IsUsingAlternateSight( part );
	}

	private Equipment FindEquipment()
	{
		var weapon = GameObject.Parent?.Parent?.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelfAndAncestors );
		if ( !weapon.IsValid() ) return null;
		var view = weapon.Components.Get<ViewModel>( FindMode.EverythingInSelf );
		if ( view.IsValid() ) return view.Equipment;
		var equipment = weapon.GetComponentInParent<Equipment>( true );
		if ( equipment.IsValid() ) return equipment;
		var current = weapon.GetComponentInParent<PlayerPawn>( true )?.CurrentEquipment;
		return current.IsValid() && current.WorldModel.IsValid() && current.WorldModel.ModelRenderer == weapon ? current : null;
	}
}
