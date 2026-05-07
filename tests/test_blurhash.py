"""Tests for the blurhash Python library."""

from __future__ import annotations

import io
from pathlib import Path

import blurhash
import pytest

# ── Helpers ──────────────────────────────────────────────────────────────────

# BlurHash base-83 alphabet
_BASE83_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz#$%*+,-.:;=?@[]^_{|}~"


def _solid_rgba(w: int, h: int, r: int, g: int, b: int, a: int = 255) -> bytes:
    """Return a flat RGBA buffer filled with one colour."""
    return bytes([r, g, b, a] * (w * h))


# ── TestEncode ───────────────────────────────────────────────────────────────


class TestEncode:
    """Core encode tests."""

    def test_returns_string(self):
        rgba = _solid_rgba(8, 8, 255, 0, 0)
        result = blurhash.encode(rgba, 4, 3, 8, 8)
        assert isinstance(result, str)
        assert len(result) >= 6  # minimum BlurHash length

    def test_different_images_differ(self):
        red = blurhash.encode(_solid_rgba(8, 8, 255, 0, 0), 4, 3, 8, 8)
        blue = blurhash.encode(_solid_rgba(8, 8, 0, 0, 255), 4, 3, 8, 8)
        assert red != blue

    def test_accepts_bytearray(self):
        rgba = bytearray(_solid_rgba(10, 10, 128, 128, 128))
        result = blurhash.encode(rgba, 4, 3, 10, 10)
        assert isinstance(result, str)

    def test_solid_red(self):
        rgba = _solid_rgba(8, 8, 255, 0, 0)
        result = blurhash.encode(rgba, 4, 3, 8, 8)
        assert isinstance(result, str)
        assert len(result) >= 6

    def test_solid_blue(self):
        rgba = _solid_rgba(8, 8, 0, 0, 255)
        result = blurhash.encode(rgba, 4, 3, 8, 8)
        assert isinstance(result, str)
        assert len(result) >= 6

    def test_rejects_invalid_components_zero(self):
        rgba = _solid_rgba(8, 8, 0, 0, 0)
        with pytest.raises(ValueError):
            blurhash.encode(rgba, 0, 3, 8, 8)

    def test_rejects_invalid_components_nine(self):
        rgba = _solid_rgba(8, 8, 0, 0, 0)
        with pytest.raises(ValueError):
            blurhash.encode(rgba, 4, 10, 8, 8)

    def test_rejects_buffer_mismatch(self):
        # Buffer is 10 bytes but dimensions require 8*8*4 = 256 bytes
        with pytest.raises(ValueError):
            blurhash.encode(b"\x00" * 10, 4, 3, 8, 8)


# ── TestDecode ───────────────────────────────────────────────────────────────


class TestDecode:
    """Core decode tests."""

    def test_returns_bytes(self):
        rgba = _solid_rgba(8, 8, 200, 50, 50)
        hash_str = blurhash.encode(rgba, 4, 3, 8, 8)
        result = blurhash.decode(hash_str, 32, 32)
        assert isinstance(result, bytes)
        assert len(result) == 32 * 32 * 4

    def test_alpha_is_255(self):
        rgba = _solid_rgba(8, 8, 128, 64, 200)
        hash_str = blurhash.encode(rgba, 4, 3, 8, 8)
        result = blurhash.decode(hash_str, 16, 16)
        # All alpha values (every 4th byte starting at index 3) should be 255
        for i in range(3, len(result), 4):
            assert result[i] == 255

    def test_too_short_hash(self):
        with pytest.raises(ValueError):
            blurhash.decode("abc", 32, 32)

    def test_length_mismatch(self):
        # A hash that's at least 6 chars but encodes a wrong internal length
        # We create a hash that appears valid but has mismatched data.
        # The simplest approach: use a real hash and corrupt its length byte.
        rgba = _solid_rgba(8, 8, 128, 128, 128)
        hash_str = blurhash.encode(rgba, 4, 3, 8, 8)
        # Tamper with the size-digit character to make it inconsistent
        # The first char encodes (cx - 1) + (cy - 1) * 9
        # The second char encodes the max AC component value
        # Characters after encode the actual DC and AC components.
        # Replace first char with something that implies a different number of
        # components than the hash actually contains.
        # With 4x3 = 12 components, hash has specific length.
        # A 9x9 hash would need 81 AC components + 1 DC = 82 encoded values.
        # Setting first char to maximum (base83 value 82 = '}') makes the
        # decoder expect 9x9 components but the hash body is too short.
        tampered = "}" + hash_str[1:]
        with pytest.raises(ValueError):
            blurhash.decode(tampered, 32, 32)


# ── TestRoundTrip ────────────────────────────────────────────────────────────


class TestRoundTrip:
    """Encode/decode round-trip tests."""

    def test_encode_decode_roundtrip(self):
        rgba = _solid_rgba(20, 20, 128, 64, 200)
        hash_str = blurhash.encode(rgba, 4, 3, 20, 20)
        decoded = blurhash.decode(hash_str, 20, 20)
        assert len(decoded) == 20 * 20 * 4

    def test_roundtrip_various_sizes(self):
        for size in [(4, 4), (8, 8), (16, 16)]:
            w, h = size
            rgba = _solid_rgba(w, h, 100, 150, 200)
            hash_str = blurhash.encode(rgba, 4, 3, w, h)
            decoded = blurhash.decode(hash_str, w, h)
            assert len(decoded) == w * h * 4, f"Failed for size {size}"

    def test_roundtrip_preserves_color(self):
        # Solid red should decode with dominant red channel
        rgba = _solid_rgba(16, 16, 255, 0, 0)
        hash_str = blurhash.encode(rgba, 4, 3, 16, 16)
        decoded = blurhash.decode(hash_str, 16, 16)
        # Average the R, G, B channels
        r_sum = sum(decoded[i] for i in range(0, len(decoded), 4))
        g_sum = sum(decoded[i] for i in range(1, len(decoded), 4))
        b_sum = sum(decoded[i] for i in range(2, len(decoded), 4))
        n_pixels = 16 * 16
        r_avg = r_sum / n_pixels
        g_avg = g_sum / n_pixels
        b_avg = b_sum / n_pixels
        # Red channel should be dominant
        assert r_avg > g_avg, "Red should dominate green"
        assert r_avg > b_avg, "Red should dominate blue"


# ── TestKnownHashes ──────────────────────────────────────────────────────────


class TestKnownHashes:
    """Test with known BlurHash strings."""

    def test_decode_known_hash(self):
        # A well-known BlurHash for a sunset-like image
        known_hash = "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
        result = blurhash.decode(known_hash, 64, 64)
        assert isinstance(result, bytes)
        assert len(result) == 64 * 64 * 4
        # All pixels should be valid RGBA (alpha = 255)
        for i in range(3, len(result), 4):
            assert result[i] == 255

    def test_encode_produces_valid_hash(self):
        rgba = _solid_rgba(32, 32, 128, 64, 200)
        hash_str = blurhash.encode(rgba, 4, 3, 32, 32)
        assert isinstance(hash_str, str)
        assert len(hash_str) >= 6
        # Every character should be from the base-83 alphabet
        for ch in hash_str:
            assert ch in _BASE83_ALPHABET, f"Invalid base83 character: {ch!r}"


# ── TestEdgeCases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge-case tests."""

    def test_1x1_image(self):
        rgba = bytes([255, 0, 0, 255])
        hash_str = blurhash.encode(rgba, 4, 3, 1, 1)
        assert isinstance(hash_str, str)
        assert len(hash_str) >= 6

    def test_1x1_components(self):
        rgba = _solid_rgba(8, 8, 100, 150, 200)
        hash_str = blurhash.encode(rgba, 1, 1, 8, 8)
        assert isinstance(hash_str, str)
        # 1x1 should produce a short hash (only DC component)
        decoded = blurhash.decode(hash_str, 8, 8)
        assert len(decoded) == 8 * 8 * 4

    def test_9x9_components(self):
        rgba = _solid_rgba(8, 8, 100, 150, 200)
        hash_str = blurhash.encode(rgba, 9, 9, 8, 8)
        assert isinstance(hash_str, str)
        # 9x9 produces the longest hash (81 AC components + DC)
        decoded = blurhash.decode(hash_str, 8, 8)
        assert len(decoded) == 8 * 8 * 4

    def test_large_image(self):
        rgba = _solid_rgba(100, 100, 42, 84, 168)
        hash_str = blurhash.encode(rgba, 4, 3, 100, 100)
        assert isinstance(hash_str, str)
        decoded = blurhash.decode(hash_str, 100, 100)
        assert len(decoded) == 100 * 100 * 4


# ── Encoded image input tests ────────────────────────────────────────────────


class TestEncodedImageInputs:
    @pytest.fixture(params=["one.jpg", "two.jpg", "four.jpg", "OPS.jpg"])
    def image_path(self, request):
        path = Path(__file__).parent / request.param
        assert path.exists(), f"Test image not found: {path}"
        return path

    def test_encode_image_from_bytes_without_pillow_import(
        self, image_path, monkeypatch
    ):
        import builtins

        image_bytes = image_path.read_bytes()
        original_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("Pillow intentionally blocked")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked_import)
        hash_str = blurhash.encode_image(image_bytes, cx=4, cy=3)
        assert isinstance(hash_str, str)
        assert len(hash_str) >= 6

    def test_encode_image_accepts_file_like_without_pillow_import(
        self, image_path, monkeypatch
    ):
        import builtins

        buf = io.BytesIO(image_path.read_bytes())
        original_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("Pillow intentionally blocked")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked_import)
        hash_str = blurhash.encode_image(buf, cx=4, cy=3)
        assert isinstance(hash_str, str)
        assert len(hash_str) >= 6


# ── TestPillowIntegration ────────────────────────────────────────────────────


class TestPillowIntegration:
    """Pillow integration tests (only runs if Pillow is installed)."""

    @pytest.fixture(autouse=True)
    def _skip_no_pillow(self):
        pytest.importorskip("PIL", reason="Pillow not installed")

    def test_encode_image(self):
        from PIL import Image

        img = Image.new("RGB", (80, 60), color=(255, 128, 0))
        hash_str = blurhash.encode_image(img)
        assert isinstance(hash_str, str)
        assert len(hash_str) >= 6

    def test_decode_image(self):
        from PIL import Image

        # First encode so we have a valid hash
        img = Image.new("RGB", (64, 64), color=(0, 128, 255))
        hash_str = blurhash.encode_image(img)

        result = blurhash.decode_image(hash_str, 64, 64)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGBA"
        assert result.size == (64, 64)

    def test_encode_decode_pillow_roundtrip(self):
        from PIL import Image

        img = Image.new("RGB", (80, 60), color=(200, 100, 50))
        hash_str = blurhash.encode_image(img, cx=4, cy=3)
        placeholder = blurhash.decode_image(hash_str, 80, 60)
        assert placeholder.mode == "RGBA"
        assert placeholder.size == (80, 60)
        # Verify all pixels have alpha = 255
        raw = placeholder.tobytes()
        for i in range(3, len(raw), 4):
            assert raw[i] == 255

    def test_rgba_image(self):
        from PIL import Image

        img = Image.new("RGBA", (40, 40), color=(0, 0, 255, 180))
        hash_str = blurhash.encode_image(img)
        assert isinstance(hash_str, str)
        placeholder = blurhash.decode_image(hash_str, 40, 40)
        assert placeholder.mode == "RGBA"

    def test_grayscale_image(self):
        from PIL import Image

        img = Image.new("L", (50, 50), color=128)
        hash_str = blurhash.encode_image(img)
        assert isinstance(hash_str, str)
        assert len(hash_str) >= 6
