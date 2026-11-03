# media-compressor

**CLI to compress images and videos** — one Fire entry point over ffmpeg (plus Pillow / rawpy for image paths), with progress bars and optional overwrite.

## Why media-compressor?

Batch media downsizing without juggling ad-hoc ffmpeg flags. Point at a file or a flat folder, pick a speed/quality preset, and get compressed outputs with CPU utilization control.

- **Videos** — `.mp4`, `.avi`, `.mov`, `.mkv` via **libx264** (CRF 23) + AAC
- **Images** — `.jpg`, `.jpeg`, `.png`, `.tiff`, `.cr2` via ffmpeg (JPEG quality / PNG compression tweaks)
- **Presets** — ffmpeg x264 presets from `ultrafast` … `placebo`
- **Progress** — tqdm while encoding; opens the output location when done

Requires a working **ffmpeg** binary on `PATH`, plus the Python deps below.

## Quick start

```bash
# system ffmpeg must be installed and on PATH
python -m pip install ffmpeg-python tqdm Pillow fire rawpy

python compress.py /path/to/input.mp4 /path/to/output.mp4 medium
python compress.py /path/to/photos /path/to/out slow --overwrite --utilization=0.8
```

| Argument / flag | Meaning |
| --------------- | ------- |
| `src` | Input file **or** folder (folder → folder only; file → file only) |
| `dst` | Output path (same kind as `src`) |
| `preset` | ffmpeg preset string (`ultrafast` … `placebo`) |
| `--overwrite` | Replace existing destination (folder mode removes `dst` first) |
| `--utilization` | Fraction of CPU cores for ffmpeg threads (clamped ~0.1–1.0) |

Folder mode only compresses **top-level** approved extensions in `src` (not recursive).

## What you get

| Surface | Role |
| ------- | ---- |
| `compress.py` | Fire CLI (`Main().compress`) and compressor classes |
| `tests/` | Placeholder unittest modules (images / videos) |
| `.vscode/launch.json` | Example debugger launch args for local runs |

## Contributing & development

Agent/developer workflow (layout, deps, CI labels): see [`AGENTS.md`](./AGENTS.md).

Report security issues privately via [GitHub advisories](https://github.com/danielnachumdev/media-compressor/security/advisories/new) — please do not open a public issue for vulnerabilities.
