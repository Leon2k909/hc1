namespace Facepunch.Gunsmith;

public partial class GunsmithPart
{
	/// <summary>
	/// A list of every single gunsmith part.
	/// </summary>
	public static HashSet<GunsmithPart> All { get; set; } = new();

	/// <summary>
	/// A list of every single gunsmith part, mapped by type.
	/// </summary>
	public static Dictionary<GunsmithPartType, HashSet<GunsmithPart>> Categories { get; set; } = new();

	/// <summary>
	/// Bumped whenever a part loads or reloads: what's kept from the parts (GunsmithLoadoutManager's index and fitted
	/// parts, <see cref="AttachmentUnlocks"/>' ladders) is made again.
	/// </summary>
	public static int LibraryVersion { get; private set; }

	private static void LibraryChanged()
	{
		LibraryVersion++;
		GunsmithLoadoutManager.MarkChanged();
	}

	protected override void PostReload() => LibraryChanged();

	protected override void PostLoad()
	{
		LibraryChanged();

		if ( !All.Contains( this ) )
		{
			All.Add( this );
		}

		if ( Categories.TryGetValue( Category, out var list ) )
		{
			list.Add( this );
		}
		else
		{
			Categories.TryAdd( this.Category, new()
			{
				this
			} );
		}		
	}
}
