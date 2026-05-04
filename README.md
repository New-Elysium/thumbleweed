# thumbleweed

**Fast ThumbHash encode/decode for Python — Rust-powered, zero mandatory dependencies.**

A drop-in replacement for [`thumbhash`](https://pypi.org/project/thumbhash/) and [`fast-thumbhash`](https://pypi.org/project/fast-thumbhash/), built with [PyO3](https://pyo3.rs/) and [maturin](https://www.maturin.rs/).

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

Both `import thumbhash` and `import thumbleweed` work.

---

## Quick-start

### Raw RGBA bytes

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

### Pillow images

```python
from PIL import Image
import thumbhash as th

img = Image.open("photo.jpg")

hash_bytes = th.encode_image(img)                   # any mode, any size
placeholder = th.decode_image(hash_bytes)           # → RGBA Image, ≈32 px
placeholder.save("placeholder.png")
```

`encode_image` automatically converts to RGBA and shrinks the longest side to ≤ 100 px (the algorithm's hard limit).

---

## API reference

| Function | Description |
|---|---|
| `encode(w, h, rgba) → bytes` | Encode raw RGBA bytes → ThumbHash |
| `decode(hash) → (w, h, rgba)` | Decode ThumbHash → raw RGBA bytes |
| `average_rgba(hash) → (r,g,b,a)` | Dominant colour in [0, 1] |
| `approximate_aspect_ratio(hash) → float` | Width / height of the original image |
| `encode_image(img) → bytes` | Encode a Pillow `Image` *(requires Pillow)* |
| `decode_image(hash) → Image` | Decode a ThumbHash to a Pillow `Image` *(requires Pillow)* |

---

## Building from source

```bash
git clone https://github.com/New-Elysium/thumbleweed.git
cd thumbleweed
python3 -m venv .venv && . .venv/bin/activate
pip install "maturin>=1.10,<2" "Pillow>12" pytest
maturin develop --release
pytest -v
```

---

## Licence

MIT — see [LICENCE](LICENCE).
