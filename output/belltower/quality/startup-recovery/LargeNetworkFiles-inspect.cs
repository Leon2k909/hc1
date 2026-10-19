using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Sandbox.Diagnostics;
using Sandbox.Internal;
using Sandbox.Network;
using Sandbox.Utility;

namespace Sandbox;

[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 8)]
internal class LargeNetworkFiles
{
	private record struct LargeFileInfo(long Size, ulong CRC);

	[Expose]
	public record struct RequestFile(string filename);

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 17)]
	private HashSet<string> downloadQueue = new HashSet<string>();

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 10)]
	public BaseFileSystem Files { get; private set; }

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 11)]
	public StringTable StringTable { get; init; }

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 15)]
	private RedirectFileSystem RedirectFileSystem { get; set; }

	public LargeNetworkFiles(string name)
	{
		StringTable = new StringTable(name, compressed: true);
		StringTable stringTable = StringTable;
		stringTable.OnChangeOrAdd = (Action<StringTable.Entry>)Delegate.Combine(stringTable.OnChangeOrAdd, new Action<StringTable.Entry>(OnTableEntryUpdated));
		StringTable stringTable2 = StringTable;
		stringTable2.OnRemoved = (Action<StringTable.Entry>)Delegate.Combine(stringTable2.OnRemoved, new Action<StringTable.Entry>(OnTableEntryRemoved));
		StringTable stringTable3 = StringTable;
		stringTable3.OnSnapshot = (Action)Delegate.Combine(stringTable3.OnSnapshot, new Action(OnTableSnapshot));
	}

	/// <summary>
	/// Reset the string table.
	/// </summary>
	[Description("Reset the string table.")]
	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 30)]
	public void Reset()
	{
		StringTable.Reset();
		Files?.Dispose();
		RedirectFileSystem = AssetDownloadCache.CreateRedirectFileSystem();
		Files = new BaseFileSystem(RedirectFileSystem);
	}

	/// <summary>
	/// Add all files from the network.
	/// </summary>
	[Description("Add all files from the network.")]
	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 42)]
	public void Refresh()
	{
		foreach (var (_, entry2) in StringTable.Entries)
		{
			AddFileToFileSystem(entry2.Name, entry2.Read<LargeFileInfo>());
		}
	}

	/// <summary>
	/// Add a file from the mounted filesystem used to serve download requests.
	/// </summary>
	[Description("Add a file from the mounted filesystem used to serve download requests.")]
	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 53)]
	public bool AddFile(BaseFileSystem mounted, string fileName)
	{
		Stream stream;
		try
		{
			stream = mounted.OpenRead(fileName);
		}
		catch (FileNotFoundException)
		{
			return false;
		}
		catch (DirectoryNotFoundException)
		{
			return false;
		}
		if (stream == null)
		{
			return false;
		}
		using (stream)
		{
			long length = stream.Length;
			ulong cRC = Crc64.FromStream(stream);
			string name = NormalizeFileName(fileName);
			StringTable.Set(name, new LargeFileInfo(length, cRC));
			if (AssetDownloadCache.DebugNetworkFiles)
			{
				GlobalSystemNamespace.Log.Info($"Adding LARGE File {fileName} ({length.FormatBytes()})");
			}
		}
		return true;
	}

	/// <summary>
	/// Remove a networked file.
	/// </summary>
	[Description("Remove a networked file.")]
	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 88)]
	public void RemoveFile(string fileName)
	{
		string name = NormalizeFileName(fileName);
		StringTable.Remove(name);
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 94)]
	private string NormalizeFileName(string fileName)
	{
		return BaseFileSystem.NormalizeFilename(fileName).TrimStart('/');
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 99)]
	private void OnTableEntryUpdated(StringTable.Entry entry)
	{
		AddFileToFileSystem(entry.Name, entry.Read<LargeFileInfo>());
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 104)]
	private void OnTableEntryRemoved(StringTable.Entry entry)
	{
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 109)]
	private void OnTableSnapshot()
	{
		GlobalSystemNamespace.Log.Info("Checking for network files..");
		Stopwatch stopwatch = Stopwatch.StartNew();
		Refresh();
		GlobalSystemNamespace.Log.Info($"..done in {stopwatch.Elapsed.TotalSeconds:0.00}s");
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 119)]
	private void AddFileToFileSystem(string fileName, LargeFileInfo contents)
	{
		if (EngineFileSystem.Mounted.FileExists(fileName) && EngineFileSystem.Mounted.FileSize(fileName) == contents.Size && EngineFileSystem.Mounted.GetCrc(fileName) == contents.CRC)
		{
			if (AssetDownloadCache.DebugNetworkFiles)
			{
				GlobalSystemNamespace.Log.Info($"Skipping downloading {fileName} - we already have it");
			}
		}
		else if (AssetDownloadCache.IsLegalDownload(fileName) && !AssetDownloadCache.TryMount(RedirectFileSystem, fileName, contents.CRC))
		{
			if (AssetDownloadCache.DebugNetworkFiles)
			{
				GlobalSystemNamespace.Log.Info($"Queued Network File: {fileName} / {contents.Size} / {contents.CRC}");
			}
			downloadQueue.Add(fileName);
		}
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 153)]
	public async Task RunDownloadQueue(NetworkSystem system, CancellationToken token)
	{
		if (RedirectFileSystem == null)
		{
			return;
		}
		Assert.NotNull(Connection.Host);
		GlobalSystemNamespace.Log.Info($"Downloading {downloadQueue.Count} files..");
		int currentCount = 0;
		Stopwatch sw = Stopwatch.StartNew();
		foreach (string file in downloadQueue)
		{
			if (!StringTable.Entries.TryGetValue(file, out var value))
			{
				continue;
			}
			LargeFileInfo info = value.Read<LargeFileInfo>();
			if (AssetDownloadCache.DebugNetworkFiles)
			{
				GlobalSystemNamespace.Log.Info($"Download file {file}");
			}
			LoadingScreen.Title = $"Downloading Files ({currentCount + 1}/{downloadQueue.Count})";
			LoadingScreen.Subtitle = file;
			if (RedirectFileSystem.FileExists(file.NormalizeFilename()))
			{
				currentCount++;
				continue;
			}
			token.ThrowIfCancellationRequested();
			if (Connection.Host == null)
			{
				throw new TaskCanceledException("Connection became null");
			}
			object obj = await Connection.Host.SendRequest(new RequestFile
			{
				filename = file
			});
			token.ThrowIfCancellationRequested();
			if (!(obj is byte[] array) || array.Length == 0)
			{
				GlobalSystemNamespace.Log.Warning($"Failed to download file {file}! (response: {obj})");
				currentCount++;
				continue;
			}
			string text = AssetDownloadCache.StoreFile(file, info.CRC, array);
			if (text != null)
			{
				RedirectFileSystem.AddAbsFile(file, text);
			}
			currentCount++;
		}
		LoadingScreen.Subtitle = null;
		GlobalSystemNamespace.Log.Info($"Download Complete ({currentCount} files total) ({sw.Elapsed.TotalSeconds:0.00}s)");
		downloadQueue.Clear();
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 219)]
	internal void NetworkInitialize(GameNetworkSystem instance)
	{
		instance.AddHandler((Func<RequestFile, Connection, Guid, Task>)OnRequestNetworkFile);
	}

	[SourceLocation("Systems\\Networking\\Tables\\LargeNetworkFiles.cs", 224)]
	private async Task OnRequestNetworkFile(RequestFile file, Connection connection, Guid msgGuid)
	{
		if (!EngineFileSystem.Mounted.FileExists(file.filename))
		{
			GlobalSystemNamespace.Log.Warning($"Client ({connection.Name}) requested missing file: {file.filename}");
			connection.SendResponse(msgGuid, Array.Empty<byte>());
		}
		else
		{
			connection.SendResponse(msgGuid, await EngineFileSystem.Mounted.ReadAllBytesAsync(file.filename));
		}
	}
}
