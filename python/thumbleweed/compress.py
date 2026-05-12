"""
thumbleweed.compress
====================
Image re-encoding/compression powered by the
`pixo <https://crates.io/crates/pixo>`_ Rust crate.

This is an **optional** subsystem; it must be opted into at wheel-build time
via the ``pixo`` cargo feature. When the wheel is built without it, every
function in this module degrades to a safe pass-through (the input bytes are
returned unchanged) so callers don't need to special-case the missing
backend.

Quick-start
-----------
>>> from thumbleweed import compress
>>> if compress.is_available():
...     smaller = compress.compress(jpeg_or_png_bytes, quality=85)
...
>>> # Auto-applied to thumbnails when the feature is on
>>> from thumbleweed import thumbnail
>>> thumb = thumbnail.create("photo.jpg", compress=True)  # default
"""

from __future__ import annotations

import io
import os
import pathlib
from typing import Any

from thumbleweed._core import (  # type: ignore[import]
    compress_detect_format as _detect_format,
)
from thumbleweed._core import (
    compress_image as _compress_image,
)
from thumbleweed._core import (
    compress_is_available as _is_available,
)

__all__ = [
    "compress",
    "compress_path",
    "is_available",
    "detect_format",
    "Format",
]

Format = ("auto", "jpeg", "jpg", "png")


def _to_bytes(source: Any) -> bytes:
    """Normalise ``source`` to raw encoded image bytes."""
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source)

    if isinstance(source, (str, pathlib.Path, os.PathLike)):
        with open(source, "rb") as fh:
            return fh.read()

    if hasattr(source, "read"):
        pos = source.tell() if hasattr(source, "tell") else None
        try:
            data = source.read()
        finally:
            if pos is not None and hasattr(source, "seek"):
                try:
                    source.seek(pos)
                except (OSError, ValueError):
                    pass
        return bytes(data)

    try:
        from PIL import Image  # noqa: PLC0415

        if isinstance(source, Image.Image):
            buf = io.BytesIO()
            # PNG is lossless so we don't introduce extra quality loss before
            # handing the bytes to pixo.
            source.convert("RGBA").save(buf, format="PNG")
            return buf.getvalue()
    except ImportError:
        pass

    raise TypeError(
        "compress: unsupported input type "
        f"{type(source).__name__!r}. Pass bytes, BytesIO, a file path, "
        "or a Pillow Image."
    )


def is_available() -> bool:
    """Return ``True`` if the wheel was built with the ``pixo`` cargo feature."""
    return bool(_is_available())


def detect_format(source: Any) -> str:
    """Detect the encoded format of ``source``.

    Returns one of ``"jpeg"``, ``"png"``, ``"webp"``, or ``"unknown"``.
    """
    data = _to_bytes(source)
    return _detect_format(data[:32] if len(data) > 32 else data)


def compress(
    source: Any,
    format: str = "auto",
    quality: int = 85,
) -> bytes:
    """Re-encode ``source`` using pixo's max-compression preset.

    Parameters
    ----------
    source:
        ``bytes`` / ``bytearray`` / ``memoryview`` / file path /
        file-like object / ``PIL.Image.Image``. The data must contain an
        encoded image (JPEG, PNG, WebP, …); raw RGBA pixel buffers are not
        supported here — use the lower-level ``thumbleweed._core``
        bindings if you have raw pixels already.
    format:
        ``"auto"`` (default), ``"jpeg"``, or ``"png"``. ``"auto"`` infers
        from the input's magic bytes; non-JPEG/PNG inputs (WebP, GIF,
        unknown) are returned unchanged.
    quality:
        1–100 (default 85). Only used for JPEG output; ignored for PNG.

    Returns
    -------
    bytes
        The re-encoded image, OR the original input if (a) pixo couldn't
        shrink it, (b) the format is one pixo doesn't handle, or (c) the
        wheel was built without the ``pixo`` cargo feature.
    """
    data = _to_bytes(source)
    return _compress_image(data, format=format, quality=quality)


def compress_path(
    input_path: str | os.PathLike[str],
    output_path: str | os.PathLike[str] | None = None,
    format: str = "auto",
    quality: int = 85,
) -> int:
    """Compress an image file in-place (or to ``output_path``).

    Returns the number of bytes saved (``original_size - new_size``); zero
    when nothing was written / no shrinkage was possible.
    """
    input_path = pathlib.Path(input_path)
    original = input_path.read_bytes()
    out = compress(original, format=format, quality=quality)
    if output_path is None:
        target = input_path
    else:
        target = pathlib.Path(output_path)
    if out == original and output_path is None:
        # Nothing to do, save a syscall.
        return 0
    target.write_bytes(out)
    return max(0, len(original) - len(out))
