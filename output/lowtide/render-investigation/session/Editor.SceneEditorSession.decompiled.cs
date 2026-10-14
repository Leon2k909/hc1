using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using Facepunch.ActionGraphs;
using Sandbox;
using Sandbox.ActionGraphs;
using Sandbox.Diagnostics;
using Sandbox.Helpers;
using Sandbox.Internal;
using Sandbox.Mounting;
using Sandbox.Navigation;

namespace Editor;

/// <summary>
/// A SceneEditorSession holds a Scene that is open in the editor.
/// It creates a widget, has a selection and undo system.
/// </summary>
public class SceneEditorSession : Scene.ISceneEditorSession, ResourceLibrary.IEventListener, NavMesh.IEventListener
{
	private sealed class SuppressUndoSoundScope : IDisposable
	{
		private readonly SceneEditorSession _session;

		private readonly bool _previous;

		public SuppressUndoSoundScope(SceneEditorSession session)
		{
			_session = session;
			_previous = session._suppressUndoSounds;
			session._suppressUndoSounds = true;
		}

		public void Dispose()
		{
			_session._suppressUndoSounds = _previous;
		}
	}

	private static HashSet<SceneEditorSession> editedScenes = new HashSet<SceneEditorSession>();

	private bool _destroyed;

	private RealTimeSince timeSinceSavedState;

	private int _reloadHash;

	private static RealTimeSince timeSinceLastUpdatePrefabs;

	private bool unsavedChanges;

	/// <summary>
	/// when changing the selection, we save it as the previous, so that undo has a frame of reference
	/// </summary>
	private string previousSavedSelection;

	private bool _suppressUndoSounds;

	/// <summary>
	/// All open editor sessions
	/// </summary>
	public static List<SceneEditorSession> All { get; } = new List<SceneEditorSession>();

	internal static SceneEditorSession Playing => All.FirstOrDefault((SceneEditorSession x) => x.GameSession != null);

	/// <summary>
	/// The editor session that is currently active
	/// </summary>
	public static SceneEditorSession Active
	{
		get;
		private set
		{
			if (field != value)
			{
				field = value;
				field?.UpdateEditorTitle();
			}
		}
	}

	/// <summary>
	/// Returns true if this session is editing a prefab
	/// </summary>
	public bool IsPrefabSession => this is PrefabEditorSession;

	public Scene Scene { get; private set; }

	internal Widget SceneDock { get; set; }

	/// <summary>
	/// Should we call <see cref="M:Sandbox.Scene.EditorTick(System.Single,System.Single)" /> while this session is visible?
	/// </summary>
	public bool ShouldUpdate { get; set; } = true;

	public Action<BBox> OnFrameTo { get; set; }

	internal int EditVersion { get; private set; }

	internal bool CompilationDirty { get; set; }

	/// <summary>
	/// True if this session is editing a scene opened from a mount. Mounted scenes live at a
	/// read-only mount:// path, so they can't be saved and never report unsaved changes.
	/// </summary>
	public bool IsMounted => MountUtility.IsMountPath(Scene?.Source?.ResourcePath);

	public bool HasUnsavedChanges
	{
		get
		{
			if (unsavedChanges)
			{
				return !IsMounted;
			}
			return false;
		}
		set
		{
			if (value)
			{
				MarkCompilationDirty();
			}
			editedScenes.Add(this);
			if (unsavedChanges != value)
			{
				unsavedChanges = value;
				UpdateEditorTitle();
			}
		}
	}

	BaseFileSystem Scene.ISceneEditorSession.TransientFilesystem => FileSystem.Transient;

	/// <summary>
	/// The game session of this editor session, if playing.
	/// </summary>
	public GameEditorSession GameSession { get; private set; }

	public virtual bool IsPlaying => GameSession != null;

	/// <summary>
	/// Only the active session contributes selection-driven previews.
	/// </summary>
	bool Scene.ISceneEditorSession.IsActive => Active == this;

	public SelectionSystem Selection { get; } = new SelectionSystem();

	public UndoSystem UndoSystem { get; } = new UndoSystem();

	internal SceneUndoSnapshot LastUndoSnapshot { get; set; }

	internal bool IsUndoScopeOpen => LastUndoSnapshot?.IsOpen ?? false;

	protected SceneEditorSession(Scene scene)
	{
		ArgumentNullException.ThrowIfNull(scene, "scene");
		Scene = scene;
		Scene.Editor = this;
		All.Add(this);
		InitUndo();
		timeSinceSavedState = 0f;
		_reloadHash = scene.ReloadHash;
		if (!(this is GameEditorSession))
		{
			CreateSceneDock();
		}
		EditorEvent.Register(this);
	}

	/// <summary>
	/// Create the scene view widget and open it as a tab in the central scene area
	/// </summary>
	private void CreateSceneDock()
	{
		SceneDock = GlobalToolsNamespace.EditorTypeLibrary.Create<Widget>("SceneDock", new object[1] { this });
		SceneDock.Name = "SceneDock:" + (Scene.Source?.ResourcePath ?? "untitled");
		GlobalToolsNamespace.EditorWindow.SceneTabs.Open(this);
		UpdateEditorTitle();
	}

	public virtual void Destroy()
	{
		if (_destroyed)
		{
			return;
		}
		_destroyed = true;
		if (GameSession != null && Game.IsPlaying)
		{
			EditorScene.Stop();
		}
		if (this == Active)
		{
			Active = null;
			int num = All.IndexOf(this);
			if (num >= 0 && All.Count > 1)
			{
				num = ((num <= 0) ? (num + 1) : (num - 1));
				Active = All[num];
			}
		}
		All.Remove(this);
		EditorEvent.Unregister(this);
		GlobalToolsNamespace.EditorWindow?.SceneTabs?.Remove(this);
		Scene?.Destroy();
		Scene = null;
		GameSession?.Destroy();
		GameSession = null;
		SceneDock?.Destroy();
		SceneDock = null;
	}

	/// <summary>
	/// Makes this scene active and brings it to the front
	/// </summary>
	public void MakeActive(bool bringToFront = true)
	{
		Active = this;
		if (bringToFront && GlobalToolsNamespace.EditorWindow != null)
		{
			BringToFront();
		}
	}

	/// <summary>
	/// Bring this scene tab to the front
	/// </summary>
	public void BringToFront()
	{
		GlobalToolsNamespace.EditorWindow?.SceneTabs?.MakeCurrent(this);
		UpdateEditorTitle();
	}

	public void Tick()
	{
		if (Scene.Source is SceneFile { IsSourceSnapshot: not false } sceneFile)
		{
			SceneSource.FindAsset(sceneFile);
		}
		Scene.ProcessDeletes();
		int reloadHash = Scene.ReloadHash;
		if (reloadHash != _reloadHash)
		{
			_reloadHash = reloadHash;
			Scene.Reload();
		}
		if (timeSinceSavedState > 1f)
		{
			timeSinceSavedState = 0f;
			EditorEvent.Run("scene.session.save");
		}
	}

	internal void UpdateEditorTitle()
	{
		if (!SceneDock.IsValid())
		{
			return;
		}
		string text = Scene.Name.Trim();
		Scene.ISceneEditorSession editor = Scene.Editor;
		if (editor != null && editor.HasUnsavedChanges)
		{
			text += "*";
		}
		GlobalToolsNamespace.EditorWindow?.UpdateEditorTitle(text);
		if (SceneDock != null)
		{
			SceneDock.Name = "SceneDock:" + (Scene.Source?.ResourcePath ?? "untitled");
			if (IsPrefabSession)
			{
				SceneDock.SetWindowIcon("home_repair_service");
				SceneDock.WindowTitle = "Prefab: " + text;
			}
			else
			{
				SceneDock.SetWindowIcon("grid_4x4");
				SceneDock.WindowTitle = text;
			}
			GlobalToolsNamespace.EditorWindow?.SceneTabs?.UpdateTitle(this);
		}
	}

	protected virtual void OnEdited()
	{
		SceneCompileSession.Current.OnSceneEdited(Scene);
	}

	internal static void ProcessSceneEdits()
	{
		if (!((double)(float)timeSinceLastUpdatePrefabs < 0.1))
		{
			timeSinceLastUpdatePrefabs = 0f;
			SceneEditorSession[] array = editedScenes.ToArray();
			for (int i = 0; i < array.Length; i++)
			{
				array[i].OnEdited();
			}
			editedScenes.Clear();
		}
	}

	/// <summary>
	/// Pushes the active scene to the current scope
	/// </summary>
	public static IDisposable Scope()
	{
		return Active.Scene.Push();
	}

	[Obsolete]
	void Scene.ISceneEditorSession.AddSelectionUndo()
	{
		PushUndoSelection();
	}

	/// <summary>
	/// Zoom the scene to view this bbox
	/// </summary>
	public virtual void FrameTo(in BBox box)
	{
		BringToFront();
		OnFrameTo?.Invoke(box);
	}

	private void MarkCompilationDirty()
	{
		EditVersion++;
		CompilationDirty = true;
	}

	public void Reload()
	{
		if (Scene.Source == null)
		{
			return;
		}
		GameResource gameResource = Scene.Source;
		if (gameResource is SceneFile file)
		{
			Asset asset = SceneSource.FindAsset(file);
			if (asset != null && File.Exists(asset.GetSourceFile(absolute: true)))
			{
				gameResource = SceneSource.LoadForEditing(asset);
			}
		}
		InitUndo();
		MarkCompilationDirty();
		Scene.Load(gameResource);
		Selection.Clear();
	}

	public void Save(bool saveAs)
	{
		if (IsMounted)
		{
			return;
		}
		if (Scene.Source is SceneFile file)
		{
			SceneSource.FindAsset(file);
		}
		bool flag = Scene is PrefabScene;
		string text = (flag ? "prefab" : "scene");
		string text2 = (flag ? "Prefab" : "Scene");
		string empty = string.Empty;
		if (!saveAs && Scene.Source != null)
		{
			Asset asset = AssetSystem.FindByPath(Scene.Source.ResourcePath);
			if (asset != null)
			{
				empty = asset.AbsolutePath;
				goto IL_0160;
			}
		}
		empty = GlobalToolsNamespace.ProjectCookie.GetString("LastSaveLocation." + text, string.Empty);
		if (!System.IO.Directory.Exists(empty))
		{
			empty = Project.Current.GetAssetsPath();
		}
		empty = EditorUtility.SaveFileDialog("Save " + text2 + " As..", text, Path.Combine(empty, "untitled." + text));
		if (empty == null)
		{
			return;
		}
		if (!empty.NormalizeFilename(enforceInitialSlash: false).StartsWith(Project.Current.GetAssetsPath().NormalizeFilename(enforceInitialSlash: false)))
		{
			EditorUtility.DisplayDialog("Save Failed: Invalid location", text2 + "s must be saved inside the Assets folder of your project", "Cancel", "Retry", () =>
			{
				Save(saveAs: true);
			});
			return;
		}
		GlobalToolsNamespace.ProjectCookie.SetString("LastSaveLocation." + text, Path.GetDirectoryName(empty));
		goto IL_0160;
		IL_0160:
		EditorEvent.Run("scene.beforesave", Active.Scene);
		Asset asset2 = AssetSystem.CreateResource(text, empty);
		Assert.NotNull(asset2, "Failed to CreateResource for " + text2 + " at " + empty);
		GameResource gameResource = ((Scene is PrefabScene prefabScene) ? ((GameResource)prefabScene.ToPrefabFile()) : ((GameResource)Scene.CreateSceneFile()));
		if (gameResource is SceneFile sceneFile)
		{
			sceneFile.InitializeSource(asset2.Path, asset2.Guid);
		}
		if (!asset2.SaveToDisk(gameResource))
		{
			GlobalGameNamespace.Log.Error($"Could not save {asset2.Path}.");
			return;
		}
		if (!flag)
		{
			if (Scene.Source?.ResourcePath != asset2.Path)
			{
				MarkCompilationDirty();
			}
			if (CompilationDirty)
			{
				SceneCompileCache.WriteSetting(asset2, "sceneCompileDirty", JsonValue.Create(value: true));
			}
		}
		Scene.Source = gameResource;
		Scene.Name = Path.GetFileNameWithoutExtension(empty);
		HasUnsavedChanges = false;
		EditorEvent.Run("scene.saved", Scene);
		UpdateEditorTitle();
	}

	/// <summary>
	/// Resolve a scene to an editor session. If it's a game scene, resolves the parent editor session.
	/// </summary>
	public static SceneEditorSession Resolve(Scene scene)
	{
		if (scene.Editor is SceneEditorSession sceneEditorSession)
		{
			if (sceneEditorSession is GameEditorSession gameEditorSession)
			{
				return gameEditorSession.Parent;
			}
			return sceneEditorSession;
		}
		return All.FirstOrDefault((SceneEditorSession x) => x.Scene == scene);
	}

	/// <summary>
	/// Resolve a Component to an editor session.
	/// </summary>
	public static Scene.ISceneEditorSession Resolve(Component component)
	{
		return Resolve(component?.GameObject);
	}

	/// <summary>
	/// Resolve a GameObject to an editor session.
	/// </summary>
	public static Scene.ISceneEditorSession Resolve(GameObject go)
	{
		if (go == null)
		{
			return null;
		}
		Scene.ISceneEditorSession editor = go.Scene.Editor;
		if (editor == null)
		{
			GlobalGameNamespace.Log.Error($"Failed to resolve session for GameObject: {go}");
		}
		return editor;
	}

	/// <summary>
	/// Resolve a scene file to an editor session.
	/// </summary>
	public static SceneEditorSession Resolve(SceneFile sceneFile)
	{
		return All.FirstOrDefault((SceneEditorSession x) => x != null && !x.IsPrefabSession && !(x is GameEditorSession) && string.Equals(sceneFile.ResourcePath, x.Scene.Source?.ResourcePath, StringComparison.OrdinalIgnoreCase));
	}

	/// <summary>
	/// Resolve a prefab file to an editor session.
	/// </summary>
	public static SceneEditorSession Resolve(PrefabFile prefabFile)
	{
		return All.FirstOrDefault((SceneEditorSession x) => x != null && x.IsPrefabSession && !(x is GameEditorSession) && string.Equals(prefabFile.ResourcePath, x.Scene.Source?.ResourcePath, StringComparison.OrdinalIgnoreCase));
	}

	/// <summary>
	/// Resolve an action graph source location to an editor session.
	/// </summary>
	public static SceneEditorSession Resolve(ISourceLocation sourceLocation)
	{
		if (sourceLocation is GameResourceSourceLocation { Resource: var resource })
		{
			if (resource is SceneFile sceneFile)
			{
				return Resolve(sceneFile);
			}
			if (resource is PrefabFile prefabFile)
			{
				return Resolve(prefabFile);
			}
		}
		return null;
	}

	[Obsolete]
	public void RecordChange(SerializedProperty property)
	{
	}

	/// <summary>
	/// Persist the list of open scenes so they can be reopened next session.
	/// </summary>
	internal static void SaveOpenSessions()
	{
		string[] value = (from x in All
			where !(x is GameEditorSession)
			select x.Scene.Source?.ResourcePath into x
			where !string.IsNullOrEmpty(x)
			select x).Distinct().ToArray();
		GlobalToolsNamespace.ProjectCookie?.Set("editor.openscenes", value);
		GlobalToolsNamespace.ProjectCookie?.Set("editor.activescene", Active?.Scene.Source?.ResourcePath);
	}

	/// <summary>
	/// Reopen the scenes that were open last session. Falls back to the project's
	/// startup scene (or a blank scene) if there's nothing to restore.
	/// </summary>
	internal static void RestoreOpenSessions()
	{
		string[] array = GlobalToolsNamespace.ProjectCookie?.Get("editor.openscenes", Array.Empty<string>()) ?? Array.Empty<string>();
		for (int i = 0; i < array.Length; i++)
		{
			CreateFromPath(array[i]);
		}
		if (All.Count == 0)
		{
			string text = Project.Current?.Config.GetMetaOrDefault<string>("StartupScene", null);
			SceneEditorSession sceneEditorSession = (string.IsNullOrWhiteSpace(text) ? null : CreateFromPath(text));
			if (sceneEditorSession == null)
			{
				sceneEditorSession = CreateDefault();
			}
			sceneEditorSession.MakeActive();
		}
		else
		{
			string activePath = GlobalToolsNamespace.ProjectCookie?.Get<string>("editor.activescene", null);
			(All.FirstOrDefault((SceneEditorSession x) => x.Scene.Source?.ResourcePath == activePath) ?? All[0]).MakeActive();
		}
	}

	/// <summary>
	/// Make a new SceneEditorSession with a default scene
	/// </summary>
	public static SceneEditorSession CreateDefault()
	{
		Scene scene = Scene.CreateEditorScene();
		using (scene.Push())
		{
			scene.Name = "Untitled Scene";
			GameObject gameObject = scene.CreateObject();
			gameObject.Name = "Main Camera";
			gameObject.LocalTransform = new Transform(Vector3.Up * 100f + Vector3.Backward * 300f);
			gameObject.Components.Create<CameraComponent>();
			GameObject gameObject2 = scene.CreateObject();
			gameObject2.Name = "Directional Light";
			gameObject2.LocalTransform = new Transform(Vector3.Up * 200f, Rotation.From(80f, 45f, 0f));
			gameObject2.Components.Create<DirectionalLight>();
			return new SceneEditorSession(scene);
		}
	}

	/// <summary>
	/// Opens an editor session from an existing scene or prefab
	/// </summary>
	public static SceneEditorSession CreateFromPath(string path)
	{
		Resource resource = null;
		Asset asset = AssetSystem.FindByPath(path);
		if (asset != null && asset.AssetType.FileExtension == "scene" && File.Exists(asset.GetSourceFile(absolute: true)))
		{
			resource = SceneSource.LoadForEditing(asset);
		}
		if (resource == null)
		{
			resource = ResourceLibrary.Get<Resource>(path);
		}
		if (resource == null)
		{
			resource = SceneFile.Load(path);
		}
		if (resource == null)
		{
			resource = PrefabFile.Load(path);
		}
		if (resource is SceneFile sceneFile)
		{
			if (sceneFile.IsCompiled)
			{
				GlobalGameNamespace.Log.Error($"Cannot edit compiled scene '{path}' without its .scene source file.");
				return null;
			}
			SceneEditorSession sceneEditorSession = Resolve(sceneFile);
			if (sceneEditorSession != null)
			{
				sceneEditorSession.MakeActive();
				return sceneEditorSession;
			}
			Scene scene = Scene.CreateEditorScene();
			using (scene.Push())
			{
				scene.Load(sceneFile);
				return new SceneEditorSession(scene);
			}
		}
		if (resource is PrefabFile prefabFile)
		{
			if (Resolve(prefabFile) is PrefabEditorSession prefabEditorSession)
			{
				prefabEditorSession.MakeActive();
				return prefabEditorSession;
			}
			PrefabScene prefabScene = PrefabScene.CreateForEditing();
			using (prefabScene.Push())
			{
				prefabScene.Load(prefabFile);
				return new PrefabEditorSession(prefabScene);
			}
		}
		return null;
	}

	public IEnumerable<object> GetSelection()
	{
		foreach (object item in Selection)
		{
			yield return item;
		}
	}

	public SceneFolder GetSceneFolder()
	{
		string text = Scene?.Source?.ResourcePath;
		if (text != null)
		{
			Asset asset = AssetSystem.FindByPath(text);
			if (asset != null)
			{
				string sourceFile = asset.GetSourceFile();
				string sourceFile2 = asset.GetSourceFile(absolute: true);
				if (string.IsNullOrEmpty(sourceFile) || string.IsNullOrEmpty(sourceFile2))
				{
					return null;
				}
				return new <SceneEditorSession>FB6E318FF087053CB71B522E5AEDE35D648DD1123A29E3E4C7D4F02E1057A0AD1__AssetFolderInstance(sourceFile, sourceFile2);
			}
		}
		return null;
	}

	void ResourceLibrary.IEventListener.OnRegister(GameResource resource)
	{
		if (resource is PrefabFile prefab)
		{
			EditorScene.UpdatePrefabInstancesInScene(Scene, prefab);
		}
	}

	void ResourceLibrary.IEventListener.OnUnregister(GameResource resource)
	{
		if (resource is PrefabFile prefab)
		{
			EditorScene.UpdatePrefabInstancesInScene(Scene, prefab);
		}
	}

	void ResourceLibrary.IEventListener.OnExternalChangesPostLoad(GameResource resource)
	{
		if (resource is PrefabFile prefab)
		{
			EditorScene.UpdatePrefabInstancesInScene(Scene, prefab);
		}
	}

	void NavMesh.IEventListener.OnAreaDefinitionChanged()
	{
		Scene.NavMesh?.UpdateAreaIds();
	}

	public void SetPlaying(Scene scene)
	{
		Assert.IsNull(Playing, "Attempted to create a game session while another is active.");
		GameSession = new GameEditorSession(this, scene);
		GameSession.DeserializeSelection(SerializeSelection());
		GameSession.MakeActive();
	}

	public virtual void StopPlaying()
	{
		GameSession?.Destroy();
		GameSession = null;
		MakeActive();
	}

	/// <summary>
	/// Serlialize the current selection to a json string. The aim here is to make something we can transfer back to objects.
	/// </summary>
	public string SerializeSelection()
	{
		return Json.Serialize((from x in Selection.OfType<GameObject>()
			select x.Id).Order().ToArray());
	}

	/// <summary>
	/// Take a json string created by SerializeSelection and turn it into a selection
	/// </summary>
	public void DeserializeSelection(string selection)
	{
		previousSavedSelection = selection;
		if (string.IsNullOrWhiteSpace(selection))
		{
			Selection.Clear();
			return;
		}
		Guid[] array = Json.Deserialize<Guid[]>(selection);
		Selection.Clear();
		Guid[] array2 = array;
		foreach (Guid guid in array2)
		{
			GameObject gameObject = Scene.Directory.FindByGuid(guid);
			if (gameObject != null)
			{
				Selection.Add(gameObject);
			}
		}
	}

	private void InitUndo()
	{
		UndoSystem.Initialize();
		UndoSystem.OnUndo = (UndoSystem.Entry x) =>
		{
			HasUnsavedChanges = true;
		};
		UndoSystem.OnRedo = (UndoSystem.Entry x) =>
		{
			HasUnsavedChanges = true;
		};
	}

	/// <summary>
	/// Temporarily disables undo/redo sounds.
	/// </summary>
	public IDisposable SuppressUndoSounds()
	{
		return new SuppressUndoSoundScope(this);
	}

	/// <summary>
	/// Take a full scene snapshot for the undo system. This is usually a last resort, if you can't do anything more incremental.
	/// </summary>
	[Obsolete("Manual full scene undo snapshots are no longer working use UndoScope or AddUndo")]
	public void FullUndoSnapshot(string title)
	{
	}

	/// <summary>
	/// Push the current selection into the undo system
	/// </summary>
	[Obsolete("Manual selections snapshots are no longer working use UndoScope or AddUndo")]
	public void PushUndoSelection()
	{
	}

	[Obsolete("EditLog is no longer working use UndoScope or AddUndo")]
	void Scene.ISceneEditorSession.OnEditLog(string name, object source)
	{
	}

	public void AddUndo(string name, Action undo, Action redo)
	{
		UndoSystem.Insert(name, undo, redo);
	}

	public ISceneUndoScope UndoScope(string name)
	{
		return new SceneUndoScope(this, name);
	}

	/// <summary>
	/// Cancels any open undo scopes, because we don't want the most
	/// recent change to appear in the undo stack.
	/// </summary>
	public void CancelUndoScope()
	{
		LastUndoSnapshot?.Cancel();
	}

	internal void SucceedUndoRedo()
	{
		if (!_suppressUndoSounds && EditorPreferences.UndoSounds)
		{
			EditorUtility.PlayRawSound("sounds/editor/success.wav");
		}
	}

	internal void FailUndoRedo()
	{
		if (!_suppressUndoSounds && EditorPreferences.UndoSounds)
		{
			EditorUtility.PlayRawSound("sounds/editor/fail.wav");
		}
	}
}
