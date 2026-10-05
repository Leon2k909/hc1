using System.Threading.Tasks;

public partial class DamageIndicator : Panel
{
	public static DamageIndicator Current;

	public DamageIndicator()
	{
		Current = this;
	}

	/// <summary>
	/// A hit from pos: where the damage came from, not where it struck (PlayerPawn.IndicatorSource).
	/// </summary>
	public void OnHit( Vector3 pos )
	{
		// Straight over or under the view (a grenade at your feet) there's no way round to point: a flat direction of
		// nothing read as dead ahead.
		var camera = Scene.Camera;
		if ( camera.IsValid() && pos.WithZ( 0 ).Distance( camera.WorldPosition.WithZ( 0 ) ) < 8f )
			return;

		var p = new HitPoint( pos );
		p.Parent = this;
	}

	public class HitPoint : Panel
	{
		public Vector3 Position;

		public HitPoint( Vector3 pos )
		{
			Position = pos;

			// Just the red end: drawing it as this panel's bottom border also drew hairline sides along its length.
			Add.Panel( "bar" );

			_ = Lifetime();
		}

		public override void Tick()
		{
			base.Tick();

			var wpos = Scene.Camera.WorldRotation.Inverse * (Position.WithZ( 0 ) - Scene.Camera.WorldPosition.WithZ( 0 )).Normal;
			wpos = wpos.WithZ( 0 ).Normal;

			var angle = MathF.Atan2( wpos.y, -1.0f * wpos.x );

			var pt = new PanelTransform();

			pt.AddTranslateX( Length.Percent( -50.0f ) );
			pt.AddTranslateY( Length.Percent( -0.0f ) );
			pt.AddRotation( 0, 0, angle.RadianToDegree() );

			Style.Transform = pt;

		}

		async Task Lifetime()
		{
			await Task.Delay( 1000 );
			AddClass( "dying" );
			await Task.Delay( 500 );
			Delete();
		}
	}
}
