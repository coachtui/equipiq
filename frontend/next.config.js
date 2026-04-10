/** @type {import('next').NextConfig} */
const nextConfig = {
  // Extend the proxy socket timeout so sessions that take 30s+ don't get ECONNRESET.
  // Node default is ~5s keep-alive; 90s covers worst-case multi-turn + synthesize_result latency.
  httpAgentOptions: {
    keepAliveMsecs: 90_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL || "http://localhost:8000"}/api/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${process.env.API_URL || "http://localhost:8000"}/uploads/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
