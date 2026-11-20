import type { NextConfig } from "next";

if (process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.includes("localhost")) {
  throw new Error(
    "PRODUCTION CONFIG ERROR: NEXT_PUBLIC_API_URL is pointing to localhost. Remove it from your production build environment."
  );
}

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
