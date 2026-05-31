from pathlib import Path
from django.core.management.base import BaseCommand

SIZES = (192, 512)
GREEN = (0, 166, 81, 255)
WHITE = (255, 255, 255, 255)


class Command(BaseCommand):
    help = 'Generate PWA icon PNGs (192×192 and 512×512) into booster/static/booster/icons/'

    def handle(self, *args, **options):
        from PIL import Image, ImageDraw

        out_dir = Path(__file__).resolve().parents[2] / 'static' / 'booster' / 'icons'
        out_dir.mkdir(parents=True, exist_ok=True)

        for size in SIZES:
            img = _make_icon(size)
            dest = out_dir / f'icon-{size}.png'
            img.save(dest, 'PNG')
            self.stdout.write(self.style.SUCCESS(f'  Wrote {dest}'))


def _make_icon(size):
    from PIL import Image, ImageDraw

    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── background: green rounded square ──────────────────────────────────
    draw.rounded_rectangle(
        [0, 0, size - 1, size - 1],
        radius=size // 6,
        fill=GREEN,
    )

    # ── white "J" drawn from three geometric primitives ───────────────────
    #
    # Proportions (all relative to `size` so both 192 and 512 look identical):
    #   t  – stroke thickness
    #   p  – padding from icon edge to the J bounding box
    #   L/R – left/right bounds of the J
    #
    t = round(size * 0.135)   # stroke width   (~26 px at 192, ~69 px at 512)
    p = round(size * 0.155)   # outer padding  (~30 px at 192, ~79 px at 512)
    L, R = p, size - p        # left / right inner edges

    # Arc bounding box for the bottom hook of the J
    # The arc is drawn from 0° (right-midpoint) → 180° (left-midpoint), i.e. the
    # lower half of the ellipse, which is the J curve.
    ax1, ax2 = L, R
    ay1 = round(size * 0.47)   # arc top  (~90 px at 192)
    ay2 = size - p             # arc bottom
    # y-coordinate of the 0°/180° endpoints = vertical midpoint of the arc bbox
    arc_mid_y = (ay1 + ay2) // 2

    # 1. Top horizontal bar
    draw.rectangle([L, p, R, p + t], fill=WHITE)

    # 2. Vertical stem — right side; extend 1 extra half-stroke into the arc
    #    zone so it visually connects with the arc's start point
    draw.rectangle([R - t, p, R, arc_mid_y + t // 2 + 1], fill=WHITE)

    # 3. Hook arc (0° → 180°)
    draw.arc([ax1, ay1, ax2, ay2], start=0, end=180, fill=WHITE, width=t)

    return img
