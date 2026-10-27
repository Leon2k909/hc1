## Landing on slopes and stairs (`CharacterController.CategorizePosition`)
- The user (2026-10-19): "when i jump onto stairs i end up like levitating/gliding". Most maps' stairs collide as a slope
  (a wedge hull or an inclined deck under the steps). Landing on one while moving uphill, the controller's slide turns
  the fall into motion along the slope, which rises. The rule "rising faster than 40 u/s never lands" then kept the
  player airborne: no ground friction or stepping, held by air control at a steady float up the stairs (on a 32° ramp,
  44 u/s up and 70 along).
- Now rising only counts as leaving the ground if it's away from the surface touched (`Velocity · normal > 40`), which on
  level ground is the same test. For `JumpLandingGrace` (0.2 s) after a `Punch` (a jump) the old rule stands, so a jump
  straight into a steep slope still leaves it.
- `output/stairs-mantle/` has the trials (in an isolated editor scene, driving the real input and movement code):
  - `ramp-glide.cs.txt`: 23°, 32° and 40° stair ramps. Before, jumping onto the 32° and 40° ones at a sprint left the
    player airborne against them for 84-124 ticks (1.7-2.5 s); after, 0-11 (the grace).
  - `collider-stairs.cs.txt`: Collider's four flights on its own collision models (5 ticks to 0).
  - `stairs-mantle-checks.cs.txt`: stepped (per-step box) stairs and two real ledges. The mantle never starts on stairs
    and still does on the ledges. Its "on the 4th step" rows start the player inside a step; their airborne ticks are
    that, not a glide.
  - `Tools/SlideChecks/JumpLandingChecks.cs.txt` still passes (7287 checks, 189 simulations).
  - Not yet tried in a match.

