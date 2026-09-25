namespace Facepunch.Gunsmith;

/// <summary>Keeps the raised optic bridge on the MP5's native claw rail during weapon animation and ADS.</summary>
public sealed class GunsmithMp5OpticRiser : Component, ICameraSetup
{
	private SkinnedModelRenderer weapon;

	protected override void OnStart()
	{
		weapon = GetComponentInParent<SkinnedModelRenderer>( true );
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
		WorldTransform = GunsmithMw22Attachment.BoneDelta( weapon, "weapon_root" );
	}
}
