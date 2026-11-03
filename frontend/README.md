# thumbleweed.org frontend

Marketing site + live playground for [thumbleweed](https://github.com/New-Elysium/thumbleweed),
built with [vinext](https://vinext.dev) (the Next.js API surface on Vite), Tailwind CSS v4,
daisyUI 5, framer-motion, and Bun as the package manager.

## Stack

| Piece | Version | Notes |
|---|---|---|
| vinext | 1.4.x | App Router + RSC on Vite 8 |
| React | 19.3.x | |
| Tailwind CSS | 4.3.x | via `@tailwindcss/postcss` |
| daisyUI | 5.7.x | custom `tumbleweed` theme in `app/globals.css` |
| framer-motion | 14.x | client components only |
| Vite | 8.3.x | runs under Node ≥ 22.18 (Cloudflare config loader rejects the Bun runtime) |

## The WASM playground

The "Try it in your browser" section runs the **actual ThumbHash and BlurHash algorithms**
from `src/thumbhash.rs` / `src/blurhash.rs`, cross-compiled to a 52 KB
`wasm32-unknown-unknown` module:

- `wasm-thumbleweed/` — a standalone `cdylib` crate with trimmed (pyo3-free) copies of the
  pure algorithm cores and a small C ABI (`tw_alloc`, `tw_thumbhash_encode`, …).
  Unit tests round-trip both hashes: `cargo test` inside that directory.
- `app/lib/wasm.ts` — JS wrapper that instantiates the module directly (no wasm-bindgen glue).
- `public/wasm/thumbleweed.wasm` — the built artifact, refreshed via:

```bash
bun run build:wasm   # cargo + wasm32-unknown-unknown target required
```

## Commands

```bash
bun install          # install deps
bun run dev          # dev server (http://localhost:3001)
bun run build        # production build
bun run start        # preview the production build
bun run deploy       # build + deploy to Cloudflare (thumbleweed.org custom domains)
bun run build:wasm   # rebuild public/wasm/thumbleweed.wasm from Rust sources
```

> **Why `node` in the scripts?** `@cloudflare/vite-plugin` cannot load
> `cloudflare.config.ts` under the Bun runtime — Bun stays the package manager, but the
> vite/CLI entry points are invoked through Node.

## Deployment

`bun run deploy` uses `@vinext/cloudflare deploy` (auth via `cf`). First-time auth:

```bash
bunx cf auth login               # or: export CLOUDFLARE_API_TOKEN=...
```

The `thumbleweed.org` and `www.thumbleweed.org` custom domains and the zone routing are
declared in `cloudflare.config.ts` (`domains`, `workersDev: false`) and applied on every
deploy — no dashboard steps needed. The workers.dev preview URL is intentionally disabled;
the site is served exclusively from the zone.
