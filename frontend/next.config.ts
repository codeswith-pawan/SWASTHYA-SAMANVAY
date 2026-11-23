import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable standalone output on Vercel to avoid .next/next-server.js.nft.json ENOENT errors
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
};

export default nextConfig;
