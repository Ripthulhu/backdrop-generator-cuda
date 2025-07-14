# Jellyfin/Emby Backdrop Video Generator

Generates short `.mp4` backdrop videos for Jellyfin or Emby libraries using FFmpeg.

## 🎥 Features
- Adjustable length, resolution, and compression
- **Audio control**: Generate clips with or without audio (default: with audio)
- **Expert mode**: Add custom FFmpeg parameters for advanced users
- Avoids upscaling small sources
- Safe random clip offset (not from start or end)
- Automatically skips already processed files unless `--force` is used
- Optional daemon mode for periodic rescanning
- Failed attempt tracking with placeholder files

## 🚀 Usage

### Build the Docker image
```bash
docker build -t backdrop-generator .
```

### Run the generator
```docker compose up
```

### Generate silent clips
```
  Add the ENV var NO_AUDIO=true to the compose file
```


### Example Flags & Environment Variables
- `--length` / `LENGTH`: Clip duration in seconds (default: 5)
- `--resolution` / `RESOLUTION`: 720 or 1080 (default: 720)
- `--crf` / `CRF`: Compression factor (lower is better quality; default: 28)
- `--force` / `FORCE`: Regenerate even if backdrop exists (default: false)
- `--timeout` / `TIMEOUT`: Timeout per FFmpeg call in seconds (default: 300)
- `--no-audio` / `NO_AUDIO`: Generate clips without audio (default: false)
- `--ffmpeg-extra` / `FFMPEG_EXTRA`: Custom FFmpeg parameters for expert users

## 🔧 Advanced Configuration

### Audio Options
By default, clips include audio encoded with AAC. To generate silent clips:
- Set `NO_AUDIO=true` environment variable, or
- Use `--no-audio` flag when running directly

### Expert Mode
Add custom FFmpeg parameters using the `FFMPEG_EXTRA` environment variable:
```bash
# Example: Add fast start flag and specific pixel format
FFMPEG_EXTRA="-movflags +faststart -pix_fmt yuv420p"

# Example: Tune for film content with high profile
FFMPEG_EXTRA="-tune film -profile:v high"

# Example: Custom bitrate control
FFMPEG_EXTRA="-maxrate 2M -bufsize 4M"
```

**Note**: Custom parameters are added to the FFmpeg command line. Use quotes for parameters with spaces.

## 🐳 Dockerfile Based
This script uses FFmpeg inside a lightweight Python 3 image with minimal dependencies.

## ✅ Compatible with
- Jellyfin
- Emby

## 📜 License
MIT
