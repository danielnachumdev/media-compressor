# media-compressor – Agent Context

Implementation guide for coding agents changing **media-compressor**. Product pitch and user-facing run: [`README.md`](README.md).

---

## Orientation

| Question | Answer |
| -------- | ------ |
| What is this? | Python **Fire** CLI that compresses images/videos with **ffmpeg** (and related libs) |
| Entry point | `compress.py` → `Fire(Main().compress)` |
| Toolchain | Plain script + pip; **no** `pyproject.toml` / `uv.lock` yet |
| Python | 3.x with typing; run with the env that has the deps installed |
| Tests | `tests/` — unittest stubs today; **never delete** the suite |
| System dep | **ffmpeg** binary on `PATH` (not the same as `ffmpeg-python`) |
| Secrets | No OAuth/API keys; do not commit local media under `data/` / `output/` |

```text
.
├── .github/              # CODEOWNERS, dependabot, thin CI (when present on default branch)
├── compress.py           # CLI + Compressor hierarchy
├── tests/                # unittest (images / videos) — keep
├── .vscode/launch.json   # Local debug example (do not paste real user paths into docs)
├── README.md             # Marketing / user docs
└── AGENTS.md             # This file
```

Default branch is **`master`**. Shared CI/semver: [`danielnachumdev/actions`](https://github.com/danielnachumdev/actions). How to adopt: [`HOW-TO-USE.md`](https://github.com/danielnachumdev/actions/blob/v1/HOW-TO-USE.md). Prefer thin orchestrators and shared reusable workflows — do not re-vendor CI bodies here.

---

## Develop

```bash
# Install runtime deps (same list as the import guard in compress.py)
python -m pip install ffmpeg-python tqdm Pillow fire rawpy

# Ensure ffmpeg is available
ffmpeg -version

# Smoke the CLI help surface (Fire)
python compress.py --help
```

| Task | Command |
| ---- | ------- |
| Run CLI | `python compress.py <src> <dst> <preset> [--overwrite] [--utilization=0.8]` |
| Tests | `python -m unittest discover -s tests -v` (stubs currently always pass) |

### Dependencies

- **Runtime (pip):** `ffmpeg-python`, `tqdm`, `Pillow`, `fire`, `rawpy`
- **System:** `ffmpeg` on `PATH`
- Import failures print a pip install line and exit — keep that guard accurate when adding imports
- There is **no** packaging/CD/PyPI path yet — do not invent `publish` / wheel release unless explicitly requested

---

## Code style & domain notes

- Prefer extending the existing **class hierarchy** (`Compressor` → `ObjectCompressor` / `FolderCompressor` / `FileCompressor` → video/image implementations) rather than a second CLI entry point.
- Routing: `SwitchCompressor` maps extensions → `FFMPEGVideoCompressor` or `FFMPEGImageCompressor`. Approved folder extensions live in `FolderCompressor`.
- **Videos:** `libx264`, `crf=23`, `aac` / `128k`, preset from `FFMPEGCompressionPreset`, thread count from `cpu_count * utilization`.
- **Images:** ffmpeg output with JPEG `qscale:v` / PNG `compression_level` tweaks; CR2/TIFF go through the same ffmpeg path (rawpy is imported for availability — keep behavior consistent if you wire raw decoding).
- `src`/`dst` must both be files or both folders; mismatches abort. Folder mode is **non-recursive** (breaks after the first `os.walk` level).
- After success, the CLI opens the output location (`open` / `start`) — keep that behavior cross-platform or gate it deliberately if changing UX.
- Follow the writing-python skill when splitting modules (class-first, SRP files). Do not invent a package layout unless the user asks to package the project.

---

## PRs, CI, and releases

1. Branch off `master`; open a PR into `master`.
2. Attach **exactly one** semver label: `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor`.
3. **CI** — thin `.github/workflows/ci.yml` calling `danielnachumdev/actions` (`ci.yml` + `semver-ci.yml`; Dependabot auto-merge when configured). Prefer check names **`CI / CI`** and **`Semver / Semver`**. Empty/placeholder suites may use `allow-empty` until real tests land.
4. **CD** — no `semver-cd` / PyPI publish in this repo yet. Do not add release publishing unless explicitly requested; change shared semver/CD behavior in **`danielnachumdev/actions`**, not by vendoring.
5. Dependabot PRs stay on `noBump`.
6. Docs-only / chore PRs use `noBump`.

### Repo gates

- Semver labels present on the repo
- `.github/CODEOWNERS` — `@danielnachumdev` (when CI/howto is on the default branch)
- Private vulnerability reporting via GitHub Security Advisories

---

## Sensitive / ignored

Do not commit: local media (`data/`, `output/` are gitignored), `.venv/`, `__pycache__/`, API keys, or real personal file paths in checked-in launch configs / docs. Respect `.gitignore`.
