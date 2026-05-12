//! thumbleweed — unified image hashing library (Rust core).
//!
//! This crate provides ThumbHash, BlurHash, and (eventually) ColorThief
//! implementations, exposed to Python via PyO3.

mod blurhash;
mod colorthief;
mod compress;
mod thumbhash;
mod thumbnail;

use std::path::PathBuf;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

// ── ThumbHash Python bindings ────────────────────────────────────────────────

/// Encode raw RGBA bytes to a ThumbHash.
///
/// Parameters
/// ----------
/// w : int
///     Image width in pixels (1-100).
/// h : int
///     Image height in pixels (1-100).
/// rgba : bytes | bytearray
///     Raw pixel data, row-major, 4 bytes per pixel (R G B A).
///     RGB must **not** be premultiplied by A.
///
/// Returns
/// -------
/// bytes
///     The ThumbHash (typically 5-32 bytes).
#[pyfunction]
fn thumbhash_encode<'py>(
    py: Python<'py>,
    w: usize,
    h: usize,
    rgba: Vec<u8>,
) -> PyResult<Bound<'py, PyBytes>> {
    let hash = py.detach(|| thumbhash::rgba_to_thumb_hash(w, h, &rgba))?;
    Ok(PyBytes::new(py, &hash))
}

/// Encode raw PNG/JPEG/WebP/GIF/BMP image bytes to a ThumbHash.
///
/// This decodes the image using Rust's `image` crate, resizes the longest side
/// to at most 100 px, converts to RGBA, and returns the raw ThumbHash bytes.
#[pyfunction]
fn thumbhash_encode_image_bytes<'py>(
    py: Python<'py>,
    image: Vec<u8>,
) -> PyResult<Bound<'py, PyBytes>> {
    let hash = py.detach(|| {
        let img = image::load_from_memory(&image)
            .map_err(|e| PyValueError::new_err(format!("failed to decode image: {e}")))?;
        let rgba = img.to_rgba8();
        let (mut w, mut h) = (rgba.width(), rgba.height());
        let resized = if w > 100 || h > 100 {
            let scale = 100.0 / w.max(h) as f32;
            w = ((w as f32 * scale).round() as u32).max(1);
            h = ((h as f32 * scale).round() as u32).max(1);
            image::imageops::resize(&rgba, w, h, image::imageops::FilterType::Lanczos3)
        } else {
            rgba
        };
        thumbhash::rgba_to_thumb_hash(w as usize, h as usize, resized.as_raw()).map_err(PyErr::from)
    })?;
    Ok(PyBytes::new(py, &hash))
}

/// Decode a ThumbHash to a ~32-pixel RGBA image.
///
/// Parameters
/// ----------
/// hash : bytes | bytearray
///     The ThumbHash bytes.
///
/// Returns
/// -------
/// tuple[int, int, bytes]
///     ``(width, height, rgba_bytes)`` — raw row-major RGBA (not premultiplied).
#[pyfunction]
fn thumbhash_decode<'py>(
    py: Python<'py>,
    hash: Vec<u8>,
) -> PyResult<(usize, usize, Bound<'py, PyBytes>)> {
    let (w, h, rgba) = py.detach(|| thumbhash::thumb_hash_to_rgba(&hash))?;
    Ok((w, h, PyBytes::new(py, &rgba)))
}

/// Extract the average colour from a ThumbHash.
///
/// Returns
/// -------
/// tuple[float, float, float, float]
///     ``(r, g, b, a)`` each in ``[0.0, 1.0]``. RGB is **not** premultiplied.
#[pyfunction]
fn thumbhash_average_rgba(hash: Vec<u8>) -> PyResult<(f32, f32, f32, f32)> {
    Ok(thumbhash::thumb_hash_to_average_rgba(&hash)?)
}

/// Return the approximate aspect ratio (width / height) of the original image.
#[pyfunction]
fn thumbhash_approximate_aspect_ratio(hash: Vec<u8>) -> PyResult<f32> {
    Ok(thumbhash::thumb_hash_to_approximate_aspect_ratio(&hash)?)
}

// ── BlurHash Python bindings ─────────────────────────────────────────────────

/// Decode a BlurHash string to RGBA pixels.
///
/// Parameters
/// ----------
/// blur_hash : str
///     The BlurHash string (e.g. ``"LEHV6nWB2yk8pyo0adR*.7kCMdnj"``).
/// width : int
///     Output image width in pixels.
/// height : int
///     Output image height in pixels.
///
/// Returns
/// -------
/// bytes
///     Raw RGBA pixel data (4 bytes per pixel, alpha always 255).
#[pyfunction]
fn blurhash_decode<'py>(
    py: Python<'py>,
    blur_hash: &str,
    width: usize,
    height: usize,
) -> PyResult<Bound<'py, PyBytes>> {
    let pixels = py.detach(|| blurhash::decode(blur_hash, width, height))?;
    Ok(PyBytes::new(py, &pixels))
}

/// Encode RGBA pixels to a BlurHash string.
///
/// Parameters
/// ----------
/// pixels : bytes | bytearray
///     Raw RGBA pixel data (4 bytes per pixel, row-major).
/// cx : int
///     Number of horizontal components (1-9).
/// cy : int
///     Number of vertical components (1-9).
/// width : int
///     Image width in pixels.
/// height : int
///     Image height in pixels.
///
/// Returns
/// -------
/// str
///     The BlurHash string.
#[pyfunction]
fn blurhash_encode<'py>(
    py: Python<'py>,
    pixels: Vec<u8>,
    cx: usize,
    cy: usize,
    width: usize,
    height: usize,
) -> PyResult<String> {
    let hash = py.detach(|| blurhash::encode(&pixels, cx, cy, width, height))?;
    Ok(hash)
}

/// Encode raw PNG/JPEG/WebP/GIF/BMP image bytes to a BlurHash string.
///
/// This decodes the image using Rust's `image` crate and converts it to RGBA
/// pixels before running the BlurHash encoder.
#[pyfunction]
fn blurhash_encode_image_bytes(
    py: Python<'_>,
    image: Vec<u8>,
    cx: usize,
    cy: usize,
) -> PyResult<String> {
    py.detach(|| {
        let img = image::load_from_memory(&image)
            .map_err(|e| PyValueError::new_err(format!("failed to decode image: {e}")))?;
        let rgba = img.to_rgba8();
        let (w, h) = (rgba.width() as usize, rgba.height() as usize);
        blurhash::encode(rgba.as_raw(), cx, cy, w, h).map_err(PyErr::from)
    })
}

// ── ColorThief Python bindings ──────────────────────────────────────────────

/// Extract the dominant colour from raw image bytes.
///
/// Parameters
/// ----------
/// image : bytes | bytearray
///     Raw image data (PNG, JPEG, WebP, BMP, GIF, TIFF, etc.).
/// quality : int, optional
///     Quality/bias parameter. Default 10.
///
/// Returns
/// -------
/// tuple[int, int, int]
///     ``(r, g, b)`` in [0, 255].
#[pyfunction]
#[pyo3(signature = (image, quality=None))]
fn colorthief_get_color_bytes(
    py: Python<'_>,
    image: Vec<u8>,
    quality: Option<u8>,
) -> PyResult<(u8, u8, u8)> {
    py.detach(|| colorthief::get_dominant_from_bytes(&image, quality))
        .map_err(PyErr::from)
}

/// Extract a colour palette from raw image bytes.
///
/// Parameters
/// ----------
/// image : bytes | bytearray
///     Raw image data (PNG, JPEG, WebP, BMP, GIF, TIFF, etc.).
/// color_count : int, optional
///     Maximum number of palette entries. Default 10.
/// quality : int, optional
///     Quality/bias parameter. Default 10.
///
/// Returns
/// -------
/// list[tuple[int, int, int]]
///     List of ``(r, g, b)`` tuples, each in [0, 255].
#[pyfunction]
#[pyo3(signature = (image, color_count=None, quality=None))]
fn colorthief_get_palette_bytes(
    py: Python<'_>,
    image: Vec<u8>,
    color_count: Option<u8>,
    quality: Option<u8>,
) -> PyResult<Vec<(u8, u8, u8)>> {
    py.detach(|| colorthief::get_palette_from_bytes(&image, color_count, quality))
        .map_err(PyErr::from)
}

// ── Thumbnail Python bindings ───────────────────────────────────────────────

fn run_thumbnail(
    bytes: Option<&[u8]>,
    path: Option<PathBuf>,
    width: u32,
    height: u32,
    quality: u8,
    format: thumbnail::OutputFormat,
    engine: &str,
    compress: bool,
) -> Result<Vec<u8>, thumbnail::ThumbnailError> {
    let raw = run_thumbnail_inner(bytes, path, width, height, quality, format, engine)?;
    if !compress {
        return Ok(raw);
    }
    // Apply the pixo re-encoder when we asked for a format pixo understands.
    // `compress::compress_encoded` is a safe no-op pass-through when either
    // (a) the `pixo` cargo feature isn't compiled in, or (b) the bytes don't
    // begin with a JPEG/PNG magic header. So this call is always safe.
    let cf = match format {
        thumbnail::OutputFormat::Jpeg => compress::CompressFormat::Jpeg,
        thumbnail::OutputFormat::Png => compress::CompressFormat::Png,
        // pixo cannot re-encode WebP — just skip the step.
        thumbnail::OutputFormat::Webp => return Ok(raw),
    };
    match compress::compress_encoded(&raw, cf, quality) {
        Ok(out) => Ok(out),
        // If pixo trips for any reason, fall back to the original bytes
        // — we never want compression to break thumbnail generation.
        Err(_) => Ok(raw),
    }
}

fn run_thumbnail_inner(
    bytes: Option<&[u8]>,
    path: Option<PathBuf>,
    width: u32,
    height: u32,
    quality: u8,
    format: thumbnail::OutputFormat,
    engine: &str,
) -> Result<Vec<u8>, thumbnail::ThumbnailError> {
    match engine {
        "crude" => match (bytes, path) {
            (Some(b), _) => {
                thumbnail::crude_thumbnail_from_bytes(b, width, height, quality, format)
            }
            (None, Some(p)) => {
                thumbnail::crude_thumbnail_from_path(&p, width, height, quality, format)
            }
            (None, None) => Err(thumbnail::ThumbnailError::InvalidArgs(
                "either bytes or path must be supplied".to_string(),
            )),
        },
        "auto-thumbnail" | "auto_thumbnail" => {
            #[cfg(feature = "auto-thumbnail")]
            {
                match (bytes, path) {
                    (Some(b), _) => thumbnail::auto_backend::create_from_bytes(
                        b, width, height, quality, format,
                    ),
                    (None, Some(p)) => thumbnail::auto_backend::create_from_path(
                        &p, width, height, quality, format,
                    ),
                    (None, None) => Err(thumbnail::ThumbnailError::InvalidArgs(
                        "either bytes or path must be supplied".to_string(),
                    )),
                }
            }
            #[cfg(not(feature = "auto-thumbnail"))]
            {
                let _ = (bytes, path, width, height, quality, format);
                Err(thumbnail::ThumbnailError::BackendUnavailable(
                    "thumbleweed was built without the `auto-thumbnail` cargo feature".to_string(),
                ))
            }
        }
        "auto" => {
            #[cfg(feature = "auto-thumbnail")]
            {
                let auto_result = match (bytes, path.clone()) {
                    (Some(b), _) => thumbnail::auto_backend::create_from_bytes(
                        b, width, height, quality, format,
                    ),
                    (None, Some(p)) => thumbnail::auto_backend::create_from_path(
                        &p, width, height, quality, format,
                    ),
                    (None, None) => Err(thumbnail::ThumbnailError::InvalidArgs(
                        "either bytes or path must be supplied".to_string(),
                    )),
                };
                match auto_result {
                    Ok(b) => Ok(b),
                    Err(_) => match (bytes, path) {
                        (Some(b), _) => {
                            thumbnail::crude_thumbnail_from_bytes(b, width, height, quality, format)
                        }
                        (None, Some(p)) => {
                            thumbnail::crude_thumbnail_from_path(&p, width, height, quality, format)
                        }
                        (None, None) => Err(thumbnail::ThumbnailError::InvalidArgs(
                            "either bytes or path must be supplied".to_string(),
                        )),
                    },
                }
            }
            #[cfg(not(feature = "auto-thumbnail"))]
            {
                match (bytes, path) {
                    (Some(b), _) => {
                        thumbnail::crude_thumbnail_from_bytes(b, width, height, quality, format)
                    }
                    (None, Some(p)) => {
                        thumbnail::crude_thumbnail_from_path(&p, width, height, quality, format)
                    }
                    (None, None) => Err(thumbnail::ThumbnailError::InvalidArgs(
                        "either bytes or path must be supplied".to_string(),
                    )),
                }
            }
        }
        other => Err(thumbnail::ThumbnailError::InvalidArgs(format!(
            "unknown engine {other:?} (expected auto | crude | auto-thumbnail)"
        ))),
    }
}

/// Create a thumbnail from raw image / video / PDF bytes.
///
/// Parameters
/// ----------
/// data : bytes | bytearray
///     Raw bytes of the source file. The format is auto-detected from the
///     leading magic bytes (JPEG, PNG, WebP, GIF, BMP, MP4/MOV, MKV/WebM, PDF).
/// width, height : int, optional
///     Maximum thumbnail dimensions (default 256x256). Aspect ratio is preserved.
/// quality : int, optional
///     Quality (1–100, default 85) for JPEG and lossy WebP. Ignored for PNG.
/// format : str, optional
///     Output format: ``"jpeg"`` (default), ``"png"``, or ``"webp"``.
/// engine : str, optional
///     ``"auto"`` (default), ``"crude"``, or ``"auto-thumbnail"``. ``auto``
///     prefers the auto-thumbnail backend (when compiled in) and falls back
///     to the pure-Rust crude pipeline on any error.
///
/// Returns
/// -------
/// bytes
///     Encoded thumbnail bytes in the requested ``format``.
#[pyfunction]
#[pyo3(signature = (data, width=256, height=256, quality=85, format="jpeg", engine="auto", compress=true))]
fn thumbnail_create_from_bytes<'py>(
    py: Python<'py>,
    data: Vec<u8>,
    width: u32,
    height: u32,
    quality: u8,
    format: &str,
    engine: &str,
    compress: bool,
) -> PyResult<Bound<'py, PyBytes>> {
    let fmt = thumbnail::OutputFormat::from_str_ci(format)?;
    let engine_owned = engine.to_string();
    let bytes = py.detach(|| {
        run_thumbnail(
            Some(&data),
            None,
            width,
            height,
            quality,
            fmt,
            &engine_owned,
            compress,
        )
    })?;
    Ok(PyBytes::new(py, &bytes))
}

/// Create a thumbnail from a file path.
#[pyfunction]
#[pyo3(signature = (path, width=256, height=256, quality=85, format="jpeg", engine="auto", compress=true))]
fn thumbnail_create_from_path<'py>(
    py: Python<'py>,
    path: PathBuf,
    width: u32,
    height: u32,
    quality: u8,
    format: &str,
    engine: &str,
    compress: bool,
) -> PyResult<Bound<'py, PyBytes>> {
    let fmt = thumbnail::OutputFormat::from_str_ci(format)?;
    let engine_owned = engine.to_string();
    let bytes = py.detach(|| {
        run_thumbnail(
            None,
            Some(path),
            width,
            height,
            quality,
            fmt,
            &engine_owned,
            compress,
        )
    })?;
    Ok(PyBytes::new(py, &bytes))
}

/// Create a thumbnail and write it to ``output_path``.
#[pyfunction]
#[pyo3(signature = (input_path, output_path, width=256, height=256, quality=85, format=None, engine="auto", compress=true))]
fn thumbnail_save(
    py: Python<'_>,
    input_path: PathBuf,
    output_path: PathBuf,
    width: u32,
    height: u32,
    quality: u8,
    format: Option<&str>,
    engine: &str,
    compress: bool,
) -> PyResult<()> {
    // Infer format from the output path extension when not specified.
    let inferred = output_path
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("jpeg");
    let fmt_str = format.unwrap_or(inferred);
    let fmt = thumbnail::OutputFormat::from_str_ci(fmt_str)?;
    let engine_owned = engine.to_string();
    py.detach(|| -> Result<(), thumbnail::ThumbnailError> {
        let bytes = run_thumbnail(
            None,
            Some(input_path),
            width,
            height,
            quality,
            fmt,
            &engine_owned,
            compress,
        )?;
        std::fs::write(&output_path, &bytes)?;
        Ok(())
    })?;
    Ok(())
}

/// Detect the input kind from magic bytes. Returns one of
/// ``"image"``, ``"video"``, ``"pdf"``, or ``"unknown"``.
#[pyfunction]
fn thumbnail_detect_kind(data: &[u8]) -> &'static str {
    match thumbnail::detect_kind(data) {
        thumbnail::InputKind::Image => "image",
        thumbnail::InputKind::Video => "video",
        thumbnail::InputKind::Pdf => "pdf",
        thumbnail::InputKind::Unknown => "unknown",
    }
}

/// Return the list of compiled-in thumbnail backends.
#[pyfunction]
fn thumbnail_available_backends() -> Vec<&'static str> {
    thumbnail::available_backends()
}

// ── Compression (pixo) Python bindings ────────────────────────────────────────

/// Re-encode an image using pixo's max-compression preset.
///
/// Parameters
/// ----------
/// data : bytes | bytearray
///     Encoded image bytes (JPEG, PNG, or anything else — see ``format``).
/// format : str, optional
///     ``"auto"`` (default), ``"jpeg"``, or ``"png"``. ``"auto"`` infers the
///     format from the input's magic bytes; non-JPEG/PNG inputs (WebP, GIF,
///     unknown blobs) are returned verbatim.
/// quality : int, optional
///     1–100 (default 85). Only used when re-encoding JPEG.
///
/// Returns
/// -------
/// bytes
///     Re-encoded bytes if pixo produced something smaller than the input,
///     otherwise the input unchanged. If thumbleweed was built without the
///     ``pixo`` cargo feature, this function is a no-op pass-through.
#[pyfunction]
#[pyo3(signature = (data, format="auto", quality=85))]
fn compress_image<'py>(
    py: Python<'py>,
    data: Vec<u8>,
    format: &str,
    quality: u8,
) -> PyResult<Bound<'py, PyBytes>> {
    let fmt = compress::CompressFormat::from_str_ci(format)?;
    let bytes = py.detach(|| compress::compress_encoded(&data, fmt, quality))?;
    Ok(PyBytes::new(py, &bytes))
}

/// Returns ``True`` when the wheel was built with the ``pixo`` cargo feature.
#[pyfunction]
fn compress_is_available() -> bool {
    compress::is_available()
}

/// Detect the encoded format of ``data``: ``"jpeg"``, ``"png"``, ``"webp"``,
/// or ``"unknown"``.
#[pyfunction]
fn compress_detect_format(data: &[u8]) -> &'static str {
    compress::detect_encoded(data)
}

// ── Module ───────────────────────────────────────────────────────────────────

/// thumbleweed — unified image hashing library.
///
/// Provides ThumbHash, BlurHash, and (eventually) ColorThief implementations.
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // ThumbHash
    m.add_function(wrap_pyfunction!(thumbhash_encode, m)?)?;
    m.add_function(wrap_pyfunction!(thumbhash_encode_image_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(thumbhash_decode, m)?)?;
    m.add_function(wrap_pyfunction!(thumbhash_average_rgba, m)?)?;
    m.add_function(wrap_pyfunction!(thumbhash_approximate_aspect_ratio, m)?)?;

    // BlurHash
    m.add_function(wrap_pyfunction!(blurhash_encode, m)?)?;
    m.add_function(wrap_pyfunction!(blurhash_encode_image_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(blurhash_decode, m)?)?;

    // ColorThief
    m.add_function(wrap_pyfunction!(colorthief_get_color_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(colorthief_get_palette_bytes, m)?)?;

    // Thumbnail
    m.add_function(wrap_pyfunction!(thumbnail_create_from_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(thumbnail_create_from_path, m)?)?;
    m.add_function(wrap_pyfunction!(thumbnail_save, m)?)?;
    m.add_function(wrap_pyfunction!(thumbnail_detect_kind, m)?)?;
    m.add_function(wrap_pyfunction!(thumbnail_available_backends, m)?)?;

    // Compression (pixo)
    m.add_function(wrap_pyfunction!(compress_image, m)?)?;
    m.add_function(wrap_pyfunction!(compress_is_available, m)?)?;
    m.add_function(wrap_pyfunction!(compress_detect_format, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
