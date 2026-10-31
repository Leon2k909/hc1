# Paste renders into a sheet: python sheet.py <out.png> <columns> <cell width> <file[:label]> ...
import sys

from PIL import Image, ImageDraw, ImageFont

out, cols, cell = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
items = [a.rsplit("|", 1) if "|" in a else (a, "") for a in sys.argv[4:]]
ims = [Image.open(p).convert("RGB") for p, _ in items]
ims = [im.resize((cell, int(cell * im.height / im.width)), Image.LANCZOS) for im in ims]
h = ims[0].height
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell + (cols - 1) * 6, rows * h + (rows - 1) * 6), (18, 18, 18))
font = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", max(16, cell // 26))
draw = ImageDraw.Draw(sheet)
for i, (im, (_, label)) in enumerate(zip(ims, items)):
    x, y = (i % cols) * (cell + 6), (i // cols) * (h + 6)
    sheet.paste(im, (x, y))
    if label:
        draw.rectangle((x, y, x + 12 + draw.textlength(label, font=font), y + font.size + 12), fill=(0, 0, 0))
        draw.text((x + 6, y + 5), label, (238, 238, 238), font=font)
sheet.save(out)
print(out, sheet.size)
