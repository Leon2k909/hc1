"""Let immovable Lowtide scenery and local lights use engine static shadow caches.

Glass, water, wind-driven trees, gameplay objects and the weather-controlled sun
remain dynamic. Only explicitly named world meshes and authored local lamps are
marked; never mark the scene root or descendants indiscriminately.
"""

STATIC = 32768  # Native GameObjectFlags.Static, verified in s&box 26.10.13.
WORLD_MESHES = frozenset({
    "Fleet", "East", "West", "Dressing East", "Dressing West", "Backdrop",
    "Masonry Details", "Tidal Details", "Harbour Details",
})
LOCAL_LIGHT_TYPES = frozenset({"Sandbox.PointLight", "Sandbox.SpotLight"})


def targets(scene):
    roots = {o.get("Name"): o for o in scene["GameObjects"]}
    for obj in roots["Lowtide"].get("Children", []):
        if obj.get("Name") in WORLD_MESHES:
            yield obj
    for obj in roots["Lights"].get("Children", []):
        if any(c.get("__type") in LOCAL_LIGHT_TYPES for c in obj.get("Components", [])):
            yield obj


def apply_scene(scene):
    for obj in targets(scene):
        obj["Flags"] = obj.get("Flags", 0) | STATIC
