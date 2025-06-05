# Jellyfin/Emby Backdrop Video Generator

Generates short `.mp4` backdrop videos for Jellyfin or Emby libraries using FFmpeg.

## 🎥 Features
- Adjustable length, resolution, and compression
- Avoids upscaling small sources
- Safe random clip offset (not from start or end)
- Automatically skips already processed files unless `--force` is used
- Optional daemon mode for periodic rescanning

## 🚀 Usage

### Build the Docker image
```bash
docker build -t backdrop-generator .
```

### Run the generator
```bash
docker run --rm \
  -v /path/to/Movies:/movies \
  -v /path/to/TV:/tv \
  backdrop-generator \
  --movies /movies \
  --tv /tv \
  --length 5 \
  --resolution 720 \
  --crf 28 \
  --force \
  --timeout 30
```

### Example Flags
- `--length`: Clip duration in seconds (default: 5)
- `--resolution`: 720 or 1080 (default: 720)
- `--crf`: Compression factor (lower is better quality; default: 28)
- `--force`: Regenerate even if backdrop exists
- `--timeout`: Timeout per FFmpeg call in seconds

## 🐳 Dockerfile Based
This script uses FFmpeg inside a lightweight Python 3 image with minimal dependencies.

## ✅ Compatible with
- Jellyfin
- Emby

## 📜 License
MIT
