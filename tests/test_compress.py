"""Tests for the thumbleweed.compress module (pixo backend).

These tests exercise the public Python surface (``thumbleweed.compress``) and
the auto-compress wiring inside ``thumbleweed.thumbnail``.

When the wheel is built without the ``pixo`` cargo feature, every routine
here must still run without raising — they degrade to a transparent
pass-through.
"""

from __future__ import annotations

import io
import pathlib

import pytest
import thumbleweed
from thumbleweed import compress, thumbnail

FIXTURES = pathlib.Path(__file__).parent
JPEG_FIXTURES = sorted(FIXTURES.glob("*.jpg"))
PDF_FIXTURES = sorted(FIXTURES.glob("*.pdf"))
MP4_FIXTURES = sorted(FIXTURES.glob("*.mp4"))

assert JPEG_FIXTURES, "expected .jpg fixtures"

JPEG_SOI = b"\xff\xd8\xff"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
WEBP_RIFF = b"RIFF"


# ── Module surface ───────────────────────────────────────────────────────────


class TestModuleSurface:
    def test_top_level_exposes_compress(self):
        assert thumbleweed.compress is compress
        assert callable(thumbleweed.compress_image)
        assert callable(thumbleweed.compress_is_available)
        assert callable(thumbleweed.compress_detect_format)

    def test_is_available_returns_bool(self):
        assert isinstance(compress.is_available(), bool)

    def test_format_constant(self):
        assert "auto" in compress.Format
        assert "jpeg" in compress.Format
        assert "png" in compress.Format


# ── Format detection ─────────────────────────────────────────────────────────


class TestDetectFormat:
    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_fixture(self, path: pathlib.Path):
        assert compress.detect_format(path) == "jpeg"
        assert compress.detect_format(path.read_bytes()) == "jpeg"

    def test_png(self):
        # Build a tiny PNG via thumbnail.
        png = thumbnail.create(
            JPEG_FIXTURES[0], width=32, height=32, format="png", engine="crude"
        )
        assert compress.detect_format(png) == "png"

    def test_webp(self):
        webp = thumbnail.create(
            JPEG_FIXTURES[0], width=32, height=32, format="webp", engine="crude"
        )
        assert compress.detect_format(webp) == "webp"

    def test_unknown(self):
        assert compress.detect_format(b"not an image") == "unknown"


# ── compress() — direct ──────────────────────────────────────────────────────


class TestCompressDirect:
    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_passthrough_or_smaller(self, path: pathlib.Path):
        original = path.read_bytes()
        out = compress.compress(original, format="auto", quality=85)
        # Must always be a valid JPEG and never larger than the input.
        assert out.startswith(JPEG_SOI)
        assert len(out) <= len(original)

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_explicit_format(self, path: pathlib.Path):
        out = compress.compress(path.read_bytes(), format="jpeg", quality=80)
        assert out.startswith(JPEG_SOI)

    def test_png_compress_no_larger(self):
        # Pre-build an uncompressed-ish PNG via thumbnail w/o pixo so we have
        # something pixo can plausibly shrink.
        png = thumbnail.create(
            JPEG_FIXTURES[0],
            width=128,
            height=128,
            format="png",
            engine="crude",
            compress=False,
        )
        out = compress.compress(png, format="auto")
        assert out.startswith(PNG_SIG)
        assert len(out) <= len(png)

    def test_webp_passthrough(self):
        webp = thumbnail.create(
            JPEG_FIXTURES[0],
            width=64,
            height=64,
            format="webp",
            engine="crude",
            compress=False,
        )
        # pixo doesn't handle WebP; bytes must be returned unchanged.
        out = compress.compress(webp, format="auto")
        assert out == webp

    def test_unknown_passthrough(self):
        garbage = b"definitely not an image"
        assert compress.compress(garbage, format="auto") == garbage

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            compress.compress(JPEG_FIXTURES[0].read_bytes(), format="tiff")

    def test_unsupported_input_type(self):
        with pytest.raises(TypeError):
            compress.compress(12345)  # type: ignore[arg-type]

    def test_bytesio_input(self):
        buf = io.BytesIO(JPEG_FIXTURES[0].read_bytes())
        out = compress.compress(buf)
        assert out.startswith(JPEG_SOI)
        # Position must be preserved by _to_bytes.
        assert buf.tell() == 0

    def test_path_input(self):
        out = compress.compress(JPEG_FIXTURES[0])
        assert out.startswith(JPEG_SOI)

    def test_pillow_input(self):
        pytest.importorskip("PIL")
        from PIL import Image

        with Image.open(JPEG_FIXTURES[0]) as im:
            im.load()
            out = compress.compress(im)
        # PIL gets serialised through PNG before pixo sees it.
        assert out.startswith(PNG_SIG) or out.startswith(JPEG_SOI)


# ── compress_path() ──────────────────────────────────────────────────────────


class TestCompressPath:
    def test_inplace(self, tmp_path: pathlib.Path):
        src = tmp_path / "photo.jpg"
        src.write_bytes(JPEG_FIXTURES[0].read_bytes())
        original_len = src.stat().st_size
        saved = compress.compress_path(src)
        assert saved >= 0
        assert src.stat().st_size <= original_len

    def test_to_separate_output(self, tmp_path: pathlib.Path):
        out = tmp_path / "out.jpg"
        compress.compress_path(JPEG_FIXTURES[0], out)
        assert out.exists()
        assert out.read_bytes().startswith(JPEG_SOI)


# ── Auto-compression integration with thumbnail.create ───────────────────────


class TestThumbnailAutoCompress:
    """When pixo is available, compress=True (the default) should never
    produce larger bytes than compress=False, and never break correctness.
    """

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_compressed_vs_uncompressed(self, path: pathlib.Path):
        raw = thumbnail.create(
            path, width=128, height=128, format="jpeg", compress=False
        )
        cooked = thumbnail.create(
            path, width=128, height=128, format="jpeg", compress=True
        )
        assert raw.startswith(JPEG_SOI)
        assert cooked.startswith(JPEG_SOI)
        # Compressed must be no larger than uncompressed (regardless of
        # whether the pixo feature is on).
        assert len(cooked) <= len(raw)

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_png_compressed_vs_uncompressed(self, path: pathlib.Path):
        raw = thumbnail.create(
            path, width=128, height=128, format="png", compress=False
        )
        cooked = thumbnail.create(
            path, width=128, height=128, format="png", compress=True
        )
        assert raw.startswith(PNG_SIG)
        assert cooked.startswith(PNG_SIG)
        assert len(cooked) <= len(raw)

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_webp_unchanged_by_compress_flag(self, path: pathlib.Path):
        # pixo can't re-encode WebP; the flag must be a no-op for that format.
        a = thumbnail.create(path, width=64, height=64, format="webp", compress=False)
        b = thumbnail.create(path, width=64, height=64, format="webp", compress=True)
        assert a == b
        assert a[:4] == WEBP_RIFF

    @pytest.mark.skipif(
        not compress.is_available(),
        reason="requires the `pixo` cargo feature",
    )
    def test_pixo_shrinks_at_least_some_jpegs(self):
        # Pixo can't always beat already-optimised JPEGs (e.g. OPS.jpg ships
        # with mozjpeg-class quantization tables). The contract is therefore
        # “should shrink at least one of the fixtures” — sufficient evidence
        # that pixo is wired in and re-encoding, while tolerating the
        # genuinely-incompressible cases.
        wins = 0
        for path in JPEG_FIXTURES:
            raw = thumbnail.create(
                path, width=256, height=256, format="jpeg", compress=False
            )
            cooked = thumbnail.create(
                path, width=256, height=256, format="jpeg", compress=True
            )
            assert len(cooked) <= len(raw)
            if len(cooked) < len(raw):
                wins += 1
        assert wins >= 1, (
            "pixo did not shrink any JPEG fixture — the integration looks broken"
        )

    @pytest.mark.skipif(
        not compress.is_available(),
        reason="requires the `pixo` cargo feature",
    )
    def test_pixo_shrinks_at_least_some_pngs(self):
        wins = 0
        for path in JPEG_FIXTURES:
            raw = thumbnail.create(
                path, width=256, height=256, format="png", compress=False
            )
            cooked = thumbnail.create(
                path, width=256, height=256, format="png", compress=True
            )
            assert len(cooked) <= len(raw)
            if len(cooked) < len(raw):
                wins += 1
        assert wins >= 1, (
            "pixo did not shrink any PNG fixture — the integration looks broken"
        )

    @pytest.mark.parametrize("path", PDF_FIXTURES, ids=lambda p: p.name)
    def test_pdf_thumbnail_with_compress(self, path: pathlib.Path):
        # PDFs go through the crude extractor + pixo (when enabled). Must
        # always produce a valid JPEG no larger than the uncompressed version.
        raw = thumbnail.create(path, width=128, height=128, compress=False)
        cooked = thumbnail.create(path, width=128, height=128, compress=True)
        assert raw.startswith(JPEG_SOI)
        assert cooked.startswith(JPEG_SOI)
        assert len(cooked) <= len(raw)

    @pytest.mark.parametrize("path", MP4_FIXTURES, ids=lambda p: p.name)
    def test_mp4_thumbnail_with_compress(self, path: pathlib.Path):
        raw = thumbnail.create(path, width=128, height=128, compress=False)
        cooked = thumbnail.create(path, width=128, height=128, compress=True)
        assert raw.startswith(JPEG_SOI)
        assert cooked.startswith(JPEG_SOI)
        assert len(cooked) <= len(raw)


# ── Smoke matrix ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("fmt", ["jpeg", "png"])
@pytest.mark.parametrize(
    "path",
    JPEG_FIXTURES + MP4_FIXTURES + PDF_FIXTURES,
    ids=lambda p: p.name,
)
def test_compress_does_not_break_anything(path: pathlib.Path, fmt: str):
    out = thumbnail.create(
        path, width=64, height=64, format=fmt, engine="auto", compress=True
    )
    if fmt == "jpeg":
        assert out.startswith(JPEG_SOI)
    else:
        assert out.startswith(PNG_SIG)
    assert len(out) > 20
