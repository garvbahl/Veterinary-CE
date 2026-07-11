import type { Metadata } from "next";
import "./globals.css";

import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Veterinary Dentistry CE | aggregated by PerioVive",
  description:
    "A directory of veterinary dentistry continuing education, aggregated by PerioVive from providers across the profession. Filter by RACE credits, audience, format, and topic.",
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