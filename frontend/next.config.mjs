/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  // Static export: no Next.js server at runtime. FastAPI serves out/ at same origin.
  images: {
    unoptimized: true,
  },
  trailingSlash: false,
  // All API/SSE calls use relative /api paths -> same origin in prod.
};

export default nextConfig;
