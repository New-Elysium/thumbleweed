"use client";

import { motion } from "framer-motion";

const subsystems = [
  {
    name: "ThumbHash",
    tagline: "Compact, high-fidelity placeholders",
    body: "5–32 byte hashes with alpha support. Store one tiny blob per image and render blurry-but-faithful previews instantly.",
    replaces: ["thumbhash", "fast-thumbhash"],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-7">
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M3 15l5-4 4 3 4-5 5 6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    name: "BlurHash",
    tagline: "Smooth gradient placeholders",
    body: "The classic base-83 string format, encoded and decoded entirely in Rust. Drop-in compatible with the blurhash-python API.",
    replaces: ["blurhash-python"],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-7">
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M3 9h18M3 14h18M8 4v16M15 4v16" opacity="0.45" />
        <path d="M3 20c6-8 12-2 18-8" strokeLinecap="round" opacity="0.8" />
      </svg>
    ),
  },
  {
    name: "ColorThief",
    tagline: "Dominant colour & palettes",
    body: "Median-cut palette extraction from any image format — bytes, BytesIO, paths or PIL Images. Strict, validated quality range.",
    replaces: ["colorthief", "fast-colorthief"],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-7">
        <circle cx="9" cy="9" r="6" />
        <circle cx="15" cy="15" r="6" opacity="0.55" />
        <circle cx="9" cy="15" r="6" opacity="0.75" />
      </svg>
    ),
  },
  {
    name: "Thumbnail",
    tagline: "Real thumbnails, any source",
    body: "Rasterised thumbnails for images, MP4 videos and PDFs. A pure-Rust fallback engine needs no ffmpeg and no pdfium.",
    replaces: ["no direct equivalent"],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-7">
        <rect x="3" y="5" width="13" height="14" rx="2" />
        <path d="m16 10 5-3v10l-5-3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    name: "Compress",
    tagline: "mozjpeg-class re-encoding",
    body: "Optional pixo-powered JPEG & PNG optimisation, auto-applied to thumbnail output. Never returns a larger file — guaranteed by a strict size guard.",
    replaces: ["pixo feature"],
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" className="size-7">
        <path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" strokeLinecap="round" />
        <path d="M9 12h6" strokeLinecap="round" />
      </svg>
    ),
  },
];

export default function Features() {
  return (
    <section id="features" className="relative mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6 }}
        className="mb-10 max-w-2xl"
      >
        <p className="font-mono text-xs font-medium tracking-[0.2em] uppercase text-secondary">
          What&apos;s in the wheel
        </p>
        <h2 className="font-display mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          One package that herds the whole flock
        </h2>
        <p className="mt-3 text-base-content/70">
          Every subsystem is a drop-in replacement for the library it replaces — same import
          names, same API shapes, just dramatically faster.
        </p>
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {subsystems.map((s, i) => (
          <motion.article
            key={s.name}
            initial={{ opacity: 0, y: 28 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: (i % 3) * 0.1, ease: "easeOut" }}
            whileHover={{ y: -4 }}
            className="card bg-base-100 shadow-sm ring-1 ring-base-300 transition-shadow hover:shadow-lg"
          >
            <div className="card-body">
              <div className="mb-1 flex size-12 items-center justify-center rounded-field bg-secondary/15 text-secondary">
                {s.icon}
              </div>
              <h3 className="font-display card-title text-xl">{s.name}</h3>
              <p className="text-sm font-medium text-primary">{s.tagline}</p>
              <p className="text-sm leading-relaxed text-base-content/70">{s.body}</p>
              <div className="mt-auto flex flex-wrap gap-1.5 pt-2">
                {s.replaces.map((r) => (
                  <span key={r} className="badge badge-sm badge-ghost font-mono">
                    ↻ {r}
                  </span>
                ))}
              </div>
            </div>
          </motion.article>
        ))}

        <motion.article
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
          className="wood-panel rounded-box flex flex-col justify-between p-6"
        >
          <div>
            <h3 className="font-display text-xl font-semibold">Built like farm equipment</h3>
            <ul className="mt-3 space-y-2 text-sm leading-relaxed">
              <li className="flex gap-2">
                <span className="text-accent">✓</span> GIL released for every CPU-bound call
              </li>
              <li className="flex gap-2">
                <span className="text-accent">✓</span> Fully typed — py.typed + .pyi stubs
              </li>
              <li className="flex gap-2">
                <span className="text-accent">✓</span> 500+ tests across Python &amp; Rust
              </li>
              <li className="flex gap-2">
                <span className="text-accent">✓</span> Wheels for Windows, Linux, macOS —
                x86&nbsp;64-bit, ARM64, i686, armv7
              </li>
            </ul>
          </div>
          <p className="mt-4 font-mono text-xs text-accent/80">— the thumbleweed warranty</p>
        </motion.article>
      </div>
    </section>
  );
}
