namespace Facepunch;

public static class CosmeticPreferences
{
	private const string SprayCookie = "hc1.cosmetics.spray.v1";
	private const string LoadingCookie = "hc1.cosmetics.loading.v1";
	private const string ImageCookie = "hc1.cosmetics.loading-image.v1";
	public static int Version { get; private set; }
	private static string _appliedMedia;
	private static string _previousMedia;

	public static string SprayId => CosmeticCatalog.FindSpray( Game.Cookies.Get( SprayCookie, "precision" ) )?.Id ?? "precision";
	public static string LoadingId
	{
		get
		{
			var id = Game.Cookies.Get( LoadingCookie, "default" );
			return id == "custom" && CustomImage is not null ? id : CosmeticCatalog.FindLoadingScreen( id )?.Id ?? "default";
		}
	}
	public static string CustomImage => CosmeticCatalog.TryImageUrl( Game.Cookies.Get( ImageCookie, "" ), out var url ) ? url : null;
	public static string LoadingImage => LoadingId == "custom" ? CustomImage : CosmeticCatalog.FindLoadingScreen( LoadingId )?.Image;

	public static void SelectSpray( string id )
	{
		if ( CosmeticCatalog.FindSpray( id ) is null ) return;
		Game.Cookies.Set( SprayCookie, id );
		Version++;
	}
	public static void SelectLoadingScreen( string id )
	{
		if ( CosmeticCatalog.FindLoadingScreen( id ) is null ) return;
		Game.Cookies.Set( LoadingCookie, id );
		Version++;
		ApplyLoadingScreen();
	}
	public static bool SelectCustomImage( string text )
	{
		if ( !CosmeticCatalog.TryImageUrl( text, out var url ) ) return false;
		Game.Cookies.Set( ImageCookie, url );
		Game.Cookies.Set( LoadingCookie, "custom" );
		Version++;
		ApplyLoadingScreen();
		return true;
	}
	public static void ApplyLoadingScreen()
	{
		if ( Application.IsDedicatedServer ) return;
		var image = LoadingImage;
		if ( string.IsNullOrEmpty( image ) )
		{
			if ( _appliedMedia is not null && LoadingScreen.Media == _appliedMedia ) LoadingScreen.Media = _previousMedia;
			_appliedMedia = null;
			_previousMedia = null;
			return;
		}
		if ( LoadingScreen.Media == image ) return;
		if ( _appliedMedia is null || LoadingScreen.Media != _appliedMedia ) _previousMedia = LoadingScreen.Media;
		LoadingScreen.Media = _appliedMedia = image;
	}
}
