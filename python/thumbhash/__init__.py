"""thumbhash
=========
Fast ThumbHash encode/decode for Python, backed by a Rust extension.

This is a compatibility shim — everything is also available via
``import thumbleweed``.

Quick-start
-----------
>>> import thumbhash
>>> # From raw RGBA bytes
>>> hash_bytes = thumbhash.encode(w, h, rgba_bytes)
>>> w, h, rgba = thumbhash.decode(hash_bytes)

>>> # From / to a Pillow Image (requires  pip install thumbleweed[pillow])
>>> from PIL import Image
>>> img = Image.open("photo.jpg")
>>> hash_str = thumbhash.encode_image(img)   # returns a base64 string
>>> placeholder = thumbhash.decode_image(hash_str)

>>> # From a BytesIO / bytes / file path — no Pillow required
>>> import io
>>> with open("photo.jpg", "rb") as f:
...     hash_str = thumbhash.encode_image(f.read())
>>> buf = io.BytesIO(open("photo.jpg", "rb").read())
>>> hash_str = thumbhash.encode_image(buf)
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

from thumbleweed._core import (  # type: ignore[import]
    __version__,
)
from thumbleweed._core import (  # type: ignore[import]
    thumbhash_approximate_aspect_ratio as _approximate_aspect_ratio,
)
from thumbleweed._core import (  # type: ignore[import]
    thumbhash_average_rgba as _average_rgba,
)
from thumbleweed._core import (
    thumbhash_decode as decode,
)
from thumbleweed._core import (
    thumbhash_encode as encode,
)

# ── Helpers to accept both raw bytes and base64 strings ─────────────────────


def _to_raw_bytes(hash_input: bytes | bytearray | str) -> bytes:
    """Convert a ThumbHash to raw bytes, accepting either raw bytes or a base64 string."""
    import base64

    if isinstance(hash_input, str):
        return base64.b64decode(hash_input)
    return bytes(hash_input)


def average_rgba(
    hash_input: bytes | bytearray | str,
) -> tuple[float, float, float, float]:
    """Extract the average colour from a ThumbHash.

    Accepts raw bytes / bytearray, or a base64-encoded string
    (as returned by :func:`encode_image`).

    Returns
    -------
    tuple[float, float, float, float]
        ``(r, g, b, a)`` each in ``[0.0, 1.0]``. RGB is **not** premultiplied.
    """
    return _average_rgba(_to_raw_bytes(hash_input))


def approximate_aspect_ratio(hash_input: bytes | bytearray | str) -> float:
    """Return the approximate aspect ratio (width / height) of the original image.

    Accepts raw bytes / bytearray, or a base64-encoded string
    (as returned by :func:`encode_image`).
    """
    return _approximate_aspect_ratio(_to_raw_bytes(hash_input))


# ── Internal helpers ─────────────────────────────────────────────────────────


def _read_bytes(source: object) -> bytes:
    """Normalise *source* to raw file bytes (not decoded pixels).

    Accepts:
    - ``bytes`` / ``bytearray`` / ``memoryview``  — returned as-is (or copied).
    - ``io.IOBase`` / any file-like with ``.read()`` — read to end.
    - ``str`` / ``pathlib.Path`` — opened in binary mode.

    Raises ``TypeError`` for anything else (e.g. a Pillow Image).
    """
    import io
    import pathlib

    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source)
    if isinstance(source, (str, pathlib.Path)):
        try:
            with open(source, "rb") as fh:
                return fh.read()
        except FileNotFoundError as exc:
            raise ValueError(f"Image file not found: {source}") from exc
    if hasattr(source, "read"):
        pos = source.tell() if hasattr(source, "tell") else None
        data = source.read()
        if pos is not None and hasattr(source, "seek"):
            source.seek(pos)
        return bytes(data)
    raise TypeError(
        f"encode_image() does not know how to handle {type(source).__name__!r}. "
        "Pass a Pillow Image, bytes, bytearray, BytesIO, or a file path."
    )


def _pil_encode(img: object) -> bytes:
    """Encode a Pillow Image to ThumbHash bytes (internal, Pillow must be present)."""
    from PIL import Image  # noqa: PLC0415

    pil_img: Image.Image = img.convert("RGBA")  # type: ignore[union-attr]

    max_side = 100
    w, h = pil_img.size
    if w > max_side or h > max_side:
        scale = max_side / max(w, h)
        new_w = max(1, round(w * scale))
        new_h = max(1, round(h * scale))
        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

    w, h = pil_img.size
    return encode(w, h, pil_img.tobytes())


def _decode_file_bytes_to_pil(data: bytes) -> "Image.Image":  # noqa: F821
    """Load raw image-file bytes into a Pillow Image (Pillow must be present)."""
    import io

    from PIL import Image  # noqa: PLC0415

    return Image.open(io.BytesIO(data))


# ── Optional Pillow helpers ──────────────────────────────────────────────────


def encode_image(image: object) -> str:
    """Encode an image to a ThumbHash.

    Accepts a wide range of input types — Pillow is only required when
    ``image`` is a :class:`PIL.Image.Image` object:

    - :class:`PIL.Image.Image` — converted to ``RGBA`` and resized (requires
      Pillow).
    - :class:`bytes` / :class:`bytearray` / :class:`memoryview` — treated as
      raw encoded image data (PNG, JPEG, WebP, etc.) and decoded via Pillow.
    - :class:`io.BytesIO` or any file-like with ``.read()`` — read then
      decoded as above.
    - :class:`str` / :class:`pathlib.Path` — opened and decoded as above.

    Parameters
    ----------
    image:
        Image source (see above).

    Returns
    -------
    str
        Base64-encoded ThumbHash string, suitable for JSON transport.

    Raises
    ------
    ImportError
        If Pillow is not installed and the input is not already a decoded
        pixel buffer.
    TypeError
        If the input type is unsupported.
    """
    import base64

    # Fast path — already a Pillow Image.
    try:
        from PIL import Image  # noqa: PLC0415

        if isinstance(image, Image.Image):
            raw = _pil_encode(image)
            return base64.b64encode(raw).decode("ascii")
    except ImportError:
        pass

    # For all other types, get the raw file bytes first, then use Pillow to
    # decode into pixels.
    _require_pillow()
    raw_bytes = _read_bytes(image)
    pil_img = _decode_file_bytes_to_pil(raw_bytes)
    raw = _pil_encode(pil_img)
    return base64.b64encode(raw).decode("ascii")


def decode_image(
    hash_input: bytes | bytearray | str,
) -> "Image.Image":  # noqa: F821
    """Decode a ThumbHash to a Pillow :class:`~PIL.Image.Image`.

    Parameters
    ----------
    hash_input:
        ThumbHash payload — either raw bytes / bytearray, or a base64-encoded
        string (as returned by :func:`encode_image`).

    Returns
    -------
    PIL.Image.Image
        A small (≈ 32 px) ``RGBA`` placeholder image.

    Raises
    ------
    ImportError
        If Pillow is not installed.
    ValueError
        If ``hash_input`` is invalid or too short.
    """
    import base64

    _require_pillow()
    from PIL import Image  # noqa: PLC0415

    if isinstance(hash_input, str):
        hash_bytes = base64.b64decode(hash_input)
    else:
        hash_bytes = bytes(hash_input)

    w, h, rgba_bytes = decode(hash_bytes)
    return Image.frombytes("RGBA", (w, h), rgba_bytes)


def _require_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for image helpers. "
            "Install it with:  pip install thumbleweed[pillow]"
        ) from exc
