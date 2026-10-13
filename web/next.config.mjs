/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pure static site: `next build` emits ./out, deployable to any static host
  // Pages fetch /data/*.synthetic.json at runtime; only the explorer's live
  // classification calls the Python API (cri.server) at NEXT_PUBLIC_API_BASE_URL.
  output: "export",
  // Emit <route>/index.html so the site resolves on any static host (and a bare
  // python http.server) without per-host extensionless-route rewrites.
  trailingSlash: true,
  images: { unoptimized: true },
  // No ESLint config shipped; keep the production build deterministic offline.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
