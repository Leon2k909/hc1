using Sandbox.Internal;

namespace Sandbox.Rendering;

/// <summary>
/// When manually rendering a Renderer this will let you override specific
/// elements of that render. This means you can use most of the Renderer's
/// properties, but override some without disturbing the Renderer itself.
/// </summary>
[Description("When manually rendering a Renderer this will let you override specific elements of that render. This means you can use most of the Renderer's properties, but override some without disturbing the Renderer itself.")]
public struct RendererSetup
{
	/// <summary>
	/// Overrides the transform used for rendering
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\ViewSetup.cs", 265)]
	public Transform? Transform;

	/// <summary>
	/// Overrides the color used for rendering
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\ViewSetup.cs", 270)]
	public Color? Color;

	/// <summary>
	/// Overrides the material used for rendering
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\ViewSetup.cs", 275)]
	public Material Material;
}
