"""The zombies' walk, made from a person's gait instead of ported from a clip (zombie_anims.py writes it as walk_a).

None of No More Room in Hell's shambles walks like a person: they waddle, lurch, limp or hold the arms out, and the
one upright one (walk7) shuffles. Ported and IK'd to the Walkers' 70 u/s, walk7 still walked "a bit weird" (the user,
2026-10-01): its uneven source timing, and legs placed by IK on top of it, gave knees that snapped and feet that
glided. So the walk is built on the citizen's own skeleton over one stride, as a person walks at that pace:

  - The body stands upright, the arms hanging just clear of the sides with the elbows a little bent and the hands
    relaxed (`standing`). Over the stride the pelvis turns, lists and tilts, the chest turns against it, the head holds
    its gaze, and the arms swing opposite the legs, the elbows bending more as each arm swings forward (`upper_body`).
  - The legs follow a person's sagittal gait at a brisk pace (Winter's and Perry's angle curves, by share of the
    stride: STANCE_KNEE, HEEL_RISE, SWING_KNEE, SWING_THIGH). A foot lands heel first, rolls flat, lifts its heel about
    the ball and leaves over the toes, sliding back at exactly the walk's speed while it's down, so in the game it holds
    still on the ground (`Leg`).
  - The hips go as high as the legs on the ground let them (`hips`): each stance knee bends at least WALK.knee_min,
    wants its curve's bend and gives no more than WALK.give past it. That's a linear programme over the loop, which
    also keeps the hips' height smooth (its acceleration bounded, its jerk penalised), so they bob ~2" and the knee
    takes the weight with a little give after heel strike instead of snapping straight.
  - Late in the stance the trailing heel rises further than its curve when the knee needs it (`Leg.pitch_limits`): a
    push-off, which keeps that leg from holding the hips down.
  - The swing leaves the stance at its own rates and follows the knee's and thigh's curves to heel strike, the knee
    straightest just before the heel lands and the thigh swinging back into it (swing-leg retraction), so the foot
    comes down slowing (`make_swing`, `swing_q`). The foot clears the floor by WALK.clearance at mid-swing.

`python Tools/zombie_walk.py` prints the stride frame by frame: both knees, the left foot's pitch and height, and the
hips' height.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.interpolate import PchipInterpolator
from scipy.optimize import linprog

import zombie_anims as z

R = np.radians
UP, FWD, LEFT = np.array([0.0, 0.0, 1.0]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])


@dataclass(frozen=True)
class Walk:
    # The stride. 70 u/s is the Walkers' speed, so ZombieAI plays it at 1x; a cadence of ~138 steps a minute makes
    # 0.77 m steps, a person's brisk walk. The stride is rounded to whole frames (26).
    speed: float = 70.0
    cadence: float = 138.5
    fps: float = 30.0
    # Each foot is down this share of the stride (0.6 at an easy pace, less faster), and its ankle passes under the
    # hip this share of the way through its stance, so a foot lands less far ahead than it leaves behind.
    stance: float = 0.57
    mid: float = 0.40
    # The foot: toes up this far as the heel lands, flat by this share of the stance, then the heel rising (HEEL_RISE)
    # to this pitch as the toes leave. It rolls about the ball, the toes flat on the floor, up to `toe_bend`, then
    # over the toes' tips.
    heel_strike: float = 15.0
    flat: float = 0.15
    toe_off: float = 66.0
    toe_bend: float = 45.0
    # From `adapt_from` of the stance to `adapt_full`, the heel may come to `adapt_down` lower or `adapt_up` higher than
    # its curve (at most `pitch_max`), so the knee bends as far as its curve says.
    adapt_from: float = 0.65
    adapt_full: float = 0.8
    adapt_down: float = 10.0
    adapt_up: float = 25.0
    pitch_max: float = 75.0
    # The hips: each stance knee bends at least `knee_min`, wants its curve's bend (at `need_weight` times the cost of
    # an inch of sinking) and no more than `give` past it (`cap_weight`). Their height's acceleration stays within
    # `accel` (inches/s^2), and its jerk costs `jerk_weight`.
    knee_min: float = 5.0
    give: float = 4.0
    need_weight: float = 20.0
    cap_weight: float = 20.0
    accel: float = 450.0
    jerk_weight: float = 0.5
    # The swing: the knee bends up to `knee_peak` (SWING_KNEE's 61, scaled), the foot clears the floor by `clearance`
    # at mid-swing, and the ankle is dorsiflexed `dorsi` there. The swing leaves the stance at its rates, eased into
    # the curves over `rate_reach` of it.
    knee_peak: float = 60.0
    clearance: float = 0.4
    dorsi: float = 10.0
    rate_reach: float = 0.25
    # Feet: ankles this far apart, the toes turned out this many degrees; the heel's back is `heel` behind the ankle and
    # the toes reach `toes` past the ball.
    width: float = 6.0
    toe_out: float = 7.0
    heel: float = 1.5
    toes: float = 2.5
    # The pelvis (degrees, inches): turning with the swinging leg, dropping on its side, tilting with the steps,
    # shifting over the planted foot and surging forward and back.
    pel_yaw: float = 5.0
    pel_list: float = 4.0
    pel_tilt: float = 1.5
    shift: float = 0.8
    surge: float = 0.35
    # The chest turns against the pelvis and leans a little forward, the head turning back `head_yaw` of the way.
    chest_yaw: float = 3.5
    lean: float = 4.0
    chest_pitch: float = 1.0
    head_yaw: float = 0.25
    # The arms hang `arm_pitch` forward (negative: back), `arm_abd` out and turned `arm_rot`, and swing `arm_amp` each
    # way, `arm_lag` of a stride after the opposite leg, about an axis turned `arm_in` towards the body. The elbows bend
    # `elbow_mean`, `elbow_amp` more or less as the arm swings, and the clavicles follow `clav`.
    arm_pitch: float = -6.0
    arm_abd: float = 10.0
    arm_rot: float = 15.0
    arm_amp: float = 15.0
    arm_lag: float = 0.05
    arm_in: float = 12.0
    elbow_mean: float = 18.0
    elbow_amp: float = 10.0
    elbow_lag: float = 0.08
    clav: float = 2.5


WALK = Walk()

# A person's sagittal gait at a brisk pace (Winter; Perry), by share of the stride from heel strike (stance) or from
# toe-off (swing), in degrees.
# The knee through the stance: a little give as the weight comes on, nearly straight at mid-stance, bending fast in
# pre-swing.
STANCE_KNEE = PchipInterpolator([0, .05, .1, .15, .2, .3, .4, .45, .5, .55, .6],
                                [4, 9, 14, 16, 14, 8, 5, 5, 8.3, 16.7, 30])
# The foot's pitch as the heel rises: off the floor from ~38% of the stride, leaving it pitched ~60.
HEEL_RISE = PchipInterpolator([0, .38, .45, .5, .55, .6], [0, 0, 6, 18, 35, 60])
# The knee and the thigh's angle forward through the swing. The knee is straightest just before heel strike, and the
# thigh swings back into it (swing-leg retraction), so the foot comes down slowing, its heel first.
SWING_KNEE = PchipInterpolator([0, .125, .25, .3, .375, .5, .625, .75, .85, .93, 1],
                               [35, 49, 59, 61, 60, 54, 42, 25, 12, 4, 4.5])
SWING_THIGH = PchipInterpolator([0, .125, .25, .375, .5, .625, .75, .85, 1],
                                [-6, 2, 10, 17, 23, 27, 28.5, 28, 24])


def smooth(u: float) -> float:
    return u * u * (3 - 2 * u)


def hermite(w: float) -> tuple[float, float, float, float]:
    """The cubic Hermite basis: start value, start slope, end value, end slope."""
    return 2 * w**3 - 3 * w**2 + 1, w**3 - 2 * w**2 + w, -2 * w**3 + 3 * w**2, w**3 - w**2


def ease_rate(w: float, c: float) -> float:
    """A correction with slope 1 at w = 0 that's gone by w = c, so a rate matched at one end bends the path only near
    that end."""
    return w * (1 - w / c) ** 2 if w < c else 0.0


# ── The body ────────────────────────────────────────────────────────────────────

def subtrees(cit: z.Skeleton) -> dict[str, list[int]]:
    """Each bone with everything below it."""
    children = [[] for _ in cit.names]
    for i, p in enumerate(cit.parents):
        if p >= 0:
            children[p].append(i)
    out = {}
    for name, b in cit.index.items():
        sub, stack = [], [b]
        while stack:
            i = stack.pop()
            sub.append(i)
            stack.extend(children[i])
        out[name] = sub
    return out


def turn(world: list[np.ndarray], sub: list[int], pivot: np.ndarray, rot: np.ndarray) -> None:
    for i in sub:
        world[i][:3, :3] = rot @ world[i][:3, :3]
        world[i][:3, 3] = pivot + rot @ (world[i][:3, 3] - pivot)


def standing(cit: z.Skeleton, p: Walk) -> list[np.ndarray]:
    """The citizen's own upright trunk, shoulders and head, the arms hanging just clear of the body with the elbows a
    little bent, and relaxed hands."""
    ci = cit.index
    local = [m.copy() for m in cit.bind_local]
    world = z.world_of(cit.parents, local)
    relaxed = z.relaxed_hands(cit)
    for s in "LR":
        sign = 1.0 if s == "L" else -1.0
        upper, lower = ci[f"arm_upper_{s}"], ci[f"arm_lower_{s}"]
        chest = world[ci["spine_2"]][:3, :3] @ cit.bind_world[ci["spine_2"]][:3, :3].T
        # The upper arm's direction, and its elbow's hinge facing forward, turned `arm_rot` in.
        d = np.array([np.tan(R(p.arm_pitch)), sign * np.tan(R(p.arm_abd)), -1.0])
        d = chest @ (d / np.linalg.norm(d))
        f = chest @ np.array([1.0, -sign * np.tan(R(p.arm_rot)), 0.0])
        f -= np.dot(f, d) * d
        f /= np.linalg.norm(f)
        rest = cit.bind_world[upper][:3, :3]
        was = np.column_stack([rest[:, 0], rest[:, 2], np.cross(rest[:, 0], rest[:, 2])])
        now = np.column_stack([d, np.cross(d, f), np.cross(d, np.cross(d, f))])
        local[upper][:3, :3] = world[cit.parents[upper]][:3, :3].T @ now @ was.T @ rest
        # The elbow: from the rest pose's bend to `elbow_mean`, about its hinge (local Z).
        local[lower][:3, :3] = cit.bind_local[lower][:3, :3]
        posed = z.world_of(cit.parents, local)
        a = posed[lower][:3, 3] - posed[upper][:3, 3]
        b = posed[ci[f"hand_{s}"]][:3, 3] - posed[lower][:3, 3]
        bend = np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))
        local[lower][:3, :3] = local[lower][:3, :3] @ z.axis_rotation(np.array([0, 0, 1.0]), R(p.elbow_mean) - bend)
        for name in z.HAND_BONES:
            if name.endswith(s):
                local[ci[name]][:3, :3] = relaxed[name]
    return z.world_of(cit.parents, local)


def upper_body(cit: z.Skeleton, base: list[np.ndarray], p: Walk, n: int) -> list[list[np.ndarray]]:
    """The stride's n + 1 frames (the last is the first) with the pelvis, trunk, head and arms moving; the left foot
    lands on frame 0 and the right half way. The legs are left for the gait."""
    ci = cit.index
    sub = subtrees(cit)
    pelvis, chest = ci["pelvis"], ci["spine_2"]
    frames = []
    for t in range(n + 1):
        phase = (t % n) / n
        w = [m.copy() for m in base]
        cos = lambda k, lag=0.0: np.cos(2 * np.pi * (k * phase - lag))
        sin = lambda k, lag=0.0: np.sin(2 * np.pi * (k * phase - lag))
        shift = np.array([p.surge * sin(2), p.shift * sin(1, 0.05), 0.0])
        for i in sub["pelvis"]:
            w[i][:3, 3] += shift
        tilt = (z.axis_rotation(UP, -R(p.pel_yaw) * cos(1))
                @ z.axis_rotation(FWD, R(p.pel_list) * sin(1, -0.05))
                @ z.axis_rotation(LEFT, R(p.pel_tilt) * cos(2, 0.47)))
        turn(w, sub["pelvis"], w[pelvis][:3, 3].copy(), tilt)
        # The chest: turned against the pelvis and leaning, spread over the spine.
        target = (z.axis_rotation(UP, R(p.chest_yaw) * cos(1))
                  @ z.axis_rotation(LEFT, R(p.lean) + R(p.chest_pitch) * cos(2, 0.1))) @ base[chest][:3, :3]
        fix = z.rotation_vector(target @ w[chest][:3, :3].T)
        for b in z.SPINE:
            turn(w, sub[b], w[ci[b]][:3, 3].copy(), z.from_rotation_vector(fix / 3))
        # The head turns back towards where the walk's going, half of that in the neck.
        head, neck = ci["head"], ci["neck_0"]
        aim = z.axis_rotation(UP, R(p.chest_yaw * p.head_yaw) * cos(1)) @ base[head][:3, :3]
        fix = z.rotation_vector(aim @ w[head][:3, :3].T)
        turn(w, sub["neck_0"], w[neck][:3, 3].copy(), z.from_rotation_vector(fix / 2))
        fix = z.rotation_vector(aim @ w[head][:3, :3].T)
        turn(w, sub["head"], w[head][:3, 3].copy(), z.from_rotation_vector(fix))
        # The arms swing opposite the legs: the right forward as the left foot lands.
        for side, lag in (("R", 0.0), ("L", 0.5)):
            sign = 1.0 if side == "L" else -1.0
            moved = w[chest][:3, :3] @ base[chest][:3, :3].T
            lateral, vertical = moved @ LEFT, moved @ UP
            clavicle = ci[f"clavicle_{side}"]
            angle = R(p.clav) * cos(1, lag + p.arm_lag)
            turn(w, sub[f"clavicle_{side}"], w[clavicle][:3, 3].copy(), z.axis_rotation(vertical, -sign * angle))
            upper = ci[f"arm_upper_{side}"]
            swing = R(p.arm_amp) * cos(1, lag + p.arm_lag)
            axis = z.axis_rotation(vertical, -sign * R(p.arm_in)) @ lateral
            turn(w, sub[f"arm_upper_{side}"], w[upper][:3, 3].copy(), z.axis_rotation(axis, -swing))
            lower = ci[f"arm_lower_{side}"]
            flex = R(p.elbow_amp) * cos(1, lag + p.arm_lag + p.elbow_lag)
            hinge = w[lower][:3, :3] @ np.array([0, 0, 1.0])
            turn(w, sub[f"arm_lower_{side}"], w[lower][:3, 3].copy(), z.axis_rotation(hinge, flex))
        frames.append(w)
    return frames


# ── The legs ────────────────────────────────────────────────────────────────────

class Leg:
    """One leg's geometry and its foot's path over a loop of `period` frames, the foot landing on frame `down`."""

    def __init__(self, cit: z.Skeleton, s: str, p: Walk, period: int, down: float, hip_x: float, mid_y: float):
        ci = cit.index
        self.p = p
        sign = 1.0 if s == "L" else -1.0
        self.period, self.down = period, down
        self.stance = p.stance * period
        self.swing = period - self.stance
        self.v = p.speed / p.fps  # inches a frame
        ankle_b, ball_b = cit.bind_world[ci[f"ankle_{s}"]], cit.bind_world[ci[f"ball_{s}"]]
        toe = ball_b[:3, 3] - ankle_b[:3, 3]
        out = z.euler_matrix(0, 0, sign * R(p.toe_out) - np.arctan2(toe[1], toe[0]))
        self.foot, self.toes = out @ ankle_b[:3, :3], out @ ball_b[:3, :3]  # flat on the floor, turned out
        self.toes_on_foot = ankle_b[:3, :3].T @ ball_b[:3, :3]
        ahead = out @ np.array([toe[0], toe[1], 0.0])
        self.ahead = ahead / np.linalg.norm(ahead)
        self.axis = np.cross(UP, self.ahead)  # turning the foot about this tips its toes down
        height = float(ankle_b[2, 3])
        self.height = height
        # Points on the sole, from the ankle of a flat foot: the heel's back and under the ball.
        self.heel = -p.heel * self.ahead - height * UP
        self.ball = out @ toe
        self.ball[2] = -height
        self.land = hip_x + self.v * p.mid * self.stance
        self.y = mid_y + sign * p.width / 2
        self.thigh = float(np.linalg.norm(cit.bind_local[ci[f"leg_lower_{s}"]][:3, 3]))
        self.shin = float(np.linalg.norm(cit.bind_local[ci[f"ankle_{s}"]][:3, 3]))
        self.swing_path: dict = {}

    def phase(self, t: float) -> tuple[str, float]:
        d = (t - self.down) % self.period
        return ("stance", d / self.stance) if d < self.stance else ("swing", (d - self.stance) / self.swing)

    def reach(self, knee: float) -> float:
        """The hip-to-ankle distance with the knee bent this far."""
        return float(np.sqrt(self.thigh ** 2 + self.shin ** 2 + 2 * self.thigh * self.shin * np.cos(knee)))

    def pose(self, sigma: float, pitch: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The ankle, the foot's and the toes' rotations this far through the stance, the foot pitched toes down: about
        the heel (pitch < 0), about the ball with the toes flat on the floor up to `toe_bend`, then about the toes'
        tips. A planted foot slides back at the walk's speed."""
        flat = np.array([self.land - self.v * self.stance * sigma, self.y, self.height])
        if pitch < 0:
            r = z.axis_rotation(self.axis, pitch)
            return flat + self.heel - r @ self.heel, r @ self.foot, r @ self.foot @ self.toes_on_foot
        bend = R(self.p.toe_bend)
        r = z.axis_rotation(self.axis, min(pitch, bend))
        ankle, rot, toes = flat + self.ball - r @ self.ball, r @ self.foot, self.toes
        if pitch > bend:
            tip = flat + self.ball + self.p.toes * self.ahead
            r = z.axis_rotation(self.axis, pitch - bend)
            ankle, rot, toes = tip + r @ (ankle - tip), r @ rot, r @ toes
        return ankle, rot, toes

    def knee_target(self, sigma: float) -> float:
        return R(float(STANCE_KNEE(np.clip(sigma, 0, 1) * 0.6)))

    def profile(self, sigma: float) -> float:
        """The foot's pitch through the stance (toes down): the heel strike, flat, then the heel rising."""
        if sigma < self.p.flat:
            return -R(self.p.heel_strike) * (0.5 + 0.5 * np.cos(np.pi * sigma / self.p.flat))
        return R(float(HEEL_RISE(np.clip(sigma, 0, 1) * 0.6))) * self.p.toe_off / 60.0

    def pitch_limits(self, sigma: float) -> tuple[float, float]:
        """How far the foot's pitch may stray from its profile: not at all until `adapt_from`, then down to
        `adapt_down` lower and up to `adapt_up` higher (at most `pitch_max`) by `adapt_full`. The heel then rises as
        far as the knee's bend needs, as a push-off does."""
        p = self.p
        pitch = self.profile(sigma)
        if sigma <= p.adapt_from:
            return pitch, pitch
        u = smooth(min(1.0, (sigma - p.adapt_from) / (p.adapt_full - p.adapt_from)))
        lo = max(pitch - R(p.adapt_down) * u, min(pitch, 0.0))
        hi = max(pitch, min(pitch + R(p.adapt_up) * u, R(p.pitch_max)))
        return lo, hi

    def stance_pose(self, sigma: float, hip: np.ndarray | None = None):
        """The planted foot's (ankle, foot, toes, pitch), the pitch within its limits bending the knee its target."""
        pitch = self.profile(sigma)
        lo, hi = self.pitch_limits(sigma)
        if hip is not None and hi > lo:
            want = self.reach(self.knee_target(sigma))
            dist = lambda a: float(np.linalg.norm(self.pose(sigma, a)[0] - hip))
            if dist(lo) <= want:
                pitch = lo
            elif dist(hi) >= want:
                pitch = hi
            else:
                a, b = lo, hi
                for _ in range(40):
                    m = 0.5 * (a + b)
                    a, b = (m, b) if dist(m) > want else (a, m)
                pitch = 0.5 * (a + b)
        return self.pose(sigma, pitch) + (pitch,)

    def bound(self, sigma: float, hip: np.ndarray, knee: float, pitch: float) -> float:
        """The hips' drop that leaves this stance knee bent `knee`, the foot pitched `pitch`."""
        want = self.reach(knee)
        to = self.pose(sigma, pitch)[0] - hip
        return -float(to[2]) - float(np.sqrt(max(want * want - float(np.dot(to[:2], to[:2])), 0.0)))

    def need(self, sigma: float, hip: np.ndarray, knee: float | None = None) -> float:
        """The least drop that lets the knee bend this much (its target), the heel as high as it may go."""
        knee = self.knee_target(sigma) if knee is None else knee
        return self.bound(sigma, hip, knee, self.pitch_limits(sigma)[1])

    def cap(self, sigma: float, hip: np.ndarray) -> float:
        """The most drop that keeps the knee within `give` of its target, the heel as low as it may go."""
        return self.bound(sigma, hip, self.knee_target(sigma) + R(self.p.give), self.pitch_limits(sigma)[0])


def polar(leg: Leg, hip: np.ndarray, ankle: np.ndarray) -> np.ndarray:
    """(knee flexion, the thigh's angle forward of straight down, sideways offset) of the leg from `hip` to `ankle`."""
    d = ankle - hip
    dist = float(np.linalg.norm(d))
    a, b = leg.thigh, leg.shin
    knee = float(np.arccos(np.clip((dist ** 2 - a * a - b * b) / (2 * a * b), -1, 1)))
    line = float(np.arctan2(d[0], -d[2]))
    at_hip = float(np.arccos(np.clip((a * a + dist * dist - b * b) / (2 * a * dist), -1, 1)))
    return np.array([knee, line + at_hip, float(d[1])])


def from_polar(leg: Leg, hip: np.ndarray, q: np.ndarray) -> np.ndarray:
    knee, thigh, dy = q
    a, b = leg.thigh, leg.shin
    dist = leg.reach(knee)
    at_hip = float(np.arccos(np.clip((a * a + dist * dist - b * b) / (2 * a * dist), -1, 1)))
    line = thigh - at_hip
    rxz = float(np.sqrt(max(dist ** 2 - dy ** 2, 1e-9)))
    return hip + np.array([rxz * np.sin(line), dy, -rxz * np.cos(line)])


def shank_angle(q: np.ndarray) -> float:
    """The shank's angle forward of straight down."""
    return q[1] - q[0]


def lp_heights(n: int, p: Walk, hard, soft, caps) -> np.ndarray:
    """The hips' drop over a loop of n frames: as little as it can be, at least each `hard` (fractional frame, drop),
    its second difference within `accel` and its third difference costing `jerk_weight`. A `soft` (frame, drop,
    weight) wants at least that drop and a `cap` (frame, drop, weight) at most that; either can give, at `weight` times
    the cost of sinking. Each is on the drop interpolated linearly between frames."""
    m = len(soft) + len(caps)
    cols = n + m + n
    jerk = n + m
    rows, b = [], []

    def at(t: float, scale: float) -> np.ndarray:
        row = np.zeros(cols)
        i = int(np.floor(t)) % n
        f = t - np.floor(t)
        row[i] += scale * (1 - f)
        row[(i + 1) % n] += scale * f
        return row

    for t in range(n):
        row = np.zeros(cols)
        row[(t - 1) % n] += 1.0
        row[t] -= 2.0
        row[(t + 1) % n] += 1.0
        rows += [row, -row]
        b += [p.accel / p.fps ** 2] * 2
        # |third difference| <= the jerk variable, which costs: the hips' speed changes smoothly.
        row = np.zeros(cols)
        for k, c in zip(range(-1, 3), (-1.0, 3.0, -3.0, 1.0)):
            row[(t + k) % n] += c
        row[jerk + t] = -1.0
        rows.append(row)
        row = -row
        row[jerk + t] = -1.0
        rows.append(row)
        b += [0.0, 0.0]
    for t, v in hard:
        rows.append(at(t, -1.0))
        b.append(-v)
    cost = np.concatenate([np.ones(n), np.zeros(m), np.full(n, p.jerk_weight)])
    for j, (t, v, weight) in enumerate(soft):
        row = at(t, -1.0)
        row[n + j] = -1.0
        rows.append(row)
        b.append(-v)
        cost[n + j] = weight
    for j, (t, v, weight) in enumerate(caps):
        row = at(t, 1.0)
        row[n + len(soft) + j] = -1.0
        rows.append(row)
        b.append(v)
        cost[n + len(soft) + j] = weight
    res = linprog(cost, A_ub=sparse.csr_matrix(np.array(rows)), b_ub=np.array(b),
                  bounds=[(None, None)] * n + [(0, None)] * (m + n), method="highs")
    assert res.success, res.message
    return res.x[:n]


def hips(cit: z.Skeleton, frames: list[list[np.ndarray]], p: Walk):
    """The legs, each hip's place at any (fractional) frame, and how far the hips sink on each frame."""
    ci = cit.index
    n = len(frames) - 1
    pelvis = ci["pelvis"]
    hip_of = lambda w, s: (w[pelvis] @ np.linalg.inv(cit.bind_world[pelvis]) @ cit.bind_world[ci[f"leg_upper_{s}"]])[:3, 3]
    mid_y = float(np.mean([w[pelvis][1, 3] for w in frames[:n]]))
    legs = {s: Leg(cit, s, p, n, down, float(np.mean([hip_of(w, s)[0] for w in frames[:n]])), mid_y)
            for s, down in (("L", 0.0), ("R", n / 2))}
    hips0 = {s: np.array([hip_of(w, s) for w in frames[:n]]) for s in "LR"}

    def hip0(s: str, t: float) -> np.ndarray:
        t = t % n
        i = int(np.floor(t))
        f = t - i
        return (1 - f) * hips0[s][i] + f * hips0[s][(i + 1) % n]

    # As high as the stance legs let them be: each knee must bend `knee_min` (`hard`), wants its target (`soft`) and
    # no more than `give` past it (`caps`), sampled three times a frame.
    hard, soft, caps = [], [], []
    for s, leg in legs.items():
        steps = int(np.ceil(leg.stance * 3))
        for k in range(steps + 1):
            x = k / steps
            t = leg.down + x * leg.stance
            hip = hip0(s, t)
            hard.append((t % n, leg.need(x, hip, R(p.knee_min))))
            soft.append((t % n, leg.need(x, hip), p.need_weight))
            caps.append((t % n, leg.cap(x, hip), p.cap_weight))
    drop = lp_heights(n, p, hard, soft, caps)

    def hip_at(s: str, t: float) -> np.ndarray:
        h = hip0(s, t)
        t = t % n
        i = int(np.floor(t))
        f = t - i
        h[2] -= (1 - f) * drop[i] + f * drop[(i + 1) % n]
        return h

    return legs, hip_at, drop


def make_swing(leg: Leg, hip_at, p: Walk) -> None:
    """The swing from toe-off to heel strike, as the knee's bend, the thigh's angle and the ankle's sideways offset
    from the hip (`swing_q`). It leaves at the stance's rates and lands at the curves', with the knee straightening
    and the thigh swinging back: the stance's loading bend and the hips passing over the foot start at heel strike."""
    e = 0.02
    t_off, t_on = leg.down + leg.stance, leg.down + leg.period

    def state(sigma: float, t: float):
        hip = hip_at(t)
        pose = leg.stance_pose(sigma, hip)
        q = polar(leg, hip, pose[0])
        return q, pose[3] + shank_angle(q), pose

    q0, a0, off = state(1.0, t_off)
    before, _, _ = state(1.0 - e, t_off - e * leg.stance)
    q1, a1, _ = state(0.0, t_on)
    after, _, _ = state(e, t_on + e * leg.stance)
    scale = leg.swing / leg.stance
    sw = leg.swing_path
    # `a0`, `a1`: the ankle joint's angle as the toes leave and as the heel lands. `bent`: the toes on the foot as they
    # leave.
    sw.update(q0=q0, q1=q1, dq0=(q0 - before) / e * scale, dy1=(after[2] - q1[2]) / e * scale, a0=a0, a1=a1,
              bent=off[1].T @ off[2], bumps=[])
    # Where the foot comes nearer the floor than `clearance` (as the root of a sine over the swing), the knee bends 1
    # degree more round there, again until it doesn't.
    ws = np.linspace(0.0, 1.0, 81)[4:-4]
    for _ in range(20):
        worst, at = min((swing_pose(leg, u, hip_at(t_off + u * leg.swing))[3]
                         - p.clearance * np.sin(np.pi * u) ** 0.5, u) for u in ws)
        if worst >= -1e-3:
            break
        sw["bumps"].append((at, R(1.0)))
    sw["lowest"] = min(swing_pose(leg, u, hip_at(t_off + u * leg.swing))[3] for u in ws)


def swing_q(leg: Leg, w: float) -> np.ndarray:
    """The swing `w` of the way through: the knee and thigh follow their curves, offset to meet the stance at both
    ends and eased from the stance's rates at toe-off."""
    sw, p = leg.swing_path, leg.p
    h00, h10, h01, h11 = hermite(w)
    c = p.rate_reach
    scale = p.knee_peak / 61.0
    k0, k1, dk0 = (R(float(SWING_KNEE(*a))) * scale for a in ((0,), (1,), (0, 1)))
    knee = (R(float(SWING_KNEE(w))) * scale + (sw["q0"][0] - k0) * h00 + (sw["q1"][0] - k1) * h01
            + (sw["dq0"][0] - dk0) * ease_rate(w, c))
    for at, amp in sw["bumps"]:
        knee += amp * np.exp(-0.5 * ((w - at) / 0.12) ** 2) * np.sin(np.pi * w)
    th0, th1 = float(SWING_THIGH(0)), float(SWING_THIGH(1))
    span = sw["q1"][1] - sw["q0"][1]
    frac = (float(SWING_THIGH(w)) - th0) / (th1 - th0)
    f0 = float(SWING_THIGH(0, 1)) / (th1 - th0)
    thigh = sw["q0"][1] + span * frac + (sw["dq0"][1] - span * f0) * ease_rate(w, c)
    dy = sw["q0"][2] * h00 + sw["q1"][2] * h01 + sw["dq0"][2] * h10 + sw["dy1"] * h11
    return np.array([knee, thigh, dy])


def swing_pose(leg: Leg, w: float, hip: np.ndarray):
    """The swinging foot's (ankle, foot, toes, lowest point of the sole). The ankle joint goes from its plantarflexion
    at toe-off to `dorsi` of dorsiflexion at mid-swing, then to its angle at heel strike, still at both ends; the toes
    straighten over the first third."""
    sw, p = leg.swing_path, leg.p
    q = swing_q(leg, w)
    ankle = from_polar(leg, hip, q)
    if w < 0.5:
        h00, _, h01, _ = hermite(w / 0.5)
        joint = sw["a0"] * h00 - R(p.dorsi) * h01
    else:
        h00, _, h01, _ = hermite((w - 0.5) / 0.5)
        joint = -R(p.dorsi) * h00 + sw["a1"] * h01
    r = z.axis_rotation(leg.axis, joint - shank_angle(q))
    rot = r @ leg.foot
    toe_rot = rot @ z.slerp(sw["bent"], leg.toes_on_foot, smooth(min(1.0, w / 0.35)))
    tip = r @ leg.ball + p.toes * (toe_rot @ leg.toes.T @ leg.ahead)
    low = min(float((ankle + v)[2]) for v in (r @ leg.heel, r @ leg.ball, tip))
    return ankle, rot, toe_rot, low


# ── The walk ────────────────────────────────────────────────────────────────────

def walk(cit: z.Skeleton, p: Walk = WALK) -> tuple[list[list[np.ndarray]], dict]:
    """The stride's frames (bone world transforms, the last the first), walking in place at `p.speed` with the left
    foot landing on frame 0, and figures about it for the report."""
    ci = cit.index
    n = int(round(2 * 60.0 / p.cadence * p.fps))
    frames = upper_body(cit, standing(cit, p), p, n)
    legs, hip_at, drop = hips(cit, frames, p)
    for s, leg in legs.items():
        make_swing(leg, lambda t, s=s: hip_at(s, t), p)
    below_pelvis = subtrees(cit)["pelvis"]
    for t, world in enumerate(frames):
        for i in below_pelvis:
            world[i][2, 3] -= drop[t % n]
        for s, leg in legs.items():
            kind, x = leg.phase(t)
            ankle, foot, toes = (leg.stance_pose(x, hip_at(s, t)) if kind == "stance"
                                 else swing_pose(leg, x, hip_at(s, t)))[:3]
            z.plant_leg(world, cit, s, ankle, leg.ahead)
            world[ci[f"ankle_{s}"]][:3, :3] = foot
            world[ci[f"ball_{s}"]][:3, :3] = toes
        z.finish(cit, world)
    # Centre the hips' sway on the driver's origin.
    mean = np.mean([w[ci["pelvis"]][:3, 3] for w in frames[:-1]], axis=0) - cit.bind_world[ci["pelvis"]][:3, 3]
    for world in frames:
        for m in world:
            m[:2, 3] -= mean[:2]
    stats = dict(n=n, cadence=2 * 60.0 / (n / p.fps), drop=drop, swing_lowest=min(leg.swing_path["lowest"] for leg in legs.values()))
    return frames, stats


def report(cit: z.Skeleton, frames: list[list[np.ndarray]], stats: dict, p: Walk = WALK) -> None:
    ci = cit.index
    angle = lambda a, b: np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1)))
    step = p.speed * 60 / stats["cadence"]
    drop = stats["drop"]
    print(f"{stats['n']} frames a stride at {p.fps:g} fps: {stats['cadence']:.1f} steps a minute, {step:.1f} u "
          f"({step * 0.0254:.2f} m) a step at {p.speed:g} u/s")
    print(f"hips bob {np.ptp(drop):.2f} u; the swinging foot's lowest point {stats['swing_lowest']:.2f} u off the floor")
    print(" t  knee L knee R | L foot pitch  height | hips z")
    for t, w in enumerate(frames):
        at = lambda b: w[ci[b]][:3, 3]
        knees = [angle(at(f"leg_lower_{s}") - at(f"leg_upper_{s}"), at(f"ankle_{s}") - at(f"leg_lower_{s}")) for s in "LR"]
        foot = w[ci["ankle_L"]][:3, :3] @ cit.bind_world[ci["ankle_L"]][:3, :3].T
        pitch = np.degrees(np.arcsin(np.clip(-(foot @ FWD)[2], -1, 1)))
        print(f"{t:2d}  {knees[0]:6.1f} {knees[1]:6.1f} | {pitch:12.1f} {at('ankle_L')[2]:7.2f} | {at('pelvis')[2]:6.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--citizen-data", default=str(z.WORK / "zombie_work/citizen_human_male_data.txt"))
    args = parser.parse_args()
    cit = z.read_model_skeleton(Path(args.citizen_data))
    frames, stats = walk(cit)
    report(cit, frames, stats)


if __name__ == "__main__":
    main()
