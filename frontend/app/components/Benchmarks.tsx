"use client";

import { motion, useInView } from "framer-motion";
import { useEffect, useRef, useState } from "react";

const rows = [
  { op: "ThumbHash encode", mine: 825.4, theirs: 27260, unit: "µs", factor: 33.0, competitor: "thumbhash-python (pure Python)" },
  { op: "ThumbHash decode", mine: 56.4, theirs: 5490, unit: "µs", factor: 97.3, competitor: "thumbhash-python (pure Python)" },
  { op: "BlurHash encode", mine: 4980, theirs: 4420, unit: "µs", factor: 1.0, competitor: "blurhash-python (CFFI)" },
  { op: "BlurHash decode 64×64", mine: 902.4, theirs: 842.2, unit: "µs", factor: 1.0, competitor: "blurhash-python (CFFI)" },
  { op: "ColorThief dominant", mine: 5090, theirs: 18620, unit: "µs", factor: 3.7, competitor: "fast-colorthief (C ext + NumPy)" },
  { op: "ColorThief palette-10", mine: 5170, theirs: 18380, unit: "µs", factor: 3.6, competitor: "fast-colorthief (C ext + NumPy)" },
];

function useCountUp(target: number, active: boolean, duration = 1400) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setValue(target * (1 - Math.pow(1 - t, 3)));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, active, duration]);
  return value;
}

// Smallest bar we still draw, so a very fast call stays visible as a sliver
// instead of collapsing to a 1px line.
const MIN_BAR_WIDTH = 3;

function Bar({
  label,
  competitor,
  mine,
  theirs,
  factor,
  index,
  active,
}: {
  label: string;
  competitor: string;
  mine: number;
  theirs: number;
  factor: number;
  index: number;
  active: boolean;
}) {
  const animatedFactor = useCountUp(factor, active);
  // Each pair shares one scale: the slower of the two fills the track and the
  // faster one is proportional to it, so bar length reads as the ratio instead
  // of being measured against an arbitrary global axis.
  const slowest = Math.max(mine, theirs);
  const widthFor = (v: number) =>
    Math.max(MIN_BAR_WIDTH, Math.min(100, (v / slowest) * 100));
  const wins = factor >= 1.5;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={active ? { opacity: 1, y: 0 } : {}}
      transition={{ delay: index * 0.08, duration: 0.5 }}
    >
      <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="font-medium">{label}</span>
        <span className="text-xs text-base-content/70">vs {competitor}</span>
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="w-20 shrink-0 font-mono text-xs text-secondary sm:w-24">
            thumbleweed
          </span>
          <div className="h-4 min-w-0 flex-1 overflow-hidden rounded-field bg-base-200">
            <motion.div
              className="h-full rounded-field bg-secondary"
              initial={{ width: 0 }}
              animate={active ? { width: `${widthFor(mine)}%` } : {}}
              transition={{ delay: index * 0.08 + 0.15, duration: 0.7, ease: "easeOut" }}
            />
          </div>
          <span className="w-16 shrink-0 text-right font-mono text-xs text-base-content/70 sm:w-20">
            {mine < 1000 ? `${mine} µs` : `${(mine / 1000).toFixed(1)} ms`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-20 shrink-0 truncate font-mono text-xs text-base-content/70 sm:w-24">
            competitor
          </span>
          <div className="h-4 min-w-0 flex-1 overflow-hidden rounded-field bg-base-200">
            <motion.div
              className="h-full rounded-field bg-base-content/30"
              initial={{ width: 0 }}
              animate={active ? { width: `${widthFor(theirs)}%` } : {}}
              transition={{ delay: index * 0.08 + 0.3, duration: 0.7, ease: "easeOut" }}
            />
          </div>
          <span className="w-16 shrink-0 text-right font-mono text-xs text-base-content/70 sm:w-20">
            {theirs < 1000 ? `${theirs} µs` : `${(theirs / 1000).toFixed(1)} ms`}
          </span>
        </div>
      </div>
      <div
        className={`mt-1 text-right text-sm font-semibold ${wins ? "text-primary" : "text-base-content/70"}`}
      >
        {wins ? `⚡ ${animatedFactor.toFixed(1)}× faster` : "~ on par"}
      </div>
    </motion.div>
  );
}

export default function Benchmarks() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });

  return (
    <section id="benchmarks" className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6 }}
        className="mb-10 max-w-2xl"
      >
        <p className="font-mono text-xs font-medium tracking-[0.2em] uppercase text-secondary">
          Horsepower
        </p>
        <h2 className="font-display mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
          Measured against the old workhorses
        </h2>
        <p className="mt-3 text-base-content/70">
          Mean per-call latency over the real test-fixture images (5 rounds × 100 iterations).
          Lower is better; each pair is scaled to its own slower bar, so bar length tracks
          latency directly. Full methodology lives in the repo README.
        </p>
      </motion.div>

      <motion.div
        ref={ref}
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.5 }}
        className="grid gap-x-10 gap-y-8 rounded-box bg-base-100 p-6 shadow-sm ring-1 ring-base-300 md:grid-cols-2 sm:p-8"
      >
        { rows.map((row, i) => (
          <Bar key={row.op} label={row.op} competitor={row.competitor} mine={row.mine} theirs={row.theirs} factor={row.factor} index={i} active={inView} />
        ))}
      </motion.div>
      <p className="mt-4 text-center text-xs text-base-content/70">
        ThumbHash &amp; ColorThief timings include full image decode — real end-to-end usage, not
        just the inner loop.
      </p>
    </section>
  );
}
