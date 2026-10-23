#!/usr/bin/env python3
"""Acquire an authorized web video, verify it, and optionally extract keyframes."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def which(name: str) -> str | None:
    return shutil.which(name)


def tool_command(executable: str, module: str) -> list[str] | None:
    located = which(executable)
    if located:
        return [located]
    if importlib.util.find_spec(module):
        return [sys.executable, "-m", module]
    return None


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")


def emit(data: dict, code: int = 0) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def safe_tail(value: str, limit: int = 3000) -> str:
    return value[-limit:].strip()


def instagram_shortcode(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"instagram.com", "www.instagram.com"}:
        return None
    match = re.match(r"^/(?:p|reel|tv)/([^/?#]+)/?", parsed.path)
    return match.group(1) if match else None


def probe(path: Path) -> dict:
    proc = run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ])
    if proc.returncode:
        raise RuntimeError(f"ffprobe failed: {safe_tail(proc.stderr)}")
    data = json.loads(proc.stdout)
    if not any(stream.get("codec_type") == "video" for stream in data.get("streams", [])):
        raise RuntimeError("downloaded output has no video stream")
    return data


def extract_frames(media: Path, frame_dir: Path) -> tuple[list[str], str | None]:
    frame_dir.mkdir(parents=True, exist_ok=False)
    pattern = frame_dir / "frame_%03d.jpg"
    proc = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(media),
        "-vf", "select='gt(scene,0.28)',scale=960:-2", "-vsync", "vfr",
        "-frames:v", "24", "-q:v", "2", str(pattern),
    ])
    if proc.returncode:
        raise RuntimeError(f"frame extraction failed: {safe_tail(proc.stderr)}")
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    if not frames:
        fallback = run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(media),
            "-vf", "fps=1/5,scale=960:-2", "-frames:v", "12", "-q:v", "2", str(pattern),
        ])
        if fallback.returncode:
            raise RuntimeError(f"fallback frame extraction failed: {safe_tail(fallback.stderr)}")
        frames = sorted(frame_dir.glob("frame_*.jpg"))

    sheet = None
    magick = which("magick")
    if magick and frames:
        sheet_path = frame_dir.parent / "contact_sheet.jpg"
        montage = run([magick, "montage", *map(str, frames), "-tile", "4x", "-geometry", "+8+8", str(sheet_path)])
        if montage.returncode == 0 and sheet_path.exists():
            sheet = str(sheet_path.resolve())
    return [str(p.resolve()) for p in frames], sheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?")
    parser.add_argument("-o", "--output", default=".")
    parser.add_argument("--cookies-from-browser", choices=["chrome", "edge", "firefox", "brave", "chromium"])
    parser.add_argument("--instagram-user", help="Use an existing Instaloader session; never a password")
    parser.add_argument("--frames", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    ytdlp_cmd = tool_command("yt-dlp", "yt_dlp")
    instaloader_cmd = tool_command("instaloader", "instaloader")
    deps = {
        "yt-dlp": bool(ytdlp_cmd), "instaloader": bool(instaloader_cmd),
        "ffmpeg": bool(which("ffmpeg")), "ffprobe": bool(which("ffprobe")),
    }
    if args.check:
        emit({"status": "ok" if deps["ffmpeg"] and deps["ffprobe"] and (deps["yt-dlp"] or deps["instaloader"]) else "missing_dependency", "dependencies": deps})
    if not args.url:
        parser.error("url is required unless --check is used")
    if not deps["ffprobe"] or (args.frames and not deps["ffmpeg"]):
        emit({"status": "failed", "kind": "missing_dependency", "dependencies": deps}, 2)

    base = Path(args.output).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    job = base / ("web-video-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    job.mkdir()
    attempts: list[dict] = []
    media: Path | None = None
    downloader: str | None = None

    if deps["yt-dlp"]:
        cmd = [*ytdlp_cmd, "--no-playlist", "--no-overwrites", "--restrict-filenames", "--merge-output-format", "mp4", "--print", "after_move:filepath", "-o", str(job / "%(title).100s_%(id)s.%(ext)s")]
        if args.cookies_from_browser:
            cmd += ["--cookies-from-browser", args.cookies_from_browser]
        cmd.append(args.url)
        proc = run(cmd)
        attempts.append({"tool": "yt-dlp", "returncode": proc.returncode, "error": safe_tail(proc.stderr)})
        if proc.returncode == 0:
            candidates = [Path(line.strip()) for line in proc.stdout.splitlines() if line.strip()]
            existing = [p.resolve() for p in candidates if p.exists() and p.is_file()]
            if existing:
                media, downloader = existing[-1], "yt-dlp"

    shortcode = instagram_shortcode(args.url)
    if media is None and shortcode and deps["instaloader"]:
        cmd = [*instaloader_cmd, "--dirname-pattern", str(job), "--filename-pattern", "{date_utc}_UTC_{shortcode}", "--no-captions", "--no-metadata-json", "--no-compress-json"]
        if args.instagram_user:
            cmd += ["--login", args.instagram_user]
        cmd += ["--", "-" + shortcode]
        proc = run(cmd, cwd=job)
        attempts.append({"tool": "instaloader", "returncode": proc.returncode, "error": safe_tail(proc.stderr)})
        videos = sorted(job.rglob("*.mp4"), key=lambda p: p.stat().st_mtime)
        if proc.returncode == 0 and videos:
            media, downloader = videos[-1].resolve(), "instaloader"

    if media is None:
        emit({"status": "failed", "kind": "download_failed", "job_dir": str(job), "attempts": attempts, "dependencies": deps}, 1)

    try:
        media_probe = probe(media)
        frames: list[str] = []
        sheet = None
        if args.frames:
            frames, sheet = extract_frames(media, job / "frames")
    except Exception as exc:
        emit({"status": "failed", "kind": "verification_failed", "media_path": str(media), "error": str(exc), "attempts": attempts}, 1)

    emit({
        "status": "ok", "downloader": downloader, "media_path": str(media),
        "job_dir": str(job), "probe": media_probe, "frames": frames,
        "contact_sheet": sheet, "attempts": attempts,
    })


if __name__ == "__main__":
    main()
