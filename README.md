# thumbleweed

**Unified image hashing for Python — ThumbHash, BlurHash, and ColorThief.**  
Rust-powered via [PyO3](https://pyo3.rs/) + [maturin](https://www.maturin.rs/). Zero mandatory dependencies.

- ✅ **ThumbHash** — compact image placeholder hashes (drop-in for [`thumbhash`](https://pypi.org/project/thumbhash/) & [`fast-thumbhash`](https://pypi.org/project/fast-thumbhash/))
- ✅ **BlurHash** — smooth gradient placeholders (drop-in for [`blurhash-python`](https://pypi.org/project/blurhash/))
- ✅ **ColorThief** — dominant colour + palette extraction (drop-in for [`colorthief`](https://pypi.org/project/colorthief/) & [`fast-colorthief`](https://pypi.org/project/fast-colorthief/))
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

## Development with uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
make sync
make test
```

All import paths work:

```python
import thumbleweed   # the unified package
import thumbhash     # ThumbHash only (backward-compatible)
import blurhash      # BlurHash only
import colorthief    # ColorThief
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
hash_bytes = th.encode_image(img)           # any mode, any size
placeholder = th.decode_image(hash_bytes)   # → RGBA Image, ≈32 px

# From a BytesIO object
buf = io.BytesIO(open("photo.jpg", "rb").read())
hash_bytes = th.encode_image(buf)

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
palette = ct.get_palette(image_bytes, color_count=5)   # → [(r, g, b), ...]

# From a file path
dominant = ct.get_color_from_file("photo.jpg")

# From a BytesIO object
import io
buf = io.BytesIO(open("photo.jpg", "rb").read())
dominant = ct.get_color_image(buf)          # accepts bytes, BytesIO, file path, or PIL Image
palette = ct.get_palette_image(buf, color_count=5)

# Class-based API (drop-in for the colorthief package)
thief = ct.ColorThief("photo.jpg")
dominant = thief.get_color()
palette = thief.get_palette(color_count=8)
```

### thumbleweed (unified)

```python
import thumbleweed

# ThumbHash
hash_bytes = thumbleweed.thumbhash_encode(w, h, rgba)
w, h, rgba = thumbleweed.thumbhash_decode(hash)

# BlurHash
hash_str = thumbleweed.blurhash_encode(rgba, 4, 3, w, h)
rgba = thumbleweed.blurhash_decode(hash_str, 64, 64)

# ColorThief
dominant = thumbleweed.colorthief_get_color_bytes(image_bytes)
palette = thumbleweed.colorthief_get_palette_bytes(image_bytes, 5, 10)
```

---

## Project structure

```
thumbleweed/
├── src/
│   ├── lib.rs            # PyO3 module — Python bindings
│   ├── thumbhash.rs      # Pure Rust ThumbHash encode/decode
│   ├── blurhash.rs       # Pure Rust BlurHash encode/decode
│   └── colorthief.rs     # ColorThief — dominant colour & palette extraction
├── python/
│   ├── thumbleweed/      # Main package — re-exports everything
│   ├── thumbhash/        # Backward-compatible ThumbHash shim
│   ├── blurhash/         # BlurHash shim
│   └── colorthief/       # ColorThief shim
├── tests/
│   ├── test_thumbhash.py # 70 ThumbHash tests
│   ├── test_blurhash.py  # 28 BlurHash tests
│   ├── test_colorthief.py # ColorThief tests
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
| `encode_image(img) → bytes` | Encode a Pillow `Image`, `bytes`, `BytesIO`, or file path → ThumbHash |
| `decode_image(hash) → Image` | Decode to a Pillow `Image` *(requires Pillow)* |

### BlurHash (`import blurhash`)

| Function | Description |
|---|---|
| `encode(pixels, cx, cy, w, h) → str` | Encode raw RGBA bytes → BlurHash string |
| `decode(hash, w, h) → bytes` | Decode BlurHash → raw RGBA bytes |
| `encode_image(img, cx, cy) → str` | Encode a Pillow `Image`, `bytes`, `BytesIO`, or file path → BlurHash |
| `decode_image(hash, w, h) → Image` | Decode to a Pillow `Image` *(requires Pillow)* |

### ColorThief (`import colorthief`)

| Function | Description |
|---|---|
| `get_color(image_bytes, quality) → (r,g,b)` | Dominant colour from encoded image bytes |
| `get_palette(image_bytes, color_count, quality) → list[(r,g,b)]` | Colour palette from encoded image bytes |
| `get_color_from_file(path) → (r,g,b)` | Dominant colour from a file path |
| `get_palette_from_file(path, color_count, quality) → list[(r,g,b)]` | Palette from a file path |
| `get_color_image(image) → (r,g,b)` | Dominant colour from `bytes`, `BytesIO`, file path, or PIL Image |
| `get_palette_image(image, color_count, quality) → list[(r,g,b)]` | Palette from `bytes`, `BytesIO`, file path, or PIL Image |
| `ColorThief(image)` | Class-based API — accepts `bytes`, `BytesIO`, file path, or PIL Image |

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

---

## Licence

MIT — see [LICENCE](LICENCE).
