"""
Builds the Red Team / Blue Team logos in Assets/ui/teams from the user's source art (transparent PNG/WebP).

    python Tools/team_logos.py Tools/team_logo_sources/red.webp Tools/team_logo_sources/blue.webp

For each team it writes <team>_team_logo.png (1024 square: scoreboard, win banner, minimap) and
<team>_team_logo_banner.png (1920x1080, the logo over a thin line: the spawn banner, PlayerRole). The old team art
(anarchists_*, operators_*) is left in place because the menus use operators_logo_banner.png as the game's brand logo.
"""
import os
import sys

import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), "..", "Assets", "ui", "teams")
COLORS = {"red": (228, 32, 40), "blue": (5, 146, 235)}  # TeamExtensions.GetColor


def trimmed(path):
    image = Image.open(path).convert("RGBA")
    alpha = np.array(image)[..., 3]
    ys, xs = np.where(alpha > 8)
    return image.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def fit(image, width, height, fill):
    """The logo scaled to fill `fill` of the canvas's height or width, centred."""
    scale = min(width * fill / image.width, height * fill / image.height)
    logo = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(logo, ((width - logo.width) // 2, (height - logo.height) // 2))
    return canvas


def line(width, height, color, thickness=6):
    """A team-coloured rule across the middle that fades out toward both edges, like the old banners' line."""
    x = np.linspace(-1.0, 1.0, width)
    fade = np.clip(1.0 - np.abs(x), 0.0, 1.0) ** 0.6
    rgba = np.zeros((height, width, 4), np.uint8)
    top = height // 2 - thickness // 2
    rgba[top:top + thickness, :, :3] = color
    rgba[top:top + thickness, :, 3] = (fade * 200).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def main(red, blue):
    for team, source in (("red", red), ("blue", blue)):
        logo = trimmed(source)
        fit(logo, 1024, 1024, 0.94).save(os.path.join(OUT, f"{team}_team_logo.png"))
        banner = line(1920, 1080, COLORS[team])
        banner.alpha_composite(fit(logo, 1920, 1080, 0.86))
        banner.save(os.path.join(OUT, f"{team}_team_logo_banner.png"))
        print(team, "logo from", source, logo.size)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
