namespace Facepunch;

public abstract partial class WeaponModel
{
	/// <summary>Launch solid brass in weapon space; retain authored transforms for legacy particle effects.</summary>
	public GameObject EjectCasing( GameObject prefab, PlayerPawn owner = null )
	{
		if ( Application.IsDedicatedServer || !prefab.IsValid() || !EjectionPort.IsValid() ) return null;

		if ( prefab.GetComponent<SpentCasing>( true ).IsValid() )
		{
			// Bone GameObjects can retain their bind pose while the viewmodel graph animates.
			// Read the rendered pose so brass actually leaves the receiver on screen.
			var position = EjectionPort.WorldPosition;
			if ( ModelRenderer.IsValid() && ModelRenderer.TryGetBoneTransform( EjectionPort.Name, out var bone ) )
				position = bone.Position;
			var casing = prefab.Clone( new CloneConfig
			{
				Transform = new Transform( position, WorldRotation ),
				StartEnabled = false,
				Name = "Spent casing"
			} );
			casing.GetComponent<SpentCasing>( true ).Launch( WorldRotation, owner.IsValid() ? owner.SyncedVelocity : Vector3.Zero,
				owner.IsValid() ? owner.GameObject : GameObject );
			casing.Enabled = true;
			return casing;
		}

		return prefab.Clone( new CloneConfig
		{
			Parent = EjectionPort,
			Transform = new(),
			StartEnabled = true,
			Name = "Casing ejection"
		} );
	}
}
