import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EchoBridge",
  description: "An accessibility-first communication bridge for deaf, hard-of-hearing, and speech-impaired users.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}