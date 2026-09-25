#!/usr/bin/env python3
"""Tile images into a labelled contact sheet: sheet.py out.png cols img1 img2 ..."""
import sys
from PIL import Image, ImageDraw
out, cols, paths = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(p).convert('RGB') for p in paths]
w = max(i.width for i in ims); h = max(i.height for i in ims) + 12
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (w * cols, h * rows), (40, 0, 40))
d = ImageDraw.Draw(sheet)
for k, (im, p) in enumerate(zip(ims, paths)):
    x, y = (k % cols) * w, (k // cols) * h
    sheet.paste(im, (x, y + 12)); d.text((x + 2, y), p.split('/')[-1], fill=(255, 255, 0))
sheet.save(out)
