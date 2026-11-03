"use client";

import { motion } from "framer-motion";
import { useState } from "react";

type Snippet = { id: string; label: string; lang: string; code: string };

const snippets: Snippet[] = [
  {
    id: "thumbhash",
    label: "ThumbHash",
    lang: "python",
    code: `from PIL import Image
import thumbhash as th

img = Image.open("photo.jpg")
hash_str = th.encode_image(img)      # base64, ~20-40 chars
placeholder = th.decode_image(hash_str)  # RGBA preview, ≈32 px

# Raw pixel API — no Pillow needed
hash_bytes = th.encode(w, h, rgba_bytes)`,
  },
  {
    id: "blurhash",
    label: "BlurHash",
    lang: "python",
    code: `import blurhash as bh

hash_str = bh.encode_image(img, cx=4, cy=3)
rgba = bh.decode(hash_str, width=64, height=64)

# Decoding rejects invalid base-83 characters,
# instead of silently treating them as zero.`,
  },
  {
    id: "colorthief",
    label: "ColorThief",
    lang: "python",
    code: `import colorthief as ct

dominant = ct.get_color(image_bytes)            # (r, g, b)
palette = ct.get_palette(image_bytes, color_count=5)

# Class-based API — drop-in for the colorthief package
thief = ct.ColorThief("photo.jpg")
palette = thief.get_palette(color_count=8)`,
  },
  {
    id: "thumbnail",
    label: "Thumbnail",
    lang: "python",
    code: `from thumbleweed import thumbnail

thumb = thumbnail.create("holiday.mp4", width=256)   # video
thumb = thumbnail.create("manual.pdf", format="png") # PDF
thumbnail.save("photo.jpg", "thumb.webp", width=64)

thumbnail.detect_kind("file.pdf")      # "pdf"
thumbnail.available_backends()         # ['crude', ...]`,
  },
  {
    id: "compress",
    label: "Compress",
    lang: "python",
    code: `from thumbleweed import compress

smaller = compress.compress(jpeg_bytes, quality=85)
saved = compress.compress_path("photo.jpg")  # in-place

# Returns the smaller of (pixo output, original) —
# output is NEVER larger than the input.`,
  },
];

export default function CodeShowcase() {
  const [active, setActive] = useState(snippets[0].id);
  const [copied, setCopied] = useState(false);
  const current = snippets.find((s) => s.id === active) ?? snippets[0];

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(current.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable — ignore
    }
  };

  return (
    <section id="quickstart" className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <div className="grid gap-10 lg:grid-cols-[1fr_1.2fr] lg:items-center">
        <motion.div
          initial={{ opacity: 0, x: -24 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6 }}
        >
          <p className="font-mono text-xs font-medium tracking-[0.2em] uppercase text-secondary">
            Saddle up in seconds
          </p>
          <h2 className="font-display mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
            Same APIs, Rust speed
          </h2>
          <p className="mt-3 leading-relaxed text-base-content/70">
            If you already use <code className="font-mono text-sm text-primary">thumbhash</code>,{" "}
            <code className="font-mono text-sm text-primary">blurhash</code> or{" "}
            <code className="font-mono text-sm text-primary">colorthief</code>, switching is a
            one-line change of the import. The higher-level helpers accept Pillow images, raw
            bytes, <code className="font-mono text-sm text-primary">BytesIO</code> or file paths —
            Pillow is only needed for <code className="font-mono text-sm text-primary">PIL.Image</code> inputs.
          </p>
          <div className="mt-6 rounded-box bg-base-200/70 p-4 font-mono text-sm">
            <div className="text-base-content/60"># the whole flock, one import</div>
            <div>
              <span className="text-primary">import</span> thumbleweed
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 24 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="wood-panel rounded-box p-1.5 shadow-xl"
        >
          <div className="rounded-box bg-neutral p-4 text-neutral-content">
            <div role="tablist" className="tabs tabs-border mb-3">
              {snippets.map((s) => (
                <button
                  key={s.id}
                  role="tab"
                  aria-selected={active === s.id}
                  className={`tab font-mono ${active === s.id ? "tab-active text-accent" : ""}`}
                  onClick={() => setActive(s.id)}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <motion.pre
              key={current.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="relative overflow-x-auto pt-2 font-mono text-[13px] leading-relaxed"
            >
              <button
                onClick={copy}
                className="btn btn-xs btn-ghost absolute top-2 right-0 text-neutral-content/60 hover:text-neutral-content"
                aria-label="Copy code"
              >
                {copied ? "copied ✓" : "copy"}
              </button>
              <code>{current.code}</code>
            </motion.pre>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
