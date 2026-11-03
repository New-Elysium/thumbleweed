//! thumbleweed-wasm — C-ABI exports of the ThumbHash + BlurHash cores for the
//! website playground. Loaded directly via `WebAssembly.instantiate` with no
//! glue tooling; see frontend/app/lib/wasm.ts for the JS wrapper.
//!
//! Conventions:
//! - Every function returns a byte count on success, or 0 on error.
//! - Callers allocate scratch buffers with `tw_alloc` and free them with `tw_free`.

mod blurhash;
mod thumbhash;

use std::slice;

/// Allocate `len` bytes, returning a pointer (or null on allocation failure).
#[unsafe(no_mangle)]
pub extern "C" fn tw_alloc(len: usize) -> *mut u8 {
    if len == 0 {
        return std::ptr::null_mut();
    }
    let mut buf = Vec::with_capacity(len);
    let ptr = buf.as_mut_ptr();
    std::mem::forget(buf);
    ptr
}

/// Free a buffer of `len` bytes previously returned by `tw_alloc` (or written
/// to via tw_* functions that allocate internally — see notes in the JS
/// wrapper; only memory obtained from `tw_alloc` may be freed here).
#[unsafe(no_mangle)]
pub extern "C" fn tw_free(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
    unsafe {
        drop(Vec::from_raw_parts(ptr, 0, len));
    }
}

/// Encode raw RGBA pixels to a ThumbHash. `out_ptr` must have capacity >= 32.
/// Returns the hash byte count, or 0 on error.
#[unsafe(no_mangle)]
pub extern "C" fn tw_thumbhash_encode(
    w: usize,
    h: usize,
    rgba_ptr: *const u8,
    rgba_len: usize,
    out_ptr: *mut u8,
) -> usize {
    if rgba_ptr.is_null() || out_ptr.is_null() {
        return 0;
    }
    let rgba = unsafe { slice::from_raw_parts(rgba_ptr, rgba_len) };
    match thumbhash::rgba_to_thumb_hash(w, h, rgba) {
        Ok(hash) => {
            let n = hash.len();
            unsafe {
                std::ptr::copy_nonoverlapping(hash.as_ptr(), out_ptr, n);
            }
            n
        }
        Err(_) => 0,
    }
}

/// Decode a ThumbHash into `out_ptr` (capacity >= 8 + 32*32*4).
/// Layout: u32 LE width, u32 LE height, then `width * height * 4` RGBA bytes.
/// Returns total bytes written, or 0 on error.
#[unsafe(no_mangle)]
pub extern "C" fn tw_thumbhash_decode(
    hash_ptr: *const u8,
    hash_len: usize,
    out_ptr: *mut u8,
) -> usize {
    if hash_ptr.is_null() || out_ptr.is_null() {
        return 0;
    }
    let hash = unsafe { slice::from_raw_parts(hash_ptr, hash_len) };
    match thumbhash::thumb_hash_to_rgba(hash) {
        Ok((w, h, rgba)) => {
            let total = 8 + rgba.len();
            unsafe {
                std::ptr::copy_nonoverlapping(&(w as u32).to_le_bytes()[0], out_ptr, 4);
                std::ptr::copy_nonoverlapping(&(h as u32).to_le_bytes()[0], out_ptr.add(4), 4);
                std::ptr::copy_nonoverlapping(rgba.as_ptr(), out_ptr.add(8), rgba.len());
            }
            total
        }
        Err(_) => 0,
    }
}

/// Average colour of a ThumbHash. Writes r, g, b, a (u8, alpha-scaled) to
/// `out_ptr`. Returns 4 on success, 0 on error.
#[unsafe(no_mangle)]
pub extern "C" fn tw_thumbhash_average(
    hash_ptr: *const u8,
    hash_len: usize,
    out_ptr: *mut u8,
) -> usize {
    if hash_ptr.is_null() || out_ptr.is_null() {
        return 0;
    }
    let hash = unsafe { slice::from_raw_parts(hash_ptr, hash_len) };
    match thumbhash::thumb_hash_to_average_rgba(hash) {
        Ok((r, g, b, a)) => {
            unsafe {
                *out_ptr = (r * 255.0).round() as u8;
                *out_ptr.add(1) = (g * 255.0).round() as u8;
                *out_ptr.add(2) = (b * 255.0).round() as u8;
                *out_ptr.add(3) = (a * 255.0).round() as u8;
            }
            4
        }
        Err(_) => 0,
    }
}

/// Encode raw RGBA pixels to a BlurHash string (ASCII, written to `out_ptr`).
/// Returns the hash character count, or 0 on error.
#[unsafe(no_mangle)]
pub extern "C" fn tw_blurhash_encode(
    rgba_ptr: *const u8,
    rgba_len: usize,
    w: usize,
    h: usize,
    cx: usize,
    cy: usize,
    out_ptr: *mut u8,
    out_cap: usize,
) -> usize {
    if rgba_ptr.is_null() || out_ptr.is_null() {
        return 0;
    }
    let rgba = unsafe { slice::from_raw_parts(rgba_ptr, rgba_len) };
    match blurhash::encode(rgba, cx, cy, w, h) {
        Ok(hash) => {
            let n = hash.len().min(out_cap);
            unsafe {
                std::ptr::copy_nonoverlapping(hash.as_ptr(), out_ptr, n);
            }
            n
        }
        Err(_) => 0,
    }
}

/// Decode a BlurHash string to RGBA. `out_ptr` must have capacity >= w*h*4.
/// Returns bytes written, or 0 on error.
#[unsafe(no_mangle)]
pub extern "C" fn tw_blurhash_decode(
    hash_ptr: *const u8,
    hash_len: usize,
    w: usize,
    h: usize,
    out_ptr: *mut u8,
    out_cap: usize,
) -> usize {
    if hash_ptr.is_null() || out_ptr.is_null() {
        return 0;
    }
    let hash_bytes = unsafe { slice::from_raw_parts(hash_ptr, hash_len) };
    let hash = match std::str::from_utf8(hash_bytes) {
        Ok(s) => s,
        Err(_) => return 0,
    };
    match blurhash::decode(hash, w, h) {
        Ok(pixels) => {
            if pixels.len() > out_cap {
                return 0;
            }
            unsafe {
                std::ptr::copy_nonoverlapping(pixels.as_ptr(), out_ptr, pixels.len());
            }
            pixels.len()
        }
        Err(_) => 0,
    }
}

#[cfg(test)]
mod tests {
    use super::blurhash;
    use super::thumbhash;

    #[test]
    fn thumbhash_roundtrip() {
        let (w, h) = (16usize, 16usize);
        let mut rgba = vec![0u8; w * h * 4];
        for (i, px) in rgba.as_chunks_mut::<4>().0.iter_mut().enumerate() {
            px[0] = (i % 255) as u8;
            px[1] = 80;
            px[2] = 40;
            px[3] = 255;
        }
        let hash = thumbhash::rgba_to_thumb_hash(w, h, &rgba).unwrap();
        assert!((5..=32).contains(&hash.len()));
        let (dw, dh, _decoded) = thumbhash::thumb_hash_to_rgba(&hash).unwrap();
        assert!(dw > 0 && dh > 0 && dw <= 32 && dh <= 32);
    }

    #[test]
    fn blurhash_roundtrip() {
        let (w, h) = (16usize, 16usize);
        let mut rgba = vec![0u8; w * h * 4];
        for px in rgba.as_chunks_mut::<4>().0 {
            px.copy_from_slice(&[200, 120, 60, 255]);
        }
        let hash = blurhash::encode(&rgba, 4, 3, w, h).unwrap();
        assert_eq!(hash.len(), 4 + 4 * 3 * 2);
        let decoded = blurhash::decode(&hash, w, h).unwrap();
        assert_eq!(decoded.len(), w * h * 4);
    }
}
