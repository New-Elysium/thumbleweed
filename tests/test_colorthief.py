"""Tests for the colorthief Python library."""

from __future__ import annotations

import io
import pathlib

import colorthief
import pytest
import thumbleweed

# ── Helpers ──────────────────────────────────────────────────────────────────

# Create a tiny 1×1 red PNG in memory.
RED_PNG = bytes.fromhex(
    "89504e47"  # PNG signature
    "0d0a1a0a"
)

# A small valid PNG (1×1 red pixel) byte string.
_1X1_RED_PNG = bytes(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff"
    b"\xff?\x00\x05\xfe\x02\xfe\x3c\xe1\xdd\x59\x00\x00\x00\x00IEND\xae"
    b"B`\x82"
)


# A larger 4×4 solid-green PNG (RGBA 8-bit)
def _make_solid_png(r: int, g: int, b: int, a: int = 255) -> bytes:
    """Return a 4×4 RGBA PNG with every pixel the same colour."""
    import io
    import struct
    import zlib

    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"
    # IHDR chunk
    width, height = 4, 4
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = _png_chunk(b"IHDR", ihdr_data)
    # IDAT chunk (raw image data)
    raw = bytearray()
    for _ in range(height):
        raw.append(0)  # filter byte: none
        for _ in range(width):
            raw.extend([r, g, b, a])
    compressed = zlib.compress(bytes(raw), level=9)
    idat = _png_chunk(b"IDAT", compressed)
    # IEND chunk
    iend = _png_chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


def _png_chunk(name: bytes, data: bytes) -> bytes:
    import struct
    import zlib

    chunk = name + data
    crc = zlib.crc32(chunk) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", crc)


# ── TestColorThiefEncode ─────────────────────────────────────────────────────


class TestColorThiefEncode:
    """Core palette / dominant-colour tests using raw bytes."""

    def test_get_color_red(self):
        png = _make_solid_png(255, 0, 0)
        r, g, b = colorthief.get_color(png)
        assert isinstance(r, int)
        assert 0 <= r <= 255
        assert r > 200, f"Expected red to dominate, got {(r, g, b)}"
        assert g < 50
        assert b < 50

    def test_get_color_blue(self):
        png = _make_solid_png(0, 0, 255)
        r, g, b = colorthief.get_color(png)
        assert b > 200, f"Expected blue to dominate, got {(r, g, b)}"
        assert r < 50
        assert g < 50

    def test_get_color_green(self):
        png = _make_solid_png(0, 200, 0)
        r, g, b = colorthief.get_color(png)
        assert g > 150, f"Expected green to dominate, got {(r, g, b)}"
        assert r < 50
        assert b < 50

    def test_get_palette_returns_list(self):
        png = _make_solid_png(128, 64, 200)
        palette = colorthief.get_palette(png, color_count=5)
        assert isinstance(palette, list)
        assert len(palette) > 0
        for colour in palette:
            assert isinstance(colour, tuple)
            assert len(colour) == 3
            r, g, b = colour
            assert all(isinstance(ch, int) for ch in (r, g, b))
            assert all(0 <= ch <= 255 for ch in (r, g, b))

    def test_palette_deduplicated(self):
        # Solid colour should yield a single-dominant palette.
        png = _make_solid_png(255, 128, 0)
        palette = colorthief.get_palette(png, color_count=5)
        # At least one colour, and colours should be deduplicated.
        assert len(palette) >= 1

    def test_color_count_parameter(self):
        png = _make_solid_png(100, 100, 100)
        palette = colorthief.get_palette(png, color_count=3)
        assert len(palette) <= 3

    def test_quality_parameter(self):
        png = _make_solid_png(200, 50, 50)
        # Different quality should still return a valid colour.
        # Note: the color-thief crate only accepts quality in [1, 10].
        for q in (1, 5, 10):
            r, g, b = colorthief.get_color(png, quality=q)
            assert all(isinstance(ch, int) for ch in (r, g, b))


# ── TestColorThiefClass ────────────────────────────────────────────────────


class TestColorThiefClass:
    """Tests for the class-based API mimicking python-colorthief."""

    def test_class_get_color(self):
        png = _make_solid_png(255, 0, 0)
        ct = colorthief.ColorThief(png)
        r, g, b = ct.get_color()
        assert r > 200
        assert g < 50
        assert b < 50

    def test_class_get_palette(self):
        png = _make_solid_png(0, 0, 255)
        ct = colorthief.ColorThief(png)
        palette = ct.get_palette(color_count=3)
        assert isinstance(palette, list)
        assert len(palette) > 0
        assert len(palette) <= 3

    def test_class_accepts_bytearray(self):
        # ColorThief(image: bytes) should accept bytearray too.
        png = _make_solid_png(0, 255, 0)
        ct = colorthief.ColorThief(bytearray(png))
        r, g, b = ct.get_color()
        assert g > 200


# ── TestThumbleweedFlatAPI ─────────────────────────────────────────────────


class TestThumbleweedFlatAPI:
    """Tests for the flat ``thumbleweed.*`` functions."""

    def test_colorthief_get_color_bytes(self):
        png = _make_solid_png(128, 0, 0)
        r, g, b = thumbleweed.colorthief_get_color_bytes(png)
        assert r > 100
        assert g < 50
        assert b < 50

    def test_colorthief_get_palette_bytes(self):
        png = _make_solid_png(0, 128, 0)
        palette = thumbleweed.colorthief_get_palette_bytes(png, color_count=4)
        assert isinstance(palette, list)
        assert len(palette) > 0


# ── TestBytesIOAndPillowInput ────────────────────────────────────────────────


class TestBytesIOAndPillowInput:
    """Verify that all variants accept BytesIO and PIL.Image."""

    def test_get_color_image_from_bytesio(self):
        import io

        png = _make_solid_png(255, 0, 0)
        buf = io.BytesIO(png)
        r, g, b = colorthief.get_color_image(buf)
        assert r > 200
        assert g < 50
        assert b < 50

    def test_get_palette_image_from_bytesio(self):
        import io

        png = _make_solid_png(0, 0, 255)
        buf = io.BytesIO(png)
        palette = colorthief.get_palette_image(buf, color_count=3)
        assert isinstance(palette, list)
        assert len(palette) > 0

    def test_colorthief_class_from_bytesio(self):
        import io

        png = _make_solid_png(0, 200, 0)
        buf = io.BytesIO(png)
        ct = colorthief.ColorThief(buf)
        r, g, b = ct.get_color()
        assert g > 150

    def test_get_color_image_from_pil(self):
        pytest.importorskip("PIL")
        from PIL import Image

        img = Image.new("RGB", (16, 16), color=(255, 0, 0))
        r, g, b = colorthief.get_color_image(img)
        assert r > 200
        assert g < 50
        assert b < 50

    def test_get_palette_image_from_pil(self):
        pytest.importorskip("PIL")
        from PIL import Image

        img = Image.new("RGB", (16, 16), color=(0, 0, 255))
        palette = colorthief.get_palette_image(img, color_count=3)
        assert isinstance(palette, list)
        assert len(palette) > 0

    def test_colorthief_class_from_pil(self):
        pytest.importorskip("PIL")
        from PIL import Image

        img = Image.new("RGB", (16, 16), color=(0, 200, 0))
        ct = colorthief.ColorThief(img)
        r, g, b = ct.get_color()
        assert g > 150

    def test_thumbleweed_get_color_image_bytesio(self):
        import io

        png = _make_solid_png(128, 0, 0)
        buf = io.BytesIO(png)
        r, g, b = thumbleweed.colorthief_get_color_image(buf)
        assert r > 100
        assert g < 50
        assert b < 50

    def test_thumbleweed_get_palette_image_bytesio(self):
        import io

        png = _make_solid_png(0, 128, 0)
        buf = io.BytesIO(png)
        palette = thumbleweed.colorthief_get_palette_image(buf, color_count=3)
        assert isinstance(palette, list)
        assert len(palette) > 0


class TestErrorHandling:
    """Error handling tests."""

    def test_invalid_bytes(self):
        with pytest.raises(ValueError):
            colorthief.get_color(b"not-an-image")

    def test_empty_bytes(self):
        with pytest.raises(ValueError):
            colorthief.get_color(b"")

    def test_invalid_path(self):
        with pytest.raises(ValueError):
            colorthief.get_color_from_file("/nonexistent/file.jpg")

    def test_invalid_path_palette(self):
        with pytest.raises(ValueError):
            colorthief.get_palette_from_file("/nonexistent/file.jpg")


# ── TestFilePathAPI ─────────────────────────────────────────────────────────


class TestFilePathAPI:
    """Tests for the file/path/bytes APIs using the real test images."""

    @pytest.fixture(params=["one.jpg", "two.jpg", "four.jpg", "OPS.jpg"])
    def image_path(self, request):
        path = pathlib.Path(__file__).parent / request.param
        assert path.exists(), f"Test image not found: {path}"
        return path

    def test_file_based_dominant_color(self, image_path):
        colour = colorthief.get_color_from_file(str(image_path))
        r, g, b = colour
        assert all(isinstance(ch, int) for ch in (r, g, b))
        assert all(0 <= ch <= 255 for ch in (r, g, b))

    def test_file_based_palette(self, image_path):
        palette = colorthief.get_palette_from_file(str(image_path), color_count=3)
        assert isinstance(palette, list)
        assert len(palette) > 0
        assert len(palette) <= 3

    def test_class_with_file_bytes(self, image_path):
        ct = colorthief.ColorThief(image_path.read_bytes())
        r, g, b = ct.get_color()
        assert all(isinstance(ch, int) for ch in (r, g, b))
        assert all(0 <= ch <= 255 for ch in (r, g, b))

    def test_get_color_image_from_real_image_bytesio(self, image_path):
        buf = io.BytesIO(image_path.read_bytes())
        r, g, b = colorthief.get_color_image(buf)
        assert all(isinstance(ch, int) for ch in (r, g, b))
        assert all(0 <= ch <= 255 for ch in (r, g, b))
