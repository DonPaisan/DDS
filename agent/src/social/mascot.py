"""Buck: the Debt Direct Solutions mascot, drawn as SVG from the logo's money bag.

Vector, hand-built, deterministic: no generative imagery, so nothing for Meta to label.
Every part is a small path so expressions and poses compose:

    mascot(expr="happy", pose="wave", prop="phone")  -> "<svg ...>...</svg>"

Expressions: happy, worried, surprised, thinking, relieved, determined, sad, wink.
Poses: rest, wave, chin, hold (holds the prop), shrug, cheer, point.
Props: phone, bill, calculator, coffee, piggy, letter, card, none.
"""
from __future__ import annotations

NAVY = "#1c2b3a"
YELLOW = "#ffd84d"
YELLOW_DK = "#e6b800"
BLUE = "#3b9cf6"
BLUE_DK = "#1c6fd1"
PEACH = "#f6c9a3"
WHITE = "#ffffff"
RED = "#e35d5b"
GREEN = "#3bb273"

W = 400  # viewBox width; the character is centred at x=200


def _bag() -> str:
    """Body: a soft pear-shaped bag, a rope-tied neck, and a gathered tuft leaning a little right."""
    return f"""
<path d="M158 178 C 100 205, 78 300, 118 350 C 150 388, 250 388, 282 350 C 322 300, 300 205, 242 178 C 225 170, 175 170, 158 178 Z" fill="{YELLOW}" stroke="{NAVY}" stroke-width="9" stroke-linejoin="round"/>
<path d="M126 330 C 150 372, 250 372, 274 330" fill="none" stroke="{YELLOW_DK}" stroke-width="7" stroke-linecap="round" opacity=".55"/>
<path d="M160 178 C 168 160, 232 160, 240 178 L 236 150 L 164 150 Z" fill="{YELLOW}" stroke="{NAVY}" stroke-width="9" stroke-linejoin="round"/>
<path d="M164 150 C 150 128, 158 104, 182 96 C 198 90, 224 92, 238 100 C 256 110, 258 132, 236 150 Z" fill="{YELLOW}" stroke="{NAVY}" stroke-width="9" stroke-linejoin="round"/>
<path d="M186 104 C 190 118, 190 132, 186 146 M212 100 C 218 116, 218 132, 214 146" fill="none" stroke="{YELLOW_DK}" stroke-width="5" stroke-linecap="round" opacity=".8"/>
<rect x="152" y="142" width="96" height="18" rx="9" fill="{BLUE}" stroke="{NAVY}" stroke-width="7"/>
<circle cx="250" cy="151" r="9" fill="{BLUE}" stroke="{NAVY}" stroke-width="6"/>
<path d="M256 156 q 14 6 12 20" fill="none" stroke="{NAVY}" stroke-width="6" stroke-linecap="round"/>
"""


def _dollar(y: int = 350) -> str:
    return f"""<text x="200" y="{y}" text-anchor="middle" font-family="Poppins, Arial, sans-serif" font-weight="800" font-size="64" fill="{NAVY}">$</text>"""


def _eyes(expr: str) -> str:
    lx, rx, y = 172, 228, 232
    if expr in ("happy", "relieved"):
        # closed, smiling eyes
        return f"""<path d="M{lx-14} {y+2} Q {lx} {y-14} {lx+14} {y+2}" fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"/>
<path d="M{rx-14} {y+2} Q {rx} {y-14} {rx+14} {y+2}" fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"/>"""
    if expr == "wink":
        return f"""<circle cx="{lx}" cy="{y}" r="14" fill="{WHITE}" stroke="{NAVY}" stroke-width="7"/><circle cx="{lx+3}" cy="{y+2}" r="7" fill="{NAVY}"/><circle cx="{lx+6}" cy="{y-1}" r="2.5" fill="{WHITE}"/>
<path d="M{rx-14} {y} Q {rx} {y+10} {rx+14} {y}" fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"/>"""
    r = 18 if expr == "surprised" else 14
    pr = 9 if expr == "surprised" else 7
    dx = 3 if expr != "thinking" else 8
    return f"""<circle cx="{lx}" cy="{y}" r="{r}" fill="{WHITE}" stroke="{NAVY}" stroke-width="7"/><circle cx="{lx+dx}" cy="{y-1}" r="{pr}" fill="{NAVY}"/><circle cx="{lx+dx+3}" cy="{y-4}" r="2.5" fill="{WHITE}"/>
<circle cx="{rx}" cy="{y}" r="{r}" fill="{WHITE}" stroke="{NAVY}" stroke-width="7"/><circle cx="{rx+dx}" cy="{y-1}" r="{pr}" fill="{NAVY}"/><circle cx="{rx+dx+3}" cy="{y-4}" r="2.5" fill="{WHITE}"/>"""


def _brows(expr: str) -> str:
    lx, rx, y = 172, 228, 204
    s = f'fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"'
    if expr in ("worried", "sad"):
        return f'<path d="M{lx-16} {y+6} L {lx+12} {y-4}" {s}/><path d="M{rx-12} {y-4} L {rx+16} {y+6}" {s}/>'
    if expr == "determined":
        return f'<path d="M{lx-16} {y-6} L {lx+12} {y+6}" {s}/><path d="M{rx-12} {y+6} L {rx+16} {y-6}" {s}/>'
    if expr == "surprised":
        return f'<path d="M{lx-16} {y-8} Q {lx} {y-20} {lx+16} {y-8}" {s}/><path d="M{rx-16} {y-8} Q {rx} {y-20} {rx+16} {y-8}" {s}/>'
    if expr == "thinking":
        return f'<path d="M{lx-16} {y} L {lx+14} {y-2}" {s}/><path d="M{rx-14} {y-12} Q {rx} {y-18} {rx+16} {y-6}" {s}/>'
    return ""


def _mouth(expr: str) -> str:
    y = 262
    s = f'fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"'
    if expr in ("happy", "wink"):
        return f'<path d="M176 {y} Q 200 {y+26} 224 {y}" {s}/>'
    if expr == "relieved":
        return f'<path d="M180 {y+2} Q 200 {y+18} 220 {y+2}" {s}/>'
    if expr in ("worried",):
        return f'<path d="M180 {y+12} Q 200 {y-4} 220 {y+12}" {s}/>'
    if expr == "sad":
        return f'<path d="M178 {y+14} Q 200 {y-6} 222 {y+14}" {s}/>'
    if expr == "surprised":
        return f'<ellipse cx="200" cy="{y+6}" rx="13" ry="17" fill="{NAVY}"/>'
    if expr == "thinking":
        return f'<path d="M184 {y+6} L 216 {y+2}" {s}/>'
    if expr == "determined":
        return f'<path d="M180 {y+6} Q 200 {y+14} 220 {y+6}" {s}/>'
    return f'<path d="M182 {y+4} L 218 {y+4}" {s}/>'


def _cheeks() -> str:
    return f'<circle cx="148" cy="262" r="10" fill="{RED}" opacity=".22"/><circle cx="252" cy="262" r="10" fill="{RED}" opacity=".22"/>'


def _hand(x: int, y: int, rot: int = 0) -> str:
    return f'<g transform="translate({x} {y}) rotate({rot})"><circle r="20" fill="{PEACH}" stroke="{NAVY}" stroke-width="8"/></g>'


def _arm(side: str, pose: str) -> str:
    """Arms are a stroke from the shoulder to the hand, then a hand circle."""
    sx = 118 if side == "L" else 282
    sy = 270
    d = -1 if side == "L" else 1
    poses = {
        "rest":  (sx + d * 30, 335),
        "wave":  (sx + d * 55, 190) if side == "R" else (sx + d * 30, 335),
        "chin":  (200 - 30, 285) if side == "R" else (sx + d * 30, 335),
        "hold":  (200 + d * 38, 330),
        "shrug": (sx + d * 62, 250),
        "cheer": (sx + d * 55, 180),
        "point": (sx + d * 70, 240) if side == "R" else (sx + d * 30, 335),
    }
    hx, hy = poses.get(pose, poses["rest"])
    cx, cy = (sx + hx) / 2 + d * 18, (sy + hy) / 2 + 10
    return f'<path d="M{sx} {sy} Q {cx} {cy} {hx} {hy}" fill="none" stroke="{NAVY}" stroke-width="12" stroke-linecap="round"/>{_hand(int(hx), int(hy))}'


def _legs() -> str:
    return f"""<path d="M172 366 L 168 396" stroke="{NAVY}" stroke-width="12" stroke-linecap="round"/><path d="M228 366 L 232 396" stroke="{NAVY}" stroke-width="12" stroke-linecap="round"/>
<ellipse cx="160" cy="400" rx="26" ry="11" fill="{BLUE}" stroke="{NAVY}" stroke-width="7"/><ellipse cx="240" cy="400" rx="26" ry="11" fill="{BLUE}" stroke="{NAVY}" stroke-width="7"/>"""


def _prop(name: str) -> str:
    """Drawn between the hands when pose == hold (centred near 200, 330)."""
    s = f'stroke="{NAVY}" stroke-width="7" stroke-linejoin="round"'
    if name == "phone":
        return f'<rect x="168" y="290" width="64" height="100" rx="12" fill="{NAVY}"/><rect x="176" y="300" width="48" height="76" rx="6" fill="{BLUE}"/>'
    if name == "bill" or name == "letter":
        return f'<rect x="150" y="296" width="100" height="84" rx="6" fill="{WHITE}" {s}/><path d="M164 316 H 236 M164 334 H 236 M164 352 H 210" stroke="{NAVY}" stroke-width="6" stroke-linecap="round"/>' + (f'<text x="200" y="372" text-anchor="middle" font-family="Poppins, Arial" font-weight="800" font-size="20" fill="{RED}">DUE</text>' if name == "bill" else "")
    if name == "calculator":
        return f'<rect x="160" y="290" width="80" height="100" rx="10" fill="{NAVY}"/><rect x="170" y="300" width="60" height="22" rx="4" fill="{WHITE}"/>' + "".join(f'<circle cx="{180+i*20}" cy="{340+j*20}" r="6" fill="{YELLOW}"/>' for i in range(3) for j in range(2))
    if name == "coffee":
        return f'<path d="M170 306 H 230 L 224 372 H 176 Z" fill="{WHITE}" {s}/><path d="M230 318 C 252 318, 252 350, 228 350" fill="none" {s}/><path d="M188 300 q 3 -6 0 -11 M202 300 q 3 -6 0 -11" fill="none" stroke="{NAVY}" stroke-width="5" stroke-linecap="round" opacity=".6"/>'
    if name == "piggy":
        return f'<ellipse cx="200" cy="340" rx="52" ry="38" fill="#f7a8c4" {s}/><circle cx="240" cy="336" r="14" fill="#f7a8c4" {s}/><rect x="186" y="298" width="28" height="7" rx="3" fill="{NAVY}"/>'
    if name == "card":
        return f'<rect x="146" y="312" width="108" height="66" rx="8" fill="{BLUE}" {s}/><rect x="146" y="326" width="108" height="14" fill="{NAVY}"/><rect x="158" y="352" width="44" height="10" rx="3" fill="{WHITE}"/>'
    return ""


def _sweat(expr: str) -> str:
    if expr in ("worried", "sad"):
        return f'<path d="M268 200 q 10 14 0 24 q -10 -10 0 -24 z" fill="{BLUE}" stroke="{NAVY}" stroke-width="4"/>'
    return ""


def _thought(expr: str) -> str:
    if expr == "thinking":
        return f'<circle cx="292" cy="160" r="7" fill="{WHITE}" stroke="{NAVY}" stroke-width="5"/><circle cx="312" cy="134" r="11" fill="{WHITE}" stroke="{NAVY}" stroke-width="5"/>'
    return ""


def mascot(expr: str = "happy", pose: str = "rest", prop: str = "none", *, shadow: bool = True, size: int | None = None) -> str:
    """Full character SVG. Layers: shadow, back arm, body, prop, front arm, face."""
    if prop != "none" and pose == "rest":
        pose = "hold"
    parts = []
    if shadow:
        parts.append(f'<ellipse cx="200" cy="404" rx="96" ry="14" fill="{NAVY}" opacity=".12"/>')
    parts.append(_arm("L", pose))
    parts.append(_bag())
    parts.append(_dollar())
    parts.append(_legs())
    if pose == "hold":
        parts.append(_prop(prop))
    parts.append(_arm("R", pose))
    parts += [_brows(expr), _eyes(expr), _mouth(expr), _cheeks(), _sweat(expr), _thought(expr)]
    attrs = f'width="{size}" height="{size}"' if size else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="60 80 280 340" {attrs}>{"".join(parts)}</svg>'


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/buck")
    out.mkdir(parents=True, exist_ok=True)
    for e in ["happy", "worried", "surprised", "thinking", "relieved", "determined", "sad", "wink"]:
        (out / f"{e}.svg").write_text(mascot(e))
    for p in ["phone", "bill", "calculator", "coffee", "piggy", "card"]:
        (out / f"hold-{p}.svg").write_text(mascot("happy", "hold", p))
    for p in ["wave", "chin", "shrug", "cheer", "point"]:
        (out / f"pose-{p}.svg").write_text(mascot("happy", p))
    print("wrote", out)
