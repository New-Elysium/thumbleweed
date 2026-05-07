# thumbleweed

**Unified image hashing for Python — ThumbHash, BlurHash, and (soon) ColorThief.**  
Rust-powered via [PyO3](https://pyo3.rs/) + [maturin](https://www.maturin.rs/). Zero mandatory dependencies.

- ✅ **ThumbHash** — compact image placeholder hashes (drop-in for [`thumbhash`](https://pypi.org/project/thumbhash/) & [`fast-thumbhash`](https://pypi.org/project/fast-thumbhash/))
- ✅ **BlurHash** — smooth gradient placeholders (drop-in for [`blurhash-python`](https://pypi.org/project/blurhash/))
- 🔜 **ColorThief** — dominant colour extraction *(placeholder, not yet implemented)*
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
make prepare
make dist
```

All import paths work:

```python
import thumbleweed   # the unified package
import thumbhash     # ThumbHash only (backward-compatible)
import blurhash      # BlurHash only
import colorthief    # ColorThief (placeholder)
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

### Pillow images

```python
from PIL import Image

# ThumbHash
import thumbhash as th
img = Image.open("photo.jpg")
hash_bytes = th.encode_image(img)           # any mode, any size
placeholder = th.decode_image(hash_bytes)   # → RGBA Image, ≈32 px

# BlurHash
import blurhash as bh
hash_str = bh.encode_image(img, cx=4, cy=3)
placeholder = bh.decode_image(hash_str, width=64, height=64)
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
```

---

## Project structure

```
thumbleweed/
├── src/
│   ├── lib.rs            # PyO3 module — Python bindings
│   ├── thumbhash.rs      # Pure Rust ThumbHash encode/decode
│   ├── blurhash.rs       # Pure Rust BlurHash encode/decode
│   └── colorthief.rs     # Placeholder for future color extraction
├── python/
│   ├── thumbleweed/      # Main package — re-exports everything
│   ├── thumbhash/        # Backward-compatible ThumbHash shim
│   ├── blurhash/         # BlurHash shim
│   └── colorthief/       # Placeholder shim
├── tests/
│   ├── test_thumbhash.py # 70 ThumbHash tests
│   ├── test_blurhash.py  # 28 BlurHash tests
│   └── test_imports.py   # 13 import / version-consistency tests
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
| `encode_image(img) → bytes` | Encode a Pillow `Image` *(requires Pillow)* |
| `decode_image(hash) → Image` | Decode to a Pillow `Image` *(requires Pillow)* |

### BlurHash (`import blurhash`)

| Function | Description |
|---|---|
| `encode(pixels, cx, cy, w, h) → str` | Encode raw RGBA bytes → BlurHash string |
| `decode(hash, w, h) → bytes` | Decode BlurHash → raw RGBA bytes |
| `encode_image(img, cx, cy) → str` | Encode a Pillow `Image` *(requires Pillow)* |
| `decode_image(hash, w, h) → Image` | Decode to a Pillow `Image` *(requires Pillow)* |

### thumbleweed (`import thumbleweed`)

All of the above, prefixed with `thumbhash_` or `blurhash_`.

---

## Building from source

```bash
git clone https://github.com/New-Elysium/thumbleweed.git
cd thumbleweed
make sync
make test
make prepare
```

### Make targets

- `make sync` — sync uv environment (dev + bench) and install the extension in editable mode
- `make test` — run Python tests and Rust tests
- `make prepare` — run the real-image performance benchmark and inject the table into `CLAUDE.md`
- `make dist` — build wheels / distributions into `dist/`
- `make upload` — upload `dist/*` with `twine`
- `make upload-testpypi` — upload `dist/*` to TestPyPI with `twine`

The repository is uv-managed and includes a checked-in `uv.lock`.

---

## Licence

MIT — see [LICENCE](LICENCE).
