"""
colorthief
==========
Dominant colour and palette extraction for Python, backed by a Rust extension.

This is a compatibility shim — everything is also available via
``import thumbleweed``.

Quick-start
-----------
>>> import colorthief
>>> # From raw image bytes (PNG, JPEG, WebP, …)
>>> dominant = colorthief.get_color(image_bytes)
>>> palette = colorthief.get_palette(image_bytes, color_count=5)

>>> # From a file path
>>> dominant = colorthief.get_color_from_file("photo.jpg")
>>> palette = colorthief.get_palette_from_file("photo.jpg", color_count=5)

>>> # From a BytesIO object or Pillow Image
>>> import io
>>> buf = io.BytesIO(open("photo.jpg", "rb").read())
>>> dominant = colorthief.get_color_image(buf)
>>> palette = colorthief.get_palette_image(buf, color_count=5)
"""

from __future__ import annotations

__all__ = [
    "get_color",
    "get_palette",
    "get_color_from_file",
    "get_palette_from_file",
    "get_color_image",
    "get_palette_image",
    "ColorThief",
    "__version__",
]

from thumbleweed._core import (  # type: ignore[import]
    __version__,
)
from thumbleweed._core import (
    colorthief_get_color as get_color_from_file,
)
from thumbleweed._core import (
    colorthief_get_color_bytes as get_color,
)
from thumbleweed._core import (
    colorthief_get_palette as get_palette_from_file,
)
from thumbleweed._core import (
    colorthief_get_palette_bytes as get_palette,
)

# ── Internal helpers ─────────────────────────────────────────────────────────


def _to_image_bytes(source: object) -> bytes:
    """Normalise *source* to raw encoded image bytes (PNG / JPEG / …).

    Accepts:
    - ``bytes`` / ``bytearray`` / ``memoryview`` — assumed to already be
      encoded image data; returned as-is (or copied).
    - File-like objects with ``.read()`` (e.g. ``io.BytesIO``) — read in full.
    - ``str`` / ``pathlib.Path`` — opened in binary mode.
    - :class:`PIL.Image.Image` — saved to an in-memory PNG buffer (requires
      Pillow).

    Raises ``TypeError`` for unsupported types.
    """
    import pathlib

    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source)

    if isinstance(source, (str, pathlib.Path)):
        with open(source, "rb") as fh:
            return fh.read()

    if hasattr(source, "read"):
        pos = source.tell() if hasattr(source, "tell") else None
        data = source.read()
        if pos is not None and hasattr(source, "seek"):
            source.seek(pos)
        return bytes(data)

    # Pillow Image — save to an in-memory PNG
    try:
        from PIL import Image  # noqa: PLC0415

        if isinstance(source, Image.Image):
            import io

            buf = io.BytesIO()
            # Convert to RGB so color-thief gets sensible colours.
            source.convert("RGB").save(buf, format="PNG")
            return buf.getvalue()
    except ImportError:
        pass

    raise TypeError(
        f"colorthief: unsupported input type {type(source).__name__!r}. "
        "Pass bytes, bytearray, BytesIO, a file path, or a Pillow Image."
    )


# ── Image-aware convenience functions ────────────────────────────────────────


def get_color_image(
    image: object,
    quality: int = 10,
) -> tuple[int, int, int]:
    """Extract the dominant colour from any image source.

    Accepts :class:`PIL.Image.Image`, :class:`bytes`, :class:`bytearray`,
    :class:`io.BytesIO` (or any file-like), ``str`` / :class:`pathlib.Path`.

    Parameters
    ----------
    image:
        Image source (see above).
    quality:
        Quality/bias parameter (lower = faster). Default 10.

    Returns
    -------
    tuple[int, int, int]
        ``(r, g, b)`` each in [0, 255].
    """
    return get_color(_to_image_bytes(image), quality)


def get_palette_image(
    image: object,
    color_count: int = 10,
    quality: int = 10,
) -> list[tuple[int, int, int]]:
    """Extract a colour palette from any image source.

    Accepts :class:`PIL.Image.Image`, :class:`bytes`, :class:`bytearray`,
    :class:`io.BytesIO` (or any file-like), ``str`` / :class:`pathlib.Path`.

    Parameters
    ----------
    image:
        Image source (see above).
    color_count:
        Maximum number of palette entries. Default 10.
    quality:
        Quality/bias parameter. Default 10.

    Returns
    -------
    list[tuple[int, int, int]]
        List of ``(r, g, b)`` tuples, each in [0, 255].
    """
    return get_palette(_to_image_bytes(image), color_count, quality)


# --------------------------------------------------------------------------
# Compatibility shim — class-based API mimicking the Python colorthief
# package as closely as possible.
# --------------------------------------------------------------------------


class ColorThief:
    """Extract dominant colours and palettes from an image.

    Accepts the same input types as :func:`get_color_image`:
    :class:`PIL.Image.Image`, :class:`bytes`, :class:`bytearray`,
    :class:`io.BytesIO` (or any file-like), ``str`` / :class:`pathlib.Path`.

    Parameters
    ----------
    image : bytes | bytearray | BytesIO | str | Path | PIL.Image.Image
        Image source.
    """

    def __init__(self, image: object) -> None:
        self._image = _to_image_bytes(image)

    def get_color(self, quality: int = 10) -> tuple[int, int, int]:
        """Return the dominant colour as ``(r, g, b)``.

        Parameters
        ----------
        quality : int, default 10
            Quality/bias parameter (lower = faster, less accurate).
        """
        return get_color(self._image, quality)

    def get_palette(
        self, color_count: int = 10, quality: int = 10
    ) -> list[tuple[int, int, int]]:
        """Return a colour palette as a list of ``(r, g, b)`` tuples.

        Parameters
        ----------
        color_count : int, default 10
            Maximum number of colours to return.
        quality : int, default 10
            Quality/bias parameter (lower = faster, less accurate).
        """
        return get_palette(self._image, color_count, quality)
