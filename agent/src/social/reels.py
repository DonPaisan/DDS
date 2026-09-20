"""Turn a carousel spec into a 9:16 Reel: each slide with a slow zoom, crossfades, and a
music bed from agent/assets/audio/ (drop in MP3s you hold a license for; Instagram's
own music library is not available through the API).

  python src/social/reels.py 2026-09-22-am --out 2026-09-22-pm-reel
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import AGENT_DIR, REPO_DIR  # noqa: E402
from social.htmlslides import render_carousel  # noqa: E402

AUDIO_DIR = AGENT_DIR / "assets" / "audio"
IMG_DIR = REPO_DIR / "site" / "social"
FPS = 30
W, H = 1080, 1920


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def pick_music(exclude: set[str] | None = None) -> Path | None:
    tracks = sorted(p for p in AUDIO_DIR.glob("*.mp3") if p.name not in (exclude or set()))
    return random.choice(tracks) if tracks else None


def placeholder_bed(path: Path, seconds: float) -> Path:
    """A soft synthesized pad for previews only. Never posted (needs_audio stays true)."""
    expr = "0.18*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.08*t)) + 0.10*sin(2*PI*165*t) + 0.08*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*0.05*t))"
    subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"aevalsrc={expr}:s=44100:d={seconds}",
                    "-af", "lowpass=f=900,afade=t=in:d=1.5,afade=t=out:st={:.1f}:d=2".format(max(0, seconds - 2)), "-c:a", "libmp3lame", "-q:a", "4", str(path)], check=True)
    return path


def build_reel(frames: list[Path], out: Path, music: Path | None, per_slide: float = 3.2, fade: float = 0.6, hold_last: float = 1.2) -> Path:
    n = len(frames)
    durs = [per_slide] * n
    durs[-1] += hold_last
    total = sum(durs) - fade * (n - 1)
    cmd = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"]
    for f, d in zip(frames, durs):
        cmd += ["-loop", "1", "-t", f"{d + fade:.2f}", "-i", str(f)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
    fc = []
    for i, d in enumerate(durs):
        frames_n = int((d + fade) * FPS)
        # slow push-in: 1.00 → 1.06 over the slide
        fc.append(f"[{i}:v]scale={W*2}:{H*2},zoompan=z='min(1+0.06*on/{frames_n},1.06)':d={frames_n}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},format=yuv420p[v{i}]")
    prev = "v0"
    offset = 0.0
    for i in range(1, n):
        offset += durs[i - 1]
        fc.append(f"[{prev}][v{i}]xfade=transition=fade:duration={fade}:offset={offset:.2f}[x{i}]")
        prev = f"x{i}"
    vmap = f"[{prev}]"
    if music:
        fc.append(f"[{n}:a]atrim=0:{total:.2f},volume=0.9,afade=t=in:d=1.2,afade=t=out:st={total-2:.2f}:d=2[a]")
    cmd += ["-filter_complex", ";".join(fc), "-map", vmap]
    if music:
        cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out


def reel_from_carousel(spec: dict, slug: str, out_slug: str, music: Path | None = None, preview_bed: bool = False) -> dict:
    frames = render_carousel(IMG_DIR / "frames", out_slug, spec, surface="reel")
    total = 3.2 * len(frames) + 1.2 - 0.6 * (len(frames) - 1)
    needs_audio = False
    if music is None:
        music = pick_music()
    if music is None and preview_bed:
        music = placeholder_bed(IMG_DIR / "frames" / f"{out_slug}-bed.mp3", total + 1)
        needs_audio = True
    elif music is None:
        needs_audio = True
    out = build_reel(frames, IMG_DIR / f"{out_slug}.mp4", music)
    return {"video": out, "cover": frames[0], "needs_audio": needs_audio, "music": music.name if music else None, "seconds": round(total, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("carousel_id")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview-bed", action="store_true", help="use a synthesized pad when no licensed track exists (preview only)")
    args = ap.parse_args(argv)
    for qf in sorted((AGENT_DIR / "social" / "queue").glob("*.json")):
        data = json.loads(qf.read_text())
        for p in data["posts"]:
            if p["id"] == args.carousel_id:
                r = reel_from_carousel(p["spec"], p["id"], args.out, preview_bed=args.preview_bed)
                print(json.dumps({k: str(v) for k, v in r.items()}, indent=2))
                return
    sys.exit("carousel not found")


if __name__ == "__main__":
    main()
