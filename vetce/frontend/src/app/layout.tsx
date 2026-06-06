import type { Metadata } from "next";
import "./globals.css";

import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "PerioVive CE — Veterinary Continuing Education",
  description:
    "Aggregated veterinary continuing education listings. Filter by RACE credits, audience, format, and topic.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased text-ink-900 bg-white">
        <Header />
        <div className="min-h-[calc(100vh-4rem)]">{children}</div>
        <Footer />
      </body>
    </html>
  );
}