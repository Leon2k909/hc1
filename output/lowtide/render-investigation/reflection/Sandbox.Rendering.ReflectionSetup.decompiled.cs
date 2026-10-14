using Sandbox.Internal;

namespace Sandbox.Rendering;

/// <summary>
/// Allows special setup for reflections, such as offsetting the reflection plane
/// </summary>
[Description("Allows special setup for reflections, such as offsetting the reflection plane")]
public struct ReflectionSetup
{
	/// <summary>
	/// Allows overriding everything you normally can
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\ViewSetup.cs", 205)]
	public ViewSetup ViewSetup;

	/// <summary>
	/// Offset the reflection plane's clip plane by this much
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\ViewSetup.cs", 210)]
	public float ClipOffset;

	/// <summary>
	/// If true we'll render the reflection even if we're behind the plane
	/// </summary>
	[SourceLocation("Systems\\Render\\CommandList\\ViewSetup.cs", 215)]
	public bool RenderBehind;

	/// <summary>
	/// If we can't render the reflection and this is set, we'll clear the render target to this color
	/// </summary>
	[Description("If we can't render the reflection and this is set, we'll clear the render target to this color")]
	[SourceLocation("Systems\\Render\\CommandList\\ViewSetup.cs", 220)]
	public Color? FallbackColor { get; set; }
}
