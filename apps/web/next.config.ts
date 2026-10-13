import type { NextConfig } from "next";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

// Set FRAME_ANCESTORS (e.g. "'self' https://huggingface.co") at build time to allow embedding; default is no framing.
const FRAME_ANCESTORS = process.env.FRAME_ANCESTORS;

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  FRAME_ANCESTORS
    ? { key: "Content-Security-Policy", value: `frame-ancestors ${FRAME_ANCESTORS}` }
    : { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  // The browser talks to FastAPI through this same-origin proxy so the session cookie stays httpOnly + SameSite.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion", "@react-three/drei"],
  },
};

export default nextConfig;
