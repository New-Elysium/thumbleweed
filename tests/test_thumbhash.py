"""Tests for the thumbhash Python library."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
import thumbhash

# ── Helpers ──────────────────────────────────────────────────────────────────


def _solid_rgba(w: int, h: int, r: int, g: int, b: int, a: int = 255) -> bytes:
    """Return a flat RGBA buffer filled with one colour."""
    return bytes([r, g, b, a] * (w * h))


# ── encode / decode round-trip ───────────────────────────────────────────────


class TestEncode:
    def test_returns_bytes(self):
        rgba = _solid_rgba(8, 8, 255, 0, 0)
        result = thumbhash.encode(8, 8, rgba)
        assert isinstance(result, bytes)
        assert len(result) >= 5

    def test_different_images_differ(self):
        red = thumbhash.encode(8, 8, _solid_rgba(8, 8, 255, 0, 0))
        blue = thumbhash.encode(8, 8, _solid_rgba(8, 8, 0, 0, 255))
        assert red != blue

    def test_accepts_bytearray(self):
        rgba = bytearray(_solid_rgba(10, 10, 128, 128, 128))
        result = thumbhash.encode(10, 10, rgba)
        assert isinstance(result, bytes)

    def test_max_size(self):
        rgba = _solid_rgba(100, 100, 0, 255, 0)
        result = thumbhash.encode(100, 100, rgba)
        assert len(result) >= 5

    def test_landscape(self):
        rgba = _solid_rgba(100, 50, 255, 255, 0)
        result = thumbhash.encode(100, 50, rgba)
        ratio = thumbhash.approximate_aspect_ratio(result)
        assert ratio > 1.0

    def test_portrait(self):
        rgba = _solid_rgba(50, 100, 0, 255, 255)
        result = thumbhash.encode(50, 100, rgba)
        ratio = thumbhash.approximate_aspect_ratio(result)
        assert ratio < 1.0

    def test_with_alpha(self):
        rgba = _solid_rgba(8, 8, 200, 100, 50, 128)  # semi-transparent
        result = thumbhash.encode(8, 8, rgba)
        r, g, b, a = thumbhash.average_rgba(result)
        assert 0.0 <= a <= 1.0

    def test_size_too_large_raises(self):
        rgba = _solid_rgba(101, 1, 0, 0, 0)
        with pytest.raises(ValueError):
            thumbhash.encode(101, 1, rgba)

    def test_wrong_buffer_length_raises(self):
        with pytest.raises(ValueError):
            thumbhash.encode(8, 8, b"\x00" * 10)  # should be 256 bytes


class TestDecode:
    def _roundtrip_hash(self, w: int, h: int, rgba: bytes) -> bytes:
        return thumbhash.encode(w, h, rgba)

    def test_returns_tuple(self):
        h = self._roundtrip_hash(8, 8, _solid_rgba(8, 8, 200, 50, 50))
        result = thumbhash.decode(h)
        assert isinstance(result, tuple) and len(result) == 3
        w_out, h_out, data = result
        assert isinstance(w_out, int)
        assert isinstance(h_out, int)
        assert isinstance(data, bytes)

    def test_output_dimensions(self):
        h = self._roundtrip_hash(8, 8, _solid_rgba(8, 8, 100, 100, 100))
        w_out, h_out, data = thumbhash.decode(h)
        assert data == bytes(w_out * h_out * 4)[:0] or len(data) == w_out * h_out * 4

    def test_landscape_output_wider(self):
        h = self._roundtrip_hash(80, 40, _solid_rgba(80, 40, 255, 0, 0))
        w_out, h_out, _ = thumbhash.decode(h)
        assert w_out > h_out

    def test_portrait_output_taller(self):
        h = self._roundtrip_hash(40, 80, _solid_rgba(40, 80, 0, 0, 255))
        w_out, h_out, _ = thumbhash.decode(h)
        assert h_out > w_out

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            thumbhash.decode(b"\x00\x01")

    def test_accepts_bytearray(self):
        h = bytearray(self._roundtrip_hash(8, 8, _solid_rgba(8, 8, 0, 200, 0)))
        w, h_px, data = thumbhash.decode(h)
        assert len(data) == w * h_px * 4


class TestAverageRgba:
    def test_opaque_image(self):
        rgba = _solid_rgba(10, 10, 255, 0, 0)  # solid red
        h = thumbhash.encode(10, 10, rgba)
        r, g, b, a = thumbhash.average_rgba(h)
        assert a == pytest.approx(1.0, abs=0.1)
        assert r > g and r > b  # red dominant

    def test_fully_transparent_image(self):
        rgba = _solid_rgba(10, 10, 0, 0, 0, 0)
        h = thumbhash.encode(10, 10, rgba)
        _, _, _, a = thumbhash.average_rgba(h)
        assert a < 0.1

    def test_values_in_range(self):
        rgba = _solid_rgba(8, 8, 128, 64, 200)
        h = thumbhash.encode(8, 8, rgba)
        for v in thumbhash.average_rgba(h):
            assert 0.0 <= v <= 1.0


class TestApproximateAspectRatio:
    def test_square(self):
        rgba = _solid_rgba(50, 50, 128, 128, 128)
        h = thumbhash.encode(50, 50, rgba)
        ratio = thumbhash.approximate_aspect_ratio(h)
        assert ratio == pytest.approx(1.0, abs=0.1)

    def test_wide(self):
        rgba = _solid_rgba(100, 25, 0, 0, 0)
        h = thumbhash.encode(100, 25, rgba)
        assert thumbhash.approximate_aspect_ratio(h) > 1.5

    def test_tall(self):
        rgba = _solid_rgba(25, 100, 0, 0, 0)
        h = thumbhash.encode(25, 100, rgba)
        assert thumbhash.approximate_aspect_ratio(h) < 0.7


# ── Pillow integration ────────────────────────────────────────────────────────


class TestPillowIntegration:
    pytest.importorskip("PIL", reason="Pillow not installed")

    def test_encode_decode_image(self):
        from PIL import Image

        img = Image.new("RGB", (80, 60), color=(255, 128, 0))
        h = thumbhash.encode_image(img)
        assert isinstance(h, bytes) and len(h) >= 5

        placeholder = thumbhash.decode_image(h)
        assert placeholder.mode == "RGBA"
        assert placeholder.size[0] > 0 and placeholder.size[1] > 0

    def test_large_image_is_resized(self):
        from PIL import Image

        img = Image.new("RGBA", (800, 600), color=(100, 200, 50, 255))
        # Should not raise even though it's > 100 px
        h = thumbhash.encode_image(img)
        assert len(h) >= 5

    def test_rgba_image(self):
        from PIL import Image

        img = Image.new("RGBA", (40, 40), color=(0, 0, 255, 180))
        h = thumbhash.encode_image(img)
        placeholder = thumbhash.decode_image(h)
        assert placeholder.mode == "RGBA"

    def test_grayscale_image(self):
        from PIL import Image

        img = Image.new("L", (50, 50), color=128)
        h = thumbhash.encode_image(img)
        assert len(h) >= 5


# ── Real image file tests (with Pillow) ──────────────────────────────────────


class TestWithImageFiles:
    """Tests using real JPEG images from the tests/ directory."""

    @pytest.fixture(params=["one.jpg", "two.jpg", "four.jpg", "OPS.jpg"])
    def image_path(self, request):
        pytest.importorskip("PIL")
        path = Path(__file__).parent / request.param
        assert path.exists(), f"Test image not found: {path}"
        return path

    def test_encode_image_from_file(self, image_path):
        from PIL import Image

        img = Image.open(image_path)
        h = thumbhash.encode_image(img)
        assert isinstance(h, bytes)
        assert len(h) >= 5

    def test_decode_roundtrip_from_file(self, image_path):
        from PIL import Image

        img = Image.open(image_path)
        h = thumbhash.encode_image(img)
        placeholder = thumbhash.decode_image(h)
        assert placeholder.mode == "RGBA"
        assert placeholder.size[0] > 0
        assert placeholder.size[1] > 0

    def test_average_rgba_from_file(self, image_path):
        from PIL import Image

        img = Image.open(image_path)
        h = thumbhash.encode_image(img)
        r, g, b, a = thumbhash.average_rgba(h)
        for v in (r, g, b, a):
            assert 0.0 <= v <= 1.0

    def test_aspect_ratio_from_file(self, image_path):
        from PIL import Image

        img = Image.open(image_path)
        w, h_px = img.size
        h = thumbhash.encode_image(img)
        ratio = thumbhash.approximate_aspect_ratio(h)
        assert ratio > 0
        # The approximate ratio should be in the right ballpark
        expected_ratio = w / h_px
        assert abs(ratio - expected_ratio) < 0.5


# ── Raw bytes from real images (no Pillow required at test time) ─────────────


class TestImageFilesRawBytes:
    """Test raw encode/decode with pixel data extracted from real images."""

    @pytest.fixture(params=["one.jpg", "two.jpg", "four.jpg", "OPS.jpg"])
    def image_rgba(self, request):
        """Pre-extracted RGBA data from the test images."""
        pytest.importorskip("PIL")
        from PIL import Image

        path = Path(__file__).parent / request.param
        img = Image.open(path).convert("RGBA")
        w, h = img.size
        # Shrink to fit the 100px limit
        max_side = 100
        if w > max_side or h > max_side:
            scale = max_side / max(w, h)
            w = max(1, round(w * scale))
            h = max(1, round(h * scale))
            img = img.resize((w, h), Image.LANCZOS)
        return w, h, img.tobytes()

    def test_encode_raw_from_file(self, image_rgba):
        w, h, rgba = image_rgba
        result = thumbhash.encode(w, h, rgba)
        assert isinstance(result, bytes)
        assert len(result) >= 5

    def test_decode_raw_from_file(self, image_rgba):
        w, h, rgba = image_rgba
        h_hash = thumbhash.encode(w, h, rgba)
        w_out, h_out, rgba_out = thumbhash.decode(h_hash)
        assert len(rgba_out) == w_out * h_out * 4

    def test_aspect_ratio_raw(self, image_rgba):
        w, h, rgba = image_rgba
        h_hash = thumbhash.encode(w, h, rgba)
        ratio = thumbhash.approximate_aspect_ratio(h_hash)
        assert ratio > 0


# ── BytesIO tests ────────────────────────────────────────────────────────────


class TestBytesIO:
    """Test encode/decode with BytesIO-based workflows."""

    def test_encode_from_bytesio_rgba(self):
        """Simulate getting RGBA bytes from a BytesIO source (no Pillow needed)."""
        w, h = 10, 10
        rgba = bytes([128, 64, 200, 255] * (w * h))
        buf = io.BytesIO(rgba)
        data = buf.read()
        result = thumbhash.encode(w, h, data)
        assert isinstance(result, bytes)
        assert len(result) >= 5

    def test_encode_bytesio_then_decode(self):
        """Full round-trip using BytesIO as an intermediary."""
        w, h = 8, 8
        rgba = bytes([255, 0, 0, 255] * (w * h))
        buf = io.BytesIO(rgba)
        hash_bytes = thumbhash.encode(w, h, buf.read())
        w_out, h_out, rgba_out = thumbhash.decode(hash_bytes)
        assert len(rgba_out) == w_out * h_out * 4

    def test_bytesio_from_pil_image(self):
        """Encode an image that was serialized through BytesIO (Pillow present)."""
        pytest.importorskip("PIL")
        from PIL import Image

        # Create image, save to BytesIO as PNG, reload, encode
        img = Image.new("RGBA", (40, 30), color=(100, 200, 50, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        reloaded = Image.open(buf)
        h = thumbhash.encode_image(reloaded)
        assert isinstance(h, bytes)

    def test_bytesio_raw_tobytes(self):
        """Use Image.tobytes() fed through BytesIO to encode."""
        pytest.importorskip("PIL")
        from PIL import Image

        img = Image.new("RGB", (20, 20), color=(255, 128, 0))
        img = img.convert("RGBA")
        raw = img.tobytes()
        # Simulate receiving raw bytes over a stream
        buf = io.BytesIO(raw)
        w, h = img.size
        h_hash = thumbhash.encode(w, h, buf.read())
        w_out, h_out, _ = thumbhash.decode(h_hash)
        assert w_out > 0 and h_out > 0

    def test_bytesio_partial_read(self):
        """Read only part of a BytesIO to simulate streaming."""
        w, h = 8, 8
        total = w * h * 4
        rgba = bytes([200, 100, 50, 255] * (w * h))
        buf = io.BytesIO(rgba)
        data = buf.read(total)
        h_hash = thumbhash.encode(w, h, data)
        assert len(h_hash) >= 5


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_minimum_size_1x1(self):
        rgba = bytes([255, 0, 0, 255])
        h = thumbhash.encode(1, 1, rgba)
        assert len(h) >= 5

    def test_1x1_roundtrip(self):
        rgba = bytes([100, 150, 200, 255])
        h = thumbhash.encode(1, 1, rgba)
        w, h_out, data = thumbhash.decode(h)
        # Decode always scales longest side to ~32 px
        assert len(data) == w * h_out * 4
        assert w > 0 and h_out > 0

    def test_square_max_size(self):
        rgba = bytes([42] * 4 * 100 * 100)
        h = thumbhash.encode(100, 100, rgba)
        assert len(h) >= 5

    def test_transparent_image(self):
        rgba = bytes([0, 0, 0, 0] * 10 * 10)
        h = thumbhash.encode(10, 10, rgba)
        _, _, _, a = thumbhash.average_rgba(h)
        assert a < 0.1

    def test_solid_white(self):
        rgba = bytes([255, 255, 255, 255] * 10 * 10)
        h = thumbhash.encode(10, 10, rgba)
        r, g, b, a = thumbhash.average_rgba(h)
        assert a > 0.9
        assert r > 0.9 and g > 0.9 and b > 0.9

    def test_solid_black(self):
        rgba = bytes([0, 0, 0, 255] * 10 * 10)
        h = thumbhash.encode(10, 10, rgba)
        r, g, b, a = thumbhash.average_rgba(h)
        assert a > 0.9
        assert r < 0.1 and g < 0.1 and b < 0.1

    def test_empty_bytes_raises(self):
        with pytest.raises(ValueError):
            thumbhash.encode(8, 8, b"")

    def test_zero_width_raises(self):
        with pytest.raises(ValueError):
            thumbhash.encode(0, 10, b"\x00" * 40)

    def test_zero_height_raises(self):
        with pytest.raises(ValueError):
            thumbhash.encode(10, 0, b"\x00" * 40)

    def test_hash_accepts_memoryview(self):
        rgba = bytes([128, 64, 200, 255] * 8 * 8)
        h = thumbhash.encode(8, 8, rgba)
        mv = memoryview(h)
        w, h_px, data = thumbhash.decode(mv)
        assert len(data) == w * h_px * 4

    def test_encode_accepts_memoryview(self):
        rgba = bytes([128, 64, 200, 255] * 8 * 8)
        mv = memoryview(rgba)
        h = thumbhash.encode(8, 8, mv)
        assert isinstance(h, bytes)

    def test_bytearray_hash_decode(self):
        rgba = bytes([255, 128, 0, 255] * 10 * 10)
        h = thumbhash.encode(10, 10, rgba)
        w, h_px, data = thumbhash.decode(bytearray(h))
        assert len(data) == w * h_px * 4
