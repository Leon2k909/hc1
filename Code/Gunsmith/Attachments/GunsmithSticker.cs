namespace Facepunch.Gunsmith;

/// <summary>
/// A sticker: the part's artwork (<see cref="GunsmithPart.StickerImage"/>) printed on a thin quad laid on the sticker
/// point's surface, so it rides the gun like any other part. The point's local +X is the surface's outward normal and
/// its +Z the artwork's up; the artwork fills as much of <see cref="GunsmithAttachmentPoint.StickerSize"/> as its shape
/// allows. It's a mesh rather than a decal: a decal would lag the viewmodel by a frame and paint the hands too.
/// </summary>
public sealed class GunsmithSticker : GunsmithAttachment
{
	/// <summary>How far the quad stands off the surface, so the gun's own faces don't show through it.</summary>
	private const float Lift = 0.012f;

	private SkinnedModelRenderer weapon;

	protected override void OnInitialize()
	{
		var part = AttachmentPoint?.CurrentPart;
		var renderer = Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
		if ( !part.IsValid() || !renderer.IsValid() || string.IsNullOrEmpty( part.StickerImage ) ) return;

		var materialPath = string.IsNullOrEmpty( part.StickerMaterial ) ? System.IO.Path.ChangeExtension( part.StickerImage, ".vmat" ) : part.StickerMaterial;
		var material = Material.Load( materialPath );
		if ( material is null )
		{
			Log.Warning( $"Gunsmith: sticker '{part.ResourcePath}' has no material at '{materialPath}'." );
			return;
		}

		var room = AttachmentPoint.StickerSize;
		if ( room.x <= 0f || room.y <= 0f ) room = new Vector2( 1.5f, 1.5f );
		var aspect = 1f;
		var texture = Texture.Load( part.StickerImage, false );
		if ( texture is not null && texture.Width > 1 && texture.Height > 1 ) aspect = texture.Width / (float)texture.Height;
		var width = MathF.Min( room.x, room.y * aspect );
		var height = width / aspect;
		renderer.Model = BuildQuad( material, width, height );

		weapon = string.IsNullOrEmpty( AttachmentPoint.StickerBone ) ? null : AttachmentPoint.GetComponentInParent<SkinnedModelRenderer>( true );
		Follow();
	}

	protected override void OnUpdate() => Follow();

	/// <summary>
	/// Rides <see cref="GunsmithAttachmentPoint.StickerBone"/>, as the MW22 parts ride theirs: the point is placed in the
	/// model's bind space, and the sticker goes where the bone's animation has taken that spot. It's set relative to the
	/// point, which moves with the model, so when the camera places the viewmodel later in the frame the sticker goes
	/// with it.
	/// </summary>
	private void Follow()
	{
		if ( !weapon.IsValid() || !AttachmentPoint.IsValid() ) return;
		var pose = GunsmithMw22Attachment.BoneDelta( weapon, AttachmentPoint.StickerBone );
		var bindFrame = weapon.WorldTransform.ToLocal( AttachmentPoint.WorldTransform );
		LocalTransform = AttachmentPoint.WorldTransform.ToLocal( pose.ToWorld( bindFrame ) );
	}

	/// <summary>A quad facing +X, <see cref="Lift"/> off the point, drawn from both sides so it shows whichever way the point was authored.</summary>
	private static Model BuildQuad( Material material, float width, float height )
	{
		var w = width * 0.5f;
		var h = height * 0.5f;
		var normal = Vector3.Forward;
		var tangent = Vector3.Left;
		var vertices = new[]
		{
			new Vertex( new Vector3( Lift, -w, h ), normal, tangent, new Vector4( 0, 0, 0, 0 ) ),
			new Vertex( new Vector3( Lift, w, h ), normal, tangent, new Vector4( 1, 0, 0, 0 ) ),
			new Vertex( new Vector3( Lift, w, -h ), normal, tangent, new Vector4( 1, 1, 0, 0 ) ),
			new Vertex( new Vector3( Lift, -w, -h ), normal, tangent, new Vector4( 0, 1, 0, 0 ) ),
		};

		var mesh = new Mesh( material );
		mesh.CreateVertexBuffer( vertices.Length, vertices );
		mesh.CreateIndexBuffer( 12, new[] { 0, 1, 2, 2, 3, 0, 0, 3, 2, 2, 1, 0 } );
		mesh.Bounds = new BBox( new Vector3( 0f, -w, -h ), new Vector3( Lift * 2f, w, h ) );
		return Model.Builder.AddMesh( mesh ).Create();
	}
}
