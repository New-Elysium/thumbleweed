"""
thumbleweed
===========
Fast ThumbHash encode/decode for Python, backed by a Rust extension.

This is an alias package — everything is also available via ``import thumbhash``.

Quick-start
-----------
>>> import thumbleweed
>>> # From raw RGBA bytes
>>> hash_bytes = thumbleweed.encode(w, h, rgba_bytes)
>>> w, h, rgba = thumbleweed.decode(hash_bytes)

>>> # From / to a Pillow Image (requires  pip install thumbleweed[pillow])
>>> from PIL import Image
>>> img = Image.open("photo.jpg")
>>> hash_bytes = thumbleweed.encode_image(img)
>>> placeholder = thumbleweed.decode_image(hash_bytes)
"""

from __future__ import annotations

# Re-export the entire public API from the thumbhash package.
from thumbhash import (  # noqa: F401
    __all__,
    __version__,
    approximate_aspect_ratio,
    average_rgba,
    decode,
    decode_image,
    encode,
    encode_image,
)
