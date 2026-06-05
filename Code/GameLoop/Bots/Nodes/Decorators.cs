namespace Facepunch;

public abstract class DecoratorBaseNode : IBehaviorNode
{
	protected IBehaviorNode Child { get; }

	public string Name => GetType().Name.Replace("Node", "");

	protected DecoratorBaseNode(IBehaviorNode child)
	{
		Child = child ?? throw new ArgumentNullException(nameof(child));
	}

	// Subclasses implement tick-based evaluation
	public abstract NodeResult Evaluate(BotContext context);

	// Default reset propagates to child
	public virtual void Reset()
	{
		Child.Reset();
	}
}

public class RepeaterNode : DecoratorBaseNode
{
	private readonly int? _repeatCount;
	private int _currentCount;

	public RepeaterNode(IBehaviorNode child, int? repeatCount = null)
		: base(child)
	{
		_repeatCount = repeatCount;
		_currentCount = 0;
	}

	public override NodeResult Evaluate(BotContext context)
	{
		// If we've already reached the repeat count, return success
		if (_repeatCount.HasValue && _currentCount >= _repeatCount.Value)
		{
			_currentCount = 0;
			return NodeResult.Success;
		}

		var result = Child.Evaluate(context);

		switch (result)
		{
			case NodeResult.Running:
				return NodeResult.Running;

			case NodeResult.Failure:
				_currentCount = 0;
				return NodeResult.Failure;

			case NodeResult.Success:
				_currentCount++;
				Child.Reset(); // restart child for next repetition
				// If we hit the repeat count this frame, return success
				if (_repeatCount.HasValue && _currentCount >= _repeatCount.Value)
				{
					_currentCount = 0;
					return NodeResult.Success;
				}
				// Otherwise, still running — will continue next tick
				return NodeResult.Running;

			default:
				return NodeResult.Failure;
		}
	}

	public override void Reset()
	{
		_currentCount = 0;
		base.Reset();
	}
}

public class InverterNode : DecoratorBaseNode
{
	public InverterNode(IBehaviorNode child) : base(child) { }

	public override NodeResult Evaluate(BotContext context)
	{
		var result = Child.Evaluate(context);

		return result switch
		{
			NodeResult.Success => NodeResult.Failure,
			NodeResult.Failure => NodeResult.Success,
			NodeResult.Running => NodeResult.Running,
			_ => NodeResult.Failure
		};
	}
}

public class SucceederNode : DecoratorBaseNode
{
	public SucceederNode(IBehaviorNode child) : base(child) { }

	public override NodeResult Evaluate(BotContext context)
	{
		_ = Child.Evaluate(context); // ignore result
		return NodeResult.Success;
	}
}

public class FailerNode : DecoratorBaseNode
{
	public FailerNode(IBehaviorNode child) : base(child) { }

	public override NodeResult Evaluate(BotContext context)
	{
		_ = Child.Evaluate(context); // ignore result
		return NodeResult.Failure;
	}
}

public class ConditionalNode : DecoratorBaseNode
{
	private readonly Func<BotContext, bool> _condition;

	public ConditionalNode(IBehaviorNode child, Func<BotContext, bool> condition)
		: base(child)
	{
		_condition = condition ?? throw new ArgumentNullException(nameof(condition));
	}

	public override NodeResult Evaluate(BotContext context)
	{
		if (!_condition(context))
			return NodeResult.Failure;

		return Child.Evaluate(context);
	}
}
