//! Thumbnail generation for images, videos, and PDFs.
//!
//! Two backends are available:
//!
//! * **crude** (always available) — uses the `image` crate to resize images,
//!   scans MP4 containers for an embedded `covr` cover-art atom, scans PDF
//!   files for the first `/DCTDecode` (JPEG) image stream, and falls back to a
//!   deterministic colour-gradient placeholder when no embedded image can be
//!   found. Works without ffmpeg or pdfium.
//!
//! * **auto-thumbnail** (cargo feature `auto-thumbnail`) — wraps the
//!   [`auto-thumbnail`](https://crates.io/crates/auto-thumbnail) crate.
//!   Upstream currently exposes image/PDF/video support as an all-or-nothing
//!   dependency set, so enabling this feature pulls in `pdfium-render` and
//!   ffmpeg (`video-rs`) for high-quality PDF/video rasterisation.

use std::path::Path;

use image::{
    DynamicImage, GenericImageView, ImageEncoder,
    codecs::{jpeg::JpegEncoder, png::PngEncoder},
    imageops::FilterType,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use thiserror::Error;

// ── Error type ───────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ThumbnailError {
    #[error("image error: {0}")]
    Image(#[from] image::ImageError),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("unsupported input kind: {0}")]
    Unsupported(String),

    #[error("invalid arguments: {0}")]
    InvalidArgs(String),

    #[error("backend not available: {0}")]
    BackendUnavailable(String),

    #[error("backend failed: {0}")]
    BackendFailed(String),
}

impl From<ThumbnailError> for PyErr {
    fn from(e: ThumbnailError) -> Self {
        PyValueError::new_err(e.to_string())
    }
}

// ── Output format ────────────────────────────────────────────────────────────

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum OutputFormat {
    Jpeg,
    Png,
    Webp,
}

impl OutputFormat {
    pub fn from_str_ci(s: &str) -> Result<Self, ThumbnailError> {
        match s.to_ascii_lowercase().as_str() {
            "jpeg" | "jpg" => Ok(Self::Jpeg),
            "png" => Ok(Self::Png),
            "webp" => Ok(Self::Webp),
            other => Err(ThumbnailError::InvalidArgs(format!(
                "unknown output format {other:?} (expected jpeg | png | webp)"
            ))),
        }
    }

    // NOTE: only consumed by the auto-thumbnail backend (used to pick the
    // suffix for the temp output file). When the `auto-thumbnail` cargo
    // feature is OFF, this method is unreferenced — silence that warning
    // without removing the method, since it's part of the public API.
    #[allow(dead_code)]
    pub fn extension(&self) -> &'static str {
        match self {
            Self::Jpeg => "jpg",
            Self::Png => "png",
            Self::Webp => "webp",
        }
    }
}

// ── Magic-byte input detection ───────────────────────────────────────────────

#[derive(Copy, Clone, Debug, PartialEq, Eq)]
pub enum InputKind {
    Image,
    Video,
    Pdf,
    Unknown,
}

pub fn detect_kind(bytes: &[u8]) -> InputKind {
    if bytes.len() >= 12 && &bytes[0..4] == b"RIFF" && &bytes[8..12] == b"WEBP" {
        return InputKind::Image;
    }
    if bytes.len() >= 8 && &bytes[4..8] == b"ftyp" {
        return InputKind::Video;
    }
    if bytes.starts_with(b"\xFF\xD8\xFF") {
        return InputKind::Image;
    }
    if bytes.starts_with(b"\x89PNG\r\n\x1a\n") {
        return InputKind::Image;
    }
    if bytes.starts_with(b"GIF87a") || bytes.starts_with(b"GIF89a") {
        return InputKind::Image;
    }
    if bytes.starts_with(b"BM") {
        return InputKind::Image;
    }
    if bytes.starts_with(b"%PDF") {
        return InputKind::Pdf;
    }
    // Matroska / WebM
    if bytes.starts_with(b"\x1A\x45\xDF\xA3") {
        return InputKind::Video;
    }
    InputKind::Unknown
}

// ── Encoding ─────────────────────────────────────────────────────────────────

pub fn encode_image(
    img: &DynamicImage,
    format: OutputFormat,
    quality: u8,
) -> Result<Vec<u8>, ThumbnailError> {
    let mut out = Vec::new();
    let (w, h) = img.dimensions();
    match format {
        OutputFormat::Jpeg => {
            // JPEG has no alpha channel — flatten to RGB.
            let rgb = img.to_rgb8();
            let q = quality.clamp(1, 100);
            let encoder = JpegEncoder::new_with_quality(&mut out, q);
            encoder.write_image(rgb.as_raw(), w, h, image::ExtendedColorType::Rgb8)?;
        }
        OutputFormat::Png => {
            let rgba = img.to_rgba8();
            let encoder = PngEncoder::new(&mut out);
            encoder.write_image(rgba.as_raw(), w, h, image::ExtendedColorType::Rgba8)?;
        }
        OutputFormat::Webp => {
            // image 0.25's built-in WebP encoder is lossless-only; quality is ignored.
            let rgba = img.to_rgba8();
            let encoder = image::codecs::webp::WebPEncoder::new_lossless(&mut out);
            encoder.write_image(rgba.as_raw(), w, h, image::ExtendedColorType::Rgba8)?;
        }
    }
    Ok(out)
}

pub fn fit_within(img: DynamicImage, max_w: u32, max_h: u32) -> DynamicImage {
    let max_w = max_w.max(1);
    let max_h = max_h.max(1);
    let (w, h) = img.dimensions();
    if w <= max_w && h <= max_h {
        return img;
    }
    img.resize(max_w, max_h, FilterType::Lanczos3)
}

// ── Crude placeholder generation ─────────────────────────────────────────────

fn deterministic_color(bytes: &[u8]) -> [u8; 3] {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};
    let mut hasher = DefaultHasher::new();
    bytes.len().hash(&mut hasher);
    let take = bytes.len().min(4096);
    bytes[..take].hash(&mut hasher);
    let h = hasher.finish();
    [
        (h & 0xff) as u8,
        ((h >> 8) & 0xff) as u8,
        ((h >> 16) & 0xff) as u8,
    ]
}

pub fn placeholder_image(width: u32, height: u32, color: [u8; 3]) -> DynamicImage {
    let w = width.max(1);
    let h = height.max(1);
    let mut img = image::RgbaImage::new(w, h);
    let [r, g, b] = color;
    let denom = (w + h).max(1) as f32;
    for (x, y, px) in img.enumerate_pixels_mut() {
        let t = ((x + y) as f32) / denom;
        let lighten = (t * 80.0) as i16;
        let rr = (r as i16 + lighten).clamp(0, 255) as u8;
        let gg = (g as i16 + lighten).clamp(0, 255) as u8;
        let bb = (b as i16 + lighten).clamp(0, 255) as u8;
        *px = image::Rgba([rr, gg, bb, 255]);
    }
    DynamicImage::ImageRgba8(img)
}

// ── Crude container-aware extraction ─────────────────────────────────────────

/// Walk MP4 box structure: returns the (start, end) byte range of the *payload*
/// of the first immediate child atom of type `wanted`.
fn find_atom(buf: &[u8], wanted: &[u8; 4]) -> Option<(usize, usize)> {
    let mut pos = 0;
    while pos + 8 <= buf.len() {
        let size = u32::from_be_bytes(buf[pos..pos + 4].try_into().ok()?) as usize;
        let typ = &buf[pos + 4..pos + 8];
        let (header_len, end) = if size == 1 {
            if pos + 16 > buf.len() {
                return None;
            }
            let big = u64::from_be_bytes(buf[pos + 8..pos + 16].try_into().ok()?) as usize;
            (16usize, pos.checked_add(big)?)
        } else if size == 0 {
            (8usize, buf.len())
        } else if size < 8 {
            return None;
        } else {
            (8usize, pos.checked_add(size)?)
        };
        if end > buf.len() || end <= pos + header_len {
            return None;
        }
        if typ == wanted {
            return Some((pos + header_len, end));
        }
        pos = end;
    }
    None
}

fn descend<'a>(mut buf: &'a [u8], path: &[&[u8; 4]]) -> Option<&'a [u8]> {
    for atom_type in path {
        let (s, e) = find_atom(buf, atom_type)?;
        buf = &buf[s..e];
        // The `meta` atom carries a 4-byte version+flags before its children
        // (FullBox).
        if atom_type == &b"meta" {
            if buf.len() < 4 {
                return None;
            }
            buf = &buf[4..];
        }
    }
    Some(buf)
}

/// Extract iTunes-style cover art from an MP4 file (atom path
/// `moov/udta/meta/ilst/covr/data`). Returns the embedded JPEG/PNG bytes if
/// present.
pub fn extract_mp4_cover(bytes: &[u8]) -> Option<Vec<u8>> {
    let ilst = descend(bytes, &[b"moov", b"udta", b"meta", b"ilst"])?;
    let (covr_s, covr_e) = find_atom(ilst, b"covr")?;
    let covr = &ilst[covr_s..covr_e];
    let (data_s, data_e) = find_atom(covr, b"data")?;
    let data = &covr[data_s..data_e];
    // `data` atom payload is: 4-byte type-indicator + 4-byte locale + value
    if data.len() <= 8 {
        return None;
    }
    Some(data[8..].to_vec())
}

fn find_subseq(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || haystack.len() < needle.len() {
        return None;
    }
    haystack.windows(needle.len()).position(|w| w == needle)
}

/// Scan a PDF file for the first JPEG (`/DCTDecode`) image XObject stream and
/// return the JPEG byte range. Crude but works for many PDFs that contain a
/// scanned page or photographic illustration.
pub fn extract_pdf_first_jpeg(bytes: &[u8]) -> Option<Vec<u8>> {
    let needle = b"/DCTDecode";
    let mut search_from = 0usize;
    while let Some(rel) = find_subseq(&bytes[search_from..], needle) {
        let i = search_from + rel;
        let after = i + needle.len();
        // Find the start of the stream payload within a small window after the
        // filter declaration.
        let window_end = (after + 4096).min(bytes.len());
        if let Some(stream_rel) = find_subseq(&bytes[after..window_end], b"stream") {
            let mut k = after + stream_rel + b"stream".len();
            if bytes.get(k) == Some(&b'\r') {
                k += 1;
            }
            if bytes.get(k) == Some(&b'\n') {
                k += 1;
            }
            // Verify JPEG SOI marker.
            if bytes.get(k) == Some(&0xFF) && bytes.get(k + 1) == Some(&0xD8) {
                // Find JPEG EOI (FF D9).
                let mut e = k + 2;
                while e + 1 < bytes.len() {
                    if bytes[e] == 0xFF && bytes[e + 1] == 0xD9 {
                        return Some(bytes[k..=e + 1].to_vec());
                    }
                    e += 1;
                }
                // Fallback: stop at endstream marker.
                if let Some(end_rel) = find_subseq(&bytes[k..], b"endstream") {
                    let mut end = k + end_rel;
                    while end > k && (bytes[end - 1] == b'\n' || bytes[end - 1] == b'\r') {
                        end -= 1;
                    }
                    return Some(bytes[k..end].to_vec());
                }
            }
        }
        search_from = after;
    }
    None
}

// ── Crude pipeline ───────────────────────────────────────────────────────────

pub fn crude_thumbnail_from_bytes(
    bytes: &[u8],
    width: u32,
    height: u32,
    quality: u8,
    format: OutputFormat,
) -> Result<Vec<u8>, ThumbnailError> {
    let kind = detect_kind(bytes);
    let img = match kind {
        InputKind::Image => image::load_from_memory(bytes)?,
        InputKind::Video => {
            match extract_mp4_cover(bytes).and_then(|j| image::load_from_memory(&j).ok()) {
                Some(i) => i,
                None => placeholder_image(width, height, deterministic_color(bytes)),
            }
        }
        InputKind::Pdf => {
            match extract_pdf_first_jpeg(bytes).and_then(|j| image::load_from_memory(&j).ok()) {
                Some(i) => i,
                None => placeholder_image(width, height, deterministic_color(bytes)),
            }
        }
        InputKind::Unknown => {
            return Err(ThumbnailError::Unsupported(
                "could not detect input format from magic bytes".to_string(),
            ));
        }
    };
    let resized = fit_within(img, width, height);
    encode_image(&resized, format, quality)
}

pub fn crude_thumbnail_from_path(
    path: &Path,
    width: u32,
    height: u32,
    quality: u8,
    format: OutputFormat,
) -> Result<Vec<u8>, ThumbnailError> {
    let bytes = std::fs::read(path)?;
    crude_thumbnail_from_bytes(&bytes, width, height, quality, format)
}

// ── auto-thumbnail backend (optional) ────────────────────────────────────────

#[cfg(feature = "auto-thumbnail")]
pub mod auto_backend {
    use super::*;
    use auto_thumbnail::{ThumbnailSize, Thumbnailer};

    fn ext_for_input(bytes: &[u8]) -> &'static str {
        match detect_kind(bytes) {
            InputKind::Image => {
                if bytes.starts_with(b"\xFF\xD8\xFF") {
                    "jpg"
                } else if bytes.starts_with(b"\x89PNG") {
                    "png"
                } else if bytes.starts_with(b"GIF") {
                    "gif"
                } else if bytes.len() >= 12 && &bytes[8..12] == b"WEBP" {
                    "webp"
                } else if bytes.starts_with(b"BM") {
                    "bmp"
                } else {
                    "bin"
                }
            }
            InputKind::Video => {
                if bytes.len() >= 8 && &bytes[4..8] == b"ftyp" {
                    "mp4"
                } else if bytes.starts_with(b"\x1A\x45\xDF\xA3") {
                    "mkv"
                } else {
                    "bin"
                }
            }
            InputKind::Pdf => "pdf",
            InputKind::Unknown => "bin",
        }
    }

    pub fn create_to_path(
        input: &Path,
        output: &Path,
        width: u32,
        height: u32,
        quality: u8,
    ) -> Result<(), ThumbnailError> {
        let q = quality.clamp(1, 100);
        let t = Thumbnailer::new(ThumbnailSize::Custom((width.max(1), height.max(1))), q);
        t.create_thumbnail(input, output)
            .map_err(|e| ThumbnailError::BackendFailed(format!("auto-thumbnail: {e}")))
    }

    pub fn create_from_path(
        input: &Path,
        width: u32,
        height: u32,
        quality: u8,
        format: OutputFormat,
    ) -> Result<Vec<u8>, ThumbnailError> {
        let suffix = format!(".{}", format.extension());
        // Build a temp output path, then drop the handle so auto-thumbnail can
        // re-create the file via `File::create`.
        let tmp = tempfile::Builder::new()
            .prefix("thumbleweed-out-")
            .suffix(&suffix)
            .tempfile()?;
        let tmp_path = tmp.path().to_path_buf();
        drop(tmp);
        let result = create_to_path(input, &tmp_path, width, height, quality);
        let bytes = match result {
            Ok(()) => std::fs::read(&tmp_path)?,
            Err(e) => {
                let _ = std::fs::remove_file(&tmp_path);
                return Err(e);
            }
        };
        let _ = std::fs::remove_file(&tmp_path);
        Ok(bytes)
    }

    pub fn create_from_bytes(
        bytes: &[u8],
        width: u32,
        height: u32,
        quality: u8,
        format: OutputFormat,
    ) -> Result<Vec<u8>, ThumbnailError> {
        let suffix = format!(".{}", ext_for_input(bytes));
        let in_tmp = tempfile::Builder::new()
            .prefix("thumbleweed-in-")
            .suffix(&suffix)
            .tempfile()?;
        std::fs::write(in_tmp.path(), bytes)?;
        let in_path = in_tmp.path().to_path_buf();
        create_from_path(&in_path, width, height, quality, format)
    }
}

// ── Backend introspection ────────────────────────────────────────────────────

pub fn available_backends() -> Vec<&'static str> {
    // NOTE: `mut` is required only when an optional cargo feature pushes onto
    // the list. When all such features are disabled the binding is unused, so
    // we suppress the lint without changing semantics.
    #[allow(unused_mut)]
    let mut v = vec!["crude"];
    #[cfg(feature = "auto-thumbnail")]
    {
        v.push("auto-thumbnail");
    }
    v
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detect_jpeg_magic() {
        assert_eq!(detect_kind(b"\xFF\xD8\xFF\xE0xxxxxxxx"), InputKind::Image);
    }

    #[test]
    fn detect_png_magic() {
        assert_eq!(detect_kind(b"\x89PNG\r\n\x1a\nxxxx"), InputKind::Image);
    }

    #[test]
    fn detect_pdf_magic() {
        assert_eq!(detect_kind(b"%PDF-1.4\n..."), InputKind::Pdf);
    }

    #[test]
    fn detect_mp4_magic() {
        // size=0x20, type='ftyp', brand='mp42'
        assert_eq!(
            detect_kind(b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00"),
            InputKind::Video
        );
    }

    #[test]
    fn detect_unknown() {
        assert_eq!(detect_kind(b"garbage"), InputKind::Unknown);
    }

    #[test]
    fn placeholder_dimensions() {
        let img = placeholder_image(48, 64, [10, 20, 30]);
        assert_eq!(img.dimensions(), (48, 64));
    }

    #[test]
    fn placeholder_deterministic() {
        let a = deterministic_color(b"hello world");
        let b = deterministic_color(b"hello world");
        assert_eq!(a, b);
    }

    #[test]
    fn output_format_parsing() {
        assert_eq!(
            OutputFormat::from_str_ci("JPG").unwrap(),
            OutputFormat::Jpeg
        );
        assert_eq!(OutputFormat::from_str_ci("png").unwrap(), OutputFormat::Png);
        assert_eq!(
            OutputFormat::from_str_ci("WebP").unwrap(),
            OutputFormat::Webp
        );
        assert!(OutputFormat::from_str_ci("tiff").is_err());
    }

    #[test]
    fn crude_image_roundtrip_jpeg() {
        // build a 100x50 RGB image and encode as PNG
        let mut buf = Vec::new();
        let img = image::RgbaImage::from_pixel(100, 50, image::Rgba([200, 50, 50, 255]));
        let dyn_img = DynamicImage::ImageRgba8(img);
        {
            let enc = PngEncoder::new(&mut buf);
            let rgba = dyn_img.to_rgba8();
            enc.write_image(rgba.as_raw(), 100, 50, image::ExtendedColorType::Rgba8)
                .unwrap();
        }
        let thumb = crude_thumbnail_from_bytes(&buf, 32, 32, 80, OutputFormat::Jpeg).unwrap();
        assert!(thumb.starts_with(b"\xFF\xD8\xFF"));
    }

    #[test]
    fn crude_unknown_input_errors() {
        let err = crude_thumbnail_from_bytes(b"garbage", 32, 32, 80, OutputFormat::Png)
            .err()
            .unwrap();
        assert!(matches!(err, ThumbnailError::Unsupported(_)));
    }

    #[test]
    fn pdf_extractor_returns_none_for_garbage() {
        assert!(extract_pdf_first_jpeg(b"%PDF-1.4 nothing useful here").is_none());
    }

    #[test]
    fn mp4_extractor_returns_none_for_garbage() {
        assert!(extract_mp4_cover(b"\x00\x00\x00\x20ftypmp42").is_none());
    }
}
