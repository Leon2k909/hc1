namespace Facepunch;

/// <summary>Host-owned spray identity and transform; each viewer creates its own decal.</summary>
public sealed class SprayMark : Component
{
	[Sync( SyncFlags.FromHost )] public string SprayId { get; set; }
	private TimeSince _age = 0f;
	private string _drawnId;
	private Decal _decal;
	private static readonly Dictionary<string, DecalDefinition> Definitions = new();

	protected override void OnUpdate()
	{
		if ( Networking.IsHost && _age > SprayRules.Lifetime )
		{
			GameObject.Destroy();
			return;
		}
		if ( Application.IsDedicatedServer || _drawnId == SprayId ) return;
		var art = CosmeticCatalog.FindSpray( SprayId );
		if ( art is null ) return;
		if ( !Definitions.TryGetValue( art.Id, out var definition ) )
		{
			var image = Texture.Load( art.Image );
			if ( !image.IsValid() ) return;
			Definitions[art.Id] = definition = new DecalDefinition
			{
				ColorTexture = image, Width = 32f, Height = 32f, ColorMix = 1f, Tint = Color.White
			};
		}
		_decal ??= GameObject.Components.Create<Decal>();
		_decal.Flags |= ComponentFlags.NotSaved | ComponentFlags.NotNetworked;
		_decal.Decals = new() { definition };
		_decal.Size = new Vector2( 1f, 1f );
		_decal.Depth = 2f;
		_decal.Parallax = 0f;
		_decal.ColorTint = Color.White;
		_decal.ColorMix = 1f;
		_drawnId = art.Id;
	}
}
