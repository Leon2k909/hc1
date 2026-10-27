## Hotload: no lambdas in explicit IGameEventHandler<T> methods
- s&box's hotloader can't re-link static lambdas inside explicit generic interface methods
  (`void IGameEventHandler<T>.OnGameEvent`), so after any hotload they throw "Unable to find matching substitution for
  a static method" every time the event fires. Keep those methods lambda-free: forward to a named method
  (`=> DropOnKill( eventArgs );`, see `EquipmentDropper`), with any `[After<>/Before<>]` attributes left on the
  interface method.

