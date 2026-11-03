"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const links = [
  { href: "#features", label: "Features" },
  { href: "#playground", label: "Playground" },
  { href: "#benchmarks", label: "Benchmarks" },
  { href: "#quickstart", label: "Quick start" },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
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
            className="btn btn-sm btn-primary"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="size-4" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
            GitHub
          </a>
        </div>
      </div>
    </motion.header>
  );
}
