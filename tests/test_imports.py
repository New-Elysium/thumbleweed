"""Tests for import paths across all thumbleweed sub-packages."""

from __future__ import annotations

import blurhash
import colorthief
import pytest
import thumbhash
import thumbleweed

# ── Helpers ──────────────────────────────────────────────────────────────────


def _solid_rgba(w: int, h: int, r: int, g: int, b: int, a: int = 255) -> bytes:
    """Return a flat RGBA buffer filled with one colour (for thumbhash)."""
    return bytes([r, g, b, a] * (w * h))


def _solid_rgba_blur(w: int, h: int, r: int, g: int, b: int, a: int = 255) -> bytes:
    """Return a flat RGBA buffer filled with one colour (for blurhash)."""
    return bytes([r, g, b, a] * (w * h))


# ── TestThumbleweedImports ───────────────────────────────────────────────────


class TestThumbleweedImports:
    """Verify the top-level thumbleweed package exposes the right API."""

    THUMBHASH_ATTRS = [
        "thumbhash_encode",
        "thumbhash_decode",
        "thumbhash_average_rgba",
        "thumbhash_approximate_aspect_ratio",
    ]
    BLURHASH_ATTRS = [
        "blurhash_encode",
        "blurhash_decode",
    ]
    COLORTHIEF_ATTRS = [
        "colorthief_get_color",
        "colorthief_get_color_bytes",
        "colorthief_get_palette",
        "colorthief_get_palette_bytes",
    ]
    THUMBHASH_IMAGE_ATTRS = [
        "thumbhash_encode_image",
        "thumbhash_decode_image",
    ]
    BLURHASH_IMAGE_ATTRS = [
        "blurhash_encode_image",
        "blurhash_decode_image",
    ]

    def test_import_thumbleweed(self):
        import thumbleweed as tw

        for attr in (
            self.THUMBHASH_ATTRS
            + self.THUMBHASH_IMAGE_ATTRS
            + self.BLURHASH_ATTRS
            + self.BLURHASH_IMAGE_ATTRS
            + self.COLORTHIEF_ATTRS
            + ["__version__"]
        ):
            assert hasattr(tw, attr), f"thumbleweed is missing attribute: {attr}"

    def test_version(self):
        assert isinstance(thumbleweed.__version__, str)
        assert len(thumbleweed.__version__) > 0

    def test_thumbhash_functions(self):
        for name in self.THUMBHASH_ATTRS:
            func = getattr(thumbleweed, name)
            assert callable(func), f"thumbleweed.{name} should be callable"

    def test_blurhash_functions(self):
        for name in self.BLURHASH_ATTRS:
            func = getattr(thumbleweed, name)
            assert callable(func), f"thumbleweed.{name} should be callable"

    def test_colorthief_functions(self):
        for name in self.COLORTHIEF_ATTRS:
            func = getattr(thumbleweed, name)
            assert callable(func), f"thumbleweed.{name} should be callable"


# ── TestThumbhashImports ─────────────────────────────────────────────────────


class TestThumbhashImports:
    """Verify the thumbhash compatibility shim works."""

    EXPECTED_ATTRS = [
        "encode",
        "decode",
        "average_rgba",
        "approximate_aspect_ratio",
        "encode_image",
        "decode_image",
        "__version__",
    ]

    def test_import_thumbhash(self):
        for attr in self.EXPECTED_ATTRS:
            assert hasattr(thumbhash, attr), f"thumbhash is missing attribute: {attr}"

    def test_version(self):
        assert isinstance(thumbhash.__version__, str)
        assert thumbhash.__version__ == thumbleweed.__version__

    def test_encode_decode(self):
        rgba = _solid_rgba(8, 8, 255, 0, 0)
        h = thumbhash.encode(8, 8, rgba)
        assert isinstance(h, bytes)
        w, h_out, rgba_out = thumbhash.decode(h)
        assert isinstance(w, int)
        assert isinstance(h_out, int)
        assert isinstance(rgba_out, bytes)
        assert len(rgba_out) == w * h_out * 4


# ── TestBlurhashImports ──────────────────────────────────────────────────────


class TestBlurhashImports:
    """Verify the blurhash compatibility shim works."""

    EXPECTED_ATTRS = [
        "encode",
        "decode",
        "encode_image",
        "decode_image",
        "__version__",
    ]

    def test_import_blurhash(self):
        for attr in self.EXPECTED_ATTRS:
            assert hasattr(blurhash, attr), f"blurhash is missing attribute: {attr}"

    def test_version(self):
        assert isinstance(blurhash.__version__, str)
        assert blurhash.__version__ == thumbleweed.__version__

    def test_encode_decode(self):
        rgba = _solid_rgba_blur(8, 8, 128, 64, 200)
        hash_str = blurhash.encode(rgba, 4, 3, 8, 8)
        assert isinstance(hash_str, str)
        decoded = blurhash.decode(hash_str, 32, 32)
        assert isinstance(decoded, bytes)
        assert len(decoded) == 32 * 32 * 4


# ── TestColorthiefImports ────────────────────────────────────────────────────


class TestColorthiefImports:
    """Verify the colorthief compatibility shim works."""

    EXPECTED_ATTRS = [
        "get_color",
        "get_palette",
        "ColorThief",
        "__version__",
    ]

    def test_import_colorthief(self):
        for attr in self.EXPECTED_ATTRS:
            assert hasattr(colorthief, attr), f"colorthief is missing attribute: {attr}"

    def test_version(self):
        assert isinstance(colorthief.__version__, str)
        assert colorthief.__version__ == thumbleweed.__version__


# ── TestVersionConsistency ───────────────────────────────────────────────────


class TestVersionConsistency:
    """All sub-packages should report the same version."""

    def test_all_versions_match(self):
        versions = {
            "thumbleweed": thumbleweed.__version__,
            "thumbhash": thumbhash.__version__,
            "blurhash": blurhash.__version__,
            "colorthief": colorthief.__version__,
        }
        unique = set(versions.values())
        assert len(unique) == 1, f"Versions are not consistent: {versions}"
