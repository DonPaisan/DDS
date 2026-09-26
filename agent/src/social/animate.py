"""Animated Buck comics as Reels, with no generative video: the mascot's SVG parts are animated
with CSS keyframes (bob, blink, wave, sweat drop, bubble pop), every frame is a Chromium
screenshot at a fixed time, and ffmpeg stitches the frames into a 9:16 video.

  python src/social/animate.py 2026-09-26-comic --out 2026-09-26-comic-reel

Deterministic, on-brand, nothing for Meta to label. Music comes from agent/assets/audio/ when
present; otherwise a placeholder bed is used and the queue entry stays needs_audio=true.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, REPO_DIR  # noqa: E402
from social import htmlslides as H  # noqa: E402
from social.reels import ffmpeg, pick_music, placeholder_bed  # noqa: E402

IMG_DIR = REPO_DIR / "site" / "social"
FPS = 12

ANIM_CSS = """
/* time is frozen per frame: every animation is paused and offset by --t seconds */
.anim * { animation-play-state: paused !important; }
.anim .buck { animation: enter .7s cubic-bezier(.2,1.3,.4,1) both; animation-delay: calc(0s - 1s * var(--t)); }
@keyframes enter { from { transform: translateY(140px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.anim .buck svg { animation: bob 2.4s ease-in-out infinite; animation-delay: calc(.7s - 1s * var(--t)); transform-origin: 50% 100%; }
@keyframes bob { 0%, 100% { transform: translateY(0) scale(1, 1); } 50% { transform: translateY(-10px) scale(.985, 1.015); } }
.anim .buck svg .eyes { transform-box: view-box; transform-origin: 200px 250px; animation: blink 3.4s infinite; animation-delay: calc(1.1s - 1s * var(--t)); }
@keyframes blink { 0%, 91%, 100% { transform: scaleY(1); } 94% { transform: scaleY(.06); } 97% { transform: scaleY(1); } }
.anim .buck svg.pose-wave .arm-R, .anim .buck svg.pose-cheer .arm-R, .anim .buck svg.pose-cheer .arm-L, .anim .buck svg.pose-point .arm-R { transform-box: view-box; animation: wave 1.1s ease-in-out infinite; animation-delay: calc(.7s - 1s * var(--t)); }
.anim .buck svg .arm-R { transform-origin: 296px 300px; }
.anim .buck svg .arm-L { transform-origin: 104px 300px; }
@keyframes wave { 0%, 100% { transform: rotate(0deg); } 50% { transform: rotate(-14deg); } }
.anim .buck svg.pose-cheer .arm-L { animation-name: wave-l; }
@keyframes wave-l { 0%, 100% { transform: rotate(0deg); } 50% { transform: rotate(14deg); } }
.anim .buck svg .sweat { animation: drop 1.5s ease-in infinite; animation-delay: calc(.9s - 1s * var(--t)); }
@keyframes drop { 0% { transform: translateY(0); opacity: 1; } 80% { opacity: 1; } 100% { transform: translateY(70px); opacity: 0; } }
.anim .buck svg .thought { animation: pulse 1.6s ease-in-out infinite; animation-delay: calc(.9s - 1s * var(--t)); }
@keyframes pulse { 0%, 100% { opacity: .4; } 50% { opacity: 1; } }
.anim .buck svg.pose-hold .prop, .anim .buck svg.pose-hold .hand { transform-box: view-box; transform-origin: 200px 350px; animation: hold 2.4s ease-in-out infinite; animation-delay: calc(.7s - 1s * var(--t)); }
@keyframes hold { 0%, 100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-6px) rotate(-1.5deg); } }
.anim .bubble { animation: pop .45s cubic-bezier(.2,1.5,.4,1) both; animation-delay: calc(.6s - 1s * var(--t)); transform-origin: 20% 100%; }
@keyframes pop { from { transform: scale(0); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.anim .cap, .anim .cap.bottom { animation: fade .4s ease both; animation-delay: calc(.2s - 1s * var(--t)); }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
.anim .fx { animation: slam .35s cubic-bezier(.2,1.6,.4,1) both; animation-delay: calc(1.0s - 1s * var(--t)); }
@keyframes slam { from { transform: rotate(-12deg) scale(2.2); opacity: 0; } to { transform: rotate(-12deg) scale(1); opacity: 1; } }
"""


def panel_html(spec: dict, i: int, total: int, t: float) -> str:
    s = spec["slides"][i - 2]
    v = H.variant(spec.get("_slug", "anim"), spec.get("variant"))
    cls = H.variant_classes(v, body=True) + " anim"
    html = H.slide_comic(s, i, total, "white", spec["kicker"], "reel", cls)
    return html.replace("</style>", ANIM_CSS + f":root{{--t:{t:.4f}}}</style>", 1)


def render_frames(spec: dict, slug: str, out_dir: Path, seconds: float = 3.6, cover: bool = True, cta_seconds: float = 2.5, still_seconds: float = 3.2) -> list[tuple[Path, float]]:
    """Returns [(frame_or_still_path, duration_seconds)] in order: cover, animated panels, lesson, cta."""
    spec = dict(spec, _slug=slug)
    slides = spec["slides"]
    total = len(slides) + 2
    stills = H.render_carousel(out_dir / "stills", slug, spec, surface="reel")   # 9:16 stills of every slide
    seq: list[tuple[Path, float]] = [(stills[0], 2.2)] if cover else []
    jobs, frames_dir = [], out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="dds-anim-"))
    n_frames = int(seconds * FPS)
    for i, s in enumerate(slides, start=2):
        if s["kind"] != "comic":
            seq.append((stills[i - 1], still_seconds))
            continue
        for k in range(n_frames):
            hp = tmp / f"{slug}-{i:02d}-{k:03d}.html"
            hp.write_text(panel_html(spec, i, total, k / FPS), encoding="utf-8")
            op = frames_dir / f"{slug}-{i:02d}-{k:03d}.jpg"
            jobs.append({"html": str(hp), "out": str(op), "width": 1080, "height": 1920})
        seq.append((frames_dir / f"{slug}-{i:02d}-%03d.jpg", seconds))
    seq.append((stills[-1], cta_seconds))
    jf = tmp / "jobs.json"
    jf.write_text(json.dumps(jobs))
    env = {**os.environ, "NODE_PATH": os.environ.get("NODE_PATH", "") + ":/opt/node22/lib/node_modules:" + str(REPO_DIR / "node_modules")}
    r = subprocess.run(["node", str(H.HERE / "render.mjs"), str(jf)], capture_output=True, text=True, env=env, cwd=REPO_DIR)
    if r.returncode != 0:
        raise RuntimeError(f"frame render failed: {r.stderr[-1500:]}")
    return seq


def build_video(seq: list[tuple[Path, float]], out: Path, music: Path | None) -> Path:
    """Each item becomes a clip (still → looped image, pattern → image sequence); clips are concatenated."""
    tmp = Path(tempfile.mkdtemp(prefix="dds-anim-clips-"))
    clips = []
    for n, (src, dur) in enumerate(seq):
        clip = tmp / f"clip{n:02d}.mp4"
        if "%03d" in str(src):
            cmd = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(FPS), "-i", str(src), "-t", f"{dur:.2f}"]
        else:
            cmd = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(src), "-t", f"{dur:.2f}"]
        cmd += ["-vf", "scale=1080:1920,format=yuv420p", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-an", str(clip)]
        subprocess.run(cmd, check=True)
        clips.append(clip)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    cmd = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music), "-shortest", "-c:a", "aac", "-b:a", "128k", "-af", "afade=t=out:st={:.1f}:d=1.5".format(max(0, sum(d for _, d in seq) - 1.5))]
    cmd += ["-c:v", "copy", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out


def animate_comic(spec: dict, slug: str, out_slug: str, music: Path | None = None, preview_bed: bool = False) -> dict:
    work = IMG_DIR / "anim" / out_slug
    seq = render_frames(spec, out_slug, work)
    total = sum(d for _, d in seq)
    needs_audio = False
    if music is None:
        music = pick_music()
    if music is None and preview_bed:
        music = placeholder_bed(work / f"{out_slug}-bed.mp3", total + 1)
        needs_audio = True
    elif music is None:
        needs_audio = True
    out = build_video(seq, IMG_DIR / f"{out_slug}.mp4", music)
    return {"video": out, "cover": seq[0][0], "seconds": round(total, 1), "needs_audio": needs_audio, "music": music.name if music else None}


def animate_clip(spec: dict, out_slug: str, music: Path | None = None, preview_bed: bool = False, seconds: float = 3.2) -> dict:
    """A short tip clip (10-15 s): no cover, one or two animated panels, a lesson still, the follow card."""
    work = IMG_DIR / "anim" / out_slug
    seq = render_frames(spec, out_slug, work, seconds=seconds, cover=False, cta_seconds=1.8, still_seconds=2.6)
    total = sum(d for _, d in seq)
    needs_audio = False
    if music is None:
        music = pick_music()
    if music is None and preview_bed:
        music = placeholder_bed(work / f"{out_slug}-bed.mp3", total + 1)
        needs_audio = True
    elif music is None:
        needs_audio = True
    out = build_video(seq, IMG_DIR / f"{out_slug}.mp4", music)
    return {"video": out, "cover": seq[0][0], "seconds": round(total, 1), "needs_audio": needs_audio, "music": music.name if music else None}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("comic_id")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview-bed", action="store_true")
    args = ap.parse_args(argv)
    for qf in sorted((AGENT_DIR / "social" / "queue").glob("*.json")):
        for p in json.loads(qf.read_text())["posts"]:
            if p["id"] == args.comic_id:
                r = animate_comic(p["spec"], p["id"], args.out, preview_bed=args.preview_bed)
                print(json.dumps({k: str(v) for k, v in r.items()}, indent=2))
                return
    sys.exit("comic not found")


if __name__ == "__main__":
    main()
