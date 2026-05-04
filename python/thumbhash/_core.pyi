"""Type stubs for the compiled Rust extension ``thumbhash._core``."""

__version__: str

def encode(w: int, h: int, rgba: bytes | bytearray) -> bytes:
    """Encode raw RGBA bytes to a ThumbHash.

    Parameters
    ----------
    w:
        Image width in pixels (must be ≤ 100).
    h:
        Image height in pixels (must be ≤ 100).
    rgba:
        Raw pixel data, row-major, 4 bytes per pixel (R G B A).
        RGB must **not** be premultiplied by A.

    Returns
    -------
    bytes
        ThumbHash payload (typically 5–32 bytes).
    """
    ...

def decode(hash: bytes | bytearray) -> tuple[int, int, bytes]:
    """Decode a ThumbHash to raw RGBA bytes.

    Parameters
    ----------
    hash:
        ThumbHash payload.

    Returns
    -------
    tuple[int, int, bytes]
        ``(width, height, rgba_bytes)`` – raw row-major RGBA data,
        not premultiplied by alpha.
    """
    ...

def average_rgba(hash: bytes | bytearray) -> tuple[float, float, float, float]:
    """Extract the average colour from a ThumbHash.

    Returns
    -------
    tuple[float, float, float, float]
        ``(r, g, b, a)`` each in ``[0, 1]``.
        RGB is **not** premultiplied by A.
    """
    ...

def approximate_aspect_ratio(hash: bytes | bytearray) -> float:
    """Return the approximate aspect ratio (width / height) of the original image."""
    ...
