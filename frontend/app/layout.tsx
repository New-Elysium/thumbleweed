import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Fraunces, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://thumbleweed.org"),
  icons: { icon: "/thumbleweed.svg" },
  title: {
    default: "thumbleweed — image hashing, thumbnails & compression from Rust",
    template: "%s · thumbleweed",
  },
  description:
    "ThumbHash, BlurHash, ColorThief, thumbnails and compression for Python — five tools in one wheel, powered by a pure-Rust core. Zero mandatory dependencies.",
  applicationName: "thumbleweed",
  keywords: [
    "thumbhash",
    "blurhash",
    "colorthief",
    "placeholder",
    "image hashing",
    "thumbnail",
    "compression",
    "rust",
    "python",
    "pyo3",
  ],
  openGraph: {
    title: "thumbleweed",
    description:
      "Five tools. One wheel. Zero dependencies. ThumbHash, BlurHash, ColorThief, thumbnails and compression for Python — Rust under the hood.",
    url: "https://thumbleweed.org",
    siteName: "thumbleweed",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary",
    title: "thumbleweed",
    description:
      "ThumbHash, BlurHash, ColorThief, thumbnails and compression for Python — Rust under the hood.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-theme="tumbleweed" className={`${fraunces.variable} ${plexMono.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
