use std::f32::consts::PI;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use thiserror::Error;

// ── Error type ───────────────────────────────────────────────────────────────

/// All errors that can be produced by the pure-Rust thumbhash layer.
///
/// Using `thiserror` keeps error variants typed so callers can match on them,
/// while `Display` impls are derived automatically for the Python boundary.
#[derive(Debug, Error)]
pub enum ThumbHashError {
    #[error("hash is too short: need at least {need} bytes, got {got}")]
    TooShort { need: usize, got: usize },

    #[error("image dimensions must be 1–100 px, got {w}×{h}")]
    InvalidDimensions { w: usize, h: usize },

    #[error("RGBA buffer length mismatch: expected {expected} bytes for {w}×{h}, got {actual}")]
    BufferMismatch {
        w: usize,
        h: usize,
        expected: usize,
        actual: usize,
    },
}

// Teach PyO3 how to turn our error into a Python ValueError automatically,
// so every `?` at the Rust→Python boundary does the right thing.
impl From<ThumbHashError> for PyErr {
    fn from(e: ThumbHashError) -> Self {
        PyValueError::new_err(e.to_string())
    }
}

// ── Pure-Rust ThumbHash implementation ──────────────────────────────────────
// Adapted from the reference Rust implementation (MIT licence).
// All functions return Result instead of panicking so errors surface cleanly
// across the GIL boundary.

/// Encodes an RGBA image to a ThumbHash.
/// RGB must **not** be premultiplied by A. `w` and `h` must be in 1–100.
fn rgba_to_thumb_hash(w: usize, h: usize, rgba: &[u8]) -> Result<Vec<u8>, ThumbHashError> {
    if w == 0 || h == 0 || w > 100 || h > 100 {
        return Err(ThumbHashError::InvalidDimensions { w, h });
    }
    let expected = w * h * 4;
    if rgba.len() != expected {
        return Err(ThumbHashError::BufferMismatch {
            w,
            h,
            expected,
            actual: rgba.len(),
        });
    }

    // Determine the average colour
    let mut avg_r = 0.0f32;
    let mut avg_g = 0.0f32;
    let mut avg_b = 0.0f32;
    let mut avg_a = 0.0f32;
    for px in rgba.chunks_exact(4) {
        let alpha = px[3] as f32 / 255.0;
        avg_r += alpha / 255.0 * px[0] as f32;
        avg_g += alpha / 255.0 * px[1] as f32;
        avg_b += alpha / 255.0 * px[2] as f32;
        avg_a += alpha;
    }
    if avg_a > 0.0 {
        avg_r /= avg_a;
        avg_g /= avg_a;
        avg_b /= avg_a;
    }

    let has_alpha = avg_a < (w * h) as f32;
    let l_limit = if has_alpha { 5usize } else { 7usize };
    let lx = ((l_limit * w) as f32 / w.max(h) as f32).round().max(1.0) as usize;
    let ly = ((l_limit * h) as f32 / w.max(h) as f32).round().max(1.0) as usize;

    let mut l_chan = Vec::with_capacity(w * h);
    let mut p_chan = Vec::with_capacity(w * h);
    let mut q_chan = Vec::with_capacity(w * h);
    let mut a_chan = Vec::with_capacity(w * h);

    // Convert RGBA -> LPQA (composite atop the average colour)
    for px in rgba.chunks_exact(4) {
        let alpha = px[3] as f32 / 255.0;
        let r = avg_r * (1.0 - alpha) + alpha / 255.0 * px[0] as f32;
        let g = avg_g * (1.0 - alpha) + alpha / 255.0 * px[1] as f32;
        let b = avg_b * (1.0 - alpha) + alpha / 255.0 * px[2] as f32;
        l_chan.push((r + g + b) / 3.0);
        p_chan.push((r + g) / 2.0 - b);
        q_chan.push(r - g);
        a_chan.push(alpha);
    }

    // DCT encode - closure captures `w` and `h` from the outer scope
    let encode_channel = |channel: &[f32], nx: usize, ny: usize| -> (f32, Vec<f32>, f32) {
        let mut dc = 0.0f32;
        let mut ac: Vec<f32> = Vec::with_capacity(nx * ny / 2);
        let mut scale = 0.0f32;
        let mut fx = vec![0.0f32; w];
        for cy in 0..ny {
            let mut cx = 0usize;
            while cx * ny < nx * (ny - cy) {
                let mut f = 0.0f32;
                for x in 0..w {
                    fx[x] = (PI / w as f32 * cx as f32 * (x as f32 + 0.5)).cos();
                }
                for y in 0..h {
                    let fy = (PI / h as f32 * cy as f32 * (y as f32 + 0.5)).cos();
                    for x in 0..w {
                        f += channel[x + y * w] * fx[x] * fy;
                    }
                }
                f /= (w * h) as f32;
                if cx > 0 || cy > 0 {
                    ac.push(f);
                    if f.abs() > scale {
                        scale = f.abs();
                    }
                } else {
                    dc = f;
                }
                cx += 1;
            }
        }
        if scale > 0.0 {
            for v in &mut ac {
                *v = 0.5 + 0.5 / scale * *v;
            }
        }
        (dc, ac, scale)
    };

    let (l_dc, l_ac, l_scale) = encode_channel(&l_chan, lx.max(3), ly.max(3));
    let (p_dc, p_ac, p_scale) = encode_channel(&p_chan, 3, 3);
    let (q_dc, q_ac, q_scale) = encode_channel(&q_chan, 3, 3);
    let (a_dc, a_ac, a_scale) = if has_alpha {
        encode_channel(&a_chan, 5, 5)
    } else {
        (1.0, Vec::new(), 1.0)
    };

    // Write header
    let is_landscape = w > h;
    let header24 = (63.0 * l_dc).round() as u32
        | (((31.5 + 31.5 * p_dc).round() as u32) << 6)
        | (((31.5 + 31.5 * q_dc).round() as u32) << 12)
        | (((31.0 * l_scale).round() as u32) << 18)
        | if has_alpha { 1 << 23 } else { 0 };
    let header16: u16 = (if is_landscape { ly } else { lx }) as u16
        | (((63.0 * p_scale).round() as u16) << 3)
        | (((63.0 * q_scale).round() as u16) << 9)
        | if is_landscape { 1 << 15 } else { 0 };

    let mut hash: Vec<u8> = Vec::with_capacity(25);
    hash.extend_from_slice(&[
        (header24 & 0xff) as u8,
        ((header24 >> 8) & 0xff) as u8,
        (header24 >> 16) as u8,
        (header16 & 0xff) as u8,
        (header16 >> 8) as u8,
    ]);
    if has_alpha {
        hash.push((15.0 * a_dc).round() as u8 | (((15.0 * a_scale).round() as u8) << 4));
    }

    // Write AC coefficients (packed two nibbles per byte)
    let mut is_odd = false;
    for &f in l_ac.iter().chain(p_ac.iter()).chain(q_ac.iter()) {
        let u = (15.0 * f).round() as u8;
        if is_odd {
            *hash.last_mut().unwrap() |= u << 4;
        } else {
            hash.push(u);
        }
        is_odd = !is_odd;
    }
    if has_alpha {
        for &f in &a_ac {
            let u = (15.0 * f).round() as u8;
            if is_odd {
                *hash.last_mut().unwrap() |= u << 4;
            } else {
                hash.push(u);
            }
            is_odd = !is_odd;
        }
    }
    Ok(hash)
}

/// Decode a ThumbHash into `(width, height, rgba_bytes)`.
fn thumb_hash_to_rgba(hash: &[u8]) -> Result<(usize, usize, Vec<u8>), ThumbHashError> {
    // aspect ratio check also validates minimum length
    let ratio = thumb_hash_to_approximate_aspect_ratio(hash)?;

    let header24 = hash[0] as u32 | ((hash[1] as u32) << 8) | ((hash[2] as u32) << 16);
    let header16 = hash[3] as u16 | ((hash[4] as u16) << 8);
    let l_dc = (header24 & 63) as f32 / 63.0;
    let p_dc = ((header24 >> 6) & 63) as f32 / 31.5 - 1.0;
    let q_dc = ((header24 >> 12) & 63) as f32 / 31.5 - 1.0;
    let l_scale = ((header24 >> 18) & 31) as f32 / 31.0;
    let has_alpha = (header24 >> 23) != 0;
    let p_scale = ((header16 >> 3) & 63) as f32 / 63.0;
    let q_scale = ((header16 >> 9) & 63) as f32 / 63.0;
    let is_landscape = (header16 >> 15) != 0;
    let l_max = if has_alpha { 5u16 } else { 7u16 };
    let lx = 3usize.max(if is_landscape { l_max } else { header16 & 7 } as usize);
    let ly = 3usize.max(if is_landscape { header16 & 7 } else { l_max } as usize);

    let (a_dc, a_scale, ac_hash) = if has_alpha {
        if hash.len() < 6 {
            return Err(ThumbHashError::TooShort { need: 6, got: hash.len() });
        }
        (
            (hash[5] & 15) as f32 / 15.0,
            (hash[5] >> 4) as f32 / 15.0,
            &hash[6..],
        )
    } else {
        (1.0f32, 1.0f32, &hash[5..])
    };

    // Decode AC coefficients from packed nibbles.
    // `read_nibble` pads with zeros when the hash is shorter than expected
    // (graceful degradation rather than a hard error for partial hashes).
    let read_nibble = |idx: usize| -> u8 {
        let byte = ac_hash.get(idx / 2).copied().unwrap_or(0);
        if idx & 1 == 0 { byte & 0x0f } else { byte >> 4 }
    };

    let mut nibble_idx: usize = 0;
    let mut decode_channel = |nx: usize, ny: usize, scale: f32| -> Vec<f32> {
        let mut ac = Vec::new();
        for cy in 0..ny {
            let mut cx = if cy > 0 { 0 } else { 1 };
            while cx * ny < nx * (ny - cy) {
                let bits = read_nibble(nibble_idx) as f32;
                nibble_idx += 1;
                ac.push((bits / 7.5 - 1.0) * scale);
                cx += 1;
            }
        }
        ac
    };

    let l_ac = decode_channel(lx, ly, l_scale);
    let p_ac = decode_channel(3, 3, p_scale * 1.25);
    let q_ac = decode_channel(3, 3, q_scale * 1.25);
    let a_ac = if has_alpha {
        decode_channel(5, 5, a_scale)
    } else {
        Vec::new()
    };

    // Determine output dimensions (longest side = 32 px)
    let (w, h) = if ratio > 1.0 {
        (32usize, (32.0f32 / ratio).round() as usize)
    } else {
        ((32.0f32 * ratio).round() as usize, 32usize)
    };
    let w = w.max(1);
    let h = h.max(1);

    let mut rgba = Vec::with_capacity(w * h * 4);
    let mut fx = [0.0f32; 7];
    let mut fy = [0.0f32; 7];

    for y in 0..h {
        for x in 0..w {
            let mut l = l_dc;
            let mut p = p_dc;
            let mut q = q_dc;
            let mut a = a_dc;

            // Precompute DCT basis coefficients for this pixel
            for cx in 0..lx.max(if has_alpha { 5 } else { 3 }) {
                fx[cx] = (PI / w as f32 * (x as f32 + 0.5) * cx as f32).cos();
            }
            for cy in 0..ly.max(if has_alpha { 5 } else { 3 }) {
                fy[cy] = (PI / h as f32 * (y as f32 + 0.5) * cy as f32).cos();
            }

            // Decode L
            let mut j = 0;
            for cy in 0..ly {
                let mut cx = if cy > 0 { 0 } else { 1 };
                let fy2 = fy[cy] * 2.0;
                while cx * ly < lx * (ly - cy) {
                    l += l_ac[j] * fx[cx] * fy2;
                    j += 1;
                    cx += 1;
                }
            }

            // Decode P and Q
            let mut j = 0;
            for cy in 0..3 {
                let mut cx = if cy > 0 { 0 } else { 1 };
                let fy2 = fy[cy] * 2.0;
                while cx < 3 - cy {
                    let f = fx[cx] * fy2;
                    p += p_ac[j] * f;
                    q += q_ac[j] * f;
                    j += 1;
                    cx += 1;
                }
            }

            // Decode A
            if has_alpha {
                let mut j = 0;
                for cy in 0..5 {
                    let mut cx = if cy > 0 { 0 } else { 1 };
                    let fy2 = fy[cy] * 2.0;
                    while cx < 5 - cy {
                        a += a_ac[j] * fx[cx] * fy2;
                        j += 1;
                        cx += 1;
                    }
                }
            }

            // Convert L P Q -> R G B
            let b = l - 2.0 / 3.0 * p;
            let r = (3.0 * l - b + q) / 2.0;
            let g = r - q;
            rgba.push((r.clamp(0.0, 1.0) * 255.0) as u8);
            rgba.push((g.clamp(0.0, 1.0) * 255.0) as u8);
            rgba.push((b.clamp(0.0, 1.0) * 255.0) as u8);
            rgba.push((a.clamp(0.0, 1.0) * 255.0) as u8);
        }
    }

    Ok((w, h, rgba))
}

fn thumb_hash_to_average_rgba(hash: &[u8]) -> Result<(f32, f32, f32, f32), ThumbHashError> {
    if hash.len() < 5 {
        return Err(ThumbHashError::TooShort { need: 5, got: hash.len() });
    }
    let header = hash[0] as u32 | ((hash[1] as u32) << 8) | ((hash[2] as u32) << 16);
    let l = (header & 63) as f32 / 63.0;
    let p = ((header >> 6) & 63) as f32 / 31.5 - 1.0;
    let q = ((header >> 12) & 63) as f32 / 31.5 - 1.0;
    let has_alpha = (header >> 23) != 0;
    let a = if has_alpha {
        if hash.len() < 6 {
            return Err(ThumbHashError::TooShort { need: 6, got: hash.len() });
        }
        (hash[5] & 15) as f32 / 15.0
    } else {
        1.0
    };
    let b = l - 2.0 / 3.0 * p;
    let r = (3.0 * l - b + q) / 2.0;
    let g = r - q;
    Ok((r.clamp(0.0, 1.0), g.clamp(0.0, 1.0), b.clamp(0.0, 1.0), a))
}

fn thumb_hash_to_approximate_aspect_ratio(hash: &[u8]) -> Result<f32, ThumbHashError> {
    if hash.len() < 5 {
        return Err(ThumbHashError::TooShort { need: 5, got: hash.len() });
    }
    let has_alpha = (hash[2] & 0x80) != 0;
    let l_max: u8 = if has_alpha { 5 } else { 7 };
    let l_min: u8 = hash[3] & 7;
    let is_landscape = (hash[4] & 0x80) != 0;
    let lx = if is_landscape { l_max } else { l_min };
    let ly = if is_landscape { l_min } else { l_max };
    Ok(lx as f32 / ly as f32)
}

// ── PyO3 bindings ────────────────────────────────────────────────────────────

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
///
/// Raises
/// ------
/// ValueError
///     If dimensions are out of range or the buffer length does not match.
#[pyfunction]
fn encode<'py>(
    py: Python<'py>,
    w: usize,
    h: usize,
    rgba: Vec<u8>, // Vec<u8> extracts from bytes, bytearray, and buffer-protocol objects
) -> PyResult<Bound<'py, PyBytes>> {
    // Validate before releasing the GIL - fast, no threads needed.
    if w == 0 || h == 0 || w > 100 || h > 100 {
        return Err(ThumbHashError::InvalidDimensions { w, h }.into());
    }
    let expected = w * h * 4;
    if rgba.len() != expected {
        return Err(ThumbHashError::BufferMismatch { w, h, expected, actual: rgba.len() }.into());
    }

    // Release the GIL for the CPU-bound DCT computation.
    // `rgba` is an owned Vec - no Python objects are touched inside the closure.
    let hash = py.allow_threads(|| rgba_to_thumb_hash(w, h, &rgba))?;
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
///     ``(width, height, rgba_bytes)`` - raw row-major RGBA (not premultiplied).
///
/// Raises
/// ------
/// ValueError
///     If the hash is too short to be valid.
#[pyfunction]
fn decode<'py>(
    py: Python<'py>,
    hash: Vec<u8>, // accepts bytes and bytearray
) -> PyResult<(usize, usize, Bound<'py, PyBytes>)> {
    // Release the GIL for the CPU-bound DCT decode.
    let (w, h, rgba) = py.allow_threads(|| thumb_hash_to_rgba(&hash))?;
    Ok((w, h, PyBytes::new(py, &rgba)))
}

/// Extract the average colour from a ThumbHash.
///
/// Returns
/// -------
/// tuple[float, float, float, float]
///     ``(r, g, b, a)`` each in ``[0.0, 1.0]``. RGB is **not** premultiplied.
///
/// Raises
/// ------
/// ValueError
///     If the hash is too short.
#[pyfunction]
fn average_rgba(hash: Vec<u8>) -> PyResult<(f32, f32, f32, f32)> {
    // O(1) header read - no benefit to releasing the GIL.
    Ok(thumb_hash_to_average_rgba(&hash)?)
}

/// Return the approximate aspect ratio (width / height) of the original image.
///
/// Raises
/// ------
/// ValueError
///     If the hash is too short.
#[pyfunction]
fn approximate_aspect_ratio(hash: Vec<u8>) -> PyResult<f32> {
    Ok(thumb_hash_to_approximate_aspect_ratio(&hash)?)
}

// ── Module ───────────────────────────────────────────────────────────────────

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(encode, m)?)?;
    m.add_function(wrap_pyfunction!(decode, m)?)?;
    m.add_function(wrap_pyfunction!(average_rgba, m)?)?;
    m.add_function(wrap_pyfunction!(approximate_aspect_ratio, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}