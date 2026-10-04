namespace Facepunch;

public abstract partial class WeaponModel : Component
{
	[Property] public SkinnedModelRenderer ModelRenderer { get; set; }

	[Property]
	public GameObject Muzzle { get; set; }

	[Property]
	public GameObject EjectionPort { get; set; }

	public void Deploy()
	{
		ModelRenderer.SetBool( "b_deploy", true );
	}

}
