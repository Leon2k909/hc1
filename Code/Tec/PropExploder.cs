namespace Tec;

public class PropExploder : Component
{
	[Property] public float DamageMultiplier { get; set; } = 3f;

	private GameObject _lastValidAttacker;
	
	[RequireComponent]
	public Exploder Exploder
	{
		get
		{
			field ??= GetComponent<Exploder>();
			return field;
		}
	}
	
	public Prop Prop
	{
		get
		{
			field ??= GetComponent<Prop>();
			return field;
		}
	}
	
	protected override void OnStart()
	{
		Prop.OnPropBreak += Explode;
	}

	protected override void OnFixedUpdate()
	{
		if ( Prop.LastAttacker != null ) _lastValidAttacker = Prop.LastAttacker;
	}

	private void Explode()
	{
		// Log.Info("EXPLODEEEEEEEEEEEEEE"  );
		// Log.Info( $"Log lastvalidattacker -------------------> {_lastValidAttacker}" );
		
		Exploder.Explode( WorldPosition, Prop.Model.Data.ExplosionRadius, Prop.Model.Data.ExplosionDamage * DamageMultiplier, _lastValidAttacker.GetComponent<Component>(), this, Exploder.DamageFalloff );
	}
}
