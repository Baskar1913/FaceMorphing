import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FaceMorph Studio — Identity-aware AI Video Editing",
  description: "Upload a video and two reference faces to morph one specific person while preserving every other face and the original audio.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
