"""
thumbleweed.thumbnail
=====================
Real (rasterised) thumbnail extraction for **images, videos, and PDFs**.

Two backends ship in the wheel:

* **crude** — always available; pure Rust. Resizes images via the
  ``image`` crate, scrapes embedded cover art from MP4 containers
  (iTunes-style ``covr`` atom), scrapes the first JPEG (``/DCTDecode``)
  XObject from PDFs, and falls back to a deterministic colour-gradient
  placeholder when no embedded image can be found.
* **auto-thumbnail** — uses the
  `auto-thumbnail <https://crates.io/crates/auto-thumbnail>`_ crate.
  This backend is optional and requires the wheel to have been built
  with the ``auto-thumbnail`` cargo feature, which currently pulls in
  both ``pdfium-render`` and ``ffmpeg``/``video-rs`` as an all-or-nothing
  dependency set.

Quick-start
-----------
>>> from thumbleweed import thumbnail
>>> # bytes / BytesIO / path / Pillow Image are all accepted
>>> jpeg = thumbnail.create("video.mp4", width=256, height=256)
>>> with open("thumb.png", "wb") as fh:
...     fh.write(thumbnail.create("doc.pdf", format="png"))
>>> thumbnail.save("photo.jpg", "photo_thumb.jpg", width=128, height=128)

>>> # Inspect what backends are available in this wheel
>>> thumbnail.available_backends()
['crude', 'auto-thumbnail']
"""

from __future__ import annotations

import io
import os
import pathlib
from typing import Any

from thumbleweed._core import (  # type: ignore[import]
    thumbnail_available_backends as _available_backends,
)
from thumbleweed._core import (
    thumbnail_create_from_bytes as _create_from_bytes,
)
from thumbleweed._core import (
    thumbnail_create_from_path as _create_from_path,
)
from thumbleweed._core import (
    thumbnail_detect_kind as _detect_kind,
)
from thumbleweed._core import (
    thumbnail_save as _save_native,
)

__all__ = [
    "create",
    "create_from_bytes",
    "create_from_path",
    "save",
    "detect_kind",
    "available_backends",
    "Engine",
    "OutputFormat",
]

# Re-export the literal sets as module constants for discoverability.
Engine = ("auto", "crude", "auto-thumbnail")
OutputFormat = ("jpeg", "jpg", "png", "webp")


# ── Input normalisation ──────────────────────────────────────────────────────


def _is_pil_image(obj: Any) -> bool:
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        return False
    return isinstance(obj, Image.Image)


def _to_bytes(source: Any) -> bytes:
    """Normalise a source to raw encoded bytes.

    Accepts ``bytes``, ``bytearray``, ``memoryview``, file paths
    (``str`` / ``os.PathLike``), file-like objects with ``.read()``,
    and ``PIL.Image.Image`` objects (encoded to PNG).
    """
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

    if _is_pil_image(source):
        buf = io.BytesIO()
        # RGBA preserves alpha so the crude/auto pipelines can pick the right
        # output format. JPEG output will flatten this on the Rust side.
        source.convert("RGBA").save(buf, format="PNG")
        return buf.getvalue()

    raise TypeError(
        "thumbnail: unsupported input type "
        f"{type(source).__name__!r}. Pass bytes, BytesIO, a file path, "
        "or a Pillow Image."
    )


# ── Public API ───────────────────────────────────────────────────────────────


def create(
    source: Any,
    width: int = 256,
    height: int = 256,
    quality: int = 85,
    format: str = "jpeg",
    engine: str = "auto",
    compress: bool = True,
) -> bytes:
    """Create a thumbnail from any supported source.

    Parameters
    ----------
    source:
        ``bytes`` / ``bytearray`` / ``memoryview`` / file path /
        file-like object / ``PIL.Image.Image``.
    width, height:
        Maximum thumbnail dimensions. Aspect ratio is preserved.
    quality:
        1–100 (default 85), used for JPEG and lossy WebP encoding.
    format:
        ``"jpeg"`` (default), ``"png"``, or ``"webp"``.
    engine:
        ``"auto"`` (default), ``"crude"``, or ``"auto-thumbnail"``.
    compress:
        When ``True`` (default) and the wheel was built with the ``pixo``
        cargo feature, automatically re-encode the JPEG/PNG thumbnail using
        pixo's max-compression preset. WebP outputs and inputs that pixo
        cannot shrink are returned unchanged. This is a no-op when the
        ``pixo`` feature is not compiled in, so it's always safe to leave on.

    Returns
    -------
    bytes
        Encoded thumbnail in the requested ``format``.
    """
    # Fast path: file paths can go straight through to Rust without an extra
    # round-trip through Python bytes.
    if isinstance(source, (str, pathlib.Path, os.PathLike)) and not _is_pil_image(
        source
    ):
        return _create_from_path(
            os.fspath(source),
            width=width,
            height=height,
            quality=quality,
            format=format,
            engine=engine,
            compress=compress,
        )

    data = _to_bytes(source)
    return _create_from_bytes(
        data,
        width=width,
        height=height,
        quality=quality,
        format=format,
        engine=engine,
        compress=compress,
    )


def create_from_bytes(
    data: bytes | bytearray | memoryview,
    width: int = 256,
    height: int = 256,
    quality: int = 85,
    format: str = "jpeg",
    engine: str = "auto",
    compress: bool = True,
) -> bytes:
    """Create a thumbnail from raw bytes."""
    return _create_from_bytes(
        bytes(data),
        width=width,
        height=height,
        quality=quality,
        format=format,
        engine=engine,
        compress=compress,
    )


def create_from_path(
    path: str | os.PathLike[str],
    width: int = 256,
    height: int = 256,
    quality: int = 85,
    format: str = "jpeg",
    engine: str = "auto",
    compress: bool = True,
) -> bytes:
    """Create a thumbnail from a file path."""
    return _create_from_path(
        os.fspath(path),
        width=width,
        height=height,
        quality=quality,
        format=format,
        engine=engine,
        compress=compress,
    )


def save(
    source: Any,
    output_path: str | os.PathLike[str],
    width: int = 256,
    height: int = 256,
    quality: int = 85,
    format: str | None = None,
    engine: str = "auto",
    compress: bool = True,
) -> None:
    """Create a thumbnail and write it to ``output_path``.

    When ``format`` is ``None``, the format is inferred from the output path's
    file extension (defaulting to JPEG).
    """
    output_path = os.fspath(output_path)

    # If we have a real path on disk, hand it directly to Rust to avoid an
    # unnecessary round-trip.
    if isinstance(source, (str, pathlib.Path, os.PathLike)) and not _is_pil_image(
        source
    ):
        _save_native(
            os.fspath(source),
            output_path,
            width=width,
            height=height,
            quality=quality,
            format=format,
            engine=engine,
            compress=compress,
        )
        return

    inferred = pathlib.Path(output_path).suffix.lstrip(".") or "jpeg"
    fmt = format or inferred
    data = create(
        source,
        width=width,
        height=height,
        quality=quality,
        format=fmt,
        engine=engine,
        compress=compress,
    )
    with open(output_path, "wb") as fh:
        fh.write(data)


def detect_kind(source: Any) -> str:
    """Detect the source kind from magic bytes.

    Returns one of ``"image"``, ``"video"``, ``"pdf"``, or ``"unknown"``.
    """
    data = _to_bytes(source)
    return _detect_kind(data[:64] if len(data) > 64 else data)


def available_backends() -> list[str]:
    """Return the list of thumbnail backends compiled into this wheel."""
    return list(_available_backends())
