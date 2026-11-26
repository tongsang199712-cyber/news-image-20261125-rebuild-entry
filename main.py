#!/usr/bin/env python3
"""news-image-20261125-rebuild: draw a one-page newspaper front page that sums
up the world news of Wednesday 25 November 2026, using only the Python
standard library (no network, no third-party packages, no system fonts).

The program renders everything itself into an RGB pixel buffer -- masthead,
headlines, body text (from an embedded 5x7 bitmap font drawn at several
scales) and flat vector-style illustrations -- and writes a deterministic
PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png for local runs).
Two runs produce byte-identical output: no time, no randomness, no
environment-dependent data anywhere in the render.
"""

import os
import struct
import zlib
from binascii import crc32

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- palette ---
PAPER = (247, 243, 232)      # newsprint off-white
INK = (18, 18, 18)           # near-black ink
NAVY = (16, 42, 92)          # masthead band
NAVY_LIGHT = (32, 68, 140)
RED = (178, 34, 34)          # kicker / accent red
GOLD = (201, 162, 39)
SEA = (23, 92, 142)
SEA_DARK = (13, 62, 102)
SEA_LIGHT = (126, 180, 214)
SKY = (178, 214, 235)
SAND = (226, 205, 158)
GREEN = (34, 139, 34)
DARK_GREEN = (118, 185, 0)   # Nvidia green
ORANGE = (232, 116, 0)
FLAME = (245, 176, 0)
GREY = (110, 110, 110)
LIGHT_GREY = (220, 220, 220)
WHITE = (255, 255, 255)
BROWN = (120, 72, 20)

OUT_NAME = "entry.png"


# ------------------------------------------------------------- bitmap font --
# Each glyph is 7 rows of 5 pixels, "#" = ink, "." = empty. Uppercase
# letters, digits and the punctuation this page needs, hand-drawn here.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
}

CHAR_W = 5
CHAR_H = 7


def text_width(text, scale):
    """Pixel width of text rendered at the given scale (1px tracking)."""
    return len(text) * (CHAR_W + 1) * scale - scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ------------------------------------------------------------------ canvas --
class Canvas:
    """A plain RGB pixel buffer with small flat-drawing helpers."""

    def __init__(self, width, height, background):
        self.w = width
        self.h = height
        self.px = bytearray(width * height * 3)
        for i in range(width * height):
            self.px[i * 3] = background[0]
            self.px[i * 3 + 1] = background[1]
            self.px[i * 3 + 2] = background[2]

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = color[0]
                self.px[i + 1] = color[1]
                self.px[i + 2] = color[2]

    def rect(self, x, y, w, h, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def hline(self, x, y, w, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)

    def vline(self, x, y, h, color, thickness=1):
        self.fill_rect(x, y, thickness, h, color)

    def line(self, x0, y0, x1, y1, color, thickness=1):
        """Bresenham line with square brush."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thickness // 2
        while True:
            self.fill_rect(x0 - half, y0 - half, thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, color):
        """Filled circle."""
        for yy in range(cy - r, cy + r + 1):
            half = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.fill_rect(cx - half, yy, half * 2 + 1, 1, color)

    def ring(self, cx, cy, r, color, thickness=2):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - thickness) ** 2 <= d2 <= r * r:
                    self.set(xx, yy, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for yy in range(cy - ry, cy + ry + 1):
            t = (yy - cy) / ry if ry else 0
            half = int(rx * (1 - t * t) ** 0.5) if abs(t) <= 1 else 0
            self.fill_rect(cx - half, yy, half * 2 + 1, 1, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Filled triangle by scanline."""
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts

        def interp(xa, ya, xb, yb, y):
            if yb == ya:
                return xa
            return xa + (xb - xa) * (y - ya) / (yb - ya)

        for y in range(ay, cy + 1):
            if y < by:
                xa = interp(ax, ay, bx, by, y)
                xb = interp(ax, ay, cx, cy, y)
            else:
                xa = interp(bx, by, cx, cy, y)
                xb = interp(ax, ay, cx, cy, y)
            self.fill_rect(int(min(xa, xb)), y, int(abs(xb - xa)) + 1, 1, color)

    def poly(self, points, color):
        """Filled polygon (convex or concave) by scanline."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    if y1 != y0:
                        xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[i]), y, int(xs[i + 1] - xs[i]) + 1, 1, color)

    def draw_char(self, ch, x, y, scale, color):
        glyph = FONT.get(ch.upper(), FONT["?"])
        for row_i, row in enumerate(glyph):
            for col_i, bit in enumerate(row):
                if bit == "1":
                    self.fill_rect(
                        x + col_i * scale, y + row_i * scale, scale, scale, color
                    )

    def draw_text(self, text, x, y, scale, color):
        cx = x
        for ch in text:
            if ch == " ":
                cx += (CHAR_W + 1) * scale
                continue
            self.draw_char(ch, cx, y, scale, color)
            cx += (CHAR_W + 1) * scale
        return cx

    def draw_text_centered(self, text, cx, y, scale, color):
        x = cx - text_width(text, scale) // 2
        self.draw_text(text, x, y, scale, color)
        return x

    def draw_wrapped(self, text, x, y, max_width, scale, color, line_gap=4):
        lines = wrap_text(text, max_width, scale)
        for i, line in enumerate(lines):
            self.draw_text(line, x, y + i * (CHAR_H * scale + line_gap), scale, color)
        return y + len(lines) * (CHAR_H * scale + line_gap)


# -------------------------------------------------------------- PNG writer --
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(canvas, path):
    """Encode the canvas as a deterministic RGB PNG (no ancillary chunks)."""
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        start = y * stride
        raw += canvas.px[start : start + stride]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ------------------------------------------------------------- the day's news --
# Wednesday 25 November 2026, verified against same-day reporting (Reuters,
# AP, CNN, Le Monde, Just Security's Early Edition of 25 Nov 2026). Only
# events that happened, or were first reported, on 25 November 2026, plus
# the two stories still leading the day's front pages from the day before.
# Each story: (kicker, headline, body, accent colour).
STORIES = [
    (
        "LEAD  -  STRAIT OF HORMUZ",
        "TANKERS HIT MINES IN HORMUZ",
        "TWO OIL TANKERS EXPLODED AND CAUGHT FIRE AFTER STRIKING NAVAL "
        "MINES IN THE STRAIT OF HORMUZ, IRAN'S REVOLUTIONARY GUARD SAID, "
        "AS TEHRAN WARNED SHIPS TO FOLLOW ITS ORDERS OR RISK THE MINES.",
        SEA,
    ),
    (
        "MIDDLE EAST",
        "HOUTHIS HIT SAUDI REFINERY",
        "YEMEN'S HOUTHIS SAID THEY ATTACKED THE RAS TANURA OIL REFINERY, "
        "A DAY AFTER A STRIKE ON A RIYADH TOWER WOUNDED 11 PEOPLE.",
        ORANGE,
    ),
    (
        "PACIFIC",
        "SOLOMONS PICK AUSTRALIA",
        "SOLOMON ISLANDS SIGNED A SECURITY TREATY MAKING AUSTRALIA ITS "
        "PARTNER OF CHOICE AND BARRING ANY FOREIGN MILITARY BASE.",
        NAVY_LIGHT,
    ),
    (
        "CLIMATE",
        "POPE LAMENTS COP31 FAILURE",
        "POPE LEO CALLED THE COLLAPSE OF THE ANTALYA CLIMATE TALKS "
        "TROUBLING, AS OPEC BLAMED THE EU FOR THE NO-DEAL ENDING.",
        GREEN,
    ),
    (
        "TECH  -  US COURT",
        "HUAWEI FOUND GUILTY",
        "A US FEDERAL COURT CONVICTED HUAWEI OF STEALING TRADE SECRETS "
        "AND BANK FRAUD, BUT CLEARED IT OF RACKETEERING.",
        INK,
    ),
    (
        "FRANCE",
        "SARKOZY TO STAND TRIAL",
        "NICOLAS SARKOZY AND HIS WIFE CARLA BRUNI WERE ORDERED TO STAND "
        "TRIAL OVER WITNESS TAMPERING IN THE LIBYA FUNDING CASE.",
        RED,
    ),
    (
        "MARKETS",
        "HUANG BACK AT NVIDIA",
        "JENSEN HUANG IS BACK AS NVIDIA CHIEF AFTER THE BOARD REINSTATED "
        "HIM, AND SHARES SOARED AS WALL STREET RALLIED.",
        DARK_GREEN,
    ),
    (
        "NATO  -  POLAND",
        "AWACS TO POLAND",
        "NATO IS SENDING AN EARLY-WARNING AIRCRAFT TO POLAND AFTER "
        "RUSSIAN MISSILES LANDED THERE, AND A DRONE BRIEFLY ENTERED "
        "POLISH AIRSPACE AGAIN.",
        NAVY,
    ),
]


# ------------------------------------------------------------- panel helpers --
def panel_frame(cv, x, y, w, h, accent):
    """White panel with a thin ink border and an accent top bar."""
    cv.fill_rect(x, y, w, h, WHITE)
    cv.fill_rect(x, y, w, 6, accent)
    cv.rect(x, y, w, h, INK, 2)


def kicker_line(cv, x, y, text, scale, color):
    cv.draw_text(text, x, y, scale, color)
    return y + CHAR_H * scale + 4


def headline_block(cv, x, y, w, headline, scale, color=INK, gap=3):
    lines = wrap_text(headline, w, scale)
    for i, line in enumerate(lines):
        cv.draw_text(line, x, y + i * (CHAR_H * scale + gap), scale, color)
    return y + len(lines) * (CHAR_H * scale + gap)


def body_block(cv, x, y, w, body, scale, color=INK):
    return cv.draw_wrapped(body, x, y, w, scale, color, line_gap=3)


def explosion(cv, cx, cy, r):
    """Fireball: jagged red edge, orange body, yellow core, grey smoke."""
    import math

    outer = []
    for i in range(24):
        ang = math.radians(i * 15)
        rr = r if i % 2 == 0 else int(r * 0.55)
        outer.append((cx + int(rr * math.cos(ang)),
                      cy + int(rr * math.sin(ang))))
    cv.poly(outer, RED)
    cv.disc(cx, cy, int(r * 0.68), ORANGE)
    cv.disc(cx, cy, int(r * 0.38), (255, 240, 160))
    # smoke puffs drifting up-left
    cv.disc(cx - int(r * 0.9), cy - int(r * 1.1), int(r * 0.34), (120, 120, 120))
    cv.disc(cx - int(r * 1.3), cy - int(r * 1.5), int(r * 0.26), (150, 150, 150))


def tanker(cv, x, y, w, h, hull=(40, 40, 40)):
    """Side view of an oil tanker: hull, deck, bridge, funnel."""
    cv.fill_rect(x, y + h // 2, w, h // 2, hull)
    cv.poly([(x, y + h // 2), (x + w, y + h // 2),
             (x + int(w * 0.94), y + h), (x + int(w * 0.06), y + h)], hull)
    # deck containers / tanks
    for i in range(4):
        cx0 = x + 14 + i * (w // 5)
        cv.fill_rect(cx0, y + 8, w // 7, h // 2 - 8, (200, 200, 200))
    # bridge tower + funnel
    cv.fill_rect(x + int(w * 0.82), y - 6, 22, h // 2 + 6, WHITE)
    cv.fill_rect(x + int(w * 0.82), y - 6, 22, 8, RED)
    cv.fill_rect(x + int(w * 0.90), y - 26, 12, 22, (60, 60, 60))
    cv.fill_rect(x + int(w * 0.90), y - 26, 12, 6, GOLD)


def sea_mine(cv, cx, cy, r):
    """A spiked naval mine."""
    import math

    for ang in range(0, 360, 45):
        a = math.radians(ang)
        x1 = cx + int(r * 0.8 * math.cos(a))
        y1 = cy + int(r * 0.8 * math.sin(a))
        x2 = cx + int(r * 1.35 * math.cos(a))
        y2 = cy + int(r * 1.35 * math.sin(a))
        cv.line(x1, y1, x2, y2, INK, 3)
    cv.disc(cx, cy, r, INK)
    cv.disc(cx - r // 3, cy - r // 3, r // 3, (90, 90, 90))


# ------------------------------------------------------------------ masthead --
def draw_masthead(cv):
    cv.fill_rect(0, 0, WIDTH, 118, NAVY)
    cv.fill_rect(0, 118, WIDTH, 5, GOLD)
    cv.draw_text_centered("THE WORLD IN ONE PICTURE", WIDTH // 2, 14, 6, WHITE)
    cv.draw_text_centered("WEDNESDAY 25 NOVEMBER 2026", WIDTH // 2, 62, 5, GOLD)
    cv.hline(24, 108, WIDTH - 48, WHITE, 2)


# -------------------------------------------------------------- lead panel --
def draw_lead(cv, x, y, w, h):
    """Full-width lead: Hormuz tanker scene with headline and body."""
    kicker, headline, body, accent = STORIES[0]
    panel_frame(cv, x, y, w, h, accent)
    # scene strip across the top of the panel
    sy, sh = y + 6, 128
    cv.fill_rect(x + 2, sy, w - 4, sh, SKY)
    # sun and smoke
    cv.disc(x + w - 90, sy + 34, 22, FLAME)
    cv.ellipse(x + w - 200, sy + 30, 46, 14, (240, 240, 240))
    cv.ellipse(x + w - 150, sy + 44, 56, 16, (225, 225, 225))
    # sea
    cv.fill_rect(x + 2, sy + 78, w - 4, sh - 78, SEA)
    cv.fill_rect(x + 2, sy + 78, w - 4, 4, SEA_LIGHT)
    for wx in range(x + 20, x + w - 20, 90):
        cv.hline(wx, sy + 96, 44, SEA_LIGHT, 2)
        cv.hline(wx + 30, sy + 112, 44, SEA_LIGHT, 2)
    # tanker, mine, explosion
    tanker(cv, x + 40, sy + 34, 330, 56)
    sea_mine(cv, x + 470, sy + 96, 13)
    explosion(cv, x + 560, sy + 52, 30)
    explosion(cv, x + 700, sy + 44, 20)
    # strait label
    cv.draw_text("STRAIT OF HORMUZ", x + w - 250, sy + sh - 26, 2, WHITE)
    # text below the scene
    ty = sy + sh + 12
    ty = kicker_line(cv, x + 16, ty, kicker, 2, RED)
    ty = headline_block(cv, x + 16, ty, w - 32, headline, 4, INK)
    body_block(cv, x + 16, ty + 2, w - 32, body, 2, INK)


# ------------------------------------------------------------ small panels --
def draw_refinery(cv, x, y, w, h):
    """Ras Tanura refinery: towers, tanks and flames at dusk."""
    cv.fill_rect(x, y, w, h, (44, 24, 16))
    cv.disc(x + w - 28, y + 22, 14, FLAME)
    for i, tx in enumerate((10, 52, 94)):
        cv.fill_rect(x + tx, y + h - 66, 30, 66, (150, 150, 150))
        cv.fill_rect(x + tx, y + h - 72, 30, 6, (110, 110, 110))
    cv.fill_rect(x + 126, y + h - 84, 10, 84, (180, 180, 180))
    cv.triangle(x + 122, y + h - 84, x + 140, y + h - 84, x + 131, y + h - 102,
                (180, 180, 180))
    explosion(cv, x + 131, y + h - 102, 12)
    explosion(cv, x + 30, y + h - 78, 10)
    cv.fill_rect(x, y + h - 8, w, 8, (20, 12, 8))


def draw_islands(cv, x, y, w, h):
    """Pacific: sun, sea and two islands with a palm."""
    cv.fill_rect(x, y, w, h, SKY)
    cv.disc(x + w - 42, y + 24, 16, FLAME)
    cv.fill_rect(x, y + h - 52, w, 52, SEA)
    cv.hline(x + 10, y + h - 40, 60, SEA_LIGHT, 2)
    cv.hline(x + w - 80, y + h - 28, 60, SEA_LIGHT, 2)
    cv.ellipse(x + 60, y + h - 46, 52, 16, SAND)
    cv.ellipse(x + w - 70, y + h - 40, 34, 12, SAND)
    # palm on the big island
    cv.line(x + 60, y + h - 48, x + 60, y + h - 84, BROWN, 4)
    for dx, dy in ((-26, -14), (26, -14), (-18, -26), (18, -26), (0, -30)):
        cv.line(x + 60, y + h - 84, x + 60 + dx, y + h - 84 + dy, GREEN, 3)
    # a small flag on the small island
    cv.vline(x + w - 70, y + h - 62, 24, INK, 3)
    cv.fill_rect(x + w - 70, y + h - 62, 22, 12, NAVY_LIGHT)


def draw_climate(cv, x, y, w, h):
    """COP31: a globe on a cracked, warming earth, no deal."""
    cv.fill_rect(x, y, w, h, (238, 226, 200))
    cv.disc(x + w // 2, y + h // 2 - 6, 46, SEA)
    cv.ellipse(x + w // 2 - 18, y + h // 2 - 22, 22, 12, GREEN)
    cv.ellipse(x + w // 2 + 8, y + h // 2 + 12, 18, 10, GREEN)
    cv.ellipse(x + w // 2 - 30, y + h // 2 + 18, 14, 8, SAND)
    cv.ring(x + w // 2, y + h // 2 - 6, 46, INK, 2)
    # thermometer rising
    cv.fill_rect(x + w - 34, y + 16, 10, h - 40, WHITE)
    cv.rect(x + w - 34, y + 16, 10, h - 40, INK, 2)
    cv.fill_rect(x + w - 32, y + 30, 6, h - 62, RED)
    cv.disc(x + w - 29, y + h - 26, 9, RED)
    # cracked ground
    cv.fill_rect(x, y + h - 14, w, 14, (196, 164, 120))
    cv.line(x + 20, y + h - 14, x + 44, y + h - 2, BROWN, 2)
    cv.line(x + 120, y + h - 14, x + 104, y + h - 2, BROWN, 2)


def draw_chip(cv, x, y, w, h):
    """Huawei: a chip stamped GUILTY under a gavel."""
    cv.fill_rect(x, y, w, h, (226, 232, 240))
    cx, cy = x + 16, y + 12
    cv.fill_rect(cx - 8, cy - 8, 72, 72, INK)
    cv.fill_rect(cx, cy, 56, 56, (40, 40, 40))
    for i in range(3):
        cv.fill_rect(cx - 8, cy + 8 + i * 18, 8, 6, GOLD)
        cv.fill_rect(cx + 56, cy + 8 + i * 18, 8, 6, GOLD)
        cv.fill_rect(cx + 8 + i * 18, cy - 8, 6, 8, GOLD)
        cv.fill_rect(cx + 8 + i * 18, cy + 56, 6, 8, GOLD)
    cv.fill_rect(cx + 16, cy + 16, 24, 24, DARK_GREEN)
    # gavel, top right
    cv.line(x + w - 22, y + 14, x + w - 52, y + 44, BROWN, 6)
    cv.fill_rect(x + w - 58, y + 34, 26, 14, BROWN)
    cv.fill_rect(x + w - 30, y + 6, 26, 14, BROWN)
    # GUILTY stamp, bottom
    cv.rect(x + 10, y + h - 32, w - 20, 24, RED, 3)
    cv.draw_text("GUILTY", x + (w - text_width("GUILTY", 2)) // 2,
                 y + h - 26, 2, RED)


def draw_court(cv, x, y, w, h):
    """Sarkozy: courthouse columns and scales of justice."""
    cv.fill_rect(x, y, w, h, (232, 228, 218))
    # pediment
    cv.triangle(x + 20, y + 26, x + w - 20, y + 26, x + w // 2, y + 6, NAVY)
    cv.fill_rect(x + 20, y + 26, w - 40, 8, NAVY)
    for i in range(4):
        cx0 = x + 30 + i * ((w - 60) // 4)
        cv.fill_rect(cx0, y + 34, 12, h - 48, WHITE)
        cv.rect(cx0, y + 34, 12, h - 48, INK, 1)
    cv.fill_rect(x + 16, y + h - 16, w - 32, 10, NAVY)
    # scales
    scx, scy = x + w - 52, y + h - 52
    cv.vline(scx, scy - 26, 26, GOLD, 3)
    cv.hline(scx - 18, scy - 26, 36, GOLD, 3)
    cv.line(scx - 18, scy - 26, scx - 26, scy - 10, GOLD, 2)
    cv.line(scx + 18, scy - 26, scx + 26, scy - 10, GOLD, 2)
    cv.disc(scx - 26, scy - 8, 7, GOLD)
    cv.disc(scx + 26, scy - 8, 7, GOLD)


def draw_nvidia(cv, x, y, w, h):
    """Nvidia: green chip and a rising market line."""
    cv.fill_rect(x, y, w, h, (16, 16, 16))
    # rising chart
    pts = [(x + 10, y + h - 26), (x + 42, y + h - 44), (x + 72, y + h - 38),
           (x + 104, y + h - 62), (x + 132, y + h - 88)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], DARK_GREEN, 4)
    cv.triangle(pts[-1][0] - 8, pts[-1][1] + 2, pts[-1][0] + 10, pts[-1][1] + 2,
                pts[-1][0] + 2, pts[-1][1] - 12, DARK_GREEN)
    # chip
    cx, cy = x + 30, y + 18
    cv.fill_rect(cx, cy, 46, 46, DARK_GREEN)
    cv.fill_rect(cx + 12, cy + 12, 22, 22, (16, 16, 16))
    for i in range(3):
        cv.fill_rect(cx - 8, cy + 8 + i * 14, 8, 5, DARK_GREEN)
        cv.fill_rect(cx + 46, cy + 8 + i * 14, 8, 5, DARK_GREEN)
    cv.draw_text("+31%", x + w - 78, y + 12, 2, WHITE)


def draw_awacs(cv, x, y, w, h):
    """NATO AWACS: radar plane over a map strip, sweeping arcs."""
    cv.fill_rect(x, y, w, h, SKY)
    cv.disc(x + 40, y + 24, 14, WHITE)
    # ground strip
    cv.fill_rect(x, y + h - 34, w, 34, (190, 200, 170))
    cv.fill_rect(x, y + h - 34, w, 3, GREEN)
    # radar arcs
    for r in (34, 52, 70):
        cv.ring(x + w - 60, y + h - 34, r, NAVY, 2)
    cv.disc(x + w - 60, y + h - 34, 6, RED)
    # plane: fuselage, radar dome, wings, tail
    px, py = x + 60, y + 56
    cv.ellipse(px, py, 66, 12, WHITE)
    cv.disc(px - 6, py - 16, 14, LIGHT_GREY)
    cv.poly([(px + 66, py - 4), (px + 86, py), (px + 66, py + 5)], WHITE)
    cv.poly([(px - 40, py - 6), (px - 10, py - 6), (px - 26, py - 34),
             (px - 44, py - 34)], WHITE)
    cv.poly([(px - 40, py + 6), (px - 10, py + 6), (px - 26, py + 30),
             (px - 44, py + 30)], WHITE)
    cv.poly([(px - 66, py - 4), (px - 52, py - 4), (px - 58, py - 26),
             (px - 70, py - 26)], NAVY)
    cv.fill_rect(px + 40, py - 6, 14, 4, SKY)


ILLUSTRATIONS = [None, draw_refinery, draw_islands, draw_climate,
                 draw_chip, draw_court, draw_nvidia, draw_awacs]


def draw_small_panel(cv, x, y, w, h, idx):
    """Wide panel: illustration on the left, kicker/headline/body on the right."""
    kicker, headline, body, accent = STORIES[idx]
    panel_frame(cv, x, y, w, h, accent)
    ill = ILLUSTRATIONS[idx]
    iw = 150
    ill(cv, x + 2, y + 8, iw, h - 16)
    tx = x + iw + 14
    tw = w - iw - 26
    ty = y + 10
    ty = kicker_line(cv, tx, ty, kicker, 2, accent)
    ty = headline_block(cv, tx, ty, tw, headline, 3, INK)
    body_block(cv, tx, ty + 2, tw, body, 2, INK)


# ------------------------------------------------------------------- layout --
def render():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    draw_masthead(cv)
    # lead story, full width
    draw_lead(cv, 16, 130, WIDTH - 32, 288)
    # three rows of two wide panels
    px, py = 16, 428
    pw, ph = 492, 168
    gap = 8
    for row in range(3):
        for col in range(2):
            idx = 1 + row * 2 + col
            draw_small_panel(cv, px + col * (pw + gap), py + row * (ph + gap),
                             pw, ph, idx)
    # bottom strip: the eighth story, wide panel
    by = 428 + 3 * ph + 2 * gap
    kicker, headline, body, accent = STORIES[7]
    panel_frame(cv, 16, by, WIDTH - 32, 48, accent)
    cv.draw_text(kicker, 28, by + 6, 2, accent)
    cv.draw_text(headline, 28, by + 25, 3, INK)
    # footer
    cv.draw_text_centered(
        "ALL STORIES VERIFIED FROM SAME-DAY REPORTING  -  25 NOVEMBER 2026",
        WIDTH // 2, HEIGHT - 22, 2, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, OUT_NAME)
    size = write_png(render(), path)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
