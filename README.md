# Jellyfin / Emby **GPU** Backdrop Video Generator

A Docker-packaged tool that creates short `.mp4` back‑drop videos for your Jellyfin or Emby libraries.  
**This fork is fully hardware‑accelerated**: it decodes with **NVDEC**, scales with **CUDA**, and encodes with **NVENC**

---

## 🎥 Key features

|  |  |
| --- | --- |
| **Full‑GPU pipeline** – NVDEC → `scale_cuda` → NVENC (falls back to CPU only for formats the GPU can’t decode, e.g. AV1 on older cards). |
| Adjustable clip **length**, **resolution** (720 p / 1080 p), and **quality** (CRF & preset). |
| **No up‑scaling** of small sources – the script only downsizes. |
| Safe random **offset** (clips are cut from 10–50 % into the video). |
| Optional **audio strip** (`NO_AUDIO=true`) or AAC re‑encode. |
| **Force** re‑generate, timeout, placeholder tracking on errors. |
| **Daemon mode** – rescans libraries on a schedule. |
| **Anime library** supported alongside Movies & TV. |
| Expert **FFmpeg override** flags (`FFMPEG_PRE` / `FFMPEG_EXTRA`). |

---

## 🚀 Quick start

```bash
# 1. build the CUDA‑enabled image
docker compose build

# 2. start the backdrop generator (daemon mode)
docker compose up -d
```

The container scans **/movies**, **/tv**, and **/anime** (if mounted), then keeps watching on the interval you set.

---

## 🔧 Configuration

Set options via **environment variables** (recommended) or pass flags directly.

| Variable / Flag | Purpose | Default |
| --------------- | ------- | ------- |
| `LENGTH` / `--length` | Clip duration (s) | `5` |
| `RESOLUTION` / `--resolution` | `720` or `1080` | `720` |
| `CRF` / `--crf` | Quality (lower = better) | `28` |
| `FORCE` / `--force` | Overwrite existing backdrops | `false` |
| `TIMEOUT` / `--timeout` | FFmpeg timeout (s) | `300` |
| `NO_AUDIO` / `--no-audio` | Strip audio track | `false` |
| `DAEMON` / `--daemon` | Run continuously | `false` |
| `INTERVAL` / `--interval` | Rescan period (s) | `3600` |
| `FFMPEG_PRE` | Flags **before** `-i` (e.g. `-hwaccel cuda`) | *(see compose)* |
| `FFMPEG_EXTRA` | Flags **after** output (e.g. `-c:v hevc_nvenc`) | *(see compose)* |

### Typical GPU compose snippet

```yaml
environment:
  # GPU decode
  FFMPEG_PRE: -hwaccel cuda -hwaccel_output_format cuda

  # GPU encode (10‑bit friendly)
  FFMPEG_EXTRA: -c:v hevc_nvenc -preset p5

  # main tunables
  LENGTH: 20
  RESOLUTION: 1080
  DAEMON: "true"
  INTERVAL: 21600        # every 6 h
```

> **Tip:** leave `FFMPEG_PRE` untouched – the script skips it automatically when the codec is AV1 or any other format your GPU can’t decode.

---

## 🖥️ Requirements

* **NVIDIA driver** ≥ 450 with NVENC/NVDEC (Pascal, Turing, Ampere, Ada…).
* Docker Engine 19.03+ with *nvidia‑container‑runtime* (Compose v2 device‑reservation syntax).
* AV1 hardware decode needs an Ada Lovelace (RTX 40‑series) or newer; older cards fall back to CPU.

---

## ✅ Tested with

* Jellyfin 10.8 / 10.9  
* Emby 4.8  
* NVIDIA GTX 1080 Ti

---

## 📜 License

MIT – use it as you like, credit appreciated.
