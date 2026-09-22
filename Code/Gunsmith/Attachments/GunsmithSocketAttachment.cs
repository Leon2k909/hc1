namespace Facepunch.Gunsmith;

/// <summary>
/// Places standalone attachment art on the weapon's animated model socket.
/// Gunsmith floating selection points are UI anchors and need not coincide with the mesh.
/// </summary>
public sealed class GunsmithSocketAttachment : GunsmithAttachment, ICameraSetup
{
	[Property] public string SocketName { get; set; } = "muzzle";
	[Property] public Vector3 SocketOffset { get; set; }
	[Property] public Angles SocketAngles { get; set; }
	/// <summary>Calibrates socket roll for models authored with a different up axis.</summary>
	[Property] public System.Collections.Generic.Dictionary<string, Angles> ModelSocketAngles { get; set; } = new();
	[Property] public System.Collections.Generic.Dictionary<string, Vector3> ModelSocketOffsets { get; set; } = new();
	[Property] public System.Collections.Generic.Dictionary<string, float> ModelScales { get; set; } = new();
	[Property] public System.Collections.Generic.Dictionary<string, Vector3> ModelScaleMultipliers { get; set; } = new();
	[Property] public System.Collections.Generic.Dictionary<string, Model> ModelVariants { get; set; } = new();

	private SkinnedModelRenderer weaponRenderer;
	private WeaponModel weaponModel;
	private Transform? socketOffset;

	protected override void OnInitialize()
	{
		if ( !AttachmentPoint.IsValid() )
			return;

		// World-model prefabs receive their loadout before their root is enabled.
		weaponRenderer = AttachmentPoint.GetComponentInParent<SkinnedModelRenderer>( true );
		weaponModel = AttachmentPoint.GetComponentInParent<WeaponModel>( true );
		if ( weaponRenderer.IsValid() && weaponRenderer.Model is not null
			&& ModelVariants is not null && ModelVariants.TryGetValue( weaponRenderer.Model.Name, out var variant ) && variant is not null )
		{
			var renderer = Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
			if ( renderer.IsValid() ) renderer.Model = variant;
		}
		FollowSocket();
	}

	protected override void OnUpdate()
	{
		FollowSocket();
	}

	// Follow the viewmodel after camera setup moves it this frame.
	void ICameraSetup.PostSetup( CameraComponent cc )
	{
		GunsmithMw22Attachment.FollowingCamera = true;
		try { FollowSocket(); }
		finally { GunsmithMw22Attachment.FollowingCamera = false; }
	}

	private void FollowSocket()
	{
		if ( !weaponRenderer.IsValid() )
			return;

		var socket = weaponRenderer.GetAttachment( SocketName );
		// World sockets are stale after camera setup moves the viewmodel; reuse the offset from the update phase.
		if ( socket.HasValue && !GunsmithMw22Attachment.FollowingCamera ) socketOffset = weaponRenderer.WorldTransform.ToLocal( socket.Value );
		else if ( socket.HasValue && socketOffset.HasValue ) socket = weaponRenderer.WorldTransform.ToWorld( socketOffset.Value );
		// Some static world models have no model sockets. Their authored muzzle
		// object is already the source used by firing effects and is the fallback.
		if ( !socket.HasValue && SocketName == "muzzle" && weaponModel.IsValid() && weaponModel.Muzzle.IsValid() )
			socket = weaponModel.Muzzle.WorldTransform;

		if ( !socket.HasValue )
			return;

		var correction = new Angles();
		var offset = SocketOffset;
		var scale = 1.0f;
		var scaleMultiplier = Vector3.One;
		if ( weaponRenderer.Model is not null )
		{
			var modelName = weaponRenderer.Model.Name;
			ModelSocketAngles?.TryGetValue( modelName, out correction );
			if ( ModelSocketOffsets is not null && ModelSocketOffsets.TryGetValue( modelName, out var modelOffset ) )
				offset = modelOffset;
			if ( ModelScales is not null && ModelScales.TryGetValue( modelName, out var modelScale ) && modelScale > 0 )
				scale = modelScale;
			if ( ModelScaleMultipliers is not null && ModelScaleMultipliers.TryGetValue( modelName, out var multiplier ) )
				scaleMultiplier = multiplier;
		}

		var rotation = socket.Value.Rotation * Rotation.From( correction ) * Rotation.From( SocketAngles );
		// Existing muzzle devices can also be used with the imported shorter barrels.
		var fittedBarrel = GunsmithMw22Attachment.Find( weaponRenderer, GunsmithPartType.Barrel );
		if ( fittedBarrel.IsValid() && AttachmentPoint.Category == GunsmithPartType.Muzzle )
		{
			var delta = GunsmithMw22Attachment.BoneDelta( weaponRenderer, "weapon_root" );
			socket = delta.WithPosition( delta.PointToWorld( fittedBarrel.BarrelMuzzle ) );
			offset = new Vector3( -.25f, 0, 0 );
			rotation = delta.Rotation * Rotation.From( SocketAngles );
		}
		var mount = new Transform( socket.Value.Position, rotation, socket.Value.Scale );
		WorldPosition = mount.PointToWorld( offset );
		WorldRotation = rotation;
		WorldScale = weaponRenderer.WorldScale * scale * scaleMultiplier;
	}
}
