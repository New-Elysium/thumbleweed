"use client";

import { motion } from "framer-motion";

const platforms = [
  { os: "Linux", archs: ["x86_64", "aarch64", "i686", "armv7"], manylinux: true },
  { os: "macOS", archs: ["x86_64 (Intel)", "arm64 (Apple Silicon)"], manylinux: false },
  { os: "Windows", archs: ["x86_64", "i686", "aarch64"], manylinux: false },
];

const pythons = ["3.11", "3.12", "3.13", "3.14", "3.14t", "3.15", "3.15t"];

export default function Compat() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
      <div className="grid gap-4 md:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5 }}
          className="card bg-base-100 shadow-sm ring-1 ring-base-300"
        >
          <div className="card-body">
            <h3 className="font-display card-title">Python versions</h3>
            <div className="flex flex-wrap gap-2 pt-1">
              {pythons.map((p) => (
                <span key={p} className="badge badge-lg badge-outline font-mono">
                  {p.endsWith("t") ? (
                    <>
                      {p.slice(0, -1)}
                      <span className="ml-1 text-secondary">free-threaded</span>
                    </>
                  ) : (
                    p
                  )}
                </span>
              ))}
            </div>
            <p className="pt-2 text-sm text-base-content/60">
              Pre-built wheels for every version above, built fresh in CI on each release.
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="card bg-base-100 shadow-sm ring-1 ring-base-300"
        >
          <div className="card-body">
            <h3 className="font-display card-title">Platforms</h3>
            <div className="space-y-2 pt-1">
              {platforms.map((p) => (
                <div key={p.os} className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-medium">{p.os}</span>
                  <span className="font-mono text-sm text-base-content/60">{p.archs.join(" · ")}</span>
                </div>
              ))}
            </div>
            <p className="pt-2 text-sm text-base-content/60">
              Linux wheels tagged <code className="font-mono">manylinux_2_28</code>; macOS and
              Windows wheels are universal installs.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
