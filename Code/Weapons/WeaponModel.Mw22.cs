using Facepunch.Gunsmith;

namespace Facepunch;

public abstract partial class WeaponModel
{
	/// <summary>Discharge effects follow the fitted barrel/device; the original mount stays intact.</summary>
	public GameObject DischargeMuzzle
	{
		get
		{
			var factory = ModelRenderer.IsValid() ? ModelRenderer.Components.Get<GunsmithMw22Factory>( FindMode.EverythingInSelf ) : null;
			return factory.IsValid() && factory.MuzzleEffectPoint.IsValid() ? factory.MuzzleEffectPoint : Muzzle;
		}
	}
}
