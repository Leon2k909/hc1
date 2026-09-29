namespace TerrorTown;

/// <summary>
/// TTT's hinged door. Keeps TTT's name so doors in TTT maps load into it, see <see cref="MapMover"/>.
/// </summary>
public sealed class FuncDoorRotating : MapMover
{
	/// <summary>
	/// Hinge position in the door's local space, used when <see cref="PivotTarget"/> isn't set.
	/// </summary>
	[Property] public Vector3 Pivot { get; set; }
	[Property] public GameObject PivotTarget { get; set; }

	/// <summary>
	/// Local rotation when fully open.
	/// </summary>
	[Property] public Angles TargetRotation { get; set; } = new Angles( 0f, 90f, 0f );

	[Property] public bool OpenAwayFromActivator { get; set; } = true;

	Vector3 _localPivot;

	/// <summary> The hinge in world space, where the door stood closed. </summary>
	public Vector3 HingePosition => (GameObject.Parent?.WorldTransform ?? global::Transform.Zero)
		.PointToWorld( StartTransform.PointToWorld( _localPivot ) );

	/// <summary>
	/// How far the door reaches from its hinge. It can open either way, so it sweeps a full circle this size.
	/// </summary>
	public float SwingRadius
	{
		get
		{
			if ( GetComponent<ModelRenderer>()?.Model is not { } model )
				return 56f;

			var b = model.Bounds;
			var reach = 0f;
			foreach ( var x in new[] { b.Mins.x, b.Maxs.x } )
				foreach ( var y in new[] { b.Mins.y, b.Maxs.y } )
					reach = MathF.Max( reach, new Vector2( x - _localPivot.x, y - _localPivot.y ).Length );

			return reach * WorldScale.x;
		}
	}

	protected override void OnStart()
	{
		_localPivot = PivotTarget.IsValid() ? WorldTransform.PointToLocal( PivotTarget.WorldPosition ) : Pivot;
		base.OnStart();
	}

	protected override Transform GetTransform( float amount, bool reverse )
	{
		var start = StartTransform;
		var rotation = Rotation.From( TargetRotation * (reverse ? -amount : amount) );

		// Rotate around the hinge in the door's own space, expressed in the parent's space
		var parentRotation = start.Rotation * rotation * start.Rotation.Inverse;
		var pivot = start.PointToWorld( _localPivot );

		return start
			.WithPosition( pivot + parentRotation * (start.Position - pivot) )
			.WithRotation( parentRotation * start.Rotation );
	}

	protected override bool ShouldReverse( Vector3 activatorPosition )
	{
		if ( !OpenAwayFromActivator ) return false;

		var model = GetComponent<ModelRenderer>()?.Model;
		if ( model is null ) return false;

		// Only called while closed, so the world transform is the closed one.
		// Nudge the door open a little and see which side the middle of it swings towards.
		var parent = GameObject.Parent?.WorldTransform ?? global::Transform.Zero;
		var center = model.Bounds.Center;
		var closedCenter = WorldTransform.PointToWorld( center );
		var nudgedCenter = parent.ToWorld( GetTransform( 0.1f, false ) ).PointToWorld( center );

		return Vector3.Dot( nudgedCenter - closedCenter, activatorPosition - closedCenter ) > 0f;
	}
}
