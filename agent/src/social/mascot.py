"""Buck: the Debt Direct Solutions mascot, a classic animated money bag, drawn as SVG.

Vector, hand-built, deterministic: no generative imagery, so nothing for Meta to label.
Design cues from the classic animated money bag: a wide soft sack, a rope tied round the neck
with the cloth flaring above it in loose folds, a dollar on the belly, big eyes with coloured
irises and two highlights, gloved four-finger hands, sneakers, soft radial shading.

    mascot(expr="happy", pose="wave", prop="phone")  -> "<svg ...>...</svg>"

Expressions: happy, worried, surprised, thinking, relieved, determined, sad, wink, big (open-mouth grin).
Poses: rest, wave, chin, hold (holds the prop), shrug, cheer, point.
Props: phone, bill, calculator, coffee, piggy, letter, card, none.
"""
from __future__ import annotations

NAVY = "#1c2b3a"
YELLOW = "#ffd84d"
YELLOW_LT = "#ffe98a"
YELLOW_DK = "#e0ac1c"
BLUE = "#3b9cf6"
BLUE_DK = "#1c6fd1"
IRIS = "#2f7fd0"
ROPE = "#c98a3a"
ROPE_DK = "#8a5a1e"
WHITE = "#ffffff"
RED = "#e35d5b"
PINK = "#f28b8b"
TONGUE = "#e0575d"

# Face anchor points (body centre x=200). Eyes sit high on a wide face, Disney-style.
EY, LX, RX = 250, 168, 232


def _defs() -> str:
    return f"""<defs>
<radialGradient id="bagg" cx="38%" cy="30%" r="80%"><stop offset="0" stop-color="{YELLOW_LT}"/><stop offset=".55" stop-color="{YELLOW}"/><stop offset="1" stop-color="{YELLOW_DK}"/></radialGradient>
<radialGradient id="glove" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#dfe4ea"/></radialGradient>
</defs>"""


def _bag() -> str:
    """Sack body, rope, and the flared cloth above the rope."""
    return f"""
<path d="M148 190 C 92 214, 66 300, 96 348 C 122 388, 278 388, 304 348 C 334 300, 308 214, 252 190 C 232 180, 168 180, 148 190 Z" fill="url(#bagg)" stroke="{NAVY}" stroke-width="9" stroke-linejoin="round"/>
<path d="M116 322 C 150 366, 250 366, 284 322" fill="none" stroke="{YELLOW_DK}" stroke-width="8" stroke-linecap="round" opacity=".45"/>
<ellipse cx="150" cy="232" rx="26" ry="14" fill="{WHITE}" opacity=".28" transform="rotate(-30 150 232)"/>
<path d="M150 190 C 158 168, 242 168, 250 190 L 244 160 L 156 160 Z" fill="{YELLOW}" stroke="{NAVY}" stroke-width="9" stroke-linejoin="round"/>
<path d="M156 160 C 118 148, 122 108, 150 104 C 156 90, 176 84, 186 96 C 196 80, 220 82, 226 98 C 244 88, 266 100, 260 118 C 284 124, 282 154, 244 160 Z" fill="url(#bagg)" stroke="{NAVY}" stroke-width="9" stroke-linejoin="round"/>
<path d="M172 112 C 178 128, 178 146, 172 158 M200 100 C 204 120, 204 142, 200 158 M228 110 C 224 128, 224 146, 228 158" fill="none" stroke="{YELLOW_DK}" stroke-width="5" stroke-linecap="round" opacity=".75"/>
<path d="M146 168 C 168 156, 232 156, 254 168" fill="none" stroke="{ROPE}" stroke-width="16" stroke-linecap="round"/>
<path d="M146 168 C 168 156, 232 156, 254 168" fill="none" stroke="{ROPE_DK}" stroke-width="16" stroke-linecap="round" stroke-dasharray="6 9" opacity=".55"/>
<path d="M146 168 C 168 156, 232 156, 254 168" fill="none" stroke="{NAVY}" stroke-width="4" stroke-linecap="round" opacity=".35" transform="translate(0 8)"/>
<circle cx="254" cy="170" r="10" fill="{ROPE}" stroke="{NAVY}" stroke-width="5"/>
<path d="M258 178 q 16 10 10 30 M262 176 q 22 -2 30 14" fill="none" stroke="{ROPE}" stroke-width="8" stroke-linecap="round"/>
<path d="M258 178 q 16 10 10 30 M262 176 q 22 -2 30 14" fill="none" stroke="{NAVY}" stroke-width="3" stroke-linecap="round" opacity=".45"/>
"""


def _dollar() -> str:
    return f"""<text x="200" y="382" text-anchor="middle" font-family="Poppins, Arial, sans-serif" font-weight="800" font-size="52" fill="{YELLOW_DK}" stroke="{NAVY}" stroke-width="3">$</text>"""


def _eye(cx: int, look_x: int = 0, look_y: int = 0, scale: float = 1.0) -> str:
    rx, ry = 20 * scale, 25 * scale
    px, py = cx + look_x, EY + look_y
    return (f'<ellipse cx="{cx}" cy="{EY}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{WHITE}" stroke="{NAVY}" stroke-width="6"/>'
            f'<circle cx="{px}" cy="{py}" r="{12 * scale:.1f}" fill="{IRIS}"/><circle cx="{px}" cy="{py}" r="{7 * scale:.1f}" fill="{NAVY}"/>'
            f'<circle cx="{px - 4}" cy="{py - 5}" r="{3.6 * scale:.1f}" fill="{WHITE}"/><circle cx="{px + 4}" cy="{py + 4}" r="{1.8 * scale:.1f}" fill="{WHITE}"/>')


def _eyes(expr: str) -> str:
    if expr in ("happy", "relieved"):
        return (f'<path d="M{LX-20} {EY+4} Q {LX} {EY-22} {LX+20} {EY+4}" fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"/>'
                f'<path d="M{RX-20} {EY+4} Q {RX} {EY-22} {RX+20} {EY+4}" fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"/>')
    if expr == "wink":
        return _eye(LX, 2, 0) + f'<path d="M{RX-20} {EY} Q {RX} {EY+14} {RX+20} {EY}" fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"/>'
    if expr == "surprised":
        return _eye(LX, 0, 0, 1.25) + _eye(RX, 0, 0, 1.25)
    if expr == "thinking":
        return _eye(LX, 9, -7) + _eye(RX, 9, -7)
    if expr == "big":
        return _eye(LX, 0, 2, 1.1) + _eye(RX, 0, 2, 1.1)
    if expr in ("worried", "sad"):
        return _eye(LX, 0, 3) + _eye(RX, 0, 3)
    return _eye(LX, 2, 0) + _eye(RX, 2, 0)


def _brows(expr: str) -> str:
    y = EY - 40
    s = f'fill="none" stroke="{NAVY}" stroke-width="9" stroke-linecap="round"'
    if expr in ("worried", "sad"):
        return f'<path d="M{LX-20} {y+10} Q {LX} {y-2} {LX+16} {y-4}" {s}/><path d="M{RX-16} {y-4} Q {RX} {y-2} {RX+20} {y+10}" {s}/>'
    if expr == "determined":
        return f'<path d="M{LX-20} {y-8} Q {LX} {y-2} {LX+16} {y+8}" {s}/><path d="M{RX-16} {y+8} Q {RX} {y-2} {RX+20} {y-8}" {s}/>'
    if expr in ("surprised", "big"):
        return f'<path d="M{LX-20} {y-4} Q {LX} {y-22} {LX+20} {y-6}" {s}/><path d="M{RX-20} {y-6} Q {RX} {y-22} {RX+20} {y-4}" {s}/>'
    if expr == "thinking":
        return f'<path d="M{LX-20} {y+4} Q {LX} {y} {LX+18} {y+2}" {s}/><path d="M{RX-18} {y-10} Q {RX} {y-22} {RX+20} {y-8}" {s}/>'
    if expr == "wink":
        return f'<path d="M{LX-20} {y+2} Q {LX} {y-10} {LX+18} {y}" {s}/><path d="M{RX-18} {y+2} Q {RX} {y-8} {RX+20} {y+4}" {s}/>'
    return f'<path d="M{LX-20} {y+2} Q {LX} {y-10} {LX+18} {y}" {s}/><path d="M{RX-18} {y} Q {RX} {y-10} {RX+20} {y+2}" {s}/>'


def _mouth(expr: str) -> str:
    y = EY + 40
    s = f'fill="none" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"'
    if expr in ("happy", "wink"):
        return f'<path d="M168 {y} Q 200 {y+34} 232 {y}" {s}/>'
    if expr == "big":
        return (f'<path d="M160 {y-6} Q 200 {y+60} 240 {y-6} Z" fill="{NAVY}"/>'
                f'<path d="M166 {y-2} Q 200 {y+8} 234 {y-2} L 234 {y+6} Q 200 {y+16} 166 {y+6} Z" fill="{WHITE}"/>'
                f'<ellipse cx="200" cy="{y+34}" rx="16" ry="10" fill="{TONGUE}"/>')
    if expr == "relieved":
        return f'<path d="M174 {y} Q 200 {y+22} 226 {y}" {s}/>'
    if expr == "worried":
        return f'<path d="M176 {y+12} Q 200 {y-6} 224 {y+12}" {s}/>'
    if expr == "sad":
        return f'<path d="M172 {y+16} Q 200 {y-8} 228 {y+16}" {s}/>'
    if expr == "surprised":
        return f'<ellipse cx="200" cy="{y+8}" rx="14" ry="19" fill="{NAVY}"/><ellipse cx="200" cy="{y+16}" rx="8" ry="6" fill="{TONGUE}"/>'
    if expr == "thinking":
        return f'<path d="M184 {y+6} Q 200 {y+2} 218 {y}" {s}/>'
    if expr == "determined":
        return f'<path d="M178 {y+6} Q 200 {y+16} 222 {y+6}" {s}/>'
    return f'<path d="M182 {y+4} L 218 {y+4}" {s}/>'


def _cheeks() -> str:
    return f'<ellipse cx="138" cy="{EY+34}" rx="13" ry="8" fill="{PINK}" opacity=".45"/><ellipse cx="262" cy="{EY+34}" rx="13" ry="8" fill="{PINK}" opacity=".45"/>'


def _glove(x: int, y: int, rot: int = 0) -> str:
    """A four-finger cartoon glove."""
    return (f'<g transform="translate({x} {y}) rotate({rot})">'
            f'<path d="M-22 4 C -26 -12, -14 -24, -2 -22 C 6 -30, 20 -26, 22 -14 C 30 -10, 30 6, 20 12 C 16 24, -8 26, -20 16 Z" fill="url(#glove)" stroke="{NAVY}" stroke-width="7" stroke-linejoin="round"/>'
            f'<path d="M-6 -20 L -6 -6 M8 -22 L 8 -6" stroke="{NAVY}" stroke-width="4" stroke-linecap="round" opacity=".5"/>'
            f'<path d="M-14 16 q 14 -6 28 -2" fill="none" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/></g>')


def _arm(side: str, pose: str) -> str:
    sx = 112 if side == "L" else 288
    sy = 292
    d = -1 if side == "L" else 1
    poses = {
        "rest":  (sx + d * 34, 352),
        "wave":  (sx + d * 62, 190) if side == "R" else (sx + d * 34, 352),
        "chin":  (200 - 34, 322) if side == "R" else (sx + d * 34, 352),
        "hold":  (200 + d * 40, 360),
        "shrug": (sx + d * 68, 262),
        "cheer": (sx + d * 62, 176),
        "point": (sx + d * 78, 250) if side == "R" else (sx + d * 34, 352),
    }
    hx, hy = poses.get(pose, poses["rest"])
    cx, cy = (sx + hx) / 2 + d * 20, (sy + hy) / 2 + 12
    rot = {"wave": -20 * d, "cheer": -30 * d, "point": -60 * d, "shrug": -40 * d, "chin": 20}.get(pose, 0)
    return f'<path d="M{sx} {sy} Q {cx} {cy} {hx} {hy}" fill="none" stroke="{NAVY}" stroke-width="13" stroke-linecap="round"/>{_glove(int(hx), int(hy), rot)}'


def _legs() -> str:
    return f"""<path d="M170 376 L 166 398" stroke="{NAVY}" stroke-width="13" stroke-linecap="round"/><path d="M230 376 L 234 398" stroke="{NAVY}" stroke-width="13" stroke-linecap="round"/>
<path d="M132 404 C 132 392, 150 386, 166 388 C 182 388, 194 394, 194 404 C 194 412, 176 416, 160 416 C 144 416, 132 412, 132 404 Z" fill="{BLUE}" stroke="{NAVY}" stroke-width="6"/><path d="M136 408 q 30 8 56 0" fill="none" stroke="{WHITE}" stroke-width="5" stroke-linecap="round"/>
<path d="M206 404 C 206 394, 218 388, 234 388 C 250 386, 268 392, 268 404 C 268 412, 256 416, 240 416 C 224 416, 206 412, 206 404 Z" fill="{BLUE}" stroke="{NAVY}" stroke-width="6"/><path d="M208 408 q 30 8 56 0" fill="none" stroke="{WHITE}" stroke-width="5" stroke-linecap="round"/>"""


def _prop(name: str) -> str:
    """Drawn between the hands when pose == hold (centred near 200, 344)."""
    s = f'stroke="{NAVY}" stroke-width="7" stroke-linejoin="round"'
    if name == "phone":
        return f'<rect x="168" y="304" width="64" height="100" rx="12" fill="{NAVY}"/><rect x="176" y="314" width="48" height="76" rx="6" fill="{BLUE}"/>'
    if name in ("bill", "letter"):
        return f'<rect x="150" y="310" width="100" height="84" rx="6" fill="{WHITE}" {s}/><path d="M164 330 H 236 M164 348 H 236 M164 366 H 210" stroke="{NAVY}" stroke-width="6" stroke-linecap="round"/>' + (f'<text x="200" y="386" text-anchor="middle" font-family="Poppins, Arial" font-weight="800" font-size="20" fill="{RED}">DUE</text>' if name == "bill" else "")
    if name == "calculator":
        return f'<rect x="160" y="304" width="80" height="100" rx="10" fill="{NAVY}"/><rect x="170" y="314" width="60" height="22" rx="4" fill="{WHITE}"/>' + "".join(f'<circle cx="{180+i*20}" cy="{354+j*20}" r="6" fill="{YELLOW}"/>' for i in range(3) for j in range(2))
    if name == "coffee":
        return f'<path d="M170 320 H 230 L 224 386 H 176 Z" fill="{WHITE}" {s}/><path d="M230 332 C 252 332, 252 364, 228 364" fill="none" {s}/><path d="M188 314 q 3 -6 0 -11 M202 314 q 3 -6 0 -11" fill="none" stroke="{NAVY}" stroke-width="5" stroke-linecap="round" opacity=".6"/>'
    if name == "piggy":
        return f'<ellipse cx="200" cy="354" rx="52" ry="38" fill="#f7a8c4" {s}/><circle cx="240" cy="350" r="14" fill="#f7a8c4" {s}/><rect x="186" y="312" width="28" height="7" rx="3" fill="{NAVY}"/>'
    if name == "card":
        return f'<rect x="146" y="326" width="108" height="66" rx="8" fill="{BLUE}" {s}/><rect x="146" y="340" width="108" height="14" fill="{NAVY}"/><rect x="158" y="366" width="44" height="10" rx="3" fill="{WHITE}"/>'
    return ""


def _sweat(expr: str) -> str:
    if expr in ("worried", "sad"):
        return f'<path d="M282 214 q 12 16 0 28 q -12 -12 0 -28 z" fill="{BLUE}" stroke="{NAVY}" stroke-width="4"/>'
    return ""


def _thought(expr: str) -> str:
    if expr == "thinking":
        return f'<circle cx="300" cy="188" r="7" fill="{WHITE}" stroke="{NAVY}" stroke-width="5"/><circle cx="320" cy="162" r="11" fill="{WHITE}" stroke="{NAVY}" stroke-width="5"/>'
    return ""


def mascot(expr: str = "happy", pose: str = "rest", prop: str = "none", *, shadow: bool = True, size: int | None = None) -> str:
    """Full character SVG. Layers: shadow, back arm, body, dollar, legs, prop, front arm, face."""
    if prop != "none" and pose == "rest":
        pose = "hold"
    parts = [_defs()]
    if shadow:
        parts.append(f'<ellipse cx="200" cy="414" rx="100" ry="13" fill="{NAVY}" opacity=".12"/>')
    parts.append(_arm("L", pose))
    parts.append(_bag())
    parts.append(_dollar())
    parts.append(_legs())
    if pose == "hold":
        parts.append('<g transform="translate(0 16)">' + _prop(prop) + "</g>")
    parts.append(_arm("R", pose))
    parts += [_cheeks(), _brows(expr), _eyes(expr), _mouth(expr), _sweat(expr), _thought(expr)]
    attrs = f'width="{size}" height="{size}"' if size else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="50 70 300 360" {attrs}>{"".join(parts)}</svg>'


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/buck")
    out.mkdir(parents=True, exist_ok=True)
    for e in ["happy", "worried", "surprised", "thinking", "relieved", "determined", "sad", "wink", "big"]:
        (out / f"{e}.svg").write_text(mascot(e))
    print("wrote", out)
