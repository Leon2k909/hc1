using System;
using System.IO;
using System.Text.RegularExpressions;
using Sandbox.Internal;

namespace Sandbox;

/// <summary>
/// Downloadeded assets go in the ".source2/assets" folder, where they are symlinked on demand
/// for use by the engine.
/// </summary>
[Description("Downloadeded assets go in the \".source2/assets\" folder, where they are symlinked on demand for use by the engine.")]
[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 10)]
internal static class AssetDownloadCache
{
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 15)]
	private static string cacheFolder;

	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 104)]
	private static string[] _neverDownloadExtensions = new string[11]
	{
		".dll", ".exe", ".bat", ".cmd", ".msi", ".scr", ".com", ".cpl", ".vbs", ".ps1",
		".reg"
	};

	/// <summary>
	/// <see cref="M:Sandbox.AssetDownloadCache.ResolveCached(System.String,System.UInt64)" />'s answer for a file core content already has, so nothing needs mounting.
	/// </summary>
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 145)]
	internal static readonly string CoreContent = "core";

	[SkipHotload]
	private static Action<bool> __DebugNetworkFiles_ConVarAttribute__CachedSetter = null;

	[SkipHotload]
	private static Func<bool> __DebugNetworkFiles_ConVarAttribute__CachedSetterGetter = null;

	[SkipHotload]
	private static Func<bool> __DebugNetworkFiles_ConVarAttribute__CachedGetter = null;

	[SkipHotload]
	private static readonly Attribute[] __DebugNetworkFiles__Attrs = new Attribute[2]
	{
		new ConVarAttribute("debug_network_files", ConVarFlags.Protected),
		new ConVarAttribute("debug_network_files", ConVarFlags.Protected)
	};

	[ConVar("debug_network_files", ConVarFlags.Protected)]
	[DefaultValue(false)]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 12)]
	internal static bool DebugNetworkFiles
	{
		get
		{
			WrappedPropertyGet<bool> p = new WrappedPropertyGet<bool>
			{
				Value = ((Func<bool>)(() => field))(),
				Object = null,
				IsStatic = true,
				TypeName = "Sandbox.AssetDownloadCache",
				PropertyName = "DebugNetworkFiles",
				MemberIdent = 713666886,
				Attributes = __DebugNetworkFiles__Attrs
			};
			return ConsoleSystem.OnWrappedGet(in p);
		}
		set
		{
			WrappedPropertySet<bool> p = new WrappedPropertySet<bool>
			{
				Value = value,
				Object = null,
				Setter = (bool v) =>
				{
					field = v;
				},
				Getter = () => DebugNetworkFiles,
				IsStatic = true,
				TypeName = "Sandbox.AssetDownloadCache",
				PropertyName = "DebugNetworkFiles",
				MemberIdent = 713666886,
				Attributes = __DebugNetworkFiles__Attrs
			};
			ConsoleSystem.OnWrappedSet(in p);
		}
	} = false;

	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 17)]
	public static void Initialize(string folder)
	{
		Directory.CreateDirectory(folder);
		cacheFolder = folder;
	}

	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 23)]
	internal static RedirectFileSystem CreateRedirectFileSystem()
	{
		if (string.IsNullOrEmpty(cacheFolder))
		{
			return null;
		}
		return RedirectFileSystem.Create(cacheFolder);
	}

	/// <summary>
	/// We have downloaded an asset file. Store it for reuse in the future
	/// </summary>
	[Description("We have downloaded an asset file. Store it for reuse in the future")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 34)]
	public static string StoreFile(string relativePath, ulong crc, byte[] data)
	{
		string path = CreateCacheFilename(relativePath, crc);
		string text = Path.Combine(cacheFolder, path);
		Directory.CreateDirectory(Path.GetDirectoryName(text));
		File.WriteAllBytes(text, data);
		return text;
	}

	/// <summary>
	/// Try to mount the downloaded file with this path and crc. If it doesn't exist, return false
	/// </summary>
	[Description("Try to mount the downloaded file with this path and crc. If it doesn't exist, return false")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 54)]
	public static bool IsFileDownloaded(string relativePath, ulong crc, out bool isCoreContent)
	{
		isCoreContent = false;
		relativePath = relativePath.NormalizeFilename().Trim(new char[2] { '/', '\\' });
		if (EngineFileSystem.CoreContent.FileExists(relativePath) && EngineFileSystem.CoreContent.GetCrc(relativePath) == crc)
		{
			isCoreContent = true;
			return true;
		}
		string path = CreateCacheFilename(relativePath, crc);
		if (!File.Exists(Path.Combine(cacheFolder, path)))
		{
			return false;
		}
		return true;
	}

	/// <summary>
	/// Makes sure the directory exists, and returns the relative path to this file
	/// </summary>
	[Description("Makes sure the directory exists, and returns the relative path to this file")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 83)]
	public static string CreateCacheFilename(string filePath, ulong crc)
	{
		string extension = Path.GetExtension(filePath);
		int length = extension.Length;
		string input = filePath.Substring(0, filePath.Length - length);
		input = Regex.Replace(input, "[^a-zA-Z0-9/]", "_");
		input = input.TrimStart(new char[2] { '/', '\\' });
		return $"{input}.{crc:x}{extension}";
	}

	/// <summary>
	/// Generate the absolute path for this, whether it exists or not
	/// </summary>
	[Description("Generate the absolute path for this, whether it exists or not")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 98)]
	internal static string GetAbsolutePath(string path, ulong crc)
	{
		return Path.Combine(cacheFolder, CreateCacheFilename(path, crc));
	}

	/// <summary>
	/// Is a file an legal download or not (filter out executables etc)
	/// </summary>
	[Description("Is a file an legal download or not (filter out executables etc)")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 109)]
	internal static bool IsLegalDownload(string path)
	{
		if (string.IsNullOrWhiteSpace(path))
		{
			return false;
		}
		if (path.Length < 3)
		{
			return false;
		}
		if (path.Contains(".."))
		{
			return false;
		}
		string extension = Path.GetExtension(path);
		if (string.IsNullOrWhiteSpace(extension))
		{
			return false;
		}
		if (_neverDownloadExtensions.Contains(extension, StringComparer.OrdinalIgnoreCase))
		{
			return false;
		}
		return true;
	}

	/// <summary>
	/// Given a file with a crc, create a unique cache filename for it
	/// </summary>
	[Description("Given a file with a crc, create a unique cache filename for it")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 128)]
	internal static string CreateGameCacheFilename(string path, string crc)
	{
		return path.ToLowerInvariant().Md5() + "." + crc + ".cache";
	}

	/// <summary>
	/// Is this file in the game cache, core content or the download cache, without mounting it
	/// </summary>
	[Description("Is this file in the game cache, core content or the download cache, without mounting it")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 136)]
	internal static bool IsCached(string path, ulong crc)
	{
		string path2 = "/gamecache/" + CreateGameCacheFilename(path, crc.ToString("x"));
		bool isCoreContent;
		if (!EngineFileSystem.Root.FileExists(path2))
		{
			return IsFileDownloaded(path, crc, out isCoreContent);
		}
		return true;
	}

	/// <summary>
	/// Where a cached copy of this file is: the absolute path in the game or download cache,
	/// <see cref="F:Sandbox.AssetDownloadCache.CoreContent" />, or null when it has to be downloaded. Only reads, safe off the main thread.
	/// </summary>
	[Description("Where a cached copy of this file is: the absolute path in the game or download cache, <span style=\"color: #4EC9B0;\">AssetDownloadCache</span>.<span style=\"color: #DCDCDC;\">CoreContent</span>, or null when it has to be downloaded. Only reads, safe off the main thread.")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 151)]
	internal static string ResolveCached(string path, ulong crc)
	{
		string path2 = "/gamecache/" + CreateGameCacheFilename(path, crc.ToString("x"));
		if (EngineFileSystem.Root.FileExists(path2))
		{
			return EngineFileSystem.Root.GetFullPath(path2);
		}
		if (!IsFileDownloaded(path, crc, out var isCoreContent))
		{
			return null;
		}
		if (!isCoreContent)
		{
			return GetAbsolutePath(path, crc);
		}
		return CoreContent;
	}

	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 163)]
	internal static bool TryMount(RedirectFileSystem fs, string path, ulong crc)
	{
		string text = ResolveCached(path, crc);
		if (text == null)
		{
			return false;
		}
		Mount(fs, path, text);
		return true;
	}

	/// <summary>
	/// Mount a file at what <see cref="M:Sandbox.AssetDownloadCache.ResolveCached(System.String,System.UInt64)" /> found for it.
	/// </summary>
	[Description("Mount a file at what <span style=\"color: #4EC9B0;\">AssetDownloadCache</span>.<span style=\"color: #DCDCAA;\">ResolveCached</span>(<span style=\"color: #4EC9B0;\">string</span>,<span style=\"color: #86C691;\">ulong</span>) found for it.")]
	[SourceLocation("Systems\\Filesystem\\AssetDownloadCache.cs", 175)]
	internal static void Mount(RedirectFileSystem fs, string path, string resolved)
	{
		if ((object)resolved != CoreContent)
		{
			fs.AddAbsFile(path.NormalizeFilename(), resolved);
		}
	}
}
