"""
thumbleweed
===========
A unified image hashing library — ThumbHash, BlurHash, and ColorThief.

Backed by a Rust core via PyO3. Zero mandatory dependencies; Pillow helpers
are optional.

Quick-start
-----------
>>> import thumbleweed
>>> # ThumbHash — from raw RGBA bytes
>>> hash_bytes = thumbleweed.thumbhash_encode(w, h, rgba_bytes)
>>> w, h, rgba = thumbleweed.thumbhash_decode(hash_bytes)

>>> # BlurHash — from raw RGBA bytes
>>> blur_str = thumbleweed.blurhash_encode(rgba_bytes, 4, 3, w, h)
>>> rgba = thumbleweed.blurhash_decode(blur_str, 64, 64)

>>> # ThumbHash / BlurHash — from any image source (file, BytesIO, Pillow Image …)
>>> hash_bytes = thumbleweed.thumbhash_encode_image(image_path_or_bytes_or_pil)
>>> blur_str = thumbleweed.blurhash_encode_image(image_path_or_bytes_or_pil)

# ColorThief — dominant colour / palette from any image source
>>> rgb = thumbleweed.colorthief_get_color(image_path_or_bytes_or_pil)
>>> palette = thumbleweed.colorthief_get_palette(image_path_or_bytes_or_pil)
>>> # Or use the raw-bytes-only API:
>>> rgb = thumbleweed.colorthief_get_color_bytes(image_bytes)
"""

from __future__ import annotations

__all__ = [
    # ThumbHash — raw bytes API
    "thumbhash_encode",
    "thumbhash_decode",
    "thumbhash_average_rgba",
    "thumbhash_approximate_aspect_ratio",
    # ThumbHash — image-aware helpers (Pillow / BytesIO / path)
    "thumbhash_encode_image",
    "thumbhash_decode_image",
    # BlurHash — raw bytes API
    "blurhash_encode",
    "blurhash_decode",
    # BlurHash — image-aware helpers
    "blurhash_encode_image",
    "blurhash_decode_image",
    # ColorThief — raw bytes API (calls Rust directly)
    "colorthief_get_color_bytes",
    "colorthief_get_palette_bytes",
    # ColorThief — high-level helpers (BytesIO / bytes / path / Pillow)
    "colorthief_get_color",
    "colorthief_get_palette",
    # Metadata
    "__version__",
]

# ── Rust core (always available) ─────────────────────────────────────────────
from thumbleweed._core import (  # type: ignore[import]
    __version__,
    blurhash_decode,
    blurhash_encode,
    colorthief_get_color_bytes,
    colorthief_get_palette_bytes,
    thumbhash_approximate_aspect_ratio,
    thumbhash_average_rgba,
    thumbhash_decode,
    thumbhash_encode,
)

# ── Image-aware helpers — lazily imported to avoid circular imports ───────────
# The shim packages (thumbhash, blurhash, colorthief) themselves import from
# thumbleweed._core, which would cause a circular import if we imported them at
# module-load time here.  We resolve them on first access via __getattr__.

_LAZY: dict[str, tuple[str, str]] = {
    "thumbhash_encode_image": ("thumbhash", "encode_image"),
    "thumbhash_decode_image": ("thumbhash", "decode_image"),
    "blurhash_encode_image": ("blurhash", "encode_image"),
    "blurhash_decode_image": ("blurhash", "decode_image"),
    "colorthief_get_color": ("colorthief", "get_color"),
    "colorthief_get_palette": ("colorthief", "get_palette"),
}


def __getattr__(name: str) -> object:
    if name in _LAZY:
        module_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(module_name)
        obj = getattr(mod, attr)
        # Cache in the module namespace so subsequent accesses are fast.
        globals()[name] = obj
        return obj
    raise AttributeError(f"module 'thumbleweed' has no attribute {name!r}")
