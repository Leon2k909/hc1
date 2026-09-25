namespace TerrorTown;

/// <summary>
/// TTT's sliding mover (shutters, secret doors). Keeps TTT's name so movers in TTT maps load into it, see <see cref="MapMover"/>.
/// </summary>
public sealed class FuncMoveLinear : MapMover
{
	/// <summary>
	/// How far to move when fully open, in the parent's space.
	/// </summary>
	[Property] public Vector3 MoveDelta { get; set; }

	protected override Transform GetTransform( float amount, bool reverse )
	{
		return StartTransform.WithPosition( StartTransform.Position + MoveDelta * amount );
	}
}
