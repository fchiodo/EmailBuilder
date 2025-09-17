/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/orchestrator/:path*',
        destination: `${process.env.ORCHESTRATOR_URL || 'http://localhost:8000'}/:path*`,
      },
    ];
  },
  env: {
    ORCHESTRATOR_URL: process.env.ORCHESTRATOR_URL || 'http://localhost:8000',
  },
};

module.exports = nextConfig;