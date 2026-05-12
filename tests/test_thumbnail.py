"""Tests for the thumbleweed.thumbnail module.

Exercises every fixture in ``tests/`` (jpgs, mp4s, pdfs) through both the
``crude`` and ``auto`` engines, plus all input shapes (bytes, BytesIO,
file path, pathlib.Path, Pillow.Image).
"""

from __future__ import annotations

import io
import pathlib

import pytest
import thumbleweed
from thumbleweed import thumbnail

FIXTURES = pathlib.Path(__file__).parent

JPEG_FIXTURES = sorted(FIXTURES.glob("*.jpg"))
MP4_FIXTURES = sorted(FIXTURES.glob("*.mp4"))
PDF_FIXTURES = sorted(FIXTURES.glob("*.pdf"))

# Sanity-check the test data layout: this also documents which fixtures the
# suite is expected to exercise.
assert JPEG_FIXTURES, "expected at least one .jpg fixture"
assert MP4_FIXTURES, "expected at least one .mp4 fixture"
assert PDF_FIXTURES, "expected at least one .pdf fixture"

JPEG_SOI = b"\xff\xd8\xff"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
WEBP_RIFF = b"RIFF"


# ── Module surface ───────────────────────────────────────────────────────────


class TestModuleSurface:
    def test_thumbnail_attached_to_top_level(self):
        assert thumbleweed.thumbnail is thumbnail
        assert callable(thumbleweed.thumbnail_create)
        assert callable(thumbleweed.thumbnail_save)
        assert callable(thumbleweed.thumbnail_detect_kind)
        assert callable(thumbleweed.thumbnail_available_backends)

    def test_available_backends_contains_crude(self):
        backends = thumbnail.available_backends()
        assert "crude" in backends
        # The auto-thumbnail backend may or may not be compiled in; both are OK.
        for b in backends:
            assert b in {"crude", "auto-thumbnail"}

    def test_engine_and_format_constants(self):
        assert "crude" in thumbnail.Engine
        assert "auto" in thumbnail.Engine
        assert "jpeg" in thumbnail.OutputFormat
        assert "png" in thumbnail.OutputFormat


# ── Magic byte detection ─────────────────────────────────────────────────────


class TestDetectKind:
    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_fixtures(self, path: pathlib.Path):
        assert thumbnail.detect_kind(path) == "image"
        assert thumbnail.detect_kind(path.read_bytes()) == "image"

    @pytest.mark.parametrize("path", MP4_FIXTURES, ids=lambda p: p.name)
    def test_mp4_fixtures(self, path: pathlib.Path):
        assert thumbnail.detect_kind(path) == "video"

    @pytest.mark.parametrize("path", PDF_FIXTURES, ids=lambda p: p.name)
    def test_pdf_fixtures(self, path: pathlib.Path):
        assert thumbnail.detect_kind(path) == "pdf"

    def test_unknown(self):
        assert thumbnail.detect_kind(b"definitely not a known format") == "unknown"


# ── Crude engine: images ─────────────────────────────────────────────────────


class TestCrudeImage:
    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_path_to_jpeg(self, path: pathlib.Path):
        out = thumbnail.create(path, width=128, height=128, engine="crude")
        assert out.startswith(JPEG_SOI)
        assert len(out) > 100

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_path_to_png(self, path: pathlib.Path):
        out = thumbnail.create(path, width=64, height=64, format="png", engine="crude")
        assert out.startswith(PNG_SIG)

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_path_to_webp(self, path: pathlib.Path):
        out = thumbnail.create(path, width=64, height=64, format="webp", engine="crude")
        assert out[:4] == WEBP_RIFF
        assert out[8:12] == b"WEBP"

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_bytes_input(self, path: pathlib.Path):
        out = thumbnail.create(path.read_bytes(), engine="crude")
        assert out.startswith(JPEG_SOI)

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_bytesio_input(self, path: pathlib.Path):
        buf = io.BytesIO(path.read_bytes())
        out = thumbnail.create(buf, engine="crude")
        assert out.startswith(JPEG_SOI)
        # BytesIO position should be preserved.
        assert buf.tell() == 0

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_jpeg_pathlib_input(self, path: pathlib.Path):
        # already a pathlib.Path; ensure the str fast-path works too.
        out_str = thumbnail.create(str(path), engine="crude")
        out_path = thumbnail.create(path, engine="crude")
        assert out_str.startswith(JPEG_SOI)
        assert out_path.startswith(JPEG_SOI)

    def test_jpeg_pillow_input(self):
        pytest.importorskip("PIL")
        from PIL import Image

        with Image.open(JPEG_FIXTURES[0]) as im:
            im.load()
            out = thumbnail.create(im, width=64, height=64, engine="crude")
        assert out.startswith(JPEG_SOI)

    def test_resize_cap(self):
        out = thumbnail.create(JPEG_FIXTURES[0], width=32, height=32, engine="crude")
        # decode and check the dimensions
        from PIL import Image

        with Image.open(io.BytesIO(out)) as im:
            assert max(im.size) <= 32


# ── Crude engine: video (MP4) ────────────────────────────────────────────────


class TestCrudeVideo:
    @pytest.mark.parametrize("path", MP4_FIXTURES, ids=lambda p: p.name)
    def test_mp4_produces_thumbnail(self, path: pathlib.Path):
        # Even without ffmpeg, the crude path must always return *something*
        # — either an extracted cover atom or a deterministic placeholder.
        out = thumbnail.create(path, width=64, height=64, engine="crude")
        assert out.startswith(JPEG_SOI)
        assert len(out) > 50

    @pytest.mark.parametrize("path", MP4_FIXTURES, ids=lambda p: p.name)
    def test_mp4_placeholder_is_deterministic(self, path: pathlib.Path):
        a = thumbnail.create(path, width=64, height=64, engine="crude")
        b = thumbnail.create(path, width=64, height=64, engine="crude")
        assert a == b

    @pytest.mark.parametrize("path", MP4_FIXTURES, ids=lambda p: p.name)
    def test_mp4_bytes_and_path_match(self, path: pathlib.Path):
        from_path = thumbnail.create(path, width=48, height=48, engine="crude")
        from_bytes = thumbnail.create(
            path.read_bytes(), width=48, height=48, engine="crude"
        )
        assert from_path == from_bytes

    @pytest.mark.parametrize("path", MP4_FIXTURES, ids=lambda p: p.name)
    def test_mp4_png_output(self, path: pathlib.Path):
        out = thumbnail.create(path, width=32, height=32, format="png", engine="crude")
        assert out.startswith(PNG_SIG)


# ── Crude engine: PDF ────────────────────────────────────────────────────────


class TestCrudePdf:
    @pytest.mark.parametrize("path", PDF_FIXTURES, ids=lambda p: p.name)
    def test_pdf_produces_thumbnail(self, path: pathlib.Path):
        out = thumbnail.create(path, width=128, height=128, engine="crude")
        assert out.startswith(JPEG_SOI)
        assert len(out) > 50

    @pytest.mark.parametrize("path", PDF_FIXTURES, ids=lambda p: p.name)
    def test_pdf_deterministic(self, path: pathlib.Path):
        a = thumbnail.create(path, width=128, height=128, engine="crude")
        b = thumbnail.create(path, width=128, height=128, engine="crude")
        assert a == b

    @pytest.mark.parametrize("path", PDF_FIXTURES, ids=lambda p: p.name)
    def test_pdf_png_output(self, path: pathlib.Path):
        out = thumbnail.create(path, width=64, height=64, format="png", engine="crude")
        assert out.startswith(PNG_SIG)


# ── Auto engine (falls back to crude when no auto-thumbnail) ─────────────────


class TestAutoEngine:
    @pytest.mark.parametrize(
        "path",
        JPEG_FIXTURES + MP4_FIXTURES + PDF_FIXTURES,
        ids=lambda p: p.name,
    )
    def test_auto_always_works(self, path: pathlib.Path):
        out = thumbnail.create(path, width=64, height=64, engine="auto")
        # must produce a valid encoded image of the requested format.
        assert out.startswith(JPEG_SOI)
        assert len(out) > 50

    def test_auto_thumbnail_engine_explicit(self):
        backends = thumbnail.available_backends()
        if "auto-thumbnail" in backends:
            out = thumbnail.create(
                JPEG_FIXTURES[0], width=64, height=64, engine="auto-thumbnail"
            )
            assert out.startswith(JPEG_SOI)
        else:
            with pytest.raises(ValueError, match="auto-thumbnail"):
                thumbnail.create(
                    JPEG_FIXTURES[0],
                    width=64,
                    height=64,
                    engine="auto-thumbnail",
                )


# ── save() ───────────────────────────────────────────────────────────────────


class TestSave:
    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_save_jpeg(self, path: pathlib.Path, tmp_path: pathlib.Path):
        out = tmp_path / "thumb.jpg"
        thumbnail.save(path, out, width=64, height=64, engine="crude")
        assert out.exists()
        assert out.read_bytes().startswith(JPEG_SOI)

    @pytest.mark.parametrize("path", JPEG_FIXTURES, ids=lambda p: p.name)
    def test_save_png_inferred_from_extension(
        self, path: pathlib.Path, tmp_path: pathlib.Path
    ):
        out = tmp_path / "thumb.png"
        thumbnail.save(path, out, width=64, height=64, engine="crude")
        assert out.read_bytes().startswith(PNG_SIG)

    @pytest.mark.parametrize("path", PDF_FIXTURES, ids=lambda p: p.name)
    def test_save_pdf_thumbnail(self, path: pathlib.Path, tmp_path: pathlib.Path):
        out = tmp_path / f"{path.stem}_thumb.png"
        thumbnail.save(path, out, width=128, height=128, engine="crude")
        assert out.read_bytes().startswith(PNG_SIG)

    @pytest.mark.parametrize("path", MP4_FIXTURES, ids=lambda p: p.name)
    def test_save_mp4_thumbnail(self, path: pathlib.Path, tmp_path: pathlib.Path):
        out = tmp_path / f"{path.stem}_thumb.jpg"
        thumbnail.save(path, out, width=128, height=128, engine="crude")
        assert out.read_bytes().startswith(JPEG_SOI)

    def test_save_from_bytesio(self, tmp_path: pathlib.Path):
        out = tmp_path / "from_bytesio.jpg"
        buf = io.BytesIO(JPEG_FIXTURES[0].read_bytes())
        thumbnail.save(buf, out, width=64, height=64, engine="crude")
        assert out.read_bytes().startswith(JPEG_SOI)


# ── Error handling ───────────────────────────────────────────────────────────


class TestErrors:
    def test_unknown_format(self):
        with pytest.raises(ValueError):
            thumbnail.create(JPEG_FIXTURES[0], format="tiff", engine="crude")

    def test_unknown_engine(self):
        with pytest.raises(ValueError):
            thumbnail.create(JPEG_FIXTURES[0], engine="bogus")

    def test_unknown_format_bytes_input(self):
        with pytest.raises(ValueError, match="unsupported|unknown"):
            thumbnail.create(b"not a real file", engine="crude")

    def test_unsupported_input_type(self):
        with pytest.raises(TypeError):
            thumbnail.create(12345, engine="crude")  # type: ignore[arg-type]

    def test_nonexistent_path(self, tmp_path: pathlib.Path):
        missing = tmp_path / "does_not_exist.jpg"
        with pytest.raises((ValueError, FileNotFoundError, OSError)):
            thumbnail.create(missing, engine="crude")


# ── Smoke matrix: every fixture × every engine × every format ────────────────


@pytest.mark.parametrize("fmt", ["jpeg", "png", "webp"])
@pytest.mark.parametrize("engine", ["crude", "auto"])
@pytest.mark.parametrize(
    "path",
    JPEG_FIXTURES + MP4_FIXTURES + PDF_FIXTURES,
    ids=lambda p: p.name,
)
def test_full_matrix(path: pathlib.Path, engine: str, fmt: str):
    out = thumbnail.create(path, width=48, height=48, format=fmt, engine=engine)
    assert isinstance(out, bytes)
    assert len(out) > 20
    if fmt == "jpeg":
        assert out.startswith(JPEG_SOI)
    elif fmt == "png":
        assert out.startswith(PNG_SIG)
    elif fmt == "webp":
        assert out[:4] == WEBP_RIFF and out[8:12] == b"WEBP"
