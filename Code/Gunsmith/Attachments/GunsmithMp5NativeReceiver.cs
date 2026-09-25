namespace Facepunch.Gunsmith;

/// <summary>
/// Shows a piece cut from the original MP5 mesh (receiver, sights, bolt...) and
/// follows the bone it is skinned to. Barrel attachments hide whole native
/// materials, which also hold parts they don't replace; see Tools/fit_mp5_barrels.py.
/// </summary>
public sealed class GunsmithMp5NativeReceiver : Component, ICameraSetup
{
	/// <summary>The v_mp5 bone this piece is skinned to. Its mesh is in bind-pose model space.</summary>
	[Property] public string BoneName { get; set; } = "weapon_root";

	private SkinnedModelRenderer weapon;

	protected override void OnStart()
	{
		weapon = GetComponentInParent<SkinnedModelRenderer>( true );
		// The third-person MP5 uses a separate material atlas and already keeps
		// its own body. This mesh is the first-person receiver only.
		if ( weapon.IsValid() && weapon.Model?.Name != "models/weapons/sbox_smg_mp5/v_mp5.vmdl" )
		{
			var mesh = Components.Get<ModelRenderer>();
			if ( mesh.IsValid() ) mesh.Enabled = false;
			weapon = null;
			return;
		}
		Refresh();
	}

	protected override void OnUpdate() => Refresh();

	void ICameraSetup.PostSetup( CameraComponent camera )
	{
		GunsmithMw22Attachment.FollowingCamera = true;
		try { Refresh(); }
		finally { GunsmithMw22Attachment.FollowingCamera = false; }
	}

	private void Refresh()
	{
		if ( !weapon.IsValid() || weapon.Model is null ) return;
		WorldTransform = GunsmithMw22Attachment.BoneDelta( weapon, BoneName );
	}
}
