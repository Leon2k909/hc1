using System;
using Sandbox.Internal;
using Sandbox.Rendering;

namespace Sandbox;

/// <summary>
/// The base class for all post process effects.
/// </summary>
[Description("The base class for all post process effects.")]
[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 9)]
public abstract class BasePostProcess : Component, Component.ExecuteInEditor, Component.DontExecuteOnServer
{
	public ref struct BlitMode
	{
		/// <summary>
		/// The material to use for the blit.
		/// </summary>
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 59)]
		public Material Material;

		/// <summary>
		/// We'll use this instead of BasePostProcess.Attributes if set.
		/// </summary>
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 64)]
		public RenderAttributes Attributes;

		/// <summary>
		/// Where to place this in the render pipeline
		/// </summary>
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 69)]
		public Stage RenderStage;

		/// <summary>
		/// The order within the stage. Lower numbers get rendered first.
		/// </summary>
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 74)]
		public int Order;

		/// <summary>
		/// If true, the backbuffer will be copied to a texture called "ColorBuffer" before the blit.
		/// </summary>
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 79)]
		public bool WantsBackbuffer;

		/// <summary>
		/// If both WantsBackbuffer and this is true the backbuffer will be mipped after being copied.
		/// </summary>
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 84)]
		public bool WantsBackbufferMips;

		/// <summary>
		/// Shortcut to build a simple blit mode
		/// </summary>
		[Description("Shortcut to build a simple blit mode")]
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 89)]
		public static BlitMode Simple(Material m, Stage stage, int order = 0)
		{
			return new BlitMode
			{
				Material = m,
				RenderStage = stage,
				Order = order
			};
		}

		/// <summary>
		/// Shortcut to build a blit mode that copies the backbuffer first
		/// </summary>
		[Description("Shortcut to build a blit mode that copies the backbuffer first")]
		[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 94)]
		public static BlitMode WithBackbuffer(Material m, Stage stage, int order = 0, bool mip = false)
		{
			return new BlitMode
			{
				Material = m,
				RenderStage = stage,
				Order = order,
				WantsBackbuffer = true,
				WantsBackbufferMips = mip
			};
		}
	}

	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 11)]
	private PostProcessContext? _currentContext;

	/// <summary>
	/// The default attributes for this post process. This will be used by helper functions like Blit.
	/// </summary>
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 30)]
	protected readonly RenderAttributes Attributes = new RenderAttributes();

	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 13)]
	internal PostProcessContext context
	{
		get
		{
			if (!_currentContext.HasValue)
			{
				throw new Exception("Should only be called during build");
			}
			return _currentContext.Value;
		}
	}

	/// <summary>
	/// The camera we're being applied to. This is only valid during the Render call.
	/// </summary>
	[Description("The camera we're being applied to. This is only valid during the Render call.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 25)]
	protected CameraComponent Camera => context.Camera;

	/// <summary>
	/// Whether its command list is compute only - dispatches, barriers, temporary targets, attributes and pipeline textures, no
	/// draws or clears - over the prepass's depth chain and normals, so that at <c>AfterDepthPrepass</c> the managed scene renderer
	/// may run it on the async compute queue, beside the shadow maps (<c>r_managed_async_compute</c>), before the stage's other
	/// command lists. Native runs it at the stage as always.
	/// </summary>
	[Description("Whether its command list is compute only - dispatches, barriers, temporary targets, attributes and pipeline textures, no draws or clears - over the prepass's depth chain and normals, so that at <code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">AfterDepthPrepass</code> the managed scene renderer may run it on the async compute queue, beside the shadow maps (<code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">r_managed_async_compute</code>), before the stage's other command lists. Native runs it at the stage as always.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 144)]
	internal virtual bool AsyncCompute => false;

	/// <summary>
	/// Whether the effect reads the normals and roughness G-buffer the depth-normals prepass writes. Native always draws
	/// that prepass; the managed scene renderer (<c>r_managed_scene</c>) draws depth only unless a camera's effect needs it.
	/// </summary>
	[Description("Whether the effect reads the normals and roughness G-buffer the depth-normals prepass writes. Native always draws that prepass; the managed scene renderer (<code style=\"color: #DCDCDC; background-color: #111111; padding: 4px;\">r_managed_scene</code>) draws depth only unless a camera's effect needs it.")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 150)]
	internal virtual bool NeedsDepthNormals => false;

	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 32)]
	internal void Build(PostProcessContext ctx)
	{
		_currentContext = ctx;
		try
		{
			Attributes.Clear();
			Render();
		}
		finally
		{
			_currentContext = null;
		}
	}

	/// <summary>
	/// Override in your implementation to do your rendering
	/// </summary>
	[Description("Override in your implementation to do your rendering")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 51)]
	public abstract void Render();

	/// <summary>
	/// Helper to do a blit with the current camera's post process
	/// </summary>
	[Description("Helper to do a blit with the current camera's post process")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 100)]
	protected void Blit(BlitMode blit, string debugName)
	{
		if (blit.Material.IsValid())
		{
			CommandList commandList = new CommandList(debugName);
			if (blit.WantsBackbuffer)
			{
				commandList.Attributes.GrabFrameTexture("ColorBuffer", blit.WantsBackbufferMips);
			}
			commandList.Blit(blit.Material, blit.Attributes ?? Attributes);
			InsertCommandList(commandList, blit.RenderStage, blit.Order, debugName);
		}
	}

	/// <summary>
	/// Helper to do a blit with the current camera's post process
	/// </summary>
	[Description("Helper to do a blit with the current camera's post process")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 120)]
	protected void BlitSimple(Material shader, Stage stage, int order, string debugName)
	{
		Blit(BlitMode.Simple(shader, stage, order), debugName);
	}

	/// <summary>
	/// Helper to add a command list to the current camera's post process
	/// </summary>
	[Description("Helper to add a command list to the current camera's post process")]
	[SourceLocation("Scene\\Components\\PostProcessing\\BasePostProcess.cs", 128)]
	protected void InsertCommandList(CommandList cl, Stage stage, int order, string debugName)
	{
		PostProcessLayer postProcessLayer = context.Camera.PostProcess.CreateLayer(stage);
		postProcessLayer.Order = order;
		postProcessLayer.CommandList = cl;
		postProcessLayer.Name = debugName;
		postProcessLayer.NeedsDepthNormals = NeedsDepthNormals;
		postProcessLayer.AsyncCompute = AsyncCompute && stage == Stage.AfterDepthPrepass;
	}
}
