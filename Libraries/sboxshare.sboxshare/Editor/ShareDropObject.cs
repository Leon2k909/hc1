using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Editor;
using Sandbox;

namespace Share;

[DropObject( "sharefile", "box" )]
public class ShareDropObject : BaseDropObject
{
	string assetName = "Dropped Asset";
	string downloadUrl;
	List<FileEntry> files = new();

	record FileEntry( string ZipPath, string InstallPath );

	protected override async Task Initialize( string dragData, CancellationToken token )
	{
		Log.Info( $"[ShareDrop] dragData: '{dragData}'" );

		var tempManifest = Path.Combine( Path.GetTempPath(), "sbox_drop_manifest.box" );
		var success = await EditorUtility.DownloadAsync( dragData.Trim(), tempManifest, token: token );

		if ( !success )
		{
			Log.Warning( "[ShareDrop] Failed to download manifest" );
			return;
		}

		try
		{
			var json = JsonDocument.Parse( File.ReadAllText( tempManifest ) );
			var root = json.RootElement;

			if ( root.TryGetProperty( "title", out var title ) )
				assetName = title.GetString() ?? assetName;

			if ( root.TryGetProperty( "download_url", out var url ) )
				downloadUrl = url.GetString();

			if ( root.TryGetProperty( "files", out var filesArr ) && filesArr.ValueKind == JsonValueKind.Array )
			{
				foreach ( var f in filesArr.EnumerateArray() )
				{
					var zipPath = f.TryGetProperty( "path", out var p ) ? p.GetString() : null;
					var installPath = f.TryGetProperty( "install_path", out var ip ) ? ip.GetString() : null;
					if ( zipPath != null && installPath != null )
						files.Add( new FileEntry( zipPath, installPath ) );
				}
			}
		}
		catch ( Exception e )
		{
			Log.Warning( $"[ShareDrop] Failed to parse manifest: {e.Message}" );
		}
	}

	public override async Task OnDrop()
	{
		await WaitForLoad();

		if ( string.IsNullOrEmpty( downloadUrl ) )
		{
			Log.Warning( "[ShareDrop] No download URL available" );
			return;
		}

		if ( files.Count > 0 )
			await DropZipPackage();
		else
			await DropSingleFile();
	}

	// New path: manifest has a files array — download ZIP, extract, install each file.
	async Task DropZipPackage()
	{
		var safeName = assetName.Replace( " ", "_" ).ToLower();
		var tempZip = Path.Combine( Path.GetTempPath(), $"{safeName}.zip" );

		if ( !await EditorUtility.DownloadAsync( downloadUrl, tempZip ) )
		{
			Log.Warning( $"[ShareDrop] Failed to download ZIP for '{assetName}'" );
			return;
		}

		var tempExtract = Path.Combine( Path.GetTempPath(), $"sbox_extract_{safeName}" );

		try
		{
			if ( Directory.Exists( tempExtract ) )
				Directory.Delete( tempExtract, recursive: true );

			ZipFile.ExtractToDirectory( tempZip, tempExtract, overwriteFiles: true );

			var projectRoot = Project.Current?.GetRootPath();
			if ( string.IsNullOrEmpty( projectRoot ) )
			{
				Log.Warning( "[ShareDrop] No current project root" );
				return;
			}
			var contentRoot = projectRoot + "/Assets/share";

			// Pass 1: copy every file from the ZIP to its install destination.
			var copied = new List<(FileEntry Entry, string DestPath)>();
			foreach ( var entry in files )
			{
				var srcPath = Path.Combine( tempExtract, entry.ZipPath.Replace( '/', Path.DirectorySeparatorChar ) );
				if ( !File.Exists( srcPath ) )
				{
					Log.Warning( $"[ShareDrop] Missing in ZIP: {entry.ZipPath}" );
					continue;
				}

				var relative = entry.InstallPath.TrimStart( '/' );
				string destPath;
				if ( relative.StartsWith( "code/", StringComparison.OrdinalIgnoreCase ) )
				{
					// Code files go to {projectRoot}/Code/
					var codeRelative = relative["code/".Length..];
					destPath = Path.Combine( projectRoot, "Code/Share", codeRelative.Replace( '/', Path.DirectorySeparatorChar ) );
				}
				else
				{
					if ( relative.StartsWith( "share/", StringComparison.OrdinalIgnoreCase ) )
						relative = relative["share/".Length..];
					destPath = Path.Combine( contentRoot, relative.Replace( '/', Path.DirectorySeparatorChar ) );
				}
				Directory.CreateDirectory( Path.GetDirectoryName( destPath ) );
				File.Copy( srcPath, destPath, overwrite: true );
				copied.Add( (entry, destPath) );
			}

			// Pass 2: rewrite stale path references inside text-format source files.
			var filenameMap = BuildFilenameMap( copied );
			foreach ( var (_, destPath) in copied )
			{
				if ( IsSourceFile( destPath ) )
					ApplyPathFixup( destPath, filenameMap );
			}

			// Pass 3: register every installed asset file with the asset system.
			// Code files (.cs) are skipped — the compiler picks them up automatically.
			Asset primaryAsset = null;
			foreach ( var (entry, destPath) in copied )
			{
				if ( !File.Exists( destPath ) ) continue;
				if ( Path.GetExtension( destPath ).Equals( ".cs", StringComparison.OrdinalIgnoreCase ) )
				{
					Log.Info( $"[ShareDrop] Installed code: {Path.GetFileName( destPath )}" );
					continue;
				}
				var asset = AssetSystem.RegisterFile( destPath );
				if ( asset is null )
				{
					Log.Warning( $"[ShareDrop] AssetSystem could not register {destPath}" );
					continue;
				}
				Log.Info( $"[ShareDrop] Installed: {asset.Path}" );
				primaryAsset ??= asset;
				if ( IsPrimaryAssetType( entry.InstallPath ) )
					primaryAsset = asset;
			}

			if ( primaryAsset is null )
				Log.Warning( "[ShareDrop] No assets were registered" );
			else
				Log.Info( $"[ShareDrop] Done. Primary asset: {primaryAsset.Path}" );
		}
		catch ( Exception e )
		{
			Log.Warning( $"[ShareDrop] Extraction failed: {e.Message}" );
		}
		finally
		{
			if ( Directory.Exists( tempExtract ) )
				Directory.Delete( tempExtract, recursive: true );
		}
	}

	// Indexes every installed file under all trailing suffixes of its ZipPath so
	// references like "wood.vmat", "materials/wood.vmat", or "props/materials/wood.vmat"
	// all resolve to the correct installed game-relative path — regardless of whether
	// the creator zipped from their project root or just the assets directly.
	// More-specific (longer) suffixes are written first and never overwritten.
	static Dictionary<string, string> BuildFilenameMap( List<(FileEntry Entry, string DestPath)> copied )
	{
		var map = new Dictionary<string, string>( StringComparer.OrdinalIgnoreCase );
		foreach ( var (entry, _) in copied )
		{
			var rel = entry.InstallPath.TrimStart( '/' );
			if ( rel.StartsWith( "share/", StringComparison.OrdinalIgnoreCase ) )
				rel = rel["share/".Length..];
			var gamePath = "share/" + rel.Replace( '\\', '/' );

			var segments = entry.ZipPath.Replace( '\\', '/' ).Split( '/' );
			for ( var i = 0; i < segments.Length; i++ )
			{
				var suffix = string.Join( "/", segments[i..] );
				if ( !map.ContainsKey( suffix ) )
					map[suffix] = gamePath;
			}
		}
		return map;
	}

	// Scans a text-format source file for quoted path references and rewrites any that
	// match an installed file, resolving from most-specific to least-specific suffix so
	// "models/wood.vmat" beats "wood.vmat" when both are in the map.
	static void ApplyPathFixup( string filePath, Dictionary<string, string> filenameMap )
	{
		try
		{
			var content = File.ReadAllText( filePath );
			var original = content;

			content = Regex.Replace( content, @"""([^""\r\n]+\.[a-zA-Z0-9_]{1,10})""", match =>
			{
				var refPath = match.Groups[1].Value.Replace( '\\', '/' );
				var segments = refPath.Split( '/' );
				for ( var i = 0; i < segments.Length; i++ )
				{
					var suffix = string.Join( "/", segments[i..] );
					if ( filenameMap.TryGetValue( suffix, out var newPath ) &&
					     !string.Equals( refPath, newPath, StringComparison.OrdinalIgnoreCase ) )
						return $"\"{newPath}\"";
				}
				return match.Value;
			} );

			if ( content != original )
				File.WriteAllText( filePath, content );
		}
		catch ( Exception e )
		{
			Log.Warning( $"[ShareDrop] Path fixup failed for {Path.GetFileName( filePath )}: {e.Message}" );
		}
	}

	// Returns true for text-format s&box source files that embed asset path references.
	static bool IsSourceFile( string path )
	{
		var ext = Path.GetExtension( path ).ToLower();
		return ext is ".vmat" or ".vmdl" or ".vmesh" or ".prefab" or ".scene"
		           or ".vpcf" or ".vsnd" or ".vsndevts" or ".vdata" or ".vpost";
	}

	// Legacy path: no files array — download the single file directly.
	async Task DropSingleFile()
	{
		var safeName = assetName.Replace( " ", "_" ).ToLower();
		var ext = Path.GetExtension( downloadUrl.Split( '?' )[0] );
		if ( string.IsNullOrEmpty( ext ) ) ext = ".bin";

		var tempPath = Path.Combine( Path.GetTempPath(), $"{safeName}{ext}" );
		if ( !await EditorUtility.DownloadAsync( downloadUrl, tempPath ) )
		{
			Log.Warning( $"[ShareDrop] Failed to download asset: {assetName}" );
			return;
		}

		try
		{
			var projectRoot = Project.Current?.GetRootPath();
			if ( string.IsNullOrEmpty( projectRoot ) )
			{
				Log.Warning( "[ShareDrop] No current project root" );
				return;
			}
			var contentDir = projectRoot + "/Assets/Share/";
			Directory.CreateDirectory( contentDir );
			var destPath = contentDir + safeName + ext;
			File.Copy( tempPath, destPath, overwrite: true );

			if ( !File.Exists( destPath ) )
			{
				Log.Warning( $"[ShareDrop] Dest file missing before register: {destPath}" );
				return;
			}

			var asset = AssetSystem.RegisterFile( destPath );
			asset.CompileIfNeededAsync( 30f );
			if ( asset is null )
			{
				Log.Warning( $"[ShareDrop] AssetSystem could not register {destPath}" );
				return;
			}

			Log.Info( $"[ShareDrop] Registered asset: {asset.Path}" );
		}
		catch ( Exception e )
		{
			Log.Warning( $"[ShareDrop] DropSingleFile failed: {e.Message}" );
		}
	}

	// Prefer .vmdl/.vmat/.prefab etc. over raw texture sources for the inspector selection.
	static bool IsPrimaryAssetType( string installPath )
	{
		var ext = Path.GetExtension( installPath ).ToLower();
		return ext is ".vmdl" or ".vmesh" or ".vmat" or ".prefab" or ".vsnd" or ".vsndevts" or ".vpcf" or ".vdata" or ".vpost";
	}
}
