import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClassificationBanner } from "@/components/gaia/classification-banner";
import { AppSidebar } from "@/components/layout/app-sidebar";
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
  title: "GEOINT Prospect",
  description: "Intelligence workstation for geospatial discovery and analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex h-dvh flex-col overflow-hidden">
        <ClassificationBanner />
        <div className="flex min-h-0 flex-1">
          <AppSidebar />
          <main className="min-w-0 flex-1 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
