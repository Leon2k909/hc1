"""
Draws the Tactical Operator's portrait (Assets/ui/operators/tactical.png) from the Military Operator's, standard
library only.

    python Tools/operator_portraits.py

It's a stand-in until there's an in-engine capture like the other two portraits. Both outfits are the same army
garments on the same body (MilitaryUniform), so it recolours military.png:
  - every garment's pixels are dyed with MilitaryUniform.TacticalTint, multiplied in linear space as the engine does
    (the Field Operator's portrait matches its tints on military.png to within 2 sRGB steps), so keep TACTICAL in step
    with that table;
  - the head and neck go under a black balaclava, shaded like the skin it covers, with an eye slot behind the helmet's
    clear eye protection;
  - the backs of the hands get the fingerless gloves, the Field Operator's brown leather ones dyed black.
Pixels are sorted by where they are in the 512x640 picture and by colour (skin is redder than any of the kit).
"""
import os
import struct
import zlib

OPERATORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Assets", "ui", "operators")

# MilitaryUniform.TacticalTint
TACTICAL = {
    "helmet": (.27, .33, .51),
    "vest": (.24, .32, .54),
    "boots": (.14, .17, .27),
    "gloves": (.45, .62, .85),
    "camo": (.58, .64, 1.0),
}
GLOVES_UNDYED = (48, 36, 29)  # the Field Operator's gloves, which it doesn't tint
KNIT = (30, 30, 32)  # a black balaclava
EYE_SLOT = (233, 112, 283, 124)  # x0, y0, x1, y1: the eyes behind the helmet's eye protection
HEAD = (195, 325, 170)  # x0, x1 and the bottom: the helmet, its headset and the face
COLLAR = (235, 290, 140)  # x0, x1 and the top: the shirt's collar under the chin
GLOVE_ROWS = (326, 357)  # the backs of the hands, down to the knuckles
VEST = (205, 158, 312, 292)  # the plate carrier's box; the tan in it is the carrier, the green the shirt
BOOT_TOP = 525


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    pos, idat = 8, b""
    while pos < len(data):
        size, kind = struct.unpack(">I", data[pos:pos + 4])[0], data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + size]
        pos += 12 + size
        if kind == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and colour == 6 and interlace == 0, "expects 8-bit RGBA, not interlaced"
        elif kind == b"IDAT":
            idat += body
    raw, stride, rows, prev, i = zlib.decompress(idat), width * 4, [], bytearray(width * 4), 0
    for _ in range(height):
        kind, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - 4] if x >= 4 else 0
            b = prev[x]
            c = prev[x - 4] if x >= 4 else 0
            if kind == 1:
                line[x] = (line[x] + a) & 255
            elif kind == 2:
                line[x] = (line[x] + b) & 255
            elif kind == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return width, height, rows


def write_png(path, width, height, rows):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def linear(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def encode(value):
    value = min(max(value, 0.0), 1.0)
    c = value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
    return min(max(round(c * 255), 0), 255)


def dye(pixel, tint):
    return tuple(encode(linear(pixel[i]) * tint[i]) for i in range(3))


def luminance(pixel):
    return 0.2126 * linear(pixel[0]) + 0.7152 * linear(pixel[1]) + 0.0722 * linear(pixel[2])


def is_skin(pixel):
    r, g, b = pixel[:3]
    return r > 8 and (r - g) / r >= 0.2 and r >= b


def main():
    width, height, rows = read_png(os.path.join(OPERATORS, "military.png"))
    pixel = lambda x, y: tuple(rows[y][x * 4:x * 4 + 4])
    face = [pixel(x, y) for y in range(112, 145) for x in range(235, 285) if pixel(x, y)[3] > 250 and is_skin(pixel(x, y))]
    skin_mean = sum(map(luminance, face)) / len(face)
    gloves = dye(GLOVES_UNDYED, TACTICAL["gloves"])

    def over_skin(colour, p):
        """`colour` shaded like the skin pixel it covers."""
        k = min(max(luminance(p) / skin_mean, 0.25), 2.2)
        return tuple(encode(linear(colour[i]) * k) for i in range(3))

    out = []
    for y in range(height):
        row = bytearray(rows[y])
        for x in range(width):
            p = pixel(x, y)
            if p[3] == 0:
                continue
            skin = is_skin(p)
            if y < HEAD[2] and HEAD[0] <= x <= HEAD[1]:
                if skin:
                    in_slot = EYE_SLOT[0] <= x <= EYE_SLOT[2] and EYE_SLOT[1] <= y <= EYE_SLOT[3]
                    colour = p[:3] if in_slot else over_skin(KNIT, p)
                elif y >= COLLAR[2] and COLLAR[0] <= x <= COLLAR[1]:
                    colour = dye(p, TACTICAL["camo"])
                else:
                    colour = dye(p, TACTICAL["helmet"])
            elif skin:
                colour = over_skin(gloves, p) if GLOVE_ROWS[0] <= y <= GLOVE_ROWS[1] else p[:3]
            elif y >= BOOT_TOP:
                colour = dye(p, TACTICAL["boots"])
            elif VEST[0] <= x <= VEST[2] and VEST[1] <= y <= VEST[3] and (p[0] - p[1]) / max(p[0], 1) >= 0.08:
                colour = dye(p, TACTICAL["vest"])
            else:
                colour = dye(p, TACTICAL["camo"])
            row[x * 4:x * 4 + 3] = bytes(colour)
        out.append(row)

    path = os.path.join(OPERATORS, "tactical.png")
    write_png(path, width, height, out)
    print("wrote", os.path.normpath(path))


if __name__ == "__main__":
    main()
