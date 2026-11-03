"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  blurhashDecode,
  blurhashEncode,
  loadWasm,
  putRgba,
  thumbhashAverage,
  thumbhashDecode,
  thumbhashEncode,
  type WasmApi,
} from "../lib/wasm";

type Result = {
  originalUrl: string;
  thumbUrl: string;
  blurUrl: string;
  thumbBytes: number;
  thumbBase64: string;
  blurString: string;
  average: [number, number, number, number];
  encodeMs: number;
  width: number;
  height: number;
};

const MAX_DIM = 64; // downscale before encoding (ThumbHash allows up to 100)

async function fileToImageData(file: File): Promise<{ data: ImageData; url: string }> {
  const url = URL.createObjectURL(file);
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_DIM / Math.max(bitmap.width, bitmap.height));
  const w = Math.max(1, Math.round(bitmap.width * scale));
  const h = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas 2d context unavailable");
  ctx.drawImage(bitmap, 0, 0, w, h);
  bitmap.close();
  return { data: ctx.getImageData(0, 0, w, h), url };
}

function rgbaToCanvasUrl(rgba: Uint8Array, w: number, h: number): string {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas 2d context unavailable");
  putRgba(ctx, rgba, w, h);
  return canvas.toDataURL("image/png");
}

export default function Playground() {
  const [wasm, setWasm] = useState<WasmApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadWasm()
      .then(setWasm)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "failed to load wasm"));
  }, []);

  const run = useCallback(
    async (file: File) => {
      if (!wasm) return;
      setBusy(true);
      setError(null);
      try {
        const { data, url } = await fileToImageData(file);
        const t0 = performance.now();
        const pixels = new Uint8Array(data.data);

        const hash = thumbhashEncode(wasm, pixels, data.width, data.height);
        if (!hash) throw new Error("ThumbHash encode failed");
        const decoded = thumbhashDecode(wasm, hash);
        if (!decoded) throw new Error("ThumbHash decode failed");
        const average = thumbhashAverage(wasm, hash);
        const blurString = blurhashEncode(wasm, pixels, data.width, data.height, 4, 3);
        if (!blurString) throw new Error("BlurHash encode failed");
        const blurRgba = blurhashDecode(wasm, blurString, 32, 32);
        if (!blurRgba) throw new Error("BlurHash decode failed");

        const encodeMs = performance.now() - t0;
        const thumbBase64 =
          typeof btoa === "function"
            ? btoa(Array.from(hash, (b) => String.fromCharCode(b)).join(""))
            : "";

        setResult({
          originalUrl: url,
          thumbUrl: rgbaToCanvasUrl(decoded.rgba, decoded.w, decoded.h),
          blurUrl: rgbaToCanvasUrl(blurRgba, 32, 32),
          thumbBytes: hash.length,
          thumbBase64,
          blurString,
          average: average ?? [0, 0, 0, 0],
          encodeMs,
          width: data.width,
          height: data.height,
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "something went wrong");
      } finally {
        setBusy(false);
      }
    },
    [wasm],
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void run(file);
  };

  const [r, g, b] = result?.average ?? [0, 0, 0, 0];

  return (
    <section id="playground" className="relative py-20">
      <div className="wood-panel -skew-y-1 absolute inset-0" aria-hidden="true" />
      <div className="relative z-10 mx-auto max-w-6xl px-4 py-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
          className="mb-10 max-w-2xl"
        >
          <p className="font-mono text-xs font-medium tracking-[0.2em] uppercase text-accent">
            Live · runs in your browser
          </p>
          <h2 className="font-display mt-2 text-3xl font-semibold tracking-tight text-[#efe3cc] sm:text-4xl">
            The Rust core, compiled to WebAssembly
          </h2>
          <p className="mt-3 text-[#efe3cc]/70">
            This playground runs the <em>actual</em> ThumbHash and BlurHash algorithms from
            thumbleweed — the same pure-Rust code shipped in the Python wheel, cross-compiled to a
            52&nbsp;KB <code className="font-mono text-accent">.wasm</code> module. Nothing is sent
            to a server.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="rounded-box bg-base-100 p-4 shadow-xl ring-1 ring-base-300 sm:p-6"
        >
          {!wasm && !error && (
            <div className="flex items-center justify-center gap-3 py-16 text-base-content/60">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 4, ease: "linear" }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/thumbleweed-mark-animated.svg" alt="" className="size-10" />
              </motion.div>
              Loading the Rust module…
            </div>
          )}
          {error && (
            <div className="alert alert-error mx-auto max-w-md">
              <span>{error}</span>
            </div>
          )}
          {wasm && (
            <>
              <div
                role="button"
                tabIndex={0}
                onClick={() => inputRef.current?.click()}
                onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-box border-2 border-dashed p-10 text-center transition-colors ${
                  dragging
                    ? "border-primary bg-primary/5"
                    : "border-base-300 hover:border-primary/50 hover:bg-base-200/50"
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void run(file);
                    e.target.value = "";
                  }}
                />
                <motion.div animate={busy ? { rotate: 360 } : { rotate: 0 }} transition={busy ? { repeat: Infinity, duration: 1, ease: "linear" } : {}}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src="/thumbleweed.svg" alt="" className="size-12" />
                </motion.div>
                <p className="font-medium">
                  {busy ? "Stamping hashes…" : "Drop an image here, or click to pick one"}
                </p>
                <p className="text-sm text-base-content/60">
                  Encoded locally at ≤64 px — ThumbHash caps input at 100×100
                </p>
              </div>

              <AnimatePresence>
                {result && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <div className="mt-6 grid gap-4 lg:grid-cols-3">
                      {[
                        { title: "Original", src: result.originalUrl, sub: `${result.width}×${result.height} input` },
                        { title: "ThumbHash", src: result.thumbUrl, sub: "decoded from hash bytes", pixel: true },
                        { title: "BlurHash", src: result.blurUrl, sub: "decoded at 32×32", pixel: true },
                      ].map((img, i) => (
                        <motion.figure
                          key={img.title}
                          initial={{ opacity: 0, scale: 0.94 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: i * 0.12, duration: 0.4 }}
                          className="rounded-box overflow-hidden bg-base-200 ring-1 ring-base-300"
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={img.src}
                            alt={img.title}
                            className={`aspect-square w-full bg-[repeating-conic-gradient(#d9cba6_0%_25%,#ece2cb_0%_50%)] bg-[length:16px_16px] object-contain ${img.pixel ? "pixelated" : ""}`}
                          />
                          <figcaption className="flex items-center justify-between px-3 py-2 text-sm">
                            <span className="font-medium">{img.title}</span>
                            <span className="text-xs text-base-content/60">{img.sub}</span>
                          </figcaption>
                        </motion.figure>
                      ))}
                    </div>

                    <motion.div
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.35, duration: 0.4 }}
                      className="mt-4 grid gap-3 md:grid-cols-2"
                    >
                      <div className="stitch rounded-box bg-base-100 p-3">
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="font-medium">ThumbHash bytes</span>
                          <span className="badge badge-primary badge-sm font-mono">{result.thumbBytes} B</span>
                        </div>
                        <code className="block truncate rounded bg-base-200 px-2 py-1.5 font-mono text-xs text-base-content/80">
                          base64: {result.thumbBase64}
                        </code>
                      </div>
                      <div className="stitch rounded-box bg-base-100 p-3">
                        <div className="mb-1 flex items-center justify-between text-sm">
                          <span className="font-medium">BlurHash string</span>
                          <span className="badge badge-secondary badge-sm font-mono">{result.blurString.length} chars</span>
                        </div>
                        <code className="block truncate rounded bg-base-200 px-2 py-1.5 font-mono text-xs text-base-content/80">
                          {result.blurString}
                        </code>
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.45, duration: 0.4 }}
                      className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-box bg-base-200/60 px-4 py-3 text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="size-5 rounded-full ring-2 ring-base-100 ring-offset-1 ring-offset-base-300"
                          style={{ backgroundColor: `rgb(${r} ${g} ${b})` }}
                        />
                        <span className="font-mono text-xs text-base-content/70">
                          average_rgba() → rgb({r}, {g}, {b})
                        </span>
                      </div>
                      <span className="font-mono text-xs text-secondary">
                        encoded + decoded both hashes in {result.encodeMs.toFixed(1)} ms — in wasm
                      </span>
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </motion.div>
      </div>
    </section>
  );
}
