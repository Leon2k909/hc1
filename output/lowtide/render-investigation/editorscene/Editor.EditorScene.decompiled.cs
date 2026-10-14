using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Nodes;
using Sandbox;
using Sandbox.Audio;
using Sandbox.Diagnostics;
using Sandbox.Engine;
using Sandbox.Internal;
using Sandbox.Modals;

namespace Editor;

public static class EditorScene
{
	private static SceneEditorSession recentlyActivePlayableScene;

	private static JsonObject _mixerStore;

	/// <summary>
	/// Should the game start in play mode when hitting play, instead of playing the active scene.
	/// </summary>
	public static bool PlayMode
	{
		get
		{
			return GlobalToolsNamespace.ProjectCookie?.Get("editor.playmode", fallback: false) ?? false;
		}
		set
		{
			GlobalToolsNamespace.ProjectCookie?.Set("editor.playmode", value);
		}
	}

	public static Gizmo.SceneSettings GizmoSettings { get; private set; } = new Gizmo.SceneSettings();

	public static SelectionSystem Selection => SceneEditorSession.Active?.Selection;

	public static void RestoreState()
	{
		_ = Project.Current.Package;
		Gizmo.SceneSettings sceneSettings = GlobalToolsNamespace.ProjectCookie?.Get<Gizmo.SceneSettings>("gizmo.settings", null);
		if (sceneSettings != null)
		{
			GizmoSettings = sceneSettings;
		}
	}

	[Shortcut("editor.new", "CTRL+N", ShortcutType.Widget)]
	public static void NewScene()
	{
		SceneEditorSession.CreateDefault().MakeActive();
	}

	[Shortcut("editor.open", "CTRL+O", ShortcutType.Widget)]
	public static void Open()
	{
		FileDialog fileDialog = new FileDialog(null)
		{
			Title = "Open",
			Directory = Project.Current.GetAssetsPath()
		};
		fileDialog.SetNameFilter("(*.scene; *.prefab)");
		if (fileDialog.Execute())
		{
			SceneEditorSession sceneEditorSession = SceneEditorSession.CreateFromPath(AssetSystem.FindByPath(fileDialog.SelectedFile).RelativePath);
			if (sceneEditorSession == null)
			{
				GlobalGameNamespace.Log.Error($"Failed to open {fileDialog.SelectedFile}");
			}
			else
			{
				sceneEditorSession.MakeActive();
			}
		}
	}

	/// <summary>
	/// Opens the given scene file for editing, if it's not already open.
	/// </summary>
	public static void OpenScene(SceneFile resource)
	{
		SceneEditorSession sceneEditorSession = SceneEditorSession.Resolve(resource);
		if (sceneEditorSession != null)
		{
			sceneEditorSession.MakeActive();
		}
		else if (!string.IsNullOrWhiteSpace(resource.ResourcePath))
		{
			SceneEditorSession.CreateFromPath(resource.ResourcePath)?.MakeActive();
		}
	}

	/// <summary>
	/// Opens the given prefab file for editing, if it's not already open.
	/// </summary>
	public static void OpenPrefab(PrefabFile resource)
	{
		if (SceneEditorSession.Resolve(resource) is PrefabEditorSession prefabEditorSession)
		{
			prefabEditorSession.MakeActive();
			return;
		}
		PrefabScene prefabScene = PrefabScene.CreateForEditing();
		using (prefabScene.Push())
		{
			prefabScene.Load(resource);
			PrefabEditorSession prefabEditorSession2 = new PrefabEditorSession(prefabScene);
			prefabEditorSession2.MakeActive();
		}
	}

	[Shortcut("editor.save", "CTRL+S", ShortcutType.Widget)]
	public static void SaveSession()
	{
		SceneEditorSession.Active?.Save(saveAs: false);
	}

	[Shortcut("editor.save-as", "CTRL+SHIFT+S", ShortcutType.Widget)]
	public static void SaveSessionAs()
	{
		SceneEditorSession.Active?.Save(saveAs: true);
	}

	[Shortcut("editor.save-all", "CTRL+ALT+SHIFT+S", ShortcutType.Widget)]
	public static void SaveAllSessions()
	{
		foreach (SceneEditorSession item in SceneEditorSession.All)
		{
			item.Save(saveAs: false);
		}
	}

	public static void Discard()
	{
		SceneEditorSession active = SceneEditorSession.Active;
		if (active == null || active.HasUnsavedChanges)
		{
			PopupDialogWidget popup = new PopupDialogWidget("\ud83d\udd04\ufe0f");
			popup.FixedWidth = 500f;
			popup.WindowTitle = "Scene";
			popup.MessageLabel.Text = "Are you sure you want to do this, you'll lose all your progress...";
			popup.ButtonLayout.Spacing = 4f;
			popup.ButtonLayout.AddStretchCell();
			popup.ButtonLayout.Add(new Button.Primary("Yes")
			{
				Clicked = () =>
				{
					Scene scene = SceneEditorSession.Active?.Scene;
					scene?.Load(scene.Source);
					popup.Destroy();
				}
			});
			popup.ButtonLayout.Add(new Button("No, nevermind")
			{
				Clicked = popup.Destroy
			});
			popup.SetModal(on: true, application: true);
			popup.Hide();
			popup.Show();
		}
	}

	private static SceneEditorSession FindPlayableSession()
	{
		if (!(SceneEditorSession.Active?.Scene is PrefabScene))
		{
			return SceneEditorSession.Active;
		}
		if (SceneEditorSession.All.Contains(recentlyActivePlayableScene))
		{
			return recentlyActivePlayableScene;
		}
		List<SceneEditorSession> list = SceneEditorSession.All.Where((SceneEditorSession x) => !(x.Scene is PrefabScene)).ToList();
		int num = list.IndexOf(SceneEditorSession.Active);
		if (num < 0)
		{
			return null;
		}
		return list.Take(num).LastOrDefault() ?? list.Skip(num + 1).FirstOrDefault();
	}

	/// <summary>
	/// Toggles play mode.
	/// </summary>
	[Shortcut("editor.toggle-play", "F5", ShortcutType.Window)]
	public static void TogglePlay()
	{
		EditorShortcuts.ReleaseAll();
		if (!Game.IsPlaying)
		{
			Play();
		}
		else
		{
			Stop();
		}
	}

	/// <summary>
	/// Store stuff before playing
	/// </summary>
	private static void OnPlayStore()
	{
		_mixerStore = Mixer.Master.Serialize();
	}

	/// <summary>
	/// Restore stuff before playing
	/// </summary>
	private static void OnPlayRestore()
	{
		if (_mixerStore != null)
		{
			Mixer.ResetToDefault();
			Mixer.Master.Deserialize(_mixerStore, GlobalGameNamespace.TypeLibrary);
		}
	}

	public static void PlayMap(Asset asset)
	{
		Stop();
		if (asset == null)
		{
			GlobalGameNamespace.Log.Error("Cannot play map: map unknown.");
			return;
		}
		LaunchArguments.Map = asset.RelativePath;
		Play(playMode: true);
	}

	public static void Play(SceneEditorSession session = null)
	{
		Play(PlayMode, session);
	}

	public static void Play(bool playMode, SceneEditorSession playableSession = null)
	{
		if (playableSession == null)
		{
			playableSession = FindPlayableSession();
		}
		if (playableSession == null)
		{
			return;
		}
		SceneLoadOptions options = null;
		if (!playMode && !SceneSource.PreparePlay(playableSession, out options))
		{
			return;
		}
		using (options?.RuntimePreparationScope())
		{
			OnPlayStore();
			Game.IsPlaying = true;
			IModalSystem.Current?.CloseAll(immediate: true);
			EditorEvent.Run("scene.startplay");
			if (playMode)
			{
				if (IGameInstance.Current != null)
				{
					LoadingScreen.IsVisible = true;
					LoadingScreen.Title = "Loading Game..";
					if (!IGameInstanceDll.Current.EditorPlay())
					{
						Game.IsPlaying = false;
						LoadingScreen.IsVisible = false;
						OnPlayRestore();
						return;
					}
				}
			}
			else
			{
				LoadingScreen.IsVisible = true;
				LoadingScreen.Title = "Loading Scene..";
				if (Game.ActiveScene != null && !Game.ActiveScene.IsEditor)
				{
					Game.ActiveScene?.Destroy();
					Game.ActiveScene = null;
				}
				string name = playableSession.Scene.Name;
				Game.ActiveScene = new Scene();
				Game.ActiveScene.Name = name;
				Game.ActiveScene.StartLoading();
				if (options == null)
				{
					options = new SceneLoadOptions();
					options.SetScene(playableSession.Scene.CreateSceneFile());
				}
				using (options.RuntimePreparationScope())
				{
					bool flag = options.PrepareRuntime();
					if (flag)
					{
						Game.ActiveScene.RunEvent((ISceneStartup x) =>
						{
							x.OnHostPreInitialize(options.GetSceneFile());
						});
					}
					if (!flag || !Game.ActiveScene.Load(options))
					{
						Game.ActiveScene.Destroy();
						Game.ActiveScene = null;
						Game.IsPlaying = false;
						LoadingScreen.IsVisible = false;
						OnPlayRestore();
						return;
					}
					Game.ActiveScene.RunEvent((ISceneStartup x) =>
					{
						x.OnHostInitialize();
					});
					Game.ActiveScene.RunEvent((ISceneStartup x) =>
					{
						x.OnClientInitialize();
					});
				}
			}
			if (Game.ActiveScene == null)
			{
				GlobalGameNamespace.Log.Warning("Tried to play, but there was no scene.");
				return;
			}
			SceneEditorSession.Active.SetPlaying(Game.ActiveScene);
			EditorEvent.Run("scene.play");
		}
	}

	public static void Stop()
	{
		IModalSystem.Current?.CloseAll(immediate: true);
		Game.IsClosing = true;
		SceneEditorSession.Playing?.StopPlaying();
		Game.IsPlaying = false;
		Game.IsPaused = false;
		ScreenRecorder.StopRecording();
		using (Networking.DisconnectScope())
		{
			Game.ActiveScene?.Destroy();
			Game.ActiveScene = null;
		}
		Game.IsClosing = false;
		Sound.StopAll(0.5f);
		SceneEditorTick();
		EditorEvent.Run("scene.stop");
		Mouse.Visibility = MouseVisibility.Auto;
		OnPlayRestore();
	}

	/// <summary>
	/// Called once a frame to keep the game camera in sync with the main camera in the editor scene
	/// </summary>
	[EditorEvent.Frame]
	public static void SceneEditorTick()
	{
		if (SceneEditorSession.Active != null)
		{
			if (!(SceneEditorSession.Active.Scene is PrefabScene))
			{
				recentlyActivePlayableScene = SceneEditorSession.Active;
			}
			SceneEditorSession.ProcessSceneEdits();
		}
	}

	[EditorForAssetType("scene")]
	[EditorForAssetType("prefab")]
	public static void LoadFromResource(GameResource resource)
	{
		Assert.NotNull(resource, "resource should not be null");
		SceneEditorSession.CreateFromPath(resource.ResourcePath)?.MakeActive();
	}

	internal static void UpdatePrefabInstancesInScene(Scene scene, PrefabFile prefab)
	{
		using (scene.Push())
		{
			foreach (GameObject item in (from x in scene.GetAllObjects(enabled: false)
				where x.IsPrefabInstanceRoot && x.PrefabInstance.PrefabSource.Guid == prefab.Guid
				select x.OutermostPrefabInstanceRoot).ToHashSet())
			{
				if (item.IsValid())
				{
					item.UpdateFromPrefab();
					scene.Editor.HasUnsavedChanges = true;
				}
			}
		}
	}

	/// <summary>
	/// Update any/all instances of a prefab in any open sessions.
	/// Two passes are needed so that changes propagate through prefab dependency
	/// chains regardless of iteration order (e.g. PrefabA → PrefabC → PrefabB).
	/// </summary>
	public static void UpdatePrefabInstances(PrefabFile prefab)
	{
		ArgumentNullException.ThrowIfNull(prefab, "prefab");
		List<SceneEditorSession> all = SceneEditorSession.All;
		foreach (SceneEditorSession item in all)
		{
			if (item is PrefabEditorSession prefabEditorSession && prefabEditorSession.Scene.Source != prefab)
			{
				UpdatePrefabInstancesInScene(prefabEditorSession.Scene, prefab);
				prefabEditorSession.Scene.ToPrefabFile();
			}
		}
		foreach (SceneEditorSession item2 in all)
		{
			if (!(item2 is PrefabEditorSession prefabEditorSession2) || prefabEditorSession2.Scene.Source != prefab)
			{
				UpdatePrefabInstancesInScene(item2.Scene, prefab);
			}
		}
	}

	[Event("model.reload")]
	internal static void OnModelReload(Model model)
	{
		ArgumentNullException.ThrowIfNull(model, "model");
		foreach (SceneEditorSession item in SceneEditorSession.All)
		{
			Scene scene = item.Scene;
			using (scene.Push())
			{
				foreach (IHasModel allComponent in scene.GetAllComponents<IHasModel>())
				{
					if (allComponent.Model == model)
					{
						allComponent.OnModelReloaded();
					}
				}
			}
		}
	}

	[Shortcut("editor.cut", "CTRL+X", ShortcutType.Widget)]
	public static void Cut()
	{
		GameObject[] array = Selection.OfType<GameObject>().ToArray();
		if (array.Count() < 1)
		{
			return;
		}
		Scene.ISceneEditorSession sceneEditorSession = SceneEditorSession.Resolve(array.FirstOrDefault());
		using (sceneEditorSession.Scene.Push())
		{
			GameObject.SerializeOptions options = new GameObject.SerializeOptions();
			EditorUtility.Clipboard.Copy(Json.Serialize(array.Select((GameObject x) => x.Serialize(options)).ToArray()));
			using (sceneEditorSession.UndoScope("Cut").WithGameObjectDestructions(array).Push())
			{
				sceneEditorSession.Selection.Clear();
				GameObject[] array2 = array;
				for (int num = 0; num < array2.Length; num++)
				{
					array2[num].Destroy();
				}
			}
		}
	}

	[Shortcut("editor.select-all", "CTRL+A", ShortcutType.Widget)]
	public static void SelectAll()
	{
		using (SceneEditorSession.Active.UndoScope("Select All").Push())
		{
			Selection.Clear();
			foreach (GameObject item in SceneEditorSession.Active.Scene.Children.Where((GameObject x) => x.ShouldShowInHierarchy()))
			{
				Selection.Add(item);
			}
		}
	}

	[Shortcut("editor.copy", "CTRL+C", ShortcutType.Widget)]
	public static void Copy()
	{
		GameObject.SerializeOptions options = new GameObject.SerializeOptions();
		GameObject[] source = Selection.OfType<GameObject>().ToArray();
		if (!source.Any())
		{
			return;
		}
		EditorUtility.Clipboard.Copy(Json.Serialize(source.Select((GameObject x) =>
		{
			using BlobDataSerializer.BlobContext blobContext = BlobDataSerializer.Capture();
			JsonObject jsonObject = x.Serialize(options);
			jsonObject["Position"] = JsonValue.Create(x.WorldPosition);
			jsonObject["Rotation"] = JsonValue.Create(x.WorldRotation);
			jsonObject["Scale"] = JsonValue.Create(x.WorldScale);
			blobContext.SaveTo(jsonObject);
			return jsonObject;
		})));
	}

	[Shortcut("editor.paste", "CTRL+V", ShortcutType.Widget)]
	public static void Paste()
	{
		PasteInternal();
	}

	public static void PasteAt(SceneTraceResult tr)
	{
		PasteInternal(tr);
	}

	private static void PasteInternal(SceneTraceResult? tr = null)
	{
		GameObject gameObject = Selection.FirstOrDefault() as GameObject;
		using ((SceneEditorSession.Resolve(gameObject) ?? SceneEditorSession.Active).Scene.Push())
		{
			if (gameObject == null)
			{
				gameObject = SceneEditorSession.Active.Scene;
			}
			if (gameObject is Scene)
			{
				PasteAsChildAt(tr);
			}
			else
			{
				ExecutableUndoablePaste(gameObject, asChild: false, tr);
			}
		}
	}

	private static void PasteAsChildAt(SceneTraceResult? tr = null)
	{
		GameObject[] array = Selection.OfType<GameObject>().ToArray();
		GameObject gameObject = array.FirstOrDefault();
		using ((SceneEditorSession.Resolve(gameObject) ?? SceneEditorSession.Active).Scene.Push())
		{
			if (!gameObject.IsValid())
			{
				array = new GameObject[1] { SceneEditorSession.Active.Scene };
			}
			ExecutableUndoablePaste(array, asChild: true, tr);
		}
	}

	[Shortcut("editor.paste-as-child", "CTRL+SHIFT+V", ShortcutType.Widget)]
	public static void PasteAsChild()
	{
		PasteAsChildAt();
	}

	[Shortcut("editor.paste-special", "CTRL+ALT+V", ShortcutType.Widget)]
	public static void PasteSpecial()
	{
		new ScenePasteSpecialDialog(ScenePasteSpecialDialog.Execute).Show();
	}

	private static void ExecutableUndoablePaste(GameObject target, bool asChild, SceneTraceResult? tr)
	{
		ExecutableUndoablePaste(new <>z__ReadOnlySingleElementList<GameObject>(target), asChild, tr);
	}

	private static void ExecutableUndoablePaste(IEnumerable<GameObject> targets, bool asChild, SceneTraceResult? tr)
	{
		string source = EditorUtility.Clipboard.Paste();
		try
		{
			IEnumerable<JsonObject> enumerable = Json.Deserialize<IEnumerable<JsonObject>>(source);
			if (enumerable == null)
			{
				return;
			}
			int num = enumerable.Count();
			if (num == 0)
			{
				return;
			}
			Scene.ISceneEditorSession sceneEditorSession = SceneEditorSession.Resolve(targets.FirstOrDefault());
			using (sceneEditorSession.Scene.Push())
			{
				using (sceneEditorSession.UndoScope($"Paste {num} Objects").WithGameObjectCreations().Push())
				{
					Selection.Clear();
					foreach (GameObject target in targets)
					{
						foreach (JsonObject item in enumerable)
						{
							GameObject gameObject = SceneEditorSession.Active.Scene.CreateObject();
							SceneUtility.MakeIdGuidsUnique(item);
							using (BlobDataSerializer.LoadFrom(item))
							{
								gameObject.Deserialize(item);
								if (target.IsValid())
								{
									if (asChild)
									{
										gameObject.SetParent(target);
									}
									else
									{
										target.AddSibling(gameObject, before: false);
									}
								}
								gameObject.MakeNameUnique();
								Selection.Add(gameObject);
							}
						}
					}
					if (tr.HasValue)
					{
						SceneTraceResult valueOrDefault = tr.GetValueOrDefault();
						PlaceBoundsOnSurface(Selection.OfType<GameObject>(), valueOrDefault.HitPosition, valueOrDefault.Normal);
					}
				}
			}
		}
		catch
		{
			GlobalGameNamespace.Log.Warning("Failed to paste, invalid JSON.");
		}
	}

	/// <summary>
	/// Helper function to offset gameobjects to surface bounds.
	/// </summary>
	public static void PlaceBoundsOnSurface(IEnumerable<GameObject> gos, Vector3 position, Vector3 normal)
	{
		BBox bBox = BBox.FromBoxes(gos.Select((GameObject x) => x.GetBounds()));
		Vector3 center = bBox.Center;
		float num = float.NegativeInfinity;
		foreach (Vector3 corner in bBox.Corners)
		{
			float num2 = Vector3.Dot(corner - center, in normal);
			if (num2 > num)
			{
				num = num2;
			}
		}
		Vector3 vector = position + normal * num - center;
		foreach (GameObject go in gos)
		{
			go.WorldPosition += vector;
		}
	}

	/// <summary>
	/// Capture a high resolution screenshot using the active scene camera.
	/// </summary>
	[ConCmd("screenshot_highres", ConVarFlags.None, Help = "Take a high resolution screenshot you specify the width and height")]
	public static void TakeHighResScreenshot(int width, int height)
	{
		ScreenshotService.TakeHighResScreenshot(SceneEditorSession.Active.Scene, width, height);
	}
}
