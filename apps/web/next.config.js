const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ["@prisma/client", "@daytonaio/sdk"],
  },
  webpack: (config, { isServer }) => {
    // Make @daytonaio/sdk optional - it will be installed in production
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push("@daytonaio/sdk");
    }
    return config;
  },
};

module.exports = withSentryConfig(
  nextConfig,
  {
    silent: true,
    org: process.env.SENTRY_ORG,
    project: process.env.SENTRY_PROJECT,
  },
  {
    widenClientFileUpload: true,
    transpileClientSDK: true,
    tunnelRoute: "/monitoring",
    hideSourceMaps: true,
    disableLogger: true,
    automaticVercelMonitors: true,
  }
);
