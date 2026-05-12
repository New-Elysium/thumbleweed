"""Type stubs for the compiled Rust extension ``thumbleweed._core``."""

__version__: str

# ── ThumbHash ─────────────────────────────────────────────────────────────────

def thumbhash_encode(w: int, h: int, rgba: bytes | bytearray) -> bytes:
    """Encode raw RGBA bytes to a ThumbHash."""
    ...

def thumbhash_encode_image_bytes(image: bytes | bytearray) -> bytes:
    """Encode raw PNG/JPEG/WebP/GIF/BMP image bytes to raw ThumbHash bytes."""
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

def blurhash_encode_image_bytes(
    image: bytes | bytearray,
    cx: int,
    cy: int,
) -> str:
    """Encode raw PNG/JPEG/WebP/GIF/BMP image bytes to a BlurHash string."""
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

# ── Thumbnail ────────────────────────────────────────────────────────────────

def thumbnail_create_from_bytes(
    data: bytes | bytearray,
    width: int = 256,
    height: int = 256,
    quality: int = 85,
    format: str = "jpeg",
    engine: str = "auto",
    compress: bool = True,
) -> bytes:
    """Create a thumbnail from raw image / video / PDF bytes."""
    ...

def thumbnail_create_from_path(
    path: str,
    width: int = 256,
    height: int = 256,
    quality: int = 85,
    format: str = "jpeg",
    engine: str = "auto",
    compress: bool = True,
) -> bytes:
    """Create a thumbnail from a file path."""
    ...

def thumbnail_save(
    input_path: str,
    output_path: str,
    width: int = 256,
    height: int = 256,
    quality: int = 85,
    format: str | None = None,
    engine: str = "auto",
    compress: bool = True,
) -> None:
    """Create a thumbnail and write it to ``output_path``."""
    ...

def thumbnail_detect_kind(data: bytes | bytearray) -> str:
    """Detect the source kind: ``"image"`` | ``"video"`` | ``"pdf"`` | ``"unknown"``."""
    ...

def thumbnail_available_backends() -> list[str]:
    """Return the list of compiled-in thumbnail backends."""
    ...

# ── Compression (pixo) ─────────────────────────────────────────────────────────

def compress_image(
    data: bytes | bytearray,
    format: str = "auto",
    quality: int = 85,
) -> bytes:
    """Re-encode an image using pixo's max-compression preset."""
    ...

def compress_is_available() -> bool:
    """Return True iff the wheel was built with the ``pixo`` cargo feature."""
    ...

def compress_detect_format(data: bytes | bytearray) -> str:
    """Detect encoded format: ``"jpeg"`` | ``"png"`` | ``"webp"`` | ``"unknown"``."""
    ...
