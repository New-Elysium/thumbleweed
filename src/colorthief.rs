//! ColorThief — dominant colour and palette extraction from images.
//!
//! Wraps the colour-theif_ crate to extract dominant colours and palettes
//! from any image format supported by the `image` crate (PNG, JPEG, WebP,
//! BMP, GIF, TIFF, etc.).
//!
//! .. _colour-theif: https://crates.io/crates/color-thief

use std::path::Path;

use itertools::Itertools;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use thiserror::Error;

// ── Error types ───────────────────────────────────────────────────────────────

/// Errors that can occur during colour extraction.
#[derive(Debug, Error)]
pub enum ColorThiefError {
    /// The `image` crate could not decode the input.
    #[error("failed to decode image: {0}")]
    ImageDecode(#[from] image::ImageError),

    /// The colour-thief extraction itself failed.
    #[error("palette extraction failed: {message}")]
    ExtractionFailed { message: String },

    /// The extracted palette is empty (should never happen with valid images).
    #[error("palette is empty")]
    EmptyPalette,
}

// Single conversion point — every `?` at the Rust→Python boundary does the
// right thing without repeating PyValueError::new_err at every call site.
impl From<ColorThiefError> for PyErr {
    fn from(e: ColorThiefError) -> Self {
        PyValueError::new_err(e.to_string())
    }
}

/// Internal helper: turn a `color_thief` error into our typed error variant.
impl From<color_thief::Error> for ColorThiefError {
    fn from(e: color_thief::Error) -> Self {
        ColorThiefError::ExtractionFailed {
            message: e.to_string(),
        }
    }
}

// ── Image helpers ─────────────────────────────────────────────────────────────

/// Convert a `DynamicImage` to an RGBA byte buffer and the matching
/// `ColorFormat`.
fn image_to_buffer(img: &image::DynamicImage) -> (Vec<u8>, color_thief::ColorFormat) {
    let rgba = img.to_rgba8();
    let (w, h) = (rgba.width() as usize, rgba.height() as usize);
    debug_assert_eq!(rgba.len(), w * h * 4);
    let bytes = rgba.into_raw();
    (bytes, color_thief::ColorFormat::Rgba)
}

// ── Core palette logic ────────────────────────────────────────────────────────

/// Extract a deduplicated colour palette from a `DynamicImage`.
/// This is pure CPU work — suitable for calling inside `py.detach()`.
pub fn palette_from_image(
    img: &image::DynamicImage,
    color_count: Option<u8>,
    quality: Option<u8>,
) -> Result<Vec<(u8, u8, u8)>, ColorThiefError> {
    let quality_val = quality.unwrap_or(10);
    if quality_val == 0 || quality_val > 10 {
        return Err(ColorThiefError::ExtractionFailed {
            message: format!(
                "quality must be between 1 and 10 inclusive, got {}",
                quality_val
            ),
        });
    }
    let requested_count = color_count.unwrap_or(10);
    if requested_count == 0 {
        return Err(ColorThiefError::ExtractionFailed {
            message: "color_count must be at least 1".to_string(),
        });
    }

    // The upstream `color-thief` crate asserts `max_colors > 1`. Treat a
    // requested one-colour palette as a dominant-colour request and truncate
    // the deduplicated result back to one entry to avoid panics across the FFI
    // boundary.
    let crate_count = requested_count.max(2);

    let (buffer, format) = image_to_buffer(img);
    let colors = color_thief::get_palette(&buffer, format, quality_val, crate_count)
        .map_err(ColorThiefError::from)?;

    Ok(colors
        .iter()
        .map(|c| (c.r, c.g, c.b))
        .unique()
        .take(requested_count as usize)
        .collect())
}

/// Extract the dominant colour (first palette entry) from a `DynamicImage`.
pub fn dominant_from_image(
    img: &image::DynamicImage,
    quality: Option<u8>,
) -> Result<(u8, u8, u8), ColorThiefError> {
    palette_from_image(img, Some(5), quality)
        .and_then(|p| p.into_iter().next().ok_or(ColorThiefError::EmptyPalette))
}

// ── Public API (bytes / path) ─────────────────────────────────────────────────

/// Extract a palette from raw image bytes.
pub fn get_palette_from_bytes(
    image_bytes: &[u8],
    color_count: Option<u8>,
    quality: Option<u8>,
) -> Result<Vec<(u8, u8, u8)>, ColorThiefError> {
    let img = image::load_from_memory(image_bytes)?;
    palette_from_image(&img, color_count, quality)
}

/// Extract a palette from a file path.
pub fn get_palette_from_path(
    path: &Path,
    color_count: Option<u8>,
    quality: Option<u8>,
) -> Result<Vec<(u8, u8, u8)>, ColorThiefError> {
    let img = image::open(path)?;
    palette_from_image(&img, color_count, quality)
}

/// Extract the dominant colour from raw image bytes.
pub fn get_dominant_from_bytes(
    image_bytes: &[u8],
    quality: Option<u8>,
) -> Result<(u8, u8, u8), ColorThiefError> {
    let img = image::load_from_memory(image_bytes)?;
    dominant_from_image(&img, quality)
}

/// Extract the dominant colour from a file path.
pub fn get_dominant_from_path(
    path: &Path,
    quality: Option<u8>,
) -> Result<(u8, u8, u8), ColorThiefError> {
    let img = image::open(path)?;
    dominant_from_image(&img, quality)
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use image::ImageEncoder;

    fn create_solid_image(r: u8, g: u8, b: u8, a: u8) -> image::DynamicImage {
        let rgba_img = image::RgbaImage::from_pixel(8, 8, image::Rgba([r, g, b, a]));
        image::DynamicImage::ImageRgba8(rgba_img)
    }

    #[test]
    fn palette_solid_red() {
        let img = create_solid_image(255, 0, 0, 255);
        let pal = palette_from_image(&img, Some(5), Some(10)).unwrap();
        assert!(!pal.is_empty(), "Palette should not be empty");
        let (r, g, b) = pal[0];
        assert!(r > 200, "Red should dominate, got R={}", r);
        assert!(g < 50, "Green should be low, got G={}", g);
        assert!(b < 50, "Blue should be low, got B={}", b);
    }

    #[test]
    fn dominant_solid_blue() {
        let img = create_solid_image(0, 0, 255, 255);
        let (r, g, b) = dominant_from_image(&img, Some(10)).unwrap();
        assert!(r < 50, "Red should be low, got R={}", r);
        assert!(g < 50, "Green should be low, got G={}", g);
        assert!(b > 200, "Blue should dominate, got B={}", b);
    }

    #[test]
    fn invalid_bytes() {
        let result = get_palette_from_bytes(&[], None, None);
        assert!(matches!(result, Err(ColorThiefError::ImageDecode(_))));
    }

    #[test]
    fn nonexistent_file() {
        let result = get_palette_from_path(Path::new("/nonexistent/file.jpg"), None, None);
        // image::open returns an error for missing files
        assert!(result.is_err());
    }

    #[test]
    fn png_roundtrip_via_bytes() {
        // Build a 4×4 solid-green PNG entirely in memory.

        let img = create_solid_image(0, 128, 0, 255);
        let mut buf = Vec::new();
        {
            let encoder = image::codecs::png::PngEncoder::new(&mut buf);
            let rgba = img.to_rgba8();
            encoder
                .write_image(&rgba.into_raw(), 8, 8, image::ExtendedColorType::Rgba8)
                .unwrap();
        }
        let palette = get_palette_from_bytes(&buf, Some(5), Some(10)).unwrap();
        assert!(!palette.is_empty());
        let (r, g, b) = palette[0];
        assert!(r < 50, "R should be low, got {}", r);
        assert!(g > 100 && g < 160, "G should be ~128, got {}", g);
        assert!(b < 50, "B should be low, got {}", b);
    }

    #[test]
    fn dominant_roundtrip_via_bytes() {
        let img = create_solid_image(200, 50, 50, 255);
        let mut buf = Vec::new();
        let rgba = img.to_rgba8();
        {
            let encoder = image::codecs::png::PngEncoder::new(&mut buf);
            encoder
                .write_image(&rgba.into_raw(), 8, 8, image::ExtendedColorType::Rgba8)
                .unwrap();
        }
        let (r, g, b) = get_dominant_from_bytes(&buf, Some(10)).unwrap();
        assert!(r > 150, "R should dominate, got {}", r);
        assert!(g < 100, "G should be low, got {}", g);
        assert!(b < 100, "B should be low, got {}", b);
    }
}
