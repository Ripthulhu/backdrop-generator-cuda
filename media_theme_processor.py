#!/usr/bin/env python3
"""media_backdrop_processor.py
Generate short backdrop clips for Emby/Jellyfin libraries.

Features
========
* Adjustable **clip length** (`--length`, default 5 s).
* Selectable **resolution** 720 p or 1080 p (`--resolution`, default 720).
  The filter only downsizes → no up‑scaling of small sources.
* Tunable **compression** via CRF (`--crf`, default 28) and preset
  (`--preset`, default *veryfast*).
* **Overwrite** mode (`--force`) to re‑generate even if the backdrop exists
  or a *.failed* placeholder is present.
* Optional **per‑folder delay** (`--delay`, default 0 s).
* Daemon mode with re‑scan interval just as before.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "media_processor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BACKDROP_TIMEOUT_DEFAULT = 300  # seconds per FFmpeg call
PLACEHOLDER_SUFFIX = ".failed"  # mark failed attempts
VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}

# ---------------------------------------------------------------------------
# Processor class
# ---------------------------------------------------------------------------


class MediaBackdropProcessor:
    """Create backdrop clips for movie & TV folders."""

    def __init__(
        self,
        movies_path: str,
        tv_path: str,
        *,
        timeout: int,
        clip_len: int,
        resolution: int,
        crf: int,
        preset: str,
        delay: float,
        force: bool,
    ) -> None:
        self.movies_path = Path(movies_path)
        self.tv_path = Path(tv_path)
        self.timeout = timeout
        self.clip_len = clip_len
        self.resolution = resolution  # 720 or 1080
        self.crf = crf
        self.preset = preset
        self.delay = delay
        self.force = force

        self.width, self.height = (1280, 720) if resolution == 720 else (1920, 1080)

    @staticmethod
    def _touch_placeholder(target: Path) -> None:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            (target.with_suffix(target.suffix + PLACEHOLDER_SUFFIX)).touch(exist_ok=True)
        except Exception as exc:
            logger.error("Could not create placeholder for %s: %s", target, exc)

    @staticmethod
    def _video_duration(video: Path) -> float:
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                str(video),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(json.loads(result.stdout)["format"]["duration"])
        except Exception as exc:
            logger.warning("Duration error for %s: %s", video, exc)
            return 0.0

    def _extract_clip(self, src: Path, dst: Path) -> bool:
        total = self._video_duration(src)
        if total < 60:
            logger.info("Video too short: %s", src)
            return False

        start_safe, end_safe = total * 0.1, total * 0.5
        if end_safe - start_safe < self.clip_len:
            logger.info("Insufficient safe range in %s", src)
            return False

        start = random.uniform(start_safe, end_safe - self.clip_len)
        dst.parent.mkdir(parents=True, exist_ok=True)

        scale_pad = (
            f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
            f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2"
        )

        ff_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start}",
            "-i",
            str(src),
            "-t",
            str(self.clip_len),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-vf",
            scale_pad,
            "-preset",
            self.preset,
            "-crf",
            str(self.crf),
            "-avoid_negative_ts",
            "make_zero",
            str(dst),
        ]

        try:
            subprocess.run(ff_cmd, capture_output=True, text=True, timeout=self.timeout, check=True)
            logger.info("Backdrop created: %s", dst)
            return True
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out (%ss) for %s", self.timeout, src)
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg error for %s: %s", src, exc.stderr or exc)
        except Exception as exc:
            logger.error("Unexpected error for %s: %s", src, exc)

        self._touch_placeholder(dst)
        return False

    @staticmethod
    def _find_videos(folder: Path) -> List[Path]:
        return sorted(p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXTS)

    def _find_first_ep(self, show: Path) -> Optional[Path]:
        seasons = [d for d in show.iterdir() if d.is_dir() and "season" in d.name.lower()]
        season1 = next((d for d in seasons if "01" in d.name or "season 1" in d.name.lower()), None) or (
            seasons[0] if seasons else None
        )
        for folder in ([season1] if season1 else [show]):
            vids = self._find_videos(folder)
            if not vids:
                continue
            for v in vids:
                l = v.name.lower()
                if "e01" in l or "episode 1" in l:
                    return v
            return vids[0]
        return None

    def _process(self, folder: Path, is_tv: bool) -> None:
        label = "TV" if is_tv else "Movie"
        logger.info("Processing %s: %s", label, folder.name)

        dst = folder / "backdrops" / "backdrop.mp4"
        placeholder = dst.with_suffix(dst.suffix + PLACEHOLDER_SUFFIX)

        if not self.force and (dst.exists() or placeholder.exists()):
            logger.debug("Backdrop already present for %s", folder.name)
            return

        if self.force:
            if dst.exists():
                dst.unlink(missing_ok=True)
            if placeholder.exists():
                placeholder.unlink(missing_ok=True)

        src: Optional[Path]
        if is_tv:
            src = self._find_first_ep(folder)
        else:
            vids = self._find_videos(folder)
            src = max(vids, key=lambda p: p.stat().st_size) if vids else None

        if not src:
            logger.warning("No video found in %s", folder)
            self._touch_placeholder(dst)
            return

        self._extract_clip(src, dst)

        if self.delay:
            time.sleep(self.delay)

    def run_once(self) -> None:
        if not self.movies_path.exists() and not self.tv_path.exists():
            logger.error("Both movies and TV paths are missing – nothing to do.")
            return

        if self.movies_path.exists():
            for f in (d for d in self.movies_path.iterdir() if d.is_dir()):
                try:
                    self._process(f, is_tv=False)
                except Exception as exc:
                    logger.error("Error processing movie %s: %s", f.name, exc)

        if self.tv_path.exists():
            for f in (d for d in self.tv_path.iterdir() if d.is_dir()):
                try:
                    self._process(f, is_tv=True)
                except Exception as exc:
                    logger.error("Error processing TV show %s: %s", f.name, exc)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate backdrop clips for Emby/Jellyfin.")
    p.add_argument("--movies", required=True, help="Path to the movies directory")
    p.add_argument("--tv", required=True, help="Path to the TV‑shows directory")

    p.add_argument("--daemon", action="store_true", help="Run continuously and rescan on an interval")
    p.add_argument("--interval", type=int, default=3600, help="Seconds between scans when --daemon is set")

    p.add_argument("--length", type=int, default=5, help="Clip length in seconds (default 5)")
    p.add_argument("--resolution", type=int, choices=[720, 1080], default=720, help="Output resolution (default 720)")
    p.add_argument("--crf", type=int, default=28, help="x264 CRF value (default 28 → smaller file)")
    p.add_argument("--preset", default="veryfast", help="x264 preset (default 'veryfast')")

    p.add_argument("--timeout", type=int, default=BACKDROP_TIMEOUT_DEFAULT, help="FFmpeg timeout in seconds")
    p.add_argument("--delay", type=float, default=0, help="Seconds to wait after each folder")
    p.add_argument("--force", action="store_true", help="Overwrite existing backdrops and ignore placeholders")

    return p.parse_args()


def main() -> None:
    args = parse_cli()

    processor = MediaBackdropProcessor(
        args.movies,
        args.tv,
        timeout=args.timeout,
        clip_len=args.length,
        resolution=args.resolution,
        crf=args.crf,
        preset=args.preset,
        delay=args.delay,
        force=args.force,
    )

    if args.daemon:
        logger.info(
            "Daemon mode – interval:%ds len:%ds res:%dp crf:%d preset:%s",
            args.interval,
            args.length,
            args.resolution,
            args.crf,
            args.preset,
        )
        try:
            while True:
                processor.run_once()
                logger.info("Sleeping …")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
    else:
        processor.run_once()


if __name__ == "__main__":
    main()
