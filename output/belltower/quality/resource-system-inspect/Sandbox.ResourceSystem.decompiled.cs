using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using NativeEngine;
using Sandbox.Diagnostics;
using Sandbox.Engine;
using Sandbox.Internal;

namespace Sandbox;

[SourceLocation("Resources\\ResourceLibrary.cs", 10)]
public class ResourceSystem
{
	internal struct ResourceStats
	{
		[SourceLocation("Resources\\ResourceLibrary.cs", 490)]
		public Dictionary<string, int> StrongIndex = new Dictionary<string, int>();

		[SourceLocation("Resources\\ResourceLibrary.cs", 491)]
		public Dictionary<string, int> WeakIndexEntries = new Dictionary<string, int>();

		[SourceLocation("Resources\\ResourceLibrary.cs", 492)]
		public int StrongTotal = 0;

		[SourceLocation("Resources\\ResourceLibrary.cs", 493)]
		public int WeakTotal = 0;

		public ResourceStats()
		{
		}
	}

	/// <summary>
	/// Prune dead entries from the WeakIndex to prevent unbounded growth.
	/// Only runs every 30 seconds.
	/// </summary>
	[SourceLocation("Resources\\ResourceLibrary.cs", 214)]
	private TimeSince _lastWeakPrune;

	[SourceLocation("Resources\\ResourceLibrary.cs", 13)]
	private Dictionary<int, Resource> ResourceIndex { get; } = new Dictionary<int, Resource>();

	[SourceLocation("Resources\\ResourceLibrary.cs", 14)]
	private Dictionary<ulong, Resource> ResourceIndexLong { get; } = new Dictionary<ulong, Resource>();

	[SourceLocation("Resources\\ResourceLibrary.cs", 15)]
	private Dictionary<Guid, Resource> GuidIndex { get; } = new Dictionary<Guid, Resource>();

	[SourceLocation("Resources\\ResourceLibrary.cs", 18)]
	private Dictionary<int, WeakReference<Resource>> WeakIndex { get; } = new Dictionary<int, WeakReference<Resource>>();

	[SourceLocation("Resources\\ResourceLibrary.cs", 19)]
	private Dictionary<ulong, WeakReference<Resource>> WeakIndexLong { get; } = new Dictionary<ulong, WeakReference<Resource>>();

	[SourceLocation("Resources\\ResourceLibrary.cs", 20)]
	private Dictionary<Guid, WeakReference<Resource>> WeakGuidIndex { get; } = new Dictionary<Guid, WeakReference<Resource>>();

	/// Maps ResourceIdLong → path for all resources that exist on disk.
	/// Populated at startup without loading anything; used as on-demand load fallback during
	/// network deserialization when a resource hasn't been loaded on the client yet.
	[SourceLocation("Resources\\ResourceLibrary.cs", 25)]
	private Dictionary<ulong, string> PathIndex { get; } = new Dictionary<ulong, string>();

	[SourceLocation("Resources\\ResourceLibrary.cs", 539)]
	private Dictionary<string, AssetTypeAttribute> TypeCache { get; } = new Dictionary<string, AssetTypeAttribute>(StringComparer.OrdinalIgnoreCase);

	[SourceLocation("Resources\\ResourceLibrary.cs", 28)]
	internal void RegisterPath(string path)
	{
		path = Resource.FixPath(path);
		if (!string.IsNullOrEmpty(path))
		{
			PathIndex[path.FastHash64()] = path;
		}
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 35)]
	internal void Register(Resource resource)
	{
		ThreadSafe.AssertIsMainThread("Register");
		if (!string.IsNullOrEmpty(resource.ResourcePath))
		{
			ResourceIndex[resource.ResourceId] = resource;
			ResourceIndexLong[resource.ResourceIdLong] = resource;
		}
		if (resource.Guid != Guid.Empty)
		{
			if (GuidIndex.TryGetValue(resource.Guid, out var value) && value != resource && resource.ResourceIdLong != value.ResourceIdLong && !value.IsError)
			{
				GlobalSystemNamespace.Log.Warning($"GUID not unique! Assigning temp new GUID to: {resource.ResourcePath}");
				resource.Guid = Guid.NewGuid();
			}
			GuidIndex[resource.Guid] = resource;
		}
		GameResource gameResource = resource as GameResource;
		if (gameResource != null && !gameResource.IsPromise)
		{
			IToolsDll.Current?.RunEvent((ResourceLibrary.IEventListener i) =>
			{
				i.OnRegister(gameResource);
			});
		}
	}

	/// <summary>
	/// Register a resource with a weak reference, allowing GC to collect it when no longer in use.
	/// </summary>
	[Description("Register a resource with a weak reference, allowing GC to collect it when no longer in use.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 70)]
	internal void RegisterWeak(Resource resource)
	{
		if (!string.IsNullOrEmpty(resource.ResourcePath))
		{
			WeakIndex[resource.ResourceId] = new WeakReference<Resource>(resource);
			WeakIndexLong[resource.ResourceIdLong] = new WeakReference<Resource>(resource);
		}
		if (resource.Guid != Guid.Empty)
		{
			WeakGuidIndex[resource.Guid] = new WeakReference<Resource>(resource);
		}
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 86)]
	internal void Unregister(Resource resource)
	{
		ThreadSafe.AssertIsMainThread("Unregister");
		if (!(RemoveIndexed(ResourceIndexLong, resource.ResourceIdLong, resource) | RemoveIndexedWeak(WeakIndexLong, resource.ResourceIdLong, resource) | RemoveIndexed(ResourceIndex, resource.ResourceId, resource) | RemoveIndexedWeak(WeakIndex, resource.ResourceId, resource) | RemoveIndexed(GuidIndex, resource.Guid, resource) | RemoveIndexedWeak(WeakGuidIndex, resource.Guid, resource)))
		{
			return;
		}
		GameResource gameResource = resource as GameResource;
		if (gameResource != null && !gameResource.IsPromise)
		{
			IToolsDll.Current?.RunEvent((ResourceLibrary.IEventListener i) =>
			{
				i.OnUnregister(gameResource);
			});
		}
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 110)]
	private static bool RemoveIndexed<TKey>(Dictionary<TKey, Resource> index, TKey key, Resource resource)
	{
		if (!index.TryGetValue(key, out var value) || value != resource)
		{
			return false;
		}
		return index.Remove(key);
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 118)]
	private static bool RemoveIndexedWeak<TKey>(Dictionary<TKey, WeakReference<Resource>> index, TKey key, Resource resource)
	{
		if (!index.TryGetValue(key, out var value))
		{
			return false;
		}
		if (!value.TryGetTarget(out var target))
		{
			index.Remove(key);
			return false;
		}
		if (target != resource)
		{
			return false;
		}
		return index.Remove(key);
	}

	/// <summary>
	/// Update the path of a resource, updating the index and re-registering it.
	/// </summary>
	[Description("Update the path of a resource, updating the index and re-registering it.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 140)]
	internal void MoveResource(Resource resource, string newPath)
	{
		ThreadSafe.AssertIsMainThread("MoveResource");
		newPath = Resource.FixPath(newPath);
		if (!string.Equals(resource.ResourcePath, newPath))
		{
			ThreadSafe.AssertIsMainThread("MoveResource");
			if (!string.IsNullOrEmpty(resource.ResourcePath))
			{
				GlobalSystemNamespace.Log.Info($"Resource moved: {resource.ResourcePath} -> {newPath} ({resource.Guid})");
			}
			Unregister(resource);
			if (resource is GameResource gameResource)
			{
				gameResource.Register(newPath);
			}
			else
			{
				resource.RegisterWeakResourceId(newPath);
			}
		}
	}

	/// <summary>
	/// Grant a new GUID to a resource, updating the index.
	/// </summary>
	[Description("Grant a new GUID to a resource, updating the index.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 167)]
	internal void AssignGuid(Resource resource, Guid newGuid)
	{
		if (newGuid == Guid.Empty || newGuid == resource.Guid)
		{
			return;
		}
		if (resource is GameResource)
		{
			RemoveIndexed(GuidIndex, resource.Guid, resource);
		}
		else
		{
			RemoveIndexedWeak(WeakGuidIndex, resource.Guid, resource);
		}
		resource.Guid = newGuid;
		if (!(resource.Guid == Guid.Empty))
		{
			if ((GuidIndex.TryGetValue(newGuid, out var value) || (WeakGuidIndex.TryGetValue(newGuid, out var value2) && value2.TryGetTarget(out value))) && value != resource)
			{
				GlobalSystemNamespace.Log.Error($"GUID collision! ({newGuid}) incoming: {resource.ResourcePath}, existing: {value.ResourcePath}");
			}
			if (resource is GameResource)
			{
				GuidIndex[newGuid] = resource;
			}
			else
			{
				WeakGuidIndex[resource.Guid] = new WeakReference<Resource>(resource);
			}
		}
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 205)]
	internal void OnHotload()
	{
		TypeCache.Clear();
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 216)]
	internal void PruneWeakIndex()
	{
		if (_lastWeakPrune < 30)
		{
			return;
		}
		_lastWeakPrune = 0f;
		foreach (int item in (from kvp in WeakIndex
			where !kvp.Value.TryGetTarget(out var _)
			select kvp.Key).ToList())
		{
			WeakIndex.Remove(item);
		}
		foreach (ulong item2 in (from kvp in WeakIndexLong
			where !kvp.Value.TryGetTarget(out var _)
			select kvp.Key).ToList())
		{
			WeakIndexLong.Remove(item2);
		}
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 236)]
	internal void Clear()
	{
		Resource[] array = ResourceIndex.Values.ToArray();
		foreach (GameResource item in array.OfType<GameResource>())
		{
			item.DestroyInternal();
		}
		Resource[] array2 = array;
		for (int i = 0; i < array2.Length; i++)
		{
			array2[i]?.Destroy();
		}
		GuidIndex.Clear();
		WeakGuidIndex.Clear();
		ResourceIndex.Clear();
		WeakIndex.Clear();
		ResourceIndexLong.Clear();
		WeakIndexLong.Clear();
		PathIndex.Clear();
		TypeCache.Clear();
	}

	/// <summary>
	/// Find all alive weak resources of a given type whose ResourcePath starts with the given prefix.
	/// Used for hotload scenarios like SVG textures with query parameters.
	/// </summary>
	[Description("Find all alive weak resources of a given type whose ResourcePath starts with the given prefix. Used for hotload scenarios like SVG textures with query parameters.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 270)]
	internal IEnumerable<T> FindWeakByPathPrefix<T>(string pathPrefix) where T : Resource
	{
		foreach (KeyValuePair<int, WeakReference<Resource>> item in WeakIndex)
		{
			if (item.Value.TryGetTarget(out var target) && target is T val && target.ResourcePath != null && target.ResourcePath.TrimStart('/').StartsWith(pathPrefix, StringComparison.OrdinalIgnoreCase))
			{
				yield return val;
			}
		}
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 285)]
	internal Resource Get(Type t, ResourceId id)
	{
		Guid? guid = id.Guid;
		if (guid.HasValue)
		{
			Guid valueOrDefault = guid.GetValueOrDefault();
			if (valueOrDefault != default(Guid))
			{
				if (GuidIndex.TryGetValue(valueOrDefault, out var value))
				{
					if (value.GetType().IsAssignableTo(t))
					{
						return value;
					}
					return null;
				}
				if (WeakGuidIndex.TryGetValue(valueOrDefault, out var value2) && value2.TryGetTarget(out value))
				{
					if (value.GetType().IsAssignableTo(t))
					{
						return value;
					}
					return null;
				}
			}
		}
		if (!string.IsNullOrEmpty(id.Path))
		{
			ulong key = Resource.FixPath(id.Path).FastHash64();
			if (ResourceIndexLong.TryGetValue(key, out var value3))
			{
				if (value3.GetType().IsAssignableTo(t))
				{
					return value3;
				}
				return null;
			}
			if (WeakIndexLong.TryGetValue(key, out var value4) && value4.TryGetTarget(out var target) && target.GetType().IsAssignableTo(t))
			{
				return target;
			}
		}
		return null;
	}

	/// <summary>
	/// Get a cached resource by its hash.
	/// </summary>
	/// <typeparam name="T">Resource type to get.</typeparam>
	/// <param name="identifier">Resource hash to look up.</param>
	[Obsolete("Use Get<T>(path) instead. Identifier based access will be removed in a future update.")]
	[Description("Get a cached resource by its hash.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 338)]
	public T Get<T>([Description("Resource hash to look up.")] int identifier) where T : Resource
	{
		if (ResourceIndex.TryGetValue(identifier, out var value))
		{
			return value as T;
		}
		if (WeakIndex.TryGetValue(identifier, out var value2) && value2.TryGetTarget(out var target))
		{
			return target as T;
		}
		return null;
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 351)]
	internal T GetByIdLong<T>(ulong idLong) where T : Resource
	{
		if (ResourceIndexLong.TryGetValue(idLong, out var value))
		{
			return value as T;
		}
		if (WeakIndexLong.TryGetValue(idLong, out var value2) && value2.TryGetTarget(out var target))
		{
			return target as T;
		}
		return null;
	}

	/// <summary>
	/// Get a cached resource by GUID.
	/// </summary>
	/// <typeparam name="T">Resource type to get.</typeparam>
	/// <param name="id">GUID of the resource.</param>
	[Description("Get a cached resource by GUID.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 367)]
	public T Get<T>([Description("GUID of the resource.")] Guid id) where T : Resource
	{
		if (GuidIndex.TryGetValue(id, out var value))
		{
			return value as T;
		}
		if (WeakGuidIndex.TryGetValue(id, out var value2) && value2.TryGetTarget(out var target))
		{
			return target as T;
		}
		return null;
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 378)]
	internal string LookupPath(ulong idLong)
	{
		return PathIndex.GetValueOrDefault(idLong);
	}

	/// <summary>
	/// Get a cached resource by its file path.
	/// </summary>
	/// <typeparam name="T">Resource type to get.</typeparam>
	/// <param name="filepath">File path to the resource.</param>
	[Description("Get a cached resource by its file path.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 388)]
	public T Get<T>([Description("File path to the resource.")] string filepath) where T : Resource
	{
		filepath = Resource.FixPath(filepath);
		return GetByIdLong<T>(filepath.FastHash64());
	}

	/// <summary>
	/// Get a cached resource
	/// </summary>
	[Description("Get a cached resource")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 399)]
	internal T Get<T>(ResourceId id) where T : Resource
	{
		return Get(typeof(T), id) as T;
	}

	/// <summary>
	/// Try to get a cached resource by its file path.
	/// </summary>
	/// <typeparam name="T">Resource type to get.</typeparam>
	/// <param name="filepath">File path to the resource.</param>
	/// <param name="resource">The retrieved resource, if any.</param>
	/// <returns>True if resource was retrieved successfully.</returns>
	[Description("Try to get a cached resource by its file path.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 411)]
	[return: Description("True if resource was retrieved successfully.")]
	public bool TryGet<T>([Description("File path to the resource.")] string filepath, [Description("The retrieved resource, if any.")] out T resource) where T : Resource
	{
		resource = Get<T>(filepath);
		return resource != null;
	}

	/// <summary>
	/// Try to get a cached resource by its GUID.
	/// </summary>
	/// <typeparam name="T">Resource type to get.</typeparam>
	/// <param name="id">GUID of the resource.</param>
	/// <param name="resource">The retrieved resource, if any.</param>
	/// <returns>True if resource was retrieved successfully.</returns>
	[Description("Try to get a cached resource by its GUID.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 424)]
	[return: Description("True if resource was retrieved successfully.")]
	public bool TryGet<T>([Description("GUID of the resource.")] Guid id, [Description("The retrieved resource, if any.")] out T resource) where T : Resource
	{
		resource = Get<T>(id);
		return resource != null;
	}

	/// <summary>
	/// Get all cached resources of given type.
	/// </summary>
	/// <typeparam name="T">Resource type to get.</typeparam>
	[Description("Get all cached resources of given type.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 434)]
	public IEnumerable<T> GetAll<T>()
	{
		return ResourceIndex.Values.OfType<T>().Distinct();
	}

	/// <summary>
	/// Get all cached resources of given type in a specific folder.
	/// </summary>
	/// <typeparam name="T">Resource type to get.</typeparam>
	/// <param name="filepath">The path of the folder to check.</param>
	/// <param name="recursive">Whether or not to check folders within the specified folder.</param>
	[Description("Get all cached resources of given type in a specific folder.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 445)]
	public IEnumerable<T> GetAll<T>([Description("The path of the folder to check.")] string filepath, [Description("Whether or not to check folders within the specified folder.")] bool recursive = true) where T : Resource
	{
		filepath = filepath.Replace('\\', '/');
		if (!filepath.EndsWith("/"))
		{
			filepath += "/";
		}
		return ResourceIndex.Values.OfType<T>().Distinct().Where((T x) =>
		{
			if (x.ResourcePath.StartsWith(filepath))
			{
				if (recursive)
				{
					return true;
				}
				if (!x.ResourcePath.Substring(filepath.Length).Contains("/"))
				{
					return true;
				}
			}
			return false;
		});
	}

	/// <summary>
	/// Returns stats about the ResourceIndex and WeakIndex for debug overlays.
	/// </summary>
	[Description("Returns stats about the ResourceIndex and WeakIndex for debug overlays.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 463)]
	internal ResourceStats GetResourceStats()
	{
		ResourceStats result = new ResourceStats();
		foreach (Resource value3 in ResourceIndex.Values)
		{
			string name = value3.GetType().Name;
			result.StrongIndex.TryGetValue(name, out var value);
			result.StrongIndex[name] = value + 1;
		}
		foreach (KeyValuePair<int, WeakReference<Resource>> item in WeakIndex)
		{
			string key = (item.Value.TryGetTarget(out var target) ? target.GetType().Name : "(dead)");
			result.WeakIndexEntries.TryGetValue(key, out var value2);
			result.WeakIndexEntries[key] = value2 + 1;
		}
		result.StrongTotal = ResourceIndex.Count;
		result.WeakTotal = WeakIndex.Count;
		return result;
	}

	/// <summary>
	/// Read compiled resource as JSON from the provided buffer.
	/// </summary>
	[Description("Read compiled resource as JSON from the provided buffer.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 505)]
	internal unsafe string ReadCompiledResourceJson(Span<byte> data)
	{
		fixed (byte* data2 = data)
		{
			return EngineGlue.ReadCompiledResourceFileJson((nint)data2, data.Length) ?? throw new InvalidDataException("Compiled resource has invalid JSON data or an invalid container.");
		}
	}

	/// <summary>
	/// Read compiled resource as JSON from the provided file path.
	/// </summary>
	[Description("Read compiled resource as JSON from the provided file path.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 517)]
	internal string ReadCompiledResourceJson(BaseFileSystem fs, string fileName)
	{
		if (!fs.FileExists(fileName))
		{
			return string.Empty;
		}
		return ReadCompiledResourceJson(fs.ReadAllBytes(fileName));
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 525)]
	internal unsafe byte[] ReadCompiledResourceBlock(string blockName, Span<byte> data)
	{
		fixed (byte* pHeader = data)
		{
			nint num = EngineGlue.ReadCompiledResourceFileBlock(blockName, (nint)pHeader, data.Length, out var nSize);
			if (num == IntPtr.Zero || nSize <= 0)
			{
				return null;
			}
			byte[] array = new byte[nSize];
			Marshal.Copy(num, array, 0, nSize);
			return array;
		}
	}

	/// <summary>
	/// Get the <see cref="T:Sandbox.AssetTypeAttribute" /> for a given extension.
	/// </summary>
	[Description("Get the <span style=\"color: #4EC9B0;\">AssetTypeAttribute</span> for a given extension.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 544)]
	internal bool TryGetType(string extension, out AssetTypeAttribute resourceAttribute)
	{
		if (extension.StartsWith('.'))
		{
			extension = extension.Substring(1);
		}
		if (extension.EndsWith("_c", StringComparison.OrdinalIgnoreCase))
		{
			string text = extension;
			extension = text.Substring(0, text.Length - 2);
		}
		if (TypeCache.TryGetValue(extension, out resourceAttribute))
		{
			return true;
		}
		resourceAttribute = Game.TypeLibrary.GetAttributes<AssetTypeAttribute>().FirstOrDefault((AssetTypeAttribute x) => string.Equals(x.Extension, extension, StringComparison.OrdinalIgnoreCase));
		if (resourceAttribute != null)
		{
			TypeCache[extension] = resourceAttribute;
			return true;
		}
		return false;
	}

	/// <summary>
	/// garry: why the fuck does this exist
	/// garry: fuck me why the fuck does this exist
	/// </summary>
	[Description("garry: why the fuck does this exist garry: fuck me why the fuck does this exist")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 568)]
	internal GameResource LoadRawGameResource(string path)
	{
		string extension = Path.GetExtension(path);
		if (!TryGetType(extension, out var resourceAttribute))
		{
			GlobalSystemNamespace.Log.Warning($"Could not find GameResource for extension '{extension}'");
			return null;
		}
		string text = EngineGlue.ReadCompiledResourceFileJsonFromFilesystem(path);
		if (string.IsNullOrEmpty(text))
		{
			GlobalSystemNamespace.Log.Warning($"Failed to load {path}");
			return null;
		}
		try
		{
			GameResource promise = GameResource.GetPromise(resourceAttribute.TargetType, path);
			if (promise == null)
			{
				return null;
			}
			promise.LoadFromJson(text);
			Register(promise);
			promise.PostLoadInternal();
			return promise;
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Warning(ex, $"\t\tError when deserializing {path} ({ex.Message})");
		}
		return null;
	}

	[SourceLocation("Resources\\ResourceLibrary.cs", 606)]
	internal T LoadGameResource<T>(string file, BaseFileSystem fs, bool deferPostload = false, Package sourcePackage = null) where T : GameResource
	{
		AssetTypeAttribute customAttribute = typeof(T).GetCustomAttribute<AssetTypeAttribute>();
		if (customAttribute == null)
		{
			return null;
		}
		customAttribute.TargetType = typeof(T);
		return LoadGameResource(customAttribute, file, fs, deferPostload, sourcePackage) as T;
	}

	/// <summary>
	/// Loads a Gameresource from disk. Doesn't look at cache. Registers the resource if successful.
	/// </summary>
	[Description("Loads a Gameresource from disk. Doesn't look at cache. Registers the resource if successful.")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 621)]
	internal GameResource LoadGameResource(AssetTypeAttribute type, string file, BaseFileSystem fs, bool deferPostload = false, Package sourcePackage = null)
	{
		Assert.NotNull(type);
		Assert.NotNull(file);
		if (!file.EndsWith("_c"))
		{
			file += "_c";
		}
		Span<byte> data = null;
		try
		{
			if (fs.FileExists(file))
			{
				data = fs.ReadAllBytes(file);
			}
			if (data.Length <= 3)
			{
				GlobalSystemNamespace.Log.Warning($"\t\tSkipping {file} (is null)");
				return null;
			}
			ResourceId id = file;
			if (g_pResourceSystem.ResolvePathToGuid(file, out var guid))
			{
				id.Guid = guid;
			}
			GameResource promise = GameResource.GetPromise(type.TargetType, id);
			if (promise == null)
			{
				return null;
			}
			if (sourcePackage != null)
			{
				promise.Package = sourcePackage;
			}
			promise.TryLoadFromData(data);
			if (Application.IsEditor)
			{
				string path = file.Substring(0, file.Length - 2);
				if (fs.FileExists(path))
				{
					string str = fs.ReadAllText(path);
					promise.LastSavedSourceHash = str.FastHash();
				}
			}
			if (Application.IsDedicatedServer)
			{
				InstallReferences(promise);
			}
			Guid? guid2 = id.Guid;
			if (guid2.HasValue)
			{
				Guid valueOrDefault = guid2.GetValueOrDefault();
				if (valueOrDefault != default(Guid))
				{
					AssignGuid(promise, valueOrDefault);
				}
			}
			if (promise.ResourcePath != file)
			{
				MoveResource(promise, file);
			}
			else
			{
				Register(promise);
			}
			if (!deferPostload)
			{
				promise.PostLoadInternal();
			}
			return promise;
		}
		catch (Exception ex)
		{
			GlobalSystemNamespace.Log.Warning(ex, $"\t\tError when deserializing {file} ({ex.Message})");
			return null;
		}
	}

	/// <summary>
	/// Installs all references for a GameResource 
	/// </summary>
	[Description("Installs all references for a GameResource")]
	[SourceLocation("Resources\\ResourceLibrary.cs", 708)]
	private void InstallReferences(GameResource se)
	{
		foreach (string referencedPackage in se.GetReferencedPackages())
		{
			PackageLoadOptions options = new PackageLoadOptions();
			options.PackageIdent = referencedPackage;
			options.ContextTag = "server";
			PackageManager.InstallAsync(options);
		}
	}
}
