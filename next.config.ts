import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Tauri serves the compiled frontend from disk, so it must be a static export.
  output: "export",
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
