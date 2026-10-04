namespace Facepunch;

/// <summary>
/// Sets and reads anim graph flags around an s&amp;box bug (the 26.10.02 update, sbox-public #5893; fixed by #6000, not
/// yet released). A bool reaches the graph as an AnimVariant built from <c>BitConverter.Int32BitsToSingle( 1 )</c>, a
/// denormal float. The JIT folds that constant through a double, and the engine's threads run with denormals-are-zero
/// set, so it folds to 0: every <c>Set( name, true )</c> arrives as false (reloads, fire, deploy, IK).
/// <para>An int set at runtime gets through, and the engine converts it to an enum parameter. So
/// <c>Tools/animgraph_flags.py</c> turns our graphs' bool parameters into enums of false and true, and these set them
/// as 0 or 1 and read them back as ints. That keeps working once the fix is out.</para>
/// <para>A bool parameter in a graph we don't have (the engine's human graph, which the bodies use) gets the same int.
/// The engine turns it into a bool through the same constructor, but that has come through: in a match on 2026-10-04
/// the bodies' hand IK read back true from the graph once this was in, where it had been false all match. Where the
/// graph's default is true (b_grounded), the parameter is reset to its default instead, since a default comes from
/// native code.</para>
/// </summary>
public static class AnimBools
{
	/// <summary>How a graph holds a flag.</summary>
	private enum Kind : byte
	{
		/// <summary>An enum of false and true (converted), or a graph not loaded yet.</summary>
		Flag,
		Bool,
		BoolTrueByDefault
	}

	/// <summary>
	/// 0 and 1, read from an array so the JIT can't see the 1: a constant 1 inlined into the variant's constructor would
	/// fold through a double the same way.
	/// </summary>
	private static readonly int[] Values = { 0, 1 };

	private static readonly Dictionary<(AnimationGraph Graph, string Name), Kind> _kinds = new();

	public static void SetBool( this SkinnedModelRenderer renderer, string name, bool value )
	{
		if ( value && KindOf( renderer, name ) == Kind.BoolTrueByDefault )
			renderer.Parameters.Reset( name );
		else
			renderer.Set( name, Values[value ? 1 : 0] );
	}

	/// <summary>Reads a flag set with <see cref="SetBool"/>. <c>GetBool</c> can't read an enum.</summary>
	public static bool GetFlag( this SkinnedModelRenderer renderer, string name )
	{
		return KindOf( renderer, name ) == Kind.Flag ? renderer.GetInt( name ) != 0 : renderer.GetBool( name );
	}

	private static Kind KindOf( SkinnedModelRenderer renderer, string name )
	{
		var graph = renderer.SceneModel.IsValid() ? renderer.SceneModel.AnimationGraph : null;
		if ( graph is null || !graph.IsValid )
			return Kind.Flag;

		if ( _kinds.TryGetValue( (graph, name), out var kind ) )
			return kind;

		kind = graph.GetParameterType( name ) != typeof( bool ) ? Kind.Flag
			: graph.GetParameter<bool>( name ).DefaultValue ? Kind.BoolTrueByDefault
			: Kind.Bool;
		_kinds[(graph, name)] = kind;
		return kind;
	}
}
