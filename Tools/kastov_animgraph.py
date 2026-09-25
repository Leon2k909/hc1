#!/usr/bin/env python3
"""Write a Kastov viewmodel's animgraph (e.g. Assets/Weapons/Kastov/v_kastov.vanmgrph).

    root = (state machine + ADS layer) + walk layer

State machine: idle (start), sprint, lowered, deploy, fire, reload, reload_empty.
  - b_attack / b_deploy are one-shot triggers (auto-reset) taken from any state.
  - b_reload is held true by Reloadable for the whole reload, so the reload states leave as soon as it drops (the
    reload finished or was cancelled); b_empty picks the empty variant.
  - reload speed follows reload_speed, like the other HC1 viewmodels.
  - a gun with Weapon.reload_variants (the RPK) also has reload_variant (enum, set by ViewModel from the fitted
    magazine), which picks the reload and reload_empty clips: 0 the factory ones, then one per variant.
ADS layer: ironsights (enum, set to 0/1 by ViewModel) selects zero_delta / ads_delta.
Walk layer: move_bob blends zero_delta -> walk_delta.

Run: python Tools/kastov_animgraph.py [--weapon kastov762|kastov74u|vityaz|rpk]
"""

from __future__ import annotations

import zlib
from pathlib import Path

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
        return self._node("CSelectorAnimNode", key, position,
                          m_children=[connection(child) for child in children],
                          m_tags=[ref(NONE) for _ in children],
                          m_selectionSource="SelectionSource_Enum",
                          m_boolParamID=ref(NONE),
                          m_enumParamID=ref(self.param_ids[param]),
                          m_intParamID=ref(NONE),
                          m_intParamMinValue=0,
                          m_intParamMaxValue=len(children) - 1,
                          m_blendDuration=blend,
                          m_tagBehavior="SelectorTagBehavior_OffWhenFinished",
                          m_bResetOnChange=False,
                          m_bSyncCyclesOnChange=False,
                          m_blendCurve=BLEND_CURVE,
                          m_intParamNames=[])

    def blend(self, key: str, children: list[tuple[int, str, float]], param: str, position) -> int:
        return self._node("CBlendAnimNode", key, position,
                          m_children=[{"m_inputConnection": connection(child), "m_name": name,
                                       "m_blendValue": value} for child, name, value in children],
                          m_blendValueSource="Parameter",
                          m_param=ref(self.param_ids[param]),
                          m_blendKeyType="BlendKey_UserValue",
                          m_bLockBlendOnReset=False,
                          m_bSyncCycles=True,
                          m_bLoop=True,
                          m_bLockWhenWaning=False,
                          m_damping={"_class": "CAnimInputDamping", "m_speedFunction": "Spring",
                                     "m_fSpeedScale": 50.0, "m_fMinSpeed": 0.0, "m_fMaxTension": 1000.0,
                                     "m_fTension": 100.0, "m_fDamping": 5.0})

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
        text = kv3(document)
        path.write_text(f"{HEADER}\n{text.lstrip()}\n", encoding="utf-8", newline="\n")


def build(weapon: Weapon) -> Graph:
    graph = Graph()
    for name in ("b_attack", "b_deploy"):
        graph.bool_param(name, auto_reset=True)
    for name in ("b_reload", "b_empty", "b_sprint", "b_lower_weapon"):
        graph.bool_param(name)
    graph.enum_param("ironsights", ["not_in_ironsights", "enabled"])
    graph.float_param("move_bob", 0.0, 0.0, 1.0)
    graph.float_param("reload_speed", 1.0, 0.0, 5.0)
    if weapon.reload_variants:
        graph.enum_param("reload_variant", ["factory"] + [suffix.lstrip("_") for suffix in weapon.reload_variants])

    idle = graph.sequence("idle", "idle", True, (-640.0, -320.0))
    sprint = graph.sequence("sprint", "sprint", True, (-640.0, -256.0))
    lowered = graph.sequence("lowered", "lowered", True, (-640.0, -192.0))
    deploy = graph.sequence("draw", "draw", False, (-640.0, -128.0))
    fire = graph.sequence("fire", "fire", False, (-640.0, -64.0))

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
    ads_layer = graph.enum_selector("ironsights", [zero_for_ads, ads], "ironsights", 0.25, (0.0, 96.0))
    with_ads = graph.add("add_ads", main, ads_layer, (128.0, -64.0))

    zero_for_walk = graph.sequence("zero_walk", "zero_delta", True, (-256.0, 256.0))
    walk = graph.sequence("walk_delta", "walk_delta", True, (-256.0, 320.0))
    walk_layer = graph.blend("move_bob", [(zero_for_walk, "still", 0.0), (walk, "walk", 1.0)], "move_bob",
                             (0.0, 288.0))
    with_walk = graph.add("add_walk", with_ads, walk_layer, (320.0, 0.0))
    graph.root(with_walk)
    return graph


def main() -> None:
    weapon = kastov_weapons.from_command_line(__doc__)
    out = weapon.folder / f"v_{weapon.model}.vanmgrph"
    build(weapon).write(out, f"{weapon.asset}/v_{weapon.model}.vmdl")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
