// JS wrapper around frontend/wasm-thumbleweed (C ABI, no glue tooling).
// The module has no imports, so a plain WebAssembly.instantiate is enough.

export type WasmApi = {
  alloc: (len: number) => number;
  free: (ptr: number, len: number) => void;
  thumbhashEncode: (
    w: number,
    h: number,
    rgbaPtr: number,
    rgbaLen: number,
    outPtr: number,
  ) => number;
  thumbhashDecode: (hashPtr: number, hashLen: number, outPtr: number) => number;
  thumbhashAverage: (hashPtr: number, hashLen: number, outPtr: number) => number;
  blurhashEncode: (
    rgbaPtr: number,
    rgbaLen: number,
    w: number,
    h: number,
    cx: number,
    cy: number,
    outPtr: number,
    outCap: number,
  ) => number;
  blurhashDecode: (
    hashPtr: number,
    hashLen: number,
    w: number,
    h: number,
    outPtr: number,
    outCap: number,
  ) => number;
  memory: WebAssembly.Memory;
};

// Raw symbol names exported by wasm-thumbleweed/src/lib.rs. Keep in sync with
// that crate's `#[unsafe(no_mangle)] pub extern "C" fn tw_*` definitions.
type RawExports = {
  memory: WebAssembly.Memory;
  tw_alloc: (len: number) => number;
  tw_free: (ptr: number, len: number) => void;
  tw_thumbhash_encode: WasmApi["thumbhashEncode"];
  tw_thumbhash_decode: WasmApi["thumbhashDecode"];
  tw_thumbhash_average: WasmApi["thumbhashAverage"];
  tw_blurhash_encode: WasmApi["blurhashEncode"];
  tw_blurhash_decode: WasmApi["blurhashDecode"];
};

const REQUIRED_EXPORTS = [
  "memory",
  "tw_alloc",
  "tw_free",
  "tw_thumbhash_encode",
  "tw_thumbhash_decode",
  "tw_thumbhash_average",
  "tw_blurhash_encode",
  "tw_blurhash_decode",
] as const;

/** Map the module's `tw_*` C-ABI symbols onto the camelCase wrapper API. */
function bindExports(exports: Record<string, unknown>): WasmApi {
  const missing = REQUIRED_EXPORTS.filter((name) => !(name in exports));
  if (missing.length > 0) {
    throw new Error(
      `wasm module is missing exports: ${missing.join(", ")} — rebuild it with \`bun run build:wasm\``,
    );
  }
  const e = exports as unknown as RawExports;
  return {
    memory: e.memory,
    alloc: e.tw_alloc,
    free: e.tw_free,
    thumbhashEncode: e.tw_thumbhash_encode,
    thumbhashDecode: e.tw_thumbhash_decode,
    thumbhashAverage: e.tw_thumbhash_average,
    blurhashEncode: e.tw_blurhash_encode,
    blurhashDecode: e.tw_blurhash_decode,
  };
}

let instance: WasmApi | null = null;
let loading: Promise<WasmApi> | null = null;

const THUMBHASH_OUT_CAP = 32;
const THUMBHASH_DECODE_CAP = 8 + 32 * 32 * 4;

export async function loadWasm(): Promise<WasmApi> {
  if (instance) return instance;
  if (!loading) {
    loading = (async () => {
      const res = await fetch("/wasm/thumbleweed.wasm");
      if (!res.ok) throw new Error(`failed to fetch wasm module (${res.status})`);
      const mod = await WebAssembly.compile(await res.arrayBuffer());
      const inst = await WebAssembly.instantiate(mod, {});
      const e = bindExports(inst.exports as Record<string, unknown>);
      instance = e;
      return e;
    })();
    loading.catch(() => {
      loading = null;
    });
  }
  return loading;
}

function copyIn(wasm: WasmApi, bytes: Uint8Array): { ptr: number; len: number } {
  const len = bytes.byteLength;
  const ptr = wasm.alloc(len || 1);
  new Uint8Array(wasm.memory.buffer, ptr, len).set(bytes);
  return { ptr, len };
}

/** Encode RGBA pixels (w*h*4) to ThumbHash bytes. Returns null on error. */
export function thumbhashEncode(
  wasm: WasmApi,
  rgba: Uint8Array,
  w: number,
  h: number,
): Uint8Array | null {
  const input = copyIn(wasm, rgba);
  const outPtr = wasm.alloc(THUMBHASH_OUT_CAP);
  try {
    const n = wasm.thumbhashEncode(w, h, input.ptr, input.len, outPtr);
    if (n <= 0) return null;
    return new Uint8Array(wasm.memory.buffer, outPtr, n).slice();
  } finally {
    wasm.free(input.ptr, input.len || 1);
    wasm.free(outPtr, THUMBHASH_OUT_CAP);
  }
}

/** Decode ThumbHash bytes to { w, h, rgba }. Returns null on error. */
export function thumbhashDecode(
  wasm: WasmApi,
  hash: Uint8Array,
): { w: number; h: number; rgba: Uint8Array } | null {
  const input = copyIn(wasm, hash);
  const outPtr = wasm.alloc(THUMBHASH_DECODE_CAP);
  try {
    const n = wasm.thumbhashDecode(input.ptr, input.len, outPtr);
    if (n <= 8) return null;
    const view = new DataView(wasm.memory.buffer, outPtr, n);
    const w = view.getUint32(0, true);
    const h = view.getUint32(4, true);
    const rgba = new Uint8Array(wasm.memory.buffer, outPtr + 8, n - 8).slice();
    return { w, h, rgba };
  } finally {
    wasm.free(input.ptr, input.len || 1);
    wasm.free(outPtr, THUMBHASH_DECODE_CAP);
  }
}

/** Average colour of a ThumbHash as [r, g, b, a] (0–255, alpha-scaled). */
export function thumbhashAverage(wasm: WasmApi, hash: Uint8Array): [number, number, number, number] | null {
  const input = copyIn(wasm, hash);
  const outPtr = wasm.alloc(4);
  try {
    const n = wasm.thumbhashAverage(input.ptr, input.len, outPtr);
    if (n !== 4) return null;
    const out = new Uint8Array(wasm.memory.buffer, outPtr, 4);
    return [out[0], out[1], out[2], out[3]];
  } finally {
    wasm.free(input.ptr, input.len || 1);
    wasm.free(outPtr, 4);
  }
}

/** Encode RGBA pixels to a BlurHash string. Returns null on error. */
export function blurhashEncode(
  wasm: WasmApi,
  rgba: Uint8Array,
  w: number,
  h: number,
  cx = 4,
  cy = 3,
): string | null {
  const input = copyIn(wasm, rgba);
  const outCap = 4 + 81 * 2;
  const outPtr = wasm.alloc(outCap);
  try {
    const n = wasm.blurhashEncode(input.ptr, input.len, w, h, cx, cy, outPtr, outCap);
    if (n <= 0) return null;
    const bytes = new Uint8Array(wasm.memory.buffer, outPtr, n);
    return new TextDecoder("ascii").decode(bytes);
  } finally {
    wasm.free(input.ptr, input.len || 1);
    wasm.free(outPtr, outCap);
  }
}

/** Decode a BlurHash string to RGBA pixels at width x height. */
export function blurhashDecode(
  wasm: WasmApi,
  hash: string,
  w: number,
  h: number,
): Uint8Array | null {
  const input = copyIn(wasm, new TextEncoder().encode(hash));
  const outCap = w * h * 4;
  const outPtr = wasm.alloc(outCap);
  try {
    const n = wasm.blurhashDecode(input.ptr, input.len, w, h, outPtr, outCap);
    if (n !== outCap) return null;
    return new Uint8Array(wasm.memory.buffer, outPtr, n).slice();
  } finally {
    wasm.free(input.ptr, input.len || 1);
    wasm.free(outPtr, outCap);
  }
}

/** Draw RGBA bytes onto a canvas context at native pixel size. */
export function putRgba(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
  rgba: Uint8Array,
  w: number,
  h: number,
): void {
  const imageData = ctx.createImageData(w, h);
  imageData.data.set(rgba.subarray(0, w * h * 4));
  ctx.putImageData(imageData, 0, 0);
}
