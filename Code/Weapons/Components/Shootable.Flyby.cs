namespace Facepunch;

public partial class Shootable
{
	/// <summary> Where one of the last shot's rounds stopped, and whether it struck something there. </summary>
	private readonly struct Flyby
	{
		public readonly Vector3 End;
		public readonly bool Hit;

		public Flyby( Vector3 end, bool hit )
		{
			End = end;
			Hit = hit;
		}
	}

	/// <summary> Where the last shot's rounds left from. </summary>
	private Vector3 _flybyOrigin;

	/// <summary> The last shot's rounds, one per pellet, filled in by <see cref="GetShootTrace"/> and <see cref="Shoot"/>. </summary>
	private readonly List<Flyby> _flybys = new();

	/// <summary>
	/// Sends the last shot's rounds to every machine, so each hears them pass (<see cref="BulletFlyby"/>): a crack
	/// or a whizz for anyone but the shooter, and what they struck for anyone who didn't see it struck here.
	/// </summary>
	private void SendFlybys()
	{
		if ( _flybys.Count == 0 )
			return;

		// A shotgun's pellets pass within a millisecond or so of each other, so four of them carry the sound and keep the
		// message small.
		var count = Math.Min( _flybys.Count, 4 );
		var stream = ByteStream.Create( 16 + count * 16 );
		try
		{
			stream.Write( _flybyOrigin );
			stream.Write( (byte)count );
			for ( var i = 0; i < count; i++ )
			{
				stream.Write( _flybys[i].End );
				stream.Write( _flybys[i].Hit );
			}

			DoFlybyEffects( stream.ToArray() );
		}
		finally
		{
			stream.Dispose();
		}
	}

	[Rpc.Broadcast( NetFlags.Unreliable )]
	private void DoFlybyEffects( byte[] data )
	{
		if ( Application.IsDedicatedServer || !Equipment.IsValid() || data is null )
			return;

		// The shooter hears their own rounds strike where they fired them (CreateImpactEffects), and doesn't hear them pass.
		var own = Equipment.Owner?.IsViewer ?? false;
		var struckHere = !IsProxy;
		if ( own && struckHere )
			return;

		var stream = ByteStream.CreateReader( data );
		try
		{
			var origin = stream.Read<Vector3>();
			var count = stream.Read<byte>();
			for ( var i = 0; i < count; i++ )
			{
				var end = stream.Read<Vector3>();
				var hit = stream.Read<bool>();
				BulletFlyby.Pass( this, origin, end, flyby: !own, impact: hit && !struckHere, reflections: i == 0 );
			}
		}
		finally
		{
			stream.Dispose();
		}
	}

	/// <summary>
	/// How long after the shot its round's strike at <paramref name="point"/> is heard here: the round's flight, then the
	/// sound's way back.
	/// </summary>
	private float ImpactSoundDelay( Vector3 point ) =>
		BulletFlyby.TimeOfFlight( this, _flybyOrigin, point ) + GunshotAudio.SoundDelay( point );
}
