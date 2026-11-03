namespace Facepunch;

public sealed class DecoyGrenade : BaseGrenade, ICustomMinimapIcon
{
	[RequireComponent] Rigidbody Rigidbody { get; set; }

	[Property, Group( "Balance" )] public float ChatterSpeed { get; set; } = 50f;
	[Property, Group( "Balance" )] RangedFloat ShotDelay { get; set; } = new( 0.5f, 1.0f );
	[Property, Group( "Effects" )] SoundEvent ShotSound { get; set; }
	[Property, Group( "Effects" )] GameObject Effect { get; set; }

	TimeUntil TimeUntilShot = 0;
	TimeSince TimeSinceShot = 1;

	string IMinimapIcon.IconPath => "ui/minimaps/enemy_icon.png";
	Vector3 IMinimapElement.WorldPosition => WorldPosition;
	// Looks like one of the thrower's team on the enemy's minimap (PlayerMarker's enemy tint).
	string ICustomMinimapIcon.CustomStyle => $"background-image-tint: {(Player.IsValid() ? Player.Team.GetColor() : Color.Red).Hex}";
	bool IMinimapElement.IsVisible( Pawn viewer ) => TimeSinceShot < 0.5f && IsEnemy;

	protected override void OnUpdate()
	{
		// The grenade's owner chooses one firing schedule for every listener.
		if ( !IsProxy && Rigidbody.IsValid() && Rigidbody.Velocity.Length < ChatterSpeed && TimeUntilShot )
		{
			TimeUntilShot = ShotDelay.GetValue();
			Fire();
		}

		base.OnUpdate();
	}

	[Rpc.Broadcast]
	void Fire()
	{
		if ( Rpc.Caller is not null && Rpc.Caller != Connection.Host && Rpc.Caller != Network.Owner ) return;

		TimeSinceShot = 0;

		if ( ShotSound is not null )
			Sound.Play( ShotSound, WorldPosition );

		Effect?.Clone( new CloneConfig()
		{
			Parent = GameObject,
			Transform = new Transform(),
			StartEnabled = true
		} );
	}
}
