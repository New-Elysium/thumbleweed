"""Type stubs for the compiled Rust extension ``thumbleweed._core``."""

__version__: str

# ── ThumbHash ─────────────────────────────────────────────────────────────────

def thumbhash_encode(w: int, h: int, rgba: bytes | bytearray) -> bytes:
    """Encode raw RGBA bytes to a ThumbHash."""
    ...

def thumbhash_decode(hash: bytes | bytearray) -> tuple[int, int, bytes]:
    """Decode a ThumbHash to raw RGBA bytes."""
    ...

def thumbhash_average_rgba(
    hash: bytes | bytearray,
) -> tuple[float, float, float, float]:
    """Extract the average colour from a ThumbHash."""
    ...

def thumbhash_approximate_aspect_ratio(hash: bytes | bytearray) -> float:
    """Return the approximate aspect ratio (width / height) of the original image."""
    ...

# ── BlurHash ──────────────────────────────────────────────────────────────────

def blurhash_decode(blur_hash: str, width: int, height: int) -> bytes:
    """Decode a BlurHash string to RGBA pixels."""
    ...

def blurhash_encode(
    pixels: bytes | bytearray,
    cx: int,
    cy: int,
    width: int,
    height: int,
) -> str:
    """Encode RGBA pixels to a BlurHash string."""
    ...

# ── ColorThief ───────────────────────────────────────────────────────────────

def colorthief_get_color_bytes(
    image: bytes | bytearray, quality: int | None = None
) -> tuple[int, int, int]:
    """Extract the dominant colour from raw image bytes.

    Parameters
    ----------
    image:
        Raw image data (PNG, JPEG, WebP, BMP, GIF, TIFF, etc.).
    quality:
        Quality/bias parameter. Default 10.

    Returns
    -------
    tuple[int, int, int]
        ``(r, g, b)`` each in [0, 255].
    """
    ...

# Note: image-aware helpers (encode_image, get_color, get_palette, etc.) that
# accept BytesIO / bytes / PIL.Image / paths live in the thumbhash, blurhash,
# and colorthief shim packages and are re-exported by thumbleweed.__init__.
#
# thumbhash_encode_image returns a base64-encoded string.
# thumbhash_decode_image accepts base64 string or raw bytes.

def colorthief_get_palette_bytes(
    image: bytes | bytearray,
    color_count: int | None = None,
    quality: int | None = None,
) -> list[tuple[int, int, int]]:
    """Extract a colour palette from raw image bytes.

    Parameters
    ----------
    image:
        Raw image data (PNG, JPEG, WebP, BMP, GIF, TIFF, etc.).
    color_count:
        Maximum number of palette entries. Default 10.
    quality:
        Quality/bias parameter. Default 10.

    Returns
    -------
    list[tuple[int, int, int]]
        Deduplicated list of ``(r, g, b)`` colours.
    """
    ...
