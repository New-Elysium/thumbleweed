"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.15 + i * 0.12, duration: 0.6, ease: [0.22, 1, 0.36, 1] as const },
  }),
};

/** A little tumbleweed that rolls across the prairie once, on mount. */
function RollingTumbleweed() {
  return (
    <motion.div
      className="pointer-events-none absolute bottom-10 left-0 hidden lg:block"
      initial={{ x: -80, opacity: 0 }}
      animate={{ x: "56rem", opacity: [0, 1, 1, 0] }}
      transition={{ duration: 11, delay: 1.2, ease: "linear", opacity: { times: [0, 0.06, 0.94, 1] } }}
      aria-hidden="true"
    >
      <motion.svg
        viewBox="0 0 48 48"
        className="size-12 text-primary/60"
        fill="none"
        animate={{ rotate: 1440 }}
        transition={{ duration: 11, ease: "linear" }}
        style={{ x: "-50%" }}
      >
        <g stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
          <path d="M8 30c8-10 16-2 26-14" />
          <path d="M10 20c10 6 14-4 28 2" />
          <path d="M12 34c6-4 18 2 24-8" />
          <path d="M16 12c2 8 12 6 18 18" />
        </g>
      </motion.svg>
    </motion.div>
  );
}

/** Patch of prairie grass along the bottom of the hero. */
function PrairieGrass() {
  return (
    <svg
      viewBox="0 0 1200 60"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-x-0 bottom-0 h-10 w-full text-secondary/50"
      aria-hidden="true"
    >
      <path
        fill="currentColor"
        d="M0 60c30-18 42-34 50-44 2 10 6 28 12 44 18-12 30-26 36-38 4 12 10 26 18 38 16-14 26-28 30-40 6 14 14 28 24 40 14-10 24-22 30-34 6 12 14 24 24 34 12-8 20-18 26-30 6 12 16 22 28 30 10-8 18-16 24-26 8 10 18 18 30 26 10-6 18-14 24-22 8 8 18 16 30 22 10-6 18-12 24-18 10 8 22 14 34 18 8-4 16-10 22-16 10 6 22 12 36 16 12-2 24-6 34-12 10 6 24 10 38 12 14-2 26-6 36-12 12 6 26 10 40 12 14-2 26-8 36-14 12 6 26 10 42 12 16-2 30-6 42-12 14 6 30 10 46 12V60H0Z"
      />
    </svg>
  );
}

export default function Hero() {
  const [launching, setLaunching] = useState(false);
  const [copied, setCopied] = useState(false);
  const [encodeUs, setEncodeUs] = useState(0);

  useEffect(() => {
    const controls = { raf: 0, start: 0 };
    const target = 825.4;
    controls.start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - controls.start) / 1600);
      const eased = 1 - Math.pow(1 - t, 3);
      setEncodeUs(target * eased);
      if (t < 1) controls.raf = requestAnimationFrame(tick);
    };
    controls.raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(controls.raf);
  }, []);

  const copyInstall = async () => {
    try {
      await navigator.clipboard.writeText("pip install thumbleweed");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable (e.g. insecure context) — still redirect
    }
    setLaunching(true);
    setTimeout(() => {
      window.location.href = "https://pypi.org/project/thumbleweed/";
    }, 1000);
  };

  return (
    <section id="top" className="relative overflow-hidden pt-32 pb-40 sm:pt-40">
      <RollingTumbleweed />
      <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
        <motion.p
          custom={0}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="postmark inline-flex rotate-[-2deg] px-4 py-1 font-mono text-xs font-medium tracking-[0.2em] uppercase text-primary"
        >
          Rust under the hood · Python on the reins
        </motion.p>

        <motion.h1
          custom={1}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="font-display mt-6 max-w-3xl text-4xl leading-[1.1] font-semibold tracking-tight text-base-content sm:text-6xl"
        >
          Five tools.{" "}
          <span className="text-primary">One wheel.</span>{" "}
          <span className="relative inline-block">
            Zero dependencies.
            <motion.svg
              viewBox="0 0 300 12"
              className="absolute -bottom-1 left-0 w-full text-accent"
              fill="none"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 1, duration: 0.8, ease: "easeOut" }}
            >
              <motion.path
                d="M4 8 C 80 2, 160 10, 296 4"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: 1, duration: 0.8, ease: "easeOut" }}
              />
            </motion.svg>
          </span>
        </motion.h1>

        <motion.p
          custom={2}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-6 max-w-2xl text-lg leading-relaxed text-base-content/75"
        >
          thumbleweed unifies <strong>ThumbHash</strong>, <strong>BlurHash</strong>,{" "}
          <strong>ColorThief</strong>, real <strong>thumbnails</strong> (images, videos, PDFs) and{" "}
          <strong>mozjpeg-class compression</strong> into a single Python package — powered by a
          pure-Rust core. No C extensions. No NumPy. No fuss.
        </motion.p>

        <motion.div
          custom={3}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-8 flex flex-wrap items-center gap-3"
        >
          <button onClick={copyInstall} className="btn btn-primary btn-lg font-mono">
            <span aria-hidden="true">$</span>
            <code className="text-base">pip install thumbleweed</code>
            {launching ? (
              <motion.span
                animate={{ x: [0, 4, 0] }}
                transition={{ repeat: Infinity, duration: 1.6, ease: "easeInOut" }}
                className="ml-1"
                aria-hidden="true"
              >
                →
              </motion.span>
            ) : (
              <svg viewBox="0 0 20 20" fill="currentColor" className="size-4 opacity-70" aria-hidden="true">
                <path d="M7 3a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V8.4L11.6 5H7Z" opacity=".5" />
                <path d="M12 1H5a2 2 0 0 0-2 2v9h2V3h5.6L14 6.4V12h2V5.6a2 2 0 0 0-.6-1.4l-2.6-2.6A2 2 0 0 0 12 1Z" opacity=".35" />
              </svg>
            )}
          </button>
          <a href="#playground" className="btn btn-outline btn-lg">
            Try it in your browser
            <motion.span
              animate={{ x: [0, 4, 0] }}
              transition={{ repeat: Infinity, duration: 1.6, ease: "easeInOut" }}
            >
              →
            </motion.span>
          </a>
        </motion.div>

        <motion.div
          custom={4}
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="mt-12 grid max-w-3xl grid-cols-2 gap-3 sm:grid-cols-4"
        >
          {[
            { value: `${encodeUs.toFixed(0)} µs`, label: "ThumbHash encode", sub: "33× faster than pure Python" },
            { value: "5", label: "subsystems", sub: "one import away" },
            { value: "3.11–3.15", label: "Python versions", sub: "incl. free-threaded" },
            { value: "0", label: "dependencies", sub: "Pillow optional" },
          ].map((stat) => (
            <div key={stat.label} className="stitch rounded-box bg-base-100/70 px-4 py-3">
              <div className="font-display text-2xl font-semibold text-primary">{stat.value}</div>
              <div className="text-sm font-medium text-base-content">{stat.label}</div>
              <div className="text-xs text-base-content/60">{stat.sub}</div>
            </div>
          ))}
        </motion.div>
      </div>
      <PrairieGrass />

      <AnimatePresence>
        {copied && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="toast toast-bottom toast-center"
            role="status"
          >
            <div className="alert alert-success">
              <span>Copied to clipboard</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
