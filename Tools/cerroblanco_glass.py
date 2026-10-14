"""Individual Museo panes using the game's existing networked BreakableGlass.

The aggregate mesh remains available for map previews and collision checks;
the scene uses only these independently breakable renderers and colliders.
"""
import hashlib
import json
import math
import uuid
from dataclasses import dataclass

import numpy as np
import map_kit as K

RESOURCE = "models/maps/cerroblanco/glass"
OUT = K.ASSETS / RESOURCE
PAINTS = {"cb_glass", "cb_glass_frit"}


def rotation(axes):
    """Convert basis to a quaternion directly, including horizontal panes at Euler gimbal lock."""
    m = np.column_stack([K.to_world(a) for a in axes])
    assert np.allclose(m.T @ m, np.eye(3), atol=1e-6) and np.linalg.det(m) > .999
    q = np.zeros(4)
    trace = np.trace(m)
    if trace > 0:
        s = math.sqrt(trace + 1) * 2
        q[:] = ((m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s,
                (m[1, 0] - m[0, 1]) / s, s / 4)
    else:
        i = int(np.argmax(np.diag(m)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = math.sqrt(1 + m[i, i] - m[j, j] - m[k, k]) * 2
        q[i], q[3] = s / 4, (m[k, j] - m[j, k]) / s
        q[j], q[k] = (m[j, i] + m[i, j]) / s, (m[k, i] + m[i, k]) / s
    return K.vec(q)


@dataclass
class Pane:
    centre: np.ndarray
    axes: tuple
    size: tuple
    paint: str
    shape: str = "box"

    @property
    def name(self):
        signature = json.dumps((self.shape, self.paint, [round(v, 6) for v in self.size]))
        return f"{self.paint}_{hashlib.sha256(signature.encode()).hexdigest()[:12]}"

    @property
    def path(self):
        return f"{RESOURCE}/{self.name}.vmdl"

    @property
    def rotation(self):
        return rotation(self.axes)


class GlassModel(K.Model):
    def __init__(self):
        super().__init__()
        self.panes = []
        self.guards = []

    def record(self, centre, axes, size, paint):
        # Put the thin dimension along local X; BreakableGlass emits over local Y/Z.
        axes = [K.normalise(a) for a in axes]
        thin = int(np.argmin(size))
        normal = axes[thin]
        if abs(normal[2]) > .99:
            across = axes[(thin + 1) % 3]
            up = np.cross(normal, across)
        else:
            up = np.array((0., 0., 1.))
            across = np.cross(up, normal)
        local_axes = (normal, across, up)
        dimensions = tuple(float(sum(abs(np.dot(a, b)) * s for b, s in zip(axes, size)))
                           for a in local_axes)
        self.panes.append(Pane(np.asarray(centre, float), local_axes, dimensions, paint))

    def box(self, lo, hi, paints, surface=None, skip=()):
        super().box(lo, hi, paints, surface, skip)
        if isinstance(paints, str) and paints in PAINTS:
            lo, hi = np.minimum(lo, hi).astype(float), np.maximum(lo, hi).astype(float)
            self.record((lo + hi) / 2, np.eye(3), hi - lo, paints)

    def oriented_box(self, centre, axes, size, paints, surface=None):
        super().oriented_box(centre, axes, size, paints, surface)
        if isinstance(paints, str) and paints in PAINTS:
            self.record(centre, axes, size, paints)

    def guard_clip(self, centre, axes, size):
        self.guards.append((np.asarray(centre, float), tuple(axes), tuple(size)))

    def add_roof_disc(self, centre, radius, z0, z1, paint="cb_glass"):
        super().cylinder(centre, radius, z0, z1, paint, sides=32, surface="glass")
        axes = (np.array((0., 0., 1.)), np.array((1., 0., 0.)), np.array((0., 1., 0.)))
        self.panes.append(Pane(np.array((*centre, (z0 + z1) / 2)), axes,
                               (z1 - z0, radius * 2, radius * 2), paint, "disc"))

    def guard_colliders(self):
        model = K.Model()
        for centre, axes, size in self.guards:
            model.oriented_box(centre, axes, size, None, "metal")
        return model

    def scene_group(self, ids):
        children = []
        for index, pane in enumerate(self.panes):
            key = f"world/cerroblanco_glass/pane/{index}"
            components = [
                K.component(ids, "Sandbox.ModelRenderer", key + "/renderer",
                            Model=pane.path, BodyGroups=18446744073709551615,
                            RenderType="Off", Tint="1,1,1,1"),
                K.component(ids, "Sandbox.ModelCollider" if pane.shape == "disc" else "Sandbox.BoxCollider",
                            key + "/collider", IsTrigger=False, Static=True,
                            **({"Model": pane.path} if pane.shape == "disc" else
                               {"Center": "0,0,0", "Scale": K.vec(pane.size), "Surface": "surfaces/glass.surface"})),
                K.component(ids, "Facepunch.BreakableGlass", key + "/glass",
                            IntactModel=pane.path, BrokenModels=[], PaneSize=K.vec(pane.size[1:]),
                            ShardDensity=14, BreakSound="sounds/buildings/glass_break.sound",
                            ShardEffect={"_type": "gameobject", "prefab": "prefabs/buildings/glass_shatter.prefab"}),
            ]
            children.append(K.game_object(ids, f"Museum Glass Pane {index + 1}", key,
                            K.to_world(pane.centre), rotation=pane.rotation,
                            components=components, tags="glass,navskip"))
        # Keep safety rails blocking players and navmesh, but let bullets and grenades pass.
        for index, (centre, axes, size) in enumerate(self.guards):
            key = f"world/cerroblanco_glass/guard/{index}"
            orientation = rotation(axes)
            children.append(K.game_object(ids, f"Balustrade Player Clip {index + 1}", key,
                K.to_world(centre), rotation=orientation, tags="playerclip", components=[
                    K.component(ids, "Sandbox.BoxCollider", key + "/collider", Center="0,0,0",
                                Scale=K.vec(size), Static=True, IsTrigger=False)]))
        return K.game_object(ids, "Breakable Glass", "world/cerroblanco_glass", children=children)

    def write_models(self):
        unique = {pane.name: pane for pane in self.panes}
        for name, pane in unique.items():
            model = pane_model(pane)
            K.write_model(OUT, RESOURCE, name, model)
            for suffix in (".obj", ".vmdl"):
                path = OUT / f"{name}{suffix}"
                meta = path.with_name(path.name + ".meta")
                if not meta.exists():
                    K.write_text(meta, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL,
                        "hc1/cerroblanco/glass/" + path.name))}, indent=2) + "\n")
        print(f"Museo: {len(self.panes)} breakable panes, {len(unique)} reusable meshes, {len(self.guards)} safety rails")


def pane_model(pane):
    model = K.Model()
    thickness, width, height = pane.size
    if pane.shape == "box":
        # Plan (e,n,z) becomes local world (n,-e,z).
        model.box((-width / 2, -thickness / 2, -height / 2),
                  (width / 2, thickness / 2, height / 2), pane.paint)
    else:
        rings = [[np.array((-width / 2 * math.cos(t), x, height / 2 * math.sin(t)))
                  for t in np.linspace(0, math.tau, 32, endpoint=False)]
                 for x in (-thickness / 2, thickness / 2)]
        for ring, normal in zip(rings, ((0, -1, 0), (0, 1, 0))):
            points = ring[::-1] if normal[1] < 0 else ring
            model.polygon(pane.paint, points, normal=normal)
        for i in range(32):
            j = (i + 1) % 32
            points = [rings[0][i], rings[0][j], rings[1][j], rings[1][i]]
            centre = np.mean(points, axis=0)
            if np.dot(np.cross(points[1] - points[0], points[2] - points[0]), centre) < 0:
                points.reverse()
            model.polygon(pane.paint, points)
        model.hull(rings[0] + rings[1], "glass")
    model.material_overrides[pane.paint] = f"materials/cerroblanco/{pane.paint}.vmat"
    model.tile_overrides[pane.paint] = 64
    return model


def build_glazing():
    import cerroblanco_map as M
    buildings, glazing, dressing, canopy = K.Model(), GlassModel(), K.Model(), K.Model()
    M.west_gallery(buildings, glazing, dressing)
    M.rotunda(buildings, glazing, dressing)
    M.east_block(buildings, glazing, dressing)
    M.south_gallery(buildings, glazing, dressing, canopy)
    return glazing, buildings


def install():
    """Update only glazing, its safety clips and the affected roof cap; preserve all scene settings."""
    import cerroblanco_map as M
    glazing, buildings = build_glazing()
    glazing.write_models()
    # Remove the old decorative roof glazing from the building mesh, retaining its frame.
    M.configure(buildings)
    K.write_model(M.OUT_DIR, M.RESOURCE_DIR, "cerroblanco_buildings", buildings)
    scene = json.loads(M.SCENE_FILE.read_text(encoding="utf-8-sig"))
    world = next(obj for obj in scene["GameObjects"] if obj["__guid"] == M.ids("world"))
    old_id = M.ids("world/cerroblanco_glass")
    world["Children"] = [glazing.scene_group(M.ids) if obj["__guid"] == old_id else obj
                         for obj in world["Children"]]
    assert sum(obj["__guid"] == old_id for obj in world["Children"]) == 1
    K.write_text(M.SCENE_FILE, json.dumps(scene, indent=2), newline=None)


if __name__ == "__main__":
    install()
