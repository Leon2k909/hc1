using Facepunch.Gunsmith;

namespace Facepunch;

public abstract partial class WeaponModel
{
	private GameObject shiftedMuzzle;

	/// <summary>Discharge effects follow the fitted barrel/device; the original mount stays intact.</summary>
	public GameObject DischargeMuzzle
	{
		get
		{
			var factory = ModelRenderer.IsValid() ? ModelRenderer.Components.Get<GunsmithMw22Factory>( FindMode.EverythingInSelf ) : null;
			if ( factory.IsValid() && factory.MuzzleEffectPoint.IsValid() ) return factory.MuzzleEffectPoint;

			// A bodygroup barrel of another length moves the muzzle along the bore (the muzzle's own axes).
			var shift = ModelRenderer.IsValid() ? GunsmithAttachmentPoint.MuzzleShift( ModelRenderer.GameObject ) : Vector3.Zero;
			if ( shift == Vector3.Zero || !Muzzle.IsValid() ) return Muzzle;
			if ( !shiftedMuzzle.IsValid() || shiftedMuzzle.Parent != Muzzle )
			{
				shiftedMuzzle?.Destroy();
				shiftedMuzzle = new GameObject( Muzzle, true, "Shifted Muzzle" );
				shiftedMuzzle.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			}
			shiftedMuzzle.LocalPosition = shift;
			return shiftedMuzzle;
		}
	}
}
