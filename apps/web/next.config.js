const nextConfig= {
  // Standalone output for Docker deployment
  output: "standalone",

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "cdn.aurafit.ai" },
      { protocol: "https", hostname: "*.amazonaws.com" },
      { protocol: "https", hostname: "storage.googleapis.com" },
      { protocol: "http",  hostname: "localhost" },
    ],
    formats: ["image/avif", "image/webp"],
  },

  experimental: {
    // Optimise bundle for App Router
    optimizePackageImports: ["lucide-react", "framer-motion", "@radix-ui/react-*"],
  },

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_APP_NAME: "AuraFit",
    NEXT_PUBLIC_APP_VERSION: "1.0.0",
  },

  // Security headers
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options",    value: "nosniff" },
          { key: "X-Frame-Options",            value: "DENY" },
          { key: "Referrer-Policy",            value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy",         value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },

  // API proxy — avoids CORS in development
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:80"}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
