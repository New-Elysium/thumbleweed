# thumbhash

**Fast ThumbHash encode/decode for Python — Rust-powered, zero mandatory dependencies.**

A modern, OSS drop-in replacement for [`fast-thumbhash`](https://pypi.org/project/fast-thumbhash/),
built with [maturin](https://www.maturin.rs/) and [PyO3](https://pyo3.rs/).

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

---

## Quick-start

### Raw RGBA bytes

```python
from thumbhash import encode, decode

# Encode -------------------------------------------------------------------
# rgba_bytes must be a bytes/bytearray of length w*h*4 (R G B A, non-premult.)
hash_bytes: bytes = tw.encode(w, h, rgba_bytes)

# Decode -------------------------------------------------------------------
w_out, h_out, rgba_out = tw.decode(hash_bytes)

# Helpers ------------------------------------------------------------------
r, g, b, a = tw.average_rgba(hash_bytes)   # dominant colour [0, 1]
ratio = tw.approximate_aspect_ratio(hash_bytes)  # width / height
```

### Pillow images

```python
from PIL import Image
from thumbhash import encode_image, decode_image

img = Image.open("photo.jpg")

hash_bytes = tw.encode_image(img)         # any mode, any size
placeholder: Image.Image = tw.decode_image(hash_bytes)   # RGBA, ≈32 px
placeholder.save("placeholder.png")
```

`encode_image` automatically converts the image to RGBA and shrinks it so
the longest side is ≤ 100 px (the algorithm's hard limit).

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

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Rust (stable) | ≥ 1.75 (tested with **1.95.0**) | `curl https://sh.rustup.rs -sSf \| sh` |
| Python | 3.9 – **3.14** | system / pyenv |
| maturin | ≥ 1.7, < 2 | `pip install "maturin>=1.7,<2"` |

> **Ubuntu 26.04 / Python 3.14 note** — Ubuntu 26.04 ships Python 3.14.
> The steps below work unchanged; maturin detects the interpreter automatically.

### 1 — Clone and enter the project

```bash
git clone https://github.com/New-Elysium/thumbleweed.git
cd thumbleweed
```

### 2 — Set up a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install "maturin>=1.10,<2" "Pillow>12" pytest
```

### 3 — Development build (editable)

Compiles the Rust extension and installs the package in editable mode so
that changes to the Python files in `python/thumbhash/` take effect
immediately without a rebuild.

```bash
maturin develop --release
```

### 4 — Run the tests

```bash
pytest -v
```

### 5 — Build release wheels

#### Local wheel (current platform only)

```bash
maturin build --release
# wheel lands in  target/wheels/thumbhash-*.whl
pip install target/wheels/thumbhash-*.whl
```

#### Portable `manylinux` wheels (for PyPI)

Use the official maturin Docker image to build wheels that are compatible
with virtually every Linux distribution:

```bash
docker run --rm \
  -v "$(pwd)":/io \
  -w /io \
  ghcr.io/pyo3/maturin:latest \
  build --release --out dist
```

Wheels for each CPython version land in `dist/`.

#### macOS (universal2)

```bash
rustup target add aarch64-apple-darwin x86_64-apple-darwin
maturin build --release --target universal2-apple-darwin
```

#### Windows

```powershell
maturin build --release
```

#### Free-threaded Python 3.13t / 3.14t

maturin ≥ 1.7 detects the free-threaded interpreter automatically.
Just activate the `python3.14t` (or `python3.13t`) virtual environment and
run `maturin develop` or `maturin build` as normal.

---

## Publishing to PyPI

### One-time setup

```bash
pip install twine
# Create a PyPI account and generate an API token at https://pypi.org/manage/account/token/
```

Store the token in `~/.pypirc`:

```ini
[pypi]
  username = __token__
  password = pypi-<your-token-here>
```

Or export it as an environment variable:

```bash
export MATURIN_PYPI_TOKEN=pypi-<your-token-here>
```

### Build all wheels with `maturin publish` (recommended)

`maturin publish` builds *and* uploads in one step.  It uses
[`cibuildwheel`](https://cibuildwheel.pypa.io/) conventions internally when
run in CI.

```bash
maturin publish --token pypi-<your-token-here>
```

### Manual upload with twine

If you built wheels separately (e.g. via the Docker approach above):

```bash
twine upload dist/*.whl dist/*.tar.gz
```

### CI / GitHub Actions (recommended for cross-platform wheels)

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - uses: PyO3/maturin-action@v1
        with:
          command: build
          args: --release --out dist
          manylinux: auto   # builds manylinux wheels on Linux

      - uses: actions/upload-artifact@v4
        with:
          name: wheels-${{ matrix.os }}
          path: dist

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write   # OIDC trusted publishing
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: wheels-*
          merge-multiple: true
          path: dist

      - uses: pypa/gh-action-pypi-publish@release/v1
        # Trusted publishing — no API token needed when configured on PyPI
```

> **Tip**: Enable [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
> on PyPI to avoid managing API tokens in GitHub secrets.

---

## Project layout

```
thumbhash-py/
├── Cargo.toml          # Rust crate manifest
├── pyproject.toml      # maturin + PEP 621 metadata
├── README.md
├── src/
│   └── lib.rs          # Rust implementation + PyO3 bindings
├── python/
│   └── thumbhash/
│       ├── __init__.py # Public Python API + Pillow helpers
│       ├── _core.pyi   # Type stubs for the compiled extension
│       └── py.typed    # PEP 561 marker
└── tests/
    └── test_thumbhash.py
```

---

## Algorithm

ThumbHash is a compact image placeholder algorithm by
[Evan Wallace](https://evanw.github.io/thumbhash/).  It encodes images using
a discrete cosine transform (DCT) into a small byte string (typically 5–32
bytes) that decodes to a smooth, colourful placeholder.

Compared to BlurHash it supports a more accurate aspect ratio, alpha
transparency, and better colour fidelity.

---

## Licence

MIT — see [LICENCE](LICENCE).
