/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pure static site: `next build` emits ./out, deployable to any static host
  // (Streamlit-free, no backend). Data is fetched at runtime from /data/cluster.json.
  output: "export",
  // Emit <route>/index.html so the site resolves on any static host (and a bare
  // python http.server) without per-host extensionless-route rewrites.
  trailingSlash: true,
  images: { unoptimized: true },
  // No ESLint config shipped; keep the production build deterministic offline.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
