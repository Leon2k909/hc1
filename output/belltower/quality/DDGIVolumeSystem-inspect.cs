using System;
using System.Collections.Generic;
using System.Linq;
using Sandbox.Diagnostics;
using Sandbox.Internal;

namespace Sandbox;

/// <summary>
/// Maintains GPU data for all <see cref="T:Sandbox.IndirectLightVolume" /> instances in a scene.
/// Collects, sorts, and uploads volume parameters to the renderer.
/// </summary>
[Description("Maintains GPU data for all <span style=\"color: #4EC9B0;\">IndirectLightVolume</span> instances in a scene. Collects, sorts, and uploads volume parameters to the renderer.")]
[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 12)]
internal sealed class DDGIVolumeSystem : GameObjectSystem<DDGIVolumeSystem>
{
	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 14)]
	private GpuBuffer<IndirectLightVolume.DDGIVolumeGpuData> GpuBuffer;

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 15)]
	private bool _dirty = true;

	public DDGIVolumeSystem(Scene scene)
		: base(scene)
	{
		Listen(Stage.FinishUpdate, 0, UpdateVolumes, "UpdateDDGIVolumes");
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 22)]
	public override void Dispose()
	{
		ReleaseBuffer();
		Scene?.RenderAttributes?.Set(StringToken.Literal("DDGI_VolumeCount", 1666729117u), 0);
		Scene?.RenderAttributes?.Set(StringToken.Literal("DDGI_Volumes", 1039222852u), (GpuBuffer)null);
		base.Dispose();
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 32)]
	internal void MarkDirty()
	{
		_dirty = true;
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 37)]
	private void UpdateVolumes()
	{
		using (PerformanceStats.Timings.Render.Scope())
		{
			if (!Graphics.IsAvailable || Scene?.RenderAttributes == null)
			{
				return;
			}
			foreach (IndirectLightVolume item in Scene.Query<IndirectLightVolume>())
			{
				if (item != null && item.Active && item.Enabled)
				{
					item.IrradianceTexture?.MarkUsed();
					item.DistanceTexture?.MarkUsed();
					item.RelocationTexture?.MarkUsed();
				}
			}
			if (!_dirty)
			{
				return;
			}
			_dirty = false;
			IOrderedEnumerable<IndirectLightVolume> orderedEnumerable = from volume in Scene.GetAll<IndirectLightVolume>()
				where volume?.Active ?? false
				orderby volume.Bounds.Volume
				select volume;
			List<IndirectLightVolume.DDGIVolumeGpuData> list = new List<IndirectLightVolume.DDGIVolumeGpuData>();
			foreach (IndirectLightVolume item2 in orderedEnumerable)
			{
				if (item2.Enabled && item2.BuildData(out var data))
				{
					list.Add(data);
				}
			}
			if (list.Count > 0)
			{
				EnsureBufferCapacity(list.Count);
				GpuBuffer.SetData(list);
				Scene.RenderAttributes.Set(StringToken.Literal("DDGI_VolumeCount", 1666729117u), list.Count);
				RenderAttributes renderAttributes = Scene.RenderAttributes;
				StringToken k = StringToken.Literal("DDGI_Volumes", 1039222852u);
				GpuBuffer value = GpuBuffer;
				renderAttributes.Set(in k, in value);
			}
			else
			{
				ReleaseBuffer();
				Scene.RenderAttributes.Set(StringToken.Literal("DDGI_VolumeCount", 1666729117u), 0);
				Scene.RenderAttributes.Set(StringToken.Literal("DDGI_Volumes", 1039222852u), (GpuBuffer)null);
			}
		}
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 93)]
	private void EnsureBufferCapacity(int count)
	{
		if (GpuBuffer == null || GpuBuffer.ElementCount < count)
		{
			ReleaseBuffer();
			GpuBuffer = new GpuBuffer<IndirectLightVolume.DDGIVolumeGpuData>(Math.Max(count, 1), Sandbox.GpuBuffer.UsageFlags.Structured, "DDGI_Volumes");
		}
	}

	[SourceLocation("Scene\\Components\\IndirectLighting\\DDGIVolumeSystem.cs", 102)]
	private void ReleaseBuffer()
	{
		GpuBuffer?.Dispose();
		GpuBuffer = null;
	}
}
