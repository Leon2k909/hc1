namespace Facepunch;

/// <summary>
/// Sets bool anim graph parameters around an s&amp;box bug (the 26.10.02 update, sbox-public #5893). A bool reaches the
/// graph as an AnimVariant built from <c>BitConverter.Int32BitsToSingle( 1 )</c>, a denormal float. The JIT folds that
/// constant through a double, and the engine's thread compiles with denormals-are-zero set, so it folds to 0: every
/// <c>Set( name, true )</c> arrives as false (reloads, fire, deploy, IK). False still works, and so does a parameter's
/// own default, which comes from native code. So a parameter whose graph default is true (b_grounded on the bodies)
/// is set true by resetting it to its default. The rest can't be set true from game code until Facepunch fixes it.
/// </summary>
public static class AnimBools
{
	private static readonly Dictionary<(AnimationGraph Graph, string Name), bool> _defaultsTrue = new();

	public static void SetBool( this SkinnedModelRenderer renderer, string name, bool value )
	{
		if ( value && DefaultsTrue( renderer, name ) )
			renderer.Parameters.Reset( name );
		else
			renderer.Set( name, value );
	}

	private static bool DefaultsTrue( SkinnedModelRenderer renderer, string name )
	{
		var graph = renderer.SceneModel.IsValid() ? renderer.SceneModel.AnimationGraph : null;
		if ( graph is null || !graph.IsValid )
			return false;

		if ( _defaultsTrue.TryGetValue( (graph, name), out var defaultsTrue ) )
			return defaultsTrue;

		defaultsTrue = graph.GetParameterType( name ) == typeof( bool ) && graph.GetParameter<bool>( name ).DefaultValue;
		_defaultsTrue[(graph, name)] = defaultsTrue;
		return defaultsTrue;
	}
}
