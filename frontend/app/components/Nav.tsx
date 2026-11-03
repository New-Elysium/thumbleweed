"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const links = [
  { href: "#features", label: "Features" },
  { href: "#playground", label: "Playground" },
  { href: "#benchmarks", label: "Benchmarks" },
  { href: "#quickstart", label: "Quick start" },
];

function formatStars(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1).replace(/\.0$/, "")}k` : String(n);
}

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [stars, setStars] = useState<number | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    fetch("https://api.github.com/repos/New-Elysium/thumbleweed")
      .then((r) => (r.ok ? r.json() : null))
      .then((d: unknown) => {
        if (d && typeof d === "object" && typeof (d as { stargazers_count?: unknown }).stargazers_count === "number") {
          setStars((d as { stargazers_count: number }).stargazers_count);
        }
      })
      .catch(() => {
        // rate-limited or offline — button still works without the count
      });
  }, []);

  return (
    <motion.header
      initial={{ y: -56, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="fixed inset-x-0 top-0 z-50"
    >
      <div
        className={`mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 transition-all duration-300 sm:px-6 ${
          scrolled
            ? "mt-2 rounded-box border border-base-300 bg-base-100/90 py-2 shadow-md backdrop-blur"
            : "mt-4 py-3"
        }`}
      >
        <a href="#top" className="flex items-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/thumbleweed-animated.svg"
            alt="thumbleweed"
            className="h-9 w-auto sm:h-10"
          />
        </a>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-field px-3 py-1.5 text-sm font-medium text-base-content/70 transition-colors hover:bg-base-200 hover:text-base-content"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <a
            href="https://pypi.org/project/thumbleweed/"
            target="_blank"
            rel="noreferrer"
            className="btn btn-sm btn-ghost hidden sm:inline-flex"
          >
            PyPI
          </a>
          <a
            href="https://github.com/New-Elysium/thumbleweed"
            target="_blank"
            rel="noreferrer"
            className="btn btn-sm btn-primary gap-1.5"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="size-4" aria-hidden="true">
              <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z" />
            </svg>
            Star
            <span className="hidden sm:inline">on GitHub</span>
            {stars !== null && (
              <span className="ml-0.5 rounded-full border border-base-100/30 bg-base-100/15 px-1.5 font-mono text-xs">
                {formatStars(stars)}
              </span>
            )}
          </a>
        </div>
      </div>
    </motion.header>
  );
}
