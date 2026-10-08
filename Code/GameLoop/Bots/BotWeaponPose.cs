namespace Facepunch;

/// <summary>Keeps a held weapon's stock outside the torso while fitting the arms to its final pose.</summary>
public sealed class BotWeaponPose
{
	private Model _gunModel, _bodyModel;
	private ulong _groups;
	private Vector3 _stockBack, _stockFront;
	private int _pelvis = -1, _neck = -1, _leftShoulder = -1, _rightShoulder = -1;

	public Vector3 Fit( SkinnedModelRenderer body, WorldModel gun, BotSupportHand support, BotSupportHand grip,
		Vector3 wrist, float supportWeight )
	{
		if ( !body.IsValid() || !body.SceneModel.IsValid() || !gun.IsValid() || !gun.ModelRenderer.IsValid() || gun.ModelRenderer.Model is null ) return Vector3.Zero;
		CacheStock( gun );
		if ( _bodyModel != body.Model ) CacheBody( body.Model );
		var hasTorso = Torso( body, out var torso, out var bounds );
		var back = gun.WorldTransform.PointToWorld( _stockBack );
		var front = gun.WorldTransform.PointToWorld( _stockFront );
		var target = gun.IkLeftHand;
		var shift = Vector3.Zero;
		for ( var i = 0; i < 8; i++ )
		{
			var previous = shift;
			if ( supportWeight > 0f && target.IsValid() && target.Active )
			{
				var left = target.WorldPosition + shift;
				shift += (support.Reachable( body, left ) - left) * supportWeight;
			}
			var right = wrist + shift;
			shift += grip.Reachable( body, right ) - right;
			if ( hasTorso )
				shift += Clearance( torso, bounds, back + shift, front + shift );
			if ( (shift - previous).LengthSquared < .000001f ) break;
		}
		return shift;
	}

	private void CacheStock( WorldModel gun )
	{
		var renderer = gun.ModelRenderer;
		if ( _gunModel == renderer.Model && _groups == renderer.BodyGroups ) return;
		_gunModel = renderer.Model;
		_groups = renderer.BodyGroups;
		var mins = new Vector3( float.MaxValue );
		var maxs = new Vector3( float.MinValue );
		var found = false;
		// The model's total bounds include every gunsmith stock, even those that are hidden.
		foreach ( var mesh in _gunModel.MeshInfo.Meshes )
		{
			if ( (mesh.MeshGroupMask & _groups) == 0 || !mesh.Name.Contains( "stock", StringComparison.OrdinalIgnoreCase ) ) continue;
			mins = Vector3.Min( mins, mesh.BoundsMin );
			maxs = Vector3.Max( maxs, mesh.BoundsMax );
			found = true;
		}
		if ( !found )
		{
			var bounds = _gunModel.Bounds;
			var bore = gun.Muzzle.IsValid() ? renderer.WorldTransform.PointToLocal( gun.Muzzle.WorldPosition ).z : bounds.Center.z;
			mins = new Vector3( bounds.Mins.x, 0f, bore - 1f );
			maxs = new Vector3( MathF.Min( 0f, bounds.Maxs.x ), 0f, bore + 1f );
		}
		var center = (mins + maxs) * .5f;
		var toGun = gun.WorldTransform.ToLocal( renderer.WorldTransform );
		_stockBack = toGun.PointToWorld( new Vector3( mins.x, center.y, center.z ) );
		_stockFront = toGun.PointToWorld( new Vector3( maxs.x, center.y, center.z ) );
	}

	private void CacheBody( Model model )
	{
		_bodyModel = model;
		int Bone( string human, string legacy ) => (model?.Bones.GetBone( human ) ?? model?.Bones.GetBone( legacy ))?.Index ?? -1;
		_pelvis = Bone( "pelvis", "pelvis" );
		_neck = Bone( "neck_0", "neck" );
		_leftShoulder = Bone( "arm_upper_L", "l_upperarm" );
		_rightShoulder = Bone( "arm_upper_R", "r_upperarm" );
	}

	private bool Torso( SkinnedModelRenderer body, out Transform frame, out BBox bounds )
	{
		frame = Transform.Zero;
		bounds = default;
		if ( _pelvis < 0 || _neck < 0 || _leftShoulder < 0 || _rightShoulder < 0 ) return false;
		var scene = body.SceneModel;
		var pelvis = scene.GetBoneWorldTransform( _pelvis ).Position;
		var neck = scene.GetBoneWorldTransform( _neck ).Position;
		var left = scene.GetBoneWorldTransform( _leftShoulder ).Position;
		var right = scene.GetBoneWorldTransform( _rightShoulder ).Position;
		var up = (neck - pelvis).Normal;
		var side = (left - right).Normal;
		var forward = side.Cross( up ).Normal;
		if ( forward.IsNearZeroLength || up.IsNearZeroLength ) return false;
		frame = new Transform( (pelvis + neck) * .5f, Rotation.LookAt( forward, up ) );
		var halfHeight = pelvis.Distance( neck ) * .5f;
		var halfWidth = left.Distance( right ) * .5f;
		// Include the plate carrier and the thickness of the stock, but leave the shoulder above the neck line free.
		bounds = new BBox( new Vector3( -6f, -halfWidth, -halfHeight ), new Vector3( 8f, halfWidth, halfHeight - 1f ) );
		return true;
	}

	private static Vector3 Clearance( Transform torso, BBox bounds, Vector3 back, Vector3 front )
	{
		var a = torso.PointToLocal( back );
		var b = torso.PointToLocal( front );
		var delta = b - a;
		var enter = 0f;
		var exit = 1f;
		for ( var axis = 0; axis < 3; axis++ )
		{
			if ( MathF.Abs( delta[axis] ) < .0001f )
			{
				if ( a[axis] <= bounds.Mins[axis] || a[axis] >= bounds.Maxs[axis] ) return Vector3.Zero;
				continue;
			}
			var t0 = (bounds.Mins[axis] - a[axis]) / delta[axis];
			var t1 = (bounds.Maxs[axis] - a[axis]) / delta[axis];
			enter = MathF.Max( enter, MathF.Min( t0, t1 ) );
			exit = MathF.Min( exit, MathF.Max( t0, t1 ) );
			if ( enter >= exit ) return Vector3.Zero;
		}
		// Slide towards the front or the nearest side of the torso; never resolve a collision by putting the gun behind it.
		var forward = bounds.Maxs.x - MathF.Min( a.x, b.x ) + .05f;
		var right = bounds.Mins.y - MathF.Max( a.y, b.y ) - .05f;
		var left = bounds.Maxs.y - MathF.Min( a.y, b.y ) + .05f;
		var sideways = MathF.Abs( right ) <= MathF.Abs( left ) ? right : left;
		var correction = forward <= MathF.Abs( sideways ) ? new Vector3( forward, 0f, 0f ) : new Vector3( 0f, sideways, 0f );
		return torso.Rotation * correction;
	}
}
