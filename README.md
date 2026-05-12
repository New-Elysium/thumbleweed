# thumbleweed

<p align="center">
<a href="https://github.com/New-Elysium/thumbleweed/actions?query=workflow%3A%22Build+%26+Publish+Wheels%22+branch%3Amain" target="_blank">
    <img src="https://github.com/New-Elysium/thumbleweed/actions/workflows/build-and-publish-wheels.yml/badge.svg?branch=main" alt="Build & Publish Wheels">
</a>
<a href="https://pypi.org/project/thumbleweed" target="_blank">
    <img src="https://img.shields.io/pypi/v/thumbleweed?color=%2334D058&label=pypi%20package" alt="Package version">
</a>
<a href="https://pypi.org/project/thumbleweed" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/thumbleweed.svg?color=%2334D058" alt="Supported Python versions">
</a>
<a href="https://github.com/New-Elysium/thumbleweed/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/New-Elysium/thumbleweed" alt="MIT License">
</a>
</p>

**Unified image hashing, thumbnailing, and compression for Python.**  
Rust-powered via [PyO3](https://pyo3.rs/) + [maturin](https://www.maturin.rs/). Zero mandatory dependencies.

- ✅ **ThumbHash** — compact image placeholder hashes (drop-in for [`thumbhash`](https://pypi.org/project/thumbhash/) & [`fast-thumbhash`](https://pypi.org/project/fast-thumbhash/))
- ✅ **BlurHash** — smooth gradient placeholders (drop-in for [`blurhash-python`](https://pypi.org/project/blurhash/))
- ✅ **ColorThief** — dominant colour + palette extraction (drop-in for [`colorthief`](https://pypi.org/project/colorthief/) & [`fast-colorthief`](https://pypi.org/project/fast-colorthief/))
- ✅ **Thumbnails** — real rasterised thumbnails for **images, videos (MP4), and PDFs**, with a pure-Rust crude fallback that needs **no ffmpeg, no pdfium**
- ✅ **Compression** — optional pixo-powered JPEG/PNG re-encoder, auto-applied to thumbnail output (mozjpeg/oxipng-class quality, pure Rust)
- ✅ Python 3.10 – 3.14 (including free-threaded `3.13t` / `3.14t`)
- ✅ Pillow > 11 integration (optional)
- ✅ Typed (`py.typed` + `.pyi` stubs)
- ✅ Pure-Rust core — no C extensions, no NumPy required

---

## Installation

```bash
pip install thumbleweed
# with Pillow helpers:
pip install "thumbleweed[pillow]"
```

### Optional Rust-side features

A few capabilities are gated behind **cargo features** so the default wheel
stays small and portable. The Python install extras are documentation
hooks — to actually enable a feature you must build the wheel from source
with the matching cargo feature:

| Cargo feature | What it enables | Pulls in |
|---|---|---|
| `pixo` | mozjpeg/oxipng-class JPEG & PNG compression; auto-applied to thumbnail output via `compress=True` | pure Rust |
| `auto-thumbnail` | High-fidelity thumbnail backend including PDF (via `pdfium-render`) and video (via `ffmpeg`/`video-rs`) | pdfium + ffmpeg |

Build from source with extras enabled:

```bash
# Compression only (lightweight, pure Rust)
MATURIN_PEP517_ARGS="--features pixo" pip install thumbleweed --no-binary thumbleweed

# Compression + full pdf/video backend (requires system pdfium + ffmpeg)
MATURIN_PEP517_ARGS="--features pixo,auto-thumbnail" \
    pip install thumbleweed --no-binary thumbleweed
```

Without these features the **crude** thumbnail engine is still available
(MP4 cover-art atom scrape + PDF JPEG-stream scrape + deterministic
gradient placeholder) and the `compress` module degrades to a safe
pass-through.

Note that `auto-thumbnail` is currently an all-or-nothing upstream feature:
enabling it pulls in both PDF and video support together rather than as
separate cargo toggles.

## Development with uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
make sync
make test
```

All import paths work:

```python
import thumbleweed   # the unified package
import thumbhash     # ThumbHash only
import blurhash      # BlurHash only
import colorthief    # ColorThief
from thumbleweed import thumbnail   # rasterised thumbnails
from thumbleweed import compress    # optional pixo compression
```

---

## Quick-start

### ThumbHash

```python
import thumbhash as th

# Encode — rgba_bytes must be bytes/bytearray of length w*h*4 (R G B A, non-premultiplied)
hash_bytes: bytes = th.encode(w, h, rgba_bytes)

# Decode
w_out, h_out, rgba_out = th.decode(hash_bytes)

# Helpers
r, g, b, a = th.average_rgba(hash_bytes)           # dominant colour [0, 1]
ratio = th.approximate_aspect_ratio(hash_bytes)     # width / height
```

### BlurHash

```python
import blurhash as bh

# Encode
hash_str: str = bh.encode(rgba_bytes, cx=4, cy=3, width=w, height=h)

# Decode
rgba: bytes = bh.decode(hash_str, width=64, height=64)
```

### Pillow images / BytesIO

```python
from PIL import Image
import io

# From a Pillow Image
import thumbhash as th
img = Image.open("photo.jpg")
hash_str = th.encode_image(img)             # base64 string; input is resized internally
placeholder = th.decode_image(hash_str)     # → RGBA Image, ≈32 px

# From a BytesIO object
buf = io.BytesIO(open("photo.jpg", "rb").read())
hash_str = th.encode_image(buf)

# BlurHash
import blurhash as bh
hash_str = bh.encode_image(img, cx=4, cy=3)
placeholder = bh.decode_image(hash_str, width=64, height=64)
```

### ColorThief

```python
import colorthief as ct

# From encoded image bytes (PNG, JPEG, WebP, …)
dominant = ct.get_color(image_bytes)                    # → (r, g, b)
palette = ct.get_palette(image_bytes, color_count=5)   # → [(r, g, b), (r, g, b), ...]

# From a file path
dominant = ct.get_color("photo.jpg")

# From a BytesIO object
import io
buf = io.BytesIO(open("photo.jpg", "rb").read())
dominant = ct.get_color(buf)                # accepts bytes, BytesIO, file path, or PIL Image
palette = ct.get_palette(buf, color_count=5)

# Class-based API (drop-in for the colorthief package)
thief = ct.ColorThief("photo.jpg")
dominant = thief.get_color()
palette = thief.get_palette(color_count=8)
```

### thumbleweed (unified)

```python
import thumbleweed

# ThumbHash raw-pixel API
hash_bytes = thumbleweed.thumbhash_encode(w, h, rgba)  # raw ThumbHash bytes
w, h, rgba = thumbleweed.thumbhash_decode(hash_bytes)

# ThumbHash image helper API
hash_str = thumbleweed.thumbhash_encode_image(image_bytes)  # base64 string like BlurHash

# BlurHash
hash_str = thumbleweed.blurhash_encode(rgba, 4, 3, w, h)
rgba = thumbleweed.blurhash_decode(hash_str, 64, 64)

# ColorThief
dominant = thumbleweed.colorthief_get_color(image_bytes)
palette = thumbleweed.colorthief_get_palette(image_bytes, 5, 10)
```

### Thumbnails (images / videos / PDFs)

```python
from thumbleweed import thumbnail

# Works on JPEG, PNG, WebP, GIF, BMP, MP4, MKV/WebM, PDF —
# accepts bytes, BytesIO, file paths, pathlib.Path, and PIL.Image.
jpeg_bytes = thumbnail.create("holiday.mp4", width=256, height=256)
png_bytes  = thumbnail.create("manual.pdf", format="png", width=128, height=128)
webp_bytes = thumbnail.create("photo.jpg", format="webp", width=64, height=64)

# Save directly
thumbnail.save("video.mp4", "video_thumb.jpg", width=256, height=256)

# Inspect the wheel's capabilities
print(thumbnail.detect_kind("file.pdf"))     # → "pdf"
print(thumbnail.available_backends())         # → ['crude'] or ['crude', 'auto-thumbnail']
```

**Two engines** ship in the wheel:

* `crude` (always available): pure-Rust pipeline. Resizes images via the
  `image` crate; scrapes embedded cover art from MP4 (`covr` atom) and
  the first JPEG (`/DCTDecode`) image stream from PDFs; otherwise
  generates a deterministic colour-gradient placeholder.
* `auto-thumbnail` (cargo feature): wraps the
  [auto-thumbnail](https://crates.io/crates/auto-thumbnail) crate for
  proper PDF rasterisation (pdfium) and video frame extraction (ffmpeg).

Default `engine="auto"` picks `auto-thumbnail` when present, falling
back to `crude` on any failure — you always get *something* back.

### Compression (optional, pixo-backed)

```python
from thumbleweed import compress, thumbnail

if compress.is_available():
    smaller = compress.compress(open("photo.jpg", "rb").read(), quality=85)
    bytes_saved = compress.compress_path("photo.jpg")  # in-place

# Auto-applied to thumbnail output (the default — pass compress=False to skip)
thumb = thumbnail.create("photo.jpg", width=256, height=256)            # compressed
thumb = thumbnail.create("photo.jpg", width=256, height=256, compress=False)
```

When the wheel is **not** built with `--features pixo`, every function in
`thumbleweed.compress` becomes a no-op pass-through, so `compress=True`
remains safe to leave on as the default everywhere.

---

## Project structure

```
thumbleweed/
├── src/
│   ├── lib.rs            # PyO3 module — Python bindings
│   ├── thumbhash.rs      # Pure Rust ThumbHash encode/decode
│   ├── blurhash.rs       # Pure Rust BlurHash encode/decode
│   ├── colorthief.rs     # ColorThief — dominant colour & palette extraction
│   ├── thumbnail.rs      # Rasterised thumbnails (crude + auto-thumbnail)
│   └── compress.rs       # Optional pixo-powered JPEG/PNG re-encoder
├── python/
│   ├── thumbleweed/      # Main package — re-exports everything
│   │   ├── thumbnail.py  # High-level thumbnail submodule
│   │   └── compress.py   # High-level compression submodule
│   ├── thumbhash/        # Backward-compatible ThumbHash shim
│   ├── blurhash/         # BlurHash shim
│   └── colorthief/       # ColorThief shim
├── tests/
│   ├── test_thumbhash.py # 70+ ThumbHash tests
│   ├── test_blurhash.py  # 28+ BlurHash tests
│   ├── test_colorthief.py# ColorThief tests
│   ├── test_thumbnail.py # 153 thumbnail tests across all jpg / mp4 / pdf fixtures
│   ├── test_compress.py  # 60+ compression + integration tests
│   └── test_imports.py   # import / version-consistency tests
└── Cargo.toml
```

---

## API reference

### ThumbHash (`import thumbhash`)

| Function | Description |
|---|---|
| `encode(w, h, rgba) → bytes` | Encode raw RGBA bytes → ThumbHash |
| `decode(hash) → (w, h, rgba)` | Decode ThumbHash → raw RGBA bytes |
| `average_rgba(hash) → (r,g,b,a)` | Dominant colour in `[0, 1]` |
| `approximate_aspect_ratio(hash) → float` | Width / height of the original image |
| `encode_image(img) → str` | Encode a Pillow `Image` *(Pillow required)*, or encoded image `bytes`, `BytesIO`, or file path *(no Pillow required)* → base64 ThumbHash string |
| `decode_image(hash) → Image` | Decode a base64 ThumbHash string or raw ThumbHash bytes to a Pillow `Image` *(requires Pillow)* |

### BlurHash (`import blurhash`)

| Function | Description |
|---|---|
| `encode(pixels, cx, cy, w, h) → str` | Encode raw RGBA bytes → BlurHash string |
| `decode(hash, w, h) → bytes` | Decode BlurHash → raw RGBA bytes |
| `encode_image(img, cx, cy) → str` | Encode a Pillow `Image` *(Pillow required)*, or encoded image `bytes`, `BytesIO`, or file path *(no Pillow required)* → BlurHash |
| `decode_image(hash, w, h) → Image` | Decode to a Pillow `Image` *(requires Pillow)* |

### ColorThief (`import colorthief`)

| Function | Description |
|---|---|
| `get_color(image, quality) → (r,g,b)` | Dominant colour from `bytes`, `BytesIO`, file path, or PIL Image |
| `get_palette(image, color_count, quality) → list[(r,g,b)]` | Colour palette from `bytes`, `BytesIO`, file path, or PIL Image |
| `ColorThief(image)` | Class-based API — accepts `bytes`, `BytesIO`, file path, or PIL Image |

### Thumbnail (`from thumbleweed import thumbnail`)

| Function | Description |
|---|---|
| `create(source, width, height, quality, format, engine, compress) → bytes` | Build a thumbnail from any image / video / PDF source |
| `create_from_bytes(data, ...) → bytes` | Build from raw encoded bytes (skip the input-normalisation overhead) |
| `create_from_path(path, ...) → bytes` | Build from a file path |
| `save(source, output_path, ...) → None` | Build a thumbnail and write it to disk |
| `detect_kind(source) → str` | Inspect magic bytes — returns `"image"` / `"video"` / `"pdf"` / `"unknown"` |
| `available_backends() → list[str]` | Lists which backends were compiled in — always includes `"crude"` |

### Compress (`from thumbleweed import compress`)

| Function | Description |
|---|---|
| `compress(source, format, quality) → bytes` | Re-encode JPEG/PNG via pixo's max preset (no-op for WebP / unknown / when feature is off). Returns the input verbatim if pixo can't shrink it. |
| `compress_path(input, output=None, ...) → int` | Compress a file in-place (or to `output`). Returns bytes saved. |
| `is_available() → bool` | True if the wheel was built with the `pixo` cargo feature |
| `detect_format(source) → str` | `"jpeg"` / `"png"` / `"webp"` / `"unknown"` |

---

<!-- BENCHMARK_TABLE:START -->
## Performance Benchmark Results

> Benchmark configuration: 5 rounds × 100 iterations (pure-Python libraries use 5 iterations).
> Input corpus: all real image fixtures in `tests/` (`one.jpg`, `two.jpg`, `four.jpg`, `OPS.jpg`).
> All times are mean per-call latency. Lower is better.

| Operation | thumbleweed | Comparison | Result |
|-----------|-------------|------------|--------|
| ThumbHash encode (real test images) | 825.4 µs | thumbhash-python (pure Python): 27.26 ms | **33.0×** faster |
| ThumbHash decode (real test images) | 56.4 µs | thumbhash-python (pure Python): 5.49 ms | **97.3×** faster |
| BlurHash encode (real test images) | 4.98 ms | blurhash-python (CFFI): 4.42 ms | 1.1× slower |
| BlurHash decode 64×64 (real test images) | 902.4 µs | blurhash-python (CFFI): 842.2 µs | 1.1× slower |
| ColorThief dominant (real test images) | 5.09 ms | fast-colorthief (C ext + NumPy): 18.62 ms | **3.7×** faster |
| ColorThief palette-10 (real test images) | 5.17 ms | fast-colorthief (C ext + NumPy): 18.38 ms | **3.6×** faster |

<!-- BENCHMARK_TABLE:END -->

(_The above values are updated by a benchmark script ocassionally_)

**Notes on ColorThief timing:** thumbleweed includes image decode in its timing because it accepts raw encoded bytes from the real test fixtures, while `fast-colorthief` also reads from in-memory file-like objects in these benchmarks. This measures realistic end-to-end usage rather than just the inner palette routine.

---

## Building from source

```bash
git clone https://github.com/New-Elysium/thumbleweed.git
cd thumbleweed
make sync   # sync uv environment + install editable
make test   # run Python + Rust tests
```

### Make targets

- `make sync` — sync uv environment and install the extension in editable mode
- `make test` — run Python tests and Rust tests
- `make dist` — build wheels into `dist/`
- `make upload` — upload `dist/*` with `twine`

## Running Benchmarks

Benchmarks require `bench` dependencies which might not be compatible with all Python versions (e.g. `thumbhash-python` fails to resolve on Python 3.14). To avoid conflicts, run them with a supported Python version (e.g. 3.12):

```bash
# Sync using a Python version that supports the benchmark dependencies
uv sync --group bench --python 3.12
uv run python tests/bench_comparison.py

# Refresh the benchmark table in this README
uv run python scripts/update_readme.py
```

---

## Licence

MIT — see [LICENCE](LICENCE).
