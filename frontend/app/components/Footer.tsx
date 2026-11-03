export default function Footer() {
  return (
    <footer className="wood-panel mt-10">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="flex flex-col items-start justify-between gap-8 md:flex-row">
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/thumbleweed.svg" alt="" className="size-9" />
              <span className="font-display text-xl font-semibold">thumbleweed</span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[#efe3cc]/70">
              Unified image hashing, thumbnailing and compression for Python. Rust-powered via
              PyO3 + maturin. MIT licensed.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10">
            <div>
              <h4 className="font-mono text-xs tracking-[0.2em] uppercase text-accent">Install</h4>
              <ul className="mt-3 space-y-2 text-sm text-[#efe3cc]/80">
                <li>
                  <code className="font-mono">pip install thumbleweed</code>
                </li>
                <li>
                  <code className="font-mono">pip install &quot;thumbleweed[pillow]&quot;</code>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-mono text-xs tracking-[0.2em] uppercase text-accent">Links</h4>
              <ul className="mt-3 space-y-2 text-sm">
                <li>
                  <a className="link-hover link text-[#efe3cc]/80" href="https://pypi.org/project/thumbleweed/" target="_blank" rel="noreferrer">
                    PyPI
                  </a>
                </li>
                <li>
                  <a className="link-hover link text-[#efe3cc]/80" href="https://github.com/New-Elysium/thumbleweed" target="_blank" rel="noreferrer">
                    GitHub
                  </a>
                </li>
                <li>
                  <a className="link-hover link text-[#efe3cc]/80" href="https://github.com/New-Elysium/thumbleweed/issues" target="_blank" rel="noreferrer">
                    Issues
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="rope-divider mt-10" />
        <p className="mt-4 text-center font-mono text-xs text-[#efe3cc]/50">
          © {new Date().getFullYear()} thumbleweed contributors · MIT Licence · tumbleweeds roll
          free
        </p>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/footer.svg"
          alt="A tumbleweed rolling across the desert horizon"
          className="mx-auto mt-8 h-auto w-full max-w-3xl rounded-box opacity-90"
        />
      </div>
    </footer>
  );
}
