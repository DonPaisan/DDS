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
EY, LX, RX = 238, 170, 230


def _defs() -> str:
    return f"""<defs>
<radialGradient id="bagg" cx="38%" cy="30%" r="80%"><stop offset="0" stop-color="{YELLOW_LT}"/><stop offset=".55" stop-color="{YELLOW}"/><stop offset="1" stop-color="{YELLOW_DK}"/></radialGradient>
<radialGradient id="glove" cx="40%" cy="35%" r="70%"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#dfe4ea"/></radialGradient>
</defs>"""


def _bag() -> str:
    """One continuous sack: wide rounded base, sides tapering smoothly to a string tie, a small
    flare of cloth above the tie with three short points (the classic flat money-bag icon)."""
    return f"""
<path d="M178 156 C 148 186, 90 230, 80 310 C 72 368, 108 394, 200 394 C 292 394, 328 368, 320 310 C 310 230, 252 186, 222 156 Z" fill="url(#bagg)" stroke="{NAVY}" stroke-width="8" stroke-linejoin="round"/>
<path d="M110 348 q 10 14 26 10 M118 366 q 10 12 24 8" fill="none" stroke="{YELLOW_DK}" stroke-width="5" stroke-linecap="round" opacity=".6"/>
<path d="M226 200 C 262 236, 288 280, 296 330" fill="none" stroke="{YELLOW_DK}" stroke-width="10" stroke-linecap="round" opacity=".28"/>
<ellipse cx="150" cy="246" rx="24" ry="12" fill="{WHITE}" opacity=".25" transform="rotate(-40 150 246)"/>
<path d="M178 156 C 158 148, 138 132, 140 112 C 142 100, 158 100, 170 110 C 180 118, 186 128, 192 136 C 190 122, 192 106, 200 96 C 210 90, 220 102, 218 120 C 217 126, 216 132, 214 136 C 224 124, 240 112, 256 110 C 270 110, 272 124, 262 134 C 254 144, 240 152, 224 156 Z" fill="url(#bagg)" stroke="{NAVY}" stroke-width="8" stroke-linejoin="round"/>
<path d="M188 146 C 178 136, 168 126, 158 118 M203 146 C 204 132, 205 118, 206 106 M218 146 C 228 136, 240 126, 252 120" fill="none" stroke="{YELLOW_DK}" stroke-width="4" stroke-linecap="round" opacity=".55"/>
<path d="M170 160 C 186 154, 214 154, 230 160" fill="none" stroke="{NAVY}" stroke-width="7" stroke-linecap="round"/>
<path d="M172 169 C 188 163, 212 163, 228 169" fill="none" stroke="{NAVY}" stroke-width="7" stroke-linecap="round"/>
<circle cx="230" cy="165" r="7" fill="{NAVY}"/>
<path d="M234 170 C 250 176, 254 192, 248 210 M236 168 C 254 166, 264 178, 266 194" fill="none" stroke="{NAVY}" stroke-width="6" stroke-linecap="round"/>
"""


def _dollar() -> str:
    return f"""<text x="200" y="374" text-anchor="middle" font-family="Poppins, Arial, sans-serif" font-weight="800" font-size="60" fill="{YELLOW_DK}" stroke="{NAVY}" stroke-width="3">$</text>"""


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
        return (f'<path d="M160 {y-6} Q 200 {y+48} 240 {y-6} Z" fill="{NAVY}"/>'
                f'<path d="M166 {y-2} Q 200 {y+8} 234 {y-2} L 234 {y+6} Q 200 {y+16} 166 {y+6} Z" fill="{WHITE}"/>'
                f'<ellipse cx="200" cy="{y+26}" rx="15" ry="9" fill="{TONGUE}"/>')
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


def _glove(x: int, y: int, rot: float = 0, mirror: bool = False) -> str:
    """A cartoon four-finger glove: palm, three fingers, a thumb. Fingers point 'up' before rotation."""
    fingers = [(-12, -6, -15, -24), (0, -8, 0, -28), (12, -6, 15, -24)]
    thumb = (-13, 2, -27, -6)
    def layer(color, w):
        out = f'<circle cx="0" cy="0" r="{18 if w > 12 else 12}" fill="{color}"/>'
        for x1, y1, x2, y2 in fingers + [thumb]:
            out += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" stroke-linecap="round"/>'
        return out
    cuff = f'<path d="M-16 8 q 16 10 32 0" fill="none" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
    flip = " scale(-1 1)" if mirror else ""
    return f'<g transform="translate({x} {y}) rotate({rot:.0f}){flip}">{layer(NAVY, 20)}{layer(WHITE, 12)}{cuff}</g>'


def _fist(x: int, y: int, rot: float = 0, mirror: bool = False) -> str:
    """A closed cartoon hand gripping something: mitten palm, three knuckle bumps curling over the edge, a thumb across."""
    flip = " scale(-1 1)" if mirror else ""
    body = (f'<path d="M-20 -4 C -20 -18, -10 -24, 0 -24 C 12 -24, 22 -16, 22 -4 L 22 10 C 22 20, 12 24, 0 24 C -12 24, -20 18, -20 8 Z" fill="{WHITE}" stroke="{NAVY}" stroke-width="7" stroke-linejoin="round"/>'
            f'<path d="M-16 -2 a 8 8 0 0 1 14 0 M-2 -4 a 8 8 0 0 1 14 0 M11 0 a 7 7 0 0 1 11 2" fill="none" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M-14 12 C -6 8, 6 8, 16 12" fill="none" stroke="{NAVY}" stroke-width="5" stroke-linecap="round"/>'
            f'<path d="M-20 4 q 14 -2 26 4" fill="none" stroke="{NAVY}" stroke-width="4" stroke-linecap="round" opacity=".6"/>')
    return f'<g transform="translate({x} {y}) rotate({rot:.0f}){flip}">{body}</g>'


def _arm(side: str, pose: str) -> str:
    sx = 104 if side == "L" else 296
    sy = 300
    d = -1 if side == "L" else 1
    poses = {
        "rest":  (sx + d * 34, 352),
        "wave":  (sx + d * 62, 190) if side == "R" else (sx + d * 34, 352),
        "chin":  (200 - 34, 322) if side == "R" else (sx + d * 34, 352),
        "hold":  (200 + d * 46, 352),
        "shrug": (sx + d * 68, 262),
        "cheer": (sx + d * 62, 176),
        "point": (sx + d * 78, 250) if side == "R" else (sx + d * 34, 352),
    }
    hx, hy = poses.get(pose, poses["rest"])
    cx, cy = (sx + hx) / 2 + d * 20, (sy + hy) / 2 + 12
    import math
    along = math.degrees(math.atan2(hy - cy, hx - cx)) + 90   # fingers continue the arm's direction
    if pose == "hold":
        rot = -25 * d          # gripping the prop from below, fingers up and slightly inward
    elif pose == "chin":
        rot = -30 if side == "R" else along
    elif pose == "rest":
        rot = along + 35 * d   # hanging hands: fingers down and a little outward
    else:
        rot = along
    mirror = side == "R"       # thumb toward the body on both hands
    line = f'<path d="M{sx} {sy} Q {cx} {cy} {hx} {hy}" fill="none" stroke="{NAVY}" stroke-width="13" stroke-linecap="round"/>'
    hand = _fist(int(hx), int(hy), -15 * d, mirror) if pose == "hold" else _glove(int(hx), int(hy), rot, mirror)
    return line + hand


def _arm_parts(side: str, pose: str) -> tuple[str, str]:
    """(arm line, hand) so the hands can be layered in front of a held prop."""
    full = _arm(side, pose)
    k = full.index("<g ")
    return full[:k], full[k:]


def _legs() -> str:
    """Rubber-hose legs and big oval shoes, like the classic running money bag."""
    return f"""<path d="M170 390 C 166 398, 158 404, 150 408" fill="none" stroke="{NAVY}" stroke-width="14" stroke-linecap="round"/><path d="M230 390 C 234 398, 242 404, 250 408" fill="none" stroke="{NAVY}" stroke-width="14" stroke-linecap="round"/>
<ellipse cx="140" cy="414" rx="40" ry="16" fill="{NAVY}" transform="rotate(-8 140 410)"/><ellipse cx="260" cy="414" rx="40" ry="16" fill="{NAVY}" transform="rotate(8 260 410)"/>
<path d="M116 408 q 24 -8 46 -2" fill="none" stroke="#5a6b80" stroke-width="4" stroke-linecap="round" opacity=".7"/><path d="M238 406 q 22 -6 46 2" fill="none" stroke="#5a6b80" stroke-width="4" stroke-linecap="round" opacity=".7"/>"""


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
        return f'<path d="M286 216 q 12 16 0 28 q -12 -12 0 -28 z" fill="{BLUE}" stroke="{NAVY}" stroke-width="4"/>'
    return ""


def _thought(expr: str) -> str:
    if expr == "thinking":
        return f'<circle cx="290" cy="186" r="7" fill="{WHITE}" stroke="{NAVY}" stroke-width="5"/><circle cx="310" cy="160" r="11" fill="{WHITE}" stroke="{NAVY}" stroke-width="5"/>'
    return ""


def mascot(expr: str = "happy", pose: str = "rest", prop: str = "none", *, shadow: bool = True, size: int | None = None) -> str:
    """Full character SVG. Layers: shadow, back arm, body, dollar, legs, prop, front arm, face."""
    if prop != "none" and pose == "rest":
        pose = "hold"
    parts = [_defs()]
    if shadow:
        parts.append(f'<ellipse cx="200" cy="424" rx="112" ry="12" fill="{NAVY}" opacity=".12"/>')
    if pose == "hold":
        l_line, l_hand = _arm_parts("L", pose)
        r_line, r_hand = _arm_parts("R", pose)
        parts += [l_line, _bag(), _dollar(), _legs(), r_line, '<g transform="translate(0 8)">' + _prop(prop) + "</g>", l_hand, r_hand]
    else:
        parts += [_arm("L", pose), _bag(), _dollar(), _legs(), _arm("R", pose)]
    parts += [_cheeks(), _brows(expr), _eyes(expr), _mouth(expr), _sweat(expr), _thought(expr)]
    attrs = f'width="{size}" height="{size}"' if size else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="20 60 360 380" {attrs}>{"".join(parts)}</svg>'


if __name__ == "__main__":
    import sys
    from pathlib import Path
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/buck")
    out.mkdir(parents=True, exist_ok=True)
    for e in ["happy", "worried", "surprised", "thinking", "relieved", "determined", "sad", "wink", "big"]:
        (out / f"{e}.svg").write_text(mascot(e))
    print("wrote", out)
