"""Stable daylight art direction shared by map generators and native editor updates.

Apply after a map restores its saved quality/lighting state. This edits existing
environment components only; it adds no runtime controller or per-frame work.
Baked maps retain their sun transform, direct light, GI and reflection resources.
"""
from copy import deepcopy
import math

PROFILES = {
    "Belltower": {
        "mood": "Warm afternoon",
        "components": {
            "SkyBox2D": {"Tint": "1.4,1.48,1.56,1"},
            "GradientFog": {"Color": "0.43,0.48,0.57,0.55"},
        },
    },
    "Boxyard": {
        "mood": "Clear midday",
        "sun_angles": (62.0, -15.0, 0.0),
        "components": {
            "DirectionalLight": {"LightColor": "1.5,1.44,1.34,1", "SkyColor": "0.46,0.50,0.56,1", "ShadowHardness": 0.25},
            "SkyBox2D": {"SkyMaterial": "materials/boxyard/sky/boxyard_midday.vmat", "Tint": "1,1,1,1"},
            "GradientFog": {"Color": "0.66,0.73,0.81,0.4", "StartDistance": 5000, "EndDistance": 60000},
            "ColorGrading": {"ColorTempK": 6500, "BlendFactor": 0.12},
            "Tonemapping": {"MinimumExposure": 2.0, "MaximumExposure": 3.0},
        },
    },
    "Cerro Blanco": {
        "mood": "Clear late morning",
        "components": {
            "SkyBox2D": {"Tint": "1.04,1.04,1.04,1"},
            "GradientFog": {"Color": "0.50,0.64,0.81,0.52", "StartDistance": 3800},
        },
    },
    "Lowtide": {
        "mood": "Soft coastal daylight",
        "components": {
            "SkyBox2D": {"Tint": "1.03,1.06,1.09,1"},
            "GradientFog": {"Color": "0.55,0.64,0.71,0.50", "StartDistance": 2800, "EndDistance": 38000},
        },
    },
    "Railhead": {
        # The station's clocks and sky are already authored for 14:03.
        "mood": "Early autumn afternoon",
        "components": {
            "GradientFog": {"Color": "0.63,0.70,0.81,0.75"},
        },
    },
    "Riverdale": {
        "mood": "Golden morning",
        "components": {
            "SkyBox2D": {"Tint": "1.08,1.08,1.08,1"},
            "GradientFog": {"Color": "0.96,0.84,0.72,0.58", "StartDistance": 3200},
        },
    },
    "Orion": {
        # Its static sky/wet reflection cubes retain the same sun and sky.
        "mood": "Bright golden hour",
        "components": {
            "DirectionalLight": {"SkyColor": "0.23,0.235,0.26,1"},
            # Broad full-strength AO hid detail along the tunnel stairs.
            "AmbientOcclusion": {"Intensity": 0.65, "Radius": 96},
            "GradientFog": {"Color": "0.61,0.59,0.57,0.62", "StartDistance": 2200},
        },
    },
    "Veridant": {
        "mood": "Soft golden evening",
        "components": {
            "DirectionalLight": {"SkyColor": "0.48,0.47,0.54,1"},
            "SkyBox2D": {"Tint": "1.52,1.52,1.52,1"},
            "GradientFog": {"Color": "0.78,0.73,0.70,0.56", "StartDistance": 3200},
        },
    },
    "Ares": {
        "mood": "Warm Martian light",
        "components": {
            "DirectionalLight": {"SkyColor": "0.24,0.18,0.14,1"},
            "SkyBox2D": {"Tint": "1.12,1.10,1.08,1"},
        },
    },
}


def components(scene):
    def visit(objects):
        for obj in objects:
            for component in obj.get("Components", []):
                yield obj, component
            yield from visit(obj.get("Children", []))
    yield from visit(scene.get("GameObjects", []))


def same_value(left, right):
    """Compare serialized colours/rotations and native resource references by value."""
    if isinstance(left, dict) and "Path" in left:
        left = left["Path"]
    if isinstance(right, dict) and "Path" in right:
        right = right["Path"]
    if left == right:
        return True
    if isinstance(left, str) and isinstance(right, str) and "," in left and "," in right:
        try:
            a, b = [float(v) for v in left.split(",")], [float(v) for v in right.split(",")]
            return len(a) == len(b) and all(math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-7) for x, y in zip(a, b))
        except ValueError:
            return False
    return False


def apply_profile(scene):
    """Apply a known map's profile in place, returning only the edited properties.

    Reapplying is idempotent. Unknown/specialist maps keep their authored lighting.
    Strict component counts prevent silently targeting the wrong light or volume.
    """
    title = scene.get("Title")
    profile = PROFILES.get(title)
    if profile is None:
        return []
    found = list(components(scene))
    pending = []
    for kind, properties in profile["components"].items():
        matches = [(obj, c) for obj, c in found if c.get("__type", "").split(".")[-1] == kind]
        if len(matches) != 1:
            raise ValueError(f"{title}: expected one {kind}, found {len(matches)}")
        obj, component = matches[0]
        for key, value in properties.items():
            if not same_value(component.get(key), value):
                pending.append((component, key, deepcopy(value)))
    if "sun_angles" in profile:
        if any(c.get("__type", "").endswith("IndirectLightVolume") for _, c in found):
            raise ValueError(f"{title}: rotating a baked sun requires a reviewed rebake")
        from map_kit import angles_rotation
        sun = next(obj for obj, c in found if c.get("__type", "").endswith("DirectionalLight"))
        rotation = angles_rotation(*profile["sun_angles"])
        if not same_value(sun.get("Rotation"), rotation):
            pending.append((sun, "Rotation", rotation))
    changes = []
    for owner, key, value in pending:
        changes.append({"id": owner.get("__guid"), "property": key, "before": owner.get(key), "after": value})
        owner[key] = value
    return changes

