#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
media_backdrop_processor.py – generate short backdrop clips for Emby/Jellyfin.
(Feature list unchanged for brevity)
"""
from __future__ import annotations

import argparse, json, logging, random, shlex, subprocess, sys, time
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "media_processor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BACKDROP_TIMEOUT_DEFAULT = 300
PLACEHOLDER_SUFFIX = ".failed"
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}


class MediaBackdropProcessor:
    def __init__(
        self,
        movies_path: str,
        tv_path: str,
        anime_path: Optional[str],
        *,
        timeout: int,
        clip_len: int,
        resolution: int,
        crf: int,
        preset: str,
        delay: float,
        force: bool,
        include_audio: bool,
        ffmpeg_extra: str,
        ffmpeg_pre: str,
    ) -> None:
        self.movies_path = Path(movies_path)
        self.tv_path = Path(tv_path)
        self.anime_path = Path(anime_path) if anime_path else None
        self.timeout = timeout
        self.clip_len = clip_len
        self.resolution = resolution
        self.crf = crf
        self.preset = preset
        self.delay = delay
        self.force = force
        self.include_audio = include_audio
        self.ffmpeg_extra = ffmpeg_extra
        self.ffmpeg_pre = ffmpeg_pre
        self.width, self.height = (1280, 720) if resolution == 720 else (1920, 1080)

    # ---------- helpers --------------------------------------------------
    @staticmethod
    def _touch_placeholder(p: Path) -> None:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            (p.with_suffix(p.suffix + PLACEHOLDER_SUFFIX)).touch(exist_ok=True)
        except Exception as exc:
            logger.error("Could not create placeholder for %s: %s", p, exc)

    @staticmethod
    def _video_duration(video: Path) -> float:
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", str(video)],
                text=True,
            )
            return float(json.loads(out)["format"]["duration"])
        except Exception as exc:
            logger.warning("Duration error for %s: %s", video, exc)
            return 0.0

    @staticmethod
    def _codec_name(video: Path) -> str:
        try:
            out = subprocess.check_output(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_name", "-of", "default=nw=1",
                 str(video)],
                text=True,
            )
            return out.strip().split("=")[-1].lower()
        except Exception:
            return ""

    # ---------- core FFmpeg call ----------------------------------------
    def _extract_clip(self, src: Path, dst: Path) -> bool:
        total = self._video_duration(src)
        if total < 60:
            logger.info("Video too short: %s", src); return False

        start_safe, end_safe = total * 0.1, total * 0.5
        if end_safe - start_safe < self.clip_len:
            logger.info("Insufficient safe range in %s", src); return False

        start = random.uniform(start_safe, end_safe - self.clip_len)
        dst.parent.mkdir(parents=True, exist_ok=True)

        codec = self._codec_name(src)
        use_hwaccel = self.ffmpeg_pre and codec != "av1"

        if use_hwaccel:
            vf_chain = (
                f"scale_cuda={self.width}:{self.height}"
                f":interp_algo=lanczos:format=nv12"
            )
        else:
            vf_chain = (
                f"format=yuv420p,"
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2"
            )

        ff_cmd: list[str] = ["ffmpeg", "-y"]
        if use_hwaccel:
            ff_cmd.extend(shlex.split(self.ffmpeg_pre))

        ff_cmd.extend(
            [
                "-ss", f"{start}",
                "-i", str(src),
                "-t", str(self.clip_len),
                "-c:v", "libx264",
                "-vf", vf_chain,
                "-preset", self.preset,
                "-crf", str(self.crf),
                "-avoid_negative_ts", "make_zero",
            ]
        )

        ff_cmd.extend(["-c:a", "aac"] if self.include_audio else ["-an"])
        if self.ffmpeg_extra:
            try:
                ff_cmd.extend(shlex.split(self.ffmpeg_extra))
            except ValueError as exc:
                logger.warning("Bad FFmpeg extra args '%s': %s", self.ffmpeg_extra, exc)

        ff_cmd.append(str(dst))

        try:
            subprocess.run(ff_cmd, capture_output=True, text=True,
                           timeout=self.timeout, check=True)
            logger.info("Backdrop created: %s", dst); return True
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out (%s s) for %s", self.timeout, src)
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg error for %s: %s", src, exc.stderr or exc)
        except Exception as exc:
            logger.error("Unexpected error for %s: %s", src, exc)

        self._touch_placeholder(dst); return False

    # ---------- discovery helpers ---------------------------------------
    @staticmethod
    def _find_videos(folder: Path) -> List[Path]:
        return sorted(p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXTS)

    def _find_first_ep(self, show: Path) -> Optional[Path]:
        seasons = [d for d in show.iterdir() if d.is_dir() and "season" in d.name.lower()]
        season1 = next((d for d in seasons if "01" in d.name or "season 1" in d.name.lower()), None) or \
                  (seasons[0] if seasons else None)
        for folder in ([season1] if season1 else [show]):
            vids = self._find_videos(folder)
            if not vids: continue
            for v in vids:
                if any(tag in v.name.lower() for tag in ("e01", "episode 1")):
                    return v
            return vids[0]
        return None

    # ---------- processing and run loop ----------------------------------
    def _process(self, folder: Path, is_tv: bool) -> None:
        label = "TV/Anime" if is_tv else "Movie"
        logger.info("Processing %s: %s", label, folder.name)

        dst = folder / "backdrops" / "backdrop.mp4"
        placeholder = dst.with_suffix(dst.suffix + PLACEHOLDER_SUFFIX)
        if not self.force and (dst.exists() or placeholder.exists()):
            logger.debug("Backdrop already present for %s", folder.name); return
        if self.force:
            dst.unlink(missing_ok=True); placeholder.unlink(missing_ok=True)

        src = self._find_first_ep(folder) if is_tv else (
            max(self._find_videos(folder), key=lambda p: p.stat().st_size) if self._find_videos(folder) else None
        )
        if not src:
            logger.warning("No video found in %s", folder); self._touch_placeholder(dst); return

        self._extract_clip(src, dst)
        if self.delay: time.sleep(self.delay)

    def run_once(self) -> None:
        roots = [(self.movies_path, False), (self.tv_path, True)]
        if self.anime_path: roots.append((self.anime_path, True))

        valid = False
        for root, is_tv in roots:
            if root and root.exists():
                valid = True
                for f in (d for d in root.iterdir() if d.is_dir()):
                    try: self._process(f, is_tv)
                    except Exception as exc:
                        logger.error("Error processing %s %s: %s",
                                     "TV/anime show" if is_tv else "movie", f.name, exc)
        if not valid: logger.error("No valid library paths found - nothing to do.")

# ---------- CLI / main --------------------------------------------------
def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate backdrop clips for Emby/Jellyfin.")
    p.add_argument("--movies", required=True, help="Movies directory")
    p.add_argument("--tv", required=True, help="TV-shows directory")
    p.add_argument("--anime", help="Optional Anime directory (treated like TV)")
    p.add_argument("--daemon", action="store_true", help="Run continuously")
    p.add_argument("--interval", type=int, default=3600, help="Seconds between scans")
    p.add_argument("--length", type=int, default=5, help="Clip length")
    p.add_argument("--resolution", type=int, choices=[720, 1080], default=720, help="Output resolution")
    p.add_argument("--crf", type=int, default=28, help="x264 CRF value")
    p.add_argument("--preset", default="veryfast", help="x264 preset")
    p.add_argument("--no-audio", action="store_true", help="Generate clips without audio")
    p.add_argument("--ffmpeg-extra", default="", help="Extra FFmpeg parameters after output file")
    p.add_argument("--ffmpeg-pre", default="", help="Extra FFmpeg parameters before -i")
    p.add_argument("--timeout", type=int, default=BACKDROP_TIMEOUT_DEFAULT, help="FFmpeg timeout")
    p.add_argument("--delay", type=float, default=0, help="Seconds to wait per folder")
    p.add_argument("--force", action="store_true", help="Overwrite existing backdrops")
    return p.parse_args()

def main() -> None:
    a = parse_cli()
    proc = MediaBackdropProcessor(
        a.movies, a.tv, a.anime,
        timeout=a.timeout, clip_len=a.length, resolution=a.resolution,
        crf=a.crf, preset=a.preset, delay=a.delay, force=a.force,
        include_audio=not a.no_audio, ffmpeg_extra=a.ffmpeg_extra, ffmpeg_pre=a.ffmpeg_pre,
    )
    aud = "with audio" if not a.no_audio else "without audio"
    extra = (f" pre:{a.ffmpeg_pre}" if a.ffmpeg_pre else "") + (f" post:{a.ffmpeg_extra}" if a.ffmpeg_extra else "")
    if a.daemon:
        logger.info("Daemon mode interval:%ds %s%s", a.interval, aud, extra)
        try:
            while True:
                proc.run_once(); logger.info("Sleeping ..."); time.sleep(a.interval)
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
    else:
        logger.info("Single run mode %s%s", aud, extra); proc.run_once()

if __name__ == "__main__":
    main()
