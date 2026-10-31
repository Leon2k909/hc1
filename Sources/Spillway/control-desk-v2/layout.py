"""Where everything on the control desk's two instrument panels sits, shared by the build and the paint. Inches.

The slope panel's u runs along +Y from its left end as the operator sees it, v climbs the slope. The upright panel's u is the
same, its v climbs +Z. Five bays: three turbine units, the station bay in the middle and the spill gates.
"""
import math

PANEL_W = 112.0
BAYS = 5
BAY_W = PANEL_W / BAYS
SLOPE_LOW = (-2.0, 33.0)  # (x, z)
SLOPE_HIGH = (-19.0, 47.5)
SLOPE_L = math.hypot(SLOPE_HIGH[0] - SLOPE_LOW[0], SLOPE_HIGH[1] - SLOPE_LOW[1])
SLOPE_DIR = ((SLOPE_HIGH[0] - SLOPE_LOW[0]) / SLOPE_L, (SLOPE_HIGH[1] - SLOPE_LOW[1]) / SLOPE_L)
SLOPE_NORMAL = (SLOPE_DIR[1], -SLOPE_DIR[0])  # (x, z), facing the operator and up.
UPRIGHT_H = 10.0
UPRIGHT_X = -19.0
UPRIGHT_Z = 47.5

# Panel atlas: both panels at one density, upright above the slope.
PANEL_ATLAS = (4096, 1280)
PPI = PANEL_ATLAS[0] / PANEL_W
UPRIGHT_ROW = 16
SLOPE_ROW = UPRIGHT_ROW + int(UPRIGHT_H * PPI) + 16

BAY_TITLES = ["UNIT 1", "UNIT 2", "STATION CONTROL", "UNIT 3", "SPILL GATES"]
SWITCH_LABELS = [["GOV", "EXC", "GATE", "BRKR"], ["GOV", "EXC", "GATE", "BRKR"], [], ["GOV", "EXC", "GATE", "BRKR"], ["GATE 1", "GATE 2", "GATE 3", "GATE 4"]]
SWITCH_AT = [(6.0, 7.6), (16.4, 7.6), (6.0, 12.8), (16.4, 12.8)]
SWITCH_ANGLES = [-40, 0, 40, 40, -40, 0, 0, 40, 40, -40, 0, 0, 0, 0, 40, -40, -40, 40, 0, 0]
HMI = (5.0, 6.2, 17.4, 13.7)  # u0, v0, u1, v1 inside the station bay.
ESTOP = (11.2, 3.1)
LAMP_ROWS = (16.0, 17.9)
LAMPS_PER_ROW = 7
BUTTON_V = 2.9
BUTTONS = 6
# On or off, and which colour: a fixed pattern so all four desks read as one working board.
LAMP_PATTERN = "GgRgGaGG" "gGGrGGaG" "GGrGgGGa" "RGGgGGgr" "GaGgGrGG" "gGGGaGgR" "GrgGGGGa"


def bay_left(i):
    return i * BAY_W


def lamp_places(i):
    for r, v in enumerate(LAMP_ROWS):
        for k in range(LAMPS_PER_ROW):
            yield bay_left(i) + 2.8 + k * (BAY_W - 5.6) / (LAMPS_PER_ROW - 1), v, LAMP_PATTERN[(i * 9 + r * 5 + k) % len(LAMP_PATTERN)]


def button_places(i):
    for k in range(BUTTONS):
        if i == 2 and 1 < k < 4:
            continue  # The emergency stop has this space.
        yield bay_left(i) + 3.2 + k * (BAY_W - 6.4) / (BUTTONS - 1), BUTTON_V, k


# Round meters and the chart recorder on the upright panel.
METER_U = [5.5, 14.5, 23.5, 32.5, 41.5, 70.5, 79.5, 88.5, 97.5, 106.5]
METER_V = 5.0
METER_R = 3.75
METER_LABELS = ["MW", "MVAR", "KV", "HZ", "RPM", "M HEAD", "GATE %", "BRG C", "AMPS", "FLOW"]
METER_NEEDLES = [0.62, 0.35, 0.56, 0.5, 0.52, 0.71, 0.44, 0.38, 0.6, 0.66]
CHART = (47.5, 0.9, 64.5, 9.1)  # u0, v0, u1, v1

# Screens atlas: rows from the top, x, y, w, h in pixels.
SCREEN_ATLAS = (2048, 1280)
SCREENS = {"main": (0, 0, 1024, 600), "trend": (1024, 0, 1024, 600), "alarms": (0, 600, 1024, 600), "hmi": (1024, 600, 1024, 600)}
# Lamp swatches: letter to (centre x, centre y). Capital means lit.
SWATCH_Y = 1240
SWATCH_R = 34
SWATCHES = {"G": 40, "R": 120, "A": 200, "W": 280, "g": 360, "r": 440, "a": 520, "w": 600}

# The desk, as the build makes it.
DESK_X = (-35.0, 35.0)
DESK_Y = (-60.0, 60.0)
MUG_XY = (7.0, 49.0)
