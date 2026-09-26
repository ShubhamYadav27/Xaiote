import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://www.xaiote.com"),
  title: "Xaiote — Manufacturing Intelligence",
  description: "Production Risk & Root-Cause Intelligence",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Xaiote — Manufacturing Intelligence",
    description: "Production Risk & Root-Cause Intelligence",
    url: "https://www.xaiote.com",
    siteName: "Xaiote",
    images: [{ url: "/Logo(icon).png", width: 800, height: 600 }],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Xaiote — Manufacturing Intelligence",
    description: "Production Risk & Root-Cause Intelligence",
    images: ["/Logo(icon).png"],
  },
  icons: {
    icon: "/Logo(icon).png",
    shortcut: "/Logo(icon).png",
    apple: "/Logo(icon).png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
