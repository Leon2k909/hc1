using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using Editor;
using Facepunch.ActionGraphs;
using Sandbox.Audio;
using Sandbox.Diagnostics;
using Sandbox.Engine.Utility.RayTrace;
using Sandbox.Internal;
using Sandbox.Navigation;
using Sandbox.Network;
using Sandbox.Rendering;
using Sandbox.Tasks;
using Sandbox.UI;
using Sandbox.Utility;
using Sandbox.Volumes;

namespace Sandbox;

[SourceLocation("Scene\\Scene\\Scene.Camera.cs", 3)]
[SourceLocation("Scene\\Scene\\Scene.Components.cs", 5)]
[SourceLocation("Scene\\Scene\\Scene.cs", 7)]
[SourceLocation("Scene\\Scene\\Scene.DebugDraw.cs", 3)]
[SourceLocation("Scene\\Scene\\Scene.Deletes.cs", 3)]
[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 3)]
[SourceLocation("Scene\\Scene\\Scene.Event.cs", 3)]
[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 3)]
[SourceLocation("Scene\\Scene\\Scene.Loading.cs", 5)]
[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 7)]
[SourceLocation("Scene\\Scene\\Scene.NavMesh.cs", 3)]
[SourceLocation("Scene\\Scene\\Scene.Network.cs", 5)]
[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 17)]
[SourceLocation("Scene\\Scene\\Scene.Static.cs", 5)]
[Expose]
[SourceLocation("Scene\\Scene\\Scene.System.cs", 5)]
[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 5)]
[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 6)]
[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 6)]
public class Scene : GameObject
{
	public interface ISceneEditorSession
	{
		/// <summary>
		/// The scene for this session
		/// </summary>
		[Description("The scene for this session")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 16)]
		Scene Scene { get; }

		/// <summary>
		/// Whether this is the active editor session. Used for selection-driven previews.
		/// </summary>
		[Description("Whether this is the active editor session. Used for selection-driven previews.")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 21)]
		bool IsActive => true;

		/// <summary>
		/// True if this scene has unsaved changes
		/// </summary>
		[Description("True if this scene has unsaved changes")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 26)]
		bool HasUnsavedChanges { get; set; }

		/// <summary>
		/// Selection system for this session
		/// </summary>
		[Description("Selection system for this session")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 31)]
		SelectionSystem Selection { get; }

		/// <summary>
		/// If we have any gameobjects selected, return the first one
		/// </summary>
		[Description("If we have any gameobjects selected, return the first one")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 36)]
		GameObject SelectedGameObject => Selection.OfType<GameObject>().FirstOrDefault();

		/// <summary>
		/// Get the filesystem in which temporary files can be created. These files can be used (and shipped) by a package, but won't be stored in source control.
		/// This is usually used for files that are expected to be re-generated at runtime by the package itself.
		/// </summary>
		[Description("Get the filesystem in which temporary files can be created. These files can be used (and shipped) by a package, but won't be stored in source control. This is usually used for files that are expected to be re-generated at runtime by the package itself.")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 80)]
		BaseFileSystem TransientFilesystem { get; }

		/// <summary>
		/// You have changed the editor's selection, add a new undo entry
		/// </summary>
		[Obsolete]
		[Description("You have changed the editor's selection, add a new undo entry")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 41)]
		void AddSelectionUndo();

		[Obsolete]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 44)]
		void OnEditLog(string name, object source);

		/// <summary>
		/// Focus the editor camera onto this box
		/// </summary>
		[Description("Focus the editor camera onto this box")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 50)]
		void FrameTo(in BBox box);

		/// <summary>
		/// Save this scene to disk
		/// </summary>
		[Description("Save this scene to disk")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 55)]
		void Save(bool forceSaveAs);

		/// <summary>
		/// Tell undo about this property change
		/// </summary>
		[Obsolete]
		[Description("Tell undo about this property change")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 60)]
		void RecordChange(SerializedProperty property);

		/// <summary>
		/// Add a new undo entry
		/// </summary>
		[Description("Add a new undo entry")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 66)]
		void AddUndo(string name, Action undo, Action redo);

		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 68)]
		ISceneUndoScope UndoScope(string name);

		/// <summary>
		/// Gets the current selection from the editor
		/// </summary>
		[Obsolete("Use Selection")]
		[Description("Gets the current selection from the editor")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 73)]
		IEnumerable<object> GetSelection();

		/// <summary>
		/// Get the folder for this scene. This is a folder in which we can store assets that are referenced by this scene. Things like envmap textures, lightmaps, baked data, etc.
		/// </summary>
		[Description("Get the folder for this scene. This is a folder in which we can store assets that are referenced by this scene. Things like envmap textures, lightmaps, baked data, etc.")]
		[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 85)]
		SceneFolder GetSceneFolder()
		{
			return null;
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 139)]
	private sealed class SystemOverrideScope : IDisposable
	{
		[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 141)]
		private readonly Scene _scene;

		[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 142)]
		private readonly List<(GameObjectSystem System, PropertyDescription Property, object Value)> _overrides = new List<(GameObjectSystem, PropertyDescription, object)>();

		[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 143)]
		private bool _disposed;

		[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 145)]
		public bool HasOverrides => _overrides.Count > 0;

		public SystemOverrideScope(Scene scene)
		{
			_scene = scene;
		}

		[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 152)]
		public void AddOverride(GameObjectSystem system, PropertyDescription property, object previousValue, object value)
		{
			(GameObjectSystem, PropertyDescription) key = (system, property);
			_scene._preTransientSystemValues.TryAdd(key, previousValue);
			_overrides.Add((system, property, value));
		}

		[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 159)]
		public bool TryGetOverride(GameObjectSystem system, PropertyDescription property, out object value)
		{
			foreach (var @override in _overrides)
			{
				if (@override.System == system && @override.Property == property)
				{
					value = @override.Value;
					return true;
				}
			}
			value = null;
			return false;
		}

		[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 174)]
		public void Dispose()
		{
			if (!_disposed)
			{
				_disposed = true;
				_scene._transientSystemOverrides.Remove(this);
				for (int num = _overrides.Count - 1; num >= 0; num--)
				{
					var (system, property, _) = _overrides[num];
					_scene.RestoreTransientValue(system, property);
				}
				_overrides.Clear();
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Components.cs", 7)]
	internal HashSetEx<Component> pendingStartComponents = new HashSetEx<Component>();

	[SourceLocation("Scene\\Scene\\Scene.cs", 29)]
	private bool _destroyed;

	[SourceLocation("Scene\\Scene\\Scene.cs", 30)]
	private SceneWorld _sceneWorld;

	[SourceLocation("Scene\\Scene\\Scene.cs", 77)]
	private Gizmo.Instance gizmoInstance = new Gizmo.Instance();

	[SourceLocation("Scene\\Scene\\Scene.cs", 99)]
	private PhysicsWorld _physicsWorld;

	[SourceLocation("Scene\\Scene\\Scene.cs", 100)]
	private ScenePhysicsMode _physicsMode;

	[SourceLocation("Scene\\Scene\\Scene.cs", 314)]
	private static Superluminal _renderTimer = new Superluminal("Scene.Render", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.cs", 315)]
	private static Superluminal _cameraRenderTimer = new Superluminal("Camera", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.cs", 400)]
	private VolumeSystem _volumeSystem;

	[SourceLocation("Scene\\Scene\\Scene.Deletes.cs", 5)]
	private HashSet<GameObject> deleteList = new HashSet<GameObject>();

	[SourceLocation("Scene\\Scene\\Scene.Loading.cs", 7)]
	private readonly List<LoadingContext> _loadingTasks = new List<LoadingContext>();

	[SourceLocation("Scene\\Scene\\Scene.Loading.cs", 8)]
	private Task _loadingMainTask;

	[SourceLocation("Scene\\Scene\\Scene.NavMesh.cs", 7)]
	private Task _navMeshLoadTask;

	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 15)]
	internal readonly HashSet<NetworkObject> networkedObjects = new HashSet<NetworkObject>();

	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 31)]
	private RealTimeSince _timeSinceNetworkUpdate = 0f;

	/// <summary>
	/// A cache of all the MapInstances that gets updated every frame
	/// </summary>
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 189)]
	private readonly List<MapInstance> _networkMapInstanceCache = new List<MapInstance>();

	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 190)]
	private readonly List<IDeltaSnapshot> _dirtySnapshotObjects = new List<IDeltaSnapshot>();

	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 191)]
	private readonly List<IDeltaSnapshot> _cleanSnapshotObjects = new List<IDeltaSnapshot>();

	[SuppressNullKeyWarning]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 20)]
	private Dictionary<Type, HashSetEx<object>> objectIndex = new Dictionary<Type, HashSetEx<object>>();

	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 24)]
	private HashSet<object> objectsInIndex = new HashSet<object>();

	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 27)]
	internal HashSetEx<Component> updateComponents = new HashSetEx<Component>();

	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 28)]
	internal HashSetEx<Component> fixedUpdateComponents = new HashSetEx<Component>();

	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 29)]
	internal HashSetEx<Component> preRenderComponents = new HashSetEx<Component>();

	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 35)]
	private static readonly ReflectionCache<Type, Type[]> indexableTypesCache = new ReflectionCache<Type, Type[]>((Type rootType) =>
	{
		List<Type> list = new List<Type>();
		Type type = rootType;
		while ((object)type != null && !(type == typeof(object)) && !(type == typeof(Component)) && !(type == typeof(GameObjectSystem)) && !(type == typeof(Panel)) && !(type == typeof(Label)))
		{
			list.Add(type);
			list.AddRange(type.GetInterfaces());
			type = type.BaseType;
		}
		return list.ToArray();
	});

	[SourceLocation("Scene\\Scene\\Scene.System.cs", 8)]
	private Dictionary<Type, GameObjectSystem> systems = new Dictionary<Type, GameObjectSystem>();

	[SourceLocation("Scene\\Scene\\Scene.System.cs", 127)]
	private Dictionary<GameObjectSystem.Stage, TimedCallbackList> listeners = new Dictionary<GameObjectSystem.Stage, TimedCallbackList>();

	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 7)]
	private readonly List<SystemOverrideScope> _transientSystemOverrides = new List<SystemOverrideScope>();

	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 8)]
	private readonly Dictionary<(GameObjectSystem System, PropertyDescription Property), object> _preTransientSystemValues = new Dictionary<(GameObjectSystem, PropertyDescription), object>();

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 8)]
	private FixedUpdate fixedUpdate = new FixedUpdate();

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 40)]
	private double estimatedServerTime;

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 108)]
	private List<CameraComponent> _cameraViewScratch = new List<CameraComponent>();

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 132)]
	private List<Component.IRenderThread> renderThreadEventTargets = new List<Component.IRenderThread>();

	/// <summary>
	/// Screen panels in draw order, captured in PreRender(). Sorted here so the render
	/// thread neither walks the object index nor sorts every frame.
	/// </summary>
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 138)]
	internal List<ScreenPanel> renderScreenPanels = new List<ScreenPanel>();

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 176)]
	private static Superluminal _updateTimer = new Superluminal("Scene.Update", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 177)]
	private static Superluminal _preRenderTimer = new Superluminal("Scene.PreRender", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 178)]
	private static Superluminal _signalUpdateBones = new Superluminal("Signal.UpdateBones", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 179)]
	private static Superluminal _signalStarthUpdate = new Superluminal("Signal.StartUpdate", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 180)]
	private static Superluminal _signalFinishUpdate = new Superluminal("Signal.FinishUpdate", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 342)]
	private static Superluminal _fixedUpdateTimer = new Superluminal("Scene.FixedUpdate", Color.Cyan);

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 343)]
	private static Superluminal _processDeletesTimer = new Superluminal("ProcessDeletes", Color.Orange);

	[ThreadStatic]
	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 11)]
	private static List<PhysicsTraceResult> _physicsTraceScratch;

	[ActionGraphInclude]
	[SourceLocation("Scene\\Scene\\Scene.Camera.cs", 5)]
	public CameraComponent Camera { get; private set; }

	[SourceLocation("Scene\\Scene\\Scene.cs", 9)]
	public bool IsEditor { get; private set; }

	/// <summary>
	/// Pause scene updates, rendering, UI and spatial audio without destroying their state.
	/// Overlays, local audio and external async work remain active.
	/// </summary>
	[Description("Pause scene updates, rendering, UI and spatial audio without destroying their state. Overlays, local audio and external async work remain active.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 15)]
	internal bool IsSuspended { get; set; }

	/// <summary>
	/// A snapshot is currently creating objects whose map content it already supplies.
	/// </summary>
	[Description("A snapshot is currently creating objects whose map content it already supplies.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 20)]
	internal bool IsLoadingSnapshot { get; private set; }

	/// <summary>
	/// True if the scene world has been created. Reading <see cref="P:Sandbox.Scene.SceneWorld" /> creates
	/// it - check this first when you only want to act on a world that already exists.
	/// </summary>
	[Description("True if the scene world has been created. Reading <span style=\"color: #4EC9B0;\">Scene</span>.<span style=\"color: #DCDCDC;\">SceneWorld</span> creates it - check this first when you only want to act on a world that already exists.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 36)]
	internal bool HasSceneWorld => _sceneWorld != null;

	/// <summary>
	/// True if the physics world has been created. Reading <see cref="P:Sandbox.Scene.PhysicsWorld" /> creates
	/// it - check this first when you only want to act on a world that already exists.
	/// </summary>
	[Description("True if the physics world has been created. Reading <span style=\"color: #4EC9B0;\">Scene</span>.<span style=\"color: #DCDCDC;\">PhysicsWorld</span> creates it - check this first when you only want to act on a world that already exists.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 42)]
	internal bool HasPhysicsWorld => _physicsWorld.IsValid();

	/// <summary>
	/// The scene world, holding this scene's renderables. Created on first access, so
	/// scenes that never render anything (like prefab caches or tests) never create one.
	/// </summary>
	[Description("The scene world, holding this scene's renderables. Created on first access, so scenes that never render anything (like prefab caches or tests) never create one.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 48)]
	public SceneWorld SceneWorld
	{
		get
		{
			if (_sceneWorld == null && !_destroyed)
			{
				_sceneWorld = new SceneWorld();
			}
			return _sceneWorld;
		}
		private set
		{
			_sceneWorld = value;
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 62)]
	public SceneWorld DebugSceneWorld => gizmoInstance?.World;

	[Obsolete("Use Scene.Editor.HasUnsavedChanges")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 64)]
	public bool HasUnsavedChanges { get; private set; }

	[SourceLocation("Scene\\Scene\\Scene.cs", 67)]
	public GameResource Source { get; internal set; }

	/// <summary>
	/// For scenes within a hammer MapWorld, for action graph stack traces,
	/// and so the editor knows the map must be saved when editing graphs from it.
	/// </summary>
	[Description("For scenes within a hammer MapWorld, for action graph stack traces, and so the editor knows the map must be saved when editing graphs from it.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 73)]
	internal ISourceLocation OverrideSourceLocation { get; set; }

	[SourceLocation("Scene\\Scene\\Scene.cs", 75)]
	public GameObjectDirectory Directory { get; private set; }

	[JsonIgnore]
	[Obsolete("please use the SceneInformation component")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 79)]
	public string Title { get; set; }

	[JsonIgnore]
	[Obsolete("please use the SceneInformation component")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 83)]
	public string Description { get; set; }

	/// <summary>
	/// If true we'll additive load the system scene when this scene is loaded. Defaults
	/// to true. You might want to disable this for specific scenes, like menu scenes etc.
	/// </summary>
	[Property]
	[DefaultValue(true)]
	[Description("If true we'll additive load the system scene when this scene is loaded. Defaults to true. You might want to disable this for specific scenes, like menu scenes etc.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 91)]
	public bool WantsSystemScene { get; set; } = true;

	/// <summary>
	/// Global render attributes accessible on any renderable in this Scene.
	/// </summary>
	[Description("Global render attributes accessible on any renderable in this Scene.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 97)]
	public RenderAttributes RenderAttributes { get; }

	/// <summary>
	/// Which physics simulation this scene runs. The physics world is built for one mode, so this
	/// is chosen once when the scene is authored and can't be changed while the scene is running.
	/// </summary>
	[Property]
	[Description("Which physics simulation this scene runs. The physics world is built for one mode, so this is chosen once when the scene is authored and can't be changed while the scene is running.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 106)]
	public ScenePhysicsMode PhysicsMode
	{
		get
		{
			return _physicsMode;
		}
		set
		{
			if (_physicsMode != value)
			{
				if (HasPhysicsWorld && !IsEditor)
				{
					GlobalSystemNamespace.Log.Warning(FormattableStringFactory.Create("Can't change {0} once the physics world exists - reload the scene instead", "PhysicsMode"));
				}
				else
				{
					_physicsMode = value;
				}
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 127)]
	internal bool Is2D => PhysicsMode == ScenePhysicsMode.Physics2D;

	/// <summary>
	/// Hash of scene settings that require a world reload when changed.
	/// </summary>
	[Description("Hash of scene settings that require a world reload when changed.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 132)]
	internal int ReloadHash => HashCode.Combine(PhysicsMode);

	[SourceLocation("Scene\\Scene\\Scene.cs", 134)]
	public PhysicsWorld PhysicsWorld => _physicsWorld ?? (_physicsWorld = CreatePhysicsWorld());

	/// <summary>
	/// Returns true if this scene has not been destroyed
	/// </summary>
	[Description("Returns true if this scene has not been destroyed")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 192)]
	public override bool IsValid => !_destroyed;

	/// <summary>
	/// Cache all enabled and disabled cameras in the scene.
	/// Registered/Deregistered in CameraComponent.OnAwake and OnDestroy.
	/// </summary>
	[Description("Cache all enabled and disabled cameras in the scene. Registered/Deregistered in CameraComponent.OnAwake and OnDestroy.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 360)]
	internal HashSet<CameraComponent> Cameras { get; } = new HashSet<CameraComponent>();

	/// <summary>
	/// Allows quickly finding components that have a volume
	/// </summary>
	[Description("Allows quickly finding components that have a volume")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 405)]
	public VolumeSystem Volumes => _volumeSystem ?? (_volumeSystem = GameObjectSystem<VolumeSystem>.Get(this));

	/// <summary>
	/// Allows access to the scene's editor session from the game. This will be null if there is no
	/// editor session active on this scene.
	/// </summary>
	[Description("Allows access to the scene's editor session from the game. This will be null if there is no editor session active on this scene.")]
	[SourceLocation("Scene\\Scene\\Scene.Editor.cs", 9)]
	public ISceneEditorSession Editor { get; internal set; }

	/// <summary>
	/// Default scene sound listener, at the camera.
	/// </summary>
	[Description("Default scene sound listener, at the camera.")]
	[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 8)]
	internal Listener Listener { get; set; }

	/// <summary>
	/// Multiple scene sound listeners, created by audio listener components.
	/// </summary>
	[Description("Multiple scene sound listeners, created by audio listener components.")]
	[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 13)]
	internal HashSet<Listener> Listeners { get; private set; }

	/// <summary>
	/// Return true if we're in an initial loading phase
	/// </summary>
	[Description("Return true if we're in an initial loading phase")]
	[SourceLocation("Scene\\Scene\\Scene.Loading.cs", 27)]
	public bool IsLoading
	{
		get
		{
			_loadingTasks.RemoveAll((LoadingContext x) => x.IsCompleted);
			if (_loadingMainTask == null)
			{
				return false;
			}
			if (_loadingMainTask.IsCompleted)
			{
				return false;
			}
			return true;
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.NavMesh.cs", 5)]
	public NavMesh NavMesh { get; private set; } = new NavMesh();

	[Obsolete("Moved to ProjectSettings.Networking.UpdateRate")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 7)]
	public float NetworkFrequency { get; set; }

	/// <summary>
	/// One divided by ProjectSettings.Networking.UpdateRate.
	/// </summary>
	[Description("One divided by ProjectSettings.Networking.UpdateRate.")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 13)]
	public float NetworkRate => 1f / ProjectSettings.Networking.UpdateRate.Clamp(1f, 500f);

	[SourceLocation("Scene\\Scene\\Scene.Static.cs", 7)]
	private static WeakHashSet<Scene> _all { get; set; } = new WeakHashSet<Scene>();

	/// <summary>
	/// All active non-editor scenes.
	/// </summary>
	[Description("All active non-editor scenes.")]
	[SourceLocation("Scene\\Scene\\Scene.Static.cs", 12)]
	public static IEnumerable<Scene> All => _all.Where((Scene x) => !x.IsEditor && x.Active);

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 9)]
	public bool IsFixedUpdate { get; private set; }

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 11)]
	public float FixedDelta => (float)fixedUpdate.Delta;

	[Obsolete("Moved to Sandbox.ProjectSettings.PhysicsSettings")]
	[DefaultValue(50f)]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 13)]
	public float FixedUpdateFrequency { get; set; } = 50f;

	[Obsolete("Moved to Sandbox.ProjectSettings.PhysicsSettings")]
	[DefaultValue(5)]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 14)]
	public int MaxFixedUpdates { get; set; } = 5;

	[Obsolete("Moved to Sandbox.ProjectSettings.PhysicsSettings")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 15)]
	public int PhysicsSubSteps { get; set; }

	[Obsolete("Unused. Animation is always threaded.")]
	[DefaultValue(true)]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 16)]
	public bool ThreadedAnimation { get; set; } = true;

	[Obsolete("Moved to Sandbox.ProjectSettings.PhysicsSettings")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 17)]
	public bool UseFixedUpdate { get; set; }

	[Property]
	[Range(0f, 1f)]
	[DefaultValue(1f)]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 19)]
	public float TimeScale { get; set; } = 1f;

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 55)]
	internal double TimeNow { get; private set; }

	[DefaultValue(0.1)]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 56)]
	internal double TimeDelta { get; private set; } = 0.1;

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 340)]
	private Input.Context FixedUpdateInputContext { get; set; } = Input.Context.Create("Scene.FixedUpdate");

	[ActionGraphIgnore]
	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 8)]
	public SceneTrace Trace => new SceneTrace(this);

	[SourceLocation("Scene\\Scene\\Scene.Camera.cs", 8)]
	internal void UpdateMainCamera()
	{
		Camera = (from x in GetAllComponents<CameraComponent>()
			where !x.IsSceneEditorCamera
			orderby (!x.IsMainCamera) ? 1 : 0, x.Priority
			select x).FirstOrDefault();
	}

	/// <summary>
	/// Called for every enabled component
	/// </summary>
	[Description("Called for every enabled component")]
	[SourceLocation("Scene\\Scene\\Scene.Components.cs", 12)]
	internal void RegisterComponent(Component c)
	{
		AddObjectToDirectory(c);
		pendingStartComponents.Add(c);
	}

	[SourceLocation("Scene\\Scene\\Scene.Components.cs", 19)]
	internal void UnregisterComponent(Component c)
	{
		RemoveObjectFromDirectory(c);
		pendingStartComponents.Remove(c);
	}

	/// <summary>
	/// Get all components of type. This can include interfaces.
	/// This function can only find enabled/active components.
	/// </summary>
	[Pure]
	[Description("Get all components of type. This can include interfaces. This function can only find enabled/active components.")]
	[SourceLocation("Scene\\Scene\\Scene.Components.cs", 30)]
	public IEnumerable<T> GetAllComponents<T>()
	{
		return GetAll<T>();
	}

	/// <summary>
	/// Get all components of type. This can include interfaces.
	/// This function can only find enabled/active components.
	/// </summary>
	[Pure]
	[Description("Get all components of type. This can include interfaces. This function can only find enabled/active components.")]
	[SourceLocation("Scene\\Scene\\Scene.Components.cs", 40)]
	public IEnumerable<Component> GetAllComponents(Type type)
	{
		if (!objectIndex.TryGetValue(type, out var value))
		{
			yield break;
		}
		foreach (object item in value.EnumerateLocked())
		{
			Component component = item as Component;
			if (component.IsValid())
			{
				yield return component;
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 22)]
	internal IDisposable LoadingSnapshotScope()
	{
		bool previous = IsLoadingSnapshot;
		IsLoadingSnapshot = true;
		return new DisposeAction(() =>
		{
			IsLoadingSnapshot = previous;
		});
	}

	/// <summary>
	/// Creates the physics world for this scene, matching <see cref="P:Sandbox.Scene.PhysicsMode" />.
	/// </summary>
	[Description("Creates the physics world for this scene, matching <span style=\"color: #4EC9B0;\">Scene</span>.<span style=\"color: #DCDCDC;\">PhysicsMode</span>.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 139)]
	private PhysicsWorld CreatePhysicsWorld()
	{
		if (PhysicsMode == ScenePhysicsMode.Physics2D)
		{
			return new PhysicsWorld2d
			{
				Gravity = Vector2.Down * 850f,
				Scene = this,
				CollisionRules = ProjectSettings.Collision
			}.Owner;
		}
		return new PhysicsWorld3d
		{
			Gravity = Vector3.Down * 850f,
			SimulationMode = PhysicsSimulationMode.Continuous,
			DebugSceneWorld = DebugSceneWorld,
			Scene = this,
			CollisionRules = ProjectSettings.Collision
		}.Owner;
	}

	protected Scene(bool isEditor)
		: base(enabled: true, "Scene")
	{
		_all.Add(this);
		Directory = new GameObjectDirectory(this);
		RenderAttributes = new RenderAttributes();
		IsEditor = isEditor;
		if (!(this is PrefabCacheScene))
		{
			InitSystems();
		}
	}

	public Scene()
		: this(isEditor: false)
	{
	}

	~Scene()
	{
		MainThread.Queue(DestroyInternal);
	}

	/// <summary>
	/// Destroy this scene. After this you should never use it again.
	/// </summary>
	[Description("Destroy this scene. After this you should never use it again.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 197)]
	public override void Destroy()
	{
		DestroyInternal();
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 202)]
	internal virtual void DestroyInternal()
	{
		_all.Remove(this);
		ClearObjectIndex();
		Clear();
		ProcessDeletes();
		ShutdownSystems();
		GC.SuppressFinalize(this);
		_destroyed = true;
		_physicsWorld?.Delete();
		_physicsWorld = null;
		SceneWorld?.Delete();
		SceneWorld = null;
		gizmoInstance?.Dispose();
		gizmoInstance = null;
		NavMesh?.Dispose();
		NavMesh = null;
		DisposeListeners();
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 238)]
	public static Scene CreateEditorScene()
	{
		return new Scene(isEditor: true);
	}

	/// <summary>
	/// Create a GameObject on this scene. This doesn't require the scene to be the active scene.
	/// </summary>
	[Description("Create a GameObject on this scene. This doesn't require the scene to be the active scene.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 246)]
	public GameObject CreateObject(bool enabled = true)
	{
		using (Push())
		{
			return new GameObject(enabled)
			{
				Enabled = enabled,
				Parent = this
			};
		}
	}

	/// <summary>
	/// Push this scene as the active scene, for a scope
	/// </summary>
	[Description("Push this scene as the active scene, for a scope")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 261)]
	public IDisposable Push()
	{
		return new ScenePushScope(this);
	}

	/// <summary>
	/// Collects anything inside into a batch group. A batchgroup is used with GameObject and Components to
	/// make sure that their OnEnable/OnDisable and other callbacks are called in a deterministic order,
	/// and that they can find each other during creation. <see cref="M:Sandbox.GameObject.NetworkSpawn" /> calls will also be batched.
	/// </summary>
	[SourceLocation("Scene\\Scene\\Scene.cs", 271)]
	public IDisposable BatchGroup()
	{
		IDisposable networkScope = SceneNetworkSystem.Instance?.NetworkSpawnBatch();
		CallbackBatch callbackScope = CallbackBatch.Isolated("BatchGroup");
		return DisposeAction.Create(() =>
		{
			callbackScope?.Dispose();
			networkScope?.Dispose();
		});
	}

	[Obsolete]
	[SourceLocation("Scene\\Scene\\Scene.cs", 283)]
	public void ClearUnsavedChanges()
	{
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 288)]
	internal override void OnHotload()
	{
		base.OnHotload();
		SceneNetworkSystem.Instance?.OnHotload();
		foreach (GameObject allGameObject in Directory.AllGameObjects)
		{
			if (allGameObject != this)
			{
				allGameObject.OnHotload();
			}
		}
		foreach (NetworkObject networkedObject in networkedObjects)
		{
			networkedObject.OnHotload();
		}
		foreach (GameObjectSystem value in systems.Values)
		{
			value.OnHotload();
		}
		HotloadObjectIndex();
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 317)]
	internal void Render(SwapChainHandle_t swapChain, Vector2? size)
	{
		if (IsSuspended)
		{
			return;
		}
		using (_renderTimer.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.cs", 322, "Render"))
		{
			PreCameraRender();
			foreach (CameraComponent item in Cameras.OrderBy((CameraComponent x) => x.Priority))
			{
				if (item.Active && !item.IsSceneEditorCamera)
				{
					using (_cameraRenderTimer.Start(item.GameObject?.Name, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.cs", 332, "Render"))
					{
						item.AddToRenderList(swapChain, size);
					}
				}
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.cs", 337)]
	internal void RenderEnvmaps()
	{
		if (IsSuspended)
		{
			return;
		}
		if (Graphics.IsActive)
		{
			if (!Application.IsRetail)
			{
				GlobalSystemNamespace.Log.Error("Attempted to render envmaps while inside a render pass!");
			}
			return;
		}
		foreach (EnvmapProbe item in (from x in GetAllComponents<EnvmapProbe>()
			where x.Dirty
			select x).Take(1))
		{
			item.RenderCubemap();
		}
	}

	/// <summary>
	/// Should be called before rendering. This allows things like reflections to render.
	/// </summary>
	[Description("Should be called before rendering. This allows things like reflections to render.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 365)]
	internal void PreCameraRender()
	{
		foreach (CameraComponent item in Cameras.OrderBy((CameraComponent x) => x.Priority))
		{
			item.InitializeRendering();
		}
		Color c = Color.Transparent;
		foreach (DirectionalLight item2 in Query<DirectionalLight>())
		{
			if (!Camera.IsValid() || !item2.Tags.HasAny(Camera.RenderExcludeTags))
			{
				c += item2.SkyColor;
			}
		}
		foreach (AmbientLight allComponent in GetAllComponents<AmbientLight>())
		{
			if (!Camera.IsValid() || !allComponent.Tags.HasAny(Camera.RenderExcludeTags))
			{
				c += allComponent.Color;
			}
		}
		if (SceneWorld.IsValid())
		{
			SceneWorld.AmbientLightColor = c;
		}
	}

	/// <summary>
	/// Adds the "system" scene, which is defined in the project settings.
	/// </summary>
	[Description("Adds the \"system\" scene, which is defined in the project settings.")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 410)]
	internal void AddSystemScene()
	{
		if (WantsSystemScene)
		{
			string text = Application.GamePackage?.GetMeta("SystemScene", "") ?? null;
			if (!string.IsNullOrWhiteSpace(text))
			{
				SceneLoadOptions sceneLoadOptions = new SceneLoadOptions();
				sceneLoadOptions.IsSystemScene = true;
				sceneLoadOptions.IsAdditive = true;
				sceneLoadOptions.SetScene(text);
				Load(sceneLoadOptions);
			}
		}
	}

	/// <summary>
	/// Find objects with all tags
	/// </summary>
	[Description("Find objects with all tags")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 431)]
	public IEnumerable<GameObject> FindAllWithTags(IEnumerable<string> tags)
	{
		foreach (GameObject allGameObject in Directory.AllGameObjects)
		{
			if (allGameObject.Tags.HasAll(tags))
			{
				yield return allGameObject;
			}
		}
	}

	/// <summary>
	/// Find objects with tag
	/// </summary>
	[Description("Find objects with tag")]
	[SourceLocation("Scene\\Scene\\Scene.cs", 445)]
	public IEnumerable<GameObject> FindAllWithTag(string tag)
	{
		return Directory.AllGameObjects.Where((GameObject x) => x.Tags.Has(tag));
	}

	[SourceLocation("Scene\\Scene\\Scene.DebugDraw.cs", 5)]
	private void DebugDraw()
	{
		NavMesh.DebugDraw();
	}

	/// <summary>
	/// Adds a GameObject to delete later
	/// </summary>
	[Description("Adds a GameObject to delete later")]
	[SourceLocation("Scene\\Scene\\Scene.Deletes.cs", 10)]
	internal void QueueDelete(GameObject gameObject)
	{
		deleteList.Add(gameObject);
	}

	/// <summary>
	/// Delete any GameObjects waiting to be deleted
	/// </summary>
	[Description("Delete any GameObjects waiting to be deleted")]
	[SourceLocation("Scene\\Scene\\Scene.Deletes.cs", 18)]
	public void ProcessDeletes()
	{
		if (deleteList.Count > 0)
		{
			GameObject[] array = deleteList.ToArray();
			foreach (GameObject gameObject in array)
			{
				gameObject.DestroyImmediate();
				deleteList.Remove(gameObject);
			}
		}
		_sceneWorld?.DeletePendingObjects();
	}

	/// <summary>
	/// Run an event on all components. The find argument is unused when calling this on a scene.
	/// </summary>
	[Description("Run an event on all components. The find argument is unused when calling this on a scene.")]
	[SourceLocation("Scene\\Scene\\Scene.Event.cs", 8)]
	public override void RunEvent<T>(Action<T> action, FindMode find = FindMode.EnabledInSelfAndDescendants)
	{
		foreach (T item in GetAll<T>())
		{
			try
			{
				action(item);
			}
			catch (Exception ex)
			{
				GlobalSystemNamespace.Log.Warning(ex, ex.Message);
			}
		}
	}

	/// <summary>
	/// Run an IRenderThread event using the snapshot captured in PreRender().
	/// Safe to call from the render thread — iterates a plain List that the main thread
	/// does not touch until the next PreRender().
	/// </summary>
	[Description("Run an IRenderThread event using the snapshot captured in PreRender(). Safe to call from the render thread — iterates a plain List that the main thread does not touch until the next PreRender().")]
	[SourceLocation("Scene\\Scene\\Scene.Event.cs", 29)]
	internal void RunRenderThreadEvent(CameraComponent camera, Stage stage)
	{
		foreach (Component.IRenderThread renderThreadEventTarget in renderThreadEventTargets)
		{
			try
			{
				renderThreadEventTarget.OnRenderStage(camera, stage);
			}
			catch (Exception ex)
			{
				GlobalSystemNamespace.Log.Warning(ex, ex.Message);
			}
		}
	}

	/// <summary>
	/// Update default sound listener to camera.
	/// </summary>
	[Description("Update default sound listener to camera.")]
	[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 18)]
	private void UpdateDefaultListener()
	{
		if (Listener == null)
		{
			Listener listener = (Listener = new Listener(this));
		}
		Listener.Transform = new Transform(Camera.WorldPosition, Camera.WorldRotation);
	}

	/// <summary>
	/// Dispose any sound listeners we created.
	/// </summary>
	[Description("Dispose any sound listeners we created.")]
	[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 28)]
	private void DisposeListeners()
	{
		Listener?.Dispose();
		Listener = null;
		if (Listeners == null)
		{
			return;
		}
		foreach (Listener listener in Listeners)
		{
			listener?.Dispose();
		}
		Listeners.Clear();
		Listeners = null;
	}

	/// <summary>
	/// Add a new sound listener and return it.
	/// </summary>
	[Description("Add a new sound listener and return it.")]
	[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 48)]
	internal Listener AddListener()
	{
		if (Listeners == null)
		{
			HashSet<Listener> hashSet = (Listeners = new HashSet<Listener>());
		}
		Listener listener = new Listener(this);
		Listeners.Add(listener);
		return listener;
	}

	/// <summary>
	/// Remove and dispose a scene sound listener.
	/// </summary>
	[Description("Remove and dispose a scene sound listener.")]
	[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 59)]
	internal void RemoveListener(Listener listener)
	{
		if (listener != null && Listeners.Remove(listener))
		{
			listener?.Dispose();
		}
	}

	/// <summary>
	/// Find the closest sound listener at this point.
	/// </summary>
	[Description("Find the closest sound listener at this point.")]
	[SourceLocation("Scene\\Scene\\Scene.Listener.cs", 73)]
	internal Listener FindClosestListener(Vector3 point)
	{
		if (Listeners == null || Listeners.Count == 0)
		{
			return Listener;
		}
		Listener listener = Listener;
		float num = ((listener == null) ? float.MaxValue : Vector3.DistanceBetweenSquared(listener.Position, in point));
		foreach (Listener listener2 in Listeners)
		{
			float num2 = Vector3.DistanceBetweenSquared(listener2.Position, in point);
			if (num2 < num)
			{
				num = num2;
				listener = listener2;
			}
		}
		return listener;
	}

	[SourceLocation("Scene\\Scene\\Scene.Loading.cs", 10)]
	internal void AddLoadingTask(LoadingContext loadingTask)
	{
		_loadingTasks.Add(loadingTask);
		LoadingScreen.UpdateLoadingTasks(_loadingTasks);
	}

	[SourceLocation("Scene\\Scene\\Scene.Loading.cs", 16)]
	public void StartLoading()
	{
		if (_loadingMainTask == null)
		{
			_loadingMainTask = WaitForLoading();
		}
	}

	/// <summary>
	/// Wait for scene loading to finish
	/// </summary>
	[Description("Wait for scene loading to finish")]
	[SourceLocation("Scene\\Scene\\Scene.Loading.cs", 43)]
	internal async Task WaitForLoading()
	{
		if (_loadingMainTask != null)
		{
			await _loadingMainTask;
			return;
		}
		try
		{
			IGameInstance instance = IGameInstance.Current;
			await Task.Yield();
			while (_loadingTasks.Count > 0)
			{
				LoadingScreen.UpdateLoadingTasks(_loadingTasks);
				await Task.WhenAny(_loadingTasks.Select((LoadingContext x) => x.Task));
				_loadingTasks.RemoveAll((LoadingContext x) => x.IsCompleted);
			}
			LoadingScreen.UpdateLoadingTasks(new List<LoadingContext>());
			if (!IsValid)
			{
				return;
			}
			if (NavMesh.IsEnabled && !(this is PrefabScene))
			{
				LoadingScreen.Subtitle = "Generating NavMesh..";
				await NavMesh.Load(PhysicsWorld);
				LoadingScreen.Subtitle = "Loading Finished..";
			}
			if (!IsValid)
			{
				return;
			}
			using (Push())
			{
				instance?.OnLoadingFinished();
				RunEvent((ISceneLoadingEvents x) =>
				{
					x.AfterLoad(this);
				});
				RunPendingStarts();
				if (WantsSystemScene && !(this is PrefabScene))
				{
					g_pRenderDevice.FlushPipelineCache();
				}
				GameNetworkSystem.OnLoadedScene(Components.Get<SceneInformation>()?.Title);
			}
		}
		finally
		{
			_loadingMainTask = null;
			LoadingScreen.IsVisible = false;
		}
	}

	/// <summary>
	/// Load from the provided <see cref="T:Sandbox.SceneFile" />. This will not load the scene for other clients in a
	/// multiplayer session, you should instead use <see cref="M:Sandbox.Game.ChangeScene(Sandbox.SceneLoadOptions)" />
	/// if you want to bring other clients.
	/// </summary>
	[Description("Load from the provided <span style=\"color: #4EC9B0;\">SceneFile</span>. This will not load the scene for other clients in a multiplayer session, you should instead use <span style=\"color: #4EC9B0;\">Game</span>.<span style=\"color: #DCDCAA;\">ChangeScene</span>(<span style=\"color: #4EC9B0;\">SceneLoadOptions</span>) if you want to bring other clients.")]
	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 14)]
	public virtual bool Load(GameResource resource)
	{
		if (resource is SceneFile scene)
		{
			SceneLoadOptions sceneLoadOptions = new SceneLoadOptions();
			if (!sceneLoadOptions.SetScene(scene))
			{
				return false;
			}
			return Load(sceneLoadOptions);
		}
		return false;
	}

	/// <summary>
	/// Load from the provided <see cref="T:Sandbox.SceneLoadOptions" />. This will not load the scene for other clients in a
	/// multiplayer session, you should instead use <see cref="M:Sandbox.Game.ChangeScene(Sandbox.SceneLoadOptions)" />
	/// if you want to bring other clients.
	/// </summary>
	[Description("Load from the provided <span style=\"color: #4EC9B0;\">SceneLoadOptions</span>. This will not load the scene for other clients in a multiplayer session, you should instead use <span style=\"color: #4EC9B0;\">Game</span>.<span style=\"color: #DCDCAA;\">ChangeScene</span>(<span style=\"color: #4EC9B0;\">SceneLoadOptions</span>) if you want to bring other clients.")]
	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 34)]
	public bool Load(SceneLoadOptions options)
	{
		using (options.RuntimePreparationScope())
		{
			if (!IsEditor && !options.PrepareRuntime())
			{
				return false;
			}
			SceneFile sceneFile = options.GetSceneFile();
			if (!sceneFile.IsValid())
			{
				GlobalSystemNamespace.Log.Error("No valid Scene was found in SceneLoadOptions.");
				return false;
			}
			if (sceneFile.ResourceName != null)
			{
				Name = sceneFile.ResourceName;
			}
			ProcessDeletes();
			if (!options.IsAdditive)
			{
				if (options.DeleteEverything)
				{
					Clear(includeSaved: true);
				}
				else
				{
					foreach (GameObject item in from x in GetAllObjects(enabled: false)
						where x.Flags.Contains(GameObjectFlags.DontDestroyOnLoad)
						select x)
					{
						bool flag = false;
						for (GameObject parent = item.Parent; parent != this; parent = parent.Parent)
						{
							if (parent != null && parent.Flags.Contains(GameObjectFlags.DontDestroyOnLoad))
							{
								flag = true;
								break;
							}
						}
						if (!flag)
						{
							item.SetParent(this);
						}
					}
					Clear(includeSaved: false);
				}
				ProcessDeletes();
				NavMesh.Reset();
			}
			if (!IsEditor && options.ShowLoadingScreen)
			{
				StartLoading();
				LoadingScreen.IsVisible = true;
				LoadingScreen.Title = "Loading Scene";
			}
			RunEvent((ISceneLoadingEvents x) =>
			{
				x.BeforeLoad(this, options);
			});
			if (sceneFile.Id != Guid.Empty && sceneFile.Id != Id)
			{
				ForceChangeId(sceneFile.Id);
				Directory.Add(this);
			}
			if (!options.IsAdditive)
			{
				Source = sceneFile;
			}
			using (ActionGraph.PushSerializationOptions(sceneFile.SerializationOptions with
			{
				ForceUpdateCached = IsEditor
			}))
			{
				using (Push())
				{
					using (sceneFile.LoadBlobData())
					{
						using (CallbackBatch.Batch("Load"))
						{
							if (sceneFile.GameObjects != null)
							{
								JsonObject[] gameObjects = sceneFile.GameObjects;
								foreach (JsonObject node in gameObjects)
								{
									CreateObject(enabled: false).Deserialize(node);
								}
							}
							if (sceneFile.SceneProperties != null)
							{
								DeserializeProperties(sceneFile.SceneProperties, options.IsSystemScene);
							}
							List<LoadingContext> sceneLoadingTasks = new List<LoadingContext>();
							RunEvent((ISceneLoadingEvents x) =>
							{
								LoadingContext loadingContext = new LoadingContext();
								loadingContext.Task = x.OnLoad(this, options, loadingContext);
								sceneLoadingTasks.Add(loadingContext);
							});
							foreach (LoadingContext item2 in sceneLoadingTasks)
							{
								AddLoadingTask(item2);
							}
							if (!IsEditor)
							{
								NetworkSpawnRecursive(null);
							}
						}
					}
				}
			}
			if (!IsEditor && !options.IsAdditive)
			{
				AddSystemScene();
			}
			if (!options.IsSystemScene)
			{
				Signal(GameObjectSystem.Stage.SceneLoaded);
			}
			return true;
		}
	}

	/// <summary>
	/// Load from the provided file name. This will not load the scene for other clients in a
	/// multiplayer session, you should instead use <see cref="M:Sandbox.Game.ChangeScene(Sandbox.SceneLoadOptions)" />
	/// if you want to bring other clients.
	/// </summary>
	[Description("Load from the provided file name. This will not load the scene for other clients in a multiplayer session, you should instead use <span style=\"color: #4EC9B0;\">Game</span>.<span style=\"color: #DCDCAA;\">ChangeScene</span>(<span style=\"color: #4EC9B0;\">SceneLoadOptions</span>) if you want to bring other clients.")]
	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 178)]
	public bool LoadFromFile(string filename)
	{
		SceneLoadOptions sceneLoadOptions = new SceneLoadOptions();
		if (!sceneLoadOptions.SetScene(filename))
		{
			return false;
		}
		return Load(sceneLoadOptions);
	}

	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 188)]
	public override JsonObject Serialize(SerializeOptions options = null)
	{
		if (this is PrefabScene)
		{
			return base.Serialize(options);
		}
		JsonObject jsonObject = new JsonObject
		{
			{ "Type", "Scene" },
			{
				"Properties",
				SerializeProperties()
			}
		};
		JsonArray jsonArray = new JsonArray();
		using (Push())
		{
			foreach (GameObject child in Children)
			{
				JsonObject jsonObject2 = child.Serialize(options);
				if (jsonObject2 != null)
				{
					jsonArray.Add(jsonObject2);
				}
			}
			jsonObject.Add("GameObjects", jsonArray);
			return jsonObject;
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 218)]
	internal void Reload()
	{
		JsonObject node = Serialize();
		_physicsWorld?.Delete();
		_physicsWorld = null;
		ReloadSystems();
		Deserialize(node);
	}

	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 229)]
	public override void Deserialize(JsonObject node, DeserializeOptions option)
	{
		if (this is PrefabScene)
		{
			base.Deserialize(node, option);
			return;
		}
		ProcessDeletes();
		Clear();
		if (node.TryGetPropertyValue("Properties", out JsonNode jsonNode))
		{
			DeserializeProperties(jsonNode.AsObject());
		}
		using (Push())
		{
			using (CallbackBatch.Batch("Deserialize"))
			{
				if (!(node["GameObjects"] is JsonArray jsonArray))
				{
					return;
				}
				using IEnumerator<JsonNode> enumerator = jsonArray.GetEnumerator();
				while (enumerator.MoveNext() && enumerator.Current is JsonObject node2)
				{
					GameObject gameObject = new GameObject(enabled: false);
					gameObject.Parent = this;
					gameObject.Deserialize(node2, option);
				}
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 263)]
	public JsonObject SerializeProperties()
	{
		JsonObject jsonObject = new JsonObject();
		foreach (PropertyDescription item in from x in Game.TypeLibrary.GetType<Scene>().Properties
			where x.HasAttribute<PropertyAttribute>()
			orderby x.Name
			select x)
		{
			if (!(item.Name == "Enabled") && !(item.Name == "Name") && !(item.Name == "Lerp"))
			{
				jsonObject.Add(item.Name, JsonValue.Create(item.GetValue(this)));
			}
		}
		jsonObject.Add("Metadata", SerializeMetadata());
		jsonObject.Add("NavMesh", NavMesh.Serialize());
		if (!(this is PrefabScene))
		{
			JsonNode jsonNode = SerializeGameObjectSystems();
			if (jsonNode != null)
			{
				jsonObject.Add("GameObjectSystems", jsonNode);
			}
		}
		return jsonObject;
	}

	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 294)]
	private JsonNode SerializeGameObjectSystems()
	{
		SortedDictionary<string, SortedDictionary<string, object>> sortedDictionary = new SortedDictionary<string, SortedDictionary<string, object>>(StringComparer.Ordinal);
		foreach (GameObjectSystem system in GetSystems())
		{
			TypeDescription type = Game.TypeLibrary.GetType(system.GetType());
			if (type == null)
			{
				continue;
			}
			string fullName = type.FullName;
			SortedDictionary<string, object> sortedDictionary2 = null;
			foreach (PropertyDescription item in type.Properties.Where((PropertyDescription x) => x.HasAttribute<PropertyAttribute>()))
			{
				if (!item.CanWrite)
				{
					continue;
				}
				object value = (TryGetPreTransientValue(system, item, out var value2) ? value2 : item.GetValue(system));
				object value3 = (ProjectSettings.Systems.TryGetPropertyValue(type, item, out var value4) ? value4 : SystemsConfig.GetDefaultValue(item));
				JsonNode? node = JsonSerializer.SerializeToNode(value, Json.options);
				JsonNode node2 = JsonSerializer.SerializeToNode(value3, Json.options);
				if (!JsonNode.DeepEquals(node, node2))
				{
					if (sortedDictionary2 == null)
					{
						sortedDictionary2 = new SortedDictionary<string, object>(StringComparer.Ordinal);
					}
					sortedDictionary2[item.Name] = value;
				}
			}
			if (sortedDictionary2 != null)
			{
				sortedDictionary[fullName] = sortedDictionary2;
			}
		}
		if (!sortedDictionary.Any())
		{
			return null;
		}
		return JsonSerializer.SerializeToNode(sortedDictionary, Json.options);
	}

	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 337)]
	private JsonObject SerializeMetadata()
	{
		JsonObject jsonObject = new JsonObject();
		foreach (ISceneMetadata allComponent in GetAllComponents<ISceneMetadata>())
		{
			Dictionary<string, string> metadata = allComponent.GetMetadata();
			if (metadata == null)
			{
				continue;
			}
			foreach (KeyValuePair<string, string> item in metadata)
			{
				jsonObject[item.Key] = item.Value;
			}
		}
		return jsonObject;
	}

	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 353)]
	private void DeserializeProperties(JsonObject data, bool isSystemScene = false)
	{
		TypeDescription type = Game.TypeLibrary.GetType<Scene>();
		Assert.NotNull(type, "Scene type is inaccessible!");
		foreach (PropertyDescription item in type.Properties.Where((PropertyDescription x) => x.HasAttribute<PropertyAttribute>()))
		{
			if (!(item.Name == "Enabled") && !(item.Name == "Name") && !(item.Name == "Lerp") && data.TryGetPropertyValue(item.Name, out JsonNode jsonNode))
			{
				try
				{
					item.SetValue(this, Json.FromNode(jsonNode, item.PropertyType));
				}
				catch (Exception ex)
				{
					GlobalSystemNamespace.Log.Warning(ex, $"Error when deserializing {this}.{item.Name} ({ex.Message})");
				}
			}
		}
		if (!isSystemScene && data.TryGetPropertyValue("GameObjectSystems", out JsonNode jsonNode2))
		{
			ApplyGameObjectSystemOverrides(jsonNode2);
		}
		if (!isSystemScene)
		{
			NavMesh.Deserialize(data["NavMesh"] as JsonObject);
		}
	}

	/// <summary>
	/// Create a new SceneFile from this scene
	/// </summary>
	[Description("Create a new SceneFile from this scene")]
	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 399)]
	internal SceneFile CreateSceneFile()
	{
		SceneFile sceneFile = new SceneFile();
		ToSceneFile(sceneFile);
		return sceneFile;
	}

	/// <summary>
	/// Save the contents of this scene to the SceneFile
	/// </summary>
	[Description("Save the contents of this scene to the SceneFile")]
	[SourceLocation("Scene\\Scene\\Scene.LoadSave.cs", 409)]
	internal void ToSceneFile(SceneFile target)
	{
		Assert.IsValid(this);
		target.ActionGraphCache.Clear();
		using (Push())
		{
			using (target.PushSerializationScope())
			{
				using BlobDataSerializer.BlobContext blobContext = BlobDataSerializer.Capture();
				target.Id = Id;
				target.GameObjects = (from x in Children
					select x.Serialize() into x
					where x != null
					select x).ToArray();
				target.SceneProperties = SerializeProperties();
				target.BinaryData = blobContext.ToByteArray();
			}
		}
	}

	/// <summary>
	/// In editor this gets called every frame
	/// In game this gets called every fixed update
	/// </summary>
	[Description("In editor this gets called every frame In game this gets called every fixed update")]
	[SourceLocation("Scene\\Scene\\Scene.NavMesh.cs", 13)]
	private void Nav_Update()
	{
		if (!NavMesh.IsEnabled || this is PrefabScene)
		{
			return;
		}
		if (!NavMesh.IsLoaded && IsEditor)
		{
			if (_navMeshLoadTask != null && !_navMeshLoadTask.IsCompleted)
			{
				return;
			}
			_navMeshLoadTask = NavMesh.Load(PhysicsWorld);
			_navMeshLoadTask.ContinueWith((Task t) =>
			{
				_navMeshLoadTask = null;
				if (t.Exception != null)
				{
					GlobalSystemNamespace.Log.Warning($"NavMesh load failed: {t.Exception.InnerException?.Message ?? t.Exception.Message}");
				}
			});
		}
		else if (!NavMesh.IsGenerating)
		{
			if (NavMesh.IsDirty || (NavMesh.DrawMesh && NavMesh.EditorAutoUpdate && IsEditor))
			{
				NavMesh.InvalidateAllTiles(PhysicsWorld);
			}
			NavMesh.UpdateCache(PhysicsWorld);
			NavMesh.Simulation.Update(Time.Delta);
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 17)]
	internal void RegisterNetworkedObject(NetworkObject obj)
	{
		networkedObjects.Add(obj);
	}

	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 22)]
	internal void UnregisterNetworkObject(NetworkObject obj)
	{
		SceneNetworkSystem.Instance?.DeltaSnapshots?.ClearNetworkObject(obj);
		networkedObjects.Remove(obj);
	}

	/// <summary>
	/// Send any pending network updates at our desired <see cref="P:Sandbox.Scene.NetworkRate" />.
	/// </summary>
	[Description("Send any pending network updates at our desired <span style=\"color: #4EC9B0;\">Scene</span>.<span style=\"color: #DCDCDC;\">NetworkRate</span>.")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 36)]
	internal void SceneNetworkUpdate()
	{
		_networkMapInstanceCache.Clear();
		GetAll(_networkMapInstanceCache);
		SceneNetworkSystem instance = SceneNetworkSystem.Instance;
		if (instance == null || _timeSinceNetworkUpdate < NetworkRate)
		{
			return;
		}
		_timeSinceNetworkUpdate = 0f;
		SendClientTick(instance);
		instance.DeltaSnapshots.UpdateTime();
		IEnumerable<Connection> filteredConnections = instance.GetFilteredConnections(Connection.ChannelState.Connected);
		Connection[] connections = (filteredConnections as Connection[]) ?? filteredConnections.ToArray();
		_dirtySnapshotObjects.Clear();
		_cleanSnapshotObjects.Clear();
		foreach (NetworkObject networkedObject in networkedObjects)
		{
			if (networkedObject.LocalSnapshotState.UpdatedConnections.Count == 0)
			{
				_dirtySnapshotObjects.Add(networkedObject);
			}
			else
			{
				_cleanSnapshotObjects.Add(networkedObject);
			}
		}
		IEnumerable<IDeltaSnapshot> enumerable = _dirtySnapshotObjects.Concat(_cleanSnapshotObjects);
		if (Networking.IsHost)
		{
			enumerable = enumerable.Concat(systems.Values);
		}
		instance.DeltaSnapshots.Send(enumerable, connections);
		instance.DeltaSnapshots.Tick();
	}

	/// <summary>
	/// Create messages for what <paramref name="source" /> should see; null source means everything.
	/// </summary>
	[Description("Create messages for what <span style=\"color: #9CDCFE;\">source</span> should see; null source means everything.")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 84)]
	internal void SerializeNetworkObjects(Connection source, List<object> collection, bool includeLocalObjects = false, SnapshotCapture capture = null)
	{
		HashSet<NetworkObject> included = new HashSet<NetworkObject>();
		foreach (NetworkObject networkedObject in networkedObjects)
		{
			GameObject gameObject = networkedObject.GameObject;
			if (gameObject != null && !gameObject.IsDestroyed)
			{
				NetworkObject rootNetworkObject = networkedObject.RootNetworkObject;
				if (source == null || networkedObject.ShouldIncludeInSnapshot(source) || (rootNetworkObject != networkedObject && rootNetworkObject != null && rootNetworkObject.ShouldIncludeInSnapshot(source)))
				{
					AddWithAncestors(source, networkedObject, included, collection, includeLocalObjects, capture);
				}
			}
		}
	}

	/// <summary>
	/// Emit the create message for <paramref name="target" /> and every networked ancestor above it,
	/// each at most once. A networked child must never be sent without its parent chain.
	/// </summary>
	[Description("Emit the create message for <span style=\"color: #9CDCFE;\">target</span> and every networked ancestor above it, each at most once. A networked child must never be sent without its parent chain.")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 107)]
	internal void AddWithAncestors(Connection source, NetworkObject target, HashSet<NetworkObject> included, List<object> collection, bool includeLocalObjects, SnapshotCapture capture = null)
	{
		NetworkObject networkObject = target;
		while (networkObject != null)
		{
			GameObject gameObject = networkObject.GameObject;
			if (gameObject != null && !gameObject.IsDestroyed && included.Add(networkObject))
			{
				collection.Add(networkObject.GetCreateMessage(includeLocalObjects, capture));
				if (source != null)
				{
					networkObject.MarkCreateMessageSent(source);
				}
				networkObject = networkObject.GameObject.Parent?._net;
				continue;
			}
			break;
		}
	}

	/// <summary>
	/// Do appropriate actions based on the <see cref="T:Sandbox.NetworkOrphaned" /> mode for all networked objects owned by a specific connection.
	/// </summary>
	[Description("Do appropriate actions based on the <span style=\"color: #86C691;\">NetworkOrphaned</span> mode for all networked objects owned by a specific connection.")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 130)]
	internal void DoOrphanedActions(Connection connection)
	{
		NetworkObject[] array = networkedObjects.Where((NetworkObject n) => n.Owner == connection.Id).ToArray();
		for (int num = 0; num < array.Length; num++)
		{
			array[num].DoOrphanedAction();
		}
	}

	/// <summary>
	/// Send all of our visibility origins to other clients. These are points we can observe from, which helps
	/// to determine the visibility of network objects and sends a user command.
	/// </summary>
	[Description("Send all of our visibility origins to other clients. These are points we can observe from, which helps to determine the visibility of network objects and sends a user command.")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 144)]
	internal void SendClientTick(SceneNetworkSystem system)
	{
		Connection local = Connection.Local;
		if (local.VisibilityOrigins.Length == 0)
		{
			local.VisibilityOrigins = new Vector3[1];
		}
		local.VisibilityOrigins[0] = Camera?.WorldPosition ?? default(Vector3);
		UserCommand cmd = UserCommand.Create();
		local.BuildUserCommand(ref cmd);
		foreach (Connection filteredConnection in system.GetFilteredConnections())
		{
			ByteStream bs = ByteStream.Create(256);
			bs.Write(InternalMessageType.ClientTick);
			bs.Write((char)local.VisibilityOrigins.Length);
			for (int i = 0; i < local.VisibilityOrigins.Length; i++)
			{
				Vector3 vector = local.VisibilityOrigins[i];
				bs.Write(vector.x);
				bs.Write(vector.y);
				bs.Write(vector.z);
			}
			if (filteredConnection.IsHost)
			{
				cmd.Serialize(ref bs);
			}
			filteredConnection.SendStream(bs, NetFlags.UnreliableNoDelay);
			bs.Dispose();
		}
	}

	/// <summary>
	/// Are these bounds visible to the specified <see cref="T:Sandbox.Connection" />?
	/// </summary>
	[Description("Are these bounds visible to the specified <span style=\"color: #4EC9B0;\">Connection</span>?")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 196)]
	public unsafe bool IsBBoxVisibleToConnection(Connection target, BBox box)
	{
		Vector3[] visibilityOrigins = target.VisibilityOrigins;
		foreach (IPVS item in _networkMapInstanceCache.Select((MapInstance x) => x.GetNetworkPvs()))
		{
			if (!item.IsValid || item.IsEmptyPVS())
			{
				continue;
			}
			fixed (Vector3* sources = visibilityOrigins)
			{
				if (!item.IsAbsBoxInPVS(visibilityOrigins.Length, (nint)sources, box.Mins, box.Maxs))
				{
					return false;
				}
			}
		}
		return true;
	}

	/// <summary>
	/// Is a position visible to the specified <see cref="T:Sandbox.Connection" />?
	/// </summary>
	[Description("Is a position visible to the specified <span style=\"color: #4EC9B0;\">Connection</span>?")]
	[SourceLocation("Scene\\Scene\\Scene.Network.cs", 218)]
	public unsafe bool IsPointVisibleToConnection(Connection target, Vector3 position)
	{
		Vector3[] visibilityOrigins = target.VisibilityOrigins;
		foreach (IPVS item in _networkMapInstanceCache.Select((MapInstance x) => x.GetNetworkPvs()))
		{
			if (!item.IsValid || item.IsEmptyPVS())
			{
				continue;
			}
			fixed (Vector3* sources = visibilityOrigins)
			{
				if (!item.IsInPVS(visibilityOrigins.Length, (nint)sources, position))
				{
					return false;
				}
			}
		}
		return true;
	}

	/// <summary>
	/// Should only be called when destroying the scene. This here just to avoid unregistering
	/// all of the objects when we don't need to, because we're just quitting.
	/// </summary>
	[Description("Should only be called when destroying the scene. This here just to avoid unregistering all of the objects when we don't need to, because we're just quitting.")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 59)]
	private void ClearObjectIndex()
	{
		foreach (HashSetEx<object> value in objectIndex.Values)
		{
			value?.Clear();
		}
		objectsInIndex.Clear();
		objectIndex.Clear();
		updateComponents.Clear();
		fixedUpdateComponents.Clear();
		preRenderComponents.Clear();
	}

	/// <summary>
	/// When hotload occurs, the interfaces etc could have changed. So first of all we want to
	/// go through and remove any null entries, then we want to go through and re-add everything.
	/// </summary>
	[Description("When hotload occurs, the interfaces etc could have changed. So first of all we want to go through and remove any null entries, then we want to go through and re-add everything.")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 77)]
	private void HotloadObjectIndex()
	{
		FastTimer fastTimer = FastTimer.StartNew();
		List<object> list = objectsInIndex.ToList();
		objectsInIndex.Clear();
		objectIndex.Clear();
		foreach (object item in list)
		{
			if (item != null)
			{
				AddObjectToDirectory(item);
			}
		}
		if (fastTimer.ElapsedMilliSeconds > 10.0)
		{
			GlobalSystemNamespace.Log.Warning($"HotloadObjectIndex took {fastTimer.ElapsedMilliSeconds:0.0}ms");
		}
	}

	/// <summary>
	/// Adds object instance, indexed by type, to the directory so that its values are accessible by GetAll
	/// </summary>
	[Description("Adds object instance, indexed by type, to the directory so that its values are accessible by GetAll")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 108)]
	internal void AddObjectToDirectory(object obj)
	{
		if (!objectsInIndex.Add(obj))
		{
			return;
		}
		Type[] array = indexableTypesCache[obj.GetType()];
		foreach (Type key in array)
		{
			objectIndex.GetOrCreate(key).Add(obj);
		}
		if (obj is Component component)
		{
			if (component is IUpdateSubscriber || component.OnComponentUpdate != null)
			{
				updateComponents.Add(component);
			}
			if (component is IFixedUpdateSubscriber || component.OnComponentFixedUpdate != null)
			{
				fixedUpdateComponents.Add(component);
			}
			if (component is IPreRenderSubscriber)
			{
				preRenderComponents.Add(component);
			}
		}
	}

	/// <summary>
	/// Adds object instance, indexed by type, to the directory so that its values are accessible by GetAll
	/// </summary>
	[Description("Adds object instance, indexed by type, to the directory so that its values are accessible by GetAll")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 129)]
	internal void RemoveObjectFromDirectory(object obj)
	{
		if (!objectsInIndex.Remove(obj))
		{
			return;
		}
		Type[] array = indexableTypesCache[obj.GetType()];
		foreach (Type key in array)
		{
			objectIndex.GetOrCreate(key).Remove(obj);
		}
		if (obj is Component component)
		{
			if (component is IUpdateSubscriber || component.OnComponentUpdate != null)
			{
				updateComponents.Remove(component);
			}
			if (component is IFixedUpdateSubscriber || component.OnComponentFixedUpdate != null)
			{
				fixedUpdateComponents.Remove(component);
			}
			if (component is IPreRenderSubscriber)
			{
				preRenderComponents.Remove(component);
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 148)]
	internal HashSetEx<object> GetIndexSet(Type type)
	{
		if (!objectIndex.TryGetValue(type, out var value) || value.Count <= 0)
		{
			return null;
		}
		return value;
	}

	/// <summary>
	/// Get all objects of this type. This could be a component or a GameObjectSystem, or other stuff in the future.
	/// </summary>
	/// <remarks>
	/// Allocates once per call. Engine code should prefer <see cref="M:Sandbox.Scene.Query``1" /> for direct iteration.
	/// </remarks>
	[Pure]
	[Description("Get all objects of this type. This could be a component or a GameObjectSystem, or other stuff in the future.")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 157)]
	public IEnumerable<T> GetAll<T>()
	{
		return Query<T>();
	}

	/// <summary>
	/// Gets all objects of this type as a struct enumerable. Direct <c>foreach</c> iteration is allocation-free.
	/// </summary>
	[Pure]
	[Description("Gets all objects of this type as a struct enumerable. Direct <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">foreach</code> iteration is allocation-free.")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 163)]
	internal SceneObjectQuery<T> Query<T>()
	{
		return new SceneObjectQuery<T>(this);
	}

	/// <summary>
	/// Get all objects of this type. This could be a component or a GameObjectSystem, or other stuff in the future.
	/// </summary>
	[Pure]
	[Description("Get all objects of this type. This could be a component or a GameObjectSystem, or other stuff in the future.")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 169)]
	public void GetAll<T>(List<T> target)
	{
		if (!objectIndex.TryGetValue(typeof(T), out var value) || value.Count == 0)
		{
			return;
		}
		foreach (T item in value.EnumerateLocked())
		{
			if (item != null && !(item is IValid { IsValid: false }))
			{
				target.Add(item);
			}
		}
	}

	/// <summary>
	/// Gets the first object found of this type. This could be a component or a GameObjectSystem, or other stuff in the future.
	/// </summary>
	/// <typeparam name="T"></typeparam>
	/// <returns></returns>
	[Pure]
	[Description("Gets the first object found of this type. This could be a component or a GameObjectSystem, or other stuff in the future.")]
	[SourceLocation("Scene\\Scene\\Scene.ObjectIndex.cs", 190)]
	public T Get<T>()
	{
		if (!objectIndex.TryGetValue(typeof(T), out var value) || value.Count == 0)
		{
			return default;
		}
		foreach (T item in value.EnumerateLocked())
		{
			if (item != null && !(item is IValid { IsValid: false }))
			{
				return item;
			}
		}
		return default;
	}

	/// <summary>
	/// Call dispose on all installed hooks
	/// </summary>
	[Description("Call dispose on all installed hooks")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 13)]
	private void ShutdownSystems()
	{
		foreach (GameObjectSystem value in systems.Values)
		{
			if (value != null)
			{
				try
				{
					RemoveObjectFromDirectory(value);
					value.Dispose();
				}
				catch (Exception exception)
				{
					GlobalSystemNamespace.Log.Warning(exception, $"Exception when disposing GameObjectSystem '{value.GetType()}'");
				}
			}
		}
		systems.Clear();
	}

	/// <summary>
	/// Find all types of SceneHook, create an instance of each one and install it.
	/// </summary>
	[Description("Find all types of SceneHook, create an instance of each one and install it.")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 37)]
	private void InitSystems()
	{
		using (Push())
		{
			ShutdownSystems();
			TypeDescription[] array = (from x in Game.TypeLibrary.GetTypes<GameObjectSystem>()
				where !x.IsAbstract
				select x).ToArray();
			for (int num = 0; num < array.Length; num++)
			{
				GameObjectSystem gameObjectSystem = array[num].Create<GameObjectSystem>(new object[1] { this });
				if (gameObjectSystem != null)
				{
					ApplyGameObjectSystemConfig(gameObjectSystem);
					systems[gameObjectSystem.GetType()] = gameObjectSystem;
					AddObjectToDirectory(gameObjectSystem);
				}
			}
		}
	}

	/// <summary>
	/// Dispose and recreate all existing systems without rediscovering types.
	/// </summary>
	[Description("Dispose and recreate all existing systems without rediscovering types.")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 63)]
	internal void ReloadSystems()
	{
		if (systems.Count == 0)
		{
			return;
		}
		using (Push())
		{
			Type[] array = systems.Keys.ToArray();
			ShutdownSystems();
			Type[] array2 = array;
			foreach (Type type in array2)
			{
				GameObjectSystem gameObjectSystem = Game.TypeLibrary.GetType(type)?.Create<GameObjectSystem>(new object[1] { this });
				if (gameObjectSystem != null)
				{
					ApplyGameObjectSystemConfig(gameObjectSystem);
					systems[gameObjectSystem.GetType()] = gameObjectSystem;
					AddObjectToDirectory(gameObjectSystem);
				}
			}
		}
	}

	/// <summary>
	/// Apply configuration values to a GameObjectSystem with priority:
	/// 1. Project-wide value (from <see cref="P:Sandbox.ProjectSettings.Systems" />)
	/// 2. Default value (already set by property initializer)
	/// Scene-specific overrides are applied during deserialization via <see cref="M:Sandbox.Scene.ApplyGameObjectSystemOverrides(System.Text.Json.Nodes.JsonNode)" />
	/// </summary>
	[Description("Apply configuration values to a GameObjectSystem with priority: 1. Project-wide value (from <span style=\"color: #4EC9B0;\">ProjectSettings</span>.<span style=\"color: #DCDCDC;\">Systems</span>) 2. Default value (already set by property initializer) Scene-specific overrides are applied during deserialization via <span style=\"color: #4EC9B0;\">Scene</span>.<span style=\"color: #DCDCAA;\">ApplyGameObjectSystemOverrides</span>(<span style=\"color: #4EC9B0;\">JsonNode</span>)")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 92)]
	private void ApplyGameObjectSystemConfig(GameObjectSystem system)
	{
		TypeDescription type = Game.TypeLibrary.GetType(system.GetType());
		if (type == null)
		{
			return;
		}
		using (Push())
		{
			foreach (PropertyDescription item in type.Properties.Where((PropertyDescription x) => x.HasAttribute<PropertyAttribute>()))
			{
				if (item.CanWrite && ProjectSettings.Systems.TryGetPropertyValue(type, item, out var value))
				{
					try
					{
						item.SetValue(system, value);
					}
					catch (Exception ex)
					{
						GlobalSystemNamespace.Log.Warning($"Failed to apply config value to {type.FullName}.{item.Name}: {ex.Message}");
					}
				}
			}
		}
	}

	/// <summary>
	/// Signal a hook stage
	/// </summary>
	[Description("Signal a hook stage")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 122)]
	internal void Signal(in GameObjectSystem.Stage stage)
	{
		GetCallbacks(in stage).Run();
	}

	/// <summary>
	/// Get the hook container for this stage
	/// </summary>
	[Description("Get the hook container for this stage")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 132)]
	private TimedCallbackList GetCallbacks(in GameObjectSystem.Stage stage)
	{
		if (listeners.TryGetValue(stage, out var value))
		{
			return value;
		}
		value = new TimedCallbackList();
		listeners[stage] = value;
		return value;
	}

	/// <summary>
	/// Reset the listener metrics to 0, like before a benchmark or something
	/// </summary>
	[Description("Reset the listener metrics to 0, like before a benchmark or something")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 145)]
	internal void ResetListenerMetrics()
	{
		foreach (TimedCallbackList value in listeners.Values)
		{
			value.ClearMetrics();
		}
	}

	/// <summary>
	/// Get a JSON serializable list of metrics from the scene's listeners.
	/// (this is just internal object[] right now because I can't be fucked to exose it properly)
	/// </summary>
	[Description("Get a JSON serializable list of metrics from the scene's listeners. (this is just internal object[] right now because I can't be fucked to exose it properly)")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 157)]
	internal object[] GetListenerMetrics()
	{
		return listeners.Values.SelectMany((TimedCallbackList x) => x.GetMetrics()).ToArray();
	}

	/// <summary>
	/// Call this method on this stage. This returns a disposable that will remove the hook when disposed.
	/// </summary>
	[Description("Call this method on this stage. This returns a disposable that will remove the hook when disposed.")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 165)]
	public IDisposable AddHook(GameObjectSystem.Stage stage, int order, Action action, string className, string description)
	{
		return GetCallbacks(in stage).Add(order, action, className, description);
	}

	/// <summary>
	/// Get a specific system by type.
	/// </summary>
	[Description("Get a specific system by type.")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 173)]
	public T GetSystem<T>() where T : GameObjectSystem
	{
		if (!systems.TryGetValue(typeof(T), out var value))
		{
			return null;
		}
		return value as T;
	}

	/// <summary>
	/// Get a specific system by type.
	/// </summary>
	[Description("Get a specific system by type.")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 181)]
	public void GetSystem<T>(out T val) where T : GameObjectSystem
	{
		val = (systems.TryGetValue(typeof(T), out var value) ? (value as T) : null);
	}

	/// <summary>
	/// Get a specific system by <see cref="T:Sandbox.TypeDescription" />.
	/// </summary>
	[Description("Get a specific system by TypeDescription.")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 189)]
	internal GameObjectSystem GetSystemByType(TypeDescription type)
	{
		if (!systems.TryGetValue(type.TargetType, out var value))
		{
			return null;
		}
		return value;
	}

	/// <summary>
	/// Get all systems belonging to this scene.
	/// </summary>
	[Description("Get all systems belonging to this scene.")]
	[SourceLocation("Scene\\Scene\\Scene.System.cs", 197)]
	internal Dictionary<Type, GameObjectSystem>.ValueCollection GetSystems()
	{
		return systems.Values;
	}

	/// <summary>
	/// Applies GameObjectSystem property overrides from the given node.
	/// </summary>
	[Description("Applies GameObjectSystem property overrides from the given node.")]
	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 13)]
	internal void ApplyGameObjectSystemOverrides(JsonNode overridesNode)
	{
		ApplyGameObjectSystemOverrides(overridesNode, null);
	}

	/// <summary>
	/// Applies GameObjectSystem property overrides and returns a scope that reverts them.
	/// </summary>
	[Description("Applies GameObjectSystem property overrides and returns a scope that reverts them.")]
	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 21)]
	internal IDisposable ApplyTransientGameObjectSystemOverrides(JsonNode overridesNode)
	{
		SystemOverrideScope systemOverrideScope = new SystemOverrideScope(this);
		try
		{
			ApplyGameObjectSystemOverrides(overridesNode, systemOverrideScope);
			if (!systemOverrideScope.HasOverrides)
			{
				return null;
			}
			_transientSystemOverrides.Add(systemOverrideScope);
			SystemOverrideScope result = systemOverrideScope;
			systemOverrideScope = null;
			return result;
		}
		finally
		{
			systemOverrideScope?.Dispose();
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 43)]
	private void ApplyGameObjectSystemOverrides(JsonNode overridesNode, SystemOverrideScope scope)
	{
		if (overridesNode == null)
		{
			return;
		}
		Dictionary<string, JsonObject> dictionary;
		try
		{
			dictionary = Json.FromNode<Dictionary<string, JsonObject>>(overridesNode);
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Warning(ex, $"Error when deserializing GameObjectSystem overrides ({ex.Message})");
			return;
		}
		if (dictionary == null || dictionary.Count == 0)
		{
			return;
		}
		foreach (GameObjectSystem value3 in systems.Values)
		{
			TypeDescription type = Game.TypeLibrary.GetType(value3.GetType());
			if (type == null || !dictionary.TryGetValue(type.FullName, out var value))
			{
				continue;
			}
			foreach (PropertyDescription item in type.Properties.Where((PropertyDescription x) => x.HasAttribute<PropertyAttribute>()))
			{
				if (item.CanWrite && value.TryGetPropertyValue(item.Name, out JsonNode jsonNode) && (scope == null || item.CanRead))
				{
					try
					{
						object value2 = Json.FromNode(jsonNode, item.PropertyType);
						object previousValue = ((scope != null) ? item.GetValue(value3) : null);
						item.SetValue(value3, value2);
						scope?.AddOverride(value3, item, previousValue, value2);
					}
					catch (Exception ex2)
					{
						GlobalSystemNamespace.Log.Warning($"Failed to apply scene override to {type.FullName}.{item.Name}: {ex2.Message}");
					}
				}
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 99)]
	private bool TryGetPreTransientValue(GameObjectSystem system, PropertyDescription property, out object value)
	{
		return _preTransientSystemValues.TryGetValue((system, property), out value);
	}

	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 104)]
	private void RestoreTransientValue(GameObjectSystem system, PropertyDescription property)
	{
		for (int num = _transientSystemOverrides.Count - 1; num >= 0; num--)
		{
			if (_transientSystemOverrides[num].TryGetOverride(system, property, out var value))
			{
				SetSystemPropertyValue(system, property, value);
				return;
			}
		}
		(GameObjectSystem, PropertyDescription) key = (system, property);
		if (_preTransientSystemValues.TryGetValue(key, out var value2) && SetSystemPropertyValue(system, property, value2))
		{
			_preTransientSystemValues.Remove(key);
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.System.Overrides.cs", 125)]
	private static bool SetSystemPropertyValue(GameObjectSystem system, PropertyDescription property, object value)
	{
		try
		{
			property.SetValue(system, value);
			return true;
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Warning($"Failed to revert system override on {system.GetType().FullName}.{property.Name}: {ex.Message}");
			return false;
		}
	}

	/// <summary>
	/// The update loop will turn certain settings on
	/// Here we turn them to their defaults.
	/// </summary>
	[Description("The update loop will turn certain settings on Here we turn them to their defaults.")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 25)]
	private void PreTickReset()
	{
		if (_physicsWorld.IsValid())
		{
			_physicsWorld.SubSteps = ProjectSettings.Physics.SubSteps;
		}
		if (_sceneWorld != null)
		{
			_sceneWorld.GradientFog.Enabled = false;
		}
	}

	/// <summary>
	/// Update the current time from the host
	/// </summary>
	[Description("Update the current time from the host")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 45)]
	internal void UpdateTimeFromHost(double time)
	{
		estimatedServerTime = time;
		if (TimeNow == 0.0)
		{
			TimeNow = time;
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 58)]
	public void EditorTick(float timeNow, float timeDelta)
	{
		if (!IsEditor || !IsValid || IsSuspended)
		{
			return;
		}
		TimeNow = timeNow;
		TimeDelta = timeDelta;
		using (Time.Scope(TimeNow, TimeDelta))
		{
			using (gizmoInstance.Push())
			{
				SharedTick();
				using (PerformanceStats.Timings.NavMesh.Scope())
				{
					Nav_Update();
				}
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 79)]
	public void EditorDraw()
	{
		DebugDraw();
		DrawGizmos();
	}

	/// <summary>
	/// Run OnStart on all components that haven't had OnStart called yet
	/// </summary>
	[Description("Run OnStart on all components that haven't had OnStart called yet")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 88)]
	internal void RunPendingStarts()
	{
		foreach (Component item in pendingStartComponents.EnumerateLocked())
		{
			if (item.IsValid())
			{
				item.InternalOnStart();
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 99)]
	internal void InternalUpdate()
	{
		RunPendingStarts();
		Signal(GameObjectSystem.Stage.Interpolation);
		foreach (Component item in updateComponents.EnumerateLocked(nullChecks: true))
		{
			item.InternalUpdate();
		}
	}

	/// <summary>
	/// Composes every enabled camera's view - the one point in the frame where the camera moves.
	/// Runs after Update and bone merging, before PreRender.
	/// </summary>
	[Description("Composes every enabled camera's view - the one point in the frame where the camera moves. Runs after Update and bone merging, before PreRender.")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 114)]
	private void UpdateCameraViews()
	{
		_cameraViewScratch.Clear();
		_cameraViewScratch.AddRange(Cameras);
		ICameraModifier[] modifiers = (IsEditor ? null : CameraComponent.GatherModifiers(this));
		foreach (CameraComponent item in _cameraViewScratch)
		{
			if (item.IsValid() && item.Active)
			{
				item.ComposeView(modifiers);
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 140)]
	internal void PreRender()
	{
		renderThreadEventTargets.Clear();
		GetAll(renderThreadEventTargets);
		renderScreenPanels.Clear();
		GetAll(renderScreenPanels);
		SortScreenPanels(renderScreenPanels);
		foreach (Component item in preRenderComponents.EnumerateLocked())
		{
			item.OnPreRenderInternal();
		}
	}

	/// <summary>
	/// Sort by ZIndex, keeping scene order for equal ZIndex so overlapping panels draw
	/// in a predictable order. List.Sort isn't stable; a stable insertion sort is fine
	/// for the handful of panels a scene has and doesn't allocate.
	/// </summary>
	[Description("Sort by ZIndex, keeping scene order for equal ZIndex so overlapping panels draw in a predictable order. List.Sort isn't stable; a stable insertion sort is fine for the handful of panels a scene has and doesn't allocate.")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 159)]
	private static void SortScreenPanels(List<ScreenPanel> panels)
	{
		for (int i = 1; i < panels.Count; i++)
		{
			ScreenPanel screenPanel = panels[i];
			int num = i - 1;
			while (num >= 0 && panels[num].ZIndex > screenPanel.ZIndex)
			{
				panels[num + 1] = panels[num];
				num--;
			}
			panels[num + 1] = screenPanel;
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 182)]
	private void FixedUpdate()
	{
		if (!ProjectSettings.Physics.UseFixedUpdate)
		{
			InternalFixedUpdate();
			return;
		}
		fixedUpdate.Frequency = ProjectSettings.Physics.FixedUpdateFrequency;
		IsFixedUpdate = true;
		fixedUpdate.Run(InternalFixedUpdate, Time.NowDouble, ProjectSettings.Physics.MaxFixedUpdates);
		IsFixedUpdate = false;
	}

	/// <summary>
	/// This is called in EditorTick and GameTick. It's only called in EditorTick if we're actually
	/// an editor scene.
	/// </summary>
	[Description("This is called in EditorTick and GameTick. It's only called in EditorTick if we're actually an editor scene.")]
	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 202)]
	private void SharedTick()
	{
		Scene.RunEvent((Component.ISceneStage x) =>
		{
			x.Start();
		});
		if (!IsEditor)
		{
			using (PerformanceStats.Timings.Network.Scope())
			{
				SceneNetworkUpdate();
			}
		}
		FixedUpdate();
		ProcessDeletes();
		using (_signalStarthUpdate.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.Tick.cs", 222, "SharedTick"))
		{
			Signal(GameObjectSystem.Stage.StartUpdate);
		}
		using (_updateTimer.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.Tick.cs", 227, "SharedTick"))
		{
			using (PerformanceStats.Timings.Update.Scope())
			{
				PreTickReset();
				InternalUpdate();
			}
		}
		using (_signalUpdateBones.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.Tick.cs", 234, "SharedTick"))
		{
			Signal(GameObjectSystem.Stage.UpdateBones);
		}
		UpdateCameraViews();
		if (!Application.IsHeadless)
		{
			using (_preRenderTimer.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.Tick.cs", 244, "SharedTick"))
			{
				using (PerformanceStats.Timings.Render.Scope())
				{
					PreRender();
				}
			}
		}
		ProcessDeletes();
		using (_signalFinishUpdate.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.Tick.cs", 253, "SharedTick"))
		{
			Signal(GameObjectSystem.Stage.FinishUpdate);
		}
		Scene.RunEvent((Component.ISceneStage x) =>
		{
			x.End();
		});
		if (!IsEditor)
		{
			using (PerformanceStats.Timings.Async.Scope())
			{
				SyncContext.FrameStage.PreRender.Trigger();
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 271)]
	internal void SyncServerTime()
	{
		if (!Networking.IsHost)
		{
			estimatedServerTime += TimeDelta;
			double num = Math.Abs(TimeNow - estimatedServerTime);
			if (num > 0.25)
			{
				TimeNow = estimatedServerTime;
			}
			else
			{
				TimeNow = MathX.Lerp(TimeNow, estimatedServerTime, (double)RealTime.Delta + num);
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 293)]
	internal void UpdateTime(double delta)
	{
		if (!(delta <= 0.0))
		{
			TimeDelta = delta * (double)TimeScale;
			TimeNow += TimeDelta;
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 301)]
	public void GameTick(double timeDelta = 0.1)
	{
		if (IsSuspended)
		{
			return;
		}
		UpdateTime(timeDelta);
		if (Camera != null)
		{
			gizmoInstance.Input.Camera = Camera.SceneCamera;
			UpdateDefaultListener();
		}
		using (Time.Scope(TimeNow, TimeDelta))
		{
			using (gizmoInstance?.Push())
			{
				using (PerformanceStats.Timings.Async.Scope())
				{
					SyncContext.FrameStage.Update.Trigger();
				}
				if (!IsLoading && !Game.IsPaused)
				{
					SharedTick();
					if (IsLoading)
					{
						GameTick();
					}
				}
			}
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Tick.cs", 345)]
	internal void InternalFixedUpdate()
	{
		FixedUpdateInputContext.Flip();
		using (FixedUpdateInputContext.Push())
		{
			using (_fixedUpdateTimer.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.Tick.cs", 350, "InternalFixedUpdate"))
			{
				Signal(GameObjectSystem.Stage.StartFixedUpdate);
				RunPendingStarts();
				using (PerformanceStats.Timings.Update.Scope())
				{
					foreach (Component item in fixedUpdateComponents.EnumerateLocked())
					{
						if (item.IsValid())
						{
							item.InternalFixedUpdate();
						}
					}
				}
				Signal(GameObjectSystem.Stage.PhysicsStep);
				if (!IsEditor)
				{
					using (PerformanceStats.Timings.NavMesh.Scope())
					{
						Nav_Update();
					}
				}
				using (_processDeletesTimer.Start(null, "C:\\actions-runner\\_work\\sbox\\sbox\\engine\\Sandbox.Engine\\Scene\\Scene\\Scene.Tick.cs", 380, "InternalFixedUpdate"))
				{
					ProcessDeletes();
				}
				using (PerformanceStats.Timings.Async.Scope())
				{
					SyncContext.FrameStage.FixedUpdate.Trigger();
				}
				Signal(GameObjectSystem.Stage.FinishFixedUpdate);
			}
			Connection.ClearFixedUpdateContextInput();
		}
	}

	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 13)]
	internal IEnumerable<SceneTraceResult> RunTraceAll(SceneTrace trace)
	{
		SceneMetrics.RayTraceAll++;
		if (trace.NeedsFilterCallback)
		{
			SceneTrace.SetTraceFilter(in trace);
			trace.PhysicsTrace.filterCallback = SceneTrace.PhysicsFilterCallback;
		}
		List<PhysicsTraceResult> list = null;
		if (trace.IncludePhysicsWorld)
		{
			list = _physicsTraceScratch ?? (_physicsTraceScratch = new List<PhysicsTraceResult>());
			list.Clear();
			trace.PhysicsTrace.RunAll(list);
		}
		List<SceneTraceResult> list2 = new List<SceneTraceResult>(list?.Count ?? 0);
		if (list != null)
		{
			foreach (PhysicsTraceResult item2 in list)
			{
				SceneTraceResult item = SceneTraceResult.From(this, item2);
				list2.Add(item);
			}
		}
		if (trace.IncludeRenderMeshes && SceneWorld != null)
		{
			MeshTraceRequest meshTraceRequest = MeshTraceRequest.From(trace.PhysicsTrace.request, SceneWorld, trace.CullMode);
			meshTraceRequest.filterCallback = (trace.NeedsFilterCallback ? SceneTrace.MeshFilterCallback : null);
			MeshTraceRequest.Result[] array = meshTraceRequest.RunAll();
			for (int i = 0; i < array.Length; i++)
			{
				MeshTraceRequest.Result r = array[i];
				if (r.Hit)
				{
					list2.Add(SceneTraceResult.From(this, in r));
				}
			}
		}
		foreach (GameObjectSystem value in systems.Values)
		{
			if (value is GameObjectSystem.ITraceProvider traceProvider)
			{
				traceProvider.DoTrace(in trace, list2);
			}
		}
		SceneTrace.ClearTraceFilter();
		list2.Sort((SceneTraceResult a, SceneTraceResult b) => a.Fraction.CompareTo(b.Fraction));
		return list2;
	}

	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 73)]
	internal SceneTraceResult RunTrace(SceneTrace trace)
	{
		SceneMetrics.RayTrace++;
		SceneTraceResult result = new SceneTraceResult
		{
			Fraction = float.MaxValue
		};
		if (trace.NeedsFilterCallback)
		{
			SceneTrace.SetTraceFilter(in trace);
			trace.PhysicsTrace.filterCallback = SceneTrace.PhysicsFilterCallback;
		}
		if (trace.IncludePhysicsWorld)
		{
			result = SceneTraceResult.From(this, trace.PhysicsTrace.Run());
		}
		if (trace.IncludeRenderMeshes && SceneWorld != null)
		{
			MeshTraceRequest meshTraceRequest = MeshTraceRequest.From(trace.PhysicsTrace.request, SceneWorld, trace.CullMode);
			meshTraceRequest.filterCallback = (trace.NeedsFilterCallback ? SceneTrace.MeshFilterCallback : null);
			MeshTraceRequest.Result r = meshTraceRequest.Run();
			if (r.Hit)
			{
				SceneTraceResult sceneTraceResult = SceneTraceResult.From(this, in r);
				if (sceneTraceResult.Fraction < result.Fraction)
				{
					result = sceneTraceResult;
				}
			}
		}
		foreach (GameObjectSystem value in systems.Values)
		{
			if (value is GameObjectSystem.ITraceProvider traceProvider)
			{
				SceneTraceResult? sceneTraceResult2 = traceProvider.DoTrace(in trace);
				if (sceneTraceResult2.HasValue && sceneTraceResult2.Value.Fraction < result.Fraction)
				{
					result = sceneTraceResult2.Value;
				}
			}
		}
		SceneTrace.ClearTraceFilter();
		if (result.Fraction < 2f)
		{
			return result;
		}
		return new SceneTraceResult
		{
			Scene = trace.scene,
			Hit = false,
			StartedSolid = false,
			StartPosition = trace.PhysicsTrace.request.StartPos,
			EndPosition = trace.PhysicsTrace.request.EndPos,
			HitPosition = trace.PhysicsTrace.request.EndPos,
			Fraction = 1f,
			Direction = (trace.PhysicsTrace.request.EndPos - trace.PhysicsTrace.request.StartPos).Normal,
			_rawTags = default
		};
	}

	/// <summary>
	/// Find game objects in a sphere using physics.
	/// </summary>
	[Description("Find game objects in a sphere using physics.")]
	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 141)]
	public IEnumerable<GameObject> FindInPhysics(Sphere sphere)
	{
		return PhysicsWorld.FindInPhysics(sphere);
	}

	/// <summary>
	/// Find game objects in a box using physics.
	/// </summary>
	[Description("Find game objects in a box using physics.")]
	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 147)]
	public IEnumerable<GameObject> FindInPhysics(BBox box)
	{
		return PhysicsWorld.FindInPhysics(box);
	}

	/// <summary>
	/// Find game objects in a frustum using physics.
	/// </summary>
	[Description("Find game objects in a frustum using physics.")]
	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 153)]
	public IEnumerable<GameObject> FindInPhysics(Frustum frustum)
	{
		return PhysicsWorld.FindInPhysics(frustum);
	}

	/// <summary>
	/// Find physics bodies overlapping a sphere, writing into a caller-provided span.
	/// </summary>
	[Description("Find physics bodies overlapping a sphere, writing into a caller-provided span.")]
	[SourceLocation("Scene\\Scene\\Scene.Trace.cs", 159)]
	internal int FindBodiesInPhysics(Vector3 center, float radius, Span<PhysicsBody> result)
	{
		return (PhysicsWorld?._world?.FindBodiesInPhysics(center, radius, result)).GetValueOrDefault();
	}
}
