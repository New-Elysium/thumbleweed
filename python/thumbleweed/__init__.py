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
>>> hash_str = thumbleweed.thumbhash_encode_image(image_path_or_bytes_or_pil)  # base64 string
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
    # Thumbnail submodule + helpers
    "thumbnail",
    "thumbnail_create",
    "thumbnail_save",
    "thumbnail_detect_kind",
    "thumbnail_available_backends",
    # Compression (pixo) submodule + helpers
    "compress",
    "compress_image",
    "compress_is_available",
    "compress_detect_format",
    # Metadata
    "__version__",
]

# ── Rust core (always available) ─────────────────────────────────────────────
# Eagerly expose the thumbnail submodule (no shim package, just a submodule
# that does its own thin wrapping over _core).
from thumbleweed import compress as compress  # noqa: PLC0414
from thumbleweed import thumbnail as thumbnail  # noqa: PLC0414
from thumbleweed._core import (  # type: ignore[import]
    __version__,
    blurhash_decode,
    blurhash_encode,
    colorthief_get_color_bytes,
    colorthief_get_palette_bytes,
    compress_detect_format,
    compress_image,
    compress_is_available,
    thumbhash_approximate_aspect_ratio,
    thumbhash_average_rgba,
    thumbhash_decode,
    thumbhash_encode,
    thumbnail_available_backends,
    thumbnail_detect_kind,
)
from thumbleweed.thumbnail import create as thumbnail_create
from thumbleweed.thumbnail import save as thumbnail_save

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

# The raw _core functions for average_rgba and approximate_aspect_ratio
# only accept bytes.  The thumbhash shim wraps them to also accept base64
# strings (as returned by thumbhash_encode_image).  We expose the wrapped
# versions as the default, but keep the raw _core originals accessible
# via private names.
_thumbhash_average_rgba_raw = thumbhash_average_rgba
_thumbhash_approximate_aspect_ratio_raw = thumbhash_approximate_aspect_ratio


def _thumbhash_to_raw_bytes(hash_input: bytes | bytearray | str) -> bytes:
    """Convert a ThumbHash to raw bytes, accepting either raw bytes or a base64 string."""
    import base64
    import binascii

    if isinstance(hash_input, str):
        try:
            return base64.b64decode(hash_input, validate=True)
        except binascii.Error as exc:
            raise ValueError("Invalid base64 ThumbHash string") from exc
    return bytes(hash_input)


def thumbhash_average_rgba(hash_input: bytes | bytearray | str):
    """Extract the average colour from a ThumbHash.

    Accepts raw bytes / bytearray, or a base64-encoded string
    (as returned by :func:`thumbhash_encode_image`).
    """
    return _thumbhash_average_rgba_raw(_thumbhash_to_raw_bytes(hash_input))


def thumbhash_approximate_aspect_ratio(hash_input: bytes | bytearray | str):
    """Return the approximate aspect ratio (width / height) of the original image.

    Accepts raw bytes / bytearray, or a base64-encoded string
    (as returned by :func:`thumbhash_encode_image`).
    """
    return _thumbhash_approximate_aspect_ratio_raw(_thumbhash_to_raw_bytes(hash_input))


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
