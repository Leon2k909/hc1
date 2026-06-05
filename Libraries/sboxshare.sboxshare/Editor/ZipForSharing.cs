using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using Editor;
using Sandbox;

namespace Share;

public static class ZipForSharing
{
	[Event( "asset.contextmenu", Priority = 50 )]
	public static void OnAssetContextMenu( AssetContextMenu e )
	{
		var assets = e.SelectedList
			.Where( x => x.Asset is not null )
			.Select( x => x.Asset )
			.ToList();

		if ( assets.Count == 0 ) return;

		e.Menu.AddOption( assets.Count == 1 ? "Zip For Sharing" : $"Zip {assets.Count} Assets For Sharing", "archive", () =>
		{
			foreach ( var asset in assets )
				ZipAsset( asset );
		} );
	}

	static void ZipAsset( Asset asset )
	{
		var projectRoot = Project.Current?.GetRootPath();
		var contentRoot = Project.Current?.GetAssetsPath();

		if ( string.IsNullOrEmpty( projectRoot ) || string.IsNullOrEmpty( contentRoot ) )
		{
			Log.Warning( "[ZipForSharing] No current project" );
			return;
		}

		var codeRoot = Path.Combine( projectRoot, "Code" );

		// Collect the selected asset and all files it references, recursively.
		var assetFiles = new HashSet<string>( StringComparer.OrdinalIgnoreCase );
		CollectDependencies( asset.AbsolutePath, contentRoot, assetFiles );

		// Scan prefab/scene files for __type references and bundle matching .cs files.
		var codeFiles = new HashSet<string>( StringComparer.OrdinalIgnoreCase );
		foreach ( var filePath in assetFiles.Where( IsTypeReferenceFile ) )
			CollectCodeDependencies( filePath, codeRoot, codeFiles );

		if ( assetFiles.Count == 0 && codeFiles.Count == 0 )
		{
			Log.Warning( $"[ZipForSharing] No files collected for '{asset.Name}'" );
			return;
		}

		// Root asset files at their highest shared ancestor folder so relative paths are preserved.
		var commonPrefix = assetFiles.Count > 0 ? GetCommonDirectoryPrefix( assetFiles.ToList() ) : string.Empty;

		var exportDir = Path.Combine( projectRoot, "export" );
		Directory.CreateDirectory( exportDir );

		var safeName = Regex.Replace( asset.Name, @"[^\w\-]", "_" ).ToLower();
		var zipPath = Path.Combine( exportDir, $"{safeName}_share.zip" );

		try
		{
			if ( File.Exists( zipPath ) ) File.Delete( zipPath );

			using ( var zip = ZipFile.Open( zipPath, ZipArchiveMode.Create ) )
			{
				foreach ( var filePath in assetFiles )
				{
					var entryName = Path.GetRelativePath( commonPrefix, filePath ).Replace( '\\', '/' );
					zip.CreateEntryFromFile( filePath, entryName, CompressionLevel.Optimal );
					Log.Info( $"[ZipForSharing]   + {entryName}" );
				}
				foreach ( var filePath in codeFiles )
				{
					// Code files always go under code/ so ShareDropObject installs them to Code/.
					var entryName = "code/" + Path.GetFileName( filePath );
					zip.CreateEntryFromFile( filePath, entryName, CompressionLevel.Optimal );
					Log.Info( $"[ZipForSharing]   + {entryName}" );
				}
			}

			var total = assetFiles.Count + codeFiles.Count;
			Log.Info( $"[ZipForSharing] Created {total} file(s) ({codeFiles.Count} code) → {zipPath}" );

			Process.Start( new ProcessStartInfo
			{
				FileName = "explorer.exe",
				Arguments = $"/select,\"{zipPath}\"",
				UseShellExecute = true,
			} );
		}
		catch ( Exception ex )
		{
			Log.Warning( $"[ZipForSharing] Failed to create ZIP: {ex.Message}" );
		}
	}

	// Adds filePath to the visited set, then — for text-format source files — scans
	// for quoted path references and recurses into any that resolve on disk.
	static void CollectDependencies( string filePath, string contentRoot, HashSet<string> visited )
	{
		if ( !File.Exists( filePath ) ) return;
		if ( !visited.Add( filePath ) ) return; // already queued

		// Shader source files have a compiled counterpart (.shader → .shader.c).
		if ( Path.GetExtension( filePath ).Equals( ".shader", StringComparison.OrdinalIgnoreCase ) )
		{
			var compiledShader = filePath + "_c";
			if ( File.Exists( compiledShader ) )
				visited.Add( compiledShader );
		}

		if ( !IsSourceFile( filePath ) ) return; // binary — include but don't scan

		string content;
		try { content = File.ReadAllText( filePath ); }
		catch { return; }

		foreach ( Match match in Regex.Matches( content, @"""([^""\r\n]+\.[a-zA-Z0-9_]{1,10})""" ) )
		{
			var refPath = match.Groups[1].Value.Replace( '\\', '/' );

			// Try progressively shorter path suffixes so both "Share/models/chair.vmdl"
			// and "models/chair.vmdl" style references resolve correctly.
			var segments = refPath.Split( '/' );
			for ( var i = 0; i < segments.Length; i++ )
			{
				var suffix = string.Join( Path.DirectorySeparatorChar.ToString(), segments[i..] );
				var candidate = Path.Combine( contentRoot, suffix );
				if ( File.Exists( candidate ) )
				{
					CollectDependencies( candidate, contentRoot, visited );
					break;
				}
			}
		}
	}

	// Scans a prefab or scene file for __type references and finds matching .cs files under codeRoot.
	// Strips any namespace prefix so "MyGame.ChairPickup" -> looks for ChairPickup.cs.
	static void CollectCodeDependencies( string sourceFilePath, string codeRoot, HashSet<string> codeFiles )
	{
		if ( !Directory.Exists( codeRoot ) ) return;

		string content;
		try { content = File.ReadAllText( sourceFilePath ); }
		catch { return; }

		foreach ( Match match in Regex.Matches( content, @"""?__type""?\s*[=:]\s*""([^""]+)""" ) )
		{
			var typeName = match.Groups[1].Value.Split( '.' ).Last();
			foreach ( var f in Directory.GetFiles( codeRoot, $"{typeName}.cs", SearchOption.AllDirectories ) )
				codeFiles.Add( f );
		}
	}

	// Only prefab and scene files embed component __type references.
	static bool IsTypeReferenceFile( string path )
	{
		var ext = Path.GetExtension( path ).ToLower();
		return ext is ".prefab" or ".scene";
	}

	// Returns the deepest directory that is an ancestor of every path in the list.
	static string GetCommonDirectoryPrefix( List<string> paths )
	{
		if ( paths.Count == 1 )
			return Path.GetDirectoryName( paths[0] )!;

		var splitDirs = paths
			.Select( p => Path.GetDirectoryName( p )!.Split( Path.DirectorySeparatorChar ) )
			.ToList();

		var common = splitDirs[0].ToList();
		foreach ( var parts in splitDirs.Skip( 1 ) )
		{
			var len = Math.Min( common.Count, parts.Length );
			var trimmed = new List<string>();
			for ( var i = 0; i < len; i++ )
			{
				if ( string.Equals( common[i], parts[i], StringComparison.OrdinalIgnoreCase ) )
					trimmed.Add( common[i] );
				else
					break;
			}
			common = trimmed;
		}

		return string.Join( Path.DirectorySeparatorChar.ToString(), common );
	}

	static bool IsSourceFile( string path )
	{
		var ext = Path.GetExtension( path ).ToLower();
		return ext is ".vmat" or ".vmdl" or ".vmesh" or ".prefab" or ".scene"
		           or ".vpcf" or ".vsnd" or ".vsndevts" or ".vdata" or ".vpost";
	}
}
