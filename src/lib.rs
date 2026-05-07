//! thumbleweed — unified image hashing library (Rust core).
//!
//! This crate provides ThumbHash, BlurHash, and (eventually) ColorThief
//! implementations, exposed to Python via PyO3.

mod blurhash;
mod colorthief;
mod thumbhash;

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

// ── Module ───────────────────────────────────────────────────────────────────

/// thumbleweed — unified image hashing library.
///
/// Provides ThumbHash, BlurHash, and (eventually) ColorThief implementations.
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // ThumbHash
    m.add_function(wrap_pyfunction!(thumbhash_encode, m)?)?;
    m.add_function(wrap_pyfunction!(thumbhash_decode, m)?)?;
    m.add_function(wrap_pyfunction!(thumbhash_average_rgba, m)?)?;
    m.add_function(wrap_pyfunction!(thumbhash_approximate_aspect_ratio, m)?)?;

    // BlurHash
    m.add_function(wrap_pyfunction!(blurhash_encode, m)?)?;
    m.add_function(wrap_pyfunction!(blurhash_decode, m)?)?;

    // ColorThief
    m.add_function(wrap_pyfunction!(colorthief_get_color_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(colorthief_get_palette_bytes, m)?)?;

    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
