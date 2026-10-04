#!/usr/bin/env python3
"""Write a Kastov viewmodel's animgraph (e.g. Assets/Weapons/Kastov/v_kastov.vanmgrph).

    root = hand IK(((state machine + ADS layer) + walk layer) + sway layer)

State machine: idle (start), sprint, lowered, deploy, fire, reload, reload_empty.
  - b_attack / b_deploy are one-shot triggers (auto-reset) taken from any state.
  - b_reload is held true by Reloadable for the whole reload, so the reload states leave as soon as it drops (the
    reload finished or was cancelled); b_empty picks the empty variant.
  - reload speed follows reload_speed, like the other HC1 viewmodels.
  - a gun with Weapon.reload_variants (the RPK) also has reload_variant (enum, set by ViewModel from the fitted
    magazine), which picks the reload and reload_empty clips: 0 the factory ones, then one per variant.
  - a gun with Weapon.ads_fire (the P90) fires with fire blended into fire_ads by ironsights_weight, as the QC's fire
    sequence blends them by the MW base's ADS fraction.
ADS layer: ironsights_weight (float, 0..1) blends zero_delta -> ads_delta. ViewModel moves it toward 0 or 1 over
  ViewModel.AimTime (Weapon.ads_time) and eases it, so letting go of aim halfway in turns the gun back from where it
  is. (A selector on the ironsights enum restarts its blend from the full old pose, so the gun snapped to the sights
  or the hip first.)
Walk layer: move_bob blends zero_delta -> walk_delta.
Sway layer: the M4's look sway (kastov_sway.py). Like v_m4a1's graph, it blends single-frame gun poses by
  aim_yaw_inertia / aim_pitch_inertia (ViewModel: how far the view turned since the last frame, and strafing) through
  the M4's springs: turn, roll, then vertical and sideways shift, added up. The poses are the M4's hip half already,
  and ironsights_weight cuts the sum to kastov_sway.ADS of it in ADS.
Hand IK: both arms solved onto their IK targets (bones on the gun that hold each hand's pose in every clip), the hands
  turned to match, as the M4's are. On a clip's own frames it changes nothing; it keeps the hands on the gun while
  the gun sways, in every state.

Run: python Tools/kastov_animgraph.py [--weapon kastov762|kastov74u|vityaz|rpk|bizon|ak105|vepr12|m16|p90|mp7|aug|uzi|fal|famas|m18|mcx]
"""

from __future__ import annotations

import zlib
from pathlib import Path

import animgraph_flags
import kastov_sway
import kastov_weapons
from kastov_weapons import Weapon

NONE = 4294967295

HEADER = ("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} "
          "format:animgraph2:version{0f7898b8-5471-45c4-9867-cd9c46bcfdb5} -->")


def uid(name: str) -> int:
    """Stable id for a node, state or parameter."""
    return zlib.crc32(f"kastov/{name}".encode()) & 0x7FFFFFFF


class Raw(str):
    """Written without quotes (enum-like identifiers are quoted in KV3 too, so this is only for special cases)."""


def kv3(value, depth: int = 0) -> str:
    pad = "\t" * depth
    inner = "\t" * (depth + 1)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(round(value, 6))
    if isinstance(value, str):
        return value if isinstance(value, Raw) else f'"{value}"'
    if isinstance(value, dict):
        lines = ["", pad + "{"]
        for key, item in value.items():
            lines.append(f"{inner}{key} = {kv3(item, depth + 1)}")
        lines.append(pad + "}")
        return "\n".join(lines)
    if isinstance(value, (list, tuple)):
        if not value:
            return "[  ]"
        if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value):
            return "[ " + ", ".join(kv3(float(item)) for item in value) + " ]"
        lines = ["", pad + "["]
        for item in value:
            text = kv3(item, depth + 1)
            if text.startswith("\n"):
                text = text[1:]
            else:
                text = inner + text
            lines.append(text + ",")
        lines.append(pad + "]")
        return "\n".join(lines)
    raise TypeError(type(value))


def ref(node_id: int) -> dict:
    return {"m_id": node_id}


def connection(node_id: int) -> dict:
    return {"m_nodeID": ref(node_id), "m_outputID": ref(NONE)}


BLEND_CURVE = {"m_vControlPoint1": [0.5, 0.0], "m_vControlPoint2": [0.5, 1.0]}
SPRING = {"_class": "CAnimInputDamping", "m_speedFunction": "Spring", "m_fSpeedScale": 50.0, "m_fMinSpeed": 0.0,
          "m_fMaxTension": 1000.0, "m_fTension": 100.0, "m_fDamping": 5.0}
NO_DAMPING = {"_class": "CAnimInputDamping", "m_speedFunction": "NoDamping", "m_fSpeedScale": 1.0, "m_fMinSpeed": 0.0,
              "m_fMaxTension": 1000.0, "m_fTension": 100.0, "m_fDamping": 5.0}


def bouncy_spring(speed: float, tension: float, damping: float) -> dict:
    """The M4's springs on its sway blends' inputs (kastov_sway's *_SPRING)."""
    return {"_class": "CAnimInputDamping", "m_speedFunction": "BouncySpring", "m_fSpeedScale": speed,
            "m_fMinSpeed": 0.0, "m_fMaxTension": 1000.0, "m_fTension": tension, "m_fDamping": damping}


class Graph:
    def __init__(self):
        self.nodes: list[dict] = []
        self.parameters: list[dict] = []
        self.param_ids: dict[str, int] = {}

    # --- parameters ---------------------------------------------------------------------------------------------

    def bool_param(self, name: str, auto_reset: bool = False) -> None:
        self.param_ids[name] = uid(f"param/{name}")
        self.parameters.append({
            "_class": "CBoolAnimParameter",
            "m_name": name,
            "m_id": ref(self.param_ids[name]),
            "m_previewButton": "ANIMPARAM_BUTTON_NONE",
            "m_bUseMostRecentValue": False,
            "m_bAutoReset": auto_reset,
            "m_bDefaultValue": False,
        })

    def float_param(self, name: str, default: float, low: float, high: float) -> None:
        self.param_ids[name] = uid(f"param/{name}")
        self.parameters.append({
            "_class": "CFloatAnimParameter",
            "m_name": name,
            "m_id": ref(self.param_ids[name]),
            "m_previewButton": "ANIMPARAM_BUTTON_NONE",
            "m_bUseMostRecentValue": False,
            "m_bAutoReset": False,
            "m_fDefaultValue": default,
            "m_fMinValue": low,
            "m_fMaxValue": high,
        })

    def enum_param(self, name: str, options: list[str]) -> None:
        self.param_ids[name] = uid(f"param/{name}")
        self.parameters.append({
            "_class": "CEnumAnimParameter",
            "m_name": name,
            "m_id": ref(self.param_ids[name]),
            "m_previewButton": "ANIMPARAM_BUTTON_NONE",
            "m_bUseMostRecentValue": False,
            "m_bAutoReset": False,
            "m_defaultValue": 0,
            "m_enumOptions": options,
        })

    # --- nodes --------------------------------------------------------------------------------------------------

    def _node(self, kind: str, key: str, position, **fields) -> int:
        node_id = uid(f"node/{key}")
        value = {"_class": kind, "m_sName": key, "m_vecPosition": list(position), "m_nNodeID": ref(node_id),
                 "m_sNote": ""}
        value.update(fields)
        self.nodes.append({"key": ref(node_id), "value": value})
        return node_id

    def root(self, source: int) -> int:
        node_id = uid("node/root")
        self.nodes.append({"key": ref(node_id), "value": {
            "_class": "CRootAnimNode", "m_sName": "Unnamed", "m_vecPosition": [512.0, 0.0],
            "m_nNodeID": ref(node_id), "m_sNote": "", "m_inputConnection": connection(source)}})
        return node_id

    def sequence(self, key: str, sequence: str, loop: bool, position) -> int:
        return self._node("CSequenceAnimNode", key, position, m_tagSpans=[], m_sequenceName=sequence,
                          m_playbackSpeed=1.0, m_bLoop=loop)

    def speed_scale(self, key: str, source: int, param: str, position) -> int:
        return self._node("CSpeedScaleAnimNode", key, position, m_inputConnection=connection(source),
                          m_param=ref(self.param_ids[param]))

    def add(self, key: str, base: int, additive: int, position) -> int:
        return self._node("CAddAnimNode", key, position, m_baseInput=connection(base),
                          m_additiveInput=connection(additive), m_timingBehavior="UseChild1", m_flTimingBlend=0.5,
                          m_footMotionTiming="Child1", m_bResetBase=False, m_bResetAdditive=False,
                          m_bApplyChannelsSeparately=True, m_bModelSpace=False)

    def enum_selector(self, key: str, children: list[int], param: str, blend: float, position) -> int:
        return self._selector(key, children, "SelectionSource_Enum", param, blend, position, sync=False)

    def bool_selector(self, key: str, when_false: int, when_true: int, param: str, blend: float, position,
                      sync: bool = False) -> int:
        """Picks a child by a bool parameter: the first while it's false, the second while it's true."""
        return self._selector(key, [when_false, when_true], "SelectionSource_Bool", param, blend, position, sync)

    def _selector(self, key: str, children: list[int], source: str, param: str, blend: float, position,
                  sync: bool) -> int:
        is_bool = source == "SelectionSource_Bool"
        return self._node("CSelectorAnimNode", key, position,
                          m_children=[connection(child) for child in children],
                          m_tags=[ref(NONE) for _ in children],
                          m_selectionSource=source,
                          m_boolParamID=ref(self.param_ids[param] if is_bool else NONE),
                          m_enumParamID=ref(NONE if is_bool else self.param_ids[param]),
                          m_intParamID=ref(NONE),
                          m_intParamMinValue=0,
                          m_intParamMaxValue=len(children) - 1,
                          m_blendDuration=blend,
                          m_tagBehavior="SelectorTagBehavior_OffWhenFinished",
                          m_bResetOnChange=False,
                          m_bSyncCyclesOnChange=sync,
                          m_blendCurve=BLEND_CURVE,
                          m_intParamNames=[])

    def blend(self, key: str, children: list[tuple[int, str, float]], param: str, position,
              damping: dict = SPRING, loop: bool = True) -> int:
        return self._node("CBlendAnimNode", key, position,
                          m_children=[{"m_inputConnection": connection(child), "m_name": name,
                                       "m_blendValue": value} for child, name, value in children],
                          m_blendValueSource="Parameter",
                          m_param=ref(self.param_ids[param]),
                          m_blendKeyType="BlendKey_UserValue",
                          m_bLockBlendOnReset=False,
                          m_bSyncCycles=True,
                          m_bLoop=loop,
                          m_bLockWhenWaning=False,
                          m_damping=dict(damping))

    def blend2d(self, key: str, items: list[tuple[str, tuple[float, float]]], param_x: str, param_y: str, position,
                damping: dict) -> int:
        """A 2D blend of sequences (name, (x, y)) by two float parameters."""
        return self._node("CBlend2DAnimNode", key, position,
                          m_items=[{"_class": "CBlend2DItem", "m_tagSpans": [], "m_sequenceName": sequence,
                                    "m_blendValue": [x, y]} for sequence, (x, y) in items],
                          m_blendSourceX="Parameter",
                          m_paramX=ref(self.param_ids[param_x]),
                          m_blendSourceY="Parameter",
                          m_paramY=ref(self.param_ids[param_y]),
                          m_bLoop=True,
                          m_bLockBlendOnReset=False,
                          m_bLockWhenWaning=True,
                          m_playbackSpeed=1.0,
                          m_damping=dict(damping))

    def two_bone_ik(self, key: str, source: int, chain: str, target_bone: str, position) -> int:
        """Solves an IK chain so its end bone sits on a bone and turns with it, as Facepunch's citizen graph puts its
        hands on their IK rule bones."""
        return self._node("CTwoBoneIKAnimNode", key, position,
                          m_inputConnection=connection(source),
                          m_ikChainName=chain,
                          m_endEffectorType="IkEndEffector_Bone",
                          m_endEffectorAttachmentName="",
                          m_targetType="IkTarget_Bone",
                          m_attachmentName="",
                          m_targetBoneName=target_bone,
                          m_targetParam=ref(NONE),
                          m_bMatchTargetOrientation=True,
                          m_rotationParam=ref(NONE))

    def state_machine(self, key: str, states: list[dict], position) -> int:
        return self._node("CStateMachineAnimNode", key, position, m_states=states, m_bBlockWaningTags=False,
                          m_bLockStateWhenWaning=False)

    # --- state machine pieces -----------------------------------------------------------------------------------

    def when(self, param: str, value: bool) -> dict:
        return {"_class": "CParameterAnimCondition", "m_comparisonOp": 0, "m_paramID": ref(self.param_ids[param]),
                "m_comparisonValue": {"m_nType": 1, "m_data": value}}

    @staticmethod
    def finished(almost: bool = False) -> dict:
        return {"_class": "CFinishedCondition", "m_comparisonOp": 0,
                "m_option": "FinishedConditionOption_OnAlmostFinished" if almost
                else "FinishedConditionOption_OnFinished",
                "m_bIsFinished": True}

    @staticmethod
    def transition(dest: str, conditions: list[dict], blend: float, reset: bool = True) -> dict:
        return {"_class": "CAnimStateTransition", "m_conditions": conditions, "m_blendDuration": blend,
                "m_destState": ref(uid(f"state/{dest}")), "m_bReset": reset, "m_resetCycleOption": "Beginning",
                "m_flFixedCycleValue": 0.0, "m_blendCurve": BLEND_CURVE, "m_bForceFootPlant": False,
                "m_bDisabled": False, "m_bRandomTimeBetween": False, "m_flRandomTimeStart": 0.0,
                "m_flRandomTimeEnd": 0.0}

    @staticmethod
    def state(name: str, source: int, transitions: list[dict], position, start: bool = False,
              any_state: bool = False) -> dict:
        return {"_class": "CAnimState", "m_transitions": transitions, "m_tags": [], "m_tagBehaviors": [],
                "m_name": name, "m_inputConnection": connection(source), "m_stateID": ref(uid(f"state/{name}")),
                "m_position": list(position), "m_bIsStartState": start, "m_bIsEndtState": False,
                "m_bIsPassthrough": False, "m_bIsRootMotionExclusive": False, "m_bAlwaysEvaluate": any_state}

    def write(self, path: Path, preview_model: str) -> None:
        document = {
            "_class": "CAnimationGraph",
            "m_nodeManager": {"_class": "CAnimNodeManager", "m_nodes": self.nodes},
            "m_pParameterList": {"_class": "CAnimParameterList", "m_Parameters": self.parameters},
            "m_pTagManager": {"_class": "CAnimTagManager", "m_tags": []},
            "m_pMovementManager": {"_class": "CAnimMovementManager",
                                   "m_MotorList": {"_class": "CAnimMotorList", "m_motors": []},
                                   "m_MovementSettings": {"_class": "CAnimMovementSettings",
                                                          "m_bShouldCalculateSlope": False}},
            "m_pSettingsManager": {"_class": "CAnimGraphSettingsManager", "m_settingsGroups": [
                {"_class": "CAnimGraphGeneralSettings", "m_iGridSnap": 16},
                {"_class": "CAnimGraphNetworkSettings"}]},
            "m_pActivityValuesList": {"_class": "CActivityValueList", "m_activities": []},
            "m_previewModels": [preview_model],
            "m_boneMergeModels": [],
            "m_cameraSettings": {"m_flFov": 60.0, "m_sLockBoneName": "camera", "m_bLockCamera": False,
                                 "m_bViewModelCamera": False},
        }
        text = f"{HEADER}\n{kv3(document).lstrip()}\n"
        if animgraph_flags.ENABLED:
            # The bool parameters as enums, while s&box can't set a bool true (see animgraph_flags).
            text, _ = animgraph_flags.convert_text(text, label=path.name)
        path.write_text(text, encoding="utf-8", newline="\n")


def build(weapon: Weapon) -> Graph:
    graph = Graph()
    for name in ("b_attack", "b_deploy"):
        graph.bool_param(name, auto_reset=True)
    for name in ("b_reload", "b_empty", "b_sprint", "b_lower_weapon"):
        graph.bool_param(name)
    graph.float_param("ironsights_weight", 0.0, 0.0, 1.0)
    graph.float_param("move_bob", 0.0, 0.0, 1.0)
    graph.float_param("reload_speed", 1.0, 0.0, 5.0)
    graph.float_param("aim_yaw_inertia", 0.0, -180.0, 180.0)
    graph.float_param("aim_pitch_inertia", 0.0, -180.0, 180.0)
    if weapon.reload_variants:
        graph.enum_param("reload_variant", ["factory"] + [suffix.lstrip("_") for suffix in weapon.reload_variants])

    def slide_lock(key: str, source: int, y: float) -> int:
        """With Weapon.slide_lock (a pistol's slide held back after the last round), the source with the slide lock
        added on while the magazine is empty (b_empty)."""
        if not weapon.slide_lock:
            return source
        # idle's first frame minus itself: no change.
        home = graph.sequence(f"{key}_slide_home", "slide_home", True, (-1024.0, y))
        locked = graph.sequence(f"{key}_slide_locked", "empty_delta", True, (-1024.0, y + 16.0))
        layer = graph.bool_selector(f"{key}_slide", home, locked, "b_empty", 0.0, (-832.0, y))
        return graph.add(f"{key}_with_slide", source, layer, (-736.0, y))

    idle = slide_lock("idle", graph.sequence("idle", "idle", True, (-640.0, -320.0)), -320.0)
    sprint = slide_lock("sprint", graph.sequence("sprint", "sprint", True, (-640.0, -256.0)), -256.0)
    lowered = slide_lock("lowered", graph.sequence("lowered", "lowered", True, (-640.0, -192.0)), -192.0)
    deploy = slide_lock("draw", graph.sequence("draw", "draw", False, (-640.0, -128.0)), -128.0)

    def fire_clip(suffix: str, y: float) -> int:
        if weapon.ads_fire:
            # The QC's fire sequence: the hip shot turning into the aimed one as the sights come up. It plays once, so
            # the fire state still finishes.
            hip_fire = graph.sequence(f"fire{suffix}", f"fire{suffix}", False, (-832.0, y - 16.0))
            aimed_fire = graph.sequence(f"fire_ads{suffix}", f"fire_ads{suffix}", False, (-832.0, y + 16.0))
            return graph.blend(f"fire_aim{suffix}", [(hip_fire, "hip", 0.0), (aimed_fire, "aimed", 1.0)],
                               "ironsights_weight", (-640.0, y), damping=NO_DAMPING, loop=False)
        return graph.sequence(f"fire{suffix}", f"fire{suffix}", False, (-640.0, y))

    fire = fire_clip("", -64.0)
    if weapon.slide_lock:
        # The last round (b_empty goes on with it): the same shot with the slide staying back. Synced, so a b_empty
        # that lands a frame after b_attack picks the empty clip up where the other one was.
        fire = graph.bool_selector("fire_last_round", fire, fire_clip("_empty", -32.0), "b_empty", 0.0,
                                   (-544.0, -64.0), sync=True)

    def reload_clip(clip: str, y: float) -> int:
        """The reload clip, or with reload variants a reload_variant selector over the factory clip and theirs."""
        factory = graph.sequence(clip, clip, False, (-832.0, y))
        if not weapon.reload_variants:
            return factory
        variants = [graph.sequence(f"{clip}{suffix}", f"{clip}{suffix}", False, (-1024.0, y + 16.0 * i))
                    for i, suffix in enumerate(weapon.reload_variants, 1)]
        return graph.enum_selector(f"{clip}_variant", [factory] + variants, "reload_variant", 0.0, (-736.0, y))

    reload = graph.speed_scale("reload_speed", reload_clip("reload", 0.0), "reload_speed", (-640.0, 0.0))
    reload_empty = graph.speed_scale("reload_empty_speed", reload_clip("reload_empty", 64.0), "reload_speed",
                                     (-640.0, 64.0))

    def to_reload() -> list[dict]:
        return [graph.transition("reload", [graph.when("b_reload", True), graph.when("b_empty", False)], 0.1),
                graph.transition("reload_empty", [graph.when("b_reload", True), graph.when("b_empty", True)], 0.1)]

    back_to_idle = [graph.when("b_sprint", False), graph.when("b_lower_weapon", False)]
    states = [
        graph.state("idle", idle, to_reload() + [
            graph.transition("sprint", [graph.when("b_sprint", True)], 0.25),
            graph.transition("lowered", [graph.when("b_lower_weapon", True)], 0.3),
        ], (-128.0, -160.0), start=True),
        graph.state("sprint", sprint, to_reload() + [
            graph.transition("idle", [graph.when("b_sprint", False)], 0.25),
        ], (128.0, -224.0)),
        graph.state("lowered", lowered, to_reload() + [
            graph.transition("idle", back_to_idle, 0.3),
            graph.transition("sprint", [graph.when("b_sprint", True)], 0.25),
        ], (128.0, -96.0)),
        graph.state("deploy", deploy, to_reload() + [
            graph.transition("idle", [graph.finished()], 0.2),
        ], (-384.0, 112.0)),
        graph.state("fire", fire, to_reload() + [
            graph.transition("idle", [graph.finished(almost=True)], 0.1),
        ], (-368.0, -128.0)),
        graph.state("reload", reload, [
            graph.transition("idle", [graph.when("b_reload", False)], 0.3),
            graph.transition("idle", [graph.finished()], 0.2),
        ], (-368.0, -240.0)),
        graph.state("reload_empty", reload_empty, [
            graph.transition("idle", [graph.when("b_reload", False)], 0.3),
            graph.transition("idle", [graph.finished()], 0.2),
        ], (-368.0, -352.0)),
        graph.state("Any", NONE, [
            graph.transition("fire", [graph.when("b_attack", True)], 0.0),
            graph.transition("deploy", [graph.when("b_deploy", True)], 0.0),
        ], (-640.0, -240.0), any_state=True),
    ]
    main = graph.state_machine("main", states, (-256.0, -160.0))

    zero_for_ads = graph.sequence("zero_ads", "zero_delta", True, (-256.0, 64.0))
    ads = graph.sequence("ads_delta", "ads_delta", True, (-256.0, 128.0))
    ads_layer = graph.blend("ironsights", [(zero_for_ads, "hip", 0.0), (ads, "aimed", 1.0)], "ironsights_weight",
                            (0.0, 96.0), damping=NO_DAMPING)
    with_ads = graph.add("add_ads", main, ads_layer, (128.0, -64.0))

    zero_for_walk = graph.sequence("zero_walk", "zero_delta", True, (-256.0, 256.0))
    walk = graph.sequence("walk_delta", "walk_delta", True, (-256.0, 320.0))
    walk_layer = graph.blend("move_bob", [(zero_for_walk, "still", 0.0), (walk, "walk", 1.0)], "move_bob",
                             (0.0, 288.0))
    with_walk = graph.add("add_walk", with_ads, walk_layer, (320.0, 0.0))
    with_sway = graph.add("add_sway", with_walk, sway_layer(graph), (320.0, 160.0))
    # Last, so the hands stay on the gun as it sways.
    hands = with_sway
    for index, (chain, _, target) in enumerate(kastov_sway.IK_CHAINS):
        hands = graph.two_bone_ik(f"ik_{chain}", hands, chain, target, (384.0 + 64.0 * index, 96.0))
    graph.root(hands)
    return graph


def sway_layer(graph: Graph) -> int:
    """The look sway (kastov_sway.py): v_m4a1's blends of its weapon_root poses on kastov_sway.REST, added up;
    ironsights_weight cuts the sum to kastov_sway.ADS of it in ADS."""
    x, y = -448.0, 448.0

    def sequence(key: str, name: str) -> int:
        nonlocal y
        y += 32.0
        return graph.sequence(key, name, True, (x, y))

    def along(key: str, poses: list[tuple[str, float]], param: str, spring: tuple[float, float, float]) -> int:
        """A 1D blend of poses by param, with no sway at 0."""
        children = [(sequence(f"{key}_rest", kastov_sway.REST), "center", 0.0)]
        for pose, value in poses:
            name = kastov_sway.sequence(pose)
            children.append((sequence(name, name), name, value))
        return graph.blend(key, sorted(children, key=lambda child: child[2]), param, (x + 192.0, y),
                           damping=bouncy_spring(*spring))

    items = [(kastov_sway.REST, (0.0, 0.0))] + [(kastov_sway.sequence(pose), value)
                                                for pose, value in kastov_sway.ORIENTATION]
    orientation = graph.blend2d("sway_orientation", items, "aim_yaw_inertia", "aim_pitch_inertia", (x + 192.0, y),
                                bouncy_spring(*kastov_sway.ORIENTATION_SPRING))
    chain = graph.add("add_sway_orientation", sequence("sway_base", kastov_sway.REST), orientation, (x + 384.0, y))
    for key, poses, param, spring in (
            ("sway_roll", kastov_sway.ROLL, "aim_yaw_inertia", kastov_sway.ROLL_SPRING),
            ("sway_vertical", kastov_sway.VERTICAL, "aim_pitch_inertia", kastov_sway.VERTICAL_SPRING),
            ("sway_horizontal", kastov_sway.HORIZONTAL, "aim_yaw_inertia", kastov_sway.HORIZONTAL_SPRING)):
        chain = graph.add(f"add_{key}", chain, along(key, poses, param, spring), (x + 384.0, y))
    aimed = sequence("sway_rest_aimed", kastov_sway.REST)
    # Blending toward no sway, placed past the parameter's end so ironsights_weight 1 keeps ADS of it.
    return graph.blend("sway_ads", [(chain, "hip", 0.0), (aimed, "aimed", 1.0 / (1.0 - kastov_sway.ADS))],
                       "ironsights_weight", (x + 576.0, y), damping=NO_DAMPING)


def main() -> None:
    weapon = kastov_weapons.from_command_line(__doc__)
    out = weapon.folder / f"v_{weapon.model}.vanmgrph"
    build(weapon).write(out, f"{weapon.asset}/v_{weapon.model}.vmdl")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
