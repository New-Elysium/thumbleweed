"""
thumbhash
=========
Fast ThumbHash encode/decode for Python, backed by a Rust extension.

Quick-start
-----------
>>> import thumbhash
>>> # From raw RGBA bytes
>>> hash_bytes = thumbhash.encode(w, h, rgba_bytes)
>>> w, h, rgba = thumbhash.decode(hash_bytes)

>>> # From / to a Pillow Image (requires  pip install thumbhash[pillow])
>>> from PIL import Image
>>> img  = Image.open("photo.jpg")
>>> hash_bytes = thumbhash.encode_image(img)
>>> placeholder = thumbhash.decode_image(hash_bytes)
"""

from __future__ import annotations

__all__ = [
    "encode",
    "decode",
    "average_rgba",
    "approximate_aspect_ratio",
    "encode_image",
    "decode_image",
    "__version__",
]

from ._core import (  # type: ignore[import]
    encode,
    decode,
    average_rgba,
    approximate_aspect_ratio,
    __version__,
)


# ── Optional Pillow helpers ──────────────────────────────────────────────────

def encode_image(image: "Image.Image") -> bytes:  # noqa: F821
    """Encode a Pillow :class:`~PIL.Image.Image` to a ThumbHash.

    The image is automatically converted to ``RGBA`` mode and resized so
    that the longer edge is at most 100 pixels (required by the algorithm).

    Parameters
    ----------
    image:
        Any Pillow image.

    Returns
    -------
    bytes
        ThumbHash payload (typically 5–32 bytes).

    Raises
    ------
    ImportError
        If Pillow is not installed.  Install it with
        ``pip install thumbhash[pillow]``.
    """
    _require_pillow()
    from PIL import Image  # noqa: PLC0415

    img: Image.Image = image.convert("RGBA")

    # Clamp the longest side to 100 px
    max_side = 100
    w, h = img.size
    if w > max_side or h > max_side:
        scale = max_side / max(w, h)
        new_w = max(1, round(w * scale))
        new_h = max(1, round(h * scale))
        img = img.resize((new_w, new_h), Image.LANCZOS)

    w, h = img.size
    rgba_bytes: bytes = img.tobytes()
    return encode(w, h, rgba_bytes)


def decode_image(
    hash_bytes: bytes | bytearray,
) -> "Image.Image":  # noqa: F821
    """Decode a ThumbHash to a Pillow :class:`~PIL.Image.Image`.

    Parameters
    ----------
    hash_bytes:
        ThumbHash payload.

    Returns
    -------
    PIL.Image.Image
        A small (≈ 32 px) ``RGBA`` placeholder image.

    Raises
    ------
    ImportError
        If Pillow is not installed.
    ValueError
        If ``hash_bytes`` is invalid or too short.
    """
    _require_pillow()
    from PIL import Image  # noqa: PLC0415

    w, h, rgba_bytes = decode(bytes(hash_bytes))
    return Image.frombytes("RGBA", (w, h), rgba_bytes)


def _require_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for image helpers. "
            "Install it with:  pip install thumbhash[pillow]"
        ) from exc
