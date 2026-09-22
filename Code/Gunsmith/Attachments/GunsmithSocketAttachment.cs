namespace Facepunch.Gunsmith;

/// <summary>
/// Places standalone attachment art on the weapon's animated model socket.
/// Gunsmith floating selection points are UI anchors and need not coincide with the mesh.
/// </summary>
public sealed class GunsmithSocketAttachment : GunsmithAttachment
{
	[Property] public string SocketName { get; set; } = "muzzle";
	[Property] public Vector3 SocketOffset { get; set; }
	[Property] public Angles SocketAngles { get; set; }
	/// <summary>Calibrates socket roll for models authored with a different up axis.</summary>
	[Property] public System.Collections.Generic.Dictionary<string, Angles> ModelSocketAngles { get; set; } = new();

	private SkinnedModelRenderer weaponRenderer;
	private WeaponModel weaponModel;

	protected override void OnInitialize()
	{
		weaponRenderer = AttachmentPoint.GetComponentInParent<SkinnedModelRenderer>();
		weaponModel = AttachmentPoint.GetComponentInParent<WeaponModel>();
		FollowSocket();
	}

	protected override void OnUpdate()
	{
		FollowSocket();
	}

	private void FollowSocket()
	{
		if ( !weaponRenderer.IsValid() )
			return;

		var socket = weaponRenderer.GetAttachment( SocketName );
		// Some static world models have no model sockets. Their authored muzzle
		// object is already the source used by firing effects and is the fallback.
		if ( !socket.HasValue && SocketName == "muzzle" && weaponModel.IsValid() && weaponModel.Muzzle.IsValid() )
			socket = weaponModel.Muzzle.WorldTransform;

		if ( !socket.HasValue )
			return;

		var correction = new Angles();
		if ( weaponRenderer.Model is not null && ModelSocketAngles is not null )
			ModelSocketAngles.TryGetValue( weaponRenderer.Model.Name, out correction );

		var rotation = socket.Value.Rotation * Rotation.From( correction ) * Rotation.From( SocketAngles );
		var mount = new Transform( socket.Value.Position, rotation, socket.Value.Scale );
		WorldPosition = mount.PointToWorld( SocketOffset );
		WorldRotation = rotation;
		WorldScale = weaponRenderer.WorldScale;
	}
}
