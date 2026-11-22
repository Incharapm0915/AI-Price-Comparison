import type { Metadata } from "next";

import { Header } from "@/components/Header";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI Price Comparison",
  description: "Compare the same product across Amazon, Flipkart, and more.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[var(--background)] antialiased">
        <Header />
        {children}
      </body>
    </html>
  );
}
