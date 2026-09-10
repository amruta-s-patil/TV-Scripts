"""Draw the SD-X v11 chart legend as a PNG for the user guide.

  python sdx_legend.py            -> sdx_legend.png

Every marker the signals script can plot, with the same colours Pine uses,
so the picture stays truthful when the script changes: edit here, re-run.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle

# Pine's named colours
LIME, FUCH, ORNG = "#00FF00", "#FF00FF", "#FF9800"
YELL, BLUE, BLCK = "#FFEB3B", "#2962FF", "#000000"
MARO, GREN, RED = "#880E4F", "#4CAF50", "#FF5252"
TEAL, PURP, GRAY = "#00897B", "#9C27B0", "#787B86"
UP, DN = "#26a69a", "#ef5350"          # default candle body colours
SUPPLY, DEMAND = "#ff8a65", "#4db6ac"  # zone fills

# (kind, spec, name, meaning) -- kind drives how the swatch is drawn
SECTIONS = [
 ("Trade markers - the only ones you act on", [
  ("candle", dict(body=UP, up=True, mark=("dot", GREN, "sig"), label="BUY 23650 CE  zone"),
   "BIG green circle (below) + label",
   "BUY ATM CE. All four stages passed. The label names the strike and which source\n"
   "fired: zone / level / 4-flag / absorb."),
  ("candle", dict(body=DN, up=False, mark=("dot", RED, "sig"), label="BUY 23650 PE  zone"),
   "BIG red circle (above) + label",
   "BUY ATM PE. The same on the short side.\n"
   "Note: the tiny climax dots use the same colours - a trade always has a label."),
  ("candle", dict(body=DN, up=False, mark=("x", GRAY, "small")),
   "Grey x",
   "A setup existed here and was REJECTED by a filter, risk, room, regime or session\n"
   "rule. Do not trade it. The DIAG table says which rule killed it."),
  ("line", dict(color=RED, ls="-", lw=2.2, tag="SL 23627.70  (prem -10)"),
   "Red line + SL label",
   "Stop loss in index points, plus the premium move it implies at your ATM delta."),
  ("line", dict(color=BLCK, ls="-", lw=2.2, tag="TGT 23687.70  2R  (prem +20)"),
   "Black line + TGT label",
   "Target. Both lines extend bar by bar and freeze when hit, tagged TARGET, STOP\n"
   "or SQ-OFF, so scrolling back shows the real outcome of every past signal."),
 ]),
 ("Bar colour - who is trading this candle", [
  ("candle", dict(body=BLUE, up=True),
   "Blue bar",
   "Whale buying: volume > 1.35x its 20-bar average with a bullish close or a\n"
   "long lower wick. Institutional demand stepped in on this bar."),
  ("candle", dict(body=BLCK, up=False),
   "Black bar",
   "Whale selling: same volume test, bearish close or long upper wick.\n"
   "Institutional supply hit this bar."),
  ("candle", dict(body=YELL, up=True),
   "Yellow bar",
   "Range expansion: bar range >= 1.4 x ATR on above-average volume. The move is\n"
   "being pushed, not drifting. Direction is whatever the body says."),
  ("candle", dict(body=GRAY, up=True),
   "Grey bar",
   "Absorption or belan: a wick at least 1.3x the body, or a body under 15% of\n"
   "the range. Someone is soaking up the flow; the move is stalling."),
  ("candle", dict(body=UP, up=True, twin=DN),
   "Normal green / red",
   "No whale, expansion or absorption condition. An ordinary bar - context only,\n"
   "never a reason to trade on its own."),
  ("bg", dict(),
   "Purple background shading",
   "Compression: Bollinger Bands inside Keltner Channels. Volatility is coiled.\n"
   "Expect the break to come out of the shade. Entries can be blocked while on."),
 ]),
 ("Candle shape markers - what the wick is telling you", [
  ("candle", dict(body=UP, up=True, lowwick=3.0, mark=("tri_up", LIME, "big")),
   "Big lime triangle (below bar)",
   "Strong bullish injection: lower wick > 1.8x body, almost no upper wick, and the\n"
   "bar is wider than ATR. Sellers were rejected hard. Bullish."),
  ("candle", dict(body=DN, up=False, hiwick=3.0, mark=("tri_dn", FUCH, "big")),
   "Big magenta triangle (above bar)",
   "Strong bearish injection: the mirror image. Buyers were rejected hard. Bearish."),
  ("candle", dict(body=UP, up=True, lowwick=2.2, small=True, mark=("dot", LIME, "small")),
   "Small lime dot (below bar)",
   "Weak bullish injection: same wick shape, but the bar is narrower than ATR.\n"
   "A hint, not a signal. Very common in chop."),
  ("candle", dict(body=DN, up=False, hiwick=2.2, small=True, mark=("dot", FUCH, "small")),
   "Small magenta dot (above bar)",
   "Weak bearish injection. Same caveat - low conviction."),
  ("candle", dict(body=GRAY, doji=True, mark=("diamond", ORNG, "big")),
   "Orange diamond (above bar)",
   "Strong belan: a near-doji body inside a wide range. Violent two-way fight and\n"
   "nobody won. Often marks the pivot of the swing."),
  ("candle", dict(body=GRAY, doji=True, small=True, mark=("x", ORNG, "small")),
   "Orange x (above bar)",
   "Weak belan: a narrow doji. Indecision without the volatility. Background noise."),
 ]),
 ("Structure markers - regime and exhaustion", [
  ("candle", dict(body=DN, up=False, hiwick=2.5, mark=("label_dn", MARO, "W5")),
   "W5 maroon tag (above bar)",
   "Wave (5) exhaustion at the highs: a new high that RSI does NOT confirm, price\n"
   "> 0.8 ATR above VWAP, and the bar rejects with an upper wick.\n"
   "LONGS ARE VETOED for the next 8 bars. Stop chasing."),
  ("candle", dict(body=UP, up=True, lowwick=2.5, mark=("label_up", GREN, "W5")),
   "W5 green tag (below bar)",
   "Wave (5) exhaustion at the lows: the mirror image.\n"
   "SHORTS ARE VETOED for the next 8 bars."),
  ("candle", dict(body=UP, up=True, mark=("label_dn", YELL, "TRAP", BLCK)),
   "TRAP yellow tag",
   "Shark trap: three same-direction bodies breaking 30-bar isolation, with no\n"
   "fourth. The run failed to extend - fade it or stand aside. Above the bar =\n"
   "failed up-run, below the bar = failed down-run."),
  ("candle", dict(body=UP, up=True, mark=("label_up", BLUE, "4F")),
   "4F blue tag (below bar)",
   "Whale 4-flag long: a fourth consecutive bullish body extending the run. This is\n"
   "an ENTRY SOURCE - a continuation trade, stop under the last 4 bars."),
  ("candle", dict(body=DN, up=False, mark=("label_dn", BLCK, "4F")),
   "4F black tag (above bar)",
   "Whale 4-flag short: the mirror. Also an entry source."),
  ("candle", dict(body=BLCK, up=False, mark=("label_up", MARO, "3")),
   "Maroon number under a black candle",
   "Nth institutional selling candle inside the demand zone. At the threshold\n"
   "(default 3) the zone has held, and a close above that candle's high is a long."),
  ("candle", dict(body=BLUE, up=True, mark=("label_dn", BLUE, "3")),
   "Blue number above a blue candle",
   "Nth institutional buying candle inside the supply zone. A close below that\n"
   "candle's low is the short."),
  ("candle", dict(body=DN, up=False, mark=("dot", RED, "small")),
   "Small red dot (above bar)",
   "Bear climax: outsized volume - or range, on a feed with no volume - into the\n"
   "base. Selling exhaustion. A maroon shelf is drawn at the low."),
  ("candle", dict(body=UP, up=True, mark=("dot", GREN, "small")),
   "Small green dot (below bar)",
   "Bull climax: the same into the ceiling. Buying exhaustion. An orange shelf is\n"
   "drawn at the high."),
 ]),
 ("Lines, zones and shading", [
  ("box", dict(color=SUPPLY),
   "Salmon box - Supply",
   "Where price previously ran out of buyers. Longs are not taken into it; a\n"
   "rejection out of it is the short trigger."),
  ("box", dict(color=DEMAND),
   "Teal box - Demand",
   "Where price previously ran out of sellers. The long trigger."),
  ("box", dict(color="#80cbc4", faint=True),
   "Pale teal band",
   "Target tier (gap-adaptive zone mode only): where the move is trying to reach,\n"
   "not where it turns. Structural targets aim at these."),
  ("line", dict(color="#ff3d00", ls="-", lw=1.4, tag="BN"),
   "Solid red line, tag BN",
   "The Nifty price at the moment BANKNIFTY made a swing HIGH. Acts as resistance.\n"
   "It disappears once price closes through it."),
  ("line", dict(color="#ff3d00", ls="--", lw=1.4, tag="BN"),
   "Dashed red line, tag BN",
   "The Nifty price at a BANKNIFTY swing LOW. Acts as support. Bounces off these\n"
   "levels are an entry source."),
  ("line", dict(color=MARO, ls="-", lw=2.4, tag="8"),
   "Maroon shelf + day number",
   "Climax shelf at a selling-exhaustion low. The number is the day of the month it\n"
   "was made. Price often returns to it."),
  ("line", dict(color=ORNG, ls="-", lw=2.4, tag="8"),
   "Orange shelf + day number",
   "Climax shelf at a buying-exhaustion high."),
  ("line", dict(color=TEAL, ls="--", lw=1.6, tag=""),
   "Dashed half-shelf",
   "The midpoint of the climax bar - the first place the move usually pauses."),
  ("line", dict(color="#2962ff", ls="-", lw=2.4, tag=""),
   "Thick blue line pair",
   "The opening candle's high and low. Fake opens (open == high, or open == low)\n"
   "are skipped and the second candle is used instead."),
  ("line", dict(color="#2962ff", ls="-", lw=1.0, tag=""),
   "Faint blue lines",
   "Ladder rungs: the opening candle's height projected in 1:1, 1:2 and 1:3\n"
   "multiples from each edge. Book into them; 1:3 is where institutions book too."),
  ("line", dict(color="#ff9800", ls="-", lw=1.8, tag="VWAP"),
   "Orange line",
   "Session VWAP, the primary bias filter: longs above, shorts below, unless Stretch\n"
   "mode allows a mean-reversion entry 1.5 ATR away from it."),
 ]),
]

SEC_H = 1.0         # header band height
SW_X = 0.6          # left margin
COL_W = 18.6        # one legend column
GUTTER = 1.2
TX_OFF = 7.8        # swatch origin -> text origin
LINE_H = 0.36       # one line of body text
MIN_ROW = 1.9       # a candle plus its marker needs this much vertical room


def row_height(meaning):
    return max(MIN_ROW, 0.75 + LINE_H * (meaning.count("\n") + 1))


def draw_candle(ax, cx, cy, s):
    """One candle centred at (cx, cy), with optional wick stretch and marker."""
    body = s["body"]
    up = s.get("up", True)
    w = 0.9
    small = s.get("small", False)
    bh = 0.15 if small else 0.22
    unit = 0.06 if small else 0.09
    lw_ = s.get("lowwick", 0.6) * unit
    hw_ = s.get("hiwick", 0.6) * unit
    if s.get("doji"):
        bh = 0.03
        lw_ = hw_ = 0.24 if not small else 0.14
    top, bot = cy + bh, cy - bh
    ax.plot([cx, cx], [top, top + hw_], color=body, lw=1.4, solid_capstyle="butt", zorder=3)
    ax.plot([cx, cx], [bot, bot - lw_], color=body, lw=1.4, solid_capstyle="butt", zorder=3)
    ax.add_patch(Rectangle((cx - w / 2, bot), w, bh * 2, facecolor=body,
                           edgecolor=body, zorder=4))
    if s.get("twin"):
        draw_candle(ax, cx + 1.6, cy, dict(body=s["twin"], up=False))
    if s.get("mark"):
        draw_mark(ax, cx, top + hw_, bot - lw_, s["mark"], up)
    if s.get("label"):
        yy = bot - lw_ - 0.30 if up else top + hw_ + 0.30
        ax.text(cx + 0.8, yy, s["label"], fontsize=6.4, color="white", va="center",
                ha="left", zorder=6,
                bbox=dict(boxstyle="round,pad=0.25", fc=GREN if up else RED, ec="none"))


def draw_mark(ax, cx, ytop, ybot, m, up):
    """Marker above or below the candle, matching Pine's location.* argument."""
    kind, col = m[0], m[1]
    above = kind in ("tri_dn", "label_dn") or (kind in ("dot", "x", "diamond") and not up)
    y = (ytop + 0.22) if above else (ybot - 0.22)
    size = m[2] if len(m) > 2 else "small"
    if kind == "tri_up":
        ax.add_patch(Polygon([[cx - .28, y - .12], [cx + .28, y - .12], [cx, y + .18]],
                             fc=col, ec="none", zorder=5))
    elif kind == "tri_dn":
        ax.add_patch(Polygon([[cx - .28, y + .12], [cx + .28, y + .12], [cx, y - .18]],
                             fc=col, ec="none", zorder=5))
    elif kind == "diamond":
        ax.add_patch(Polygon([[cx, y + .18], [cx + .22, y], [cx, y - .18], [cx - .22, y]],
                             fc=col, ec="none", zorder=5))
    elif kind == "dot":
        ax.add_patch(Circle((cx, y), 0.21 if size == "sig" else 0.12,
                            fc=col, ec="none", zorder=5))
    elif kind == "x":
        ax.plot([cx - .15, cx + .15], [y - .15, y + .15], color=col, lw=1.6, zorder=5)
        ax.plot([cx - .15, cx + .15], [y + .15, y - .15], color=col, lw=1.6, zorder=5)
    elif kind in ("label_up", "label_dn"):
        tcol = m[3] if len(m) > 3 else "white"
        ax.text(cx, y, m[2], fontsize=6.5, color=tcol, ha="center", va="center",
                zorder=6, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.22", fc=col, ec="none"))


def draw_row(ax, top, h, kind, spec, name, meaning, x0=SW_X):
    """Row occupies the band [top - h, top]. Swatch centred, text top-aligned."""
    mid = top - h / 2
    tx = x0 + TX_OFF
    if kind == "candle":
        draw_candle(ax, x0 + 1.7, mid, spec)
    elif kind == "bg":
        ax.add_patch(Rectangle((x0, mid - 0.42), 3.4, 0.84,
                               fc=PURP, alpha=0.13, ec="none", zorder=1))
        draw_candle(ax, x0 + 1.2, mid, dict(body=UP, up=True, small=True))
        draw_candle(ax, x0 + 2.4, mid, dict(body=DN, up=False, small=True))
    elif kind == "line":
        ax.plot([x0, x0 + 3.1], [mid, mid], color=spec["color"], ls=spec["ls"],
                lw=spec["lw"], zorder=3)
        tag = spec.get("tag")
        if tag:
            boxed = tag.startswith(("SL", "TGT"))
            ax.text(x0 + 3.25, mid, tag, fontsize=6.3, va="center", ha="left",
                    color="white" if boxed else spec["color"],
                    bbox=dict(boxstyle="round,pad=0.22", fc=spec["color"], ec="none")
                    if boxed else None)
    elif kind == "box":
        ax.add_patch(Rectangle((x0, mid - 0.30), 3.1, 0.60, fc=spec["color"],
                               alpha=0.30 if spec.get("faint") else 0.60,
                               ec="none", zorder=2))
    ax.text(tx, top - 0.34, name, fontsize=8.8, fontweight="bold", va="center", ha="left")
    ax.text(tx, top - 0.60, meaning, fontsize=7.6, va="top", ha="left",
            color="#333333", linespacing=1.45)


def section_height(items):
    return SEC_H + sum(row_height(m) for _, _, _, m in items)


def split_columns():
    """Two columns, split on whole sections at the most balanced cut."""
    heights = [section_height(items) for _, items in SECTIONS]
    cut = min(range(1, len(SECTIONS)),
              key=lambda i: abs(sum(heights[:i]) - sum(heights[i:])))
    return SECTIONS[:cut], SECTIONS[cut:], max(sum(heights[:cut]), sum(heights[cut:]))


def draw_column(ax, sections, x0, top):
    y = top
    for title, items in sections:
        ax.add_patch(Rectangle((x0 - 0.25, y - 0.62), COL_W, 0.62,
                               fc="#eceff1", ec="none", zorder=1))
        ax.text(x0, y - 0.31, title.upper(), fontsize=9.0, fontweight="bold",
                va="center", color="#263238", zorder=2)
        y -= SEC_H
        for kind, spec, name, meaning in items:
            h = row_height(meaning)
            draw_row(ax, y, h, kind, spec, name, meaning, x0)
            y -= h
            ax.plot([x0 - 0.25, x0 + COL_W - 0.5], [y, y],
                    color="#e0e0e0", lw=0.5, zorder=1)


def main(path="sdx_legend.png"):
    left, right, tallest = split_columns()
    total = tallest + 2.4
    width = COL_W * 2 + GUTTER + 1.2
    fig = plt.figure(figsize=(16.0, total * (16.0 / width)), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, total)
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), width, total, fc="white", ec="none", zorder=0))

    ax.text(SW_X, total - 0.6, "SD-X v11  -  chart legend",
            fontsize=16, fontweight="bold", va="center")
    ax.text(SW_X, total - 1.15,
            "Every marker the signals script can draw. Only the big labelled circles "
            "are trades - everything else is context.",
            fontsize=8.5, color="#555555", va="center")

    top = total - 1.9
    draw_column(ax, left, SW_X, top)
    draw_column(ax, right, SW_X + COL_W + GUTTER, top)

    fig.savefig(path, facecolor="white")
    print("wrote", path)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sdx_legend.png")
