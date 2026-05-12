//! Image compression powered by the [`pixo`](https://crates.io/crates/pixo) crate.
//!
//! pixo is a pure-Rust JPEG/PNG re-encoder competitive with mozjpeg / oxipng.
//! This module exposes:
//!
//! * [`compress_jpeg`] — re-encode RGB pixels as a (smaller) JPEG.
//! * [`compress_png`]  — re-encode RGBA pixels as a (smaller) PNG.
//! * [`compress_encoded`] — accept already-encoded bytes (JPEG/PNG/WebP/...),
//!   decode via the `image` crate and re-encode through pixo. WebP and other
//!   formats that pixo cannot encode are returned unchanged.
//!
//! All routines guarantee that the returned bytes are no larger than the
//! input — if pixo's output is bigger (e.g. a tiny placeholder), the original
//! bytes are returned verbatim.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum CompressError {
    #[error("image decode error: {0}")]
    Image(#[from] image::ImageError),

    #[error("pixo encode error: {0}")]
    Pixo(String),

    #[error("invalid arguments: {0}")]
    InvalidArgs(String),
}

impl From<CompressError> for pyo3::PyErr {
    fn from(e: CompressError) -> Self {
        pyo3::exceptions::PyValueError::new_err(e.to_string())
    }
}

/// Output formats this module knows how to re-encode.
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum CompressFormat {
    /// Auto-detect the format from the input's magic bytes.
    Auto,
    Jpeg,
    Png,
}

impl CompressFormat {
    pub fn from_str_ci(s: &str) -> Result<Self, CompressError> {
        match s.to_ascii_lowercase().as_str() {
            "auto" => Ok(Self::Auto),
            "jpeg" | "jpg" => Ok(Self::Jpeg),
            "png" => Ok(Self::Png),
            other => Err(CompressError::InvalidArgs(format!(
                "unknown compress format {other:?} (expected auto | jpeg | png)"
            ))),
        }
    }
}

/// Detect what kind of encoded image is held in `bytes`.
///
/// Returns one of ``"jpeg"``, ``"png"``, ``"webp"``, or ``"unknown"``.
pub fn detect_encoded(bytes: &[u8]) -> &'static str {
    if bytes.starts_with(b"\xFF\xD8\xFF") {
        "jpeg"
    } else if bytes.starts_with(b"\x89PNG\r\n\x1a\n") {
        "png"
    } else if bytes.len() >= 12 && &bytes[0..4] == b"RIFF" && &bytes[8..12] == b"WEBP" {
        "webp"
    } else {
        "unknown"
    }
}

// ── pixo-backed pipeline (compiled in only with the `pixo` feature) ─────────

#[cfg(feature = "pixo")]
mod pixo_impl {
    use super::*;
    use pixo::{ColorType, jpeg, png};

    pub fn jpeg_encode(
        rgb: &[u8],
        width: u32,
        height: u32,
        quality: u8,
    ) -> Result<Vec<u8>, CompressError> {
        let q = quality.clamp(1, 100);
        // Preset 2 (Max) enables: optimized Huffman, progressive scans, and
        // trellis quantization — the closest pure-Rust analogue to mozjpeg's
        // `--max` profile.
        let opts = jpeg::JpegOptions::max(width, height, q);
        let opts = jpeg::JpegOptions {
            color_type: ColorType::Rgb,
            ..opts
        };
        jpeg::encode(rgb, &opts).map_err(|e| CompressError::Pixo(e.to_string()))
    }

    pub fn png_encode(rgba: &[u8], width: u32, height: u32) -> Result<Vec<u8>, CompressError> {
        // Preset 2 (Max) enables level-9 DEFLATE, MinSum filtering, optimal
        // Zopfli-style compression, plus colour-type / palette / alpha
        // optimisations — competitive with oxipng's max preset.
        let opts = png::PngOptions::max(width, height);
        let opts = png::PngOptions {
            color_type: ColorType::Rgba,
            ..opts
        };
        png::encode(rgba, &opts).map_err(|e| CompressError::Pixo(e.to_string()))
    }
}

/// Re-encode raw RGB pixels as a JPEG using pixo's "max" preset.
///
/// Returns `Err(InvalidArgs)` if the `pixo` cargo feature is not enabled.
//
// NOTE: when the `pixo` cargo feature is OFF this function is technically
// unreachable from the rest of the crate (we only call `compress_encoded`),
// but it remains part of the documented public Rust API for downstream
// consumers. Suppress the dead-code lint without removing the function.
#[allow(unused_variables, dead_code)]
pub fn compress_jpeg(
    rgb: &[u8],
    width: u32,
    height: u32,
    quality: u8,
) -> Result<Vec<u8>, CompressError> {
    #[cfg(feature = "pixo")]
    {
        pixo_impl::jpeg_encode(rgb, width, height, quality)
    }
    #[cfg(not(feature = "pixo"))]
    {
        Err(CompressError::InvalidArgs(
            "thumbleweed was built without the `pixo` cargo feature".to_string(),
        ))
    }
}

/// Re-encode raw RGBA pixels as a PNG using pixo's "max" preset.
///
/// Returns `Err(InvalidArgs)` if the `pixo` cargo feature is not enabled.
//
// NOTE: same rationale as `compress_jpeg` — part of the public Rust surface,
// silenced when the optional `pixo` feature is not compiled in.
#[allow(unused_variables, dead_code)]
pub fn compress_png(rgba: &[u8], width: u32, height: u32) -> Result<Vec<u8>, CompressError> {
    #[cfg(feature = "pixo")]
    {
        pixo_impl::png_encode(rgba, width, height)
    }
    #[cfg(not(feature = "pixo"))]
    {
        Err(CompressError::InvalidArgs(
            "thumbleweed was built without the `pixo` cargo feature".to_string(),
        ))
    }
}

/// Re-encode previously-encoded image bytes through pixo and return the
/// smaller of (pixo output, original input).
///
/// Behaviour:
///
/// * JPEG → decoded to RGB and re-encoded via pixo's max preset.
/// * PNG  → decoded to RGBA and re-encoded via pixo's max preset.
/// * WebP / other / unknown → returned unchanged.
/// * If the pixo `cargo` feature is not enabled, the input is returned
///   unchanged. This makes the function safe to call unconditionally.
///
/// `quality` is only used for JPEG output and is clamped to ``1..=100``.
/// Passing ``CompressFormat::Auto`` infers the format from the input's
/// magic bytes.
pub fn compress_encoded(
    bytes: &[u8],
    format: CompressFormat,
    quality: u8,
) -> Result<Vec<u8>, CompressError> {
    let resolved = match format {
        CompressFormat::Auto => match detect_encoded(bytes) {
            "jpeg" => CompressFormat::Jpeg,
            "png" => CompressFormat::Png,
            // Unknown / WebP / other formats: pixo cannot help; return as-is.
            _ => return Ok(bytes.to_vec()),
        },
        other => other,
    };

    #[cfg(not(feature = "pixo"))]
    {
        // Without the pixo feature, this function is a no-op so it remains
        // safe to call unconditionally from the thumbnail pipeline.
        let _ = (resolved, quality);
        return Ok(bytes.to_vec());
    }

    #[cfg(feature = "pixo")]
    {
        let img = image::load_from_memory(bytes)?;
        let (w, h) = (img.width(), img.height());
        let recoded = match resolved {
            CompressFormat::Jpeg => {
                let rgb = img.to_rgb8();
                compress_jpeg(rgb.as_raw(), w, h, quality)?
            }
            CompressFormat::Png => {
                let rgba = img.to_rgba8();
                compress_png(rgba.as_raw(), w, h)?
            }
            CompressFormat::Auto => unreachable!(),
        };
        if recoded.len() < bytes.len() {
            Ok(recoded)
        } else {
            Ok(bytes.to_vec())
        }
    }
}

/// Returns whether the `pixo` cargo feature was compiled in.
pub const fn is_available() -> bool {
    cfg!(feature = "pixo")
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use image::{ExtendedColorType, ImageEncoder};

    // Same rationale as `make_png`: only consumed by feature-gated tests.
    #[allow(dead_code)]
    fn make_jpeg(w: u32, h: u32, quality: u8) -> Vec<u8> {
        // Build a noisy RGB image so JPEG compression has work to do.
        let mut pixels = Vec::with_capacity((w * h * 3) as usize);
        for y in 0..h {
            for x in 0..w {
                pixels.push(((x * 7 + y * 11) % 256) as u8);
                pixels.push(((x * 13 + y * 5) % 256) as u8);
                pixels.push(((x * 3 + y * 17) % 256) as u8);
            }
        }
        let mut out = Vec::new();
        let enc = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut out, quality);
        enc.write_image(&pixels, w, h, ExtendedColorType::Rgb8)
            .unwrap();
        out
    }

    // NOTE: only used by tests gated on `cfg(feature = "pixo")`. Silence
    // the unused-function warning when building tests without that feature.
    #[allow(dead_code)]
    fn make_png(w: u32, h: u32) -> Vec<u8> {
        // Build a noisy RGBA image so PNG can do real work.
        let mut pixels = Vec::with_capacity((w * h * 4) as usize);
        for y in 0..h {
            for x in 0..w {
                pixels.push(((x * 7 + y * 11) % 256) as u8);
                pixels.push(((x * 13 + y * 5) % 256) as u8);
                pixels.push(((x * 3 + y * 17) % 256) as u8);
                pixels.push(255);
            }
        }
        let mut out = Vec::new();
        let enc = image::codecs::png::PngEncoder::new(&mut out);
        enc.write_image(&pixels, w, h, ExtendedColorType::Rgba8)
            .unwrap();
        out
    }

    #[test]
    fn detect_basic_formats() {
        assert_eq!(detect_encoded(b"\xFF\xD8\xFF\xE0xxx"), "jpeg");
        assert_eq!(detect_encoded(b"\x89PNG\r\n\x1a\nxxxx"), "png");
        assert_eq!(detect_encoded(b"RIFF\0\0\0\0WEBPxx"), "webp");
        assert_eq!(detect_encoded(b"hello world"), "unknown");
    }

    #[test]
    fn format_parsing() {
        assert_eq!(
            CompressFormat::from_str_ci("AUTO").unwrap(),
            CompressFormat::Auto
        );
        assert_eq!(
            CompressFormat::from_str_ci("jpg").unwrap(),
            CompressFormat::Jpeg
        );
        assert_eq!(
            CompressFormat::from_str_ci("png").unwrap(),
            CompressFormat::Png
        );
        assert!(CompressFormat::from_str_ci("webp").is_err());
    }

    #[test]
    fn unknown_input_returned_verbatim() {
        let input = b"not an image at all";
        let out = compress_encoded(input, CompressFormat::Auto, 85).unwrap();
        assert_eq!(out.as_slice(), input);
    }

    #[test]
    #[cfg(feature = "pixo")]
    fn jpeg_roundtrip_no_larger() {
        let original = make_jpeg(96, 96, 85);
        let compressed = compress_encoded(&original, CompressFormat::Auto, 85).unwrap();
        assert!(compressed.len() <= original.len());
        // pixo's max-preset JPEG should still be a valid JPEG.
        if compressed != original {
            assert!(compressed.starts_with(b"\xFF\xD8\xFF"));
        }
    }

    #[test]
    #[cfg(feature = "pixo")]
    fn png_roundtrip_no_larger() {
        let original = make_png(96, 96);
        let compressed = compress_encoded(&original, CompressFormat::Auto, 85).unwrap();
        assert!(compressed.len() <= original.len());
        if compressed != original {
            assert!(compressed.starts_with(b"\x89PNG\r\n\x1a\n"));
        }
    }

    #[test]
    #[cfg(not(feature = "pixo"))]
    fn passthrough_when_feature_disabled() {
        let original = make_jpeg(32, 32, 85);
        let out = compress_encoded(&original, CompressFormat::Auto, 85).unwrap();
        assert_eq!(out, original);
    }
}
