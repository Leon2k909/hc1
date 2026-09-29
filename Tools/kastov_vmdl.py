#!/usr/bin/env python3
"""Write a Kastov's ModelDoc files (v_<model>.vmdl, w_<model>.vmdl) for the DMX files port_kastov.py exports.

The viewmodel's additive layers (ads_delta, walk_delta, zero_delta) are the full-pose clips minus idle's first
frame, which the animgraph adds on top of its state machine. So are the look sway's poses (kastov_sway.py), each a
single frame of sway.dmx. The viewmodel also gets the M4's arm IK chains, which the animgraph solves onto the hands'
IK targets.

Run: python Tools/kastov_vmdl.py [--weapon kastov762|kastov74u|vityaz|rpk|bizon|ak105|vepr12|m16|p90|mp7|aug|uzi|fal|m18]
"""

from __future__ import annotations

import kastov_sway
import kastov_weapons
from kastov_weapons import Weapon

HEADER = ("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} "
          "format:modeldoc30:version{8c2d7a91-9c42-4bf0-883a-5a3b1762d4f1} -->")

# name, source clip, looping, subtract (clip whose first frame is subtracted, making it additive)
ANIMATIONS = [
    ("idle", "idle", True, None),
    ("draw", "draw", False, None),
    ("fire", "fire", False, None),
    ("reload", "reload", False, None),
    ("reload_empty", "reload_empty", False, None),
    ("sprint", "sprint", True, None),
    ("lowered", "lowered", True, None),
    ("ads", "ads", True, None),
    ("walk", "walk", True, None),
    ("zero_delta", "idle", True, "idle"),
    ("ads_delta", "ads", True, "idle"),
    ("walk_delta", "walk", True, "idle"),
]
# The pieces port_kastov.py writes separately (Weapon.optional_meshes), each its own bodygroup: name -> shown by
# default. The gunsmith switches them per slot (GunsmithAttachmentPoint.FittedBodygroups in kastov_prefabs.py). A gun
# gets bodygroups only for the pieces it has. The AK-105's folding stock hinge gives way to the fixed wooden stocks.
# The M16's carry handle (with its rear sight) comes off under an optic, like the real flat-top's, and its bottom
# rail's cover under a grip. The P90's iron sights come off the top rail for an optic. The FAL's rear sight folds
# down under an optic (iron_sights off, sight_folded on).
BODY_GROUPS = {"muzzle_tip": True, "optic_rail": False, "grip_rail": False, "laser_rail": False, "stock_hinge": True,
               "carry_handle": True, "grip_cover": True, "iron_sights": True, "sight_folded": False,
               "stock_adapter": False,
               "factory_barrel": True, "factory_handguard": True, "factory_front_sight": True,
               "factory_stock": True, "factory_grip": True}
# name, bone
ATTACHMENTS = [("muzzle", "muzzle"), ("eject", "tag_brass")]


def indent(text: str, depth: int) -> str:
    return "\n".join("\t" * depth + line if line else line for line in text.splitlines())


def material_group(weapon: Weapon) -> str:
    remaps = "".join(
        "{\n"
        f'\tfrom = "{name}.vmat"\n'
        f'\tto = "{material}"\n'
        "},\n" for name, material in weapon.materials().items())
    return (
        "{\n"
        '\t_class = "MaterialGroupList"\n'
        "\tchildren = \n"
        "\t[\n"
        "\t\t{\n"
        '\t\t\t_class = "DefaultMaterialGroup"\n'
        "\t\t\tremaps = \n"
        "\t\t\t[\n"
        f"{indent(remaps, 4)}\n"
        "\t\t\t]\n"
        "\t\t\tuse_global_default = false\n"
        '\t\t\tglobal_default_material = ""\n'
        "\t\t},\n"
        "\t]\n"
        "},")


def render_meshes(meshes: list[tuple[str, str]]) -> str:
    items = "".join(
        "{\n"
        '\t_class = "RenderMeshFile"\n'
        f'\tname = "{name}"\n'
        f'\tfilename = "{filename}"\n'
        "\timport_translation = [ 0.0, 0.0, 0.0 ]\n"
        "\timport_rotation = [ 0.0, 0.0, 0.0 ]\n"
        "\timport_scale = 1.0\n"
        '\talign_origin_x_type = "None"\n'
        '\talign_origin_y_type = "None"\n'
        '\talign_origin_z_type = "None"\n'
        '\tparent_bone = ""\n'
        "\timport_filter = \n"
        "\t{\n"
        "\t\texclude_by_default = false\n"
        "\t\texception_list = [  ]\n"
        "\t}\n"
        "},\n" for name, filename in meshes)
    return list_node("RenderMeshList", [items.rstrip("\n")])


def body_group(name: str, choices: list[tuple[str, str]]) -> str:
    """A bodygroup whose choices each show one mesh ("" for none)."""
    body = "\n".join(
        "{\n"
        '\t_class = "BodyGroupChoice"\n'
        f'\tname = "{choice}"\n'
        "\tmeshes = \n"
        "\t[\n"
        f'\t\t"{member}",\n'
        "\t]\n"
        "}," for choice, member in choices)
    return (
        "{\n"
        '\t_class = "BodyGroup"\n'
        f'\tname = "{name}"\n'
        "\tchildren = \n"
        "\t[\n"
        f"{indent(body, 2)}\n"
        "\t]\n"
        "\thidden_in_tools = false\n"
        "},")


def body_groups(weapon: Weapon, prefix: str) -> str:
    """One bodygroup per optional piece, choice 0 being its default (see BODY_GROUPS), then one per part_choices
    group, choice 0 being the factory part."""
    groups = []
    for name, shown in BODY_GROUPS.items():
        if name not in weapon.optional_meshes:
            continue
        mesh = f"{prefix}_{name}"
        if name == "muzzle_tip":
            # Other barrels' tips go between on and off (Weapon.tip_choices).
            tips = [(tip, f"{mesh}_{tip}") for tip in weapon.tip_choices]
            groups.append(body_group(name, [("on", mesh), *tips, ("off", "")]))
        else:
            variants = [(choice, f"{mesh}_{choice}" if path else "") for choice, path, _ in weapon.optional_variants.get(name, [])]
            groups.append(body_group(name, [("on", mesh), *variants, ("off", "")] if shown
                                     else [("off", ""), ("on", mesh), *variants]))
    for group, choices in weapon.part_choices.items():
        groups.append(body_group(group, [(choice, f"{prefix}_{group}_{choice}") for choice, _ in choices]))
    return list_node("BodyGroupList", groups)


def mesh_files(weapon: Weapon, prefix: str) -> list[tuple[str, str]]:
    pieces = [name for name in BODY_GROUPS if name in weapon.optional_meshes]
    pieces += [f"muzzle_tip_{tip}" for tip in weapon.tip_choices]
    pieces += [f"{group}_{choice}" for group, choices in weapon.optional_variants.items() for choice, path, _ in choices if path]
    pieces += [f"{group}_{choice}" for group, choices in weapon.part_choices.items() for choice, _ in choices]
    return [(prefix, f"{weapon.asset}/models/{prefix}.dmx")] + [
        (f"{prefix}_{name}", f"{weapon.asset}/models/{prefix}_{name}.dmx") for name in pieces]


def anim_file(weapon: Weapon, name: str, clip: str, looping: bool, subtract: str | None,
              frame: int | None = None) -> str:
    """One AnimFile: the whole clip, or only its given frame."""
    children = ""
    if subtract is not None:
        children = (
            "\tchildren = \n"
            "\t[\n"
            "\t\t{\n"
            '\t\t\t_class = "AnimSubtract"\n'
            f'\t\t\tanim_name = "{subtract}"\n'
            "\t\t\tframe = 0\n"
            "\t\t},\n"
            "\t]\n")
    return (
        "{\n"
        '\t_class = "AnimFile"\n'
        f'\tname = "{name}"\n'
        f"{children}"
        '\tactivity_name = ""\n'
        "\tactivity_weight = 1\n"
        '\tweight_list_name = ""\n'
        "\tfade_in_time = 0.2\n"
        "\tfade_out_time = 0.2\n"
        f"\tlooping = {'true' if looping else 'false'}\n"
        "\tdelta = false\n"
        "\tworldSpace = false\n"
        "\thidden = false\n"
        "\tanim_markup_ordered = false\n"
        "\tdisable_compression = false\n"
        "\tdisable_interpolation = false\n"
        "\tenable_scale = false\n"
        f'\tsource_filename = "{weapon.asset}/models/anims/{clip}.dmx"\n'
        f"\tstart_frame = {-1 if frame is None else frame}\n"
        f"\tend_frame = {-1 if frame is None else frame}\n"
        "\tframerate = -1.0\n"
        "\ttake = 0\n"
        "\treverse = false\n"
        "},")


def attachment(name: str, bone: str) -> str:
    return (
        "{\n"
        '\t_class = "Attachment"\n'
        f'\tname = "{name}"\n'
        f'\tparent_bone = "{bone}"\n'
        "\trelative_origin = [ 0.0, 0.0, 0.0 ]\n"
        "\trelative_angles = [ 0.0, 0.0, 0.0 ]\n"
        "\tweight = 1.0\n"
        "\tignore_rotation = false\n"
        "},")


def ik_data() -> str:
    """kastov_sway.IK_CHAINS as ModelDoc IK chains, written as Facepunch's citizen_ikdata.vmdl_prefab writes them."""
    chains = []
    for name, (upper, lower, hand), target in kastov_sway.IK_CHAINS:
        chains.append(
            "{\n"
            '\t_class = "IKChain"\n'
            f'\tname = "{name}"\n'
            "\tchildren = \n"
            "\t[\n"
            "\t\t{\n"
            '\t\t\t_class = "IKChainJoint"\n'
            f'\t\t\tname = "{upper}"\n'
            "\t\t\tchildren = \n"
            "\t\t\t[\n"
            "\t\t\t\t{\n"
            '\t\t\t\t\t_class = "IKChainJoint"\n'
            f'\t\t\t\t\tname = "{lower}1"\n'
            "\t\t\t\t\tchildren = \n"
            "\t\t\t\t\t[\n"
            "\t\t\t\t\t\t{\n"
            '\t\t\t\t\t\t\t_class = "IKChainJoint"\n'
            f'\t\t\t\t\t\t\tname = "{hand}1"\n'
            f'\t\t\t\t\t\t\tbone = "{hand}"\n'
            "\t\t\t\t\t\t},\n"
            "\t\t\t\t\t]\n"
            f'\t\t\t\t\tbone = "{lower}"\n'
            "\t\t\t\t},\n"
            "\t\t\t]\n"
            f'\t\t\tbone = "{upper}"\n'
            "\t\t},\n"
            "\t]\n"
            "\tm_bDoBonesOrientAlongPositiveX = true\n"
            '\t"m_DefaultSolverSettings.m_nNumIterations" = 6\n'
            '\t"m_DefaultSolverSettings.m_SolverType" = "IKSOLVER_TwoBone"\n'
            '\t"m_DefaultTargetSettings.m_Bone" = \n'
            "\t{\n"
            f'\t\tm_Name = "{target}"\n'
            "\t}\n"
            '\t"m_DefaultTargetSettings.m_TargetSource" = "Bone"\n'
            '\t"m_Data.m_DefaultTargetSettings.m_AnimgraphParameterNamePosition" = \n'
            "\t{\n"
            "\t\tm_id = 4294967295\n"
            "\t}\n"
            '\t"m_Data.m_EndEffectorFixedOffsetAttachment" = \n'
            "\t{\n"
            '\t\tm_Name = ""\n'
            "\t}\n"
            '\t"m_Data.m_bParentJointRequiresAlignment" = true\n'
            "},")
    return list_node("IKData", chains)


def list_node(kind: str, items: list[str], extra: str = "") -> str:
    body = "\n".join(indent(item, 2) for item in items)
    return (
        "{\n"
        f'\t_class = "{kind}"\n'
        "\tchildren = \n"
        "\t[\n"
        f"{body}\n"
        "\t]\n"
        f"{extra}"
        "},")


def model(nodes: list[str], graph: str = "") -> str:
    body = "\n".join(indent(node, 3) for node in nodes)
    return (
        f"{HEADER}\n"
        "{\n"
        "\trootNode = \n"
        "\t{\n"
        '\t\t_class = "RootNode"\n'
        "\t\tchildren = \n"
        "\t\t[\n"
        f"{body}\n"
        "\t\t]\n"
        '\t\tmodel_archetype = ""\n'
        '\t\tprimary_associated_entity = ""\n'
        f'\t\tanim_graph_name = "{graph}"\n'
        '\t\tbase_model_name = ""\n'
        "\t}\n"
        "}\n")


def animations(weapon: Weapon) -> list[tuple]:
    """ANIMATIONS plus Weapon.ads_fire's fire_ads after fire (and Weapon.slide_lock's clips), the reloads of Weapon.reload_variants (the RPK's box
    magazines) after the factory reloads, and last the look sway's: sway.dmx's frame 0 as kastov_sway.REST, then a
    pose per frame, each minus idle's first frame (anim_file's frame)."""
    names = [name for name, *_ in ANIMATIONS]
    fire = [("fire_ads", "fire_ads", False, None)] if weapon.ads_fire else []
    if weapon.slide_lock:
        # The last round's fire clips, with the slide held back, and the slide lock on its own (empty minus idle's
        # first frame), which the animgraph adds on while b_empty is set.
        fire += [("fire_empty", "fire_empty", False, None)]
        fire += [("fire_ads_empty", "fire_ads_empty", False, None)] if weapon.ads_fire else []
        fire += [("empty_delta", "empty", True, "idle"), ("slide_home", "idle", True, "idle", 0)]
    variants = [(f"{clip}{suffix}", f"{clip}{suffix}", False, None)
                for suffix in weapon.reload_variants for clip in ("reload", "reload_empty")]
    after_fire, after_reloads = names.index("fire") + 1, names.index("reload_empty") + 1
    sway = [(kastov_sway.REST, "sway", True, "idle", 0)] + [
        (name, "sway", True, "idle", frame) for frame, (name, _, _) in enumerate(kastov_sway.poses(), 1)]
    return (ANIMATIONS[:after_fire] + fire + ANIMATIONS[after_fire:after_reloads] + variants
            + ANIMATIONS[after_reloads:] + sway)


def main() -> None:
    weapon = kastov_weapons.from_command_line(__doc__)
    assert set(weapon.optional_meshes) <= set(BODY_GROUPS), "every optional mesh needs a bodygroup"
    v_name, w_name = f"v_{weapon.model}", f"w_{weapon.model}"
    bone_markup = '{\n\t_class = "BoneMarkupList"\n\tbone_cull_type = "None"\n},'
    viewmodel = model([
        material_group(weapon),
        bone_markup,
        render_meshes(mesh_files(weapon, v_name)),
        body_groups(weapon, v_name),
        list_node("AnimationList", [anim_file(weapon, *animation) for animation in animations(weapon)],
                  '\tdefault_root_bone_name = ""\n'),
        list_node("AttachmentList", [attachment(*item) for item in ATTACHMENTS]),
        ik_data(),
    ], f"{weapon.asset}/{v_name}.vanmgrph")
    (weapon.folder / f"{v_name}.vmdl").write_text(viewmodel, encoding="utf-8", newline="\n")

    world = model([
        material_group(weapon),
        render_meshes(mesh_files(weapon, w_name)),
        body_groups(weapon, w_name),
    ])
    (weapon.folder / f"{w_name}.vmdl").write_text(world, encoding="utf-8", newline="\n")
    print(f"wrote {v_name}.vmdl, {w_name}.vmdl")


if __name__ == "__main__":
    main()
