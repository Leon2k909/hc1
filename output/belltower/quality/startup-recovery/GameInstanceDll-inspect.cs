using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using NativeEngine;
using Sandbox.Audio;
using Sandbox.Diagnostics;
using Sandbox.Engine;
using Sandbox.Generator;
using Sandbox.Internal;
using Sandbox.Modals;
using Sandbox.Mounting;
using Sandbox.Network;
using Sandbox.Platform;
using Sandbox.Services;
using Sandbox.Speech;
using Sandbox.Tasks;
using Sandbox.UI;
using Sandbox.Utility;
using Sandbox.VR;

namespace Sandbox;

internal class GameInstanceDll : IGameInstanceDll
{
	public static GameInstance gameInstance;

	private bool _isAssemblyLoadingPaused;

	private CancellationTokenSource _loadGameCts;

	private Task<bool> _loadGameTask;

	private static int Counter;

	internal Input.Context _perFrameInput = Input.Context.Create("ClientPerFrame");

	private readonly StringTable CodeArchiveTable = new StringTable("CodeArchive", compressed: true);

	internal readonly ServerPackages ServerPackages = new ServerPackages();

	/// <summary>
	/// The config table is used to send config (like physics config, input config) to the client.
	/// This isn't always needed, because the config is loaded from the package. But if we're operating
	/// without a package, it is needed.
	/// </summary>
	private readonly StringTable ConfigTable = new StringTable("Config", compressed: true);

	/// <summary>
	/// Hold and network any small files such as StyleSheets and compiled prefab assets.
	/// </summary>
	private readonly SmallNetworkFiles NetworkedSmallFiles = new SmallNetworkFiles("SmallFiles");

	/// <summary>
	/// Hold and network any files from Project Settings (.config files.)
	/// </summary>
	private readonly SmallNetworkFiles NetworkedConfigFiles = new SmallNetworkFiles("ConfigFiles");

	/// <summary>
	/// Hold and network any localization files.
	/// </summary>
	private readonly SmallNetworkFiles NetworkedLangFiles = new SmallNetworkFiles("LangFiles");

	/// <summary>
	/// Hold and network any small files such as StyleSheets and compiled prefab assets.
	/// </summary>
	private readonly LargeNetworkFiles NetworkedLargeFiles = new LargeNetworkFiles("LargeFiles");

	/// <summary>
	/// Hold and network any small files such as StyleSheets and compiled prefab assets.
	/// </summary>
	private readonly ReplicatedConvars ReplicatedConvars = new ReplicatedConvars("ReplicatedConvars");

	/// <summary>
	/// This is used to compile code archives that come in from the network.
	/// </summary>
	private CompileGroup compileGroup;

	private static string[] _interestingExtensions = new string[3] { "_c", ".scss", ".ttf" };

	private static string[] _engineAssets = new string[8] { "vtex_c", "vmat_c", "vsnd_c", "vmdl_c", "vphys_c", "vpk", "vanmgrph_c", "shader_c" };

	private List<string> _netIncludePaths = new List<string>();

	public static GameInstanceDll Current { get; private set; }

	public static PackageLoader PackageLoader { get; set; }

	private PackageLoader.Enroller AssemblyEnroller { get; set; }

	public TypeLibrary TypeLibrary => GlobalGameNamespace.TypeLibrary;

	public InputContext InputContext { get; private set; }

	private List<FileWatch> FileWatchers { get; set; } = new List<FileWatch>();

	private bool DidMountNetworkedFiles { get; set; }

	/// <summary>
	/// What we enumerate for files to offer joining clients: the game's content plus any local
	/// libraries. We own this so it needs disposing, the filesystems mounted into it don't.
	/// </summary>
	internal AggregateFileSystem NetworkedFileSystem { get; private set; }

	/// <summary>
	/// Read the json configurations from the network table and apply them.
	/// To encourage a single path, this is called on the host too - even if they're
	/// not hosting a multiplayer game!
	/// </summary>
	private void UpdateConfigFromNetworkTable()
	{
		if (ConfigTable.Entries.TryGetValue("input", out var value))
		{
			Input.ReadConfig(value.ReadJson<InputSettings>());
		}
	}

	/// <summary>
	/// Called when loading a game or when a localproject has been modified while playing a game.
	/// </summary>
	public void UpdateProjectConfig(Package package)
	{
		InputSettings inputSettings = ProjectSettings.Input;
		if (inputSettings == null)
		{
			inputSettings = new InputSettings();
			inputSettings.InitDefault();
		}
		ConfigTable.SetJson("input", inputSettings);
		UpdateConfigFromNetworkTable();
	}

	/// <summary>
	/// Called when the config for a game project has been changed. 
	/// We might need to update the config table.
	/// </summary>
	public void OnProjectConfigChanged(Package package)
	{
		if (IGameInstance.Current != null)
		{
			UpdateProjectConfig(package);
		}
	}

	public void Bootstrap()
	{
		Current = this;
		GlobalContext.Current.Reset();
		GlobalContext.Current.LocalAssembly = GetType().Assembly;
		Game.InitHost();
		SetupInputContext();
		JsonUpgrader.UpdateUpgraders(TypeLibrary);
		Processor.DefaultPackageAssetResolver = ResolvePackageAsset;
		PackageManager.OnPackageInstalledToContext += OnPackageInstalled;
		GlobalContext.Current.FileMount = new AggregateFileSystem();
		if (Application.IsEditor)
		{
			FileSystem.Mounted.Mount(EngineFileSystem.LibraryContent);
		}
		FileSystem.Mounted.CreateAndMount(EngineFileSystem.Root, "/core/");
		if (!Application.IsStandalone)
		{
			FileSystem.Mounted.CreateAndMount(EngineFileSystem.Root, "/addons/citizen/Assets/");
		}
		if (Application.IsEditor)
		{
			FileSystem.Mounted.CreateAndMount(EngineFileSystem.Root, "/addons/editor/assets/");
		}
		PackageLoader?.Dispose();
		PackageLoader = new PackageLoader("GameMenu", typeof(GameInstanceDll).Assembly);
		PackageLoader.HotloadWatch(Game.GameAssembly);
		PackageLoader.OnAfterHotload = OnAfterHotload;
		ConVarSystem.AddAssembly(Game.GameAssembly, "game");
	}

	public async Task Initialize()
	{
		ResetEnvironment();
		Networking.StartThread();
		if (!Application.IsStandalone)
		{
			await MountConfig.Mount();
		}
	}

	public void Exiting()
	{
		Networking.Disconnect();
		Networking.StopThread();
		Event.Run("app.exit");
		Game.Cookies?.Save();
		if (InputContext != null)
		{
			InputContext.KeyboardFocusPanel = null;
			InputContext.MouseFocusPanel = null;
			InputContext = null;
		}
	}

	private void OnAfterHotload()
	{
		GlobalContext.Current.OnHotload();
		Game.ActiveScene?.OnHotload();
		Event.Run("hotloaded");
	}

	/// <summary>
	/// Called from the code generator. The game package should already contain this package's content
	/// so we just need to work out where it's meant to point to
	/// </summary>
	private string ResolvePackageAsset(string packageName)
	{
		return Package.FetchAsync(packageName, partial: false).Result?.PrimaryAsset;
	}

	/// <summary>
	/// This should reset our environment to a clean state.
	/// </summary>
	public void ResetEnvironment()
	{
		bool flag = gameInstance != null || AssemblyEnroller != null || DidMountNetworkedFiles;
		using (GlobalContext.GameScope())
		{
			GlobalGameNamespace.Log.Trace("Game Menu - ResetEnvironment");
			if (!PackageLoader.ToolsMode)
			{
				PackageLoader?.Dispose();
				PackageLoader = null;
				PackageLoader = new PackageLoader("GameMenu", typeof(GameInstanceDll).Assembly);
				PackageLoader.HotloadWatch(Game.GameAssembly);
				PackageLoader.OnAfterHotload = OnAfterHotload;
			}
			ResourceLoader.Clear();
			if (DidMountNetworkedFiles)
			{
				EngineFileSystem.Mounted.UnMount(NetworkedLargeFiles.Files);
				EngineFileSystem.Mounted.UnMount(NetworkedSmallFiles.Files);
				EngineFileSystem.ProjectSettings.UnMount(NetworkedConfigFiles.Files);
				DidMountNetworkedFiles = false;
			}
			FontManager.Instance.Clear(removeMenu: false);
			FontManager.Instance.LoadAll(FileSystem.Mounted);
			AssemblyEnroller?.Dispose();
			AssemblyEnroller = null;
			CodeArchiveTable.Reset();
			NetworkedSmallFiles.Reset();
			NetworkedConfigFiles.Reset();
			NetworkedLangFiles.Reset();
			NetworkedLargeFiles.Reset();
			ReplicatedConvars.Reset();
			ServerPackages.Clear();
			FileWatchers.ForEach((FileWatch w) =>
			{
				w.Dispose();
			});
			FileWatchers.Clear();
			NetworkedFileSystem?.Dispose();
			NetworkedFileSystem = null;
			Screen.UpdateFromEngine();
			Game.InitTypeLibrary();
			UserPermission.Load();
			Input.ReadConfig(null);
			StyleSheet.ResetStyleSheets();
			Networking.Reset();
			Connection.Reset();
			GlobalContext.Current.Reset();
			NativeResourceCache.Clear();
			Recognition.Reset();
			Json.Initialize();
			VRSystem.Reset();
			if (!Application.IsEditor)
			{
				Mixer.ResetToDefault();
			}
			Sound.Clear();
			Application.ClearGame();
			ReflectionQueryCache.ClearTypeCache();
			EngineFileSystem.ProjectSettings?.Dispose();
			EngineFileSystem.ProjectSettings = null;
			ProjectSettings.ClearCache();
			ErrorReporter.ResetCounters();
			AssemblyEnroller = PackageLoader.CreateEnroller($"gamedll{Counter++}");
			PackageLoader.Enroller assemblyEnroller = AssemblyEnroller;
			assemblyEnroller.OnAssemblyAdded = (Action<LoadedAssembly>)Delegate.Combine(assemblyEnroller.OnAssemblyAdded, (Action<LoadedAssembly>)((LoadedAssembly a) =>
			{
				Assert.NotNull(a.Assembly);
				if (!a.IsEditorAssembly)
				{
					Game.TypeLibrary.AddAssembly(a.Assembly, isDynamic: true);
					Game.NodeLibrary.AddAssembly(a.Assembly);
					ConVarSystem.AddAssembly(a.Assembly, "game");
					Cloud.UpdateTypes(a.Assembly);
					JsonUpgrader.UpdateUpgraders(TypeLibrary);
					if (!a.IsEditorAssembly && a.CodeArchiveBytes != null)
					{
						AddArchiveToCodeArchiveTable(a);
					}
					ReplicatedConvars.OnAssembliesLoaded();
				}
			}));
			PackageLoader.Enroller assemblyEnroller2 = AssemblyEnroller;
			assemblyEnroller2.OnAssemblyRemoved = (Action<LoadedAssembly>)Delegate.Combine(assemblyEnroller2.OnAssemblyRemoved, (Action<LoadedAssembly>)((LoadedAssembly a) =>
			{
				if (!a.IsEditorAssembly)
				{
					Assert.NotNull(a.Assembly);
					Game.NodeLibrary.RemoveAssembly(a.Assembly);
					Game.TypeLibrary.RemoveAssembly(a.Assembly);
					ConVarSystem.RemoveAssembly(a.Assembly);
					JsonUpgrader.UpdateUpgraders(TypeLibrary);
					CodeArchiveTable.Remove(a.Name);
				}
			}));
			PackageLoader.Enroller assemblyEnroller3 = AssemblyEnroller;
			assemblyEnroller3.OnAssemblyFastHotload = (Action<LoadedAssembly>)Delegate.Combine(assemblyEnroller3.OnAssemblyFastHotload, (Action<LoadedAssembly>)((LoadedAssembly a) =>
			{
				if (!a.IsEditorAssembly && a.CodeArchiveBytes != null)
				{
					AddArchiveToCodeArchiveTable(a);
				}
			}));
			IMenuDll.Current?.Reset();
			if (flag)
			{
				GC.Collect();
				GC.WaitForPendingFinalizers();
				MainThread.RunQueues();
			}
		}
	}

	/// <summary>
	/// This method grabs the currently loaded assembly's code archive, strips serverside code and spits it back out into the 
	/// CodeArchiveTable.
	/// </summary>
	/// <param name="a"></param>
	private void AddArchiveToCodeArchiveTable(LoadedAssembly a)
	{
		if (a?.CodeArchiveBytes == null || (!Application.IsEditor && (!Application.IsDedicatedServer || !(Application.GamePackage is LocalPackage))))
		{
			return;
		}
		if (!Application.IsDedicatedServer || !a.IsGame)
		{
			CodeArchiveTable.Set(a.Name, a.CodeArchiveBytes);
			return;
		}
		Compiler compiler = Project.All.Select((Project x) => x.Compiler).FirstOrDefault((Compiler x) => x?.AssemblyName.Equals(a.Name) ?? false);
		if (compiler?.Output?.Archive == null)
		{
			CodeArchiveTable.Set(a.Name, a.CodeArchiveBytes);
			return;
		}
		Compiler.Configuration configuration = compiler.GetConfiguration();
		HashSet<string> preprocessorSymbols = configuration.GetPreprocessorSymbols();
		preprocessorSymbols.RemoveWhere((string x) => x.Equals("SERVER", StringComparison.OrdinalIgnoreCase));
		Compiler.Configuration configuration2 = configuration;
		configuration2.DefineConstants = string.Join(";", preprocessorSymbols);
		Compiler.Configuration configuration3 = configuration2;
		CodeArchive codeArchive = new CodeArchive
		{
			CompilerName = compiler.Name,
			Configuration = configuration3
		};
		foreach (SyntaxTree syntaxTree in compiler.Output.Archive.SyntaxTrees)
		{
			SyntaxTree tree = CSharpSyntaxTree.ParseText(syntaxTree.GetText().ToString(), path: syntaxTree.FilePath, encoding: Encoding.UTF8, options: configuration3.GetParseOptions());
			tree = Compiler.StripDisabledTextTrivia(tree);
			codeArchive.SyntaxTrees.Add(tree);
		}
		foreach (CodeArchive.AdditionalFile additionalFile in compiler.Output.Archive.AdditionalFiles)
		{
			codeArchive.AdditionalFiles.Add(additionalFile);
		}
		foreach (KeyValuePair<string, string> item in compiler.Output.Archive.FileMap)
		{
			codeArchive.FileMap[item.Key] = item.Value;
		}
		foreach (string reference in compiler.Output.Archive.References)
		{
			codeArchive.References.Add(reference);
		}
		byte[] assemblyBytes = codeArchive.Serialize();
		CodeArchiveTable.Set(a.Name, assemblyBytes);
	}

	/// <summary>
	/// Don't attempt to load new assemblies during <see cref="M:Sandbox.GameInstanceDll.Tick" /> inside this scope.
	/// </summary>
	private DisposeAction PauseLoadingAssemblies()
	{
		if (_isAssemblyLoadingPaused)
		{
			return default;
		}
		_isAssemblyLoadingPaused = true;
		return new DisposeAction(() =>
		{
			_isAssemblyLoadingPaused = false;
		});
	}

	public void FinishLoadingAssemblies()
	{
		PackageLoader.Tick();
		Networking.System?.SendTableUpdates();
	}

	public void CloseGame()
	{
		Api.Activity.LoadAbandoned(null);
		CancelLoad();
		if (gameInstance == null)
		{
			return;
		}
		using (GlobalContext.GameScope())
		{
			LeaveGame(disconnect: true);
			LoadingScreen.IsVisible = false;
			LoadingScreen.Media = null;
			ResetEnvironment();
			MountUtility.TickPreviewRenders();
		}
	}

	/// <summary>
	/// Shut the running game down so nothing of it carries over: its scene, its sounds, its settings and,
	/// unless we're joining a session that's already open, its network session.
	/// </summary>
	private void LeaveGame(bool disconnect)
	{
		Analytics.GameClosed();
		using (GlobalContext.GameScope())
		{
			if (gameInstance != null)
			{
				ConVarSystem.SaveAll();
				using (disconnect ? Networking.DisconnectScope() : null)
				{
					gameInstance.Shutdown();
					gameInstance = null;
					IGameInstance.Current = null;
				}
				Sound.StopAll(0.2f);
			}
			else if (disconnect)
			{
				Networking.Disconnect();
			}
			Application.ClearGame();
		}
	}

	public void Tick()
	{
		Scene activeScene = Game.ActiveScene;
		using (new ScenePushScope(activeScene))
		{
			if (activeScene != null)
			{
				activeScene.UpdateTime(RealTime.Delta);
				activeScene.SyncServerTime();
				Time.Update(activeScene.TimeNow, activeScene.TimeDelta);
			}
			GameInstance gameInstance = GameInstanceDll.gameInstance;
			if (gameInstance != null && gameInstance.WantsToQuit)
			{
				CloseGame();
			}
			else
			{
				_perFrameInput.Flip();
				_perFrameInput.Push();
				Input.Process();
				Networking.PreFrameTick();
				if (!_isAssemblyLoadingPaused)
				{
					FinishLoadingAssemblies();
				}
				using (Performance.Scope("GameFrame"))
				{
					if (activeScene.IsValid())
					{
						RunGameFrame(activeScene);
					}
				}
				Networking.PostFrameTick();
				Connection.ClearUpdateContextInput();
			}
			if (!Application.IsDedicatedServer)
			{
				RichPresenceSystem.Tick();
				Achievements.Tick();
			}
			TickSceneStats(activeScene);
			Analytics.Tick();
			MainThread.RunQueues();
		}
	}

	private void RunGameFrame(Scene activeScene)
	{
		if (Game.IsPlaying && activeScene != null && !Networking.IsConnecting)
		{
			activeScene.GameTick(0.0);
			MainThread.RunQueues();
		}
	}

	public void SimulateUI()
	{
		bool allowMouseInput = true;
		if (IMenuDll.Current != null)
		{
			allowMouseInput = !IMenuDll.Current.HasOverlayMouseInput();
		}
		using (new ScenePushScope(Game.ActiveScene))
		{
			Game.Language?.Tick();
			GlobalContext.Current.UISystem.Simulate(allowMouseInput);
			Game.ActiveScene?.ProcessDeletes();
		}
	}

	public void ClosePopups(object panelClickedOn)
	{
		BasePopup.CloseAll(panelClickedOn as Panel);
	}

	public void Disconnect(string message = null)
	{
		if (!string.IsNullOrEmpty(message))
		{
			NetworkSystem system = Networking.System;
			if (system != null)
			{
				NetworkSystem networkSystem = system;
				if (networkSystem.FailureReason == null)
				{
					string text = (networkSystem.FailureReason = message);
				}
			}
			GlobalGameNamespace.Log.Warning(FormattableStringFactory.Create("Disconnected: {0}", message.Replace("\n", "")));
		}
		if (Networking.IsMatchmaking)
		{
			return;
		}
		Api.Activity.SetExitReason(string.IsNullOrEmpty(message) ? "leave" : "disconnect", message);
		Api.Activity.CancelRequest(Api.Activity.PendingRequest);
		Api.Activity.LoadAbandoned(string.IsNullOrEmpty(message) ? null : message);
		CancelLoad();
		Game.Close();
		if (!string.IsNullOrEmpty(message))
		{
			using (GlobalContext.MenuScope())
			{
				IModalSystem.Current.Notice("Disconnected", message, "wifi_off");
			}
		}
		LoadingScreen.IsVisible = false;
	}

	private void CancelLoad()
	{
		_loadGameCts?.Cancel();
		_loadGameCts?.Dispose();
		_loadGameCts = null;
	}

	/// <summary>
	/// Loads the game asynchronously. Only one game loads at a time: any load still in
	/// flight is cancelled, and this one waits for it to finish tearing down before it starts.
	/// </summary>
	public async Task<bool> LoadGamePackageAsync(string ident, GameLoadingFlags flags, CancellationToken ct)
	{
		ThreadSafe.AssertIsMainThread("LoadGamePackageAsync");
		Task<bool> loadGameTask = _loadGameTask;
		CancelLoad();
		_loadGameCts = CancellationTokenSource.CreateLinkedTokenSource(ct);
		_loadGameTask = LoadGamePackageInternalAsync(loadGameTask, ident, flags, _loadGameCts.Token);
		return await _loadGameTask;
	}

	/// <summary>
	/// Waits for any previous load to finish tearing down, then runs the load and handles its failure.
	/// </summary>
	private async Task<bool> LoadGamePackageInternalAsync(Task previous, string ident, GameLoadingFlags flags, CancellationToken token)
	{
		if (previous != null && !previous.IsCompleted)
		{
			try
			{
				await previous;
			}
			catch (Exception)
			{
			}
		}
		if (token.IsCancellationRequested)
		{
			return false;
		}
		LoadingScreen.IsVisible = true;
		Api.Activity.Load launch = Api.Activity.LoadBegin(ident, flags.Contains(GameLoadingFlags.Remote));
		try
		{
			await DoLoadGamePackageAsync(ident, flags, token);
			if (token.IsCancellationRequested)
			{
				launch.End("cancel");
				return false;
			}
			launch.Stage(flags.Contains(GameLoadingFlags.Host) ? "scene" : "join");
			return true;
		}
		catch (Exception ex2)
		{
			launch.End((ex2 is OperationCanceledException) ? "cancel" : "fail", (ex2 is OperationCanceledException) ? null : ex2.Message);
			ResetEnvironment();
			if (!(ex2 is OperationCanceledException))
			{
				using (IMenuDll.Current?.PushScope())
				{
					IModalSystem.Current?.Notice("Loading Error", "An error occurred when loading this game.\n\n" + ex2.Message, "error");
				}
				GlobalGameNamespace.Log.Warning(ex2, ex2.Message);
				if (Application.IsEditor)
				{
					throw;
				}
			}
			LoadingScreen.IsVisible = false;
			LoadingScreen.Media = null;
		}
		return false;
	}

	private async Task DoLoadGamePackageAsync(string ident, GameLoadingFlags flags, CancellationToken ct)
	{
		if (gameInstance != null && !flags.Contains(GameLoadingFlags.Reload))
		{
			Package.TryParseIdent(ident, out (string, string, int?, bool) parsed);
			Package.TryParseIdent(gameInstance?.Ident, out (string, string, int?, bool) parsed2);
			if (parsed.Item2 == parsed2.Item2 && parsed.Item1 == parsed2.Item1 && parsed.Item3 == parsed2.Item3)
			{
				return;
			}
		}
		Api.Activity.LoadStage("teardown");
		LeaveGame(!flags.Contains(GameLoadingFlags.Remote));
		if (!Application.IsDedicatedServer && !Application.IsStandalone)
		{
			Stats.GlobalStats globalStats = Stats.GetGlobalStats(ident);
			if (!globalStats.IsRefreshing)
			{
				globalStats.Refresh();
			}
			Stats.PlayerStats localPlayerStats = Stats.GetLocalPlayerStats(ident);
			if (!localPlayerStats.IsRefreshing)
			{
				localPlayerStats.Refresh();
			}
			await Task.Yield();
			if (LoadingScreen.Title == null)
			{
				LoadingScreen.Title = "Loading..";
			}
		}
		GameInstance newInstance = null;
		try
		{
			newInstance = ((!Application.IsStandalone) ? new GameInstance(ident, flags) : new StandaloneGameInstance(ident, flags));
			using (GlobalContext.GameScope())
			{
				Api.Activity.LoadStage("reset");
				ResetEnvironment();
				NativeErrorReporter.Breadcrumb(action: true, "game", "Loading game package " + ident);
				NativeErrorReporter.SetTag("game", ident);
				NativeErrorReporter.SetTag("map", LaunchArguments.Map);
				if (!Application.IsDedicatedServer && !Application.IsStandalone)
				{
					await Task.Yield();
				}
				if (!(await newInstance.LoadAsync(AssemblyEnroller, ct)))
				{
					if (ct.IsCancellationRequested)
					{
						return;
					}
					throw new Exception("GameInstance load failed");
				}
				Json.PopulateReflectionCache(Game.TypeLibrary);
				if (ct.IsCancellationRequested)
				{
					return;
				}
				await Task.Yield();
				GC.Collect(GC.MaxGeneration, GCCollectionMode.Optimized, blocking: false, compacting: false);
				await Task.Yield();
				if (Package.TryParseIdent(ident, out (string, string, int?, bool) parsed3))
				{
					EngineFileSystem.Data.CreateDirectory(parsed3.Item1);
					string text = (parsed3.Item4 ? (parsed3.Item2 + "#local") : parsed3.Item2);
					GlobalContext.Current.FileOrg = EngineFileSystem.Data.CreateSubSystem(parsed3.Item1);
					GlobalContext.Current.FileOrg.CreateDirectory(text);
					GlobalContext.Current.FileData = FileSystem.OrganizationData.CreateSubSystem(text);
				}
				else if (Application.IsStandalone && ident == Standalone.Manifest.Ident)
				{
					GlobalContext.Current.FileOrg = EngineFileSystem.Data;
					GlobalContext.Current.FileData = EngineFileSystem.Data;
				}
				else
				{
					EngineFileSystem.Data.CreateDirectory(".local");
					GlobalContext.Current.FileOrg = EngineFileSystem.Data.CreateSubSystem(".local");
					GlobalContext.Current.FileOrg.CreateDirectory(ident);
					GlobalContext.Current.FileData = FileSystem.OrganizationData.CreateSubSystem(ident);
				}
				Game.Cookies = new CookieContainer("cookies", noexpire: false, GlobalContext.Current.FileData);
				IGameInstance.Current = newInstance;
				gameInstance = newInstance;
				newInstance = null;
				if (flags.Contains(GameLoadingFlags.Host))
				{
					Api.Activity.LoadStage("scene");
					LoadingScreen.Title = "Loading Scene";
					await Task.Yield();
					if (!gameInstance.OpenStartupScene())
					{
						throw new Exception("Failed to load startup scene");
					}
				}
				if (Application.IsEditor)
				{
					Game.CheatsEnabled = true;
				}
				if (!Application.IsEditor)
				{
					Game.IsPlaying = true;
					LoadingScreen.Title = (flags.Contains(GameLoadingFlags.Host) ? "Starting Game" : "Joining Game..");
					await Task.Yield();
				}
			}
		}
		finally
		{
			if (newInstance != null)
			{
				using (GlobalContext.GameScope())
				{
					newInstance.Close();
					newInstance.Shutdown();
				}
			}
		}
	}

	private void OnPackageInstalled(PackageManager.ActivePackage package, string context)
	{
		if (!(context != "game"))
		{
			GlobalGameNamespace.Log.Trace($"OnPackageInstalled: {package.Package.FullIdent} {context}");
			AssemblyEnroller?.LoadPackage(package.Package.FullIdent);
		}
	}

	/// <summary>
	/// Called when the game menu is closed
	/// </summary>
	/// <param name="instance"></param>
	public void Shutdown(IGameInstance instance)
	{
		NativeErrorReporter.Breadcrumb(action: true, "game", "Closed game instance");
		NativeErrorReporter.SetTag("game", null);
		NativeErrorReporter.SetTag("map", null);
		if (gameInstance == instance)
		{
			gameInstance = null;
		}
		if (IGameInstance.Current == instance)
		{
			IGameInstance.Current = null;
		}
	}

	public void OnRender(SwapChainHandle_t swapChain)
	{
		Game.Render(swapChain);
	}

	/// <summary>
	/// The play button was pressed in the editor
	/// </summary>
	public bool EditorPlay()
	{
		if (gameInstance == null)
		{
			GlobalGameNamespace.Log.Warning("Tried to editor play but we don't have a game instance");
			return false;
		}
		Game.IsPlaying = true;
		if (!gameInstance.OpenStartupScene())
		{
			GlobalGameNamespace.Log.Warning("There was a problem opening the StartupScene");
			Game.ActiveScene?.Destroy();
			Game.ActiveScene = null;
			Game.IsPlaying = false;
			return false;
		}
		return true;
	}

	/// <summary>
	/// Pushes the game scope. This will push the active scene and the right time.
	/// </summary>
	public ScenePushScope PushScope()
	{
		return new ScenePushScope(Game.ActiveScene);
	}

	/// <summary>
	/// Called per frame to add scene's stats to our analytics
	/// </summary>
	private void TickSceneStats(Scene scene)
	{
		bool flag = scene.IsValid();
		int num = 0;
		int num2 = 0;
		if (flag)
		{
			foreach (CameraComponent item in scene.Query<CameraComponent>())
			{
				_ = item;
				num++;
			}
			foreach (ParticleEffect item2 in scene.Query<ParticleEffect>())
			{
				num2 += item2.Particles.Count;
			}
		}
		Api.Performance.CollectStat("GameObjectCount", flag ? scene.Directory.GameObjectCount : 0);
		Api.Performance.CollectStat("ComponentCount", flag ? scene.Directory.ComponentCount : 0);
		Api.Performance.CollectStat("RootGameObjects", flag ? scene.Children.Count : 0);
		Api.Performance.CollectStat("CameraCount", num);
		Api.Performance.CollectStat("ColliderCount", flag ? scene.PhysicsWorld.BodyCount : 0);
		Api.Performance.CollectStat("Particles", num2);
		Api.Performance.CollectStat("GameObjectsDestroyed", SceneMetrics.GameObjectsDestroyed);
		Api.Performance.CollectStat("ParticlesCreated", SceneMetrics.ParticlesCreated);
		Api.Performance.CollectStat("ParticlesDestroyed", SceneMetrics.ParticlesDestroyed);
		Api.Performance.CollectStat("GameObjectsCreated", SceneMetrics.GameObjectsCreated);
		Api.Performance.CollectStat("GameObjectsDestroyed", SceneMetrics.GameObjectsDestroyed);
		Api.Performance.CollectStat("ComponentsCreated", SceneMetrics.ComponentsCreated);
		Api.Performance.CollectStat("ComponentsDestroyed", SceneMetrics.ComponentsDestroyed);
		Api.Performance.CollectStat("RayTrace", SceneMetrics.RayTrace);
		Api.Performance.CollectStat("RayTraceAll", SceneMetrics.RayTraceAll);
		SceneMetrics.Flip();
	}

	void IGameInstanceDll.ResetSceneListenerMetrics()
	{
		Game.ActiveScene.ResetListenerMetrics();
	}

	object IGameInstanceDll.GetSceneListenerMetrics()
	{
		return Game.ActiveScene.GetListenerMetrics();
	}

	[ConCmd("game", ConVarFlags.Protected, Help = "Play a game")]
	public static async Task StartGame(string gameIdent, string mapIdent = null)
	{
		if (Application.IsEditor)
		{
			return;
		}
		Api.Activity.GameRequested(new Api.Activity.Origin("console", gameIdent), replace: false);
		if ((Application.IsDedicatedServer || CommandLine.HasSwitch("-mcp")) && gameIdent.EndsWith(".sbproj", StringComparison.OrdinalIgnoreCase))
		{
			await Project.InitializeBuiltIn(syncPackageManager: false);
			Project project = Project.AddFromFile(gameIdent);
			FullFileSystem.AddProjectPath(gameIdent, project.GetAssetsPath().ToLowerInvariant());
			string path = Path.Combine(project.RootDirectory.FullName, "Libraries");
			IEnumerable<string> enumerable2;
			if (!System.IO.Directory.Exists(path))
			{
				IEnumerable<string> enumerable = Array.Empty<string>();
				enumerable2 = enumerable;
			}
			else
			{
				enumerable2 = System.IO.Directory.EnumerateDirectories(path);
			}
			foreach (string item in enumerable2)
			{
				string[] array = System.IO.Directory.EnumerateFiles(item, "*.sbproj").ToArray();
				if (array.Length == 1)
				{
					Project.AddFromFile(array[0]);
				}
			}
			project.Load();
			await Project.CompileAsync();
			if (!project.Active)
			{
				GlobalGameNamespace.Log.Error($"Unable to load {gameIdent}");
				return;
			}
			gameIdent = project.Package.FullIdent;
		}
		GlobalGameNamespace.Log.Info($"Loading game '{gameIdent}'");
		LaunchArguments.Map = mapIdent;
		if (LaunchArguments.Map != null)
		{
			GlobalGameNamespace.Log.Info($" with map: '{LaunchArguments.Map}'");
		}
		LoadingScreen.IsVisible = true;
		LoadingScreen.Media = null;
		LoadingScreen.Title = null;
		await Current.LoadGamePackageAsync(gameIdent, GameLoadingFlags.Host, default);
	}

	public static void Create()
	{
		IGameInstanceDll.Current = new GameInstanceDll();
		ReflectionUtility.PreJITAsync(typeof(GameInstanceDll).Assembly);
		ReflectionUtility.PreJITAsync(typeof(Vector3).Assembly);
		ReflectionUtility.PreJITAsync(typeof(Bootstrap).Assembly);
	}

	/// <summary>
	/// Try to get the replicated var value from the host
	/// </summary>
	public bool TryGetReplicatedVarValue(string name, out string value)
	{
		value = null;
		if (!Networking.IsActive)
		{
			return false;
		}
		if (Networking.IsHost)
		{
			return false;
		}
		return ReplicatedConvars.TryGetValue(name, out value);
	}

	internal void SetupInputContext()
	{
		UISystem uISystem = new UISystem();
		InputContext inputContext = new InputContext();
		inputContext.Name = GetType().Name;
		inputContext.TargetUISystem = uISystem;
		inputContext.OnGameMouseWheel = (Action<Vector2>)Delegate.Combine(inputContext.OnGameMouseWheel, new Action<Vector2>(Input.AddMouseWheel));
		inputContext.OnMouseMotion = (Action<Vector2>)Delegate.Combine(inputContext.OnMouseMotion, new Action<Vector2>(Input.AddMouseMovement));
		inputContext.OnGameButton = (Action<ButtonCode, string, bool>)Delegate.Combine(inputContext.OnGameButton, new Action<ButtonCode, string, bool>(Input.OnButton));
		InputContext = inputContext;
		GlobalContext.Current.UISystem = uISystem;
		GlobalContext.Current.InputContext = inputContext;
	}

	/// <summary>
	/// Load the assemblies from this package into the current game instance
	/// </summary>
	public Task LoadPackageAssembliesAsync(Package package)
	{
		AssemblyEnroller.LoadPackage(package.FullIdent);
		return Task.CompletedTask;
	}

	public void OnBecameHost()
	{
		ReplicatedConvars.OnBecameHost();
	}

	public GameNetworkSystem CreateGameNetworking(NetworkSystem system)
	{
		SceneNetworkSystem sceneNetworkSystem = new SceneNetworkSystem(TypeLibrary, system);
		NetworkedLargeFiles.NetworkInitialize(sceneNetworkSystem);
		Chat.NetworkInitialize(sceneNetworkSystem);
		if (Networking.IsHost)
		{
			AddFilesToNetwork(NetworkedConfigFiles, EngineFileSystem.ProjectSettings, new HashSet<string> { ".config" });
			AddFilesToNetwork(NetworkedLangFiles, Game.Language.FileSystem, new HashSet<string> { ".json" });
			BuildNetworkedFiles();
		}
		else if (!DidMountNetworkedFiles)
		{
			EngineFileSystem.ProjectSettings.Mount(NetworkedConfigFiles.Files);
			Game.Language.FileSystem.Mount(NetworkedLangFiles.Files);
			Game.Language.Refresh();
			FileSystem.Mounted.Mount(NetworkedLargeFiles.Files);
			FileSystem.Mounted.Mount(NetworkedSmallFiles.Files);
			NetworkedSmallFiles.Refresh();
			NetworkedConfigFiles.Refresh();
			NetworkedLangFiles.Refresh();
			ResourceLoader.LoadAllGameResource(FileSystem.Mounted, reloadExisting: true);
			FontManager.Instance.LoadAll(FileSystem.Mounted);
			DidMountNetworkedFiles = true;
		}
		return sceneNetworkSystem;
	}

	public async Task<GameNetworkSystem> CreateGameNetworkingAsync(NetworkSystem system)
	{
		SceneNetworkSystem instance = new SceneNetworkSystem(TypeLibrary, system);
		NetworkedLargeFiles.NetworkInitialize(instance);
		Chat.NetworkInitialize(instance);
		if (Networking.IsHost)
		{
			AddFilesToNetwork(NetworkedConfigFiles, EngineFileSystem.ProjectSettings, new HashSet<string> { ".config" });
			AddFilesToNetwork(NetworkedLangFiles, Game.Language.FileSystem, new HashSet<string> { ".json" });
			BuildNetworkedFiles();
		}
		else if (!DidMountNetworkedFiles)
		{
			EngineFileSystem.ProjectSettings.Mount(NetworkedConfigFiles.Files);
			Game.Language.FileSystem.Mount(NetworkedLangFiles.Files);
			Game.Language.Refresh();
			FileSystem.Mounted.Mount(NetworkedLargeFiles.Files);
			FileSystem.Mounted.Mount(NetworkedSmallFiles.Files);
			NetworkedSmallFiles.Refresh();
			NetworkedConfigFiles.Refresh();
			NetworkedLangFiles.Refresh();
			LoadingScreen.Title = "Loading Resources";
			await ResourceLoader.LoadAllGameResourceAsync(FileSystem.Mounted, default, reloadExisting: true);
			FontManager.Instance.LoadAll(FileSystem.Mounted);
			DidMountNetworkedFiles = true;
		}
		return instance;
	}

	private void AddFilesToNetwork(SmallNetworkFiles target, BaseFileSystem fs, HashSet<string> validExtensions)
	{
		foreach (string item in fs.FindFile("/", "*", recursive: true))
		{
			string extension = Path.GetExtension(item);
			if (validExtensions.Contains(extension))
			{
				Span<byte> span = fs.ReadAllBytes(item);
				target.AddFile(fs, item, span.ToArray());
			}
		}
		FileWatch fileWatch = fs.Watch();
		fileWatch.OnChanges += (FileWatch w) =>
		{
			foreach (string change in w.Changes)
			{
				string extension2 = Path.GetExtension(change);
				if (validExtensions.Contains(extension2))
				{
					if (fs.FileExists(change))
					{
						Span<byte> span2 = fs.ReadAllBytes(change);
						target.AddFile(fs, change, span2.ToArray());
					}
					else
					{
						target.RemoveFile(change);
					}
				}
			}
		};
		FileWatchers.Add(fileWatch);
	}

	public void InstallNetworkTables(NetworkSystem system)
	{
		system.InstallTable(CodeArchiveTable);
		system.InstallTable(ServerPackages.StringTable);
		system.InstallTable(NetworkedSmallFiles.StringTable);
		system.InstallTable(NetworkedConfigFiles.StringTable);
		system.InstallTable(NetworkedLangFiles.StringTable);
		system.InstallTable(NetworkedLargeFiles.StringTable);
		system.InstallTable(ReplicatedConvars.StringTable);
		CodeArchiveTable.OnChangeOrAdd = (StringTable.Entry entry) =>
		{
			CodeArchive codeArchive = new CodeArchive(entry.Data);
			compileGroup.GetOrCreateCompiler(codeArchive.CompilerName).UpdateFromArchive(codeArchive);
		};
		CodeArchiveTable.PostNetworkUpdate = () =>
		{
			FinishLoadingCodeArchives();
		};
		system.InstallTable(ConfigTable);
		ConfigTable.PostNetworkUpdate = UpdateConfigFromNetworkTable;
	}

	private bool FinishLoadingCodeArchives()
	{
		if (!compileGroup.NeedsBuild)
		{
			FinishLoadingAssemblies();
			return true;
		}
		SyncContext.RunBlocking(compileGroup.BuildAsync());
		if (!compileGroup.BuildResult.Success)
		{
			return false;
		}
		foreach (CompilerOutput item in compileGroup.BuildResult.Output)
		{
			using MemoryStream stream = new MemoryStream(item.AssemblyData);
			AssemblyEnroller.LoadAssemblyFromStream(item.Compiler.AssemblyName, stream);
		}
		FinishLoadingAssemblies();
		return true;
	}

	public async Task<bool> LoadNetworkTables(NetworkSystem system)
	{
		compileGroup = new CompileGroup("server");
		using (PauseLoadingAssemblies())
		{
			foreach (KeyValuePair<string, StringTable.Entry> entry in CodeArchiveTable.Entries)
			{
				CodeArchive codeArchive = new CodeArchive(entry.Value.Data);
				compileGroup.GetOrCreateCompiler(codeArchive.CompilerName).UpdateFromArchive(codeArchive);
			}
			if (!FinishLoadingCodeArchives())
			{
				Disconnect("Failed to compile code archives. Check log for details.");
				return false;
			}
			UpdateConfigFromNetworkTable();
			await ServerPackages.InstallAll();
			List<Workshop.Item> mismatchedWorkshopItems = ServerPackages.GetMismatchedWorkshopItems();
			if (mismatchedWorkshopItems.Count > 0)
			{
				Disconnect(ServerPackages.MismatchMessage(mismatchedWorkshopItems));
				return false;
			}
			if (string.IsNullOrWhiteSpace(LoadingScreen.Title))
			{
				LoadingScreen.Title = "Loading..";
			}
			await NetworkedLargeFiles.RunDownloadQueue(system, default);
			return true;
		}
	}

	internal static bool ShouldUseLargeDownload(string filename, long size)
	{
		if (size < 65536)
		{
			return _engineAssets.Any((string x) => filename.EndsWith(x));
		}
		return true;
	}

	private bool ShouldNetworkFile(string filename)
	{
		filename = filename.NormalizeFilename();
		if (!AssetDownloadCache.IsLegalDownload(filename))
		{
			return false;
		}
		if (_netIncludePaths.Any((string x) => filename.WildcardMatch(x)))
		{
			return true;
		}
		return _interestingExtensions.Any((string x) => filename.EndsWith(x));
	}

	private void UpdateNetworkFile(BaseFileSystem fs, string filename)
	{
		if (!filename.Contains("\\code\\obj\\", StringComparison.OrdinalIgnoreCase))
		{
			if (filename.EndsWith("vmap"))
			{
				filename = Path.ChangeExtension(filename, ".vpk");
			}
			else if (!ShouldNetworkFile(filename))
			{
				return;
			}
			AddNetworkFile(fs, EngineFileSystem.Mounted, filename, NetworkedSmallFiles, NetworkedLargeFiles);
		}
	}

	internal static void AddNetworkFile(BaseFileSystem source, BaseFileSystem mounted, string filename, SmallNetworkFiles smallFiles, LargeNetworkFiles largeFiles)
	{
		if (ShouldUseLargeDownload(filename, 0L))
		{
			if (source.FileExists(filename))
			{
				AddLargeFile();
			}
			return;
		}
		Stream stream;
		try
		{
			stream = source.OpenRead(filename);
		}
		catch (FileNotFoundException)
		{
			return;
		}
		catch (DirectoryNotFoundException)
		{
			return;
		}
		if (stream == null)
		{
			return;
		}
		using (stream)
		{
			long length = stream.Length;
			if (!ShouldUseLargeDownload(filename, length))
			{
				byte[] array = new byte[length];
				stream.ReadExactly(array);
				smallFiles.AddFile(filename, array);
				if (AssetDownloadCache.DebugNetworkFiles)
				{
					GlobalGameNamespace.Log.Info($"Adding Small File {filename} ({length.FormatBytes()})");
				}
				return;
			}
		}
		AddLargeFile();
		void AddLargeFile()
		{
			if (!largeFiles.AddFile(mounted, filename))
			{
				GlobalGameNamespace.Log.Warning($"File '{filename}' ('{source.GetFullPath(filename)}') doesn't exist - skipping");
			}
		}
	}

	/// <summary>
	/// Go through our mounted files and make them available to joining clients for download
	/// </summary>
	private void BuildNetworkedFiles()
	{
		Stopwatch stopwatch = Stopwatch.StartNew();
		if (!(IGameInstance.Current is GameInstance gameInstance))
		{
			GlobalGameNamespace.Log.Warning("Game Instance was null when building network files");
		}
		else
		{
			if (gameInstance.IsRemote)
			{
				return;
			}
			if (AssetDownloadCache.DebugNetworkFiles)
			{
				GlobalGameNamespace.Log.Info("Building network files..");
			}
			Project current = Project.Current;
			if (current != null && !string.IsNullOrWhiteSpace(current.Config.Resources))
			{
				IEnumerable<string> collection = from x in current.Config.Resources.Split("\n", StringSplitOptions.RemoveEmptyEntries)
					select x.Trim() into x
					where !x.StartsWith("//")
					select x.NormalizeFilename(enforceInitialSlash: true, enforceLowerCase: false);
				_netIncludePaths.AddRange(collection);
			}
			Project[] array = Project.Libraries.Where((Project x) => x.Active && x.RootDirectory != null).ToArray();
			AggregateFileSystem fs = new AggregateFileSystem();
			fs.Mount(gameInstance.GameFileSystem);
			Project[] array2 = array;
			for (int num = 0; num < array2.Length; num++)
			{
				PackageManager.ActivePackage activePackage = PackageManager.Find(array2[num].Package.FullIdent, allowLocalPackages: true);
				if (activePackage != null)
				{
					fs.Mount(activePackage.FileSystem);
				}
			}
			NetworkedFileSystem = fs;
			foreach (string item in fs.FindFile("/", "*", recursive: true))
			{
				UpdateNetworkFile(fs, item);
			}
			FileWatch fileWatch = fs.Watch();
			fileWatch.OnChanges += (FileWatch w) =>
			{
				foreach (string change in w.Changes)
				{
					UpdateNetworkFile(fs, change);
				}
			};
			FileWatchers.Add(fileWatch);
			NetworkTransientGeneratedFiles(current);
			if (AssetDownloadCache.DebugNetworkFiles)
			{
				GlobalGameNamespace.Log.Info($"..done in {stopwatch.Elapsed.TotalSeconds:0.00}s");
			}
		}
	}

	/// <summary>
	/// Make runtime-generated assets in the project's .sbox/transient/ folder available to joining clients
	/// This is necessary for connected clients to see things like TextureGenerators.
	/// </summary>
	private void NetworkTransientGeneratedFiles(Project project)
	{
		if (project == null)
		{
			return;
		}
		string text = Path.Combine(project.GetRootPath(), ".sbox", "transient");
		if (!System.IO.Directory.Exists(text))
		{
			return;
		}
		LocalFileSystem transientFs = new LocalFileSystem(text);
		foreach (string item in transientFs.FindFile("/", "*", recursive: true))
		{
			UpdateNetworkFile(transientFs, item);
		}
		FileWatch fileWatch = transientFs.Watch();
		fileWatch.OnChanges += (FileWatch w) =>
		{
			foreach (string change in w.Changes)
			{
				UpdateNetworkFile(transientFs, change);
			}
		};
		FileWatchers.Add(fileWatch);
	}
}
